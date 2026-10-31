# Companion identifier services

OLS verifies terms in its loaded ontology releases. The four services below answer
different questions. Reviewed 2026-10-01 against official schemas/source and public
read-only requests; endpoint results and registry mappings can change.

| Service | Use it for | Do not use it for |
| --- | --- | --- |
| Bioregistry | Is this prefix real? Does the local id match the recorded pattern? What is the preferred prefix? | Whether the term exists or is obsolete |
| Identifiers.org | Landing-page URLs from Bioregistry `providers.miriam` | Synonym prefixes (`HPO:…`); templating `preferred_prefix`; existence checks |
| ZOOMA | Mapping lab shorthand OLS cannot lexical-match | Unfiltered annotate; writing an ID without OLS validation |
| Ontobee | The OBO Foundry HTML/RDF page for a term IRI | Search, validation, or routine resolution — there is no JSON search API |

## Bioregistry

Base URL: `https://bioregistry.io/api`. No API key. Official
[usage guide](https://bioregistry.io/usage) and [OpenAPI schema](https://bioregistry.io/openapi.json).
These are individual-resource lookups and an unpaged prefix search, not paginated term searches.

| Endpoint | Question |
| --- | --- |
| `GET /registry/{prefix}` | What is this prefix? Accepts synonyms. |
| `GET /reference/{CURIE}` | Is the local id well-formed, and which providers resolve it? |
| `GET /search?q=` | Prefix search. Returns `[[canonical, synonym], …]`. |

Useful record fields: `prefix` (canonical, usually lowercase), `preferred_prefix`
(`HP`, `CHEBI`), `pattern` (regex for the **local** id only), `example`,
`uri_format` (`$1` is the local id), `synonyms`, `mappings.ols`,
`mappings.ontobee`, `mappings.miriam`.

`lookup_prefix.py` wraps the first two endpoints.

### Trap — synonym prefixes resolve here and fail elsewhere

```
GET /registry/HPO          -> 200, prefix=hp, preferred_prefix=HP, synonyms=["hpo"]
GET /reference/HPO:0001250 -> 200, same providers as HP:0001250
GET https://resolver.api.identifiers.org/HPO:0001250
                           -> 400, "NOT A NAMESPACE"
```

If a metadata file writes `HPO:0001250`, Bioregistry will accept the synonym while
Identifiers.org rejects it. `HP:0001250` works for both OLS and Identifiers.org. Do not
generalize this to every prefix: Bioregistry prefers `ORPHA`, OLS uses `Orphanet`/`ordo`,
and Identifiers.org uses `orphanet`. Verify the mapping and IRI, not only capitalization.

### Trap — 404 is two different failures

`/reference/{CURIE}` returns HTTP 404 with a JSON `detail` for both:

- unknown prefix: `"Prefix not found: …"`
- known prefix, bad local id: `"invalid identifier: hp:notanid for pattern ^\\d{7}$"`

Read `detail`. Treating both as "no such prefix" hides a well-formed-prefix,
malformed-local-id error. Client-side `re.fullmatch(pattern, local)` is the
same check and does not need a network call once you have the record.

### Trap — `pattern` is the local id, not the CURIE

`HP` has `pattern: ^\d{7}$`. `0001250` matches; `HP:0001250` does not. Never
run the regex against the whole CURIE.

## Identifiers.org

Resolver: `https://resolver.api.identifiers.org/{CURIE}`. [Resolver API documentation](https://docs.identifiers.org/pages/api.html). No API key.
This returns provider URLs in one response, not paginated ontology terms. No provider
URL or successful resolver response proves that the term exists in its underlying database.

A successful body is `{apiVersion, errorMessage: null, payload: {resolvedResources: […]}}`.
Each resource has `compactIdentifierResolvedUrl`, `providerCode`, `official`,
and `recommendation.recommendationIndex`.

### Trap — preferred prefix is not the Identifiers.org namespace

Bioregistry `preferred_prefix`, OLS CURIE spelling, and MIRIAM namespaces can differ,
and not every prefix has a MIRIAM mapping:

```
GET /reference/orphanet:558  -> providers.miriam = https://identifiers.org/orphanet:558
GET resolver/ORPHA:558       -> 400 NOT A NAMESPACE   (preferred_prefix is ORPHA)
GET resolver/orphanet:558    -> 200
GET /reference/OBA:0000001   -> no providers.miriam   (OBA, XAO, ECTO have none)
GET resolver/hp:0001250      -> 400                   (namespace embeds HP: in the LUI)
GET resolver/CHEBI:15377     -> 200
GET resolver/chebi:15377     -> 400
```

Always take the landing page from `/api/reference/{CURIE}` `providers.miriam`.
Leave the column empty when that mapping is missing. Do not template
`https://identifiers.org/{preferred_prefix}:{local}` — that is how
`ORPHA:558` and `OBA:0000001` become dead links next to a rejection note.

### Trap — do not encode the colon

`https://resolver.api.identifiers.org/HP:0001250` works.
`https://resolver.api.identifiers.org/HP%3A0001250` is HTTP 400
("NOT A NAMESPACE"). Leave `:` unencoded in the path.

A 400 body still parses as JSON — `errorMessage` is set and
`resolvedResources` is null. That is a rejected compact identifier, not a
transport failure. Timeouts, malformed JSON and 5xx responses are service failures;
`lookup_prefix.py` retains the registry-supplied URL and labels it unverified rather than
claiming the identifier was rejected. Only a resolver rejection blanks that URL.

## ZOOMA

Bundled compatibility route: `GET https://www.ebi.ac.uk/spot/zooma/v2/api/services/annotate`.
No API key or pagination. The client uses a 60-second timeout and limits returned rows locally.
Current [official docs source](https://github.com/EBISPOT/zooma2/blob/dev/frontend/src/pages/docs/api.tsx)
also describes v3 JSON mapping/streaming routes; this client deliberately retains the supported
[v2 contract](https://github.com/EBISPOT/zooma2/blob/dev/backend/src/main/java/uk/ac/ebi/zooma2/api/v2/ZoomaApiV2.java).

| Parameter | Effect |
| --- | --- |
| `propertyValue` | Free-text string. |
| `propertyType` | Optional context such as `organism part` or `cell type`. |
| `filter` | The client requires `ontologies:[uberon],defining_only:[true]`; the service itself allows omission. |

Ontology restrictions select targets; `defining_only:[true]` excludes imported namespaces.
Omitting `required` permits available curated sources. The older `required:[none]` was not a
requirement of the API and is no longer sent. Do not use `ontologies:[none]` to disable ontology
matching: the current v2 adapter interprets that legacy sentinel as no ontology restriction.

Hits contain `confidence` (`HIGH`, `GOOD`, `MEDIUM`, `LOW`), `semanticTags` (IRIs),
`annotatedProperty`, `provenance`, and often `derivedFrom`. Unknown IRI namespaces remain
unconverted rather than being turned into plausible CURIEs by splitting a URL.

### Confidence and provenance are not curation verdicts

Current v2 source assigns HIGH to full curated/label/synonym matches; other scores are bucketed.
These are ranking categories, not calibrated correctness probabilities. In the review's live
`liver` query, the organ was HIGH while several narrower liver parts were GOOD.

The v2 outer wrapper always uses `ZOOMA_INFERRED_FROM_CURATED`, including underlying
`OLS_TEXT_TAGGER` and `OLS_EMBEDDING` matches. `flatten_hit()` reports evidence/source from
`derivedFrom` and retains the full available provenance chain in JSON. Do not infer human
curation from the outer evidence label. See the official
[annotation adapter](https://github.com/EBISPOT/zooma2/blob/dev/backend/src/main/java/uk/ac/ebi/zooma2/api/v2/dto/V2AnnotationDto.java)
and [confidence logic](https://github.com/EBISPOT/zooma2/blob/dev/backend/src/main/java/uk/ac/ebi/zooma2/api/v2/dto/V2ConfidenceLevel.java).

`map_terms.py --high-confidence-only` retains HIGH/GOOD candidates. `--exact-only` is a legacy
alias for that confidence filter, unrelated to OLS lexical exactness. Legacy output names
`safe` and `zooma_safe` also mean only HIGH/GOOD. Always check each candidate's OLS term detail,
definition, synonym scope, schema and sample context before writing the annotation.

## Ontobee

Ontobee is the default linked-data server for most OBO Foundry ontologies.
It serves an HTML page and RDF for a term IRI. It is not a resolver and it
has no JSON search API.

Term page:

```
https://ontobee.org/ontology/{PREFIX}?iri={url-encoded IRI}
```

`lookup_prefix.py` builds this only when the registry record has
`mappings.ontobee`, using that value (not `preferred_prefix`) plus
`uri_format`. Example: `HP:0001250` →
`https://ontobee.org/ontology/HP?iri=http%3A%2F%2Fpurl.obolibrary.org%2Fobo%2FHP_0001250`.
Orphanet has no `mappings.ontobee` — the templated `ORPHA` / `ORDO` page is
HTTP 500 — so that cell stays empty.

HTML keyword search (`/search?ontology=UBERON&keywords=liver`) is a browser
page, not an API — do not scrape it. For text → ID use OLS (or ZOOMA for
shorthand). For ID → verdict use OLS.

SPARQL is available at the Hegroup endpoint documented on
https://ontobee.org/tutorial/sparql, for axiom queries OLS does not expose.
The graph URI pattern (`http://purl.obolibrary.org/obo/merged/FOO`) is not
reliable; do not put SPARQL in a routine resolve/validate path.

## Which call to make

1. Prefix looks wrong, or you need a landing page → `lookup_prefix.py`.
2. Free text, expected ontology known → `resolve_terms.py` (OLS).
3. OLS returned unresolved / partial on lab shorthand → `map_terms.py`, then
   `validate_terms.py` on every CURIE you might keep.
4. You already have a CURIE → `validate_terms.py` (OLS). Optionally
   `lookup_prefix.py` first if the prefix itself might be a synonym.
5. You want the OBO Foundry page for a known IRI → the Ontobee URL from
   `lookup_prefix.py`, not a new search.
