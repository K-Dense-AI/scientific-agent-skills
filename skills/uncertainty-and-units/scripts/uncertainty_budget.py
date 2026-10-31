#!/usr/bin/env python3
"""Turn a list of uncertainty components into a GUM uncertainty budget.

Each component arrives the way it is actually stated on a certificate, a data
sheet, or a repeatability worksheet. The divisor that converts it to a standard
uncertainty depends on which of those it is, and getting that divisor wrong is
the most common defect in a real budget. This CLI applies JCGM 100:2008 4.3,
combines the components, and reports the Welch-Satterthwaite effective degrees
of freedom and the resulting coverage factor.
"""

from __future__ import annotations

import argparse
import math
import sys
from typing import Any

import _common
from _common import CliError


TEMPLATE: dict[str, Any] = {
    "measurand": "example flow rate",
    "unit": "L/min",
    "value": 12.345,
    "coverage_probability": 0.95,
    "components": [
        {
            "label": "repeatability of ten readings",
            "type": "A",
            "distribution": "normal",
            "value": 0.052,
            "dof": 9,
            "note": "experimental standard deviation of the mean",
        },
        {
            "label": "calibration certificate",
            "type": "B",
            "distribution": "expanded",
            "value": 0.10,
            "coverage_factor": 2.0,
        },
        {
            "label": "display resolution",
            "type": "B",
            "distribution": "rectangular",
            "value": 0.005,
            "note": "half-width equals half of the last displayed digit",
        },
        {
            "label": "long-term drift since calibration",
            "type": "B",
            "distribution": "rectangular",
            "value": 0.04,
        },
        {
            "label": "temperature correction",
            "type": "B",
            "distribution": "triangular",
            "value": 0.03,
            "sensitivity": 0.8,
        },
    ],
}


def normalize_component(raw: Any, index: int, measurand: float | None) -> dict[str, Any]:
    """Validate one budget component and reduce it to a standard uncertainty."""

    if not isinstance(raw, dict):
        raise CliError(f"component {index + 1} must be a JSON object")
    label = raw.get("label") or f"component {index + 1}"
    if not isinstance(label, str) or len(label) > 200:
        raise CliError(f"component {index + 1}: label must be a string under 200 chars")

    kind = str(raw.get("type", "B")).strip().upper()
    if kind not in {"A", "B"}:
        raise CliError(f"{label}: evaluation type must be 'A' or 'B'")

    shape = raw.get("distribution")
    shape = "expanded" if str(shape).strip().lower() == "expanded" else shape
    if shape == "expanded":
        distribution = "expanded"
    else:
        distribution = _common.normalize_distribution(
            shape, label=f"{label}.distribution"
        )

    value = _common.as_finite(raw.get("value"), label=f"{label}.value")
    if value < 0:
        raise CliError(f"{label}: value must not be negative")

    relative = raw.get("relative", False)
    if not isinstance(relative, bool):
        raise CliError(f"{label}: relative must be a JSON boolean")
    if relative:
        if measurand is None:
            raise CliError(
                f"{label}: a relative component needs a top-level measurand 'value'"
            )
        value = value * abs(measurand)

    if distribution == "expanded":
        factor = _common.as_finite(
            raw.get("coverage_factor"), label=f"{label}.coverage_factor"
        )
        if factor <= 0:
            raise CliError(f"{label}: coverage_factor must be greater than zero")
        divisor = factor
    else:
        divisor = _common.DISTRIBUTION_DIVISORS[distribution]

    if "divisor" in raw:
        divisor = _common.as_finite(raw["divisor"], label=f"{label}.divisor")
        if divisor <= 0:
            raise CliError(f"{label}: divisor must be greater than zero")

    sensitivity = _common.as_finite(
        raw.get("sensitivity", 1.0), label=f"{label}.sensitivity"
    )
    dof = _common.as_degrees_of_freedom(raw.get("dof"), label=f"{label}.dof")
    standard = value / divisor
    if distribution == "exact" and value != 0:
        raise CliError(f"{label}: an exact component must have zero uncertainty")
    note = raw.get("note")
    if note is not None and (not isinstance(note, str) or len(note) > 500):
        raise CliError(f"{label}: note must be a string under 500 chars")

    return {
        "label": label,
        "type": kind,
        "distribution": distribution,
        "stated_value": value,
        "divisor": divisor,
        "standard_uncertainty": standard,
        "sensitivity": sensitivity,
        "contribution": sensitivity * standard,
        "dof": dof,
        "note": note,
    }


def build_budget(spec: dict[str, Any], coverage_override: float | None) -> dict[str, Any]:
    """Combine components into u_c, effective degrees of freedom, and U."""

    if spec.get("correlations") or spec.get("covariance") or spec.get("covariance_matrix"):
        raise CliError("this budget combines independent components only; use a covariance-aware model")
    raw_components = spec.get("components")
    if not isinstance(raw_components, list) or not raw_components:
        raise CliError("the spec must contain a non-empty 'components' list")
    if len(raw_components) > _common.MAX_COMPONENTS:
        raise CliError(f"at most {_common.MAX_COMPONENTS} components are supported")

    measurand_value = spec.get("value")
    if measurand_value is not None:
        measurand_value = _common.as_finite(measurand_value, label="value")

    components = [
        normalize_component(raw, index, measurand_value)
        for index, raw in enumerate(raw_components)
    ]

    variance = sum(item["contribution"] ** 2 for item in components)
    combined = math.sqrt(variance)
    for item in components:
        item["variance_fraction"] = (
            (item["contribution"] ** 2) / variance if variance > 0 else 0.0
        )

    coverage = coverage_override
    if coverage is None:
        coverage = _common.as_finite(
            spec.get("coverage_probability", 0.95), label="coverage_probability"
        )
    if not 0 < coverage < 1:
        raise CliError("coverage probability must be strictly between 0 and 1")

    effective_dof = _common.welch_satterthwaite(
        combined, [(abs(item["contribution"]), item["dof"]) for item in components]
    )
    factor = _common.coverage_factor(effective_dof, coverage)
    expanded = factor * combined

    result: dict[str, Any] = {
        "measurand": spec.get("measurand"),
        "unit": spec.get("unit"),
        "value": measurand_value,
        "components": components,
        "combined_standard_uncertainty": combined,
        "effective_degrees_of_freedom": (
            None if not math.isfinite(effective_dof) else effective_dof
        ),
        "coverage_probability": coverage,
        "coverage_factor": factor,
        "expanded_uncertainty": expanded,
    }
    if measurand_value is not None:
        result["coverage_interval"] = [
            measurand_value - expanded,
            measurand_value + expanded,
        ]
        if measurand_value != 0:
            result["relative_standard_uncertainty"] = combined / abs(measurand_value)
    result["warnings"] = collect_warnings(result)
    for item in components:
        item["dof"] = _common.json_dof(item["dof"])
    return result


def collect_warnings(budget: dict[str, Any]) -> list[str]:
    """Flag budget defects that change how the result should be reported."""

    warnings: list[str] = []
    warnings.append(
        "the normal/Student-t coverage approximation requires a suitable output "
        "distribution; this budget does not verify coverage or measurement-model validity"
    )
    components = budget["components"]
    for item in components:
        if item["type"] == "A" and not math.isfinite(item["dof"]):
            warnings.append(
                f"{item['label']}: a Type A component evaluated from n readings has "
                "n-1 degrees of freedom; leaving it infinite understates the "
                "coverage factor"
            )
        if (
            item["type"] == "B"
            and item["distribution"] == "normal"
            and item["divisor"] == 1.0
        ):
            warnings.append(
                f"{item['label']}: a Type B component declared normal is divided by "
                "1, so the stated value is taken as a standard uncertainty; "
                "certificates normally quote an expanded U, which needs "
                "distribution 'expanded' with its coverage_factor"
            )
    dof = budget["effective_degrees_of_freedom"]
    if dof is not None and dof < 6:
        warnings.append(
            f"effective degrees of freedom is {dof:.1f}; k = "
            f"{budget['coverage_factor']:.2f} rather than the customary 2, and the "
            "interval is sensitive to one small sample"
        )
    if components:
        dominant = max(components, key=lambda item: item["variance_fraction"])
        if dominant["variance_fraction"] > 0.9:
            warnings.append(
                f"{dominant['label']} contributes "
                f"{dominant['variance_fraction'] * 100:.1f}% of the variance; "
                "improving other components has limited effect on the result"
            )
        largest = max(abs(item["contribution"]) for item in components)
        negligible = [
            item["label"]
            for item in components
            if largest > 0 and abs(item["contribution"]) < largest / 3.0
        ]
        if negligible:
            warnings.append(
                "each of these components is below one third of the largest; "
                f"their aggregate effect may still matter: {', '.join(negligible)}"
            )
    return warnings


def render_markdown(budget: dict[str, Any]) -> str:
    """Render the budget as a Markdown table plus the combined result."""

    unit = f" {budget['unit']}" if budget.get("unit") else ""
    lines = [
        f"# Uncertainty budget: {budget.get('measurand') or 'measurand'}",
        "",
        "| Component | Type | Distribution | Stated | Divisor | u(x) | c | "
        "c*u(x) | % variance | dof |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in budget["components"]:
        dof = _common.format_dof(item["dof"])
        lines.append(
            f"| {item['label']} | {item['type']} | {item['distribution']} | "
            f"{item['stated_value']:.6g} | {item['divisor']:.4g} | "
            f"{item['standard_uncertainty']:.4g} | {item['sensitivity']:.4g} | "
            f"{item['contribution']:.4g} | {item['variance_fraction'] * 100:.1f} | "
            f"{dof} |"
        )
    effective = budget["effective_degrees_of_freedom"]
    lines += [
        "",
        "## Combined result",
        "",
        f"- Combined standard uncertainty u_c: "
        f"{budget['combined_standard_uncertainty']:.6g}{unit}",
        f"- Effective degrees of freedom: "
        f"{'infinite' if effective is None else f'{effective:.1f}'}",
        f"- Coverage factor k: {budget['coverage_factor']:.4g} at p = "
        f"{budget['coverage_probability']:.3g}",
        f"- Expanded uncertainty U: {budget['expanded_uncertainty']:.6g}{unit}",
    ]
    if budget.get("value") is not None:
        low, high = budget["coverage_interval"]
        lines.append(
            f"- Result: {budget['value']:.6g} +/- "
            f"{budget['expanded_uncertainty']:.6g}{unit} "
            f"[{low:.6g}, {high:.6g}]"
        )
    if budget.get("warnings"):
        lines += ["", "## Warnings", ""]
        lines += [f"- {message}" for message in budget["warnings"]]
    lines += [
        "",
        "Components are combined in quadrature, which assumes they are "
        "uncorrelated (JCGM 100:2008 equation 10). Use "
        "`propagate_uncertainty.py --correlation` when they are not.",
    ]
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Combine stated uncertainty components into a GUM budget with "
            "distribution-aware divisors and a Welch-Satterthwaite coverage factor."
        )
    )
    parser.add_argument("--spec", help="JSON file describing the budget")
    parser.add_argument(
        "--template",
        action="store_true",
        help="print a worked example spec and exit",
    )
    parser.add_argument(
        "--coverage",
        type=_common.probability,
        help="override the coverage probability in the spec",
    )
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", help="write the report to this file")
    parser.add_argument(
        "--force", action="store_true", help="overwrite an existing output file"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        if arguments.template:
            _common.emit_json(
                TEMPLATE, output=arguments.output, force=arguments.force
            )
            return 0
        spec = TEMPLATE
        if arguments.spec:
            loaded = _common.load_json(arguments.spec)
            if not isinstance(loaded, dict):
                raise CliError("the spec file must hold a JSON object")
            spec = loaded
        budget = build_budget(spec, arguments.coverage)
        if arguments.format == "markdown":
            _common.emit_text(
                render_markdown(budget), output=arguments.output, force=arguments.force
            )
        else:
            _common.emit_json(budget, output=arguments.output, force=arguments.force)
    except CliError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
