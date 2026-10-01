# OneKGPd command reference

Full argument tables for every `onekgpd_api.py` subcommand and the schema of a
returned variant. Run with `uv run scripts/onekgpd_api.py <command> [flags]`.

Coordinates are **GRCh38, 1-based inclusive**. Resolve a gene/feature to
coordinates against an authoritative source before querying. Every command
writes full JSON to a file (`--output PATH`, default a temp file) and prints a
short summary to stdout.

## Shared flags

### Connection / output (all commands)

| flag | type | required | default | description |
| --- | --- | --- | --- | --- |
| `--timeout` | float | no | 30 | Positive finite seconds per RPC. Whole-fetch retries and pagination can exceed this overall. |
| `--output` | path | no | temp file | Write full JSON here; otherwise a `onekgpd_<cmd>_*.json` temp file is created and its path printed. |

There is no endpoint, credential, or assembly override: the skill targets
the public 1000 Genomes instance on GRCh38 only.

### Region input (count/select variants and samples)

Provide **either** a single region **or** one-or-more `--region`, not both.

| flag | type | required | default | description |
| --- | --- | --- | --- | --- |
| `--chrom` | str | single-region mode | – | Chromosome: `chr17`, `17`, `X`, `MT` (case-insensitive). |
| `--start` | int | with `--chrom` | – | 1-based inclusive start. |
| `--end` | int | with `--chrom` | – | 1-based inclusive end (≥ start). |
| `--ref` | str | no | – | Narrow to one reference allele (single-region only). |
| `--alt` | str | no | – | Narrow to one alternate allele (single-region only). |
| `--region` | `CHR:START-END` | multi-region mode | – | A region; repeat the flag for multiple regions. |
| `--min-len-bp` | int | no | – | Minimum alternate-allele length (bp). |
| `--max-len-bp` | int | no | – | Maximum alternate-allele length (bp). |

### Zygosity (count/select variants and samples)

| flag | type | required | default | description |
| --- | --- | --- | --- | --- |
| `--het-only` | switch | no | both | Include HETEROZYGOUS variants ONLY (0/1 genotypes). |
| `--hom-only` | switch | no | both | Include HOMOZYGOUS variants ONLY (1/1 genotypes). |

With no zygosity flag, both HETEROZYGOUS (0/1) and HOMOZYGOUS (1/1) carriage are
queried — use the default when you need homozygous OR heterozygous variants, or
when uncertain. `--het-only` and `--hom-only` are mutually exclusive.

### Annotation filters (count/select variants and samples)

See `annotation_vocabularies.md` for the valid CSV terms. Different filter fields
combine with **AND**; multiple CSV values within one field combine with **OR**.

| flag | type | maps to |
| --- | --- | --- |
| `--af-lt` / `--af-gt` | float | 1000 Genomes dataset AF bounds |
| `--gnomad-exomes-af-lt` / `--gnomad-exomes-af-gt` | float | gnomAD v4.1 exomes AF bounds |
| `--gnomad-genomes-af-lt` / `--gnomad-genomes-af-gt` | float | gnomAD v4.1 genomes AF bounds |
| `--clin-significance` | CSV | ClinVar significance terms |
| `--consequence` | CSV | SO consequence terms |
| `--impact` | CSV | VEP impact (HIGH,MODERATE,LOW,MODIFIER) |
| `--variant-type` | CSV | SO variant class terms |
| `--feature-type` | CSV | VEP feature types |
| `--bio-type` | CSV | VEP biotypes |
| `--alpha-missense-class` | CSV | AM_LIKELY_BENIGN,AM_LIKELY_PATHOGENIC,AM_AMBIGUOUS |
| `--alpha-missense-score-lt` / `--alpha-missense-score-gt` | float | AlphaMissense score bounds |
| `--biallelic-only` / `--multiallelic-only` | switch | site multiplicity (mutually exclusive) |
| `--exclude-males` / `--exclude-females` | switch | sex exclusion (mutually exclusive) |

Mutual exclusions enforced: `--biallelic-only`/`--multiallelic-only`,
`--exclude-males`/`--exclude-females`, and `--alpha-missense-class` vs the
AlphaMissense score bounds. Every numeric AF/AlphaMissense bound must be finite,
in `(0, 1]`, and remain nonzero when encoded as float32. **Zero means unset in
the protobuf API**; the wrapper rejects it rather than silently dropping the
filter. Setting a positive `*-gt` ≥ its matching `*-lt` defines an empty range.

The gnomAD `< X` bounds include unannotated variants, represented by AF = 0.
Choose a scientifically meaningful positive lower bound to exclude those zeros;
this also excludes annotated values at or below that bound. For exact annotation
presence, retrieve complete variants and post-filter the relevant AF > 0 locally.
Do not substitute an arbitrary epsilon without documenting its effect.

---

## Commands

### `dataset-info`

No flags beyond `--output` / `--timeout`. Returns dataset totals (sample count, sex split,
variant total, assembly) and the cohort breakdown. Doubles as a connectivity
check.

JSON: `{command, samples_total, females_total, males_total, variants_total,
assembly, cohorts:[{cohort_name, samples_count, female_count, male_count,
synthetic}]}`.

### `count-variants`

Region + zygosity + annotation flags. Counts variants in the region(s),
cohort-wide. JSON: `{command, count, request, result_incomplete}`.

### `select-variants`

SELECT variants which exist in ANY genomic region provided.

Region + zygosity + annotation flags, plus pagination:

| flag | type | required | default | description |
| --- | --- | --- | --- | --- |
| `--limit` | int | no | 200 | Hard cap on returned variants (mutually exclusive with `--page-size`). |
| `--page-size` | int | no | – | Retrieve ALL matching variants in pages of this size (full walk). |

JSON: `{command, count_returned, truncated, request, result_incomplete,
variants:[…]}`. `truncated` is true when the count hit `--limit` (more may
exist; raise `--limit` or use `--page-size`). Empty `variants` array if no
matches. Paging accumulates the complete result in memory. Check
`result_incomplete` separately from `truncated`; a count taken before selection
is not a transactional snapshot.

### `count-variants-in-samples`

As `count-variants`, plus `--samples CSV` (required) — counts variants carried
by the named individuals. Blank/empty CSV is rejected before connecting, because
the SDK otherwise routes an empty sample list to the cohort-wide endpoint.

### `select-variants-in-samples`

As `select-variants`, plus `--samples CSV` (required) — selects variants carried
by the named individuals.

### `count-samples`

Region + zygosity + annotation flags. Counts how many individuals carry a
matching variant. JSON: `{command, count, request, result_incomplete}`.

### `select-samples`

Region + zygosity + annotation flags, plus pagination:

| flag | type | required | default | description |
| --- | --- | --- | --- | --- |
| `--skip` | int | no | – | Skip the first N individuals. |
| `--limit` | int | no | – | Return at most N individuals. |

Returns the **names** of individuals carrying a matching variant. To see which
variants qualified them, feed the names into `select-variants-in-samples`. JSON:
`{command, count, samples:[…], request, result_incomplete}`. Empty `samples` array
if no matches.

### `count-samples-hom-ref`

| flag | type | required | description |
| --- | --- | --- | --- |
| `--chrom` | str | yes | Chromosome. |
| `--position` | int | yes | 1-based position. |

Counts individuals with a homozygous-reference (0/0) call at the position. JSON:
`{command, count, variant_present, request, result_incomplete}`. For a complete
response the count uses a **sentinel**:

- `-1` → no variant exists at the position at all (`variant_present=false`).
- `0` → a variant exists, but no individual is homozygous reference.
- `>0` → number of homozygous-reference individuals.

If `result_incomplete=true`, `variant_present=null` and the count is not
definitive. No variant record does not imply all samples are callable reference.

### `select-samples-hom-ref`

Same `--chrom`/`--position` as above. Lists the individuals with a homozygous-
reference call at the position. JSON:
`{command, count, samples:[…], request, result_incomplete}`.

### `kinship`

| flag | type | required | description |
| --- | --- | --- | --- |
| `--sample1` | str | yes | First sample name. |
| `--sample2` | str | yes | Second sample name. |

Returns the relatedness degree and the KING kinship coefficient between the two
named individuals. JSON: `{command, sample1, sample2, degree, phi_bwf,
result_incomplete}`. `degree` ∈ `{TWINS_MONOZYGOTIC, FIRST_DEGREE,
SECOND_DEGREE, THIRD_DEGREE, UNRELATED}`; `phi_bwf` is the KING between-family
robust coefficient (≈ 0.5 monozygotic, 0.25 first-degree, 0.125 second-degree,
0.0625 third-degree).

---

## Returned-variant output schema

`select-variants` and `select-variants-in-samples` return a `variants` array;
each element has these keys (filter-only criteria such as ClinVar significance
and VEP consequence are **not** echoed back on a returned variant):

| key | type | meaning |
| --- | --- | --- |
| `chr` | str | Chromosome, e.g. `chr17`. |
| `start` | int | 1-based inclusive start. |
| `end` | int | 1-based inclusive end. |
| `ref` | str | Reference allele. |
| `alt` | str | Alternate allele. |
| `af` | float | Whole-dataset allele frequency, not recalculated for `--samples`. |
| `ac` | float | Dataset allele count (0.5 for male non-PAR het calls on X and Y chromosomes). |
| `an` | int | Dataset allele number. |
| `hom_samples` | int | Number of all samples with a homozygous genotype. |
| `het_samples` | int | Number of all samples with a heterozygous genotype. |
| `mis_samples` | int | Number of all samples with a missing (no-call) genotype. |
| `hom_samples_fx` | int | Number of female samples with a homozygous genotype, X chromosome only (0 outside X). |
| `het_samples_fx` | int | Number of female samples with a heterozygous genotype, X chromosome only (0 outside X). |
| `mis_samples_fx` | int | Number of female samples with a missing (no-call) genotype, X chromosome only (0 outside X). |
| `hom_samples_mxy` | int | Number of male samples with a homozygous genotype, X & Y chromosomes only (0 outside X and Y). |
| `het_samples_mxy` | int | Number of male samples with a heterozygous genotype, X & Y chromosomes only (0 outside X and Y). |
| `mis_samples_mxy` | int | Number of male samples with a missing (no-call) genotype, X & Y chromosomes only (0 outside X and Y). |
| `gnomad_exomes_af` | float | gnomAD v4.1 exomes AF. `0.0` = not annotated in this service snapshot. |
| `gnomad_genomes_af` | float | gnomAD v4.1 genomes AF. `0.0` = not annotated in this service snapshot. |
| `am_score` | float | AlphaMissense score. `0.0` = not annotated. |
| `amino_acids` | str | HGVSp annotation string; may contain multiple transcript entries, canonical first. |
| `biallelic` | bool | Whether the site was biallelic in the input VCFs. |

---

# Sample & population metadata commands (offline)

A second script, `scripts/onekgpd_meta.py`, answers population/pedigree questions
from a data file bundled in the skill (`assets/kgpe.json`) — **no network, no
credentials, no dependencies**. Run with
`uv run scripts/onekgpd_meta.py <command> [flags]`. The sample identifier is the
same name used by the variant/kinship commands (e.g. `NA19240`), so the two
layers compose (e.g. `select-samples-by-population` → `select-variants-in-samples`).

The 1000 Genomes cohort has **5 superpopulations** (`AFR` Africa, `AMR` America,
`EAS` East Asia, `EUR` Europe, `SAS` South Asia) and **26 populations**. Use
`list-populations` / `list-superpopulations` to discover valid codes and full
names. Population/superpopulation values are matched **case-insensitively**
against either the short code or the full name; **sample IDs are case-sensitive**.

All six commands write JSON to `--output` (or a temp file) and print a summary.

## `sample-metadata`

| flag | type | required | description |
| --- | --- | --- | --- |
| `--samples` | CSV | yes | Comma-separated sample IDs (case-sensitive), e.g. `NA19240,HG00096`. |

JSON: `{command, samples:[{...}]}` ordered by `sample_id`. Each sample object:

| key | type | meaning |
| --- | --- | --- |
| `sample_id` | str | Sample identifier (`externalIDs`). |
| `family_id` | str\|null | Family/pedigree ID; `null` if absent. |
| `gender` | str | `male` / `female`. |
| `paternal_id` | str\|null | Father's `sample_id`; `null` if not in the dataset. |
| `maternal_id` | str\|null | Mother's `sample_id`; `null` if not in the dataset. |
| `relationship` | str\|null | `mother` / `father` / `child` / `null`. |
| `children` | list[str] | Sorted children whose **both** parents are recorded; `[]` if none. |
| `population_code` | str | e.g. `YRI`. |
| `population` | str | e.g. `Yoruba in Ibadan, Nigeria`. |
| `superpopulation_code` | str | e.g. `AFR`. |
| `superpopulation` | str | e.g. `Africa`. |
| `phase3` | str | `"TRUE"` / `"FALSE"` (phase-3 inclusion flag). |

## `list-populations`

No flags. JSON: `{command, populations:[{population_code, population,
superpopulation_code, superpopulation, sample_count}]}`, ordered by
(superpopulation, population). 26 entries.

## `list-superpopulations`

No flags. JSON: `{command, superpopulations:[{superpopulation_code,
superpopulation, sample_count, populations:[codes]}]}`, ordered by
superpopulation. 5 entries.

## `population-stats`

| flag | type | required | description |
| --- | --- | --- | --- |
| `--populations` | repeatable | yes | One population code or full name per flag; repeat for multiple. Repeated (not CSV) because full names contain commas. Case-insensitive. |

JSON: `{command, populations:[{population_code, population, superpopulation_code,
superpopulation, sample_count, male_count, female_count, phase3_count,
trio_count}]}`, ordered by population. `trio_count` = samples that are offspring
with **both** parents in the dataset (not the `relationship` label).

## `superpopulation-summary`

| flag | type | required | description |
| --- | --- | --- | --- |
| `--superpopulations` | repeatable | yes | One superpopulation code or full name per flag; repeat for multiple. Case-insensitive. |

JSON: `{command, superpopulations:[{superpopulation_code, superpopulation,
sample_count, male_count, female_count, phase3_count, trio_count, populations:[
<population-stats object>]}]}`. The per-superpopulation counts are sums over the
nested per-population breakdown.

## `select-samples-by-population`

| flag | type | required | default | description |
| --- | --- | --- | --- | --- |
| `--population` | str | one of the two | – | Population code or full name (case-insensitive). |
| `--superpopulation` | str | one of the two | – | Superpopulation code or full name (case-insensitive). |
| `--skip` | int | no | 0 | Number of results to skip (≥ 0). |
| `--limit` | int | no | 50 | Max results to return (1–3202). |

At least one of `--population` / `--superpopulation` is required; when both are
given the results are intersected (AND). JSON: `{command, count, samples:[ids],
request:{population, superpopulation, skip, limit}}`, sample IDs ordered
ascending then paginated by `skip`/`limit`.


## Verified API contract

Reviewed 2026-09-30 against released `dnaerys 0.2.1`, protobuf **R1.20.0**,
and public TLS gRPC `db.dnaerys.org:443`. The service prefix is
`org.dnaerys.cluster.grpc.DnaerysService/`; do not append REST routes to the host.
All routes below were exercised with small read-only queries. Health and dataset
metadata also succeeded: 3,202 samples, GRCh38, 138,044,723 variants, eight rings,
and a 5,000-variant cap per ring. These are observed snapshot totals, not constants
that clients may assume forever.

| Wrapper operation / input | gRPC method suffix |
| --- | --- |
| `dataset-info` | `DatasetInfo` |
| `count-variants`, single / multiple regions | `CountVariantsInRegion` / `CountVariantsInMultiRegions` |
| `count-variants-in-samples`, single / multiple | `CountVariantsInRegionInSamples` / `CountVariantsInMultiRegionsInSamples` |
| `select-variants`, single / multiple | `SelectVariantsInRegion` / `SelectVariantsInMultiRegions` |
| `select-variants-in-samples`, single / multiple | `SelectVariantsInRegionInSamples` / `SelectVariantsInMultiRegionsInSamples` |
| `count-samples`, single / multiple | `CountSamplesInRegion` / `CountSamplesInMultiRegions` |
| `select-samples`, single / multiple | `SelectSamplesInRegion` / `SelectSamplesInMultiRegions` |
| `count-samples-hom-ref` / `select-samples-hom-ref` | `CountSamplesHomReference` / `SelectSamplesHomReference` |
| `kinship` | `KinshipDuo` |

The SDK reuses variant routes for pagination and discovers the per-ring cap via
`DatasetInfo`; do not reproduce per-ring offsets as global pagination. Small
paginated results reconciled with the count. Large multi-ring exports and outage
recovery were not stress-tested; incompleteness/retry behavior is covered by mocks.

The protobuf and live service take precedence over prose when they disagree:
`gnomad_exomes_af_gt=0` returned 15 variants including two zero annotations in
a small test region; a positive bound of `1e-12` returned 13 with none missing.
The latter is a positive threshold, not a universal definition of presence.

Sources:

- [Released SDK](https://pypi.org/project/dnaerys/0.2.1/) and
  [official source](https://github.com/dnaerys/dnaerys-python).
- [RPC definitions and zero-filter semantics](https://github.com/dnaerys/dnaerys-python/blob/master/proto/dnaerys.proto).
- [Timeout/TLS options](https://github.com/dnaerys/dnaerys-python/blob/master/docs/source/connection.rst),
  [pagination](https://github.com/dnaerys/dnaerys-python/blob/master/docs/source/pagination.rst),
  and [missing-annotation convention](https://github.com/dnaerys/dnaerys-python/blob/master/docs/source/caveats.rst).
- [Hosted cohort and annotation versions](https://github.com/dnaerys/onekgpd-mcp),
  [annotation composition](https://github.com/dnaerys/onekgpd-mcp/blob/master/docs/annotations.md),
  and [offline metadata source](https://github.com/dnaerys/onekgpd-mcp/blob/master/src/main/resources/kgpe.json).
  The bundled 3,202 records matched this source on review; they are not live metadata.
- [BRCA1 coordinate source](https://www.ncbi.nlm.nih.gov/gene/672): Gene 672,
  GRCh38.p14, NC_000017.11:43044295-43170327, annotation RS_2025_08.
