---
name: pacsomatic
description: Operator toolkit for nf-core/pacsomatic matched tumor-normal workflows from BAM inputs. Use this skill when the user needs to validate run inputs, generate pacsomatic-compliant samplesheets, prepare reproducible Nextflow launch artifacts, run locally or submit to schedulers (LSF/Slurm/PBS/SGE), and triage execution failures. Triggers on requests to run pacsomatic, prepare launch commands/scripts, perform dry-run checks, or troubleshoot pipeline startup and scheduler submission errors.
license: MIT
metadata:
  version: "1.0"
  skill-author: Beifang Niu
  contributors: Haidong, Wenchao
  upstream-pipeline: https://github.com/nf-core/pacsomatic
---

# pacsomatic

## Overview

This skill provides a reproducible execution workflow for nf-core/pacsomatic, centered on a single helper entrypoint that handles validation, artifact generation, and optional execution.

Primary entrypoint:
- `scripts/run_pacsomatic.py`

The helper script:
- validates required identifiers, files, reference mode, and runtime prerequisites
- writes a pacsomatic-compatible samplesheet (`patient,sample,status,bam,pbi`)
- generates a params YAML and launch script for reproducible reruns
- supports dry-run validation and run/submit execution paths

Use this skill as the default path for pacsomatic operations. Do not bypass it with manually assembled `nextflow run nf-core/pacsomatic` commands unless the user explicitly asks for manual command construction.

## When to Use This Skill

Invoke this skill when the user asks to:
- run matched tumor-normal analysis from BAM files
- generate or fix pacsomatic samplesheet and launch artifacts
- execute locally or submit to schedulers (LSF/Slurm/PBS/SGE)
- perform dry-run validation before execution
- troubleshoot launch failures or summarize run outputs

Do not use this skill for:
- deep biological interpretation beyond run-level sanity checks
- editing pipeline internals unless explicitly requested

Typical trigger phrases:
- "run nf-core/pacsomatic for this tumor-normal pair"
- "prepare pacsomatic samplesheet and launch script"
- "do a dry run first and tell me what is missing"
- "submit pacsomatic to slurm/lsf and return the job id"
- "why did pacsomatic submission fail"

## Routing and Execution Rules

1. Always collect required run inputs first.
2. Always route through `scripts/run_pacsomatic.py` for validation and artifact generation.
3. Default to `--dry-run` when the user asks for checks/validation only.
4. Use `--run` only when the user asks to execute/submit.
5. For scheduler modes, include executor-specific resource arguments and return detected job ID when available.
6. If execution fails, report first failure point and next triage target (`.nextflow.log`, `pipeline_info`, failing task logs).

## Inputs Required

Required:
- tumor BAM path
- normal BAM path
- patient ID
- tumor sample ID
- normal sample ID
- output directory
- exactly one reference mode: `--fasta` or `--genome`

Optional:
- profile, resources, scheduler account/queue
- pipeline version (`-r`)
- params file, resume/report/dag flags
- `--dry-run` and/or `--run`

## Workflow

1. Validate identity and input constraints.
2. Validate required local paths (BAM, optional PBI, optional FASTA).
3. Resolve runtime and dependency checks.
4. Build samplesheet and generated params YAML.
5. Generate launch script for selected executor.
6. If `--dry-run` and not `--run`, stop after artifact generation.
7. If `--run`, execute locally or submit to scheduler.
8. Return command/script path, validation status, and job ID (if detected).

## Agent Response Contract

Every response after invocation should include:
- exact command used or generated script path
- confirmation that validation checks ran
- run type (`dry-run` vs `run`)
- scheduler job ID when available
- one concrete next step for validation/triage

## Quick Start

Dry run:

```bash
python scripts/run_pacsomatic.py \
  --tumor-bam /path/to/tumor.bam \
  --normal-bam /path/to/normal.bam \
  --patient-id P001 \
  --tumor-sample-id P001_T \
  --normal-sample-id P001_N \
  --outdir /path/to/output \
  --genome GRCh38 \
  --profile singularity,sanger \
  --dry-run
```

Scheduler execution example (Slurm):

```bash
python scripts/run_pacsomatic.py \
  --tumor-bam /path/to/tumor.bam \
  --normal-bam /path/to/normal.bam \
  --patient-id P001 \
  --tumor-sample-id P001_T \
  --normal-sample-id P001_N \
  --outdir /path/to/output \
  --genome GRCh38 \
  --profile singularity,sanger \
  --executor slurm \
  --queue compute \
  --project my_account \
  --cpus 16 \
  --memory-gb 64 \
  --walltime 48:00 \
  --run
```

## Configuration

Use `config.yaml` as the baseline for profile/executor/runtime defaults. Override at invocation time when user requirements differ.

## Testing

Run unit tests from skill root:

```bash
python -m unittest discover -s tests -v
```

## References

- `references/agent-playbook.md`
- `references/config-and-output.md`
- `references/pacsomatic_guide.md`
- `scripts/run_pacsomatic.py`
