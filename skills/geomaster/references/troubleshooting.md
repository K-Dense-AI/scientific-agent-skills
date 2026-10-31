# GeoMaster troubleshooting

Reviewed 2026-10-01. Diagnose the specific contract before changing data. Preserve
original inputs and report excluded/changed records.

## Installation and ABI

Use one coherent wheel or conda-forge stack. Rasterio wheels bundle GDAL; they do
not supply `from osgeo import gdal` or every native driver. Building GDAL bindings
requires compatible native GDAL and headers. Avoid unverified third-party wheel
indexes or mixing independently built GEOS/GDAL/PROJ binaries into one environment.
Use the official package installation guides and capture actual runtime versions.

```python
import sys, rasterio, geopandas, pyproj
print(sys.version)
print('GeoPandas', geopandas.__version__)
print('Rasterio', rasterio.__version__, 'GDAL', rasterio.__gdal_version__)
print('PyProj', pyproj.__version__, 'PROJ', pyproj.proj_version_str)
```

`gdal.VersionInfo('PROJ')` is not the way to query the PROJ version.
QGIS/ArcPy/GRASS need their application environment; `pip install` is not a substitute
for native runtime initialization or a licensed ArcGIS installation.

## CRS and units

- Unknown CRS: retrieve authoritative metadata. Plausible lon/lat bounds do not prove
  EPSG:4326, and `estimate_utm_crs()` cannot infer an unknown source CRS.
- `set_crs` assigns a label without moving points; `to_crs` transforms known coordinates.
- Use `Transformer.from_crs(..., always_xy=True)` for explicit x/y order and
  `errcheck=True` for failures. `always_z` is not a Transformer option.
- `GeoDataFrame.to_crs` has no `geometry_precision` argument. Simplification/precision
  reduction changes geometry and must be an explicit separate operation in known units.
- Check area of use, units, datum epochs and transformation grids. A round trip is a
  numerical consistency check, not proof of geographic accuracy.

```python
from pyproj import Transformer, Geod

forward = Transformer.from_crs(4326, 32610, always_xy=True)
inverse = Transformer.from_crs(32610, 4326, always_xy=True)
x, y = forward.transform(-122.4, 37.7, errcheck=True)
lon2, lat2 = inverse.transform(x, y, errcheck=True)
_, _, roundtrip_metres = Geod(ellps='WGS84').inv(-122.4, 37.7, lon2, lat2)
assert roundtrip_metres < 0.001
```

Do not measure geographic-coordinate `.distance()` then print the degree result as metres.

## Geometry failures

```python
report = {'missing': int(gdf.geometry.isna().sum()),
          'empty': int(gdf.geometry.is_empty.sum()),
          'invalid': int((~gdf.geometry.is_valid & gdf.geometry.notna()).sum()),
          'types': gdf.geom_type.value_counts().to_dict()}
repaired = gdf.copy()
repaired.geometry = repaired.geometry.make_valid()
```

Inspect the repair: it can split polygons or produce GeometryCollections/lines.
Compare area/type/count against the original and retain failed features separately.
`buffer(0)` is not a guaranteed equivalent repair. Missing and empty geometries are
different; `.is_empty` does not identify every null geometry. `.x`/`.y` apply to
points, not arbitrary polygons/lines.

Spatial join predicates encode meaning: `within` excludes boundary points,
`intersects` includes them. Nearest joins need suitable projected units and may return
multiple equidistant matches. Indexing accelerates candidates but does not fix wrong
CRS or unwanted duplicate matches.

## Memory and storage

Read windows or use `rioxarray.open_rasterio(..., chunks=...)`. Dask has no
`array.from_rasterio`. A lazy object can still force a full in-memory array via
`.values`, `.compute()` or output drivers. Bound spatial extent as well as chunk size.
Global statistics and focal filters must be independent of arbitrary chunk boundaries.

Rasterio mask/crop returns a new affine transform. Update height/width/transform
when writing cropped/resampled data. Store arrays as `(bands, rows, columns)`;
`dst.write(array, 1)` expects a 2D single-band array, while `dst.write(array)` expects
3D. Update dtype/count/nodata together. Categorical outputs must not inherit NaN
nodata in an integer dtype or a reflectance nodata code that collides with a class.

Compression and tiling do not certify a COG. Use the COG driver or rio-cogeo, then
validate. Zarr v3 removed `DirectoryStore`; use `LocalStore` or an Xarray path with
explicit format. In GeoParquet, pandas `index=True` is not a spatial index.

## Optical/SAR data

Band positions are not universal Sentinel names. Inspect descriptions/assets and
record the stack manifest. Separate optical DN calibration from SCL categorical
codes; do not scale QA bands. Apply product-specific additive offsets before ratios,
and physical reflectance before EVI/SAVI. Unsigned subtraction can wrap.

```python
import numpy as np
# NumPy SCL array: invalid is True for the listed classes.
invalid = np.isin(scl_array, [0, 1, 3, 8, 9, 10])
# Earth Engine equivalent uses image remap or explicit comparisons, not .isin().
keep = scl_image.eq(4).Or(scl_image.eq(5)).Or(scl_image.eq(6))
clean = ee_image.updateMask(keep)
```

Decide separately how to treat dark/unclassified/snow cells. Scene cloud percentage
is not a per-pixel mask. QA60 has a documented historical gap in harmonized S2 SR;
use SCL or a suitable supported cloud product for that interval.

SAR dB inputs must not be passed through `10*log10` again. Calibrate raw inputs before
linear power ratios; handle nonpositive/masked cells. A VV/VH ratio is not a measured
soil-moisture fraction.

## API and result debugging

- Empty STAC search: inspect bbox order, dates, collection IDs, item geometry and
  filter extension support. Use `.items()`; `limit` is a page size.
- Expired Planetary Computer URLs: re-sign near access time; retain unsigned item
  provenance. Missing calibration metadata requires product-level verification.
- Earth Engine: authenticate, register/initialize the correct project, keep server-side
  objects server-side, and inspect export task status. Constructor success is not output.
- CDS: current PAT configuration and dataset terms are required. Use `data_format`
  and the download form's current generated request.
- Google geocoder: HTTP200 with non-OK JSON status is a service error/empty result,
  not a usable first location. Keep ambiguity rather than silently selecting a result.
- OSM services: comply with documented use limits and identity; do not retry tight
  loops or mistake timeout/partial results for a complete AOI.

See [data-sources.md](data-sources.md) for reviewed endpoints and official links;
[core-libraries.md](core-libraries.md) for current local APIs.
