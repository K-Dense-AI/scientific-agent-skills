# Running nf-core & Custom Pipelines

End-to-end guidance for running pipelines reproducibly. Reviewed with nf-core tools 4.1.0 and the [rnaseq 3.27.0 usage guide](https://nf-co.re/rnaseq/3.27.0/docs/usage/). Commands requiring containers or biological inputs are illustrative and were not executed.

## Table of Contents

- [Find a pipeline](#find-a-pipeline)
- [The standard run pattern](#the-standard-run-pattern)
- [Samplesheets (the input)](#samplesheets-the-input)
- [Parameters and params files](#parameters-and-params-files)
- [Profiles and containers](#profiles-and-containers)
- [Reference genomes / iGenomes](#reference-genomes--igenomes)
- [Institutional configs](#institutional-configs)
- [Offline / air-gapped execution](#offline--air-gapped-execution)
- [Monitoring and troubleshooting](#monitoring-and-troubleshooting)

## Find a pipeline

```bash
nf-core pipelines list                 # all nf-core pipelines, sorted by activity
nf-core pipelines list rna             # keyword search
nextflow info nf-core/rnaseq           # metadata of a locally cached pipeline
```

Browse the catalog at https://nf-co.re/pipelines. Each pipeline page documents its parameters, samplesheet format, and outputs.

## The standard run pattern

1. **Smoke-test** the selected release with its small dataset after reviewing resource/download requirements:

```bash
nextflow run nf-core/rnaseq -r 3.27.0 -profile test,docker --outdir test_results
```

2. **Real run** — pin a revision, choose a container engine, provide a samplesheet:

```bash
nextflow run nf-core/rnaseq -r 3.27.0 \
  -profile docker \
  --input samplesheet.csv \
  --fasta reference.fa --gtf annotation.gtf \
  --outdir results \
  -resume
```

`nextflow run nf-core/rnaseq` auto-pulls the pipeline from GitHub into `~/.nextflow/assets`. Use `nextflow pull nf-core/rnaseq` to pre-fetch/update, and `-r` to pin a tag.

### Interactive command builder

`nf-core pipelines launch` walks through every parameter (validated against the pipeline's `nextflow_schema.json`) and writes a `nf-params.json` you can reuse:

```bash
nf-core pipelines launch nf-core/rnaseq --revision 3.27.0 --params-out nf-params.json
nextflow run nf-core/rnaseq -r 3.27.0 -profile docker -params-file nf-params.json
```

## Samplesheets (the input)

Many nf-core pipelines take a **CSV samplesheet** (via `--input`) to preserve sample metadata. Others use different input interfaces; inspect the selected release’s schema. The exact columns are pipeline-specific (see each pipeline's docs), but a typical RNA-seq sheet:

```csv
sample,fastq_1,fastq_2,strandedness
CONTROL_REP1,s3://.../ctrl_1.fastq.gz,s3://.../ctrl_2.fastq.gz,auto
TREAT_REP1,/data/treat_1.fastq.gz,/data/treat_2.fastq.gz,auto
```

- Leave `fastq_2` empty for single-end data.
- Supported local/remote paths are staged by Nextflow; cloud credentials, permissions and compatible filesystem plugins remain required.
- Validate unique sample/lane identifiers, intended technical-replicate merging, pair orientation, strandedness and reference compatibility. A schema-valid row does not establish these scientific facts.
- Validation (via the `nf-schema` (or `nf-validation` in older releases) plugin) fails fast with clear errors if columns/values are wrong.

## Parameters and params files

Pass parameters three ways (later overrides earlier): config files → `-params-file` → `--cli` flags. For anything non-trivial, prefer a **params file** (reproducible, reviewable):

```bash
nf-core pipelines create-params-file nf-core/rnaseq --revision 3.27.0 --output params.yml
nextflow run nf-core/rnaseq -r 3.27.0 -profile docker -params-file params.yml --outdir results
```

```yaml
# params.yml
input:  samplesheet.csv
outdir: results
fasta: reference.fa
gtf: annotation.gtf
aligner: star_salmon
```

## Profiles and containers

- **Container engine**: pick one — `-profile docker` (local/CI), `-profile singularity` (HPC), `-profile conda` (last resort).
- **`test`**: tiny bundled dataset; always combine with an engine, e.g. `-profile test,docker`.
- Combine comma-separated; strict parser 26.04 applies CLI order, while the legacy parser uses definition order. Layer site config with `-c custom.config` and per-process tweaks via `withName` selectors (see `references/configuration.md`).

## Reference genomes / iGenomes

Many pipelines accept `--genome <KEY>` (e.g. `GRCh38`, `GRCm38`, `R64-1-1`) and pull references from AWS iGenomes automatically. Alternatives:
- Provide your own references explicitly (`--fasta`, `--gtf`, `--star_index`, …) — recommended for control/reproducibility. Add `--save_reference` to keep built indices for reuse.
- Mirror iGenomes locally and set `--igenomes_base` to the local path for offline use.
- `--igenomes_ignore` disables the iGenomes logic entirely.

> The rnaseq 3.27.0 guide treats iGenomes as legacy and discourages it for new analyses. Supply compatible `--fasta`/`--gtf` or a pinned custom `params.genomes` catalogue. Record assembly, annotation release, contig naming, masking, checksums and the tool/version that built each index; a key such as GRCh38 alone is insufficient.

## Institutional configs

nf-core/configs provides ready-made profiles for many HPC systems and clouds (executor, queues, container cache, resource limits). Use one with `-profile <institution>` (e.g. `-profile crick,singularity`); Nextflow fetches it from the central repo. To write your own, see https://nf-co.re/docs/running/configuration/configuration-options and `references/configuration.md`. Point at a local/private config repo with `--custom_config_base` (offline).

## Offline / air-gapped execution

```bash
# On a connected machine: bundle pipeline + configs + containers
nf-core pipelines download nf-core/rnaseq \
  --revision 3.27.0 \
  --container-system singularity \
  --compress none \
  --outdir nf-core-rnaseq

# Transfer the folder, then on the offline machine:
export NXF_OFFLINE=true
export NXF_SINGULARITY_CACHEDIR=/shared/sif
nextflow run nf-core-rnaseq/3_27_0 -profile singularity --input samplesheet.csv --outdir results
```

Use the actual workflow directory printed by the downloader. Tools 4.1.0 sanitizes the revision into a directory such as `3_27_0`; the public download page’s older `workflow/` example does not match this release’s implementation. The bundle does not establish that runtime plugins, references and remote configs are available offline.

To reuse a shared image cache instead of copying images into the bundle, set `$NXF_SINGULARITY_CACHEDIR` and pass `--container-cache-utilisation amend`. Also pre-stage reference genomes locally and set the relevant `--*_index`/`igenomes_base` params, pin all plugin versions, and `export NXF_OFFLINE=true`. See https://nf-co.re/docs/usage/getting_started/offline.

## Monitoring and troubleshooting

- **Logs**: each run prints a live task table; the full `.nextflow.log` is in the launch dir. Find a failed task's work dir in the error message and inspect `.command.sh`, `.command.out`, `.command.err`, `.exitcode` there.
- **Resume**: fix the issue and rerun with `-resume` to avoid recomputing successful tasks.
- **Reports**: add `-with-report -with-trace -with-timeline` to profile resource usage and right-size requests (see `references/configuration.md`).
- **Common failures**: exit 137 → inspect scheduler/task logs to distinguish OOM, timeout or cancellation before changing resources; missing input column → fix the samplesheet; container pull failure → check engine/profile and cache dir; wrong Java/Nextflow version → set `NXF_VER` and check `nextflow info`.
- **Scientific provenance**: retain the full command, resolved non-secret config, params/samplesheet, pipeline/module/plugin revisions, image digests, engine/Java versions, input/reference checksums, seeds and reports. Check expected sample counts and QC failures; `-resume` and successful exit codes are not evidence of biological correctness.
- **Seqera Platform**: run with `-with-tower` (and `TOWER_ACCESS_TOKEN`) for a web dashboard, or launch pipelines from Seqera Platform directly.
