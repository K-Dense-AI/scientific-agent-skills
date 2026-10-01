# Google Data Commons API

## Base URL

```
https://api.datacommons.org
```

## Authentication

**API key required.** Obtain through https://apikeys.datacommons.org/.

Pass as query parameter: `&key=YOUR_KEY`

Or as header: `X-API-Key: YOUR_KEY`

All access to the base Data Commons requires a key. Custom Data Commons instances have their own base URL and do not accept the base-service key.

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
| select       | Yes       | Fields to select: `entity`, `variable`, `date`, `value`   |

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

### 4. Supported V2 operations

V2 provides `/observation`, `/node` and `/resolve`, each supporting GET and POST.
It does not expose `/v2/sparql`. For graph queries outside these operations,
consult the documented Data Commons BigQuery access.

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

### 6. Search for statistical variables

Use `/v2/resolve` with `resolver=indicator` and `nodes` containing a natural-language
description. Resolve returns candidate DCIDs and match metadata; inspect the
candidates and variable definitions before retrieving observations.

```bash
# Illustrative authenticated request
curl --fail-with-body --get 'https://api.datacommons.org/v2/resolve' \
  -H "X-API-Key: $DATACOMMONS_API_KEY" \
  --data-urlencode 'nodes=unemployment rate' --data-urlencode 'resolver=indicator'
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

### Resolve and pagination

Resolve responses contain `entities`, each with the input `node` and a list of
`candidates`. For any paginated V2 response, repeat the same request with its
`nextToken` until no continuation token remains. Keep facet provenance with
observations; dates, units and measurement methods can differ across facets.

## Rate Limits

- Base-service requests require an API key; quota depends on the issued key.
- With API key: not formally published, but generally generous for normal use.
- Implement client-side throttling (1-2 requests/second recommended).
- Bulk data available via the Data Commons data download for large-scale analysis.

## Notes

- The V2 API (paths starting with `/v2/`) is the current recommended version.
- Older V1 endpoints (`/v1/bulk/observations/series`, `/stat/value`, etc.) still work but are deprecated.
- DCID = Data Commons Identifier. Every entity, statistical variable, and concept has a unique DCID.
- The knowledge graph includes data from US Census, World Bank, CDC, BLS, FBI, and many other sources.

Official contracts: [V2](https://docs.datacommons.org/api/rest/v2/), [resolve](https://docs.datacommons.org/api/rest/v2/resolve.html).
