# OpenFDA API

## Base URL
```
https://api.fda.gov
```

## Auth
Optional free API key (40 req/min without, 240 req/min with). Register at https://open.fda.gov/apis/authentication/
Pass as: `?api_key=YOUR_KEY`

## Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `/drug/event.json` | Drug adverse events (FAERS) |
| `/drug/label.json` | Drug product labeling (SPL) |
| `/drug/ndc.json` | NDC directory |
| `/drug/drugsfda.json` | Drugs@FDA (approvals) |
| `/drug/enforcement.json` | Drug recalls |
| `/device/event.json` | Device adverse events |
| `/device/510k.json` | 510(k) clearances |
| `/food/event.json` | Food adverse events |
| `/food/enforcement.json` | Food enforcement |

## Query Parameters

- `search` — query using OpenFDA syntax
- `count` — count unique values for a field
- `limit` — results per request (max 1000)
- `skip` — pagination offset (max 25000)

### Search Syntax
- Field search: `field:"value"`
- AND: `field1:value1+AND+field2:value2`
- OR: `field1:value1+OR+field2:value2`
- Date range: `field:[20230101+TO+20231231]`
- Wildcards: `field:aspir*`
- OpenFDA harmonized fields use `openfda.` prefix

## Example Calls

```
# Adverse events for aspirin
/drug/event.json?search=patient.drug.openfda.brand_name:"aspirin"&limit=5

# Top adverse reactions for a drug
/drug/event.json?search=patient.drug.openfda.generic_name:"metformin"&count=patient.reaction.reactionmeddrapt.exact

# Drug labels by generic name
/drug/label.json?search=openfda.generic_name:"ibuprofen"&limit=3

# Drug recalls in date range
/drug/enforcement.json?search=report_date:[20230101+TO+20231231]&limit=10

# Serious adverse events only
/drug/event.json?search=patient.drug.openfda.brand_name:"warfarin"+AND+serious:1&limit=10
```

## Rate Limits
| Tier | Requests/min | Requests/day |
|------|-------------|-------------|
| No API key | 40 | 1,000 |
| With API key (free) | 240 | 120,000 |
