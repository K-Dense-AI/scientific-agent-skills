# Vector I/O, GeoParquet, Arrow, and PostGIS

GeoPandas 1.x defaults to pyogrio for vector-file I/O. pyogrio and Fiona are
bindings to GDAL/OGR; actual formats, options, and behavior depend on the
installed native GDAL and drivers.

## Local-only intake policy

Do not automatically pass any of these to GeoPandas/GDAL:

- `http://`, `https://`, `s3://`, `gs://`, Azure, or another remote URI;
- GDAL `/vsicurl/`, `/vsis3/`, `/vsizip/`, chained virtual filesystems, or
  pyogrio `zip+...` paths;
- ZIP/KMZ/TAR/GZ/7z/RAR or nested archives;
- macro-enabled office files or an untrusted permissive driver;
- a user-supplied PostGIS connection string.

GeoPandas officially supports URLs and GDAL supports network/archive virtual
filesystems, but that capability crosses network, decompression, parser, and
credential trust boundaries. Obtain explicit approval, verify source/hash and
size out of band, unpack in a sandbox with resource limits, then process an
allowlisted local regular file.

The bundled CLIs reject URL/VSI/archive syntax, symlinks, path traversal, and
non-allowlisted suffixes.

## Inspect before reading features

For GDAL-backed formats:

```python
from pathlib import Path
import pyogrio
import geopandas

path = Path("approved/input.gpkg")
if not path.is_file() or path.is_symlink():
    raise ValueError("Expected a vetted local regular file")

layers = pyogrio.list_layers(path)
info = pyogrio.read_info(
    path, layer="approved_layer", force_feature_count=False, force_total_bounds=False
)
drivers = pyogrio.list_drivers()
```

GeoPandas 1.2 adds `geopandas.read_file_info(path, layer=...)`, a small wrapper
with only those two parameters. Use `pyogrio.read_info` directly for options
such as `force_feature_count` and `force_total_bounds`; the wrapper rejects them.

Record:

- primary-file hash and byte size (a Shapefile hash does not cover sidecars);
- driver, layer, declared feature count, fields/dtypes, encoding, geometry type;
- CRS and whether bounds were present, but redact precise bounds by default;
- `pyogrio.__gdal_version__`, `pyogrio.__gdal_geos_version__`, Shapely GEOS,
  pyproj PROJ, package versions, and enabled driver capabilities.

In pyogrio 0.13, `list_drivers()` reports capabilities containing `r`, `w`,
and/or `a` (append, GDAL >=3.11); `list_drivers(append=True)` filters for known
append support. A listed driver is not proof every field/geometry is supported. Treat drivers as
an allowlist, not merely a discovered list.

## `read_file`

Stable signature:

```python
gdf = geopandas.read_file(
    filename,
    bbox=None,
    mask=None,
    columns=None,
    rows=None,
    engine="pyogrio",
    use_arrow=True,
)
```

Rules:

- `bbox` and `mask` are mutually exclusive.
- With pyogrio, a bbox tuple must already be in the dataset CRS. Fiona can
  reproject a GeoSeries/GeoDataFrame bbox; do not depend on engine-specific
  implicit behavior.
- A mask must have an explicit CRS compatible with the source.
- `columns=[]` reads geometry without attributes; `ignore_geometry=True`
  returns a pandas DataFrame.
- `rows=n` reads the first n rows; `rows=slice(a, b)` reads a slice.
- `where=` is evaluated by a driver SQL dialect. Do not concatenate untrusted
  expressions.
- Encoding auto-detection can fail; set a verified encoding explicitly.
- `use_arrow=True` requires PyArrow and speeds pyogrio bulk transfer, but does
  not change parser trust or correctness requirements.
- Bound both file bytes and features. Some drivers cannot cheaply report a
  count; read at most `limit + 1` and fail closed when the limit is exceeded.

GeoPandas may use HTTP range requests or download an entire URL in memory.
This skill therefore does not include remote-read examples.

## Filters are not always exact

pyogrio documents:

- `bbox`/`mask` coordinates must use the dataset CRS;
- when GDAL is built with GEOS, geometry intersection filtering is exact;
- without GEOS, filters can return features whose **bounding boxes** intersect,
  requiring a second exact predicate check;
- Arrow reads involving skip/max may read batches beyond the requested slice
  before slicing;
- feature IDs are driver-specific and may start at 0, 1, or another value.

Do not treat driver FID as a portable stable feature ID.

## Writing traditional vector formats

Write a new path and reopen it:

```python
output = Path("derived/result.gpkg")
if output.exists() or output.is_symlink():
    raise FileExistsError("Choose a new output path")

gdf.to_file(
    output,
    layer="result",
    driver="GPKG",
    engine="pyogrio",
    index=False,
    use_arrow=True,
)

roundtrip = geopandas.read_file(output, layer="result", engine="pyogrio")
```

Never use implicit overwrite/append. Driver behavior varies and multi-file
formats complicate atomic writes.

### Format tradeoffs

- **GeoPackage**: good general local interchange; multiple layers, one geometry
  column per layer, SQL-backed metadata.
- **GeoJSON**: broadly interoperable but normally WGS84 longitude/latitude,
  limited type fidelity, text-heavy, and easy to leak precise coordinates.
- **Shapefile**: legacy multi-file format with field-name, type, null, encoding,
  geometry, and size constraints. Avoid for new work.
- **FlatGeobuf**: efficient stream/spatial-index format, but interoperability
  still depends on driver versions.
- **GeoParquet**: efficient columnar storage with multiple geometry columns and
  explicit geospatial metadata.

Traditional formats often cannot store lists, structs, arbitrary objects, or
multiple geometry columns. Plan conversions and reject silent loss.

## GeoParquet and Feather

```python
gdf.to_parquet(
    "derived/result.parquet",
    index=False,
    compression="snappy",
    geometry_encoding="WKB",
    write_covering_bbox=False,
    schema_version="1.1.0",
)

roundtrip = geopandas.read_parquet(
    "derived/result.parquet",
    columns=["feature_id", "geometry"],
)
```

GeoPandas 1.2.0 write semantics:

- all geometry columns are preserved;
- default `geometry_encoding="WKB"` maximizes interoperability;
- default supported stable schema is **1.1.0**; request 1.0.0 explicitly for
  consumers that require the older metadata contract;
- `geometry_encoding="geoarrow"` requires GeoParquet 1.1.0, supports
  single-geometry native encodings, and is still described as experimental;
- `write_covering_bbox=True` adds a per-row `bbox` column and 1.1 covering
  metadata. It costs compute and may reveal precise extents;
- `schema_version` replaces the removed/deprecated old `version=` usage;
- `index=None` writes non-RangeIndex values as columns and stores RangeIndex as
  metadata. Use an explicit stable feature-ID column instead.

Read semantics:

- selecting no geometry columns raises; use `pandas.read_parquet` for a
  non-spatial result;
- if the stored primary geometry is omitted, the first selected geometry
  becomes active;
- `bbox=` filtering works with covering metadata, native `point` encoding,
  or GeoParquet 2.0 logical geometry types. Bounding-box intersection can admit
  false positives for non-point geometries; apply an exact predicate afterward;
- if GeoParquet `crs` metadata is **missing**, the specification default is
  `OGC:CRS84`;
- an explicit `crs: null` means unknown/undefined, which is different;
- WKB/native coordinates are x/y regardless of authority axis order.
- 1.2 writes and restores JSON-serializable `gdf.attrs`. Review or clear these
  attributes before publication; paths, source IDs, and study notes can leak
  through file metadata even when columns are clean.

GeoParquet 1.1 metadata requires a `geo` JSON value, `primary_column`, and
metadata for every geometry column. Geometry columns must be root-level and may
be optional; native child coordinates cannot contain nulls. `edges` defaults to
`planar`. Feature identifiers are outside the core specification, so define and
document your own stable-ID metadata/column.

Do not use bbox covering for public sensitive-location data without
generalization and approval.

### GeoParquet 2.0 opt-in

GeoPandas 1.2 supports the **upcoming** 2.0.0 specification through
`schema_version="2.0.0"`. Writing needs PyArrow >=21 and uses WKB with the
Parquet Geometry logical type; `geometry_encoding="geoarrow"` is rejected.
The release supports bbox filtering without a separate covering column for
these files. Treat this as an explicit interoperability choice and test the
actual downstream reader. The bundled export planner deliberately supports
only stable 1.0/1.1 contracts; do not infer 2.0 support from planner success.

### Arrow in memory

GeoPandas 1.0 added `to_arrow()` and `from_arrow()` using GeoArrow extension
types. These improve interchange but do not make an array self-validating:
verify extension metadata, CRS, geometry encoding/type, nulls, and active
geometry after round-trip. GeoPandas 1.1 adds `to_pandas_kwargs` controls for
non-geometry Arrow conversion.

## PostGIS without credential leakage

The following PostGIS examples are illustrative; no live database was tested.
Required writing dependencies are SQLAlchemy, GeoAlchemy2, and psycopg/psycopg2.
Create connections from named secrets without embedding or logging a connection
URL:

```python
import os
from sqlalchemy import URL, create_engine

db_url = URL.create(
    "postgresql+psycopg",
    username=os.environ["GEOPANDAS_POSTGIS_USER"],
    password=os.environ["GEOPANDAS_POSTGIS_PASSWORD"],
    host=os.environ["GEOPANDAS_POSTGIS_HOST"],
    port=int(os.environ["GEOPANDAS_POSTGIS_PORT"]),
    database=os.environ["GEOPANDAS_POSTGIS_DATABASE"],
)
engine = create_engine(db_url)
```

Read only those named variables (or secret-manager equivalents). Never print
`db_url`, `engine.url`, exception payloads containing it, or the broader
environment.

Use parameterized values and trusted SQL identifiers:

```python
from sqlalchemy import text

query = text(
    "SELECT feature_id, geom FROM approved_schema.features "
    "WHERE category = :category"
)
chunks = geopandas.read_postgis(
    query,
    con=engine,
    geom_col="geom",
    params={"category": approved_category},
    chunksize=10_000,
)
```

`read_postgis` infers one CRS from the SRID of the first geometry and assigns it
to all rows unless `crs=` is supplied. Verify all geometries share the expected
SRID. With `chunksize`, it returns an iterator; validate every chunk and enforce
a total-row limit.

For writes:

```python
with engine.begin() as connection:
    gdf.to_postgis(
        "derived_features",
        con=connection,
        schema="approved_schema",
        if_exists="fail",
        index=False,
        chunksize=10_000,
    )
```

- Default to `if_exists="fail"`.
- `replace` drops an existing table and is destructive.
- Validate schema/table/geometry column names against an allowlist; do not
  interpolate user input.
- GeoPandas 1.1.2 fixed SQL injection through a geometry-column name; remain on
  a patched version and still validate identifiers. Version 1.1.4 added
  further hardening; 1.2.0 includes both fixes.
- Use least-privilege database roles and a transaction.

## Fiona-to-pyogrio migration

GeoPandas 1.0 changed the default engine from Fiona to pyogrio. Differences
include:

- schema/metadata keywords and driver options;
- writing attribute-only tables;
- handling empty geometries and unsupported field types;
- datetime resolution/timezone behavior;
- append and encoding behavior;
- error/warning text and filter behavior.

Set `engine=` explicitly for reproducibility and test round-trips before
migration. Do not assume identical outputs merely because both engines use GDAL.

## Export verification and provenance

For every output:

1. choose a new local path and explicit format/driver/layer;
2. record source hashes, source layer, stack/native versions, CRS, precision,
   repair, and transformation choices;
3. record field names/types/nullability, geometry columns/types, stable ID,
   index policy, encoding, dimensions, and expected losses;
4. write, then reopen with an independent code path when feasible;
5. compare row count, stable-ID set, null/empty/invalid/type counts, CRS, bounds
   at protected precision, and representative attribute values;
6. hash the completed artifact and store the audit separately.

Use `scripts/vector_inventory.py` for redacted intake and
`scripts/export_plan.py` for a non-executing output contract.

## Sources (verified 2026-10-01)

- [GeoPandas reading and writing files](https://geopandas.org/en/stable/docs/user_guide/io.html).
- [geopandas.read_file](https://geopandas.org/en/stable/docs/reference/api/geopandas.read_file.html).
- [GeoDataFrame.to_file](https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoDataFrame.to_file.html).
- [GeoDataFrame.to_parquet](https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoDataFrame.to_parquet.html).
- [geopandas.read_parquet](https://geopandas.org/en/stable/docs/reference/api/geopandas.read_parquet.html).
- [geopandas.read_postgis](https://geopandas.org/en/stable/docs/reference/api/geopandas.read_postgis.html).
- [GeoDataFrame.to_postgis](https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoDataFrame.to_postgis.html).
- [Fiona-to-pyogrio migration](https://geopandas.org/en/stable/docs/user_guide/fiona_to_pyogrio.html).
- [pyogrio introduction](https://pyogrio.readthedocs.io/en/stable/introduction.html).
- [pyogrio API](https://pyogrio.readthedocs.io/en/stable/api.html).
- [GeoParquet 1.1.0 specification](https://geoparquet.org/releases/v1.1.0/).
- [GeoArrow specification](https://github.com/geoarrow/geoarrow).
- [GeoPandas 1.1.2 security/bug-fix release](https://github.com/geopandas/geopandas/releases/tag/v1.1.2) — released 2025-12-22.
- [GeoPandas 1.2.0 Arrow implementation](https://github.com/geopandas/geopandas/blob/v1.2.0/geopandas/io/arrow.py).
- [pyogrio 0.13.0 metadata API source](https://github.com/geopandas/pyogrio/blob/v0.13.0/pyogrio/core.py).
