# Whole slide and cohort runs

DeepSpot-M predicts per tile. A slide-scale virtual spatial transcriptomics map is a
tiling step, a batched prediction loop, and an assembly step that puts the values back on
the slide grid.

## 1. Pick the level that gives about 20x

Tiles must be 224x224 at roughly 20x, near 0.5 microns per pixel. Read the resolution off
the slide rather than assuming level 0 is 20x, since many scanners write level 0 at 40x:

```python
import openslide

slide = openslide.open_slide("slide.svs")
mpp_x = float(slide.properties.get(openslide.PROPERTY_NAME_MPP_X))
downsamples = slide.level_downsamples

level = min(
    range(slide.level_count),
    key=lambda i: abs(mpp_x * downsamples[i] - 0.5),
)
```

Tile at that level. A slide already scanned at 20x gives level 0; a 40x slide usually
gives level 1.

## 2. Extract a tile grid

Use the `histolab` skill for tiling. A grid tiler at 224x224 with a tissue check covers
the section and skips background:

```python
from histolab.slide import Slide
from histolab.tiler import GridTiler

slide = Slide("slide.svs", processed_path="tiles/")

tiler = GridTiler(
    tile_size=(224, 224),
    level=level,
    check_tissue=True,
    tissue_percent=80.0,
    pixel_overlap=0,
)
tiler.extract(slide)
```

Write a coordinate manifest during extraction with `tile_name,x_coord,y_coord,level`
and document whether coordinates use level-0 or selected-level pixels and tile origins
or centers. The assembly example assumes this explicit schema; do not assume a
`ScoreTiler` scoring report supplies these fields. Preserve tile IDs through batching.

## 3. Predict in batches

Load the model once, then stream tiles through it. Reloading per batch redownloads nothing
but rebuilds the model each time, which dominates the runtime of a slide:

```python
from pathlib import Path

import torch
from PIL import Image
from deepspotm import DeepSpotM

TILE_PX = 224

def require_tile(tile):
    if tile.size != (TILE_PX, TILE_PX):
        raise ValueError(
            f"DeepSpot-M expects a {TILE_PX}x{TILE_PX} tile at about 20x "
            f"(~0.5 microns per pixel); got {tile.size[0]}x{tile.size[1]}."
        )
    return tile.convert("RGB")

def batched(items, size):
    for start in range(0, len(items), size):
        yield items[start : start + size]

device = "cuda" if torch.cuda.is_available() else "cpu"
model, image_processor = DeepSpotM.from_pretrained(
    "ratschlab/DeepSpotM", source="scgpt", device=device
)

genes = ["EPCAM", "CD3D", "PTPRC", "MKI67"]
tile_paths = sorted(Path("tiles/").glob("*.png"))

chunks = []
for paths in batched(tile_paths, 32):
    tiles = [require_tile(Image.open(p)) for p in paths]
    batch = torch.stack([image_processor(t) for t in tiles]).to(device)
    chunks.append(model.predict_genes(batch, genes).cpu())

expression = torch.cat(chunks).numpy()  # tiles by genes, log1p-CPM
```

Batch sizing: start at 32 tiles on a GPU and 8 on CPU. Memory grows with both the batch
size and the number of genes requested in one call, so lower one when the other is large.
Ask for the full gene list in each call rather than looping gene by gene, since the tile
tokens are computed once per batch and reused across gene queries.

## 4. Assemble the slide map

Pair the matrix with the tile coordinates and the gene list. `AnnData` is the natural
container, and it is what spatial analysis tools read:

```python
import anndata as ad
import numpy as np
import pandas as pd

# Manifest produced during extraction: tile_name, x_coord, y_coord, level.
# Coordinate units/origin must be documented by that extraction workflow.
report = pd.read_csv("tiles_report.csv").set_index("tile_name", verify_integrity=True)
tile_names = [path.name for path in tile_paths]  # prediction row order
if len(tile_names) != len(set(tile_names)):
    raise ValueError("Tile filenames must be unique within a slide")
if expression.shape != (len(tile_names), len(genes)):
    raise ValueError("Prediction dimensions do not match tile and gene manifests")
if set(report.index) != set(tile_names):
    raise ValueError("Coordinate manifest must match the predicted tile set exactly")
report = report.loc[tile_names]
coords = report[["x_coord", "y_coord"]].to_numpy(dtype=float)

adata = ad.AnnData(
    X=expression,
    obs=report.copy(),
    var=pd.DataFrame(index=pd.Index(genes, name="gene")),
)
adata.obsm["spatial"] = coords
adata.uns["deepspotm"] = {
    "source": "scgpt",
    "units": "log1p-CPM",
    "tile_px": 224,
    "level": int(level),
}
adata.write_h5ad("slide.h5ad")
```

Recording `source`, `units` and `level` in `uns` keeps the run readable later, and makes it
obvious when two slides were produced under different settings.

## 5. Plot a gene

```python
import matplotlib.pyplot as plt

values = adata[:, "EPCAM"].X.ravel()
plt.scatter(coords[:, 0], -coords[:, 1], c=values, s=6, cmap="viridis")
plt.gca().set_aspect("equal")
plt.colorbar(label="EPCAM (log1p-CPM)")
```

Negating the y coordinate puts the map in slide orientation, since slide coordinates grow
downward.

## 6. Cohort scale

For many slides, run one slide per process and write one `.h5ad` per slide rather than
holding a cohort in memory:

```python
for svs in sorted(Path("cohort/").glob("*.svs")):
    out = Path("out") / f"{svs.stem}.h5ad"
    if out.exists():
        continue          # resume without recomputing finished slides
    run_slide(svs, out)   # steps 1 to 4 above
```

Points worth fixing across a cohort:

- One `source` for every slide, so values stay comparable.
- One gene list, stored in a file and read by every run.
- The same target resolution, chosen per slide from its own metadata.
- A skip-if-exists guard, so an interrupted cohort resumes where it stopped.

Concatenate afterwards with `ad.concat(slides, label="slide_id")` when a cohort-level
matrix is needed. This is the shape of the run that produced the TCGA atlas of 28,664
slides across 32 cancer types.

## Primary sources

- Paper: <https://doi.org/10.64898/2026.06.19.26356060> (medRxiv, posted 22 June 2026)
- Code: <https://github.com/ratschlab/DeepSpotM>
- Weights: <https://huggingface.co/ratschlab/DeepSpotM>
