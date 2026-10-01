---
name: qiime2-amplicon
description: Processes paired-end 16S amplicon reads into QIIME 2 ASVs and taxonomy with retained artifact provenance. Checks paired FASTQ manifests, primer orientation diagnostics, predicted post-trimming overlap, sample IDs, runtime versions and read retention, and guides selection of compatible taxonomic classifiers.
license: MIT
compatibility: Python 3.10+ for the standard-library validation helper; QIIME 2 2026.7 distribution with cutadapt, dada2, demux, feature-table, feature-classifier, taxa and types plugins for execution. Install through the official conda/container distribution, not PyPI. Requires a compatible trusted classifier and network for installation/reference downloads.
metadata:
  version: "1.1"
  skill-author: K-Dense Inc.
  upstream-version: "2026.7"
  last-reviewed: "2026-10-01"
---

# QIIME 2 paired-end 16S amplicons

Use for a demultiplexed, paired-end 16S assay with known primers, quality encoding, expected insert
length, and sample metadata. This bounded workflow imports reads, removes 5′ primers, denoises with
DADA2, classifies ASVs using an explicitly supplied classifier, and retains `.qza`/`.qzv` provenance.
Do not treat read counts as absolute cell counts or taxonomy assignments as strain identification.

## Establish the assay before running

- Confirm Phred+33, read orientation, primer sequences **as sequenced** in forward/reverse reads,
  and whether primers have already been removed. The bundled runner requires primers still
  present at the 5′ ends; it anchors Cutadapt matching and discards untrimmed pairs. Already
  trimmed reads need a direct import → DADA2 workflow with that omission recorded in provenance.
- Choose truncation positions from actual per-base quality and error profiles. `trunc-f/r` are
  positions **after primer removal**. The expected maximum insert length also excludes primers.
  Require `trunc_f + trunc_r - maximum_insert_length >= 12`; use a margin for length variation.
  The check predicts geometrical overlap, not successful biological merging.
- Choose a classifier whose reference database, taxonomic coverage, orientation and training
  approach fit the assay. Full-length classifiers are supported; primer-region-specific training
  is not mandatory. Match its scikit-learn version exactly to the installed environment
  (the official 2026.7 distribution pins 1.7.1). Record source URL, database version and checksum.
  QIIME's current data-resources page links externally hosted classifiers for 2026.4 and later;
  its older downloads are not automatically compatible. Do not automatically fetch
  an arbitrary “latest” classifier or reuse an incompatible serialized sklearn model. Load sklearn
  classifier artifacts only from trusted sources: QZA format validation does not make an
  untrusted serialized model safe.
- Include extraction blanks, PCR negatives, and a mock community where available. The runner
  rejects empty FASTQs; preserve empty-control IDs separately and report them rather than silently
  deleting control evidence. Assess contamination before ecological interpretation.

## Input files

Manifest is a **tab-separated** `PairedEndFastqManifestPhred33V2` file with exactly these headers:

```text
sample-id	forward-absolute-filepath	reverse-absolute-filepath
sample1	/data/sample1_R1.fastq.gz	/data/sample1_R2.fastq.gz
```

This is the helper's deliberately narrow manifest profile. Use actual tab characters, literal
absolute paths visible to the runtime (expand environment variables before calling this helper),
and one row per sample; no comment/directive rows or additional columns in this manifest.
Do not reverse-complement R2 files. Sample metadata is a tab-separated file with first column
`sample-id`, unique IDs matching the manifest, and optional `#q2:types` annotation. Include
covariates and biological replicate IDs needed downstream.
The helper checks metadata IDs and row structure; QIIME performs full metadata typing/directive
validation during execution. Metadata used by actions persists in artifact provenance, so use
de-identified biological replicate IDs.

## Execute

The helper lives at [scripts/amplicon_workflow.py](scripts/amplicon_workflow.py). Commands below
assume the skill directory is the working directory. First validate
without QIIME. These example primers and lengths are **illustrative**, not universal assay settings:

```bash
python scripts/amplicon_workflow.py validate \
  --manifest manifest.tsv --metadata sample-metadata.tsv \
  --primer-f GTGYCAGCMGCCGCGGTAA --primer-r GGACTACNVGGGTWTCTAAT \
  --trunc-f 220 --trunc-r 200 --amplicon-max 300
```

Then run in the QIIME 2 2026.7 environment with a compatible classifier. This study-specific
invocation is illustrative; choose lengths using a preceding quality inspection or pilot:

```bash
python scripts/amplicon_workflow.py run \
  --manifest manifest.tsv --metadata sample-metadata.tsv \
  --primer-f GTGYCAGCMGCCGCGGTAA --primer-r GGACTACNVGGGTWTCTAAT \
  --trunc-f 220 --trunc-r 200 --amplicon-max 300 \
  --classifier compatible-classifier.qza --threads 4 --output run01
```

`run` executes immediately, writes only to a fresh output directory, and stops on a failing QIIME
command. It streams through every paired FASTQ record to catch mismatched IDs/order/counts,
checks sequence/quality consistency and sample alignment, and profiles the first 1,000 read pairs
for exact IUPAC primer matches. Low exact-match rates are warnings: Cutadapt allows mismatches,
but a low rate can also indicate incorrect orientation, adapters, or already-trimmed data.
At least one complete pair per sample must meet nominal post-primer truncation lengths.
These length estimates subtract the stated primer lengths; they do not simulate Cutadapt indels
or quality filtering, and do not establish that any pair will actually merge.

The runner uses `--output-dir` for plugin methods with evolving output sets, preserving Cutadapt
statistics and DADA2 base-transition artifacts when supplied by the release. The 2026.7 table
summary also produces `feature-frequencies.qza` and `sample-frequencies.qza` beside `table.qzv`.
It records
`qiime-info.txt`, `commands.json`, `workflow.log`, input QC, classifier checksum and output artifact
checksums. It runs maximum-level QIIME artifact validation before reporting completion.
See [references/runtime-and-interpretation.md](references/runtime-and-interpretation.md) for the
release-pinned runtime, actual validation scope, restart handling and scientific interpretation.

## Inspect results before analysis

Open `trimmed.qzv`, `table.qzv`, and `taxa.qzv` in a local QIIME visualization environment or
[QIIME 2 View](https://view.qiime2.org/) as appropriate for the data. Examine quality/length profiles,
per-sample depth and dominant taxa. Retain original artifacts rather than replacing them with
CSV/BIOM exports: exports do not retain the original provenance graph.

`retention-qc.json` compares raw pairs with DADA2 input and non-chimeric reads, so trimming losses
remain visible. A <50% retained fraction is a review heuristic, not a universal rejection rule.
Inspect the individual stages in `stats/stats.tsv`: filtering loss suggests quality/expected-error
settings; loss after forward denoising includes reverse-denoising and merging failures; chimera loss warrants reviewing library
quality and parameters. Investigate missing/zero samples and control behavior before rarefaction,
diversity, or differential abundance. Those downstream analyses need a separate design decision;
this skill does not choose a rarefaction depth automatically.
The standalone `retention stats.tsv` subcommand knows only DADA2 input counts: it reports
`raw_pairs: null` and names that denominator explicitly. It supports merged-only paired DADA2
statistics, as produced by this runner; it rejects retained-unmerged/concatenated-read statistics.

## Primary references

- [Current installation entry point](https://library.qiime2.org/quickstart/qiime2) and
  [amplicon documentation](https://amplicon-docs.qiime2.org/en/latest/).
- [Import formats](https://amplicon-docs.qiime2.org/en/latest/how-to-guides/how-to-import/).
- [Cutadapt actions](https://amplicon-docs.qiime2.org/en/latest/references/plugins/cutadapt/) and
  [DADA2 actions](https://amplicon-docs.qiime2.org/en/latest/references/plugins/dada2/).
- [Classifier data resources](https://library.qiime2.org/data-resources).

The rolling documentation may describe a development release. Inspect `qiime info` and action
`--help` in the exact installed environment before adapting the pinned runner to a later release.
