# Latch Data and Remote Paths

This reference distinguishes the two supported Python data models:

- `LPath` is the modern, `pathlib`-like API for explicit remote operations.
- `LatchFile` and `LatchDir` are the established workflow parameter types for
  automatic task staging and output upload.

Do not assume methods from one model exist on the other. In particular,
`LatchDir.glob()` is not a current SDK API.

## Choosing an API

Use `LPath` when you need to:

- Inspect, upload, download, copy, list, or delete a remote path explicitly
- Work from scripts, Pods, Plots, or task code
- Avoid automatic transfer of an entire directory
- Store an `LPath` value in Registry with SDK 2.67.22+

Use `LatchFile` or `LatchDir` when you need to:

- Expose a file or directory in a workflow form
- Automatically stage an input onto a task machine
- Automatically upload a returned task output
- Compose with older workflows or `latch.verified` wrappers

It is normal to accept a `LatchFile` in a workflow and construct an `LPath`
from its `remote_path` for a targeted remote operation.

## Latch URLs

Common forms include:

```text
latch:///path/in/current-workspace
latch://12345.account/path/in/workspace
latch://shared/path/to/shared-data
latch://67890.node
```

- `latch:///...` resolves relative to the active or execution workspace.
- Account-qualified URLs avoid ambiguity across workspaces.
- Node URLs address a Latch Data object by immutable numeric ID.
- Shared URLs refer to data shared across accounts.

Do not concatenate URLs with filesystem utilities that discard the URL scheme.
`LPath` supports `/` for child paths.

## `LPath`

Import it from its actual module:

```python
from latch.ldata.path import LPath
```

### Metadata and listing

```python
from latch.ldata.path import LPath

root = LPath("latch:///welcome")

if root.exists():
    print(root.node_id())
    print(root.name())
    print(root.is_dir())
    print(root.size_recursive())

    for child in root.iterdir():
        print(child.path, child.content_type(), child.size())
```

`iterdir()` is shallow. It returns an iterator of child `LPath` objects and
does not recursively traverse nested directories.

Metadata is cached for the lifetime of the object after a lookup. Call
`fetch_metadata()` after an external rename or modification when fresh values
are required.

### Download

Always provide an explicit destination for durable files:

```python
from pathlib import Path

from latch.ldata.path import LPath

remote = LPath("latch:///inputs/design.csv")
local = remote.download(Path("work/design.csv"), cache=True)
print(local.read_text(encoding="utf-8"))
```

Without a destination, the SDK downloads beneath `~/.latch/lpath/` and
registers the temporary directory for cleanup when the process exits. Do not
rely on that path after process termination.

With `cache=True`, the SDK uses the remote version identifier and local extended
attributes where supported. Explicit paths plus caching are especially
important in long-lived Pods and Plots.

### Upload

The destination's parent must exist:

```python
from pathlib import Path

from latch.ldata.path import LPath

destination_dir = LPath("latch:///results/run-001")
destination_dir.mkdirp()

report = destination_dir / "report.txt"
report.upload_from(Path("report.txt"))
```

`upload_from` accepts either a local file or directory. Avoid concurrent writes
to the same destination.

### Remote copy and delete

```python
from latch.ldata.path import LPath

source = LPath("latch:///results/run-001/report.txt")
backup = LPath("latch:///archive/run-001/report.txt")
source.copy_to(backup)
```

Deletion is recursive and destructive:

```python
target = LPath("latch:///scratch/run-001")
target.rmr()
```

Before `rmr()`:

1. Print or otherwise surface the exact resolved path.
2. Confirm it is not a workspace root, shared production folder, or active
   workflow output.
3. Obtain user confirmation unless deletion was already explicit.

## `LatchFile` and `LatchDir`

These types carry both a local execution path and an optional remote path:

```python
from pathlib import Path

from latch import small_task
from latch.types import LatchFile


@small_task
def summarize(input_file: LatchFile) -> LatchFile:
    source = Path(input_file.local_path)
    output = Path("/root/summary.txt")
    output.write_text(
        f"name={source.name}\nbytes={source.stat().st_size}\n",
        encoding="utf-8",
    )
    return LatchFile(str(output), "latch:///results/summary.txt")
```

For a passed input:

- `local_path` is the staged path on the task machine.
- `remote_path` identifies its source in Latch Data or S3.

For a returned value:

- The first constructor argument is the local file or directory.
- The second argument is the remote destination.

Use `LatchOutputFile` and `LatchOutputDir` in workflow signatures for
destinations that may not exist yet:

```python
from latch.types import LatchOutputDir, LatchOutputFile
```

### Directory behavior

Returning a local `LatchDir` to an existing remote directory adds or updates
the returned children. It does not imply deletion of unrelated remote files.
Do not depend on this merge behavior as a synchronization or cleanup strategy.

`LatchDir.iterdir()` lists children of a remote directory. For globbing local
task outputs into remote `LatchFile` values, use `file_glob`:

```python
from latch import small_task
from latch.types import LatchFile, file_glob


@small_task
def collect_fastq_outputs() -> list[LatchFile]:
    # Run the scientific tool here; it must create outputs/*.fastq.gz.
    return file_glob("outputs/*.fastq.gz", "latch:///results/fastq/")
```

## Data CLI

Inspect help for the installed version before scripting a command:

```bash
latch --version
latch cp --help
latch sync --help
```

Common operations:

```bash
# List
latch ls latch:///inputs

# Upload or download
latch cp ./sample.fastq.gz latch:///inputs/sample.fastq.gz
latch cp latch:///results/report.html ./report.html

# Create parents
latch mkdirp latch:///results/run-001

# Synchronize a local tree to a remote directory
latch sync ./results latch:///results/run-001

# Recursive removal — confirm the target first
latch rmr latch:///scratch/run-001
```

Prefer `mkdirp` and `rmr`; the older `mkdir`, `rm`, `touch`, and `open` commands
were deprecated.

## Reliability and Security

- Never print signed download URLs or authentication headers.
- Avoid loading a whole remote directory when only one file is needed.
- Use unique run destinations to prevent concurrent output collisions.
- Validate local checksums or scientific file integrity when correctness
  depends on complete transfer.
- Treat mounted cloud paths according to the source bucket's access policy.
- Keep workspace IDs explicit in automation that can access several workspaces.
- Do not call data mutations at module import time.

## Official Sources

- Remote files (`LPath`): https://wiki.latch.bio/workflows/sdk/api/working-with-files
- Legacy file support: https://wiki.latch.bio/workflows/sdk/python/legacy-file-support
- Latch URLs: https://wiki.latch.bio/workflows/sdk/python/latch-urls
- Data CLI: https://wiki.latch.bio/data/data-command-line
- Data overview: https://wiki.latch.bio/data/overview
- `LPath` source in the 2.76.8 release commit: https://github.com/latchbio/latch/blob/0faa9dcd8186444ac008f50adf95d43f0fa30e06/src/latch/ldata/path.py
