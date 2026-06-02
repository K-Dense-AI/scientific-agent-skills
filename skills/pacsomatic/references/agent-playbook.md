# Agent Playbook

## What The User Needs To Provide

Users only need to provide run inputs; they do not need to know pipeline internals:

- tumor BAM path
- normal BAM path
- reference input (`--fasta` path or `--genome` key)
- output directory

Optional:

- sample metadata IDs
- executor/resource preferences
- optional `pbi` paths

No repository checkout directory is required for this skill.

Use this sequence when helping a user run nf-core/pacsomatic:

1. Collect required inputs.
   - tumor BAM
   - normal BAM
   - patient ID
   - tumor sample ID
   - normal sample ID
   - output directory
   - one reference mode: `--fasta` or `--genome`
2. Validate naming rules.
   Patient/sample identifiers cannot contain spaces.
3. Validate local input paths.
   Local BAMs must exist. `pbi` is optional, but if provided the file must exist.
4. Start with a dry run when uncertain.
   Use `--dry-run` to validate assumptions and generate artifacts without scheduling.
5. Launch when requested.
   Use `--run` with a selected `--executor` (`local`, `lsf`, `slurm`, `pbs`, or `sge`).
6. After submission.
   Report generated samplesheet path, script path, printed run command, and detected job ID if present.
7. If pipeline fails later.
   Inspect launcher logs first, then Nextflow report and DAG outputs.

Recommended helper command:

```bash
python .github/skills/pacsomatic/scripts/run_pacsomatic.py \
  --tumor-bam /path/to/tumor.bam \
  --normal-bam /path/to/normal.bam \
  --patient-id P001 \
  --tumor-sample-id P001_T \
  --normal-sample-id P001_N \
  --outdir /path/to/output \
  --genome GRCh38 \
  --profile singularity,sanger \
   --executor local \
  --dry-run
```

Launch command variant:

```bash
python .github/skills/pacsomatic/scripts/run_pacsomatic.py \
  --tumor-bam /path/to/tumor.bam \
  --normal-bam /path/to/normal.bam \
  --patient-id P001 \
  --tumor-sample-id P001_T \
  --normal-sample-id P001_N \
  --outdir /path/to/output \
  --fasta /path/to/reference.fa \
  --profile singularity,sanger \
   --executor lsf \
  --run
```
