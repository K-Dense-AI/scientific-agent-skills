# LINCS L1000 (Clue.io) API Reference

## Overview
The LINCS L1000 dataset is accessible via the **Connectivity Map (CMap) API** at clue.io.

## Base URL
```
https://api.clue.io/api
```

## Authentication
- **API key required** (free registration at clue.io)
- Pass via header: `user_key: YOUR_API_KEY`

## Key Endpoints

| Endpoint | Description |
|---|---|
| `GET /perts` | Query perturbagens (compounds, gene knockdowns, overexpression) |
| `GET /genes` | Query genes (L1000 landmark + inferred) |
| `GET /cells` | Query cell lines used in L1000 |
| `GET /sigs` | Query connectivity signatures |
| `GET /profiles` | Access expression profiles (level 5 z-scores) |
| `GET /pcls` | Perturbagen classes |

## Query Parameters
All endpoints support a `filter` parameter using Loopback-style JSON:
- `where` — filter conditions
- `fields` — select specific fields
- `limit` / `skip` — pagination

## Example Calls

```bash
# Search for a compound perturbagen by name
curl -H "user_key: YOUR_API_KEY" \
  "https://api.clue.io/api/perts?filter={\"where\":{\"pert_iname\":\"vorinostat\"}}"

# Get landmark genes
curl -H "user_key: YOUR_API_KEY" \
  "https://api.clue.io/api/genes?filter={\"where\":{\"is_lm\":true},\"limit\":10}"

# Query cell lines
curl -H "user_key: YOUR_API_KEY" \
  "https://api.clue.io/api/cells?filter={\"where\":{\"cell_iname\":\"MCF7\"}}"

# Get connectivity signatures for a compound
curl -H "user_key: YOUR_API_KEY" \
  "https://api.clue.io/api/sigs?filter={\"where\":{\"pert_iname\":\"vorinostat\"},\"limit\":5}"
```

## Response Format
JSON. Example (perturbagen):
```json
[
  {
    "pert_id": "BRD-K81418486",
    "pert_iname": "vorinostat",
    "pert_type": "trt_cp",
    "moa": ["HDAC inhibitor"],
    "target": ["HDAC1","HDAC2","HDAC3","HDAC6"]
  }
]
```

## Rate Limits
- Free tier: moderate rate limiting (exact numbers not publicly documented)
- Bulk data downloads available separately via clue.io data portal
