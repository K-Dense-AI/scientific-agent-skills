# InterPro API Reference

## Base URL
```
https://www.ebi.ac.uk/interpro/api
```

## Authentication
None required. Fully public API.

## Rate Limits
No published hard limits. EBI general guidance: be reasonable, use bulk downloads for large datasets.

## Response Format
JSON by default. Some endpoints support `?format=json` explicitly.

## Key Endpoints

### 1. Entry Lookup (by accession)
```
GET https://www.ebi.ac.uk/interpro/api/entry/interpro/{accession}
```
Example:
```
GET https://www.ebi.ac.uk/interpro/api/entry/interpro/IPR000504
```
Returns JSON with entry name, type (family/domain/site/etc.), description, GO terms, literature references.

### 2. Entry Lookup by Member Database
```
GET https://www.ebi.ac.uk/interpro/api/entry/pfam/{pfam_accession}
GET https://www.ebi.ac.uk/interpro/api/entry/smart/{smart_accession}
GET https://www.ebi.ac.uk/interpro/api/entry/prosite/{prosite_accession}
```
Example:
```
GET https://www.ebi.ac.uk/interpro/api/entry/pfam/PF00076
```

### 3. Search / List Entries
```
GET https://www.ebi.ac.uk/interpro/api/entry/interpro?search={query}
```
Example:
```
GET https://www.ebi.ac.uk/interpro/api/entry/interpro?search=kinase
```
Returns paginated list of matching InterPro entries.

### 4. Protein Annotations — Get InterPro Entries for a Protein
```
GET https://www.ebi.ac.uk/interpro/api/entry/interpro/protein/uniprot/{uniprot_accession}
```
Example:
```
GET https://www.ebi.ac.uk/interpro/api/entry/interpro/protein/uniprot/P12345
```
Returns all InterPro entries annotating that protein.

### 5. Proteins with a Given Entry
```
GET https://www.ebi.ac.uk/interpro/api/protein/uniprot/entry/interpro/{accession}
```
Example:
```
GET https://www.ebi.ac.uk/interpro/api/protein/uniprot/entry/interpro/IPR000504
```
Returns paginated list of UniProt proteins annotated with that entry.

### 6. Structure Mappings
```
GET https://www.ebi.ac.uk/interpro/api/structure/pdb/entry/interpro/{accession}
```
Example:
```
GET https://www.ebi.ac.uk/interpro/api/structure/pdb/entry/interpro/IPR000504
```

### 7. Entry by Type Filter
```
GET https://www.ebi.ac.uk/interpro/api/entry/interpro?type=domain
GET https://www.ebi.ac.uk/interpro/api/entry/interpro?type=family
GET https://www.ebi.ac.uk/interpro/api/entry/interpro?type=homologous_superfamily
```

### 8. Taxonomy Cross-Reference
```
GET https://www.ebi.ac.uk/interpro/api/taxonomy/uniprot/entry/interpro/{accession}
```

## Pagination
Responses include `next` and `previous` URLs:
```json
{
  "count": 1234,
  "next": "https://www.ebi.ac.uk/interpro/api/entry/interpro?cursor=...&page_size=20",
  "previous": null,
  "results": [...]
}
```
Use `?page_size=N` to control page size (default 20).

## Entry Response Key Fields
```json
{
  "metadata": {
    "accession": "IPR000504",
    "name": "RNA recognition motif domain",
    "type": "domain",
    "source_database": "interpro",
    "member_databases": {"pfam": {"PF00076": "RRM_1"}},
    "go_terms": [{"identifier": "GO:0003723", "name": "RNA binding"}],
    "description": ["<p>The RNA recognition motif...</p>"]
  }
}
```

## Notes
- The API follows a composable URL pattern: combine entity types (entry, protein, structure, taxonomy) to create cross-reference queries.
- Member databases: pfam, smart, prosite, prints, panther, cdd, hamap, tigrfam, pirsf, sfld, ncbifam.
