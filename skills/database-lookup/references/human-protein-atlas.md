# Human Protein Atlas (HPA)

## Base URL
```
https://www.proteinatlas.org
```

## Auth
No API key required.

## Key Endpoints

| Purpose | URL Pattern |
|---|---|
| Gene data by Ensembl ID | `/{ENSEMBL_ID}.json` |
| Gene data by symbol | `/{GENE_NAME}.json` |
| Search (JSON) | `/search/{QUERY}?format=json` |
| Search (XML) | `/search/{QUERY}?format=xml` |

## Example Calls

```
# Gene data by Ensembl ID
https://www.proteinatlas.org/ENSG00000141510.json

# Gene data by symbol
https://www.proteinatlas.org/TP53.json

# Search
https://www.proteinatlas.org/search/TP53?format=json
```

## Response Format (JSON, gene endpoint)
```json
{
  "Gene": "TP53",
  "Gene synonym": ["p53", "LFS1"],
  "Ensembl": "ENSG00000141510",
  "Gene description": "tumor protein p53",
  "Uniprot": ["P04637"],
  "Chromosome": "17",
  "Protein class": ["Transcription factors"],
  "RNA tissue specificity": "Low tissue specificity",
  "Subcellular location": ["Nucleoplasm"],
  "Pathology prognostics": [...]
}
```

## Bulk Downloads
For large-scale work, use TSV files from https://www.proteinatlas.org/about/download:
- `normal_tissue.tsv` — IHC tissue expression
- `rna_tissue_consensus.tsv` — RNA consensus
- `subcellular_location.tsv`
- `pathology.tsv` — cancer prognostics

## Rate Limits
No published limits. Be reasonable. Prefer bulk downloads for large queries.
