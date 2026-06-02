# World Bank Open Data API

## Base URL

```
https://api.worldbank.org/v2
```

## Authentication

**No API key required.** The API is fully open.

## Key Endpoints

### 1. Get Indicator Data for a Country
```
GET /country/{country_code}/indicator/{indicator_code}
```
| Parameter | Required | Description                                        |
|-----------|----------|----------------------------------------------------|
| format    | No       | `json`, `xml` (default), `jsonP`                  |
| date      | No       | Year range: `2010:2023`, single year: `2020`       |
| page      | No       | Page number (default 1)                            |
| per_page  | No       | Results per page (default 50, max 32500)           |
| MRV       | No       | Most recent values: number of recent data points   |
| gapfill   | No       | `Y` to fill gaps with most recent value            |
| frequency | No       | `M` (monthly), `Q` (quarterly), `Y` (yearly)      |
| source    | No       | Source ID number                                   |

Example (GDP for USA, 2015-2023):
```
https://api.worldbank.org/v2/country/US/indicator/NY.GDP.MKTP.CD?format=json&date=2015:2023
```

Example (most recent 5 values):
```
https://api.worldbank.org/v2/country/US/indicator/NY.GDP.MKTP.CD?format=json&MRV=5
```

### 2. Get Indicator Data for Multiple Countries
```
GET /country/{code1};{code2};{code3}/indicator/{indicator_code}
```
Example:
```
https://api.worldbank.org/v2/country/US;GB;CN;IN/indicator/SP.POP.TOTL?format=json&date=2020:2023
```

### 3. Get Indicator Data for All Countries
```
GET /country/all/indicator/{indicator_code}
```
Example:
```
https://api.worldbank.org/v2/country/all/indicator/SI.POV.DDAY?format=json&date=2020&per_page=300
```

### 4. Get Indicator Data by Region/Income Group
```
GET /country/{aggregate_code}/indicator/{indicator_code}
```
Aggregate codes: `EAS` (East Asia), `ECS` (Europe & Central Asia), `LIC` (Low Income), `HIC` (High Income), `WLD` (World), etc.

Example:
```
https://api.worldbank.org/v2/country/WLD/indicator/NY.GDP.MKTP.CD?format=json&date=2020:2023
```

### 5. List All Countries
```
GET /country
```
Example:
```
https://api.worldbank.org/v2/country?format=json&per_page=300
```

### 6. Get Country Info
```
GET /country/{country_code}
```
Example:
```
https://api.worldbank.org/v2/country/US?format=json
```

### 7. List All Indicators
```
GET /indicator
```
Example:
```
https://api.worldbank.org/v2/indicator?format=json&per_page=100
```

### 8. Search Indicators
```
GET /indicator
```
Use the query string directly in the URL path or filter by topic/source.

By topic:
```
https://api.worldbank.org/v2/topic/3/indicator?format=json
```

By source:
```
https://api.worldbank.org/v2/source/2/indicator?format=json&per_page=50
```

### 9. List Topics
```
GET /topic
```
Example:
```
https://api.worldbank.org/v2/topic?format=json
```

### 10. List Sources
```
GET /source
```
Example:
```
https://api.worldbank.org/v2/source?format=json
```

## Common Indicator Codes

| Indicator Code         | Description                                     |
|------------------------|-------------------------------------------------|
| NY.GDP.MKTP.CD        | GDP (current US$)                               |
| NY.GDP.MKTP.KD.ZG     | GDP growth (annual %)                           |
| NY.GDP.PCAP.CD        | GDP per capita (current US$)                    |
| NY.GDP.PCAP.PP.CD     | GDP per capita, PPP (current intl $)            |
| SP.POP.TOTL           | Population, total                               |
| SP.POP.GROW           | Population growth (annual %)                    |
| SP.DYN.LE00.IN        | Life expectancy at birth (years)                |
| SP.DYN.TFRT.IN        | Fertility rate (births per woman)               |
| SL.UEM.TOTL.ZS        | Unemployment (% of total labor force)           |
| FP.CPI.TOTL.ZG        | Inflation, consumer prices (annual %)           |
| SI.POV.DDAY           | Poverty headcount at $2.15/day (% of pop)       |
| SI.POV.GINI           | Gini index                                      |
| BX.KLT.DINV.CD.WD     | Foreign direct investment, net inflows (BoP, US$)|
| NE.EXP.GNFS.ZS        | Exports of goods and services (% of GDP)        |
| EN.ATM.CO2E.PC        | CO2 emissions (metric tons per capita)          |
| SE.ADT.LITR.ZS        | Literacy rate, adult (% ages 15+)               |
| SH.XPD.CHEX.PC.CD     | Current health expenditure per capita (US$)     |
| IT.NET.USER.ZS        | Individuals using the Internet (% of pop)       |

## Common Country Codes (ISO 3166-1 alpha-2)

`US` (USA), `GB` (UK), `CN` (China), `IN` (India), `JP` (Japan), `DE` (Germany), `FR` (France), `BR` (Brazil), `ZA` (South Africa), `NG` (Nigeria), `AU` (Australia), `CA` (Canada)

## Response Format

**Important:** JSON responses are returned as a **two-element array**. The first element is pagination metadata; the second is the data array.

### Indicator observations
```json
[
  {
    "page": 1,
    "pages": 1,
    "per_page": 50,
    "total": 9,
    "sourceid": "2",
    "lastupdated": "2024-03-28"
  },
  [
    {
      "indicator": {
        "id": "NY.GDP.MKTP.CD",
        "value": "GDP (current US$)"
      },
      "country": {
        "id": "US",
        "value": "United States"
      },
      "countryiso3code": "USA",
      "date": "2023",
      "value": 27360935000000,
      "unit": "",
      "obs_status": "",
      "decimal": 0
    },
    {
      "indicator": { "id": "NY.GDP.MKTP.CD", "value": "GDP (current US$)" },
      "country": { "id": "US", "value": "United States" },
      "countryiso3code": "USA",
      "date": "2022",
      "value": 25462700000000,
      "unit": "",
      "obs_status": "",
      "decimal": 0
    }
  ]
]
```

Note: `value` is `null` when data is unavailable for that year.

### Country info
```json
[
  { "page": 1, "pages": 1, "per_page": 50, "total": 1 },
  [
    {
      "id": "US",
      "iso2Code": "US",
      "name": "United States",
      "region": { "id": "NAC", "iso2code": "XU", "value": "North America" },
      "adminregion": { "id": "", "iso2code": "", "value": "" },
      "incomeLevel": { "id": "HIC", "iso2code": "XD", "value": "High income" },
      "lendingType": { "id": "LNX", "iso2code": "XX", "value": "Not classified" },
      "capitalCity": "Washington D.C.",
      "longitude": "-77.032",
      "latitude": "38.8895"
    }
  ]
]
```

## Rate Limits

- No formal rate limits published; the API is open and generous.
- For bulk downloads, use `per_page=32500` to minimize requests.
- Be respectful: 1-2 requests/second for automated scripts.
- For very large datasets, consider the World Bank bulk download facility.

## Notes

- Always include `format=json` -- the default is XML.
- Results are returned in **descending** date order by default.
- `null` values are common for recent years (data not yet published) or for indicators with sparse coverage.
- Pagination: check `pages` in the metadata; iterate `page=1`, `page=2`, etc.
- Country codes follow ISO 3166-1 alpha-2 (2-letter) in the URL path. The response also includes `countryiso3code`.
