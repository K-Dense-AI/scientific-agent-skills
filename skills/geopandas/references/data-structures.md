# GeoPandas data structures

GeoPandas 1.2.0 extends pandas with a `geometry` extension dtype backed by
Shapely 2. A `GeoSeries` is one geometry-valued pandas Series; a `GeoDataFrame`
is a DataFrame with one active geometry column and may contain additional
geometry columns.

## Construction

Always assign CRS at construction when it is known from authoritative metadata.
Do not infer it from coordinate ranges.

```python
import geopandas as gpd
import pandas as pd
from shapely import Point, box

points = gpd.GeoSeries(
    [Point(0, 0), Point(1, 1), None],
    index=["feature-a", "feature-b", "feature-c"],
    crs="EPSG:3857",
    name="location",
)

gdf = gpd.GeoDataFrame(
    {
        "feature_id": ["feature-a", "feature-b"],
        "value": [10, 20],
        "geometry": [Point(0, 0), Point(1, 1)],
    },
    geometry="geometry",
    crs="EPSG:3857",
)

table = pd.DataFrame({"x": [0.0, 1.0], "y": [0.0, 1.0]})
from_xy = gpd.GeoDataFrame(
    table,
    geometry=gpd.points_from_xy(table["x"], table["y"]),
    crs="EPSG:3857",
)
```

`points_from_xy` interprets arguments as x then y. For geographic data, that is
normally longitude then latitude in the coordinate array, even though the
authority definition of EPSG:4326 advertises latitude-first axes.

## Active and additional geometry columns

Frame-level spatial methods act on one active geometry column:

```python
gdf["buffered"] = gdf.geometry.buffer(10)
gdf = gdf.set_geometry("buffered")

assert gdf.active_geometry_name == "buffered"
assert gdf.geometry.name == "buffered"

gdf = gdf.rename_geometry("analysis_geometry")
```

Important distinctions:

- `gdf.geometry` always returns the active geometry, not necessarily a column
  literally named `"geometry"`.
- `rename_geometry()` updates the active-column bookkeeping. A plain pandas
  `rename(columns=...)` must be followed by `set_geometry()`.
- A `GeoDataFrame` can hold multiple geometry columns with different CRS
  metadata. Switching the active column switches the CRS exposed as `gdf.crs`.
- Ordinary vector formats generally support only one geometry per layer.
  GeoParquet and Feather can preserve multiple geometry columns.
- GeoPandas 1.0 changed `set_geometry(named_series)`: the Series name becomes
  the active column name and the old geometry column is preserved. Avoid the
  deprecated `drop=` parameter; rename/drop explicitly.

Check every geometry column independently:

```python
geometry_columns = [
    name for name, dtype in gdf.dtypes.items() if str(dtype) == "geometry"
]
column_crs = {name: gdf[name].crs for name in geometry_columns}
```

## Missing, empty, and invalid are different

Treat these states separately:

| State | Test | Meaning |
|---|---|---|
| Missing | `series.isna()` | Unknown geometry, represented by `None` |
| Empty | `series.is_empty` | A geometry object with no coordinates |
| Invalid | `~series.is_valid` after excluding missing | Coordinates violate topology rules |

```python
missing = gdf.geometry.isna()
empty = gdf.geometry.is_empty
invalid = (~missing) & (~empty) & (~gdf.geometry.is_valid)
usable = ~(missing | empty | invalid)
```

Missing values generally propagate through element-wise operations and are
ignored by reductions such as `union_all()`. Empty geometries participate as
geometries: they may have area `0.0` and remain empty after intersection.
Never use only `dropna()` to remove unusable geometries.

## Index alignment

Binary geometry methods are **row-wise**, not all-pairs operations. With a
GeoSeries argument, `align=None` defaults to label alignment:

```python
left = gpd.GeoSeries([Point(0, 0), Point(1, 1)], index=["a", "b"])
right = gpd.GeoSeries([Point(1, 1), Point(0, 0)], index=["b", "a"])

by_label = left.intersects(right, align=True)
by_position = left.intersects(right, align=False)
```

Use `align=False` only after proving equal lengths and intended row order.
GeoPandas 1.0 raises on some unaligned pandas Series method arguments to avoid
ambiguous automatic alignment. For all-pairs matching use a spatial join or
spatial-index query.

Assignment also aligns by index:

```python
result = gdf.copy()
derived = result.geometry.buffer(10)
result.loc[:, "buffered"] = derived  # label-aligned
```

Reset or preserve indices deliberately before positional work. Never assume the
pandas index is a stable feature identifier.

## Feature identity and duplicate controls

Keep a non-null, stable feature-ID column across reads, joins, explode,
overlay, dissolve, and exports:

```python
ids = gdf["feature_id"]
if ids.isna().any() or ids.duplicated(keep=False).any():
    raise ValueError("feature_id must be non-null and unique for this workflow")
```

Cardinality-changing operations need explicit provenance:

- `explode(ignore_index=False, index_parts=False)` defaults to no part-level
  MultiIndex in GeoPandas 1.0+. Create a part number if parts need identity.
- Spatial joins can repeat either side; retain both source IDs.
- Overlay can split one feature into many. Add source IDs before overlay and
  generate a derived ID afterward.
- Dissolve intentionally combines IDs; record group keys and aggregation rules.
- `pd.concat` requires compatible geometry-column CRS and can preserve duplicate
  indices unless `ignore_index=True`.

## Geometry type and dimensionality

`geom_type`, `has_z`, and (with Shapely 2.1) `has_m` describe different
properties. Mixed geometry types are valid in memory but can break overlay or
export contracts. Z and M ordinates are not used by GeoPandas' planar topology:

```python
summary = {
    "types": gdf.geometry.geom_type.value_counts(dropna=False).to_dict(),
    "has_z": int(gdf.geometry.has_z.sum()),
    "has_m": int(gdf.geometry.has_m.sum()),
}
```

Do not silently drop Z/M. If a target format or operation is 2D-only, record the
loss and create a new derived artifact.

## Copying and conversion

- Use `gdf.copy()` before replacing an active geometry.
- Call `merge()` from the GeoDataFrame side; `plain_df.merge(gdf, ...)` can
  return a non-spatial DataFrame.
- Reading a non-spatial layer with `read_file()` returns a pandas DataFrame in
  GeoPandas 1.0+.
- `np.asarray(gdf.geometry)` or `gdf.geometry.to_numpy()` replaces removed
  access to `GeometryArray.data`.
- Do not serialize geometries with pickle for exchange. Use GeoPackage,
  GeoParquet, WKB, or WKT with an explicit CRS contract.

## Minimum structure audit

Record, without emitting coordinates or identifiers:

1. row and column counts;
2. active and additional geometry-column names;
3. CRS per geometry column;
4. counts of missing, empty, invalid, Z/M, and each geometry type;
5. index uniqueness and stable-ID null/duplicate counts;
6. source hash, parser/driver, package/native versions, and operation timestamp.

The bundled `scripts/vector_inventory.py` emits a redacted metadata inventory;
`scripts/geometry_validity_report.py` adds bounded geometry-state counts.

## Sources (verified 2026-10-01)

- [GeoPandas data structures](https://geopandas.org/en/stable/docs/user_guide/data_structures.html).
- [GeoSeries API](https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoSeries.html).
- [GeoDataFrame API](https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoDataFrame.html).
- [Missing and empty geometries](https://geopandas.org/en/stable/docs/user_guide/missing_empty.html).
- [GeoSeries.intersects alignment](https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoSeries.intersects.html).
- [GeoPandas 1.0.0 release and migrations](https://github.com/geopandas/geopandas/releases/tag/v1.0.0) — released 2024-06-24.
