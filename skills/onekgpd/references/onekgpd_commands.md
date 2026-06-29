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
| `--output` | path | no | temp file | Write full JSON here; otherwise a `onekgpd_<cmd>_*.json` temp file is created and its path printed. |

There is no endpoint, credential, assembly, or timeout flag: the skill targets
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
| `--het-only` | switch | no | both | Heterozygous carriage only. |
| `--hom-only` | switch | no | both | Homozygous carriage only. |

With no zygosity flag, both heterozygous and homozygous carriage are queried.
`--het-only` and `--hom-only` are mutually exclusive.

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
AlphaMissense score bounds. Setting a `*-gt` ≥ its matching `*-lt` defines an
empty range and returns nothing.

---

## Commands

### `dataset-info`

No flags beyond `--output`. Returns dataset totals (sample count, sex split,
variant total, assembly) and the cohort breakdown. Doubles as a connectivity
check.

JSON: `{command, samples_total, females_total, males_total, variants_total,
assembly, cohorts:[{cohort_name, samples_count, female_count, male_count,
synthetic}]}`.

### `count-variants`

Region + zygosity + annotation flags. Counts variants in the region(s),
cohort-wide. JSON: `{command, count, request, result_incomplete}`.

### `select-variants`

Region + zygosity + annotation flags, plus pagination:

| flag | type | required | default | description |
| --- | --- | --- | --- | --- |
| `--limit` | int | no | 1000 | Hard cap on returned variants (mutually exclusive with `--page-size`). |
| `--page-size` | int | no | – | Retrieve ALL matching variants in pages of this size (full walk). |

JSON: `{command, count_returned, truncated, request, result_incomplete,
variants:[…]}`. `truncated` is true when the count hit `--limit` (more may
exist; raise `--limit` or use `--page-size`).

### `count-variants-in-samples`

As `count-variants`, plus `--samples CSV` (required) — counts variants carried
by the named individuals.

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
`{command, count, samples:[…], request, result_incomplete}`.

### `count-samples-hom-ref`

| flag | type | required | description |
| --- | --- | --- | --- |
| `--chrom` | str | yes | Chromosome. |
| `--position` | int | yes | 1-based position. |

Counts individuals with a homozygous-reference (0/0) call at the position. JSON:
`{command, count, variant_present, request}`. The count is a **sentinel**:

- `-1` → no variant exists at the position at all (`variant_present=false`).
- `0` → a variant exists, but no individual is homozygous reference.
- `>0` → number of homozygous-reference individuals.

### `select-samples-hom-ref`

Same `--chrom`/`--position` as above. Lists the individuals with a homozygous-
reference call at the position. JSON: `{command, count, samples:[…], request}`.

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
| `af` | float | 1000 Genomes dataset allele frequency. |
| `ac` | float | Dataset allele count (0.5 for male non-PAR het calls on sex chromosomes). |
| `an` | int | Dataset allele number. |
| `homc` | int | Homozygous allele count. |
| `hetc` | int | Heterozygous allele count. |
| `misc` | int | Missing (no-call) allele count. |
| `homfc` | int | Female homozygous count (sex chromosomes). |
| `hetfc` | int | Female heterozygous count (sex chromosomes). |
| `misfc` | int | Female missing count (sex chromosomes). |
| `gnomad_exomes_af` | float | gnomAD v4.1 exomes AF. `0.0` = absent from gnomAD exomes. |
| `gnomad_genomes_af` | float | gnomAD v4.1 genomes AF. `0.0` = absent from gnomAD genomes. |
| `am_score` | float | AlphaMissense score. `0.0` = not annotated. |
| `amino_acids` | str | Amino-acid substitution (HGVSp / VEP `Amino_acids`). |
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
