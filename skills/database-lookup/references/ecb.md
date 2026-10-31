# ECB Statistical Data Warehouse (SDW) REST API Reference

## Overview
The ECB SDW API provides access to European Central Bank statistical data: exchange rates, monetary aggregates, interest rates, balance of payments, banking statistics, and more. It follows the SDMX (Statistical Data and Metadata eXchange) RESTful web services standard.

## Base URL
```
https://data-api.ecb.europa.eu/service
```

Use the current Data Portal host above; do not depend on the retired SDW hostname.

## Authentication
**No API key required.** The API is fully open and public.

## Rate Limits
- No formal rate limits published.
- ECB asks users to be respectful: avoid excessive parallel requests.
- For bulk downloads, use compressed responses (`Accept-Encoding: gzip`).

## Formats

Request `format=csvdata` for tabular output, `format=jsondata` for SDMX-JSON,
`format=structurespecificdata` for SDMX-ML structure-specific data, or
`format=genericdata` (default). Use `Accept-Encoding: gzip` for compression.
The format contract is documented at https://data.ecb.europa.eu/help/api/data.

---

## Key Endpoints

### 1. Get Data (Time Series)

```
GET /data/{flowRef}/{key}?{parameters}
```

| Component | Description |
|-----------|-------------|
| `flowRef` | Dataflow ID (e.g., `EXR` for exchange rates, `BSI` for balance sheet items) |
| `key` | Dot-separated dimension values. Use `+` for OR, `.` to skip a dimension (wildcard). |

**Query Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `startPeriod` | No | Start date: `YYYY`, `YYYY-MM`, or `YYYY-MM-DD` |
| `endPeriod` | No | End date: same formats |
| `updatedAfter` | No | ISO 8601 timestamp; returns only data updated after this time |
| `detail` | No | `full` (default), `dataonly`, `serieskeysonly`, `nodata` |
| `firstNObservations` | No | Return only first N observations per series |
| `lastNObservations` | No | Return only last N observations per series |
| `dimensionAtObservation` | No | Typically `TIME_PERIOD` (default) |

**Exchange Rate Key Structure (EXR dataflow):**
`{frequency}.{currency}.{currency_denom}.{exr_type}.{exr_suffix}`

| Position | Dimension | Common Values |
|----------|-----------|---------------|
| 1 | Frequency | `D` (daily), `M` (monthly), `A` (annual) |
| 2 | Currency | `USD`, `GBP`, `JPY`, `CHF`, `CNY`, etc. |
| 3 | Currency denominator | `EUR` (usually) |
| 4 | Exchange rate type | `SP00` (spot), `EN00` (average) |
| 5 | Exchange rate suffix | `A` (average), `E` (end of period) |

**Example -- Daily USD/EUR spot rate, 2024:**
```
GET https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?startPeriod=2024-01-01&endPeriod=2024-12-31
Append `&format=jsondata` to the query URL.
```

**Example -- Monthly GBP and JPY vs EUR, last 12 observations:**
```
GET https://data-api.ecb.europa.eu/service/data/EXR/M.GBP+JPY.EUR.SP00.A?lastNObservations=12
Append `&format=jsondata` to the query URL.
```

**Example -- All daily exchange rates for a specific date (wildcard):**
```
GET https://data-api.ecb.europa.eu/service/data/EXR/D..EUR.SP00.A?startPeriod=2024-06-01&endPeriod=2024-06-01
Append `&format=jsondata` to the query URL.
```

**JSON parsing:** inspect the returned SDMX-JSON structure and use its dimension
metadata to map index keys to series and dates. Do not assume a SDMX-JSON 2.0
`data.structures` envelope. CSV (`format=csvdata`) is simpler for flat analyses;
retain `TIME_PERIOD`, `OBS_VALUE`, unit and observation-status columns.

---

### 2. Get Dataflow Definitions (Available Datasets)

```
GET /dataflow/{agencyID}/{resourceID}/{version}
```

**Example -- List all ECB dataflows:**
```
GET https://data-api.ecb.europa.eu/service/dataflow/ECB
Accept: application/vnd.sdmx.structure+xml;version=2.1
```

**Example -- Get EXR dataflow definition:**
```
GET https://data-api.ecb.europa.eu/service/dataflow/ECB/EXR
Accept: application/vnd.sdmx.structure+xml;version=2.1
```

---

### 3. Get Data Structure Definition (Dimensions & Codes)

```
GET /datastructure/{agencyID}/{resourceID}/{version}?references=children
```

**Example:**
```
GET https://data-api.ecb.europa.eu/service/datastructure/ECB/ECB_EXR1?references=children
Accept: application/vnd.sdmx.structure+xml;version=2.1
```

This returns all dimensions, their code lists, and allowed values -- essential for constructing valid keys.

---

## Common Dataflow IDs

| Dataflow | Description |
|----------|-------------|
| `EXR` | Exchange rates |
| `BSI` | Balance sheet items (monetary financial institutions) |
| `MIR` | MFI interest rates |
| `ILM` | Internal liquidity management |
| `SEC` | Securities issues statistics |
| `BOP` | Balance of payments |
| `STP` | Structural financial indicators |
| `CBD` | Consolidated banking data |
| `ICP` | Index of consumer prices (HICP) |
| `FM` | Financial market data |
| `YC` | Yield curve data |

## Notes
- The SDMX-JSON format is verbose. For simpler parsing, use `format=csvdata`.
- When a dimension is unknown, leave it empty (e.g., `D..EUR.SP00.A`) to get all values for that dimension.
- Use `+` to request multiple values for one dimension (e.g., `USD+GBP`).
- The `detail=dataonly` parameter omits attributes and reduces response size.
- Historical data availability varies by dataflow; exchange rates go back to 1999 (euro introduction).
