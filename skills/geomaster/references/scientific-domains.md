# Scientific domain workflows

These are domain-specific workflows and illustrative recipes, not calibrated
predictive models. Inputs must have known spatial/temporal support, units, masks and
provenance. See [review.md](review.md) for execution boundaries.

## Marine and coastal

For coastal vulnerability, align DEM/bathymetry, shoreline, wave statistics and
sea-level scenarios to compatible horizontal/vertical datums. State whether height
is orthometric, ellipsoidal or tide-referenced. Define exposure and vulnerability
separately; arbitrary weighted overlays do not estimate inundation probability.
Sensitivity-test any expert weights and validate against independent coastal events.

Benthic habitat mapping combines bathymetry, backscatter, slope/rugosity and labeled
surveys. Derive slope using physical cell dimensions. Backscatter depends on sensor,
incidence angle and calibration; thresholds such as -15 dB are not portable habitat
labels. Use spatially withheld surveys and class uncertainty, and keep unsurveyed or
out-of-domain cells explicitly unknown. CHM-style DSM-minus-DEM processing is not
substitute bathymetric datum reconciliation.

## Atmospheric and climate data

ERA5 2 m temperature is Kelvin; convert to Celsius for that variable. Total
precipitation accumulation has dataset-specific time support and units. Summing
hourly temperature or already accumulated precipitation produces invalid metrics.
Inspect coordinates before slicing: ERA5 latitude often decreases, and current files
may use `valid_time` rather than `time`.

```python
import xarray as xr

def subset_temperature(ds, west, south, east, north):
    latitude = ds.latitude
    bounds = slice(north, south) if latitude[0] > latitude[-1] else slice(south, north)
    roi = ds.sel(latitude=bounds, longitude=slice(west, east))
    time = 'valid_time' if 'valid_time' in roi.coords else 'time'
    # This recipe assumes longitude convention already matches the bbox.
    return (roi.t2m - 273.15).resample({time: 'MS'}).mean()
```

Do not label a z-score of rainfall as SPI. SPI requires a documented accumulation
window, reference climatology, fitted distribution including zero precipitation,
seasonal handling and out-of-sample validation. For rasters, select a single time,
set spatial dimensions/CRS from metadata and preserve nodata before `rio.to_raster`.

For PM2.5 kriging, transform sensors to a justified metric CRS first; `1000` means
metres only in that coordinate system. Check station calibration/time alignment,
variogram fit, duplicate coordinates, spatial holdouts and uncertainty. Use
`OrdinaryKriging(..., coordinates_type='euclidean')` on projected coordinates;
geographic mode has different longitude/latitude assumptions. Kriging variance is
conditional on the fitted covariance model, not all measurement/model uncertainty.

## Hydrology

1. Select a hydrologically appropriate DEM with known vertical/horizontal units;
   assess voids, artifacts, bridges/culverts and true depressions.
2. Choose justified filling/breaching, then a named D8 or MFD implementation.
   D8 compares elevation drop divided by neighbour distance, including diagonals.
3. Compute accumulation and retain its units (cells versus contributing area).
4. Snap the outlet to a justified stream cell, preserving original and snapped
   locations. `rasterio.transform.rowcol(transform, x, y)` returns row,column;
   applying the inverse affine directly yields column,row.
5. Delineate and verify basin closure/connectivity, known hydrography and edge effects.

Use established hydrology implementations rather than an incomplete homemade D8 loop.
For an initialized GRASS location/mapset with matching projected DEM (illustrative):

```python
import grass.script as gs
gs.run_command('g.region', raster='dem', align='dem')
gs.run_command('r.watershed', elevation='dem', accumulation='accumulation',
               drainage='drainage', threshold=1000, flags='s')
# flags='s' selects single-flow-direction; threshold is a model choice, not universal.
```

Inspect GRASS drainage conventions before supplying directions to another tool.
The [r.watershed manual](https://grass.osgeo.org/grass-stable/manuals/r.watershed.html)
describes its depression/edge treatment and output meaning.

A flat-water “bathtub” map is only a screening scenario. It requires a water level
in the DEM's vertical datum and a source-connectivity model; it does not estimate a
return period, velocity, drainage response or hydraulic hazard. Validate against
calibrated hydrodynamic modeling and observations before any operational use.

## Agriculture

For crop condition, compare QA-masked NDVI/EVI time series to a locally matched crop,
phenological stage and historical baseline. Record valid observation counts,
compositing interval and missingness. NDVI maximum alone cannot infer tonnes/ha.
Fit yield against measured harvest data with field/year holdouts and uncertainty.

For precision agriculture, align soil chemistry, yield, crop demand and application
history; standardize features before exploratory clustering. KMeans labels are
management-zone candidates, not fertilizer prescriptions. Nutrient recommendations
need locally calibrated agronomic response models, unit reconciliation and applicable
constraints. A yield value in tonnes/ha multiplied by a kg/kg coefficient needs the
explicit tonne-to-kg conversion and does not account for existing soil supply.

## Forestry

Validate DSM/DEM grids and vertical datums before deriving canopy height. At each
survey plot, report valid-cell fraction and physically justified height/cover metrics.
Biomass requires a calibrated allometric/model relation with species, plot design,
units and transfer limits; arbitrary powers of height/cover are not tonnes.

Change detection compares co-registered, seasonally comparable, calibrated imagery
with joint valid support. An NDVI decrease is a vegetation-change candidate, not
proof of deforestation: drought, harvest, cloud/shadow and fire can look similar.
Confirm with independent labels/multitemporal evidence. Derive area from the affine
determinant in a suitable metric/equal-area CRS, not a fixed 900 m² assumption.

Sources: [ERA5 single levels](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels),
[PyKrige](https://geostat-framework.readthedocs.io/projects/pykrige/en/stable/generated/pykrige.ok.OrdinaryKriging.html),
[Rasterio transforms](https://rasterio.readthedocs.io/en/stable/topics/transforms.html),
[GRASS hydrology](https://grass.osgeo.org/grass-stable/manuals/r.watershed.html).
