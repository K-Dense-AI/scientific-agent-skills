# RCSB Protein Data Bank (PDB) API Reference

## Base URLs
- **Data API**: `https://data.rcsb.org/rest/v1`
- **Search API**: `https://search.rcsb.org/rcsbsearch/v2/query`
- **GraphQL**: `https://data.rcsb.org/graphql`
- **Files**: `https://files.rcsb.org`

## Authentication
None required. Fully public API.

## Rate Limits
No published hard limits; be courteous (a few requests/second). Bulk downloads available via FTP.

## Key Endpoints

### 1. Entry Lookup (Data API)
```
GET https://data.rcsb.org/rest/v1/core/entry/{entry_id}
```
Example:
```
GET https://data.rcsb.org/rest/v1/core/entry/4HHB
```
Returns JSON with resolution, method, deposition date, title, authors, etc.

### 2. Polymer Entity (unique molecular entity)
```
GET https://data.rcsb.org/rest/v1/core/polymer_entity/{entry_id}/{entity_id}
```
Example:
```
GET https://data.rcsb.org/rest/v1/core/polymer_entity/4HHB/1
```

An entity may have multiple chain instances. For chain-specific coordinates/annotations use `/core/polymer_entity_instance/{entry_id}/{label_asym_id}`; `label_asym_id` is the mmCIF identifier, not necessarily the author chain ID.

### 3. Assembly Info
```
GET https://data.rcsb.org/rest/v1/core/assembly/{entry_id}/{assembly_id}
```

### 4. Full-Text and Attribute Search (Search API)
```
POST https://search.rcsb.org/rcsbsearch/v2/query
Content-Type: application/json
```
Example — search by UniProt accession:
```json
{
  "query": {
    "type": "terminal",
    "service": "text",
    "parameters": {
      "attribute": "rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers.database_accession",
      "operator": "exact_match",
      "value": "P69905"
    }
  },
  "return_type": "entry"
}
```

### 5. Sequence Search (Search API)
```json
{
  "query": {
    "type": "terminal",
    "service": "sequence",
    "parameters": {
      "evalue_cutoff": 0.1,
      "identity_cutoff": 0.9,
      "sequence_type": "protein",
      "value": "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSH"
    }
  },
  "return_type": "polymer_entity"
}
```

### 6. Structure Similarity Search
```json
{
  "query": {
    "type": "terminal",
    "service": "structure",
    "parameters": {
      "value": {"entry_id": "4HHB", "assembly_id": "1"},
      "operator": "strict_shape_match"
    }
  },
  "return_type": "assembly"
}
```

### 7. Download Structure Files
```
GET https://files.rcsb.org/download/{entry_id}.cif
GET https://files.rcsb.org/download/{entry_id}.pdb
```

### 8. GraphQL Query
```
POST https://data.rcsb.org/graphql
```
Body example:
```json
{
  "query": "{ entry(entry_id: \"4HHB\") { rcsb_entry_info { resolution_combined } struct { title } } }"
}
```

## Response Format
REST/Data and successful Search results return JSON. Search can return HTTP 204 for no matches; do not attempt to JSON-decode an empty body. File downloads return PDB/mmCIF text.

## Useful `return_type` Values for Search
- `entry` — PDB IDs
- `polymer_entity` — entity-level results (e.g., 4HHB_1)
- `assembly` — biological assembly results

## Notes
- Search API uses POST with a JSON query DSL. Combine queries with `"type": "group"` and `"logical_operator": "and"/"or"`.
- Pagination via `"request_options": {"paginate": {"start": 0, "rows": 25}}`.
