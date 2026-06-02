# QuickGO (EBI GO Annotation Browser)

## Base URL
```
https://www.ebi.ac.uk/QuickGO/services/
```

## Auth
No auth required.

## Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `/ontology/go/terms/{goId}` | GO term details |
| `/ontology/go/terms/{goId}/children` | Child terms |
| `/ontology/go/terms/{goId}/ancestors` | Ancestor terms |
| `/ontology/go/search?query={term}` | Search GO terms by keyword |
| `/annotation/search` | Search annotations by gene/taxon/GO term |

## Annotation Search Parameters
- `goId` — GO term (e.g. GO:0003723)
- `taxonId` — NCBI taxonomy (e.g. 9606 for human)
- `geneProductId` — UniProt accession
- `evidence` — evidence code (e.g. ECO:0000269)
- `aspect` — biological_process, molecular_function, cellular_component
- `limit`, `page` — pagination

## Example Calls
```
# GO term details
https://www.ebi.ac.uk/QuickGO/services/ontology/go/terms/GO:0003723

# Human annotations for RNA binding
https://www.ebi.ac.uk/QuickGO/services/annotation/search?goId=GO:0003723&taxonId=9606&limit=10

# Search terms by keyword
https://www.ebi.ac.uk/QuickGO/services/ontology/go/search?query=apoptosis&limit=5
```

## Response Format
JSON. Annotations: paginated results with gene product, GO term, evidence, qualifier.

## Rate Limits
EBI fair-use policy. Use download endpoint for large result sets.
