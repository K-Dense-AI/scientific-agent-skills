# HPO (Human Phenotype Ontology)

## Base URL
```
https://ontology.jax.org/api
```

## Auth
No API key required.

## HP IDs
Colons work raw or percent-encoded: `HP:0001250` and `HP%3A0001250` both resolve.

## Key Endpoints

Ontology terms live under `/hp`; annotation (gene/disease/treatment links) lives
under `/network`. They are separate trees, so a term lookup and its gene list are
two different calls.

| Endpoint | Description |
|----------|-------------|
| `/hp/search?q={query}&max={n}` | Search HPO terms by name; returns `{terms: [...]}` |
| `/hp/terms/{id}` | Term details |
| `/hp/terms/{id}/children` | Child terms in hierarchy |
| `/hp/terms/{id}/parents` | Parent terms |
| `/network/annotation/{hp_id}` | Everything annotated to a phenotype: `diseases[]`, `genes[]`, `assays[]`, `medicalActions[]` |
| `/network/annotation/NCBIGene:{entrez}` | Phenotypes for a gene |
| `/network/annotation/OMIM:{id}` | Phenotypes for a disease (also accepts ORPHA/MONDO CURIEs) |

There is no `/genes` or `/diseases` sub-path on a term. Use one
`/network/annotation/{hp_id}` call and read the `genes` or `diseases` array from it.

## Example Calls
```
# Search for "seizure"
https://ontology.jax.org/api/hp/search?q=seizure&max=5

# Term details for Seizure
https://ontology.jax.org/api/hp/terms/HP:0001250

# Genes AND diseases associated with Seizure (one call)
https://ontology.jax.org/api/network/annotation/HP:0001250

# Phenotypes for SCN1A (Entrez 6323)
https://ontology.jax.org/api/network/annotation/NCBIGene:6323
```

## Response Format
JSON.

- Term (`/hp/terms/{id}`): `id`, `name`, `definition`, `comment`, `descendantCount`,
  `synonyms`, `xrefs`, `publicationReferences`, `translations`.
- Annotation (`/network/annotation/{id}`): `genes[]` as `{id: "NCBIGene:9211", name: "LGI1"}`,
  `diseases[]` as `{id: "OMIM:621475", name, mondoId, description}`, plus `assays[]` and
  `medicalActions[]` as `{id: "MAXO:...", name, relations[], sources[]}`.

Note the gene and disease objects use `id`/`name`, not `geneId`/`geneSymbol`/`diseaseId`.

## Rate Limits
No published limits. Bulk annotation and ontology files are released on GitHub at
https://github.com/obophenotype/human-phenotype-ontology/releases . The old
hpo.jax.org/data/annotations path returns 404.

## Verification
Checked 2026-09-09: `/hp/search`, `/hp/terms/{id}`, `/hp/terms/{id}/children`,
`/hp/terms/{id}/parents`, `/network/annotation/{hp_id}`,
`/network/annotation/NCBIGene:{entrez}` and `/network/annotation/OMIM:{id}` all
returned HTTP 200. The base URL itself has no route and returns 404, which is
expected. The previous `/api/hp/hpo/...` paths documented here are retired and
return 404 for every endpoint.
