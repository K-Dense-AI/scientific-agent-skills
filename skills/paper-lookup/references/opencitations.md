# OpenCitations

Open citation data (who cites whom) as open lists of citing/cited PIDs. Use it when you
need an openly licensed citation edge, a count you can cite, or an Open Citation
Identifier (OCI). It is not a paper search and it does not return titles on the Index
endpoints.

For a literature search use PubMed, OpenAlex, or Semantic Scholar. For a citation
*graph with titles and abstracts*, start with Semantic Scholar or OpenAlex and treat
OpenCitations as the open-data check. Europe PMC `/citations` is the biomedical
alternative when you already have a `{source}/{id}` pair.

All figures below verified 2026-09-10.

## Base URLs

```
https://api.opencitations.net/index/v2    # citation edges and counts
https://api.opencitations.net/meta/v1     # bibliographic metadata for a PID
```

Index v2 is current (v2.2.0, 2025-04-15). Meta lives at **v1** — `meta/v2/...`
is HTTP 404.

## Authentication

Optional. Public calls work without a token. For heavier use, request an access
token from OpenCitations and send `Authorization: <token>`. Do not add a new
`.env` key for this; proceed without one.

## Rate Limits

No published per-second cap. Serialize requests. Call `/citation-count` before
`/citations` — the list endpoint returns **every** incoming citation in one
body, with no page parameter.

## Identifier prefix (required)

Index v2 IDs must be `doi:`, `pmid:`, or `omid:`. A bare DOI is HTTP 400:

```
GET /index/v2/citation-count/10.1038/nature12373
  -> 400  the value '10.1038/nature12373' is not valid for parameter 'id'
          Example: /index/v2/citation-count/doi:10.1108/jd-12-2013-0166

GET /index/v2/citation-count/doi:10.1038/nature12373
  -> 200  [{"count": "1806"}]
```

## Key Endpoints

### 1. Incoming citation count

```
GET /index/v2/citation-count/{id}
```

Always a one-element JSON array. `count` is a **string**, not an integer.

| Query | HTTP | Body |
|---|---|---|
| `doi:10.1038/nature12373` | 200 | `[{"count": "1806"}]` |
| `pmid:23803767` | 200 | `[{"count": "94"}]` |
| `doi:10.9999/not-a-real-doi` | 200 | `[{"count": "0"}]` |

A missing work is HTTP 200 with `"0"`, not 404. Do not treat 200 as "this DOI
is in the index."

### 2. Outgoing reference count

```
GET /index/v2/reference-count/{id}
```

Same shape as citation-count.

### 3. Incoming citations / outgoing references

```
GET /index/v2/citations/{id}
GET /index/v2/references/{id}
```

Each item:

| Field | Meaning |
|---|---|
| `oci` | Open Citation Identifier (`citingOmidsuffix-citedOmidsuffix`) |
| `citing` / `cited` | Space-separated PIDs, each prefixed (`doi:`, `pmid:`, `omid:`, `openalex:`) |
| `creation` | ISO date of the citing work |
| `timespan` | XSD duration (`P6Y0M1D`) between cited and citing publication |
| `journal_sc` / `author_sc` | `"yes"` / `"no"` self-citation flags |

Verified on `doi:10.1038/nature12373` `/references`: 30 rows. First `citing` is
`omid:br/06120344846 doi:10.1038/nature12373 openalex:W2159974629 pmid:23903748`.
Parse the `doi:` token out; do not take the whole string as one DOI.

Verified on `doi:10.1186/1756-8722-6-59` `/citations`: 217 rows in one response.
For `nature12373` the count is 1806 — do not pull that list unless the user
asked for the full set.

### 4. One citation by OCI

```
GET /index/v2/citation/{oci}
```

`oci` is the two-number form without an `oci:` prefix.

### 5. Metadata (titles, authors)

```
GET /meta/v1/metadata/{id}
```

Same `doi:` / `pmid:` / `omid:` prefix. Returns `id` (space-separated PIDs),
`title`, `author` (semicolon-separated, may include ORCID + OMID). Use this
when you have an edge from Index and need a human-readable label.

## Typical Workflow

1. You have a DOI or PMID.
2. `citation-count` first. If `"0"`, say OpenCitations has no incoming citations
   — not that the paper is uncited everywhere.
3. For a short list, `/references` or `/citations`. Extract the `doi:` token
   from each `citing`/`cited` string.
4. Resolve titles with Meta, Crossref, or Semantic Scholar. Do not invent them
   from the OCI.

## Failure Modes

| What you did | What happens | What to do |
|---|---|---|
| Bare DOI, no `doi:` prefix | HTTP 400 | Prefix the scheme |
| Unknown DOI | HTTP 200, `count: "0"` | Report a gap; try Semantic Scholar |
| Parsed `citing` as one DOI | You store `omid:br/… doi:10.… pmid:…` | Split on spaces; keep the `doi:` value |
| `/citations` on a highly cited work | Multi-megabyte JSON, no pagination | Count first; bound the pull |
| `meta/v2/...` | HTTP 404 HTML | Use `meta/v1` |
