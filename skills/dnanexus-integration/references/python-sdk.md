# Python SDK (`dxpy`)

## Baseline

This reference was verified against `dxpy==0.410.0` (released 2026-07-14).
PyPI declares Python 3.8 or newer. This repository recommends Python 3.11+.

For a project:

```bash
uv add "dxpy==0.410.0"
```

For an isolated script:

```bash
uv run --with "dxpy==0.410.0" "script.py"
```

Inspect the installed API without authenticating:

```bash
uv run --with "dxpy==0.410.0" \
  "skills/dnanexus-integration/scripts/inspect_dxpy.py" --strict
```

## Authentication

`dxpy` uses the same configuration sources as `dx`. Prefer `dx login` for
interactive work and named secret injection for automation.

Never print:

- `DX_SECURITY_CONTEXT`
- API token values
- `dxpy.SECURITY_CONTEXT`
- full process environments

See `authentication.md` for configuration precedence and safe diagnosis.

## Handler Model

Use handlers for objects and executions:

| Class | Purpose |
|---|---|
| `DXFile` | File object |
| `DXRecord` | Structured metadata record |
| `DXApplet` | Project-local executable |
| `DXApp` | Versioned app |
| `DXWorkflow` | Native workflow |
| `DXJob` | App/appet execution |
| `DXAnalysis` | Workflow execution |
| `DXProject` | Project/data container |

Create handlers from IDs:

```python
import dxpy

file_obj = dxpy.DXFile("file-xxxx", project="project-xxxx")
applet = dxpy.DXApplet("applet-xxxx", project="project-xxxx")
app = dxpy.DXApp("app-xxxx")
workflow = dxpy.DXWorkflow("workflow-xxxx", project="project-xxxx")
job = dxpy.DXJob("job-xxxx")
analysis = dxpy.DXAnalysis("analysis-xxxx")
project = dxpy.DXProject("project-xxxx")
```

For an ID or link whose class is not known:

```python
handler = dxpy.get_handler(id_or_link, project="project-xxxx")
```

`get_handler()` accepts a string ID or a mapping containing a DNAnexus link.

## Links

Create a data-object link:

```python
link = dxpy.dxlink("file-xxxx")
```

Include project context for a project-qualified link:

```python
link = dxpy.dxlink("file-xxxx", "project-xxxx")
```

Create a job-based output reference:

```python
output_reference = job.get_output_ref("aligned_bam")
```

Do not wrap a job output reference with `dxpy.dxlink()`. It is already a valid
reference.

## Describe

```python
import dxpy

description = dxpy.describe(
    "file-xxxx",
    fields={"name", "size", "state", "archivalState"},
)
```

Handler:

```python
description = dxpy.DXFile(
    "file-xxxx",
    project="project-xxxx",
).describe(
    fields={"name", "size", "state"}
)
```

Request only needed fields. Object descriptions can contain PHI or internal
metadata.

## Files

### Upload

Verified signature:

```text
upload_local_file(
    filename=None,
    file=None,
    media_type=None,
    keep_open=False,
    wait_on_close=False,
    use_existing_dxfile=None,
    show_progress=False,
    write_buffer_size=None,
    multithread=True,
    **kwargs
)
```

Example:

```python
remote_file = dxpy.upload_local_file(
    "results.vcf.gz",
    project="project-xxxx",
    folder="/results",
    properties={"sample_id": "S001"},
    tags=["validated"],
    wait_on_close=True,
)
```

Exactly one of `filename` or `file` is required. `wait_on_close=True` is useful
when the next operation requires a closed object.

### Download

```python
dxpy.download_dxfile(
    "file-xxxx",
    "results.vcf.gz",
    project="project-xxxx",
    show_progress=True,
)
```

`project` can affect which project/billing context is used for the download.

### Stream

```python
with dxpy.open_dxfile(
    "file-xxxx",
    project="project-xxxx",
) as remote_stream:
    prefix = remote_stream.read(4096)
```

`DXFile.open_file()` does not exist in dxpy 0.410.0. Use
`dxpy.open_dxfile()`.

### Upload a string

```python
report = dxpy.upload_string(
    '{"status":"ok"}\n',
    project="project-xxxx",
    folder="/reports",
    name="status.json",
    media_type="application/json",
    wait_on_close=True,
)
```

Do not use this for credentials or sensitive diagnostic dumps.

## Search

### Data objects

Verified signature includes:

```text
find_data_objects(
    classname=None,
    state=None,
    visibility=None,
    name=None,
    name_mode="exact",
    properties=None,
    typename=None,
    tags=None,
    project=None,
    folder=None,
    recurse=None,
    describe=False,
    limit=None,
    region=None,
    archival_state=None,
    return_handler=False,
    ...
)
```

Example:

```python
results = dxpy.find_data_objects(
    classname="file",
    project="project-xxxx",
    folder="/results",
    recurse=True,
    name="*.vcf.gz",
    name_mode="glob",
    state="closed",
    describe={
        "fields": {
            "name": True,
            "size": True,
            "archivalState": True,
        }
    },
    limit=200,
)

for result in results:
    description = result["describe"]
    print(result["id"], description["name"])
```

Important:

- Searches return generators.
- `name_mode` defaults to exact.
- `tags` means all specified tags.
- `tag` is deprecated.
- `describe=True` returns full default descriptions; a field mapping is safer.
- Omitted `limit` means dxpy keeps paging until all matching results are read.
- Scope broad searches by project/folder/time.

Timestamps accept:

- Epoch milliseconds
- Negative milliseconds relative to now
- Relative strings such as `"-2d"` or `"-1w"`

### Executions

```python
executions = dxpy.find_executions(
    project="project-xxxx",
    state="failed",
    created_after="-2d",
    include_subjobs=True,
    include_restarted=True,
    describe={"fields": {"name": True, "failureReason": True}},
    limit=100,
)
```

Use:

- `find_executions()` for jobs and analyses
- `find_jobs()` for jobs only
- `find_analyses()` for analyses only

`find_executions()` supports `classname="job"` or
`classname="analysis"`.

## Projects and Folders

```python
project = dxpy.DXProject("project-xxxx")

project.new_folder(
    "/analysis/run-001/results",
    parents=True,
)

contents = project.list_folder(
    "/analysis/run-001",
    describe={"fields": {"name": True, "state": True}},
)
```

Move exact IDs:

```python
project.move(
    "/analysis/run-001/final",
    objects=["file-xxxx", "record-yyyy"],
)
```

Clone:

```python
source = dxpy.DXFile("file-xxxx", project="project-source")
cloned = source.clone(
    project="project-destination",
    folder="/imports",
)
```

Delete only after explicit confirmation:

```python
project.remove_objects(["file-xxxx"], force=False)
```

Do not use `force=True` merely to hide a target-resolution error.

## Records

```python
record = dxpy.new_dxrecord(
    project="project-xxxx",
    folder="/metadata",
    name="run-001",
    types=["RunMetadata"],
    details={
        "pipeline": "rna-seq",
        "version": "2.4.1",
    },
    close=True,
)
```

For an open mutable record:

```python
record = dxpy.DXRecord("record-xxxx", project="project-xxxx")
details = record.get_details()
details["status"] = "done"
record.set_details(details)
record.close()
```

`set_details()` replaces the details mapping supplied to the call. Avoid
read-modify-write races on shared open records.

## Run Executables

App/appet runs return `DXJob`:

```python
job = dxpy.DXApplet(
    "applet-xxxx",
    project="project-xxxx",
).run(
    {"reads": dxpy.dxlink("file-xxxx")},
    project="project-xxxx",
    folder="/runs/run-001",
    name="S001 alignment",
    tags=["alignment"],
    properties={"sample_id": "S001"},
    priority="normal",
    cost_limit=25,
)
```

Workflow runs return `DXAnalysis`:

```python
analysis = dxpy.DXWorkflow(
    "workflow-xxxx",
    project="project-xxxx",
).run(
    {
        "0.reads": dxpy.dxlink(
            "file-xxxx",
            "project-xxxx",
        )
    },
    project="project-xxxx",
    folder="/runs/run-002",
    cost_limit=50,
)
```

Useful run arguments in dxpy 0.410.0 include:

- `project`, `folder`, `name`
- `tags`, `properties`, `details`
- `instance_type`, `stage_instance_types`
- `stage_folders`, `rerun_stages`
- `depends_on`
- `priority`, `head_job_on_demand`
- `ignore_reuse`, `ignore_reuse_stages`
- `cost_limit`
- `max_tree_spot_wait_time`, `max_job_spot_wait_time`
- `preserve_job_outputs`
- `detailed_job_metrics`
- `system_requirements`

Billable runs and reuse changes need explicit review.

## Wait and Output

```python
from dxpy.exceptions import DXError, DXJobFailureError

try:
    job.wait_on_done(interval=5, timeout=3600)
except DXJobFailureError:
    failure = job.describe(
        fields={
            "state": True,
            "failureReason": True,
            "failureMessage": True,
        }
    )
    raise RuntimeError(
        f"{failure.get('failureReason')}: "
        f"{failure.get('failureMessage')}"
    ) from None
except DXError as error:
    raise RuntimeError(f"wait failed: {error}") from error

outputs = job.describe(fields={"output": True})["output"]
```

Defaults for `DXJob.wait_on_done()` and `DXAnalysis.wait_on_done()` are a
two-second poll interval and a seven-day timeout. Set an explicit timeout that
matches the caller's needs.

To chain jobs, avoid waiting:

```python
downstream = dxpy.DXApplet("applet-next").run(
    {"input": job.get_output_ref("result")},
    project="project-xxxx",
)
```

## Exceptions

Current public dxpy exception classes include:

- `DXError`: base SDK error
- `DXAPIError`: non-200 API response
- `DXJobFailureError`: job/analysis wait detected failure
- `DXSearchError`: invalid or failed search
- `DXFileError`: file operation failure
- `DXChecksumMismatchError`: transfer integrity failure

API error names such as `ResourceNotFound`, `PermissionDenied`, and
`InvalidInput` are usually represented by `DXAPIError.name`; they are not
top-level dxpy exception classes in 0.410.0.

```python
from dxpy.exceptions import DXAPIError

try:
    description = dxpy.describe("file-xxxx")
except DXAPIError as error:
    print(f"DNAnexus API error: {error.name} (HTTP {error.code})")
    raise
```

Do not dump `error.details` blindly; it can contain sensitive object metadata.

## Low-Level API Bindings

Generated wrappers are available under `dxpy.api`, for example:

```python
response = dxpy.api.system_find_data_objects(
    {
        "class": "file",
        "scope": {
            "project": "project-xxxx",
            "folder": "/results",
            "recurse": True,
        },
        "name": {"glob": "*.bam"},
        "limit": 100,
    }
)
```

Prefer high-level search/handler methods unless a required field is unavailable
there. Low-level methods expose API pagination, request shapes, and destructive
options directly.

Never construct arbitrary API method names, hosts, or request bodies from
untrusted input.

## Reliability Checklist

- Pin the tested dxpy version.
- Pass explicit project/folder context.
- Bound searches and polling.
- Use links and output references, not hand-built mappings.
- Wait for file closure when required.
- Catch specific SDK exceptions.
- Retry only documented transient failures with backoff.
- Preserve request IDs from API errors for support, but redact object metadata.
- Never log credentials or whole environments.
- Require confirmation for billable/destructive operations.
- Test SDK assumptions with `scripts/inspect_dxpy.py` after upgrades.
