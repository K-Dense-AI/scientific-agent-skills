---
name: depmap
description: Retrieves and analyzes Cancer Dependency Map (DepMap) release data, including CRISPR Chronos gene effects, cancer model annotations, omics biomarkers, and PRISM drug sensitivity. Supports cancer-selective dependency, co-essentiality, and candidate synthetic-lethality analyses with release-aware identifiers and statistical checks.
license: CC-BY-4.0
compatibility: Requires Python 3.10+ with numpy, pandas, and scipy>=1.11 for the bundled helpers. Network access is needed for release discovery; downloading current data may require browser verification through the DepMap portal.
metadata:
  version: "1.2"
  skill-author: Kuan-lin Huang
  last-reviewed: "2026-09-30"
---

# DepMap — Cancer Dependency Map

## When to use

Use this skill to rank dependencies in cancer models, compare prespecified biomarker
cohorts, inspect co-essentiality, or relate genetic dependencies to PRISM compound
response. These analyses generate target and synthetic-lethality hypotheses; they
do not establish clinical efficacy, a therapeutic window, or a causal interaction.

DepMap integrates Broad and Sanger CRISPR screens and hosts independent RNAi and
drug-screen datasets. Match each question to its assay and pinned release. RNAi
DEMETER2 is a different perturbation modality, not an older CRISPR scoring method.

## 1. Discover a release, then obtain its files

Use [DepMap Downloads](https://depmap.org/portal/data_page/) and the selected
release's README and release notes. On review, the live catalogue's latest
`DepMap Public` release was **26Q1**, dated 2026-04-01. Rediscover before new work;
a release name or expected quarter is not evidence a release is available.

### Verified public endpoint

`GET https://depmap.org/portal/api/no-captcha/download/files` returns a complete
CSV catalogue, with no request body, API key, or pagination parameters. Required
metadata columns are `release`, `release_date`, `filename`, and `md5_hash`.
The live response also has `url`: **older files can have links, while recent
release rows have blank links**. All 85 entries for 26Q1 had blank `url` values at
review. Treat availability per row, not per endpoint.

The [staff announcement](https://forum.depmap.org/t/provide-an-open-endpoint-for-latest-version-retrieval/4652)
introduced this metadata route in July 2026. The older
`https://depmap.org/portal/api/download/files` catalogue can supply download links
but returned an HTML verification page during review, including with HTTP 200.
Validate content before parsing. Obtain current files through the portal when
verification is required. Refresh expiring signed links immediately before use;
do not fabricate storage URLs or assume every new release is on Figshare.

No supported contract was verified for the former `/api/gene?gene_id=...` or
`/api/data/gene_dependency` examples. Use local release matrices for gene slices.
Do not assume a Python package named `depmap` is an official portal client.

From the skill root, use the bundled [helpers](scripts/depmap_data.py):

```python
from scripts.depmap_data import fetch_catalogue, select_file, verify_md5

catalogue = fetch_catalogue()
public = catalogue[catalogue["release"].str.startswith("DepMap Public ")]
print(public[["release", "release_date"]].drop_duplicates()
      .sort_values("release_date", ascending=False).head(12))

# Explicit example pin; inspect discovery output before selecting your release.
release = "DepMap Public 26Q1"
record = select_file(catalogue, release, "CRISPRGeneEffect.csv")
print(record[["release", "filename", "md5_hash"]])
# After obtaining this file from the portal:
# verify_md5("CRISPRGeneEffect.csv", record["md5_hash"])
```

Save the selected metadata, retrieval date, release citation, local checksum, and
README alongside analysis outputs. Record source dataset terms separately from
this skill's license; newer release terms differ from older Figshare releases.
For a missing published checksum, retain a local SHA-256 and explicitly state
that it was not compared with a publisher checksum.

## 2. Inspect file contracts before joining

The following names were verified in the 26Q1 catalogue. Check that release's
README for units and identifier level before treating a file as a numeric matrix.

| File | Use and important contract |
|---|---|
| `CRISPRGeneEffect.csv` | Integrated, model-level Chronos effects; rows are ModelID, columns preserve `Symbol (EntrezID)` |
| `CRISPRGeneEffectUncorrected.csv` | Uncorrected effects; not interchangeable with corrected effects |
| `CRISPRGeneDependency.csv` | Release-specific dependency statistics; confirm probability/FDR definition and direction in the README |
| `Model.csv` | Model metadata keyed by `ModelID` |
| `ModelCondition.csv` | Growth/treatment conditions keyed by `ModelConditionID`, mapping to `ModelID` |
| `ScreenGeneEffect.csv`, `ScreenSequenceMap.csv`, `CRISPRScreenMap.csv` | Screen-level effects and mappings; multiple screens can belong to one model |
| `OmicsExpressionTPMLogp1HumanProteinCodingGenes.csv` | Expression output with sequencing/model metadata and default-entry flags; exclude metadata columns from expression calculations |
| `OmicsSomaticMutationsMatrixDamaging.csv`, `OmicsSomaticMutationsMatrixHotspot.csv` | Distinct mutation annotations; damaging and hotspot calls answer different biological questions |
| `OmicsCNGeneWGS.csv`, `OmicsCNGeneMC_WES.csv` | Separate WGS/WES copy-number products; do not concatenate as one uniformly processed cohort |
| `PortalOmicsCNGeneLog2.csv` | Transformed portal copy-number product; establish the exact transform before inversion |
| `OmicsProfiles.csv`, `Gene.csv` | Omics provenance/mappings and gene annotations |
| `AchillesScreenQCReport.csv`, `AchillesSequenceQCReport.csv` | Screen/sequence QC; apply documented eligibility rules rather than invented universal cutoffs |

Current model annotations include `CellLineName`, `OncotreeLineage`,
`OncotreePrimaryDisease`, and `OncotreeSubtype`. Legacy `sample_info.csv` fields
(`DepMap_ID`, `lineage`, `primary_disease`) require an explicit conversion.
`Model.csv` includes models without CRISPR measurements: absence from the effect
matrix is not a nondependency score.

Omics may be indexed by `SequencingID`, `ModelConditionID`, or `ModelID`. For a
basal model analysis, use the release's `IsDefaultEntryForModel == Yes` flag,
then require one row per `ModelID`. The condition-level flag
`IsDefaultEntryForMC` answers a different question. Subset the assay/datatype
before selecting defaults from a mapping table. Never average repeated conditions
or count them as independent models without an explicit scientific design.

See the [mapping guide source](https://github.com/broadinstitute/depmap-portal/blob/master/frontend/packages/portal-frontend/src/dataPage/components/MapSection.tsx)
and [metadata definitions](https://forum.depmap.org/t/depmap-metadata/3694).

## 3. Interpret Chronos and inspect a target

Chronos gene effect is continuous and unbounded. More negative values indicate
stronger loss of fitness. In the normalized release matrix, approximately 0 is
the nonessential-control anchor and −1 is the common-essential-control anchor;
−1 is not a dependency boundary. A filter such as ≤ −0.5 is exploratory, not a
p-value, FDR, or probability cutoff. Positive effects may reflect growth advantage
or technical noise and need validation.

For binary calls, inspect the selected file's statistic and direction. A high
dependency probability and a low FDR are different rules. Do not silently convert
between them. Use release-matched positive/negative control lists and QC outputs.
See [score and QC caveats](references/dependency_analysis.md).

The following local-data examples are illustrative until run against your chosen
files. Helper behavior is tested using synthetic fixtures; current bulk matrices
were not downloaded during this review.

```python
from scripts.depmap_data import load_gene_effect, load_models, gene_profile

effects = load_gene_effect("CRISPRGeneEffect.csv")
models = load_models("Model.csv")
profile = gene_profile(effects, models, "KRAS (3845)")
print(profile[["CellLineName", "OncotreeLineage", "gene_effect"]].head(20))

# Inspect actual annotation values, then choose an exact cohort.
print(profile["OncotreeLineage"].value_counts())
known = profile.dropna(subset=["OncotreeLineage"])
lung = known.loc[known["OncotreeLineage"].eq("Lung"), "gene_effect"]
other = known.loc[~known["OncotreeLineage"].eq("Lung"), "gene_effect"]
if lung.empty or other.empty:
    raise ValueError("Both cohorts require observed effects and known lineage")
print({"n_lung": len(lung), "n_other": len(other),
       "other_minus_lung_mean": other.mean() - lung.mean(),
       "lung_fraction_below_exploratory_cutoff": (lung <= -0.5).mean()})
```

This is a descriptive comparison against other cancer models, not against normal
tissue. Keep the denominator and missingness counts. Preserve complete gene labels;
a symbol can be ambiguous, and the helper refuses ambiguous symbol resolution.

## 4. Test biomarker associations

1. Define the alteration before inspecting target scores. A damaging-call matrix
   does not establish biallelic loss; activating KRAS hotspots require a different
   definition from generic damaging mutations.
2. Map profiles to the correct model/condition. Use `0` only for an assayed negative,
   `1` for the prespecified biomarker, and missing for unknown status.
3. Restrict to scientifically comparable models (lineage, culture conditions,
   screen source and related-patient structure). Inspect confounding before testing.
4. Test every eligible gene in the planned family, then adjust all its p-values
   before selecting hits. Report group sizes, effect sizes, p-values, and q-values.
5. Validate candidate synthetic lethality with matched/isogenic perturbations and
   rescue or orthogonal evidence; association alone is insufficient.

```python
import pandas as pd
from scripts.depmap_data import biomarker_scan

# User-prepared, release-matched annotation after the mapping and curation above.
status = pd.read_csv("curated_biomarker_status.csv", index_col="ModelID")["status"]
results = biomarker_scan(effects, status, min_n=5)
# Positive effect_size means stronger dependency in biomarker-positive models.
candidates = results.loc[(results["qval"] < 0.1) & (results["effect_size"] > 0)]
```

This one-sided Mann–Whitney screen is exploratory and does not adjust for
covariates. `min_n=5` is an explicit example floor, not a power guarantee. For
inference across lineages, fit an appropriate adjusted model and inspect effect
stability within lineages; do not report the helper's q-value as confounder-adjusted.

## 5. Co-essentiality and drug sensitivity

```python
from scripts.depmap_data import coessentiality

correlates = coessentiality(effects, "KRAS (3845)", min_n=500)
print(correlates[["gene", "n", "r", "pval", "qval"]].head(20))
```

`min_n` is configurable and should be prespecified for the analysis. Sparse genes
can dominate rankings with spurious correlations; always retain the pairwise
sample count. The helper uses pairwise complete observations and skips constant
genes. Pearson/BH output still needs lineage, library, and screen-quality checks;
co-essentiality is not proof of a physical interaction or shared pathway.
The [DepMap team's discussion](https://forum.depmap.org/t/crispr-co-depency-top-hits-obscured-by-newly-added-screens/4503)
documents this specific sparse-coverage failure mode.

For PRISM, first select the exact screen/release and endpoint. Treatment-info CSVs
are annotations, not sensitivity values. The original primary screen's
`primary-screen-replicate-collapsed-logfold-change.csv` has response rows keyed by
cell-line `row_name` and columns keyed by treatment `column_name`. Join the
corresponding cell-line and treatment-info files; retain compound, dose, and
screen identity. Lower log2 fold change indicates greater loss of viability.
Secondary-screen AUC comes from dose-response curve parameters and is not the
same quantity as single-dose log fold change. See the
[PRISM workflow](references/dependency_analysis.md) before loading these files.

## Validation and sources

Before reporting: verify release/file identity, unique joins, identifier level,
complete gene labels, cohort membership, missingness, screen eligibility, score
units/direction, multiple-testing family, and whether evidence is observational.
Expression, copy number, and CRISPR can share technical confounders; low expression
does not guarantee a measured score of zero. Broad essentiality motivates normal
cell/selectivity studies; it does not by itself prove a target is undruggable.

- [26Q1 release notes](https://forum.depmap.org/t/announcing-the-26q1-release/4606): library correction and updated annotations.
- [25Q2 release notes](https://forum.depmap.org/t/announcing-the-25q2-release/4257): omics/default mapping and WGS/WES changes.
- [Chronos upstream](https://github.com/broadinstitute/chronos): normalization, copy-number correction, and hit-calling definitions.
- [Dempster et al., Genome Biology 22:343 (2021)](https://doi.org/10.1186/s13059-021-02540-7): Chronos method, PMID 34930405.
- [Original PRISM Repurposing resource](https://depmap.org/repurposing/): release-specific data and READMEs.

The live no-captcha catalogue and original PRISM READMEs were fetched successfully.
The helper uses Python urllib, which succeeded at review; the same public endpoint
returned HTTP 403 with a default requests client. Surface access failures instead
of treating an error page as data.
Protected portal endpoints returned verification pages; authenticated downloads
and current-matrix end-to-end analysis remain unverified. This review makes no
claim of a working bearer-token API or undocumented gene-query endpoints.
