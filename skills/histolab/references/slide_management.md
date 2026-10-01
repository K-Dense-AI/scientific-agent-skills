# Slide management (Histolab 0.7.0)

Examples using `slide.svs` are illustrative until a real slide is supplied.
The API operations below are also exercised on tiny local fixtures in the skill
suite. Source: [0.7.0 Slide implementation](https://github.com/histolab/histolab/blob/v0.7.0/histolab/slide.py).

## Load and inspect

```python
from pathlib import Path
from histolab.slide import Slide

output = Path("output/inspection")
output.mkdir(parents=True, exist_ok=True)
slide = Slide("slide.svs", processed_path=output)
print(slide.name, slide.dimensions)
print("Available levels:", slide.levels)
print("Number of levels:", len(slide.levels))
for level in slide.levels:
    print(level, slide.level_dimensions(level))
slide.thumbnail.save(output / "thumbnail.png")
slide.scaled_image(scale_factor=32).save(output / "downsampled.png")
```

`slide.levels` is a list such as `[0, 1, 2]`, not a count.
`slide.level_dimensions(level)` is a method, not an indexable tuple.
Histolab has no public `slide.level_downsamples` attribute. To read the actual
backend factors, use the documented OpenSlide API with a separate managed handle:

```python
import openslide

with openslide.open_slide("slide.svs") as wsi:
    downsamples = tuple(wsi.level_downsamples)
    print(wsi.level_dimensions, downsamples)
```

`openslide.open_slide` may fall back to a Pillow `ImageSlide` for ordinary raster
files. Those are useful for software tests but have no scanner MPP calibration.
Histolab `Slide` does not expose a public close/context-manager API in 0.7.0;
avoid keeping a whole cohort of lazy open slides alive simultaneously.

## Physical scale and metadata

`slide.properties` exposes OpenSlide metadata. Check `openslide.mpp-x` and
`openslide.mpp-y` independently; values are strings and can be missing.
`slide.base_mpp` is micrometers per pixel, **not** optical objective power. It
uses the X resolution and some vendor fallbacks, and raises when calibration
cannot be inferred. Do not assume that this scalar proves isotropic pixels.

For a level with downsample `d`, a `(w, h)` tile covers approximately
`(w * d * mpp_x, h * d * mpp_y)` micrometers. Record native metadata,
actual downsample, output size and any resampling. Missing or inconsistent MPP
requires review; a level number or "20x" filename cannot supply calibration.

`mpp` takes precedence over `level` in extraction. Exact-MPP reads use
`large_image`, even though level reads always use OpenSlide. Install the
[`large-image` package and a matching tile source](https://girder.github.io/large_image/)
(e.g. `large-image-source-openslide`) into a compatible isolated environment and
construct `Slide(..., use_largeimage=True)`. This optional path is source-verified
only here; its current dependency stack was not installed or executed.
Do not install every backend merely to access one slide format. Histolab 0.7.0
mutates internal tile dimensions and grid overlap during MPP extraction;
construct a fresh tiler per run and do not assume an MPP preview before extraction
matches saved coordinates. Check output geometry against saved bounds.

```python
# Illustrative: requires the optional large_image backend and calibrated metadata.
from histolab.slide import Slide
from histolab.tiler import GridTiler
from histolab.masks import TissueMask

slide = Slide("slide.svs", processed_path="output/mpp", use_largeimage=True)
tiler = GridTiler(tile_size=(256, 256), mpp=0.5, check_tissue=True)
tiler.extract(slide, extraction_mask=TissueMask())
```

## Explicit coordinate extraction

`CoordinatePair` contains `(x_ul, y_ul, x_br, y_br)` **in level-0 pixels**.
`tile_size` is the output width/height at the requested level. Never pass a
2-tuple in place of a bounding box.

```python
from histolab.types import CoordinatePair

# A 256 x 256 level-0 patch (must lie inside this slide).
coords = CoordinatePair(100, 200, 356, 456)
tile = slide.extract_tile(coords=coords, tile_size=(256, 256), level=0)
assert tile.image.size == (256, 256)
print(tile.coords, tile.level)
```

For coarser levels, expand the level-0 box by the actual downsample. The level
path reads `tile_size` starting from the upper-left point; it does not crop to
an arbitrarily supplied lower-right corner. Keep the box consistent with the
size and level so provenance and previews describe the pixels actually read.

## Sample data

The [data API](https://histolab.readthedocs.io/en/latest/api/data.html) returns
`(openslide_handle, local_path)`, not just an image. Close that handle when only
the path is needed. This tiny SVS is bundled with the distribution:

```python
from histolab.data import cmu_small_region
from histolab.slide import Slide

sample_handle, sample_path = cmu_small_region()
sample_handle.close()
slide = Slide(sample_path, processed_path="output/sample")
```

Other examples include `prostate_tissue`, `ovarian_tissue`, `breast_tissue`,
`heart_tissue`, and **`ihc_kidney`** (there is no `kidney_tissue`). Prostate,
ovarian and breast samples use public TCGA/GDC downloads; heart uses the
OpenSlide test repository; kidney is an IHC image from IDR. They are not all
TCGA or H&E data. `pooch` fetches and checks hashes against the release registry.
Review download sizes before invoking these functions; no large remote samples
were fetched in this review. Legacy remote URLs can move independently of the
release; preserve provenance and never silently substitute a different slide.
At this review, GDC metadata confirmed the three listed TCGA files as open and
released, and a header-only heart-file probe redirected to HTTPS successfully.
The IDR kidney download URL entered a redirect loop; `ihc_kidney()` was therefore
not verified usable. Obtain a provenance-matched local image if that helper fails.
These metadata/header probes do not verify complete download bytes or hashes.

See the [release data source](https://github.com/histolab/histolab/blob/v0.7.0/histolab/data/__init__.py)
and [URL/hash registry](https://github.com/histolab/histolab/blob/v0.7.0/histolab/data/_registry.py)
for the actual sample mappings. Histolab core processing has no remote service,
authentication, pagination or REST request body.
