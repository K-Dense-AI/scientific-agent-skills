# Tile extraction (Histolab 0.7.0)

Source: [release tiler code](https://github.com/histolab/histolab/blob/v0.7.0/histolab/tiler.py)
and [scorers](https://github.com/histolab/histolab/blob/v0.7.0/histolab/scorer.py).
Examples with `slide` assume a loaded `Slide` and a dedicated output directory.

## Parameters and strategy

All tilers accept `tile_size=(width, height)`, `level=0`, `check_tissue=True`,
`tissue_percent=80.0`, `prefix=""`, `suffix=".png"`, and optional `mpp=None`.
`mpp` overrides `level` and needs the optional backend described in slide
management. `tile_size` is required. `extraction_mask` belongs to the
`extract` and `locate_tiles` methods, not any constructor.

| Class | Additional constructor parameters | Behavior |
| --- | --- | --- |
| `RandomTiler` | Required `n_tiles`; `seed=7`, `max_iter=10000` | Up to requested count, stopping at attempt limit |
| `GridTiler` | `pixel_overlap=0` | Grid candidates within mask, then tissue checks |
| `ScoreTiler` | Required `scorer`; `n_tiles=0`, `pixel_overlap=0` | Ranks eligible grid candidates and saves top count; 0 saves all |

`max_iter >= n_tiles` is required. Seeds make same-slide, same-configuration
sampling reproducible; random tiles can overlap and are not independent samples.
Grid stride is `(width - overlap, height - overlap)` at output resolution. Keep
positive overlap below both dimensions to avoid invalid/zero strides. A negative
value adds a gap. Mask boundaries, partial tiles and tissue checks can leave
uncovered tissue even with zero overlap.

<!-- recipe: tilers -->
```python
from histolab.tiler import RandomTiler, GridTiler, ScoreTiler
from histolab.scorer import NucleiScorer
from histolab.masks import TissueMask

mask = TissueMask()
random_tiler = RandomTiler(
    tile_size=(256, 256), n_tiles=20, level=0, seed=42,
    check_tissue=True, tissue_percent=80.0, prefix="random_",
)
grid_tiler = GridTiler(
    tile_size=(256, 256), level=0, pixel_overlap=0,
    check_tissue=True, tissue_percent=80.0, prefix="grid_",
)
score_tiler = ScoreTiler(
    tile_size=(256, 256), scorer=NucleiScorer(), n_tiles=10,
    level=0, check_tissue=True, prefix="score_",
)
```

Choose one and extract into a fresh directory. Existing filenames may be
overwritten on repeated extraction; keep run outputs distinct.

```python
preview = random_tiler.locate_tiles(slide, extraction_mask=mask)
preview.save("random_locations.png")
random_tiler.extract(slide, extraction_mask=mask, log_level="INFO")
```

`locate_tiles` returns a Pillow image and has **no `n_tiles` argument**. Use a
separately constructed smaller tiler for a small preview. Score previews still
score all candidates, and preview followed by extraction repeats this work.
Do not assume the `tiles` argument accepts bare Tile objects in 0.7.0: the
implementation indexes coordinate pairs from `(tile_or_score, coords)` entries,
despite the older API annotation. Use the normal automatic preview path unless
you have verified the release-specific structure.

## What the scores measure

- `NucleiScorer()` estimates an H&E nuclear **area fraction**, multiplied by
  `tanh(tissue_fraction)`, using hematoxylin extraction, Yen thresholding and
  morphology. It does not count nuclei, classify tumors or measure mitoses.
- `CellularityScorer(consider_tissue=True)` divides thresholded hematoxylin area
  by detected tissue area (or total tile area when False). A blank/degenerate
  tissue mask can produce non-finite values; artifacts can dominate either score.
- A custom scorer is any callable accepting a `Tile` and returning a finite
  numeric score. For example, variance emphasizes texture, not validated focus:

<!-- recipe: variance-scorer -->
```python
import numpy as np

class ColorVarianceScorer:
    def __call__(self, tile):
        rgb = np.asarray(tile.image.convert("RGB"), dtype=float)
        return float(rgb.var(axis=(0, 1)).sum())
```

Validate whether the chosen score selects scientifically relevant tissue.
Rare but informative low-scoring regions can disappear under top-k selection.
Lower `n_tiles` reduces saved output but not the full grid-scoring cost.

## CSV report contract

```python
score_tiler.extract(slide, extraction_mask=mask, report_path="tiles_report.csv")
```

The file contains only these columns:

```csv
filename,score,scaled_score
score_tile_0_level0_100-200-356-456.png,0.12,1.0
```

The row above illustrates schema and filename form, not a measured result.
The report describes saved tiles, not every candidate, and does not include
`tissue_percent`, separate coordinates, slide ID or MPP. Filename bounds are
level-0 coordinates in `{prefix}tile_{index}_level{level}_{x0}-{y0}-{x1}-{y1}{suffix}`.
When extracting by MPP, the filename's level is not sufficient resolution
provenance: store the requested MPP and resampling separately.

`scaled_score` is min-max scaling over the full candidate score set, which is
slide-specific and not a cross-slide probability. In 0.7.0 equal scores cause
undefined scaling (including a possible division error). Prefer raw scores;
inspect scores and catch/report failed extraction instead of fabricating zeros.
An empty eligible grid raises `RuntimeError`. Count saved files and report rows;
log counters are not a reliable substitute for output accounting.

## Aligned extraction across levels

The same seed at different levels does **not** produce aligned locations.
Persist explicit level-0 centers. The following function makes concentric
patches with the same output pixel size and different fields of view, given
actual backend downsample factors. It is tested with a small pyramid backend;
registration of real multilevel slides remains user data dependent.

<!-- recipe: concentric-tiles -->
```python
import math
from histolab.types import CoordinatePair

def concentric_tiles(slide, center, tile_size, downsamples, levels):
    width, height = slide.dimensions
    result = []
    for level in levels:
        if level not in slide.levels:
            raise ValueError("Unavailable slide level")
        scale = float(downsamples[level])
        if not math.isfinite(scale) or scale <= 0:
            raise ValueError("Downsample must be positive and finite")
        span_x = round(tile_size[0] * scale)
        span_y = round(tile_size[1] * scale)
        x0 = round(center[0] - span_x / 2)
        y0 = round(center[1] - span_y / 2)
        box = CoordinatePair(x0, y0, x0 + span_x, y0 + span_y)
        if not (0 <= box.x_ul < box.x_br <= width and 0 <= box.y_ul < box.y_br <= height):
            raise ValueError("Requested field of view extends beyond the slide")
        result.append(slide.extract_tile(box, tile_size=tile_size, level=level))
    return result
```

This preserves centers, not equal physical field of view. Equal field of view
requires adjusting output pixel dimensions or explicit resampling. Record any
rounding offset. For independent multilevel datasets, use distinct prefixes or
folders and verify that each level exists before extraction.

## Non-destructive blur QC

OpenCV is optional; this example is illustrative and not exercised by the
Histolab-only suite. Calibrate the threshold for stain, resolution and scanner;
variance of the Laplacian is not a universal clinical quality measure.

```python
from pathlib import Path
from PIL import Image
import cv2
import numpy as np

qc_rows = []
for path in sorted(Path("output/tiles").glob("*.png")):
    with Image.open(path) as image:
        gray = np.asarray(image.convert("L"))
    score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    qc_rows.append({"filename": path.name, "laplacian_variance": score})
# Save/review these scores; retain originals rather than deleting low-score tiles.
```
