# Monarch Initiative API

## Base URL
```
https://api.monarchinitiative.org/v3/api
```

## Auth
No API key required.

## Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `/search?q={query}` | Text search across all entities |
| `/autocomplete?q={prefix}` | Autocomplete entity names |
| `/entity/{id}` | Entity details (gene, disease, phenotype) |
| `/entity/{id}/associations` | Associations for an entity |
| `/entity/{id}/associations?category={cat}` | Filtered associations |

## Entity ID Prefixes
- `MONDO:` — diseases (e.g. `MONDO:0007947`)
- `HP:` — phenotypes (e.g. `HP:0001250`)
- `HGNC:` — genes (e.g. `HGNC:3603`)
- `NCBIGene:` — genes (e.g. `NCBIGene:7157`)

## Association Categories
`biolink:GeneToPhenotypicFeatureAssociation`, `biolink:DiseaseToPhenotypicFeatureAssociation`, `biolink:GeneToDiseaseAssociation`

## Example Calls
```
# Search for Marfan syndrome
https://api.monarchinitiative.org/v3/api/search?q=Marfan+syndrome&limit=5

# Entity details for a disease
https://api.monarchinitiative.org/v3/api/entity/MONDO:0007947

# Gene-to-phenotype for FBN1
https://api.monarchinitiative.org/v3/api/entity/HGNC:3603/associations?category=biolink:GeneToPhenotypicFeatureAssociation&limit=10
```

## Response Format
JSON. Search: `items[]` with `id`, `name`, `category`. Associations: `items[]` with `subject`, `predicate`, `object`, `publications`.

## Rate Limits
No published limits. Be reasonable.
