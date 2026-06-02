# RummaGEO (GEO Gene Set Enrichment Search)

## Base URL
```
https://rummageo.com/
```

## Auth
No auth required.

## Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/enrich` | POST | Submit gene set for enrichment against GEO signatures |
| `/api/table` | GET | Paginated table of indexed GEO signatures |

## Example Call
```bash
curl -X POST "https://rummageo.com/api/enrich" \
  -H "Content-Type: application/json" \
  -d '{"genes": ["BRCA1","TP53","EGFR","MYC","PTEN"]}'
```

## Response Format
JSON. Ranked list of matching GEO signatures with overlap stats, p-values, source study links.

## Note
POST endpoint — use `curl` via shell, not WebFetch.

## Rate Limits
No published limits. Designed for interactive/programmatic use.
