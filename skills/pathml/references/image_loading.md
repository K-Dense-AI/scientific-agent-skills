# Image loading, formats, levels, and coordinates

This reference targets the **PyPI-stable PathML 3.0.8 API**. All sources were
checked on 2026-10-01 against the v3.0.8 wheel/tag. PathML examples are
illustrative: native readers were not executed in this review.

## Start with a local, de-identified file

Never infer authorization from the fact that a file is readable. Whole-slide
images and DICOM objects can carry identifiers in pixels, labels, filenames, and
metadata. Keep the original on approved storage, use a pseudonymous working name,
and do not print arbitrary metadata. The bundled inspector emits only an
allowlist of technical fields:

```bash
python scripts/slide_manifest.py inspect \
  --slide data/pseudonymous_slide.svs \
  --root .
```

It rejects URLs and symlinks. PathML itself accepts paths more broadly, so validate
before constructing a slide object.

## Stable slide classes

```python
from pathml.core import (
    CODEXSlide,
    HESlide,
    IHCSlide,
    MultiparametricSlide,
    SlideData,
    SlideDataset,
    VectraSlide,
    types,
)
```

Convenience classes pass a stable `SlideType`:

- `HESlide(...)` → `types.HE`
- `IHCSlide(...)` → `types.IHC`
- `MultiparametricSlide(...)` → `types.IF`, Bio-Formats by default
- `VectraSlide(...)` → `types.Vectra`, Bio-Formats by default
- `CODEXSlide(...)` → `types.CODEX`, Bio-Formats by default

The generic constructor is:

```python
slide = SlideData(
    "data/pseudonymous_slide.svs",
    name="slide-001",
    backend="openslide",
    slide_type=types.HE,
)
```

`SlideData.from_slide()`, `read_region()`, `level_dimensions`, and
`level_downsamples` are not stable `SlideData` APIs. Use the constructor,
`extract_region()`, `shape`, and backend-specific objects where necessary.

For a local cohort, instantiate slides first:

```python
from pathlib import Path
from pathml.core import HESlide, SlideDataset

root = Path("data/slides")
paths = sorted(root.glob("*.svs"))
slides = [HESlide(path, backend="openslide", name=path.stem) for path in paths]
dataset = SlideDataset(slides)
```

Do not recursively accept arbitrary user-controlled paths. Validate a manifest,
freeze the patient split, and then build this list.

## Backends and file types

### OpenSlide

Use `backend="openslide"` for common brightfield pyramid formats. Stable PathML
lists:

`.svs`, `.tif`, `.tiff`, `.bif`, `.ndpi`, `.vms`, `.vmu`, `.scn`, `.mrxs`,
and `.svslide`.

The complete capability depends on the installed OpenSlide build and the vendor
subtype, not only the suffix. Some generic TIFFs are not valid WSIs, and some
files with a supported suffix use unsupported compression.

Native OpenSlide is required. Official PathML guidance uses
`openslide-tools` on Debian/Ubuntu, Homebrew `openslide` on macOS, and vcpkg or
official prebuilt binaries on Windows.

### Bio-Formats

Use `backend="bioformats"` for multidimensional microscopy, OME-TIFF, QPTIFF, and
formats OpenSlide cannot read. Bio-Formats supports a large catalogue (the
upstream examples describe 160+ formats), including `.ome.tif`, `.ome.tiff`,
`.qptiff`, `.czi`, `.vsi`, `.zvi`, and many laboratory formats.

This backend requires Java, `python-bioformats`, and `python-javabridge`. It
starts a JVM and stable source configures a large maximum heap, so isolate and
resource-limit untrusted images. Java has an approximately 2 GB array limit in
the backend. A listed extension is not proof that every variant loads.

Bio-Formats returns five-dimensional arrays in PathML order:

`(i, j, z, channel, time)` = `(row, column, z, c, t)`.

Even singleton `z` and `time` dimensions are retained until a transform such as
`CollapseRunsCODEX` or `CollapseRunsVectra` changes the layout.

`extract_region(..., normalize=True)` is the default. It divides by
`2**(8 * source_dtype.itemsize)`, multiplies by 256, then casts to `uint8`.
This loses high-bit-depth intensity precision and is not a valid generic
normalization for signed/floating-point acquisitions. For quantification use
`normalize=False` in `extract_region`, `generate_tiles`, or `SlideData.run`
(forwarded through `**kwargs`), and verify dtype/range with known pixels.
This preserves the read values in memory; h5path storage has a separate float16
conversion described in `data_management.md`.

### DICOM

Use `backend="dicom"` for `.dcm` or `.dicom`. Stable PathML treats DICOM frames as
tiles. DICOM metadata is especially likely to contain PHI; de-identify with an
approved DICOM process before PathML, preserve required UIDs consistently, and
never dump the full dataset to logs.

### h5path

`.h5` and `.h5path` inputs are inferred as PathML's processed HDF5 format:

```python
from pathml.core import SlideData

processed = SlideData("derived/slide-001.h5path")
```

There is no stable `from_hdf5()` constructor. See `data_management.md`.

## Backend inference versus explicit selection

If `backend=None`, PathML infers a backend from the suffix. Prefer an explicit
backend in reproducible work:

```python
from pathml.core import HESlide

slide = HESlide("data/slide-001.svs", backend="openslide")
```

Reasons to be explicit:

- `.tif` can mean a brightfield pyramid, OME-TIFF, or a plain raster.
- Bio-Formats is broader but slower and starts Java.
- Backend metadata and pyramid interpretation differ.
- A file renamed to a recognized suffix is not thereby valid.

## Shape, regions, and tile generation

`slide.shape` returns `(height, width)` for the backend's default level.

```python
height, width = slide.shape

region = slide.extract_region(
    location=(2_000, 3_000),  # (i, j) = (row, column)
    size=(512, 768),          # (height, width)
    level=1,
)

tiles = slide.generate_tiles(
    shape=(512, 512),
    stride=(256, 256),
    pad=False,
    level=1,
)
```

`generate_tiles()` is lazy. Do not materialize all tiles just to count them.
Use the bounded planner first:

```bash
python scripts/plan_pipeline.py \
  --width 100000 --height 80000 \
  --tile-size 512 --stride 256 \
  --level-downsample 4 \
  --level-width 25000 --level-height 20000
```

The level dimensions above are illustrative; supply values read from your file.

`SlideData.run()` uses different parameter names: `tile_size`, `tile_stride`,
`tile_pad`, and `level`.

## Coordinate convention

PathML's `Tile.coords` is the top-left `(i, j)`:

- `i`: row / vertical / image `y`
- `j`: column / horizontal / image `x`
- origin: top-left pixel `(0, 0)`
- units: pixels at the **selected pyramid level**

For OpenSlide, 3.0.8 uses `int(level_downsamples[level])`, then swaps `(i, j)`
before calling OpenSlide's level-0 `(x, y)` API. A true downsample of 3.99 becomes
3 for the region origin, although the requested image still uses that pyramid
level. This shifts tiles and breaks a naive coordinate join. Prefer level 0;
otherwise reject nonintegral downsamples before extraction:

```python
downsample_level = float(slide.slide.slide.level_downsamples[level])
if not downsample_level.is_integer():
    raise ValueError("PathML 3.0.8 truncates fractional OpenSlide downsamples; use level 0")
```

For the supported integral-downsample case:

```text
row_level0 = i_level * downsample_level
col_level0 = j_level * downsample_level
y_um = row_level0 * mpp_y
x_um = col_level0 * mpp_x
```

Use scanner-provided level-0 MPP when reliable. Do not silently derive MPP from
objective power. Record:

- coordinate convention (`ij` or `xy`)
- pyramid level and exact downsample
- whether MPP is measured, metadata-derived, or unavailable
- tile height/width, stride, and padding

`QuantifyMIF` later writes `obsm["spatial"]` in `(x, y)` order, so a conversion is
required when joining it to `Tile.coords`. For a previously processed fractional
level, recover actual sampled origins plus within-tile coordinates; multiplying
the combined coordinate by the true downsample cannot repair the origin error.

## Pyramid levels

For OpenSlide, level 0 is highest resolution. Later levels are downsampled, but
the factors are slide-specific; do not assume `4x`, `16x`, or a particular
magnification sequence.

Backend-level inspection:

```python
level_count = slide.slide.level_count
level0_shape = slide.slide.get_image_shape(level=0)  # (height, width)

# OpenSlide-specific internals, not a backend-neutral PathML contract:
downsamples = tuple(slide.slide.slide.level_downsamples)
dimensions_xy = tuple(slide.slide.slide.level_dimensions)
```

Guard backend-specific access and record it as such. Bio-Formats maps image series
to levels; those series are not necessarily an optical pyramid.

## Tile count and edge behavior

For one dimension `D`, tile extent `T`, and stride `S`, `pad=False` yields:

```text
0                         if D < T
floor((D - T) / S) + 1    otherwise
```

With `pad=True`, stable PathML follows its backend implementation, which is not
identical to a generic `ceil(D / S)` rule for every overlapping configuration.
Use the bundled planner and verify a small synthetic case. Padded pixels are zero,
which can bias tissue/stain/QC transforms.

At nonzero levels supply the exact backend width/height to the planner using
`--level-width` and `--level-height`. The default `ceil(level0/downsample)` is an
estimate; vendor pyramid dimensions can differ and change the tile count.

Important stable limitation: `SlideData.generate_tiles()` does not slice
slide-level masks into padded tiles. Do not combine a slide-level mask with
`pad=True` without an explicit, tested padding policy.

## Technical metadata without PHI leakage

PathML 3.0.8 has no backend-neutral `slide.metadata` mapping. Technical metadata
is backend-specific:

- OpenSlide properties are under the wrapped OpenSlide object.
- Bio-Formats stores OME-XML in its backend `metadata`.
- DICOM contains a full clinical metadata model.

Default to a strict allowlist such as:

- dimensions and level count
- level downsamples
- MPP X/Y
- objective power
- scanner vendor/model
- pixel dtype, channels, Z, and time dimensions

Do not emit patient name/ID, accession, dates, institution, free text, UIDs, or
file paths. Even technical fields can be identifying in a small cohort; minimize
what is retained.

## Loading/QC checklist

Before large-scale processing:

1. Validate suffix, regular-file status, symlinks, size, and manifest uniqueness.
2. Confirm backend and native dependencies with a non-sensitive test slide.
3. Read a thumbnail or a few bounded regions, not the full level-0 image.
4. Confirm color/channel order, dtype, level count, dimensions, and MPP.
5. Check orientation, blank areas, focus, folds, pen, bubbles, coverslip edges,
   clipping, and scanner artifacts.
6. Confirm tile coordinates by overlaying a few sampled tiles on a thumbnail.
7. Record failures instead of silently dropping slides.

## Sources and further reading

API baseline reviewed 2026-10-01 using the released wheel/tag; hosted docs may lag.

- Stable loading guide:
  https://pathml.readthedocs.io/en/stable/loading_slides.html
- Stable core API:
  https://pathml.readthedocs.io/en/stable/api_core_reference.html
- Stable source (`slide_data.py`):
  https://github.com/Dana-Farber-AIOS/pathml/blob/v3.0.8/pathml/core/slide_data.py
- Stable source (`slide_backends.py`):
  https://github.com/Dana-Farber-AIOS/pathml/blob/v3.0.8/pathml/core/slide_backends.py
- Stable source (`tile.py`):
  https://github.com/Dana-Farber-AIOS/pathml/blob/v3.0.8/pathml/core/tile.py
- OpenSlide formats: https://openslide.org/formats/
- Bio-Formats supported formats:
  https://docs.openmicroscopy.org/bio-formats/latest/supported-formats.html
