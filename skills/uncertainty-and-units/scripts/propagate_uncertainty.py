#!/usr/bin/env python3
"""Propagate uncertainty through a measurement model two ways and compare them.

The GUM uncertainty framework (JCGM 100:2008) linearizes the model about the
best estimates. A Monte Carlo run (JCGM 101:2008) propagates the distributions
themselves. This fixed-trial CLI reports an endpoint comparison inspired by
JCGM 101 clause 8. It does not implement the adaptive stabilization procedure
required for a full validation claim, or validate the measurement model.
"""

from __future__ import annotations

import argparse
import math
import sys
from typing import Any

import _common
from _common import CliError


def parse_variable(text: str) -> dict[str, Any]:
    """Parse `name=value,u[,distribution[,dof]]` into a variable record."""

    if "=" not in text:
        raise CliError(
            f"variable {text!r} must look like name=value,standard_uncertainty"
        )
    name, _, payload = text.partition("=")
    name = name.strip()
    fields = [item.strip() for item in payload.split(",")]
    if len(fields) < 2 or len(fields) > 4:
        raise CliError(
            f"variable {name!r} takes value,standard_uncertainty[,distribution[,dof]]"
        )
    record: dict[str, Any] = {
        "name": name,
        "value": _common.finite_float(fields[0]),
        "standard_uncertainty": _common.non_negative_float(fields[1]),
    }
    if len(fields) >= 3 and fields[2]:
        record["distribution"] = fields[2]
    if len(fields) == 4 and fields[3]:
        if fields[3].lower() in {"inf", "infinite"}:
            record["dof"] = None
        else:
            record["dof"] = _common.finite_float(fields[3])
    return record


def parse_correlation(text: str) -> tuple[str, str, float]:
    """Parse `a,b=r` into a correlation coefficient between two inputs."""

    pair, _, value = text.partition("=")
    names = [item.strip() for item in pair.split(",")]
    if len(names) != 2 or not all(names) or not value.strip():
        raise CliError(f"correlation {text!r} must look like name_a,name_b=0.4")
    coefficient = _common.finite_float(value)
    if not -1.0 <= coefficient <= 1.0:
        raise CliError("correlation coefficients must lie in [-1, 1]")
    if names[0] == names[1]:
        raise CliError("a variable cannot be correlated with itself")
    return names[0], names[1], coefficient


def normalize_variables(records: list[Any]) -> list[dict[str, Any]]:
    """Validate variable records from either the CLI or a JSON spec."""

    if not records:
        raise CliError("at least one input variable is required")
    if len(records) > _common.MAX_VARIABLES:
        raise CliError(f"at most {_common.MAX_VARIABLES} variables are supported")
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            raise CliError("each variable must be a JSON object")
        name = record.get("name")
        if not isinstance(name, str) or not name.isidentifier():
            raise CliError(f"variable name {name!r} must be a Python identifier")
        if name.startswith("_"):
            raise CliError("variable names must not start with an underscore")
        if name in _common.ALLOWED_CONSTANTS or name in _common.ALLOWED_FUNCTIONS:
            raise CliError(f"variable name {name!r} shadows a built-in symbol")
        if name in seen:
            raise CliError(f"variable {name!r} is defined more than once")
        seen.add(name)
        uncertainty = record.get("standard_uncertainty", record.get("u"))
        entry = {
            "name": name,
            "value": _common.as_finite(record.get("value"), label=f"{name}.value"),
            "standard_uncertainty": _common.as_finite(
                uncertainty, label=f"{name}.standard_uncertainty"
            ),
            "distribution": _common.normalize_distribution(
                record.get("distribution"), label=f"{name}.distribution"
            ),
            "dof": _common.as_degrees_of_freedom(
                record.get("dof"), label=f"{name}.dof"
            ),
            "unit": record.get("unit") if isinstance(record.get("unit"), str) else None,
        }
        if entry["standard_uncertainty"] < 0:
            raise CliError(f"{name}: standard uncertainty must not be negative")
        if entry["distribution"] == "exact" and entry["standard_uncertainty"] != 0:
            raise CliError(f"{name}: an exact input must have zero uncertainty")
        normalized.append(entry)
    return normalized


def gum_framework(
    tree: Any,
    variables: list[dict[str, Any]],
    correlations: dict[tuple[str, str], float],
    coverage_probability: float,
) -> dict[str, Any]:
    """Evaluate the model and propagate uncertainty by first-order expansion."""

    try:
        from uncertainties import ufloat
    except ImportError as exc:
        raise CliError(
            "the uncertainties package is unavailable; install with "
            f"`{_common.PINNED_INSTALL}`"
        ) from exc

    if correlations:
        correlation_factor(variables, correlations)
        if any(math.isfinite(entry["dof"]) for entry in variables):
            raise CliError(
                "correlated inputs with finite degrees of freedom need a justified "
                "joint uncertainty model; this CLI cannot apply independent-input "
                "Welch-Satterthwaite to them"
            )
    handles = {
        entry["name"]: ufloat(entry["value"], entry["standard_uncertainty"])
        for entry in variables
    }
    result = _common.reduce_expression(tree, handles, _common.scalar_functions())
    value = float(getattr(result, "nominal_value", result))
    derivatives = getattr(result, "derivatives", {})

    inputs: list[dict[str, Any]] = []
    for entry in variables:
        sensitivity = float(derivatives.get(handles[entry["name"]], 0.0))
        contribution = sensitivity * entry["standard_uncertainty"]
        inputs.append({**entry, "sensitivity": sensitivity, "contribution": contribution})

    independent = sum(item["contribution"] ** 2 for item in inputs)
    by_name = {item["name"]: item for item in inputs}
    covariance_term = 0.0
    for (first, second), coefficient in correlations.items():
        left = by_name[first]
        right = by_name[second]
        covariance_term += (
            2.0
            * left["sensitivity"]
            * right["sensitivity"]
            * coefficient
            * left["standard_uncertainty"]
            * right["standard_uncertainty"]
        )
    variance = independent + covariance_term
    if not all(math.isfinite(number) for number in (value, independent, covariance_term)):
        raise CliError("model value or linearized uncertainty is not finite")
    if variance < -1e-12 * independent:
        raise CliError(
            "the supplied correlations give a negative combined variance; "
            "check the correlation matrix for consistency"
        )
    combined = math.sqrt(max(variance, 0.0))  # audit-units: ignore UNC003 -- plain float

    # Budget percentages are taken against the sum of squared contributions,
    # not against u_c**2. With correlated inputs the covariance term can make
    # u_c**2 smaller than that sum, and percentages of it would exceed 100.
    for item in inputs:
        item["variance_fraction"] = (
            (item["contribution"] ** 2) / independent if independent > 0 else 0.0
        )

    effective_dof = _common.welch_satterthwaite(
        combined, [(abs(item["contribution"]), item["dof"]) for item in inputs]
    )
    factor = _common.coverage_factor(effective_dof, coverage_probability)
    expanded = factor * combined
    for item in inputs:
        item["dof"] = _common.json_dof(item["dof"])
    return {
        "value": value,
        "combined_standard_uncertainty": combined,
        "independent_variance": independent,
        "covariance_term": covariance_term,
        "effective_degrees_of_freedom": (
            None if not math.isfinite(effective_dof) else effective_dof
        ),
        "coverage_probability": coverage_probability,
        "coverage_factor": factor,
        "expanded_uncertainty": expanded,
        "coverage_interval": [value - expanded, value + expanded],
        "inputs": inputs,
    }


def _draw(rng: Any, entry: dict[str, Any], trials: int) -> Any:
    """Sample one input from its assigned probability density."""

    import numpy as np

    value = entry["value"]
    uncertainty = entry["standard_uncertainty"]
    if uncertainty == 0:
        return np.full(trials, value)
    shape = entry["distribution"]
    if shape == "normal":
        return rng.normal(value, uncertainty, trials)
    half_width = uncertainty * _common.DISTRIBUTION_DIVISORS[shape]
    if shape == "rectangular":
        return rng.uniform(value - half_width, value + half_width, trials)
    if shape == "triangular":
        return rng.triangular(value - half_width, value, value + half_width, trials)
    if shape == "arcsine":
        # audit-units: ignore UNC003 -- ordinary array of draws, not a ufloat
        return value + half_width * np.cos(rng.uniform(0.0, math.pi, trials))
    raise CliError(f"cannot sample distribution {shape!r}")


def correlation_factor(
    variables: list[dict[str, Any]],
    correlations: dict[tuple[str, str], float],
) -> tuple[list[str], Any]:
    """Validate a correlation matrix and factor it, including singular PSD cases."""

    import numpy as np

    involved = sorted({name for pair in correlations for name in pair})
    by_name = {entry["name"]: entry for entry in variables}
    for name in involved:
        entry = by_name[name]
        if entry["standard_uncertainty"] <= 0:
            raise CliError(f"{name}: a correlated input needs a positive uncertainty")

    index = {name: position for position, name in enumerate(involved)}
    size = len(involved)
    matrix = np.eye(size)
    for (first, second), coefficient in correlations.items():
        if first == second or not math.isfinite(coefficient) or not -1 <= coefficient <= 1:
            raise CliError("correlations need distinct inputs and finite r in [-1, 1]")
        matrix[index[first], index[second]] = coefficient
        matrix[index[second], index[first]] = coefficient
    eigenvalues, eigenvectors = np.linalg.eigh(matrix)
    tolerance = 1e-12 * max(size, 1)
    if eigenvalues.min() < -tolerance:
        raise CliError(
            "the correlation matrix is not positive semidefinite; the supplied "
            "coefficients cannot come from a single joint distribution"
        )
    # audit-units: ignore UNC003 -- numeric eigenvalues, not uncertain variables
    factor = eigenvectors * np.sqrt(np.maximum(eigenvalues, 0.0))
    return involved, factor


def _draw_correlated(
    rng: Any,
    variables: list[dict[str, Any]],
    correlations: dict[tuple[str, str], float],
    trials: int,
) -> dict[str, Any]:
    """Sample a jointly normal distribution, allowing perfect correlations."""

    involved, factor = correlation_factor(variables, correlations)
    by_name = {entry["name"]: entry for entry in variables}
    for name in involved:
        if by_name[name]["distribution"] != "normal":
            raise CliError(
                f"{name}: correlated Monte Carlo sampling requires normal marginals "
                "and a jointly normal model; other joint distributions need a "
                "separate sampler, not a change to the declared input distribution"
            )
    index = {name: position for position, name in enumerate(involved)}
    size = len(involved)

    standard = rng.standard_normal((size, trials))
    correlated = factor @ standard
    samples: dict[str, Any] = {}
    for name in involved:
        entry = by_name[name]
        samples[name] = (
            entry["value"] + entry["standard_uncertainty"] * correlated[index[name]]
        )
    for entry in variables:
        if entry["name"] not in samples:
            samples[entry["name"]] = _draw(rng, entry, trials)
    return samples


def monte_carlo(
    tree: Any,
    variables: list[dict[str, Any]],
    correlations: dict[tuple[str, str], float],
    coverage_probability: float,
    trials: int,
    seed: int,
) -> dict[str, Any]:
    """Propagate the input distributions by Monte Carlo sampling."""

    try:
        import numpy as np
    except ImportError as exc:
        raise CliError(
            f"NumPy is unavailable; install with `{_common.PINNED_INSTALL}`"
        ) from exc

    if trials * max(len(variables), 1) > 40_000_000:
        raise CliError(
            f"{trials} trials across {len(variables)} inputs exceeds the sampling "
            "budget; lower --trials"
        )

    rng = np.random.default_rng(seed)
    if correlations:
        samples = _draw_correlated(rng, variables, correlations, trials)
    else:
        samples = {
            entry["name"]: _draw(rng, entry, trials) for entry in variables
        }

    drawn = _common.reduce_expression(tree, samples, _common.array_functions())
    drawn = np.asarray(drawn, dtype=float)
    if drawn.shape != (trials,):
        drawn = np.broadcast_to(drawn, (trials,)).astype(float)
    finite = int(np.count_nonzero(np.isfinite(drawn)))
    if finite < trials:
        raise CliError(
            f"{trials - finite} of {trials} Monte Carlo trials produced a "
            "non-finite result; the model is undefined over part of the input "
            "distribution"
        )

    tail = 0.5 * (1.0 - coverage_probability)
    ordered = np.sort(drawn)
    symmetric = (
        float(np.quantile(ordered, tail)),
        float(np.quantile(ordered, 1.0 - tail)),
    )
    shortest = _common.shortest_coverage_interval(ordered, coverage_probability)
    return {
        "trials": trials,
        "seed": seed,
        "mean": float(np.mean(drawn)),
        "standard_uncertainty": float(np.std(drawn, ddof=1)),
        "median": float(np.median(drawn)),
        "coverage_probability": coverage_probability,
        "probabilistically_symmetric_interval": list(symmetric),
        "shortest_coverage_interval": list(shortest),
        "numerical_stability_verified": False,
    }


def validate_linearization(
    framework: dict[str, Any], sampling: dict[str, Any], significant_digits: int
) -> dict[str, Any]:
    """Compare fixed-trial endpoints; do not imply adaptive JCGM validation."""

    combined = sampling["standard_uncertainty"]
    if combined <= 0:
        return {
            "significant_digits": significant_digits,
            "numerical_tolerance": None,
            "gum_framework_validated": None,
            "endpoint_agreement": None,
            "note": "Monte Carlo standard uncertainty is zero; no comparison is defined",
        }
    tolerance = _common.numerical_tolerance(combined, significant_digits)
    guf_low, guf_high = framework["coverage_interval"]
    mc_low, mc_high = sampling["probabilistically_symmetric_interval"]
    low_gap = abs(guf_low - mc_low)
    high_gap = abs(guf_high - mc_high)
    validated = low_gap <= tolerance and high_gap <= tolerance
    return {
        "significant_digits": significant_digits,
        "numerical_tolerance": tolerance,
        "endpoint_difference_low": low_gap,
        "endpoint_difference_high": high_gap,
        "endpoint_agreement": validated,
        "gum_framework_validated": None,
        "numerical_stability_verified": False,
        "note": (
            ("endpoints agree" if validated else "endpoints disagree")
            + " at this trial count; this is a fixed-trial diagnostic. Check Monte "
            "Carlo stabilization (JCGM 101 7.9 and 8.2, tolerance delta/5), input "
            "distributions, and model validity before selecting a reported interval"
        ),
    }


def collect_warnings(
    framework: dict[str, Any],
    sampling: dict[str, Any] | None,
    correlations: dict[tuple[str, str], float],
) -> list[str]:
    """Flag conditions that make the headline numbers misleading."""

    warnings: list[str] = []
    dof = framework["effective_degrees_of_freedom"]
    if dof is not None and dof < 6:
        warnings.append(
            f"effective degrees of freedom is {dof:.1f}; the coverage factor is "
            "dominated by a small Type A sample and is unstable"
        )
    if correlations:
        warnings.append(
            "correlated sampling assumes a jointly normal distribution; covariance "
            "alone does not specify a general joint distribution"
        )
    dominant = max(framework["inputs"], key=lambda item: item["variance_fraction"])
    if dominant["variance_fraction"] > 0.9 and len(framework["inputs"]) > 1:
        warnings.append(
            f"{dominant['name']} contributes "
            f"{dominant['variance_fraction'] * 100:.1f}% of the summed squared "
            "contributions; the other inputs barely affect the result"
        )
    if framework["covariance_term"] != 0:
        share = framework["covariance_term"] / framework["independent_variance"]
        warnings.append(
            f"the covariance term changes the combined variance by {share * 100:+.0f}% "
            "of the summed squared contributions, so the budget percentages below "
            "do not add up to u_c"
        )
    for item in framework["inputs"]:
        if item["value"] != 0:
            relative = item["standard_uncertainty"] / abs(item["value"])
            if relative > 0.3:
                warnings.append(
                    f"{item['name']} has a relative standard uncertainty of "
                    f"{relative * 100:.0f}%; check nonlinearity and physical support "
                    "of the input distribution (a linear model can still be exact)"
                )
    if sampling is not None:
        if any(item["dof"] is not None for item in framework["inputs"]):
            warnings.append(
                "finite input degrees of freedom affect the GUM coverage factor "
                "but are not sampled: this CLI uses the declared fixed PDFs, not "
                "Student-t input distributions or uncertainty in estimated variances"
            )
        if sampling["trials"] < _common.RECOMMENDED_TRIALS:
            warnings.append(
                f"{sampling['trials']} Monte Carlo trials is below the "
                f"{_common.RECOMMENDED_TRIALS} initial trial-count guideline; "
                "endpoint agreement can be affected by sampling noise"
            )
        combined = framework["combined_standard_uncertainty"]
        if combined > 0:
            shift = abs(sampling["mean"] - framework["value"]) / combined
            if shift > 0.1:
                warnings.append(
                    f"the Monte Carlo mean differs from the model value by "
                    f"{shift:.2f} u_c, which indicates a nonlinear model"
                )
    return warnings


def render_markdown(document: dict[str, Any]) -> str:
    """Render a human-readable propagation report."""

    framework = document["gum_framework"]
    unit = f" {document['unit']}" if document.get("unit") else ""
    lines = [
        f"# Uncertainty propagation: {document.get('measurand') or 'measurand'}",
        "",
        f"Model: `{document['expression']}`",
        "",
        "## GUM uncertainty framework (JCGM 100:2008)",
        "",
        f"- Value: {framework['value']:.6g}{unit}",
        f"- Combined standard uncertainty u_c: "
        f"{framework['combined_standard_uncertainty']:.6g}{unit}",
        f"- Effective degrees of freedom: "
        f"{_common.format_dof(framework['effective_degrees_of_freedom'])}",
        f"- Coverage factor k: {framework['coverage_factor']:.4g} "
        f"at p = {framework['coverage_probability']:.3g}",
        f"- Expanded uncertainty U: {framework['expanded_uncertainty']:.6g}{unit}",
        f"- Coverage interval: [{framework['coverage_interval'][0]:.6g}, "
        f"{framework['coverage_interval'][1]:.6g}]{unit}",
        "",
        "## Uncertainty budget",
        "",
        "| Input | Value | u(x) | Distribution | c = dy/dx | c*u(x) | % variance |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in framework["inputs"]:
        lines.append(
            f"| {item['name']} | {item['value']:.6g} | "
            f"{item['standard_uncertainty']:.4g} | {item['distribution']} | "
            f"{item['sensitivity']:.4g} | {item['contribution']:.4g} | "
            f"{item['variance_fraction'] * 100:.1f} |"
        )
    sampling = document.get("monte_carlo")
    if sampling:
        lines += [
            "",
            "## Monte Carlo propagation (JCGM 101:2008)",
            "",
            f"- Trials: {sampling['trials']} (seed {sampling['seed']})",
            f"- Mean: {sampling['mean']:.6g}{unit}",
            f"- Standard uncertainty: {sampling['standard_uncertainty']:.6g}{unit}",
            f"- Probabilistically symmetric interval: "
            f"[{sampling['probabilistically_symmetric_interval'][0]:.6g}, "
            f"{sampling['probabilistically_symmetric_interval'][1]:.6g}]{unit}",
            f"- Shortest coverage interval: "
            f"[{sampling['shortest_coverage_interval'][0]:.6g}, "
            f"{sampling['shortest_coverage_interval'][1]:.6g}]{unit}",
        ]
    validation = document.get("validation")
    if validation and validation.get("endpoint_agreement") is not None:
        verdict = "AGREE" if validation["endpoint_agreement"] else "DISAGREE"
        lines += [
            "",
            "## Fixed-trial interval comparison (not full JCGM validation)",
            "",
            f"- Numerical tolerance delta: {validation['numerical_tolerance']:.4g}",
            f"- Endpoint differences: "
            f"{validation['endpoint_difference_low']:.4g} (low), "
            f"{validation['endpoint_difference_high']:.4g} (high)",
            f"- Verdict: **{verdict}** - {validation['note']}",
        ]
    if document.get("warnings"):
        lines += ["", "## Warnings", ""]
        lines += [f"- {message}" for message in document["warnings"]]
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Propagate uncertainty through a measurement model with both the GUM "
            "framework and Monte Carlo sampling, then check the linearization."
        )
    )
    parser.add_argument(
        "--expression",
        help="measurement model, e.g. 'm / (pi * (d / 2) ** 2 * h)'",
    )
    parser.add_argument(
        "--variable",
        action="append",
        default=[],
        metavar="NAME=VALUE,U[,DIST[,DOF]]",
        help="input estimate and its standard uncertainty; repeatable",
    )
    parser.add_argument(
        "--correlation",
        action="append",
        default=[],
        metavar="A,B=R",
        help="correlation coefficient between two inputs; repeatable",
    )
    parser.add_argument("--spec", help="JSON file holding the whole model")
    parser.add_argument("--measurand", help="name of the output quantity")
    parser.add_argument("--unit", help="unit label for the report only")
    parser.add_argument(
        "--coverage",
        type=_common.probability,
        default=0.95,
        help="coverage probability for the expanded uncertainty (default 0.95)",
    )
    parser.add_argument(
        "--trials",
        type=_common.bounded_int(1_000, _common.MAX_TRIALS),
        default=_common.DEFAULT_TRIALS,
        help=f"Monte Carlo trials (default {_common.DEFAULT_TRIALS})",
    )
    parser.add_argument(
        "--seed",
        type=_common.bounded_int(0, 2**32 - 1),
        default=_common.DEFAULT_SEED,
        help="Monte Carlo seed",
    )
    parser.add_argument(
        "--significant-digits",
        type=_common.bounded_int(1, 2),
        default=2,
        help="significant digits retained in u_c for the clause 8 tolerance",
    )
    parser.add_argument(
        "--no-monte-carlo",
        action="store_true",
        help="skip sampling and report only the linearized result",
    )
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", help="write the report to this file")
    parser.add_argument(
        "--force", action="store_true", help="overwrite an existing output file"
    )
    return parser


def run(arguments: argparse.Namespace) -> dict[str, Any]:
    """Build the model from CLI flags or a spec file and propagate it."""

    spec: dict[str, Any] = {}
    if arguments.spec:
        loaded = _common.load_json(arguments.spec)
        if not isinstance(loaded, dict):
            raise CliError("the spec file must hold a JSON object")
        spec = loaded

    expression = arguments.expression or spec.get("expression")
    if not expression:
        raise CliError("supply --expression or a spec file containing 'expression'")

    records: list[Any] = list(spec.get("variables", []))
    records += [parse_variable(item) for item in arguments.variable]
    variables = normalize_variables(records)

    tree = _common.parse_expression(expression)
    required = set(_common.expression_variables(tree))
    supplied = {entry["name"] for entry in variables}
    missing = sorted(required - supplied)
    if missing:
        raise CliError(f"no value supplied for: {', '.join(missing)}")
    unused = sorted(supplied - required)
    if unused:
        raise CliError(
            f"these variables do not appear in the model: {', '.join(unused)}"
        )

    pairs: list[tuple[str, str, float]] = []
    for item in spec.get("correlations", []):
        if not isinstance(item, (list, tuple)) or len(item) != 3:
            raise CliError("each spec correlation must be [name_a, name_b, r]")
        pairs.append(
            (str(item[0]), str(item[1]), _common.as_finite(item[2], label="correlation"))
        )
    pairs += [parse_correlation(item) for item in arguments.correlation]

    correlations: dict[tuple[str, str], float] = {}
    for first, second, coefficient in pairs:
        if first == second:
            raise CliError("a variable cannot be correlated with itself")
        for name in (first, second):
            if name not in supplied:
                raise CliError(f"correlation references unknown variable {name!r}")
        if not -1.0 <= coefficient <= 1.0:
            raise CliError("correlation coefficients must lie in [-1, 1]")
        key = (first, second) if first < second else (second, first)
        if key in correlations and correlations[key] != coefficient:
            raise CliError(f"conflicting correlations given for {key[0]} and {key[1]}")
        if coefficient != 0.0:
            correlations[key] = coefficient

    coverage = spec.get("coverage_probability", arguments.coverage)
    coverage = _common.as_finite(coverage, label="coverage_probability")
    if not 0 < coverage < 1:
        raise CliError("coverage probability must be strictly between 0 and 1")

    framework = gum_framework(tree, variables, correlations, coverage)
    document: dict[str, Any] = {
        "measurand": arguments.measurand or spec.get("measurand"),
        "unit": arguments.unit or spec.get("unit"),
        "expression": expression,
        "gum_framework": framework,
        "correlations": [
            {"inputs": list(key), "coefficient": value}
            for key, value in sorted(correlations.items())
        ],
    }
    sampling = None
    if not arguments.no_monte_carlo:
        sampling = monte_carlo(
            tree, variables, correlations, coverage, arguments.trials, arguments.seed
        )
        document["monte_carlo"] = sampling
        document["validation"] = validate_linearization(
            framework, sampling, arguments.significant_digits
        )
    document["warnings"] = collect_warnings(framework, sampling, correlations)
    return document


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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
