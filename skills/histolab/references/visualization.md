# Visualization (Histolab 0.7.0)

Matplotlib is optional for these recipes. Histolab's `locate_mask` and
`locate_tiles` return Pillow images; they do not draw into an existing Matplotlib
axes or display a window automatically. Source:
[Slide](https://github.com/histolab/histolab/blob/v0.7.0/histolab/slide.py) and
[Tiler](https://github.com/histolab/histolab/blob/v0.7.0/histolab/tiler.py).

## Save and display previews

```python
from pathlib import Path
import matplotlib.pyplot as plt
from histolab.masks import TissueMask
from histolab.tiler import RandomTiler

output = Path("output/previews")
output.mkdir(parents=True, exist_ok=True)
mask = TissueMask()
tiler = RandomTiler(tile_size=(256, 256), n_tiles=20, seed=42)
mask_preview = slide.locate_mask(mask)
tile_preview = tiler.locate_tiles(slide, extraction_mask=mask)
mask_preview.save(output / "mask.png")
tile_preview.save(output / "tiles.png")
fig, axes = plt.subplots(1, 2, figsize=(12, 6))
axes[0].imshow(mask_preview)
axes[1].imshow(tile_preview)
for ax in axes:
    ax.axis("off")
fig.savefig(output / "previews.png", dpi=150, bbox_inches="tight")
plt.close(fig)
```

Grid and score tilers have the same preview signature; no preview method accepts
`n_tiles`. Set the count in the RandomTiler/ScoreTiler constructor. ScoreTiler
previews rank the full eligible grid even when only a few boxes are shown.

## Correctly align mask overlays

The mask shape can exceed the thumbnail shape in 0.7.0. Resample labels with
nearest-neighbor interpolation and use the same image extent for both layers.

<!-- recipe: mask-overlay -->
```python
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from histolab.masks import TissueMask

def plot_mask_overlay(slide, mask=None):
    mask = TissueMask() if mask is None else mask
    thumbnail = slide.thumbnail
    raw_mask = mask(slide)
    resized = Image.fromarray(raw_mask.astype(np.uint8)).resize(
        thumbnail.size, Image.Resampling.NEAREST,
    )
    labels = np.asarray(resized, dtype=bool)
    fig, ax = plt.subplots()
    ax.imshow(thumbnail)
    ax.imshow(np.ma.masked_where(~labels, labels), cmap="Reds", alpha=0.35, vmin=0, vmax=1)
    ax.set_title("Detected tissue")
    ax.axis("off")
    return fig
```

For custom coordinate overlays, scale X and Y independently from level-0 slide
bounds to the displayed image. Use the actual saved coordinate box width and
height; a fixed 512-pixel box is wrong at other levels or resolutions.

## Tile mosaic (not a spatial reconstruction)

<!-- recipe: mosaic -->
```python
from pathlib import Path
from PIL import Image
import matplotlib.pyplot as plt

def create_tile_mosaic(tile_dir, grid_size=(4, 4), pattern="*.png"):
    rows, columns = grid_size
    if rows <= 0 or columns <= 0:
        raise ValueError("Mosaic dimensions must be positive")
    paths = sorted(Path(tile_dir).glob(pattern))[:rows * columns]
    fig, axes = plt.subplots(rows, columns, figsize=(3 * columns, 3 * rows), squeeze=False)
    for ax in axes.ravel():
        ax.axis("off")
    for ax, path in zip(axes.ravel(), paths):
        with Image.open(path) as tile_image:
            ax.imshow(tile_image.convert("RGB"))
        ax.set_title(path.stem, fontsize=7)
    fig.tight_layout()
    return fig
```

Use a tile filename pattern or a directory containing only tiles so previews
are not counted as samples. Sorted filename order is not slide spatial order.
The function also handles 1x1 grids, empty directories, and fewer files than cells.

## Tile mask visualization

```python
# tile is a Tile returned by slide.extract_tile(...).
import matplotlib.pyplot as plt

tile.calculate_tissue_mask()
fig, axes = plt.subplots(1, 2)
axes[0].imshow(tile.image)
axes[1].imshow(tile.tissue_mask, cmap="gray")
axes[1].set_title(f"Detected tissue: {tile.tissue_ratio:.1%}")
for ax in axes:
    ax.axis("off")
plt.close(fig)
```

Mask fraction is an algorithm-dependent area estimate, not histological cell
fraction. `Tile` construction needs a four-coordinate `CoordinatePair`, as in
the filters reference.

## Score plots and saved tile inspection

Only `filename`, `score` and `scaled_score` are supplied in ScoreTiler CSVs.
There is no `tissue_percent` or `tile_name` column. Use the raw score histogram;
normalized scores can be non-finite when candidate scores are constant and are
not comparable probabilities across slides.

<!-- recipe: score-plot -->
```python
import csv
import math
import matplotlib.pyplot as plt

def plot_score_report(report_path):
    with open(report_path, newline="") as stream:
        rows = list(csv.DictReader(stream))
    scores = [float(row["score"]) for row in rows]
    if not scores or not all(math.isfinite(value) for value in scores):
        raise ValueError("Report needs nonempty, finite raw scores")
    fig, ax = plt.subplots()
    ax.hist(scores, bins=min(20, len(scores)))
    ax.set_xlabel("Raw tile score")
    ax.set_ylabel("Saved tile count")
    return fig
```

To inspect extremes, sort these rows by `float(row["score"])` and open
`Path(slide.processed_path) / row["filename"]`. The report contains only saved
winners: its lowest row may still be high-ranked in the full candidate pool.
Calculate any tissue-coverage scatter data separately with a named algorithm.

## Slide comparisons, figures and PDF reports

For cohort QC, record each slide's mask fraction (`mask.mean() * 100`) alongside
stain, scanner, mask resolution and parameters; differing mask resolution can
change morphology and the resulting fraction. Do not hold all slides open at
once. A high DPI export improves labels but adds no WSI image detail to a small
thumbnail.

<!-- recipe: pdf-preview -->
```python
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

def save_preview_pdf(slide, mask, tiler, path):
    images = [
        ("Slide thumbnail", slide.thumbnail),
        ("Mask", slide.locate_mask(mask)),
        ("Tile positions", tiler.locate_tiles(slide, extraction_mask=mask)),
    ]
    with PdfPages(path) as pdf:
        for title, image in images:
            fig, ax = plt.subplots(figsize=(8, 8))
            ax.imshow(image)
            ax.set_title(title)
            ax.axis("off")
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)
```

This explicitly draws the returned preview on each axes before saving, avoiding
blank tile-location PDF pages. Notebook users may call `display(preview)`.
Optional widget UIs should rebuild a `Compose` chain from `image_filters` when
parameters change; they were not executed in this review.
