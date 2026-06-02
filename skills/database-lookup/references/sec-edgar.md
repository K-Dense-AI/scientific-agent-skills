# SEC EDGAR API Reference

## Overview
SEC's Electronic Data Gathering, Analysis, and Retrieval system. Provides free access to corporate filings, company data, and XBRL financial data. No API key required, but a User-Agent header identifying you is mandatory.

## Base URLs
- **EFTS (Full-Text Search):** `https://efts.sec.gov/LATEST`
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
- SEC asks users to make requests outside market hours (9:00 PM - 6:00 AM ET) when possible for bulk downloads.

---

## Key Endpoints

### 1. Full-Text Search (EFTS)

#### `GET https://efts.sec.gov/LATEST/search-index`
Search across the full text of all EDGAR filings.

**Parameters:**
| Parameter    | Type   | Required | Description |
|-------------|--------|----------|-------------|
| `q`         | string | Yes      | Search query text. Supports boolean operators (`AND`, `OR`, `NOT`), exact phrases in quotes. |
| `dateRange` | string | No       | `custom` to enable date filtering. |
| `startdt`   | string | No       | Start date `YYYY-MM-DD`. |
| `enddt`     | string | No       | End date `YYYY-MM-DD`. |
| `forms`     | string | No       | Comma-separated form types, e.g. `10-K,10-Q,8-K`. |
| `from`      | int    | No       | Pagination offset (default 0). |
| `size`      | int    | No       | Results per page (default 10, max varies). |

**Example:**
```
https://efts.sec.gov/LATEST/search-index?q=%22artificial+intelligence%22&forms=10-K&startdt=2024-01-01&enddt=2024-12-31
```

**Response:**
```json
{
  "hits": {
    "hits": [
      {
        "_id": "0001234567-24-000123:filing.htm",
        "_source": {
          "file_date": "2024-03-15",
          "display_date_filed": "2024-03-15",
          "entity_name": "EXAMPLE CORP",
          "file_num": "001-12345",
          "form_type": "10-K",
          "file_description": "Annual report",
          "period_of_report": "2023-12-31"
        }
      }
    ],
    "total": { "value": 150 }
  }
}
```

### 2. EDGAR Full-Text Search (Preferred newer endpoint)

#### `GET https://efts.sec.gov/LATEST/search-index` (also accessible as below)

#### `GET https://efts.sec.gov/LATEST/search-index?q=...`

Note: The EDGAR full-text search has also been exposed under a simpler URL:

#### `GET https://efts.sec.gov/LATEST/search-index`

The above is the canonical endpoint. Some documentation also references the EDGAR search UI which hits the same backend.

---

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

The `filings.recent` object contains the most recent ~1000 filings. Older filings are in separate paginated files referenced by `filings.files`.

---

### 5. Company Concept (XBRL Data)

#### `GET https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/{taxonomy}/{tag}.json`
Returns all values reported by a company for a specific XBRL tag across all filings.

**Path Parameters:**
| Parameter   | Description |
|------------|-------------|
| `cik`      | Zero-padded CIK (10 digits). |
| `taxonomy` | XBRL taxonomy: `us-gaap`, `ifrs-full`, `dei`, `srt`. |
| `tag`      | XBRL concept tag, e.g., `Revenue`, `Assets`, `AccountsPayableCurrent`. |

**Example:**
```
https://data.sec.gov/api/xbrl/companyconcept/CIK0000320193/us-gaap/Revenue.json
```

**Response:**
```json
{
  "cik": 320193,
  "taxonomy": "us-gaap",
  "tag": "Revenue",
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
Returns ALL XBRL concepts reported by a company across all filings.

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
      "Revenue": { "units": { "USD": [...] } },
      "Assets": { "units": { "USD": [...] } }
    }
  }
}
```

---

### 7. Frames (Cross-Company XBRL for a period)

#### `GET https://data.sec.gov/api/xbrl/frames/{taxonomy}/{tag}/{unit}/{period}.json`
Returns a specific XBRL concept value for ALL companies for a given reporting period.

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
| `Revenue` / `Revenues` | Total revenue |
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
- The EFTS full-text search indexes the text content of filings, not XBRL data.
- For bulk downloads, SEC provides index files at `https://www.sec.gov/Archives/edgar/full-index/`.
- All responses are JSON unless otherwise noted. Filing documents can be HTML, XML, or plain text.
