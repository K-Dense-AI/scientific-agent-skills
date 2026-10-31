# ICH M10 — Bioanalytical Criteria, by Modality

Research basis: **2026-09-30**, read from the ICH Harmonised Guideline *Bioanalytical Method
Validation and Study Sample Analysis M10*, Step 4 dated 24 May 2022. ICH licenses its documents for
reuse with acknowledgement. Confirm the current text and your region's implementation at
<https://database.ich.org/sites/default/files/M10_Guideline_Step4_2022_0524.pdf>.

M10 harmonised what had been separate FDA and EMA bioanalytical guidance for studies in its scope:
methods quantifying drug and metabolite concentrations in biological matrices supporting nonclinical
and clinical studies, plus the analysis of study samples.

## The distinction that matters most

**Chromatographic assays (section 3) and ligand binding assays (section 4) have different numeric
criteria throughout.** They are not stylistic variants of one set. Applying chromatographic
tolerances to an LBA is the most common error in this area, and importing the LBA total-error
criterion into a chromatographic method is its mirror image.

| | Chromatographic | Ligand binding assay |
| --- | --- | --- |
| Calibration levels (minimum) | 6, including LLOQ and ULOQ | 6, including LLOQ and ULOQ |
| Calibration standard tolerance | ±15% | ±20% |
| … at LLOQ | ±20% | ±25% |
| … at ULOQ | ±15% | ±25% |
| Calibration standards that must pass | ≥75%, and ≥6 passing levels | ≥75%, and ≥6 passing levels; exclude anchors |
| Accuracy | ±15% | ±20% |
| … at limits | ±20% at LLOQ | ±25% at LLOQ **and** ULOQ |
| Precision (%CV) | ≤15% | ≤20% |
| … at limits | ≤20% at LLOQ | ≤25% at LLOQ **and** ULOQ |
| A&P QC levels | minimum 4 | 5 (LLOQ, low, medium, high, ULOQ) |
| A&P replicates per level per run | ≥5 (within-run) | ≥3 |
| A&P runs | ≥3 runs over ≥2 days | ≥6 runs over ≥2 days |
| **Total error** | **no such criterion** | **≤30%; ≤40% at LLOQ and ULOQ** |
| Routine run QC tolerance | ±15% | ±20% |
| Routine run QC pass rule | ≥2/3 of all QCs **and** ≥50% at each level | same rule, ±20% |
| Dilution integrity | mean within ±15% | mean within ±20% |
| Stability | mean at each QC level within ±15% | mean within ±20% |
| ISR agreement | within ±20% for ≥2/3 of repeats | within ±30% for ≥2/3 of repeats |
| Selectivity sources/lots | ≥6 individual sources | ≥10 individual sources |
| Carry-over in blank | ≤20% of LLOQ analyte response and ≤5% of IS response | below LLOQ if platform is prone to carry-over |

Verify any figure against the guideline before using it in a protocol; regional implementation and
subsequent revisions can change the picture.

## Chromatographic QC placement (section 3)

Accuracy and precision validation QCs at a minimum of **four** concentration levels:

- the **LLOQ**
- **low QC** — within three times the LLOQ
- **medium QC** — around 30–50% of the calibration curve range
- **high QC** — at least 75% of the ULOQ

For runs that are not accuracy-and-precision runs, low, medium and high QCs may be analysed in
duplicate; these plus the calibration standards form the basis for accepting or rejecting the run.

Calibration standards and QCs should be prepared from **separate stock solutions**, to avoid a bias
that is not a property of the analytical performance. If a single stock must serve both, verify the
accuracy and stability of that stock. A single source of blank matrix may be used if it is free of
interference and matrix effects.

Calibration curves for accuracy and precision assessment should use freshly spiked standards in at
least one run; if other runs use frozen standards, demonstrate their stability.

## Reporting obligations that catch people out

**Report everything.** Validation data and the determination of accuracy and precision must include
*all* results obtained, including individual QCs outside the acceptance criteria — except cases where
errors are obvious and documented. Silently dropping an out-of-criteria QC is a data integrity
problem, not a rounding decision.

**Within-run accuracy and precision are reported per run.** If the within-run criteria are not met in
every run, calculate an overall estimate of within-run accuracy and precision for each QC level.
Between-run (intermediate) accuracy and precision combine data from all runs.

**Trend within a run.** It is recommended to demonstrate accuracy and precision over at least one run
sized like a prospective study-sample run, so time-dependent drift is visible.

## Incurred sample reanalysis (section 5)

ISR repeats the analysis of a subset of study samples in separate runs, to verify that measured
concentrations in real samples are reproducible. It is not a substitute for QCs — QCs are spiked,
incurred samples are not, and only incurred samples can reveal metabolite back-conversion, protein
binding effects, or matrix instability.

- The minimum is 10% of samples for studies with up to 1,000 samples; above 1,000,
  reanalyse 100 plus 5% of the additional samples. Justify the selection and retain identifiers.
- Objective criteria for choosing the subset should be **predefined**; selecting samples around
  Cmax and the elimination phase is recommended.
- **Do not pool samples** — pooling masks anomalous findings.
- ISR samples and QCs are processed and analysed in the same manner as the original analysis.
- Percent difference is `(repeat value - initial value) / mean value x 100` -- assessed
  against the **mean of the two**, not against the initial value.
- Repeats are performed within the analyte's stability window, but **not on the same day**
  as the original analysis.
- Acceptance: within ±20% for at least 2/3 of repeats (chromatographic), or within ±30% for at least
  2/3 (LBA).

For nonclinical studies in scope, ISR should generally be performed at least once per species.
Section 5 also identifies pivotal BA/BE studies, first clinical trials in subjects, relevant pivotal
patient trials, and first or pivotal trials in hepatic/renal impairment. The "if available" condition
for study samples in cross validation (section 6.2) is not a general ISR exemption. ISR results do
not replace original study results; passing the aggregate fraction does not rule out systematic bias.

## Study sample reanalysis is a separate thing

ISR is a method-reliability check. *Reanalysis of study samples* for a reportable-value decision is
different, and the reasons for reanalysis, the number of replicates, and the criteria for selecting
the value to report must be **predefined in the protocol, study plan, or SOP before study sample
analysis begins.** Deciding after the fact which of two values to report is the classic finding.

## Partial and cross validation

M10 addresses partial validation (a change to a validated method — matrix, anticoagulant, species,
instrument, or a range change) and cross validation (comparing data from two methods or two
laboratories contributing to the same study). Both are scoped by the change and the risk; consult
the guideline for what each requires. Section 6.2 calls for the same low/medium/high QCs in at least triplicate and, if available,
at least 30 study samples spanning the range measured with both methods/laboratories. It names
Bland–Altman or Deming as options for bias assessment and allows other appropriate approaches.
TOST in `compare_methods.py` is an optional mean-bias analysis, not an M10-mandated test or a
replacement for that experimental design.

## Biomarkers and other contexts

M10's scope centres on drug and metabolite concentration measurement. Biomarker assays, immunogenicity
assays, and diagnostic measurements are addressed differently or fall outside scope; do not assume the
concentration-assay criteria transfer. Where a biomarker assay supports a regulatory decision, the
fit-for-purpose framework and the applicable regional guidance govern the extent of validation.

## Scope of the bundled checker

`check_bioanalytical_run.py --run` screens one run's reportable calibrator/QC results. It does not
fit a curve, aggregate wells, audit blanks or internal-standard response, verify sample handling,
check QC placement/5% study-size counts, or apply multi-plate and multi-batch acceptance rules.
LLOQ and ULOQ labels are mandatory; after range narrowing retain each calibrator's original
boundary tolerance and review the revised range separately. A rejected point needs a new fit and
re-evaluation; do not merely remove its row until the script exits zero. QC levels are grouped by
nominal concentration, so relabelling one level cannot manufacture three levels.

For `--total-error`, `accuracy_pct` means signed **bias from nominal** (for example 5 for 105%
recovery), and `precision_pct` is non-negative CV. The checker evaluates supplied summaries; it
does not establish whether all validation runs, days and levels support those summaries.
LBA medium QC is near the geometric mean of the range, unlike the chromatographic 30–50% placement.
