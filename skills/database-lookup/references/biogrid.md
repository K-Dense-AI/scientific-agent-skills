# BioGRID API Reference

## Base URL
```
https://webservice.thebiogrid.org/interactions
```

## Authentication
**API key REQUIRED.** Register free at https://webservice.thebiogrid.org/ to obtain an access key.
- Pass as query parameter: `?accesskey=YOUR_ACCESS_KEY`

## Rate Limits
Not formally published. Reasonable usage expected.

## Response Format
JSON (with `&format=json`), tab-delimited (`&format=tab2`), or XML. Default is tab2.

## Key Endpoints

### 1. Search Interactions by Gene
```
GET https://webservice.thebiogrid.org/interactions?accesskey={key}&format=json&searchNames=true&geneList={gene_symbol}&taxId={taxon_id}
```
Example — get TP53 interactions in human:
```
GET https://webservice.thebiogrid.org/interactions?accesskey=YOUR_KEY&format=json&searchNames=true&geneList=TP53&taxId=9606&max=50
```

### 2. Multiple Genes
```
GET https://webservice.thebiogrid.org/interactions?accesskey={key}&format=json&searchNames=true&geneList=BRCA1|BRCA2&taxId=9606&max=100
```
Separate gene names with `|` (pipe).

### 3. Filter by experimental evidence
```
GET https://webservice.thebiogrid.org/interactions?accesskey={key}&format=json&searchNames=true&geneList=TP53&taxId=9606&evidenceList=Two-hybrid&includeEvidence=true&max=50
```
`evidenceList` is a pipe-separated list of experimental systems, not the words
`physical` or `genetic`. Without `includeEvidence=true`, listed systems are
**excluded**. Discover names through `/evidence?accesskey={key}&format=json`.
To select the broad physical/genetic class, filter returned
`EXPERIMENTAL_SYSTEM_TYPE` locally. There is no documented
`experimentalSystemList` query parameter.

### 5. Search by BioGRID Interaction ID
```
GET https://webservice.thebiogrid.org/interactions/{interaction_id}?accesskey={key}&format=json
```

### 6. Search by PubMed ID
```
GET https://webservice.thebiogrid.org/interactions?accesskey={key}&format=json&pubmedList=12345678
```

### 7. Inter-species Interactions
```
GET https://webservice.thebiogrid.org/interactions?accesskey={key}&format=json&searchNames=true&geneList=TP53&taxId=9606&interSpeciesExcluded=false
```

### 8. Include Interactor Annotations
```
GET https://webservice.thebiogrid.org/interactions?accesskey={key}&format=json&searchNames=true&geneList=TP53&taxId=9606&includeInteractors=true&max=50
```

## Common Query Parameters
| Parameter | Description |
|-----------|-------------|
| `geneList` | Gene symbol(s), pipe-separated |
| `taxId` | NCBI taxonomy ID (9606=human, 10090=mouse, 559292=yeast) |
| `max` | Max results to return (default 10000) |
| `start` | Offset for pagination |
| `format` | `json`, `tab2`, `extendedTab2`, `count` |
| `searchNames` | `true` to match official symbols |
| `selfInteractionsExcluded` | `true` to exclude self-interactions |
| `evidenceList` | Experimental-system names; set `includeEvidence=true` to include |
| `throughputTag` | `low` or `high` |

## JSON Response Structure
```json
{
  "12345": {
    "BIOGRID_INTERACTION_ID": 12345,
    "ENTREZ_GENE_A": "7157",
    "ENTREZ_GENE_B": "672",
    "OFFICIAL_SYMBOL_A": "TP53",
    "OFFICIAL_SYMBOL_B": "BRCA1",
    "EXPERIMENTAL_SYSTEM": "Two-hybrid",
    "EXPERIMENTAL_SYSTEM_TYPE": "physical",
    "PUBMED_ID": "9482880",
    "ORGANISM_A": 9606,
    "ORGANISM_B": 9606,
    "THROUGHPUT": "Low Throughput",
    "SCORE": "-"
  }
}
```

## Count-Only Query
```
GET https://webservice.thebiogrid.org/interactions?accesskey={key}&format=count&searchNames=true&geneList=TP53&taxId=9606
```
Returns just the integer count.

## Notes
- BioGRID aggregates curated interaction data from literature.
- Covers physical (protein-protein) and genetic interactions.
- For bulk data, use BioGRID downloads (tab-delimited files) at https://downloads.thebiogrid.org/.
- Cross-reference with STRING for combined interaction evidence.

Official contract: https://wiki.thebiogrid.org/doku.php/biogridrest
