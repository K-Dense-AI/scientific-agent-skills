# Ready-to-Use and Referenced Workflows

Latch exposes ready-to-run workflows in two distinct ways:

1. The Latch Console and Latch MCP expose a broad catalog, including workflows
   such as AlphaFold, CRISPResso2, Bulk RNA-seq, and others.
2. The `latch.verified` Python package exports a small set of typed reference
   launch plans that can be composed into a custom SDK workflow.

Do not assume every Console workflow has a Python import.

## Current `latch.verified` Exports

In `latch==2.76.8`, `latch.verified` exports:

```python
from latch.verified import (
    deseq2_wf,
    gene_ontology_pathway_analysis,
    mafft,
    rnaseq,
    trim_galore,
)
```

The package does **not** currently export:

- `alphafold`
- `colabfold`
- `bulk_rnaseq`
- `pathway_enrichment`
- `scvelo`
- `emptydrops`
- `crispresso2`
- `phylogenetics`
- `list_workflows`

Those names appeared in older generated examples but are not public exports in
the current SDK.

## Inspect Before Composing

Reference wrappers expose typed interfaces and internally pin a registered
workflow name and version. From the skill root, inspect exports and parameter
types:

```bash
uv run --no-project --python 3.12 --with "latch==2.76.8" \
  python scripts/inspect_latch_sdk.py
```

Or from the repository root:

```bash
uv run --no-project --python 3.12 --with "latch==2.76.8" \
  python skills/latchbio-integration/scripts/inspect_latch_sdk.py
```

Do not add a made-up `workflow_version=` argument. The wrapper's
`@reference_launch_plan` declaration controls its version.
Read the installed wrapper module when exact default values are needed.

## Compose MAFFT

```python
from latch import workflow
from latch.types import LatchFile, LatchOutputDir
from latch.verified import mafft
from latch.verified.mafft import AlignmentMode


@workflow
def multiple_sequence_alignment(
    unaligned_sequences: LatchFile,
    output_directory: LatchOutputDir,
) -> LatchFile:
    return mafft(
        output_directory=output_directory,
        unaligned_seqs=unaligned_sequences,
        alignment_mode=AlignmentMode.auto,
        gap_penalty=1.53,
        offset=0.0,
        maxiterate=0,
        output_file="aligned_mafft.fa",
    )
```

## Compose Pathway Analysis

```python
from latch import workflow
from latch.types import LatchDir, LatchFile, LatchOutputDir
from latch.verified import gene_ontology_pathway_analysis


@workflow
def pathway_report(
    contrast_csv: LatchFile,
    report_name: str,
    output_directory: LatchOutputDir,
) -> LatchDir:
    return gene_ontology_pathway_analysis(
        contrast_csv=contrast_csv,
        report_name=report_name,
        number_of_pathways=20,
        output_location=output_directory,
    )
```

## Other Typed Wrappers

### DESeq2

Import `deseq2_wf`. Its current interface supports single or multiple raw count
tables, manual conditions or a conditions table, a structured design formula,
plot count, and an optional output directory. Inspect the signature rather than
copying simplified examples that use nonexistent `count_matrix` or
`sample_metadata` parameters.

### RNA-seq

Import `rnaseq` plus its current types from `latch.verified.rnaseq`, including:

- `Sample`
- `SingleEndReads`
- `PairedEndReads`
- `Strandedness`
- `LatchGenome`
- `AlignmentTools`

The wrapper has several fork-selector parameters and is not interchangeable
with a hypothetical `bulk_rnaseq(fastq_r1=..., fastq_r2=...)` call.

### Trim Galore

Import `trim_galore` plus `BaseQualityEncoding` and `AdapterSequence` from
`latch.verified.trim_galore`. Its current signature is detailed and includes
paired inputs, adapter options, clipping, quality, and output settings.

## Discover Through Latch MCP

When Latch MCP is configured:

1. Call `list_workspaces` and choose the intended workspace.
2. Call `list_workflows` to discover public and workspace workflows.
3. Call `get_workflow_schema` for the selected workflow.
4. Validate every parameter against that returned schema.
5. Show the workflow, workspace, resource/cost implications, and parameter
   summary to the user.
6. Obtain confirmation.
7. Call `launch_workflow`.
8. Monitor with `get_execution` and retrieve logs only when needed.

This path is preferable to guessing Python imports for Console-only workflows.
See `references/latch-mcp.md`.

## Discover Through the Console

Use the Workflows page:

```text
https://console.latch.bio/workflows
```

The workflow's current parameter page is authoritative for that published
version. Record:

- Workflow ID and version
- Input and output schema
- Default resources
- Required reference data
- Scientific method and citations
- Expected cost and runtime

Do not infer scientific suitability from the "Verified" label alone. Confirm
reference genome, assay assumptions, tool versions, and validation needs.

## Referencing a Workspace Workflow

For a workflow in the active workspace, `workflow_reference` wraps Flyte's
reference launch plan:

```python
from latch import workflow, workflow_reference
from latch.types import LatchFile


@workflow_reference(
    name="wf.entrypoint.existing_workflow",
    version="1.2.3-abcd12",
)
def existing(input_file: LatchFile) -> LatchFile:
    ...


@workflow
def composed_workflow(input_file: LatchFile) -> LatchFile:
    return existing(input_file=input_file)
```

The decorated reference still needs an exact typed function signature. Prefer
generated or source-backed signatures; do not invent one from a display form.

`workflow_reference` resolves `current_workspace()` when the decorator is
evaluated. Importing this module therefore requires valid Latch authentication
and network access and will fail in a fully offline test environment. Verify the
active workspace before import/registration and isolate this coupling in a
small module.

## Version and Reproducibility Rules

- Pin the Latch SDK used to register the caller workflow.
- Record the referenced workflow ID/name and version.
- Re-run schema inspection after an SDK upgrade.
- Treat a changed wrapper signature or internal reference version as a behavior
  change.
- Use a small launch plan for integration testing.
- Preserve tool and database citations in downstream reports.

## Official Sources

- Workflow catalog overview: https://wiki.latch.bio/workflows/overview
- Ready-to-use workflow guides: https://wiki.latch.bio/llms.txt
- Verified exports in the 2.76.8 release commit: https://github.com/latchbio/latch/tree/0faa9dcd8186444ac008f50adf95d43f0fa30e06/src/latch/verified
- Latch MCP: https://wiki.latch.bio/agent/latch-mcp
- Latch Verified repositories: https://github.com/latch-verified
