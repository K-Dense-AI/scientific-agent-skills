# DepMap dependency analysis contracts

## Release and score provenance

Pin the release, filenames, checksums, README, and cohort/filter rules. A portal
view can use a newer release or a different condition than a saved matrix.
Use the release citation from the dataset entry, alongside the method paper.
Do not transfer the license of this skill to downloaded data.

The [public metadata route](https://depmap.org/portal/api/no-captcha/download/files)
returns one complete CSV, not JSON or a paginated dataset API. As of 2026-09-30 it
contained 1,436 rows. The `url` column was populated for some older resources but
empty for all 26Q1 and 25Q3 release entries. A blank URL does not mean the dataset
is absent: use [portal downloads](https://depmap.org/portal/data_page/) to obtain
protected release files. The original catalogue route may return HTML with HTTP
200; never save that response as a successful matrix download.

The [July 2026 access announcement](https://forum.depmap.org/t/provide-an-open-endpoint-for-latest-version-retrieval/4652)
described bearer-token access as future work. Do not invent authentication headers
or attempt to bypass verification. A direct signed URL obtained through authorized
portal access can expire; retrieve a fresh one when needed.

Chronos normalization sets global control reference levels near 0 (nonessential)
and −1 (common-essential). It is not a universal per-cell cutoff. Prefer the
release-matched `AchillesCommonEssentialControls.csv` and
`AchillesNonessentialControls.csv` over ad hoc lists of ribosomal or unexpressed
genes. Unexpressed genes and safe-harbor loci are not interchangeable controls.
Do not apply universal rules such as “skewness < −1 and AUC > 0.85” to screen QC;
use the release's reported metrics, flags, and eligibility definition.

There is a documentation ambiguity worth resolving for any binary hit call:
[DepMap staff describes CRISPRGeneDependency as dependency probability](https://forum.depmap.org/t/meaning-of-efficacy-column-in-crisprinferredguideefficacy-csv-a-few-other-questions/3473),
while the [Chronos README](https://github.com/broadinstitute/chronos) describes
publishing `fdr_from_probabilities` under that filename. These have opposite
cutoff directions. The current protected release README/data were not fetched
for this review. Inspect that release's definition and controls before thresholding;
do not infer probability versus FDR from values lying in [0, 1]. The local helpers
analyze gene effect and do not choose a dependency-statistic cutoff.

## Correct unit of observation

A model is not a screen or sequencing library. Model metadata include
`ModelID`, `CellLineName`, `OncotreeLineage`, and `OncotreePrimaryDisease`.
Patient-related models, replicate screens, and multiple growth conditions can
violate independence assumptions. Record which unit is being compared.

Current omics files may have multiple `SequencingID` rows per model. After
choosing an assay, select the appropriate default flag and check uniqueness:

```python
import pandas as pd
from scripts.depmap_data import default_model_rows

# Illustrative until the selected release's headers and values are inspected.
raw = pd.read_csv("OmicsExpressionTPMLogp1HumanProteinCodingGenes.csv")
print(raw.columns[:10].tolist())
expression_by_model = default_model_rows(raw, flag="IsDefaultEntryForModel")
# Select gene columns using Gene.csv / the release schema before calculations;
# SequencingID, ModelConditionID and default flags are not expression measurements.
```

For a condition-specific analysis, select `IsDefaultEntryForMC` and use
`ModelConditionID` as the observation key instead; the model-level helper is
intentionally inappropriate. A unique default per model does not make different
assays interchangeable. See [current mapping guidance](https://github.com/broadinstitute/depmap-portal/blob/master/frontend/packages/portal-frontend/src/dataPage/components/MapSection.tsx)
and [why multiple sequences exist](https://forum.depmap.org/t/multiple-omics-expression-profiles/4585).

Use explicit mappings from `ScreenSequenceMap.csv`, `CRISPRScreenMap.csv`,
`ModelCondition.csv`, and `OmicsProfiles.csv`. Never recover ModelID by casually
splitting every identifier: naming conventions vary between files. In 26Q1,
`CRISPRInferredModelEfficacy.csv` is a documented exception whose misleading
`ModelID` column actually contains composite replicate-sequence identifiers.
[Staff provides its parsing contract](https://forum.depmap.org/t/how-should-crisprinferredmodelefficacy-csv-identifiers-be-mapped-in-depmap-public-26q1/4653);
consult that explanation if using this QC output. It is not the effect matrix.

## Mutation and copy-number contrasts

A `1` in the damaging mutation matrix identifies that annotation class, not
confirmed biallelic gene loss. A `0` is not necessarily “wild type” for every
possible alteration: hotspots, fusions, copy-number changes, regulatory changes,
and assay coverage need separate consideration. Missing/untested calls remain
missing. The helper deliberately excludes them from both comparison groups.

For synthetic-lethality hypotheses, define loss of function using the scientific
question and supporting annotation (allele, zygosity/LOH, transcript consequence,
expression, copy number). Predefine which models are eligible. Stratification or
covariate adjustment is required where mutation status tracks lineage, library,
culture conditions, or related patients. Report the unfiltered tested family as
well as the selected candidates; an empty eligible family is a valid result.

The 25Q2 pipeline separated WGS and WES copy-number outputs because the new WGS
method is not compatible with the WES method. In 26Q1,
`OmicsCNGeneWGS.csv` gives **linear copy number relative to model ploidy**: about 1
can represent an unaltered locus in either a diploid or tetraploid model. It is
not absolute two-copy dosage. Inspect transforms for portal log products before
inverting them, and do not label a universal ratio cutoff as homozygous loss.
Sources: [25Q2 changes](https://forum.depmap.org/t/announcing-the-25q2-release/4257),
[26Q1 normalization clarification](https://forum.depmap.org/t/26q1-omicscngenewgs-csv-normalization/4656).

## Co-essentiality

Use pairwise nonmissing measurements and report `n` for every correlation. The
bundled helper rejects duplicate observation IDs, skips constant vectors, and
applies BH correction across all eligible correlations to the chosen target.
This corrects the stated family only; scanning many target genes requires a
broader prespecified family. Different pairs may use different model sets, so
check rankings on a common cohort and across lineage/library strata.

The example minimum of 500 models is a conservative configurable analysis choice,
not a claim that every portal dataset has that coverage or that the portal's
current implementation uses that threshold. [DepMap staff](https://forum.depmap.org/t/crispr-co-depency-top-hits-obscured-by-newly-added-screens/4503)
has documented sparse single-library genes producing misleading top correlations.
A small p-value cannot remove shared lineage or technical confounding.

## PRISM response versus annotation

For the **original** [PRISM Repurposing resource](https://depmap.org/repurposing/):

| Input | Role and keys |
|---|---|
| `primary-screen-replicate-collapsed-logfold-change.csv` | Numeric log2 response; row IDs match `row_name`, columns match `column_name` |
| `primary-screen-cell-line-info.csv` | `row_name` to `depmap_id`; includes STR identity/QC annotations |
| `primary-screen-replicate-collapsed-treatment-info.csv` | `column_name` to `broad_id`, compound name, dose in µM, and `screen_id` |
| `secondary-screen-dose-response-curve-parameters.csv` | Long table keyed by compound/model/screen, with `auc`, `ic50`, `ec50`, `convergence`, and `r2` |

Matrix columns identify experimental conditions, not simply compound names.
Do not split a guessed `broad_id::name::dose` format; join treatment metadata.
Check axis overlap and mapping uniqueness before merging. Handle replicate or
screen duplicates with an explicit policy and retain dose. Use STR-QC annotations
and the corrected model identity where supplied.

A minimal axis check (illustrative with your downloaded original-primary files):

```python
import pandas as pd

response = pd.read_csv("primary-screen-replicate-collapsed-logfold-change.csv", index_col=0)
cells = pd.read_csv("primary-screen-cell-line-info.csv").set_index("row_name")
treatments = pd.read_csv("primary-screen-replicate-collapsed-treatment-info.csv").set_index("column_name")
if not cells.index.is_unique or not treatments.index.is_unique:
    raise ValueError("Duplicate PRISM metadata identifiers")
if not response.index.is_unique or not response.columns.is_unique:
    raise ValueError("Duplicate PRISM matrix identifiers")
if len(response.index.difference(cells.index)) or len(response.columns.difference(treatments.index)):
    raise ValueError("PRISM axes do not match the selected metadata files")
# Keep response numeric; join cells/treatments only after selecting the question.
```

Lower primary log2 fold change means greater growth suppression relative to
controls. For secondary AUC, examine curve-fit convergence, coverage of the
concentration range, and fit quality; compare like endpoints and doses. IC50 can
be unidentifiable or beyond the assayed range. Avoid treating nonconverged/missing
fits as resistance. A compound's annotated target does not prove that target
mediates the response.

The original secondary screen tested 1,448 compounds in an eight-dose series;
the previous “~8,000 compounds” claim was incorrect. Later PRISM releases have
different sample sizes and structures. The original landing page and secondary
README disagree on cell-line counts, so derive counts after documented QC from
the chosen files rather than copying a global count. Consult the
[primary README](https://ndownloader.figshare.com/files/20237700) and
[secondary README](https://ndownloader.figshare.com/files/20238123) for their
specific processing and technical-redo rules.
