# cuSpatial Reference

cuSpatial is a GPU-accelerated GIS library that provides spatial indexing, spatial joins, distance calculations, trajectory analysis, and GeoPandas-compatible geometry types. It integrates with cuDF for tabular data and GeoPandas for geometry interoperability, enabling you to accelerate geospatial workflows by moving the compute-heavy parts to GPU.

> **Full documentation:** https://docs.rapids.ai/api/cuspatial/stable/

## Table of Contents

1. [Installation and Setup](#installation-and-setup)
2. [GeoPandas Interoperability](#geopandas-interoperability)
3. [GeoSeries and GeoDataFrame](#geoseries-and-geodataframe)
4. [Spatial Joins — Point in Polygon](#spatial-joins--point-in-polygon)
5. [Spatial Indexing — Quadtree](#spatial-indexing--quadtree)
6. [Distance Functions](#distance-functions)
7. [Nearest Points](#nearest-points)
8. [Bounding Boxes](#bounding-boxes)
9. [Projections](#projections)
10. [Spatial Filtering](#spatial-filtering)
11. [Trajectory Analysis](#trajectory-analysis)
12. [Binary Predicates](#binary-predicates)
13. [Performance Tips](#performance-tips)
14. [Common Pitfalls](#common-pitfalls)

---

## Installation and Setup

Always use `uv add` (never `pip install` or `conda install`) in all install instructions, docstrings, comments, and error messages.

```bash
uv add --extra-index-url=https://pypi.nvidia.com cuspatial-cu12   # For CUDA 12.x
```

Verify:
```python
import cuspatial
from shapely.geometry import Point
gs = cuspatial.GeoSeries([Point(0, 0), Point(1, 1)])
print(gs)
```

---

## GeoPandas Interoperability

cuSpatial's primary on-ramp is converting from GeoPandas. Any `GeoSeries` or `GeoDataFrame` can be moved to GPU:

```python
import geopandas as gpd
import cuspatial

# GeoPandas -> cuSpatial (CPU -> GPU)
gdf = gpd.read_file("my_shapefile.shp")
cu_gdf = cuspatial.from_geopandas(gdf)

# cuSpatial -> GeoPandas (GPU -> CPU)
gdf_back = cu_gdf.to_geopandas()
```

You can also construct a `GeoDataFrame` directly:
```python
cu_gdf = cuspatial.GeoDataFrame(geopandas_dataframe)
```

---

## GeoSeries and GeoDataFrame

`cuspatial.GeoSeries` is a GPU-backed series that holds shapely-compatible geometry objects (Point, MultiPoint, LineString, MultiLineString, Polygon, MultiPolygon).

### Creating GeoSeries from Shapely objects

```python
from shapely.geometry import Point, Polygon, LineString, MultiPoint
import cuspatial

points = cuspatial.GeoSeries([Point(0, 0), Point(1, 1), Point(2, 2)])
polys = cuspatial.GeoSeries([
    Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]),
    Polygon([(2, 2), (3, 2), (3, 3), (2, 3), (2, 2)])
])
```

### Creating GeoSeries from coordinate arrays (faster for large data)

```python
import cudf

# Points from interleaved xy coordinates
xy = cudf.Series([0.0, 0.0, 1.0, 1.0, 2.0, 2.0])  # x0, y0, x1, y1, ...
points = cuspatial.GeoSeries.from_points_xy(xy)

# MultiPoints from interleaved xy + geometry offsets
multipoints = cuspatial.GeoSeries.from_multipoints_xy(
    multipoints_xy=cudf.Series([0.0, 0.0, 1.0, 1.0, 2.0, 2.0, 3.0, 3.0]),
    geometry_offset=cudf.Series([0, 2, 4])  # 2 multipoints, each with 2 points
)
```

### GeoSeries properties

```python
gs = cuspatial.GeoSeries([Point(0, 0), Point(1, 1)])
gs.points.xy        # Access raw interleaved coordinates
gs.sizes             # Number of points per geometry
gs.iloc[0]           # Access single geometry
```

### GeoDataFrame

```python
cu_gdf = cuspatial.GeoDataFrame({
    "geometry": cuspatial.GeoSeries([Point(0, 0), Point(1, 1)]),
    "value": cudf.Series([10, 20])
})
```

---

## Spatial Joins — Point in Polygon

The most common operation: test which points are inside which polygons.

### Simple point-in-polygon

```python
from shapely.geometry import Point, Polygon
import cuspatial

points = cuspatial.GeoSeries([Point(0, 0), Point(-8, -8), Point(6, 6)])
polygons = cuspatial.GeoSeries([
    Polygon([(-10, -10), (5, -10), (5, 5), (-10, 5), (-10, -10)]),
    Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
])

result = cuspatial.point_in_polygon(points, polygons)
# Returns a DataFrame of booleans: rows=points, columns=polygons
#   polygon_0  polygon_1
# 0     True      True     <- (0,0) is in both
# 1     True     False     <- (-8,-8) is in first only
# 2    False      True     <- (6,6) is in second only
```

### Quadtree-accelerated point-in-polygon (for large datasets)

For millions of points, use the quadtree pipeline — it dramatically reduces the number of point-polygon tests:

```python
import cuspatial
import cudf

# 1. Build quadtree on points
key_to_point, quadtree = cuspatial.quadtree_on_points(
    points,              # GeoSeries of points
    x_min, x_max,        # Bounding box
    y_min, y_max,
    scale=scale,         # Usually (max_extent) / (2^max_depth)
    max_depth=7,         # Max tree depth (< 16)
    max_size=125         # Max points per leaf before splitting
)

# 2. Compute polygon bounding boxes
poly_bboxes = cuspatial.polygon_bounding_boxes(polygons)

# 3. Join quadtree with bounding boxes
intersections = cuspatial.join_quadtree_and_bounding_boxes(
    quadtree, poly_bboxes, x_min, x_max, y_min, y_max, scale, max_depth
)

# 4. Test point-in-polygon only for relevant quadrants
result = cuspatial.quadtree_point_in_polygon(
    intersections, quadtree, key_to_point, points, polygons
)
# Returns DataFrame with polygon_index and point_index columns
```

---

## Spatial Indexing — Quadtree

Build a quadtree spatial index on a set of points. This is the foundation for scalable spatial joins.

```python
key_to_point, quadtree = cuspatial.quadtree_on_points(
    points,            # GeoSeries of points
    x_min, x_max,      # Area of interest bounding box
    y_min, y_max,
    scale,             # Grid resolution
    max_depth,         # Maximum tree depth (must be < 16)
    max_size           # Max points per node before splitting
)

# quadtree is a DataFrame with columns:
#   key, level, is_internal_node, length, offset
# key_to_point maps sorted quadtree indices back to original point indices
```

**Choosing scale:** `scale = max(x_max - x_min, y_max - y_min) / (2 ** max_depth)`

---

## Distance Functions

### Haversine distance (great-circle, for lat/lon coordinates)

```python
p1 = cuspatial.GeoSeries([Point(lon1, lat1), Point(lon2, lat2)])
p2 = cuspatial.GeoSeries([Point(lon3, lat3), Point(lon4, lat4)])

distances_km = cuspatial.haversine_distance(p1, p2)
# Returns cudf.Series of distances in kilometers
```

### Pairwise point distance (Euclidean)

```python
from shapely.geometry import Point, MultiPoint

p1 = cuspatial.GeoSeries([Point(0, 0), Point(1, 0)])
p2 = cuspatial.GeoSeries([Point(3, 4), Point(4, 3)])
dists = cuspatial.pairwise_point_distance(p1, p2)  # [5.0, 4.243]
```

### Pairwise linestring distance

```python
from shapely.geometry import LineString

ls1 = cuspatial.GeoSeries([LineString([(0, 0), (1, 1)])])
ls2 = cuspatial.GeoSeries([LineString([(2, 0), (3, 1)])])
dists = cuspatial.pairwise_linestring_distance(ls1, ls2)
```

### Point-to-linestring distance

```python
pts = cuspatial.GeoSeries([Point(0, 0)])
lines = cuspatial.GeoSeries([LineString([(1, 0), (0, 1)])])
dists = cuspatial.pairwise_point_linestring_distance(pts, lines)
```

### Directed Hausdorff distance

```python
from shapely.geometry import MultiPoint

spaces = cuspatial.GeoSeries([
    MultiPoint([(0, 0), (1, 0)]),
    MultiPoint([(0, 1), (0, 2)])
])
hausdorff = cuspatial.directed_hausdorff_distance(spaces)
# Returns DataFrame: hausdorff[i][j] = directed Hausdorff from space i to j
```

---

## Nearest Points

Find the nearest point on a linestring to each point:

```python
result = cuspatial.pairwise_point_linestring_nearest_points(points, linestrings)
# Returns GeoDataFrame with:
#   point_geometry_id, linestring_geometry_id, segment_id, geometry (nearest point)
```

For quadtree-accelerated nearest linestring lookup:

```python
result = cuspatial.quadtree_point_to_nearest_linestring(
    linestring_quad_pairs, quadtree, key_to_point, points, linestrings
)
# Returns DataFrame with: point_index, linestring_index, distance
```

---

## Bounding Boxes

```python
# Polygon bounding boxes
poly_bboxes = cuspatial.polygon_bounding_boxes(polygons)
# Returns DataFrame: minx, miny, maxx, maxy

# Linestring bounding boxes (with expansion radius)
line_bboxes = cuspatial.linestring_bounding_boxes(linestrings, expansion_radius=0.5)
```

---

## Projections

### Sinusoidal projection (lon/lat to Cartesian km)

For approximately converting geographic coordinates to Cartesian coordinates when all points are near a reference origin:

```python
origin_lon, origin_lat = -73.9857, 40.7484  # e.g., NYC
lonlat_points = cuspatial.GeoSeries([Point(-73.98, 40.75), Point(-73.99, 40.74)])

xy_km = cuspatial.sinusoidal_projection(origin_lon, origin_lat, lonlat_points)
# Returns GeoSeries of projected (x, y) points in kilometers
```

---

## Spatial Filtering

Filter points within a rectangular window:

```python
filtered = cuspatial.points_in_spatial_window(
    points,
    min_x=-10, max_x=10,
    min_y=-10, max_y=10
)
# Returns GeoSeries of only the points inside the window
```

---

## Trajectory Analysis

Identify, reconstruct, and analyze trajectories from timestamped point data (e.g., vehicle GPS traces).

### Derive trajectories

```python
objects, traj_offsets = cuspatial.derive_trajectories(
    object_ids=[0, 1, 0, 1],     # e.g., vehicle IDs
    points=cuspatial.GeoSeries([Point(0,0), Point(0,0), Point(1,1), Point(1,1)]),
    timestamps=[0, 0, 10000, 10000]
)
# objects: DataFrame sorted by (object_id, timestamp) with x, y, timestamp
# traj_offsets: Series of offsets marking each trajectory's start
```

### Distances and speeds

```python
dist_speed = cuspatial.trajectory_distances_and_speeds(
    len(traj_offsets),
    objects['object_id'],
    objects_points,        # GeoSeries
    objects['timestamp']
)
# Returns DataFrame with 'distance' (km) and 'speed' (m/s) per trajectory
```

### Trajectory bounding boxes

```python
traj_bboxes = cuspatial.trajectory_bounding_boxes(
    len(traj_offsets),
    objects['object_id'],
    objects_points
)
# Returns DataFrame: x_min, y_min, x_max, y_max per trajectory
```

---

## Binary Predicates

`GeoSeries` supports GeoPandas-compatible binary spatial predicates — all GPU-accelerated:

```python
# All return cudf.Series of booleans
polys.contains(points)            # Is each point inside the polygon?
polys.contains_properly(points)   # Strictly interior (not on boundary)?
geom_a.covers(geom_b)            # Does A cover B?
geom_a.crosses(geom_b)           # Do geometries cross?
geom_a.disjoint(geom_b)          # Are they disjoint?
geom_a.distance(geom_b)          # Pairwise distances
geom_a.geom_equals(geom_b)       # Are they geometrically equal?
geom_a.intersects(geom_b)        # Do they intersect?
geom_a.overlaps(geom_b)          # Do they overlap?
geom_a.touches(geom_b)           # Do they touch?
geom_a.within(geom_b)            # Is A within B?
```

The `contains` and `contains_properly` methods support an `allpairs=True` mode that returns all point-polygon containment pairs (useful when you have M points and N polygons and want all matches):

```python
result = polygons.contains(points, allpairs=True)
# Returns DataFrame with point_indices and polygon_indices columns
```

---

## Performance Tips

1. **Use the quadtree pipeline for large datasets.** Brute-force `point_in_polygon` tests every point against every polygon. The quadtree pipeline (`quadtree_on_points` + `join_quadtree_and_bounding_boxes` + `quadtree_point_in_polygon`) pre-filters using spatial indexing and can be orders of magnitude faster for millions of points/polygons.

2. **Build GeoSeries from coordinate arrays, not shapely objects.** `GeoSeries.from_points_xy()` with cuDF Series is much faster than constructing from a list of shapely Point objects, which requires serializing each geometry.

3. **Keep data on GPU.** cuSpatial integrates with cuDF — load data with `cudf.read_csv()` or `cudf.read_parquet()`, then construct GeoSeries from the coordinate columns. Avoid round-tripping through GeoPandas for large datasets.

4. **Use `allpairs=True` for many-to-many spatial joins.** If you need to find all point-polygon pairs (not just row-wise), use `contains(points, allpairs=True)` instead of expanding the data yourself.

5. **Combine with cuDF for full pipelines.** cuSpatial returns cuDF DataFrames/Series, so you can chain spatial operations with cuDF filtering, groupby, and joins without leaving the GPU.

---

## Common Pitfalls

- **Polygons must be closed.** The first and last coordinate of each polygon ring must be identical. Shapely handles this automatically, but if constructing from raw coordinates, ensure closure.

- **GeoSeries must be single-type for some operations.** Functions like `pairwise_point_distance` require the series to contain only points or only multipoints — you can't mix types in the same series.

- **Quadtree max_depth < 16.** Morton codes are represented as uint32, so max_depth must be less than 16.

- **Haversine expects lon/lat, not lat/lon.** cuSpatial follows the (longitude, latitude) convention, matching shapely/GeoJSON — not the (lat, lon) convention used by some mapping APIs.

- **No CRS transformations.** cuSpatial doesn't handle coordinate reference system conversions. Project your data to the correct CRS using GeoPandas/pyproj before moving to GPU.
