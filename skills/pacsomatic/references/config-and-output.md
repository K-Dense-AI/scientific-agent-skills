# Configuration and outputs

## Samplesheet and input scope

The helper writes exactly two records with columns `patient,sample,status,bam,pbi`:
normal `status=0`, tumor `status=1`; both share patient ID and have different sample
IDs and BAM files. Paths are absolute or remote URIs. PBI is optional and blank
when absent. PacBio PBI is not a coordinate BAI/CSI index. The pipeline aligns
reads with pbmm2 and then generates coordinate indexes; a missing input BAI is
not a defect for unaligned HiFi BAMs.

The reviewed upstream schema also permits `.cram` and `.bai/.crai` in its broadly
named `bam`/`pbi` fields. The usage docs describe unaligned PacBio BAM/PBI, and
this helper deliberately validates that narrower path. It does not promise
CRAM compatibility through the complete workflow. Upstream can handle multiple
samples, but this helper generates one tumor and one normal only; additional
samples require deliberate pairing review (upstream pairs by patient).

## Artifact and parameter controls

| Option | Contract |
| --- | --- |
| `--pipeline-version` | Remote Nextflow `-r`; default reviewed commit for nf-core/pacsomatic |
| `--repo-path` | Existing local pipeline containing main.nf; checkout/version control remains external; omit `--pipeline-version` |
| `--checkout-dir` | Explicit opt-in clone; a new clone checks out the requested revision; an existing clone must already match |
| `--params-file` | Existing local YAML/JSON for pipeline parameters; explicit helper input/outdir/reference wins |
| `--nextflow-config` | Existing local Nextflow config for task executor/resources; forwarded as `-c` |
| `--use-generated-params-file` | Use the generated YAML when no custom params file was supplied |
| `--resume` | Reuse compatible cached tasks; requires retained `.nextflow` state and work files |
| `--with-report`, `--with-dag` | Optional Nextflow report/DAG paths; choose supported formats (e.g. HTML) |
| `--overwrite` | Replace reviewed helper artifacts; never allows input/artifact aliasing |

Writes `<outdir>/samplesheet.csv`, `pacsomatic.params.generated.yaml` and
`run_pacsomatic.<executor>.sh` (`none` uses `local`). Default work path is
`<outdir>/work`. Generated YAML quotes string values. A custom params file is
referenced, not copied or merged into the generated minimal YAML; retain it and
its provenance too. Generated paths alone are not a complete run manifest.

## Scheduler semantics

`--executor` controls only how the **driver script** is launched:

| Value | Submit command | Driver resource conventions |
| --- | --- | --- |
| `local`, `none` | `bash SCRIPT` | No allocation or resource enforcement |
| `slurm` | `sbatch SCRIPT` | `--cpus-per-task`, total `--mem` MiB, `HH:MM:SS`; `%j` job ID in log names |
| `lsf` | `bsub < SCRIPT` | `-n`, explicit `-M ...MB`, `-W HH:MM`; `%J` log names |
| `pbs` | `qsub SCRIPT` | **PBS Pro/OpenPBS** `select=1:ncpus=...:mem=...mb`; not portable Torque syntax |
| `sge` | `qsub SCRIPT` | `-pe smp` and per-slot `h_vmem` rounded upward in MiB |

The helper's `--walltime` always means hours:minutes[:seconds]; minute/second
fields must be below 60 and total time positive. LSF requires zero seconds.
Resources must be positive and finite. PBS/SGE default logs are fixed
`launcher.out`/`launcher.err`; choose unique names for simultaneous submissions.
Log paths and scheduler directive fields use a conservative character set; no
whitespace, shell expansions or embedded newlines are accepted.

These are portable starting templates, not verified cluster allocations.
Confirm site-specific LSF per-process/per-job `-M` interpretation and memory
reservation policy, PBS resource names, and SGE `smp`/`h_vmem` configuration.
A driver job must be allowed to submit tasks and remain alive until they finish.
Set task resources and executor in a reviewed site profile/config, independently
of the outer scheduler. If tasks run locally inside a driver allocation, enforce
Nextflow executor capacity and per-process resource limits yourself.

No HPC scheduler was contacted during skill testing. Tests mock submission argv,
stdin, exit handling and job ID parsing (LSF/Slurm/PBS/SGE). Success from `sbatch`,
`bsub` or `qsub` means acceptance, not successful scientific results.

## Runtime checks

`--use-current-path` uses installed tools. Otherwise the helper resolves the named
Conda environment and prepends its `bin` for both checks and the generated script.
`--create-conda-env` requires an explicitly supplied environment YAML and is
unavailable in dry-run mode. `--module-load` accepts plain `module ...` commands
only; preflight cannot evaluate cluster module initialization automatically.

Preflight runs Nextflow `-version`, checks minimum 24.04.2, checks Java using
`JAVA_CMD`/`JAVA_HOME`/PATH, and checks the selected runtime executable. A profile
`singularity` requires `singularity`; `apptainer` requires `apptainer`. This does
not test daemon permissions, containers, plugins, remote credentials, task
execution or GPU compatibility. `--check-host-bio-tools` is an optional partial
PATH inventory, not a complete dependency resolver; there is no upstream
container profile named `local`.

## Results and triage

Upstream groups results under `alignment`, `germline_snv`, `somatic_snv`,
`somatic_sv`, `somatic_cnv`, `methylation`, `tumor_clonality`, `signature_analysis`,
`multiqc` and `pipeline_info`. Presence depends on enabled/successful branches.
Do not interpret a missing branch as a negative biological finding.

The pinned config uses timestamped execution report/timeline/trace filenames
and a timestamped HTML DAG under `pipeline_info`; the generic website output
page still shows some older DOT/SVG names. Inspect actual outputs, including
`params.json`, `samplesheet.valid.csv`, software versions, run exit status and
QC reports. Start failures at `<outdir>/.nextflow.log`, driver logs, then the
failing work task's `.command.sh`, `.command.err`, `.command.out` and `.exitcode`.
