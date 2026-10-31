# Geospatial data sources and API contracts

Reviewed 2026-10-01. Public STAC metadata searches were exercised; authenticated
pixel downloads, commercial APIs, CDS jobs and Earth Engine exports were not.

## Satellite, elevation and thematic catalogs

| Data | Official discovery entry point | Selection checks |
|---|---|---|
| Sentinel-1/2/3/5P | [Copernicus Data Space](https://dataspace.copernicus.eu/) | Mission, processing level, mode, polarization, baseline and QA |
| Landsat archive | [USGS EarthExplorer](https://earthexplorer.usgs.gov/) | Collection 2, L1 versus L2, optical versus thermal availability |
| PlanetScope/SkySat | [Planet](https://docs.planet.com/) | Licensed product and asset type; resolution varies by product |
| Maxar, Airbus, Capella | Provider catalogs | Confirm current license, acquisition and processing contract before ordering |
| SRTM, ASTER GDEM, Copernicus DEM | [CDSE DEM](https://documentation.dataspace.copernicus.eu/Data/Additional.html) and producer catalogs | DSM versus bare-earth DEM, void masks, vertical datum and angular pixel spacing |
| AW3D30 | [JAXA](https://www.eorc.jaxa.jp/ALOS/en/aw3d30/) | Product version, DSM interpretation, masks |
| ArcticDEM | [Polar Geospatial Center](https://www.pgc.umn.edu/data/arcticdem/) | Strip versus mosaic, reference frame and acquisition dates |
| WorldCover, MODIS land cover, NLCD | [ESA WorldCover](https://esa-worldcover.org/), [LP DAAC](https://lpdaac.usgs.gov/), [MRLC](https://www.mrlc.gov/) | Legend and year, not a universal class count |
| ERA5, MERRA-2, JRA | [CDS](https://cds.climate.copernicus.eu/), [NASA GMAO](https://gmao.gsfc.nasa.gov/), [JMA](https://jra.kishou.go.jp/) | Dataset-specific temporal coverage, grid, units and accumulation intervals |
| Admin/hydrology/population | [Natural Earth](https://www.naturalearthdata.com/), [GADM](https://gadm.org/), [HydroSHEDS](https://www.hydrosheds.org/), [WorldPop](https://www.worldpop.org/), [HDX](https://data.humdata.org/) | Boundary vintage, population counts versus densities, attribution/license |

Do not use the retired SciHub DHuS endpoint or `SentinelAPI(...scihub...)` for new
workflows. CDSE is a different service; STAC metadata discovery does not imply
unauthenticated access to every linked product. Follow the selected asset's CDSE
S3/OData access instructions rather than inventing a download URL.

## STAC search

| Catalog root | Contract |
|---|---|
| `https://stac.dataspace.copernicus.eu/v1` | CDSE public STAC discovery; inspect collection/queryables and asset access requirements |
| `https://earth-search.aws.element84.com/v1` | Element 84 Earth Search; Sentinel asset keys use names such as `red`, `nir`, `scl` |
| `https://planetarycomputer.microsoft.com/api/stac/v1` | Microsoft Planetary Computer; Sentinel keys include `B04`, `B08`, `SCL`; sign protected Azure assets |

Each supports Item Search under `/search` and returns GeoJSON `FeatureCollection`
with `features` and pagination links. Follow `rel=next` including its method/body;
do not construct page numbers. GeoJSON bbox is west,south,east,north in degrees.
Collection IDs and asset keys are provider-specific even for the same mission.

```python
from pystac_client import Client

catalog = Client.open('https://earth-search.aws.element84.com/v1')
search = catalog.search(collections=['sentinel-2-l2a'],
                        bbox=[-122.5, 37.7, -122.3, 37.9],
                        datetime='2023-06-01/2023-06-30',
                        query={'eo:cloud_cover': {'lt': 20}},
                        limit=2, max_items=5)
items = list(search.items())
if not items:
    raise ValueError('No matching items')
asset_metadata = {k: a.to_dict() for k, a in items[0].assets.items()}
```

`items()` is an iterator that fetches further pages; `item_collection()` materializes
the bounded result. `limit` is per-page, `max_items` is the client total.
Scene cloud percentage is only a coarse filter. Record item IDs, acquisition times,
asset checksums where available, scale/offset and the QA mask rule.

For Planetary Computer pass `modifier=planetary_computer.sign_inplace` to
`Client.open`. `ItemSearch` itself is not iterable; use `search.items()`.
The SDK's SAS token service is `GET /api/sas/v1/token/{account}/{container}`;
it returns `token` and `msft:expiry`. SDK signing appends the expiring SAS query to
Azure asset URLs. Do not log signed URLs or treat them as permanent identifiers.
Public metadata access was tested without a subscription key; access policies and
limits can differ for protected assets.

Sources: [CDSE STAC](https://documentation.dataspace.copernicus.eu/APIs/STAC.html),
[Earth Search](https://element84.com/earth-search/),
[PySTAC Client](https://pystac-client.readthedocs.io/en/latest/api.html),
[Planetary Computer SDK](https://github.com/microsoft/planetary-computer-sdk-for-python/blob/main/planetary_computer/sas.py).

## ERA5 through CDS

Configure CDS using its current personal-access-token setup and accept the chosen
dataset terms. The URL is `https://cds.climate.copernicus.eu/api`;
the old UID:key credential format and `/api/v2` configuration are not the current recipe.
Use the dataset download form's generated request for the exact variables/product.
This illustrative request creates a remote retrieval job:

```python
import cdsapi
client = cdsapi.Client()
client.retrieve('reanalysis-era5-single-levels', {
    'product_type': ['reanalysis'], 'variable': ['2m_temperature'],
    'year': ['2023'], 'month': ['01'], 'day': ['01'], 'time': ['12:00'],
    'area': [37.9, -122.5, 37.7, -122.3],  # north, west, south, east
    'data_format': 'netcdf', 'download_format': 'unarchived',
}, 'era5_temp.nc')
```

`retrieve` handles asynchronous processing and download, not pagination. Inspect
actual NetCDF dimensions (`valid_time` versus `time`) and units before aggregation.
[CDS setup](https://cds.climate.copernicus.eu/how-to-api) recommends current cdsapi;
credentialed retrieval was not run.

## OpenStreetMap, Overpass and Nominatim

OSMnx 2.1.1 uses `ox.features_from_place(place, tags={'building': True})`,
`ox.graph_from_place(place, network_type='drive')` and `ox.geocode_to_gdf(place)`.
These call external services. Cache permitted results, bound areas and obey service
policies. The public Nominatim service requires a meaningful identifying user-agent
and at most one request per second; it is not a bulk or autocomplete endpoint.

```python
import requests
query = '[out:json][timeout:25];way["highway"](37.700,-122.401,37.701,-122.400);out geom;'
response = requests.post('https://overpass-api.de/api/interpreter',
                         data={'data': query}, timeout=40)
response.raise_for_status()
data = response.json()
if data.get('remark'):
    raise RuntimeError(data['remark'])  # A timeout/error can accompany HTTP 200.
elements = data['elements']
```

Overpass bbox is south,west,north,east. It has no generic page parameter; subdivide
large AOIs and reconcile OSM type/ID duplicates. This query is an illustrative public
request, not executed in this refresh. See [OSMnx](https://osmnx.readthedocs.io/en/stable/user-reference.html),
[Overpass](https://wiki.openstreetmap.org/wiki/Overpass_API),
[Nominatim policy](https://operations.osmfoundation.org/policies/nominatim/).

## Geocoding and current weather

These are credentialed illustrative request contracts, not live test results.
Read tokens from an environment variable or credential store; never embed them in a
notebook, output URL or exception log. Use request timeouts and HTTP checks, then
validate the provider's response status before selecting a location.

| API | Method/path and required parameters | Response/limits |
|---|---|---|
| Google Geocoding v3 | GET `https://maps.googleapis.com/maps/api/geocode/json`; `address`, `key` | JSON `status` must be `OK`, nonempty `results`; `geometry.location` is `{lat,lng}`. `ZERO_RESULTS` is distinct from denial/quota errors. No pagination. |
| Mapbox Geocoding v6 | GET `https://api.mapbox.com/search/geocode/v6/forward`; `q`, `access_token`; use `autocomplete=false` for a completed query | GeoJSON `features`, coordinates lon/lat. `limit` is 1..10; no page traversal. v6 does not return POIs; use an address/place, not an assumed landmark lookup. Temporary results cannot be stored; request permitted permanent usage explicitly. |
| OpenWeather current | GET `https://api.openweathermap.org/data/2.5/weather`; `lat`, `lon`, `appid`, optionally `units=metric` | `main.temp`, `dt` (Unix seconds), `timezone` (seconds), `weather`; standard temperature defaults to Kelvin. A current snapshot is not a historical time series. No pagination. |

Sources: [Google request/response](https://developers.google.com/maps/documentation/geocoding/guides-v3/requests-geocoding),
[Mapbox v6](https://docs.mapbox.com/api/search/geocoding/),
[OpenWeather](https://openweathermap.org/api/current).

## Raster quality and elevation downloads

The `elevation` package wraps SRTM acquisition and native GDAL/Make tooling.
`elevation.clip(bounds=..., output=...)` downloads/crops; `elevation.clean()` cleans
temporary cache products, not raster voids. Void filling needs a separately chosen
method and QA. Never call `clean(input, output)` expecting a repaired DEM.

```python
import numpy as np
import rasterio

def assess_data_quality(path):
    with rasterio.open(path) as src:
        data = src.read(masked=True).astype('float64')
        valid = data.compressed()
        valid = valid[np.isfinite(valid)]
        return {'valid_fraction': valid.size / data.size,
                'range': (float(valid.min()), float(valid.max())) if valid.size else None,
                'crs': str(src.crs), 'resolution': src.res}
```

This checks numeric support, not acquisition quality or product correctness.
[Elevation source](https://github.com/bopen/elevation) documents its native dependencies.
