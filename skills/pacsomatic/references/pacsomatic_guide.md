# Pacsomatic Guide

This guide summarizes the official nf-core/pacsomatic usage and how this skill
helps an agent validate, prepare, and launch runs across compute platforms.

## What nf-core/pacsomatic runs

nf-core/pacsomatic is a Nextflow pipeline for matched tumor/normal PacBio HiFi
somatic analysis.

Typical upstream command from official docs:

```bash
nextflow run nf-core/pacsomatic \
  -profile <docker/singularity/.../institute> \
  --input samplesheet.csv \
  --outdir <OUTDIR> \
  --genome GRCh38
```

Important notes from docs:

- Input is a CSV samplesheet with columns: `patient,sample,status,bam[,pbi]`.
- `status` uses `1` for tumor and `0` for normal.
- Pipeline parameters should be passed via CLI flags or `-params-file`, not `-c`.

## Cross-agent reuse

This skill can be reused by other agents in the same workspace.

- Keep the whole folder `.github/skills/pacsomatic` intact when reusing.
- Other agents can either:
  - call `scripts/run_pacsomatic.py` to generate a backend-aware launch script, or
  - emit a direct platform-native script and return the matching launcher command.
- If moving to another repository, copy the same folder structure and keep
  `SKILL.md`, `references/`, and `scripts/` together.
- Validate environment assumptions per cluster (Nextflow module version,
  profile such as `singularity,sanger`, queue/project names, and network access
  for remote BAM URLs).

## Minimal samplesheet format

```csv
patient,sample,status,bam,pbi
ID1,ID1_tumor,1,/path/ID1_tumor.bam,/path/ID1_tumor.bam.pbi
ID1,ID1_normal,0,/path/ID1_normal.bam,/path/ID1_normal.bam.pbi
```

`pbi` is optional. If not available, leave it blank.

## Platform-aware execution model in this skill

By default, the helper generates artifacts. With `--run`, it executes/submits
using the selected `--executor` backend.

It produces:

- A validated samplesheet CSV from tumor/normal BAM inputs
- A standalone launch script that runs Nextflow + nf-core/pacsomatic
- A ready run command (for example `bash`, `bsub`, `sbatch`, `qsub`)
- Launcher output and detected job ID when `--run` is enabled

## Example: generate script only

```bash
python .github/skills/pacsomatic/scripts/run_pacsomatic.py \
  --tumor-bam /data/P1_tumor.bam \
  --normal-bam /data/P1_normal.bam \
  --patient-id P1 \
  --tumor-sample-id P1_tumor \
  --normal-sample-id P1_normal \
  --fasta /refs/GRCh38.fa \
  --outdir /results/p1 \
  --profile singularity \
  --executor local \
  --queue normal \
  --cpus 16 \
  --memory-gb 64 \
  --walltime 48:00
```

## Example: dry-run validation

```bash
python .github/skills/pacsomatic/scripts/run_pacsomatic.py \
  --tumor-bam /data/P1_tumor.bam \
  --normal-bam /data/P1_normal.bam \
  --patient-id P1 \
  --tumor-sample-id P1_tumor \
  --normal-sample-id P1_normal \
  --genome GRCh38 \
  --outdir /results/p1 \
  --profile singularity \
  --executor local \
  --dry-run
```

## Example: generate and submit immediately

```bash
python .github/skills/pacsomatic/scripts/run_pacsomatic.py \
  --tumor-bam /data/P1_tumor.bam \
  --normal-bam /data/P1_normal.bam \
  --patient-id P1 \
  --tumor-sample-id P1_tumor \
  --normal-sample-id P1_normal \
  --genome GRCh38 \
  --outdir /results/p1 \
  --profile singularity \
  --executor lsf \
  --run
```

## Example: submit on Slurm

```bash
python .github/skills/pacsomatic/scripts/run_pacsomatic.py \
  --tumor-bam /data/P1_tumor.bam \
  --normal-bam /data/P1_normal.bam \
  --patient-id P1 \
  --tumor-sample-id P1_tumor \
  --normal-sample-id P1_normal \
  --genome GRCh38 \
  --outdir /results/p1 \
  --profile singularity \
  --executor slurm \
  --queue compute \
  --cpus 16 \
  --memory-gb 64 \
  --run
```

## Direct command-line operation (no agent wrapper)

The helper is a standalone CLI and can be run directly from shell scripts,
terminal sessions, CI jobs, or workflow launch wrappers.

Supported HPC schedulers via `--executor`:

- `lsf` (uses `bsub`)
- `slurm` (uses `sbatch`)
- `pbs` (uses `qsub`)
- `sge` (uses `qsub`)

Local direct execution is also supported with:

- `--executor local` (runs generated script with `bash`)

## Direct LSF script (no Python wrapper)

If users request a ready-to-submit LSF script directly, provide a `.lsf.sh`
file that can be submitted as-is.

Example file: `submit_pacsomatic_hg008.lsf.sh`

```bash
#!/usr/bin/env bash
#BSUB -J Somatic_singularity
#BSUB -P Somatic_singularity
#BSUB -q heavy_io
#BSUB -n 16
#BSUB -M 64000
#BSUB -W 48:00
#BSUB -o out%J.out
#BSUB -e err%J.err

set -euo pipefail

RUN_DIR="${RUN_DIR:-$PWD/pacsomatic_hg008_run}"
OUTDIR="${OUTDIR:-$RUN_DIR/results}"
WORKDIR="${WORKDIR:-$RUN_DIR/work}"
SAMPLESHEET="$RUN_DIR/samplesheet.csv"

mkdir -p "$RUN_DIR" "$OUTDIR" "$WORKDIR"

cat > "$SAMPLESHEET" << 'CSV'
patient,sample,status,bam,pbi
Patient_HG008,DS_MT_T,1,https://raw.githubusercontent.com/nf-core/test-datasets/pacsomatic/testdata/HG008_Downsample_MT_tumor.bam,
Patient_HG008,DS_MT_N,0,https://raw.githubusercontent.com/nf-core/test-datasets/pacsomatic/testdata/HG008_Downsample_MT_normal.bam,
CSV

module load nextflow/21.10.5
export NXF_WORK="$WORKDIR"

nextflow run nf-core/pacsomatic \
  -profile singularity,sanger \
  --input "$SAMPLESHEET" \
  --outdir "$OUTDIR" \
  --genome GRCh38 \
  -with-report "$OUTDIR/HiFi_Somatic_Nextflow_Run_Report.html" \
  -with-dag "$OUTDIR/HiFi_Somatic_Flowchart.png" \
  -resume
```

Submit with:

```bash
bsub < submit_pacsomatic_hg008.lsf.sh
```

## LSF examples aligned with your cluster style

The script supports your style of submission, including `-P`, queue switching,
`module load nextflow/21.10.5`, `-resume`, and report/DAG outputs.

Built-in defaults now match your common combo:

- project: `Somatic_singularity`
- queue: `heavy_io`
- module-load: `module load nextflow/21.10.5`

Default LSF output naming now follows your style:

- stdout: `out%J.out`
- stderr: `err%J.err`

You can override with `--stdout-file` and `--stderr-file`, and optionally set
`--logdir` to place them under a specific directory.

```bash
python .github/skills/pacsomatic/scripts/run_pacsomatic.py \
  --tumor-bam /data/P1_tumor.bam \
  --normal-bam /data/P1_normal.bam \
  --patient-id P1 \
  --tumor-sample-id P1_tumor \
  --normal-sample-id P1_normal \
  --genome GRCh38 \
  --outdir /results/p1 \
  --project Somatic_test \
  --queue heavy_io \
  --memory-gb 20 \
  --job-name Somatic_test \
  --module-load "module load nextflow/21.10.5" \
  --with-report HiFi_Somatic_Nextflow_Run_Report.html \
  --with-dag HiFi_Somatic_Flowchart.png
```

For your Sanger configs usage, set combined profiles such as:

```bash
--profile singularity,sanger
```

Reference: <https://nf-co.re/configs/sanger/>

## Best practices

- Ensure BAMs are coordinate-valid and index files are available when possible.
- Use explicit pipeline version with `--pipeline-version` for reproducibility.
- Prefer pinning `--pipeline-version` when using fixed test datasets to avoid schema drift across pipeline revisions.
- Use `--params-file` for large parameter sets and keep script options minimal.
- Prefer containerized profile (`singularity` or `docker`) on HPC.
- Set `NXF_OPTS` memory ceiling if Nextflow launcher memory spikes.
- nf-core/pacsomatic may require a newer Nextflow than legacy module versions; if the cluster allows, prefer a modern Nextflow release compatible with the pipeline.
