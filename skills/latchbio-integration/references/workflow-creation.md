# Python Workflow Creation

This reference targets `latch==2.76.8`. Check the installed SDK with
`scripts/inspect_latch_sdk.py` before using version-sensitive symbols.

## Mental Model

- A function decorated with `@workflow` defines a graph.
- A function decorated with a task decorator runs in its own containerized task.
- Calling a task inside a workflow creates a node; it does not execute ordinary
  Python at graph-construction time.
- Workflow inputs and outputs must be typed.
- Put file I/O, subprocesses, network calls, secret lookup, and scientific
  computation inside tasks.
- Keep module import time deterministic and free of external side effects.

## Initialize a Project

```bash
latch init my-workflow --template subprocess
```

Current template choices are exposed by `latch init --help`; common choices
include `subprocess`, `conda`, `r`, and `empty`. A project commonly contains a
`wf/` Python package, a `version` file, dependency inputs, and optional
`Dockerfile` and metadata files.

Do not assume a hand-written Dockerfile is required. Registration can generate
one. If a Dockerfile is present at the project root, registration uses it.

## Tasks and Workflows

```python
from latch import small_task, workflow


@small_task
def normalize_name(sample_name: str) -> str:
    return sample_name.strip().replace(" ", "_")


@workflow
def normalize_sample(sample_name: str) -> str:
    """Normalize a sample identifier."""
    return normalize_name(sample_name=sample_name)
```

Use keyword arguments for task calls. They make graph wiring explicit and
survive parameter reordering.

### File input and output

`LatchFile` and `LatchDir` remain the most established workflow signature types.
Inputs are staged onto the task machine. Returned values pair a local path with
a remote destination.

```python
from pathlib import Path

from latch import small_task, workflow
from latch.types import LatchFile, LatchOutputDir


@small_task
def count_lines(input_file: LatchFile, output_dir: LatchOutputDir) -> LatchFile:
    source = Path(input_file.local_path)
    destination = Path("/root/line-count.txt")

    with source.open("r", encoding="utf-8") as handle:
        count = sum(1 for _ in handle)
    destination.write_text(f"{count}\n", encoding="utf-8")

    remote_dir = output_dir.remote_path
    if remote_dir is None:
        raise ValueError("output_dir must have a remote Latch path")

    return LatchFile(
        str(destination),
        f"{remote_dir.rstrip('/')}/line-count.txt",
    )


@workflow
def line_count_workflow(
    input_file: LatchFile,
    output_dir: LatchOutputDir,
) -> LatchFile:
    return count_lines(input_file=input_file, output_dir=output_dir)
```

For new imperative remote-path operations, prefer `LPath`; see
`references/data-management.md`. Do not silently replace typed workflow
parameters with plain strings merely to avoid learning the file types.

## Custom Workflow Metadata

Without metadata, the SDK derives a basic interface from the workflow
signature. Add `LatchMetadata` when the form needs deliberate design.

```python
from pathlib import Path

from latch import small_task, workflow
from latch.types import LatchFile
from latch.types.metadata import (
    LatchAuthor,
    LatchMetadata,
    LatchParameter,
    LatchRule,
)


@small_task
def validate_task(reads: LatchFile) -> bool:
    return Path(reads.local_path).stat().st_size > 0


metadata = LatchMetadata(
    display_name="FASTQ Validator",
    author=LatchAuthor(name="Workflow Team"),
    license="MIT",
    repository="https://github.com/example/fastq-validator",
    parameters={
        "reads": LatchParameter(
            display_name="Reads",
            description="Input FASTQ or compressed FASTQ file.",
            rules=[
                LatchRule(
                    regex=r".*\.(fastq|fq)(\.gz)?$",
                    message="Choose a .fastq, .fq, .fastq.gz, or .fq.gz file.",
                )
            ],
        )
    },
)


@workflow(metadata)
def validate_fastq(reads: LatchFile) -> bool:
    return validate_task(reads=reads)
```

Metadata keys must match workflow parameter names. The SDK rejects metadata
keys absent from the function signature.

Although `about_page_path` is documented, SDK 2.76.8 can fail while serializing
its `Path` value. Use `documentation=` and a descriptive workflow docstring
until that defect is fixed.

See `references/ui-and-automation.md` for sections, samplesheets, launch plans,
messages, and result links.

## Parallel Mapping

Use `map_task` when one task should run over a list. Mapping produces a single
map node rather than thousands of graph nodes.

```python
from pathlib import Path

from latch import map_task, small_task, workflow
from latch.types import LatchFile


@small_task
def validate_one(reads: LatchFile) -> bool:
    return Path(reads.local_path).stat().st_size > 0


@workflow
def validate_batch(reads: list[LatchFile]) -> list[bool]:
    return map_task(validate_one)(reads=reads)
```

Map task inputs must line up with the mapped function's parameter names.
Resource overrides are Flyte overrides and should be tested against the
installed SDK.

## Conditional Nodes

Ordinary Python `if` statements cannot branch on task promises. Build a
conditional node:

```python
from latch import create_conditional_section, small_task, workflow


@small_task
def double(value: float) -> float:
    return value * 2


@small_task
def square(value: float) -> float:
    return value**2


@workflow
def transform(value: float) -> float:
    doubled = double(value=value)
    return (
        create_conditional_section("choose-transform")
        .if_(doubled < 0.0)
        .then(double(value=doubled))
        .elif_(doubled > 0.0)
        .then(square(value=doubled))
        .else_()
        .fail("Zero is not accepted")
    )
```

Use `&` and `|` for compound promise expressions. For a task-produced Boolean,
use its promise truth checks rather than Python unary `not`.

## Caching, Retries, and Timeouts

Named task decorators forward Flyte task options:

```python
from datetime import timedelta

from latch import medium_task


@medium_task(
    cache=True,
    cache_version="reference-index-v2",
    retries=2,
    timeout=timedelta(hours=2),
)
def build_index(reference: LatchFile) -> LatchFile:
    ...
```

- Change `cache_version` whenever output-affecting logic or dependencies change.
- Cache only deterministic tasks.
- Retries should cover transient failures, not malformed inputs.
- Set a timeout with scientific runtime variance in mind.
- See `references/resource-configuration.md` before selecting a larger instance.

## Task-Specific Dockerfiles

Since SDK 2.57.0, a task decorator's `dockerfile` argument must be a string
literal so registration can discover it through static AST inspection:

```python
@small_task(dockerfile="Dockerfile.validation")
def validate_with_custom_image(reads: LatchFile) -> bool:
    ...
```

Do not pass a `Path`, variable, function call, or computed expression to this
argument.

## Workflow Design Checklist

- Every input and output has a concrete type.
- Workflow bodies only compose task, map, conditional, and reference nodes.
- Tasks return actual values rather than undefined placeholder variables.
- Output destinations do not collide across concurrent runs.
- Subprocess calls use argument lists and `check=True`.
- Dependencies and tool versions are pinned for releases.
- Metadata keys match the workflow signature.
- Cache versions reflect code and dependency changes.
- The image has been tested with staging registration and `latch develop`.

## Official Sources

- Python SDK overview: https://wiki.latch.bio/workflows/sdk/python/overview
- Quick start: https://wiki.latch.bio/workflows/sdk/python/quick-start
- Conditional sections: https://wiki.latch.bio/workflows/sdk/python/conditional-sections
- Map tasks: https://wiki.latch.bio/workflows/sdk/python/map-task
- Caching: https://wiki.latch.bio/workflows/sdk/python/caching
- Workflow environment: https://wiki.latch.bio/workflows/sdk/python/workflow-environment/overview
- SDK source at the 2.76.8 release commit: https://github.com/latchbio/latch/tree/0faa9dcd8186444ac008f50adf95d43f0fa30e06
