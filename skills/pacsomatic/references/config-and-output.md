# Config And Output

## Required Inputs

- `--tumor-bam`: tumor BAM path
- `--normal-bam`: normal BAM path
- `--patient-id`
- `--tumor-sample-id`
- `--normal-sample-id`
- `--outdir`
- one reference mode:
  - `--fasta`, or
  - `--genome`

## Core Optional Controls

- `--profile`: Nextflow profile list (for example `singularity,sanger`)
- `--pipeline-version`: release pin for reproducibility
- `--params-file`: structured pipeline params
- `--resume`: rerun interrupted work
- `--with-report`: Nextflow report path
- `--with-dag`: Nextflow DAG path

## Execution Backend Controls

- `--executor`: `local`, `none`, `lsf`, `slurm`, `pbs`, or `sge`

Direct CLI execution is supported in all modes. When `--run` is used, the
helper runs backend-native launch commands:

- `local` / `none`: `bash <script>`
- `lsf`: `bsub < <script>`
- `slurm`: `sbatch <script>`
- `pbs` / `sge`: `qsub <script>`

## Scheduler Controls (when executor is scheduler-backed)

- `--project`
- `--queue`
- `--cpus`
- `--memory-gb`
- `--walltime`
- `--job-name`
- `--logdir`
- `--stdout-file`
- `--stderr-file`

## Helper Outputs

The helper writes:

- samplesheet CSV (default `<outdir>/samplesheet.csv`)
- launch script (default `<outdir>/run_pacsomatic.<executor>.sh`)

It also prints:

- backend-specific run command (for example `bash`, `bsub`, `sbatch`, or `qsub`)
- launcher output when `--run` is used
- detected job ID when parseable from scheduler output

## Samplesheet Schema

Expected columns:

- `patient`
- `sample`
- `status`
- `bam`
- `pbi`

Notes:

- `bam` should be the full path to the sample BAM.
- `pbi` is optional.

Status values:

- tumor: `1`
- normal: `0`

## Run Modes

- generate only (default): write artifacts, no scheduler submission
- `--dry-run`: validate inputs/dependencies and write artifacts
- `--run`: execute or submit generated launch script using selected `--executor`

## Official Output Anchors

nf-core/pacsomatic organizes results under grouped directories, including:

- `alignment`
- `germline_snv`
- `somatic_snv`
- `somatic_sv`
- `somatic_cnv`
- `methylation`
- `tumor_clonality`
- `signature_analysis`
- `pipeline_info`
- `multiqc`
