# Latch Registry SDK

The current Registry API is object- and transaction-based. Older examples that
call `Project.create`, `Table.create`, `Record.create`, `Record.list`,
`record.update`, or `record.delete` do not match the current SDK.

This reference targets `latch==2.76.8`.

## Object Model

```text
Account (workspace)
└── Project
    └── Table
        └── Record
```

Current classes:

```python
from latch.account import Account
from latch.registry.project import Project
from latch.registry.record import Record
from latch.registry.table import Table
```

Objects are identified by numeric-string IDs. Display names are not globally
unique and must not be used as stable identifiers.

## Read Projects and Tables

```python
from latch.account import Account

account = Account.current()

for project in account.list_registry_projects():
    print(project.id, project.get_display_name())

    for table in project.list_tables():
        print("  ", table.id, table.get_display_name())
```

Most getters lazily call `load()` and cache the result. Use `load()` explicitly
when another process may have changed an object and fresh state is required.

Permissions are evaluated in the active CLI workspace or the workspace running
the task.

## Read Records

`Table.list_records()` is paginated and yields dictionaries keyed by record ID:

```python
from latch.registry.table import Table

table = Table(id="12345")

for page in table.list_records(page_size=100):
    for record_id, record in page.items():
        print(
            record_id,
            record.get_name(),
            record.get_values(),
            record.get_creation_time(),
            record.get_last_updated(),
        )
```

Record names are unique only within their table. Use `record.id` when a global
identifier is required.

To load one known record:

```python
from latch.registry.record import Record

record = Record(id="67890")
values = record.get_values()
table_id = record.get_table_id()
```

## DataFrames

`Table.get_dataframe()` requires the pandas extra:

```bash
uv pip install "latch[pandas]==2.76.8"
```

```python
frame = Table(id="12345").get_dataframe()
```

Use `list_records()` when streaming or dependency minimization matters.

## Transactional Updates

Updates are queued in a context manager and committed atomically when the
context exits successfully.

### Create a project

```python
from latch.account import Account

account = Account.current()
with account.update() as update:
    update.upsert_registry_project("RNA-seq Studies")
```

Despite the method name, creating projects and tables is not idempotent: two
calls with the same display name create two objects.

### Create a table

```python
from latch.registry.project import Project

project = Project(id="123")
with project.update() as update:
    update.upsert_table("Samples")
```

### Add columns and records

```python
from latch.registry.table import Table
from latch.types import LatchFile

table = Table(id="456")

with table.update() as update:
    update.upsert_column("condition", str, required=True)
    update.upsert_column("replicate", int)
    update.upsert_column("reads", LatchFile)

with table.update() as update:
    update.upsert_record(
        "sample-001",
        condition="treated",
        replicate=1,
        reads=LatchFile("latch:///inputs/sample-001.fastq.gz"),
    )
```

`upsert_record` takes the record name followed by column values as keyword
arguments. Unknown columns raise an error.

Supported column types include strings, integers, floats, dates, datetimes,
Booleans, `LatchFile`, `LatchDir`, enums, linked records, and selected list
forms. Check `TableUpdate.upsert_column` in the installed SDK before using a
less common nested type.

`TableUpdate.upsert_record` accepts `LPath` values in SDK 2.67.22 and later:

```python
from latch.ldata.path import LPath

with table.update() as update:
    update.upsert_record(
        "sample-002",
        reads=LPath("latch:///inputs/sample-002.fastq.gz"),
    )
```

### Delete

Deletion is queued through the corresponding updater:

```python
with table.update() as update:
    update.delete_record("sample-001")

with project.update() as update:
    update.delete_table("456")

with account.update() as update:
    update.delete_registry_project("123")
```

Record deletion takes a record **name**. Table and project deletion take IDs.
Confirm destructive operations and the active workspace first.

## Registry Samplesheets in Workflow Forms

`SamplesheetItem` preserves the source Registry record when a user imports rows
into a workflow form.

```python
from dataclasses import dataclass

from latch import small_task, workflow
from latch.registry.table import Table
from latch.types import LatchFile
from latch.types.metadata import (
    LatchAuthor,
    LatchMetadata,
    LatchParameter,
)
from latch.types.samplesheet_item import SamplesheetItem


@dataclass
class SampleRow:
    sample_name: str
    reads: LatchFile
    qc_status: str


metadata = LatchMetadata(
    display_name="Registry-aware QC",
    author=LatchAuthor(name="Workflow Team"),
    parameters={
        "samples": LatchParameter(
            display_name="Samples",
            samplesheet=True,
        )
    },
)


@small_task
def process_samples(samples: list[SamplesheetItem[SampleRow]]) -> int:
    updated = 0

    for item in samples:
        if item.record is None:
            continue

        table = Table(id=item.record.get_table_id())
        with table.update() as update:
            update.upsert_record(
                item.record.get_name(),
                qc_status="complete",
            )
        updated += 1

    return updated


@workflow(metadata)
def registry_qc(samples: list[SamplesheetItem[SampleRow]]) -> int:
    return process_samples(samples=samples)
```

Important behavior:

- `item.data` is the typed dataclass value.
- `item.record` is a `Record` when imported from Registry.
- `item.record` is `None` for a manually entered row.
- Dataclass fields should match Registry column keys where possible.
- The target table must already contain columns written by the task.
- Restrict selectable tables with `LatchParameter.allowed_tables` when the
  workflow should not accept arbitrary Registry schemas.

## Consistency and Error Handling

- Call `load()` again after out-of-band changes.
- Treat `NotFoundError` variants as either absent objects or missing permission.
- Do not infer IDs by choosing the first matching display name.
- Keep transactions focused; a failure prevents the context's commit.
- Avoid one transaction per row when a single updater can batch many changes.
- Validate all paths and types before queuing a large update.
- Record provenance fields rather than overwriting source metadata.

## Official Sources

- Registry SDK overview: https://wiki.latch.bio/registry/sdk/latch-sdk-registry-integration
- Account objects: https://wiki.latch.bio/registry/sdk/account-objects
- Project objects: https://wiki.latch.bio/registry/sdk/registry-projects
- Table objects: https://wiki.latch.bio/registry/sdk/table-objects
- Record objects: https://wiki.latch.bio/registry/sdk/record-objects
- Workflow Registry tutorial: https://wiki.latch.bio/workflows/sdk/api/registry-usage-tutorial
- Registry source in the 2.76.8 release commit: https://github.com/latchbio/latch/tree/0faa9dcd8186444ac008f50adf95d43f0fa30e06/src/latch/registry
