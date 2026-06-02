# Federal Reserve Economic Data (FRED) API

## Base URL

```
https://api.stlouisfed.org/fred
```

## Authentication

**API key required.** Register at https://fred.stlouisfed.org/docs/api/api_key.html

Pass as query parameter: `&api_key=YOUR_KEY`

## Key Endpoints

### Get a Series (metadata)
```
GET /series
```
| Parameter   | Required | Description                        |
|-------------|----------|------------------------------------|
| series_id   | Yes      | FRED series ID (e.g., `FEDFUNDS`) |
| api_key     | Yes      | Your API key                       |
| file_type   | No       | `json` (default), `xml`           |

Example:
```
https://api.stlouisfed.org/fred/series?series_id=FEDFUNDS&api_key=YOUR_KEY&file_type=json
```

### Get Series Observations (the actual data points)
```
GET /series/observations
```
| Parameter         | Required | Description                                            |
|-------------------|----------|--------------------------------------------------------|
| series_id         | Yes      | FRED series ID                                         |
| api_key           | Yes      | Your API key                                           |
| file_type         | No       | `json`, `xml`                                          |
| observation_start | No       | `YYYY-MM-DD` start date                               |
| observation_end   | No       | `YYYY-MM-DD` end date                                 |
| units             | No       | `lin` (levels), `chg`, `ch1`, `pch`, `pc1`, `pca`, `cch`, `cca`, `log` |
| frequency         | No       | `d`, `w`, `bw`, `m`, `q`, `sa`, `a` (daily to annual)|
| aggregation_method| No       | `avg`, `sum`, `eop`                                   |
| sort_order        | No       | `asc` (default), `desc`                               |
| limit             | No       | Max observations (default 100000)                      |
| offset            | No       | Pagination offset                                      |

Example:
```
https://api.stlouisfed.org/fred/series/observations?series_id=FEDFUNDS&api_key=YOUR_KEY&file_type=json&observation_start=2023-01-01&observation_end=2024-01-01
```

### Search for Series
```
GET /series/search
```
| Parameter     | Required | Description                                  |
|---------------|----------|----------------------------------------------|
| search_text   | Yes      | Keywords to search                           |
| api_key       | Yes      | Your API key                                 |
| file_type     | No       | `json`, `xml`                                |
| search_type   | No       | `full_text` (default), `series_id`           |
| limit         | No       | Max results (default 1000)                   |
| offset        | No       | Pagination offset                            |
| order_by      | No       | `search_rank`, `series_id`, `title`, `units`, `frequency`, `seasonal_adjustment`, `realtime_start`, `realtime_end`, `last_updated`, `observation_start`, `observation_end`, `popularity`, `group_popularity` |
| tag_names     | No       | Semicolon-delimited tag filter               |

Example:
```
https://api.stlouisfed.org/fred/series/search?search_text=monetary+base&api_key=YOUR_KEY&file_type=json&limit=10
```

### Get Categories for a Series
```
GET /series/categories
```
Example:
```
https://api.stlouisfed.org/fred/series/categories?series_id=FEDFUNDS&api_key=YOUR_KEY&file_type=json
```

### Browse Categories
```
GET /category
GET /category/children
GET /category/series
```
Example (root category):
```
https://api.stlouisfed.org/fred/category?category_id=0&api_key=YOUR_KEY&file_type=json
```

### Get Releases
```
GET /releases
GET /release/series
```
Example:
```
https://api.stlouisfed.org/fred/release/series?release_id=10&api_key=YOUR_KEY&file_type=json
```

### Get Tags
```
GET /tags
GET /series/tags
```

## Common Series IDs

| Series ID   | Description                              |
|-------------|------------------------------------------|
| FEDFUNDS    | Federal Funds Effective Rate             |
| DFF         | Federal Funds Rate (daily)               |
| DGS10       | 10-Year Treasury Constant Maturity Rate  |
| DGS2        | 2-Year Treasury Constant Maturity Rate   |
| M2SL        | M2 Money Stock                           |
| CPIAUCSL    | Consumer Price Index (All Urban)         |
| UNRATE      | Unemployment Rate                        |
| GDP         | Gross Domestic Product                   |
| GDPC1       | Real GDP                                 |
| A191RL1Q225SBEA | Real GDP Growth Rate (quarterly)    |
| PAYEMS      | Total Nonfarm Payrolls                   |
| T10Y2Y      | 10Y-2Y Treasury Spread                  |
| MORTGAGE30US| 30-Year Fixed Mortgage Rate              |
| DTWEXBGS    | Trade Weighted US Dollar Index           |
| BOGMBASE    | Monetary Base (total)                    |
| WALCL       | Fed Total Assets                         |

## Response Format

### Series metadata (`/series`)
```json
{
  "realtime_start": "2024-01-01",
  "realtime_end": "2024-01-01",
  "seriess": [
    {
      "id": "FEDFUNDS",
      "realtime_start": "2024-01-01",
      "realtime_end": "2024-01-01",
      "title": "Federal Funds Effective Rate",
      "observation_start": "1954-07-01",
      "observation_end": "2024-01-01",
      "frequency": "Monthly",
      "frequency_short": "M",
      "units": "Percent",
      "units_short": "%",
      "seasonal_adjustment": "Not Seasonally Adjusted",
      "seasonal_adjustment_short": "NSA",
      "last_updated": "2024-02-01 15:51:07-06",
      "popularity": 95,
      "notes": "..."
    }
  ]
}
```

### Observations (`/series/observations`)
```json
{
  "realtime_start": "2024-01-01",
  "realtime_end": "2024-01-01",
  "observation_start": "2023-01-01",
  "observation_end": "2024-01-01",
  "units": "lin",
  "output_type": 1,
  "file_type": "json",
  "order_by": "observation_date",
  "sort_order": "asc",
  "count": 12,
  "offset": 0,
  "limit": 100000,
  "observations": [
    {
      "realtime_start": "2024-01-01",
      "realtime_end": "2024-01-01",
      "date": "2023-01-01",
      "value": "4.33"
    }
  ]
}
```

Note: `value` is always a string. Missing data appears as `"."`.

### Search results (`/series/search`)
```json
{
  "realtime_start": "...",
  "realtime_end": "...",
  "order_by": "search_rank",
  "sort_order": "desc",
  "count": 500,
  "offset": 0,
  "limit": 1000,
  "seriess": [
    {
      "id": "BOGMBASE",
      "title": "Monetary Base; Total",
      "frequency": "Bi-Weekly",
      "units": "Millions of Dollars",
      "popularity": 72,
      "notes": "..."
    }
  ]
}
```

## Rate Limits

- **120 requests per minute** per API key.
- No daily limit documented, but excessive use may be throttled.
- Responses include no rate-limit headers; implement client-side throttling.
