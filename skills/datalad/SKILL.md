---
name: datalad
description: Retrieves, versions, and publishes scientific datasets with DataLad and git-annex, and captures computational provenance with datalad run, rerun, and containers-run. Use when cloning or fetching data from OpenNeuro, DANDI, datasets.datalad.org, or any DataLad dataset; when a file in a dataset reads as a broken symlink or a small pointer instead of real data; when an analysis needs a machine-readable record of how each output was produced so it can be re-executed; or when publishing a dataset to siblings such as a GitHub repository plus a storage remote. Also use to decide between DataLad and plain Git for a data-carrying repository.
compatibility: Requires Python 3.10+, DataLad 1.6.5, Git, and git-annex 10.x. Tested with git-annex 10.20260901 and datalad-container 1.2.6 on macOS ARM64. Containers additionally require Singularity, Apptainer, or Docker. Remote data access needs network access and may need provider credentials. Local filesystem workflows work offline.
license: MIT
allowed-tools: Read Write Edit Bash
metadata:
  version: "1.2"
  last-reviewed: "2026-09-30"
  skill-author: Dylan Pulver
---

# DataLad

## Overview

DataLad is a data management layer over Git and git-annex. Git tracks the dataset
structure, small text files, and the history. git-annex tracks the *content* of large
files, storing each file as a key and keeping the bytes somewhere that is not necessarily
the local repository.

A normal clone retrieves Git history and the top-level file listing while leaving
annexed bytes unfetched. Installed subdatasets have their own histories; a clone does not
automatically populate them. Clone cost depends on Git history and file count, not just
the data volume. Retrieve annexed bytes selectively with `datalad get`.

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
uv pip install "datalad==1.6.5"
uv pip install "datalad-container==1.2.6"   # only for containers-run

datalad wtf --section dependencies   # confirm git-annex version is visible
```

The PyPI `git-annex` package supplies platform-specific binaries. The reviewed
10.20260901.post1 wheels cover Linux glibc 2.34+ (x86_64/ARM64), macOS ARM64 14+ and
x86_64 15+, and Windows x86_64. Use a system package when no wheel matches. Keep its
environment on `PATH` and verify the executable; the wheel does not supply Git itself.
Configure Git author name/email before creating or saving a dataset.

`datalad wtf` prints the resolved environment and is the first thing to run when behaviour
looks impossible. An old or missing git-annex is behind a large share of confusing errors.

DataLad is MIT licensed; git-annex has a separate AGPL license. Consult the upstream
license when redistributing either tool.

## The failure that bites first: pointers are not data

After `datalad clone`, annexed files exist as symlinks into `.git/annex/objects/` (or as
small pointer files where symlinks are unavailable, such as on Windows or a crippled
filesystem). Nothing has downloaded the content yet.

Illustrative remote-data example; inspect the selected revision for the exact path and
install NiBabel before the Python read. The refresh tested equivalent local pointer/get
behavior without downloading imaging data.

```bash
datalad clone https://github.com/OpenNeuroDatasets/ds000001.git
cd ds000001
ls sub-01/anat/            # the file is listed
python -c "import nibabel; nibabel.load('sub-01/anat/sub-01_T1w.nii.gz')"   # fails
datalad get sub-01/anat/sub-01_T1w.nii.gz                                   # now it works
```

The failure mode to recognise: a tool reports the file as empty, truncated, corrupt, "not
a gzip file", or a broken symlink, and the file size on disk is a few hundred bytes. These symptoms can indicate an unfetched annex pointer; confirm with annex status
before diagnosing corruption. **Run `datalad get` before reading data, and treat
"file exists" as insufficient evidence that its content is present.**

Before an analysis touches a directory, fetch it explicitly:

```bash
datalad get sub-01/                  # everything under a path
datalad get -r .                     # everything, including subdatasets
datalad get -n -r .                  # subdataset structure only, no file content
```

`datalad status --annex availability` checks which content is present locally, and
`git annex whereis <path>` reports which repositories hold a given file. `whereis` reads
recorded state and does not contact the remotes, so it tells you what git-annex last
learned rather than what is true right now.

See [data-access.md](references/data-access.md) for finding datasets, subdataset
behaviour, dropping content safely, and repairing a dataset.

## Recording provenance with datalad run

`datalad run` is the reason to reach for DataLad in a methods context. It saves the
command alongside its effect, in the same commit:

Illustrative FSL example (requires `bet` and an existing `derivatives/` directory):

```bash
datalad run -m "extract brain and mask" \
  --input "sub-01/anat/sub-01_T1w.nii.gz" \
  --output "derivatives/sub-01_brain.nii.gz" \
  --output "derivatives/sub-01_brain_mask.nii.gz" \
  "bet {inputs[0]} {outputs[0]} -m"
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
`--explicit` to save only declared outputs. This does not capture unsaved input changes;
save all dependencies before claiming the run is reproducible. Check a
command before committing to it with `--dry-run basic` or `--dry-run command`.

A run that changes nothing produces no commit, exactly as `datalad save` does.

`run` records the command and dataset state; it does not freeze arbitrary host-installed software or external services. Version an environment lockfile and scripts as declared inputs, or use a tracked container image with `containers-run`. Record random seeds and relevant runtime settings, then test `rerun` from a fresh environment before claiming computational reproducibility.

### Re-executing

```bash
datalad rerun                       # redo the run recorded at HEAD
datalad rerun --report              # show what would be done, change nothing
datalad rerun --script recompute.sh # extract the commands instead of running them
datalad rerun --since <commit> -b check <revision>   # replay a range onto a new branch
```

`--report` only inspects the plan; it does not execute or validate the result. A branch
(`-b`) preserves the original commits, but uses the same worktree. See the reference for
a `--since`/`--onto` replay that starts before the first run, and compare annex keys or
content checksums as well as scientific outputs.

### Containers

With the `datalad-container` extension, register an image once and every subsequent run
records which image produced the outputs:

Illustrative container workflow using a previously built local SIF image (not executed
in this refresh; the runtime and image must be available):

```bash
datalad containers-add fsl --url /path/to/fsl.sif \
  --call-fmt 'apptainer exec {img} {cmd}'
datalad containers-run -n fsl -m "brain and mask in container" \
  --input "sub-01/anat/sub-01_T1w.nii.gz" \
  --output "derivatives/sub-01_brain.nii.gz" \
  --output "derivatives/sub-01_brain_mask.nii.gz" \
  "bet {inputs[0]} {outputs[0]} -m"
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

## Creating a dataset

```bash
datalad create my_dataset               # plain dataset
datalad create -c yoda my_analysis      # analysis layout (code/ tracked in Git,
                                        # README.md and CHANGELOG.md preconfigured)
datalad create -d . inputs/raw          # register a new subdataset under an existing one
```

`-c yoda` applies the analysis project layout described in
[provenance.md](references/provenance.md). `-d .` is what registers a new dataset as a
subdataset of the parent rather than leaving an unrelated repository inside it.

## Publishing

A DataLad dataset is usually published to two places at once: a Git hosting service for
the history, and a storage remote for the annexed content.

Illustrative authenticated publication (creates remote resources; requires a GitHub
token and S3 credentials). Use `myorg/mydataset` only for an organization namespace.

```bash
datalad create-sibling-github mydataset
git annex initremote store type=S3 bucket=my-bucket protocol=https \
  encryption=none autoenable=true
datalad siblings configure -s github --publish-depends store
datalad push --to github
```

The Git sibling and the storage sibling are created by different tools on purpose. A Git
sibling is a Git remote, and `datalad create-sibling-*` handles the hosting-service ones.
An S3 bucket (or WebDAV, or an SSH directory) is a *git-annex special remote*, not a Git
remote, so it is created with `git annex initremote`. `datalad siblings` picks the special
remote up afterwards and treats it like any other. Using `datalad siblings add --url
s3://...` here is the mistake this section exists to prevent: `--url` is a Git remote URL,
S3 is not, and the `push --to github` below then fails on the `--publish-depends` hop.

`--publish-depends` is what stops the common broken publication: a Git repository whose
history references content that was never uploaded, so collaborators clone successfully
and then find every `datalad get` failing. Declaring the dependency makes the storage
sibling publish first, every time.

`datalad push` sends both the Git history and, by default (`--data auto-if-wanted`), the
annexed content selected by a target's wanted settings; without wanted settings it
transfers all selected current content. `--data anything` bypasses preferred-content
filtering, but does not recover missing local bytes or archive every historical version.

See [publishing.md](references/publishing.md) for RIA stores, special remotes, credential
handling, and configuring which sibling holds what.

## Freeing disk space

```bash
git annex whereis sub-01/                 # inspect recorded locations first
datalad drop sub-01/                      # remove local content, keep the pointer
```

`datalad drop` checks required copies and availability by default. `--nocheck` is
deprecated in favor of `--reckless availability`, which disables those protections.
`--if-dirty` is deprecated and ignored; it is not an availability-check option.
`--what` selects between `filecontent` (the default), `allkeys`, `datasets`, and `all`.

## Failure modes worth knowing

| Symptom | Cause | Fix |
|---|---|---|
| File reads as empty, truncated, or a broken symlink | Content not retrieved; only the pointer is present | `datalad get <path>` |
| "Permission denied" writing an existing output | git-annex write-protects annexed content | Declare it with `--output`, or `datalad unlock <path>` |
| `datalad run` refuses to start | Dataset has unsaved changes | `datalad save` first, or pass `--explicit` |
| `datalad drop` refuses | No verified second copy of the content | Push to a reachable sibling, then retry the safety check |
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

## Validation scope

Reviewed 2026-09-30 against DataLad 1.6.5 and datalad-container 1.2.6 source and
current official manuals. Tiny local tests cover clone/get/drop, unlocked saves,
subdataset installation, run/rerun, default push selection, and RIA publish/clone/get.
Remote hosting, credentials, FSL, and container execution examples are illustrative;
no authenticated remote publication or scientific-data downloads were performed.

## Primary sources

- DataLad documentation: <https://docs.datalad.org/en/stable/>
- DataLad Handbook: <https://handbook.datalad.org/en/latest/>
- `datalad run` chapter: <https://handbook.datalad.org/en/latest/basics/101-108-run.html>
- YODA principles: <https://handbook.datalad.org/en/latest/basics/101-127-yoda.html>
- STAMPED principles (operationalized from YODA): <https://stamped-principles.org>
- datalad-container: <https://docs.datalad.org/projects/container/en/stable/>
- git-annex: <https://git-annex.branchable.com/>
- Dataset registry: <https://registry.datalad.org>

## Acknowledgment

Topic scope for this skill was informed in part by @bcmcpher's MIT-licensed
[datalad-cli](https://github.com/bcmcpher/my-skills/tree/main/plugins/datalad-cli)
plugin (nineteen per-command slash-command skills). The text here is written
independently and grounded in the upstream DataLad documentation; overlap is unavoidable
because both cover DataLad, but the structure, style, and specific technical claims are
different.
