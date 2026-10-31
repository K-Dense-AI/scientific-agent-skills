# Literature database search strategies

Reviewed 2026-09-30. These are bibliographic discovery contracts, not a promise
of complete retrieval. Save query, platform, date/time, date-field meaning,
filters, raw pages, reported total, exported count, and any failures. Mark a
capped or interrupted retrieval incomplete before screening it.

## Source selection and query design

1. Define the review type and eligibility criteria before seeing results. Use
   PICO for intervention questions; adapt the framework for other questions.
2. Select complementary bibliographic databases, relevant registries, preprint
   servers, and grey literature sources. A web search and a biological entity
   database are not substitutes for a discipline's bibliographic index.
3. Build synonym groups with OR and combine concepts with AND. Pilot against
   known eligible papers. Consider whether outcome filters, language limits,
   publication-type limits, or NOT terms discard relevant studies.
4. Translate each query to that platform. Wildcards and field syntax are not
   portable: do not copy PubMed `[MeSH]`, arXiv `ti:`, or search-engine operators
   into another API. Record the actual translated query, not just keywords.
5. For systematic reviews, screen against protocol criteria regardless of venue,
   author reputation, institutional affiliation, or citation count. Bibliometric
   metrics reflect exposure and field/age effects, not risk of bias.

## PubMed and PMC

Use the [PubMed interface](https://pubmed.ncbi.nlm.nih.gov/advanced/) or NCBI
E-utilities. `gget search` searches Ensembl and has no PubMed/bioRxiv mode.
PubMed contains bibliographic records; PMC is a full-text repository with a
partly overlapping corpus. Do not equate access to an abstract with full text.

A small first-page request, not a complete review search:

```bash
mkdir -p sources
curl --fail-with-body --get 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi' \
  --data-urlencode 'db=pubmed' \
  --data-urlencode 'term=(CRISPR[Title/Abstract]) AND ("Anemia, Sickle Cell"[MeSH Terms])' \
  --data-urlencode 'retmode=json' --data-urlencode 'retmax=5' \
  --data-urlencode 'tool=literature_review' -o sources/pubmed-first-page.json
```

- ESearch returns `esearchresult.count` (often a string), `idlist`, and query
  translation/warnings. Inspect these; HTTP 200 alone does not confirm success.
- Use `retstart`/`retmax` for paging **within the first 10,000 PubMed matches**.
  Partition larger searches into recorded, deduplicated subqueries or use a
  documented bulk method; the History server does not bypass this limit.
- EFetch is `GET .../efetch.fcgi?db=pubmed&id=PMID1,PMID2&retmode=xml` (or POST for
  large ID sets). Parse `PubmedArticleSet` XML, preserve article/book records,
  and reconcile requested versus returned IDs.
- No key is needed for small requests. Supply a real contact `email` and `tool`
  for sustained use; optional `api_key` raises the default shared limit from
  3 requests/s per IP to 10/s per key. Account for concurrent clients.
- Use explicit `[Publication Date]` ranges, and record the selected field.
  A historical example such as `2020:2024[DP]` does not mean "current years".

Sources: [NLM parameter guide](https://www.nlm.nih.gov/dataguide/eutilities/utilities.html),
[PubMed 10,000-result ceiling](https://ncbiinsights.ncbi.nlm.nih.gov/2021/10/05/updated-pubmed-api/),
[NCBI usage guidelines](https://eutilities.github.io/site/API_Key/usageandkey/).

## bioRxiv and medRxiv

The [official API](https://api.biorxiv.org/) provides date/DOI metadata retrieval,
not a general keyword query endpoint. Use the server's search interface for
keyword discovery or filter the downloaded metadata explicitly.

- `GET https://api.biorxiv.org/details/{server}/{from}/{to}/{cursor}/json`, with
  server `biorxiv` or `medrxiv`, date strings `YYYY-MM-DD`, zero-based
  cursor (start at 0), and optional `category=cell_biology`.
- Response `collection[]` holds records; `messages[]` describes status, count,
  cursor, and totals. Date-range calls return at most 30 records; advance the
  cursor by the number received, retain all versions, and check totals/status.
- Single DOI: `/details/{server}/{doi}/na/json`. Preserve DOI, `version`, `date`,
  abstract, license, and `published` linkage. A preprint and a published report
  may describe one study but are distinct reports.
- `/pubs/{server}/{from}/{to}/{cursor}` maps publication links, with up to 100
  entries per page. It has a different schema (`biorxiv_doi`, `published_doi`).
- Public reads need no API key. Use conservative sequential calls and stop on
  throttling/errors; do not interpret missing publication links as proof that
  a preprint remains unpublished.

## arXiv

`GET https://export.arxiv.org/api/query` accepts `search_query`, `id_list`,
`start` (zero-based), `max_results`, `sortBy`, and `sortOrder`. No key is needed.

```bash
curl --fail-with-body --get 'https://export.arxiv.org/api/query' \
  --data-urlencode 'search_query=cat:q-bio.QM AND ti:"single cell"' \
  --data-urlencode 'start=0' --data-urlencode 'max_results=5' \
  --data-urlencode 'sortBy=submittedDate' --data-urlencode 'sortOrder=descending' \
  -o sources/arxiv-first-page.xml
```

Parse Atom namespaces, `opensearch:totalResults`, and entry IDs; error entries
can arrive in an Atom feed. Preserve `vN`, original `published`, and `updated`
dates. `ti:` is the title field, not `title:`. Use a single connection with at
least three seconds between requests. Use pages no larger than 2,000 and do
not expect offsets to provide more than 30,000 matches; partition or use the
bulk interfaces. This is preprint discovery, not evidence of peer review.

Source: [arXiv API manual](https://info.arxiv.org/help/api/user-manual.html).

## Semantic Scholar

Use the [Graph API contract](https://api.semanticscholar.org/api-docs/graph)
(and its downloadable [schema](https://api.semanticscholar.org/graph/v1/swagger.json)).

- Relevance search: `GET https://api.semanticscholar.org/graph/v1/paper/search`;
  plain-text `query`, separate `year=2020-2024`, optional `fields`, `offset`,
  `limit` (maximum 100). Response has `data[]`, `total`, and optional `next`.
  Only 1,000 relevance-ranked records are retrievable; not an exhaustive export.
- Bulk search: `GET .../paper/search/bulk`; query uses its documented Boolean
  grammar (`+`, `|`, `-`, quotes, parentheses), with separate filters and
  `fields`. Response has `data[]` and a continuation `token`; pass that token
  unchanged to the next request. Up to 1,000 records/call, capped at 10 million.
  Nested citation/reference data are not available on this endpoint.
- Do not invent `title:`/`author:` operators for the relevance API. Use separate
  author or title search routes only after consulting their own contracts.
- API keys go in `x-api-key`; availability/quota depends on the endpoint and
  account. Anonymous access is a shared, throttled pool. Follow your granted
  quota, inspect HTTP 429, and back off; the former blanket "100 requests per
  5 minutes" is not a current service guarantee.
- Citation counts and influential-citation labels are discovery aids. Check
  paper identity, missing fields, date coverage, and source text yourself.

## OpenAlex, Crossref, and supplementary search

[OpenAlex authentication](https://help.openalex.org/api/authentication/) permits
keyless casual reads; a free key raises the daily budget. Use `api_key` or
`Authorization: Bearer` without saving secrets in search logs. `GET
https://api.openalex.org/works` accepts `search`, `filter`, `select`, and `sort`.
Responses have `results[]` and `meta`. The current `per_page` maximum is 100;
start `cursor=*` and follow `meta.next_cursor` unchanged. Basic page-based
retrieval stops at 10,000. Respect request credits and rate-limit headers;
keyless does not mean unlimited. See [paging](https://help.openalex.org/api/paging/).

Crossref `GET https://api.crossref.org/works/{doi}` is a singleton metadata
lookup with JSON `message`, no key or pagination. A 404 does not prove a DOI
from another registration agency is invalid. List searches (`/works?query...`)
have different quotas and pagination: public list limit 1/s, polite 3/s, versus
5/s and 10/s for single records. Provide real `mailto` for polite access; follow
[response headers](https://community.crossref.org/t/refining-rest-api-limits-for-improved-stability-and-reliability/16137).

Google Scholar's [interface](https://scholar.google.com/intl/en/scholar/help.html)
provides Cited by, Related articles, and Cite exports, but no supported bulk API.
Record queries and screened ranges; do not promise citation-count sorting,
unlimited results, or complete coverage from a ranked sample. Stop on access
blocks. Dimensions and licensed indexes require the access your institution
actually holds; a free website tier does not imply API entitlement.

## Result normalization and reproducibility

`search_databases.py` does **not** query or merge raw provider envelopes. Give it
a JSON array of normalized objects, preserving the raw exports separately:

```json
[
  {"title": "Example title", "authors": "Author, A. and Author, B.",
   "first_author": "Author", "year": 2026, "source": "PubMed",
   "doi": null, "url": "https://pubmed.ncbi.nlm.nih.gov/", "citations": null}
]
```

Use strings for title/authors/source and numbers or null for citation counts;
BibTeX authors require `and` separators. Keep provider IDs, search/run IDs,
retrieval dates, and source provenance as extra fields. Missing is not zero.

```bash
python scripts/search_databases.py combined_results.json --deduplicate \
  --format json --output unique_results.json --summary
```

Deduplication keeps the first normalized DOI; title fallback compares DOI-less
records only. Review title matches manually and enrich from raw duplicates;
the script does not choose the most complete metadata or link all reports of a
study. Unknown years remain for manual review. Ranking only orders the imported
sample. Use final BibTeX keys from the export; same-author/year keys receive
suffixes. An export timestamp is not the original search date.

Use the official [PRISMA guidance](https://www.prisma-statement.org/prisma-2020)
and [Cochrane selection guidance](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-04)
to keep screening decisions and report/study links auditable.
