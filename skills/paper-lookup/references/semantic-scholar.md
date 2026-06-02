# Semantic Scholar API

Semantic Scholar indexes 200M+ papers across all academic fields with AI-powered features: citation context, influential citations, TLDRs, and paper recommendations.

## Base URLs

```
https://api.semanticscholar.org/graph/v1       (Academic Graph)
https://api.semanticscholar.org/recommendations/v1  (Recommendations)
```

## Authentication

- **Without key:** Shared rate pool (frequently hits 429 errors). Works but unreliable.
- **With key:** 1 req/sec per key (higher on request).
- Header: `x-api-key: YOUR_KEY`
- Get a free key at: https://www.semanticscholar.org/product/api#api-key-form

## The `fields` Parameter

Almost every endpoint accepts `fields` -- a comma-separated list (no spaces) of fields to include. Without it, you only get `paperId` + `title`.

**Paper fields:**
`paperId`, `corpusId`, `externalIds`, `url`, `title`, `abstract`, `venue`, `publicationVenue`, `year`, `referenceCount`, `citationCount`, `influentialCitationCount`, `isOpenAccess`, `openAccessPdf`, `fieldsOfStudy`, `s2FieldsOfStudy`, `publicationTypes`, `publicationDate`, `journal`, `authors`, `citations`, `references`, `tldr`, `embedding`

**Author fields:**
`authorId`, `externalIds`, `url`, `name`, `affiliations`, `homepage`, `paperCount`, `citationCount`, `hIndex`, `papers`

## Paper ID Formats

The `{paper_id}` parameter accepts:
- `649def34f8be52c8b66281af98ae884c09aef38b` (S2 hash)
- `CorpusId:215416146`
- `DOI:10.1038/s41586-021-03819-2`
- `ARXIV:2005.14165`
- `PMID:19872477`
- `PMCID:2323736`
- `ACL:W12-3903`

## Key Endpoints

### 1. Paper search (relevance)

```
GET /graph/v1/paper/search?query={text}&fields={fields}&offset={n}&limit={n}
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `query` | required | Plain-text search |
| `fields` | paperId,title | Comma-separated |
| `offset` | 0 | Pagination start |
| `limit` | 100 | Max 100 |
| `year` | -- | `2019` or `2016-2020` |
| `publicationDateOrYear` | -- | `YYYY-MM-DD:YYYY-MM-DD` |
| `fieldsOfStudy` | -- | e.g., `Computer Science,Medicine` |
| `publicationTypes` | -- | e.g., `JournalArticle,Conference` |
| `openAccessPdf` | -- | Filter for OA papers |
| `minCitationCount` | -- | Minimum citations |
| `venue` | -- | Comma-separated venues |

**Max 1,000 results** accessible via offset.

**Example:**
```
https://api.semanticscholar.org/graph/v1/paper/search?query=CRISPR+gene+therapy&fields=title,year,abstract,citationCount,authors,openAccessPdf&limit=10&year=2023-2024
```

### 2. Paper bulk search (boolean queries, large result sets)

```
GET /graph/v1/paper/search/bulk?query={text}&fields={fields}&sort={field}:{order}&token={token}
```

- Supports boolean operators: `+` (AND), `|` (OR), `-` (NOT), `"..."` (phrase), `*` (wildcard), `()` (grouping)
- Token-based pagination (up to 10M papers)
- Returns up to 1,000 per call
- Sortable: `citationCount:desc`, `publicationDate:desc`, `paperId:asc`

### 3. Paper details (by ID)

```
GET /graph/v1/paper/{paper_id}?fields={fields}
```

**Example:**
```
https://api.semanticscholar.org/graph/v1/paper/DOI:10.1038/s41586-021-03819-2?fields=title,year,abstract,citationCount,referenceCount,isOpenAccess,openAccessPdf,authors,tldr
```

**Response:**
```json
{
  "paperId": "dc32a984b651256a8ec282be52310e6bd33d9815",
  "title": "Highly accurate protein structure prediction with AlphaFold",
  "year": 2021,
  "citationCount": 34260,
  "isOpenAccess": true,
  "openAccessPdf": {"url": "https://...pdf", "status": "HYBRID"},
  "tldr": {"text": "This work develops AlphaFold, a system that..."},
  "authors": [{"authorId": "47921134", "name": "J. Jumper"}, ...]
}
```

### 4. Paper citations

```
GET /graph/v1/paper/{paper_id}/citations?fields={fields}&offset={n}&limit={n}
```

Returns papers that cite this paper. `limit` max 1000.

Citation-specific fields: `contexts`, `intents`, `isInfluential`

### 5. Paper references

```
GET /graph/v1/paper/{paper_id}/references?fields={fields}&offset={n}&limit={n}
```

Returns papers cited by this paper. Same pagination as citations.

### 6. Paper title match

```
GET /graph/v1/paper/search/match?query={exact title}&fields={fields}
```

Returns single best match with `matchScore`. 404 if no match.

### 7. Author search

```
GET /graph/v1/author/search?query={name}&fields={fields}&offset={n}&limit={n}
```

### 8. Author details

```
GET /graph/v1/author/{author_id}?fields={fields}
```

### 9. Author's papers

```
GET /graph/v1/author/{author_id}/papers?fields={fields}&offset={n}&limit={n}
```

### 10. Paper recommendations

```
GET /recommendations/v1/papers/forpaper/{paper_id}?fields={fields}&limit={n}&from={pool}
```

`from`: `recent` (default) or `all-cs`. `limit` max 500.

### 11. Multi-paper recommendations (POST)

```
POST /recommendations/v1/papers/
Content-Type: application/json

{
  "positivePaperIds": ["paperId1", "paperId2"],
  "negativePaperIds": ["paperId3"]
}
```

### 12. Paper batch (POST)

```
POST /graph/v1/paper/batch?fields={fields}
Content-Type: application/json

{"ids": ["DOI:10.1038/nature12373", "ARXIV:2005.14165"]}
```

Max 500 IDs per request.

## Pagination

| Endpoint | Max per page | Max total | Method |
|----------|-------------|-----------|--------|
| Relevance search | 100 | 1,000 | offset/next |
| Bulk search | 1,000 | 10,000,000 | token |
| Citations/References | 1,000 | all | offset/next |
| Author search | 1,000 | -- | offset/next |

## Publication Types

`Review`, `JournalArticle`, `CaseReport`, `ClinicalTrial`, `Conference`, `Dataset`, `Editorial`, `LettersAndComments`, `MetaAnalysis`, `News`, `Study`, `Book`, `BookSection`

## Fields of Study

`Computer Science`, `Medicine`, `Chemistry`, `Biology`, `Materials Science`, `Physics`, `Geology`, `Psychology`, `Art`, `History`, `Geography`, `Sociology`, `Business`, `Political Science`, `Economics`, `Philosophy`, `Mathematics`, `Engineering`, `Environmental Science`, `Agricultural and Food Sciences`, `Education`, `Law`, `Linguistics`

## Error Format

```json
{"message": "Too Many Requests", "code": "429"}
```

HTTP 404 for not found, 429 for rate limit.
