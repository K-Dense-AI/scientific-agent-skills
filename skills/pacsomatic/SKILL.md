---
name: pacsomatic
description: Prepares and launches nf-core/pacsomatic matched tumor-normal PacBio HiFi genomics workflows from unaligned BAM inputs. Supports samplesheet generation, pinned Nextflow launch artifacts, local checks, LSF/Slurm/PBS Pro/SGE launcher submission, and startup troubleshooting. Use for pacsomatic run preparation and execution, not general short-read somatic analysis or medical imaging PACS.
license: MIT
compatibility: Requires Python 3.10+ for the standard-library helper. Execution requires Bash, Nextflow >=24.04.2, a compatible Java runtime (current Nextflow supports Java 17-26), the selected container runtime and optionally a scheduler. Network access is needed for uncached pipeline code, plugins, references and containers.
metadata:
  version: "1.4"
  skill-author: Beifang Niu
  contributors: Haidong, Wenchao
  upstream-pipeline: https://github.com/nf-core/pacsomatic
  upstream-revision: "24c84cb371b0339c1d65a4de9451671945e19772"
  last-reviewed: "2026-10-01"
---

# pacsomatic

## When to use

Use [scripts/run_pacsomatic.py](scripts/run_pacsomatic.py) to prepare one matched
PacBio HiFi tumor/normal pair, generate a samplesheet and reproducible launch
artifacts, and launch locally or submit the **Nextflow driver** to a scheduler.
The pipeline realigns input BAMs; this helper targets unaligned HiFi BAMs and
optional PacBio `.pbi` indexes. Do not substitute short reads or treat a BAM
filename as evidence of platform, matched identity, or methylation information.

The reviewed upstream `dev` commit is
`24c84cb371b0339c1d65a4de9451671945e19772`. GitHub had no releases or tags on
2026-10-01, despite the internal manifest saying `1.0.0`. The helper pins that
commit by default for `nf-core/pacsomatic`; it does not invent a release tag.
This is a source-reviewed development workflow, not a clinically validated assay.
See [references/pacsomatic_guide.md](references/pacsomatic_guide.md) for sources
and scientific checks.

## Workflow

1. Obtain distinct tumor and normal BAM paths, patient ID, distinct sample IDs,
   output directory, and exactly one reference mode: `--fasta` or `--genome`.
   IDs and BAM/PBI/FASTA paths must have no whitespace. Local inputs must be
   nonempty regular files. Remote BAM/PBI/FASTA URIs are passed through without
   downloading or authenticating; use managed filesystem/cloud credentials,
   never embed secrets or signed URLs in generated files.
2. Confirm PacBio HiFi read groups and sample identity from acquisition metadata;
   confirm that MM/ML modification tags needed for methylation have been retained.
   Verify reference sequence/contig compatibility for every annotation resource.
3. Generate artifacts with `--dry-run`. This performs helper checks and writes
   files, but does **not** invoke the pipeline, validate BAM contents, check remote
   availability, resolve every pipeline parameter, or verify biological suitability.
   Missing runtime tools are warnings here. `--dry-run` cannot be combined with
   `--run`/`--submit`, cloning, or environment creation.
4. Review samplesheet, generated params YAML, script, pipeline revision, profiles,
   and branch-specific resources/skips. Existing artifacts require explicit
   `--overwrite`; input files can never be artifact targets. `config.yaml` is an
   operator reference, not an automatically loaded configuration file.
5. For execution, select the actual runtime with `--use-current-path` or an
   existing `--conda-env`. Load cluster modules **before** invoking the helper;
   `--module-load` only repeats those commands in the generated script. No Conda
   YAML is bundled; creating an environment needs `--conda-env-file` explicitly.
6. Use `--run` only for requested execution. For HPC, distinguish the outer
   launcher scheduler (`--executor`) from Nextflow's per-task `process.executor`,
   configured by a site profile or `--nextflow-config`. Driver CPU/memory requests
   do not constrain task resources. Read [references/config-and-output.md](references/config-and-output.md).
7. Report artifact paths, revision, checks/warnings, run type, submission ID if
   present, and a concrete next QC or failure-triage step. Scheduler acceptance
   is not pipeline completion. Keep the output directory and work/cache state
   stable for `--resume`; scripts run with the output directory as their cwd.

## Examples

Run these from the repository root. Paths and site settings are **illustrative**;
local tests use synthetic placeholders only, not human genomic data.

```bash
python skills/pacsomatic/scripts/run_pacsomatic.py \
  --tumor-bam /data/P001_T.bam --normal-bam /data/P001_N.bam \
  --patient-id P001 --tumor-sample-id P001_T --normal-sample-id P001_N \
  --outdir /results/P001 --fasta /refs/GRCh38.fa \
  --profile apptainer --use-current-path --dry-run
```

After reviewing artifacts, a Slurm launch can use the same inputs plus the
following options (replace `--dry-run` with `--run`):

```text
--executor slurm --queue compute --project my_account
--cpus 2 --memory-gb 8 --walltime 48:00
--nextflow-config /configs/slurm.config --overwrite --run
```

Those resources are for the driver, assuming the reviewed infrastructure config
sets `process.executor = 'slurm'` and suitable task queue/resources. The helper
normalizes `48:00` to Slurm `48:00:00` (48 hours). Do not add a `sanger` profile
unless actually using that institution's LSF infrastructure.

Custom pipeline parameters go in `--params-file`; infrastructure goes in
`--nextflow-config` (`-c`). The helper's explicit input/outdir/reference options
win over params-file values. `--extra-args` is tokenized and shell-quoted, but
cannot override these managed inputs/configuration options. Keep paths inside
external params/config files absolute because the launcher cwd is the outdir.

## Verification and references

```bash
uv run skills-ref validate skills/pacsomatic
python tests/run_all.py --isolated pacsomatic
```

The standard-library suite checks local artifact behavior, path protections,
CLI modes, runtime failures and mocked scheduler submissions. Native Nextflow
checks use a tiny local workflow; they do not establish that pacsomatic's full
containerized scientific pipeline succeeds on a given dataset or cluster.

- [Operator playbook](references/agent-playbook.md)
- [Configuration, scheduler and output contracts](references/config-and-output.md)
- [Upstream sources and scientific checks](references/pacsomatic_guide.md)
