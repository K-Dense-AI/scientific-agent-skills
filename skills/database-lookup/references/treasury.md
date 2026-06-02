# US Treasury Fiscal Data API Reference

## Overview
The US Treasury's Fiscal Data API provides machine-readable access to federal financial data: national debt, treasury securities, interest rates, yield curves, revenue, spending, and more. Maintained by the Bureau of the Fiscal Service.

## Base URL
```
https://api.fiscaldata.treasury.gov/services/api/fiscal_service
```

## Authentication
**No API key required.** The API is fully open and public.

## Rate Limits
- **No formal rate limits published.**
- Reasonable use expected; no authentication or throttling documented.
- For bulk data, use pagination with large page sizes.

---

## Key Endpoints

### URL Pattern
All dataset endpoints follow:
```
GET /services/api/fiscal_service/{endpoint}?{parameters}
```

### Common Query Parameters (apply to all endpoints)
| Parameter | Type | Description |
|-----------|------|-------------|
| `fields` | string | Comma-separated list of fields to return |
| `filter` | string | Filter expression: `field:operator:value` (e.g., `record_date:gte:2024-01-01`) |
| `sort` | string | Sort fields: `field` (asc) or `-field` (desc); comma-separated |
| `page[number]` | int | Page number (default 1) |
| `page[size]` | int | Results per page (default 100, max 10000) |
| `format` | string | `json` (default) or `csv` |

**Filter Operators:**
`eq` (equals), `lt`, `lte`, `gt`, `gte`, `in` (comma-separated values)

---

### 1. Treasury Yield Curve Rates (Daily)
```
GET /v2/accounting/od/avg_interest_rates
```

**Better endpoint for yield curves:**
```
GET /v1/accounting/od/rates_of_exchange
```

**Daily Treasury Par Yield Curve Rates:**
Note: Daily yield curve rates are published at `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/` and available via the TreasuryDirect API. For programmatic access via Fiscal Data:

```
GET /v2/accounting/od/avg_interest_rates
```

**Example -- Average interest rates on Treasury securities:**
```
https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/avg_interest_rates?filter=record_date:gte:2024-01-01&sort=-record_date&page[size]=100
```

**Response:**
```json
{
  "data": [
    {
      "record_date": "2024-10-31",
      "security_type_desc": "Treasury Bills",
      "security_desc": "Treasury Bills",
      "avg_interest_rate_amt": "5.223",
      "src_line_nbr": "1",
      "record_fiscal_year": "2025",
      "record_fiscal_quarter": "1",
      "record_calendar_year": "2024",
      "record_calendar_quarter": "4",
      "record_calendar_month": "10",
      "record_calendar_day": "31"
    }
  ],
  "meta": {
    "count": 100,
    "labels": { ... },
    "dataTypes": { ... },
    "dataFormats": { ... },
    "total-count": 1234,
    "total-pages": 13
  },
  "links": {
    "self": "&page%5Bnumber%5D=1&page%5Bsize%5D=100",
    "first": "&page%5Bnumber%5D=1&page%5Bsize%5D=100",
    "prev": null,
    "next": "&page%5Bnumber%5D=2&page%5Bsize%5D=100",
    "last": "&page%5Bnumber%5D=13&page%5Bsize%5D=100"
  }
}
```

---

### 2. Debt to the Penny (Daily National Debt)
```
GET /v2/accounting/od/debt_to_penny
```

**Example -- Debt since 2024:**
```
https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny?filter=record_date:gte:2024-01-01&sort=-record_date&page[size]=10
```

**Key Fields:** `record_date`, `tot_pub_debt_out_amt`, `intragov_hold_amt`, `debt_held_public_amt`

---

### 3. Treasury Securities Auctions
```
GET /v1/accounting/od/auctions_query
```

**Example -- Recent T-Bill auctions:**
```
https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query?filter=security_type:eq:Bill&sort=-auction_date&page[size]=10
```

**Key Fields:** `cusip`, `security_type`, `security_term`, `auction_date`, `issue_date`, `maturity_date`, `high_yield`, `high_discount_rate`, `bid_to_cover_ratio`, `total_accepted`

---

### 4. Monthly Treasury Statement (Revenue & Outlays)
```
GET /v1/accounting/mts/mts_table_5
```

**Example -- Federal receipts/outlays:**
```
https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/mts/mts_table_5?filter=record_date:gte:2024-01-01&sort=-record_date&page[size]=50
```

---

### 5. Federal Spending by Category
```
GET /v1/accounting/mts/mts_table_9
```

**Example:**
```
https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/mts/mts_table_9?filter=record_date:gte:2024-01-01&sort=-record_date
```

---

### 6. Treasury Reporting Rates of Exchange
```
GET /v1/accounting/od/rates_of_exchange
```

**Example -- Exchange rates for a quarter:**
```
https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/rates_of_exchange?filter=record_date:eq:2024-09-30&page[size]=200
```

**Key Fields:** `country_currency_desc`, `exchange_rate`, `record_date`, `effective_date`

---

### 7. Interest Expense on the Debt
```
GET /v2/accounting/od/interest_expense
```

**Example:**
```
https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/interest_expense?filter=record_fiscal_year:eq:2024&sort=-record_date
```

---

### 8. Savings Bonds Rates
```
GET /v2/accounting/od/sb_value
```

---

## Common Endpoint Paths

| Endpoint | Description |
|----------|-------------|
| `v2/accounting/od/debt_to_penny` | Daily total public debt outstanding |
| `v2/accounting/od/avg_interest_rates` | Average interest rates on Treasury securities |
| `v1/accounting/od/auctions_query` | Treasury securities auction results |
| `v1/accounting/od/rates_of_exchange` | Treasury reporting rates of exchange |
| `v2/accounting/od/interest_expense` | Interest expense on the public debt |
| `v1/accounting/mts/mts_table_5` | Monthly Treasury statement: receipts/outlays |
| `v1/accounting/mts/mts_table_9` | Monthly Treasury statement: outlays by function |
| `v2/accounting/od/statement_net_cost` | Statement of net cost |
| `v2/accounting/od/debt_outstanding` | Historical debt outstanding (annual) |

## Response Format
All JSON responses share the same envelope:
- `data`: Array of result objects
- `meta`: Contains `count`, `total-count`, `total-pages`, field labels and data types
- `links`: Pagination links (`self`, `first`, `prev`, `next`, `last`)

## Notes
- All monetary amounts are returned as strings to preserve precision.
- Dates use `YYYY-MM-DD` format in the `record_date` field.
- The `filter` parameter supports chaining: `filter=field1:eq:val1,field2:gte:val2`.
- Use `fields=` to reduce response size by requesting only needed columns.
- The API documentation and dataset explorer is at: https://fiscaldata.treasury.gov/api-documentation/
- For Treasury yield curve rates specifically, FRED series `DGS1`, `DGS2`, `DGS5`, `DGS10`, `DGS30` may be more convenient.
