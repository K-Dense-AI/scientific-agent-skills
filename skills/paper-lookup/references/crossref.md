# Crossref API

Crossref is the DOI registration agency for scholarly content. It provides metadata for 150M+ works including journal articles, books, conference papers, datasets, and preprints.

## Base URL

```
https://api.crossref.org
```

## Authentication

None required. Add `mailto=you@example.com` to get into the **polite pool** (2x faster rate limits).

## Rate Limits

| Pool | Rate | Concurrency |
|------|------|-------------|
| Public (no mailto) | 5 req/sec | 1 concurrent |
| Polite (with mailto) | 10 req/sec | 3 concurrent |

HTTP 429 = temporarily blocked.

## Key Endpoints

### 1. Search works

```
GET /works?query={text}&rows={n}&mailto=you@example.com
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `query` | -- | Free-text search across all fields |
| `query.author` | -- | Search author names |
| `query.bibliographic` | -- | Search titles, authors, ISSNs, years |
| `query.affiliation` | -- | Search affiliations |
| `query.container-title` | -- | Search journal names |
| `filter` | -- | Comma-separated `name:value` pairs |
| `sort` | `score` | `score`, `published`, `issued`, `deposited`, `updated`, `is-referenced-by-count`, `references-count` |
| `order` | `desc` | `asc` or `desc` |
| `rows` | 20 | Results per page (max 1000) |
| `offset` | 0 | Skip N results (max 10,000) |
| `cursor` | -- | Use `*` for cursor-based deep pagination |
| `select` | -- | Comma-separated field names to return |
| `facet` | -- | Facet counts, e.g. `type-name:10` |
| `sample` | -- | Return N random items (max 100) |

**Example:**
```
https://api.crossref.org/works?query=CRISPR+gene+therapy&filter=from-pub-date:2024-01-01,type:journal-article,has-abstract:true&rows=5&sort=published&order=desc&mailto=you@example.com
```

### 2. Get work by DOI

```
GET /works/{doi}?mailto=you@example.com
```

URL-encode the DOI: `10.1038/nature12373` becomes `10.1038%2Fnature12373`

**Example:**
```
https://api.crossref.org/works/10.1038%2Fnature12373?mailto=you@example.com
```

### 3. Journals

```
GET /journals?query={name}&rows={n}
GET /journals/{issn}
GET /journals/{issn}/works?query={text}&rows={n}
```

### 4. Funders

```
GET /funders?query={name}
GET /funders/{id}
GET /funders/{id}/works?rows={n}
```

Funder IDs are from the Funder Registry (e.g., `100000001` for NSF).

### 5. Members (publishers)

```
GET /members?query={name}
GET /members/{id}/works?rows={n}
```

## Key Filters

### Date filters (accept `YYYY`, `YYYY-MM`, `YYYY-MM-DD`)
| Filter | Description |
|--------|-------------|
| `from-pub-date` / `until-pub-date` | Publication date |
| `from-print-pub-date` / `until-print-pub-date` | Print publication date |
| `from-online-pub-date` / `until-online-pub-date` | Online publication date |
| `from-posted-date` / `until-posted-date` | Posted date (preprints) |

### Boolean filters
| Filter | Description |
|--------|-------------|
| `has-abstract` | Has an abstract |
| `has-orcid` | Has ORCID IDs |
| `has-funder` | Has funder info |
| `has-full-text` | Has full-text links |
| `has-references` | Has reference list |
| `has-license` | Has license info |

### Value filters
| Filter | Description |
|--------|-------------|
| `type` | `journal-article`, `posted-content`, `book-chapter`, `proceedings-article`, etc. |
| `issn` | Journal ISSN |
| `doi` | Specific DOI |
| `orcid` | Contributor ORCID |
| `funder` | Funder Registry ID |
| `member` | Crossref member ID |
| `prefix` | DOI prefix |
| `license.url` | License URL |
| `update-type` | `correction`, `retraction` |

**Syntax:** `filter=name1:value1,name2:value2`

## Pagination

### Offset-based (max 10,000)
```
/works?query=cancer&rows=100&offset=200
```

### Cursor-based (unlimited)
1. First request: `?cursor=*&rows=100`
2. Response includes `next-cursor`
3. Next request: `?cursor={next-cursor-value}&rows=100`
4. Cursors expire after 5 minutes

## Response Format

### List response
```json
{
  "status": "ok",
  "message-type": "work-list",
  "message": {
    "total-results": 2779116,
    "items-per-page": 20,
    "next-cursor": "...",
    "items": [...]
  }
}
```

### Work object (key fields)
```json
{
  "DOI": "10.1038/nature12373",
  "title": ["Nanometre-scale thermometry in a living cell"],
  "author": [{"given": "G.", "family": "Kucsko", "sequence": "first"}],
  "publisher": "Springer Science and Business Media LLC",
  "type": "journal-article",
  "published": {"date-parts": [[2013, 7, 31]]},
  "container-title": ["Nature"],
  "ISSN": ["0028-0836", "1476-4687"],
  "volume": "500",
  "issue": "7460",
  "page": "54-58",
  "is-referenced-by-count": 1745,
  "references-count": 30,
  "abstract": "<p>Abstract text with HTML tags...</p>",
  "license": [{"URL": "...", "content-version": "vor"}],
  "link": [{"URL": "...", "content-type": "application/pdf"}],
  "reference": [{"key": "...", "doi-asserted-by": "crossref", "DOI": "..."}],
  "subject": ["Multidisciplinary"],
  "language": "en"
}
```

Note: `title` and `container-title` are arrays. `published.date-parts` is `[[year, month, day]]`. Abstract may contain HTML tags.
