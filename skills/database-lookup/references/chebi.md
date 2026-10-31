# ChEBI (Chemical Entities of Biological Interest) API Reference

## Base URLs
- **OLS (Ontology Lookup Service) API**: `https://www.ebi.ac.uk/ols4/api`
- **ChEBI REST API**: `https://www.ebi.ac.uk/chebi/backend/api/public`

## Authentication
None required. All endpoints are public.

## Rate Limits
No published hard limits. EBI general guidance: reasonable usage.

## Important Note
ChEBI 2.0 replaced the deprecated SOAP service with a public REST API. Use ChEBI REST for chemical records and structure searches; OLS4 remains useful for ontology traversal.

---

## OLS4 API Endpoints (Recommended for REST/JSON)

### 1. Search ChEBI Terms
```
GET https://www.ebi.ac.uk/ols4/api/search?q={query}&ontology=chebi
```
Example:
```
GET https://www.ebi.ac.uk/ols4/api/search?q=aspirin&ontology=chebi
```
Returns JSON with matching ChEBI terms, IDs, definitions, synonyms.

### 2. Lookup by ChEBI ID
```
GET https://www.ebi.ac.uk/ols4/api/ontologies/chebi/terms?iri=http://purl.obolibrary.org/obo/CHEBI_{id}
```
Example:
```
GET https://www.ebi.ac.uk/ols4/api/ontologies/chebi/terms?iri=http://purl.obolibrary.org/obo/CHEBI_15365
```
Returns full term details: name, definition, synonyms, xrefs, relationships.

### 3. Get Term by Short Form
```
GET https://www.ebi.ac.uk/ols4/api/ontologies/chebi/terms/http%253A%252F%252Fpurl.obolibrary.org%252Fobo%252FCHEBI_{id}
```
(Double-encoded IRI in path.)

### 4. Term Hierarchy — Parents
```
GET https://www.ebi.ac.uk/ols4/api/ontologies/chebi/terms/http%253A%252F%252Fpurl.obolibrary.org%252Fobo%252FCHEBI_{id}/parents
```

### 5. Term Hierarchy — Children
```
GET https://www.ebi.ac.uk/ols4/api/ontologies/chebi/terms/http%253A%252F%252Fpurl.obolibrary.org%252Fobo%252FCHEBI_{id}/children
```

### 6. Ontology Metadata
```
GET https://www.ebi.ac.uk/ols4/api/ontologies/chebi
```

## OLS Search Response Format
```json
{
  "response": {
    "numFound": 5,
    "docs": [
      {
        "id": "chebi:15365",
        "iri": "http://purl.obolibrary.org/obo/CHEBI_15365",
        "label": "aspirin",
        "description": ["A member of the class of benzoic acids..."],
        "short_form": "CHEBI_15365",
        "obo_id": "CHEBI:15365",
        "ontology_name": "chebi",
        "type": "class"
      }
    ]
  }
}
```

## ChEBI 2.0 REST endpoints

| GET path (relative to the ChEBI REST base) | Parameters / purpose |
|---|---|
| `/compound/{chebi_id}/` | Full entity; numeric ID or `CHEBI:` prefix |
| `/es_search/` | `term` required; `page=1`, `size=15` defaults |
| `/ontology/parents/{chebi_id}/` | Ontology parents |
| `/ontology/children/{chebi_id}/` | Ontology children |
| `/structure_search/` | `smiles`, `search_type=connectivity|similarity|substructure` |
| `/molfile/{id}/` | Structure file |

For similarity search, use `similarity` between 0.4 and 1.0. The default
`three_star_only=true` limits structure results to three-star entries; explicitly
set false when two-star entries are also in scope. Search pagination uses `page`
and `size`. The current schema leaves several response bodies unspecified;
inspect the returned JSON before choosing field paths, and do not assume OLS's
`response.docs` envelope applies to ChEBI REST.

Illustrative request:

```bash
curl --fail-with-body --get 'https://www.ebi.ac.uk/chebi/backend/api/public/es_search/' \
  --data-urlencode 'term=aspirin' --data-urlencode 'page=1' --data-urlencode 'size=5'
```

Reviewed 2026-09-30: [ChEBI OpenAPI](https://www.ebi.ac.uk/chebi/backend/api/schema/),
[ChEBI 2.0 migration](https://www.ebi.ac.uk/about/news/updates-from-data-resources/chebi-2-0-launches/).
