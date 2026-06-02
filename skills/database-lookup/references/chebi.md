# ChEBI (Chemical Entities of Biological Interest) API Reference

## Base URLs
- **OLS (Ontology Lookup Service) API**: `https://www.ebi.ac.uk/ols4/api`
- **ChEBI Web Services (SOAP)**: `https://www.ebi.ac.uk/webservices/chebi/2.0/test` (SOAP/XML only)
- **ChEBI LibChebi REST (limited)**: entity pages at `https://www.ebi.ac.uk/chebi`

## Authentication
None required. All endpoints are public.

## Rate Limits
No published hard limits. EBI general guidance: reasonable usage.

## Important Note
ChEBI's primary web service is **SOAP-based** (XML), not REST. For REST-style JSON access, use the **EBI OLS4 API** which indexes ChEBI as an ontology.

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

## ChEBI SOAP Web Service (Alternative)
If you need chemical-specific data (formula, mass, structure, InChI), use the SOAP service:
- WSDL: `https://www.ebi.ac.uk/webservices/chebi/2.0/webservice?wsdl`
- Operations: `getCompleteEntity`, `getLiteEntity`, `getStructureSearch`, `getOntologyChildren`, `getOntologyParents`
- Returns XML only.

Example SOAP request for `getCompleteEntity`:
```xml
<soapenv:Body>
  <chebi:getCompleteEntity>
    <chebi:chebiId>CHEBI:15365</chebi:chebiId>
  </chebi:getCompleteEntity>
</soapenv:Body>
```
Returns: formula, mass, charge, InChI, InChIKey, SMILES, synonyms, database links, ontology parents/children.

## Notes
- For programmatic REST access, OLS4 is the easiest path.
- For chemical structure searches (by InChI, SMILES, substructure), the SOAP service is required.
- ChEBI IDs are numeric (e.g., 15365) but referenced as "CHEBI:15365" in OBO format.
- PubChem and UniChem can cross-reference ChEBI IDs to other chemical databases.
