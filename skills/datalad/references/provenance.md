# Computational provenance with DataLad

## Why this is the interesting half

Version control tells you that a file changed. Provenance tells you what produced it, from
what, and with which software. `datalad run` captures all three in the same commit that
carries the change, which means the evidence cannot drift away from the result. `datalad
rerun` then reads that record back and re-executes it, so "is this reproducible" becomes a
command rather than an argument.

## Project layout: YODA

YODA ("YODAs Organigram on Data Analysis") is the layout convention DataLad analyses are
built on. Three principles:

- **P1, one thing one dataset.** Data, code, environments, and results live in dedicated
  modular datasets rather than one directory of everything.
- **P2, record where you got it from and where it is now.** Input data enters as a
  subdataset cloned from its source, so its origin and version are recorded rather than
  described.
- **P3, record what you did to it and with what.** Every derived file is produced by a
  tracked command, not by an unrecorded interactive session.

Apply it at creation time:

```bash
datalad create -c yoda "my_analysis"
```

That produces:

```text
.
├── .gitattributes
├── CHANGELOG.md
├── code
│   ├── .gitattributes
│   └── README.md
└── README.md
```

The configuration matters more than the directories. Everything in `code/`, plus
`README.md` and `CHANGELOG.md`, is tracked by Git rather than git-annex, so scripts stay
directly readable and diffable in a clone that has fetched no data at all. Input data is
then added as a subdataset:

```bash
datalad clone -d . https://github.com/OpenNeuroDatasets/ds000001.git inputs/raw
```

The `-d .` is what registers the clone as a subdataset of the analysis rather than leaving
an unrelated repository sitting inside it.

## datalad run

```
datalad run [-h] [-d DATASET] [-i PATH] [-o PATH] [--expand {inputs|outputs|both}]
    [--assume-ready {inputs|outputs|both}] [--explicit] [-m MESSAGE]
    [--sidecar {yes|no}] [--dry-run {basic|command}] [-J NJOBS]
    [--version] ...
```

| Option | Documented behaviour | Practical consequence |
|---|---|---|
| `-i/--input PATH` | "A dependency for the run. Before running the command, the content for this relative path will be retrieved." | The command does not fail on an unfetched pointer, and `rerun` knows what to fetch elsewhere |
| `-o/--output PATH` | "Prepare this relative path to be an output file of the command." | Unlocks or removes the target so git-annex write protection does not block the write |
| `--explicit` | "Consider the specification of inputs and outputs to be explicit. Don't warn if the repository is dirty." | Lets a run proceed in a dirty dataset, and saves only the declared outputs |
| `--assume-ready {inputs\|outputs\|both}` | "Assume that inputs do not need to be retrieved and/or outputs do not need to unlocked or removed." | Skips preparation for speed; only safe when you have already done it |
| `--expand {inputs\|outputs\|both}` | "Expand globs when storing inputs and/or outputs in the commit message." | Records the concrete file list rather than the glob, which is what you want when the glob's meaning could change |
| `--dry-run {basic\|command}` | "Do not run the command; just display details about the command execution." | Check placeholder expansion before committing anything |
| `--sidecar {yes\|no}` | Store the run record in a separate file rather than in the commit message | Keeps long records out of `git log` output |

Placeholders available in the command string: `{pwd}` (current working directory),
`{dspath}` (dataset path), `{tmpdir}` (a temporary directory), `{inputs}` and `{outputs}`
(the values of the corresponding flags), and `{inputs[0]}` for indexed access.

Globs are permitted in `--input` and `--output`, and multiple flags may be given:

```bash
datalad run -m "second-level model" \
  -i "derivatives/sub-*/func/*_bold.nii.gz" \
  -i "code/model.py" \
  -o "results/group_map.nii.gz" \
  --expand inputs \
  "python code/model.py {outputs}"
```

### The run record

The commit message carries a machine-readable JSON block between the markers
`=== Do not change lines below ===` and `^^^ Do not change lines above ^^^`. It records
the command, the dataset ID, the exit status, and the input and output specifications. The
handbook is explicit that this section is "less for the human user" and exists "for
DataLad, in particular for the `datalad rerun` command". Editing it by hand, including
during an interactive rebase, breaks `rerun` silently.

Two behaviours that surprise people:

- A run producing no change to the dataset produces no commit at all, exactly as a
  `datalad save` with nothing to save does. An empty history entry is not evidence the run
  failed to execute, only that it changed nothing.
- `datalad run` refuses to start in a dirty dataset. This is the point of the command: a
  record built on an unknown starting state does not establish anything. Save or discard
  first, or state the scope with `--explicit`.

## datalad rerun

```
datalad rerun [-h] [--since SINCE] [-d DATASET] [-b NAME] [-m MESSAGE] [--onto base]
    [--script FILE] [--report] [--assume-ready {inputs|outputs|both}] [--explicit]
    [-J NJOBS] [--version] [REVISION]
```

- `REVISION` selects which recorded command to replay and defaults to `HEAD`.
- `--since SINCE` replays a range: "the commands from all commits that are reachable from
  revision but not SINCE will be re-executed (in other words, the commands in
  `git log SINCE..REVISION`)". This is how a multi-step pipeline is replayed in order.
- `--onto base` gives the "start point for rerunning the commands. If not specified,
  commands are executed at HEAD." Use `--onto ''` to replay from the state each command
  originally ran on.
- `-b/--branch NAME` creates and checks out a branch before replaying.
- `--report` displays what would be done without executing, which is the safe first call.
- `--script FILE` extracts the commands to a file instead of running them, with `-` for
  stdout. This is how a DataLad history becomes a plain shell script for a reviewer or a
  cluster submission.

The reproducibility check worth building into a project:

```bash
datalad rerun --report --since <first-analysis-commit> HEAD    # inspect the plan
datalad rerun -b repro-check --since <first-analysis-commit> HEAD
git diff main repro-check -- results/                          # empty means reproduced
```

Rerunning onto a branch keeps the original results intact while the replay lands
elsewhere, so a mismatch is a finding rather than a lost result.

## Containers

`datalad-container` (PyPI `datalad-container`, currently 1.2.x) records the software
environment alongside the command.

```
datalad containers-add [-h] [-u URL] [-d DATASET] [--call-fmt FORMAT]
    [-i IMAGE] [--update] [--extra-input FILE] [--version] NAME
```

Supported URL schemes:

- `shub://` for Singularity Hub, for example `shub://neurodebian/dcm2niix:latest`.
- `docker://` for Docker images pulled through Singularity, for example
  `docker://debian:stable-slim`.
- `dhub://`, where "the rest of the URL will be interpreted as the argument to
  `docker pull`". Docker execution is configured automatically, mounting the working
  directory to `/tmp` and setting the working directory there.

For `shub://` and `docker://`, a Singularity-based call format is configured
automatically unless `--call-fmt` overrides it. `--call-fmt` is what you change to add
bind mounts, environment variables, or GPU flags that a given image needs.

```
datalad containers-run [-h] [-n NAME] [-d DATASET] [-i PATH] [-o PATH] [-m MESSAGE]
    [--expand {inputs|outputs|both}] [--explicit] [--sidecar {yes|no}] [--version] ...
```

`-n/--name` selects "the name of or a path to a known container to use for execution, in
case multiple containers are configured". With exactly one container configured it may be
omitted. During execution the environment variable `DATALAD_CONTAINER_NAME` holds the name
of the container in use, which is available to the command itself.

The image is tracked in the dataset like any other file, so it is annexed content: a
collaborator gets it with `datalad get` and the provenance record points at a specific
image rather than at a tag someone may have re-pushed.

## Exporting provenance to a standard form

DataLad's run records are DataLad's own format. Converting them to an interoperable
representation is an open area rather than a solved one, and this is worth stating plainly
rather than implying a pipeline exists:

- **W3C PROV** is the standard target for provenance interchange. See
  <https://www.w3.org/TR/prov-overview/>.
- **datalad-metalad** ships a `runprov` extractor that reads DataLad run records, at
  <https://github.com/datalad/datalad-metalad/blob/master/datalad_metalad/extractors/runprov.py>.
  It exists but is not in active use, so treat it as a starting point to validate rather
  than a supported path.
- **BIDS BEP028** is bringing PROV support into the BIDS specification, at
  <https://bids.neuroimaging.io/bep028>. For a BIDS derivatives dataset this is where
  exported provenance would eventually belong.

Until one of those is settled, the durable artifact is the DataLad history itself plus
`datalad rerun --script`, which produces a plain, reviewable command sequence that does
not depend on DataLad to read.

## Further reading

- `datalad run` chapter of the handbook:
  <https://handbook.datalad.org/en/latest/basics/101-108-run.html>
- YODA principles: <https://handbook.datalad.org/en/latest/basics/101-127-yoda.html>
- datalad-container documentation:
  <https://docs.datalad.org/projects/container/en/stable/>
- Git worktree workflows with DataLad:
  <https://blog.datalad.org/posts/git-worktree-workflow/>
