# ClinicalTrials.gov (v2 API)

## Base URL
```
https://clinicaltrials.gov/api/v2/
```

## Auth
No API key required. Fully public.

## Key Endpoints

### API version and data freshness
```
GET /version
```

Check `dataTimestamp` before time-sensitive retrievals to confirm the daily refresh has completed. ClinicalTrials.gov notes that data is generally refreshed Monday through Friday by 9 a.m. ET / 14:00 UTC.

ClinicalTrials.gov modernized its data ingest on August 26, 2025. For reproducible comparisons against older exports, note that some rich text markup fields and location/geopoint data may differ from the legacy pipeline.

### Search studies
```
GET /studies
```

Key parameters:
- `query.cond` — condition/disease (e.g. `breast cancer`)
- `query.intr` — intervention/treatment (e.g. `pembrolizumab`)
- `query.term` — general search terms
- `query.spons` — sponsor
- `query.id` — NCT ID
- `filter.overallStatus` — pipe-delimited: `RECRUITING|COMPLETED|ACTIVE_NOT_RECRUITING|...`
- `filter.phase` — `PHASE1|PHASE2|PHASE3|PHASE4|NA`
- `filter.geo` — `distance(lat,lon,dist)` e.g. `distance(38.89,-77.03,50mi)`
- `fields` — comma-separated field list to reduce payload
- `sort` — e.g. `LastUpdatePostDate:desc`
- `pageSize` — results per page (default 10, max 1000)
- `pageToken` — cursor for next page (from `nextPageToken` in response)
- `countTotal=true` — include total count

Example — recruiting Phase 3 breast cancer trials:
```
/studies?query.cond=breast+cancer&filter.overallStatus=RECRUITING&filter.phase=PHASE3&pageSize=5&countTotal=true
```

Response structure:
```json
{
  "totalCount": 1234,
  "studies": [
    {
      "protocolSection": {
        "identificationModule": {"nctId": "NCT05123456", "briefTitle": "..."},
        "statusModule": {"overallStatus": "RECRUITING"},
        "designModule": {"phases": ["PHASE3"], "enrollmentInfo": {"count": 500}},
        "conditionsModule": {"conditions": ["Breast Cancer"]},
        "eligibilityModule": {"minimumAge": "18 Years", "sex": "ALL"}
      }
    }
  ],
  "nextPageToken": "CAYQAg"
}
```

### Single study by NCT ID
```
GET /studies/{nctId}
```
Example: `/studies/NCT05123456`

### Study count
```
GET /stats/size?query.cond={condition}&filter.overallStatus=RECRUITING
```

### Field metadata
```
GET /studies/metadata
```

## Pagination
Uses cursor-based pagination via `pageToken` (NOT numeric offsets). Include `countTotal=true` on first request to get total.

## Rate Limits
No API key. Be reasonable — a few requests per second.

## Bulk download

Prefer the v2 `/studies` API with `pageToken` pagination for programmatic
retrieval. The former bulk URL `https://clinicaltrials.gov/AllAPIJSON.zip`
returns **404** and must not be used.

For a full-registry **XML** dump, use:

```
https://clinicaltrials.gov/AllPublicXML.zip
```

That path redirects to `https://clinicaltrials.gov/api/legacy/public-xml?format=zip`
and returns `Content-Type: application/zip` (`ctg-public-xml.zip`). Confirm the
redirect still yields a zip before large downloads; CSV / pipe-delimited export
options are documented under ClinicalTrials.gov Data API “Download” pages when
XML is not appropriate.
