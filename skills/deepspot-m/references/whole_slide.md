# Whole-slide and cohort runs

This recipe separates optional **histolab 0.7.0 tiling** (Python 3.10/3.11 and
OpenSlide) from **DeepSpot-M inference** (tested API stack on Python 3.12).
Exchange tiles plus manifests between environments. Install AnnData, NumPy, pandas
and Pillow in the inference environment for export; matplotlib is only needed to plot.
Full WSI extraction and gated inference are illustrative, not an executed clinical
or biological validation. Local synthetic checks cover the boundary logic and export.

## 1. Verify physical resolution

A 224x224 tile at 0.5 microns/pixel spans about 112x112 microns. Do not assume
level 0 is 20x or level 1 is half its resolution: pyramid factors vary by scanner.
Check both axes and reject missing/invalid metadata. This native-level example uses
an explicit 10% engineering tolerance; choose and validate that tolerance for the
study, rather than interpreting it as an established model accuracy guarantee.

```python
import math
import openslide

def select_native_level(properties, downsamples, target=0.5, tolerance=0.10):
    mpp = [float(properties.get(f"openslide.mpp-{axis}", "nan")) for axis in ("x", "y")]
    if not all(math.isfinite(v) and v > 0 for v in mpp):
        raise ValueError("Need verified positive MPP for both slide axes")
    factors = [float(v) for v in downsamples]
    if not factors or not all(math.isfinite(v) and v > 0 for v in factors):
        raise ValueError("Invalid slide pyramid downsample factors")
    level = min(range(len(factors)), key=lambda i: max(
        abs(v * factors[i] / target - 1) for v in mpp
    ))
    actual = [v * factors[level] for v in mpp]
    if any(abs(v / target - 1) > tolerance for v in actual):
        raise ValueError("No matching native level; explicitly resample from finer pixels")
    return level, mpp, actual

with openslide.open_slide("slide.svs") as raw_slide:
    level, level0_mpp, actual_mpp = select_native_level(
        raw_slide.properties, raw_slide.level_downsamples
    )
    level0_dimensions = raw_slide.dimensions
```

If no native level qualifies, stop this recipe and use a separately verified resampling
workflow. Histolab exposes `mpp=...` but that path has additional backend requirements;
it is not exercised here. Record the original metadata, source level, resampling
method and effective MPP. Upsampling coarse pixels cannot recover missing detail.

## 2. Tile and create a coordinate manifest

Use a **new, empty directory per slide/run**; stale PNGs would corrupt assembly.
The tissue mask and 80% tissue threshold are analysis choices: inspect a thumbnail
with tile outlines, especially for small fragments, sparse tissues and artifacts.
The default `BiggestTissueBoxMask` can exclude separate tissue fragments; this
example explicitly requests `TissueMask`.

```python
from pathlib import Path
from histolab.slide import Slide
from histolab.tiler import GridTiler
from histolab.masks import TissueMask

tile_dir = Path("tiles")
tile_dir.mkdir(exist_ok=False)
slide = Slide("slide.svs", processed_path=str(tile_dir))
tiler = GridTiler(
    tile_size=(224, 224), level=level, check_tissue=True,
    tissue_percent=80.0, pixel_overlap=0,
)
tiler.extract(slide, extraction_mask=TissueMask())
```

Released GridTiler 0.7.0 returns `None` and writes coordinate-bearing filenames;
it does not provide a `report_path` argument. Build this explicit manifest from
that documented naming contract. The bounds are in **level-0 pixels**.

```python
import csv
import json
import re

pattern = re.compile(r"tile_\d+_level(\d+)_(\d+)-(\d+)-(\d+)-(\d+)\.png")
rows = []
for path in sorted(tile_dir.glob("*.png")):
    match = pattern.fullmatch(path.name)
    if not match:
        raise ValueError(f"Unexpected GridTiler filename: {path.name}")
    tile_level, x0, y0, x1, y1 = map(int, match.groups())
    if tile_level != level or not (0 <= x0 < x1 <= level0_dimensions[0]
                                   and 0 <= y0 < y1 <= level0_dimensions[1]):
        raise ValueError(f"Invalid level or bounds: {path.name}")
    rows.append([path.name, x0, y0, x1, y1, tile_level])
if not rows:
    raise ValueError("No tissue tiles survived extraction")
with open("tiles_report.csv", "w", newline="", encoding="utf-8") as handle:
    writer = csv.writer(handle)
    writer.writerow(["tile_name", "x0", "y0", "x1", "y1", "level"])
    writer.writerows(rows)
Path("tiling.json").write_text(json.dumps({
    "slide_id": "slide", "level": level, "level0_mpp": level0_mpp,
    "actual_mpp": actual_mpp, "coordinate_units": "level0_pixels",
    "bounds_origin": "upper_left", "tile_px": 224,
    "tissue_mask": "TissueMask", "tissue_percent": 80.0,
}), encoding="utf-8")
```

## 3. Predict in the inference environment

Use the same gene order throughout. Start with a small batch; scale only after
measuring memory for the actual gene count. This in-memory example suits marker
panels/modest slides. A full-transcriptome WSI may require chunked persistence;
`torch.cat` temporarily duplicates stored expression chunks.

```python
from pathlib import Path
import json
import torch
from PIL import Image
from deepspotm import DeepSpotM

metadata = json.loads(Path("tiling.json").read_text(encoding="utf-8"))
tile_paths = sorted(Path("tiles").glob("*.png"))
if not tile_paths:
    raise ValueError("No input tiles")
genes = ["EPCAM", "CD3D", "PTPRC", "MKI67"]
source = "scgpt"
revision = "48be27af436a50e5c74175680ac2b7b2596a506b"
device = "cuda" if torch.cuda.is_available() else "cpu"
model, image_processor = DeepSpotM.from_pretrained(
    "ratschlab/DeepSpotM", source=source, device=device, revision=revision
)
if not genes or len(genes) != len(set(genes)) or not set(genes) <= set(model.gene_names):
    raise ValueError("Use unique genes from the loaded panel")

chunks = []
batch_size = 4
for start in range(0, len(tile_paths), batch_size):
    paths = tile_paths[start:start + batch_size]
    tensors = []
    for path in paths:
        with Image.open(path) as tile:
            if tile.size != (224, 224):
                raise ValueError(f"Wrong tile dimensions: {path.name}")
            tensors.append(image_processor(tile.convert("RGB")))
    batch = torch.stack(tensors).to(device)
    values = model.predict_genes(batch, genes).cpu()
    if values.shape != (len(paths), len(genes)) or not torch.isfinite(values).all():
        raise ValueError("Unexpected prediction shape or nonfinite values")
    chunks.append(values)
expression = torch.cat(chunks).numpy()  # tiles x genes, predicted log1p-CPM
```

## 4. Assemble and write the slide map

Join by tile ID, validate exact coverage, and store **tile centers** rather than
silently mixing origin/center coordinates. Inspect the raw CSV header before pandas
can rename duplicates. This block continues from step 3.

```python
import csv
import anndata as ad
import numpy as np
import pandas as pd

with open("tiles_report.csv", newline="", encoding="utf-8") as handle:
    header = next(csv.reader(handle))
if header != ["tile_name", "x0", "y0", "x1", "y1", "level"]:
    raise ValueError("Unexpected or duplicated manifest columns")
report = pd.read_csv("tiles_report.csv", dtype={"tile_name": str}).set_index(
    "tile_name", verify_integrity=True
)
tile_names = [path.name for path in tile_paths]
if len(tile_names) != len(set(tile_names)) or set(report.index) != set(tile_names):
    raise ValueError("Manifest must match unique predicted tile IDs exactly")
if expression.shape != (len(tile_names), len(genes)) or not np.isfinite(expression).all():
    raise ValueError("Invalid prediction matrix")
report = report.loc[tile_names]
boxes = report[["x0", "y0", "x1", "y1"]].to_numpy(dtype=float)
if not np.isfinite(boxes).all() or (boxes < 0).any() or (boxes[:, 2:] <= boxes[:, :2]).any():
    raise ValueError("Invalid coordinate bounds")
if not (report["level"] == metadata["level"]).all():
    raise ValueError("Manifest and tiling metadata levels disagree")
coords = (boxes[:, :2] + boxes[:, 2:]) / 2
adata = ad.AnnData(
    X=expression, obs=report.copy(),
    var=pd.DataFrame(index=pd.Index(genes, name="gene")),
)
adata.obsm["spatial"] = coords
adata.uns["deepspotm"] = {
    **metadata, "source": source, "model_repo": "ratschlab/DeepSpotM",
    "revision": revision, "package_version": "1.0.0", "units": "log1p-CPM",
    "measurement_type": "model_prediction", "spatial_origin": "tile_center",
}
output = Path("slide.h5ad")
temporary = output.with_name(output.stem + ".partial.h5ad")
adata.write_h5ad(temporary)
check = ad.read_h5ad(temporary)
if check.shape != adata.shape or list(check.obs_names) != tile_names:
    raise ValueError("H5AD verification failed")
temporary.replace(output)
```

A successful write is structural evidence only. Inspect image/map alignment and
validate prediction performance against held-out paired assays. Do not treat these
values as observed counts, and do not log-normalize them again. Negative predictions
are possible; report any transformations rather than silently clipping them.

## 5. Plot and scale to cohorts

```python
import matplotlib.pyplot as plt

values = np.asarray(adata[:, "EPCAM"].X).ravel()
plt.scatter(coords[:, 0], coords[:, 1], c=values, s=6, cmap="viridis")
plt.gca().invert_yaxis()
plt.gca().set_aspect("equal")
plt.colorbar(label="Predicted EPCAM (log1p-CPM)")
```

For cohorts, reuse one loaded model per inference worker and write one verified
H5AD per slide. Resume only after checking the saved shape, IDs and run provenance
(model revision, source, genes, tile/slide identity, MPP and preprocessing), not
merely the existence of a file. Avoid one process per slide sharing a single GPU
without an explicit memory/concurrency plan.

If combining slides, `ad.concat({slide_id: data, ...}, label="slide_id",
index_unique="::", join="inner")` supplies a slide label and unique observation IDs.
Check that all input gene lists match first; preserve per-slide provenance separately
because default `uns` merging does not retain it. Spatial coordinates remain local to
each slide: build spatial neighbor graphs separately rather than placing different
slides into one coordinate system. Split validation by patient/slide, not by tile.
The released base model differs from the cancer-specific fine-tuned models used for
the reported TCGA atlas; this recipe does not reproduce that atlas by itself.

## Primary sources

- [DeepSpot-M source and release context](https://github.com/ratschlab/DeepSpotM)
- [Upstream WSI example](https://github.com/ratschlab/DeepSpotM/blob/4d7793c890c500f51033444cc755f02b9d523628/examples/predict_wsi.py)
- [Histolab released metadata](https://pypi.org/pypi/histolab/0.7.0/json)
- [Histolab GridTiler reference](https://histolab.readthedocs.io/en/latest/api/tiler.html)
- [OpenSlide Python](https://openslide.org/api/python/)
- [AnnData](https://anndata.readthedocs.io/en/stable/generated/anndata.AnnData.html)
- [AnnData concatenation](https://anndata.readthedocs.io/en/stable/generated/anndata.concat.html)
