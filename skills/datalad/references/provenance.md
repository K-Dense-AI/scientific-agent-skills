# Computational provenance with DataLad

## Why this is the interesting half

Version control tells you that a file changed. Provenance tells you what produced it, from
what, and with which software. `datalad run` captures all three in the same commit that
carries the change, which means the evidence cannot drift away from the result. `datalad
rerun` then reads that record back and re-executes it, so "is this reproducible" becomes a
command rather than an argument.

## Principles: STAMPED, and the YODA layout it grew out of

YODA ("YODAs Organigram on Data Analysis") is the convention DataLad analyses were
originally built on, and it is still what `datalad create -c yoda` configures. Its three
principles (one thing one dataset, record where the data came from, record what was done
to it) describe what a well-formed analysis looks like, but they were inspirational rather
than operational: there is nothing in them to check a dataset against.

STAMPED (<https://stamped-principles.org>) is the operationalized successor, formalized by
some of the original YODA authors. It states seven properties of a reproducible research
object, each backed by normative MUST/SHOULD/MAY requirements:

| Property | Core requirement |
|---|---|
| **S**elf-contained | Everything essential to replicate the computation is reachable within a single top-level research object |
| **T**racked | Persistent content identification and provenance are recorded for every component and every modification, including the versions involved |
| **A**ctionable | The object carries enough instruction to reproduce all results, specified as *executable* specifications rather than prose |
| **M**odular | Components are organized as independently versioned modules, included directly or linked as subdatasets |
| **P**ortable | Procedures depend on no undocumented host state; environments are explicitly specified and version controlled |
| **E**phemeral | Results are produced in disposable environments built only from the object's own contents |
| **D**istributable | Every referenced module and component is persistently retrievable by others |

**Actionable is the property `datalad run` exists to satisfy.** A README describing how a
figure was produced is documentation; a run record is an executable specification, and
`datalad rerun` is what makes it executable. The same commit satisfies Tracked, because
the command, its inputs, its outputs, and the versions they were taken at are recorded
next to the change rather than in a separate log that can drift away from it. Modular maps
onto subdatasets, Portable and Ephemeral onto `containers-run`, and Distributable onto
siblings and RIA stores (see [publishing.md](publishing.md)).

Two companion resources make this checkable rather than aspirational:
<https://checklist.stamped-principles.org> walks the requirements as a MUST/SHOULD/MAY
checklist, and <https://examples.stamped-principles.org> collects worked patterns,
including ones built directly on `datalad run` and `datalad rerun`.

### The normative requirements

Each property is a spectrum rather than a pass/fail gate, and its requirements carry RFC 2119
weights: MUST is the practical minimum a careful project usually already meets, SHOULD and MAY are
progressively more tool-assisted. Grade an object requirement by requirement, citing the evidence
behind each grade rather than the impression.

| Item | Weight | Requirement |
|---|---|---|
| S.1 | MUST | Every module essential to replicating the execution is reachable within one top-level research object, either literally or by explicit reference |
| S.2 | MUST | License declarations are retrievable alongside what they govern |
| T.1 | MUST | Persistent content identification is recorded for all components |
| T.2 | SHOULD | All components use the same content-addressed version control system |
| T.3 | MUST | The provenance of all modifications is recorded |
| T.4 | SHOULD, MUST | Code-driven provenance is captured programmatically (SHOULD), and it MUST include the versions of the components involved |
| A.1 | MUST | Instructions sufficient to reproduce all results are present |
| A.2 | SHOULD | Those procedures are executable specifications rather than prose |
| M.1 | SHOULD | Components are organised modularly |
| M.2 | MAY | Modules are included directly or linked as subdatasets |
| M.3 | SHOULD | Each module declares its own license, checked for compatibility where modules combine |
| P.1 | MUST NOT | Procedures depend on undocumented host state |
| P.2 | MUST | Computational environments are explicitly specified |
| P.3 | MUST | Environment definitions are version controlled |
| E.1 | SHOULD | Results are produced in ephemeral environments rebuilt from those specifications |
| D.1 | MUST | All referenced modules are persistently retrievable by others |
| D.2 | SHOULD | Environment specifications support reproducible builds |
| D.3 | SHOULD | Each module carries an explicit license with a resolvable identifier |

The `S.1`-style labels are shorthand for walking the list in order, not identifiers taken from the
specification; <https://checklist.stamped-principles.org> is the authority for the wording and the
weights.

### Where the evidence lives

Every requirement above is checkable against a DataLad dataset with read-only commands. Nothing in
this table writes to the dataset.

| Property | What satisfies it | How to look |
|---|---|---|
| **S** | inputs registered as subdatasets rather than copied in, a top-level `README`, and a `LICENSE` beside the content it covers | `datalad subdatasets -r`, `cat .gitmodules`, `git annex whereis <path>` for content that lives elsewhere |
| **T** | git history for structure, annex keys for content, run records for modifications | `git log --oneline`, `git log --oneline --grep '\[DATALAD RUNCMD\]'` to count run records, `git annex whereis --json <path>` for recorded locations |
| **A** | replayable run records, not a prose README | `datalad rerun --report <rev>` on the commits that produced results; if that finds nothing, A.2 is unmet however good the README is |
| **M** | `code/`, `inputs/`, `outputs/` separated, each linked module keeping its own history and license | `datalad subdatasets -r`, `git ls-files` for the layout, per-module `LICENSE` |
| **P** | an environment specification tracked in Git, and commands that name no host-specific path | `git ls-files \| grep -Ei 'dockerfile\|environment.ya?ml\|requirements.txt\|pyproject.toml'`, `datalad containers-list`, and a read of the recorded commands for absolute paths outside the dataset |
| **E** | results produced by `containers-run` against a registered image rather than by ambient tools | `datalad containers-list`, and whether the run records are `containers-run` invocations |
| **D** | a sibling that others can actually reach, and content that is really there | `datalad siblings`, `git remote -v`, `git annex whereis --json <path> \| jq '.whereis \| length'` |

Grep the commit subject rather than the run record markers. With `--sidecar yes`, or with
`datalad.run.record-sidecar` set, the record itself is written to the dataset's `.datalad/runinfo`
directory instead of into the commit message, but the `[DATALAD RUNCMD]` subject is there either
way.

`datalad containers-list` needs the `datalad-container` extension; without it installed the command
does not exist, which is itself evidence about P and E. Where `datalad` is unavailable altogether,
every probe above except `subdatasets`, `containers-list`, and `rerun --report` has a plain Git or
git-annex equivalent, so a git-only assessment is still possible at reduced confidence — say so in
the readout rather than reporting a gap you could not probe for.

### Ephemeral and Distributable in practice

These are the two properties a DataLad dataset is least likely to satisfy by accident, because
neither follows from committing carefully.

**Ephemeral (E.1)** asks that results come out of an environment rebuilt from specification, not
out of whatever was installed on the machine that ran the analysis. `containers-run` is the
mechanism: the documentation states that "the container image itself will be recorded as an input
dependency of the command execution in the RUN record in the git history", so the record pins the
image as annexed content addressed by key rather than as a tag someone can re-push under. A
`Dockerfile` or `environment.yml` tracked in the dataset that *builds* that image is stronger still,
because it satisfies P.2 and P.3 as well and gives D.2 something to reproduce from.

One name collision worth heading off: `datalad clone --reckless ephemeral` has nothing to do with
this property. It symlinks the clone's annex to the origin's and marks the clone dead to git-annex,
which is a disk and inode optimisation for throwaway compute; it says nothing about how the
environment was built.

**Distributable (D.1)** fails most often in a way that looks like success. `datalad push --data`
defaults to `auto-if-wanted`, so a push that reports success can move the history and none of the
content, leaving a sibling that clones cleanly and then cannot deliver a single byte. Check the
result rather than the exit status:

```bash
datalad push --to store --data anything
git annex whereis --json <path> | jq '.whereis | length'   # more than the local annex?
```

Persistence is the other half, and a sibling on a lab server is not persistence. A RIA store keeps
the full history and annex in one addressable place (see [publishing.md](publishing.md)); for an
archived snapshot with an identifier, `datalad export-archive` writes a TAR or ZIP of the dataset
content and `datalad export-to-figshare` pushes one to figshare, which is where a DOI enters. D.3
then asks that the license carry a resolvable identifier: an SPDX identifier from
<https://spdx.org/licenses/>, or the REUSE conventions at <https://reuse.software> when modules are
licensed individually, which is also what makes M.3 checkable.

### Assessing an existing dataset

Assessment is read-only. Never `save`, `run`, `push`, or edit while grading: a report that mutates
the object it grades invalidates itself.

1. Confirm the target is a dataset at all (`.datalad/` present, or at least a Git repository), and
   report the resolved path.
2. Run the probes in the evidence table, collecting what each one shows and what it fails to show.
3. Walk S.1 through D.3, marking each item satisfied, partial, or unmet against that evidence. An
   unmet MUST outranks any number of unmet SHOULDs when ordering the result.
4. Report per property, with the evidence attached, and lead with the shape of it — "strong on S, T,
   and M, weak on P, E, and D" is the sentence a reader acts on:

   | Property | Grade | Evidence | Gap |
   |---|---|---|---|
   | S Self-contained | partial | inputs are subdatasets (`.gitmodules`) | no top-level README |
   | T Tracked | satisfied | 14 run records in history | — |

5. If a remediation plan is wanted, order it by weight and make every step a command:
   results with no run record → re-run under `datalad run` or `containers-run`; no environment
   specification → add one and `containers-add` the image; inputs copied in → `datalad clone -d .`
   into `inputs/`; no license → add one with an SPDX identifier; nothing published → `datalad push`
   to a sibling or RIA store, then archive for a DOI.

### The YODA layout in practice

Apply the layout at creation time:

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
- STAMPED principles (operationalized from YODA): <https://stamped-principles.org>
  - Compliance checklist: <https://checklist.stamped-principles.org>
  - Worked examples and stencils: <https://examples.stamped-principles.org>
- datalad-container documentation:
  <https://docs.datalad.org/projects/container/en/stable/>
