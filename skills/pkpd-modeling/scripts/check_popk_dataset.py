#!/usr/bin/env python3
"""Check common NONMEM-style population PK dataset conventions.

This is a partial sanity checker, not an NM-TRAN emulator. Verify actual event
ordering, numeric/censored DV conventions, dose history and the model's input
mapping. Advanced MDV/SS, pure PD and multi-analyte datasets need tailored checks.

    python3 check_popk_dataset.py -i nmdata.csv
    python3 check_popk_dataset.py -i nmdata.csv --covariates WT,CRCL --time-varying WT

Exit 1 means a finding at or above --fail-on; --strict also fails on warnings.
"""

from __future__ import annotations

import argparse
import math
from collections import Counter
from typing import Sequence

from _common import (
    Report,
    add_format_argument,
    main_wrapper,
    read_table,
)

SEVERITY_ORDER = {"note": 0, "warning": 1, "error": 2}

# NONMEM data item conventions. EVID 3 resets the system, 4 resets and doses.
EVID_MEANINGS = {
    "0": "observation",
    "1": "dose",
    "2": "other-type event (no dose, no observation)",
    "3": "reset",
    "4": "reset and dose",
}

MISSING = {"", ".", "na", "n/a", "nan", "null", "none"}


def _num(value: str) -> float | None:
    text = (value or "").strip()
    if text.lower() in MISSING:
        return None
    try:
        value = float(text)
        return value if math.isfinite(value) else None
    except ValueError:
        return None


def _is_missing(value: str) -> bool:
    return (value or "").strip().lower() in MISSING


class Findings:
    def __init__(self) -> None:
        self.items: list[dict[str, object]] = []

    def add(self, severity: str, check: str, detail: str, rows: Sequence[int] = ()) -> None:
        listed = list(rows)[:8]
        self.items.append(
            {
                "severity": severity,
                "check": check,
                "detail": detail,
                "n_records": len(rows),
                "example_rows": ", ".join(str(r) for r in listed) + ("..." if len(rows) > 8 else ""),
            }
        )

    def max_severity(self) -> int:
        return max((SEVERITY_ORDER[i["severity"]] for i in self.items), default=-1)


# ------------------------------------------------------------------ checks


def check_dataset(rows: list[dict[str, str]], args: argparse.Namespace) -> tuple[Findings, dict]:
    found = Findings()
    columns = list(rows[0].keys())
    upper = {c.lower(): c for c in columns}

    def col(name: str) -> str | None:
        return upper.get(name.lower())

    id_col = col(args.id_column)
    time_col = col(args.time_column)
    dv_col = col(args.dv_column)
    amt_col = col(args.amt_column)
    evid_col, mdv_col = col("evid"), col("mdv")
    rate_col, ss_col, ii_col, addl_col = col("rate"), col("ss"), col("ii"), col("addl")

    for required, name in ((id_col, args.id_column), (time_col, args.time_column), (dv_col, args.dv_column)):
        if required is None:
            found.add("error", "required column", f"no '{name}' column; NONMEM cannot build a dataset without it")
    if amt_col is None:
        found.add("error", "required column", "no AMT column: without it no dose is ever administered")
    if evid_col is None:
        found.add(
            "warning",
            "EVID absent",
            "no EVID column. NONMEM then infers events from AMT, which works only if every dose "
            "record has AMT>0 and every observation has AMT=0 or missing. Supplying EVID is safer.",
        )
    if not id_col or not time_col:
        return found, {}

    # ---- column-name hazards
    long_names = [c for c in columns if len(c) > 20]
    if long_names:
        found.add("note", "column names", f"unusually long column name(s): {', '.join(long_names[:4])}")
    non_alnum = [c for c in columns if not c.replace("_", "").isalnum()]
    if non_alnum:
        found.add(
            "warning",
            "column names",
            f"column name(s) with characters NM-TRAN will reject in $INPUT: {', '.join(non_alnum[:6])}",
        )

    # ---- per-record checks
    bad_dv_text, neg_time, neg_conc, bad_evid = [], [], [], []
    dose_without_amt, obs_with_amt, obs_missing_dv, mdv_conflict = [], [], [], []
    rate_issues, ss_missing_ii, addl_missing_ii, zero_ii = [], [], [], []

    subjects: dict[str, list[tuple[int, dict[str, str]]]] = {}
    for index, row in enumerate(rows, start=2):  # header is line 1
        subject = (row.get(id_col) or "").strip()
        subjects.setdefault(subject, []).append((index, row))

        evid = (row.get(evid_col) or "0").strip() if evid_col else None
        if evid_col and evid not in EVID_MEANINGS and not _is_missing(evid):
            bad_evid.append(index)

        time = _num(row.get(time_col, ""))
        if time is None:
            found.add("error", "TIME not numeric", f"row {index}: TIME is {row.get(time_col)!r}", [index])
        elif time < 0 and not args.allow_negative_time:
            neg_time.append(index)

        dv_raw = row.get(dv_col, "") if dv_col else ""
        amt = _num(row.get(amt_col, "")) if amt_col else None
        is_dose = (evid in {"1", "4"}) if evid_col else bool(amt and amt > 0)
        is_obs = (evid == "0") if evid_col else not is_dose

        if is_obs:
            if not _is_missing(dv_raw) and _num(dv_raw) is None:
                bad_dv_text.append(index)
            value = _num(dv_raw)
            if value is not None and value < 0:
                neg_conc.append(index)
            mdv = (row.get(mdv_col) or "0").strip() if mdv_col else "0"
            if _is_missing(dv_raw) and mdv != "1":
                obs_missing_dv.append(index)
            if not _is_missing(dv_raw) and mdv == "1":
                mdv_conflict.append(index)
            if amt not in (None, 0.0):
                obs_with_amt.append(index)
        if is_dose and (amt is None or amt <= 0) and not (ss_col and (_num(row.get(ss_col, "")) or 0) > 0 and rate_col and (_num(row.get(rate_col, "")) or 0) > 0):
            dose_without_amt.append(index)

        if rate_col and not _is_missing(row.get(rate_col, "")):
            rate = _num(row.get(rate_col, ""))
            if rate is None or (rate < 0 and rate not in (-1.0, -2.0)):
                rate_issues.append(index)
        if ss_col and (row.get(ss_col) or "0").strip() not in {"0", "", "."}:
            ii = _num(row.get(ii_col, "")) if ii_col else None
            constant_infusion = amt in (None, 0.0) and (_num(row.get(rate_col, "")) or 0) > 0
            if (ii is None or ii <= 0) and not constant_infusion:
                ss_missing_ii.append(index)
        if addl_col and (_num(row.get(addl_col, "")) or 0) > 0:
            ii = _num(row.get(ii_col, "")) if ii_col else None
            if ii is None:
                addl_missing_ii.append(index)
            elif ii <= 0:
                zero_ii.append(index)

    if bad_dv_text:
        found.add(
            "error",
            "non-numeric DV",
            "DV contains nonnumeric or nonfinite text (for example BLQ). Do not rely on parsing or "
            "automatic recoding to represent censoring. Recode to a numeric "
            "value plus a BLQ flag column and choose an M-method.",
            bad_dv_text,
        )
    if neg_time:
        found.add("error", "negative TIME", "TIME before zero without --allow-negative-time", neg_time)
    if neg_conc:
        found.add("warning", "negative DV", "negative concentrations in observation records", neg_conc)
    if bad_evid:
        found.add("error", "invalid EVID", f"EVID outside {sorted(EVID_MEANINGS)}", bad_evid)
    if dose_without_amt:
        found.add("error", "dose without AMT", "EVID marks a dose but AMT is missing or not positive", dose_without_amt)
    if obs_with_amt:
        found.add(
            "warning",
            "observation carries AMT",
            "records marked as observations also carry a non-zero AMT; if EVID is dropped from $INPUT "
            "these become doses",
            obs_with_amt,
        )
    if obs_missing_dv:
        found.add("error", "missing DV with MDV=0", "observation record has no DV but is not flagged MDV=1", obs_missing_dv)
    if mdv_conflict:
        found.add("warning", "MDV=1 with a DV present", "the observation will be ignored by the estimation", mdv_conflict)
    if rate_issues:
        found.add("error", "invalid RATE", "RATE must be 0 (bolus), >0 (known infusion rate), -1 (modelled rate), or -2 (modelled duration)", rate_issues)
    if ss_missing_ii:
        found.add("error", "SS without II", "a steady-state record needs a positive II", ss_missing_ii)
    if addl_missing_ii:
        found.add("error", "ADDL without II", "ADDL needs positive II; invalid events must be corrected before NM-TRAN/PREDPP", addl_missing_ii)
    if zero_ii:
        found.add("error", "ADDL with II<=0", "II must be positive for ADDL to place additional doses", zero_ii)

    seen_ids, previous_id = set(), None
    for row in rows:
        sid = row.get(id_col, "")
        if sid != previous_id and sid in seen_ids:
            found.add("error", "noncontiguous ID", f"subject {sid} occurs in separate blocks")
        seen_ids.add(sid)
        previous_id = sid
        if _num(sid) is None:
            found.add("error", "ID not numeric", "NONMEM ID must be numeric")

    # ---- per-subject checks
    no_obs, no_dose, unsorted, duplicated, first_not_dose = [], [], [], [], []
    obs_counts, dose_counts = [], []
    for subject, records in subjects.items():
        if subject == "":
            found.add("error", "blank ID", "records with an empty ID column", [r[0] for r in records])
            continue
        times = []
        n_obs = n_dose = 0
        for index, row in records:
            time = _num(row.get(time_col, ""))
            times.append((time, index))
            evid = (row.get(evid_col) or "0").strip() if evid_col else None
            amt = _num(row.get(amt_col, "")) if amt_col else None
            if (evid in {"1", "4"}) if evid_col else bool(amt and amt > 0):
                n_dose += 1
            elif (evid == "0") if evid_col else True:
                if not _is_missing(row.get(dv_col, "")) and (not mdv_col or _num(row.get(mdv_col, "0")) in (0, None)):
                    n_obs += 1
        obs_counts.append(n_obs)
        dose_counts.append(n_dose)
        if n_obs == 0:
            no_obs.append(subject)
        if n_dose == 0:
            no_dose.append(subject)
        numeric = [t for t, _ in times if t is not None]
        previous_time = None
        decreased = False
        for _, row in records:
            current_time = _num(row.get(time_col, ""))
            reset = evid_col and row.get(evid_col) in {"3", "4"}
            if current_time is not None and previous_time is not None and current_time < previous_time and not reset:
                decreased = True
            if current_time is not None:
                previous_time = current_time
        if decreased:
            unsorted.append(subject)
        counts = Counter(numeric)
        if any(v > 1 for v in counts.values()):
            duplicated.append(subject)
        if records:
            first_evid = (records[0][1].get(evid_col) or "0").strip() if evid_col else None
            first_amt = _num(records[0][1].get(amt_col, "")) if amt_col else None
            is_dose_first = (first_evid in {"1", "4"}) if evid_col else bool(first_amt and first_amt > 0)
            if not is_dose_first:
                first_not_dose.append(subject)

    if no_obs:
        found.add(
            "error",
            "subject with no observations",
            f"{len(no_obs)} subject(s) contribute no DV: {', '.join(no_obs[:6])}. Their ETAs are drawn "
            "entirely from the prior and they inflate the apparent N of the analysis.",
        )
    if no_dose:
        found.add("error", "subject with no dose", f"{len(no_dose)} subject(s) have observations but no dose: {', '.join(no_dose[:6])}")
    if unsorted:
        found.add("error", "TIME not sorted", f"{len(unsorted)} subject(s) have out-of-order TIME: {', '.join(unsorted[:6])}")
    if duplicated:
        found.add(
            "warning",
            "duplicate TIME within a subject",
            f"{len(duplicated)} subject(s) have records sharing a timestamp: {', '.join(duplicated[:6])}. "
            "NONMEM applies them in file order, so a dose and an observation at the same time give a "
            "pre-dose or post-dose value depending purely on which row came first.",
        )
    if first_not_dose:
        found.add(
            "note",
            "first record is not a dose",
            f"{len(first_not_dose)} subject(s) start with a non-dose record: {', '.join(first_not_dose[:6])}. "
            "Fine for a pre-dose baseline; wrong if a dose is missing.",
        )

    # ---- covariates
    for name in args.covariates:
        cov_col = col(name)
        if cov_col is None:
            found.add("error", "covariate absent", f"--covariates names '{name}' but there is no such column")
            continue
        missing_rows, non_numeric = [], []
        per_subject_values: dict[str, set[str]] = {}
        for index, row in enumerate(rows, start=2):
            raw = row.get(cov_col, "")
            subject = (row.get(id_col) or "").strip()
            per_subject_values.setdefault(subject, set()).add(raw.strip())
            if _is_missing(raw):
                missing_rows.append(index)
            elif _num(raw) is None:
                non_numeric.append(index)
        if missing_rows:
            found.add(
                "error",
                f"covariate {name} missing",
                f"{len(missing_rows)} record(s) have no value. A blank or '.' is read as 0, not as "
                f"missing, so those records enter the covariate model with {name} = 0 - a 0 kg "
                "body weight, a 0 mL/min creatinine clearance - rather than being excluded.",
                missing_rows,
            )
        if non_numeric:
            found.add("error", f"covariate {name} non-numeric", "values NM-TRAN cannot read as numbers", non_numeric)
        varying = [s for s, values in per_subject_values.items() if len(values) > 1]
        if varying and name.lower() not in {t.lower() for t in args.time_varying}:
            found.add(
                "warning",
                f"covariate {name} varies within subject",
                f"{len(varying)} subject(s) have more than one value: {', '.join(varying[:6])}. "
                "If this is intended, list it in --time-varying; if not, the model will use whichever "
                "value is on the record being evaluated.",
            )

    summary = {
        "records": len(rows),
        "subjects": len(subjects),
        "observations": sum(obs_counts),
        "dose_records": sum(dose_counts),
        "median_observations_per_subject": sorted(obs_counts)[len(obs_counts) // 2] if obs_counts else 0,
        "subjects_with_one_observation": sum(1 for c in obs_counts if c == 1),
        "columns": len(columns),
    }
    if summary["subjects"] and summary["observations"] / max(summary["subjects"], 1) < 2:
        found.add(
            "note",
            "sparse sampling",
            "fewer than two observations per subject on average. A structural model with an absorption "
            "phase is unlikely to be identifiable; consider fixing parameters from a richer study.",
        )
    return found, summary


# --------------------------------------------------------------------- CLI


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a population PK dataset against NONMEM/nlmixr2 data conventions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("--id-column", default="ID")
    parser.add_argument("--time-column", default="TIME")
    parser.add_argument("--dv-column", default="DV")
    parser.add_argument("--amt-column", default="AMT")
    parser.add_argument("--covariates", default="", help="comma-separated covariate columns to check")
    parser.add_argument("--time-varying", default="", help="covariates that are expected to change within a subject")
    parser.add_argument("--allow-negative-time", action="store_true")
    parser.add_argument(
        "--fail-on",
        choices=("note", "warning", "error"),
        default="error",
        help="lowest severity that makes the exit code 1 (default: error)",
    )
    parser.add_argument("--strict", action="store_true", help="shorthand for --fail-on warning")
    add_format_argument(parser)
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from _common import validate_numeric_args
    validate_numeric_args(args)
    args.covariates = [c.strip() for c in args.covariates.split(",") if c.strip()]
    args.time_varying = [c.strip() for c in args.time_varying.split(",") if c.strip()]
    if args.strict:
        args.fail_on = "warning"

    rows = read_table(args.input)
    found, summary = check_dataset(rows, args)

    report = Report()
    for key, value in summary.items():
        report.scalar(key, value)
    if found.items:
        ordered = sorted(found.items, key=lambda i: -SEVERITY_ORDER[str(i["severity"])])
        report.table("dataset findings", ordered)
    else:
        report.table("dataset findings", [{"severity": "none", "check": "all checks passed", "detail": "", "n_records": 0, "example_rows": ""}])

    report.note(
        "This checks data conventions, not pharmacology. A dataset that passes can still be wrong: "
        "verify units, time origin, and that DV is the quantity the model predicts."
    )
    threshold = SEVERITY_ORDER[args.fail_on]
    for item in found.items:
        if SEVERITY_ORDER[str(item["severity"])] >= threshold:
            report.finding(f"[{item['severity']}] {item['check']}: {item['detail']}")
    return report.emit(args.format)


if __name__ == "__main__":
    raise SystemExit(main_wrapper(run))
