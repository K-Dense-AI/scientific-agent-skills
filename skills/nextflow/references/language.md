# Nextflow Language (DSL2)

The complete Nextflow scripting language: processes, channels, operators, workflows, and modules. Nextflow is a Groovy-based DSL; DSL2 is the default and only DSL (DSL1 is removed, so `nextflow.enable.dsl=2` is unnecessary). Source: https://www.nextflow.io/docs/latest/

**Current syntax conventions** (a strict-syntax parser, `NXF_SYNTAX_PARSER=v2`, is opt-in in 25.x and becomes the default in **26.04** — write to it now, it also runs on the legacy parser):
- **`channel.of(...)`** (lowercase namespace) is canonical; `Channel.of(...)` still works but is discouraged.
- **Explicit closure parameters** (`{ v -> v * 2 }`) are preferred over the implicit `it`.
- Name process outputs with **`emit:`**; scale resources with **`task.attempt`**.
- **`output {}` + `publish:`** (full feature in 25.10) is the new declarative way to publish results; `publishDir` still works and remains dominant in nf-core — both are shown below.
- Avoid removed/deprecated idioms: `for`/`while` loops (use `each`/`collect`), `import`/custom `class` (use functions or `lib/`), `process shell:` (use `script:`), `include … addParams()`.

## Table of Contents

- [Script structure](#script-structure)
- [Processes](#processes)
- [Process directives](#process-directives)
- [Channels](#channels)
- [Operators](#operators)
- [Workflows](#workflows)
- [Modules](#modules)
- [Dynamic resources and error handling](#dynamic-resources-and-error-handling)
- [Groovy essentials and gotchas](#groovy-essentials-and-gotchas)

## Script structure

A Nextflow script (`.nf`) mixes process/workflow definitions with Groovy. Every script enables DSL2 implicitly (it is the default since 22.03). A run begins at the **unnamed `workflow {}`** block (the entry workflow).

```nextflow
#!/usr/bin/env nextflow

params.input = 'data/*.fastq'        // pipeline parameter with a default

process FASTQC { /* ... */ }          // a process definition

workflow {                            // entry point
    reads = channel.fromPath(params.input)
    FASTQC(reads)
}
```

Run with `nextflow run main.nf --input 'data/*.fastq'`. Parameters declared as `params.x` are overridable on the CLI (`--x`), in `nextflow.config`, or in a `-params-file`.

## Processes

A `process` defines a task: a (usually Bash) script executed in its own isolated **work directory**. Nextflow stages declared inputs in and declared outputs out, so processes never read/write each other's files directly — they communicate only through channels.

```nextflow
process ALIGN {
    tag    "$meta.id"                 // label shown in the log/trace
    label  'process_high'             // maps to resources in config
    container 'quay.io/biocontainers/bwa:0.7.17--hed695b0_7'
    publishDir "${params.outdir}/bam", mode: 'copy'

    input:
    tuple val(meta), path(reads)      // a sample: metadata map + file(s)
    path  index                       // a shared reference (value channel)

    output:
    tuple val(meta), path("*.bam"), emit: bam
    path  "versions.yml",           emit: versions

    when:
    meta.run_alignment != false       // skip task if false

    script:
    def prefix = task.ext.prefix ?: meta.id
    def args   = task.ext.args  ?: ''   // extra flags injected from config
    """
    bwa mem $args -t $task.cpus $index ${reads} | samtools sort -o ${prefix}.bam

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        bwa: \$(bwa 2>&1 | sed -n 's/Version: //p')
    END_VERSIONS
    """

    stub:
    """
    touch ${meta.id}.bam
    touch versions.yml
    """
}
```

### Inputs

Declared one per line under `input:`. Each input consumes one item from a channel.

| Qualifier | Meaning |
|-----------|---------|
| `val(x)` | Any value (string, number, map) |
| `path(f)` | A file/dir; staged into the work dir. Use `path` (not the old `file`) |
| `tuple val(meta), path(reads)` | A composite item — the nf-core standard: a meta map + files |
| `env(NAME)` | Value exposed as an environment variable |
| `stdin` | Feed the channel item to the script's stdin |
| `each x` | Repeat the process once per value in `x` (combinatorial) |

Inputs are positional and matched to channels in call order: `ALIGN(reads_ch, index_ch)`.

### Outputs

Declared under `output:`; each becomes a channel. Use `emit:` to name outputs so callers can reference `ALIGN.out.bam` instead of positional `ALIGN.out[0]`.

| Form | Meaning |
|------|---------|
| `path "*.bam"` | Files matched by glob in the work dir after the script runs |
| `tuple val(meta), path("*.bam")` | Carry metadata forward with the file |
| `val x` | Emit a value computed in the process |
| `stdout` | Capture the script's stdout as the output |
| `eval('cmd')` | Capture the stdout of a command run in the task env (24.04+) — used for tool versions |
| `path "out", emit: name` | Named output channel (reference as `PROC.out.name`) |
| `..., topic: versions` | Also route this output to a named topic channel |
| `optional true` | Output may be absent without erroring |

### Script, shell, exec

- **`script:`** (default) — a multi-line string run as Bash. Nextflow variables interpolate with `$var`/`${expr}`; escape shell vars you do NOT want Nextflow to touch as `\$var`.
- **`shell:`** — like script but Nextflow vars use `!{var}`, leaving `$` for the shell. **Deprecated as of 25.04** — use `script:` with `\$` to escape shell vars.
- **`exec:`** — native Groovy, no external process (for in-line computation).
- A process can run any interpreter via a shebang (e.g. `#!/usr/bin/env python`).

```nextflow
process PY {
    input: val x
    output: stdout
    script:
    """
    #!/usr/bin/env python
    print(${x} ** 2)
    """
}
```

### Conditional execution

- `when:` — skip the task when the expression is false (prefer filtering channels upstream when possible).
- A `script:` can branch with normal Groovy `if/else` returning different command strings.
- `stub:` — an alternate minimal script run with `-stub-run` to test pipeline wiring without the real tool. nf-core requires stubs.

## Process directives

Set inside a process (or globally via config). Most-used:

| Directive | Purpose |
|-----------|---------|
| `cpus`, `memory`, `time`, `disk` | Resource requests (e.g. `memory '8.GB'`, `time '2.h'`) |
| `container` | Container image for this process |
| `conda` | Conda packages/env for this process |
| `publishDir` | Copy/link outputs to a results dir (`mode: 'copy'|'symlink'|'link'`) |
| `tag` | Human-readable label per task in logs/trace |
| `label` | Group processes (target with `withLabel:` in config) |
| `errorStrategy` | `'terminate'` (default), `'ignore'`, `'retry'`, `'finish'` |
| `maxRetries`, `maxErrors` | Retry limits |
| `cache` | `true`/`'lenient'`/`'deep'`/`false` — caching behavior |
| `scratch` | Run in node-local scratch then stage out |
| `stageInMode`/`stageOutMode` | `'symlink'`/`'copy'`/`'link'` staging |
| `beforeScript`/`afterScript` | Commands wrapping the task script |
| `accelerator` | GPU request (e.g. `accelerator 1, type: 'nvidia-tesla-v100'`) |
| `array` | Submit as a job array (HPC/cloud), e.g. `array 100` |
| `ext` | Free-form map (`ext.args`, `ext.prefix`) injected from config |
| `pod` | Kubernetes pod options |
| `module` | Load an HPC environment module |
| `maxForks` | Cap parallel tasks for this process |

Access the resolved values at runtime via `task.*` (`task.cpus`, `task.memory`, `task.attempt`, `task.process`, `task.ext.args`).

## Channels

Channels are the asynchronous queues connecting processes. Two kinds:

- **Queue channel**: an ordered, *consumable* stream of items. Produced by most factories/operators and by process outputs. Can be consumed once.
- **Value channel** (singleton): holds one value that can be read an unlimited number of times. Created by `channel.value()`, by operators like `collect`/`first`, or implicitly from a single value. A process input bound to a value channel is reused for every task.

### Channel factories

```nextflow
channel.of(1, 2, 3)                                  // emit given values (ranges expand: 1..23)
channel.fromList([1, 2, 3])                          // emit list items
channel.value('ref.fa')                              // singleton value channel
channel.fromPath('data/*.bam')                       // one item per matching file
channel.fromPath('data/**.fastq', checkIfExists: true)   // also: arity:'1', type:'file', hidden:true
channel.fromFilePairs('data/*_{1,2}.fastq.gz')       // -> [id, [r1, r2]] for paired reads
channel.topic('versions')                            // collect values emitted to a named topic (24.04+)
channel.empty()                                      // emits nothing
```

> `channel.fromSRA(...)` exists but is deprecated as of 26.04 — prefer a **samplesheet** (`splitCsv`) over fetching reads by accession.

`fromFilePairs` is the idiomatic way to group paired-end reads; it yields `[ sampleId, [read1, read2] ]`, which you typically `map` into the nf-core `[ meta, [reads] ]` shape.

## Operators

Operators transform/combine channels. Chain with `.`; the dataflow graph is built from these connections.

| Operator | Purpose |
|----------|---------|
| `map { }` | Transform each item |
| `filter { }` | Keep items matching a condition/type/regex |
| `flatten` | Flatten nested emissions into individual items |
| `collect` | Gather all items into a single list (→ value channel) |
| `toList` / `toSortedList` | Collect into one (sorted) list |
| `groupTuple` | Group tuples by key (e.g. by `meta`) — often needs `groupTuple(by: 0)` |
| `join` | Inner-join two channels by a matching key |
| `combine` | Cartesian product (optionally `by:` a key) |
| `cross` | Combine matching keyed items |
| `mix` | Merge multiple channels into one stream |
| `concat` | Emit one channel fully, then the next, in order |
| `branch { }` | Route items into multiple named sub-channels by condition |
| `multiMap { }` | Emit to several channels from one pass |
| `splitCsv` / `splitText` / `splitFasta` / `splitFastq` | Split file contents into items |
| `collectFile` | Write items into one or more files |
| `unique` / `distinct` | De-duplicate |
| `first` / `last` / `take` / `until` | Select subsets |
| `set { ch }` | Name the resulting channel (alternative to `ch =`) |
| `view { }` | Print items for debugging (returns the channel unchanged) |
| `ifEmpty` | Provide a default if the channel is empty |
| `dump(tag:'x')` | Debug-print when run with `-dump-channels x` |

```nextflow
// Build the nf-core [meta, reads] shape from a samplesheet
channel
    .fromPath(params.input)
    .splitCsv(header: true)
    .map { row -> tuple([id: row.sample, single_end: row.fastq_2 ? false : true],
                        row.fastq_2 ? [file(row.fastq_1), file(row.fastq_2)] : [file(row.fastq_1)]) }
    .set { reads_ch }

// Group per-sample results, then join two channels by meta
counts.groupTuple()
       .join(metadata)          // matches on the first (key) element
       .view()
```

## Workflows

A `workflow` composes processes and other workflows. The **unnamed** workflow is the entry point. **Named** workflows are reusable (sub)workflows.

```nextflow
workflow RNASEQ {
    take:                       // typed inputs (channels)
    reads
    index

    main:                       // pipeline logic
    FASTQC(reads)
    ALIGN(reads, index)
    QUANT(ALIGN.out.bam)

    emit:                       // named outputs
    bam    = ALIGN.out.bam
    counts = QUANT.out.counts
    versions = FASTQC.out.versions.mix(ALIGN.out.versions)
}

workflow {                      // entry: wire inputs and call the named workflow
    reads = channel.fromFilePairs(params.reads)
    index = channel.value(file(params.index))
    RNASEQ(reads, index)
    RNASEQ.out.counts.view()
}
```

- Call a process/workflow like a function: `ALIGN(reads, index)`. Outputs are on `.out` (use `emit:` names: `ALIGN.out.bam`).
- A process can only be **called once** per workflow; to reuse it, `include` it again under an alias.
- Pipe syntax works for simple chains: `reads | FASTQC`.
- **Declarative outputs (25.10+)**: assign channels in the entry workflow's `publish:` section and describe them in a top-level `output {}` block — the recommended replacement for the `publishDir` directive (which still works and dominates nf-core):

```nextflow
workflow {
    main:
    ch = ANALYZE(input)
    publish:
    results = ch                       // name the published channel
}
output {
    results { path 'analysis' }        // -> <outputDir>/analysis (default outputDir: results/)
}
```

## Modules

Modules are `.nf` files whose processes/workflows are imported with `include`. This is the basis of nf-core's reusable components.

```nextflow
include { FASTQC }                     from './modules/fastqc/main.nf'
include { ALIGN as ALIGN_TUMOR;
          ALIGN as ALIGN_NORMAL }      from './modules/align/main.nf'
include { RNASEQ }                     from './subworkflows/rnaseq.nf'
```

- `as` aliases let you include the same component multiple times.
- Includes are resolved relative to the including file; `.nf` extension optional.
- Params should be passed explicitly (as inputs), not read globally inside modules — this keeps modules portable (an nf-core requirement).

## Dynamic resources and error handling

Make pipelines robust by retrying failures with more resources instead of over-provisioning everything. `task.attempt` increments on each retry.

```nextflow
process BIG_JOB {
    label 'process_high'
    cpus   { 4 * task.attempt }
    memory { 8.GB * task.attempt }
    time   { 4.h * task.attempt }

    errorStrategy { task.exitStatus in [137, 140, 143] ? 'retry' : 'terminate' }
    maxRetries 3
    // ...
}
```

- Exit codes 137/140/143 typically mean out-of-memory/walltime kills — retry with more resources.
- `errorStrategy 'ignore'` lets the pipeline continue past a failed task; `'finish'` stops launching new tasks but lets running ones complete.
- In nf-core, resource scaling lives in `conf/base.config` keyed on `process_*` labels (see `references/developing.md`).

## Groovy essentials and gotchas

- Strings: single-quoted are literal; double-quoted interpolate (`"${x}"`). In `script:` blocks, escape shell variables as `\$VAR`.
- Define helper values with `def` inside `script:`/closures to avoid leaking globals.
- Maps use Groovy syntax: `[ id: 'x', single_end: false ]`; access as `meta.id`.
- **Common gotchas**:
  - Re-using a consumed **queue** channel yields nothing — use a **value** channel (or `collect`) for things consumed by many tasks (like a reference index).
  - `groupTuple` may emit before all items arrive unless sizes are known; provide `size:` or use `groupTuple(by:)` carefully.
  - A process called twice without aliasing is an error; `include ... as`.
  - Globs in `output:` match the **work directory**, not `publishDir`.
  - Prefer filtering channels over `when:` for clarity and caching.
- **Strict syntax / language server**: recent Nextflow ships a VS Code extension + `nextflow lint` and a stricter parser; nf-core is migrating pipelines to it. Keep scripts to documented DSL2 constructs and avoid deprecated DSL1 idioms (`Channel.create()`, `.into{}` overuse, top-level `file()` for inputs).
