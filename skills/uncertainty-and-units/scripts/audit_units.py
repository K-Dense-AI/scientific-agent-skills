#!/usr/bin/env python3
"""Scan Python source for the unit and uncertainty defects that stay silent.

The heuristic rules identify code that warrants review, not a proof of error: a stripped unit, a rescaled covariance matrix, a destroyed
correlation, a population standard deviation used as a standard uncertainty.
The scan is static - it parses the file and never imports or runs it.
"""

# This module *is* the rule tables: it names every logarithmic unit and lists
# every CODATA value it looks for, so scanning it flags its own data. The
# directive below is the same mechanism any caller has, and suppressions are
# counted in the report rather than hidden.
# audit-units: ignore-file CONST001, UNIT004

from __future__ import annotations

import argparse
import ast
import math
import re
import sys
from decimal import Decimal
from typing import Any

import _common
from _common import CliError


SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3}
MAX_FILES = 50

# `# audit-units: ignore [RULE, ...]` silences the rules on that line;
# `# audit-units: ignore-file RULE[, ...]` silences them for the whole module.
# Both forms are counted in the report, so a suppression stays visible.
SUPPRESSION = re.compile(
    r"#\s*audit-units:\s*ignore(?P<scope>-file)?(?P<rules>[\sA-Z0-9,]*)"
)

OFFSET_UNIT_TOKENS = {
    "degC",
    "degF",
    "celsius",
    "fahrenheit",
    "degree_Celsius",
    "degree_Fahrenheit",
    "degreeC",
    "degreeF",
}
LOGARITHMIC_UNIT_TOKENS = {
    "dB",
    "dBm",
    "dBW",
    "dBu",
    "dBV",
    "dBi",
    "decibel",
    "decibelmilliwatt",
    "decibelwatt",
}
ELEMENTARY_FUNCTIONS = {
    "acos",
    "acosh",
    "asin",
    "asinh",
    "atan",
    "atan2",
    "atanh",
    "cos",
    "cosh",
    "degrees",
    "erf",
    "exp",
    "expm1",
    "fabs",
    "hypot",
    "log",
    "log10",
    "log1p",
    "radians",
    "sin",
    "sinh",
    "sqrt",
    "tan",
    "tanh",
}
UNIT_PRESERVING_CALLS = {"to", "to_base_units", "to_reduced_units", "m_as", "ito"}

# CODATA 2022 recommended values, plus the constants the 2019 SI redefinition
# fixed exactly. A literal within one part in a thousand of one of these is
# almost always a constant somebody typed from memory. Every accessor below was
# checked against scipy.constants 1.18.1, whose default data set is CODATA 2022.
KNOWN_CONSTANTS: tuple[tuple[float, str, str], ...] = (
    (299792458.0, "speed of light in vacuum", "value('speed of light in vacuum')"),
    (6.62607015e-34, "Planck constant", "value('Planck constant')"),
    (1.054571817e-34, "reduced Planck constant", "value('reduced Planck constant')"),
    (1.602176634e-19, "elementary charge", "value('elementary charge')"),
    (1.380649e-23, "Boltzmann constant", "value('Boltzmann constant')"),
    (6.02214076e23, "Avogadro constant", "value('Avogadro constant')"),
    (8.314462618, "molar gas constant", "value('molar gas constant')"),
    (9.1093837139e-31, "electron mass", "value('electron mass')"),
    (1.67262192595e-27, "proton mass", "value('proton mass')"),
    (1.66053906892e-27, "atomic mass constant", "value('atomic mass constant')"),
    (5.670374419e-8, "Stefan-Boltzmann constant", "value('Stefan-Boltzmann constant')"),
    (
        6.67430e-11,
        "Newtonian constant of gravitation",
        "value('Newtonian constant of gravitation')",
    ),
    (
        9.80665,
        "standard acceleration of gravity",
        "value('standard acceleration of gravity')",
    ),
    (
        8.8541878188e-12,
        "vacuum electric permittivity",
        "value('vacuum electric permittivity')",
    ),
    (
        1.25663706127e-6,
        "vacuum magnetic permeability",
        "value('vacuum mag. permeability')",
    ),
    (5.29177210544e-11, "Bohr radius", "value('Bohr radius')"),
    (7.2973525643e-3, "fine-structure constant", "value('fine-structure constant')"),
    (10973731.568157, "Rydberg constant", "value('Rydberg constant')"),
    (96485.33212, "Faraday constant", "value('Faraday constant')"),
    (101325.0, "standard atmosphere", "value('standard atmosphere')"),
    (273.15, "zero of the Celsius scale", "zero_Celsius"),
)


def significant_digits(value: float) -> int:
    """Count the significant digits in a float's shortest representation."""

    digits = list(Decimal(repr(abs(value))).as_tuple().digits)
    while len(digits) > 1 and digits[-1] == 0:
        digits.pop()
    while len(digits) > 1 and digits[0] == 0:
        digits.pop(0)
    return len(digits)


def parse_suppressions(source: str) -> tuple[dict[int, set[str]], set[str]]:
    """Return per-line and whole-file rule suppressions.

    A trailing directive applies to its own line. A directive alone on a line
    applies to the next line, so a long statement does not have to carry the
    comment. Naming no rule, or `ALL`, suppresses every rule and is recorded as
    the `*` sentinel.
    """

    per_line: dict[int, set[str]] = {}
    whole_file: set[str] = set()
    for number, line in enumerate(source.splitlines(), start=1):
        match = SUPPRESSION.search(line)
        if match is None:
            continue
        rules = {
            item.strip()
            for item in match.group("rules").replace(" ", ",").split(",")
            if item.strip()
        }
        if not rules or "ALL" in rules:
            rules = {"*"}
        if match.group("scope"):
            whole_file |= rules
            continue
        target = number + 1 if line.lstrip().startswith("#") else number
        existing = per_line.get(target)
        if existing == {"*"} or rules == {"*"}:
            per_line[target] = {"*"}
        else:
            per_line[target] = (existing or set()) | rules
    return per_line, whole_file


def _tokens(text: str) -> set[str]:
    """Split a unit string into candidate unit tokens."""

    current: list[str] = []
    found: set[str] = set()
    for character in text:
        if character.isalnum() or character == "_":
            current.append(character)
        else:
            if current:
                found.add("".join(current))
            current = []
    if current:
        found.add("".join(current))
    return found


class Auditor(ast.NodeVisitor):
    """Collect unit and uncertainty findings from one parsed module."""

    def __init__(self, source: str, filename: str) -> None:
        self.filename = filename
        self.findings: list[dict[str, Any]] = []
        self.registry_sites: list[ast.AST] = []
        self.imports_uncertainties = False
        self.saw_delta_unit = False
        self.saw_offset_autoconvert = "autoconvert_offset_to_baseunit" in source
        self.line_suppressions, self.file_suppressions = parse_suppressions(source)
        self.suppressed = 0

    def report(
        self,
        node: ast.AST,
        rule: str,
        severity: str,
        message: str,
        remedy: str,
    ) -> None:
        self.findings.append(
            {
                "rule": rule,
                "severity": severity,
                "line": getattr(node, "lineno", 0),
                "column": getattr(node, "col_offset", 0) + 1,
                "message": message,
                "remedy": remedy,
            }
        )

    # --- imports -----------------------------------------------------------

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name.split(".", 1)[0] == "uncertainties":
                self.imports_uncertainties = True
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module and node.module.split(".", 1)[0] == "uncertainties":
            self.imports_uncertainties = True
        self.generic_visit(node)

    # --- string literals ---------------------------------------------------

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str):
            tokens = _tokens(node.value)
            if any(token.startswith("delta_") for token in tokens):
                self.saw_delta_unit = True
            if tokens & OFFSET_UNIT_TOKENS:
                self.report(
                    node,
                    "UNIT002",
                    "medium",
                    "offset temperature unit used; pint refuses to multiply or add "
                    "degC/degF quantities because the operation is ambiguous",
                    "express temperature differences in delta_degC, or build the "
                    "registry with UnitRegistry(autoconvert_offset_to_baseunit=True)",
                )
            if tokens & LOGARITHMIC_UNIT_TOKENS:
                self.report(
                    node,
                    "UNIT004",
                    "medium",
                    "logarithmic unit used; adding two pint quantities in dB or dBm "
                    "multiplies the underlying linear quantities instead of summing "
                    "them, and reports the product in squared base units",
                    "convert to a linear unit before arithmetic, then convert back",
                )
        elif isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            self._check_constant_literal(node, float(node.value))
        self.generic_visit(node)

    def _check_constant_literal(self, node: ast.Constant, value: float) -> None:
        if value == 0 or not math.isfinite(value):
            return
        if significant_digits(value) < 3:
            return
        for reference, description, accessor in KNOWN_CONSTANTS:
            if abs(value - reference) <= 1e-3 * abs(reference):
                self.report(
                    node,
                    "CONST001",
                    "low",
                    f"hard-coded literal matches the {description}; the recommended "
                    "value may be measured or exact; confirm its source and uncertainty",
                    f"use scipy.constants.{accessor}, with scipy.constants.precision "
                    "for the relative standard uncertainty (0.0 when the SI fixes "
                    "the constant exactly)",
                )
                return

    # --- attribute access --------------------------------------------------

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr == "magnitude":
            source = node.value
            preserved = (
                isinstance(source, ast.Call)
                and isinstance(source.func, ast.Attribute)
                and source.func.attr in UNIT_PRESERVING_CALLS
            )
            if not preserved:
                self.report(
                    node,
                    "UNIT003",
                    "high",
                    ".magnitude strips the unit without stating which one, so the "
                    "number that comes out depends on whatever the quantity happened "
                    "to be carrying",
                    "call .to('unit').magnitude or .m_as('unit') so the scale is "
                    "fixed at the point of extraction",
                )
        self.generic_visit(node)

    # --- calls -------------------------------------------------------------

    def visit_Call(self, node: ast.Call) -> None:
        name = self._call_name(node)
        keywords = {keyword.arg for keyword in node.keywords if keyword.arg}

        if name == "UnitRegistry":
            self.registry_sites.append(node)

        if name == "curve_fit" and "absolute_sigma" not in keywords:
            self.report(
                node,
                "UNC001",
                "high",
                "curve_fit rescales the covariance matrix by the reduced chi-square "
                "unless absolute_sigma=True, so parameter uncertainties silently "
                "absorb the goodness of fit",
                "pass absolute_sigma=True when sigma holds real standard "
                "uncertainties; leave it False only for relative weights",
            )

        if name in {"std", "var", "nanstd", "nanvar"} and not ({"ddof", "correction"} & keywords):
            if self._is_numpy_call(node):
                self.report(
                    node,
                    "UNC002",
                    "medium",
                    f"numpy {name} defaults to ddof=0, which is the population "
                    "spread; a Type A standard uncertainty needs the sample "
                    "estimate",
                    "pass ddof=1, and divide by sqrt(n) as well when you want the "
                    "standard uncertainty of the mean rather than of one reading",
                )

        if name == "ufloat":
            for argument in node.args + [kw.value for kw in node.keywords]:
                if any(
                    isinstance(inner, ast.Attribute)
                    and inner.attr in {"nominal_value", "std_dev", "n", "s"}
                    for inner in ast.walk(argument)
                ):
                    self.report(
                        node,
                        "UNC004",
                        "high",
                        "rebuilding a ufloat from another variable's nominal_value "
                        "and std_dev creates an independent variable, discarding "
                        "every correlation the original carried",
                        "pass the existing variable through, or rebuild the whole "
                        "set with correlated_values(values, covariance_matrix)",
                    )
                    break

        if self.imports_uncertainties and name in ELEMENTARY_FUNCTIONS:
            module = self._call_module(node)
            if module in {"math", "np", "numpy"}:
                self.report(
                    node,
                    "UNC003",
                    "medium",
                    f"{module}.{name} has no derivative rule for an uncertain value; "
                    "on a scalar it raises TypeError, and on an object array it "
                    "fails in the ufunc loop",
                    "use uncertainties.umath for scalars and "
                    "uncertainties.unumpy for arrays",
                )

        self.generic_visit(node)

    @staticmethod
    def _call_name(node: ast.Call) -> str | None:
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
        return None

    @staticmethod
    def _call_module(node: ast.Call) -> str | None:
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            return node.func.value.id
        return None

    @staticmethod
    def _is_numpy_call(node: ast.Call) -> bool:
        return (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in {"np", "numpy"}
        )

    def finish(self) -> list[dict[str, Any]]:
        """Emit the findings that need whole-module context."""

        if len(self.registry_sites) > 1:
            for node in self.registry_sites[1:]:
                self.report(
                    node,
                    "UNIT001",
                    "medium",
                    "a second UnitRegistry is constructed in this module; quantities "
                    "from different registries raise ValueError on any shared "
                    "operation",
                    "build one registry and share it, or call "
                    "pint.get_application_registry() everywhere",
                )
        if self.saw_offset_autoconvert or self.saw_delta_unit:
            self.findings = [
                finding for finding in self.findings if finding["rule"] != "UNIT002"
            ]
        kept = [finding for finding in self.findings if not self._suppressed(finding)]
        self.suppressed = len(self.findings) - len(kept)
        kept.sort(key=lambda item: (item["line"], item["column"], item["rule"]))
        self.findings = kept
        return kept

    def _suppressed(self, finding: dict[str, Any]) -> bool:
        """Report whether a directive comment silences this finding."""

        if "*" in self.file_suppressions or finding["rule"] in self.file_suppressions:
            return True
        rules = self.line_suppressions.get(finding["line"])
        if rules is None:
            return False
        return "*" in rules or finding["rule"] in rules


def audit_source(source: str, filename: str) -> dict[str, Any]:
    """Parse one module and return its findings and suppression count."""

    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as exc:
        raise CliError(f"{filename}: cannot parse as Python: {exc}") from exc
    auditor = Auditor(source, filename)
    auditor.visit(tree)
    findings = auditor.finish()
    return {"findings": findings, "suppressed": auditor.suppressed}


def render_markdown(document: dict[str, Any]) -> str:
    """Render findings grouped by file."""

    lines = ["# Unit and uncertainty audit", ""]
    counts = document["counts"]
    lines.append(
        f"{counts['total']} findings across {document['files_scanned']} files "
        f"({counts['high']} high, {counts['medium']} medium, {counts['low']} low), "
        f"{counts['suppressed']} suppressed by directive comments."
    )
    for entry in document["results"]:
        lines += ["", f"## {entry['file']}", ""]
        if not entry["findings"]:
            lines.append(f"No findings ({entry['suppressed']} suppressed).")
            continue
        lines.append("| Line | Rule | Severity | Finding |")
        lines.append("| --- | --- | --- | --- |")
        for finding in entry["findings"]:
            lines.append(
                f"| {finding['line']} | {finding['rule']} | {finding['severity']} | "
                f"{finding['message']} |"
            )
        lines.append("")
        for finding in entry["findings"]:
            lines.append(
                f"- **{finding['rule']}** (line {finding['line']}): "
                f"{finding['remedy']}"
            )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Statically audit Python sources for stripped units, offset-temperature "
            "arithmetic, broken uncertainty propagation, and hard-coded constants."
        )
    )
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        required=True,
        help="Python file to audit; repeatable",
    )
    parser.add_argument(
        "--fail-on",
        choices=("none", "low", "medium", "high"),
        default="high",
        help="lowest severity that makes the command exit non-zero (default high)",
    )
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", help="write the report to this file")
    parser.add_argument(
        "--force", action="store_true", help="overwrite an existing output file"
    )
    return parser


def run(arguments: argparse.Namespace) -> dict[str, Any]:
    """Audit every requested file and summarize the findings."""

    if len(arguments.input) > MAX_FILES:
        raise CliError(f"at most {MAX_FILES} files can be audited in one run")
    results = []
    counts = {"total": 0, "low": 0, "medium": 0, "high": 0, "suppressed": 0}
    for item in arguments.input:
        source, path = _common.read_text_file(item, suffixes=(".py",))
        audited = audit_source(source, path.name)
        results.append(
            {
                "file": str(path),
                "findings": audited["findings"],
                "suppressed": audited["suppressed"],
            }
        )
        counts["suppressed"] += audited["suppressed"]
        for finding in audited["findings"]:
            counts["total"] += 1
            counts[finding["severity"]] += 1
    return {
        "files_scanned": len(results),
        "counts": counts,
        "results": results,
    }


def exit_code(document: dict[str, Any], fail_on: str) -> int:
    """Return 1 when a finding meets the configured severity threshold."""

    if fail_on == "none":
        return 0
    threshold = SEVERITY_ORDER[fail_on]
    for entry in document["results"]:
        for finding in entry["findings"]:
            if SEVERITY_ORDER[finding["severity"]] >= threshold:
                return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        document = run(arguments)
        if arguments.format == "markdown":
            _common.emit_text(
                render_markdown(document),
                output=arguments.output,
                force=arguments.force,
            )
        else:
            _common.emit_json(
                document, output=arguments.output, force=arguments.force
            )
    except CliError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return exit_code(document, arguments.fail_on)


if __name__ == "__main__":
    raise SystemExit(main())
