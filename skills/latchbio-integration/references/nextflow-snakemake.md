# Nextflow and Snakemake Integration

Latch supports Python, Nextflow, and Snakemake workflows, but their packaging
paths are not interchangeable. Confirm the SDK version and choose one track
before generating files.

## Nextflow: Documented SDK Wrapper Path

### Prerequisites

- A runnable Nextflow pipeline
- A `nextflow_schema.json`
- Containers or a documented execution profile for every process
- A pinned Latch SDK

Install:

```bash
uv pip install "latch==2.76.8"
```

### Generate metadata

```bash
latch generate-metadata nextflow_schema.json --nextflow
```

Current generation creates:

```text
latch_metadata/
├── __init__.py
└── generated.py
```

- `generated.py` is regenerated from the schema. Do not edit it.
- Put persistent custom metadata and flow changes in `latch_metadata/__init__.py`.
- Re-run generation after changing `nextflow_schema.json`.
- Review inferred file, enum, default, and required types before registration.

SDK 2.67.0 changed Nextflow generation to use one generated dataclass containing
all parameters and a generated base flow. Older `parameters.py` examples may no
longer match the generated layout.

### Register

The currently documented wrapper command is:

```bash
latch login
latch register . \
  --nf-script main.nf \
  --nf-execution-profile docker,test
```

Registration generates a Latch workflow wrapper and `latch.config`. The exact
entrypoint location depends on the generation path and SDK version.

Important:

- If a root `Dockerfile` exists, registration uses it.
- Otherwise Latch can generate a Dockerfile under `.latch/`.
- Passing `--nf-script` again can regenerate and overwrite wrapper code.
- After intentionally customizing a generated entrypoint, re-register without
  `--nf-script` to preserve it.
- Keep custom code in a separate module when possible.

### Generate an entrypoint explicitly

SDK 2.76.8 also exposes:

```bash
latch nextflow generate-entrypoint . \
  --nf-script main.nf \
  --execution-profile docker,test \
  --output wf/custom_entrypoint.py
```

This requires a valid `NextflowMetadata` object in the metadata root.

### Experimental Forch-only registration

The CLI also has:

```bash
latch nextflow register . --script-path main.nf
```

The official CLI guide marks this command **experimental** and only applicable
to Forch, Latch's architecture for running Nextflow in the user's own AWS
account. It is not a general alternative to `latch register --nf-script`.
Use it only for a configured Forch/BYOC project with current Latch guidance.

### Nextflow configuration rules

- Define every process container.
- Use profiles for environment-specific settings rather than editing the
  pipeline for Latch.
- Keep Latch's generated `latch.config` in the effective config chain.
- Use the official Latch shared-storage guidance for processes that need a
  common work directory.
- Configure private registries through Latch's supported credentials path.
- Follow the Latch GPU guide for process accelerators; do not translate Python
  task decorators into Nextflow resource syntax.
- Set `NextflowRuntimeResources.storage_gib` for the runtime/shared filesystem,
  not just final outputs.
- Understand storage-retention cost before increasing
  `storage_expiration_hours`.

### Debugging

```bash
latch register --staging .
latch develop .
latch nextflow attach --execution-id <execution-id>
```

Within `latch develop`, the production storage initializer is unavailable.
Follow the official debug-mode guidance: use the local executor, bypass the
initializer in debug mode, use a compatible Latch Nextflow base image, and
reduce process resources.

## Snakemake: Choose a Compatibility Track

The current docs and current stable package expose different Snakemake tracks.
Do not mix them.

### Track A: legacy flags in 2.76.8 source (documentation conflict)

The `2.76.8` wheel still exposes the `snakemake` extra, legacy metadata classes,
`generate-metadata --snakemake`, and `register --snakefile`. However, the
official CLI guide marks the Snakemake metadata and registration flags
deprecated and says metadata generation no longer works for
`latch >= 2.55.0.a6`.

Treat this as an unresolved source/documentation conflict. The commands below
are useful when maintaining a legacy project already known to use this path,
but should not be presented as a supported new-project flow without confirming
with current Latch documentation or support.

Use Python 3.11 for the broadest compatibility with the pinned Snakemake 7.x
dependency:

```bash
uv venv --python 3.11
source .venv/bin/activate
uv pip install "latch[snakemake]==2.76.8"
```

Generate metadata from the workflow config:

```bash
latch generate-metadata config.yaml --snakemake
```

Register:

```bash
latch register . --snakefile Snakefile
```

Relevant options:

```bash
latch register . \
  --snakefile Snakefile \
  --metadata-root latch_metadata \
  --cache-tasks
```

Use the current `SnakemakeMetadata`, `SnakemakeParameter`, `FileMetadata`,
`EnvironmentConfig`, and `DockerMetadata` APIs from `latch.types.metadata`.
Inspect their signatures before generating hand-written metadata.

### Track B: official Snakemake v2 tutorial

The current Snakemake v2 tutorial is a compatibility-specific path. At the time
of this refresh, it explicitly requires:

```bash
uv venv --python 3.11
source .venv/bin/activate
uv pip install "latch==2.62.1a2"
```

It uses imports such as:

```python
from latch.types.metadata.snakemake_v2 import SnakemakeV2Metadata
```

and commands such as:

```bash
latch snakemake generate-entrypoint .
latch dockerfile --snakemake -c environment.yaml . -f
latch register -y .
```

Those v2 metadata modules and the `latch snakemake` command group are not
present in the stable 2.76.8 source tree. The tutorial's generated Dockerfile
also pins the workflow runtime separately to
`latch[snakemake]==2.55.0.a6`.

Therefore:

- Re-check the official tutorial's exact pin before starting.
- Use an isolated environment.
- Preserve and review both the local CLI pin and generated runtime pin.
- Do not upgrade that environment to stable 2.76.8 without a migration plan.
- Do not copy v2 imports into a stable-track project.
- Treat the alpha pin as pre-release software and validate end to end.

### Snakemake resource and environment rules

- Give every rule CPU and memory resources or define safe defaults in
  `profiles/default/config.yaml`.
- Pin Conda and container environments.
- Keep the Latch executor/storage plugin configuration from the chosen track.
- Use `LatchOutputDir` for output destinations exposed in the form.
- Avoid embedding credentials in `environment.yaml`, Dockerfiles, profiles, or
  generated metadata.

## Generated-File Discipline

Before editing a generated file:

1. Find the command and source file that generated it.
2. Determine whether regeneration overwrites the file.
3. Prefer the documented extension file.
4. If customization of generated code is unavoidable, record the generation
   command and stop passing flags that regenerate it.
5. Diff generated output after every SDK upgrade.

## Release Checklist

- SDK and pipeline-engine versions are pinned.
- Schema/config and generated metadata are in sync.
- Every parameter has the expected type and default.
- Containers and package environments are immutable enough to reproduce.
- Small test data succeeds.
- Resume/cache behavior has been exercised.
- Shared storage has enough capacity and an intentional retention period.
- Result paths and execution reports appear in the Console.
- A clean registration from a fresh checkout works.

## Official Sources

- Nextflow tutorial: https://wiki.latch.bio/workflows/sdk/nextflow/tutorial
- Nextflow overview: https://wiki.latch.bio/workflows/sdk/nextflow/overview
- Nextflow dependencies: https://wiki.latch.bio/workflows/sdk/nextflow/dependencies
- Nextflow profiles: https://wiki.latch.bio/workflows/sdk/nextflow/profiles
- Nextflow GPU guide: https://wiki.latch.bio/workflows/sdk/nextflow/gpus
- Nextflow shared storage: https://wiki.latch.bio/workflows/sdk/nextflow/shared-storage
- Snakemake v2 tutorial: https://wiki.latch.bio/workflows/sdk/snakemake-v2/tutorial
- Snakemake v2 overview: https://wiki.latch.bio/workflows/sdk/snakemake-v2/overview
- CLI source in the 2.76.8 release commit: https://github.com/latchbio/latch/blob/0faa9dcd8186444ac008f50adf95d43f0fa30e06/src/latch_cli/main.py
- Changelog in the 2.76.8 release commit: https://github.com/latchbio/latch/blob/0faa9dcd8186444ac008f50adf95d43f0fa30e06/CHANGELOG.md
