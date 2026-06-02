# Unpaywall API

Unpaywall tells you whether a legal, free copy of a scholarly article exists. Given a DOI, it returns open access status, PDF links, and location details.

## Base URL

```
https://api.unpaywall.org/v2
```

## Authentication

No API key. You must include your **email address** as a query parameter: `?email=you@example.com`

**Important:** Use a real email address. Unpaywall rejects placeholder emails like `test@example.com` with HTTP 422.

## Rate Limits

100,000 calls per day. For heavier use, download the database snapshot.

## Key Endpoints

### 1. DOI Lookup

```
GET /v2/{doi}?email=you@example.com
```

**Example:**
```
https://api.unpaywall.org/v2/10.1038/nature12373?email=you@example.com
```

### 2. Search (unreliable)

```
GET /v2/search?query={text}&email=you@example.com
```

**Warning:** The search endpoint has been returning HTTP 500 errors as of March 2026. It may be deprecated or intermittently broken. Use DOI lookups instead -- find papers via PubMed/OpenAlex/Semantic Scholar first, then check OA status per-DOI.

| Parameter | Description |
|-----------|-------------|
| `query` | Search text. Supports quoted phrases, `OR`, `-` negation |
| `is_oa` | `true` or `false` -- filter by OA status |
| `page` | Page number (1-indexed), 50 results per page |

## Response Format

### DOI Lookup response
```json
{
  "doi": "10.1038/nature12373",
  "doi_url": "https://doi.org/10.1038/nature12373",
  "title": "Nanometre-scale thermometry in a living cell",
  "year": 2013,
  "published_date": "2013-07-31",
  "genre": "journal-article",
  "publisher": "Springer Nature",
  "is_oa": true,
  "oa_status": "green",
  "best_oa_location": {
    "url": "https://dash.harvard.edu/bitstream/1/...",
    "url_for_pdf": "https://dash.harvard.edu/bitstream/1/...pdf",
    "url_for_landing_page": "https://dash.harvard.edu/handle/...",
    "host_type": "repository",
    "version": "acceptedVersion",
    "license": "cc-by",
    "is_best": true,
    "oa_date": "2016-01-01"
  },
  "first_oa_location": {...},
  "oa_locations": [...],
  "has_repository_copy": true,
  "journal_name": "Nature",
  "journal_issns": "0028-0836,1476-4687",
  "journal_issn_l": "0028-0836",
  "journal_is_oa": false,
  "journal_is_in_doaj": false,
  "z_authors": [
    {"raw_author_name": "G. Kucsko", "author_position": "first"},
    {"raw_author_name": "P. C. Maurer", "author_position": "middle"}
  ]
}
```

### OA Status values
| Status | Meaning |
|--------|---------|
| `gold` | Published in a fully OA journal |
| `hybrid` | OA in a subscription journal (publisher-hosted) |
| `bronze` | Free to read on publisher site but no OA license |
| `green` | Available via a repository (e.g., institutional, preprint) |
| `closed` | No free legal copy found |

### OA Location fields
| Field | Description |
|-------|-------------|
| `url` | Best URL (PDF if available, else landing page) |
| `url_for_pdf` | Direct PDF URL (null if no PDF) |
| `url_for_landing_page` | Landing page URL |
| `host_type` | `publisher` or `repository` |
| `version` | `submittedVersion`, `acceptedVersion`, `publishedVersion` |
| `license` | e.g., `cc-by`, `cc-by-nc`, `implied-oa`, or null |
| `is_best` | Whether this is the `best_oa_location` |
| `oa_date` | When first available at this location |

### Search response
```json
{
  "results": [
    {
      "response": {...},
      "score": 42.5,
      "snippet": "...text with <b>highlighted</b> matches..."
    }
  ]
}
```

## Typical Workflow

1. You have a DOI from PubMed, Crossref, or another source
2. Call Unpaywall with the DOI
3. Check `is_oa` -- if true, use `best_oa_location.url_for_pdf` for the free PDF
4. Check `oa_status` to understand what kind of OA it is
5. If closed, `oa_locations` will be empty -- the article requires a subscription
