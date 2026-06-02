# SIMBAD Astronomical Database (CDS Strasbourg)

SIMBAD contains data on over 17 million astronomical objects beyond the Solar System, including identifications, coordinates, photometry, proper motions, parallaxes, radial velocities, spectral types, and bibliographic references.

## Base URLs

**TAP endpoint (recommended):**
```
https://simbad.cds.unistra.fr/simbad/sim-tap/sync
```

**Script interface:**
```
https://simbad.cds.unistra.fr/simbad/sim-script
```

**Simple query endpoints:**
```
https://simbad.cds.unistra.fr/simbad/sim-id
https://simbad.cds.unistra.fr/simbad/sim-coo
```

## Authentication

No API key required. All endpoints are public.

## Key Endpoints

### 1. TAP Queries (ADQL — recommended for programmatic use)

```
POST /simbad/sim-tap/sync
Content-Type: application/x-www-form-urlencoded

Parameters:
  REQUEST=doQuery
  LANG=ADQL
  QUERY=<adql query>
  FORMAT=json|votable|csv|tsv
  MAXREC=<max rows>
```

| Parameter | Type   | Description |
|-----------|--------|-------------|
| `REQUEST` | string | `doQuery` |
| `LANG`    | string | `ADQL` |
| `FORMAT`  | string | `json`, `votable`, `csv`, `tsv`. |
| `QUERY`   | string | **Required.** ADQL query. |
| `MAXREC`  | int    | Max rows returned. Always set to avoid downloading millions of rows. |

**Example — look up object by name:**
```
https://simbad.cds.unistra.fr/simbad/sim-tap/sync?request=doQuery&lang=adql&format=json&query=SELECT basic.OID, ra, dec, main_id, otype FROM basic JOIN ident ON oid = ident.oidref WHERE id = 'M31'
```

**Example — cone search (objects within 5 arcmin of coordinates):**
```
https://simbad.cds.unistra.fr/simbad/sim-tap/sync?request=doQuery&lang=adql&format=json&query=SELECT TOP 50 main_id, ra, dec, otype FROM basic WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', 10.684, 41.269, 0.083)) = 1
```
Note: radius in CIRCLE is in degrees (5 arcmin = 0.083 deg).

**Example — objects by type (e.g., all pulsars):**
```
https://simbad.cds.unistra.fr/simbad/sim-tap/sync?request=doQuery&lang=adql&format=json&query=SELECT TOP 100 main_id, ra, dec, otype FROM basic WHERE otype = 'Pulsar'
```

### 2. Identifier Query (simple lookup)

```
GET /simbad/sim-id?Ident={name}&output.format=votable
```

| Parameter        | Type   | Description |
|------------------|--------|-------------|
| `Ident`          | string | **Required.** Object name (e.g., `M31`, `Sirius`, `NGC 1275`). |
| `output.format`  | string | `votable`, `html`. |

### 3. Coordinate Query

```
GET /simbad/sim-coo?Coord={coords}&Radius={radius}&Radius.unit={unit}&output.format=votable
```

| Parameter      | Type   | Description |
|----------------|--------|-------------|
| `Coord`        | string | **Required.** Coordinates, e.g., `10.684 +41.269` or `00 42 44 +41 16 09`. |
| `Radius`       | float  | Search radius. Default: 2. |
| `Radius.unit`  | string | `arcmin`, `arcsec`, `deg`. Default: `arcmin`. |
| `output.format`| string | `votable`, `html`. |

### 4. Script Interface (for multi-command queries)

```
POST /simbad/sim-script
Content-Type: application/x-www-form-urlencoded

Body: script=<script text>
```

A script consists of configuration lines followed by query commands:

```
output console=off script=off
format object "<format string>"
query id <object name>
```

**Query commands:**
- `query id <name>` — lookup by name (e.g., `query id M31`)
- `query coo <ra> <dec> radius=<value><unit>` — cone search (units: `d`=deg, `m`=arcmin, `s`=arcsec)
- `query id wildcard <pattern>` — wildcard search (e.g., `query id wildcard NGC 10*`)
- `query sample <criteria>` — criteria search (e.g., `query sample otype='Star' & Vmag < 5.0`)

**Multi-object queries** — include multiple `query id` lines in a single script:
```
output console=off script=off
format object "%IDLIST(1) | %COO(A D;ICRS) | %OTYPE"
query id M31
query id M42
query id M101
```

## Script Format Codes

Format codes define which fields appear in script output. Use inside `format object "..."`.

### Identification

| Code | Description | Example Output |
|------|-------------|----------------|
| `%IDLIST(1)` | Primary identifier | `M  31` |
| `%IDLIST` | All identifiers | `M  31, NGC  224, UGC  454, ...` |
| `%MAIN_ID` | Main identifier | `M  31` |

### Coordinates

| Code | Description | Example Output |
|------|-------------|----------------|
| `%COO(A D;ICRS)` | RA Dec ICRS (sexagesimal) | `00 42 44.330 +41 16 07.50` |
| `%COO(d d;ICRS)` | RA Dec decimal degrees | `10.6847083 +41.2687500` |
| `%COO(A D;GAL)` | Galactic coordinates | `121.1743 -21.5733` |

### Object Properties

| Code | Description | Example Output |
|------|-------------|----------------|
| `%OTYPE` | Object type (condensed) | `Galaxy` |
| `%SP` | Spectral type | `A1V` |
| `%MT` | Morphological type | `SA(s)b` |

### Photometry

| Code | Description |
|------|-------------|
| `%FLUXLIST(V)` | V-band magnitude |
| `%FLUXLIST(B)` | B-band magnitude |
| `%FLUXLIST(U;B;V;R;I)` | Multiple bands |
| `%FLUXLIST(J;H;K)` | Near-infrared bands |

### Kinematics

| Code | Description |
|------|-------------|
| `%PM` | Proper motion (mas/yr) |
| `%PLX` | Parallax (mas) |
| `%RV` | Radial velocity (km/s) |

### Predefined Format Levels

```
Basic:    "%IDLIST(1) | %COO(A D;ICRS) | %OTYPE"
Detailed: "%IDLIST(1) | %COO(A D;ICRS) | %OTYPE | %SP | %FLUXLIST(V)"
Full:     "%IDLIST(1) | %COO(A D;ICRS;J2000) | %OTYPE | %SP | %FLUXLIST(U;B;V;R;I;J;H;K) | %PM | %PLX | %RV | %MT"
```

## Key TAP Tables

### `basic` — Main Object Table

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

| Column | Type | Description |
|--------|------|-------------|
| `oidref` | BIGINT | Reference to `basic.oid` |
| `id` | VARCHAR | Identifier string |

### `flux` — Photometric Measurements

| Column | Type | Description |
|--------|------|-------------|
| `oidref` | BIGINT | Reference to `basic.oid` |
| `filter` | VARCHAR | Filter name (U, B, V, R, I, J, H, K, u, g, r, i, z, G, etc.) |
| `flux` | DOUBLE | Magnitude value |
| `flux_err` | DOUBLE | Magnitude error |
| `bibcode` | VARCHAR | Source reference bibcode |

### `mesDistance` — Distance Measurements

| Column | Type | Description |
|--------|------|-------------|
| `oidref` | BIGINT | Reference to `basic.oid` |
| `dist` | DOUBLE | Distance value |
| `unit` | VARCHAR | Distance unit (pc, kpc, Mpc) |
| `minus_err` | DOUBLE | Lower error |
| `plus_err` | DOUBLE | Upper error |
| `method` | VARCHAR | Measurement method |
| `bibcode` | VARCHAR | Source reference |

### `has_ref` / `ref` — Bibliographic References

`has_ref` links objects to references (`oidref` → `basic.oid`, `oidbibref` → `ref.oidbib`).

| `ref` Column | Type | Description |
|--------|------|-------------|
| `oidbib` | BIGINT | Bibliography object ID |
| `bibcode` | VARCHAR | ADS bibcode |
| `title` | VARCHAR | Paper title |
| `journal` | VARCHAR | Journal name |
| `year` | INTEGER | Publication year |

### `otypedef` — Object Type Definitions

| Column | Type | Description |
|--------|------|-------------|
| `otype` | VARCHAR | Object type code |
| `description` | VARCHAR | Human-readable description |

## Common Object Types (otype)

| Code | Description |
|------|-------------|
| `Star` | Star |
| `HII` | HII region |
| `PN` | Planetary nebula |
| `SNR` | Supernova remnant |
| `Galaxy` | Galaxy |
| `AGN` | Active galactic nucleus |
| `QSO` | Quasar |
| `GClstr` | Galaxy cluster |
| `GlobCl` | Globular cluster |
| `OpCl` | Open cluster |
| `Pulsar` | Pulsar |
| `WD*` | White dwarf |
| `Planet` | Extra-solar planet |
| `**` | Double/multiple star |
| `V*` | Variable star |
| `X` | X-ray source |

Query `SELECT * FROM otypedef ORDER BY otype` for the full list.

## ADQL Query Patterns

### Spatial Queries

**Cone search** — objects within a radius of a point:
```sql
SELECT main_id, ra, dec, otype
FROM basic
WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', 83.633, 22.014, 0.5)) = 1
```
Parameters: `CIRCLE('ICRS', center_ra_deg, center_dec_deg, radius_deg)`

**Box search:**
```sql
SELECT main_id, ra, dec, otype
FROM basic
WHERE CONTAINS(POINT('ICRS', ra, dec), BOX('ICRS', 180.0, 0.0, 10.0, 5.0)) = 1
```
Parameters: `BOX('ICRS', center_ra, center_dec, width_deg, height_deg)`

**Polygon search:**
```sql
SELECT main_id, ra, dec
FROM basic
WHERE CONTAINS(POINT('ICRS', ra, dec), POLYGON('ICRS', 10.0, 40.0, 12.0, 40.0, 12.0, 42.0, 10.0, 42.0)) = 1
```

**Angular distance:**
```sql
SELECT main_id, ra, dec,
       DISTANCE(POINT('ICRS', ra, dec), POINT('ICRS', 10.68458, 41.26917)) AS dist_deg
FROM basic
WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', 10.68458, 41.26917, 0.1)) = 1
ORDER BY dist_deg ASC
```

### JOINs

```sql
-- V-band magnitudes
SELECT b.main_id, b.ra, b.dec, f.flux AS Vmag
FROM basic AS b
JOIN flux AS f ON b.oid = f.oidref
WHERE f.filter = 'V' AND f.flux < 6.0
ORDER BY f.flux ASC

-- All identifiers for an object
SELECT b.main_id, i.id
FROM basic AS b
JOIN ident AS i ON b.oid = i.oidref
WHERE b.main_id = 'M  31'

-- Distance measurements
SELECT b.main_id, d.dist, d.unit, d.method
FROM basic AS b
JOIN mesDistance AS d ON b.oid = d.oidref
WHERE b.main_id = 'M  31'
```

### Cross-Matching Identifiers Between Catalogs

```sql
SELECT b.main_id, i1.id AS hipparcos_id, i2.id AS gaia_id
FROM basic AS b
JOIN ident AS i1 ON b.oid = i1.oidref AND i1.id LIKE 'HIP %'
JOIN ident AS i2 ON b.oid = i2.oidref AND i2.id LIKE 'Gaia DR3%'
WHERE b.otype = 'Star' AND b.plx_value > 50
```

### Bibliography for Objects in a Region

```sql
SELECT b.main_id, r.bibcode, r.title, r.year
FROM basic AS b
JOIN has_ref AS hr ON b.oid = hr.oidref
JOIN ref AS r ON hr.oidbibref = r.oidbib
WHERE CONTAINS(POINT('ICRS', b.ra, b.dec), CIRCLE('ICRS', 83.633, -5.375, 0.5)) = 1
  AND r.year >= 2020
ORDER BY r.year DESC
```

### Aggregation

```sql
-- Count objects by type in a region
SELECT otype, COUNT(*) AS count
FROM basic
WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', 266.417, -29.008, 1.0)) = 1
GROUP BY otype
HAVING COUNT(*) > 5
ORDER BY count DESC

-- Average parallax by spectral class
SELECT SUBSTRING(sp_type, 1, 1) AS sp_class, AVG(plx_value) AS mean_plx, COUNT(*) AS n
FROM basic
WHERE sp_type IS NOT NULL AND plx_value IS NOT NULL
GROUP BY sp_class
ORDER BY sp_class
```

## Response Formats

### TAP JSON

```json
{
  "metadata": [
    {"name": "main_id", "datatype": "char"},
    {"name": "ra", "datatype": "double"},
    {"name": "dec", "datatype": "double"}
  ],
  "data": [
    ["M 31", 10.6847, 41.2687]
  ]
}
```

### Script Response

Plain text with pipe-delimited fields. Lines starting with `::` are metadata — filter them out. Check for `error` or `not found` in data lines to detect failures.

## Rate Limits

No formal rate limits documented. Best practices:
- Add `time.sleep(0.5)` between sequential script queries
- Use TAP/ADQL for batch queries instead of looping over the script interface
- Always set `MAXREC` or use `TOP N` in TAP queries to avoid accidentally downloading millions of rows
- Very large TAP queries may time out; tighten `WHERE` clauses or switch to async TAP at `/simbad/sim-tap/async`
- Use VOTable format for large TAP results (preserves data types and units better than JSON)

## Input Sanitization

When building ADQL or script queries from user-supplied object names, sanitize inputs to prevent injection:
- Block newlines, carriage returns, tabs, quotes, semicolons, backslashes, and angle brackets in object names
- Escape single quotes in ADQL string literals by doubling them (`'` → `''`)
- Limit input length (128 chars is reasonable)
- Collapse and trim whitespace
