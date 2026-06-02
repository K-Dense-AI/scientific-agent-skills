# NASA Exoplanet Archive API

## Base URL

```
https://exoplanetarchive.ipac.caltech.edu
```

## Authentication

No API key required. All endpoints are public.

## Key Endpoints

### 1. TAP Service (recommended — current method)

```
GET /TAP/sync?query={ADQL}&format={format}
```

| Parameter | Type   | Description |
|-----------|--------|-------------|
| `query`   | string | **Required.** ADQL query. |
| `format`  | string | `json`, `csv`, `votable`, `tsv`, `ipac`. Default: `votable`. |

**Example — confirmed planets with key parameters:**
```
https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=SELECT pl_name,hostname,sy_dist,pl_orbper,pl_rade,pl_bmasse,disc_year,discoverymethod FROM ps WHERE default_flag=1 ORDER BY disc_year DESC&format=json
```

**Example — planets in habitable zone (rough estimate):**
```
https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=SELECT TOP 50 pl_name,hostname,pl_orbsmax,st_teff,pl_rade FROM ps WHERE default_flag=1 AND pl_orbsmax BETWEEN 0.8 AND 1.5 AND st_teff BETWEEN 4000 AND 7000&format=json
```

**Example — planets discovered by TESS:**
```
https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=SELECT pl_name,pl_rade,pl_orbper,disc_year FROM ps WHERE default_flag=1 AND disc_facility='Transiting Exoplanet Survey Satellite (TESS)'&format=json
```

**Example — count planets by discovery method:**
```
https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=SELECT discoverymethod, COUNT(*) as cnt FROM ps WHERE default_flag=1 GROUP BY discoverymethod ORDER BY cnt DESC&format=json
```

### 2. Legacy API (older, still functional)

```
GET /cgi-bin/nstedAPI/nph-nstedAPI?table={table}&format={format}&where={conditions}&select={columns}
```

**Example:**
```
https://exoplanetarchive.ipac.caltech.edu/cgi-bin/nstedAPI/nph-nstedAPI?table=ps&select=pl_name,pl_orbper,pl_rade&where=disc_year=2023&format=json
```

Note: The legacy API is deprecated in favor of TAP. Use TAP for new applications.

## Key TAP Tables

| Table  | Description |
|--------|-------------|
| `ps`   | **Planetary Systems** — one row per reference per planet. Use `default_flag=1` for the default/best parameter set. |
| `pscomppars` | **Planetary Systems Composite Parameters** — one row per planet with best-fit values from multiple references. |
| `stellarhosts` | Stellar properties of host stars. |
| `td`   | Time-series data (transit curves, RV curves). |
| `keplernames` | Kepler Object of Interest cross-references. |
| `k2names` | K2 campaign cross-references. |
| `toi`  | TESS Objects of Interest. |

## Key Columns (ps table)

| Column           | Description |
|------------------|-------------|
| `pl_name`        | Planet name (e.g., "Kepler-22 b"). |
| `hostname`       | Host star name. |
| `default_flag`   | 1 = default parameter set for this planet. |
| `disc_year`      | Discovery year. |
| `discoverymethod` | `Transit`, `Radial Velocity`, `Imaging`, `Microlensing`, etc. |
| `pl_orbper`      | Orbital period (days). |
| `pl_orbsmax`     | Semi-major axis (AU). |
| `pl_rade`        | Planet radius (Earth radii). |
| `pl_bmasse`      | Planet mass (Earth masses). |
| `pl_eqt`         | Equilibrium temperature (K). |
| `sy_dist`        | Distance to system (parsecs). |
| `st_teff`        | Stellar effective temperature (K). |
| `st_rad`         | Stellar radius (solar radii). |
| `st_mass`        | Stellar mass (solar masses). |
| `disc_facility`  | Discovery facility name. |

## Response Format (TAP JSON)

```json
{
  "metadata": [
    {"name": "pl_name", "datatype": "char"},
    {"name": "pl_orbper", "datatype": "double"}
  ],
  "data": [
    ["Kepler-22 b", 289.8623]
  ]
}
```

## Rate Limits

No API key or authentication required. No formal rate limits documented, but the archive requests that users avoid excessive automated queries. Large result sets may cause timeouts; use `TOP N` in ADQL or paginate with `OFFSET` and `MAXREC`.

For very large downloads, use the bulk download interface at:
```
https://exoplanetarchive.ipac.caltech.edu/cgi-bin/TblView/nph-tblView?app=ExoTbls&config=PS
```
