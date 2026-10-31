# Consensus peaks and universe assessment

Verified against `geniml==0.8.4` release source and official BEDbase
documentation on 2026-10-01.

## Method scope

A Geniml universe is a reference interval vocabulary derived from coverage
across a collection of BED files. Release 0.8.4 implements:

- **CC**: coverage cutoff;
- **CCF**: coverage cutoff with flexible core/boundary fields;
- **ML**: maximum-likelihood flexible universe;
- **HMM**: hidden-state model over start/core/end coverage.

Primary source: Rymuza et al. (2024), *Methods for constructing and evaluating
consensus genomic interval sets*,
doi:[10.1093/nar/gkae685](https://doi.org/10.1093/nar/gkae685).

The paper motivates and evaluates these methods; it does not make one method
universally best. Choose using training-only data, assay-specific validation,
resource constraints, and held-out universe-fit metrics.

## Non-negotiable input contract

All source BED files and chromosome sizes must agree on:

- assembly/accession and patch;
- 0-based half-open BED coordinates;
- chromosome/contig naming and inclusion policy;
- sort order;
- duplicate and overlap handling;
- strand interpretation;
- liftover provenance, if any.

Reject malformed rows, negative starts, `end <= start`, coordinates beyond
contig length, unknown contigs, mixed assemblies, and integer overflow before
coverage generation. A chromosome name match alone is not proof of assembly
compatibility.

Build the universe only from the training patients/donors. If samples from a
held-out patient contribute to coverage, the resulting vocabulary leaks test
feature prevalence.

```bash
python skills/geniml/scripts/corpus_auditor.py \
  --manifest data/train_manifest.tsv \
  --group-column patient_id \
  --split-column split \
  --assembly-column assembly
```

## Coverage prerequisites

Geniml consumes bigWig tracks in a local coverage directory. With the default
prefix `all`, methods expect:

```text
all_start.bw
all_core.bw
all_end.bw
```

CC and CCF read `all_core.bw`. HMM and likelihood-based methods use
start/core/end tracks. The tracks must share contigs and lengths with the
checksummed chromosome-sizes file. CC, CCF, and HMM cast coverage to uint16:
require finite nonnegative integer counts no greater than 65,535. Fractional
coverage is truncated and larger counts can wrap. Do not feed normalized
BigWigs into these methods without verifying the required count semantics.

Official Geniml pages describe producing these tracks with the ecosystem's
coverage tooling, but the current Gtars CLI has changed across releases. Do not
emit or run a guessed `uniwig` command. Pin the exact Gtars/uniwig executable,
capture its `--help`, and smoke-test its output naming on synthetic local BED
data. Record:

- tool version and binary SHA-256;
- complete argv (not a shell-expanded wildcard);
- chromosome-sizes SHA-256;
- ordered input manifest and checksums;
- smoothing/binning parameters;
- output track sizes, contigs, lengths, and checksums.

The bundled planner validates local inputs and emits the Geniml stage, but
intentionally marks coverage generation as an external prerequisite:

```bash
python skills/geniml/scripts/consensus_plan.py \
  --manifest data/train_manifest.tsv \
  --chrom-sizes refs/GRCh38.chrom.sizes \
  --assembly GRCh38 \
  --method cc \
  --cutoff 2 \
  --output-dir work/consensus
```

It does not execute Geniml, Gtars, native binaries, or network requests.

## Exact 0.8.4 CLI

All shown CLI forms were checked against installed help. CC was executed on a
synthetic BigWig; CCF, likelihood/ML, HMM, and assessment are source-verified
illustrative templates, not completed end-to-end workflows in this review.

The top-level command is `build-universe`, not `universe build`.

### CC

```bash
geniml build-universe cc \
  --coverage-folder /absolute/project/coverage \
  --coverage-prefix all \
  --output-file /absolute/project/universe_cc.bed \
  --cutoff 2 \
  --merge 100 \
  --filter-size 50
```

`--cutoff` is an integer. If omitted, release source uses mean base coverage
for each chromosome. `--merge` merges nearby output segments; `--filter-size`
removes shorter segments. The output file must not already exist.
A tiny count-track smoke produced the exact expected BED interval. In contrast,
all-zero selected positions, 0.5-valued tracks, and 65,536-valued tracks
reproduced empty-selection IndexError failures. The release can leave partial
output if a later chromosome fails; reconcile every requested chromosome.

`merge=0, filter_size>0` enters the merging implementation and can split
adjacent covered bases into individual bases. Until that upstream behavior is
corrected, build with both zero and perform a separately validated BED
length-filter/merge step when precise gap semantics matter.

Do not claim `cutoff=number_of_files` is a strict sample intersection unless
coverage generation contributes exactly one unit per sample at each base.
Fragment/read coverage or duplicated intervals can violate that assumption.

Python:

```python
from geniml.universe.cc_universe import cc_universe

cc_universe(
    cove="work/coverage",
    file_out="work/universe_cc.bed",
    cove_prefix="all",
    merge=100,
    filter_size=50,
    cutoff=2,
)
```

### CCF

```bash
geniml build-universe ccf \
  --coverage-folder /absolute/project/coverage \
  --coverage-prefix all \
  --output-file /absolute/project/universe_ccf.bed
```

Python:

```python
from geniml.universe.ccf_universe import ccf_universe

ccf_universe(
    cove="work/coverage",
    file_out="work/universe_ccf.bed",
    cove_prefix="all",
)
```

The stable source has no CCF `--confidence`, `--merge`, or `--filter-size`
arguments. CCF writes BED9-like rows carrying core/boundary information; do
not reduce them to BED3 before confirming downstream semantics.

### Likelihood model and ML universe

The 0.8.4 likelihood command has no `build_model` subcommand:

```bash
geniml lh \
  --model-file /absolute/project/model.tar \
  --coverage-folder /absolute/project/coverage \
  --coverage-prefix all \
  --file-no 4
```

Then:

```bash
geniml build-universe ml \
  --model-file /absolute/project/model.tar \
  --coverage-folder /absolute/project/coverage \
  --coverage-prefix all \
  --output-file /absolute/project/universe_ml.bed
```

Python:

```python
from geniml.likelihood.build_model import main as build_likelihood
from geniml.universe.ml_universe import ml_universe

build_likelihood(
    model_file="work/model.tar",
    coverage_folder="work/coverage",
    coverage_prefix="all",
    file_no=4,
)
ml_universe(
    model_file="work/model.tar",
    cove_folder="work/coverage",
    cove_prefix="all",
    file_out="work/universe_ml.bed",
)
```

Treat the `.tar` likelihood model as an untrusted archive if it is not locally
created and checksummed. Inspect archive member names and reject absolute
paths, `..`, links, devices, and excessive expansion before extraction.

### HMM

```bash
geniml build-universe hmm \
  --coverage-folder /absolute/project/coverage \
  --coverage-prefix all \
  --output-file /absolute/project/universe_hmm.bed
```

Use `--not-normalize` only after validating what scale the model expects.
`--save-max-cove` adds maximum coverage information. The 0.8.4 CLI has no
`--states` argument; the model structure is defined in source constants.

Python:

```python
from geniml.universe.hmm_universe import hmm_universe

hmm_universe(
    coverage_folder="work/coverage",
    out_file="work/universe_hmm.bed",
    prefix="all",
    normalize=True,
    save_max_cove=False,
)
```

## Validate every output

Universe builders do not replace input validation. After construction:

1. Re-run BED validation against the same chromosome sizes.
2. Confirm sorted, nonempty output and expected BED column count.
3. Check region count, length distribution, covered bases, overlaps, and
   duplicate coordinates.
4. Confirm no unknown contigs or out-of-bounds ends.
5. Record output SHA-256 and method parameters.
6. Build a fresh Gtars tokenizer and record vocabulary/special-token sizes.
7. Never reorder the universe after a model or token corpus has been created.

Some 0.8.4 functions assume at least one selected base per chromosome and may
index an empty result. Test sparse/empty chromosomes synthetically and fail
closed rather than accepting a partial output.

## Assess fit to held-out collections

The release CLI is:

```bash
geniml assess-universe \
  --raw-data-folder /absolute/project/validation_beds \
  --file-list /absolute/project/validation_files.txt \
  --universe /absolute/project/universe_cc.bed \
  --overlap \
  --distance \
  --distance-universe-to-file \
  --folder-out /absolute/project/assessment \
  --pref validation \
  --no-workers 4
```

Available flags include:

- `--overlap`;
- `--distance`;
- `--distance-flexible`;
- `--distance-universe-to-file`;
- `--distance-flexible-universe-to-file`;
- `--save-to-file`;
- `--save-each`.

`--save-each` can generate large, sensitive per-interval outputs. Leave it off
unless required and bound output size. The docs still show `geniml assess`;
that is not the 0.8.4 top-level command.

Python entry points include:

```python
from geniml.assess.assess import (
    get_f_10_score,
    get_mean_rbs,
    run_all_assessment_methods,
)
```

F10, reciprocal-boundary-style distance summaries, and likelihood measure
different properties. Compare multiple candidate universes on validation
patients, then evaluate the chosen one once on test patients. Do not tune the
cutoff, merging, or method on the test collection.

## Reproducibility record

Store:

- ordered input manifest and grouping;
- assembly/accession, chromosome sizes, coordinate and contig policy;
- every input and coverage checksum;
- exact coverage and Geniml argv;
- Geniml, Gtars, pyBigWig, NumPy, HMM, Python, OS, and architecture versions;
- method, cutoff/model, prefix, normalization, merge/filter parameters;
- output and assessment checksums;
- exclusions, failures, empty contigs, and liftover losses.

Keep file names and sample labels redacted in portable reports.

## Migration corrections

Remove or correct these stale patterns:

- `geniml universe build ...` → `geniml build-universe ...`;
- `geniml universe evaluate ...` → `geniml assess-universe ...`;
- CCF `--confidence` → not present in 0.8.4;
- HMM `--states` → not present in 0.8.4;
- ML `--model-type gaussian|poisson` → not present in 0.8.4;
- generic `build_universe(...)` → not exported by the stable universe module;
- claims that a fixed percentage coverage is universally appropriate.

## Official sources

- [Official consensus CLI guide](https://docs.bedbase.org/geniml/tutorials/create-consensus-peaks)
  (undated; accessed 2026-10-01)
- [Official consensus Python guide](https://docs.bedbase.org/geniml/notebooks/create-consensus-peaks-python)
  (undated; accessed 2026-10-01)
- [Official universe assessment guide](https://docs.bedbase.org/geniml/tutorials/assess-universe/)
  (undated; fetch failed 2026-10-01; release source checked)
- [Geniml v0.8.4 universe source](https://github.com/databio/geniml/tree/v0.8.4/geniml/universe)
  (released 2026-01-14; accessed 2026-10-01)
- [Primary consensus-universe paper](https://doi.org/10.1093/nar/gkae685)
  (2024)
