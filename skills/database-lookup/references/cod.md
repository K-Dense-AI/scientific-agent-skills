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

Use `el1`, `el2`, `el3`, etc. for element filters. Use `nel=2` to restrict to exactly 2 elements.

### Search by cell parameters

```
GET /result?a_min=5.0&a_max=6.0&b_min=5.0&b_max=6.0&c_min=5.0&c_max=6.0&format=json
```

Cell parameter filters:
- `a_min`, `a_max` — a-axis length (Angstroms)
- `b_min`, `b_max` — b-axis length
- `c_min`, `c_max` — c-axis length
- `alpha_min`, `alpha_max` — alpha angle (degrees)
- `beta_min`, `beta_max` — beta angle
- `gamma_min`, `gamma_max` — gamma angle
- `vol_min`, `vol_max` — unit cell volume (A^3)

### Search by space group

```
GET /result?sg=F%20m%20-3%20m&format=json
```

### Search by text (author, journal, title)

```
GET /result?text=perovskite&format=json
```

### Combined search example

```
GET /result?el1=Ti&el2=O&nel=2&sg=P%2042/m%20n%20m&format=json
```

### Retrieve a specific CIF file

```
GET /1000000.cif
```

COD IDs are 7-digit integers. Append `.cif` for the crystallographic information file, or `.html` for the web page.

### Retrieve entry metadata as JSON

```
GET /result?id=1000000&format=json
```

### Output formats

- `format=json` — JSON array of matching entries
- `format=csv` — CSV output
- `format=lst` — list of COD IDs only
- Default (no format) — HTML page

## Response Format

```json
[
  {
    "file": "1526463",
    "a": "4.759",
    "b": "4.759",
    "c": "12.992",
    "alpha": "90",
    "beta": "90",
    "gamma": "120",
    "vol": "254.94",
    "sg": "R -3 c",
    "formula": "Fe2 O3",
    "title": "Refinement of the crystal structure of ...",
    "journal": "Zeitschrift fuer Kristallographie",
    "year": "1966",
    "authors": "Blake, R.L.; et al."
  }
]
```

The `file` field is the COD ID. Use it to fetch the CIF: `https://www.crystallography.net/cod/{file}.cif`

## Rate Limits

- No formal rate limits documented
- Be courteous: avoid bulk-downloading thousands of entries rapidly
- For bulk access, COD provides downloadable database dumps at https://www.crystallography.net/cod/archives/

## Notes

- COD contains ~500,000+ crystal structures from published literature
- All data is open-access under public domain / open licenses
- The search API returns metadata; use the CIF endpoint for full structural data
- Alternative access: MySQL database dumps and SVN access are available for bulk use
