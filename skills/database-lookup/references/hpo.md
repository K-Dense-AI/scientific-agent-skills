# Human Phenotype Ontology (HPO)

Public term API: `https://ontology.jax.org/api/hp` (no key).

| GET path | Use |
|---|---|
| `/search?q=seizure&page=0&limit=5` | Search terms; response `terms`, `totalCount` |
| `/terms/HP%3A0001250` | Term details |
| `/terms/HP%3A0001250/parents` | Direct parents |
| `/terms/HP%3A0001250/children` | Direct children |
| `/terms/HP%3A0001250/ancestors` | All ancestors |
| `/terms/HP%3A0001250/descendants` | All descendants |
| `/terms?filter=HP%3A0001250,HP%3A0001249` | Selected terms |

Search is zero-based and needs `q`, `page`, and `limit`; encode query values.
Term records include `id`, `name`, `definition`, `synonyms`, and `xrefs`.
Hierarchy endpoints return arrays. An absent term can return null.

Annotations use a separate service:
`GET https://ontology.jax.org/api/network/annotation/HP%3A0001250`.
Inspect its entity-specific response; there are no documented `/hpo/term/.../genes`
or `/hpo/gene/...` routes in the current term API. For bulk gene/disease analyses,
use the versioned HPO annotation downloads and preserve evidence and negation.

Official schemas: [terms](https://ontology.jax.org/api/hp/docs/),
[annotation network](https://ontology.jax.org/api/network/docs).
