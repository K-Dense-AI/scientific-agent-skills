# BioStudies

EMBL-EBI archive for the data outputs of a life-science study: files hosted
here, plus links out to ArrayExpress, BioImages, ENA, and other archives.
Use it when the user wants the *dataset behind a paper*, a BioStudies
accession (`S-BSST…`, `S-EPMC…`, `S-CMO…`, `E-MTAB…`), or "supplementary
data at EBI." It is not a paper index.

Find the paper in PubMed / Europe PMC, then come here with an accession or
a keyword that appears in the study record.

All figures below verified 2026-09-10.

## Base URL

```
https://www.ebi.ac.uk/biostudies/api/v1
```

## Authentication

None.

## Rate Limits

No published per-second cap. Serialize. EBI asks for reasonable use.

## Key Endpoints

### 1. Search studies

```
GET /search?query={text}&page={n}&pageSize={n}
```

```
GET /search?query=organoid&pageSize=2
```

Verified: HTTP 200 with

| Field | Value on this call | Meaning |
|---|---|---|
| `page` | 1 | 1-based |
| `pageSize` | 2 | |
| `totalHits` | 4195, then 4480 on a later call | **Approximate** |
| `isTotalHitsExact` | `false` | Do not reconcile as if this were Europe PMC `hitCount` |
| `nextCursor` | `null` | Page with `page=`, not a cursor |
| `hits` | 2 study summaries | |

A hit has `accession`, `type` (`study`), `title`, `author`, `files` (count),
`release_date`, `isPublic`, `content` (a flattened text blob). `author` may
be an empty string.

`totalHits` moved by hundreds between two calls a few seconds apart, and
`isTotalHitsExact` stayed false. Report "about N studies" and the page you
fetched. Do not claim a complete walk against that number.

Page 2 (`page=2&pageSize=2`) returned different accessions and still
`nextCursor: null`. Keep incrementing `page` until `hits` is empty.

### 2. One study

```
GET /studies/{accession}
```

```
GET /studies/S-CMO2844
```

Verified: HTTP 200. The body is **not** the search-hit shape:

```json
{
  "accno": "S-CMO2844",
  "type": "submission",
  "attributes": [{"name": "Title", …}, {"name": "ReleaseDate", …}],
  "section": { "type": "Study", "accno": "s1", "attributes": […], "subsections": […] }
}
```

Title lives in `attributes` (name `Title`), not `title`. Files and links
are nested under `section.subsections`. Walk that tree; do not expect
`files: [ …urls ]` at the top level.

A 404 means no such public accession.

## Typical Workflow

1. Search with a paper title, accession, or biological keyword.
2. Take `accession` from `hits[]`.
3. `GET /studies/{accession}` for the submission tree and file list.
4. Cite the accession and the BioStudies URL
   (`https://www.ebi.ac.uk/biostudies/studies/{accession}`).
5. If they wanted the paper, go back to PubMed / Europe PMC with the
   title or a DOI found in the study attributes.

## Failure Modes

| What you did | What happens | What to do |
|---|---|---|
| Treated `totalHits` as exact | Count drifts; `isTotalHitsExact` is false | Say "about N"; do not exit-4 reconcile |
| Expected search fields on `/studies/{acc}` | No `title`, no `files` count | Read `attributes` and `section` |
| Used BioStudies as PubMed | Studies, not articles | Search literature APIs first |
| Waited for `nextCursor` | It stays `null` | Use `page` |
