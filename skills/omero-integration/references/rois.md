# Regions of Interest (ROIs)

ROIs and shape labels may encode phenotypes, diagnoses, sample identifiers, or
analysis decisions. Export geometry and labels only within an explicit scope.

## Model Semantics

The OMERO 5.6 line uses the June 2016 OME schema. The OME ROI model defines
eight concrete 2D shape types:

- Ellipse
- Label
- Line
- Mask
- Point
- Polygon
- Polyline
- Rectangle

Plane selectors are optional:

- `TheZ`: z-section; absent means all z-sections
- `TheT`: timepoint; absent means all timepoints
- `TheC`: channel; absent means all channels

Do not coerce absent values to zero. A 3D ROI is represented as a union of 2D
shapes across planes; it is not a native volumetric mesh.

Display fields include RGBA fill/stroke colors, stroke width, fill rule, dash
array, text label, and font properties. Geometry and display metadata are
distinct.

## Current Service Status

The current Python examples still retrieve ROIs with:

```python
roi_service = conn.getRoiService()
result = roi_service.findByImage(image_id, None)
```

However, the current OMERO Blitz API marks the `IRoi` interface deprecated.
That means “still available but at removal risk,” not “already removed.” OME
does not document a general replacement for every `IRoi` method in the pages
reviewed for this snapshot.

Therefore:

- isolate `IRoi` use behind a small function;
- do not build new broad workflows around legacy measurement-table helpers;
- verify the target server's generated API before relying on it;
- record this dependency in long-lived integrations.

The official OMERO.web JSON API also documents paginated ROI listing by image:
`/api/v0/m/rois/?image=<id>&limit=<n>&offset=<n>`. Use it only when the site
exposes the documented `api` app over HTTPS and its authentication model is
appropriate.

## Bounded ROI Read

`findByImage()` does not expose page arguments. Apply explicit image, ROI, and
shape caps and report truncation:

```python
image_id = 123
max_rois = 100
max_shapes_per_roi = 500

roi_service = conn.getRoiService()
result = roi_service.findByImage(image_id, None)
rois = list(result.rois)

roi_truncated = len(rois) > max_rois
for roi in rois[:max_rois]:
    shapes = list(roi.copyShapes())
    print(
        {
            "roi_id": roi.getId().getValue(),
            "shape_count_returned": min(len(shapes), max_shapes_per_roi),
            "shape_truncated": len(shapes) > max_shapes_per_roi,
        }
    )
```

The cap limits client processing/output, not necessarily server work:
`findByImage()` may already have assembled all matching ROIs. For a known very
large image, do not call it casually; consider the documented paginated JSON
API or a site-reviewed query.

The bundled exporter requires explicit image IDs and uses redaction defaults:

```bash
python -B scripts/export_image_metadata.py \
  --image-id 123 \
  --max-rois-per-image 100 \
  --max-shapes-per-roi 500 \
  --output ./image-123-metadata.json
```

Review the dry run, then add `--execute`. ROI labels remain redacted unless
`--include-roi-labels` is specified.

## Reading Shape Fields

Generated model values are usually wrapped in OMERO rtypes. Preserve `None`:

```python
def unwrap(value):
    if value is None:
        return None
    getter = getattr(value, "getValue", None)
    return getter() if callable(getter) else value


for roi in result.rois[:max_rois]:
    for shape in list(roi.copyShapes())[:max_shapes_per_roi]:
        record = {
            "id": unwrap(shape.getId()),
            "the_z": unwrap(shape.getTheZ()),
            "the_t": unwrap(shape.getTheT()),
            "the_c": unwrap(shape.getTheC()),
            "label_redacted": True,
        }
        print(record)
```

Use type checks before geometry access:

```python
import omero.model

if isinstance(shape, omero.model.RectangleI):
    geometry = {
        "x": unwrap(shape.getX()),
        "y": unwrap(shape.getY()),
        "width": unwrap(shape.getWidth()),
        "height": unwrap(shape.getHeight()),
    }
elif isinstance(shape, omero.model.EllipseI):
    geometry = {
        "x": unwrap(shape.getX()),
        "y": unwrap(shape.getY()),
        "radius_x": unwrap(shape.getRadiusX()),
        "radius_y": unwrap(shape.getRadiusY()),
    }
elif isinstance(shape, omero.model.LineI):
    geometry = {
        "x1": unwrap(shape.getX1()),
        "y1": unwrap(shape.getY1()),
        "x2": unwrap(shape.getX2()),
        "y2": unwrap(shape.getY2()),
    }
elif isinstance(shape, (omero.model.PolygonI, omero.model.PolylineI)):
    geometry = {"points": unwrap(shape.getPoints())}
```

Validate coordinates against image dimensions. Preserve floating-point
coordinates; do not truncate them to integers merely for JSON.

For masks:

- export position, dimensions, plane selectors, and byte count only by default;
- do not serialize mask bytes into broad JSON;
- treat decoded masks as pixel-derived data;
- validate width/height and bit packing against the current model before
  reconstructing.

## Creating an ROI Is a Write

Current core-model pattern:

```python
import omero.model
from omero.rtypes import rdouble, rint, rstring

image = conn.getObject("Image", image_id)
if image is None:
    raise LookupError("Image unavailable")

x = 50.0
y = 100.0
width = 200.0
height = 150.0
z = 0
t = 0

if x < 0 or y < 0 or x + width > image.getSizeX() or y + height > image.getSizeY():
    raise ValueError("Rectangle is outside image bounds")
if not 0 <= z < image.getSizeZ() or not 0 <= t < image.getSizeT():
    raise ValueError("Plane index is outside image bounds")

rectangle = omero.model.RectangleI()
rectangle.setX(rdouble(x))
rectangle.setY(rdouble(y))
rectangle.setWidth(rdouble(width))
rectangle.setHeight(rdouble(height))
rectangle.setTheZ(rint(z))
rectangle.setTheT(rint(t))
rectangle.setTextValue(rstring("reviewed-region"))

roi = omero.model.RoiI()
roi.setImage(image._obj)
roi.addShape(rectangle)

saved = conn.getUpdateService().saveAndReturnObject(roi)
print(saved.getId().getValue())
```

Before execution, confirm:

- image ID, group, and dimensions;
- shape count and coordinate system;
- Z/T/C semantics;
- label sensitivity;
- write permission;
- whether an existing ROI should be updated rather than duplicated.

## RGBA Encoding

The official Python example encodes color bytes as a signed 32-bit integer:

```python
def rgba_to_int(red, green, blue, alpha=255):
    channels = (red, green, blue, alpha)
    if any(not 0 <= value <= 255 for value in channels):
        raise ValueError("RGBA channels must be in 0..255")
    return int.from_bytes(channels, byteorder="big", signed=True)
```

Use `rint(rgba_to_int(...))` for generated shape color fields. Do not swap RGBA
order or assume an unsigned representation.

## Intensity Measurements

The historical Python example uses
`IRoi.getShapeStatsRestricted(shape_ids, z, t, channel_indices)`. Since
`IRoi` is deprecated:

1. verify the method in the target server's generated API;
2. cap shape and channel counts;
3. preserve channel indexing (pixel channels are zero-based);
4. record the exact server/client versions;
5. do not describe the result as a replacement for a validated analysis
   pipeline.

For simple rectangular reads, a bounded pixel tile may be clearer:

```python
pixels = image.getPrimaryPixels()
z = 0
c = 0
t = 0
x = 10
y = 20
width = 100
height = 80

tile = next(pixels.getTiles([(z, c, t, (x, y, width, height))]))
```

Confirm the current API's tile generator behavior and cap tile area. Polygon,
polyline, ellipse, and mask measurements require a correctly defined raster
mask; a bounding box alone is not the ROI.

## Updates and Deletion

Updating a shape and saving an ROI is a write that can affect downstream
measurements. Deleting an ROI removes its shapes. Never add delete support to a
read-only export script.

Before update/delete:

- show image, ROI, and shape IDs;
- retrieve current values;
- check permissions and group context;
- obtain approval for the exact IDs;
- avoid namespace/label-based bulk selection;
- wait for command completion and verify the result.

## ROI Export Checklist

- Explicit image IDs only
- One group context
- Maximum images, ROIs per image, and shapes per ROI
- Labels redacted by default
- Mask bytes omitted
- No pixel values unless separately requested
- Plane selectors preserve `None`
- Geometry strings have a length cap
- `IRoi` deprecation recorded
- Connection closed in `finally`
