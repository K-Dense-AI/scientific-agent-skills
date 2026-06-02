# Eurostat API Reference

## Overview
Eurostat is the statistical office of the European Union, providing statistics on economy, population, trade, labor, environment, and more for EU/EEA member states and partner countries. The API follows the SDMX (Statistical Data and Metadata Exchange) standard.

## Base URL
```
https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1
```

An older JSON-stat endpoint also exists:
```
https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0
```

## Authentication
**No API key required.** The API is fully open and free.

## Rate Limits
- No formal rate limits documented.
- Eurostat may throttle aggressive scraping. Keep automated requests to 1-2 per second.
- Large datasets may time out; use filters to reduce response size.

---

## Key Endpoints (SDMX 2.1 API)

### 1. Get Dataset (Observations)

```
GET /data/{datasetCode}/{filter}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `datasetCode` | Yes | Eurostat dataset code (e.g., `nama_10_gdp`, `demo_pjan`) |
| `filter` | No | Dot-separated dimension filter. Use `+` for multiple values in a dimension, `.` to separate dimensions, empty segment for "all". |

**Query parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `format` | No | `sdmx+json` (default), `sdmx+csv`, `sdmx+xml`, `TSV` |
| `startPeriod` | No | Start year/quarter/month: `2015`, `2020-Q1`, `2020-01` |
| `endPeriod` | No | End year/quarter/month |
| `detail` | No | `full` (default), `dataonly`, `serieskeysonly`, `nodata` |
| `lang` | No | `en` (default), `fr`, `de` |

**Example (GDP at market prices for Germany and France, annual, 2018-2023):**
```
https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/nama_10_gdp/A.CP_MEUR.B1GQ.DE+FR?startPeriod=2018&endPeriod=2023
```

**Example (total population by country, annual):**
```
https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/demo_pjan/A.NR.T.TOTAL.DE+FR+IT+ES?startPeriod=2015&endPeriod=2023
```

**Example (unemployment rate, seasonally adjusted, monthly):**
```
https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/une_rt_m/M.SA.TOTAL.PC_ACT.T.EA20?startPeriod=2023-01&endPeriod=2024-12
```

**Example (HICP inflation, all items, monthly):**
```
https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/prc_hicp_mmor/M.RCH_A.CP00.DE+FR+IT?startPeriod=2023-01&endPeriod=2024-06&format=sdmx+json
```

### 2. Get Dataset as CSV

Append `?format=sdmx+csv` to any data request for a flat CSV response that is easier to parse.

**Example:**
```
https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/nama_10_gdp/A.CP_MEUR.B1GQ.DE+FR?startPeriod=2018&endPeriod=2023&format=sdmx+csv
```

### 3. Get Dataset Structure (Dimensions and Code Lists)

```
GET /datastructure/ESTAT/{datasetCode}
```

**Example:**
```
https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/datastructure/ESTAT/nama_10_gdp
```

Returns dimension names, positions, and code list references.

### 4. Get Code List (Dimension Values)

```
GET /codelist/ESTAT/{codelistId}
```

**Example:**
```
https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/codelist/ESTAT/GEO
```

### 5. Search/Browse Datasets (Dataflows)

```
GET /dataflow/ESTAT/all
```

Returns all available Eurostat datasets. Add `?detail=allstubs` for a lighter listing.

**Example:**
```
https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/dataflow/ESTAT/all?detail=allstubs
```

---

## JSON-stat API (Simpler Alternative)

### Base URL
```
https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data
```

### Get Data
```
GET /data/{datasetCode}?{dimension_filters}
```

Dimensions are passed as query parameters using their dimension name.

**Example (GDP for DE and FR):**
```
https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nama_10_gdp?geo=DE&geo=FR&unit=CP_MEUR&na_item=B1GQ&freq=A&time=2020&time=2021&time=2022&lang=en
```

**Response (JSON-stat format):**
```json
{
  "version": "2.0",
  "label": "GDP and main components (output, expenditure and income)",
  "id": ["freq", "unit", "na_item", "geo", "time"],
  "size": [1, 1, 1, 2, 3],
  "dimension": {
    "geo": {
      "label": "Geopolitical entity",
      "category": {
        "index": {"DE": 0, "FR": 1},
        "label": {"DE": "Germany", "FR": "France"}
      }
    },
    "time": {
      "label": "Time",
      "category": {
        "index": {"2020": 0, "2021": 1, "2022": 2}
      }
    }
  },
  "value": {3336010.0, 3601750.0, 3876810.0, 2310420.0, 2500870.0, 2639090.0},
  "status": {}
}
```

Values are in a flat array; use dimension sizes to reshape.

---

## Common Dataset Codes

| Code | Description |
|------|-------------|
| `nama_10_gdp` | GDP and main components |
| `nama_10_pc` | GDP per capita |
| `namq_10_gdp` | GDP quarterly |
| `demo_pjan` | Population on 1 January |
| `demo_gind` | Population change (births, deaths, migration) |
| `une_rt_m` | Unemployment rate (monthly) |
| `une_rt_a` | Unemployment rate (annual) |
| `lfsi_emp_a` | Employment rate (annual) |
| `prc_hicp_manr` | HICP inflation (annual rate of change, monthly) |
| `prc_hicp_mmor` | HICP inflation (monthly rate of change) |
| `ext_lt_maineu` | EU trade by partner (main partners) |
| `ext_st_27_2020sitc` | International trade by SITC |
| `bop_c6_q` | Balance of payments (quarterly) |
| `gov_10dd_edpt1` | Government deficit/surplus |
| `gov_10a_main` | Government revenue, expenditure and main aggregates |
| `sts_inpr_m` | Industrial production (monthly) |
| `tour_occ_nim` | Tourism (nights spent at accommodation) |
| `env_air_gge` | Greenhouse gas emissions |
| `tec00114` | GDP growth rate (percentage change) |
| `tec00118` | Government debt as % of GDP |

## Common Country Codes (ISO 2-letter, Eurostat uses uppercase)

`AT` Austria, `BE` Belgium, `BG` Bulgaria, `CY` Cyprus, `CZ` Czechia, `DE` Germany, `DK` Denmark, `EE` Estonia, `EL` Greece, `ES` Spain, `FI` Finland, `FR` France, `HR` Croatia, `HU` Hungary, `IE` Ireland, `IT` Italy, `LT` Lithuania, `LU` Luxembourg, `LV` Latvia, `MT` Malta, `NL` Netherlands, `PL` Poland, `PT` Portugal, `RO` Romania, `SE` Sweden, `SI` Slovenia, `SK` Slovakia

Aggregates: `EU27_2020` (EU-27), `EA20` (Euro area 20), `EA19` (Euro area 19), `EEA30_2007` (EEA)

**Note:** Greece uses `EL` (not `GR`) in Eurostat.

## SDMX JSON Response Format

```json
{
  "header": {
    "id": "...",
    "prepared": "2024-01-15T10:00:00"
  },
  "dataSets": [
    {
      "series": {
        "0:0:0:0": {
          "observations": {
            "0": [3336010.0],
            "1": [3601750.0]
          }
        }
      }
    }
  ],
  "structure": {
    "dimensions": {
      "series": [...],
      "observation": [...]
    }
  }
}
```

In SDMX+JSON, dimension values are encoded as integer indices. The `structure.dimensions` section maps indices to codes and labels. This is compact but requires index lookup.

## Notes
- Dimension order in the filter path depends on the dataset structure. Always check `/datastructure/ESTAT/{code}` first.
- Use `+` to select multiple values in one dimension (e.g., `DE+FR+IT`).
- Leave a dimension segment empty (consecutive dots `..`) to select all values.
- CSV format (`?format=sdmx+csv`) is recommended for easier parsing -- it returns flat rows with labeled columns.
- The JSON-stat API is simpler for quick queries but the SDMX API is more powerful and complete.
- Dataset codes can be found at https://ec.europa.eu/eurostat/databrowser/ by browsing themes.
- Large unrestricted queries may time out. Always filter by country and time period.
