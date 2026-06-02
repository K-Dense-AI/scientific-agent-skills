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
GET https://webservice.thebiogrid.org/interactions?accesskey={key}&format=json&geneList=BRCA1|BRCA2&taxId=9606&max=100
```
Separate gene names with `|` (pipe).

### 3. Filter by Evidence Type
```
GET https://webservice.thebiogrid.org/interactions?accesskey={key}&format=json&geneList=TP53&taxId=9606&evidenceList=physical&max=50
```
Evidence types: `physical`, `genetic`.

### 4. Filter by Experimental System
```
GET https://webservice.thebiogrid.org/interactions?accesskey={key}&format=json&geneList=TP53&taxId=9606&experimentalSystemList=Two-hybrid&max=50
```
Systems include: `Two-hybrid`, `Affinity Capture-MS`, `Co-fractionation`, `Reconstituted Complex`, `Synthetic Lethality`, `Dosage Rescue`, etc.

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
GET https://webservice.thebiogrid.org/interactions?accesskey={key}&format=json&geneList=TP53&taxId=9606&interSpeciesExcluded=false
```

### 8. Include Interactor Annotations
```
GET https://webservice.thebiogrid.org/interactions?accesskey={key}&format=json&geneList=TP53&taxId=9606&includeInteractors=true&max=50
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
| `evidenceList` | `physical` or `genetic` |
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
GET https://webservice.thebiogrid.org/interactions?accesskey={key}&format=count&geneList=TP53&taxId=9606
```
Returns just the integer count.

## Notes
- BioGRID aggregates curated interaction data from literature.
- Covers physical (protein-protein) and genetic interactions.
- For bulk data, use BioGRID downloads (tab-delimited files) at https://downloads.thebiogrid.org/.
- Cross-reference with STRING for combined interaction evidence.
