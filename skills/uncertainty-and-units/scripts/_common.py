#!/usr/bin/env python3
"""Shared, standard-library-first helpers for the uncertainty and unit CLIs."""

from __future__ import annotations

import ast
import json
import math
import os
import stat
import tempfile
from pathlib import Path
from typing import Any, Callable, Iterable


MAX_INPUT_BYTES = 4 * 1024 * 1024
MAX_REPORT_BYTES = 4 * 1024 * 1024
MAX_COMPONENTS = 256
MAX_VARIABLES = 64
MAX_TRIALS = 5_000_000
# A useful initial trial count, not a convergence guarantee. JCGM 101:2008
# 7.9 and 8.2 require numerical stabilization for a validation claim.
RECOMMENDED_TRIALS = 1_000_000
DEFAULT_TRIALS = RECOMMENDED_TRIALS
DEFAULT_SEED = 20_260_726
MAX_EXPRESSION_CHARS = 2_000
MAX_EXPRESSION_NODES = 400
MAX_EXPRESSION_DEPTH = 32
MAX_LITERAL_EXPONENT = 64

PINNED_INSTALL = (
    'uv pip install "pint==0.26.1" "uncertainties==3.2.3" '
    '"numpy==2.5.3" "scipy==1.18.1"'
)

# Standard uncertainty of a Type B component equals its half-width divided by
# these factors (JCGM 100:2008 4.3.7-4.3.9).
DISTRIBUTION_DIVISORS: dict[str, float] = {
    "normal": 1.0,
    "rectangular": math.sqrt(3.0),
    "triangular": math.sqrt(6.0),
    "arcsine": math.sqrt(2.0),
    "exact": 1.0,
}

ALLOWED_FUNCTIONS = (
    "abs",
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
)

ALLOWED_CONSTANTS = {"pi": math.pi, "e": math.e, "tau": math.tau}

_ALLOWED_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Call,
    ast.Name,
    ast.Constant,
    ast.Load,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Pow,
    ast.USub,
    ast.UAdd,
)


class CliError(ValueError):
    """An expected command-line validation error."""


def bounded_int(minimum: int, maximum: int) -> Callable[[str], int]:
    """Return an argparse converter for a bounded integer."""

    def convert(value: str) -> int:
        try:
            parsed = int(value)
        except ValueError as exc:
            raise CliError(f"expected an integer, got {value!r}") from exc
        if not minimum <= parsed <= maximum:
            raise CliError(
                f"expected an integer from {minimum} through {maximum}, got {parsed}"
            )
        return parsed

    return convert


def finite_float(value: str) -> float:
    """Parse a finite floating-point value."""

    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise CliError(f"expected a number, got {value!r}") from exc
    if not math.isfinite(parsed):
        raise CliError("value must be finite")
    return parsed


def non_negative_float(value: str) -> float:
    """Parse a finite, non-negative floating-point value."""

    parsed = finite_float(value)
    if parsed < 0:
        raise CliError("value must not be negative")
    return parsed


def positive_float(value: str) -> float:
    """Parse a finite, strictly positive floating-point value."""

    parsed = finite_float(value)
    if parsed <= 0:
        raise CliError("value must be greater than zero")
    return parsed


def probability(value: str) -> float:
    """Parse a coverage probability strictly between zero and one."""

    parsed = finite_float(value)
    if not 0 < parsed < 1:
        raise CliError("coverage probability must be strictly between 0 and 1")
    return parsed


def as_finite(value: Any, *, label: str) -> float:
    """Coerce a JSON scalar to a finite float."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CliError(f"{label} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise CliError(f"{label} must be finite")
    return number


def as_degrees_of_freedom(value: Any, *, label: str) -> float:
    """Coerce a degrees-of-freedom entry, treating null as infinite."""

    if value is None:
        return math.inf
    if isinstance(value, str) and value.strip().lower() in {"inf", "infinite"}:
        return math.inf
    number = as_finite(value, label=label)
    if number <= 0:
        raise CliError(f"{label} must be greater than zero")
    return number


def normalize_distribution(value: Any, *, label: str) -> str:
    """Validate a supported probability-density shape."""

    if value is None:
        return "normal"
    if not isinstance(value, str):
        raise CliError(f"{label} must be a string")
    name = value.strip().lower()
    aliases = {"uniform": "rectangular", "u-shaped": "arcsine", "gaussian": "normal"}
    name = aliases.get(name, name)
    if name not in DISTRIBUTION_DIVISORS:
        allowed = ", ".join(sorted(DISTRIBUTION_DIVISORS))
        raise CliError(f"{label} must be one of: {allowed}")
    return name


def checked_input_file(
    value: str | os.PathLike[str],
    *,
    suffixes: Iterable[str],
    max_bytes: int = MAX_INPUT_BYTES,
) -> Path:
    """Return a bounded regular local file, rejecting URLs and symlinks."""

    raw = os.fspath(value)
    if "://" in raw:
        raise CliError("network URLs are not accepted; provide a local file")
    path = Path(raw).expanduser()
    if path.is_symlink():
        raise CliError(f"input must not be a symlink: {path}")
    try:
        info = path.stat()
    except OSError as exc:
        raise CliError(f"cannot access input file {path}: {exc}") from exc
    if not stat.S_ISREG(info.st_mode):
        raise CliError(f"input is not a regular file: {path}")
    if info.st_size > max_bytes:
        raise CliError(f"input is {info.st_size} bytes; limit is {max_bytes} bytes")
    allowed = {suffix.lower() for suffix in suffixes}
    if path.suffix.lower() not in allowed:
        raise CliError(f"input suffix must be one of: {', '.join(sorted(allowed))}")
    return path.resolve()


def checked_output_file(
    value: str | os.PathLike[str],
    *,
    suffixes: Iterable[str],
    force: bool = False,
) -> Path:
    """Validate an explicit local output without following symlinks."""

    raw = os.fspath(value)
    if "://" in raw:
        raise CliError("network URLs are not accepted as output paths")
    path = Path(raw).expanduser()
    if path.name in {"", ".", ".."}:
        raise CliError("output must name a file")
    if path.is_symlink():
        raise CliError(f"output must not be a symlink: {path}")
    allowed = {suffix.lower() for suffix in suffixes}
    if path.suffix.lower() not in allowed:
        raise CliError(f"output suffix must be one of: {', '.join(sorted(allowed))}")
    parent = path.parent
    if not parent.exists() or not parent.is_dir() or parent.is_symlink():
        raise CliError(f"output parent must be an existing regular directory: {parent}")
    if path.exists():
        if not path.is_file():
            raise CliError(f"output exists and is not a regular file: {path}")
        if not force:
            raise CliError(f"refusing to overwrite existing output: {path}")
    return parent.resolve() / path.name


def atomic_write_bytes(path: Path, payload: bytes, *, force: bool = False) -> None:
    """Write bytes through a private same-directory temporary file."""

    destination = checked_output_file(path, suffixes={path.suffix.lower()}, force=force)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        if destination.exists() and not force:
            raise CliError(f"refusing to overwrite existing output: {destination}")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _json_bytes(document: Any) -> bytes:
    """Serialize deterministic strict JSON."""

    try:
        payload = (
            json.dumps(
                document,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CliError(f"report is not strict JSON: {exc}") from exc
    if len(payload) > MAX_REPORT_BYTES:
        raise CliError(
            f"report is {len(payload)} bytes; limit is {MAX_REPORT_BYTES} bytes"
        )
    return payload


def emit_json(
    document: Any,
    *,
    output: str | os.PathLike[str] | None = None,
    force: bool = False,
) -> None:
    """Print deterministic JSON or write it atomically."""

    payload = _json_bytes(document)
    if output is None:
        print(payload.decode("utf-8"), end="")
        return
    destination = checked_output_file(output, suffixes={".json"}, force=force)
    atomic_write_bytes(destination, payload, force=force)


def emit_text(
    text: str,
    *,
    output: str | os.PathLike[str] | None = None,
    force: bool = False,
) -> None:
    """Print text or write it atomically to Markdown."""

    payload = text.encode("utf-8")
    if len(payload) > MAX_REPORT_BYTES:
        raise CliError(
            f"report is {len(payload)} bytes; limit is {MAX_REPORT_BYTES} bytes"
        )
    if output is None:
        print(text, end="" if text.endswith("\n") else "\n")
        return
    destination = checked_output_file(output, suffixes={".md"}, force=force)
    atomic_write_bytes(destination, payload, force=force)


def load_json(value: str | os.PathLike[str]) -> Any:
    """Load bounded strict JSON from a local file."""

    path = checked_input_file(value, suffixes={".json"})

    def reject_constant(constant: str) -> None:
        raise CliError(f"non-standard JSON constant is not allowed: {constant}")

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise CliError(f"duplicate JSON key: {key!r}")
            result[key] = value
        return result

    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle, parse_constant=reject_constant,
                             object_pairs_hook=unique_object)
    except (OSError, json.JSONDecodeError) as exc:
        raise CliError(f"cannot read valid JSON from {path.name}: {exc}") from exc


def read_text_file(
    value: str | os.PathLike[str], *, suffixes: Iterable[str] = (".py",)
) -> tuple[str, Path]:
    """Read a bounded local UTF-8 text file."""

    path = checked_input_file(value, suffixes=suffixes)
    try:
        return path.read_text(encoding="utf-8"), path
    except (OSError, UnicodeDecodeError) as exc:
        raise CliError(f"cannot read {path.name} as UTF-8 text: {exc}") from exc


# --- bounded expression handling -------------------------------------------
#
# Measurement models arrive as text. Nothing here compiles or executes that
# text: the string is parsed to an AST, every node is checked against a
# whitelist, and the tree is reduced by an explicit walk over the six operators
# and the named functions below.


def parse_expression(text: str) -> ast.Expression:
    """Parse a measurement model into a validated, bounded expression tree."""

    if not isinstance(text, str) or not text.strip():
        raise CliError("expression must be a non-empty string")
    if len(text) > MAX_EXPRESSION_CHARS:
        raise CliError(
            f"expression is {len(text)} characters; limit is {MAX_EXPRESSION_CHARS}"
        )
    try:
        tree = ast.parse(text, mode="eval")
    except (SyntaxError, ValueError) as exc:
        raise CliError(f"cannot parse expression: {exc}") from exc

    nodes = list(ast.walk(tree))
    if len(nodes) > MAX_EXPRESSION_NODES:
        raise CliError(
            f"expression has {len(nodes)} nodes; limit is {MAX_EXPRESSION_NODES}"
        )
    for node in nodes:
        if not isinstance(node, _ALLOWED_NODES):
            raise CliError(
                f"expression may not contain {type(node).__name__}; allowed syntax is "
                "names, numbers, + - * / **, and whitelisted functions"
            )
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
                raise CliError("expression constants must be numbers")
            if not math.isfinite(float(node.value)):
                raise CliError("expression constants must be finite")
        if isinstance(node, ast.Name):
            if node.id.startswith("_"):
                raise CliError("expression names must not start with an underscore")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise CliError("only direct calls to whitelisted functions are allowed")
            if node.func.id not in ALLOWED_FUNCTIONS:
                allowed = ", ".join(ALLOWED_FUNCTIONS)
                raise CliError(
                    f"function {node.func.id!r} is not allowed; allowed: {allowed}"
                )
            if node.keywords:
                raise CliError("function calls may not use keyword arguments")
            arities = {"atan2": (2,), "hypot": (2,), "log": (1, 2)}
            if len(node.args) not in arities.get(node.func.id, (1,)):
                raise CliError(f"wrong number of arguments for {node.func.id}")
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
            exponent = node.right
            if isinstance(exponent, ast.Constant) and isinstance(
                exponent.value, (int, float)
            ):
                if abs(float(exponent.value)) > MAX_LITERAL_EXPONENT:
                    raise CliError(
                        f"literal exponents are limited to +/-{MAX_LITERAL_EXPONENT}"
                    )

    _check_depth(tree.body, 1)
    return tree


def _check_depth(node: ast.AST, depth: int) -> None:
    """Reject deeply nested expressions."""

    if depth > MAX_EXPRESSION_DEPTH:
        raise CliError(f"expression nesting exceeds {MAX_EXPRESSION_DEPTH} levels")
    for child in ast.iter_child_nodes(node):
        _check_depth(child, depth + 1)


def expression_variables(tree: ast.Expression) -> list[str]:
    """Return the free variable names of a parsed expression, in sorted order."""

    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    names = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
        and node.id not in called
        and node.id not in ALLOWED_CONSTANTS
    }
    if len(names) > MAX_VARIABLES:
        raise CliError(f"expression uses more than {MAX_VARIABLES} variables")
    return sorted(names)


def reduce_expression(
    tree: ast.Expression,
    variables: dict[str, Any],
    functions: dict[str, Callable[..., Any]],
) -> Any:
    """Reduce a validated expression tree against concrete values."""

    def walk(node: ast.AST) -> Any:
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            if node.id in variables:
                return variables[node.id]
            if node.id in ALLOWED_CONSTANTS:
                return ALLOWED_CONSTANTS[node.id]
            raise CliError(f"no value supplied for variable {node.id!r}")
        if isinstance(node, ast.UnaryOp):
            operand = walk(node.operand)
            return -operand if isinstance(node.op, ast.USub) else +operand
        if isinstance(node, ast.BinOp):
            left = walk(node.left)
            right = walk(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            return left**right
        if isinstance(node, ast.Call):
            name = node.func.id  # type: ignore[union-attr]
            handler = functions.get(name)
            if handler is None:
                raise CliError(f"function {name!r} is unavailable in this mode")
            return handler(*[walk(argument) for argument in node.args])
        raise CliError(f"unsupported expression node {type(node).__name__}")

    try:
        return walk(tree)
    except CliError:
        raise
    except ZeroDivisionError as exc:
        raise CliError("expression divides by zero at the supplied values") from exc
    except (ArithmeticError, ValueError, TypeError) as exc:
        raise CliError(f"cannot compute the expression: {exc}") from exc


def scalar_functions() -> dict[str, Callable[..., Any]]:
    """Return uncertainty-aware scalar functions with analytic derivatives."""

    try:
        from uncertainties import umath, wrap
    except ImportError as exc:
        raise CliError(
            f"the uncertainties package is unavailable; install with `{PINNED_INSTALL}`"
        ) from exc
    # abs(UFloat) and umath.fabs are deprecated in uncertainties 3.2.3.
    # At zero the derivative is undefined; do not invent a zero uncertainty.
    absolute = wrap(math.fabs, [lambda x: 1.0 if x > 0 else (-1.0 if x < 0 else math.nan)])
    mapping: dict[str, Callable[..., Any]] = {"abs": absolute, "fabs": absolute}
    for name in ALLOWED_FUNCTIONS:
        if name in {"abs", "fabs"}:
            continue
        handler = getattr(umath, name, None)
        if handler is not None:
            mapping[name] = handler
    return mapping


def array_functions() -> dict[str, Callable[..., Any]]:
    """Return vectorized functions for Monte Carlo sampling."""

    try:
        import numpy as np
    except ImportError as exc:
        raise CliError(
            f"NumPy is unavailable; install with `{PINNED_INSTALL}`"
        ) from exc
    mapping: dict[str, Callable[..., Any]] = {
        "abs": np.abs,
        "acos": np.arccos,
        "acosh": np.arccosh,
        "asin": np.arcsin,
        "asinh": np.arcsinh,
        "atan": np.arctan,
        "atan2": np.arctan2,
        "atanh": np.arctanh,
        "cos": np.cos,
        "cosh": np.cosh,
        "degrees": np.degrees,
        "exp": np.exp,
        "expm1": np.expm1,
        "fabs": np.fabs,
        "hypot": np.hypot,
        # np.log's second positional argument is an output buffer, NOT a base.
        "log": lambda value, base=None: (
            np.log(value) if base is None else np.log(value) / np.log(base)  # audit-units: ignore UNC003 -- MC arrays
        ),
        "log10": np.log10,
        "log1p": np.log1p,
        "radians": np.radians,
        "sin": np.sin,
        "sinh": np.sinh,
        "sqrt": np.sqrt,
        "tan": np.tan,
        "tanh": np.tanh,
    }

    def erf(value: Any) -> Any:
        try:
            from scipy.special import erf as scipy_erf
        except ImportError as exc:
            raise CliError(
                f"erf needs SciPy; install with `{PINNED_INSTALL}`"
            ) from exc
        return scipy_erf(value)

    mapping["erf"] = erf
    return mapping


def json_dof(value: float | None) -> float | None:
    """Render infinite degrees of freedom as JSON null."""

    if value is None or not math.isfinite(value):
        return None
    return float(value)


def format_dof(value: float | None) -> str:
    """Render degrees of freedom for a report table."""

    if value is None or not math.isfinite(value):
        return "inf"
    return f"{value:g}"


def welch_satterthwaite(
    combined_uncertainty: float, terms: Iterable[tuple[float, float]]
) -> float:
    """Return effective degrees of freedom from |c_i u_i| and nu_i pairs.

    JCGM 100:2008 equation G.2b. Components with infinite degrees of freedom
    contribute nothing to the denominator.
    """

    if combined_uncertainty <= 0:
        return math.inf
    denominator = 0.0
    for contribution, dof in terms:
        if not math.isfinite(dof) or dof <= 0:
            continue
        denominator += (contribution**4) / dof
    if denominator <= 0:
        return math.inf
    return (combined_uncertainty**4) / denominator


def coverage_factor(dof: float, coverage_probability: float) -> float:
    """Return the Student-t coverage factor for the given effective dof."""

    if not 0 < coverage_probability < 1:
        raise CliError("coverage probability must be strictly between 0 and 1")
    tail = 0.5 * (1.0 + coverage_probability)
    if not math.isfinite(dof):
        from statistics import NormalDist

        return float(NormalDist().inv_cdf(tail))
    try:
        from scipy.stats import t as student_t
    except ImportError as exc:
        raise CliError(
            "a Student-t coverage factor needs SciPy; install with "
            f"`{PINNED_INSTALL}`, or supply infinite degrees of freedom"
        ) from exc
    return float(student_t.ppf(tail, dof))


def numerical_tolerance(combined_uncertainty: float, significant_digits: int) -> float:
    """Return the JCGM 101:2008 clause 8 numerical tolerance for u_c.

    Writing u_c to `significant_digits` digits as c x 10**exponent, the
    tolerance is half of the unit in that last retained digit.
    """

    if significant_digits not in (1, 2):
        raise CliError("numerical tolerance is defined for 1 or 2 significant digits")
    if combined_uncertainty <= 0 or not math.isfinite(combined_uncertainty):
        raise CliError("combined standard uncertainty must be finite and positive")
    rounded = float(f"{combined_uncertainty:.{significant_digits}g}")
    decade = math.log10(rounded)  # audit-units: ignore UNC003 -- plain float
    exponent = math.floor(decade) - (significant_digits - 1)
    return 0.5 * (10.0**exponent)


def shortest_coverage_interval(
    sorted_sample: Any, coverage_probability: float
) -> tuple[float, float]:
    """Return the shortest coverage interval of a sorted Monte Carlo sample."""

    try:
        import numpy as np
    except ImportError as exc:
        raise CliError(
            f"NumPy is unavailable; install with `{PINNED_INSTALL}`"
        ) from exc
    total = int(sorted_sample.size)
    if total < 2:
        raise CliError("a coverage interval needs at least two Monte Carlo trials")
    # JCGM 101:2008 7.7.2 rounds p*M to the nearest integer.
    inside = int(math.floor(coverage_probability * total + 0.5))
    inside = min(max(inside, 1), total - 1)
    lower = sorted_sample[: total - inside]
    upper = sorted_sample[inside:]
    widths = upper - lower
    index = int(np.argmin(widths))
    return float(lower[index]), float(upper[index])
