# USPTO Public APIs

## 1. PatentsView API (Primary Patent Search)

The newer Elasticsearch-based API is the recommended endpoint.

### Base URL

```
https://search.patentsview.org/api/v1/
```

**API key required** — register at `https://patentsview.org/apis/keyrequest`

Pass as query parameter: `?api_key=YOUR_KEY`

### Key Endpoints

#### Search patents
```
GET or POST /patent/
```

Query parameter `q` accepts a JSON query object.

Operators: `_eq`, `_neq`, `_gt`, `_gte`, `_lt`, `_lte`, `_begins`, `_contains`, `_text_any`, `_text_all`, `_text_phrase`, `_and`, `_or`, `_not`

Parameters:
- `q` — JSON query
- `f` — fields to return (JSON array)
- `o` — options: `{"size": 25}` for pagination
- `s` — sort: `[{"patent_date": "desc"}]`

#### Search by keyword
```
GET /patent/?q={"_text_any":{"patent_abstract":"autonomous vehicle"}}&f=["patent_id","patent_title","patent_date"]&o={"size":5}&api_key=KEY
```

#### Search by inventor
```
GET /patent/?q={"inventors.inventor_name_last":"Tesla"}&f=["patent_id","patent_title","patent_date"]&api_key=KEY
```

#### Search by assignee
```
GET /patent/?q={"assignees.assignee_organization":"Google LLC"}&f=["patent_id","patent_title","patent_date","assignees"]&api_key=KEY
```

#### Lookup by patent number
```
GET /patent/{patent_number}/?api_key=KEY
```

#### Other entity endpoints
```
/inventor/
/assignee/
/cpc_group/
```

### Response Structure

```json
{
  "patents": [
    {
      "patent_id": "11234567",
      "patent_title": "...",
      "patent_date": "2022-03-15",
      "patent_abstract": "...",
      "assignees": [{"assignee_organization": "..."}],
      "inventors": [{"inventor_name_first": "...", "inventor_name_last": "..."}]
    }
  ],
  "count": 1,
  "total_hits": 8923
}
```

### Rate Limits

~45 requests per minute per API key.

### Important Note

The user must have a PatentsView API key for this endpoint. If they don't have one, let them know they need to register at `https://patentsview.org/apis/keyrequest`. Load the key from `.env` as `PATENTSVIEW_API_KEY`.

**Note:** The legacy API at `api.patentsview.org` has been decommissioned (returns 410 Gone). Only the new API above works.

## 3. PEDS — Patent Examination Data System

**URL**: `https://ped.uspto.gov/api/queries`

**Method**: POST

For patent prosecution data (application status, filing dates, examiner info).

```json
{
  "searchText": "applicationNumberText:16123456",
  "fl": "*",
  "mm": "100%",
  "df": "patentTitle",
  "facet": "false",
  "sort": "applId asc",
  "start": 0
}
```

No API key required but heavily rate limited. Availability can be unreliable.

## 4. TSDR — Trademark Status & Document Retrieval

For trademark lookup by serial or registration number (not full-text search).

```
GET https://tsdr.uspto.gov/documentxml/status/{serial_number}
GET https://tsdr.uspto.gov/documentxml/status/rn{registration_number}
```

Returns XML with mark details, status, owner, goods/services, prosecution history.

No API key. Rate limited. No JSON endpoint — responses are XML.

## 5. Limitations

- **No public REST API for trademark full-text search** (TESS is web-only)
- PatentsView new API requires registration for an API key
- PEDS availability is inconsistent
- TSDR requires knowing the serial/registration number already
