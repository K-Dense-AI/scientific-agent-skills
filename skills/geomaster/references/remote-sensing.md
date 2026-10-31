# Remote sensing

Reviewed 2026-10-01. Local arithmetic is tested with synthetic rasters. Catalog
metadata was probed; authenticated Earth Engine execution and real-scene scientific
validation remain illustrative. [Source ledger](review.md) records the distinction.

## Missions and product choice

Sentinel-2 optical bands span 10/20/60 m; L2A surface reflectance has no B10.
Landsat 8/9 optical and thermal products have different native supports even when
published on a common grid. MODIS supports range from 250 m to 1 km. Sentinel-1
resolution/revisit depends on constellation, mode and product. Envisat is archival.
PlanetScope and WorldView access/resolution depend on licensed product. Always
select a product/version before treating a marketing resolution as pixel accuracy.

## Sentinel-2 with STAC

Use the bounded search in [data-sources.md](data-sources.md). Earth Search uses
`red`, `nir`, `scl`; Planetary Computer uses `B04`, `B08`, `SCL`; CDSE distinguishes
asset resolution (such as `B04_10m`). Do not assume those asset names are interchangeable.
Inspect `raster:bands`, product XML and the processing baseline: the live Earth Search
2023 item in this review reported scale 0.0001 and offset -0.1. The corresponding
Planetary Computer asset did not expose `raster:bands`, so its calibration must be
resolved from product metadata; a missing offset is not evidence of zero offset.

This illustrative loader requires selected, verified items and explicit calibration:

```python
import odc.stac

# `items` comes from a bounded Planetary Computer search.
# Pixel acquisition is lazy and restricted to this small bbox.
data = odc.stac.load(items, bands=['B04', 'B08', 'SCL'],
    bbox=[-122.405, 37.700, -122.400, 37.705],
    crs='EPSG:32610', resolution=10,
    chunks={'x': 256, 'y': 256},
    resampling={'B04': 'bilinear', 'B08': 'bilinear', 'SCL': 'nearest'})
valid = data.SCL.isin([4, 5, 6]) & (data.B04 != 0) & (data.B08 != 0)
# Read scale/offset per selected product; do not assume odc.stac applied them.
# For products with different calibration, calibrate each scene before compositing.
```

SCL 4/5/6 keeps vegetation/bare soil/water conservatively. Other studies may retain
class 2/7 or snow; state the rule. SCL is 20 m, so nearest-neighbor resampling to 10 m
does not create 10 m cloud information. QA60 is masked for 2022-01-25 through
2024-02-28 in the Earth Engine harmonized archive and is not suitable for that interval.

## Spectral indices

Use `spectral_indices` from the bundled raster helper on aligned, QA-masked physical
reflectance. NBR conventionally uses SWIR2 (Sentinel B12), while NDBI/MNDWI use SWIR1
(B11). NDWI here means the green/NIR McFeeters definition, not the NIR/SWIR moisture
index. An index threshold is a candidate mask requiring field/independent validation.

```python
from raster_workflows import spectral_indices
# Six arrays with known reflectance units and identical spatial grid:
indices = spectral_indices(blue, green, red, nir, swir1, swir2)
```

Avoid unsigned subtraction, arbitrary epsilon denominators and `nan_to_num` on
science outputs. A zero NDVI is a valid observation, not a nodata sentinel.

## Earth Engine Sentinel time series

Authenticate once, initialize a registered project, and use the collection's documented
band names (`B4`, not `B04`). The following is a credential-dependent template:

```python
import ee
import pandas as pd
# ee.Authenticate()  # interactive setup, then persist credentials securely
ee.Initialize(project='your-registered-project')
roi = ee.Geometry.Point([-122.4, 37.7]).buffer(1000)

def prepare_s2(image):
    scl = image.select('SCL')
    keep = scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6))
    red = image.select('B4').multiply(0.0001)
    nir = image.select('B8').multiply(0.0001)
    ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI')
    return ndvi.updateMask(keep.And(nir.add(red).neq(0))).copyProperties(
        image, ['system:time_start'])

images = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
          .filterBounds(roi).filterDate('2023-06-01', '2023-07-01')
          .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)).map(prepare_s2))

def summarize(image):
    summary = image.reduceRegion(reducer=ee.Reducer.mean(), geometry=roi,
                                 scale=10, maxPixels=1000000)
    return ee.Feature(None, {'date': image.date().format('YYYY-MM-dd'),
                             'ndvi': summary.get('NDVI')})

# Small bounded interval only. Export a table for large series.
series = ee.FeatureCollection(images.map(summarize)).getInfo()
df = pd.DataFrame([f['properties'] for f in series['features']])
```

The end date is exclusive; keep null reductions and observation counts rather than
imputing zero. Mean over the ROI is different from sampling its centroid. Cloud/QA
masking changes spatial support across dates. `getInfo` downloads results synchronously.
Export construction is not execution: call `task.start()` only when the user intends
to create the remote output, then inspect completion/error status.

## Landsat Collection 2 surface reflectance and temperature

The `LANDSAT/LC08/C02/T1_L2` product supplies calibrated surface temperature after
`ST_B10 * 0.00341802 + 149.0` (Kelvin); subtract 273.15 for Celsius. Do not apply
another brightness-temperature/emissivity correction to this surface-temperature
product. Some L2SR images have masked thermal bands; require `PROCESSING_LEVEL=L2SP`
for temperature analysis and inspect ST QA/emissivity gaps.

```python
def prepare_landsat(image):
    # QA_PIXEL bits 0..5: fill, dilated cloud, cirrus, cloud, shadow, snow.
    keep = image.select('QA_PIXEL').bitwiseAnd(63).eq(0).And(
        image.select('QA_RADSAT').eq(0))
    sr = image.select('SR_B.').multiply(0.0000275).add(-0.2)
    red, nir = sr.select('SR_B4'), sr.select('SR_B5')
    ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI')
    ndvi = ndvi.updateMask(nir.add(red).neq(0))
    temperature = image.select('ST_B10').multiply(0.00341802).add(149).subtract(273.15).rename('LST_C')
    return image.addBands(sr, overwrite=True).addBands([ndvi, temperature]).updateMask(keep)
```

Earth Engine `normalizedDifference` masks pixels with negative input bands; this
can silently drop valid low-reflectance Collection 2 pixels after its -0.2 offset.
Explicit arithmetic makes that choice visible; handle physically implausible values
with a documented QC rule rather than silently clipping them.

## SAR

Determine whether the input is raw amplitude, intensity, calibrated linear sigma0,
gamma0, or dB before arithmetic. A raw GRD product needs calibration/geocoding and
terrain handling, not merely `10*log10(DN)`. Earth Engine `COPERNICUS/S1_GRD` is already
calibrated and terrain-corrected in dB; `S1_GRD_FLOAT` is linear power.

```python
import numpy as np

def power_to_db(power):
    power = np.ma.asarray(power, dtype='float64').filled(np.nan)
    out = np.full(power.shape, np.nan)
    np.log10(power, out=out, where=np.isfinite(power) & (power > 0))
    return 10 * out
```

For positive linear power, VV/VH becomes `VV_dB - VH_dB`. Dual-polarization
`4*VH/(VV+VH)` is a radar vegetation proxy, not calibrated biomass or soil moisture.
Speckle filtering must use a named implementation validated on linear power and
respect masks/edges. The former Gaussian “Lee approximation” was not a valid Lee
filter and is intentionally not retained as production code. Match orbit direction,
relative orbit, polarization and incidence angle when comparing acquisitions.

## Hyperspectral

`spectral.io.envi.open(header)` loads ENVI metadata; `.load()` materializes the cube
as rows, columns, bands. Verify wavelength units, monotonicity, bad-band flags,
reflectance scaling and nodata. A red-edge derivative needs wavelength spacing:

```python
import numpy as np

def red_edge_position(cube, wavelengths_nm):
    cube = np.ma.asarray(cube, dtype=float).filled(np.nan)
    wave = np.asarray(wavelengths_nm, dtype=float)
    if cube.ndim != 3 or cube.shape[-1] != wave.size or wave.size < 2:
        raise ValueError('Cube bands must match wavelength coordinates')
    if not np.isfinite(wave).all() or not np.all(np.diff(wave) > 0):
        raise ValueError('Wavelengths must be finite and strictly increasing')
    keep = np.flatnonzero((wave >= 680) & (wave <= 750))
    if keep.size < 2:
        raise ValueError('At least two red-edge bands are required')
    derivative = np.gradient(cube, wave, axis=-1)[..., keep]
    valid = np.isfinite(derivative).all(axis=-1)
    index = np.argmax(np.where(np.isfinite(derivative), derivative, -np.inf), axis=-1)
    return np.where(valid, wave[keep[index]], np.nan)
```

This estimates the sampled derivative maximum, not sub-band spectral precision.

## Atmospheric correction and pan-sharpening

Py6S requires the external 6S executable, measured geometry/atmosphere, a selected
spectral response and `s.atmos_corr = AtmosCorr.AtmosCorrLambertianFromRadiance(radiance)`
before a correction run. Coefficients act on radiance in the modeled units, not raw
DN. Calibrate first, and inspect correction outputs; a default `SixS().run()` is not
a sensor-specific surface-reflectance retrieval.

Pan-sharpening requires a real overlapping panchromatic band and grid/PSF alignment.
Sentinel-2 has no panchromatic band. Do not call an arbitrary per-band contrast
injection “Gram-Schmidt”; use a validated implementation and test spectral distortion.

Sources: [Sentinel-2 catalog](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED),
[Landsat L2](https://developers.google.com/earth-engine/datasets/catalog/LANDSAT_LC08_C02_T1_L2),
[normalizedDifference](https://developers.google.com/earth-engine/apidocs/ee-image-normalizeddifference),
[ODC loader](https://odc-stac.readthedocs.io/en/latest/_api/odc.stac.load.html),
[Sentinel-1 processing](https://developers.google.com/earth-engine/guides/sentinel1),
[Py6S parameters](https://py6s.readthedocs.io/en/latest/params.html).
