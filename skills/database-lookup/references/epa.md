# EPA Envirofacts API Reference

## Base URL
```
https://data.epa.gov/efservice
```

Note: The legacy URL `https://enviro.epa.gov/enviro/efservice` may redirect. Use the current base URL above.

## Authentication
**None required.** Fully public, no API key needed.

## Rate Limits
- No documented per-user rate limit.
- Large result sets may time out. Use row limits and pagination.

## URL Pattern
Envirofacts uses a RESTful URL-based query pattern:
```
https://data.epa.gov/efservice/{table}/{column}/{operator}/{value}/.../rows/{start}:{end}/{format}
```

- **{table}**: Database table name (e.g. `TRI_FACILITY`, `AQS_SITES`).
- **{column}/{operator}/{value}**: Filter conditions, chained in the URL path.
- **Operators**: `=` (implicit, just use `/{column}/{value}`), `>`, `<`, `!=`, `BEGINNING` (starts with), `CONTAINING`.
- **rows/{start}:{end}**: Row range for pagination (0-based).
- **{format}**: `JSON`, `XML`, `CSV`, `EXCEL`. Appended as the last path segment.

**Multiple filters** are chained sequentially in the URL path.

---

## Key Databases and Tables

### 1. Toxics Release Inventory (TRI)

Tracks releases of toxic chemicals from industrial facilities.

**Key Tables:**
| Table | Description |
|-------|-------------|
| `TRI_FACILITY` | Facility information (name, address, coordinates). |
| `TRI_REPORTING_FORM` | Annual reporting form data. |
| `TRI_RELEASE_QTY` | Quantities of releases by media (air, water, land). |
| `TRI_TRANSFER_QTY` | Quantities transferred off-site. |
| `TRI_CHEM_INFO` | Chemical information. |

**Example -- TRI facilities in North Carolina:**
```
https://data.epa.gov/efservice/TRI_FACILITY/STATE_ABBR/NC/rows/0:9/JSON
```

**Response:**
```json
[
  {
    "TRI_FACILITY_ID": "27601MPLNT501WE",
    "FACILITY_NAME": "EXAMPLE MANUFACTURING PLANT",
    "STREET_ADDRESS": "501 WEST MAIN ST",
    "CITY_NAME": "RALEIGH",
    "COUNTY_NAME": "WAKE",
    "STATE_ABBR": "NC",
    "ZIP_CODE": "27601",
    "LATITUDE": 35.7796,
    "LONGITUDE": -78.6382,
    "FEDERAL_FACILITY_FLAG": "NO",
    "INDUSTRY_SECTOR_CODE": "325",
    "PRIMARY_SIC_CODE": "2819",
    "PRIMARY_NAICS_CODE": "325180"
  }
]
```

**Example -- TRI releases of a specific chemical in a state (2022):**
```
https://data.epa.gov/efservice/TRI_RELEASE_QTY/STATE_ABBR/TX/REPORTING_YEAR/2022/CHEM_NAME/CONTAINING/BENZENE/rows/0:24/JSON
```

### 2. Air Quality System (AQS)

Air quality monitoring data from the national monitoring network.

**Key Tables:**
| Table | Description |
|-------|-------------|
| `AQS_SITES` | Monitoring site metadata. |
| `AQS_MONITORS` | Monitor-level info (parameters measured). |
| `AQS_ANNUAL_SUMMARY` | Annual summary statistics per monitor. |
| `AQS_DAILY_SUMMARY` | Daily summary observations. |

**Example -- AQS monitoring sites in California:**
```
https://data.epa.gov/efservice/AQS_SITES/STATE_CODE/06/rows/0:9/JSON
```

**Example -- annual ozone summary for a county:**
```
https://data.epa.gov/efservice/AQS_ANNUAL_SUMMARY/STATE_CODE/06/COUNTY_CODE/037/PARAMETER_CODE/44201/rows/0:9/JSON
```

**Common AQS Parameter Codes:**
| Code  | Pollutant |
|-------|-----------|
| `44201` | Ozone |
| `42401` | SO2 |
| `42101` | CO |
| `42602` | NO2 |
| `81102` | PM10 |
| `88101` | PM2.5 (FRM) |
| `88502` | PM2.5 (non-FRM) |
| `14129` | Lead (Pb) |

### 3. Facility Registry Service (FRS)

Central registry of EPA-regulated facilities.

**Key Tables:**
| Table | Description |
|-------|-------------|
| `FRS_FACILITY_SITE` | Facility location and identifiers. |
| `FRS_PROGRAM_FACILITY` | Links facilities to EPA programs. |
| `FRS_NAICS` | NAICS codes for facilities. |
| `FRS_SIC` | SIC codes for facilities. |

**Example -- EPA-regulated facilities by zip code:**
```
https://data.epa.gov/efservice/FRS_FACILITY_SITE/POSTAL_CODE/90210/rows/0:9/JSON
```

### 4. Safe Drinking Water (SDWIS)

Public drinking water system data.

**Key Tables:**
| Table | Description |
|-------|-------------|
| `WATER_SYSTEM` | Water system info. |
| `VIOLATION` | Drinking water violations. |
| `LCR_SAMPLE_RESULT` | Lead and Copper Rule sample results. |

**Example -- drinking water violations in a state:**
```
https://data.epa.gov/efservice/VIOLATION/PWSID/BEGINNING/OH/rows/0:19/JSON
```

### 5. Greenhouse Gas Reporting (GHG)

Facility-level greenhouse gas emissions data.

**Key Tables:**
| Table | Description |
|-------|-------------|
| `PUB_DIM_FACILITY` | GHG reporting facility info. |
| `PUB_FACTS_SECTOR_GHG_EMISSION` | Emissions by sector. |

**Example -- GHG facilities in a state:**
```
https://data.epa.gov/efservice/PUB_DIM_FACILITY/STATE/TX/rows/0:9/JSON
```

---

## Query Patterns

### Filtering with operators
```
# Exact match (implicit =)
/TABLE/COLUMN/VALUE/JSON

# Greater than
/TABLE/COLUMN/>/VALUE/JSON

# Less than
/TABLE/COLUMN/</VALUE/JSON

# Not equal
/TABLE/COLUMN/!=/VALUE/JSON

# Starts with
/TABLE/COLUMN/BEGINNING/VALUE/JSON

# Contains
/TABLE/COLUMN/CONTAINING/VALUE/JSON
```

### Combining filters
Chain multiple column/value pairs:
```
/TABLE/COLUMN1/VALUE1/COLUMN2/VALUE2/JSON
```

### Pagination
Use `rows/{start}:{end}` (0-based, inclusive):
```
/TABLE/rows/0:99/JSON       # First 100 rows
/TABLE/rows/100:199/JSON    # Next 100 rows
```
Default without `rows`: returns first 10,000 rows.

### Output format
Append format as the last path segment:
```
/TABLE/.../JSON
/TABLE/.../XML
/TABLE/.../CSV
/TABLE/.../EXCEL
```

---

## AQS Data API (Separate System)

For more granular air quality data, EPA also provides the AQS Data API at:
```
https://aqs.epa.gov/data/api
```

- **Requires:** Free account at https://aqs.epa.gov/data/api/signup?email=YOUR_EMAIL
- **Auth:** Pass `email` and `key` as query parameters.
- Key endpoints: `/dailyData/byState`, `/annualData/byState`, `/sampleData/bySite`, `/monitors/byState`.

**Example:**
```
https://aqs.epa.gov/data/api/dailyData/byState?email=YOUR_EMAIL&key=YOUR_KEY&param=44201&bdate=20240101&edate=20240131&state=06
```

## Notes
- Table and column names are case-insensitive in the URL.
- The Envirofacts API returns all columns for a table; you cannot select specific columns.
- For joining data across tables, you must make separate requests and join client-side using shared keys (e.g. `TRI_FACILITY_ID`, `REGISTRY_ID`).
- Some tables are very large. Always use `rows/` to limit results and paginate.
- EPA data updates vary by program: TRI is annual, AQS is daily/annual, SDWIS is quarterly.
