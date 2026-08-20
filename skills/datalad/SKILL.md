---
name: datalad
description: Retrieve, version, and publish scientific datasets with DataLad and git-annex, and capture computational provenance with datalad run, rerun, and containers-run. Use when cloning or fetching data from OpenNeuro, DANDI, datasets.datalad.org, or any DataLad dataset; when a file in a dataset reads as a broken symlink or a small pointer instead of real data; when an analysis needs a machine-readable record of how each output was produced so it can be re-executed; or when publishing a dataset to siblings such as a GitHub repository plus a storage remote. Also use to decide between DataLad and plain Git for a data-carrying repository.
compatibility: Needs datalad 1.6.x on Python 3.10+, plus git and git-annex 8.20200309 or newer. git-annex is not written in Python but installs from PyPI (uv pip install git-annex), a system package manager, or conda-forge. Container-based provenance also needs the datalad-container extension (1.2.x) and Singularity/Apptainer or Docker. clone, get, and push need network access; credentialed remotes read secrets from the system keyring or from DATALAD_CREDENTIAL_<NAME>_<COMPONENT> environment variables.
license: MIT
allowed-tools: Read Write Edit Bash
metadata:
  version: "1.0"
  skill-author: Dylan Pulver
---

# DataLad

## Overview

DataLad is a data management layer over Git and git-annex. Git tracks the dataset
structure, small text files, and the history. git-annex tracks the *content* of large
files, storing each file as a key and keeping the bytes somewhere that is not necessarily
the local repository.

That split is the single most important thing to internalise, because it means a freshly
cloned dataset contains the full history and the full file listing while containing almost
none of the data. A 100 TB dataset clones in seconds and occupies a few megabytes. The
bytes arrive only when asked for, per file, with `datalad get`.

The second thing DataLad adds is provenance. `datalad run` executes a command and commits
the result together with a machine-readable record of the command, its inputs, and its
outputs. `datalad rerun` reads that record back and re-executes it. This turns "how was
this figure produced" from an archaeology problem into a command.

## When to use DataLad instead of plain Git

Use DataLad when any of the following holds:

- Files are too large for Git to handle comfortably, or the total exceeds what every
  collaborator wants on disk.
- Data lives in more than one place (a lab server, a cluster scratch, S3, a supercomputer)
  and you need to know which copies exist.
- The analysis must be re-executable, and a plain commit message is not enough evidence.
- You are consuming published datasets from OpenNeuro, DANDI, or `datasets.datalad.org`,
  which are distributed as DataLad datasets.
- The project nests other datasets inside it and you want each one to keep its own
  independent history.

Use plain Git when the repository is code and text only, everything fits comfortably in
Git, and nobody needs partial checkouts. DataLad on top of a small pure-code repository
adds indirection without buying anything.

## Installation

```bash
# git-annex is NOT written in Python but is available from PyPI if you already
# have git itself installed:
uv pip install git-annex
# You can also install it first from the system
# (Debian/Ubuntu: apt install git-annex; macOS: brew install git-annex;
#  conda-forge: conda install -c conda-forge git-annex)
uv pip install datalad
uv pip install datalad-container   # only for containers-run

datalad wtf --section dependencies   # confirm git-annex version is visible
```

The PyPI `git-annex` package ships the prebuilt binary as a wheel for Linux, macOS, and
Windows rather than building the Haskell sources, so it installs like any other Python
dependency and can be pinned in the same environment as DataLad. It does not bring git
along with it.

`datalad wtf` prints the resolved environment and is the first thing to run when behaviour
looks impossible. An old or missing git-annex is behind a large share of confusing errors.

DataLad itself is MIT licensed. git-annex is a separate tool under the AGPL, which matters
only if you redistribute a modified git-annex rather than call it.

## The failure that bites first: pointers are not data

After `datalad clone`, annexed files exist as symlinks into `.git/annex/objects/` (or as
small pointer files where symlinks are unavailable, such as on Windows or a crippled
filesystem). Nothing has downloaded the content yet.

```bash
datalad clone https://github.com/OpenNeuroDatasets/ds000001.git
cd ds000001
ls sub-01/anat/            # the file is listed
python -c "import nibabel; nibabel.load('sub-01/anat/sub-01_T1w.nii.gz')"   # fails
datalad get sub-01/anat/sub-01_T1w.nii.gz                                   # now it works
```

The failure mode to recognise: a tool reports the file as empty, truncated, corrupt, "not
a gzip file", or a broken symlink, and the file size on disk is a few hundred bytes. That
is a pointer, not a corrupted download. **Run `datalad get` before reading data, and treat
"file exists" as insufficient evidence that its content is present.**

Before an analysis touches a directory, fetch it explicitly:

```bash
datalad get sub-01/                  # everything under a path
datalad get -r .                     # everything, including subdatasets
datalad get -n -r .                  # subdataset structure only, no file content
```

`datalad status --annex` reports how much content is present locally, and
`git annex whereis <path>` reports which repositories hold a given file. `whereis` reads
recorded state and does not contact the remotes, so it tells you what git-annex last
learned rather than what is true right now.

See [data-access.md](references/data-access.md) for finding datasets, subdataset
behaviour, dropping content safely, and repairing a dataset.

## Recording provenance with datalad run

`datalad run` is the reason to reach for DataLad in a methods context. It saves the
command alongside its effect, in the same commit:

```bash
datalad run -m "extract brain mask" \
  --input "sub-01/anat/sub-01_T1w.nii.gz" \
  --output "derivatives/sub-01_brain.nii.gz" \
  "bet {inputs} {outputs} -m"
```

What each part does, and why skipping it hurts:

- `--input` retrieves the content before running, so the command does not fail on a
  pointer. It also records the dependency, which is what lets `rerun` fetch the same
  inputs on a different machine.
- `--output` unlocks or removes the target first, so git-annex does not refuse to write
  over content it is protecting. Without it, a second run of the same command commonly
  fails with a permission error on an annexed file that looks read-only.
- `{inputs}` and `{outputs}` expand to those values. `{pwd}`, `{dspath}`, and `{tmpdir}`
  are also available, and `{inputs[0]}` indexes individual entries.
- The commit message carries a JSON run record between `=== Do not change lines below ===`
  and `^^^ Do not change lines above ^^^`. Do not hand-edit that block; `rerun` parses it.

`datalad run` refuses to start when the dataset has unsaved modifications, because an
unclean starting state makes the record unreliable. Save or discard first, or pass
`--explicit` to declare that the listed inputs and outputs are the complete story. Check a
command before committing to it with `--dry-run basic` or `--dry-run command`.

A run that changes nothing produces no commit, exactly as `datalad save` does.

### Re-executing

```bash
datalad rerun                       # redo the run recorded at HEAD
datalad rerun --report              # show what would be done, change nothing
datalad rerun --script recompute.sh # extract the commands instead of running them
datalad rerun --since <commit> -b check <revision>   # replay a range onto a new branch
```

Rerunning onto a branch (`-b`) is the safe way to test reproducibility: the replay lands
somewhere else, and a diff against the original branch answers whether the outputs came
back identical.

### Containers

With the `datalad-container` extension, register an image once and every subsequent run
records which image produced the outputs:

```bash
datalad containers-add fsl --url docker://brainlife/fsl:6.0.4
datalad containers-run -n fsl -m "brain mask in container" \
  --input "sub-01/anat/sub-01_T1w.nii.gz" \
  --output "derivatives/sub-01_brain.nii.gz" \
  "bet {inputs} {outputs} -m"
```

The image itself is tracked in the dataset, so the software environment travels with the
data and the provenance record rather than living in someone's shell history. When only
one container is configured, `-n` may be omitted.

See [provenance.md](references/provenance.md) for the STAMPED principles and the YODA
project layout, the run record format, `--explicit` and `--assume-ready` semantics, and
exporting provenance toward W3C PROV.

## Saving and inspecting changes

```bash
datalad status                 # what changed, including subdataset state
datalad save -m "add QC report" path/to/file
datalad save -m "checkpoint" -r                 # recurse into subdatasets
datalad save -m "small text file" --to-git notes.md
```

`datalad save` decides per file whether content goes to Git or to git-annex, following the
dataset's `.gitattributes`. Force a file into Git with `--to-git`, which is the right call
for code and small text files that should stay directly readable. The `yoda` procedure
(`datalad create -c yoda`) sets this up for `code/`, `README.md`, and `CHANGELOG.md`
automatically.

## Publishing

A DataLad dataset is usually published to two places at once: a Git hosting service for
the history, and a storage remote for the annexed content.

```bash
datalad create-sibling-github myaccount/mydataset
git annex initremote store type=S3 bucket=my-bucket encryption=none autoenable=true
datalad siblings configure -s github --publish-depends store
datalad push --to github
```

The two siblings are created by different tools because they are different kinds of thing.
The Git sibling holds history and is a Git remote, so DataLad creates it. The storage
sibling holds annexed content and is a git-annex special remote, which Git cannot talk to
at all, so `git annex initremote` creates it. `datalad siblings` lists it once it exists,
which is why the `configure --publish-depends` line below needs no special handling.
Passing an `s3://` URL to `datalad siblings add --url` instead produces a Git remote
pointing at a bucket, and the push then fails on the dependency hop.

`--publish-depends` is what stops the common broken publication: a Git repository whose
history references content that was never uploaded, so collaborators clone successfully
and then find every `datalad get` failing. Declaring the dependency makes the storage
sibling publish first, every time.

`datalad push` sends both the Git history and, by default (`--data auto-if-wanted`), the
annexed content the target is configured to want. Pass `--data anything` to push all
content regardless of the target's preferences.

See [publishing.md](references/publishing.md) for RIA stores, special remotes, credential
handling, and configuring which sibling holds what.

## Freeing disk space

```bash
git annex whereis sub-01/                 # confirm another copy exists first
datalad drop sub-01/                      # remove local content, keep the pointer
datalad drop --what all --reckless kill <path>   # last resort, destroys data
```

`datalad drop` refuses by default when it cannot verify another copy of the content
exists, which is a safety check rather than an obstacle. `--nocheck` and `--if-dirty` are
deprecated; the current spelling is `--reckless availability`, and it means what it says.
`--what` selects between `filecontent` (the default), `allkeys`, `datasets`, and `all`.

## Failure modes worth knowing

| Symptom | Cause | Fix |
|---|---|---|
| File reads as empty, truncated, or a broken symlink | Content not retrieved; only the pointer is present | `datalad get <path>` |
| "Permission denied" writing an existing output | git-annex write-protects annexed content | Declare it with `--output`, or `datalad unlock <path>` |
| `datalad run` refuses to start | Dataset has unsaved changes | `datalad save` first, or pass `--explicit` |
| `datalad drop` refuses | No verified second copy of the content | Push to a sibling first, or accept `--reckless availability` |
| Collaborator clones but every `get` fails | History published without the content | Publish the storage sibling, and set `--publish-depends` |
| Clone succeeds, subdataset directories are empty | Subdatasets are not installed by default | `datalad get -n -r .`, then `get` the paths you need |
| Commands behave impossibly | git-annex missing or too old | `datalad wtf --section dependencies` |

## Detailed references

- [data-access.md](references/data-access.md): finding published datasets
  (`registry.datalad.org`, OpenNeuro, DANDI, `datasets.datalad.org` and the `///`
  shortcut), clone and get options, subdataset handling, annex content states, dropping
  and removing, and `fsck` repair.
- [provenance.md](references/provenance.md): the STAMPED principles and the YODA layout,
  the run record format, `run` and `rerun` options in full, `containers-run`, and the
  current state of exporting DataLad provenance toward W3C PROV.
- [publishing.md](references/publishing.md): siblings and their actions,
  `create-sibling-*` variants, RIA stores, special remotes, `push` semantics, and
  credential handling.

## Related skills

The `bids` skill covers the Brain Imaging Data Structure that most of the neuroimaging
datasets distributed through DataLad are organised in. A typical workflow clones a BIDS
dataset with DataLad, validates it with the BIDS tooling, then runs a BIDS-App under
`datalad containers-run` so the derivatives carry provenance.

## Primary sources

- DataLad documentation: <https://docs.datalad.org/en/stable/>
- DataLad Handbook: <https://handbook.datalad.org/en/latest/>
- `datalad run` chapter: <https://handbook.datalad.org/en/latest/basics/101-108-run.html>
- YODA principles: <https://handbook.datalad.org/en/latest/basics/101-127-yoda.html>
- STAMPED principles (operationalized from YODA): <https://stamped-principles.org>
- datalad-container: <https://docs.datalad.org/projects/container/en/stable/>
- git-annex: <https://git-annex.branchable.com/>
- Dataset registry: <https://registry.datalad.org>
