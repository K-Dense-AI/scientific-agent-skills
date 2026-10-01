# Industry applications

Workflows below are illustrative study designs; they do not establish operational
hazard, traffic, agronomic or infrastructure decisions. Their geometry/counting
recipes can be tested independently of the domain model.

## Urban land use and population

Land cover and land use are different labels: optical spectra alone do not establish
residential versus commercial use. Combine appropriately licensed imagery, building
attributes and independent labels. Validate raster grids, named bands and QA before
feature extraction. Use a spatial holdout and per-class confusion matrix as in
[machine-learning.md](machine-learning.md).

`skimage.feature.graycomatrix` summarizes the supplied quantized patch. Calling it
once on the full image produces global scalars, not a per-pixel texture map. For
local textures, state window size, quantization and boundary/nodata policy and check
chunk halos. Do not apply `remove_small_objects` directly to a categorical raster
expecting each disconnected class region to be handled independently.

Dasymetric redistribution must conserve each source-zone total. This tested function
allocates a scalar count over nonnegative cell weights for **one source zone**:

```python
import numpy as np

def redistribute_population(total, weights):
    weights = np.asarray(weights, dtype=float)
    if not np.isfinite(total) or total < 0 or not np.isfinite(weights).all() or (weights < 0).any():
        raise ValueError('Population and weights must be finite and nonnegative')
    if weights.sum() == 0:
        if total == 0:
            return np.zeros_like(weights)
        raise ValueError('Positive population has no eligible destination')
    return total * weights / weights.sum()
```

Apply independently within each census zone and assert sums after masking/cropping.
Do not multiply this allocation by the original population raster again. Counts and
densities require different resampling; record rounding and reconciliation policy.

## Disaster management

Flood risk requires a calibrated discharge/scenario, hydraulic model, connected
inundation, exposure and vulnerability. A DEM threshold using invented water levels
for 10/100/500-year events is not a return-period model. Keep hazard probability,
water depth, exposed people/assets and damage separate, with common units and time.
Use [hydrology](scientific-domains.md) for the preprocessing sequence and validate
against observed events; clipping settlements yields exposure, not damage.

Wildfire assessment requires justified fuels, moisture, topography, weather and a
calibrated spread/risk model. An arbitrary product of scaled wind/slope/vegetation is
an illustrative score, not probability. Reclassify NumPy arrays using explicit lookup
or boolean masks; arrays do not have `map_classes`. Keep wind speed/direction and
fuel-model provenance, uncertainty and out-of-domain conditions with any output.

## Utilities and infrastructure

For vegetation corridors, project linework to a locally appropriate metric CRS,
buffer a justified corridor distance, reproject that geometry to the raster CRS,
and pass the **open Rasterio dataset** to `rasterio.mask.mask`, not a NumPy array.
The returned affine transform locates the cropped pixels. Masked height values and
wire height/sag/clearance uncertainty need explicit treatment.

```python
from rasterio.mask import mask
import rasterio

metric_lines = power_lines.to_crs(power_lines.estimate_utm_crs())
corridors = metric_lines.geometry.buffer(buffer_metres)
with rasterio.open('vegetation_height.tif') as src:
    if src.crs is None:
        raise ValueError('Raster CRS missing')
    heights, cropped_transform = mask(src, corridors.to_crs(src.crs), crop=True, filled=False)
# row,column component centres must be transformed through cropped_transform.
```

A chosen canopy threshold marks screening candidates, not regulatory clearance.
Compute area from valid projected-cell support, not a hardcoded 1 m² per pixel.
Export georeferenced findings for review; output generation is not authorization to
create work orders.

For pipeline least-cost routing, encode truly prohibited cells as inaccessible edges,
not merely high finite cost (which can still be selected). Raster costs must have
units, resolution and directional assumptions. Account for diagonal step length and
corner cutting, preserve barriers, check endpoint accessibility and handle no path.
Verify the reconstructed route independently against constraints and cumulative cost.

## Transportation and transit

OSMnx constructs topological street networks from OSM. `graph_from_gdf(roads)` does
not exist: `graph_from_gdfs(nodes, edges)` requires correctly indexed node/edge tables
and CRS, or download a bounded walk/drive graph. Lines that cross on a map may be
bridges/tunnels and must not be automatically connected.

For a walk-time accessibility template on an existing graph:

```python
import networkx as nx

def reachable_walk_nodes(graph, origin, minutes=15, speed_kph=5):
    if minutes < 0 or speed_kph <= 0:
        raise ValueError('Nonnegative time and positive walking speed required')
    graph = graph.copy()
    for _, _, data in graph.edges(data=True):
        length = float(data['length'])
        if not np.isfinite(length) or length < 0:
            raise ValueError('Edge length must be finite nonnegative metres')
        data['walk_seconds'] = length / (speed_kph / 3.6)
    return nx.single_source_dijkstra_path_length(
        graph, origin, cutoff=minutes * 60, weight='walk_seconds')
```

This is fixed-speed walking with the graph's direction/access restrictions. It excludes
transit waiting, timetables, transfers, grade and partial terminal edges. A convex hull
of reachable nodes can include inaccessible water/barriers; label it a visualization
approximation, not a service-area boundary. Edge count is not a travel-time measure.

AADT is vehicles/day, not a peak-hour flow. Do not divide it by vehicles/hour capacity
without a calibrated temporal conversion. Nearby sensor interpolation alone does not
model connectivity, turns or demand; validate predictions on withheld roads/times.

Sources: [Rasterio masking](https://rasterio.readthedocs.io/en/stable/api/rasterio.mask.html),
[OSMnx contracts](https://osmnx.readthedocs.io/en/stable/user-reference.html),
[NetworkX Dijkstra](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.shortest_paths.weighted.single_source_dijkstra_path_length.html),
[Scikit-image GLCM](https://scikit-image.org/docs/stable/api/skimage.feature.html#skimage.feature.graycomatrix).
