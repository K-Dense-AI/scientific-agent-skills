# NOAA Climate Data Online (CDO) API Reference

## Base URL
```
https://www.ncdc.noaa.gov/cdo-web/api/v2
```

## Authentication
- **API Token: REQUIRED.** Request a free token at https://www.ncdc.noaa.gov/cdo-web/token
- Pass as HTTP header: `Token: YOUR_TOKEN`

## Rate Limits
- **5 requests per second** per token.
- **10,000 requests per day** per token.
- Queries are limited to **1,000 results per request** (use `offset` for pagination).
- Date ranges limited to **1 year per request** for the `/data` endpoint.

## Common Parameters (apply to most endpoints)
| Parameter      | Type   | Required | Default | Description |
|---------------|--------|----------|---------|-------------|
| `datasetid`   | string | Varies   | -       | Dataset ID (e.g. `GHCND`, `GSOM`). |
| `datatypeid`  | string | No       | -       | Data type filter (e.g. `TMAX`, `PRCP`). |
| `locationid`  | string | No       | -       | Location ID (e.g. `FIPS:37`, `ZIP:28801`, `CITY:US390029`). |
| `stationid`   | string | No       | -       | Station ID (e.g. `GHCND:USW00013874`). |
| `startdate`   | string | Varies   | -       | ISO date `YYYY-MM-DD`. |
| `enddate`     | string | Varies   | -       | ISO date `YYYY-MM-DD`. |
| `units`       | string | No       | `standard` | `standard` or `metric`. |
| `limit`       | int    | No       | 25      | Results per page (max 1000). |
| `offset`      | int    | No       | 1       | Pagination offset (1-based). |
| `sortfield`   | string | No       | -       | Field to sort by (e.g. `date`, `name`). |
| `sortorder`   | string | No       | `asc`   | `asc` or `desc`. |

---

## Key Endpoints

### 1. Data (Observations)
```
GET /data
```
Returns actual observation data. This is the primary data retrieval endpoint.

**Required parameters:** `datasetid`, `startdate`, `enddate`.

**Example -- daily max temperature for a station:**
```bash
curl -H "Token: YOUR_TOKEN" \
  "https://www.ncdc.noaa.gov/cdo-web/api/v2/data?datasetid=GHCND&datatypeid=TMAX&stationid=GHCND:USW00013874&startdate=2024-01-01&enddate=2024-01-31&units=metric&limit=31"
```

**Response:**
```json
{
  "metadata": {
    "resultset": {
      "offset": 1,
      "count": 31,
      "limit": 31
    }
  },
  "results": [
    {
      "date": "2024-01-01T00:00:00",
      "datatype": "TMAX",
      "station": "GHCND:USW00013874",
      "attributes": ",,W,2400",
      "value": 12.2
    },
    {
      "date": "2024-01-02T00:00:00",
      "datatype": "TMAX",
      "station": "GHCND:USW00013874",
      "attributes": ",,W,2400",
      "value": 8.9
    }
  ]
}
```
Note: When `units=standard`, GHCND temperature values are in tenths of degrees C. With `units=metric`, they are converted to degrees C.

### 2. Datasets
```
GET /datasets
GET /datasets/{id}
```
Lists available datasets or gets details for one.

**Example:**
```bash
curl -H "Token: YOUR_TOKEN" \
  "https://www.ncdc.noaa.gov/cdo-web/api/v2/datasets?limit=10"
```

**Key Dataset IDs:**
| ID       | Name | Description |
|----------|------|-------------|
| `GHCND`  | Daily Summaries | Global daily station observations (TMAX, TMIN, PRCP, SNOW, etc.) |
| `GSOM`   | Global Summary of the Month | Monthly aggregates |
| `GSOY`   | Global Summary of the Year | Annual aggregates |
| `NORMAL_DLY` | Climate Normals Daily | 30-year daily normals |
| `NORMAL_MLY` | Climate Normals Monthly | 30-year monthly normals |
| `PRECIP_15`  | Precipitation 15-Minute | Sub-hourly precipitation |
| `PRECIP_HLY` | Precipitation Hourly | Hourly precipitation |

### 3. Data Types
```
GET /datatypes
GET /datatypes/{id}
```
Lists available data types, optionally filtered by dataset.

**Example:**
```bash
curl -H "Token: YOUR_TOKEN" \
  "https://www.ncdc.noaa.gov/cdo-web/api/v2/datatypes?datasetid=GHCND&limit=50"
```

**Common GHCND Data Types:**
| ID     | Description |
|--------|-------------|
| `TMAX` | Maximum temperature |
| `TMIN` | Minimum temperature |
| `TAVG` | Average temperature |
| `PRCP` | Precipitation |
| `SNOW` | Snowfall |
| `SNWD` | Snow depth |
| `AWND` | Average wind speed |
| `WSF2` | Fastest 2-minute wind speed |

### 4. Stations
```
GET /stations
GET /stations/{id}
```
Find weather stations, optionally filtered by location, dataset, or extent.

**Additional Parameters:**
| Parameter  | Type   | Description |
|-----------|--------|-------------|
| `extent`  | string | Bounding box: `south_lat,west_lon,north_lat,east_lon`. |

**Example -- stations near Asheville, NC with daily data:**
```bash
curl -H "Token: YOUR_TOKEN" \
  "https://www.ncdc.noaa.gov/cdo-web/api/v2/stations?datasetid=GHCND&locationid=ZIP:28801&limit=10"
```

**Response:**
```json
{
  "metadata": {"resultset": {"offset": 1, "count": 5, "limit": 10}},
  "results": [
    {
      "elevation": 661.1,
      "mindate": "1893-01-01",
      "maxdate": "2024-11-15",
      "latitude": 35.5951,
      "name": "ASHEVILLE REGIONAL AIRPORT, NC US",
      "datacoverage": 1,
      "id": "GHCND:USW00013874",
      "elevationUnit": "METERS",
      "longitude": -82.5572
    }
  ]
}
```

### 5. Locations & Location Categories
```
GET /locations
GET /locations/{id}
GET /locationcategories
GET /locationcategories/{id}
```
Browse location hierarchies (countries, states, cities, zip codes, climate regions).

**Example:**
```bash
curl -H "Token: YOUR_TOKEN" \
  "https://www.ncdc.noaa.gov/cdo-web/api/v2/locations?locationcategoryid=ST&limit=52"
```

Location category IDs: `CITY`, `CLIM_DIV`, `CLIM_REG`, `CNTRY`, `CNTY`, `HYD_ACC`, `HYD_CAT`, `HYD_REG`, `HYD_SUB`, `ST`, `ZIP`.

---

## Workflow: Finding and Querying Data

1. **Find a dataset:** `GET /datasets` to list available datasets.
2. **Find a station:** `GET /stations?datasetid=GHCND&locationid=ZIP:28801` to find nearby stations.
3. **Check available data types:** `GET /datatypes?datasetid=GHCND&stationid=GHCND:USW00013874`.
4. **Query data:** `GET /data?datasetid=GHCND&stationid=GHCND:USW00013874&datatypeid=TMAX,TMIN&startdate=2024-01-01&enddate=2024-12-31&units=metric&limit=1000`.

## Notes
- The `/data` endpoint enforces a **1-year max date range** per request. For multi-year queries, make sequential requests.
- Pagination: `offset` is 1-based. Loop until `offset + limit > count` from the metadata.
- Station IDs include a dataset prefix (e.g. `GHCND:USW00013874`).
- The `attributes` field in data results contains quality flags (comma-separated). Consult dataset documentation for flag meanings.
- Token goes in the header, not as a query parameter.
