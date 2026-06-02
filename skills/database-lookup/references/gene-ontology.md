# Gene Ontology (GO) API Reference

## Base URLs
- **QuickGO (EBI, recommended)**: `https://www.ebi.ac.uk/QuickGO/services` — most reliable endpoint
- **GO API**: `https://api.geneontology.org/api` — may return 403; use QuickGO as fallback
- **AmiGO / GOlr (Solr-based)**: `http://golr-aux.geneontology.org/solr`

## Authentication
None required. All endpoints are public.

## Rate Limits
No published hard limits. QuickGO recommends reasonable usage.

---

## GO API (api.geneontology.org)

### 1. GO Term Lookup
```
GET https://api.geneontology.org/api/ontology/term/{go_id}
```
Example:
```
GET https://api.geneontology.org/api/ontology/term/GO%3A0008150
```
Returns JSON with term name, definition, namespace (biological_process / molecular_function / cellular_component), synonyms.

### 2. Gene/Protein Annotations (Bioentity)
```
GET https://api.geneontology.org/api/bioentity/gene/{gene_id}/function
```
Example — GO annotations for a UniProt protein:
```
GET https://api.geneontology.org/api/bioentity/gene/UniProtKB%3AP04637/function
```
Returns GO annotations with evidence codes, qualifiers, references.

### 3. Genes Annotated to a GO Term
```
GET https://api.geneontology.org/api/bioentity/function/{go_id}/genes
```
Example:
```
GET https://api.geneontology.org/api/bioentity/function/GO%3A0006915/genes?rows=20
```
Returns genes/proteins annotated with that GO term.

### 4. Search Entities
```
GET https://api.geneontology.org/api/search/entity/{query}
```
Example:
```
GET https://api.geneontology.org/api/search/entity/apoptosis?rows=10
```

### 5. Ontology Ancestors / Descendants
```
GET https://api.geneontology.org/api/ontology/term/{go_id}/graph
```

---

## QuickGO API (EBI — recommended for robust annotation queries)

### 1. GO Term Details
```
GET https://www.ebi.ac.uk/QuickGO/services/ontology/go/terms/{go_ids}
```
Example:
```
GET https://www.ebi.ac.uk/QuickGO/services/ontology/go/terms/GO:0008150
```
Accepts comma-separated IDs (up to 25).

### 2. Search Annotations
```
GET https://www.ebi.ac.uk/QuickGO/services/annotation/search?geneProductId={uniprot_id}
```
Example — annotations for TP53:
```
GET https://www.ebi.ac.uk/QuickGO/services/annotation/search?geneProductId=P04637&limit=25
```

### 3. Annotations by GO Term
```
GET https://www.ebi.ac.uk/QuickGO/services/annotation/search?goId=GO:0006915&taxonId=9606&limit=25
```

### 4. Filter Annotations by Evidence
```
GET https://www.ebi.ac.uk/QuickGO/services/annotation/search?geneProductId=P04637&goUsage=descendants&evidenceCode=ECO:0000269&limit=25
```

### 5. GO Term Children
```
GET https://www.ebi.ac.uk/QuickGO/services/ontology/go/terms/GO:0008150/children
```

### 6. GO Term Ancestors (Chart)
```
GET https://www.ebi.ac.uk/QuickGO/services/ontology/go/terms/GO:0006915/ancestors?relations=is_a,part_of
```

### 7. Search GO Terms by Name
```
GET https://www.ebi.ac.uk/QuickGO/services/ontology/go/search?query=apoptosis&limit=10
```

## QuickGO Annotation Search Parameters
| Parameter | Description |
|-----------|-------------|
| `geneProductId` | UniProt accession (e.g., P04637) |
| `goId` | GO term (e.g., GO:0006915) |
| `goUsage` | `exact` or `descendants` (include child terms) |
| `taxonId` | NCBI taxonomy ID (9606 = human) |
| `evidenceCode` | ECO code (e.g., ECO:0000269 = experimental) |
| `aspect` | `biological_process`, `molecular_function`, `cellular_component` |
| `limit` | Results per page (max 100) |
| `page` | Page number (1-based) |

## QuickGO Response Format
```json
{
  "numberOfHits": 1234,
  "results": [
    {
      "geneProductId": "P04637",
      "symbol": "TP53",
      "goId": "GO:0006915",
      "goName": "apoptotic process",
      "evidenceCode": "ECO:0000269",
      "goAspect": "biological_process",
      "taxonId": 9606,
      "reference": "PMID:12345678",
      "assignedBy": "UniProt"
    }
  ]
}
```

## Notes
- QuickGO (EBI) is generally more robust and better documented for annotation queries.
- GO API (geneontology.org) is better for ontology structure traversal.
- GO IDs must be URL-encoded when used in paths (e.g., `GO%3A0008150` for `GO:0008150`).
- Three GO namespaces: biological_process (BP), molecular_function (MF), cellular_component (CC).
- Evidence codes: IDA (direct assay), IMP (mutant phenotype), IGI (genetic interaction), IEA (electronic annotation), etc.
