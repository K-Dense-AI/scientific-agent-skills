# Bureau of Labor Statistics (BLS) Public Data API

## Base URL

```
https://api.bls.gov/publicAPI/v2
```

Version 1 (no key): `https://api.bls.gov/publicAPI/v1`

## Authentication

**API key optional but strongly recommended.** Register at https://data.bls.gov/registrationEngine/

- **V1 (no key):** Limited to 25 requests/day, 10-year date range, 25 series per query.
- **V2 (with key):** 500 requests/day, 20-year date range, 50 series per query, plus catalog data and calculations.

## Key Endpoints

### 1. Get Series Data (POST -- primary method)
```
POST /timeseries/data/
```
Content-Type: `application/json`

**Request body:**
```json
{
  "seriesid": ["CUUR0000SA0", "LNS14000000"],
  "startyear": "2020",
  "endyear": "2024",
  "registrationkey": "YOUR_KEY",
  "catalog": true,
  "calculations": true,
  "annualaverage": true,
  "aspects": true
}
```

| Field            | Required | V1  | V2  | Description                                          |
|------------------|----------|-----|-----|------------------------------------------------------|
| seriesid         | Yes      | Yes | Yes | Array of series IDs (max 25 v1 / 50 v2)            |
| startyear        | Yes      | Yes | Yes | 4-digit start year                                  |
| endyear          | Yes      | Yes | Yes | 4-digit end year                                    |
| registrationkey  | No       | No  | Yes | API key (required for v2 features)                  |
| catalog          | No       | No  | Yes | `true` to include series metadata                   |
| calculations     | No       | No  | Yes | `true` to include net/pct changes                   |
| annualaverage    | No       | No  | Yes | `true` to include annual averages                   |
| aspects          | No       | No  | Yes | `true` to include footnotes and aspects             |

### 2. Get Single Series Data (GET -- convenience)
```
GET /timeseries/data/{seriesID}
```
Example:
```
https://api.bls.gov/publicAPI/v2/timeseries/data/CUUR0000SA0?registrationkey=YOUR_KEY&startyear=2022&endyear=2024
```

### 3. Latest Data (GET -- no date range)
```
GET /timeseries/data/{seriesID}
```
Without startyear/endyear, returns the most recent 3 years.

Example:
```
https://api.bls.gov/publicAPI/v2/timeseries/data/LNS14000000?registrationkey=YOUR_KEY
```

## Common Series IDs

### Consumer Price Index (CPI)
| Series ID       | Description                                       |
|-----------------|---------------------------------------------------|
| CUUR0000SA0     | CPI-U All Items, US City Avg, Not Seasonally Adj  |
| CUSR0000SA0     | CPI-U All Items, US City Avg, Seasonally Adj      |
| CUUR0000SAF1    | CPI-U Food, US City Avg                           |
| CUUR0000SETB01  | CPI-U Gasoline (all types)                        |
| CUUR0000SAH1    | CPI-U Shelter                                     |
| CUUR0000SAM     | CPI-U Medical Care                                |

CPI series ID structure: `CU` + `U/S` (unadj/adj) + `R/S` (revision) + area code + item code

### Employment / Unemployment (Current Population Survey)
| Series ID       | Description                                       |
|-----------------|---------------------------------------------------|
| LNS14000000     | Unemployment Rate (seasonally adjusted)            |
| LNS11000000     | Civilian Labor Force Level                         |
| LNS12000000     | Employment Level                                   |
| LNS13000000     | Unemployment Level                                 |
| LNS14000006     | Unemployment Rate - Black or African American      |
| LNS14000009     | Unemployment Rate - Hispanic or Latino             |

### Employment (Current Employment Statistics / Nonfarm Payrolls)
| Series ID       | Description                                       |
|-----------------|---------------------------------------------------|
| CES0000000001   | Total Nonfarm Employment (seasonally adj)          |
| CES0500000003   | Average Hourly Earnings, Total Private             |
| CES0500000002   | Average Weekly Hours, Total Private                |

### Producer Price Index (PPI)
| Series ID       | Description                                       |
|-----------------|---------------------------------------------------|
| WPSFD4          | PPI Final Demand                                  |
| WPUFD49104      | PPI Final Demand less Foods & Energy              |

### Employment Cost Index (ECI)
| Series ID       | Description                                       |
|-----------------|---------------------------------------------------|
| CIU1010000000000A | ECI Total Compensation, All Civilians           |

### Occupational Employment & Wage Statistics (OEWS)
| Series ID Pattern | Description                                     |
|-------------------|-------------------------------------------------|
| OEUM003342000000011-0000 | Example: specific occupation/area combo  |

OEWS series IDs are complex. Use the BLS Series ID finder: https://data.bls.gov/cgi-bin/srgate

## Series ID Structure

BLS series IDs encode survey, seasonal adjustment, area, industry, and item information. Key survey prefixes:

| Prefix | Survey                                          |
|--------|------------------------------------------------|
| CU     | Consumer Price Index                            |
| LN     | Current Population Survey (Labor Force)         |
| CE     | Current Employment Statistics                   |
| WP     | Producer Price Index                            |
| EI     | Employment Cost Index / National Compensation   |
| OE     | Occupational Employment & Wage Statistics       |
| LA     | Local Area Unemployment Statistics              |
| SM     | State and Metro Area Employment (CES)           |
| JT     | Job Openings and Labor Turnover (JOLTS)         |

## Response Format

### Standard response
```json
{
  "status": "REQUEST_SUCCEEDED",
  "responseTime": 85,
  "message": [],
  "Results": {
    "series": [
      {
        "seriesID": "CUUR0000SA0",
        "catalog": {
          "series_title": "All items in U.S. city average, all urban consumers, not seasonally adjusted",
          "series_id": "CUUR0000SA0",
          "seasonality": "Not Seasonally Adjusted",
          "survey_name": "Consumer Price Index - All Urban Consumers",
          "survey_abbreviation": "CU",
          "measure_data_type": "All items",
          "area": "U.S. city average",
          "item": "All items"
        },
        "data": [
          {
            "year": "2024",
            "period": "M01",
            "periodName": "January",
            "latest": "true",
            "value": "308.417",
            "footnotes": [{}],
            "calculations": {
              "net_changes": {
                "1": "0.5",
                "3": "1.2",
                "6": "2.1",
                "12": "3.1"
              },
              "pct_changes": {
                "1": "0.2",
                "3": "0.4",
                "6": "0.7",
                "12": "3.1"
              }
            }
          },
          {
            "year": "2023",
            "period": "M12",
            "periodName": "December",
            "value": "306.746",
            "footnotes": [{}]
          }
        ]
      }
    ]
  }
}
```

### Key fields in data objects
- `year`: 4-digit year string
- `period`: `M01`-`M12` (monthly), `Q01`-`Q05` (quarterly), `A01` (annual), `S01`-`S03` (semi-annual)
- `periodName`: Human-readable period name
- `value`: String (convert to float for calculations)
- `latest`: `"true"` on the most recent observation only
- `calculations`: Only present when `calculations: true` in request (V2). Contains `net_changes` and `pct_changes` over 1, 3, 6, 12 month spans.
- `footnotes`: Array of footnote objects

### Error response
```json
{
  "status": "REQUEST_NOT_PROCESSED",
  "responseTime": 10,
  "message": ["No data available for the given series and date range."],
  "Results": {
    "series": []
  }
}
```

## Rate Limits

| Feature             | V1 (no key)     | V2 (with key)    |
|---------------------|-----------------|------------------|
| Daily query limit   | 25 requests     | 500 requests     |
| Series per query    | 25              | 50               |
| Years per query     | 10              | 20               |
| Catalog data        | No              | Yes              |
| Calculations        | No              | Yes              |
| Annual averages     | No              | Yes              |
| Net/pct changes     | No              | Yes              |

## Notes

- BLS strongly prefers POST requests for data retrieval. The GET endpoint is a convenience wrapper.
- Period `M13` represents the annual average (only present when `annualaverage: true`).
- All `value` fields are strings. Missing data is typically omitted (the observation simply won't appear).
- For CPI percent change (inflation rate), you can either calculate from raw index values or use the V2 `calculations` feature which provides pre-computed 12-month percent changes.
- The BLS website has a Series ID finder tool for constructing IDs: https://data.bls.gov/cgi-bin/srgate
- Bulk data is available for download at https://download.bls.gov/pub/time.series/ organized by survey prefix.
