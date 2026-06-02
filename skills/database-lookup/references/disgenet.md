# DisGeNET (Gene-Disease Associations)

## Base URL
```
https://www.disgenet.org/api
```

## Auth
**API key required.** Register at disgenet.org, then authenticate:
```bash
curl -X POST https://www.disgenet.org/api/auth/ \
  -d 'email=you@example.com&password=yourpassword'
# Returns: {"token": "abc123..."}
```
Pass as: `Authorization: Bearer <token>`

Load token from `.env` as `DISGENET_API_KEY`.

## Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `/gda/gene/{gene_id}` | Gene-disease associations (NCBI gene ID) |
| `/gda/disease/{disease_id}` | Gene-disease associations (UMLS CUI) |
| `/gda/evidences/gene/{gene_id}` | Evidence-level data |
| `/vda/gene/{gene_id}` | Variant-disease associations for a gene |
| `/vda/variant/{rsid}` | Variant-disease associations (dbSNP rsID) |

## Parameters
- `source` — `CURATED`, `BEFREE`, `ALL`
- `min_score` — GDA score threshold (0-1)
- `min_ei` — evidence index threshold
- `format` — `json` or `tsv`
- `limit`, `offset` — pagination

## Example Calls
```
# Gene-disease for TP53 (gene ID 7157)
/gda/gene/7157?source=CURATED&min_score=0.3&limit=10&format=json

# Disease-gene for Breast Cancer (UMLS CUI C0006142)
/gda/disease/C0006142?limit=10

# Variant-disease for rs1042522
/vda/variant/rs1042522
```

## Rate Limits
Free academic tier: ~few hundred requests/day. Paid tiers available.

## Free alternative
If no API key: use **Open Targets** for disease-gene associations.
