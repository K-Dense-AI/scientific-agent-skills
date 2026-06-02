# FRED (Federal Reserve Economic Data) API Reference

## Overview
The FRED API, provided by the Federal Reserve Bank of St. Louis, offers access to over 800,000 economic time series from 100+ sources. Covers GDP, employment, inflation, interest rates, money supply, trade, housing, and much more.

## Base URL
```
https://api.stlouisfed.org/fred
```

## Authentication
- **API Key: REQUIRED.** Register at https://fred.stlouisfed.org/docs/api/api_key.html
- Pass as query parameter: `&api_key=YOUR_KEY`

## Rate Limits
- **120 requests per minute** per API key.
- No daily limit documented, but excessive use may trigger throttling.

## Common Parameters (apply to most endpoints)
| Parameter       | Type   | Required | Default | Description |
|----------------|--------|----------|---------|-------------|
| `api_key`      | string | Yes      | -       | Your FRED API key. |
| `file_type`    | string | No       | `xml`   | Response format: `xml` or `json`. |
| `realtime_start` | string | No     | today   | Start of real-time period `YYYY-MM-DD`. |
| `realtime_end`   | string | No     | today   | End of real-time period `YYYY-MM-DD`. |

---

## Key Endpoints

### 1. Series Observations (Time Series Data)

#### `GET /fred/series/observations`
Returns the data values for an economic time series.

**Parameters:**
| Parameter           | Type   | Required | Default       | Description |
|--------------------|--------|----------|---------------|-------------|
| `series_id`        | string | Yes      | -             | FRED series ID (e.g., `GDP`, `UNRATE`, `CPIAUCSL`). |
| `observation_start`| string | No       | `1776-07-04`  | Start date `YYYY-MM-DD`. |
| `observation_end`  | string | No       | `9999-12-31`  | End date `YYYY-MM-DD`. |
| `units`            | string | No       | `lin`         | Data transformation: `lin` (levels), `chg` (change), `ch1` (change from year ago), `pch` (% change), `pc1` (% change from year ago), `pca` (compounded annual % change), `cch` (continuously compounded rate of change), `cca` (continuously compounded annual rate), `log` (natural log). |
| `frequency`        | string | No       | (native)      | Aggregation frequency: `d`, `w`, `bw`, `m`, `q`, `sa`, `a` (daily through annual). |
| `aggregation_method` | string | No    | `avg`         | `avg`, `sum`, `eop` (end of period). |
| `sort_order`       | string | No       | `asc`         | `asc` or `desc`. |
| `limit`            | int    | No       | 100000        | Max observations returned (max 100000). |
| `offset`           | int    | No       | 0             | Pagination offset. |

**Example:**
```
https://api.stlouisfed.org/fred/series/observations?series_id=GDP&api_key=YOUR_KEY&file_type=json&observation_start=2020-01-01&observation_end=2024-12-31&units=pch&frequency=q
```

**Response:**
```json
{
  "realtime_start": "2024-11-01",
  "realtime_end": "2024-11-01",
  "observation_start": "2020-01-01",
  "observation_end": "2024-12-31",
  "units": "Percent Change",
  "output_type": 1,
  "file_type": "json",
  "order_by": "observation_date",
  "sort_order": "asc",
  "count": 20,
  "offset": 0,
  "limit": 100000,
  "observations": [
    {
      "realtime_start": "2024-11-01",
      "realtime_end": "2024-11-01",
      "date": "2020-01-01",
      "value": "-1.3"
    },
    {
      "realtime_start": "2024-11-01",
      "realtime_end": "2024-11-01",
      "date": "2020-04-01",
      "value": "-8.4"
    }
  ]
}
```

Note: `value` is always a string. Missing values appear as `"."`.

---

### 2. Series Info (Metadata)

#### `GET /fred/series`
Returns metadata for a series.

**Parameters:**
| Parameter   | Type   | Required | Description |
|------------|--------|----------|-------------|
| `series_id`| string | Yes      | FRED series ID. |

**Example:**
```
https://api.stlouisfed.org/fred/series?series_id=UNRATE&api_key=YOUR_KEY&file_type=json
```

**Response:**
```json
{
  "realtime_start": "2024-11-01",
  "realtime_end": "2024-11-01",
  "seriess": [
    {
      "id": "UNRATE",
      "title": "Unemployment Rate",
      "observation_start": "1948-01-01",
      "observation_end": "2024-10-01",
      "frequency": "Monthly",
      "frequency_short": "M",
      "units": "Percent",
      "units_short": "%",
      "seasonal_adjustment": "Seasonally Adjusted",
      "seasonal_adjustment_short": "SA",
      "last_updated": "2024-11-01 07:41:02-05",
      "popularity": 95,
      "notes": "The unemployment rate represents..."
    }
  ]
}
```

---

### 3. Series Search

#### `GET /fred/series/search`
Search for series by keywords.

**Parameters:**
| Parameter       | Type   | Required | Default        | Description |
|----------------|--------|----------|----------------|-------------|
| `search_text`  | string | Yes      | -              | Keywords to search. |
| `search_type`  | string | No       | `full_text`    | `full_text` or `series_id`. |
| `order_by`     | string | No       | `search_rank`  | `search_rank`, `series_id`, `title`, `units`, `frequency`, `seasonal_adjustment`, `realtime_start`, `realtime_end`, `last_updated`, `observation_start`, `observation_end`, `popularity`, `group_popularity`. |
| `sort_order`   | string | No       | `asc`          | `asc` or `desc`. |
| `limit`        | int    | No       | 1000           | Max results (max 1000). |
| `offset`       | int    | No       | 0              | Pagination offset. |
| `filter_variable` | string | No    | -              | `frequency`, `units`, `seasonal_adjustment`. |
| `filter_value` | string | No       | -              | Value to filter on (e.g., `Monthly`). |
| `tag_names`    | string | No       | -              | Semicolon-delimited tags to filter (e.g., `gdp;quarterly`). |

**Example:**
```
https://api.stlouisfed.org/fred/series/search?search_text=consumer+price+index&api_key=YOUR_KEY&file_type=json&limit=5
```

**Response:**
```json
{
  "realtime_start": "2024-11-01",
  "realtime_end": "2024-11-01",
  "order_by": "search_rank",
  "sort_order": "asc",
  "count": 1256,
  "offset": 0,
  "limit": 5,
  "seriess": [
    {
      "id": "CPIAUCSL",
      "title": "Consumer Price Index for All Urban Consumers: All Items in U.S. City Average",
      "observation_start": "1947-01-01",
      "observation_end": "2024-09-01",
      "frequency": "Monthly",
      "units": "Index 1982-1984=100",
      "seasonal_adjustment": "Seasonally Adjusted",
      "popularity": 95
    }
  ]
}
```

---

### 4. Category Lookup

#### `GET /fred/category`
Get info for a specific category.

**Parameters:**
| Parameter    | Type | Required | Description |
|-------------|------|----------|-------------|
| `category_id`| int | Yes      | Category ID (0 = root). |

**Example:**
```
https://api.stlouisfed.org/fred/category?category_id=0&api_key=YOUR_KEY&file_type=json
```

#### `GET /fred/category/children`
Get child categories.

**Example:**
```
https://api.stlouisfed.org/fred/category/children?category_id=0&api_key=YOUR_KEY&file_type=json
```

#### `GET /fred/category/series`
Get all series in a category.

**Parameters:**
| Parameter    | Type | Required | Description |
|-------------|------|----------|-------------|
| `category_id`| int | Yes      | Category ID. |
| `limit`     | int  | No       | Max results (max 1000). |
| `offset`    | int  | No       | Pagination offset. |

**Example:**
```
https://api.stlouisfed.org/fred/category/series?category_id=125&api_key=YOUR_KEY&file_type=json
```

---

### 5. Releases

#### `GET /fred/releases`
Get all economic data releases.

**Example:**
```
https://api.stlouisfed.org/fred/releases?api_key=YOUR_KEY&file_type=json
```

#### `GET /fred/release/series`
Get all series in a specific release.

**Parameters:**
| Parameter   | Type | Required | Description |
|------------|------|----------|-------------|
| `release_id`| int | Yes      | Release ID. |

**Example:**
```
https://api.stlouisfed.org/fred/release/series?release_id=53&api_key=YOUR_KEY&file_type=json
```

---

### 6. Tags

#### `GET /fred/tags`
Get all tags and their frequency of use.

#### `GET /fred/series/search/tags`
Get tags matching a series search.

**Example:**
```
https://api.stlouisfed.org/fred/series/search/tags?series_search_text=mortgage+rate&api_key=YOUR_KEY&file_type=json
```

---

## Commonly Used Series IDs

| Series ID     | Description |
|--------------|-------------|
| `GDP`        | Gross Domestic Product (quarterly, billions $) |
| `GDPC1`     | Real GDP (chained 2017 dollars) |
| `A191RL1Q225SBEA` | Real GDP growth rate (annualized quarterly) |
| `UNRATE`    | Unemployment Rate (monthly, %) |
| `PAYEMS`    | Total Nonfarm Payrolls (monthly, thousands) |
| `CPIAUCSL`  | CPI All Urban Consumers (monthly, index) |
| `CPILFESL`  | Core CPI (excl. food & energy) |
| `PCEPI`     | PCE Price Index |
| `PCEPILFE`  | Core PCE Price Index |
| `FEDFUNDS`  | Federal Funds Effective Rate (monthly, %) |
| `DFF`       | Federal Funds Effective Rate (daily) |
| `DGS10`     | 10-Year Treasury Constant Maturity Rate (daily) |
| `DGS2`      | 2-Year Treasury Rate (daily) |
| `T10Y2Y`    | 10Y-2Y Treasury Spread |
| `MORTGAGE30US` | 30-Year Fixed Mortgage Rate (weekly) |
| `M2SL`      | M2 Money Stock (monthly) |
| `HOUST`     | Housing Starts (monthly, thousands) |
| `RSAFS`     | Retail Sales (monthly, millions $) |
| `INDPRO`    | Industrial Production Index |
| `UMCSENT`   | U. of Michigan Consumer Sentiment |
| `SP500`     | S&P 500 Index (daily) |
| `VIXCLS`    | CBOE Volatility Index (daily) |
| `DEXUSEU`   | USD/EUR Exchange Rate (daily) |
| `DCOILWTICO`| WTI Crude Oil Price (daily) |
| `BOPGSTB`   | Trade Balance (monthly, millions $) |
| `GFDEBTN`   | Federal Debt Total Public Debt |

## Notes
- Real-time periods: FRED supports vintage data. The `realtime_start`/`realtime_end` parameters let you retrieve data as it was known at a specific point in time (useful for analyzing data revisions).
- The `units` parameter for transformations is very powerful -- it avoids having to compute percent changes client-side.
- Values are returned as strings; `"."` means missing/unavailable.
- For FRED bulk data, they offer a download API at `https://api.stlouisfed.org/geofred/` for geographic/regional data.
