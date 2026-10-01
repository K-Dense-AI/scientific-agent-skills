# Query Parameters — U.S. Treasury Fiscal Data API

All parameters are optional. Combine them with `&` in the URL query string.

## `fields=` — Select Columns

Returns only the specified fields. Accepts a comma-separated list of field names.

```
?fields=record_date,tot_pub_debt_out_amt
?fields=country_currency_desc,exchange_rate,record_date
```

- If omitted, all fields are returned
- Invalid field names cause an error
- Omitting some fields can trigger **automatic aggregation** (see below)

### Aggregation / Auto-Sum

In some endpoints, omitting fields aggregates non-unique rows and sums numeric values. This is not a universal SQL-style grouping guarantee. Keep the dimensions identifying each observation when working with rates, balances, totals or hierarchical statements.

```python
# Demonstrates API aggregation; this is NOT a validated cash-flow total.
# Statement subtotals and overlapping categories must be resolved first.
params = {
    "fields": "record_date,transaction_type,transaction_today_amt"
}
```

## `filter=` — Filter Records

Narrow results by field values. Multiple field filters are **comma-separated in a single `filter=` parameter**.

### Filter Syntax

```
filter=<field>:<operator>:<value>
filter=<field>:<operator>:<value>,<field>:<operator>:<value>
```

### Operators

| Operator | Meaning | Example |
|----------|---------|---------|
| `eq` | Equal to | `filter=record_date:eq:2024-03-31` |
| `lt` | Less than | `filter=exchange_rate:lt:1.5` |
| `lte` | Less than or equal | `filter=record_date:lte:2024-12-31` |
| `gt` | Greater than | `filter=record_fiscal_year:gt:2010` |
| `gte` | Greater than or equal | `filter=record_date:gte:2024-01-01` |
| `in` | Contained in set | `filter=country_currency_desc:in:(Canada-Dollar,Mexico-Peso)` |

### Date Filters

Use `YYYY-MM-DD` format for dates:

```
filter=record_date:gte:2024-01-01
filter=record_date:gte:2023-01-01,record_date:lte:2023-12-31
```

### Multi-Field Filters

```
filter=country_currency_desc:in:(Canada-Dollar,Mexico-Peso),record_date:gte:2024-01-01
```

### Common Filter Fields

Most endpoints have these standard date fields:
- `record_date` — The date of the record (YYYY-MM-DD)
- `record_fiscal_year` — Fiscal year (e.g., `2024`)
- `record_fiscal_quarter` — Fiscal quarter (1-4)
- `record_calendar_year` — Calendar year
- `record_calendar_month` — Calendar month (01-12)

## `sort=` — Sort Results

Sort by one or more fields. Prefix `-` for descending order.

```
?sort=-record_date           # Most recent first
?sort=record_date            # Oldest first
?sort=-record_fiscal_year,-record_fiscal_quarter  # Nested sort
```

**Default:** Sorted by the first column (usually `record_date` ascending).

## `format=` — Output Format

```
?format=json    # Default
?format=csv     # Comma-separated values
?format=xml     # XML
```

When using CSV or XML format, the response is the raw file content rather than JSON.

## `page[size]=` and `page[number]=` — Pagination

Controls how many records per page and which page to return.

```
?page[size]=100&page[number]=1    # Default (100 records, page 1)
?page[size]=10000                  # Large page to reduce requests
?page[number]=5&page[size]=50     # 50 records starting at page 5
```

- Default page size: **100**
- Default page number: **1**
- Use `meta.total-pages` in the response to know how many pages exist
- Use `meta.total-count` for total record count

### Fetch All Records

For small result sets where `meta.total-pages` is 1, a single request with `page[size]=10000` is enough. Use `fetch_all()` below when pagination is required.

```python
import time
import requests
import pandas as pd

def fetch_all(endpoint, params=None, max_pages=50, max_records=500_000):
    """Return all matching rows or raise on a bound or changed result size."""
    if max_pages < 1 or max_records < 1:
        raise ValueError("Bounds must be positive")
    params = dict(params or {})
    allowed = {"fields", "filter", "sort", "format", "page[size]", "page[number]"}
    if set(params) - allowed:
        raise ValueError(f"Unknown query parameters: {set(params) - allowed}")
    if params.get("format", "json") != "json":
        raise ValueError("fetch_all requires JSON")
    size = int(params.get("page[size]", 1000))
    if size < 1:
        raise ValueError("page[size] must be positive")
    params["page[size]"] = min(size, 10000)  # local request-size policy
    params["page[number]"] = 1
    base = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
    rows = []
    expected = None
    for page in range(1, max_pages + 1):
        params["page[number]"] = page
        for attempt in range(3):
            resp = requests.get(base + endpoint, params=params, timeout=30)
            if resp.status_code in (429, 502, 503, 504) and attempt < 2:
                delay = resp.headers.get("Retry-After", "")
                time.sleep(min(float(delay), 60) if delay.isdigit() else 2 ** attempt)
                continue
            resp.raise_for_status()
            break
        result = resp.json()
        if "error" in result:
            raise ValueError(result)
        total = int(result["meta"]["total-count"])
        pages = int(result["meta"]["total-pages"])
        if total > max_records or pages > max_pages:
            raise RuntimeError("Result exceeds bounds; narrow filters or raise limits")
        if expected is not None and total != expected:
            raise RuntimeError("Result count changed during pagination; rerun snapshot")
        expected = total
        rows.extend(result["data"])
        if len(rows) > max_records:
            raise RuntimeError("Result exceeds max_records")
        if page >= pages:
            if len(rows) != expected:
                raise RuntimeError("Incomplete result")
            return pd.DataFrame(rows)
    raise RuntimeError("Reached max_pages before completion")
```

This detects count changes, not every possible revision with unchanged row counts.
Use explicit date bounds and a deterministic sort (including row identifiers when
needed), and retain the raw download for a reproducible snapshot.

## Combining Parameters

```python
params = {
    "fields": "country_currency_desc,exchange_rate,record_date,effective_date",
    "filter": "country_currency_desc:in:(Canada-Dollar,Euro Zone-Euro),record_date:gte:2020-01-01",
    "sort": "-record_date",
    "format": "json",
    "page[size]": 100,
    "page[number]": 1
}
resp = requests.get(
    "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/rates_of_exchange",
    params=params,
    timeout=30,
)
resp.raise_for_status()
```
