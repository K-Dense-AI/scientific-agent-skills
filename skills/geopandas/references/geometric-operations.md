# Geometric operations, validity, and precision

GeoPandas delegates geometry work to Shapely/GEOS. Operations are planar,
two-dimensional, and expressed in CRS coordinate units. Z/M ordinates may be
carried but are not part of topology.

## Preflight state

Count missing, empty, invalid, and mixed geometries separately before any
constructive or set operation:

```python
geometry = gdf.geometry
missing = geometry.isna()
empty = geometry.is_empty
invalid = (~missing) & (~empty) & (~geometry.is_valid)

state = {
    "rows": len(gdf),
    "missing": int(missing.sum()),
    "empty": int(empty.sum()),
    "invalid": int(invalid.sum()),
    "types": geometry.geom_type.value_counts(dropna=False).to_dict(),
}
```

`is_valid` concerns polygon/ring topology; points and lines are generally valid
unless malformed. `is_simple`, `is_ring`, and `minimum_clearance` answer
different questions.

### Redacted validity diagnostics

`is_valid_reason()` can include the coordinate of a defect, for example a
self-intersection. Precise coordinates can be sensitive. Aggregate only the
reason category before `[` and retain detailed diagnostics in a protected local
artifact:

```python
reason_category = (
    geometry[invalid]
    .is_valid_reason()
    .str.split("[", n=1)
    .str[0]
    .value_counts()
)
```

## Repair is a model change

GeoPandas 1.1 exposes Shapely 2.1 repair controls:

```python
repaired = geometry.make_valid(
    method="structure",
    keep_collapsed=True,
)
```

Methods:

- `linework` preserves every edge/vertex, nodes all rings, and reconstructs
  areas with even/odd parity. It can produce complex `GeometryCollection`
  output and requires `keep_collapsed=True`.
- `structure` repairs rings, merges shells, and subtracts holes. It assumes
  shell/hole categorization is meaningful, requires GEOS >=3.10, and can drop
  collapsed parts when `keep_collapsed=False`.

Repair can turn a polygon into a multipolygon, line, point, collection, or empty
geometry. Never replace source data in place. Create a new artifact and compare:

1. valid/invalid/null/empty counts;
2. geometry-type and dimensionality transitions;
3. component counts and collapsed outputs;
4. area/length changes in appropriate units;
5. stable feature IDs and row count;
6. downstream predicate/coverage behavior.

`overlay(make_valid=True)` also repairs invalid inputs, but that convenience can
hide type changes. Audit and repair explicitly for traceable work.

## Precision models

`set_precision(grid_size, mode=...)` rounds x/y to a grid in **CRS units**:

```python
snapped = geometry.set_precision(
    grid_size=0.01,
    mode="valid_output",
)
```

Shapely 2.1 modes:

- `valid_output` removes collapsed polygonal/linear elements and duplicate
  vertices while producing valid output;
- `pointwise` rounds independently, retains duplicate vertices, and may produce
  invalid output;
- `keep_collapsed` preserves collapsed linear elements but removes collapsed
  polygonal elements.

Consequences:

- features narrower/shorter than the grid may become empty;
- spikes and narrow sections can disappear or split polygons;
- duplicate vertices are normally removed;
- Z is not rounded;
- vertex/ring/order is canonicalized and must not be used as identity;
- inputs should be valid first;
- later operations use the higher precision (smaller grid size) of inputs.

Choose the grid from documented source resolution and error—not decimal
aesthetics. `0.001` degrees is not a universal metric tolerance.

For one union/dissolve, `grid_size=` can apply fixed precision without first
attaching a precision model:

```python
merged = geometry.union_all(method="unary", grid_size=0.01)
```

GeoPandas 1.2 also accepts `grid_size=` on row-wise `intersection`, `union`,
`difference`, and `symmetric_difference`. This does not add a `grid_size`
argument to `overlay`; snap valid inputs explicitly for that workflow.
`buffer(resolution=...)` is deprecated in 1.2; use `quad_segs=`.

Record whether precision was attached to inputs or applied only to an operation.

## `union_all` algorithms

GeoPandas 1.2.0 signature:

```python
geometry.union_all(method="unary", grid_size=None)
```

- `unary`: robust general-purpose algorithm; the only method supporting
  `grid_size`.
- `coverage`: optimized for non-overlapping edge-matched polygon coverages; it
  can return invalid geometry if polygons overlap.
- `disjoint_subset`: optimized when input can be divided into non-intersecting
  subsets; requires Shapely >=2.1 and may be slower when there is one subset.

Do not use `coverage` based on visual inspection:

```python
if not geometry.is_valid_coverage(gap_width=0.0):
    edges = geometry.invalid_coverage_edges(gap_width=0.0)
    raise ValueError("Not an edge-matched non-overlapping coverage")

merged = geometry.union_all(method="coverage")
```

`is_valid_coverage()` ignores non-polygon geometry and requires Shapely >=2.1.
If narrow gaps matter, select `gap_width` in justified projected units.
`simplify_coverage()` preserves shared boundaries for a valid coverage; ordinary
element-wise `simplify()` does not.

The old `unary_union` attribute is deprecated. Use `union_all()`.

## Constructive operations

All distance/tolerance arguments are CRS units:

```python
buffered = geometry.buffer(50, quad_segs=16)
simplified = geometry.simplify(5, preserve_topology=True)
densified = geometry.segmentize(max_segment_length=10)
centroids = geometry.centroid
inside_points = geometry.representative_point()
```

Correctness notes:

- Buffering geographic degrees does not create a fixed-metre buffer.
- Negative polygon buffers can collapse to empty.
- `centroid` may fall outside a concave polygon; `representative_point()` is
  guaranteed within the geometry but is not a centroid.
- `preserve_topology=True` protects each geometry's validity, not shared
  boundaries between adjacent features.
- `segmentize()` inserts vertices along planar segments; it does not create
  geodesic densification.
- Affine rotate/scale/translate/skew operations are coordinate-space transforms,
  not CRS transformations.

## Binary predicates

Predicates implement DE-9IM relationships and are directional:

| Predicate | Practical meaning |
|---|---|
| `intersects` | Boundaries or interiors share any point |
| `disjoint` | Share no point |
| `within` | Left geometry lies in right interior/boundary under DE-9IM |
| `contains` | Inverse direction of `within`; boundary-only point is not contained |
| `covers` | No point of right lies outside left; includes boundary cases |
| `covered_by` | Inverse of `covers` |
| `contains_properly` | Contains with no common boundary points |
| `touches` | Interiors do not meet, boundaries do |
| `crosses` | Interiors meet with lower-dimensional result |
| `overlaps` | Same-dimensional partial overlap, neither contains the other |
| `dwithin` | Planar distance is within the supplied CRS-unit threshold |

Do not describe `contains`, `covers`, and `intersects` as interchangeable.
Boundary-point tests are an important synthetic fixture.

Binary GeoSeries calls are one-to-one and index-aligned by default:

```python
matched = left.intersects(right, align=True)
```

They do not answer whether each left geometry intersects *any* right geometry.
Use `sjoin` or the spatial index for all-pairs matching.

## Overlay robustness and slivers

Overlay and intersection can create tiny slivers from precision mismatch,
near-coincident edges, or distinct source accuracy:

1. validate inputs and CRS;
2. quantify source precision/accuracy;
3. select a justified grid if snapping is appropriate;
4. run overlay with explicit `keep_geom_type`;
5. validate output and count type changes;
6. summarize area distribution and very small parts in projected units;
7. compare area conservation appropriate to the selected overlay mode.

Do not delete polygons below an arbitrary area threshold. A small polygon can be
legitimate, and thresholding can bias boundaries. Record any sliver rule and
retain pre-cleaning output.

## Equality and identity

- `geom_equals` is topological equality; coordinate order may differ.
- `geom_equals_exact(tolerance=...)` checks structural coordinate equality
  within tolerance.
- `geom_equals_identical` exposes Shapely's identical comparison in GeoPandas
  1.1 and includes coordinate/order details.
- `normalize()` can canonicalize ordering for reproducible comparisons, but a
  normalized WKB hash is still geometry identity, not stable feature identity.

## Post-operation validation

For every geometry-changing operation, record:

- operation and all parameters;
- source/target CRS and units;
- package and GEOS versions;
- null/empty/invalid/type/component counts before and after;
- row expansion/contraction and stable-ID mapping;
- precision model, repair method, collapsed-part policy;
- area/length conservation checks where meaningful;
- a new output path and source/output hashes.

The bundled `scripts/geometry_validity_report.py` provides bounded dry-run
counts and optional new-file repair without emitting geometries or coordinates.

## Sources (verified 2026-10-01)

- [GeoPandas geometric manipulations](https://geopandas.org/en/stable/docs/user_guide/geometric_manipulations.html).
- [GeoSeries.make_valid](https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoSeries.make_valid.html).
- [GeoSeries.union_all](https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoSeries.union_all.html).
- [GeoSeries.is_valid_coverage](https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoSeries.is_valid_coverage.html).
- [Shapely 2.1.2 make_valid](https://shapely.readthedocs.io/en/2.1.2/reference/shapely.make_valid.html).
- [Shapely 2.1.2 set_precision](https://shapely.readthedocs.io/en/2.1.2/reference/shapely.set_precision.html).
- [Shapely 2.1.2 union_all](https://shapely.readthedocs.io/en/2.1.2/reference/shapely.union_all.html).
- [GeoPandas 1.1.0 release](https://github.com/geopandas/geopandas/releases/tag/v1.1.0) — released 2025-06-01.
