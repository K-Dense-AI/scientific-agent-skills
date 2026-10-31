# Citation API contracts

Reviewed 2026-09-30 against official documentation. The bundled clients use
read-only requests; no registration, account mutation, or full-text bulk
harvesting is part of this skill.

| Service | Request and authentication | Response and paging |
|---|---|---|
| OpenAlex | `GET https://api.openalex.org/works`; `search`, optional `filter` and `sort=cited_by_count:desc`; optional `Authorization: Bearer` from `OPENALEX_API_KEY`. Keyless casual use is supported. `mailto` is a contact identifier, not a quota upgrade. | `results[]` and `meta.next_cursor`. Start `cursor=*`, follow returned cursors; supported `per_page` maximum is 100 (`per-page` is accepted). Stop at the requested limit or terminal cursor. Any failed page aborts the export. |
| PubMed search | `GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi`; `db=pubmed`, `term`, `retmax`, `retmode=json`, `tool`, optional `email` and `api_key`. | `esearchresult.count` and `idlist`. Only the first 10,000 matches are accessible; `retstart` cannot bypass this ceiling. The bundled command caps the request and reports that limit. |
| PubMed records | `GET .../efetch.fcgi`; `db=pubmed`, comma-separated `id`, `retmode=xml`, same caller parameters. | `PubmedArticleSet/PubmedArticle`; the client batches 200 IDs and verifies that all requested IDs were parsed. PubmedBookArticle is not implemented and produces an explicit incomplete-retrieval failure. |
| PMC conversion | `GET https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/`; `ids`, `format=json`, `tool`, optional `email`. No NCBI API key is sent here. | `records[]` maps PMID/PMCID/DOI only for PMC-held articles. `pmid` may be numeric. This helper sends one ID; the service accepts 200 same-type IDs per request, without paging. The ID converter remains distinct from the retired OA download service. |
| Crossref | `GET https://api.crossref.org/works/{encoded-doi}`; public metadata needs no key. | Singleton JSON `message`; author/title/container/date fields can be incomplete. Extract the publication date, not `created`, `deposited`, or `indexed`. No pagination. Public single-record limit is 5/s; list requests are 1/s. Polite equivalents are 10/s and 3/s; respect response headers. |
| DataCite | `GET https://api.datacite.org/dois/{encoded-doi}`; public findable records need no credentials. | Singleton `data.id` and `data.attributes`, not Crossref's schema. Used by the DOI validator after Crossref 404. The general metadata extractor currently has no DataCite mapper; use DOI-to-BibTeX conversion instead. |
| DOI negotiation | `GET https://doi.org/{encoded-doi}` with `Accept: application/x-bibtex`; redirects are followed to the registration agency. No key. | One BibTeX record; the converter rejects non-BibTeX responses and generates its shared citation key. No pagination. Supports participating agencies beyond Crossref. |
| DOI resolver validation | Same DOI URL, GET without following redirects after both Crossref and DataCite lack a record. | A redirect with a Location confirms registration; 404 indicates missing DOI. Timeouts, throttling, malformed responses, or other statuses remain inconclusive warnings, never a successful verification. Publisher accessibility and bibliographic identity still need manual review. |
| arXiv | `GET https://export.arxiv.org/api/query`; `id_list`, `max_results=1`; no key. One connection, at most one request per three seconds across all workers. | Atom feed with optional DOI/journal reference. Reject API error entries; preserve requested `vN` versions. Single-ID lookup has no paging. A DOI alone does not prove journal publication. |

PubMed's ESummary (`esummary.fcgi`, `retmode=json`) returns `result.uids` and
UID-keyed records. ELink (`elink.fcgi`, `cmd=neighbor`) returns link sets;
`pubmed_pmc` requires target `db=pmc`, whereas related/cited-in PubMed links use
`db=pubmed`. EInfo (`einfo.fcgi`) describes database fields and links. These
manual alternatives in the PubMed reference are illustrative, not used by the
bundled client. NCBI E-utilities limits are 3 requests/s without a key or 10/s
with a key; account for other processes sharing the same IP/key.

Google Scholar has no supported bulk API. `scholarly.search_pubs` is an unofficial
iterator with `year_low`/`year_high`; `--sort-by citations` only sorts the returned
sample. Google caps displayed results at 1,000 per query. Follow robots.txt and
stop on blocking. Proxy support is optional and was not exercised.

## Verification evidence and limits

Credential-free read-only smoke checks on 2026-09-30 returned HTTP 200 and the
expected parsed shapes for PMC conversion (PMC7611378 returned numeric PMID
27102758), ESearch/EFetch (PMID 34265844), Crossref and DOI BibTeX negotiation
(10.1038/s41586-021-03819-2), DataCite (10.14454/qdd3-ps68), arXiv
(1706.03762 returned the v7 Atom entry), and OpenAlex (one work plus cursor).
These checks confirm those responses at that time, not uptime or bulk coverage.

Regression tests mock pagination failures, missing PubMed batches, arXiv error
feeds/pacing, DOI transport failures, numeric PMC IDs, and CLI input contracts.
Authenticated quota handling, Scholar/proxies, arbitrary publisher-page metadata,
Zotero exports, and all illustrative search queries were not exercised live.

## Official sources

- [OpenAlex authentication](https://help.openalex.org/api/authentication/), [pagination](https://help.openalex.org/api/paging/), and [search](https://help.openalex.org/api/searching/).
- [NCBI E-utilities reference](https://www.ncbi.nlm.nih.gov/books/NBK25499/), [NLM API parameter guide](https://www.nlm.nih.gov/dataguide/eutilities/utilities.html), and [PubMed result-window change](https://ncbiinsights.ncbi.nlm.nih.gov/2021/10/05/updated-pubmed-api/).
- [PMC ID Converter API](https://pmc.ncbi.nlm.nih.gov/tools/id-converter-api/).
- [Crossref REST API](https://github.com/CrossRef/rest-api-doc), [current rate-limit distinction](https://community.crossref.org/t/refining-rest-api-limits-for-improved-stability-and-reliability/16137), and [content negotiation](https://www.crossref.org/documentation/retrieve-metadata/content-negotiation/).
- [DataCite public API](https://support.datacite.org/docs/rest-api) and [singleton schema](https://support.datacite.org/docs/api-get-doi).
- [arXiv API manual](https://info.arxiv.org/help/api/user-manual.html) and [usage limits](https://info.arxiv.org/help/api/tou.html).
- [Google Scholar Help](https://scholar.google.com/intl/en/scholar/help.html) and [scholarly API](https://scholarly.readthedocs.io/en/stable/scholarly_user.html).
- [Pyzotero export types and pagination](https://pyzotero.readthedocs.io/en/latest/).
