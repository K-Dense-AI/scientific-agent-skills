# bioRxiv API

bioRxiv is a preprint server for biology. The API provides metadata for preprints, including title, authors, abstract, DOI, and publication status.

**Important:** The bioRxiv API has **no keyword search**. It supports date-range browsing and DOI lookup only. For keyword search of bioRxiv preprints, use Europe PMC (`SRC:"PPR" AND PUBLISHER:"bioRxiv"`), Semantic Scholar, or OpenAlex instead.

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
| `cursor` | Integer (default `0`) | Absolute record offset. **`/details/` returns 30 per page, so step by 30** -- see Pagination. |
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

```
https://api.biorxiv.org/publisher/10.15252/2024-01-01/2024-06-01/0
```

**Hazard:** this endpoint returns `{"messages":[{"status":"no articles found"}],"collection":[]}` for
many valid publisher prefixes, including the one above (EMBO, verified 2026-07-27) -- with **HTTP
200**, so an empty `collection` is indistinguishable from a genuine no-match. Treat an empty result
here as inconclusive, not as evidence that a publisher issued no bioRxiv preprints. To answer
"which bioRxiv preprints did publisher X publish", prefer `/pubs/` (below) and group by
`published_journal`, or query Crossref with `filter=prefix:10.15252`.

## Response Format

```json
{
  "messages": [{
    "status": "ok",
    "category": "all",
    "interval": "2024-01-01:2024-01-03",
    "funder": "all",
    "cursor": 0,
    "count": 30,
    "count_new_papers": "232",
    "total": "360"
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

### The `messages` block is not uniform -- check before reconciling

The counting fields exist **only on interval queries**. Verified 2026-07-27:

| Request | `messages[0]` contains |
|---|---|
| `/details/biorxiv/2024-01-01/2024-01-03/0` | `status`, `category`, `interval`, `funder`, `cursor`, `count`, `count_new_papers`, `total` |
| `/details/biorxiv/{doi}/na/json` | `status`, `category` only -- **no counts** |
| `/details/biorxiv/5` (N most recent) | `status`, `category` only -- **no counts** |
| `/pubs/biorxiv/{interval}/{cursor}` | `status`, `interval`, `cursor`, `count`, `total` |

So the skill's "count first, then reconcile" step has nothing to reconcile against on DOI and
N-most-recent lookups. Use `len(collection)` there and say in the provenance that the endpoint
exposes no total.

**`total` and `count_new_papers` count different things.** For `2024-01-01:2024-01-03`, `total` was
`360` and `count_new_papers` was `232`: `total` counts every *version* record in the interval, while
`count_new_papers` counts distinct first-posting preprints. Paginating to `total` and then
deduplicating by DOI lands near `count_new_papers`, not `total` -- reconcile against the right one
and report which you used.

## Pagination

**Page size differs by endpoint** -- verified 2026-07-27, and the difference is silent:

| Endpoint | Records per page | Step `cursor` by |
|---|---|---|
| `/details/{server}/{interval}/{cursor}` | **30** | 30 |
| `/pubs/{server}/{interval}/{cursor}` | 100 | 100 |

`cursor` is an absolute record offset, not a page number, and out-of-step values are accepted
without complaint: `cursor=100` on a `/details/` query returns records 100-129 and **HTTP 200**.
Stepping a `/details/` walk by 100 therefore skips records 30-99 of every hundred and looks
successful. Step by the `count` the response actually reported, and stop when
`cursor + count >= total` or `collection` comes back empty.

`scripts/paginate.py --api biorxiv` implements this walk with the right step and reconciles version-record counts against `total`; it reports `count_new_papers` as a separate note, without claiming to validate a DOI-deduplicated count.

## Rate Limits

No documented rate limits. No authentication required. Be reasonable with request frequency.

DOI lookups and N-most-recent requests are single-response lookups in the helper: they expose no total/continuation. For an exhaustive interval, use explicit dates and reconcile `total`. A DOI path requires `/na/json`, not a numeric cursor.

## Categories

Category names below are website slugs; API category filters use spaces (URL-encoded) or underscores, e.g. `cell_biology`, not hyphens.

`animal-behavior-and-cognition`, `biochemistry`, `bioengineering`, `bioinformatics`, `biophysics`, `cancer-biology`, `cell-biology`, `clinical-trials`, `developmental-biology`, `ecology`, `epidemiology`, `evolutionary-biology`, `genetics`, `genomics`, `immunology`, `microbiology`, `molecular-biology`, `neuroscience`, `paleontology`, `pathology`, `pharmacology-and-toxicology`, `physiology`, `plant-biology`, `scientific-communication-and-education`, `synthetic-biology`, `systems-biology`, `zoology`

## Official sources reviewed 2026-09-30

- https://api.biorxiv.org/
