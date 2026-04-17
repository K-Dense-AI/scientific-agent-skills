# SIMBAD TAP/ADQL Reference

SIMBAD provides a TAP (Table Access Protocol) service that accepts ADQL (Astronomical Data Query Language) queries. ADQL is a SQL-like language defined by the International Virtual Observatory Alliance (IVOA) with extensions for astronomical spatial operations.

## TAP Endpoint

```
POST https://simbad.cds.unistra.fr/simbad/sim-tap/sync
Content-Type: application/x-www-form-urlencoded

Parameters:
  REQUEST=doQuery
  LANG=ADQL
  QUERY=<adql query>
  FORMAT=json|votable|csv|tsv
  MAXREC=<max rows>
```

## Core Tables

### `basic` — Main Object Table

The primary table containing one row per astronomical object.

| Column | Type | Description |
|--------|------|-------------|
| `oid` | BIGINT | Internal object identifier (primary key) |
| `main_id` | VARCHAR | Primary object identifier |
| `ra` | DOUBLE | Right Ascension in degrees (ICRS) |
| `dec` | DOUBLE | Declination in degrees (ICRS) |
| `otype` | VARCHAR | Condensed object type code |
| `sp_type` | VARCHAR | Spectral type |
| `plx_value` | DOUBLE | Parallax in milliarcseconds |
| `plx_err` | DOUBLE | Parallax error |
| `pmra` | DOUBLE | Proper motion in RA (mas/yr) |
| `pmdec` | DOUBLE | Proper motion in Dec (mas/yr) |
| `rvz_radvel` | DOUBLE | Radial velocity (km/s) |
| `rvz_err` | DOUBLE | Radial velocity error |
| `galdim_majaxis` | DOUBLE | Galaxy major axis (arcmin) |
| `galdim_minaxis` | DOUBLE | Galaxy minor axis (arcmin) |
| `galdim_angle` | DOUBLE | Galaxy position angle (degrees) |

### `ident` — Identifier Table

All known identifiers for each object. An object can have many identifiers across different catalogs.

| Column | Type | Description |
|--------|------|-------------|
| `oidref` | BIGINT | Reference to `basic.oid` |
| `id` | VARCHAR | Identifier string |

### `flux` — Photometric Measurements

Flux/magnitude measurements in various photometric bands.

| Column | Type | Description |
|--------|------|-------------|
| `oidref` | BIGINT | Reference to `basic.oid` |
| `filter` | VARCHAR | Filter name (U, B, V, R, I, J, H, K, u, g, r, i, z, G, etc.) |
| `flux` | DOUBLE | Magnitude value |
| `flux_err` | DOUBLE | Magnitude error |
| `bibcode` | VARCHAR | Source reference bibcode |

### `mesDistance` — Distance Measurements

Published distance measurements.

| Column | Type | Description |
|--------|------|-------------|
| `oidref` | BIGINT | Reference to `basic.oid` |
| `dist` | DOUBLE | Distance value |
| `unit` | VARCHAR | Distance unit (pc, kpc, Mpc) |
| `minus_err` | DOUBLE | Lower error |
| `plus_err` | DOUBLE | Upper error |
| `method` | VARCHAR | Measurement method |
| `bibcode` | VARCHAR | Source reference |

### `has_ref` — Bibliographic References

Links objects to their bibliographic references.

| Column | Type | Description |
|--------|------|-------------|
| `oidref` | BIGINT | Reference to `basic.oid` |
| `oidbibref` | BIGINT | Reference to `ref.oidbib` |

### `ref` — Reference Details

| Column | Type | Description |
|--------|------|-------------|
| `oidbib` | BIGINT | Bibliography object ID |
| `bibcode` | VARCHAR | ADS bibcode |
| `title` | VARCHAR | Paper title |
| `journal` | VARCHAR | Journal name |
| `year` | INTEGER | Publication year |

### `otypedef` — Object Type Definitions

Lookup table for the object type classification hierarchy.

| Column | Type | Description |
|--------|------|-------------|
| `otype` | VARCHAR | Object type code |
| `description` | VARCHAR | Human-readable description |

## ADQL Syntax

### Basic SELECT

```sql
SELECT main_id, ra, dec, otype
FROM basic
WHERE otype = 'Star'
LIMIT 10
```

### TOP N (Alternative to LIMIT)

```sql
SELECT TOP 10 main_id, ra, dec
FROM basic
WHERE otype = 'Galaxy'
```

### WHERE Clauses

```sql
-- Numeric comparisons
WHERE plx_value > 50
WHERE rvz_radvel BETWEEN -100 AND 100

-- String matching
WHERE main_id = 'M  31'
WHERE sp_type LIKE 'O%'
WHERE otype IN ('Star', 'WD*', 'Pulsar')

-- NULL handling
WHERE plx_value IS NOT NULL
WHERE sp_type IS NOT NULL
```

### JOINs

```sql
-- Get V-band magnitudes with object data
SELECT b.main_id, b.ra, b.dec, b.otype, f.flux AS Vmag
FROM basic AS b
JOIN flux AS f ON b.oid = f.oidref
WHERE f.filter = 'V'
  AND f.flux < 6.0
ORDER BY f.flux ASC

-- Get all identifiers for an object
SELECT b.main_id, i.id
FROM basic AS b
JOIN ident AS i ON b.oid = i.oidref
WHERE b.main_id = 'M  31'

-- Get distance measurements
SELECT b.main_id, d.dist, d.unit, d.method
FROM basic AS b
JOIN mesDistance AS d ON b.oid = d.oidref
WHERE b.main_id = 'M  31'
```

### Spatial Queries

ADQL supports geometric predicates from the IVOA standard:

#### Cone Search (CONTAINS + CIRCLE)

Find objects within a radius of a point:

```sql
SELECT main_id, ra, dec, otype
FROM basic
WHERE CONTAINS(
    POINT('ICRS', ra, dec),
    CIRCLE('ICRS', 83.633, 22.014, 0.5)
) = 1
```

Parameters: `CIRCLE('ICRS', center_ra_deg, center_dec_deg, radius_deg)`

#### Box Search (CONTAINS + BOX)

```sql
SELECT main_id, ra, dec, otype
FROM basic
WHERE CONTAINS(
    POINT('ICRS', ra, dec),
    BOX('ICRS', 180.0, 0.0, 10.0, 5.0)
) = 1
```

Parameters: `BOX('ICRS', center_ra, center_dec, width_deg, height_deg)`

#### Polygon Search

```sql
SELECT main_id, ra, dec
FROM basic
WHERE CONTAINS(
    POINT('ICRS', ra, dec),
    POLYGON('ICRS', 10.0, 40.0, 12.0, 40.0, 12.0, 42.0, 10.0, 42.0)
) = 1
```

#### Distance Between Points

```sql
SELECT main_id, ra, dec,
       DISTANCE(POINT('ICRS', ra, dec),
                POINT('ICRS', 10.68458, 41.26917)) AS dist_deg
FROM basic
WHERE CONTAINS(
    POINT('ICRS', ra, dec),
    CIRCLE('ICRS', 10.68458, 41.26917, 0.1)
) = 1
ORDER BY dist_deg ASC
```

### Aggregation

```sql
-- Count objects by type
SELECT otype, COUNT(*) AS n
FROM basic
GROUP BY otype
ORDER BY n DESC

-- Average parallax by spectral class
SELECT SUBSTRING(sp_type, 1, 1) AS sp_class,
       AVG(plx_value) AS mean_plx,
       COUNT(*) AS n
FROM basic
WHERE sp_type IS NOT NULL
  AND plx_value IS NOT NULL
GROUP BY sp_class
ORDER BY sp_class
```

## Common Query Patterns

### Find Nearby Stars with Full Data

```sql
SELECT b.main_id, b.ra, b.dec, b.sp_type,
       b.plx_value, b.pmra, b.pmdec, b.rvz_radvel,
       f.flux AS Vmag
FROM basic AS b
LEFT JOIN flux AS f ON b.oid = f.oidref AND f.filter = 'V'
WHERE b.otype = 'Star'
  AND b.plx_value > 100
ORDER BY b.plx_value DESC
```

### Find Galaxies in a Sky Region with Redshifts

```sql
SELECT main_id, ra, dec, otype, rvz_radvel,
       galdim_majaxis, galdim_minaxis
FROM basic
WHERE CONTAINS(
    POINT('ICRS', ra, dec),
    CIRCLE('ICRS', 185.0, 12.7, 2.0)
) = 1
  AND otype = 'Galaxy'
  AND rvz_radvel IS NOT NULL
ORDER BY rvz_radvel ASC
```

### Cross-Match Identifiers Between Catalogs

```sql
SELECT b.main_id,
       i1.id AS hipparcos_id,
       i2.id AS gaia_id
FROM basic AS b
JOIN ident AS i1 ON b.oid = i1.oidref AND i1.id LIKE 'HIP %'
JOIN ident AS i2 ON b.oid = i2.oidref AND i2.id LIKE 'Gaia DR3%'
WHERE b.otype = 'Star'
  AND b.plx_value > 50
```

### Get Bibliography for Objects in a Region

```sql
SELECT b.main_id, r.bibcode, r.title, r.year
FROM basic AS b
JOIN has_ref AS hr ON b.oid = hr.oidref
JOIN ref AS r ON hr.oidbibref = r.oidbib
WHERE CONTAINS(
    POINT('ICRS', b.ra, b.dec),
    CIRCLE('ICRS', 83.633, -5.375, 0.5)
) = 1
  AND r.year >= 2020
ORDER BY r.year DESC
```

### Object Type Statistics in a Region

```sql
SELECT otype, COUNT(*) AS count
FROM basic
WHERE CONTAINS(
    POINT('ICRS', ra, dec),
    CIRCLE('ICRS', 266.417, -29.008, 1.0)
) = 1
GROUP BY otype
HAVING COUNT(*) > 5
ORDER BY count DESC
```

## Python Example: Full TAP Workflow

```python
import requests
import json

def simbad_tap_query(adql, max_results=100, fmt="json"):
    """Execute an ADQL query on SIMBAD via TAP."""
    response = requests.post(
        "https://simbad.cds.unistra.fr/simbad/sim-tap/sync",
        data={
            "REQUEST": "doQuery",
            "LANG": "ADQL",
            "QUERY": adql,
            "FORMAT": fmt,
            "MAXREC": max_results,
        },
        timeout=60,
    )
    response.raise_for_status()

    if fmt == "json":
        return response.json()
    return response.text


# Example: nearest stars with complete kinematics
results = simbad_tap_query("""
    SELECT TOP 50 main_id, ra, dec, sp_type,
           plx_value, pmra, pmdec, rvz_radvel
    FROM basic
    WHERE plx_value > 200
      AND pmra IS NOT NULL
      AND rvz_radvel IS NOT NULL
    ORDER BY plx_value DESC
""")

metadata = results.get("metadata", [])
col_names = [m["name"] for m in metadata]

print(" | ".join(col_names))
print("-" * 80)
for row in results.get("data", []):
    print(" | ".join(str(v) for v in row))
```

## Limitations

- **Synchronous TAP only**: SIMBAD supports `sync` mode (results returned directly). For very large queries, consider async TAP or use `MAXREC` to paginate.
- **No upload tables**: SIMBAD TAP does not support uploading user tables for cross-matching. Use astroquery or CDS XMatch service for that.
- **Coordinate precision**: SIMBAD coordinates are compiled from heterogeneous sources; check the `coo_qual` field for quality indicators.
- **Timeout**: Queries exceeding ~60 seconds may time out. Add `TOP` or tighten `WHERE` clauses for complex queries.

## Resources

- SIMBAD TAP Help: https://simbad.cds.unistra.fr/simbad/tap/help/
- ADQL 2.1 Specification: https://www.ivoa.net/documents/ADQL/20231215/
- SIMBAD Table Descriptions: https://simbad.cds.unistra.fr/simbad/tap/taptable.htx
- TAP Protocol: https://www.ivoa.net/documents/TAP/
