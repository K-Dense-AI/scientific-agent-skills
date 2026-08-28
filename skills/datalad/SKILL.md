---
name: datalad
description: Discover, retrieve, and version scientific datasets with DataLad, and capture computational provenance so analyses can be re-executed verbatim. Use when working with OpenNeuro or DANDI datasets, registry.datalad.org, git-annex-backed data, datalad clone/get/drop, or when a workflow needs reproducible execution records via datalad run, rerun, or containers-run.
license: MIT
compatibility: Requires Python 3.10+ with datalad (tested with 1.6.2) and git. git-annex is required to retrieve annexed file content (most published datasets). containers-run needs the datalad-container extension plus Docker or Apptainer/Singularity. Needs network access for discovery, cloning, and downloads.
metadata:
  version: "1.0"
  skill-author: ayobamiseun
---

# DataLad

DataLad manages datasets as git repositories in which large or binary file *content* is
tracked by git-annex and fetched on demand, while text and code live in git directly.
Datasets nest (a superdataset links subdatasets at exact versions), and every command a
dataset was produced by can be recorded in the git history and re-executed later. This
skill covers three jobs: **finding** published datasets, **getting** their content, and
**capturing provenance** so results are reproducible.

## When to use

- The data lives on OpenNeuro, DANDI, or another DataLad-published source, or the user
  mentions DataLad, git-annex, `datalad run`, or registry.datalad.org.
- Terabyte-scale collections must be browsed and fetched file-by-file instead of
  downloaded wholesale.
- An analysis should carry a machine-readable record of exactly which command, inputs,
  and outputs produced each result (`datalad run` / `datalad rerun` /
  `datalad containers-run`).

**When not to use:** plain code repositories (use git), uploading to DANDI (use the
`dandi` CLI), or one-off downloads where no versioning or provenance is wanted.

Check the environment first — most failures are missing system dependencies, not usage
errors:

```bash
datalad --version        # pip/uv install datalad
git annex version        # from your OS package manager, e.g. brew install git-annex
```

Without git-annex, cloning an annexed dataset fails outright (`install(error)` —
DataLad 1.6.2 requires git-annex >= 10.20230126). Install git-annex before touching
published datasets; only `--no-annex` datasets work without it.

## Finding datasets

- **DataLad Registry** — <https://registry.datalad.org> indexes ~25k datasets (DANDI,
  OpenNeuro, and other annexed or plain-git repositories). The web UI accepts free-text
  and fielded queries (`url:github`, quoted phrases, `AND`/`OR`/`NOT`, parentheses).
  There is no core CLI search: `datalad search` moved to the `datalad-deprecated`
  extension, so do not suggest it.
- **OpenNeuro** — every accession is a DataLad dataset at
  `https://github.com/OpenNeuroDatasets/<accession>`, e.g. `ds000001`. Browse or search
  accessions at <https://openneuro.org>.
- **DANDI** — every dandiset is mirrored at `https://github.com/dandisets/<id>`, e.g.
  `000003`. Search at <https://dandiarchive.org>.
- The superdataset <https://datasets.datalad.org> (clonable as `///`) aggregates many
  neuroscience collections as nested subdatasets.

## Getting data

Clone cheaply, then fetch only the content you need:

```bash
datalad clone https://github.com/OpenNeuroDatasets/ds000001.git
cd ds000001

datalad get sub-01/                  # fetch content for one directory
datalad get -n -r .                  # install nested subdatasets, no file content (-n)
datalad get -J 4 sub-0*/anat         # parallel jobs
datalad drop sub-01/                 # free local space; content stays retrievable
datalad status                       # what is modified / untracked
```

`get` is idempotent and resumable; `drop` refuses to remove content it cannot re-obtain
unless forced (`--reckless availability` — avoid). For a whole nested collection,
`datalad clone` + `datalad get -n -r` first, inspect, then `get` the leaves you need.
The equivalent Python API mirrors the CLI:

```python
import datalad.api as dl
ds = dl.clone("https://github.com/OpenNeuroDatasets/ds000001.git", path="ds000001")
ds.get("sub-01/")
```

## Creating a dataset

```bash
datalad create -c text2git my-analysis   # text files in git, binaries annexed
cd my-analysis
# ... add code and data ...
datalad save -m "raw inputs and analysis script"
```

`-c text2git` keeps scripts and small text outputs directly editable; without it,
annexed files are locked read-only symlinks until `datalad unlock`. Use
`datalad create --no-annex` only for pure-text datasets on machines without git-annex.
To ingest a remote file *with* provenance, prefer `datalad download-url <URL>` over
curl + save: it records the source URL so the file remains re-obtainable after `drop`.

Register an existing published dataset as input to yours (version-pinned nesting, the
YODA layout):

```bash
datalad clone -d . https://github.com/OpenNeuroDatasets/ds000001.git inputs/ds000001
```

## Capturing provenance: `datalad run`

Wrap any shell command; DataLad fetches declared inputs, runs it, and commits changed
outputs together with a structured record:

```bash
datalad run -m "count words" \
  -i input.txt \
  -o counts.txt \
  "wc -w input.txt > counts.txt"
```

The commit message carries a machine-readable block:

```text
[DATALAD RUNCMD] count words

=== Do not change lines below ===
{
 "cmd": "wc -w input.txt > counts.txt",
 "dsid": "6be75724-52cf-47c1-b145-eeb74a90b3fe",
 "exit": 0,
 "inputs": ["input.txt"],
 "outputs": ["counts.txt"],
 "pwd": "."
}
^^^ Do not change lines above ^^^
```

Rules that matter:

- Run from a **clean dataset** (`datalad status` empty) — otherwise unrelated
  modifications are swept into the provenance commit. `--explicit` relaxes this and
  saves only declared outputs; use it deliberately, since undeclared side effects are
  then silently untracked.
- Declare `-i`/`-o` even when the command would find the files anyway: inputs are
  `get`-ed first (so reruns work on fresh clones) and outputs are unlocked before
  execution (so annexed results can be overwritten).
- Glob patterns work: `-i "sub-*/anat/*.nii.gz"`.
- `--dry-run basic` previews what would run and where without executing.
- A failing command (nonzero exit) leaves outputs uncommitted; fix and rerun — do not
  `datalad save` a half-finished result by hand.

## Re-executing: `datalad rerun`

```bash
datalad rerun HEAD          # repeat the run recorded in the last commit
datalad rerun <shasum>      # repeat a specific recorded run
datalad rerun --since=v1.0  # replay every run since a tag/commit
datalad rerun --report HEAD # show the record without executing
datalad rerun --script analysis.sh --since= HEAD   # export all runs as a shell script
```

`rerun` re-executes the recorded command against current content: if inputs changed, a
new result commit is produced; if results are identical, DataLad notes there was
nothing new to save. `--onto` and `--branch` replay runs onto another starting point
for verification. This is the check that a result is actually regenerable — run it
before claiming an analysis is reproducible.

## Containers: fully portable provenance

Shell commands rerun exactly only where the same software exists. The
`datalad-container` extension pins the compute environment into the dataset itself.
Install `datalad-container`; execution additionally needs Docker or
Apptainer/Singularity on the machine. The command forms below match the extension's
CLI, but treat the specific image and script names as illustrative:

```bash
datalad containers-add nilearn --url docker://nilearn/nilearn:latest
datalad containers-list
datalad containers-run -n nilearn -m "first-level GLM" \
  -i inputs/ds000001/sub-01 \
  -o results/sub-01 \
  "python code/glm.py sub-01"
```

`containers-add` stores (and annexes) the image in the dataset; `containers-run` is
`datalad run` with the command executed inside that image, so the run record includes
the container. A later `datalad rerun` on another machine retrieves both data *and*
environment. Singularity/Apptainer images travel best (single annexed file); Docker
image layers are stored under `.datalad/environments/` and re-loaded on demand.

## Caveats and checks

- **git-annex absent** is the most common failure mode: `clone` of any annexed dataset
  errors immediately. Diagnose with `git annex version`.
- **Locked files**: writing to an annexed file fails with "permission denied" — use
  `datalad run -o` (auto-unlocks) or `datalad unlock <file>`.
- **Nested datasets**: `datalad status`/`save` operate on one dataset level; pass `-r`
  (recursive) or `-d <superdataset>` when results span subdatasets. After changing a
  subdataset, `datalad save` in the superdataset records the new pinned version.
- **Do not edit** the `=== Do not change lines ===` block in run commits; `rerun`
  parses it.
- Provenance records are only as complete as the declared `-i`/`-o` — audit a rerun on
  a fresh `datalad clone` of the dataset to prove the record is self-contained.
- DataLad run records can be exported toward W3C PROV via `datalad-metalad`'s
  `metalad_runprov` extractor, and BIDS provenance is being standardized as BEP028 —
  relevant when a consumer asks for standards-based provenance rather than git history.

## References

- Handbook (task-oriented): <https://handbook.datalad.org> — "Basics: Run" chapter
  covers `run`/`rerun`; "Computational reproducibility with software containers"
  covers `containers-run`.
- Command reference: <https://docs.datalad.org>
- YODA principles for analysis layout: `datalad create -c yoda`, described in the
  handbook's "YODA: Best practices" chapter.
