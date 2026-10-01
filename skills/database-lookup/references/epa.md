# EPA Envirofacts Data Service

Current public base: `https://data.epa.gov/dmapservice`.
[Official query contract](https://www.epa.gov/enviro/web-services).
No key is required for this service; AQS below is separate.

Tables are qualified as `program.table`. Discover table/column names through the
EPA data model, rather than guessing names from a program abbreviation.

```text
GET https://data.epa.gov/dmapservice/tri.tri_facility/state_abbr/equals/VA/1:10/JSON
```

Filters use `/column/operator/value`; available operators include `equals`,
`notEquals`, `lessThan`, `greaterThan`, `beginsWith`, `contains`, `in`, and `notIn`.
Combine filters with `/and/` or `/or/`; encode values in path segments.
Rows are one-based and inclusive (`1:10`, then `11:20`). Sort with
`/sort/column:asc` or `:desc` for repeatable paging. JSON is the default;
CSV, XML and other formats are available.

The API supports server-side joins. For example, qualifying two tables and
joining on their documented common identifier avoids mismatching similarly named
facilities. Use explicit join keys when needed and verify row cardinality.

The older `/efservice/.../rows/0:9` grammar is not the current documented contract.
Keep program, reporting year, units and method with environmental observations;
facility records alone do not measure exposure or individual health risk.

## AQS Data API (Separate System)

For more granular air quality data, EPA also provides the AQS Data API at:
```
https://aqs.epa.gov/data/api
```

- **Requires:** Free account at https://aqs.epa.gov/data/api/signup?email=YOUR_EMAIL
- **Auth:** Pass `email` and `key` as query parameters.
- Key endpoints: `/dailyData/byState`, `/annualData/byState`, `/sampleData/bySite`, `/monitors/byState`.

**Example:**
```
https://aqs.epa.gov/data/api/dailyData/byState?email=YOUR_EMAIL&key=YOUR_KEY&param=44201&bdate=20240101&edate=20240131&state=06
```
