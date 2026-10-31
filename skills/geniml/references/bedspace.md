# BEDspace

Verified against `geniml==0.8.4` release source, the official BEDbase tutorial,
and the archived StarSpace repository on 2026-10-01.

## Status

BEDspace jointly embeds region sets and metadata labels using the external
StarSpace program. The primary paper evaluates label-to-region,
region-to-label, and region-to-region retrieval.

Primary source: Gharavi et al. (2024), *Joint representation learning for
retrieval and annotation of genomic interval sets*,
doi:[10.3390/bioengineering11030263](https://doi.org/10.3390/bioengineering11030263).

The code path still exists in Geniml 0.8.4, but it is a **legacy reproduction
workflow**:

- StarSpace is not a Python dependency and must be compiled separately.
- `facebookresearch/StarSpace` is archived.
- Geniml does not state or enforce a compatible StarSpace version.
- several official examples and 0.8.4 CLI/API details disagree;
- with Gtars 0.10.0, `data_preparation` calls the removed
  `unknown_token_id()` API and assumes token objects instead of BatchEncoding;
  its broad exception handler prints an error and returns a blank document;
- the eight-worker preprocessing pool passes a Rust Tokenizer between workers;
  native pickling/process compatibility needs separate verification;
- the 0.8.4 `bedspace search` dispatcher imports a `main` function that is
  absent from `geniml.bedspace.search`.

Do not choose BEDspace by default for a new production search service. Use it
when reproducing the published method or an existing pinned workflow, and
record the limitations.

## Data and privacy contract

Required inputs:

- a local directory of validated BED files;
- a local metadata CSV with a file-path/name column and selected label columns;
- a local universe BED;
- explicit train/test manifests grouped by patient/donor;
- one assembly, coordinate convention, and contig policy.

Metadata values can reveal diagnoses, cell types, tissues, treatment, cohort,
or donor identity. BEDspace places selected labels directly into training text
and writes filenames/labels into result CSVs. Keep inputs and outputs in a
restricted project directory. Default logs should report only row/file counts
and schema names, not values.

Before preprocessing:

1. Split complete patients/donors into train/validation/test.
2. Build or select the universe using training data only.
3. Validate every BED and the universe against the same chromosome sizes.
4. Confirm metadata path values resolve to intended local regular files.
5. Reject URLs, symlinks, duplicate paths, missing files, and mixed assemblies.
6. Decide how missing/multi-valued labels are encoded.

```bash
python skills/geniml/scripts/corpus_auditor.py \
  --manifest data/bedspace.tsv \
  --group-column patient_id \
  --split-column split \
  --assembly-column assembly
```

## Exact 0.8.4 CLI surface

The release exposes:

```text
geniml bedspace preprocess
geniml bedspace train
geniml bedspace distances
geniml bedspace search
```

The following are source/parser-checked reproduction templates, not a working
pipeline on the current stack. The synthetic `data_preparation` call was
executed and returned a blank document for valid input. Resolve that upstream
compatibility failure and verify nonempty documents before training; a zero
exit status or file presence is insufficient. StarSpace was not built or run.
Use installed `--help` as the final authority for flags.

### Preprocess

```bash
geniml bedspace preprocess \
  --input /absolute/project/beds/ \
  --metadata /absolute/project/train.csv \
  --universe /absolute/project/universe.bed \
  --labels "cell_type,target" \
  --output /absolute/project/preprocessed/
```

The implementation creates a Gtars `Tokenizer` from the universe, uses a
hard-coded pool of eight processes, and writes:

```text
<output>train_input.txt
```

The code joins this filename by string concatenation, not `os.path.join`, so
the output argument must end in a path separator. The metadata helper also
concatenates the input directory and `file_name`, so `--input` and `--files`
need trailing separators. Use the exact `file_name` metadata column; commas
in path/label values are not preserved by its split-based representation. Create and validate the
directory first. The preprocessing text contains labels and tokenized genomic
content; protect it as sensitive derived data.

The current source does not expose worker bounds through the CLI. Run only
after estimating memory and CPU impact, or invoke a reviewed wrapper that
controls resources.

### Train

The long source flag is misspelled:

```text
--path-to-starsapce
```

Use the stable short form `-s`. Its value must be the **directory containing**
the executable named `starspace`; despite some help text, do not pass the
executable itself.

```bash
geniml bedspace train \
  -s /absolute/project/vendor/StarSpace \
  --input /absolute/project/preprocessed/train_input.txt \
  --output /absolute/project/model/ \
  --dim 100 \
  --epochs 50 \
  --lr 0.05
```

Geniml invokes an argv list equivalent to:

```text
starspace train
  -trainFile INPUT
  -model OUTPUT/starspace_trained_model
  -trainMode 0
  -dim DIM
  -epoch EPOCHS
  -negSearchLimit 5
  -thread 20
  -lr LEARNING_RATE
```

The thread count is hard-coded to 20. The implementation waits for the process
but does not check a nonzero return code. Verify output existence, size, and
checksums yourself. If an existing model path is present, Geniml adds
`-initModel` and resumes/mutates training; use a fresh output directory unless
resume is intentional.

### Distances

```bash
geniml bedspace distances \
  -i /absolute/project/model/starspace_trained_model \
  -s /absolute/project/vendor/StarSpace \
  --metadata-train /absolute/project/train.csv \
  --metadata-test /absolute/project/test.csv \
  --universe /absolute/project/universe.bed \
  --project-name heldout \
  --files /absolute/project/beds/ \
  --labels "cell_type,target" \
  --output /absolute/project/distances/ \
  --threshold 0.5
```

The current outputs are CSV/text files, not a single pickle:

- `raw_cosdist_rl.csv`
- `similarity_score_rl.csv`
- `similarity_score_rr.csv`
- `<project>_starspace_embed.txt`
- `<project>_train_starspace_embed.txt`

The implementation also uses `~/.bedspace/test_documents.txt` and
`~/.bedspace/train_documents.txt`. Use an isolated user account/environment or review that cache before
running on sensitive data. Output CSVs contain filenames and labels; never
paste unredacted rows into chat or CI logs.

### Search

The CLI advertises search types `l2r`, `r2l`, and `r2r`, with the query as a
positional argument:

```text
geniml bedspace search QUERY -t l2r -d DISTANCES.csv -n 10
```

Do not rely on this path in 0.8.4: the dispatcher imports
`geniml.bedspace.search.main`, but the release file defines only
`run_scenario1`, `run_scenario2`, and `run_scenario3`. There is no
`BEDSpaceModel` class in the release API. Read the verified CSVs with a safe
local data-frame workflow instead of loading an old `.pkl` or calling the
broken dispatcher.

## StarSpace setup: explicit legacy-only baseline

Only do this after the user approves network access and native compilation.
There is no upstream Geniml compatibility pin. The only immutable baseline
available from the archived upstream default branch is its final commit:

```text
8aee0a950aa607c023e5c91cff518bec335b5df5
```

A reproducible source checkout is:

```bash
git init vendor/StarSpace
git -C vendor/StarSpace remote add origin https://github.com/facebookresearch/StarSpace.git
git -C vendor/StarSpace fetch --depth 1 origin 8aee0a950aa607c023e5c91cff518bec335b5df5
git -C vendor/StarSpace checkout --detach FETCH_HEAD
make -C vendor/StarSpace
```

This pin makes the source immutable; it does **not** establish compatibility
with Geniml 0.8.4. Compile in an isolated build environment after reviewing
the archived source and Boost/native toolchain. Record:

- commit and repository URL;
- compiler, make, Boost, OS, and architecture;
- build log;
- SHA-256 and executable permissions of `vendor/StarSpace/starspace`;
- a synthetic preprocess/train/distances smoke result.

Never execute an unverified StarSpace binary downloaded from a third party.
Do not add its directory globally to `PATH`; pass the explicit local directory
with `-s`.

## Model and retrieval provenance

Keep one immutable manifest covering:

- Geniml/Gtars and StarSpace versions/commit;
- Python lockfile and native binary checksum;
- train/test manifest checksums and grouping;
- universe checksum, assembly, row order, and tokenizer special tokens;
- selected metadata columns and missing-value policy;
- preprocessing text checksum;
- dimension, epochs, learning rate, hard-coded thread count, and resume state;
- every model/embedding/distance output checksum.

Similarity is not a calibrated probability. Validate retrieval on held-out
patients/donors, report per-query metrics and class support, and compare with
metadata-only and interval-overlap baselines. Avoid searching the test set
while selecting labels, thresholds, or the universe.

## Migration guidance

Old guidance to remove:

- `BEDSpaceModel.load(...)` / `.search(...)`: not present in 0.8.4.
- `distances.pkl`: current distance code writes CSV/text.
- `--path-to-starspace`: official docs show it, but release source spells the
  long flag `--path-to-starsapce`; use `-s`.
- advice to install StarSpace from an unpinned branch.

For new systems, first define the retrieval task and privacy boundary. A
maintained vector-search stack over locally generated, fully versioned
embeddings may be safer than building new infrastructure around archived
StarSpace, but it is not automatically method-equivalent to BEDspace.

## Official sources

- [Official BEDspace tutorial](https://docs.bedbase.org/geniml/tutorials/bedspace/)
  (undated; accessed 2026-10-01)
- [Geniml v0.8.4 BEDspace source](https://github.com/databio/geniml/tree/v0.8.4/geniml/bedspace)
  (released 2026-01-14; accessed 2026-10-01)
- [Archived StarSpace repository](https://github.com/facebookresearch/StarSpace)
  (final default-branch commit dated 2019-12-13; repository archived; accessed
  2026-10-01)
- [Primary BEDspace paper](https://doi.org/10.3390/bioengineering11030263)
  (2024)
