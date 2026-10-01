# Zenodo

CERN's general research repository: papers, preprints, software, datasets,
presentations, and posters, each with a DataCite DOI (`10.5281/zenodo.…`).
Use it when the user wants a deposited record or file, not a journal article
index. For journal OA PDFs use Unpaywall. For biology datasets that live at
EBI, try BioStudies first.

All figures below verified 2026-09-10.

## Base URL

```
https://zenodo.org/api
```

Docs: https://developers.zenodo.org/

## Authentication

**Published records are public.** `GET /api/records` works with no token.

Deposit / publish (`/api/deposit/depositions`) requires a personal access
token and is out of scope for this skill. Without a token that path returns
HTTP **403** `Permission denied.` (not always 401). Do not start a deposit
flow from a literature lookup.

## Rate Limits

Public search is limited to **30 requests/minute**. Guest global limits are 60/minute and 2,000/hour; authenticated global limits are 100/minute and 5,000/hour. Inspect `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset`; serialize long walks.

## Key Endpoints

### 1. Search published records

```
GET /api/records?q={elasticsearch}&type={type}&size={n}&page={n}
```

`q` is Elasticsearch syntax. `type` filters the Invenio resource type
(`publication`, `software`, `dataset`, `image`, `poster`, `presentation`,
`video`, `other`). Default search mixes all of them.

```
GET /api/records?q=CRISPR+organoid&size=2
```

Verified: HTTP 200, `hits.total` 3499, two hits. First hit was an SSRN
*publication*, not a dataset. Always read `metadata.resource_type`.

```
GET /api/records?q=scanpy&type=software&size=2
```

Verified: `hits.total` 40; both hits `resource_type.type` is `software`.

Response shape:

```json
{
  "hits": { "total": 3499, "hits": [ { "id": …, "doi": …, "metadata": {…}, "files": […], "links": {…} } ] },
  "links": { "self": "…", "next": "…" }
}
```

Page with `page` (1-based) and `size`. Follow `links.next` when present. The documented `size` maximum is 25 anonymously or 100 authenticated. Use metadata exports/OAI-PMH for bulk retrieval rather than assuming unlimited search paging.

### 2. One record by id or DOI

```
GET /api/records/{id}
GET /api/records?q=doi:%2210.5281/zenodo.{id}%22
```

**Follow redirects.** A concept (parent) record id 302s to the latest version:

```
GET /api/records/3246410
  -> 302  Location: /api/records/3246411
GET /api/records/3246411   (after curl -L)
  -> 200  id=3246411
          doi=10.5281/zenodo.3246411          # this version
          conceptdoi=10.5281/zenodo.3246410   # all versions
          conceptrecid=3246410
```

`curl` without `-L` returns HTML "Redirecting…" and JSON parse fails. Use
`-L` and then report both DOIs: the version DOI is the file you fetched;
the concept DOI is the stable cite-all-versions id.

Files (when present) live on `files[]` with a download URL under `links`.
A record can be published and still have no downloadable file.

## Typical Workflow

1. Search with `q` and a `type` if the user said software, data, or poster.
2. Take `id` / `doi` from `hits.hits[]`.
3. `GET /api/records/{id}` with `-L` for files and the concept/version pair.
4. If they wanted a journal PDF, stop and use Unpaywall on the paper DOI
   instead of scraping a Zenodo landing page.

## Failure Modes

| What you did | What happens | What to do |
|---|---|---|
| Search without `type` | Software, data, and papers mixed | Filter `type=` or report the resource type |
| `GET /records/{conceptrecid}` without `-L` | HTTP 302 + HTML | Follow redirects; record both DOIs |
| Treated deposit docs as required auth | You ask the user for a token to *search* | Search is public |
| Cited `10.5281/zenodo.{concept}` as the file you downloaded | Concept DOI is all versions | Use the version DOI in provenance |

## Official sources reviewed 2026-09-30

- https://developers.zenodo.org/
