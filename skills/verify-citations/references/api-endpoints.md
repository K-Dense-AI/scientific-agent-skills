# Provider API endpoints

All providers used by verify-citations are keyless. Optional contact
configuration joins the "polite pools" and raises rate limits considerably.

## Configuration

```bash
export CROSSREF_EMAIL=you@example.com    # Crossref + OpenAlex polite pool
export OPENALEX_EMAIL=you@example.com    # same pool, checked independently
```

The scripts read these (or `VERIFY_CITATIONS_EMAIL`) and append
`mailto:` to the User-Agent (Crossref convention) / `mailto` param
(OpenAlex, E-utilities).

## Crossref

- Resolve by DOI: `GET https://api.crossref.org/works/{doi}`
- Bibliographic search: `GET https://api.crossref.org/works?query.bibliographic=<title>&rows=3&select=title,author,issued,container-title,DOI,type`
- Retraction metadata: the work message's `update-to` / `updated-by` arrays
  carry `{type, DOI}` pointing at the retraction notice; `type` containing
  `retract` or `withdraw` triggers the `retracted` verdict.
- Anonymous limit: ~50 req/s shared; polite pool is more generous and
  preferred. 404 means "DOI unknown" (used as a not-resolved signal, not an
  error).
- Titles arrive as lists; issued year lives at `issued.date-parts[0][0]`.

## arXiv

- Atom API: `GET http://export.arxiv.org/api/query?id_list=<id>&max_results=1`
- Accepts new-format (`2401.12345`, optional `v2`) and old-format
  (`cs/0112017`) identifiers.
- Response is XML (namespaced Atom); titles/authors/published year are read
  with `xml.etree`. A missing `<entry>` element means the ID is unknown.
- Limit: ~1 request / 3 seconds is the documented ceiling; the script's
  `--pause` default of 1s is fine for single-ID verification, raise it for
  bulk arXiv-only sweeps.

## PubMed E-utilities

- ESummary: `GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=<pmid>&retmode=json`
- PMIDs are extracted from references carrying `PMID:` markers.
- Limit: 3 req/s without an API key; `NCBI_API_KEY` is honoured by the
  paper-lookup skill but not required here.
- An unknown PMID comes back as a JSON `error` field inside `result`, not an
  HTTP error status.

## OpenAlex

- Fallback retraction check (and future enrichment):
  `GET https://api.openalex.org/works/doi:{doi}`
- `is_retracted` is the boolean of interest; also carries `is_paratext`
  (indexes/cover pages), useful for future filtering.
- Polite pool: add `?mailto=`. Anonymous: 10 req/s ceiling.
