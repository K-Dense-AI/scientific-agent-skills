# USGS API Reference (Earthquake Hazards + Water Services)

## Part A: Earthquake Hazards Program

### Base URL
```
https://earthquake.usgs.gov/fdsnws/event/1
```

### Authentication
**None required.** Fully public, no API key needed.

### Rate Limits
- No documented per-user rate limit, but USGS asks users to limit automated queries to avoid overloading the service.
- Requests returning very large result sets (>20,000 events) will be rejected. Use pagination or narrow your query.

### Key Endpoints

#### 1. Query Earthquakes
```
GET /query
```
Returns earthquake events matching search criteria. This is the primary endpoint.

**Parameters:**
| Parameter     | Type   | Required | Default    | Description |
|--------------|--------|----------|------------|-------------|
| `format`     | string | No       | `quakeml`  | `geojson`, `csv`, `quakeml`, `text`, `kml`. Use `geojson` for JSON. |
| `starttime`  | string | No       | (now - 30d)| ISO8601 date, e.g. `2024-01-01`. |
| `endtime`    | string | No       | (now)      | ISO8601 date. |
| `minmagnitude`| float | No       | -          | Minimum magnitude (e.g. `4.5`). |
| `maxmagnitude`| float | No       | -          | Maximum magnitude. |
| `mindepth`   | float  | No       | -          | Minimum depth in km. |
| `maxdepth`   | float  | No       | -          | Maximum depth in km. |
| `latitude`   | float  | No       | -          | Center latitude for circle search (-90 to 90). |
| `longitude`  | float  | No       | -          | Center longitude for circle search (-180 to 180). |
| `maxradiuskm`| float  | No       | -          | Max radius in km (with lat/lon). |
| `minlatitude`| float  | No       | -          | Bounding box south edge. |
| `maxlatitude`| float  | No       | -          | Bounding box north edge. |
| `minlongitude`| float | No       | -          | Bounding box west edge. |
| `maxlongitude`| float | No       | -          | Bounding box east edge. |
| `limit`      | int    | No       | -          | Max events returned (max 20000). |
| `offset`     | int    | No       | 1          | Pagination offset (1-based). |
| `orderby`    | string | No       | `time`     | `time`, `time-asc`, `magnitude`, `magnitude-asc`. |
| `alertlevel` | string | No       | -          | PAGER alert: `green`, `yellow`, `orange`, `red`. |
| `eventtype`  | string | No       | -          | e.g. `earthquake`, `quarry blast`. |

**Example -- significant earthquakes in a region:**
```
https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime=2024-01-01&endtime=2024-12-31&minmagnitude=5.0&minlatitude=30&maxlatitude=45&minlongitude=-125&maxlongitude=-110&orderby=magnitude
```

**GeoJSON Response:**
```json
{
  "type": "FeatureCollection",
  "metadata": {
    "generated": 1700000000000,
    "url": "https://earthquake.usgs.gov/fdsnws/event/1/query?...",
    "title": "USGS Earthquakes",
    "status": 200,
    "api": "1.14.1",
    "count": 42
  },
  "features": [
    {
      "type": "Feature",
      "properties": {
        "mag": 6.2,
        "place": "15 km NNE of Ridgecrest, CA",
        "time": 1700000000000,
        "updated": 1700100000000,
        "tz": null,
        "url": "https://earthquake.usgs.gov/earthquakes/eventpage/ci00000001",
        "detail": "https://earthquake.usgs.gov/fdsnws/event/1/query?eventid=ci00000001&format=geojson",
        "felt": 1500,
        "cdi": 7.1,
        "mmi": 6.5,
        "alert": "yellow",
        "status": "reviewed",
        "tsunami": 0,
        "sig": 800,
        "net": "ci",
        "code": "00000001",
        "type": "earthquake",
        "title": "M 6.2 - 15 km NNE of Ridgecrest, CA"
      },
      "geometry": {
        "type": "Point",
        "coordinates": [-117.5, 35.8, 10.5]
      },
      "id": "ci00000001"
    }
  ]
}
```
Note: `geometry.coordinates` is `[longitude, latitude, depth_km]`.

#### 2. Event Detail
```
GET /query?eventid={EVENTID}&format=geojson
```
Returns detailed info for a single event, including moment tensor, focal mechanism, and nearby cities.

#### 3. Event Count
```
GET /count
```
Same parameters as `/query`, returns just the count of matching events. Useful for checking result size before querying.

**Example:**
```
https://earthquake.usgs.gov/fdsnws/event/1/count?starttime=2024-01-01&endtime=2024-12-31&minmagnitude=4.5
```

#### 4. Real-Time Feeds (no parameters)
Pre-built GeoJSON feeds updated every minute/5 min/15 min/hour:
```
https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_month.geojson
https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson
https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson
https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson
```
Pattern: `{significance}_{timeperiod}.geojson` where significance is `significant`, `4.5`, `2.5`, `1.0`, `all` and timeperiod is `hour`, `day`, `week`, `month`.

---

## Part B: Water Services

### Base URL
```
https://waterservices.usgs.gov/nwis
```

### Authentication
**None required.** Fully public, no API key needed.

### Rate Limits
- No strict per-user limit, but USGS recommends limiting automated requests. Large queries may time out.

### Key Endpoints

#### 1. Instantaneous Values (Real-Time Data)
```
GET /iv/
```
Returns the most recent sensor readings (typically 15-minute intervals).

**Parameters:**
| Parameter       | Type   | Required | Default | Description |
|----------------|--------|----------|---------|-------------|
| `format`       | string | No       | `wml`   | `json`, `xml`, `wml,1.1`, `wml,2.0`, `rdb`. Use `json` for JSON. |
| `sites`        | string | Cond.    | -       | Comma-separated USGS site numbers (e.g. `01646500`). |
| `stateCd`      | string | Cond.    | -       | 2-letter state code (e.g. `NY`). |
| `huc`          | string | Cond.    | -       | Hydrologic Unit Code(s). |
| `bBox`         | string | Cond.    | -       | Bounding box: `west,south,east,north` (decimal degrees). |
| `countyCd`     | string | Cond.    | -       | 5-digit FIPS county code(s). |
| `parameterCd`  | string | No       | `00060` | Parameter code(s). `00060`=streamflow, `00065`=gage height, `00010`=water temp. |
| `period`       | string | No       | -       | ISO8601 duration, e.g. `P7D` (past 7 days). |
| `startDT`      | string | No       | -       | Start datetime (ISO8601). |
| `endDT`        | string | No       | -       | End datetime (ISO8601). |
| `siteType`     | string | No       | -       | e.g. `ST` (stream), `GW` (groundwater), `LK` (lake). |
| `siteStatus`   | string | No       | `all`   | `active`, `inactive`, `all`. |

At least one location parameter (`sites`, `stateCd`, `huc`, `bBox`, or `countyCd`) is required.

**Example -- real-time streamflow for a site:**
```
https://waterservices.usgs.gov/nwis/iv/?format=json&sites=01646500&parameterCd=00060&period=P1D
```

**JSON Response (abbreviated):**
```json
{
  "name": "ns1:timeSeriesResponseType",
  "declaredType": "org.cuahsi.waterml.TimeSeriesResponseType",
  "value": {
    "timeSeries": [
      {
        "sourceInfo": {
          "siteName": "Potomac River near Wash, DC Little Falls Pump Sta",
          "siteCode": [{"value": "01646500", "agencyCode": "USGS"}],
          "geoLocation": {
            "geogLocation": {"latitude": 38.94977778, "longitude": -77.12763889}
          }
        },
        "variable": {
          "variableCode": [{"value": "00060"}],
          "variableName": "Streamflow, ft&#179;/s",
          "unit": {"unitCode": "ft3/s"}
        },
        "values": [
          {
            "value": [
              {"value": "5280", "dateTime": "2024-01-15T00:00:00.000-05:00"},
              {"value": "5310", "dateTime": "2024-01-15T00:15:00.000-05:00"}
            ]
          }
        ]
      }
    ]
  }
}
```

#### 2. Daily Values (Historical Aggregates)
```
GET /dv/
```
Returns daily statistical values (mean, max, min). Same location parameters as `/iv/`.

**Additional Parameters:**
| Parameter  | Type   | Description |
|-----------|--------|-------------|
| `statCd`  | string | Statistic code: `00001`=max, `00002`=min, `00003`=mean, `00006`=sum. Default `00003`. |

**Example -- daily mean streamflow, 1 year:**
```
https://waterservices.usgs.gov/nwis/dv/?format=json&sites=01646500&parameterCd=00060&statCd=00003&startDT=2023-01-01&endDT=2023-12-31
```

#### 3. Site Information
```
GET /site/
```
Returns metadata about monitoring sites. Same location parameters apply.

**Example -- active stream sites in Virginia:**
```
https://waterservices.usgs.gov/nwis/site/?format=rdb&stateCd=VA&siteType=ST&siteStatus=active&hasDataTypeCd=iv
```

#### 4. Statistics (Pre-computed)
```
GET /stat/
```
Returns pre-computed statistics (percentiles, mean, median) for daily values, useful for comparing current conditions to historical norms.

**Example:**
```
https://waterservices.usgs.gov/nwis/stat/?format=rdb&sites=01646500&parameterCd=00060&statReportType=daily&statTypeCd=mean,p05,p25,p50,p75,p95
```

### Common Parameter Codes
| Code    | Description |
|---------|-------------|
| `00060` | Discharge/streamflow (ft3/s) |
| `00065` | Gage height (ft) |
| `00010` | Water temperature (C) |
| `00045` | Precipitation (in) |
| `00400` | pH |
| `00300` | Dissolved oxygen (mg/L) |
| `00095` | Specific conductance (uS/cm) |
| `72019` | Groundwater level depth below land surface (ft) |

## Notes
- Earthquake API returns coordinates as `[lon, lat, depth]` (note: longitude first).
- Water Services JSON wraps data in a verbose WaterML-like structure. The `rdb` (tab-delimited) format is simpler for tabular data.
- USGS site numbers are typically 8 digits for surface water, 15 for groundwater.
- Both APIs are free, public, and require no authentication.
