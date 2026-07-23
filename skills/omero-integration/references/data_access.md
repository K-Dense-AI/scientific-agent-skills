# Data Access, Hierarchies, and Transfers

Use this reference for bounded reads and explicit import/export scopes. Read
[`connection.md`](connection.md) first.

## Object Hierarchies

Common container paths are:

```text
Project -> Dataset -> Image
Screen -> Plate -> Well -> WellSample -> Image
Image -> Pixels -> Channel
Image -> Fileset -> OriginalFile(s)
```

Links are model objects and may be many-to-many. Do not assume an image has
exactly one dataset or a dataset exactly one project. Traverse links returned
by the server instead of synthesizing parent paths.

Common BlitzGateway object names documented by OME include:

- `Project`, `Dataset`, `Image`
- `Screen`, `Plate`, `PlateAcquisition`, `Well`
- `Roi`, `Shape`
- `Experimenter`, `ExperimenterGroup`
- `OriginalFile`, `Fileset`
- `Annotation` and specific annotation subtypes

Object-name support is not permission. A returned `None` may mean nonexistent
or inaccessible.

## One Object by ID

Use explicit IDs whenever possible:

```python
image_id = 123
image = conn.getObject("Image", image_id)
if image is None:
    raise LookupError("Image was not found or is not accessible")

print(image.getId())
print(image.getSizeX(), image.getSizeY())
```

Do not print names, descriptions, owner names, or acquisition metadata unless
the requested output includes them.

For multiple explicit IDs:

```python
requested_ids = [101, 102, 103]
for image in conn.getObjects(
    "Image",
    requested_ids,
    respect_order=True,
):
    print(image.getId())
```

Keep the input list bounded. Check whether inaccessible IDs were omitted.

## Bounded Pagination

`getObjects()` returns a generator. Use both an overall cap and page size:

```python
def iter_bounded(conn, object_type, *, limit=100, page_size=25):
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")
    if not 1 <= page_size <= min(limit, 200):
        raise ValueError("page_size must be between 1 and min(limit, 200)")

    emitted = 0
    offset = 0
    while emitted < limit:
        size = min(page_size, limit - emitted)
        page = list(
            conn.getObjects(
                object_type,
                opts={
                    "limit": size,
                    "offset": offset,
                    "order_by": "obj.id",
                },
            )
        )
        if not page:
            return

        for obj in page:
            yield obj
            emitted += 1

        if len(page) < size:
            return
        offset += len(page)
```

Do not write `list(conn.getObjects(...))` without server-side limits. If
another process changes rows during offset paging, results may shift; record
the extraction time and selected group.

The bundled inventory helper implements a cap of 1000 and page cap of 200:

```bash
python -B scripts/inventory.py \
  --object-type Image \
  --limit 50 \
  --page-size 25

# Review the dry-run JSON, then explicitly connect:
python -B scripts/inventory.py \
  --object-type Image \
  --limit 50 \
  --page-size 25 \
  --execute \
  --output ./image-inventory.json
```

Names are redacted unless `--include-names` is requested.

## Group and Owner Filters

Prefer one selected group:

```python
group_id = 42
conn.SERVICE_OPTS.setOmeroGroup(str(group_id))

for project in conn.getObjects(
    "Project",
    opts={"limit": 20, "offset": 0, "order_by": "obj.id"},
):
    print(project.getId())
```

Filters can further narrow a query:

```python
owner_id = conn.getUser().getId()
projects = conn.getObjects(
    "Project",
    opts={
        "owner": owner_id,
        "group": group_id,
        "limit": 20,
        "offset": 0,
        "order_by": "obj.id",
    },
)
```

Cross-group context (`-1`) must be separately approved and paired with a hard
limit. Never use it as a fallback when an object is not found.

## Traversing Containers

Downward traversal lazily loads children:

```python
project = conn.getObject("Project", project_id)
if project is None:
    raise LookupError("Project unavailable")

dataset_limit = 10
for dataset_index, dataset in enumerate(project.listChildren()):
    if dataset_index >= dataset_limit:
        break
    print(dataset.getId())

    image_limit = 25
    for image_index, image in enumerate(dataset.listChildren()):
        if image_index >= image_limit:
            break
        print(image.getId())
```

`countChildren()` can help plan a cap but does not replace one. A count may
change before retrieval.

For a direct dataset image query, prefer a server filter:

```python
images = conn.getObjects(
    "Image",
    opts={
        "dataset": dataset_id,
        "limit": 50,
        "offset": 0,
        "order_by": "obj.id",
    },
)
```

## Screening Data

Bound each hierarchy level:

```python
plate = conn.getObject("Plate", plate_id)
if plate is None:
    raise LookupError("Plate unavailable")

for well_index, well in enumerate(plate.listChildren()):
    if well_index >= 96:
        break
    print(well.getId())

    field_count = min(well.countWellSample(), 10)
    for field_index in range(field_count):
        image = well.getImage(field_index)
        if image is not None:
            print(image.getId())
```

Well rows/columns and field counts can reveal experiment design. Include them
only when requested.

## Image Metadata

Basic dimensions do not retrieve pixel planes:

```python
summary = {
    "id": image.getId(),
    "size_x": image.getSizeX(),
    "size_y": image.getSizeY(),
    "size_z": image.getSizeZ(),
    "size_c": image.getSizeC(),
    "size_t": image.getSizeT(),
    "pixels_type": image.getPixelsType(),
}
```

Physical sizes may be absent:

```python
size_x = image.getPixelSizeX(units=True)
if size_x is not None:
    print(size_x.getValue(), size_x.getSymbol())
```

Names, descriptions, acquisition dates, owner names, group names, and channel
labels are potentially sensitive metadata. Redact by default in broad reports.

## Filesets and Original Files

A fileset groups original imported files and may represent several images.
Inspect metadata before downloading:

```python
fileset = image.getFileset()
if fileset is not None:
    print(fileset.getId())
```

Downloading an `Image` or `Fileset` may retrieve several original files and
their directory structure. Estimate scope first; never use a container-wide
download merely because it is convenient.

The current CLI supports:

```bash
# One OriginalFile:
omero download OriginalFile:123 ./explicit-local-file

# Original files linked to one image:
omero download Image:123 ./explicit-empty-directory

# Original files in one fileset:
omero download Fileset:456 ./explicit-empty-directory
```

Authenticate through an already prompted CLI session. Do not add `-w`,
`--password`, or `-k` to reusable command text. Reject symlinked destinations
and collisions; never derive a local path directly from an untrusted remote
filename.

## Import Planning and Import

The OMERO importer can scan without a running server:

```bash
omero import -f ./explicit-input
omero import --depth 4 -f ./explicit-directory
```

`-f` lists files that would be imported, grouped into filesets, then exits.
This is the correct first pass; it is not a remote import.

The bundled local planner is even more conservative and does not invoke OMERO:

```bash
python -B scripts/plan_transfer.py import \
  --target Dataset:id:42 \
  --max-files 100 \
  ./explicit-input
```

After review and a prompted `omero login`, an actual scoped import is:

```bash
omero import -T Dataset:id:42 ./explicit-input
```

Important:

- The target must be in the current session group.
- Import needs compatible importer Java libraries; set `OMERODIR` to the
  matching extracted server distribution.
- `--parallel-fileset` and `--parallel-upload` are documented as experimental;
  high values can crash the client or make the server unresponsive.
- `--report --upload` can send broken source files and logs to the OME team.
  Never use it without explicit authorization to disclose that data.
- In-place imports change repository assumptions and are administrator
  workflows, not a routine client optimization.

## OME-TIFF and XML Export

The documented `omero export` command currently supports:

```bash
omero export --file ./image-123.ome.tiff Image:123
omero export --file ./image-123.ome.xml --type XML Image:123
```

This is not the same as downloading original files:

- export serializes an OMERO image as OME-TIFF or its metadata as XML;
- download retrieves original files associated with an OriginalFile,
  FileAnnotation, Image, or Fileset.

Dataset iteration exists only as an experimental export mode. Do not use it
for broad exports by default. Plan explicit image IDs instead:

```bash
python -B scripts/plan_transfer.py export \
  --format ome-tiff \
  --output-dir ./reviewed-output \
  Image:123 Image:124
```

The planner does not connect or export. Review file collisions, image count,
and available storage before running each proposed command.

## Transfer Checklist

Before any import, export, or download:

1. Confirm current session group.
2. Confirm explicit source paths or object IDs.
3. Cap file/object count and directory scan depth.
4. Distinguish derived OME-TIFF/XML export from original-file download.
5. Estimate bytes and review data-sharing authorization.
6. Use a dedicated existing output directory with no symlinks/collisions.
7. Never use credential flags.
8. Do not upload diagnostics or broken files without separate consent.
