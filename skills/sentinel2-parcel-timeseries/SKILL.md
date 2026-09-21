---
name: sentinel2-parcel-timeseries
description: Builds per-parcel Sentinel-2 L2A time series from field polygons (GeoJSON, KML, GeoPackage) via the Microsoft Planetary Computer STAC API, with SCL cloud masking, the processing-baseline +1000 offset, overlapping-tile deduplication and per-parcel clear-fraction rules, then validates pixel models trained on parcel labels with leave-one-parcel-out, parcel-level AUC, permutation tests and a pre-sowing negative control. Use for crop monitoring, NDVI or reflectance curves per field, crop disease or stress detection, yield or crop-type studies with field observations, weak labels, or whenever satellite pixels inherit a parcel label and spatial leakage must be avoided.
license: MIT
compatibility: Requires Python 3.10+ with numpy, pandas, geopandas, rasterio, pystac-client, planetary-computer, stackstac and scikit-learn. Extraction needs network access to planetarycomputer.microsoft.com (no account or key).
metadata:
  version: "1.0"
  skill-author: Brice Zemba
  last-reviewed: "2026-09-21"
---

# Sentinel-2 parcel time series

Turn field polygons into clean Sentinel-2 time series, one value per parcel and date, and
evaluate models on them without the spatial leakage that makes small agricultural data sets
look better than they are.

## When to use

- A user has parcel or field outlines and wants NDVI or reflectance curves over a season.
- Field observations exist per parcel (disease score, yield class, crop type) and a model is
  trained on satellite pixels that inherit the parcel label.
- A reported accuracy on such data needs checking: split by pixel, AUC over pixels, no control
  for site or management effects.

Not for: land-cover mapping of whole regions without parcels, Sentinel-1 radar processing, or
image-level deep learning (see the `geomaster` skill for general geospatial and remote sensing
work).

## Tested environment

Scripts and examples were run on 2026-09-21 with Python 3.12.10, numpy 2.4.1, pandas 2.2.3,
geopandas 1.1.3, shapely 2.1.2, pyproj 3.7.2, rasterio 1.5.0, xarray 2026.4.0,
pystac-client 0.9.0, planetary-computer 1.0.0, stackstac 0.5.1 and scikit-learn 1.6.1.

```bash
uv pip install numpy pandas geopandas rasterio xarray pystac-client planetary-computer \
    stackstac scikit-learn
```

## Workflow

1. **Check the polygons first.** Read them, project to UTM, compare polygon areas with declared
   areas and look for oversized or merged parcels. Most wrong curves come from wrong outlines.
   See [references/parcel-geometry.md](references/parcel-geometry.md).
2. **Extract clean series** with `scripts/s2_parcel_timeseries.py`. It keeps one MGRS tile,
   one scene per date, converts digital numbers to reflectance with the right offset per scene,
   masks pixels with SCL (classes 4 and 5 kept) and drops a parcel on a date when less than
   60 % of its pixels are clear.
3. **Inspect the curves** per parcel before modelling: season shape, sowing and harvest dates,
   isolated drops (haze missed by SCL), parcels with too few dates.
4. **Build features** per pixel or per parcel (monthly medians, phenology metrics), keeping the
   parcel identifier and the field label on every row.
5. **Validate at parcel level** with `scripts/parcel_group_cv.py`: leave one parcel out,
   average probabilities per parcel, parcel AUC, permutation p-value, leaky split for contrast.
6. **Run the negative control**: the same protocol on features from before sowing. A high AUC
   there means labels are predictable from the site, not from the crop.
7. **Report** parcels per class, the split, parcel AUC with its p-value, the negative control and
   the spread over seeds. See [references/validation-protocol.md](references/validation-protocol.md).

## Rules that prevent silent errors

| Trap | Consequence | Rule |
|---|---|---|
| Baseline 04.00 offset (from 25 January 2022) | NDVI compressed (0.71 read as 0.45), fake step in multi-year series | reflectance = (DN - 1000) / 10000 when baseline >= 04.00, else DN / 10000 |
| Overlapping MGRS tiles | every date twice at tile edges | keep one `s2:mgrs_tile` |
| DN 0 | read as black pixels | treat as no-data |
| Clouds and shadows | drops and spikes in curves | keep SCL 4 and 5, require a minimum clear fraction per parcel |
| Pixels split at random | parcels in train and test, inflated AUC | split by parcel (LeaveOneGroupOut, GroupKFold) |
| Pixel-level metrics | sample size counted in pixels | aggregate to parcels, report the number of parcels |
| Site or management confound | model predicts the block, not the condition | negative control on a pre-sowing window |
| One lucky seed | unstable AUC reported as a result | several seeds, report mean and range |

Details and the SCL class table: [references/sentinel2-data.md](references/sentinel2-data.md).

## Examples

### Extract per-parcel series

```bash
python scripts/s2_parcel_timeseries.py fields.geojson --id-column parcel_id \
    --start 2024-05-01 --end 2024-06-30 --assets B04 B08 --time-chunk 5 \
    --out parcel_timeseries.csv --pixel-out pixels.npz
```

Observed on two 5 ha test parcels in the Gharb plain (Morocco):

```text
18 scenes on tile 29SQU (2024-05-01 to 2024-06-30)
1015 parcel pixels x 18 dates -> pixels.npz
23 rows (2 parcels) -> parcel_timeseries.csv
```

The CSV has one row per kept parcel and date: `parcel_id`, `date`, `tile`, `n_pixels`,
`n_clear`, `clear_fraction`, `<band>_mean`, `ndvi_mean`, `ndvi_median`, `ndvi_std`. Dates where
a parcel is cloudy are absent for that parcel, so series have different lengths. Use
`--tile 30STD` to force a tile, `--min-clear` to change the clear-fraction rule and a smaller
`--time-chunk` when memory is short. Over June 2024, the same 13 parcel-dates extracted from
the two overlapping tiles differed by 0.0017 NDVI on average.

`pixels.npz` holds `X` (pixels, dates, bands) in reflectance with NaN where a pixel is not clear,
`parcel_id` per pixel, `dates` and `bands`.

### Monthly features per pixel

```python
import warnings

import numpy as np
import pandas as pd

d = np.load("pixels.npz")
X, bands = d["X"], list(d["bands"])
red, nir = X[..., bands.index("B04")], X[..., bands.index("B08")]
with np.errstate(divide="ignore", invalid="ignore"):
    vi = (nir - red) / (nir + red)
months = pd.to_datetime(d["dates"]).month
with warnings.catch_warnings():  # all-NaN months give NaN, filled later by the CV script
    warnings.simplefilter("ignore", RuntimeWarning)
    feat = pd.DataFrame({f"ndvi_m{m:02d}": np.nanmedian(vi[:, months == m], axis=1)
                         for m in sorted(set(months))})
feat.insert(0, "parcel_id", d["parcel_id"])
field_labels = {"A": 1, "B": 0}          # parcel-level field observations
feat["label"] = feat["parcel_id"].map(field_labels)
feat.to_csv("pixels.csv", index=False)
```

### Validate at parcel level

```bash
python scripts/parcel_group_cv.py pixels.csv --group-col parcel_id --label-col label \
    --features "^ndvi_m" --model logistic --permutations 200 --compare-leaky
```

The script refuses fewer than two parcels per class, since leaving out the only parcel of a
class leaves a single-class training set. To see why the protocol matters, run the synthetic
demonstration, where features identify parcels but labels are random:

```bash
python scripts/parcel_group_cv.py --demo --permutations 30
```

```text
parcel_auc_leave_one_parcel_out: 0.094
parcel_auc_random_pixel_split_LEAKY: 1.0
permutation_p_value: 0.9677
```

A random pixel split scores 1.0 on pure noise. Random forests with permutations take a few
minutes (about 4 minutes for this demo on a laptop); use `--model logistic` to iterate faster.

### Negative control

```bash
python scripts/parcel_group_cv.py pixels.csv --group-col parcel_id --label-col label \
    --features "_m0[34]$" --model logistic --permutations 200
```

Here only March and April features are used, before sowing for a summer crop. Adapt the
pattern to the crop calendar of the site.

## Scripts

| Script | Purpose |
|---|---|
| `scripts/s2_parcel_timeseries.py` | STAC search, tile and date deduplication, reflectance conversion, SCL mask, per-parcel stats (CSV) and per-pixel series (`.npz`) |
| `scripts/parcel_group_cv.py` | leave-one-parcel-out, parcel AUC, permutation test, leaky-split comparison, synthetic demo |

The pure functions (`to_reflectance`, `clear_mask`, `ndvi`, `choose_tile`,
`one_item_per_date`, `parcel_stats`, `parcel_table`, `parcel_auc`, `leave_one_parcel_out`) can
be imported and reused in a notebook.

## References

- [references/sentinel2-data.md](references/sentinel2-data.md): assets and resolutions, DN to
  reflectance, overlapping tiles, SCL classes, memory.
- [references/parcel-geometry.md](references/parcel-geometry.md): reading polygons, area checks,
  edge pixels, vegetation masks that empty parcels.
- [references/validation-protocol.md](references/validation-protocol.md): weak labels, parcel
  AUC, leakage demonstration, negative control, seed variance, reporting checklist.

Upstream documentation:

- Planetary Computer Sentinel-2 L2A dataset:
  <https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a>
- pystac-client: <https://pystac-client.readthedocs.io/en/stable/>
- stackstac: <https://stackstac.readthedocs.io/en/latest/>
- scikit-learn group-aware cross-validation:
  <https://scikit-learn.org/stable/modules/cross_validation.html#group-k-fold>
- Agent Skills specification: <https://agentskills.io/specification>
