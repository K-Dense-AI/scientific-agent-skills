#!/usr/bin/env python3
"""Apply ICH M10 acceptance criteria to a bioanalytical run or an ISR dataset.

Chromatographic assays and ligand binding assays carry DIFFERENT numeric
criteria in ICH M10, and conflating them is the most common error in this area.
--modality is therefore mandatory: nothing here has a default.

    # calibration standards and QCs from one analytical run
    python3 check_bioanalytical_run.py --modality chromatographic --run run1.csv

    # incurred sample reanalysis
    python3 check_bioanalytical_run.py --modality lba --isr isr.csv

    # LBA total-error criterion from accuracy/precision validation data
    python3 check_bioanalytical_run.py --modality lba --total-error ap.csv

Input for --run: columns `type` (calibrator|qc), `nominal`, `measured`, and an
optional `label` (e.g. LLOQ, low, medium, high, ULOQ, or ANCHOR for LBA anchor
points, which are excluded from the calibration pass count).

Input for --isr: columns `original` and `repeat`.

Input for --total-error: columns `label`, `accuracy_pct` (signed percent bias,
not recovery), `precision_pct` (non-negative CV).

Exit codes: 0 all applied criteria met, 1 criteria not met, 2 bad input.
"""

from __future__ import annotations

import argparse
import math
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

from _catalog import M10_CRITERIA  # noqa: E402
from _common import (  # noqa: E402
    EXIT_FINDINGS,
    EXIT_OK,
    InputError,
    add_common_args,
    emit,
    finding,
    note,
    parse_rows,
    read_input,
    require_columns,
    run_cli,
    to_float,
)

LIMIT_LABELS = {"lloq", "uloq"}


def calibrator_tolerance(label: str, crit: dict) -> float:
    """Tolerance for a calibration standard at this label.

    Routine-run QCs are not routed through here: M10 applies one flat tolerance
    to every QC level for run acceptance, which check_run uses directly.
    """
    low = label.strip().lower()
    if low == "lloq":
        return crit["calibration_tolerance_lloq_pct"]
    if low == "uloq":
        return crit["calibration_tolerance_uloq_pct"]
    return crit["calibration_tolerance_pct"]


def check_run(path: str, crit: dict) -> tuple[list[dict], list[str]]:
    rows = parse_rows(read_input(path), path)
    require_columns(rows, ["type", "nominal", "measured"])
    findings: list[str] = []
    detail: list[dict] = []

    cal_pass = cal_total = 0
    cal_by_level: dict[float, list[bool]] = {}
    qc_by_level: dict[float, list[bool]] = {}
    qc_labels: dict[float, str] = {}
    qc_pass = qc_total = 0

    for i, r in enumerate(rows):
        kind = (r["type"] or "").strip().lower()
        label = (r.get("label") or "").strip()
        nominal = to_float(r["nominal"], "nominal", i)
        measured = to_float(r["measured"], "measured", i)
        if nominal <= 0:
            raise InputError(f"row {i + 1}: nominal must be positive")
        dev = 100.0 * (measured - nominal) / nominal

        if kind in ("calibrator", "cal", "standard", "std"):
            if label.lower() == "anchor":
                if crit["total_error_pct"] is None:
                    raise InputError("ANCHOR exclusion is supported for LBA only")
                detail.append({"type": "calibrator", "label": "ANCHOR", "nominal": nominal,
                               "measured": measured, "deviation_pct": dev,
                               "tolerance_pct": float("nan"), "within": "excluded"})
                continue
            tol = calibrator_tolerance(label, crit)
            ok = abs(dev) <= tol
            cal_total += 1
            cal_pass += int(ok)
            cal_by_level.setdefault(nominal, []).append(ok)
            detail.append({"type": "calibrator", "label": label or "-", "nominal": nominal,
                           "measured": measured, "deviation_pct": dev,
                           "tolerance_pct": tol, "within": ok})
        elif kind in ("qc", "quality-control"):
            tol = crit["qc_run_tolerance_pct"]
            ok = abs(dev) <= tol
            key = nominal
            qc_labels[key] = label or f"{nominal:g}"
            qc_by_level.setdefault(key, []).append(ok)
            qc_total += 1
            qc_pass += int(ok)
            detail.append({"type": "qc", "label": qc_labels[key], "nominal": nominal,
                           "measured": measured, "deviation_pct": dev,
                           "tolerance_pct": tol, "within": ok})
        else:
            raise InputError(
                f"row {i + 1}: type must be calibrator or qc, got {r['type']!r}"
            )

    # Calibration curve criteria.
    if cal_total:
        n_levels = sum(any(flags) for flags in cal_by_level.values())
        need_levels = crit["calibration_min_levels"]
        if n_levels < need_levels:
            findings.append(
                f"calibration curve has {n_levels} passing concentration levels; M10 requires a "
                f"minimum of {need_levels} passing levels"
            )
        frac = cal_pass / cal_total
        need = crit["calibration_min_pass_fraction"]
        if frac < need:
            findings.append(
                f"{cal_pass}/{cal_total} calibration standards within tolerance "
                f"({frac * 100:.1f}%); M10 requires at least {need * 100:.0f}%"
            )
        for nominal, flags in cal_by_level.items():
            if sum(flags) / len(flags) < 0.5:
                findings.append(f"calibration level {nominal:g}: fewer than 50% of replicates pass")
        if cal_pass < cal_total:
            findings.append("failed calibrators require documented exclusion and a refitted curve; "
                            "this checker does not refit or establish a revised range")
        for boundary in ("lloq", "uloq"):
            points = [r for r in detail if r["type"] == "calibrator" and r["label"].lower() == boundary]
            if not points:
                findings.append(f"label {boundary.upper()} explicitly to verify boundary tolerances")
            else:
                expected = min(cal_by_level) if boundary == "lloq" else max(cal_by_level)
                if any(point["nominal"] != expected for point in points):
                    raise InputError(f"{boundary.upper()} label does not identify the calibration boundary")
        for anchor in (r for r in detail if r["within"] == "excluded"):
            if min(cal_by_level) <= anchor["nominal"] <= max(cal_by_level):
                raise InputError("LBA anchor points must lie outside the quantitation range")
    else:
        findings.append("no non-anchor calibration standards supplied; run assessment incomplete")

    # Routine run QC criteria: both the overall fraction and per-level fraction.
    if qc_total:
        n_qc_levels = len(qc_by_level)
        if n_qc_levels < crit["qc_levels_routine_run"]:
            findings.append(
                f"{n_qc_levels} QC levels present; M10 expects at least "
                f"{crit['qc_levels_routine_run']} for run acceptance"
            )
        frac = qc_pass / qc_total
        need = crit["qc_run_pass_fraction"]
        if frac < need:
            findings.append(
                f"{qc_pass}/{qc_total} QCs within +/-{crit['qc_run_tolerance_pct']:.0f}% "
                f"({frac * 100:.1f}%); M10 requires at least {need * 100:.0f}% of the total"
            )
        for level, flags in sorted(qc_by_level.items()):
            if len(flags) < 2:
                findings.append(f"QC level {qc_labels[level]}: at least two QC samples are needed")
            level_frac = sum(flags) / len(flags)
            if level_frac < crit["qc_run_pass_fraction_per_level"]:
                findings.append(
                    f"QC level {qc_labels[level]}: {sum(flags)}/{len(flags)} within tolerance "
                    f"({level_frac * 100:.0f}%); M10 requires at least "
                    f"{crit['qc_run_pass_fraction_per_level'] * 100:.0f}% at each level"
                )
    else:
        findings.append("no QCs supplied; run assessment incomplete")
    return detail, findings


def check_isr(path: str, crit: dict) -> tuple[list[dict], list[str]]:
    rows = parse_rows(read_input(path), path)
    require_columns(rows, ["original", "repeat"])
    tol = crit["isr_tolerance_pct"]
    detail, findings = [], []
    passes = 0
    for i, r in enumerate(rows):
        original = to_float(r["original"], "original", i)
        repeat = to_float(r["repeat"], "repeat", i)
        if original <= 0 or repeat <= 0:
            raise InputError("ISR requires positive quantified concentrations within the validated range")
        mean_val = 0.5 * (original + repeat)
        if mean_val == 0:
            raise InputError(f"row {i + 1}: mean of original and repeat is zero")
        # M10 defines the ISR percent difference against the mean of the two.
        diff = 100.0 * (repeat - original) / mean_val
        ok = abs(diff) <= tol
        passes += int(ok)
        detail.append({"sample": r.get("sample", str(i + 1)), "original": original,
                       "repeat": repeat, "mean": mean_val, "percent_difference": diff,
                       "tolerance_pct": tol, "within": ok})
    frac = passes / len(rows)
    if frac < crit["isr_pass_fraction"]:
        findings.append(
            f"ISR: {passes}/{len(rows)} repeats within +/-{tol:.0f}% ({frac * 100:.1f}%); "
            f"M10 requires at least {crit['isr_pass_fraction'] * 100:.0f}%"
        )
    return detail, findings


def check_total_error(path: str, crit: dict) -> tuple[list[dict], list[str]]:
    if crit["total_error_pct"] is None:
        raise InputError(
            "ICH M10 states a total-error criterion for ligand binding assays only; "
            "use --modality lba, or omit --total-error for a chromatographic assay"
        )
    rows = parse_rows(read_input(path), path)
    require_columns(rows, ["label", "accuracy_pct", "precision_pct"])
    detail, findings = [], []
    for i, r in enumerate(rows):
        label = (r["label"] or "").strip()
        acc = to_float(r["accuracy_pct"], "accuracy_pct", i)
        prec = to_float(r["precision_pct"], "precision_pct", i)
        if prec < 0:
            raise InputError("precision_pct must be a non-negative CV; accuracy_pct is signed bias, not recovery")
        total = abs(acc) + abs(prec)
        limit = (
            crit["total_error_pct_at_limits"]
            if label.lower() in LIMIT_LABELS
            else crit["total_error_pct"]
        )
        ok = total <= limit
        detail.append({"label": label or "-", "accuracy_pct": acc, "precision_pct": prec,
                       "total_error_pct": total, "limit_pct": limit, "within": ok})
        if not ok:
            findings.append(
                f"{label or 'level ' + str(i + 1)}: total error {total:.2f}% exceeds "
                f"{limit:.0f}%"
            )
    return detail, findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply ICH M10 acceptance criteria to bioanalytical data."
    )
    parser.add_argument("--modality", required=True, choices=sorted(M10_CRITERIA),
                        help="chromatographic or lba -- the criteria differ and there is no default")
    parser.add_argument("--run", help="calibrators and QCs from an analytical run")
    parser.add_argument("--isr", help="incurred sample reanalysis data")
    parser.add_argument("--total-error", dest="total_error",
                        help="accuracy/precision per level (ligand binding assays only)")
    parser.add_argument("--criteria", action="store_true",
                        help="print the criteria that would be applied and exit")
    add_common_args(parser)
    args = parser.parse_args()

    crit = M10_CRITERIA[args.modality]

    if args.criteria:
        rows = [
            {"criterion": k, "value": ("n/a" if v is None else v)}
            for k, v in crit.items()
            if k not in ("label", "notes")
        ]
        emit(rows, args.format)
        note(crit["label"])
        note(crit["notes"])
        return EXIT_OK

    if not any((args.run, args.isr, args.total_error)):
        raise InputError("supply at least one of --run, --isr, --total-error, or --criteria")

    detail: list[dict] = []
    findings: list[str] = []
    sections: dict[str, list[dict]] = {}

    if args.run:
        d, f = check_run(args.run, crit)
        sections["run"] = d
        findings += f
    if args.isr:
        d, f = check_isr(args.isr, crit)
        sections["isr"] = d
        findings += f
    if args.total_error:
        d, f = check_total_error(args.total_error, crit)
        sections["total_error"] = d
        findings += f

    if args.format == "json":
        emit([{"modality": args.modality, **sections, "findings": findings}], "json")
    else:
        for name, rows in sections.items():
            print(f"[{name}]")
            emit(rows, args.format)
            print()

    note(crit["label"])
    note(crit["notes"])
    note(
        "chromatographic and ligand binding assay criteria differ throughout M10; this run was "
        f"assessed as: {args.modality}"
    )
    for f in findings:
        finding(f)
    if not findings:
        note("all applied criteria met")
    note(
        "run acceptance is a documented decision by the analyst; this tool applies stated "
        "criteria and does not accept or reject a run"
    )
    if args.run:
        note("one row must represent a reportable standard or QC sample, not an individual LBA well; "
             "check blanks, zero samples, study-sample-dependent 5% QC count, bracketing, "
             "plate/batch criteria, and calibration refitting separately")
    return EXIT_FINDINGS if findings else EXIT_OK


if __name__ == "__main__":
    run_cli(main)
