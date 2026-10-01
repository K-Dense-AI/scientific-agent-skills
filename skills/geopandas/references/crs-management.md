# CRS, units, and reprojection

A CRS is part of the data model, not display metadata. An incorrect or missing
CRS can make numerically plausible results geographically wrong.

## Require authoritative CRS metadata

```python
from pyproj import CRS

if gdf.crs is None:
    raise ValueError("CRS is missing; recover it from authoritative source metadata")

crs = CRS.from_user_input(gdf.crs)
```

Do not infer EPSG:4326 because values resemble longitude/latitude. Coordinate
ranges are not evidence of datum, axis interpretation, units, or epoch.

### `set_crs` versus `to_crs`

```python
# Assign metadata only; coordinate numbers do not change.
gdf = gdf.set_crs("EPSG:4326")

# Transform coordinates; the source CRS must already be set.
projected = gdf.to_crs("EPSG:32631")
```

- Use `set_crs()` only when the coordinate values are already expressed in that
  CRS and metadata is absent or demonstrably wrong.
- Replacing existing metadata requires `allow_override=True`; record why.
- Use `to_crs()` to transform the active geometry column. Transform each
  additional geometry column explicitly.
- Do not assign `gdf.crs = ...`; manual override is deprecated.

## Axis order

EPSG definitions can be latitude/longitude while GIS coordinate arrays are
normally x/y (longitude/latitude). Inspect the authority axes:

```python
for axis in crs.axis_info:
    print(axis.name, axis.abbrev, axis.direction, axis.unit_name)
```

For explicit pyproj transformations, request traditional GIS x/y order:

```python
from pyproj import Transformer

transformer = Transformer.from_crs(
    source_crs,
    target_crs,
    always_xy=True,
    allow_ballpark=False,
    only_best=True,
)
x_out, y_out = transformer.transform(x_in, y_in, errcheck=True)
```

Record `always_xy=True`; it changes the API coordinate order, not the CRS
definition. GeoParquet 1.1 explicitly stores WKB/native coordinates as x/y even
when the CRS authority uses another axis order.

## Units and planar operations

GeoPandas and Shapely compute planar Cartesian geometry and ignore Z:

- geographic longitude/latitude axes are angular, usually degrees;
- projected axes may be metres, US survey feet, feet, or another linear unit;
- `.area` returns squared coordinate units;
- `.length`, `.distance`, `.buffer`, `sjoin_nearest(max_distance=...)`,
  `sjoin(predicate="dwithin", distance=...)`, precision grids, simplify
  tolerances, and gap widths use coordinate units.

```python
axis_units = [(axis.unit_name, axis.unit_conversion_factor) for axis in crs.axis_info]
if crs.is_geographic:
    raise ValueError("Planar measurement on angular coordinates is not accepted")
```

Do not label an output metres merely because a CRS is projected. Convert units
using the CRS axis metadata and document the conversion. Web Mercator
(`EPSG:3857`) is for web display, not general area/distance analysis.

### Choosing a measurement CRS

Choose based on the operation, study extent, datum, and required accuracy:

- local UTM or another local conformal CRS for local distances/angles;
- an equal-area CRS for area totals and areal normalization;
- an equidistant/azimuthal design for a specified distance origin;
- geodesic methods for large/global geographic extents.

`estimate_utm_crs()` is a convenience based on dataset bounds, not a proof of
suitability. It can be poor for multi-zone, polar, antimeridian-crossing, or
very large datasets.

## Geodesic measurements

When projection distortion is unacceptable, use the ellipsoid associated with
the CRS through `pyproj.Geod`, not Shapely's planar distance:

```python
geod = crs.get_geod()
azimuth_fwd, azimuth_back, metres = geod.inv(lon1, lat1, lon2, lat2)
area_m2, perimeter_m = geod.geometry_area_perimeter(polygon)
```

Ensure inputs are longitude/latitude on the intended geodetic datum. Geodesic
area is signed according to ring orientation and has documented limitations for
very large polygons; normalize orientation and test known controls.

## Datum transformations and operation selection

The same source/target CRS pair can have several operations. Selection depends
on area of interest, installed grids, authority, and accuracy:

```python
from pyproj.aoi import AreaOfInterest
from pyproj.transformer import TransformerGroup
from pyproj import network

network.set_network_enabled(False)
group = TransformerGroup(
    source_crs,
    target_crs,
    always_xy=True,
    area_of_interest=AreaOfInterest(west, south, east, north),
    allow_ballpark=False,
)

if not group.best_available or not group.transformers:
    raise RuntimeError("Best transformation unavailable; inspect missing grids")

candidate = group.transformers[0]
print(candidate.description, candidate.accuracy, candidate.area_of_use)
```

`AreaOfInterest` always takes geographic longitude/latitude **degrees**, never
projected metres/feet. The bundled planner accepts `--bbox` only for a source
CRS with geographic degree axes; omit it for projected sources. Its bounds and
transform descriptions are planning metadata, not transformed coordinates.

Privacy note: an exact area of interest can reveal a sensitive study location.
Do not log it; retain only an approved coarse region or protected audit record.

Operational rules:

1. Set `allow_ballpark=False` for accuracy-sensitive work.
2. Use `only_best=True` with `Transformer.from_crs()` when failure is preferable
   to silently selecting a lower-quality operation.
3. Verify `accuracy` (`-1` means unknown) and `area_of_use`.
4. Inspect `TransformerGroup.unavailable_operations` for missing grids.
5. Keep PROJ network disabled by default. pyproj wheels do not include all
   transformation grids; downloading grids is a separate, explicit network and
   supply-chain action.
6. Record PROJ database/native versions and the selected operation description.
7. For dynamic CRS, record coordinate epoch. A CRS alone may be insufficient.

The bundled `scripts/crs_reprojection_plan.py` performs this inspection without
transforming coordinates or enabling network access.

## Geometry transformation caveat

`GeoDataFrame.to_crs()` transforms every existing vertex. It does not interpret
a segment as a geodesic arc:

```python
out = gdf.to_crs(target_crs)
```

If source linework is sparse, densify according to a documented geodesic or
source-space tolerance before projection when shape fidelity matters. Validate
the resulting topology and bounds.

## Antimeridian and projection boundaries

`to_crs()` warns that objects crossing the dateline or another projection
boundary have undesirable behavior. A naive line from 179°E to 179°W can be
treated as spanning almost the whole map.

Safe workflow:

1. Normalize and validate longitude convention (`[-180, 180]` or `[0, 360)`).
2. Detect segment jumps and bbox representations that cross the antimeridian.
3. Split/unwrap at ±180° in a documented geographic CRS.
4. Densify geodesic edges if required by the accuracy target.
5. Transform each part with an operation valid for its area.
6. Reassemble only when target topology permits it.
7. Compare source/target control points, feature counts, validity, and bounds.

For transformed bounds, use `Transformer.transform_bounds(..., densify_pts=...)`.
When geographic output returns `right < left`, pyproj documents that the bounds
cross the antimeridian and should be represented as two polygons. Do not sort
the numbers and erase that meaning.

## CRS equality and concatenation

Compare semantic CRS objects, not raw WKT strings:

```python
left_crs = CRS.from_user_input(left.crs)
right_crs = CRS.from_user_input(right.crs)
if not left_crs.equals(right_crs):
    right = right.to_crs(left_crs)
```

Equivalent does not mean equally appropriate for the analysis. Before concat,
join, overlay, or clip, require matching CRS and confirm both datasets use the
same coordinate epoch/realization where relevant.

## Reprojection provenance

Record:

- source and target CRS as WKT2/PROJJSON plus authority IDs when available;
- source of CRS assignment and any override;
- axis order exposed by the CRS and API order (`always_xy`);
- units and conversion factors;
- area of interest at an approved precision;
- chosen operation, expected accuracy, ballpark policy, and area of use;
- required/available grids, network policy, PROJ data/database versions;
- densification, antimeridian splitting, precision, and validation checks.

## Sources (verified 2026-10-01)

- [GeoPandas projections guide](https://geopandas.org/en/stable/docs/user_guide/projections.html).
- [GeoDataFrame.to_crs](https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoDataFrame.to_crs.html).
- [GeoDataFrame.set_crs](https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoDataFrame.set_crs.html).
- [pyproj Transformer API](https://pyproj4.github.io/pyproj/stable/api/transformer.html).
- [pyproj CRS API](https://pyproj4.github.io/pyproj/stable/api/crs/crs.html).
- [pyproj transformation grids](https://pyproj4.github.io/pyproj/stable/transformation_grids.html).
- [pyproj Geod API](https://pyproj4.github.io/pyproj/stable/api/geod.html).
- [GeoParquet 1.1.0 CRS and axis-order rules](https://geoparquet.org/releases/v1.1.0/).

- [pyproj 3.8.0 AreaOfInterest source](https://github.com/pyproj4/pyproj/blob/3.8.0/pyproj/aoi.py).
