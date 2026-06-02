# Nextflow Configuration, Executors & CLI

How to configure, scale, cache, observe, and drive Nextflow runs. Source: https://www.nextflow.io/docs/latest/config.html and related pages.

## Table of Contents

- [nextflow.config and scopes](#nextflowconfig-and-scopes)
- [Profiles](#profiles)
- [Process selectors](#process-selectors-withname-withlabel)
- [Executors](#executors)
- [Cloud executors](#cloud-executors)
- [Caching and -resume](#caching-and--resume)
- [Tracing and reports](#tracing-and-reports)
- [The nextflow CLI](#the-nextflow-cli)
- [Environment variables](#environment-variables)

## nextflow.config and scopes

`nextflow.config` configures a run **without touching pipeline code**. Files are auto-loaded and merged in **increasing precedence**: (1) `$NXF_HOME/config` (`~/.nextflow/config`), (2) `nextflow.config` in the **project** dir (where the script lives), (3) `nextflow.config` in the **launch** dir (current working dir), (4) each `-c custom.config` (repeatable). Using `-C file` instead loads **only** that file and ignores every other source. CLI `--param`/`-params-file` override config params. Values are grouped into **scopes**.

```groovy
// nextflow.config
params {
    input  = null
    outdir = 'results'
    genome = 'GRCh38'
}

process {
    cpus   = 2
    memory = '4 GB'
    errorStrategy = 'retry'
    maxRetries    = 2
    container = 'ubuntu:22.04'
}

executor {
    queueSize     = 100        // max parallel tasks submitted
    submitRateLimit = '10/1min'
}

docker.enabled = true          // pick ONE container engine
// singularity.enabled = true
// conda.enabled = true

timeline.enabled = true
report.enabled   = true
trace.enabled    = true

manifest {
    name = 'my/pipeline'
    nextflowVersion = '!>=24.04.0'   // enforce a minimum engine version
}
```

Key scopes: `params`, `process`, `executor`, `docker`/`singularity`/`apptainer`/`podman`/`conda`/`wave`, `aws`/`google`/`azure`/`k8s`, `tower` (Seqera Platform), `report`/`timeline`/`trace`/`dag`, `manifest`, `env`, `cleanup`.

Assignment uses `=`. Use the dotted form (`docker.enabled = true`) or block form (`docker { enabled = true }`) interchangeably.

## Profiles

A **profile** is a named bundle of config, activated with `-profile`. nf-core pipelines ship profiles for each container engine plus a `test` profile.

```groovy
profiles {
    standard { process.executor = 'local' }

    docker      { docker.enabled = true; docker.runOptions = '-u $(id -u):$(id -g)' }
    singularity { singularity.enabled = true; singularity.autoMounts = true }
    conda       { conda.enabled = true }

    slurm {
        process.executor = 'slurm'
        process.queue    = 'compute'
    }

    test {
        params.input  = "${baseDir}/assets/test_samplesheet.csv"
        params.genome = 'R64-1-1'
    }
}
```

Activate (combine with commas; **order matters** — later profiles override earlier):

```bash
nextflow run main.nf -profile test,singularity
```

Container/infra profiles (`docker`, `singularity`, `conda`) are mutually exclusive — choose one. If no `-profile` is given, the `standard` profile (if defined) is used.

> Ordering caveat: with the legacy parser, profiles are applied in the **order they are defined in the config**, regardless of CLI order; with the strict parser (default in 26.04) they apply in **CLI order**. To stay safe, avoid combining profiles that set the *same* option to conflicting values.

## Process selectors (withName, withLabel)

Target configuration at specific processes inside the `process` scope. This is how nf-core sets per-tool resources and arguments without editing modules.

```groovy
process {
    // by resource label
    withLabel: 'process_low'    { cpus = 2;  memory = 6.GB;  time = 4.h }
    withLabel: 'process_medium' { cpus = 6;  memory = 36.GB; time = 8.h }
    withLabel: 'process_high'   { cpus = 12; memory = 72.GB; time = 16.h }

    // by process name (regex / fully-qualified WORKFLOW:SUB:PROCESS)
    withName: 'FASTQC' { cpus = 4 }
    withName: '.*:ALIGN' {
        container = 'quay.io/biocontainers/bwa:0.7.17--hed695b0_7'
        ext.args  = '-M'                 // injected into the script as task.ext.args
        publishDir = [ path: { "${params.outdir}/bam" }, mode: 'copy' ]
    }
}
```

Precedence: `withName` overrides `withLabel` overrides generic `process` settings. nf-core keeps all `withName` blocks in `conf/modules.config`.

## Executors

The executor maps tasks onto compute. Default is `local` (subprocesses on the current machine). Set globally or per-process.

```groovy
process.executor = 'slurm'        // global
// or
process { withLabel: 'process_high' { executor = 'slurm'; queue = 'bigmem' } }
```

| Executor | Platform |
|----------|----------|
| `local` | The current machine (default) |
| `slurm` | SLURM clusters |
| `sge` / `uge` | (Univa) Grid Engine |
| `lsf` | IBM Spectrum LSF |
| `pbs` / `pbspro` | PBS / Torque / PBS Pro |
| `awsbatch` | AWS Batch |
| `google-batch` | Google Cloud Batch |
| `azurebatch` | Azure Batch |
| `k8s` | Kubernetes |
| `flux`, `hyperqueue`, `oar`, `moab` | Other schedulers |

SLURM example with cluster options:

```groovy
process {
    executor   = 'slurm'
    queue      = 'compute'             // SLURM partition
    clusterOptions = '--account=lab123'
}
executor {
    queueSize       = 200              // max jobs queued at once
    submitRateLimit = '10/1min'        // throttle submissions
    perCpuMemAllocation = true         // emit --mem-per-cpu instead of --mem (some clusters require this)
}
```

## Cloud executors

Each cloud needs its scope configured (region, work bucket, etc.). Always set `workDir` to cloud storage.

```groovy
// AWS Batch
process.executor = 'awsbatch'
process.queue    = 'my-batch-queue'
aws {
    region = 'us-east-1'
    batch.cliPath = '/home/ec2-user/miniconda/bin/aws'
}
workDir = 's3://my-bucket/work'
```

```groovy
// Google Cloud Batch
process.executor = 'google-batch'
google.project   = 'my-gcp-project'
google.location  = 'us-central1'
workDir = 'gs://my-bucket/work'
```

For Azure use `azurebatch` + the `azure` scope with `workDir = 'az://...'`. For Kubernetes use `k8s` + `nextflow kuberun`. **Wave + Fusion** can accelerate cloud I/O (see `references/containers.md`). Seqera Platform (Tower) monitoring: set `tower.enabled = true` and `TOWER_ACCESS_TOKEN`, or run with `-with-tower`.

## Caching and -resume

`-resume` skips tasks whose inputs are unchanged, reusing outputs from the `work/` directory.

```bash
nextflow run main.nf -resume                 # resume the last run
nextflow run main.nf -resume <session-id>    # resume a specific session (see `nextflow log`)
```

How caching works: each task gets a hash of its inputs (file content/metadata), the script text, the container, and key directives. If the hash matches a previous run, the cached output is reused.

**Debugging cache misses** (a task re-runs when you expected a hit):
- Run `nextflow log <run> -f hash,name,status,workdir` to inspect tasks.
- Diff the task hashes of two runs: `nextflow -log a.log run … -dump-hashes json` then `nextflow -log b.log run … -resume -dump-hashes json`, and compare the `cache hash` entries to see exactly what changed.
- Common causes: a changed input file timestamp/content, an edited script, a different container tag, a non-deterministic input order, an undeclared closure variable (use `def`), or using `cache false`.
- `cache 'lenient'` hashes file size+timestamp (path) instead of content — useful on shared filesystems where content hashing is slow or timestamps shift. `cache 'deep'` hashes file content.
- Caching is per **work directory**; deleting `work/` or changing `-w`/`workDir` loses the cache.

**Work directory management**: `work/` grows fast. Clean with:

```bash
nextflow clean -f -before <run_name>    # remove work data before a run
nextflow clean -f -but <run_name>       # keep one run, remove others
```

Set `cleanup = true` in config to auto-remove `work/` on successful completion (note: this disables `-resume`).

## Tracing and reports

Observability flags (or enable the matching config scope):

| Flag | Produces |
|------|----------|
| `-with-report report.html` | Resource-usage HTML report per task |
| `-with-timeline timeline.html` | Timeline of task execution |
| `-with-trace trace.txt` | Tab-separated trace of every task (cpu, mem, time, status) |
| `-with-dag flow.html` (or `.png`/`.mmd`/`.dot`) | Workflow DAG diagram |
| `-with-tower` | Stream metrics to Seqera Platform |
| `-with-weblog <url>` | POST run events to an HTTP endpoint |

```bash
nextflow run main.nf -profile docker \
  -with-report -with-trace -with-timeline -with-dag flow.html
```

## The nextflow CLI

```bash
nextflow run <pipeline> [options]   # <pipeline> = path, .nf file, or github user/repo
```

| Option | Meaning |
|--------|---------|
| `-profile a,b` | Activate config profiles (comma-separated, ordered) |
| `-resume [id]` | Reuse cached results |
| `-r <rev>` | Git revision: tag, branch, or commit (for remote pipelines) |
| `-params-file f.yml` | Load params from YAML/JSON |
| `-c file.config` | Add an extra config file (highest-precedence config) |
| `-w <dir>` / `workDir` | Set the work directory (local path or cloud URI) |
| `-stub-run` (`-stub`) | Execute `stub:` blocks instead of real scripts |
| `-entry <name>` | Run a specific named workflow as the entry point |
| `-process.<dir> <val>` | Override a process directive at launch |
| `-bg` | Run in background; `-ansi-log false` for plain logs |
| `-dump-channels` | Print channel contents (with `.dump()`) |
| `-preview` | Build the DAG without executing |

Other top-level commands:

```bash
nextflow log [run] [-f fields]      # list past runs / fields of a run
nextflow pull   user/repo           # download/update a remote pipeline
nextflow list                       # list downloaded pipelines
nextflow info   user/repo           # show pipeline metadata
nextflow drop   user/repo           # delete a downloaded pipeline
nextflow clean  -f -before <run>    # delete work data
nextflow config [-profile p]        # print the resolved configuration
nextflow inspect <pipeline>         # resolve per-process containers without running
nextflow lint   <file|dir>          # check/format scripts & config (strict syntax)
nextflow self-update                # update the Nextflow engine
```

## Environment variables

| Variable | Effect |
|----------|--------|
| `NXF_VER` | Pin the Nextflow engine version for the run |
| `NXF_WORK` | Default work directory |
| `NXF_HOME` | Nextflow home (`~/.nextflow`) |
| `NXF_SINGULARITY_CACHEDIR` / `NXF_APPTAINER_CACHEDIR` | Where SIF images are cached (set on HPC!) |
| `NXF_CONDA_CACHEDIR` | Cached conda envs |
| `NXF_CLOUDCACHE_PATH` | Store the task cache in object storage (e.g. `s3://bucket/cache`) for cloud runs |
| `NXF_SYNTAX_PARSER=v2` | Opt into the strict-syntax parser (default in 26.04) |
| `NXF_OPTS` | JVM options, e.g. `-Xms2g -Xmx4g` for big runs |
| `TOWER_ACCESS_TOKEN` | Seqera Platform token (with `-with-tower`) |
| `NXF_OFFLINE=true` | Disable network calls (offline/air-gapped runs) |

On HPC, always set a shared `NXF_SINGULARITY_CACHEDIR` so image pulls are reused across jobs. See `references/running-pipelines.md` for offline execution.
