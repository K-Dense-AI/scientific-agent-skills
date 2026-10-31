# Small geospatial code recipes

Reviewed 2026-10-01. These focus on contracts that caused silent errors in earlier
examples. See [review.md](review.md) for tested versions. Data-dependent fragments
are illustrative; variables such as `gdf`, `polygon` and `zones` must be supplied.
The collection does not claim hundreds of executed examples.

## Coordinates, vector data and maps

```python
import geopandas as gpd
from pyproj import Geod

gdf = gpd.read_file('data.gpkg', layer='features')
if gdf.crs is None:
    raise ValueError('Source CRS is missing')
metric = gdf.to_crs(gdf.estimate_utm_crs())
metric['area_m2'] = metric.geometry.area
buffer_geometry = metric.buffer(1000)
# Keep a single active geometry when exporting to formats that require it.
buffer_gdf = metric.set_geometry(buffer_geometry)
buffer_gdf.to_file('buffers.gpkg', driver='GPKG')

# Geographic azimuth/distance: Geod returns forward azimuth, back azimuth, metres.
azimuth, back_azimuth, metres = Geod(ellps='WGS84').inv(-122.4, 37.7, -122.3, 37.8)
```

`geopy.distance.geodesic` returns distance but has no `initial_bearing` property.
Geopy coordinates are latitude,longitude; GeoJSON/PyProj with `always_xy` use longitude,latitude.
For a geographic BallTree use radians and `metric='haversine'`, then convert angular
distance using an explicit Earth-radius convention. Projected Euclidean k-NN needs
appropriate coordinate units and scaling.

Folium uses `Map(location=[latitude, longitude])` and `GeoJson(gdf.to_crs(4326))`.
Contextily uses `add_basemap(ax, crs=gdf.crs)` and a permitted tile provider. Pass
explicit data/position accessors to Pydeck; an unconfigured layer does not establish
that coordinates are displayed correctly. All web maps require attribution and
compliance with provider access/caching rules.

## Raster I/O and masks

```python
import rasterio
from rasterio.mask import mask

with rasterio.open('raster.tif') as src:
    # polygon must already be in src.crs
    clipped, transform = mask(src, [polygon], crop=True, filled=False)
    profile = src.profile.copy()
profile.update(height=clipped.shape[1], width=clipped.shape[2], transform=transform)
with rasterio.open('clipped.tif', 'w', **profile) as dst:
    dst.write(clipped, masked=True)
```

Do not read from a closed `src`. For resampling, update the affine alongside shape:

```python
from rasterio.enums import Resampling
from affine import Affine
with rasterio.open('raster.tif') as src:
    rows, cols = src.height * 2, src.width * 2
    data = src.read(out_shape=(src.count, rows, cols), masked=True,
                    resampling=Resampling.bilinear)
    transform = src.transform * Affine.scale(src.width / cols, src.height / rows)
```

Bilinear is suitable only for continuous quantities; categories need nearest/mode.
Doubling pixel count does not double actual resolving power. Reprojection needs both
source and destination CRS/transform plus a nodata/resampling policy.

## Spectral indices, classification and terrain

The bundled `raster_workflows.py` contains the maintained implementations; import it
from the skill's scripts directory. See the main skill for examples. It provides:

- `normalized_difference(a,b)`: floating-point subtraction, mask and zero-denominator handling;
- `spectral_indices(...)`: physical-reflectance NDVI/EVI/SAVI/NDWI/MNDWI/NBR/NDBI;
- `terrain_metrics(dem,transform,crs)`: physical gradients, downslope aspect, flat-cell policy;
- `write_ndvi(...)`: explicit bands/calibration, preserved raster georeferencing/nodata;
- `classify_imagery(...)`: known CRS, raster-aligned labels, valid pixels and uint16 class output.

Raster classification requires the raster's actual affine transform when rasterizing
training polygons; a default identity transform can yield wrong or empty training
samples. A Random Forest fitted to pixels has not measured spatial transfer accuracy.
Use blocked validation. Do not label a flat DEM threshold as flood-risk modeling.

## Interpolation and spatial statistics

```python
import numpy as np
from scipy.interpolate import griddata, NearestNDInterpolator, RBFInterpolator
from scipy.stats import gaussian_kde

# points: (n,2) projected coordinates; values: (n,)
linear = griddata(points, values, (xi, yi), method='linear')
nearest = NearestNDInterpolator(points, values)
rbf = RBFInterpolator(points, values, kernel='thin_plate_spline')

# KDE expects dimensions x observations, evaluation dimensions x locations.
grid_x, grid_y = np.mgrid[xmin:xmax:100j, ymin:ymax:100j]
kde = gaussian_kde(points.T)
density = kde(np.vstack([grid_x.ravel(), grid_y.ravel()])).reshape(grid_x.shape)
```

`griddata(method='linear')` is linear triangulation, not IDW.
`NearestNDInterpolator` is nearest neighbour, not natural neighbour.
KDE requires a defined bandwidth and sufficient nondegenerate observations; compare
boundary correction and sampling effort before interpreting density as risk.
For Moran's I, Geary's C and Gi*, align observation order with a chosen spatial weight
matrix. Kriging needs a defensible variogram and spatial holdouts; see
[specialized topics](specialized-topics.md).

## Image watershed versus catchment delineation

```python
from scipy.ndimage import label
from skimage.segmentation import watershed
markers, marker_count = label(local_minima)
segments = watershed(elevation, markers=markers, mask=valid_mask)
```

This is image segmentation. It does not implement hydrological catchment routing,
pour-point snapping or contributing area. `scipy.ndimage.watershed` is not this API.
For hydrology use the domain workflow and documented direction conventions.

## Tiles and network helpers

```python
import mercantile
# Geographic bbox west,south,east,north; zoom is a separate argument.
tiles = list(mercantile.tiles(-122.41, 37.70, -122.40, 37.71, zooms=12))
```

Enumerating tiles does not render/reproject raster pixels. A renderer must produce
each tile's correct Web Mercator bounds/resolution and nodata/alpha behavior. Public
OSM tiles are not a bulk/offline export service.

Use `ox.routing.shortest_path` or NetworkX shortest paths on an OSMnx graph, with
explicit weights/units and no-route handling. Metric reachability is not an edge-count
radius. See [advanced GIS](advanced-gis.md).

## Other languages

The maintained R, Julia, JavaScript, C++, Java, Go and Rust fragments are in
[programming-languages.md](programming-languages.md). In Turf,
`interpolate(points,cellSize,{property:'value',units:'kilometers'})` expects a
FeatureCollection of points with values, not a LineString.

Sources: [PyProj Geod](https://pyproj4.github.io/pyproj/stable/api/geod.html),
[Rasterio resampling](https://rasterio.readthedocs.io/en/stable/topics/resampling.html),
[SciPy interpolation](https://docs.scipy.org/doc/scipy/reference/interpolate.html),
[Scikit-image watershed](https://scikit-image.org/docs/stable/api/skimage.segmentation.html#skimage.segmentation.watershed),
[Mercantile](https://mercantile.readthedocs.io/en/latest/api/mercantile.html),
[Turf interpolation](https://turfjs.org/docs/api/interpolate).
