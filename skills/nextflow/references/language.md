# Nextflow Language (DSL2)

A working reference for the untyped DSL2 interfaces used by many existing nf-core pipelines: processes, channels, operators, workflows, and modules. Nextflow is a Groovy-based DSL; DSL2 is the default and only DSL (DSL1 is removed, so `nextflow.enable.dsl=2` is unnecessary). Targets stable 26.04.6. Source: https://github.com/nextflow-io/nextflow/tree/v26.04.6/docs and https://docs.seqera.io/nextflow/ . Incomplete biological/tool examples below are illustrative; they require the named tools, references and missing module definitions.

**Current syntax conventions**: `NXF_SYNTAX_PARSER=v2` is the default in **26.04** (opt-in in 25.x). Strict syntax does not imply static typing. Typed processes/workflows remain a preview and require `nextflow.enable.types = true` in each applicable script; do not mix their syntax with untyped examples.
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

A Nextflow script (`.nf`) uses process/workflow definitions and the supported subset of Groovy; strict syntax does not allow arbitrary Groovy. Every script enables DSL2 implicitly (it is the default since 22.03). A run begins at the **unnamed `workflow {}`** block (the entry workflow).

```nextflow
#!/usr/bin/env nextflow

params.input = 'data/*.fastq'        // pipeline parameter with a default

process FASTQC { /* ... */ }          // a process definition

workflow {                            // entry point
    reads = channel.fromPath(params.input, checkIfExists: true)
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
    // Supply a pinned environment containing BOTH bwa and samtools.
    publishDir "${params.outdir}/bam", mode: 'copy'

    input:
    tuple val(meta), path(reads)      // a sample: metadata map + file(s)
    tuple path(reference), path(index_files)  // shared FASTA + BWA sidecars as a value

    output:
    tuple val(meta), path("*.bam"), emit: bam
    path  "versions.yml",           emit: versions

    when:
    meta.run_alignment != false       // skip task if false

    script:
    def prefix = task.ext.prefix ?: meta.id
    def args   = task.ext.args  ?: ''   // extra flags injected from config
    """
    bwa mem $args -t $task.cpus "$reference" ${reads} | samtools sort -o "${prefix}.bam"

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        bwa: \$(bwa 2>&1 | sed -n 's/Version: //p')
        samtools: \$(samtools --version | sed '1!d; s/samtools //')
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
| `path "out", optional: true` | Output may be absent without erroring |

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
- `stub:` replaces that task’s script under `-stub-run`; a task without one runs its real script. Containers, staging and `eval()` outputs may still run, so this is not a no-execution or no-cost dry run. nf-core modules require stubs.

## Process directives

Set inside a process (or globally via config). Most-used:

| Directive | Purpose |
|-----------|---------|
| `cpus`, `memory`, `time`, `disk` | Resource requests (e.g. `memory '8 GB'`, `time '2 h'`) |
| `container` | Container image for this process |
| `conda` | Conda packages/env for this process |
| `publishDir` | Copy/link outputs to a results dir (`mode: 'copy'|'symlink'|'link'`) |
| `tag` | Human-readable label per task in logs/trace |
| `label` | Group processes (target with `withLabel:` in config) |
| `errorStrategy` | `'terminate'` (default), `'ignore'`, `'retry'`, `'finish'` |
| `maxRetries`, `maxErrors` | Retry limits |
| `cache` | `true`/`'lenient'`/`'deep'`/`false` — caching behavior |
| `scratch` | Run in node-local scratch then stage out |
| `stageInMode` / `stageOutMode` | Input: symlink/copy/link/rellink; scratch output: copy/move/rsync/fcp/rclone |
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

- **Queue channel**: an ordered, *consumable* stream of items. Produced by most factories/operators and by process outputs. DSL2 automatically fans the stream out to separate downstream consumers; each receives all items. A single process invocation consumes one item per queue input for each task.
- **Value channel** (singleton): holds one value that can be read an unlimited number of times. Created by `channel.value()`, by operators like `collect`/`first`, or implicitly from a single value. A process input bound to a value channel is reused for every task.

### Channel factories

```nextflow
channel.of(1, 2, 3)                                  // emit given values (ranges expand: 1..23)
channel.fromList([1, 2, 3])                          // emit list items
channel.value('ref.fa')                              // singleton value channel
channel.fromPath('data/*.bam')                       // one item per matching file
channel.fromPath('data/**/*.fastq', checkIfExists: true) // also: type:'file', hidden:true
channel.fromFilePairs('data/*_{1,2}.fastq.gz')       // -> [id, [r1, r2]] for paired reads
channel.topic('versions')                            // stable since 25.04; preview in 24.04/24.10
channel.empty()                                      // emits nothing
```

> `channel.fromSRA(...)` exists but is deprecated as of 26.04 — use the documented Entrez Direct route to discover accessions, then an explicit validated samplesheet and download workflow.

`arity` is a process `path` input/output option, not a `fromPath` option. `checkIfExists` checks matching paths, not sample pairing or biological metadata.

`fromFilePairs` is the idiomatic way to group paired-end reads; it yields `[ sampleId, [read1, read2] ]`, which you typically `map` into the nf-core `[ meta, [reads] ]` shape.

## Operators

Operators transform/combine channels. Chain with `.`; the dataflow graph is built from these connections. The table includes legacy operators still used by untyped nf-core code. In 26.04, `groupTuple`, `flatten`, `concat`, `distinct`, `first`/`last`, the channel `split*` operators, `set`, and `dump` are deprecated; use the [core operator migration guide](https://docs.seqera.io/nextflow/tutorials/static-types-operators) for new code (`groupBy`, `flatMap` with Path `split*` methods, `mix`, `unique`, direct assignment, `view`, as applicable). Do not replace order-dependent logic mechanically.

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
| `branch { }` | Route each item to the first matching named branch |
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
reads_ch = channel
    .fromPath(params.input, checkIfExists: true)
    .flatMap { sheet -> sheet.splitCsv(header: true) }
    .map { row -> tuple([id: row.sample, single_end: row.fastq_2 ? false : true],
                        row.fastq_2 ? [file(row.fastq_1, checkIfExists: true), file(row.fastq_2, checkIfExists: true)] : [file(row.fastq_1, checkIfExists: true)]) }

// Legacy tuple workflow: group results, then join on an exact meta key
counts.groupTuple()
       .join(metadata, failOnDuplicate: true, failOnMismatch: true) // exact keyed matching
       .view()
```

## Workflows

A `workflow` composes processes and other workflows. The **unnamed** workflow is the entry point. **Named** workflows are reusable (sub)workflows.

```nextflow
workflow RNASEQ {
    take:                       // named inputs (untyped here)
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
    reads = channel.fromFilePairs(params.reads, checkIfExists: true)
                   .map { id, pair -> tuple([id: id, single_end: false], pair) }
    index = channel.value(tuple(file(params.fasta, checkIfExists: true),
                                files(params.bwa_index, checkIfExists: true)))
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
- Since 26.04, registry modules can be installed with `nextflow module install -version <version> <name>` and included by registry name. This is distinct from `nf-core modules install` and its `modules.json` bookkeeping. Pin the registry version/checksum; see [module registry](https://docs.seqera.io/nextflow/modules/module-registry). Local nf-core includes remain supported.

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

- Exit codes 137/140/143 identify signals, not a definitive OOM diagnosis. Check scheduler/task logs before escalating resources; a cancellation, timeout or application failure can look similar. Bound retries and resource requests.
- `errorStrategy 'ignore'` lets the pipeline continue past a failed task; `'finish'` stops launching new tasks but lets running ones complete.
- In nf-core, resource scaling lives in `conf/base.config` keyed on `process_*` labels (see `references/developing.md`).

## Groovy essentials and gotchas

- Strings: single-quoted are literal; double-quoted interpolate (`"${x}"`). In `script:` blocks, escape shell variables as `\$VAR`.
- Define helper values with `def` inside `script:`/closures to avoid leaking globals.
- Maps use Groovy syntax: `[ id: 'x', single_end: false ]`; access as `meta.id`.
- **Common gotchas**:
  - DSL2 allows a stream to feed multiple processes. The hazard is passing multiple independent queues into one process: completion order can mismatch samples. Join on an immutable sample key into one tuple channel; use `channel.value(...)` or `toList()` for a shared reference value.
  - Legacy `groupTuple` without `size` buffers until the source closes. With `size`, it emits completed groups earlier and can drop incomplete groups unless `remainder: true`. Validate expected replicate/lane counts; never mistake a partial group for a complete sample.
  - Legacy tuple `join` does not support duplicate keys. Set `failOnDuplicate`/`failOnMismatch` explicitly; for deliberate many-to-many matching use `combine(by:)` and validate cardinality. Do not assume parser mode alone supplies these checks.
  - A full meta map used as a key must match exactly; extra/different fields can prevent joins. Keep sample keys immutable and check identities across branches.
  - `channel.topic` consumers must not feed outputs back into the same topic: that cycle can hang the workflow.
  - A process called twice without aliasing is an error; `include ... as`.
  - Globs in `output:` match the **work directory**, not `publishDir`. Publishing is asynchronous; downstream processes must consume output channels. Prevent output filename collisions between samples.
  - Prefer filtering channels over `when:` for clarity and caching.
- **Strict syntax / language server**: Nextflow provides a VS Code extension + `nextflow lint` and a stricter parser; nf-core is migrating pipelines to it. Keep scripts to documented DSL2 constructs and avoid deprecated DSL1 idioms (`Channel.create()`, `.into{}` overuse, top-level `file()` for inputs).
