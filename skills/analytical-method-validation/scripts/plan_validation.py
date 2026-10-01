#!/usr/bin/env python3
"""Design a validation study: which framework, which tests, what study layout.

Answers the first question of any validation exercise -- what am I required to
demonstrate, and with how much data -- before any sample is injected.

    python3 plan_validation.py --framework ich-q2r2 --attribute assay --technique hplc
    python3 plan_validation.py --framework ich-m10 --modality lba
    python3 plan_validation.py --list-frameworks
    python3 plan_validation.py --framework ich-q2r2 --attribute impurity --protocol > protocol.md

Exit codes: 0 plan produced, 2 bad input.
"""

from __future__ import annotations

import argparse
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

from _catalog import (  # noqa: E402
    DL_QL_APPROACHES,
    FRAMEWORKS,
    M10_CRITERIA,
    Q2R2_REPORTABLE_RANGE,
    Q2R2_STUDY_DESIGN,
    Q2R2_TESTS_BY_ATTRIBUTE,
    RESEARCH_DATE,
    TECHNIQUE_NOTES,
    resolve_attribute,
)
from _common import (  # noqa: E402
    EXIT_OK,
    InputError,
    add_common_args,
    emit,
    note,
    run_cli,
)

STATUS_TEXT = {
    "required": "conduct",
    "required-QL": "conduct (QL; DL too in some complex cases)",
    "required-DL": "conduct (DL)",
    "required-unless-reproducibility": (
        "conduct, unless intermediate precision can be derived from a reproducibility dataset"
    ),
    "not-normally": "not normally conducted",
}


def plan_q2r2(attribute: str, technique: str | None, range_use: str | None) -> list[dict]:
    tests = Q2R2_TESTS_BY_ATTRIBUTE[attribute]
    rows = []
    for characteristic, status in tests.items():
        design = Q2R2_STUDY_DESIGN.get(characteristic, {})
        rows.append(
            {
                "characteristic": characteristic,
                "required": STATUS_TEXT[status],
                "study_design": design.get("requirement", ""),
                "report": design.get("report", ""),
                "reference": design.get("reference", ""),
            }
        )
    # Robustness sits in development under Q14 but belongs in the plan.
    rows.append(
        {
            "characteristic": "robustness",
            "required": "development activity (ICH Q14); available on request",
            "study_design": Q2R2_STUDY_DESIGN["robustness"]["requirement"],
            "report": Q2R2_STUDY_DESIGN["robustness"]["report"],
            "reference": Q2R2_STUDY_DESIGN["robustness"]["reference"],
        }
    )
    if technique:
        tn = TECHNIQUE_NOTES.get(technique)
        if tn:
            rows.append(
                {
                    "characteristic": f"technique note ({technique})",
                    "required": f"see Q2(R2) Annex 2 {tn['annex_table']}",
                    "study_design": f"robustness parameters: {tn['robustness']}",
                    "report": tn["special"],
                    "reference": "Q2(R2) Annex 2",
                }
            )
    if range_use:
        rr = Q2R2_REPORTABLE_RANGE.get(range_use)
        if rr:
            rows.append(
                {
                    "characteristic": f"reportable range ({range_use})",
                    "required": "confirm response, accuracy and precision across this range",
                    "study_design": f"low: {rr['low']}",
                    "report": f"high: {rr['high']}",
                    "reference": "Q2(R2) 2.3, Table 2",
                }
            )
    return rows


def plan_m10(modality: str) -> list[dict]:
    crit = M10_CRITERIA[modality]
    rows = [
        {
            "item": "calibration curve",
            "requirement": (
                f"minimum {crit['calibration_min_levels']} concentration levels including "
                f"the LLOQ and ULOQ; at least "
                f"{crit['calibration_min_pass_fraction'] * 100:.0f}% of standards and at least 6 levels must pass"
            ),
            "tolerance": (
                f"+/-{crit['calibration_tolerance_pct']:.0f}% nominal; "
                f"+/-{crit['calibration_tolerance_lloq_pct']:.0f}% at LLOQ; "
                f"+/-{crit['calibration_tolerance_uloq_pct']:.0f}% at ULOQ"
            ),
        },
        {
            "item": "accuracy and precision QC levels",
            "requirement": (
                f"{crit['qc_levels_accuracy_precision']} levels; "
                f"{crit['ap_replicates_per_run']} replicates per level per run; "
                f"at least {crit['ap_min_runs']} runs over at least {crit['ap_min_days']} days"
            ),
            "tolerance": (
                f"accuracy +/-{crit['accuracy_tolerance_pct']:.0f}% "
                f"(+/-{crit['accuracy_tolerance_lloq_pct']:.0f}% at {crit['limit_levels']}); "
                f"precision CV <={crit['precision_cv_pct']:.0f}% "
                f"(<={crit['precision_cv_lloq_pct']:.0f}% at {crit['limit_levels']})"
            ),
        },
        {
            "item": "routine run acceptance",
            "requirement": (
                f"{crit['qc_levels_routine_run']} QC levels; at least "
                f"{crit['qc_run_pass_fraction'] * 100:.0f}% of all QCs and at least "
                f"{crit['qc_run_pass_fraction_per_level'] * 100:.0f}% at each level must pass"
            ),
            "tolerance": f"+/-{crit['qc_run_tolerance_pct']:.0f}% nominal",
        },
        {
            "item": "selectivity",
            "requirement": f"at least {crit['selectivity_min_sources']} individual matrix sources/lots",
            "tolerance": (
                f"interference <={crit['carryover_blank_pct_of_lloq']:.0f}% of LLOQ analyte "
                f"response and <={crit['carryover_blank_pct_of_is']:.0f}% of IS response"
                if crit["carryover_blank_pct_of_lloq"] is not None
                else "per guideline; evaluate interference in each source"
            ),
        },
        {
            "item": "dilution integrity",
            "requirement": "validate the dilution factors used in study sample analysis",
            "tolerance": f"mean within +/-{crit['dilution_tolerance_pct']:.0f}% nominal",
        },
        {
            "item": "stability",
            "requirement": "cover the conditions and durations study samples actually experience",
            "tolerance": f"mean at each QC level within +/-{crit['stability_tolerance_pct']:.0f}% nominal",
        },
        {
            "item": "incurred sample reanalysis",
            "requirement": (
                f"repeat a predefined subset in separate runs; at least "
                f"{crit['isr_pass_fraction'] * 100:.0f}% of repeats must agree"
            ),
            "tolerance": f"percent difference within +/-{crit['isr_tolerance_pct']:.0f}%",
        },
    ]
    if crit["total_error_pct"] is not None:
        rows.append(
            {
                "item": "total error",
                "requirement": "absolute bias (%) plus precision CV (%)",
                "tolerance": (
                    f"<={crit['total_error_pct']:.0f}%, "
                    f"<={crit['total_error_pct_at_limits']:.0f}% at LLOQ and ULOQ"
                ),
            }
        )
    return rows


def render_protocol(framework: str, attribute: str | None, modality: str | None,
                    technique: str | None, range_use: str | None) -> str:
    fw = FRAMEWORKS[framework]
    lines = [
        "# Analytical Procedure Validation Protocol",
        "",
        "> Draft skeleton. Every bracketed field is a decision the analyst and quality unit",
        "> must make and record BEFORE data collection. Acceptance criteria set after seeing",
        "> data are not acceptance criteria.",
        "",
        "## 1. Identification",
        "",
        "| Field | Value |",
        "| --- | --- |",
        "| Protocol number / version | [ ] |",
        "| Analytical procedure identifier | [ ] |",
        "| Product / analyte / matrix | [ ] |",
        "| Governing framework | " + fw["title"] + " |",
        "| Regional expectation confirmed | [ ] " + fw["effective_note"] + " |",
        "| Author / date | [ ] |",
        "| Reviewed / approved by (quality unit) | [ ] |",
        "",
        "## 2. Intended purpose and analytical target profile",
        "",
        "- Measurand and reporting unit: [ ]",
        "- Decision the result supports (release, stability, in-process, clinical): [ ]",
        "- Specification or reporting limits the procedure must serve: [ ]",
        "- Required reportable range, derived from the specification: [ ]",
        "- Performance characteristics and criteria: [ ] (formal ATP optional under ICH Q14)",
        "",
        "## 3. Pre-stated acceptance criteria",
        "",
        "| Characteristic | Criterion | Justification | Source |",
        "| --- | --- | --- | --- |",
    ]
    if framework == "ich-m10" and modality:
        for row in plan_m10(modality):
            lines.append(
                f"| {row['item']} | {row['tolerance']} | guideline default | ICH M10 |"
            )
    elif framework == "ich-q2r2" and attribute:
        for row in plan_q2r2(attribute, technique, range_use):
            crit = "[ ] state an appropriate criterion"
            lines.append(
                f"| {row['characteristic']} | {crit} | [ ] | {row['reference'] or 'ICH Q2(R2)'} |"
            )
    lines += [
        "",
        "> ICH Q2(R2) deliberately does not set numeric acceptance criteria for most",
        "> characteristics. A criterion has to come from the specification, the ATP, product",
        "> knowledge, or development data -- not from a remembered default.",
        "",
        "## 4. Study design",
        "",
        "| Characteristic | Levels | Replicates | Runs / days / analysts / instruments |",
        "| --- | --- | --- | --- |",
        "| [ ] | [ ] | [ ] | [ ] |",
        "",
        "- Reference materials and their documented identity/purity: [ ]",
        "- Number of replicates matches the routine reportable result: [ ] yes / [ ] justified",
        "- Prior knowledge or development data used in place of a test, with justification: [ ]",
        "",
        "## 5. Sample and solution handling",
        "",
        "- Preparation, storage, and solution stability window: [ ]",
        "- Blank, placebo, and spiked matrix definitions: [ ]",
        "",
        "## 6. Statistical treatment",
        "",
        "- Calibration model and weighting, stated in advance: [ ]",
        "- Interval to be reported with accuracy and precision (confidence level): [ ]",
        "- Software, version, and calculation verification: [ ]",
        "",
        "## 7. Deviations and data integrity",
        "",
        "- Deviation handling and reporting: [ ]",
        "- All results reported, including out-of-criteria values: [ ] confirmed",
        "- Raw data location and audit trail: [ ]",
        "",
        "## 8. Approvals",
        "",
        "| Role | Name | Signature | Date |",
        "| --- | --- | --- | --- |",
        "| Author | | | |",
        "| Technical reviewer | | | |",
        "| Quality unit | | | |",
        "",
        f"_Framework metadata researched {RESEARCH_DATE}. Confirm the current guideline text "
        f"and regional expectation before use: {fw['url']}_",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Plan an analytical procedure validation study.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--framework", help="governing framework key")
    parser.add_argument("--attribute", help="measured attribute (assay, impurity, identity, ...)")
    parser.add_argument("--modality", choices=sorted(M10_CRITERIA),
                        help="ICH M10 only: chromatographic or lba")
    parser.add_argument("--technique", choices=sorted(TECHNIQUE_NOTES),
                        help="analytical technique, for Annex 2 notes")
    parser.add_argument("--range-use", choices=sorted(Q2R2_REPORTABLE_RANGE),
                        help="reportable range example to include")
    parser.add_argument("--protocol", action="store_true",
                        help="emit a validation protocol skeleton in Markdown")
    parser.add_argument("--list-frameworks", action="store_true")
    parser.add_argument("--list-dl-ql", action="store_true",
                        help="list the DL/QL estimation approaches")
    add_common_args(parser)
    args = parser.parse_args()

    if args.list_frameworks:
        rows = [
            {
                "key": key,
                "title": fw["title"],
                "adopted": fw["adopted"],
                "text_reusable": "yes" if fw["reproducible"] else "no (paywalled)",
                "scope": fw["scope"],
            }
            for key, fw in FRAMEWORKS.items()
        ]
        emit(rows, args.format)
        note(f"framework metadata researched {RESEARCH_DATE}; confirm before relying on a date")
        return EXIT_OK

    if args.list_dl_ql:
        rows = [
            {"approach": k, "detection_limit": v["dl"], "quantitation_limit": v["ql"],
             "note": v["note"]}
            for k, v in DL_QL_APPROACHES.items()
        ]
        emit(rows, args.format)
        note("source: ICH Q2(R2) 3.2.3")
        return EXIT_OK

    if not args.framework:
        raise InputError("--framework is required (or use --list-frameworks)")
    if args.framework not in FRAMEWORKS:
        raise InputError(
            f"unknown framework {args.framework!r}; choose from: {', '.join(FRAMEWORKS)}"
        )
    fw = FRAMEWORKS[args.framework]

    attribute = None
    if args.attribute:
        try:
            attribute = resolve_attribute(args.attribute)
        except KeyError as exc:
            raise InputError(str(exc)) from exc

    if args.framework == "ich-m10":
        if not args.modality:
            raise InputError("ICH M10 needs --modality chromatographic|lba")
        rows = plan_m10(args.modality)
    elif args.framework == "ich-q2r2":
        if not attribute:
            raise InputError("ICH Q2(R2) needs --attribute (assay, impurity, identity, ...)")
        rows = plan_q2r2(attribute, args.technique, args.range_use)
    else:
        note(
            f"{fw['title']} is copyrighted and not reproduced here. This skill reports its "
            "designation, scope, and where to obtain it; the study design must come from the "
            "authorised text."
        )
        rows = [
            {
                "framework": args.framework,
                "title": fw["title"],
                "scope": fw["scope"],
                "obtain_from": fw["url"],
                "companion": fw["companion"],
            }
        ]

    if args.protocol:
        print(render_protocol(args.framework, attribute, args.modality,
                              args.technique, args.range_use))
        note("protocol skeleton written; every bracketed field needs a decision before data")
        return EXIT_OK

    emit(rows, args.format)
    note(f"framework: {fw['title']}")
    note(f"regional applicability: {fw['effective_note']}")
    if fw["companion"]:
        note(f"companion: {fw['companion']}")
    note(f"catalogue researched {RESEARCH_DATE}; confirm the current text at {fw['url']}")
    note("this tool reports requirements; it does not decide fitness for purpose")
    return EXIT_OK


if __name__ == "__main__":
    run_cli(main)
