# Workflow UI, Launch Plans, Messages, Results, and Automations

The workflow signature defines types. `LatchMetadata` defines how users
understand and enter those values. Treat interface design as part of workflow
correctness.

## Metadata

```python
from latch.types.metadata import (
    LatchAuthor,
    LatchMetadata,
    LatchParameter,
    LatchRule,
    Params,
    Section,
    Spoiler,
    Text,
)

metadata = LatchMetadata(
    display_name="Bulk RNA-seq QC",
    author=LatchAuthor(
        name="Workflow Team",
        github="https://github.com/example",
    ),
    documentation="https://example.org/docs/rnaseq-qc",
    repository="https://github.com/example/rnaseq-qc",
    license="MIT",
    tags=["RNA-seq", "QC"],
    parameters={
        "reads": LatchParameter(
            display_name="Reads",
            description="FASTQ input files.",
            samplesheet=True,
        ),
        "minimum_quality": LatchParameter(
            display_name="Minimum quality",
            description="Minimum accepted Phred score.",
            rules=[
                LatchRule(
                    regex=r"^(?:[0-9]|[1-3][0-9]|40)$",
                    message="Choose an integer from 0 through 40.",
                )
            ],
        ),
        "output_directory": LatchParameter(
            display_name="Output directory",
            description="Destination for reports and processed outputs.",
            output=True,
        ),
    },
    flow=[
        Section(
            "Inputs",
            Text("Select samples and input reads."),
            Params("reads"),
        ),
        Spoiler(
            "Advanced quality settings",
            Params("minimum_quality"),
        ),
        Section(
            "Outputs",
            Params("output_directory"),
        ),
    ],
)
```

Apply it:

```python
from dataclasses import dataclass
from pathlib import Path

from latch import small_task, workflow
from latch.types import LatchDir, LatchFile, LatchOutputDir


@dataclass
class SampleRow:
    sample_name: str
    reads: LatchFile


@small_task
def run_qc(
    reads: list[SampleRow],
    output_directory: LatchOutputDir,
    minimum_quality: int,
) -> LatchDir:
    local_output = Path("/root/rnaseq-qc")
    local_output.mkdir(parents=True, exist_ok=True)
    (local_output / "summary.txt").write_text(
        f"samples={len(reads)}\nminimum_quality={minimum_quality}\n",
        encoding="utf-8",
    )

    remote = output_directory.remote_path
    if remote is None:
        raise ValueError("output_directory must have a remote path")
    return LatchDir(str(local_output), remote)


@workflow(metadata)
def rnaseq_qc(
    reads: list[SampleRow],
    output_directory: LatchOutputDir,
    minimum_quality: int = 20,
) -> LatchDir:
    return run_qc(
        reads=reads,
        output_directory=output_directory,
        minimum_quality=minimum_quality,
    )
```

Metadata parameter keys must match the signature. The SDK adds default metadata
for signature parameters omitted from the metadata object.

Although `about_page_path` is documented, SDK 2.76.8 can fail while serializing
its `Path` value. Prefer `documentation=` and a descriptive workflow docstring
until that defect is fixed.

## Flow Elements

Current flow classes include:

- `Section(title, *children)`
- `Text(markdown)`
- `Title(markdown_title)`
- `Params(*parameter_names)`
- `Spoiler(title, *children)`
- `Fork(parameter_name, display_name, **branches)`
- `ForkBranch(display_name, *children)`

`flow` replaces the default top-to-bottom layout. Include every visible
parameter intentionally.

Use a `Fork` only with a matching string parameter in the workflow signature:

```python
from latch.types.metadata import Fork, ForkBranch, Params

read_type_flow = Fork(
    "read_type",
    "Read layout",
    paired=ForkBranch("Paired-end", Params("read1", "read2")),
    single=ForkBranch("Single-end", Params("read1")),
)
```

## Parameter Guidance

Use:

- `display_name` and `description` for scientific meaning
- `rules` for syntactic validation
- `hidden` for rarely changed values, not security
- `batch_table_column` for high-value bulk-run fields
- `samplesheet=True` for dataclass-backed tabular inputs
- `allowed_tables` to restrict Registry imports
- `output=True` or `LatchOutputFile` / `LatchOutputDir` for new destinations

Do not use form defaults to hide scientific assumptions. State reference
genome, strandedness, units, and algorithm defaults explicitly.

## Launch Plans

`LaunchPlan` creates a named set of defaults shown under Test Data in the
Console:

```python
from latch.resources.launch_plan import LaunchPlan
from latch.types import LatchFile, LatchOutputDir

LaunchPlan(
    rnaseq_qc,
    "Small public example",
    {
        "reads": [
            SampleRow(
                sample_name="example",
                reads=LatchFile("latch:///test-data/example.fastq.gz"),
            )
        ],
        "minimum_quality": 20,
        "output_directory": LatchOutputDir(
            "latch:///test-results/rnaseq-qc"
        ),
    },
    description="Small input for interface and integration testing.",
)
```

Constructor:

```python
LaunchPlan(
    workflow,
    name,
    default_params,
    *,
    description=None,
)
```

Rules:

- Define launch plans at module scope so registration discovers them.
- Parameter keys and values must match the workflow.
- A launch plan name cannot contain `.`.
- Use small public or workspace-safe test data.
- Avoid destinations shared by concurrent users.
- Never put secret values in a launch plan.

## Execution Messages

Use messages for concise user-facing signals, not raw logs:

```python
from latch import message, small_task


@small_task
def validate_columns(columns: list[str]) -> bool:
    required = {"sample_id", "condition"}
    missing = sorted(required.difference(columns))

    if missing:
        message(
            typ="error",
            data={
                "title": "Missing required columns",
                "body": ", ".join(missing),
            },
        )
        raise ValueError(f"missing columns: {missing}")

    message(
        typ="info",
        data={
            "title": "Input validated",
            "body": "Required sample columns are present.",
        },
    )
    return True
```

Valid message types are `info`, `warning`, and `error`. The data dictionary
requires `title` and `body`.

Do not put secrets, signed URLs, patient identifiers, or excessive raw data in
messages.

## Results Page

Publish the most useful result locations:

```python
from latch import small_task
from latch.executions import add_execution_results
from latch.types import LatchOutputDir


@small_task
def publish_results(output_directory: LatchOutputDir) -> None:
    remote = output_directory.remote_path
    if remote is None:
        raise ValueError("output directory must have a remote path")

    add_execution_results(
        [
            remote,
            f"{remote.rstrip('/')}/multiqc_report.html",
        ]
    )
```

For Nextflow parameters, `NextflowParameter.results_paths` can publish selected
subpaths under an output directory.

Result links improve discoverability; they do not upload missing outputs or
verify scientific validity.

## Automations

Automations are configured in the Console and can trigger from:

- A child added at any depth beneath a watched Latch Data directory
- A recurring time interval

### Data-added workflow contract

The automation workflow must have exactly one parameter:

```python
from latch import small_task, workflow
from latch.types import LatchDir


@small_task
def process_new_data(input_directory: LatchDir) -> None:
    children = list(input_directory.iterdir())
    print(f"observed {len(children)} children")


@workflow
def automation_workflow(input_directory: LatchDir) -> None:
    process_new_data(input_directory=input_directory)
```

The trigger fires after the configured follow-up update period following the
last addition. Modification or deletion alone does not trigger it.

### Interval workflow contract

The workflow must have no parameters:

```python
from latch import small_task, workflow


@small_task
def run_scheduled_check() -> None:
    print("scheduled check started")


@workflow
def scheduled_workflow() -> None:
    run_scheduled_check()
```

### Automation safety

- Automations can create recurring paid compute. Review frequency, map width,
  and worst-case cost before activation.
- Make processing idempotent. A Registry record or durable marker can prevent
  duplicate work.
- Do not hard-code secrets. Retrieve them inside tasks with `get_secret()`.
- Test the workflow manually before enabling the trigger.
- Start with a long enough debounce/update period to avoid launch storms.
- Disable the automation while changing its workflow contract.
- Ensure the watched directory does not include the automation's own outputs.

## Official Sources

- UI definition: https://wiki.latch.bio/workflows/sdk/ui/latch-metadata
- Launch plans: https://wiki.latch.bio/workflows/sdk/ui/launch-plans
- Messages: https://wiki.latch.bio/workflows/sdk/ui/messages
- Results: https://wiki.latch.bio/workflows/sdk/ui/results
- Automation overview: https://wiki.latch.bio/workflows/sdk/automation/overview
- Data-added trigger: https://wiki.latch.bio/workflows/sdk/automation/example-data-addition
- Interval trigger: https://wiki.latch.bio/workflows/sdk/automation/example-interval
