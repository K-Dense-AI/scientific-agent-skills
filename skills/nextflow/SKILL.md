---
name: nextflow
description: Build, run, and debug Nextflow data pipelines and nf-core workflows end to end. Use whenever the user mentions Nextflow, nf-core, .nf files, nextflow.config, DSL2, processes/channels/operators, samplesheets, or wants to run a community pipeline (e.g. nf-core/rnaseq, nf-core/sarek), write or test a module/subworkflow with nf-test, configure executors/containers (Docker, Singularity/Apptainer, Conda, Wave), scale a workflow to HPC/SLURM or cloud (AWS Batch, Google Batch, Azure, Kubernetes), or debug a failed/-resume run. Make sure to use this skill for any reproducible scientific/bioinformatics workflow work even if the user does not say the word "Nextflow", and for authoring nf-core-compliant pipelines, modules, configs, and linting.
license: Apache-2.0
metadata: {"version": "1.0", "skill-author": "K-Dense Inc."}
---

# Nextflow

## Overview

Nextflow is a workflow language and runtime for building **reproducible, portable, scalable** data pipelines. It is dominant in bioinformatics but works for any data-heavy computation. nf-core is a community curating production-grade Nextflow pipelines, reusable modules, and the `nf-core` tooling on top of Nextflow.

Key ideas:
- **Dataflow programming**: pipelines are `process` tasks connected by **channels**. Nextflow infers execution order and parallelism from data dependencies — there is no explicit scheduler to write.
- **Write once, run anywhere**: the same pipeline runs locally, on HPC (SLURM, SGE, LSF, PBS), and on cloud (AWS Batch, Google Batch, Azure Batch, Kubernetes) by changing config/profiles, not code.
- **Reproducibility**: per-task containers (Docker/Singularity/Apptainer/Conda/Wave) + `-resume` caching + pinned pipeline revisions.
- **DSL2** is the modern, required syntax: modular `process`/`workflow`/`include` definitions.

This skill covers both **running** existing pipelines and **developing** your own (Nextflow language + nf-core conventions, testing with nf-test, configuration, and deployment).

## When to Use This Skill

Use this skill when the user wants to:
- Run an nf-core or custom Nextflow pipeline, or debug a failing/resuming run.
- Write or modify `.nf` scripts, `nextflow.config`, profiles, or `nextflow_schema.json`.
- Author or test nf-core-style modules/subworkflows (`main.nf`, `meta.yml`, `tests/`, nf-test).
- Configure executors, containers, or resources; scale to HPC or cloud.
- Build a reproducible scientific/bioinformatics workflow (even if "Nextflow" is not named).
- Understand processes, channels, operators, `take`/`emit`, `publishDir`, `ext.args`, meta maps.

## Setup

Nextflow needs **Bash** and **Java 17 or newer** (17–25 supported). Verify with `java -version`.

```bash
# Install Nextflow (self-contained launcher)
curl -s https://get.nextflow.io | bash      # creates ./nextflow
sudo mv nextflow /usr/local/bin/             # put on PATH
nextflow info                                # verify

# Or via conda/bioconda (also gets a managed Java)
conda create -n nf -c bioconda -c conda-forge nextflow nf-core
```

```bash
# nf-core tools (Python) for creating/linting/running nf-core assets
pip install nf-core            # or: conda install -c bioconda nf-core
nf-core --version
```

Pin the engine for reproducibility: `export NXF_VER=24.10.0` (use an [edge] release only if needed). For air-gapped/HPC, see `references/running-pipelines.md` (offline mode) and `references/configuration.md`.

## Two Modes of Work

Decide which path the user is on — it changes everything:

| Goal | Start here |
|------|-----------|
| **Run** an existing pipeline (nf-core or a `.nf` you were given) | `references/running-pipelines.md` |
| **Develop** a new pipeline / module / subworkflow | `references/language.md` + `references/developing.md` |
| **Configure / scale** (HPC, cloud, containers, resources) | `references/configuration.md` + `references/containers.md` |
| **Test** modules/pipelines | `references/testing.md` |

## Quick Start

### Run an nf-core pipeline

Always smoke-test with the bundled `test` profile first; it uses tiny data and proves your environment works.

```bash
# 1. Confirm setup works (downloads pipeline + tiny test data)
nextflow run nf-core/rnaseq -profile test,docker --outdir results

# 2. Real run: pin a revision (-r), pick a container engine, pass inputs
nextflow run nf-core/rnaseq -r 3.14.0 \
  -profile docker \
  --input samplesheet.csv \
  --genome GRCh38 \
  --outdir results \
  -resume
```

- `-profile` (single dash) selects bundled config profiles; **combine** them comma-separated, e.g. `test,docker`. Container/infra profiles (`docker`, `singularity`, `conda`) are mutually exclusive — pick one.
- `--input`, `--genome`, `--outdir` (double dash) are **pipeline** parameters. nf-core pipelines take a **samplesheet CSV**, not loose files.
- `-resume` reuses cached results from the last run. `-r <version>` pins a release for reproducibility.

Use `nf-core pipelines launch <name>` for an interactive, schema-validated way to build the command and a `-params-file`. See `references/running-pipelines.md`.

### Write a minimal pipeline

```nextflow
#!/usr/bin/env nextflow

process SAYHELLO {
    tag "$greeting"
    publishDir "results", mode: 'copy'

    input:
    val greeting

    output:
    path "${greeting}.txt"

    script:
    """
    echo '$greeting world' > ${greeting}.txt
    """
}

workflow {
    channel.of('hello', 'bonjour', 'hola') | SAYHELLO
}
```

```bash
nextflow run main.nf            # add -resume on reruns
```

The full language (processes, channels, operators, DSL2 workflows with `take`/`main`/`emit`, modules) is in `references/language.md`.

## Core Concepts at a Glance

- **Process**: a unit of work that runs a script (Bash by default). Declares `input:`, `output:`, optional `directives` (resources, container, `publishDir`, `tag`, `errorStrategy`), and a `script:`/`shell:`/`exec:` block. Each task runs in its own isolated work directory (`work/xx/yy…`).
- **Channel**: the async queues that connect processes. **Queue channels** are consumable streams; **value channels** hold a single reusable value. Created with factories like `channel.of`, `channel.fromPath`, `channel.fromFilePairs`, `channel.value`.
- **Operator**: transforms/combines channels — `map`, `filter`, `collect`, `groupTuple`, `join`, `combine`, `mix`, `flatten`, `branch`, `multiMap`, `splitCsv`, `view`, `set`.
- **Workflow**: composes processes. DSL2 workflows can declare `take:` (inputs), `main:` (logic), `emit:` (named outputs) and be `include`d as subworkflows. The unnamed `workflow {}` is the entry point.
- **Module**: a `.nf` file exposing processes/workflows via `include { NAME } from './path'` (supports `as` aliasing).
- **Configuration**: `nextflow.config` sets `params`, `process` directives, `executor`, container engines, and named `profiles`. Selectors `withName:`/`withLabel:` target specific processes. See `references/configuration.md`.
- **meta map** (nf-core): the convention of carrying a metadata map (`[ id:'sample1', single_end:false ]`) alongside files in input/output tuples so samples stay labeled through the pipeline. See `references/developing.md`.

## nf-core tools CLI

nf-core tools (v3+) group subcommands under `pipelines`, `modules`, and `subworkflows`. (Bare forms like `nf-core lint` still work but warn — prefer the grouped form.)

| Command | Purpose |
|---------|---------|
| `nf-core pipelines list` | List/search nf-core pipelines (`--json`, keywords) |
| `nf-core pipelines create` | Scaffold a new pipeline from the nf-core template |
| `nf-core pipelines launch <name>` | Interactive, schema-driven run command + params file |
| `nf-core pipelines download <name>` | Download pipeline + containers for offline/HPC use |
| `nf-core pipelines lint` | Lint a pipeline against nf-core standards (run in repo root) |
| `nf-core pipelines schema build` | Build/edit `nextflow_schema.json` via web GUI |
| `nf-core pipelines create-params-file <name>` | Generate a documented YAML params file |
| `nf-core pipelines bump-version` / `sync` | Bump version / sync with template updates |
| `nf-core modules list/info/install/update/remove` | Manage modules from nf-core/modules |
| `nf-core modules create` / `lint` / `test` | Author, lint, and nf-test a module |
| `nf-core modules patch` / `bump-versions` | Patch an installed module / bump tool versions |
| `nf-core subworkflows install/create/lint/test` | Same lifecycle for subworkflows |

Full command reference, flags, and examples: `references/nf-core-tools.md`.

## Essential `nextflow` CLI

| Command | Purpose |
|---------|---------|
| `nextflow run <pipeline> -profile <p> --outdir <dir>` | Run a pipeline (path, `.nf`, or `user/repo`) |
| `-resume` | Reuse cached results from prior run |
| `-r <rev>` | Run a specific git revision/tag/branch |
| `-params-file params.yml` | Supply parameters from YAML/JSON |
| `-c custom.config` | Layer in an extra config file |
| `-with-report -with-trace -with-timeline -with-dag flow.html` | Execution report, trace, timeline, DAG |
| `-stub-run` | Run `stub:` blocks only (dry-run plumbing) |
| `nextflow log` | Inspect past runs |
| `nextflow clean -f -before <run>` | Delete old `work/` data |
| `nextflow pull / drop / list / info <repo>` | Manage cached remote pipelines |

Config, executors, caching internals, and tracing details: `references/configuration.md`.

## Best Practices (high-value habits)

- **Always `test` first**: `-profile test,docker` (or `singularity`/`conda`) before real data — fast and catches environment problems.
- **Pin everything**: pipeline revision (`-r`), `NXF_VER`, and tool versions (containers). Don't run `latest` for science you'll publish.
- **Use `-resume`** and understand caching: a task re-runs if its inputs, script, or container change. See cache-debugging in `references/configuration.md`.
- **Parameterize via config/params-file**, not hardcoded paths. Keep `params` and profiles in `nextflow.config`.
- **One container/conda env per process**; never rely on tools installed on the host.
- **For nf-core dev**: reuse existing modules (`nf-core modules install`) before writing new ones; pass tool flags through `ext.args` (not hardcoded in the script); always include a `stub:` block and nf-test tests; run `nf-core pipelines lint` and `prettier` before committing.
- **Right-size resources** with `process_low/medium/high` labels and `errorStrategy 'retry'` with dynamic `task.attempt` scaling instead of one giant request.
- **Write forward-compatible syntax**: the strict-syntax parser becomes the default in Nextflow 26.04. Prefer lowercase `channel.of(...)`, explicit closure params (`{ v -> ... }`), `def` for all variables, and `emit:`-named outputs. Check with `nextflow lint`.

## Reference Files

Read the relevant file when you need depth — each is self-contained:

- `references/language.md` — DSL2 language: processes, directives, channels, operators, workflows (`take`/`emit`), modules, dynamic resources, error handling.
- `references/configuration.md` — `nextflow.config`, scopes, `profiles`, `withName`/`withLabel` selectors, executors (local/SLURM/cloud), caching/`-resume` internals, tracing/reports, the `nextflow` CLI.
- `references/containers.md` — Docker, Singularity/Apptainer, Podman, Conda, Wave containers; choosing and enabling engines; common gotchas.
- `references/running-pipelines.md` — finding/running nf-core pipelines, samplesheets, params files, reference genomes (iGenomes), offline runs, institutional configs, Seqera Platform.
- `references/nf-core-tools.md` — complete `nf-core` CLI reference (pipelines/modules/subworkflows), flags, and workflows.
- `references/developing.md` — authoring nf-core pipelines & modules: template layout, module `main.nf`/`meta.yml`, meta maps, `ext.args`/`modules.config`, subworkflows, resource labels, linting & Harshil alignment style.
- `references/testing.md` — nf-test for modules/subworkflows/pipelines: test structure, assertions, snapshots, tags, running tests, CI.

Official docs: Nextflow https://www.nextflow.io/docs/latest/ · nf-core https://nf-co.re/docs/ · Training https://training.nextflow.io/
