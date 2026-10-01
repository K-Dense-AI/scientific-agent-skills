# USPTO Public APIs

## 1. PatentsView → Open Data Portal (ODP)

**Status (checked 2026-08-30):** The PatentsView PatentSearch API that lived at
`https://search.patentsview.org/api/v1/` is **unavailable**. The host no longer
resolves (NXDOMAIN). USPTO migrated PatentsView onto the Open Data Portal on
2026-03-20; PatentSearch and related interactive features are paused with no
published relaunch date. Do **not** call `search.patentsview.org`, do **not**
register at the old `patentsview.org/apis/keyrequest` flow, and do **not** treat
legacy `api.patentsview.org` query URLs as live search endpoints (they redirect
to the transition guide).

### Current access path

Use ODP for PatentsView **bulk datasets** and data dictionaries:

- Transition guide: https://data.uspto.gov/support/transition-guide/patentsview
- PatentsView program page: https://www.uspto.gov/ip-policy/economic-research/patentsview
- ODP home / bulk directory: https://data.uspto.gov/

| Category | Example tables | ODP bulk dataset page |
|---|---|---|
| Granted patents — baseline / disambiguated | `g_patent`, `g_cpc_current`, `g_assignee_disambiguated` | https://data.uspto.gov/bulkdata/datasets/pvgpatdis |
| Granted patents — long text | `g_brf_sum_text_*`, `g_claims_*`, `g_detail_desc_text_*` | https://data.uspto.gov/bulkdata/datasets/pvgpattxt |
| Pre-grant publications — baseline / disambiguated | `pg_published_application`, `pg_cpc_current` | https://data.uspto.gov/bulkdata/datasets/pvpgpubdis |
| Pre-grant publications — long text | `pg_brf_sum_text_*`, `pg_claims_*` | https://data.uspto.gov/bulkdata/datasets/pvpgpubtxt |
| Sorted (beta) | `g_sorted_applicant`, `pg_sorted_individual` | https://data.uspto.gov/bulkdata/datasets/pvsorted |
| Annualized | yearly CSV tables | https://data.uspto.gov/bulkdata/datasets/pvannual |

Data dictionaries (when published) are linked from the “Documents and Resources”
sidebar on each ODP dataset page above.

### Auth for ODP bulk / API access

ODP access requires a USPTO.gov account (MFA). Obtain an **ODP** API key from
https://data.uspto.gov/apikey — previously issued PatentsView PatentSearch keys
are **not** compatible. Prefer loading the key from `.env` as `USPTO_ODP_API_KEY`
and sending it with the header ODP documents for its Bulk Datasets API
(commonly `X-API-KEY`). Never print the key in provenance.

If the user needs interactive keyword / inventor / assignee **search** rather
than bulk tables, say clearly that PatentSearch is paused during the ODP
transition and point them at the transition guide — do not invent a replacement
search URL.

### Historical note

- Legacy PatentsView REST host `api.patentsview.org` is decommissioned for search;
  requests redirect to the ODP transition guide.
- The Elasticsearch PatentSearch base URL `https://search.patentsview.org/api/v1/`
  must not be used until USPTO republishes an ODP-hosted replacement.

## 2. Patent File Wrapper (replacement for PEDS)

PEDS has migrated to ODP. Use the current
[transition guide](https://data.uspto.gov/support/transition-guide/peds) and
[Patent File Wrapper search documentation](https://data.uspto.gov/apis/patent-file-wrapper/search).
The search endpoint is `https://api.uspto.gov/api/v1/patent/applications/search`;
obtain an ODP API key and use the current documented request schema. This is a
patent-application/file-wrapper service, distinct from the paused PatentsView
PatentSearch API. The former unauthenticated `ped.uspto.gov/api/queries` recipe
is not a current integration. ODP's stated coverage begins in 2001, unlike PEDS.
Authenticated calls were not executed in this review.

## 3. TSDR — Trademark Status & Document Retrieval

Use TSDR by application serial or registration number. The official
[TSDR FAQ](https://tsdr.uspto.gov/faqview) now shows the API host
`https://tsdrapi.uspto.gov`, for example
`/ts/cd/casestatus/sn78787878/content.html` for an HTML status report.

TSDR API access is key-based, with a documented 60 requests/minute per key and
4 PDF/ZIP downloads/minute per key. Obtain the current key/header instructions
from USPTO's ODP documentation before automating; the older Developer Hub links
redirected during this review. The former no-key `/documentxml/status/...`
recipe has been removed. Do not assume that the example HTML URL returns XML.

## 4. Limitations

- Use current USPTO Trademark Search for interactive trademark searching; TESS is retired.
- **PatentsView PatentSearch API is paused** during the ODP migration; use ODP
  bulk datasets for PatentsView tables until USPTO republishes search APIs
- PEDS has migrated to ODP Patent File Wrapper; authentication and coverage differ.
- TSDR requires knowing the serial/registration number already
