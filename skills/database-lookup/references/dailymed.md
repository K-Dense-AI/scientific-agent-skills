# DailyMed (NIH/NLM Drug Labels)

## Base URL
```
https://dailymed.nlm.nih.gov/dailymed/services/
```

## Auth
No API key required.

## Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `v2/spls.json?drug_name={name}` | Search drug labels by name |
| `v2/spls/{setid}.json` | Get label metadata by SetID |
| `v2/spls/{setid}/ndcs.json` | NDC codes for a label |
| `v2/spls/{setid}/media.json` | Images/media for a label |
| `v2/drugnames.json?drug_name={prefix}` | Drug name autocomplete |
| `v2/drugclasses.json?drug_class_name={name}` | Search by pharmacologic class |
| `v2/rxcuis.json?drug_name={name}` | RxNorm CUIs for a drug |
| `v2/ndc/{ndc_code}/spls.json` | Find labels by NDC code |

## Additional filters for `/v2/spls.json`
- `drug_class` — pharmacologic class
- `labeler` — manufacturer name
- `page` / `pagesize` — pagination (max 100)

## Example Calls

```
# Search metformin labels
https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json?drug_name=metformin

# Drug name autocomplete
https://dailymed.nlm.nih.gov/dailymed/services/v2/drugnames.json?drug_name=ator

# Search by pharmacologic class
https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json?drug_class=HMG-CoA+Reductase+Inhibitor

# Full label XML (SPL content with sections)
https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/{setid}/packaging.xml
```

## Response Format
```json
{
  "metadata": {
    "total_elements": 12,
    "elements_per_page": 10,
    "current_page": 1,
    "total_pages": 2
  },
  "data": [
    {
      "published_date": "2024-01-15",
      "title": "METFORMIN HYDROCHLORIDE tablet",
      "setid": "b03f295f-..."
    }
  ]
}
```

## Rate Limits
No published limits. Be reasonable.
