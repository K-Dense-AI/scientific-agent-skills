# Spatial joins, overlay, clip, and dissolve

Spatial operations can multiply, split, or merge records. Define geometry
semantics and expected cardinality before running them, then audit both.

## Shared preflight

For each input:

1. preserve a non-null stable feature-ID column;
2. count duplicate IDs and duplicate pandas indices;
3. require CRS and reproject to a common, justified CRS;
4. count null, empty, invalid, mixed, and Z/M geometries;
5. validate precision/accuracy compatibility;
6. state whether boundary contact should count;
7. state the expected one-to-one, one-to-many, many-to-one, or many-to-many
   relationship.

GeoPandas operations are planar and ignore Z. Geographic longitude/latitude is
not suitable for distance/nearest work.

## Attribute joins

Call `merge` from the spatial object so geometry dtype and CRS are retained:

```python
result = zones.merge(
    attributes,
    on="zone_id",
    how="left",
    validate="one_to_one",
    indicator=True,
)
```

Use pandas `validate=` whenever the key contract is known. Before merging, audit
null/duplicate keys on both sides. Afterward, count `_merge` categories and
verify row count. A pandas index is not a feature key.

## Binary-predicate spatial joins

GeoPandas 1.2.0 signature:

```python
joined = left.sjoin(
    right,
    how="inner",
    predicate="intersects",
    distance=None,
    on_attribute=None,
)
```

`predicate` is evaluated directionally from each left geometry against right
geometries. Query available values from
`left.sindex.valid_query_predicates`.

Common choices:

- point-in-polygon strict interior: points on polygon boundaries do not satisfy
  `within`;
- point in polygon including boundary: use `covered_by` for points on the
  left and polygons on the right; reversing the frames permits `covers`;
- any shared boundary/interior: `intersects`;
- boundary-only relationships: `touches`;
- distance threshold: `dwithin`.

`dwithin` requires `distance`. It may be a scalar or a one-dimensional array
with one value per **left row**; values are CRS units:

```python
joined = left.sjoin(
    right,
    predicate="dwithin",
    distance=500,
)
```

`on_attribute="category"` (or a list/tuple) adds equality on columns present in
both frames after the spatial predicate. It is a restriction, not a substitute
for checking nulls, normalization, and duplicates in the attribute.

### Geometry and index retention

- `how="left"` keeps left keys and only left geometry.
- `how="right"` keeps right keys and only right geometry.
- `how="inner"` keeps matching pairs and only left geometry.
- GeoPandas 1.0 preserves a named right index as that output column name;
  otherwise output often uses `index_right`. Do not hard-code that name as a
  permanent ID.

Every qualifying pair produces a row. One left feature intersecting three right
features yields three rows. Empty/null geometries do not produce predicate
matches.

### Cardinality audit

Add internal unique row numbers before joining; never expose user IDs in a
public report:

```python
left_work = left.reset_index(drop=True).assign(_left_row=lambda x: range(len(x)))
right_work = right.reset_index(drop=True).assign(_right_row=lambda x: range(len(x)))

pairs = left_work[["_left_row", left_work.geometry.name]].sjoin(
    right_work[["_right_row", right_work.geometry.name]],
    predicate="intersects",
    how="inner",
)

left_multiplicity = pairs.groupby("_left_row").size()
right_multiplicity = pairs.groupby("_right_row").size()
```

Report pair count, matched/unmatched counts on both sides, and counts with
multiple matches. Compare these to the declared contract. The bundled
`scripts/spatial_join_audit.py` implements this with redacted aggregate output.

## Nearest spatial joins

```python
nearest = left.sjoin_nearest(
    right,
    how="left",
    max_distance=1_000,
    distance_col="distance_crs_units",
    exclusive=False,
)
```

Key semantics:

- distance and `max_distance` use CRS units;
- geographic CRS results are inaccurate;
- `max_distance > 0` can substantially reduce work and limits accepted matches;
- all equidistant nearest or intersecting neighbors are returned, so one input
  can produce multiple rows;
- `exclusive=True` excludes geometrically equal nearest candidates;
- GeoPandas `sjoin_nearest` has no `k=` argument. For k-nearest behavior use a
  separately designed spatial-index/neighbor workflow and define tie handling.

Never silently keep the first tie. Report tie counts and specify a deterministic
domain rule if one result must be selected.

## Overlay

```python
result = left.overlay(
    right,
    how="intersection",
    keep_geom_type=False,
    make_valid=False,
)
```

Modes:

| `how` | Result |
|---|---|
| `intersection` | Areas/parts shared by both |
| `union` | All partitioned parts with attributes from either/both |
| `identity` | All left parts split by right |
| `difference` | Left minus right |
| `symmetric_difference` | Parts in exactly one input |

Constraints and choices:

- Each input must have a uniform supported family: (Multi)Polygon,
  (Multi)Point, or line/LinearRing family.
- Inputs need the same CRS.
- `make_valid=True` repairs invalid inputs and may change types; pre-audit repair
  is more traceable. With `False`, invalid inputs raise.
- `keep_geom_type=None` behaves as `True` and warns when dropping other result
  types. Set it explicitly and count dropped/type-changed results.
- Union-like modes place `NaN` in attributes absent from one side.
- Near-coincident boundaries and precision mismatch produce slivers. Use a
  justified precision model, quantify small parts, and validate area balance.

Always keep source IDs from both inputs. Overlay can split one source feature
into many derived records.

## Clip

```python
clipped = gpd.clip(
    features,
    mask,
    keep_geom_type=False,
    sort=False,
)
```

- Both layers must share CRS.
- Multiple mask geometries are dissolved before intersection, so mask
  attributes are not transferred.
- A four-number `(minx, miny, maxx, maxy)` mask activates a fast rectangle
  path. It is possibly dirty, does not guarantee valid output, and can omit a
  line that collapses to a point.
- `keep_geom_type=False` retains mixed-dimensional outputs; set deliberately.
- `sort=False` does not promise source order. Preserve IDs and sort explicitly
  if order is part of the contract.

Validate clip output. Use overlay intersection when mask attributes or more
auditable topology are required.

## Dissolve

`dissolve` performs `groupby.agg` on attributes and `union_all` on geometry:

```python
dissolved = parcels.dissolve(
    by="region_id",
    aggfunc={
        "population": "sum",
        "source_date": "max",
    },
    as_index=False,
    dropna=False,
    method="unary",
    grid_size=0.01,
)
```

Avoid the default `aggfunc="first"` for meaningful attributes. Specify every
aggregation and its units. Decide whether null group keys should be dropped
(`dropna=True`) or retained as a group (`False`).

Union methods:

- `unary`: robust general default; supports `grid_size`;
- `coverage`: fast only for proven non-overlapping, edge-matched polygons and
  may produce invalid output otherwise;
- `disjoint_subset`: Shapely >=2.1, useful for disjoint partitions.

For coverage mode, run `is_valid_coverage()` first. After dissolve, compare
group counts, summed attributes, validity, empty output, and area in a suitable
projected CRS.

## Spatial index

GeoPandas uses Shapely's spatial index automatically for joins, clip, and
overlay. Direct queries are candidate/predicate operations:

```python
predicate_names = gdf.sindex.valid_query_predicates
indices = gdf.sindex.query(query_geometry, predicate="intersects")
```

GeoPandas 1.0 removed `sindex.query_bulk`; use `query`. GeoPandas 1.1 supports
indices, dense boolean, and optional SciPy sparse boolean output formats. For array input, `output_format="indices"` returns a `(2, n)` integer array:
row 0 indexes input/query geometries and row 1 indexes the tree geometries.
Dense/sparse boolean output is `(len(tree), len(query))`; scalar queries yield
a one-dimensional result. Set the format explicitly and preserve this orientation.

Spatial indexing does not fix CRS, invalid geometry, distance units, predicate
direction, or cardinality.

## Area and distance checks

For planar metrics:

```python
if gdf.crs is None or gdf.crs.is_geographic:
    raise ValueError("Use a justified projected CRS")

area = gdf.geometry.area
length = gdf.geometry.length
distance = gdf.geometry.distance(reference_geometry)
```

Confirm axis unit and conversion factor before labeling values. For
large/global or cross-zone work, use a geodesic design instead.

## Provenance checklist

Record:

- source hashes, layer names, stable IDs, input row/state counts;
- source and operation CRS, units, and transform pipeline;
- predicate direction, boundary semantics, distance/max-distance;
- join type, attribute restrictions, expected and observed cardinality;
- validity repair, precision grid, overlay/union method;
- mask dissolve/rectangle choice, dissolve aggregations;
- output row/type/state counts and new artifact hash.

## Sources (verified 2026-10-01)

- [GeoPandas merging data guide](https://geopandas.org/en/stable/docs/user_guide/mergingdata.html).
- [geopandas.sjoin](https://geopandas.org/en/stable/docs/reference/api/geopandas.sjoin.html).
- [geopandas.sjoin_nearest](https://geopandas.org/en/stable/docs/reference/api/geopandas.sjoin_nearest.html).
- [geopandas.overlay](https://geopandas.org/en/stable/docs/reference/api/geopandas.overlay.html).
- [geopandas.clip](https://geopandas.org/en/stable/docs/reference/api/geopandas.clip.html).
- [GeoDataFrame.dissolve](https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoDataFrame.dissolve.html).
- [GeoPandas set operations guide](https://geopandas.org/en/stable/docs/user_guide/set_operations.html).
- [GeoPandas aggregation with dissolve](https://geopandas.org/en/stable/docs/user_guide/aggregation_with_dissolve.html).
