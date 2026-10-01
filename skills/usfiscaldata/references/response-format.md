# Response Format — U.S. Treasury Fiscal Data API

## Response Structure (JSON)

Illustrative shape, not an observed debt value or a complete 100-row page.

```json
{
  "data": [
    {
      "record_date": "2024-03-31",
      "tot_pub_debt_out_amt": "34589629941.12"
    }
  ],
  "meta": {
    "count": 100,
    "labels": {
      "record_date": "Record Date",
      "tot_pub_debt_out_amt": "Total Public Debt Outstanding"
    },
    "dataTypes": {
      "record_date": "DATE",
      "tot_pub_debt_out_amt": "CURRENCY"
    },
    "dataFormats": {
      "record_date": "YYYY-MM-DD",
      "tot_pub_debt_out_amt": "10.2"
    },
    "total-count": 3790,
    "total-pages": 38
  },
  "links": {
    "self": "&page%5Bnumber%5D=1&page%5Bsize%5D=100",
    "first": "&page%5Bnumber%5D=1&page%5Bsize%5D=100",
    "prev": null,
    "next": "&page%5Bnumber%5D=2&page%5Bsize%5D=100",
    "last": "&page%5Bnumber%5D=38&page%5Bsize%5D=100"
  }
}
```

## `meta` Object

| Field | Description |
|-------|-------------|
| `count` | Number of records in this response page |
| `total-count` | Total records matching the query (all pages) |
| `total-pages` | Total pages available at current page size |
| `labels` | Human-readable column labels |
| `dataTypes` | Logical types include `STRING`, `NUMBER`, `DATE`, `INTEGER`, `PERCENTAGE`, `CURRENCY` and precision variants such as `CURRENCY0`; calendar parts also use `YEAR`, `QUARTER`, `MONTH`, `DAY` |
| `dataFormats` | Format hints: `YYYY-MM-DD`, `10.2`, `$10.20`, `String` |

## `links` Object

Use the `links` object to navigate pagination programmatically:

| Field | Value |
|-------|-------|
| `self` | Current page query params |
| `first` | First page |
| `prev` | Previous page (null if on first page) |
| `next` | Next page (null if on last page) |
| `last` | Last page |

The HTTP response also includes a **`Link` header** with RFC 5988 relations (`rel="first"`, `rel="prev"`, `rel="next"`, `rel="last"`). JSON link values can be `&page...` fragments. Preserve all original filters, fields and sort when updating pagination; a fragment alone is not a complete URL.

## `data` Object

Array of row objects. All values are **strings**, regardless of logical type.

## Response Codes

| Code | Meaning |
|------|---------|
| 200 | OK — successful GET |
| 400 | Bad Request — malformed URL or invalid parameter |
| 403 | Access denied; public API requests do not require keys |
| 404 | Not Found — endpoint does not exist |
| 429 | Too Many Requests — rate limited |
| 500 | Internal Server Error |

## Error Object

An invalid field produced HTTP 400 with this JSON error in the live review:

```json
{
  "error": "Invalid Query Param",
  "message": "Invalid query parameter: Field 'not_a_column' does not exist. For more information, please see the documentation."
}
```

Unknown parameter names can be silently ignored: live `sorts=-record_date` returned
HTTP 200 with the default ascending order, despite the official guide using that
typo in its error example. Validate parameter names locally and check returned
ordering/filters. The helpers in this skill reject unknown parameter names.

Treat errors as errors even if a proxy sends HTML instead of JSON. Check status
before parsing a successful response; on failure, inspect a bounded response body
and any JSON `error`/`message` fields. Do not turn an error into an empty DataFrame.

## Common Error Causes

- Invalid field name in `fields=` parameter
- Invalid filter operator (use `eq`, `gte`, `lte`, `gt`, `lt`, `in`)
- Wrong date format (must be `YYYY-MM-DD`)
- Accessing a v2 endpoint with `/v1/` in the URL
- `sort` field not available in the endpoint

## Parsing Responses

```python
import requests
import pandas as pd

def api_to_dataframe(endpoint, params=None):
    """Fetch ONE PAGE and return a DataFrame plus pagination metadata."""
    base = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
    resp = requests.get(f"{base}{endpoint}", params=params, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    
    df = pd.DataFrame(result["data"])
    meta = result["meta"]
    
    # Apply type conversions using metadata
    for col, dtype in meta["dataTypes"].items():
        if col not in df.columns:
            continue
        if dtype in ("NUMBER", "PERCENTAGE") or dtype.startswith("CURRENCY"):
            df[col] = pd.to_numeric(df[col].replace("null", None), errors="coerce")
        elif dtype == "DATE":
            df[col] = pd.to_datetime(df[col].replace("null", None), errors="coerce")
        elif dtype == "INTEGER":
            df[col] = pd.to_numeric(df[col].replace("null", None), errors="coerce").astype("Int64")
    
    return df, meta

# Usage
df, meta = api_to_dataframe(
    "/v2/accounting/od/debt_to_penny",
    params={"sort": "-record_date", "page[size]": 30}
)
print(f"Total records available: {meta['total-count']}")
print(df[["record_date", "tot_pub_debt_out_amt"]].head())
```

Numeric pandas conversion can lose cent precision for large debt amounts. Keep raw
strings and use `decimal.Decimal` for accounting reconciliation. Calendar-part
types may be retained as strings to preserve zero padding. Units must come from
the field dictionary; a `CURRENCY` label alone does not distinguish USD from
millions of USD.

## CSV Format Response

When `format=csv` is specified, the response body is plain CSV text (not JSON):

```python
import io

resp = requests.get(
    "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny",
    params={"format": "csv", "sort": "-record_date", "page[size]": 100},
    timeout=30,
)
resp.raise_for_status()
df = pd.read_csv(io.StringIO(resp.text))
```

## XML Format Response

When `format=xml` is specified, the response body is XML:

```python
import xml.etree.ElementTree as ET

resp = requests.get(
    "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny",
    params={"format": "xml", "page[size]": 10},
    timeout=30,
)
resp.raise_for_status()
root = ET.fromstring(resp.text)
```
