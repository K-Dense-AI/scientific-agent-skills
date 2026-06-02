# CORE API

CORE aggregates open access research from 15,000+ repositories worldwide. It provides **full text** for 37M+ articles and metadata for 368M+ papers.

## Base URL

```
https://api.core.ac.uk/v3
```

**Important:** GET search paths require a **trailing slash** (e.g., `/v3/search/works/` not `/v3/search/works`).

## Authentication

- **Header:** `Authorization: Bearer YOUR_API_KEY`
- **Query param:** `?api_key=YOUR_API_KEY`
- Register at: https://core.ac.uk/services/api

**Without auth:** Basic metadata queries work, but full text is NOT available (returns "Not available for public API users").

## Rate Limits (token-based)

| User Type | Daily Tokens | Per-Minute Max |
|-----------|-------------|----------------|
| Unauthenticated | 100/day | 10/min |
| Registered Personal | 1,000/day | 25/min |
| Registered Academic | 5,000/day | 10/min |

Simple queries cost 1 token. Downloads and scroll pagination cost 3-5 tokens.

## Key Endpoints

### 1. Search works

```
GET /v3/search/works/?q={query}&limit={n}&offset={n}
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `q` | required | Search query (supports field lookups, boolean operators) |
| `limit` | 10 | Results per page (max 100) |
| `offset` | 0 | Pagination offset |
| `scroll` | false | Enable scroll pagination for >10,000 results |
| `sort` | relevance | `relevance` or `recency` |

**POST alternative** (for complex queries):
```
POST /v3/search/works
Content-Type: application/json

{"q": "machine learning", "limit": 10, "offset": 0}
```

**Example:**
```
https://api.core.ac.uk/v3/search/works/?q=CRISPR+gene+therapy&limit=10
```

### 2. Query language

| Operator | Example | Description |
|----------|---------|-------------|
| AND | `title:"AI" AND authors:"Smith"` | Both conditions |
| OR | `title:"AI" OR fullText:"Deep Learning"` | Either condition |
| Grouping | `(title:"AI" OR title:"ML") AND yearPublished>"2020"` | Precedence |
| Field lookup | `title:"Machine Learning"` | Search specific field |
| Range | `yearPublished>2018` | Numeric comparison |
| Exists | `_exists_:fullText` | Field must exist |
| Phrase | `title:"Attention is all you need"` | Exact phrase |

**Searchable fields:** `abstract`, `arxivId`, `authors`, `contributors`, `createdDate`, `dataProviders`, `depositedDate`, `documentType`, `doi`, `fullText`, `id`, `language`, `license`, `oai`, `title`, `yearPublished`

### 3. Get work by ID

```
GET /v3/works/{id}
```

`id` is a CORE Work ID (integer). Example: `/v3/works/267312`

### 4. Get output by ID

```
GET /v3/outputs/{id}
```

### 5. Download full text

```
GET /v3/outputs/{id}/download
```

Returns binary PDF. Requires authentication.

```
GET /v3/works/tei/{id}
```

Returns TEI XML format.

### 6. Search outputs

```
GET /v3/search/outputs/?q={query}&limit={n}&offset={n}
```

Search by DOI: `q=doi:10.1038/nature12373`

## Response Format

### Search response
```json
{
  "totalHits": 2281337,
  "limit": 10,
  "offset": 0,
  "scrollId": null,
  "results": [...]
}
```

### Work object (key fields)
```json
{
  "id": 8848131,
  "title": "Attention Is All You Need",
  "authors": [{"name": "Ashish Vaswani"}, ...],
  "abstract": "The dominant sequence...",
  "doi": "10.48550/arXiv.1706.03762",
  "arxivId": "1706.03762",
  "yearPublished": 2017,
  "downloadUrl": "https://core.ac.uk/download/...",
  "fullText": "Full text content (when authenticated)...",
  "language": {"code": "en", "name": "English"},
  "documentType": "research",
  "citationCount": 145678,
  "dataProviders": [{"name": "arXiv"}],
  "links": [{"type": "download", "url": "..."}]
}
```

## Pagination

- **Standard:** `offset` + `limit` (max 10,000 results)
- **Scroll:** Set `scroll=true`. Response includes `scrollId`. Use in subsequent requests to page beyond 10,000 (costs more tokens).

## Error Handling

Under heavy load, the API may return partial shard failure messages. These are transient -- retry after a brief wait.
