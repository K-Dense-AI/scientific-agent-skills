# Crystallography Open Database (COD) API

## Base URL

```
https://www.crystallography.net/cod
```

## Authentication

**None required.** COD is fully open-access with no API key needed.

## Key Endpoints

### Search by formula

```
GET /result?formula=Fe2%20O3&format=json
```

Formula format uses spaces between elements: `Fe2 O3`, `Si O2`, `C6 H12 O6`. URL-encode spaces as `%20`.

### Search by elements

```
GET /result?el1=Fe&el2=O&format=json
```

Use `el1`, `el2`, `el3`, etc. for element filters. Use `strictmin=2&strictmax=2` to restrict the number of distinct elements to exactly two. `nel1`, `nel2`, etc. exclude individual elements; they are not element counts.

### Search by cell parameters

```
GET /result?amin=5.0&amax=6.0&bmin=5.0&bmax=6.0&cmin=5.0&cmax=6.0&format=json
```

Cell parameter filters:
- `amin`, `amax` — a-axis length (Angstroms)
- `bmin`, `bmax` — b-axis length
- `cmin`, `cmax` — c-axis length
- `alpmin`, `alpmax` — alpha angle (degrees)
- `betmin`, `betmax` — beta angle
- `gamin`, `gamax` — gamma angle
- `vmin`, `vmax` — unit cell volume (A^3)

### Search by space group

```
GET /result?space_group_number=225&format=json
```

### Search by text (author, journal, title)

```
GET /result?text1=perovskite&format=json
```

### Combined search example

```
GET /result?el1=Ti&el2=O&strictmin=2&strictmax=2&space_group_number=136&format=json
```

### Retrieve a specific CIF file

```
GET /1526463.cif
```

COD IDs are 7-digit integers. Append `.cif` for the crystallographic information file, or `.html` for the web page.

### Retrieve entry metadata as JSON

```
GET /result?id=1526463&format=json
```

### Output formats

- `format=json` — JSON array of matching entries
- `format=csv` — CSV output
- `format=lst` — list of COD IDs only
- Default (no format) — HTML page

## Response Format

JSON is an array of entries; `[]` means no matching entry. The `file` string is the COD ID. Cell parameters and other numbers may also be strings, with unavailable fields null. The live `1526463` record (2026-09-30) has `sgNumber="60"`, `a="12.1005"` and formula `- Li2.78 O12 P3 V1.8 Zr0.2 -`; it is not hematite. Fetch full structural data from `https://www.crystallography.net/cod/{file}.cif`.

Use the current search form's parameter names: unknown names can be ignored and yield an unintended broad query. Formula comparison follows COD's Hill-formatted formula conventions; validate the returned formula rather than treating element presence as exact stoichiometry.

## Rate Limits

- No formal rate limits documented
- Be courteous: avoid bulk-downloading thousands of entries rapidly
- For bulk access, COD provides downloadable database dumps at https://www.crystallography.net/cod/archives/

## Notes

- COD contains published crystal structures; record the retrieved entry revision for reproducibility.
- All data is open-access under public domain / open licenses
- The search API returns metadata; use the CIF endpoint for full structural data
- Alternative access: MySQL database dumps and SVN access are available for bulk use
