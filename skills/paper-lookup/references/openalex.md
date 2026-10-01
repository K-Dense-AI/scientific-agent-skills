# OpenAlex API

OpenAlex is a comprehensive index of 250M+ scholarly works, authors, institutions, sources, and topics. It's the broadest multidisciplinary database in this skill.

## Base URL

```
https://api.openalex.org
```

## Authentication

- **API key recommended** (free). Get one at https://openalex.org/settings/api
- Pass as `?api_key=YOUR_KEY` or `Authorization: Bearer YOUR_KEY`.
- Current access is budget-based; do not promise a higher quota from the legacy `mailto` parameter.

## Rate Limits

- **100 requests/second** max
- Usage-based pricing: $0.10/day without a key, $1/day with a free account key
- Single entity lookups by ID/DOI are free (unlimited)
- List + filter queries: ~$0.0001 each (~10,000/day free)
- Search queries: ~$0.001 each (~1,000/day free)

## Key Endpoints

### 1. Get a single work

```
GET /works/{id}
```

Accepts multiple ID formats:
```
/works/W2741809807                              (OpenAlex ID)
/works/doi:10.7717/peerj.4375                  (DOI)
/works/pmid:29456894                            (PMID)
/works/https://doi.org/10.7717/peerj.4375      (full DOI URL)
```

### 2. Search works

```
GET /works?search={query}&per_page={n}&page={n}
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `search` | -- | Full-text search (title, abstract, fulltext). Supports boolean: `AND`, `OR`, `NOT` (uppercase) |
| `search.exact` | -- | No stemming |
| `search.semantic` | -- | AI embedding search (beta, 1 req/s, max 50 results) |
| `filter` | -- | Comma-separated `field:value` pairs |
| `sort` | relevance | `cited_by_count:desc`, `publication_date:desc`, `relevance_score:desc` |
| `per_page` | 25 | Results per page (max 100) |
| `page` | 1 | Page number (max `page * per_page` = 10,000) |
| `cursor` | -- | Use `*` for first page of deep pagination |
| `select` | -- | Comma-separated fields to return |
| `group_by` | -- | Aggregate by field |

**Advanced search:** Supports wildcards (`machin*`), fuzzy (`machin~1`), proximity (`"climate change"~5`), boolean grouping.

**Example:**
```
https://api.openalex.org/works?search=CRISPR+gene+therapy&filter=from_publication_date:2023-01-01&sort=cited_by_count:desc&per_page=10
```

### 3. Filter works

```
GET /works?filter={filters}
```

Key filter fields:
| Filter | Example | Description |
|--------|---------|-------------|
| `from_publication_date` | `2023-01-01` | Published after date |
| `to_publication_date` | `2024-12-31` | Published before date |
| `publication_year` | `2024` | Exact year |
| `type` | `article` | Work type |
| `cited_by_count` | `>100` | Citation threshold |
| `is_oa` | `true` | Open access only |
| `has_abstract` | `true` | Has abstract |
| `authorships.author.id` | `A5048491430` | By author ID |
| `primary_location.source.id` | `S137773608` | By journal/source |
| `institutions.country_code` | `us` | By country |
| `topics.id` | `T10001` | By topic ID; legacy concepts are deprecated |
| `doi` | `10.1038/nature12373` | By DOI |

**Operators:** `>`, `<`, `!` (negation), `|` (OR within filter)

**Example:**
```
https://api.openalex.org/works?filter=from_publication_date:2024-01-01,type:article,is_oa:true,cited_by_count:>50
```

### 4. Other entities

```
GET /authors?search={name}
GET /authors/{id}
GET /sources?search={name}          (journals, repositories)
GET /sources/{id}
GET /institutions?search={name}
GET /institutions/{id}
GET /topics/{id}
```

Authors and institutions accept similar filter/sort/pagination parameters.

### 5. Cursor pagination (for >10,000 results)

```
GET /works?filter=publication_year:2024&cursor=*&per_page=100
```

Response includes `meta.next_cursor`. Pass it as `cursor={value}` in the next request. Stop when `next_cursor` is null and the results are exhausted. The supported page maximum is 100; 200 is deprecated legacy behavior.

## Response Format

### Work object (key fields)

```json
{
  "id": "https://openalex.org/W2741809807",
  "doi": "https://doi.org/10.7717/peerj.4375",
  "title": "The state of OA",
  "publication_year": 2018,
  "publication_date": "2018-02-13",
  "type": "article",
  "language": "en",
  "is_retracted": false,
  "cited_by_count": 1169,
  "open_access": {
    "is_oa": true,
    "oa_status": "gold",
    "oa_url": "https://doi.org/10.7717/peerj.4375"
  },
  "authorships": [{
    "author": {"id": "https://openalex.org/A5048491430", "display_name": "Heather Piwowar"},
    "institutions": [{"display_name": "Impactstory"}]
  }],
  "primary_location": {
    "source": {"display_name": "PeerJ", "issn_l": "2167-8359"}
  },
  "abstract_inverted_index": {"Despite": [0], "growing": [1], "interest": [2], ...},
  "referenced_works": ["https://openalex.org/W123...", ...],
  "ids": {"openalex": "...", "doi": "...", "pmid": "..."}
}
```

### Abstract inverted index

Abstracts are stored as `{word: [positions]}`. Use the bundled parser:
```bash
python3 scripts/openalex_abstract.py work.json
```

It reports collisions and gaps instead of silently overwriting tokens. A null
index means no abstract was supplied; `select` can also exclude the field.

### List response

```json
{
  "meta": {"count": 3771834, "page": 1, "per_page": 10},
  "results": [...]
}
```

## Error Format

HTTP 403 for invalid API key, 429 for rate limit exceeded. Error responses include a message field.

## Official sources reviewed 2026-09-30

- https://help.openalex.org/api/authentication/
- https://help.openalex.org/api/paging/
- https://help.openalex.org/api/searching/
- https://help.openalex.org/api/semantic-search/
- https://help.openalex.org/api/endpoints/
- https://help.openalex.org/access/example-costs/
