# Advanced GIS: 3D, time, topology and networks

Local geometry/network contracts are covered by small synthetic tests. Native GDAL
viewshed and external trajectory datasets remain illustrative; see [review.md](review.md).

## 3D geometry and volume

Shapely stores Z but its geometric predicates, buffers and areas are planar: a point
buffer with a height tuple is not a 3D solid. Use a true 3D engine for volumetric
intersection. For Euclidean XYZ distance both horizontal/vertical coordinates must
share units and compatible datums. Polygon coordinates belong to exterior/interior
rings; `polygon.coords` is not implemented.

For DSM-minus-DEM volume, align CRS, affine, shape, pixel registration, vertical datum
and masks first. Convert to floating point before subtraction. A cell's planimetric
area is `abs(transform.a*transform.e - transform.b*transform.d)` in squared CRS units.
Sum valid positive height differences only if that is the defined estimand, and retain
negative differences for QA rather than silently hiding datum/registration errors.
Height bins must cover the intended range; report omitted/nodata area.

## Viewshed

Use the documented algorithm, not a ray sketch that compares each target to itself.
For a projected metric DEM and observer coordinates in that same CRS (illustrative):

```bash
gdal_viewshed -ox 500000 -oy 4200000 -oz 1.7 -tz 0 -md 5000 dem.tif viewshed.tif
```

GDAL's implementation requires projected coordinates for meaningful results and does
not specially handle input nodata. Resolve voids/extent beforehand. Observer and
target heights, Earth curvature/refraction and DSM versus bare-earth DEM change the
meaning; output visibility is conditional on those assumptions.
[GDAL viewshed](https://gdal.org/en/stable/programs/gdal_viewshed.html).

## Trajectories

```python
import movingpandas as mpd
import pandas as pd

# gdf is valid point data with known CRS, track_id and parsed timestamps.
collection = mpd.TrajectoryCollection(gdf, 'track_id', t='timestamp')
segments = mpd.ObservationGapSplitter(collection).split(gap=pd.Timedelta(hours=1))
smoothed = mpd.DouglasPeuckerGeneralizer(segments).generalize(tolerance=10)
stops = mpd.TrajectoryStopDetector(collection).get_stop_points(
    max_diameter=100, min_duration=pd.Timedelta(minutes=5))
moving = mpd.StopSplitter(collection).split(
    max_diameter=100, min_duration=pd.Timedelta(minutes=5), min_length=0)
for trajectory in segments:
    trajectory.add_speed(overwrite=True)
    print(trajectory.id, trajectory.get_length(), trajectory.get_duration())
```

Sort/check duplicate timestamps, timezones, sample gaps and implausible movement.
The splitter returns a trajectory collection, not a `(moving, stops)` pair.
Use metre-based projected coordinates for the tolerance shown and verify each API's
geographic-unit behavior. `get_speed()` is not a scalar trajectory mean; speed is a
per-observation attribute and a mean requires an explicit time/distance weighting.
[MovingPandas API](https://movingpandas.readthedocs.io/en/main/api/trajectorysplitter.html).

## Space-time bins and local statistics

Bin projected x/y and parsed time using a unit-consistent grid. Use lowercase hourly
frequency `h`; check timestamp gaps and empty spatial cells. The cube's row order
must match the spatial weight object. An illustrative per-time local statistic:

```python
import numpy as np
from libpysal.weights import KNN
from esda.getisord import G_Local

# coords are projected centroids, rows aligned with values; choose k scientifically.
w = KNN.from_array(coords, k=4)
local = G_Local(np.asarray(values, dtype=float), w, transform='B', star=True,
                permutations=999, seed=42, n_jobs=1, alternative='two-sided')
```

`G_Local` requires a weight object; `k=` is not a substitute. This example uses binary neighbour weights, includes self, and explicitly requests
two-sided permutation p-values. Adjust for multiplicity,
inspect islands/duplicates and check positive versus negative statistic direction.
Repeated independent Gi* tests are not ArcGIS Emerging Hot Spot Analysis, which
includes a specified space-time neighbourhood/trend classification.

## Planar topology

For an actual planar line network, node intersections before adding edges:

```python
from shapely import node, get_parts
from shapely.geometry import MultiLineString
import networkx as nx

def planar_graph(lines):
    # Single-part, valid LineStrings in one metric CRS; crossings truly connect.
    noded = node(MultiLineString(lines))
    graph = nx.MultiGraph()
    for line in get_parts(noded):
        coords = list(line.coords)
        graph.add_edge(coords[0], coords[-1], length=line.length, geometry=line)
    return graph
```

A road bridge crossing is not a planar junction; preserve grade/access attributes
when that topology matters. For polygon coverage, validate individual geometries,
interior overlap, and gaps relative to an explicit intended boundary. `touches` of a
polygon against the union of all others cannot diagnose gaps. Containment can be an
overlap even when `.overlaps()` is false. Shapely coverage validation can help, but
its gap-width rule and intended extent must be specified.

## Routing, service areas and facility location

Use OSMnx 2.x `ox.routing.add_edge_speeds` followed by `add_edge_travel_times`.
NetworkX shortest paths need nonnegative finite weights and a route-reachability
check; edge lengths are metres and travel times seconds. MultiDiGraph parallel
edges require retaining the selected edge identity for route geometry/cost totals.

Do not normalize each edge to [0,1] then silently claim a distance/time tradeoff:
subtracting a minimum per edge penalizes routes with different edge counts in an
arbitrary way. Define additive generalized costs with explicit unit conversion and
positive coefficients, then sensitivity-test the weights.

`nx.ego_graph(G, origin, radius=600, distance='travel_time')` gives reachable nodes
under the graph model. A hull over their geometry is only a display envelope, not
proof every enclosed location is reachable. Project before reporting hull area.
KMeans centres snapped to candidate sites can duplicate sites and do not solve the
p-median problem; see [specialized-topics.md](specialized-topics.md).

Sources: [Shapely node](https://shapely.readthedocs.io/en/stable/reference/shapely.node.html),
[PySAL G_Local](https://pysal.org/esda/generated/esda.G_Local.html),
[OSMnx](https://osmnx.readthedocs.io/en/stable/user-reference.html).

## Point clouds

LAS/LAZ interpretation requires point-format/version, CRS, XYZ scale/offset, vertical
datum, classification/return flags and acquisition provenance. Laspy reads the file
structure; use its scaled coordinates rather than raw integer XYZ for metric
calculations. PDAL pipelines need the native PDAL library and matching plugins.
Open3D0.20.0 has Python3.13 wheels, but geometry conversion alone does not preserve
LAS attributes/CRS automatically. Keep a separate metadata record, and validate point
count, bounds, units and flags through any conversion. No point-cloud binaries were
installed or processed in this review.
