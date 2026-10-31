# SEC EDGAR API Reference

## Overview
SEC's Electronic Data Gathering, Analysis, and Retrieval system. Provides free access to corporate filings, company data, and XBRL financial data. No API key required, but a User-Agent header identifying you is mandatory.

## Base URLs
- **Company/Filings Data:** `https://data.sec.gov`
- **EDGAR Website/Archives:** `https://www.sec.gov`
- **XBRL API:** `https://data.sec.gov/api/xbrl`

## Authentication
- **API Key:** Not required.
- **User-Agent Header:** REQUIRED on every request. Must contain company/person name and email.
  ```
  User-Agent: MyCompany admin@mycompany.com
  ```
  Requests without a proper User-Agent are blocked (403).

## Rate Limits
- **10 requests per second** per source IP.
- Exceeding this results in temporary IP-based throttling (HTTP 429).
- Use the official bulk ZIP archives for large jobs instead of querying every company separately.

---

## Key Endpoints

### Full-text discovery

Use [EDGAR full-text search](https://www.sec.gov/edgar/search/) for interactive discovery. Its `efts.sec.gov` backend is not one of the documented `data.sec.gov` public APIs; do not treat inferred UI routes, filters, or response fields as a stable retrieval contract. Use the documented submissions and XBRL routes below for reproducible API retrieval.

### 3. Company Tickers & CIK Lookup

#### `GET https://www.sec.gov/cgi-bin/browse-edgar`
Legacy EDGAR company search.

**Parameters:**
| Parameter  | Type   | Required | Description |
|-----------|--------|----------|-------------|
| `company` | string | No       | Company name search. |
| `CIK`     | string | No       | CIK number or ticker symbol. |
| `type`    | string | No       | Filing type filter (e.g., `10-K`). |
| `dateb`   | string | No       | Filed before date `YYYY-MM-DD`. |
| `owner`   | string | No       | `include`, `exclude`, or `only`. |
| `count`   | int    | No       | Number of results (max 100). |
| `action`  | string | Yes      | `getcompany` for company search. |
| `output`  | string | No       | `atom` for XML/Atom feed. |

**Example:**
```
https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=AAPL&type=10-K&dateb=&owner=include&count=10&output=atom
```

#### `GET https://www.sec.gov/files/company_tickers.json`
Returns a JSON mapping of all company tickers to CIK numbers.

**Response:**
```json
{
  "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
  "1": {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"},
  ...
}
```

#### `GET https://www.sec.gov/files/company_tickers_exchange.json`
Includes exchange information for each ticker.

---

### 4. Company Filings & Submissions

#### `GET https://data.sec.gov/submissions/CIK{cik_padded}.json`
Returns company metadata and recent filings for a given CIK (zero-padded to 10 digits).

**Example:**
```
https://data.sec.gov/submissions/CIK0000320193.json
```

**Response:**
```json
{
  "cik": "320193",
  "entityType": "operating",
  "sic": "3571",
  "sicDescription": "Electronic Computers",
  "name": "Apple Inc.",
  "tickers": ["AAPL"],
  "exchanges": ["Nasdaq"],
  "filings": {
    "recent": {
      "accessionNumber": ["0000320193-24-000123", ...],
      "filingDate": ["2024-11-01", ...],
      "reportDate": ["2024-09-28", ...],
      "form": ["10-K", ...],
      "primaryDocument": ["aapl-20240928.htm", ...],
      "primaryDocDescription": ["10-K", ...]
    },
    "files": [
      {"name": "CIK0000320193-submissions-001.json", "filingCount": 1000}
    ]
  }
}
```

`filings.recent` contains at least one year or 1,000 filings, whichever is larger. Retrieve older filenames from `filings.files` under the same `/submissions/` base; keep the parallel arrays aligned by index.

---

### 5. Company Concept (XBRL Data)

#### `GET https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/{taxonomy}/{tag}.json`
Returns all values reported by a company for a specific XBRL tag across all filings.

**Path Parameters:**
| Parameter   | Description |
|------------|-------------|
| `cik`      | Zero-padded CIK (10 digits). |
| `taxonomy` | XBRL taxonomy: `us-gaap`, `ifrs-full`, `dei`, `srt`. |
| `tag`      | XBRL concept tag, e.g., `RevenueFromContractWithCustomerExcludingAssessedTax`, `Assets`, `AccountsPayableCurrent`. |

**Example:**
```
https://data.sec.gov/api/xbrl/companyconcept/CIK0000320193/us-gaap/RevenueFromContractWithCustomerExcludingAssessedTax.json
```

**Response:**
```json
{
  "cik": 320193,
  "taxonomy": "us-gaap",
  "tag": "RevenueFromContractWithCustomerExcludingAssessedTax",
  "label": "Revenue",
  "description": "Amount of revenue recognized...",
  "entityName": "Apple Inc.",
  "units": {
    "USD": [
      {
        "start": "2023-10-01",
        "end": "2024-09-28",
        "val": 391035000000,
        "accn": "0000320193-24-000123",
        "fy": 2024,
        "fp": "FY",
        "form": "10-K",
        "filed": "2024-11-01"
      }
    ]
  }
}
```

---

### 6. Company Facts (All XBRL for one company)

#### `GET https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json`
Returns aggregated company concepts from non-custom taxonomies applying to the entire entity. Custom tags and dimensional/segment facts require inspecting the filing itself.

**Example:**
```
https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json
```

**Response:** Same structure as companyconcept but with all tags nested under `facts.us-gaap`, `facts.dei`, etc.

```json
{
  "cik": 320193,
  "entityName": "Apple Inc.",
  "facts": {
    "dei": {
      "EntityCommonStockSharesOutstanding": { "units": { "shares": [...] } }
    },
    "us-gaap": {
      "RevenueFromContractWithCustomerExcludingAssessedTax": { "units": { "USD": [...] } },
      "Assets": { "units": { "USD": [...] } }
    }
  }
}
```

---

### 7. Frames (Cross-Company XBRL for a period)

#### `GET https://data.sec.gov/api/xbrl/frames/{taxonomy}/{tag}/{unit}/{period}.json`
Returns the last-filed fact per reporting entity that best matches the requested calendar period. Reporting start/end dates can differ between entities; inspect them before comparing values.

**Path Parameters:**
| Parameter   | Description |
|------------|-------------|
| `taxonomy` | `us-gaap`, `ifrs-full`, `dei`, `srt`. |
| `tag`      | XBRL tag, e.g., `Assets`. |
| `unit`     | `USD`, `shares`, `pure`, etc. |
| `period`   | Instant: `CY2023Q4I`; Duration: `CY2023`, `CY2023Q1`. |

**Period format:**
- `CY2023` = calendar year 2023 (full year duration)
- `CY2023Q1` = Q1 2023 duration
- `CY2023Q4I` = instant at end of Q4 2023 (balance sheet items)

**Example:**
```
https://data.sec.gov/api/xbrl/frames/us-gaap/Assets/USD/CY2023Q4I.json
```

**Response:**
```json
{
  "taxonomy": "us-gaap",
  "tag": "Assets",
  "ccp": "CY2023Q4I",
  "uom": "USD",
  "label": "Assets",
  "description": "Sum of the carrying amounts...",
  "pts": 8500,
  "data": [
    {"accn": "0000320193-24-000123", "cik": 320193, "entityName": "Apple Inc.", "loc": "US-CA", "end": "2023-12-30", "val": 352583000000}
  ]
}
```

---

### 8. Filing Archives (Direct Document Access)

#### `GET https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number_no_dashes}/{filename}`
Direct access to any filing document.

**Example:**
```
https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.htm
```

The accession number format in the URL is stripped of dashes: `0000320193-24-000123` becomes `000032019324000123`.

---

## Common XBRL Tags Reference
| Tag | Description |
|-----|-------------|
| `RevenueFromContractWithCustomerExcludingAssessedTax` / `Revenues` | Revenue concepts; choose from the company's actual facts |
| `NetIncomeLoss` | Net income |
| `Assets` | Total assets |
| `Liabilities` | Total liabilities |
| `StockholdersEquity` | Total equity |
| `EarningsPerShareBasic` | Basic EPS |
| `EarningsPerShareDiluted` | Diluted EPS |
| `OperatingIncomeLoss` | Operating income |
| `CashAndCashEquivalentsAtCarryingValue` | Cash and equivalents |
| `LongTermDebt` | Long-term debt |
| `CommonStockSharesOutstanding` | Shares outstanding |

## Notes
- CIK numbers must be zero-padded to 10 digits in `data.sec.gov` URLs.
- Response excerpts and accession numbers here illustrate structure; obtain actual document names and accession numbers from submissions before constructing archive URLs.
- For bulk downloads, SEC provides index files at `https://www.sec.gov/Archives/edgar/full-index/`.
- All responses are JSON unless otherwise noted. Filing documents can be HTML, XML, or plain text.
