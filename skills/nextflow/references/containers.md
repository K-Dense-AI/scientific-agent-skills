# Software Dependencies: Containers & Conda

Nextflow uses a process’s declared software environment when the corresponding runtime is enabled; otherwise tools run on the host. Pin environments for reproducible analyses. Targets Nextflow 26.04.6; configurations below are illustrative, without live container/cloud execution. Sources: https://docs.seqera.io/nextflow/container , https://docs.seqera.io/nextflow/conda , https://docs.seqera.io/nextflow/wave .

## Choosing an engine

| Engine | Use when | Enable |
|--------|----------|--------|
| **Docker** | Local dev / laptops / CI with root or docker group | `docker.enabled = true` |
| **Singularity / Apptainer** | HPC clusters (no root, shared FS) — most common in academia | `singularity.enabled = true` (or `apptainer.enabled = true`) |
| **Podman** | Rootless alternative to Docker | `podman.enabled = true` |
| **Charliecloud / Sarus / Shifter** | Site-specific HPC runtimes | `charliecloud.enabled = true`, etc. |
| **Conda / Mamba** | No container runtime available; quick envs | `conda.enabled = true` |
| **Wave** | Resolve/build images from Conda/Dockerfiles for a supported executor/runtime | `wave.enabled = true` in addition to that execution setup |

Enable one task execution environment (container runtime or Conda). Wave is an image service, not a competing runtime, and may be combined with a supported container setup. nf-core ships these as profiles, so users typically just pass `-profile docker` / `-profile singularity` / `-profile conda`.

## The container directive

Each process declares its image; the engine config decides how it runs.

```nextflow
process SAMTOOLS_SORT {
    container 'community.wave.seqera.io/library/htslib_samtools:1.24--d697cfb9dce007cd'
    conda     'bioconda::samtools=1.24'    // fallback when -profile conda is used
    input:
    path bam
    output:
    path "sorted.bam", emit: bam
    script:
    """
    samtools sort -@ $task.cpus -o sorted.bam "$bam"
    """
}
```

nf-core modules declare **both** a `container` and a `conda` line for supported profiles; architecture and runtime support still need validation. Current modules can use Seqera Community/Wave images as well as BioContainers/Galaxy depot. In nf-core modules the `conda` directive references a separate file — `conda "${moduleDir}/environment.yml"` — rather than an inline string. Biocontainers images live on `quay.io/biocontainers/...` (and `https://depot.galaxyproject.org/singularity/...` for Singularity), auto-built from Bioconda recipes.

## Docker

```groovy
docker {
    enabled    = true
    runOptions = '-u $(id -u):$(id -g)'   // avoid root-owned output files
}
```

## Singularity / Apptainer

```groovy
singularity {
    enabled    = true
    autoMounts = true                      // auto-bind host paths
    cacheDir   = '/shared/singularity'     // or set NXF_SINGULARITY_CACHEDIR
}
```

- Nextflow auto-converts Docker images to SIF on first use and caches them. On clusters, set a **shared** `cacheDir`/`NXF_SINGULARITY_CACHEDIR` so all jobs reuse pulls.
- Bind extra paths with `runOptions = '-B /scratch'` if `autoMounts` misses them.
- Apptainer and SingularityCE are distinct runtimes; enable the scope matching the installed executable. Both support Nextflow’s image/cache/bind workflow.

## Conda / Mamba

```groovy
conda {
    enabled    = true
    useMamba   = true                       // faster solver
    channels   = 'conda-forge,bioconda'     // priority order (this is the default since 26.04)
    cacheDir   = '/shared/conda_envs'
}
process.conda = 'bioconda::bwa=0.7.17 bioconda::samtools=1.19'
```

A version-only Conda specification can resolve differently over time and does not isolate the OS. Use lockfiles/explicit package records and platform metadata; containers also need immutable digests and architecture records. Use `NXF_CONDA_CACHEDIR` to reuse built envs.

## Wave + Fusion

**Wave** resolves/builds images and handles supported registry authentication. It does not execute the task. **Fusion** exposes supported object storage to tasks through a filesystem; requirements, credentials and costs depend on executor/service configuration. Performance improvements require measurement.

```groovy
wave {
    enabled  = true
    strategy = 'conda'           // build images from process conda directives
}
fusion.enabled = true            // pair with Wave on cloud executors
// Supply TOWER_ACCESS_TOKEN via the environment when required; never commit tokens.
```

## Common gotchas

- **Two engines enabled at once** → errors or surprising behavior. Enable one (use profiles).
- **Root-owned outputs** with Docker → set `runOptions = '-u $(id -u):$(id -g)'`.
- **Singularity can't see input files** → enable `autoMounts` or add `-B` binds; ensure the work dir and inputs are on bound paths.
- **HPC pull storms / quota blowups** → set a shared `NXF_SINGULARITY_CACHEDIR` and pre-pull with `nf-core pipelines download` (see `references/running-pipelines.md`).
- **Pinning**: always use a fully versioned image tag (and digest where possible). `latest` breaks reproducibility.
- **Offline**: pre-stage images, engine/plugins, config, inputs and references. `NXF_OFFLINE=true` prevents project/plugin downloads; it does not disable container/task network access. Wave requires its service unless all requirements have been resolved and the offline workflow avoids service calls.
