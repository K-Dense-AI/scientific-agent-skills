# Metadata and Annotations

Annotations may contain participant identifiers, sample names, unpublished
results, free text, remote filenames, or attached files. Read and export the
minimum fields needed.

## Current Annotation Types

The OMERO structured annotation model includes:

- `TagAnnotation`
- `MapAnnotation`
- `FileAnnotation`
- `CommentAnnotation`
- `BooleanAnnotation`
- `LongAnnotation`
- `DoubleAnnotation`
- `TimestampAnnotation`
- `TermAnnotation`
- `XmlAnnotation`
- annotation hierarchies through annotation-to-annotation links

Current `omero.gateway` exports corresponding wrappers, including
`TagAnnotationWrapper`, `MapAnnotationWrapper`,
`FileAnnotationWrapper`, and `CommentAnnotationWrapper`. Do not import a
historical `BaseAnnotationWrapper`; the current public wrapper is
`AnnotationWrapper`.

Annotations can be linked to multiple objects. Their ownership and the
ownership of each link may differ. Deleting an annotation is not the same as
deleting one link.

## Bounded Read

`listAnnotations()` supports a namespace filter but not a page-size argument.
Cap client iteration and report truncation:

```python
from itertools import islice

image = conn.getObject("Image", image_id)
if image is None:
    raise LookupError("Image unavailable")

max_annotations = 100
items = list(islice(image.listAnnotations(), max_annotations + 1))
truncated = len(items) > max_annotations

for annotation in items[:max_annotations]:
    print(annotation.getId(), annotation.OMERO_CLASS, annotation.getNs())

print({"truncated": truncated})
```

Do not call `getValue()` when values are outside the approved export scope.
Merely avoiding printing after retrieval is weaker than not retrieving.

For explicit parent IDs, annotation links can be queried:

```python
image_ids = [101, 102]
for link in islice(
    conn.getAnnotationLinks("Image", parent_ids=image_ids),
    200,
):
    print(link.getParent().getId(), link.getChild().getId())
```

Keep both the parent-ID list and returned-link count bounded.

## Redacted Inventory

A safe default record contains identifiers and type, not values:

```python
def annotation_summary(annotation):
    details = annotation.getDetails()
    owner = details.getOwner() if details is not None else None
    return {
        "id": annotation.getId(),
        "type": annotation.OMERO_CLASS,
        "namespace": annotation.getNs(),
        "owner_id": owner.getId() if owner is not None else None,
        "value_redacted": True,
    }
```

Owner names, annotation values, file names, descriptions, and link-owner names
require separate inclusion decisions.

The bundled exporter defaults to redaction:

```bash
python -B scripts/export_image_metadata.py \
  --image-id 101 \
  --max-annotations-per-image 100 \
  --max-rois-per-image 100 \
  --output ./image-101-metadata.json

# Review, then connect. Add inclusion flags only when approved.
python -B scripts/export_image_metadata.py \
  --image-id 101 \
  --max-annotations-per-image 100 \
  --max-rois-per-image 100 \
  --execute \
  --output ./image-101-metadata.json
```

It never downloads FileAnnotation bytes or pixel data.

## Namespaces

Namespaces let tools assign semantics:

```python
for annotation in image.listAnnotations(ns="org.example.analysis.v1"):
    print(annotation.getId())
```

Use an organization-controlled URI or reverse-domain pattern and document its
schema/version. Do not claim a custom namespace is an OME standard.

The current client constant for client map annotations is:

```python
from omero.constants.metadata import NSCLIENTMAPANNOTATION
```

OME's Python example warns that a client map annotation should be linked to
only one object. Create a separate map annotation for each target when using
that namespace.

## Map Annotations

Read key/value pairs only when approved:

```python
from omero.gateway import MapAnnotationWrapper

for annotation in image.listAnnotations(ns="org.example.analysis.v1"):
    if isinstance(annotation, MapAnnotationWrapper):
        pairs = annotation.getValue()
        for key, value in pairs[:50]:
            print(key, value)
```

Apply independent limits to annotation count, pair count, key length, and
value length. Keys can be sensitive too; a “values redacted” export that leaves
participant IDs in keys is not redacted.

Creating and linking is a write:

```python
from omero.constants.metadata import NSCLIENTMAPANNOTATION
from omero.gateway import MapAnnotationWrapper

image = conn.getObject("Image", image_id)
if image is None:
    raise LookupError("Image unavailable")

pairs = [["Analysis version", "2.1"], ["Status", "reviewed"]]
annotation = MapAnnotationWrapper(conn)
annotation.setNs(NSCLIENTMAPANNOTATION)
annotation.setValue(pairs)
annotation.save()
image.linkAnnotation(annotation)
```

Before running this:

- confirm image ID and group;
- confirm write permission and namespace;
- validate pair count and string lengths;
- decide rollback behavior if save succeeds but link creation fails;
- never create duplicate metadata merely because an earlier query was scoped
  to the wrong group.

## Tags and Comments

Tag creation and linking are separate writes:

```python
from omero.gateway import TagAnnotationWrapper

tag = TagAnnotationWrapper(conn)
tag.setValue("Reviewed")
tag.setDescription("Reviewed under protocol v2")
tag.save()

image = conn.getObject("Image", image_id)
if image is None:
    raise LookupError("Image unavailable")
image.linkAnnotation(tag)
```

Query for an existing controlled tag before creating another. Check group and
owner semantics; do not reuse a same-named tag from an unintended group.

Comments are free text and often the most sensitive annotation type. Do not
include them in a general inventory. Never pass untrusted comments into shell,
HTML, SQL/HQL, filenames, or dynamic code.

## File Annotations

Inspect metadata without downloading bytes:

```python
from omero.gateway import FileAnnotationWrapper

for annotation in image.listAnnotations():
    if isinstance(annotation, FileAnnotationWrapper):
        original = annotation.getFile()
        print(
            {
                "annotation_id": annotation.getId(),
                "original_file_id": original.getId(),
                "size": original.getSize(),
                "mimetype": original.getMimetype(),
                "name_redacted": True,
            }
        )
```

Remote filenames are untrusted input. Never join them directly to an output
directory.

For one explicitly approved file, check size and use a caller-chosen path:

```python
from pathlib import Path

max_bytes = 50 * 1024 * 1024
destination = Path("./approved-result.bin")

original = file_annotation.getFile()
if original.getSize() > max_bytes:
    raise ValueError("File exceeds approved byte limit")
if destination.exists() or destination.is_symlink():
    raise FileExistsError(destination)

written = 0
with destination.open("xb") as handle:
    for chunk in file_annotation.getFileInChunks():
        written += len(chunk)
        if written > max_bytes:
            raise ValueError("Received more than approved byte limit")
        handle.write(chunk)
```

On failure, delete the partial local file if policy permits. Do not download
all file annotations attached to a project/dataset without an explicit list.

Uploading is a mutation:

```python
source = "./approved-analysis.csv"
annotation = conn.createFileAnnfromLocalFile(
    source,
    mimetype="text/csv",
    ns="org.example.analysis.v1",
    desc="Reviewed analysis results",
)
dataset.linkAnnotation(annotation)
```

Check local file size, type, content classification, target dataset ID/group,
and whether upload is permitted before execution.

## Numeric and Boolean Values

Wrapper examples:

```python
from omero.gateway import (
    BooleanAnnotationWrapper,
    DoubleAnnotationWrapper,
    LongAnnotationWrapper,
)
```

Numeric values still need units and semantics in the namespace/schema.
Do not infer that `DoubleAnnotation` values are in micrometers or that a
`LongAnnotation` is a count.

## Unlink Versus Delete

- **Unlink** deletes an object-annotation link but keeps the annotation and
  other links.
- **Delete annotation** deletes the annotation and may affect every linked
  object.

Before either operation:

1. retrieve and display exact link/annotation IDs;
2. count other links;
3. verify ownership and permission;
4. obtain explicit approval for the exact operation;
5. do not use a namespace-only bulk delete without an ID review;
6. wait for and check command completion.

Read-only export utilities must not include delete/unlink modes.

## Metadata Export Checklist

- Explicit object type and IDs
- One group context
- Maximum objects, annotations, links, pairs, and string length
- Values redacted by default
- File names and owner names separately gated
- No attachment bytes unless one file and byte cap are approved
- Output path chosen by caller; no remote-derived path
- Atomic write with owner-only permissions
- Connection closed in `finally`
