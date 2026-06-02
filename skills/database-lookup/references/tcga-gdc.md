# TCGA / GDC Data Portal API

## Base URL
```
https://api.gdc.cancer.gov
```

## Auth
No auth for public data. Token needed only for controlled-access downloads.

## Key Endpoints

All search endpoints accept GET or POST (POST preferred for complex filters).

| Endpoint | Description |
|----------|-------------|
| `/projects` | List/filter cancer projects (e.g. TCGA-BRCA) |
| `/cases` | Search cases (patients/samples) |
| `/files` | Search/filter files (BAM, VCF, expression) |
| `/genes` | Search gene-level data |
| `/ssms` | Search simple somatic mutations |
| `/ssm_occurrences` | Mutation occurrences across cases |
| `/files/{uuid}` | File metadata by UUID |
| `/data/{uuid}` | Download file by UUID |

## Filter Syntax (POST body)
```json
{
  "filters": {
    "op": "in",
    "content": {"field": "cases.project.project_id", "value": ["TCGA-BRCA"]}
  },
  "fields": "file_id,file_name,data_type",
  "format": "JSON",
  "size": 10
}
```
Operators: `in`, `=`, `!=`, `>`, `<`, `>=`, `<=`, `is`, `not`, `and`, `or`

## Example Calls
```
# List projects
https://api.gdc.cancer.gov/projects?size=5&fields=project_id,name,primary_site

# BRCA1 mutations (POST)
curl -X POST https://api.gdc.cancer.gov/ssms \
  -H "Content-Type: application/json" \
  -d '{"filters":{"op":"in","content":{"field":"consequence.transcript.gene.symbol","value":["BRCA1"]}},"fields":"ssm_id,genomic_dna_change","size":5}'

# Cases in TCGA-LUAD
https://api.gdc.cancer.gov/cases?filters=%7B%22op%22%3A%22in%22%2C%22content%22%3A%7B%22field%22%3A%22project.project_id%22%2C%22value%22%3A%5B%22TCGA-LUAD%22%5D%7D%7D&size=3&fields=submitter_id,disease_type
```

## Pagination
`from` (offset) and `size` (limit, max 10000). Default size is 10.

## Rate Limits
No strict limit for metadata queries. Use GDC Transfer Tool for bulk file downloads.
