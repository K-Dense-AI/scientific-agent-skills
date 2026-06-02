# Addgene (Plasmid Repository)

## Base URL
```
https://www.addgene.org/api/
```

## Auth
API key required. Register at addgene.org and request API access.
Pass as: `Authorization: Token <your_api_key>`

Load from `.env` as `ADDGENE_API_KEY`.

## Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `/plasmids/{addgene_id}/` | Get plasmid details by ID |
| `/plasmids/search/?q={query}` | Search plasmids by keyword |
| `/depositors/{id}/` | Depositor information |
| `/articles/{id}/` | Associated publications |

## Example Calls
```
# Get plasmid details (e.g., pSpCas9)
GET https://www.addgene.org/api/plasmids/12260/
Authorization: Token YOUR_KEY

# Search plasmids
GET https://www.addgene.org/api/plasmids/search/?q=GFP
Authorization: Token YOUR_KEY
```

## Response Format
JSON with plasmid name, backbone, inserts, resistance markers, depositor, sequences, publications.

## Rate Limits
No published limits. Reasonable use expected.
