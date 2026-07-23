# Data Operations

## Safety Model

DNAnexus data objects live in projects or other data containers. Before a
mutation:

1. Resolve the project to a `project-...` ID.
2. Resolve every path to an object ID.
3. Detect duplicate names.
4. Inspect state, archival state, size, and relevant metadata.
5. Confirm source/destination permissions and restrictions.
6. Show exact IDs and impact for deletion, cloning, archival, or egress.

Names and paths are convenient for humans but are not immutable identifiers.
Use IDs in automation.

## Object Lifecycle

Files use:

```text
open → closing → closed
```

- `open`: parts/content can still be uploaded.
- `closing`: finalization is in progress; content cannot be read or written.
- `closed`: content is immutable and available to download/share.

Files must be closed before they can be read or cloned. They may be submitted
as job inputs while open or closing, but the job remains `waiting_on_input`
until closure. Open/closing files inactive for about 24 hours are considered
abandoned and are later deleted by the platform.

When a data object closes, content plus types, details/links, and visibility
become fixed. User-editable metadata such as name, properties, and tags can
still be managed according to permissions.

Records may intentionally remain open when mutable structured details are
required. Document this exception because open records weaken reproducibility.

## Transfer Tool Selection

| Workload | Tool |
|---|---|
| One or a few small files | `dx upload`, `dx download` |
| Multiple files or a file larger than 50 MB | Upload Agent (`ua`) |
| Many/large/long-running downloads | Download Agent (`dx-download-agent`) |
| Custom Python automation | `dxpy` |

Use platform transfer agents when resumability and per-part integrity matter.

## Small Transfers with `dx`

Upload:

```bash
dx upload "sample.fastq.gz" \
  --path "project-xxxx:/raw/sample.fastq.gz" \
  --property "sample_id=S001" \
  --tag "raw"
```

Download:

```bash
dx download "project-xxxx:/results/sample.bam" \
  --output "sample.bam"
```

Use quoted full paths. If a name is non-unique, use the object ID.

For scripts, use `--brief` or machine-readable output where supported instead
of parsing human-formatted tables.

Current `dx` warns when a download or generated download URL targets a file
flagged as malicious. Stop on that warning unless the user approves a
containment procedure that prevents execution and protects the local system.

## Upload Agent

Upload Agent is resumable and uses parallel connections. Important behavior:

- Uncompressed files are compressed by default.
- `.gz` is appended to the remote name.
- Already compressed inputs are not recompressed.
- `--do-not-compress` preserves the original bytes/name behavior.
- Repeating the same command resumes a matching incomplete transfer.
- `--wait-on-close` blocks until uploaded file objects are closed.
- Per-part `Content-MD5` is verified by the platform.

Example:

```bash
ua \
  --project "project-xxxx" \
  --folder "/raw" \
  --wait-on-close \
  --progress \
  "sample.fastq.gz"
```

For an uncompressed file that must not be transformed:

```bash
ua \
  --project "project-xxxx" \
  --folder "/raw" \
  --do-not-compress \
  --wait-on-close \
  "reference.fa"
```

Do not run `ua --env` in captured output because it displays the active token.
`DX_API_TOKEN` and `DX_SECURITY_CONTEXT` are both secrets.

Download Agent checks `DX_API_TOKEN` and otherwise falls back to the saved
dx-toolkit configuration. `dx`, `dxpy`, and normal toolkit sessions use
`DX_SECURITY_CONTEXT`; do not assume one variable name works for every client.

Use `--do-not-resume` only when creating a deliberate second copy. Otherwise
let the agent resume interrupted uploads.

## Download Agent

Download Agent consumes a BZIP2-compressed JSON manifest. Use the manifest
creation utility from the official `dnanexus/dxda` release and review its
resolved file set before starting egress.

```bash
dx-download-agent download "manifest.json.bz2"
dx-download-agent progress "manifest.json.bz2"
dx-download-agent inspect "manifest.json.bz2"
```

`inspect` revalidates downloaded parts against manifest checksums. If a part is
missing or corrupt, rerun `download`.

Before a large download:

- Confirm local free space.
- Confirm data egress approval and cost.
- Confirm download restrictions/TRE policy.
- Check that all files are live and closed.
- Review the manifest for unexpected projects or PHI.
- Use a token that remains valid for the expected transfer duration.

Do not place an API token in a Docker command line or committed compose file.

## Python Upload and Download

```python
from pathlib import Path

import dxpy

project_id = "project-xxxx"

remote = dxpy.upload_local_file(
    "sample.fastq.gz",
    project=project_id,
    folder="/raw",
    properties={"sample_id": "S001"},
    tags=["raw"],
    wait_on_close=True,
    show_progress=True,
)

dxpy.download_dxfile(
    remote,
    str(Path("downloads") / "sample.fastq.gz"),
    project=project_id,
    show_progress=True,
)
```

`project` on download is also a billing/context hint. Pass it when the same file
has copies in multiple projects or the billing context matters.

Read a remote file as a stream:

```python
import dxpy

with dxpy.open_dxfile("file-xxxx", project="project-xxxx") as stream:
    first_chunk = stream.read(1024)
```

`DXFile.open_file()` is not a current dxpy method; use
`dxpy.open_dxfile()`.

## Search

### CLI

```bash
dx find data \
  --class file \
  --path "project-xxxx:/results" \
  --name "*.bam" \
  --name-mode glob
```

Use `dx find data --help` from the installed toolkit for current filter flags.

### dxpy

```python
import dxpy

results = dxpy.find_data_objects(
    classname="file",
    project="project-xxxx",
    folder="/results",
    recurse=True,
    name="*.bam",
    name_mode="glob",
    state="closed",
    archival_state="live",
    describe={
        "fields": {
            "name": True,
            "size": True,
            "created": True,
            "archivalState": True,
            "properties": True,
        }
    },
    limit=500,
)

for result in results:
    print(result["id"], result["describe"]["name"])
```

Critical semantics:

- Default `name_mode` is `"exact"`.
- Use `"glob"` for `*` and `?`.
- Use `"regexp"` only with a reviewed, bounded pattern.
- Results are generators and dxpy handles API pagination.
- Without `limit`, dxpy can traverse the full result set.
- `describe` adds API work and may expose metadata; request only needed fields.
- `archival_state` requires a file class plus project/folder scope.

The API defaults to pages of at most 1000. DNAnexus documents a 200 API
calls/second account limit; implement bounded concurrency and exponential
backoff rather than flooding the service.

## Metadata

Properties are string key/value pairs; tags are strings.

```python
import dxpy

file_obj = dxpy.DXFile("file-xxxx", project="project-xxxx")
file_obj.set_properties(
    {
        "sample_id": "S001",
        "pipeline_version": "2.4.1",
    }
)
file_obj.add_tags(["validated", "release-2026-07"])
file_obj.rename("S001.aligned.bam")
```

Avoid direct identifiers in tags/properties when projects contain PHI. Follow
the organization's approved metadata model.

Metadata updates affect discovery and provenance. Review overwrite semantics
before replacing a full property/detail mapping.

## Records

Create a closed immutable record:

```python
import dxpy

record = dxpy.new_dxrecord(
    project="project-xxxx",
    folder="/metadata",
    name="run-001",
    types=["RunMetadata"],
    details={
        "pipeline": "rna-seq",
        "pipeline_version": "2.4.1",
    },
    close=True,
)
```

Create an open record only when continued mutation is required:

```python
record = dxpy.new_dxrecord(
    project="project-xxxx",
    name="mutable-status",
    details={"state": "queued"},
    close=False,
)
record.set_details({"state": "running"})
record.close()
```

Closing fixes details and links. For append-only provenance, prefer creating a
new versioned record instead of mutating a shared open record.

## Folders

```python
import dxpy

project = dxpy.DXProject("project-xxxx")
project.new_folder("/analysis/run-001/results", parents=True)
listing = project.list_folder(
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

Never use a broad recursive operation until the folder listing and count have
been shown to the user.

## Cloning

```python
import dxpy

source = dxpy.DXFile("file-xxxx", project="project-source")
clone = source.clone(
    project="project-destination",
    folder="/imports",
)
print(clone.get_id())
```

Requirements and caveats:

- Source object must be closed.
- `VIEW` or higher is needed on the source.
- `UPLOAD` or higher is needed on the destination.
- Restricted projects/TREs can forbid cloning.
- Databases cannot be cloned.
- Hidden linked objects may be cloned with their visible parent.
- Archive transitions can block cloning.
- Cross-`billTo` cloning of archived data requires live objects.
- The clone is independent; removing the source does not remove the clone.

Use `dx cp` for project-to-project copies when folder structure is the primary
interface:

```bash
dx cp \
  "project-source:/results" \
  "project-destination:/imports"
```

Confirm source, destination, file count, and billing entity first.

## Archival

Archive and unarchive are billable/storage-affecting operations and may take
time:

```bash
dx archive "project-xxxx:/old-results/sample.bam"
dx unarchive "project-xxxx:/old-results/sample.bam"
```

Before archiving:

- Check whether active workflows, collaborators, or published outputs need it.
- Check all copies and billing behavior.
- Confirm the target is a file or intended folder.

Before unarchiving:

- Confirm retrieval cost and required completion time.
- Avoid launching dependent jobs until files return to `live`.

Programmatic wrappers exist as `dxpy.api.project_archive()` and
`dxpy.api.project_unarchive()`, but prefer the CLI for one-off human-reviewed
operations.

## Deletion

Data removal is irreversible on the platform. Removing a visible object can
also remove orphaned hidden linked objects.

Safe sequence:

1. List the exact IDs.
2. Describe each object.
3. Confirm project, folder, size, state, and linked-object impact.
4. Ask for confirmation.
5. Remove by ID.
6. Verify absence and record an audit note outside the deleted data.

Project controls are distinct:

- `protected=true` restricts project-data deletion to project administrators;
  when false, contributors can also delete.
- `destroyProtected=true` blocks destruction of the entire project regardless
  of requester permissions until an authorized administrator clears it.
- Project destruction removes every object. It fails while jobs are active
  unless `terminateJobs=true`, which force-terminates them.

Never clear `destroyProtected`, set `terminateJobs=true`, or destroy a project
as an implicit extension of an object-deletion request. Each requires separate
explicit authorization after listing active jobs, project protections, billing
context, and total data impact.

Python:

```python
import dxpy

project = dxpy.DXProject("project-xxxx")
project.remove_objects(["file-xxxx"], force=False)
```

Recursive folder removal:

```python
project.remove_folder("/obsolete/run-001", recurse=True, force=False)
```

This is dangerous. Removing `/` recursively deletes all container contents.
Never generate or execute that operation.

The API removes at most 10,000 objects per folder-removal request. Do not
automatically loop partial deletion without rechecking the remaining scope.

Project deletion, permission changes, and delegated
`overrideProjectAccess` deletion require separate explicit authorization.

## Batch Operation Checklist

- Bound result count and concurrency.
- Materialize and review the target ID list before mutation.
- Preserve a machine-readable manifest of source IDs and destinations.
- Make operations restartable/idempotent.
- Do not treat duplicate names as one object.
- Check file state after upload.
- Validate transfer integrity.
- Capture failures without logging credentials or sensitive metadata.
- Reconcile completed, skipped, and failed IDs.
- Respect service limits and use exponential backoff.
