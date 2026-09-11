# DOAJ (Directory of Open Access Journals)

A curated directory of *open-access journals* and the articles those journals
have registered with DOAJ. Use it to answer "is this journal in DOAJ?" or
"articles in DOAJ-listed journals matching X." It is not a general literature
index and it is not Unpaywall.

Nature is not in DOAJ. A paper can be open access (hybrid, bronze, green)
without its journal being listed here. For "is there a free PDF of this DOI?"
use Unpaywall. For the yes/no "is this journal in DOAJ?" when you are already
on OpenAlex, `GET /sources/issn:{issn}` returns `is_in_doaj` (PLoS ONE
`1932-6203` is `true`; Nature `0028-0836` is `false`) — stay there. Come
to DOAJ when you need APC, licence, or `oa_start`. For "papers on CRISPR"
use PubMed / OpenAlex, then optionally restrict to DOAJ journals.

All figures below verified 2026-09-10 against API **v4**.

## Base URL

```
https://doaj.org/api
```

Docs (live): https://doaj.org/api/docs

Search URLs you write as `/api/search/...` are served as v4; `next` links
in the JSON point at `/api/v4/search/...`. Either form works.

## Authentication

Public search needs no key. API keys are for publisher submitters. Do not
ask the user for a DOAJ key to look up a journal.

## Rate Limits

No published per-second cap. Be polite. Prefer a journal ISSN lookup over
paging through tens of thousands of article hits.

## Query syntax

The path segment *is* the query (Elasticsearch query string). Slash in a DOI
is escaped for you.

| Goal | Query |
|---|---|
| Article title words | `bibjson.title:CRISPR` |
| DOI | `doi:10.3389/fpsyg.2013.00479` |
| Journal ISSN | `issn:1932-6203` |
| Exact journal title | `bibjson.title.exact:"PLoS ONE"` |
| Short names | `title:`, `issn:`, `publisher:`, `license:` (journals) |

`.exact` works on full field names, **not** on the short aliases.

## Key Endpoints

### 1. Search articles

```
GET /search/articles/{query}?page=1&pageSize=10
```

```
GET /search/articles/bibjson.title:CRISPR?pageSize=2
```

Verified: `total` 7777, `page` 1, `pageSize` 2, `results` length 2.
`next` was
`https://doaj.org/api/v4/search/articles/bibjson.title:CRISPR?page=2&pageSize=2`.
Follow `next` (or increment `page`) rather than guessing a last page —
`last` pointed at page 3889.

Each result has `id`, `created_date`, `last_updated`, `bibjson`. Identifiers
are a **list**:

```json
"identifier": [
  {"id": "10.3390/v14102045", "type": "doi"},
  {"id": "1999-4915", "type": "eissn"}
]
```

Pick `type == "doi"`. Do not take `identifier[0]` blindly (it may be an ISSN).

### 2. Search journals

```
GET /search/journals/{query}?page=1&pageSize=10
```

Verified:

| Query | `total` | Notes |
|---|---|---|
| `issn:0028-0836` (Nature) | 0 | Subscription journal. Empty is the answer. |
| `issn:1932-6203` (PLoS ONE) | 1 | `bibjson.title` `PLoS ONE`, `oa_start` 2006, `apc.has_apc` true, max 2477 USD |

HTTP 200 + `total: 0` + `results: []` means "not a DOAJ journal," not an
outage. Unpaywall may still find a green or hybrid copy of a Nature paper.

Journal `bibjson` includes title, ISSNs, publisher, license, APC, and
`oa_start`. That is the record to quote when someone asks "is this journal
OA in DOAJ?"

## Typical Workflow

1. Have an ISSN or journal title → `/search/journals/issn:{issn}`.
2. Have a DOI you believe is in a DOAJ journal → `/search/articles/doi:{doi}`.
3. If journals search is empty, say so and check Unpaywall for the article.
4. Do not page `bibjson.title:CRISPR` as a substitute for PubMed.

## Failure Modes

| What you did | What happens | What to do |
|---|---|---|
| ISSN of a non-DOAJ journal | 200, `total: 0` | Report "not in DOAJ"; try Unpaywall |
| Took `identifier[0]` as the DOI | You may get an eISSN | Filter `type == "doi"` |
| Used DOAJ as Unpaywall | Misses hybrid/green OA | Article-level OA is Unpaywall |
| Second host just for yes/no | Extra call | OpenAlex `sources.is_in_doaj` if you are already there |
| Used short field + `.exact` | Query does not mean what you think | Use `bibjson.title.exact` |
