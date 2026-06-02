# bioRxiv API

bioRxiv is a preprint server for biology. The API provides metadata for preprints, including title, authors, abstract, DOI, and publication status.

**Important:** The bioRxiv API has **no keyword search**. It supports date-range browsing and DOI lookup only. For keyword search of bioRxiv preprints, use Semantic Scholar, OpenAlex, or CORE instead.

## Base URL

```
https://api.biorxiv.org
```

## Authentication

None required. Fully public API.

## Key Endpoints

### 1. Content Detail -- Browse by date range

```
GET /details/biorxiv/{interval}/{cursor}/{format}
```

| Parameter | Values | Description |
|-----------|--------|-------------|
| `interval` | `YYYY-MM-DD/YYYY-MM-DD` | Date range (inclusive). Keep ranges narrow (1-3 days) to avoid timeouts. |
| | `N` (integer) | N most recent preprints |
| | `Nd` (integer + "d") | Last N days |
| `cursor` | Integer (default `0`) | Pagination offset (100 results per page) |
| `format` | `json` (default), `xml` | Response format |

Optional query parameter: `?category=neuroscience` (filter by category, use underscores for spaces)

**Examples:**
```
https://api.biorxiv.org/details/biorxiv/2024-01-01/2024-01-31/0
https://api.biorxiv.org/details/biorxiv/5
https://api.biorxiv.org/details/biorxiv/10d
https://api.biorxiv.org/details/biorxiv/2024-01-01/2024-01-31?category=neuroscience
```

### 2. Content Detail -- DOI lookup

```
GET /details/biorxiv/{doi}/na/{format}
```

**Example:**
```
https://api.biorxiv.org/details/biorxiv/10.1101/2024.01.16.575895/na/json
```

### 3. Published Article Links

```
GET /pubs/biorxiv/{interval}/{cursor}
GET /pubs/biorxiv/{doi}/na
```

Links preprints to their published journal versions. Accepts both preprint DOI and published DOI.

### 4. Publisher Filter

```
GET /publisher/{prefix}/{interval}/{cursor}
```

Find bioRxiv papers published by a specific publisher (by DOI prefix).

**Example:**
```
https://api.biorxiv.org/publisher/10.15252/2024-01-01/2024-06-01/0
```

## Response Format

```json
{
  "messages": [{
    "status": "ok",
    "count": 100,
    "total": "1029",
    "cursor": 0
  }],
  "collection": [{
    "title": "Paper title...",
    "authors": "Surname, A.; Surname, B.",
    "author_corresponding": "Full Name",
    "author_corresponding_institution": "Institution",
    "doi": "10.1101/2024.01.16.575895",
    "date": "2024-01-20",
    "version": "1",
    "type": "new results",
    "license": "cc_no",
    "category": "cancer biology",
    "jatsxml": "https://www.biorxiv.org/content/early/.../source.xml",
    "abstract": "Full abstract text...",
    "published": "10.1158/2159-8290.CD-24-0187",
    "server": "bioRxiv"
  }]
}
```

- `published` is `"NA"` if not yet published in a journal, or the published DOI if it has been.
- `type` values: `new results`, `confirmatory results`, `contradictory results`

## Pagination

All multi-result endpoints return **100 results per page**. Use `cursor` to paginate. The `messages` object tells you the `total` count.

## Rate Limits

No documented rate limits. No authentication required. Be reasonable with request frequency.

## Categories

`animal-behavior-and-cognition`, `biochemistry`, `bioengineering`, `bioinformatics`, `biophysics`, `cancer-biology`, `cell-biology`, `clinical-trials`, `developmental-biology`, `ecology`, `epidemiology`, `evolutionary-biology`, `genetics`, `genomics`, `immunology`, `microbiology`, `molecular-biology`, `neuroscience`, `paleontology`, `pathology`, `pharmacology-and-toxicology`, `physiology`, `plant-biology`, `scientific-communication-and-education`, `synthetic-biology`, `systems-biology`, `zoology`
