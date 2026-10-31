---
name: onekgpd
description: >
  Queries the 1000 Genomes Project dataset (3,202 whole-genome-sequenced
  individuals, GRCh38) at the level of individual participants.
  Use when a question is about individuals or variants in the 1000 Genomes
  Project cohort: which individuals carry variants matching specific criteria
  in a gene or region, which individuals are homozygous-reference at a position,
  which variants exist in the dataset or carried by specified individuals
  in a gene or region, the relatedness between two specified individuals.
  Variants are returned with 1000 Genomes allele frequencies (AF),
  gnomAD v4.1 exome and genome AF, AlphaMissense score, and HGVSp annotations.
license: MIT
compatibility: Requires Python >=3.11. Variant and sample queries require outbound network access to the public 1000 Genomes query endpoint over TLS; the sample/population metadata commands run fully offline over a data file bundled in the skill. No credentials, API keys, or environment variables are used.
allowed-tools: Write Bash
metadata:
  version: "1.4"
  last-reviewed: "2026-09-30"
  upstream-version: "dnaerys 0.2.1; proto R1.20.0"
  skill-author: Dnaerys
---

# OneKGPd: Individual-Level Queries over the 1000 Genomes Project

## Scope

This skill queries the 1000 Genomes Project dataset — the extended high-coverage cohort
of 3,202 whole-genome-sequenced individuals, on the GRCh38 assembly. All results
are drawn from this cohort, and sample names returned by the skill (for example
`HG00096` or `NA21130`) identify its participants.

Queries resolve against the cohort's per-individual genotype data. This supports
two complementary classes of question: selecting **variants** carried within a
region (across the whole cohort or within a specified set of individuals), and
selecting the **individuals** who carry variants matching given criteria.
Variant selection can be filtered by allele frequency, predicted consequence,
clinical significance, AlphaMissense classification, and the other annotation
axes listed below. Relatedness between two named individuals is also available.

The genotype state in which a variant is carried — heterozygous or homozygous —
is a criterion that queries may specify; results are returned as variants or as
sample names, not as raw genotypes.

The public service is **TLS gRPC at `db.dnaerys.org:443`**, accessed with
`dnaerys 0.2.1` (Python 3.11+); it is not a REST base URL. The maintained
service snapshot advertises VEP 115 / GENCODE 49, ClinVar 202502, and gnomAD
4.1. These are the service's annotation releases, not the latest release of
each upstream resource. Record them when interpreting results.

## When to Use

**Use this skill when you need to:**

-   Find **variants** carried in a region or set of regions matching some criteria
    across the whole cohort (`select-variants`).
-   Find **variants** carried in a region or set of regions matching some criteria
    in specific set of individuals (`select-variants-in-samples`).
-   Find **which 1000 Genomes individuals** carry variants matching some criteria
    in a region or set of regions (`select-samples`).
-   Count how many individuals carry specific variants (`count-samples`).
-   Restrict any variant query to **heterozygous-only or homozygous-only**
    carriage, or query both together (default).
-   Identify which individuals are **homozygous reference** at a single position
    (`select-samples-hom-ref`).
-   Determine the **relatedness** between two named 1000 Genomes individuals —
    both the degree (twin / 1st / 2nd / 3rd / unrelated) and the KING kinship
    coefficient (`kinship`).
-   Get **dataset totals** — sample count, sex split, variant count, assembly
    (`dataset-info`).
-   Variant selection can be specified by KGP allele frequency, gnomAD 4.1 exome and
    gnomAD 4.1 genome allele frequency, AlphaMissense Score and AlphaMissense Class,
    ClinVar significance (202502), and VEP annotations (impact, biotype, feature type,
    variant class, consequences).

**Do NOT use this skill for:**

-   Resolving a gene symbol, rsID, or transcript to coordinates, or fetching
    reference sequence. Resolve coordinates first (see Coordinate Provenance
    below), then query this skill with the resolved GRCh38 region.
-   Any cohort other than the 1000 Genomes Project — this skill serves only that
    dataset.

## Prerequisites

1.  **`uv`**: This skill's script is run with `uv run`, which reads the script's
    inline dependency metadata and provisions an ephemeral environment. Ensure
    `uv` is installed and on PATH (https://docs.astral.sh/uv/).
2.  **Data use terms**: The 1000 Genomes Project data is open; users should be
    aware of the 1000 Genomes Project / IGSR data-use terms
    (https://www.internationalgenome.org/data).
3.  **Access constraints**: There is no API key, no `.env` file, and no
    rate-limit token to configure.
4.  **Timeouts**: network commands use `--timeout 30` seconds per RPC by default.
    A positive finite override is allowed. Pagination makes several RPCs and
    retryable failures retry the whole fetch up to three times, so this is not
    a deadline for the whole command.

## Core Rules

-   **Use the Wrappers**: ALWAYS execute the provided helper scripts rather than
    constructing your own client calls or network requests. Use
    `scripts/onekgpd_api.py` for variant/sample/kinship queries (it handles the
    connection, streaming, pagination, and JSON serialization), and
    `scripts/onekgpd_meta.py` for sample/population metadata (offline, see
    [Sample & population metadata](#sample--population-metadata-offline)).
-   **Coordinates MUST be resolved against an authoritative source first** — see
    [Coordinate Provenance](#coordinate-provenance-mandatory-first-step). This
    is mandatory, not advisory.
-   **Count before you select**: every variant and sample selection has a paired
    counting command. Call the count command FIRST to size the result set, then
    select only if the count is manageable.
-   **Zygosity defaults to both**: selection and counting commands include both
    heterozygous and homozygous carriage by default. Narrow with `--het-only`
    or `--hom-only` when the question is specifically about one state. (You do
    not need to pass anything to get both.)
-   **Output**: scripts write full JSON to a file (`--output`, default under
    `/tmp/`) and print a concise summary to stdout. Do not read large JSON files
    into context — use `jq` or a small disposable `uv run python` snippet to
    extract fields. `--page-size` retrieves every page but accumulates all
    variants in RAM; it is not a bounded-memory export. Size the query first.
-   **Check completeness**: `result_incomplete=true` means results cannot support
    a definitive zero/absence claim. Re-run after service recovery. For capped
    variant selections, `truncated=true` means the limit was reached and more
    records may exist, even if the cluster result itself was complete.

## Coordinate Provenance (MANDATORY FIRST STEP)

Before any region-based query, resolve the gene or feature to **GRCh38**
coordinates against an authoritative source (for example Ensembl or NCBI), and query
with those resolved coordinates. Inputs are **1-based, inclusive**: a BED interval
`[start0, end0)` becomes `start=start0+1, end=end0`. Record the source accession,
annotation release, and retrieval date; gene boundaries can differ by annotation
release even on the same assembly. The assembly must be explicit, and a gene-range
must be resolved to precise positions before use. This is structural, not
advisory: there is no source-side guardrail that would catch a misplaced region,
so an unverified coordinate produces results for an unintended location with no
error.

```bash
# Resolve gene symbol -> GRCh38 region with an authoritative source FIRST,
# then pass the verified coordinates to the OneKGPd query below.
```

> [!CAUTION]
> The dataset is GRCh38. A GRCh37 coordinate, or any region that does not
> correctly correspond to the intended feature on GRCh38, will return
> results for an unintended location without raising an error. Verify the
> assembly and the resolved coordinates before querying.

## Command Selection Guide

Match the question to the command. Counting commands are cheap and should
precede their selection counterpart.

-   Which individuals carry matching variants in a region → `count-samples`
    then `select-samples`
-   Which variants are carried in a region, cohort-wide → `count-variants`
    then `select-variants`
-   Which variants are carried in a region, within a named set of individuals →
    `count-variants-in-samples` then `select-variants-in-samples`
-   Who is homozygous-reference at a single position → `count-samples-hom-ref`
    then `select-samples-hom-ref`
-   Relatedness (degree + coefficient) between two named individuals →
    `kinship`
-   Dataset totals (sample count, sex split, variant total, assembly) →
    `dataset-info`

## Cohort interpretation

The 3,202-sample cohort includes relatives: the additional 698 high-coverage
samples extend the original 2,504-sample panel. Carrier counts therefore are
not counts of independent observations, and cohort AF is not a population
prevalence estimate. For association or frequency comparisons, document the
selected populations and relatedness policy; use the bundled pedigree metadata
and `kinship` when choosing or auditing the analysis set. See the
[IGSR cohort announcement](https://www.internationalgenome.org/announcements/3202-samples-at-high-coverage-from-NYGC/).

## Annotation filters (shared across variant and sample selection/counting)

All variant- and sample-selection commands (`count-variants`,
`select-variants`, their `-in-samples` forms, `count-samples`, `select-samples`)
accept the same annotation filters. Different filter fields are combined with
**AND**; multiple values within one field are combined with **OR**. Enum values
are case-insensitive (e.g. `missense_variant` or `MISSENSE_VARIANT`).

These are selection criteria applied on the server. The fields returned on a
selected variant are listed under
[Variant-returning commands](#variant-returning-commands); a criterion used for
filtering is not necessarily echoed back on the returned variant.

-   `--af-lt` / `--af-gt`: 1000 Genomes dataset allele frequency bounds
-   `--gnomad-exomes-af-lt` / `--gnomad-exomes-af-gt`: gnomAD v4.1 exome AF bounds
-   `--gnomad-genomes-af-lt` / `--gnomad-genomes-af-gt`: gnomAD v4.1 genome AF bounds
-   `--clin-significance`: ClinVar significance terms, CSV (e.g. `PATHOGENIC,LIKELY_PATHOGENIC`)
-   `--consequence`: Sequence Ontology consequence terms, CSV (e.g. `MISSENSE_VARIANT,STOP_GAINED`)
-   `--impact`: VEP impact, CSV (`HIGH,MODERATE,LOW,MODIFIER`)
-   `--variant-type`, `--feature-type`, `--bio-type`: SO variant class / VEP feature / VEP biotype, CSV
-   `--alpha-missense-class`: `AM_LIKELY_BENIGN,AM_LIKELY_PATHOGENIC,AM_AMBIGUOUS` (CSV)
-   `--alpha-missense-score-lt` / `--alpha-missense-score-gt`: AlphaMissense score bounds
-   `--biallelic-only` / `--multiallelic-only`
-   `--exclude-males` / `--exclude-females`
-   `--min-len-bp` / `--max-len-bp`: alternate-allele length bounds (bp)

> [!NOTE]
> `--alpha-missense-class` and `--alpha-missense-score-*` are mutually exclusive
> (the engine ignores the class when a score bound is set). `--biallelic-only`
> and `--multiallelic-only` are mutually exclusive. `--exclude-males` and
> `--exclude-females` are mutually exclusive. Setting a `*-gt` bound greater than
> or equal to its matching `*-lt` bound defines an empty range and will return
> nothing.

> [!NOTE]
> `gnomad_exomes_af`, `gnomad_genomes_af`, and `am_score` use `0.0` for
> **not annotated in this service snapshot**. This does not establish absence
> from the current gnomAD release, biological rarity, or a benign prediction.
> The dataset's own `af` field is a different statistic, not this sentinel.

> [!CAUTION]
> **A zero numeric filter is unset on the server**, so `--gnomad-exomes-af-gt 0`
> does not exclude missing annotations. The wrapper rejects zero, nonfinite,
> out-of-range, and float32-underflowing bounds. Choose an explicit positive
> threshold (for example `--gnomad-exomes-af-gt 0.000001` means AF > 1e-6,
> not merely annotation presence). For exact `> 0`, retrieve a complete variant
> set and post-filter the returned AF locally. A `< X` filter alone includes
> unannotated zero values. Apply the same missing-score caution to AlphaMissense.

Categorical annotations are retained across transcripts. Combining consequence
and impact filters does not establish that they describe the same transcript.
`amino_acids` may contain multiple HGVSp entries; the generic gRPC service places
canonical annotations first, whereas the separate MCP layer trims its output.
Preserve transcript identifiers, and do not treat a model's likely-pathogenic
class as a clinical diagnosis or a participant phenotype.

## Quick Start

```bash
# Step 1. NCBI Gene 672, GRCh38.p14 / NC_000017.11, RS_2025_08:
# BRCA1 spans chr17:43044295-43170327 (1-based inclusive).
# Source: https://www.ncbi.nlm.nih.gov/gene/672 ; re-resolve for your analysis.
# Step 2. Size the result set: how many individuals carry predicted likely-pathogenic
#    missense variants in this region?
uv run scripts/onekgpd_api.py count-samples \
  --chrom chr17 --start 43044295 --end 43170327 \
  --consequence MISSENSE_VARIANT \
  --alpha-missense-class AM_LIKELY_PATHOGENIC \
  --output /tmp/count.json
# Step 3. If the count is manageable, list those individuals.
uv run scripts/onekgpd_api.py select-samples \
  --chrom chr17 --start 43044295 --end 43170327 \
  --consequence MISSENSE_VARIANT \
  --alpha-missense-class AM_LIKELY_PATHOGENIC \
  --output /tmp/samples.json
# Step 4. Count then select variants for actual returned sample IDs.
# HG03169,NA20506 below are illustrative IDs; substitute the Step 3 results.
uv run scripts/onekgpd_api.py count-variants-in-samples \
  --chrom chr17 --start 43044295 --end 43170327 \
  --samples HG03169,NA20506 \
  --consequence MISSENSE_VARIANT --alpha-missense-class AM_LIKELY_PATHOGENIC \
  --output /tmp/variant_count.json
uv run scripts/onekgpd_api.py select-variants-in-samples \
  --chrom chr17 --start 43044295 --end 43170327 \
  --samples HG03169,NA20506 \
  --consequence MISSENSE_VARIANT --alpha-missense-class AM_LIKELY_PATHOGENIC \
  --output /tmp/variants.json
```

## Commands

Each command writes full JSON to a file (`--output PATH`, default a temp file)
and prints a concise stdout summary. All region/sample commands share: the
region input (`--chrom`/`--start`/`--end` with optional `--ref`/`--alt`, or one
or more repeated `--region CHR:START-END`), the zygosity flags
(`--het-only`/`--hom-only`, default both), and the annotation filters above.
The full per-flag tables live in
[references/onekgpd_commands.md](references/onekgpd_commands.md).

### Variant-returning commands

`select-*` return matching variants; `count-*` return an integer count.

-   `count-variants` — count variants in a region, cohort-wide.
-   `select-variants` — select variants in a region, cohort-wide. Use `--limit N`
    (hard cap, default 200) **or** `--page-size N` (retrieve the full set in
    pages); the two are mutually exclusive. The summary flags `truncated` when
    the cap is reached.
-   `count-variants-in-samples` — as `count-variants`, restricted to
    `--samples NAME1,NAME2,...` (required).
-   `select-variants-in-samples` — as `select-variants`, restricted to
    `--samples NAME1,NAME2,...` (required).

Each returned variant carries these 22 keys: `chr`, `start`, `end`, `ref`,
`alt`, `af`, `ac`, `an`, `hom_samples`, `het_samples`, `mis_samples`,
`hom_samples_fx`, `het_samples_fx`, `mis_samples_fx`, `hom_samples_mxy`,
`het_samples_mxy`, `mis_samples_mxy`, `gnomad_exomes_af`, `gnomad_genomes_af`,
`am_score`, `amino_acids`, `biallelic`.
ClinVar significance and VEP consequence are filter criteria only and are not
returned. Full schema:
[references/onekgpd_commands.md](references/onekgpd_commands.md).

### Sample-returning commands

-   `count-samples` — count individuals carrying a matching variant in a region.
-   `select-samples` — list the names of individuals carrying a matching variant.
    Supports `--skip N` and `--limit N`. Returns names only; to see which
    variants qualified an individual, feed the names into
    `select-variants-in-samples`.

### Homozygous-reference commands

Single position via `--chrom` + `--position` (not a region).

-   `count-samples-hom-ref` — count individuals with a 0/0 call at the position.
    The count uses a sentinel: `-1` = no variant exists at that position at all;
    `0` = a variant exists but no individual is homozygous reference; `>0` = the
    number of homozygous-reference individuals. These interpretations require
    `result_incomplete=false`; otherwise `variant_present` is `null`. No variant
    record is not evidence that all 3,202 individuals have callable 0/0 genotypes.
-   `select-samples-hom-ref` — list the individuals with a 0/0 call at the position.

### Relatedness command

-   `kinship --sample1 NAME --sample2 NAME` — relatedness between two named
    individuals: the degree (`TWINS_MONOZYGOTIC` / `FIRST_DEGREE` /
    `SECOND_DEGREE` / `THIRD_DEGREE` / `UNRELATED`) and the KING kinship
    coefficient (`phi_bwf`).

### Dataset metadata command

-   `dataset-info` — dataset totals: `samples_total` (3,202), female/male split,
    `variants_total`, `assembly` (GRCh38), and the cohort breakdown. No region
    required; doubles as a connectivity check.

## Sample & population metadata (offline)

Population, sex, pedigree, and superpopulation questions are answered by a second
script, `scripts/onekgpd_meta.py`, from a data file bundled in the skill — **no
network, no credentials, no coordinates**. The sample IDs are the same names the
variant commands use, so the two layers compose (e.g. pick a cohort by population,
then query its variants). Run `uv run scripts/onekgpd_meta.py <command>`.

The cohort has 5 superpopulations (`AFR`, `AMR`, `EAS`, `EUR`, `SAS`) and 26
populations. Population/superpopulation values match **case-insensitively** by
short code or full name; **sample IDs are case-sensitive**.

-   `sample-metadata --samples NA19240,HG00096` — family, gender, parents,
    children, population, superpopulation, and phase3 status for the given samples.
-   `list-populations` — all 26 populations with superpopulation and sample count
    (use to discover valid values).
-   `list-superpopulations` — the 5 superpopulations with sample count and
    constituent populations.
-   `population-stats --populations YRI [--populations CHS …]` — per-population sex
    split, phase3 count, and trio membership. Repeat `--populations` for multiple
    values (full names contain commas, so they are not comma-separated).
-   `superpopulation-summary --superpopulations EAS [--superpopulations EUR …]` —
    per-superpopulation totals with a per-population breakdown.
-   `select-samples-by-population --population YRI` and/or `--superpopulation AFR`,
    with optional `--skip`/`--limit` (default 0 / 50, max 3202) — the sample IDs in
    a population and/or superpopulation; both given intersects. Feed the names into
    `select-variants-in-samples` to see their variants.

See [references/onekgpd_commands.md](references/onekgpd_commands.md) for full
argument tables and JSON output schemas.

## Typical Workflows

### Which individuals, then which variants they carry

The following is an illustrative template; replace all angle-bracket placeholders.

```bash
# Step 1: resolve gene -> verified GRCh38 region (authoritative source).
# Step 2: count individuals carrying a qualifying variant in the region.
uv run scripts/onekgpd_api.py count-samples \
  --chrom <chr> --start <start> --end <end> \
  --consequence MISSENSE_VARIANT --alpha-missense-class AM_LIKELY_PATHOGENIC \
  --output /tmp/n.json
# Step 3: list those individuals.
uv run scripts/onekgpd_api.py select-samples \
  --chrom <chr> --start <start> --end <end> \
  --consequence MISSENSE_VARIANT --alpha-missense-class AM_LIKELY_PATHOGENIC \
  --output /tmp/who.json
# Step 4: count variants for those individuals before selecting.
uv run scripts/onekgpd_api.py count-variants-in-samples \
  --chrom <chr> --start <start> --end <end> \
  --samples <name1,name2,...> \
  --consequence MISSENSE_VARIANT --alpha-missense-class AM_LIKELY_PATHOGENIC \
  --output /tmp/variant_count.json
uv run scripts/onekgpd_api.py select-variants-in-samples \
  --chrom <chr> --start <start> --end <end> \
  --samples <name1,name2,...> \
  --consequence MISSENSE_VARIANT --alpha-missense-class AM_LIKELY_PATHOGENIC \
  --output /tmp/variants.json
```

### Homozygous-reference carriers at a position of interest

Illustrative template; replace the placeholders with verified coordinates.

```bash
# After identifying a position of interest (verified coordinate):
uv run scripts/onekgpd_api.py count-samples-hom-ref \
  --chrom <chr> --position <pos> --output /tmp/homref_n.json
uv run scripts/onekgpd_api.py select-samples-hom-ref \
  --chrom <chr> --position <pos> --output /tmp/homref.json
```

## Common Mistakes

-   **Mistake:** Querying with an unverified coordinate.
    **Fix:** Always resolve gene/feature → GRCh38 against an authoritative
    source first.
    A misplaced region returns results for an unintended location without error.
-   **Mistake:** Calling a selection command before its counting command.
    **Fix:** Count first; selection result sets can be large.
-   **Mistake:** Assuming a GRCh37 coordinate will work.
    **Fix:** The dataset is GRCh38 only.

## References

-   [references/onekgpd_commands.md](references/onekgpd_commands.md) — full
    per-command argument tables and the returned-variant output schema.
-   [references/annotation_vocabularies.md](references/annotation_vocabularies.md)
    — the controlled-vocabulary terms accepted by the CSV filter flags
    (consequence, impact, biotype, feature type, ClinVar significance,
    AlphaMissense class, variant class).
-   Current API contract and live-check scope: the
    [command reference](references/onekgpd_commands.md#verified-api-contract).
-   1000 Genomes Project / IGSR: https://www.internationalgenome.org/
-   1000 Genomes Project dataset online: https://dnaerys.org/online/
