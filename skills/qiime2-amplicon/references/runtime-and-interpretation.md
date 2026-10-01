# Release-pinned runtime and interpretation

## Installation and environment

This runner targets **QIIME 2 2026.7**, still the stable release selected by the official
quickstart on 2026-10-01. The official distribution image is
`quay.io/qiime2/qiime2:2026.7` (the image naming changed from earlier `amplicon` releases).
Use the official [quickstart](https://library.qiime2.org/quickstart/qiime2) for its conda environment
or container. A PyPI package with a similar name is not a replacement for the distribution's R,
DADA2 and plugin environment. On Apple Silicon, the previously tested container uses Linux amd64
emulation; official conda instructions require x86-64/Rosetta, rather than an ARM build.

For example, mount a data directory at `/data` and this skill at `/skill`, and run the Python helper
inside the container. Manifest absolute paths must be `/data/...`, not host-only paths. Ensure
enough disk space for both image download/unpacking and working artifacts; artifact creation can
copy/intermediately materialize the reads.

This installation example was checked against current documentation, not rerun during the
2026-10-01 refresh:

```bash
docker run --rm --platform linux/amd64 \
  -v "$PWD/data:/data" -v "$PWD/qiime2-amplicon:/skill:ro" \
  quay.io/qiime2/qiime2:2026.7 qiime info
```

`qiime info` and `qiime dada2 denoise-paired --help` in the target environment are the authoritative
command contract. Rolling web documentation can already describe `2026.10.0.dev0` and Python
`rachis` imports while an installed release has a different action signature. The runner uses the
CLI and release check rather than relying on rolling Python import paths. Both trimming and
DADA2 use `--output-dir`, preserving release-specific additional outputs. In 2026.7,
`feature-table summarize` takes `--m-metadata-file` and produces `--o-summary`,
`--o-feature-frequencies`, and `--o-sample-frequencies`; older tutorials using
`--m-sample-metadata-file` and `--o-visualization` do not apply to this action.
The helper checks the framework, q2cli and every used plugin's version line, rather than accepting
an unrelated occurrence of `2026.7` in the environment report. Development/mixed releases fail
preflight. This verifies reported package versions, not native-library health.

## Verified 2026.7 action contract

The 2026.7.0 plugin registrations and implementations were checked alongside rolling docs:

| Action | Contract used by this workflow |
| --- | --- |
| `tools import` | `SampleData[PairedEndSequencesWithQuality]`, format `PairedEndFastqManifestPhred33V2`; `.qza` output. The underlying V2 manifest is QIIME metadata; this helper accepts a narrower literal-path three-column profile. |
| `cutadapt trim-paired` | `demultiplexed_sequences`, IUPAC `front_f/front_r` anchored with `^`, `discard_untrimmed`, `cores`; outputs `trimmed_sequences` and `stats` (`ImmutableMetadata`). With both primers supplied, default pair filtering discards a pair if either mate is untrimmed. |
| `demux summarize` | `data` input and `visualization` output; positional quality plots sample reads, rather than verifying all per-base qualities. |
| `dada2 denoise-paired` | `demultiplexed_seqs`, positive `trunc_len_f/r`, zero `trim_left_f/r`, `min_overlap`, `n_threads`; outputs table, representative sequences, denoising stats and base-transition stats. |
| `feature-table summarize` | A pipeline accepting `table` and metadata; produces two `ImmutableMetadata` artifacts and a `summary` visualization. |
| `feature-classifier classify-sklearn` | `TaxonomicClassifier` and sequence reads, `n_jobs`; output `FeatureData[Taxonomy]`. Default confidence is 0.7; `read_orientation=auto` selects an orientation using the first 100 reads. |
| `taxa barplot` | Frequency table, taxonomy and metadata; all table feature IDs need taxonomy annotations. `barplot` remains supported; the separate `barplot2` is experimental. |
| `tools export` / `tools validate` | Export the DADA2 stats artifact to `stats.tsv`; validate each QZA with positional artifact path and `--level max`. Exports omit artifact provenance. |

The fixture additionally imports `FeatureData[Sequence]` and headerless
`FeatureData[Taxonomy]` using `HeaderlessTSVTaxonomyFormat`, then calls
`feature-classifier fit-classifier-naive-bayes` with `reference_reads` and `reference_taxonomy`
to produce a `TaxonomicClassifier`. These are local CLI/plugin APIs, not hosted analysis endpoints.

Defaults matter: the runner inherits Cutadapt error rate 0.1, indel matching, one removal pass and
no quality trimming; DADA2 uses maximum expected errors 2 per mate, `trunc_q=2`, independent
denoising, consensus chimera removal, zero merge mismatches and `retain_unmerged=False`.
DADA2's minimum overlap API permits 4 or more bases, but this helper deliberately requires at
least 12. `retain_unmerged=True` produces linked sequences and adds concatenated counts; those
are outside this helper's merged-ASV retention contract. Samples with zero retained frequency
remain represented by the default `retain_all_samples=True`. The official distribution pins
Cutadapt 5.2, R 4.5.2 and DADA2 1.38.0; do not independently upgrade them in the pinned environment.

## Classifiers and provenance

Supply a trusted `TaxonomicClassifier` with suitable database coverage, training choices and
compatible QIIME/scikit-learn environment. Full-length training is supported; the official resource
page no longer requires region-specific classifiers. Record database citation, any region extraction primers,
training parameters, confidence threshold, source URL, artifact UUID and SHA-256. Keep the training
artifact lineage when available. QIIME's ZIP/schema validation does not establish the safety of an
untrusted serialized sklearn model.

If no matching classifier exists, train within the target distribution from an appropriate curated
reference sequence/taxonomy pair using its feature-classifier actions. A classifier trained on a
tiny test reference only validates execution and label plumbing; it says nothing about taxonomic
accuracy on biological samples. Do not silently substitute such a test reference for a real database.

The resulting QZA files preserve QIIME action provenance. `commands.json` supplements this with
actual CLI arguments; the runner also records release information and hashes. Copying only exported
FASTA/TSV/BIOM loses the artifact provenance graph. Retain the original FASTQs and classifier.

## Read retention and assay interpretation

The helper's overlap formula assumes fixed positive DADA2 truncation positions after primer
removal, no additional `trim-left`, and an upper bound on primer-free amplicon length. Use the
longest plausible insert rather than its mean. ITS and other highly variable-length amplicons need
a different strategy; applying a 16S fixed-length workflow can preferentially exclude taxa.

Exact primer-prefix matching profiles only the first 1,000 pairs. It is a diagnostic, not a
Cutadapt simulator: Cutadapt allows mismatches/indels according to its defaults. Anchoring assumes
primers begin at base one; staggered primers or remaining sequencing adapters need explicit
adaptation. The helper inspects every record for paired IDs, sequence/quality lengths and raw counts.
Phred+33 character validation cannot establish that the acquisition actually used Phred+33 rather
than Phred+64; obtain that fact from sequencing metadata.

Use `stats/stats.tsv` to localize losses. Raw → DADA2 input includes primer trimming; input →
filtered reflects quality/length/error limits; denoised is the forward-denoised count, so denoised →
merged includes both reverse-denoising and merging losses; merged →
non-chimeric tests chimera removal. The runner's 50% retention warning is a review heuristic.
Do not automatically relax quality settings until every sample passes. Compare loss patterns by
batch, treatment, read quality, and controls, and report samples excluded from downstream analyses.

ASVs are denoised marker-gene sequences, not guaranteed species or organisms. 16S copy number,
primer bias and contamination affect abundance. Taxonomic confidence does not remove ambiguity
in a short region. Preserve unassigned features and investigate them before choosing exclusions.
Classifier confidence is a model threshold, not a calibrated probability of species identity;
automatic orientation detection does not establish the assay's biological orientation.
This fixed-length workflow also assumes no unresolved opposite-primer read-through; short inserts
can violate that assumption even when the maximum-length overlap check passes.

## Restart behavior

The runner stops at the first failed command and leaves its log, command list and completed QZA
artifacts intact. It requires a new output directory for an entire rerun. To resume a specific step,
use the recorded QIIME command with validated preceding artifacts and a new output path, keeping
the original parameters unless the failure evidence justifies a change. A changed trimming or
DADA2 parameter produces a different analysis, not an interchangeable continuation.

## Earlier native integration evidence

The following is the pre-existing bounded native-run record. The 2026-10-01 refresh verified current
official documentation/source and reran portable input/retention tests; it did **not** rerun QIIME,
install its distribution, or independently revalidate the archived container digest. The example
workflow is therefore source-verified for the pinned release, with the earlier native evidence
bounded as described below.

The bounded regression used the official `quay.io/qiime2/qiime2:2026.7` image at digest
`sha256:ffde217254fe71bc3ace7f17d4ee5efebbad4f81dab52b6af8aee124ebc713c8`, under Linux
amd64 emulation on Apple Silicon. `qiime info` reported Python 3.12.13, rachis/q2cli 2026.7.0,
and the relevant plugins at 2026.7.0.

Ten nonempty paired samples, each with 100 pairs, derive from the official q2-dada2 regression
fixture at commit `8bbf5158d6c71b37b57a0e1f6e2b1cb69b9e96d7`. Synthetic Q40 primer prefixes were
added so the real Cutadapt stage restores the original upstream reads. The original empty BLANK
control is documented separately. DADA2 recovered exactly the expected **18 ASV sequences and
243 non-chimeric reads**; every sample's input, filtered, denoised, merged and non-chimeric counts
matched the upstream expected table. Two samples have zero retained reads, deliberately exercising
retention reporting rather than silently removing those samples from QC.

The run trained a tiny classifier inside the same environment using the expected sequences and
invented `SyntheticFixture` labels. Real `classify-sklearn` assigned those domain labels to all
18 ASVs, and table/taxonomy visualizations were produced. This verifies artifact and classification
plumbing, not biological taxonomic accuracy or a production database's suitability.

The initial run exposed the changed 2026.7 feature-table summary arguments described above.
After correcting the runner, execution resumed from the already completed DADA2 artifacts;
input import, trimming and denoising were not rerun. The runtime evidence retains both the failed
and corrected commands and the original artifact provenance. In a repository checkout,
`tests/qiime2-amplicon/run_integration.py --output FRESH_DIRECTORY` stages the bundled licensed
fixtures and runs the corrected workflow. Its `--verify-only RESULTS_DIRECTORY` mode independently
checks exact stage counts, ASV sequences, taxonomy feature IDs and synthetic labels, and artifact
action provenance. The portable pytest suite uses only the standard library and does not launch
or download the large QIIME distribution.

All **10 generated QZA artifacts** passed maximum-level QIIME validation. After three sequential
checks had passed, the remaining independent read-only checks used at most three identical
containers concurrently; an interrupted fourth check was recorded and rerun. The final retention
report was generated with the same bundled `retention` and `digest` functions. The standalone
integration verifier passed all count, sequence, taxonomy identity and action-provenance checks.
These results establish regression behavior on the small fixture, not DADA2 error-model
calibration or taxonomic accuracy for a new biological study.

## Official sources reviewed

- [Distribution dependency pins](https://github.com/qiime2/distributions/blob/dev/2026.7/qiime2/released/rachis-qiime2-linux-64-conda.yml).
- [DADA2 2026.7.0 source](https://github.com/qiime2/q2-dada2/tree/2026.7.0/q2_dada2),
  [Cutadapt 2026.7.0 source](https://github.com/qiime2/q2-cutadapt/tree/2026.7.0/q2_cutadapt),
  and [Cutadapt 5.2 paired filtering](https://cutadapt.readthedocs.io/en/v5.2/guide.html#filtering-paired-end-reads).
- [Feature-table registration](https://github.com/qiime2/q2-feature-table/blob/2026.7.0/q2_feature_table/plugin_setup.py),
  [demux registration](https://github.com/qiime2/q2-demux/blob/2026.7.0/q2_demux/plugin_setup.py),
  [taxa registration](https://github.com/qiime2/q2-taxa/blob/2026.7.0/q2_taxa/plugin_setup.py).
- [Classifier source](https://github.com/qiime2/q2-feature-classifier/tree/2026.7.0/q2_feature_classifier)
  and [current classifier resources](https://library.qiime2.org/data-resources).
- [Manifest implementation](https://github.com/qiime2/q2-types/blob/2026.7.0/q2_types/per_sample_sequences/_formats.py),
  [metadata rules](https://use.qiime2.org/en/latest/references/metadata/),
  and [CLI tools](https://github.com/rachis-org/rachis-cli/blob/2026.7.0/q2cli/builtin/tools.py).
