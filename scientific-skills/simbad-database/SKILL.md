---
name: simbad-database
description: Direct access to the SIMBAD astronomical database via REST API and TAP/ADQL. Query astronomical objects by name, coordinates, or identifier patterns. Retrieve object types, coordinates, photometry, proper motions, radial velocities, and bibliographic references for millions of objects beyond the Solar System. Use this when tasks involve identifying astronomical objects, resolving object names to coordinates, cross-matching sources, or performing complex catalog queries with ADQL.
license: CDS Terms of Use
metadata:
    skill-author: Steven
---

# SIMBAD Database

## Overview

SIMBAD (Set of Identifications, Measurements and Bibliography for Astronomical Data) is a comprehensive astronomical database operated by the Centre de Données astronomiques de Strasbourg (CDS). It contains data on over 17 million astronomical objects beyond the Solar System, including identifications, coordinates, photometry, proper motions, parallaxes, radial velocities, spectral types, and bibliographic references.

SIMBAD provides two main access methods:
1. **Script interface** (`sim-script`) — Simple queries by name, coordinates, or identifier pattern
2. **TAP service** (`sim-tap`) — Complex queries using ADQL (Astronomical Data Query Language), a SQL-like language for astronomical databases

## When to Use This Skill

Use this skill when tasks involve:
- Resolving astronomical object names to coordinates (e.g., "Where is M31?")
- Looking up object properties: type, spectral type, magnitudes, radial velocity, parallax
- Searching for objects near a sky position (cone search)
- Finding objects matching an identifier pattern (e.g., all NGC objects starting with "10")
- Querying SIMBAD tables with complex criteria using ADQL (object type, magnitude range, coordinate box, etc.)
- Cross-referencing object identifiers across catalogs (HD, HIP, NGC, IC, 2MASS, Gaia, etc.)
- Retrieving bibliographic references for an astronomical object
- Building source lists for observing proposals or catalog studies

For Python-based coordinate transformations, FITS file handling, or cosmological calculations, use the **astropy** skill instead. SIMBAD complements astropy by providing the catalog data that astropy can then process.

## Quick Start

### Using requests (direct HTTP)

```python
import requests

# Query an object by name
response = requests.post(
    "https://simbad.cds.unistra.fr/simbad/sim-script",
    data={"script": '\n'.join([
        "output console=off script=off",
        'format object "%IDLIST(1) | %COO(A D;ICRS) | %OTYPE | %SP | %FLUXLIST(V)"',
        "query id M31",
    ])}
)
print(response.text)
```

### Using astroquery (recommended for Python workflows)

```python
from astroquery.simbad import Simbad

result = Simbad.query_object("M31")
print(result)
```

### Using TAP/ADQL for complex queries

```python
import requests

params = {
    "REQUEST": "doQuery",
    "LANG": "ADQL",
    "QUERY": "SELECT TOP 10 main_id, ra, dec, otype FROM basic WHERE otype = 'Galaxy' AND ra BETWEEN 10 AND 12",
    "FORMAT": "json",
}
response = requests.post(
    "https://simbad.cds.unistra.fr/simbad/sim-tap/sync",
    data=params
)
print(response.json())
```

## Core Capabilities

### 1. Query by Object Name

Resolve any astronomical object name to its properties. SIMBAD recognizes catalog designations (M31, NGC 1068, HD 209458), common names (Sirius, Betelgeuse, Andromeda), and survey identifiers (2MASS, Gaia DR3, SDSS).

**Key operations:**
- Get coordinates (ICRS, FK5, Galactic)
- Get object type classification
- Get spectral type
- Get photometric magnitudes (U, B, V, R, I, J, H, K)
- Get proper motion, parallax, and radial velocity
- Get all known identifiers for an object

**See:** `references/api_reference.md` for format strings and output customization.

### 2. Coordinate (Cone) Search

Find all objects within a given radius of a sky position.

```python
from astroquery.simbad import Simbad
from astropy.coordinates import SkyCoord
import astropy.units as u

coord = SkyCoord(ra=10.68458, dec=41.26917, unit="deg", frame="icrs")
result = Simbad.query_region(coord, radius=5 * u.arcmin)
print(result)
```

Or via the script interface:

```python
import requests

script = '\n'.join([
    "output console=off script=off",
    'format object "%IDLIST(1) | %COO(A D;ICRS) | %OTYPE"',
    "query coo 10.68458 +41.26917 radius=5m",
])
response = requests.post(
    "https://simbad.cds.unistra.fr/simbad/sim-script",
    data={"script": script}
)
print(response.text)
```

### 3. Identifier Pattern Search

Search for objects matching a wildcard identifier pattern.

```python
import requests

script = '\n'.join([
    "output console=off script=off",
    'format object "%IDLIST(1) | %COO(A D;ICRS) | %OTYPE"',
    "query id wildcard NGC 10*",
])
response = requests.post(
    "https://simbad.cds.unistra.fr/simbad/sim-script",
    data={"script": script}
)
print(response.text)
```

### 4. Advanced ADQL Queries via TAP

Use ADQL (a SQL dialect for astronomy) to query SIMBAD's relational tables with full filtering, joins, and aggregation.

**Key tables:**
- `basic` — Core object data (main_id, ra, dec, otype, sp_type, plx, rvz_radvel, pmra, pmdec)
- `ident` — All identifiers for each object
- `flux` — Photometric measurements
- `mesDistance` — Distance measurements
- `biblio` — Bibliographic references
- `otypedef` — Object type definitions and descriptions

```python
import requests

query = """
SELECT TOP 20 main_id, ra, dec, otype, sp_type, plx_value
FROM basic
WHERE otype = 'Star'
  AND plx_value > 100
ORDER BY plx_value DESC
"""

response = requests.post(
    "https://simbad.cds.unistra.fr/simbad/sim-tap/sync",
    data={
        "REQUEST": "doQuery",
        "LANG": "ADQL",
        "QUERY": query,
        "FORMAT": "json",
    }
)
data = response.json()
for row in data.get("data", []):
    print(row)
```

**See:** `references/adql_reference.md` for table schemas, joins, and advanced query patterns.

### 5. Using astroquery.simbad (Recommended Python Interface)

The `astroquery` package provides a Pythonic interface with automatic result parsing into astropy Tables.

```python
from astroquery.simbad import Simbad

# Add custom fields to the default query
custom_simbad = Simbad()
custom_simbad.add_votable_fields('sp', 'flux(V)', 'flux(B)', 'plx', 'rv_value')

# Query by name
result = custom_simbad.query_object("Vega")
print(result.colnames)
print(result)

# Query by region
from astropy.coordinates import SkyCoord
import astropy.units as u

center = SkyCoord("05h23m34.5s", "-69d45m22s", frame="icrs")
result = custom_simbad.query_region(center, radius=10 * u.arcmin)
print(f"Found {len(result)} objects")
```

## Installation

```bash
# For direct HTTP access (no extra dependencies)
uv pip install requests

# For the recommended astroquery interface
uv pip install astroquery astropy
```

## Common Workflows

### Resolving an Object Name to Coordinates

```python
from astroquery.simbad import Simbad

result = Simbad.query_object("Crab Nebula")
ra = result['RA'][0]
dec = result['DEC'][0]
print(f"Crab Nebula: RA={ra}, DEC={dec}")
```

### Getting All Known Identifiers for an Object

```python
from astroquery.simbad import Simbad

ids = Simbad.query_objectids("M1")
for row in ids:
    print(row['ID'])
```

### Finding Bright Stars Near a Position

```python
import requests

query = """
SELECT main_id, ra, dec, otype, sp_type,
       FLUX_V as Vmag
FROM basic
JOIN flux ON basic.oid = flux.oidref AND flux.filter = 'V'
WHERE CONTAINS(POINT('ICRS', ra, dec),
               CIRCLE('ICRS', 83.633, 22.014, 1.0)) = 1
  AND FLUX_V < 8
ORDER BY FLUX_V ASC
"""

response = requests.post(
    "https://simbad.cds.unistra.fr/simbad/sim-tap/sync",
    data={
        "REQUEST": "doQuery",
        "LANG": "ADQL",
        "QUERY": query,
        "FORMAT": "json",
    }
)
for row in response.json().get("data", []):
    print(row)
```

### Cross-Matching with External Catalogs

```python
import requests

query = """
SELECT b.main_id, b.ra, b.dec, b.otype, i.id AS gaia_id
FROM basic AS b
JOIN ident AS i ON b.oid = i.oidref
WHERE i.id LIKE 'Gaia DR3%'
  AND b.otype = 'Planet'
ORDER BY b.main_id
"""

response = requests.post(
    "https://simbad.cds.unistra.fr/simbad/sim-tap/sync",
    data={
        "REQUEST": "doQuery",
        "LANG": "ADQL",
        "QUERY": query,
        "FORMAT": "json",
        "MAXREC": 50,
    }
)
print(response.json())
```

### Retrieving Bibliography for an Object

```python
from astroquery.simbad import Simbad

refs = Simbad.query_bibobj("M31")
print(f"Found {len(refs)} bibliographic references for M31")
print(refs[:5])
```

## Python Implementation

For programmatic access, use the provided helper script `scripts/simbad_client.py` which implements:

- `query_object(name, output_format)` — Query by object name
- `query_region(ra, dec, radius, max_results)` — Cone search by coordinates
- `query_identifiers(pattern, max_results)` — Wildcard identifier search
- `tap_query(adql_query, max_results, fmt)` — Execute ADQL via TAP
- `get_all_identifiers(name)` — Get all catalog IDs for an object

**Alternative Python packages:**
- **astroquery**: Full-featured astronomical query package (recommended)
- **pyvo**: Generic Virtual Observatory (VO) TAP client

## Object Type Codes

SIMBAD uses a hierarchical object type classification. Common codes:

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

Use the `otypedef` table via TAP to get the full list:

```python
import requests

response = requests.post(
    "https://simbad.cds.unistra.fr/simbad/sim-tap/sync",
    data={
        "REQUEST": "doQuery",
        "LANG": "ADQL",
        "QUERY": "SELECT * FROM otypedef ORDER BY otype",
        "FORMAT": "json",
    }
)
for row in response.json().get("data", []):
    print(row)
```

## Best Practices

1. **Prefer astroquery for Python workflows**: It handles pagination, parsing, and error handling automatically
2. **Use TAP/ADQL for complex queries**: The script interface is best for simple lookups; TAP supports joins, aggregation, and spatial queries
3. **Respect rate limits**: SIMBAD is a free public service; avoid rapid-fire requests. Add `time.sleep(0.5)` between batch queries
4. **Use `MAXREC` in TAP queries**: Always limit results to avoid accidentally downloading millions of rows
5. **Check coordinate frames**: SIMBAD defaults to ICRS (J2000); be explicit about frames when cross-matching
6. **Use `CONTAINS(POINT, CIRCLE)` for cone searches in ADQL**: This is the standard VO spatial predicate
7. **Handle missing data**: Not all objects have all measurements; check for NULL/empty values
8. **Verify object types**: Use the condensed object type (`otype`) for filtering, not the long description
9. **Cache results locally**: Store frequently accessed object data to minimize API calls
10. **Use VOTable format for large TAP results**: It preserves data types and units better than JSON
11. **Validate user input before querying**: When building ADQL or script queries from user-supplied object names, sanitize input to prevent injection. Use the provided `simbad_client.py` which validates and escapes inputs safely.

## Resources

### scripts/
`simbad_client.py` — Python client with helper functions for common SIMBAD operations including name queries, coordinate searches, identifier pattern matching, and TAP/ADQL queries.

### references/
- `api_reference.md` — Script interface format strings, output fields, and query syntax
- `adql_reference.md` — SIMBAD TAP table schemas, ADQL syntax, joins, spatial queries, and advanced patterns

## Additional Resources

- **SIMBAD Web Interface**: https://simbad.cds.unistra.fr/simbad/
- **SIMBAD TAP Documentation**: https://simbad.cds.unistra.fr/simbad/tap/help/
- **astroquery SIMBAD Module**: https://astroquery.readthedocs.io/en/latest/simbad/simbad.html
- **ADQL Specification**: https://www.ivoa.net/documents/ADQL/
- **CDS Portal**: https://cds.unistra.fr/
