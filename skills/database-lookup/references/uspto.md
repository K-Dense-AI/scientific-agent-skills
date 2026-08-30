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

## 2. PEDS — Patent Examination Data System

**URL**: `https://ped.uspto.gov/api/queries`

**Method**: POST

For patent prosecution data (application status, filing dates, examiner info).

```json
{
  "searchText": "applicationNumberText:16123456",
  "fl": "*",
  "mm": "100%",
  "df": "patentTitle",
  "facet": "false",
  "sort": "applId asc",
  "start": 0
}
```

No API key required but heavily rate limited. Availability can be unreliable.

## 3. TSDR — Trademark Status & Document Retrieval

For trademark lookup by serial or registration number (not full-text search).

```
GET https://tsdr.uspto.gov/documentxml/status/{serial_number}
GET https://tsdr.uspto.gov/documentxml/status/rn{registration_number}
```

Returns XML with mark details, status, owner, goods/services, prosecution history.

No API key. Rate limited. No JSON endpoint — responses are XML.

## 4. Limitations

- **No public REST API for trademark full-text search** (TESS is web-only)
- **PatentsView PatentSearch API is paused** during the ODP migration; use ODP
  bulk datasets for PatentsView tables until USPTO republishes search APIs
- PEDS availability is inconsistent
- TSDR requires knowing the serial/registration number already
