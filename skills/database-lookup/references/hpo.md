# HPO (Human Phenotype Ontology)

## Base URL
```
https://ontology.jax.org/api/hp
```

## Auth
No API key required.

## Important: URL-encode colons in HP IDs — `HP:0001250` becomes `HP%3A0001250`

## Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `/hpo/search?q={query}&max={n}` | Search HPO terms by name |
| `/hpo/term/{id}` | Term details |
| `/hpo/term/{id}/genes` | Genes associated with a phenotype |
| `/hpo/term/{id}/diseases` | Diseases associated with a phenotype |
| `/hpo/term/{id}/children` | Child terms in hierarchy |
| `/hpo/term/{id}/parents` | Parent terms |
| `/hpo/gene/{gene_id}` | Phenotypes for a gene (Entrez ID) |
| `/hpo/disease/{disease_id}` | Phenotypes for a disease (OMIM/ORPHA) |

## Example Calls
```
# Search for "seizure"
https://ontology.jax.org/api/hp/hpo/search?q=seizure&max=5

# Term details for Seizure
https://ontology.jax.org/api/hp/hpo/term/HP%3A0001250

# Genes associated with Seizure
https://ontology.jax.org/api/hp/hpo/term/HP%3A0001250/genes

# Diseases for Seizure
https://ontology.jax.org/api/hp/hpo/term/HP%3A0001250/diseases

# Phenotypes for SCN1A (Entrez 6323)
https://ontology.jax.org/api/hp/hpo/gene/6323
```

## Response Format
JSON. Terms: `id`, `name`, `definition`, `synonyms`. Gene associations: `genes[]` with `geneId`, `geneSymbol`. Diseases: `diseases[]` with `diseaseId`, `diseaseName`.

## Rate Limits
No published limits. Bulk annotation files at https://hpo.jax.org/data/annotations
