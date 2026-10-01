# Developing nf-core Pipelines, Modules & Subworkflows

Conventions for building nf-core-compliant components. Reviewed against nf-core tools 4.1.0 templates and current [module specifications](https://nf-co.re/docs/specifications/components/modules/general). The small teaching wrapper was checked locally with SAMtools 1.24; container/Conda execution and full biological pipelines were not tested.

## Table of Contents

- [Pipeline directory layout](#pipeline-directory-layout)
- [The meta map convention](#the-meta-map-convention)
- [Anatomy of a module](#anatomy-of-a-module)
- [meta.yml](#metayml)
- [ext.args and modules.config](#extargs-and-modulesconfig)
- [Subworkflows](#subworkflows)
- [Resource labels and base.config](#resource-labels-and-baseconfig)
- [Schema and parameters](#schema-and-parameters)
- [Linting and the Harshil alignment style](#linting-and-the-harshil-alignment-style)

## Pipeline directory layout

`nf-core pipelines create` scaffolds this structure:

```
my-pipeline/
├── main.nf                     # entry: includes the main workflow
├── nextflow.config             # params defaults, profiles, includes conf/*
├── nextflow_schema.json        # parameter schema (validation + docs + launch GUI)
├── workflows/
│   └── mypipeline.nf           # the primary workflow (orchestrates subworkflows)
├── subworkflows/
│   ├── local/                  # pipeline-specific subworkflows
│   └── nf-core/                # installed shared subworkflows
├── modules/
│   ├── local/                  # pipeline-specific modules
│   └── nf-core/                # installed shared modules
├── conf/
│   ├── base.config             # default resources keyed by process_* labels
│   ├── modules.config          # per-process ext.args, publishDir (withName:)
│   ├── test.config             # tiny test profile inputs
│   └── igenomes.config         # reference genome keys
├── assets/                     # samplesheet schema, email templates, MultiQC config
├── bin/                        # executable helper scripts (on PATH in tasks)
├── docs/                       # usage.md, output.md, parameter docs
├── modules.json                # pins installed nf-core modules/subworkflows by SHA
└── .nf-core.yml                # tools config (lint rules, template features)
```

`main.nf` includes the workflow in `workflows/`; that workflow includes subworkflows and modules. Parameters are declared in `nextflow.config` + `nextflow_schema.json`; per-process behavior lives in `conf/modules.config`. Keep logic in workflows/modules, not in `main.nf`.

## The meta map convention

nf-core carries a **metadata map** alongside every sample's files in input/output tuples. This keeps samples labeled and lets `groupTuple`/`join` operate on the key as data flows through the pipeline.

```nextflow
// channel item shape:
[ [ id:'sample1', single_end:false ], [ sample1_R1.fastq.gz, sample1_R2.fastq.gz ] ]
```

- **Prefer `meta.id` and `meta.single_end`**. Current specifications also recognize `meta.strandedness`, but new modules SHOULD pass strandedness through `ext.args`; direct use is reserved for siblings of tools already following that convention.
- Inside a **module**, avoid custom hardcoded meta keys (the documented strandedness exception above is narrow); pass per-sample values in via `ext.args` from `conf/modules.config` instead (e.g. `ext.args = { "--strandedness ${meta.strandedness}" }`).
- The first meta in a tuple is named `meta`, the second `meta2`, etc. — not custom names.
- Outputs re-emit the **same `meta`** so downstream steps stay aligned: `tuple val(meta), path("*.bam")`.
- Build it from the samplesheet with `splitCsv` + `map` (see `references/language.md`). **Subworkflows** may create/emit new meta keys (document them in `meta.yml`).

Why it matters: decoupling metadata from module logic lets any pipeline name its metadata however it likes while reusing the same module unchanged.

## Anatomy of a module

A module lives in `modules/nf-core/<tool>/<subtool>/` (all lowercase, one command/subcommand per module) with these files:

```
modules/nf-core/samtools/sort/
├── environment.yml     # Conda channels + pinned deps
├── main.nf             # the process
├── meta.yml            # documented I/O + tools (schema-validated)
└── tests/
    ├── main.nf.test    # nf-test tests (required, incl. a stub test)
    └── main.nf.test.snap
```

`environment.yml` (pin the version, not the build):

```yaml
channels:
  - conda-forge
  - bioconda
dependencies:
  - bioconda::samtools=1.24
```

The following **BAM-only teaching wrapper** uses the current topic-version convention; it is not a copy of the installed nf-core `samtools/sort` module. The current upstream module takes three inputs (BAM tuple, reference tuple, index format). Inspect the installed `meta.yml` and pin its SHA before wiring modules together. Keep existing tool pins unless intentionally upgrading.

```nextflow
process SAMTOOLS_SORT {
    tag "$meta.id"                        // per-sample label
    label 'process_medium'                // exactly ONE bundled resource label (conf/base.config)

    conda "${moduleDir}/environment.yml"  // references the file above (NOT inline package strings)
    container "${ workflow.containerEngine in ['singularity', 'apptainer'] && !task.ext.singularity_pull_docker_container ?
        'https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/e9/e994bf4eb3731150511a14f5706b7bdfd64df1b6d40898fff334286c027e0859/data' :
        'community.wave.seqera.io/library/htslib_samtools:1.24--d697cfb9dce007cd' }"

    input:
    tuple val(meta), path(bam)            // meta map is ALWAYS the first tuple element

    output:
    tuple val(meta), path("*.bam"), emit: bam
    tuple val("${task.process}"), val("samtools"),
          eval('samtools --version | sed "1!d; s/samtools //"'),
          emit: versions_samtools, topic: versions

    when:
    task.ext.when == null || task.ext.when           // frozen line; gate via ext.when in config

    script:
    def args   = task.ext.args   ?: ''               // tool flags come from config, never hardcoded
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    samtools sort $args -@ $task.cpus -o ${prefix}.bam $bam

    """

    stub:                                            // required: each required file output is created
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    touch ${prefix}.bam
    """
}
```

Key module rules:
- **Both** `conda "${moduleDir}/environment.yml"` and `container` are declared for supported runtime profiles; this does not prove every image/architecture/engine combination works. Use the pinned image supplied by the reviewed module: current components may use Seqera Community/Wave images, while older ones use BioContainers/Galaxy depot. Preserve image digest/build and target architecture.
- Tool arguments are **not** hardcoded — they come from `task.ext.args` (and `args2`, `args3`, … for piped tools). The output filename prefix comes from `task.ext.prefix`; output names SHOULD be `${prefix}` + suffix.
- The `when:` line is boilerplate — never edit it; gate execution via `ext.when` in config.
- Always include a `stub:` block (touch ≥1 file per output channel; for gzip outputs use `echo '' | gzip > x.gz`, not bare `touch`).
- One tool/subcommand per module; no pipeline-specific logic; no reading `params.*` inside a module.

### Reporting tool versions (current vs legacy)

Current module specifications and tools 4.1.0 templates recommend **topic channels + `eval()`**, as shown above. The command executes in the task environment, including stub runs, so the version executable is still required. Template-based scripts may retain a HEREDOC `versions.yml`, but current specifications require `topic: versions` on that output. Older installed modules may expose only `out.versions`; preserve their interface until a tested coordinated migration.

The topic form emits a tuple, not a YAML file:

```nextflow
output:
tuple val("${task.process}"), val('samtools'),
      eval('samtools --version | sed "1!d; s/samtools //"'),
      topic: versions, emit: versions_samtools
```

The version string must start with a digit (strip a leading `v`). The pipeline gathers `channel.topic("versions")` and formats the records for its report. Do not wire a topic-consuming process back into the same topic. Inspect the installed interface: `out.versions_samtools` is not interchangeable with a legacy `out.versions` file.

## meta.yml

Machine-readable description of the module's interface (generated by `nf-core modules create`, validated by `nf-core modules lint`, used by `nf-core modules info` and docs). Current schema: `input` is a nested list (meta and its file are **separate** entries), `output` is a mapping keyed by `emit` name, each file entry carries an `ontologies` list, and each tool has an `identifier` (bio.tools ID where available):

```yaml
name: "samtools_sort"
description: Sort a BAM/CRAM/SAM file
keywords:
  - sort
  - bam
  - genomics
tools:
  - samtools:
      description: Tools for manipulating SAM/BAM/CRAM
      homepage: http://www.htslib.org/
      licence: ["MIT"]
      identifier: biotools:samtools
      args_id: "$args"
input:
  - - meta:
        type: map
        description: "Groovy Map with sample info, e.g. [ id:'test', single_end:false ]"
    - bam:
        type: file
        description: Input BAM/CRAM/SAM file
        pattern: "*.{bam,cram,sam}"
        ontologies: []
output:
  bam:
    - - meta:
          type: map
          description: Groovy Map with sample info
      - "*.bam":
          type: file
          description: Sorted BAM file
          pattern: "*.bam"
          ontologies: []
  versions_samtools:
    - - "${task.process}":
          type: string
          description: Process name
      - samtools:
          type: string
          description: Tool name
      - 'samtools --version | sed "1!d; s/samtools //"':
          type: eval
          description: Tool version command
topics:
  versions:
    - - "${task.process}":
          type: string
          description: Process name
      - samtools:
          type: string
          description: Tool name
      - 'samtools --version | sed "1!d; s/samtools //"':
          type: eval
          description: Tool version command
authors:
  - "@author"
maintainers:
  - "@maintainer"
```

## ext.args and modules.config

Per-process configuration (tool flags, output paths, naming) is injected from `conf/modules.config` using `withName:` selectors — never edit the module to change behavior.

```groovy
// conf/modules.config
process {
    withName: 'SAMTOOLS_SORT' {
        // evaluate parameter-dependent arguments lazily; threads still come from task.cpus
        ext.args   = { [ params.fast ? '-l 1' : '-l 9' ].join(' ') }
        ext.prefix = { "${meta.id}.sorted" }         // closures can read meta
        publishDir = [
            path: { "${params.outdir}/samtools" },
            mode: params.publish_dir_mode,
            pattern: "*.bam"
        ]
    }
    withName: '.*:ALIGN_BWA:BWA_MEM' { ext.args = '-M' }   // target a fully-qualified path
}
```

Permitted `ext` keys: `ext.args`/`args2`/`args3`/`argsN` (numbered by tool order in a piped script), `ext.prefix`/`prefix2`, `ext.when`, `ext.use_gpu`, `ext.singularity_pull_docker_container`. Rule of thumb: optional flags → `ext.args`; mandatory non-file tool arguments SHOULD be declared inputs; all input files MUST be declared `path` inputs. Optional non-file flags belong in `ext.args`, including scientific parameters; record them in provenance and confirm they affect the task hash. Do not hide a file dependency in an argument string. This separation (logic in the module, config in `modules.config`) is what makes nf-core modules reusable across pipelines.

## Subworkflows

A subworkflow chains modules into a reusable unit, in `subworkflows/nf-core/<name>/main.nf` with `take`/`main`/`emit` and a `meta.yml`. It must contain at least two modules. Tools 4.1.0 subworkflow templates use modules that publish versions to the shared topic and do not emit a redundant `versions` channel. The public subworkflow general specification still describes legacy YAML-channel mixing; preserve that pattern only when the installed modules actually expose it. Name it `<file-type>_<operation(s)>_<tool(s)>`, e.g. `bam_sort_stats_samtools`.

```nextflow
include { SAMTOOLS_SORT  } from '../../../modules/nf-core/samtools/sort/main'
include { SAMTOOLS_INDEX } from '../../../modules/nf-core/samtools/index/main'

workflow BAM_SORT_SAMTOOLS {
    take:
    ch_bam            // channel: [ val(meta), path(bam) ]

    main:
    SAMTOOLS_SORT(ch_bam, [[:], [], []], '') // BAM input: no FASTA or requested inline index

    SAMTOOLS_INDEX(SAMTOOLS_SORT.out.bam)

    emit:
    bam      = SAMTOOLS_SORT.out.bam        // [ val(meta), path(bam) ]
    index    = SAMTOOLS_INDEX.out.index
}
```

Document each channel shape in comments and `meta.yml`. For legacy modules, explicitly mix their YAML `out.versions` channels and emit that legacy channel; for current modules, collect the pipeline-level topic. Do not invent missing outputs to satisfy stale examples.

## Resource labels and base.config

Modules carry a `process_*` label; `conf/base.config` maps labels → resources (with `task.attempt` scaling for retries):

```groovy
process {
    cpus   = { 1    * task.attempt }
    memory = { 6.GB * task.attempt }
    time   = { 4.h  * task.attempt }
    errorStrategy = { task.exitStatus in ((130..145) + 104 + (175..177)) ? 'retry' : 'finish' }
    maxRetries    = 1

    withLabel: process_single      { cpus = { 1 };             memory = { 6.GB  * task.attempt }; time = { 4.h  * task.attempt } }
    withLabel: process_low         { cpus = { 2 * task.attempt }; memory = { 12.GB * task.attempt }; time = { 4.h  * task.attempt } }
    withLabel: process_medium      { cpus = { 6 * task.attempt }; memory = { 36.GB * task.attempt }; time = { 8.h  * task.attempt } }
    withLabel: process_high        { cpus = { 12 * task.attempt }; memory = { 72.GB * task.attempt }; time = { 16.h * task.attempt } }
    withLabel: process_long        { time = { 20.h * task.attempt } }
    withLabel: process_high_memory { memory = { 200.GB * task.attempt } }
    withLabel: error_ignore        { errorStrategy = 'ignore' }
    withLabel: error_retry         { errorStrategy = 'retry'; maxRetries = 2 }
}
```

Attach exactly **one** bundled label (`process_single/low/medium/high`) per module and optionally stack a modifier (`process_long`, `process_high_memory`). These closures scale on retries; exit codes are only a heuristic, so check scheduler logs and bound retries. To cap escalation to what the platform allows, set `process.resourceLimits = [ cpus: 16, memory: 128.GB, time: 24.h ]` (the modern replacement for the old `check_max()`/`--max_cpus`/`--max_memory` pattern) in `nextflow.config` or an institutional config.

## Schema and parameters

`nextflow_schema.json` is a JSON-Schema description of every pipeline parameter. It powers CLI/`-params-file` validation (via the `nf-schema` plugin), the `nf-core pipelines launch` GUI, and auto-generated docs. Keep it in sync with `params` in `nextflow.config`:

```bash
nf-core pipelines schema build      # interactive web editor to add/edit params
nf-core pipelines schema lint       # CI checks schema ↔ params consistency
```

The samplesheet itself is validated against the pipeline's own
`<pipeline>/assets/schema_input.json`.

## Linting and the Harshil alignment style

- Run `nf-core pipelines lint` (pipelines) and `nf-core modules lint <tool>` / `nf-core subworkflows lint <name>` (components) before every PR; CI enforces them. Lint exceptions live in `.nf-core.yml`.
- Code must be free of Nextflow syntax warnings: `NXF_SYNTAX_PARSER=v2 nextflow lint modules/nf-core/<tool>` (strict syntax is the default in Nextflow 26.04 — see `references/language.md`). Common fixes: declare local variables with `def` inside closures/process scripts, use explicit closure params (`{ meta, file -> ... }`) not `it`, avoid `for` loops.
- Code is formatted with **Prettier** (`prettier -w .`) and follows the **Harshil alignment** style: align assignment `=`, the commas/`emit:`/`optional:` in I/O declarations, and trailing comments into columns for readability. EditorConfig + pre-commit hooks ship in the template; comment `@nf-core-bot fix linting` on a PR to auto-fix.
- Other expectations: pinned tool versions, `conda`+`container`, a `stub:` block, nf-test tests for every module/subworkflow, and `CHANGELOG.md`/`CITATIONS.md` updates.

See `references/testing.md` for the testing requirements and `references/nf-core-tools.md` for the CLI. Full normative spec: https://nf-co.re/docs/specifications/components/modules/general .
