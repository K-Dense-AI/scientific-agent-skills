#!/usr/bin/env python3
"""Framework catalogue for analytical method validation.

Content sourced 2026-09-30 from the freely published ICH guidelines, which ICH
licenses for reuse with acknowledgement. Compendial (USP) and CLSI documents are
copyrighted and paywalled: they are referenced here by designation, title, and
scope only. No proprietary text is reproduced.

See ../references/source-ledger.md for the provenance of every entry.
"""

from __future__ import annotations

from typing import Any

RESEARCH_DATE = "2026-09-30"

# --------------------------------------------------------------------------
# Frameworks
# --------------------------------------------------------------------------

FRAMEWORKS: dict[str, dict[str, Any]] = {
    "ich-q2r2": {
        "title": "ICH Q2(R2) Validation of Analytical Procedures",
        "adopted": "2023-11-01",
        "effective_note": (
            "Adopted by the ICH Assembly 1 Nov 2023; an error correction to Table 5 and "
            "Tables 6-11 is dated 30 Nov 2023. Confirm the adoption/implementation date for "
            "your region with the regional regulator."
        ),
        "supersedes": "ICH Q2(R1) (2005)",
        "url": "https://database.ich.org/sites/default/files/ICH_Q2%28R2%29_Guideline_2023_1130.pdf",
        "reproducible": True,
        "scope": (
            "Analytical procedures for release and stability testing of commercial drug "
            "substances and products; applicable to other control-strategy procedures on a "
            "risk basis, and phase-appropriately during clinical development."
        ),
        "governs": ["assay", "potency", "purity", "impurity-quantitative",
                    "impurity-limit", "identity", "dissolution", "content-uniformity"],
        "companion": "ICH Q14 (analytical procedure development, robustness, lifecycle)",
    },
    "ich-m10": {
        "title": "ICH M10 Bioanalytical Method Validation and Study Sample Analysis",
        "adopted": "2022-05-24",
        "effective_note": (
            "Step 4 adopted 24 May 2022. Regional implementation dates differ; confirm with "
            "the regional regulator."
        ),
        "supersedes": (
            "Harmonises region-specific bioanalytical guidance (e.g., FDA 2018 BMV, "
            "EMA 2011); what it replaces depends on the region's implementation"
        ),
        "url": "https://database.ich.org/sites/default/files/M10_Guideline_Step4_2022_0524.pdf",
        "reproducible": True,
        "scope": (
            "Bioanalytical methods quantifying drug/metabolite concentrations in biological "
            "matrices supporting nonclinical and clinical studies, plus study sample analysis."
        ),
        "governs": ["pk-concentration", "toxicokinetics", "bioequivalence"],
        "companion": "Distinct criteria for chromatographic methods vs ligand binding assays",
    },
    "usp-1220": {
        "title": "USP General Chapter <1220> Analytical Procedure Life Cycle",
        "adopted": "official 2022-05-01",
        "effective_note": (
            "Official 1 May 2022 (USP Council of Experts report). "
            "Confirm the current official text and any revision in the USP-NF."
        ),
        "supersedes": "integrates the concepts of <1224>, <1225>, and <1226> into a lifecycle",
        "url": "https://doi.usp.org/USPNF/USPNF_M10975_02_01.html",
        "reproducible": False,
        "scope": (
            "Three-stage lifecycle: procedure design (Stage 1), performance qualification "
            "(Stage 2), ongoing performance verification (Stage 3), organised around an "
            "analytical target profile."
        ),
        "governs": ["compendial-lifecycle"],
        "companion": "<1225> validation, <1226> verification, <1224> transfer, <1010> data treatment",
    },
    "usp-1225": {
        "title": "USP General Chapter <1225> Validation of Compendial Procedures",
        "adopted": "see current USP-NF",
        "effective_note": "The linked 2025 page is a revision proposal, not proof of official status; confirm the effective controlled text in USP-NF.",
        "supersedes": "",
        "url": "https://doi.usp.org/USPNF/USPNF_M99945_40101_01.html",
        "reproducible": False,
        "scope": (
            "Validation of non-compendial procedures and of compendial procedures used "
            "outside their stated scope; Stage 2 activities under <1220>."
        ),
        "governs": ["assay", "impurity-quantitative", "impurity-limit", "identity"],
        "companion": "<1226> when verifying a compendial procedure as written",
    },
    "usp-1226": {
        "title": "USP General Chapter <1226> Verification of Compendial Procedures",
        "adopted": "see current USP-NF",
        "effective_note": "Confirm the current official text and revision in the USP-NF.",
        "supersedes": "",
        "url": "https://doi.usp.org/USPNF/USPNF_M870_03_01.html",
        "reproducible": False,
        "scope": (
            "Assessment of selected performance characteristics to show a compendial "
            "procedure works under actual conditions of use. Verification is not "
            "revalidation and does not repeat the full validation."
        ),
        "governs": ["compendial-verification"],
        "companion": "<1225> when the procedure is used outside its compendial scope",
    },
    "clsi": {
        "title": "CLSI EP series (clinical laboratory measurement procedures)",
        "adopted": "per document",
        "effective_note": (
            "Publisher listings checked 30 Sep 2026; EP05 is fourth edition, other editions "
            "are recorded in references/compendial-and-clsi.md. "
            "Verify the current edition before designing a study."
        ),
        "supersedes": "",
        "url": "https://clsi.org/shop/standards/",
        "reproducible": False,
        "scope": (
            "Establishment and user verification of performance for clinical laboratory "
            "measurement procedures, under CLIA/CAP and ISO 15189 quality systems."
        ),
        "governs": ["clinical-verification", "clinical-establishment"],
        "companion": "ISO 15189 for the surrounding medical laboratory quality system",
    },
    "iso-17025": {
        "title": "ISO/IEC 17025:2017 (testing and calibration laboratory competence)",
        "adopted": "2017",
        "effective_note": "Copyrighted. Obtain an authorised copy from ISO or a national member.",
        "supersedes": "ISO/IEC 17025:2005",
        "url": "https://www.iso.org/standard/66912.html",
        "reproducible": False,
        "scope": (
            "Clause 7.2 covers selection, verification and validation of methods; clause 7.6 "
            "covers measurement uncertainty. Method validation is required to the extent "
            "necessary for the intended use."
        ),
        "governs": ["nonstandard-method", "lab-developed-method", "modified-standard-method"],
        "companion": (
            "The repo's iso-standards-readiness skill covers the surrounding quality system; "
            "this skill covers the individual procedure."
        ),
    },
}

# --------------------------------------------------------------------------
# ICH Q2(R2) Table 1 -- which validation tests for which measured attribute
# Source: ICH Q2(R2), Table 1. "+" normally conducted, "-" not normally conducted.
# --------------------------------------------------------------------------

Q2R2_TESTS_BY_ATTRIBUTE: dict[str, dict[str, str]] = {
    "identity": {
        "specificity": "required",
        "response": "not-normally",
        "lower-range-limit": "not-normally",
        "accuracy": "not-normally",
        "repeatability": "not-normally",
        "intermediate-precision": "not-normally",
    },
    "impurity-quantitative": {
        "specificity": "required",
        "response": "required",
        "lower-range-limit": "required-QL",
        "accuracy": "required",
        "repeatability": "required",
        "intermediate-precision": "required-unless-reproducibility",
    },
    "impurity-limit": {
        "specificity": "required",
        "response": "not-normally",
        "lower-range-limit": "required-DL",
        "accuracy": "not-normally",
        "repeatability": "not-normally",
        "intermediate-precision": "not-normally",
    },
    "assay": {
        "specificity": "required",
        "response": "required",
        "lower-range-limit": "not-normally",
        "accuracy": "required",
        "repeatability": "required",
        "intermediate-precision": "required-unless-reproducibility",
    },
}

ATTRIBUTE_ALIASES = {
    "content": "assay",
    "potency": "assay",
    "assay": "assay",
    "identification": "identity",
    "identity": "identity",
    "id": "identity",
    "impurity": "impurity-quantitative",
    "impurities": "impurity-quantitative",
    "related-substances": "impurity-quantitative",
    "purity": "impurity-quantitative",
    "impurity-quantitative": "impurity-quantitative",
    "impurity-limit": "impurity-limit",
    "limit-test": "impurity-limit",
}

# ICH Q2(R2) Table 2 -- examples of reportable ranges.
Q2R2_REPORTABLE_RANGE: dict[str, dict[str, str]] = {
    "assay": {
        "low": "80% of declared content, or 80% of the lower specification acceptance criterion",
        "high": "120% of declared content, or 120% of the upper specification acceptance criterion",
    },
    "potency": {
        "low": "lowest specification acceptance criterion -20%",
        "high": "highest specification acceptance criterion +20%",
    },
    "content-uniformity": {
        "low": "70% of declared content",
        "high": "130% of declared content",
    },
    "dissolution-ir-one-point": {
        "low": "Q - 45% of the lowest strength specification",
        "high": "130% of declared content of the highest strength",
    },
    "dissolution-ir-multi-point": {
        "low": "lower limit of reportable range as justified by the specification, or QL",
        "high": "130% of declared content of the highest strength",
    },
    "dissolution-modified-release": {
        "low": "lower limit of reportable range as justified by the specification, or QL",
        "high": "130% of declared content of the highest strength",
    },
    "impurity-quantitative": {
        "low": "reporting threshold",
        "high": "120% of the specification acceptance criterion",
    },
    "purity-area-percent": {
        "low": "80% of the lower specification acceptance criterion",
        "high": "upper specification acceptance criterion, or 100%",
    },
}

# ICH Q2(R2) recommended data, section 3.
Q2R2_STUDY_DESIGN: dict[str, dict[str, str]] = {
    "response": {
        "requirement": "minimum of 5 concentrations appropriately distributed across the range",
        "reference": "Q2(R2) 3.2.2.1",
        "report": (
            "plot of the data, correlation coefficient or coefficient of determination, "
            "y-intercept, slope, and an analysis of deviation of points from the line "
            "(residual pattern)"
        ),
    },
    "accuracy": {
        "requirement": (
            "appropriate number of determinations and levels across the reportable range "
            "(e.g., 3 concentrations / 3 replicates each of the full procedure)"
        ),
        "reference": "Q2(R2) 3.3.1.4",
        "report": (
            "mean percent recovery of a known added amount, or difference between mean and "
            "accepted true value, with a 100(1-alpha)% confidence interval"
        ),
    },
    "repeatability": {
        "requirement": (
            "minimum 9 determinations covering the reportable range (e.g., 3 concentrations "
            "/ 3 replicates), or minimum 6 determinations at 100% of the test concentration"
        ),
        "reference": "Q2(R2) 3.3.2.1",
        "report": "standard deviation, relative standard deviation, and a 100(1-alpha)% CI",
    },
    "intermediate-precision": {
        "requirement": (
            "effects of random events -- typically different days, environmental conditions, "
            "analysts, equipment. Studying effects individually is not necessary; DoE is "
            "encouraged. Extent justified by development understanding and risk (ICH Q14)"
        ),
        "reference": "Q2(R2) 3.3.2.2",
        "report": "standard deviation, relative standard deviation, and a 100(1-alpha)% CI",
    },
    "reproducibility": {
        "requirement": (
            "inter-laboratory trial; usually NOT required for a regulatory submission, but "
            "consider for pharmacopoeial standardisation or multi-site procedures"
        ),
        "reference": "Q2(R2) 3.3.2.3",
        "report": "standard deviation, relative standard deviation, and a 100(1-alpha)% CI",
    },
    "specificity": {
        "requirement": (
            "absence of interference, orthogonal procedure comparison, or technology-inherent "
            "justification. For a stability-indicating claim, include samples containing "
            "relevant degradation products (spiked, stressed, or aged)"
        ),
        "reference": "Q2(R2) 3.1, 2.4",
        "report": "interference data, resolution/peak purity, or orthogonal comparison",
    },
    "lower-range-limit": {
        "requirement": (
            "DL/QL by visual evaluation, signal-to-noise, standard deviation of the response "
            "and slope, or direct accuracy and precision at the lower limit. An estimated "
            "limit should then be confirmed with samples at or near that limit"
        ),
        "reference": "Q2(R2) 3.2.3",
        "report": "the limit and the approach used to determine it",
    },
    "robustness": {
        "requirement": (
            "deliberate variation of procedure parameters plus solution stability. Normally "
            "performed during development under ICH Q14; submitted case-by-case or available "
            "on request"
        ),
        "reference": "Q2(R2) 3.4, ICH Q14 section 5",
        "report": "parameters varied, ranges, and the effect on the reportable result",
    },
}

# ICH Q2(R2) 3.2.3.2/3.2.3.3 -- the estimation approaches and their constants.
DL_QL_APPROACHES = {
    "visual": {
        "dl": "lowest level reliably detected by analysis of known concentrations",
        "ql": "lowest level reliably quantitated by analysis of known concentrations",
        "note": "acceptable for both non-instrumental and instrumental procedures",
    },
    "signal-to-noise": {
        "dl": "S/N of 3:1 generally acceptable",
        "ql": "S/N of at least 10:1 acceptable",
        "note": "only for procedures exhibiting baseline noise; define the noise region",
    },
    "sd-and-slope": {
        "dl": "DL = 3.3 * sigma / S",
        "ql": "QL = 10 * sigma / S",
        "note": (
            "sigma from the SD of blank responses, the residual SD of the regression line, "
            "or the SD of y-intercepts of regression lines; S is the calibration slope"
        ),
    },
    "accuracy-precision": {
        "dl": "not applicable",
        "ql": "QL validated directly by accuracy and precision at the lower range limit",
        "note": "avoids relying on an estimate; Q2(R2) 3.2.3.4",
    },
}

# --------------------------------------------------------------------------
# ICH M10 acceptance criteria. Verified against the Step 4 guideline text.
# Chromatographic (CC) and ligand binding assay (LBA) criteria differ and are
# the single most commonly conflated pair in bioanalysis.
# --------------------------------------------------------------------------

M10_CRITERIA: dict[str, dict[str, Any]] = {
    "chromatographic": {
        "label": "Chromatographic assays (ICH M10 section 3)",
        "calibration_min_levels": 6,
        "calibration_tolerance_pct": 15.0,
        "calibration_tolerance_lloq_pct": 20.0,
        "calibration_tolerance_uloq_pct": 15.0,
        "calibration_min_pass_fraction": 0.75,
        "accuracy_tolerance_pct": 15.0,
        "accuracy_tolerance_lloq_pct": 20.0,
        "precision_cv_pct": 15.0,
        "precision_cv_lloq_pct": 20.0,
        "limit_levels": "LLOQ",
        "qc_levels_accuracy_precision": 4,
        "qc_levels_routine_run": 3,
        "ap_replicates_per_run": 5,
        "ap_min_runs": 3,
        "ap_min_days": 2,
        "qc_run_pass_fraction": 2.0 / 3.0,
        "qc_run_pass_fraction_per_level": 0.50,
        "qc_run_tolerance_pct": 15.0,
        "total_error_pct": None,
        "total_error_pct_at_limits": None,
        "isr_tolerance_pct": 20.0,
        "isr_pass_fraction": 2.0 / 3.0,
        "carryover_blank_pct_of_lloq": 20.0,
        "carryover_blank_pct_of_is": 5.0,
        "selectivity_min_sources": 6,
        "dilution_tolerance_pct": 15.0,
        "stability_tolerance_pct": 15.0,
        "notes": (
            "Accuracy/precision validation QCs at a minimum of 4 levels: LLOQ, low QC within "
            "3x the LLOQ, medium QC around 30-50% of the calibration range, and high QC at "
            "least 75% of the ULOQ. Within-run uses at least 5 replicates per level per run; "
            "between-run uses each level in at least 3 runs over at least 2 days. Routine "
            "(non-accuracy-and-precision) runs may use low, medium and high QCs in duplicate. "
            "M10 states no explicit total-error criterion for chromatographic assays."
        ),
    },
    "lba": {
        "label": "Ligand binding assays (ICH M10 section 4)",
        "calibration_min_levels": 6,
        "calibration_tolerance_pct": 20.0,
        "calibration_tolerance_lloq_pct": 25.0,
        "calibration_tolerance_uloq_pct": 25.0,
        "calibration_min_pass_fraction": 0.75,
        "accuracy_tolerance_pct": 20.0,
        "accuracy_tolerance_lloq_pct": 25.0,
        "precision_cv_pct": 20.0,
        "precision_cv_lloq_pct": 25.0,
        "limit_levels": "LLOQ and ULOQ",
        "qc_levels_accuracy_precision": 5,
        "qc_levels_routine_run": 3,
        "ap_replicates_per_run": 3,
        "ap_min_runs": 6,
        "ap_min_days": 2,
        "qc_run_pass_fraction": 2.0 / 3.0,
        "qc_run_pass_fraction_per_level": 0.50,
        "qc_run_tolerance_pct": 20.0,
        "total_error_pct": 30.0,
        "total_error_pct_at_limits": 40.0,
        "isr_tolerance_pct": 30.0,
        "isr_pass_fraction": 2.0 / 3.0,
        "carryover_blank_pct_of_lloq": None,
        "carryover_blank_pct_of_is": None,
        "selectivity_min_sources": 10,
        "dilution_tolerance_pct": 20.0,
        "stability_tolerance_pct": 20.0,
        "notes": (
            "Anchor points outside the quantitation range are excluded from the calibration "
            "pass count. Accuracy and precision are evaluated at 5 QC levels (LLOQ, low, "
            "medium (geometric mean of the range), high, ULOQ) with at least 3 replicates per level per run in at least 6 "
            "runs over 2 or more days. LBAs carry an additional total-error criterion: the "
            "sum of absolute bias (%) and precision CV (%) must not exceed 30%, or 40% at "
            "the LLOQ and ULOQ. Chromatographic assays have no such criterion."
        ),
    },
}

# --------------------------------------------------------------------------
# Technique notes distilled from ICH Q2(R2) Annex 2 (illustrative, not mandatory)
# --------------------------------------------------------------------------

TECHNIQUE_NOTES: dict[str, dict[str, str]] = {
    "hplc": {
        "annex_table": "Table 3 (quantitative separation techniques)",
        "robustness": (
            "extraction volume/time/temperature, dilution, column or capillary lot, mobile "
            "phase and buffer composition and pH, column temperature, flow rate, detection "
            "wavelength; plus stability of sample and reference preparations"
        ),
        "special": (
            "Relative response factors: if the RRF falls outside 0.8-1.2, apply a correction "
            "factor. If an impurity is overestimated it may be acceptable to omit the "
            "correction. Determine RRF under final procedure conditions and document it."
        ),
    },
    "gc": {"annex_table": "Table 3 (quantitative separation techniques)",
           "robustness": "as for HPLC, plus inlet temperature, split ratio, carrier flow, oven ramp",
           "special": "same relative response factor 0.8-1.2 consideration as HPLC"},
    "ce": {"annex_table": "Table 3 (quantitative separation techniques)",
           "robustness": "capillary lot, buffer composition and pH, capillary temperature, voltage",
           "special": "same relative response factor consideration as HPLC"},
    "icp": {"annex_table": "Table 4 (elemental impurities by ICP-OES or ICP-MS)",
            "robustness": "plasma conditions, sample introduction, internal standard, matrix matching",
            "special": "spectral and non-spectral interference; ICH Q3D drives which elements matter"},
    "dissolution": {"annex_table": "Table 5 (dissolution with HPLC as product performance test)",
                    "robustness": "medium composition and volume, deaeration, agitation, sinker, filter",
                    "special": (
                        "Table 5 was corrected on 30 Nov 2023 (reportable range linearity "
                        "formulae). Use the corrected text."
                    )},
    "qnmr": {"annex_table": "Table 6 (quantitative 1H-NMR for assay of a drug substance)",
             "robustness": "pulse angle, relaxation delay, number of scans, temperature, shimming",
             "special": "internal standard purity and signal selection dominate accuracy"},
    "bioassay": {"annex_table": "Table 7 (biological assays)",
                 "robustness": "cell passage, incubation time and temperature, reagent lot, plate layout",
                 "special": (
                     "Non-linear (4- or 5-parameter logistic) response is expected. Linearity "
                     "of the concentration-response relationship is NOT required; evaluate "
                     "proportionality of results to expected values instead."
                 )},
    "qpcr": {"annex_table": "Table 8 (quantitative PCR)",
             "robustness": "primer/probe lot, master mix, cycling parameters, template input",
             "special": "amplification efficiency and specificity of amplicon detection"},
    "particle-size": {"annex_table": "Table 9 (particle size measurement)",
                      "robustness": "dispersion medium, sonication, pump speed, obscuration",
                      "special": "technology-inherent justification may substitute for some characteristics"},
    "nir": {"annex_table": "Table 10 (NIR analytical procedure)",
            "robustness": "instrument, probe, sample presentation, temperature, humidity",
            "special": (
                "Multivariate: validate in two phases (calibration plus internal testing, "
                "then an independent validation set). Report RMSEP against RMSEC. Reference "
                "procedure performance must equal or exceed the multivariate procedure's."
            )},
    "lcms": {"annex_table": "Table 11 (quantitative LC/MS)",
             "robustness": "source conditions, mobile phase additives, column lot, matrix lots",
             "special": (
                 "Matrix effects and ion suppression need explicit evaluation. For a "
                 "bioanalytical purpose, ICH M10 governs instead of Q2(R2)."
             )},
}


def resolve_attribute(name: str) -> str:
    key = name.strip().lower().replace("_", "-")
    if key in ATTRIBUTE_ALIASES:
        return ATTRIBUTE_ALIASES[key]
    raise KeyError(
        f"unknown attribute {name!r}; choose from: {', '.join(sorted(set(ATTRIBUTE_ALIASES)))}"
    )
