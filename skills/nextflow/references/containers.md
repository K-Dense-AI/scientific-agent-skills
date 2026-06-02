# Software Dependencies: Containers & Conda

Nextflow runs each process in an isolated software environment so pipelines are reproducible and portable. Never depend on tools installed on the host. Source: https://www.nextflow.io/docs/latest/container.html , https://www.nextflow.io/docs/latest/conda.html , https://www.nextflow.io/docs/latest/wave.html

## Choosing an engine

| Engine | Use when | Enable |
|--------|----------|--------|
| **Docker** | Local dev / laptops / CI with root or docker group | `docker.enabled = true` |
| **Singularity / Apptainer** | HPC clusters (no root, shared FS) — most common in academia | `singularity.enabled = true` (or `apptainer.enabled = true`) |
| **Podman** | Rootless alternative to Docker | `podman.enabled = true` |
| **Charliecloud / Sarus / Shifter** | Site-specific HPC runtimes | `charliecloud.enabled = true`, etc. |
| **Conda / Mamba** | No container runtime available; quick envs | `conda.enabled = true` |
| **Wave** | On-the-fly container builds from conda/Dockerfiles, private registries, cloud speedups | `wave.enabled = true` |

Enable exactly **one** container engine. nf-core ships these as profiles, so users typically just pass `-profile docker` / `-profile singularity` / `-profile conda`.

## The container directive

Each process declares its image; the engine config decides how it runs.

```nextflow
process SAMTOOLS_SORT {
    container 'quay.io/biocontainers/samtools:1.19.2--h50ea8bc_0'
    conda     'bioconda::samtools=1.19.2'    // fallback when -profile conda is used
    script:
    """
    samtools sort -@ $task.cpus -o sorted.bam $input
    """
}
```

nf-core modules declare **both** a `container` (often a Biocontainers/Galaxy depot image) and a `conda` line, so the same module works under any engine. In nf-core modules the `conda` directive references a separate file — `conda "${moduleDir}/environment.yml"` — rather than an inline string. Biocontainers images live on `quay.io/biocontainers/...` (and `https://depot.galaxyproject.org/singularity/...` for Singularity), auto-built from Bioconda recipes.

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
- Apptainer (the renamed Singularity) uses the same options under the `apptainer` scope.

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

Conda is the least reproducible option (solver drift, no OS isolation); prefer containers for published results. Use `NXF_CONDA_CACHEDIR` to reuse built envs.

## Wave + Fusion

**Wave** builds/augments containers on demand from a `conda` directive or a Dockerfile, pushes to a registry, and can mount private registries. **Fusion** is a virtual distributed file system that lets tasks read/write cloud object storage (S3/GCS) as if local — big speedups on cloud.

```groovy
wave {
    enabled  = true
    strategy = 'conda'           // build images from process conda directives
}
fusion.enabled = true            // pair with Wave on cloud executors
tower.accessToken = secrets.TOWER_ACCESS_TOKEN   // some Wave features use Seqera creds
```

## Common gotchas

- **Two engines enabled at once** → errors or surprising behavior. Enable one (use profiles).
- **Root-owned outputs** with Docker → set `runOptions = '-u $(id -u):$(id -g)'`.
- **Singularity can't see input files** → enable `autoMounts` or add `-B` binds; ensure the work dir and inputs are on bound paths.
- **HPC pull storms / quota blowups** → set a shared `NXF_SINGULARITY_CACHEDIR` and pre-pull with `nf-core pipelines download` (see `references/running-pipelines.md`).
- **Pinning**: always use a fully versioned image tag (and digest where possible). `latest` breaks reproducibility.
- **Offline**: pre-stage all images (Singularity SIFs or a local Docker registry) and set `NXF_OFFLINE=true`.
