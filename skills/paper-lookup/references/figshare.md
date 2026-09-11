# Figshare

A general research repository (figures, datasets, posters, papers, media).
Use it when the user names Figshare or a `figshare.com` DOI, or wants files
deposited there. It is not a journal index. For OA journal PDFs use Unpaywall;
for EBI-hosted study packages use BioStudies; for CERN-style software dumps
prefer Zenodo.

All figures below verified 2026-09-10.

## Base URL

```
https://api.figshare.com/v2
```

Docs: https://docs.figshare.com/v2/

## Authentication

Public article metadata does not need a token. Private records, uploads, and
account endpoints do (`Authorization: token ACCESS_TOKEN`). This skill only
uses the public routes.

## Rate Limits

Documented on the API site; stay well under interactive use. Serialize.

## Key Endpoints

### 1. Search — POST, not GET

```
POST /v2/articles/search
Content-Type: application/json

{"search_for": "CRISPR", "page": 1, "page_size": 10}
```

Verified: HTTP 200, a **bare JSON array** (no `total`, no `hits` wrapper).
First hit was a CRISPR supplementary dataset (`defined_type_name: dataset`).

There is no count in the body and no useful `Link`/`X-Count` header on this
call. Walk `page` until a page comes back shorter than `page_size` or empty.
Do not invent a total.

**GET is not a search.** This is the trap that produces a confident wrong
paper:

```
GET /v2/articles?search_for=CRISPR&page_size=1
```

Verified: HTTP 200, one article, title *Social capital in the workplace…*,
DOI `10.1016/j.labeco.2007.07.006`. The query string is ignored; you are
listing articles. If the user asked for CRISPR and you used GET, you will
report the wrong object with a 200.

### 2. One article

```
GET /v2/articles/{id}
```

```
GET /v2/articles/12345
```

Verified: HTTP 200 with `id`, `title`, `doi`, `defined_type_name`, `url`,
authors, files, license. Use this after search, or when the user already
has a Figshare id.

Files, when public, appear on the article object. A 404 is either no such
id or a record you are not allowed to read (the API uses 404 for both).

## Typical Workflow

1. `POST /articles/search` with a JSON body.
2. Read `id`, `title`, `doi`, `defined_type_name` from each element.
3. `GET /articles/{id}` only if you need files or a fuller record.
4. If they wanted papers *about* a topic, go to OpenAlex / PubMed. Figshare
   search is repository search.

## Failure Modes

| What you did | What happens | What to do |
|---|---|---|
| `GET /articles?search_for=…` | HTTP 200, unrelated latest-ish articles | POST `/articles/search` |
| Expected `{hits: …, total: N}` | A raw array | Treat `[]` as empty; no total to reconcile |
| Reported a Figshare hit as a journal article | `defined_type_name` may be dataset, figure, media | Read and report the type |
