# Pixels, Rendering, and Derived Images

Pixel planes, thumbnails, rendered images, channel labels, and physical sizes
are data exports. Set explicit image IDs, coordinates, byte/memory caps, and
output paths before retrieval.

## Dimensions Before Data

Inspect dimensions without loading a plane:

```python
image = conn.getObject("Image", image_id)
if image is None:
    raise LookupError("Image unavailable")

dimensions = {
    "size_x": image.getSizeX(),
    "size_y": image.getSizeY(),
    "size_z": image.getSizeZ(),
    "size_c": image.getSizeC(),
    "size_t": image.getSizeT(),
    "pixels_type": image.getPixelsType(),
}
```

Estimate element count and memory before a read. A single `uint16` plane uses
roughly `size_x * size_y * 2` bytes before NumPy/container overhead. Do not
retrieve a full 5D image by default.

## One Raw Plane

Raw pixel access is zero-based in Z, C, and T:

```python
z = 0
c = 0
t = 0

if not 0 <= z < image.getSizeZ():
    raise ValueError("Z out of range")
if not 0 <= c < image.getSizeC():
    raise ValueError("C out of range")
if not 0 <= t < image.getSizeT():
    raise ValueError("T out of range")

max_pixels = 16_000_000
if image.getSizeX() * image.getSizeY() > max_pixels:
    raise ValueError("Plane exceeds approved pixel count; use tiles")

pixels = image.getPrimaryPixels()
plane = pixels.getPlane(z, c, t)
print(plane.shape, plane.dtype)
```

Do not print arrays. Summaries such as min/max may still reveal signal
distribution and should be included only when requested.

## Several Explicit Planes

`getPlanes()` accepts a list of `(z, c, t)` tuples and returns an iterator.
Bound the coordinate list and process incrementally:

```python
coordinates = [(0, 0, 0), (1, 0, 0), (2, 0, 0)]
if len(coordinates) > 20:
    raise ValueError("Too many planes")

for (z, c, t), plane in zip(coordinates, pixels.getPlanes(coordinates)):
    print({"z": z, "c": c, "t": t, "shape": plane.shape})
```

Do not create a coordinate list from all dimensions until the resulting count
has been checked.

## Tiles for Large Images

`getTiles()` accepts `(z, c, t, (x, y, width, height))` tuples:

```python
x = 0
y = 0
width = 512
height = 512
z = 0
c = 0
t = 0

if width <= 0 or height <= 0:
    raise ValueError("Tile dimensions must be positive")
if x < 0 or y < 0:
    raise ValueError("Tile origin must be non-negative")
if x + width > image.getSizeX() or y + height > image.getSizeY():
    raise ValueError("Tile exceeds image bounds")
if width * height > 1_048_576:
    raise ValueError("Tile exceeds approved pixel count")

request = [(z, c, t, (x, y, width, height))]
tile = next(pixels.getTiles(request))
```

For a tiled scan, cap:

- number of tiles;
- pixels per tile;
- total pixels;
- channels/Z/T;
- memory retained at once.

Do not infer that a rectangular tile is equivalent to a nonrectangular ROI.

## Channel Metadata

Channel metadata may include sensitive labels:

```python
max_channels = min(image.getSizeC(), 16)
for index, channel in enumerate(image.getChannels()):
    if index >= max_channels:
        break
    print(
        {
            "index": index,
            "label_redacted": True,
            "color": channel.getColor().getRGB(),
            "lut": channel.getLut(),
            "reverse_intensity": channel.isReverseIntensity(),
        }
    )
```

Raw pixel channel indices are zero-based. BlitzGateway rendering channel
selectors are one-based. Keep this conversion explicit.

## Physical Dimensions

Physical sizes can be absent:

```python
for axis, value in (
    ("x", image.getPixelSizeX(units=True)),
    ("y", image.getPixelSizeY(units=True)),
    ("z", image.getPixelSizeZ(units=True)),
):
    if value is not None:
        print(axis, value.getValue(), value.getSymbol())
```

Preserve the unit. Do not assume an unwrapped numeric value has the unit needed
by downstream analysis.

Changing pixel sizes mutates the server model and must be a separately
reviewed write. Do not “correct” missing metadata automatically.

## Thumbnail Bytes

`getThumbnail()` returns encoded image bytes using current rendering settings:

```python
from io import BytesIO
from PIL import Image

thumbnail_bytes = image.getThumbnail(size=(96, 96))
thumbnail = Image.open(BytesIO(thumbnail_bytes))
thumbnail.load()
print(thumbnail.size)
```

To save, use a caller-selected filename and refuse collisions/symlinks:

```python
from pathlib import Path

destination = Path("./image-123-thumbnail.png")
if destination.exists() or destination.is_symlink():
    raise FileExistsError(destination)
thumbnail.save(destination, format="PNG")
```

Do not derive `destination` from `image.getName()`.

## Rendering

`renderImage(z, t, compression=0.9)` returns a Pillow image:

```python
z = image.getSizeZ() // 2
t = 0
rendered = image.renderImage(z, t, compression=0.9)
```

The rendered result reflects the current rendering model, active channels,
colors, windows, LUTs, and defaults. Record those settings when a reproducible
figure depends on them.

Current official examples set active rendering channels with one-based
indices:

```python
image.setActiveChannels(
    [1, 2],
    [[20.0, 300.0], [50.0, 500.0]],
    ["00FF00", "FF0000"],
)
rendered = image.renderImage(z, t)
```

This initializes a stateful rendering engine. Keep the rendering scope short.
Closing the BlitzGateway closes its tracked services; if using low-level
stateful services directly, close each in `finally`. Do not depend on private
attributes such as `image._re` in durable code.

`saveDefaults()` or other persistence calls change server rendering settings.
Do not call them in a read/render helper. Rendering locally does not authorize
persisting new defaults.

## Histograms and Statistics

Histograms and min/max statistics can be large or expensive across many
channels/planes. Restrict:

- one explicit image;
- an allowlisted channel list;
- bin count;
- Z/T;
- number of returned arrays.

Do not use whole-dataset histograms as a connectivity test.

## Derived Images Are Writes

`BlitzGateway.createImageFromNumpySeq(...)` creates a server image:

```python
result = conn.createImageFromNumpySeq(
    plane_iterator,
    "reviewed-derived-image",
    sizeZ=1,
    sizeC=source.getSizeC(),
    sizeT=source.getSizeT(),
    description="Method and source IDs recorded separately",
    dataset=target_dataset,
    sourceImageId=source.getId(),
)
```

Before execution:

1. validate iterator plane order and exact expected plane count;
2. validate each shape and dtype;
3. cap source planes and memory;
4. confirm target dataset and group;
5. confirm output name/description contains no secrets;
6. decide cleanup for a partial write;
7. copy physical dimensions only when semantically valid.

For a maximum-intensity projection, the derived image has one Z plane.
Do not copy a source Z spacing that no longer describes the data.

## Dtype Handling

Keep the source dtype unless the algorithm requires conversion:

```python
import numpy as np

plane_float = plane.astype(np.float32)
# Perform reviewed numerical processing.
result = np.clip(plane_float, 0, np.iinfo(np.uint16).max).astype(np.uint16)
```

Document clipping, scaling, normalization, and rounding. Never cast a float
array to an integer type without checking range and non-finite values.

## Rendering and Pixel Checklist

- Explicit image ID and group
- Dimensions inspected before retrieval
- Z/C/T and coordinates range-checked
- Plane/tile count and total pixels bounded
- Raw channel indexing distinguished from rendering indexing
- Labels and pixel-derived values classified for export
- Caller-selected non-symlink output with collision refusal
- Rendering services short-lived
- No rendering-default save in read-only workflows
- Derived-image creation separately approved
- Connection and stateful services closed
