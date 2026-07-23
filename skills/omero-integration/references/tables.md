# OMERO.tables

OMERO.tables stores columnar analysis data as an `OriginalFile` backed by an
HDF table. Treat table reads as data exports and table creation/update as
server writes.

## Compatibility and Scope

The current stable OMERO.tables definition is part of `omero-blitz` 5.8.5 in
the OMERO.server 5.6.18 documentation. OMERO.server 5.6.12 specifically
required OMERO.py 5.19.4 for the Tables service to start correctly, which
illustrates why client/server pairing matters.

Before using tables:

- confirm the server's tested OMERO.py version;
- confirm the Tables service is active;
- select one group and one table/attached object;
- cap columns and rows;
- plan handle closure even after read/query failure.

## Column Types

Current scalar columns:

- `FileColumn`, `ImageColumn`, `RoiColumn`, `WellColumn`, `PlateColumn`
- `BoolColumn`
- `LongColumn` (signed 64-bit)
- `DoubleColumn` (64-bit)
- `StringColumn(name, description, size, values)`

Current fixed-width array columns include:

- `FloatArrayColumn(name, description, size, values)`
- `DoubleArrayColumn(name, description, size, values)`
- `LongArrayColumn(name, description, size, values)`

The array `size` argument is required. Older examples that omit it are stale.
All columns added in one operation must contain the same number of rows.
Column names are unique; names beginning with double underscore are reserved.

The service performs limited validation of string and array lengths. Validate
every value against the initialized schema before writing.

## Read-Only Table Inspection

Start from one explicit `OriginalFile` ID, not a filename search:

```python
original_file_id = 123
max_rows = 100
max_columns = 20

original = conn.getObject("OriginalFile", original_file_id)
if original is None:
    raise LookupError("Table OriginalFile unavailable")

resources = conn.c.sf.sharedResources()
table = resources.openTable(original._obj)
try:
    headers = list(table.getHeaders())
    if len(headers) > max_columns:
        raise ValueError("Table has more columns than approved")

    row_count = table.getNumberOfRows()
    stop = min(row_count, max_rows)
    column_indices = list(range(len(headers)))
    data = table.read(column_indices, 0, stop)

    print(
        {
            "original_file_id": original_file_id,
            "total_rows": row_count,
            "returned_rows": stop,
            "truncated": row_count > stop,
            "columns": [column.name for column in headers],
        }
    )
finally:
    table.close()
```

`read(colNumbers, start, stop)` uses a stop-exclusive row range, except the
current docs note that `start=0, stop=0` returns the first row. Avoid that edge
case: do not call `read` when the approved row count is zero.

Other current read methods:

- `readCoordinates(rowNumbers)`: complete rows at explicit indices
- `slice(colNumbers, rowNumbers)`: selected columns and rows
- `getWhereList(condition, variables, start, stop, step)`: matching row
  indices, which can then be passed to `readCoordinates`

An empty column or row selection in `slice` may mean “all,” so never use empty
lists as a safety limit.

## Paged Read

Read consecutive chunks instead of every row:

```python
def iter_table_pages(table, column_indices, *, limit=1000, page_size=100):
    if not 1 <= limit <= 10_000:
        raise ValueError("limit out of range")
    if not 1 <= page_size <= min(limit, 500):
        raise ValueError("page_size out of range")

    total = min(table.getNumberOfRows(), limit)
    start = 0
    while start < total:
        stop = min(start + page_size, total)
        yield table.read(column_indices, start, stop)
        start = stop
```

Do not accumulate all pages unless the total cap and memory cost were reviewed.
Large string/array columns can make a small row count expensive.

## Fixed Queries and Bound Variables

OMERO.tables uses PyTables condition syntax. Keep the condition code fixed and
bind user values:

```python
from omero.rtypes import rint

row_count = table.getNumberOfRows()
max_rows_considered = min(row_count, 1000)
matches = table.getWhereList(
    condition="(Image > minimum_id)",
    variables={"minimum_id": rint(100)},
    start=0,
    stop=max_rows_considered,
    step=0,
)
matches = list(matches[:100])
data = table.readCoordinates(matches)
```

Never concatenate user text into a condition. Validate column names against
`getHeaders()` and map requested operations to a fixed allowlist.

The documented condition language includes logical, comparison, arithmetic,
and selected mathematical operations. Treat it as a query language, not as
arbitrary Python. Do not use Python `eval()` or `exec()` around it.

## Creating a Table

Creation is a write. Use a unique, caller-reviewed name and one selected
repository:

```python
from omero.grid import DoubleColumn, ImageColumn, StringColumn

columns = [
    ImageColumn("Image", "Source image", []),
    DoubleColumn("MeanIntensity", "Mean raw value", []),
    StringColumn("Status", "Review status", 32, []),
]

resources = conn.c.sf.sharedResources()
repositories = resources.repositories().descriptions
if not repositories:
    raise RuntimeError("No table repository is available")

repository_id = repositories[0].getId().getValue()
table = resources.newTable(repository_id, "analysis-v2-explicit-name")
try:
    table.initialize(columns)
    table.addData(
        [
            ImageColumn("Image", "Source image", [101, 102]),
            DoubleColumn("MeanIntensity", "Mean raw value", [12.5, 14.0]),
            StringColumn("Status", "Review status", 32, ["reviewed", "reviewed"]),
        ]
    )
    table_file_id = table.getOriginalFile().getId().getValue()
finally:
    table.close()
```

Before execution:

- verify repository selection with the administrator;
- validate every referenced object ID in the same intended group;
- validate all row counts, numeric ranges, strings, and array sizes;
- cap rows per `addData` batch;
- decide recovery if initialization succeeds but data upload fails.

## Linking a Table

The table `OriginalFile` becomes discoverable through a `FileAnnotation` and an
object-annotation link:

```python
from omero.model import (
    DatasetAnnotationLinkI,
    DatasetI,
    FileAnnotationI,
    OriginalFileI,
)

file_annotation = FileAnnotationI()
file_annotation.setFile(OriginalFileI(table_file_id, False))
file_annotation = conn.getUpdateService().saveAndReturnObject(file_annotation)

link = DatasetAnnotationLinkI()
link.setParent(DatasetI(dataset_id, False))
link.setChild(FileAnnotationI(file_annotation.getId().getValue(), False))
conn.getUpdateService().saveAndReturnObject(link)
```

This is a second write after table creation. If link creation fails, the table
and file annotation may remain orphaned. Record IDs after every successful
step and define cleanup before starting.

OMERO.web table viewing expects conventions such as a column named `Image`
with a supported ID/numeric column type. A custom column called something else
may store valid data but not receive the same UI behavior.

## Concurrency and Lifecycle

Each OMERO table is backed by one HDF table. PyTables/HDF does not support
general concurrent access, so OMERO.tables adds global locking. Keep table
handles short-lived:

```python
table = resources.openTable(original._obj)
try:
    # One bounded operation.
    ...
finally:
    table.close()
```

Do not hold a handle across:

- user interaction;
- network retries/reconnection;
- long pixel analysis;
- another process's expected write window.

If BlitzGateway reconnects, discard any old table proxy and open a fresh one.

## Updating or Deleting

`addData()` and `update()` mutate table content. Deleting the backing
`OriginalFile` may remove the table; deleting one annotation link may merely
detach it from one object. These require separate impact review.

Never:

- update rows selected by a dynamically constructed condition;
- append an unbounded result set;
- delete a table based only on filename;
- overwrite an existing table as a retry strategy;
- leave a handle open after an exception.

## Table Checklist

- Explicit `OriginalFile` ID and selected group
- Server/client pairing verified
- Column count, row limit, page size, string size, and array width bounded
- Fixed conditions with bound variables
- No empty selection that means “all”
- Handle closed in `finally`
- Writes and links reviewed separately
- Partial-create IDs recorded for recovery
- Export classification reviewed before JSON/CSV output
