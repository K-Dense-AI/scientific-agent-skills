#!/usr/bin/env python3
"""Audit portable QuTiP skill JSON without loading Python objects."""

from __future__ import annotations

import argparse
import math
from collections.abc import Mapping
from typing import Any

from _common import (
    MAX_SWEEP_RUNS,
    MAX_TIME_POINTS,
    QUTIP_VERSION,
    CliError,
    add_output_arguments,
    emit_json,
    finite_float,
    load_json_object,
    run_cli,
)


def _check(
    checks: list[dict[str, Any]],
    *,
    name: str,
    passed: bool,
    detail: str,
    severity: str = "error",
) -> None:
    checks.append(
        {
            "name": name,
            "passed": bool(passed),
            "severity": severity,
            "detail": detail,
        }
    )


def _finite_sequence(
    value: Any,
    *,
    name: str,
    maximum: int,
) -> list[float]:
    if not isinstance(value, list) or not 2 <= len(value) <= maximum:
        raise CliError(f"{name} must contain from 2 through {maximum} values")
    result: list[float] = []
    for index, item in enumerate(value):
        number = finite_float(item, name=f"{name}[{index}]")
        result.append(number)
    return result


def _audit_simulation(
    document: Mapping[str, Any],
    *,
    tolerance: float,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    required = {
        "qutip_version",
        "configuration",
        "model",
        "times",
        "expectations",
        "analytic_reference",
        "trajectory_statistics",
        "checks",
        "solver",
    }
    missing = sorted(required - set(document))
    _check(
        checks,
        name="required_fields",
        passed=not missing,
        detail="all required fields present" if not missing else f"missing: {missing}",
    )
    if missing:
        return checks

    _check(
        checks,
        name="exact_qutip_version",
        passed=document["qutip_version"] == QUTIP_VERSION,
        detail=f"reported {document['qutip_version']!r}; expected {QUTIP_VERSION}",
    )

    try:
        times = _finite_sequence(
            document["times"],
            name="times",
            maximum=MAX_TIME_POINTS,
        )
        increasing = all(right > left for left, right in zip(times, times[1:]))
    except CliError as exc:
        times = []
        increasing = False
        time_detail = str(exc)
    else:
        time_detail = f"{len(times)} finite values"
    _check(
        checks,
        name="bounded_monotonic_time_grid",
        passed=bool(times) and increasing,
        detail=time_detail if not times or increasing else "times are not increasing",
    )

    expectations = document["expectations"]
    if not isinstance(expectations, Mapping) or "excited_population" not in expectations:
        populations: list[float] = []
        population_detail = "expectations.excited_population is missing"
    else:
        try:
            populations = _finite_sequence(
                expectations["excited_population"],
                name="expectations.excited_population",
                maximum=MAX_TIME_POINTS,
            )
        except CliError as exc:
            populations = []
            population_detail = str(exc)
        else:
            population_detail = f"{len(populations)} finite values"
    lengths_match = bool(times) and bool(populations) and len(times) == len(populations)
    _check(
        checks,
        name="population_length",
        passed=lengths_match,
        detail=population_detail,
    )
    if populations:
        violation = max(
            max(0.0, -min(populations)),
            max(0.0, max(populations) - 1.0),
        )
    else:
        violation = math.inf
    _check(
        checks,
        name="population_bounds",
        passed=violation <= tolerance,
        detail=f"maximum [0,1] violation is {violation}",
    )

    analytic = document["analytic_reference"]
    analytic_ok = True
    analytic_detail = "not applicable"
    if isinstance(analytic, Mapping) and analytic.get("applicable"):
        try:
            reference = _finite_sequence(
                analytic["excited_population"],
                name="analytic_reference.excited_population",
                maximum=MAX_TIME_POINTS,
            )
            reported_error = finite_float(
                analytic["max_abs_error"],
                name="analytic_reference.max_abs_error",
                minimum=0.0,
            )
            recomputed = max(
                abs(observed - expected)
                for observed, expected in zip(populations, reference)
            )
            analytic_ok = (
                len(reference) == len(populations)
                and abs(recomputed - reported_error)
                <= max(1.0e-12, 10.0 * tolerance)
            )
            analytic_detail = (
                f"reported error {reported_error}; recomputed {recomputed}"
            )
        except (CliError, KeyError, ValueError) as exc:
            analytic_ok = False
            analytic_detail = str(exc)
    _check(
        checks,
        name="analytic_reference_consistency",
        passed=analytic_ok,
        detail=analytic_detail,
    )

    model = document["model"]
    assumptions = model.get("assumptions") if isinstance(model, Mapping) else None
    _check(
        checks,
        name="physical_assumptions_recorded",
        passed=isinstance(assumptions, list) and len(assumptions) >= 3,
        detail="model assumptions are present" if assumptions else "assumptions missing",
        severity="warning",
    )

    solver = document["solver"]
    stats = solver.get("stats") if isinstance(solver, Mapping) else None
    _check(
        checks,
        name="solver_stats_recorded",
        passed=isinstance(stats, Mapping) and bool(stats),
        detail="solver stats present" if stats else "solver stats missing or empty",
        severity="warning",
    )

    configuration = document["configuration"]
    solver_name = (
        configuration.get("solver") if isinstance(configuration, Mapping) else None
    )
    trajectory = document["trajectory_statistics"]
    if solver_name == "mcsolve":
        count = trajectory.get("trajectories_run") if isinstance(trajectory, Mapping) else None
        seeds = trajectory.get("seeds") if isinstance(trajectory, Mapping) else None
        trajectory_ok = (
            isinstance(count, int)
            and count > 0
            and isinstance(seeds, list)
            and len(seeds) == count
        )
        trajectory_detail = (
            f"trajectories_run={count}, seed_records="
            f"{len(seeds) if isinstance(seeds, list) else 'missing'}"
        )
    else:
        trajectory_ok = True
        trajectory_detail = "deterministic solver"
    _check(
        checks,
        name="trajectory_seed_manifest",
        passed=trajectory_ok,
        detail=trajectory_detail,
    )
    return checks


def _audit_convergence(
    document: Mapping[str, Any],
    *,
    tolerance: float,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    runs = document.get("runs")
    comparisons = document.get("comparisons")
    _check(
        checks,
        name="bounded_run_count",
        passed=isinstance(runs, list) and 2 <= len(runs) <= MAX_SWEEP_RUNS,
        detail=(
            f"run count {len(runs)}"
            if isinstance(runs, list)
            else "runs is not an array"
        ),
    )
    _check(
        checks,
        name="comparisons_present",
        passed=isinstance(comparisons, list) and bool(comparisons),
        detail=(
            f"comparison count {len(comparisons)}"
            if isinstance(comparisons, list)
            else "comparisons is not an array"
        ),
    )
    _check(
        checks,
        name="exact_qutip_version",
        passed=document.get("qutip_version") == QUTIP_VERSION,
        detail=f"reported {document.get('qutip_version')!r}",
    )
    finite = True
    maximum_difference = 0.0
    if isinstance(comparisons, list):
        for index, comparison in enumerate(comparisons):
            if not isinstance(comparison, Mapping):
                finite = False
                continue
            candidates = [
                value
                for key, value in comparison.items()
                if "difference" in key and isinstance(value, (int, float))
            ]
            for value in candidates:
                try:
                    number = finite_float(
                        value,
                        name=f"comparisons[{index}] difference",
                        minimum=0.0,
                    )
                except CliError:
                    finite = False
                else:
                    maximum_difference = max(maximum_difference, number)
    _check(
        checks,
        name="finite_convergence_differences",
        passed=finite,
        detail=f"largest recorded absolute difference is {maximum_difference}",
    )
    design = document.get("design")
    varied = design.get("varied") if isinstance(design, Mapping) else None
    _check(
        checks,
        name="sweep_design_recorded",
        passed=isinstance(varied, list) and bool(varied),
        detail=f"varied controls: {varied!r}",
        severity="warning",
    )
    _check(
        checks,
        name="requested_tolerance_recorded",
        passed=isinstance(document.get("acceptance"), (int, float))
        and abs(float(document["acceptance"]) - tolerance) >= 0.0,
        detail=f"report acceptance: {document.get('acceptance')!r}",
        severity="warning",
    )
    return checks


def audit_document(
    document: Mapping[str, Any],
    *,
    tolerance: float,
) -> dict[str, Any]:
    """Audit one recognized portable report."""

    if type(document.get("schema_version")) is not int or document["schema_version"] != 1:
        raise CliError("schema_version must be the integer 1")
    report_type = document.get("report_type")
    if report_type == "qutip.two_level_simulation":
        checks = _audit_simulation(document, tolerance=tolerance)
    elif report_type == "qutip.convergence_sweep":
        checks = _audit_convergence(document, tolerance=tolerance)
    else:
        raise CliError(
            "unsupported report_type; expected qutip.two_level_simulation "
            "or qutip.convergence_sweep"
        )

    failed = [
        check
        for check in checks
        if not check["passed"] and check["severity"] == "error"
    ]
    warnings = [
        check
        for check in checks
        if not check["passed"] and check["severity"] == "warning"
    ]
    status = "fail" if failed else ("pass_with_warnings" if warnings else "pass")
    return {
        "report_type": "qutip.result_audit",
        "schema_version": 1,
        "audited_report_type": report_type,
        "tolerance": tolerance,
        "status": status,
        "interpretation": (
            "Status describes report consistency, not physical validity or "
            "convergence. Review analytic error, invariant audits, and the "
            "original simulation or sweep acceptance status separately."
        ),
        "checks": checks,
        "summary": {
            "passed": sum(check["passed"] for check in checks),
            "errors": len(failed),
            "warnings": len(warnings),
        },
        "safety": {
            "input_format": "strict JSON",
            "python_object_deserialization": False,
            "network": False,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit bounded QuTiP skill JSON without importing QuTiP or "
            "deserializing Python objects."
        )
    )
    parser.add_argument("report", help="local strict-JSON report path")
    parser.add_argument("--tolerance", type=float, default=1.0e-6)
    add_output_arguments(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    tolerance = finite_float(
        args.tolerance,
        name="tolerance",
        minimum=1.0e-12,
        maximum=0.1,
    )
    document = load_json_object(args.report)
    report = audit_document(document, tolerance=tolerance)
    emit_json(report, output=args.output, force=args.force)
    return 0 if report["status"] != "fail" else 1


if __name__ == "__main__":
    raise SystemExit(run_cli(main))
