# Google Data Commons API

## Base URL

```
https://api.datacommons.org
```

## Authentication

**API key required.** Obtain from the Google Cloud Console (enable the Data Commons API).

Pass as query parameter: `&key=YOUR_KEY`

Or as header: `X-API-Key: YOUR_KEY`

Note: Many endpoints work without a key for light usage, but a key is recommended for reliable access.

## Key Endpoints

### 1. Get Statistical Value (single observation)
```
GET /v2/observation
```
| Parameter    | Required | Description                                                |
|-------------|----------|------------------------------------------------------------|
| key          | Yes      | API key                                                    |
| entity.dcids | Yes     | Place DCID(s) (e.g., `country/USA`, `geoId/06`)          |
| variable.dcids| Yes    | Statistical variable DCID(s)                               |
| date         | No       | Specific date or `LATEST`                                 |
| select       | No       | Fields to select: `entity`, `variable`, `date`, `value`   |

Example:
```
https://api.datacommons.org/v2/observation?key=YOUR_KEY&entity.dcids=country/USA&variable.dcids=Count_Person&date=LATEST&select=entity&select=variable&select=date&select=value
```

### 2. Get Statistical Time Series
```
GET /v2/observation
```
Use same endpoint but omit `date` parameter (or set `date=''`) to get the full time series.

Example (population time series for USA):
```
https://api.datacommons.org/v2/observation?key=YOUR_KEY&entity.dcids=country/USA&variable.dcids=Count_Person&select=entity&select=variable&select=date&select=value
```

### 3. Node Info (property values of an entity)
```
GET /v2/node
```
| Parameter | Required | Description                                        |
|-----------|----------|----------------------------------------------------|
| key       | Yes      | API key                                            |
| nodes     | Yes      | DCID(s) of the node                               |
| property  | Yes      | Property expression: `->prop` (out), `<-prop` (in)|

Example (get properties of California):
```
https://api.datacommons.org/v2/node?key=YOUR_KEY&nodes=geoId/06&property=->*
```

Example (get name of a place):
```
https://api.datacommons.org/v2/node?key=YOUR_KEY&nodes=geoId/06&property=->name
```

### 4. SPARQL Query
```
POST /v2/sparql
```
Content-Type: `application/json`

Body:
```json
{
  "query": "SELECT ?name WHERE { ?state typeOf State . ?state name ?name . ?state containedInPlace country/USA }"
}
```

Pass API key as query param or header.

Example (curl):
```
curl -X POST 'https://api.datacommons.org/v2/sparql?key=YOUR_KEY' \
  -H 'Content-Type: application/json' \
  -d '{"query": "SELECT ?name WHERE { ?place typeOf Country . ?place name ?name } LIMIT 10"}'
```

### 5. Resolve Entities (map names/coords to DCIDs)
```
GET /v2/resolve
```
| Parameter  | Required | Description                                    |
|------------|----------|------------------------------------------------|
| key        | Yes      | API key                                        |
| nodes      | Yes      | Entity identifiers to resolve                 |
| property   | Yes      | `<-description` (name lookup) or coordinate-based |

Example (resolve by name):
```
https://api.datacommons.org/v2/resolve?key=YOUR_KEY&nodes=California&property=<-description->dcid
```

### 6. Search for Statistical Variables
```
GET /v2/variable/search
```
| Parameter | Required | Description            |
|-----------|----------|------------------------|
| key       | Yes      | API key                |
| query     | Yes      | Search keywords        |

Example:
```
https://api.datacommons.org/v2/variable/search?key=YOUR_KEY&query=unemployment+rate
```

## Common DCIDs

### Places
| DCID              | Description          |
|-------------------|----------------------|
| country/USA       | United States        |
| country/GBR       | United Kingdom       |
| country/CHN       | China                |
| geoId/06          | California           |
| geoId/0667000     | San Francisco city   |
| geoId/06085       | Santa Clara County   |

### Statistical Variables
| DCID                                    | Description                    |
|-----------------------------------------|--------------------------------|
| Count_Person                            | Total population               |
| Count_Person_Employed                   | Employed persons               |
| UnemploymentRate_Person                 | Unemployment rate              |
| Median_Income_Person                    | Median income                  |
| Amount_EconomicActivity_GrossDomesticProduction_Nominal | Nominal GDP     |
| Mean_ConsumerPriceIndex                 | Consumer price index           |
| Count_Death                             | Number of deaths               |
| Count_Person_BelowPovertyLevelInThePast12Months | Persons in poverty  |
| Median_Age_Person                       | Median age                     |

## Response Format

### Observation response
```json
{
  "byVariable": {
    "Count_Person": {
      "byEntity": {
        "country/USA": {
          "orderedFacets": [
            {
              "facetId": "2176550201",
              "observations": [
                {
                  "date": "2020",
                  "value": 331449281
                },
                {
                  "date": "2021",
                  "value": 331893745
                }
              ]
            }
          ]
        }
      }
    }
  },
  "facets": {
    "2176550201": {
      "importName": "CensusACS5YearSurvey",
      "provenanceUrl": "https://www.census.gov/",
      "measurementMethod": "CensusACS5yrSurvey"
    }
  }
}
```

### Node response
```json
{
  "data": {
    "geoId/06": {
      "arcs": {
        "name": {
          "nodes": [
            {
              "value": "California"
            }
          ]
        }
      }
    }
  }
}
```

### SPARQL response
```json
{
  "header": ["?name"],
  "rows": [
    { "cells": [{ "value": "Alabama" }] },
    { "cells": [{ "value": "Alaska" }] }
  ]
}
```

### Variable search response
```json
{
  "variables": [
    {
      "dcid": "UnemploymentRate_Person",
      "displayName": "Unemployment Rate"
    }
  ]
}
```

## Rate Limits

- Without API key: very limited (roughly a few requests per minute; may be blocked).
- With API key: not formally published, but generally generous for normal use.
- Implement client-side throttling (1-2 requests/second recommended).
- Bulk data available via the Data Commons data download for large-scale analysis.

## Notes

- The V2 API (paths starting with `/v2/`) is the current recommended version.
- Older V1 endpoints (`/v1/bulk/observations/series`, `/stat/value`, etc.) still work but are deprecated.
- DCID = Data Commons Identifier. Every entity, statistical variable, and concept has a unique DCID.
- The knowledge graph includes data from US Census, World Bank, CDC, BLS, FBI, and many other sources.
