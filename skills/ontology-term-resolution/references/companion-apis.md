# Companion identifier services

OLS is the authority for "does this term exist, and is it current?". The four
services below answer different questions. Every behaviour here was checked
against the live APIs in September 2026.

| Service | Use it for | Do not use it for |
| --- | --- | --- |
| Bioregistry | Is this prefix real? Does the local id match the recorded pattern? What is the preferred prefix? | Whether the term exists or is obsolete |
| Identifiers.org | Landing-page URLs from Bioregistry `providers.miriam` | Synonym prefixes (`HPO:…`); templating `preferred_prefix`; existence checks |
| ZOOMA | Mapping lab shorthand OLS cannot lexical-match | Unfiltered annotate; writing an ID without OLS validation |
| Ontobee | The OBO Foundry HTML/RDF page for a term IRI | Search, validation, or routine resolution — there is no JSON search API |

## Bioregistry

Base URL: `https://bioregistry.io/api`. No API key.

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

If a metadata file writes `HPO:0001250`, Bioregistry will look fine and
Identifiers.org will reject the compact identifier. Rewrite to the preferred
prefix (`HP:0001250`) before handing the CURIE to any other resolver.

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

Resolver: `https://resolver.api.identifiers.org/{CURIE}`. Registry docs at
https://docs.identifiers.org/. No API key.

A successful body is `{apiVersion, errorMessage: null, payload: {resolvedResources: […]}}`.
Each resource has `compactIdentifierResolvedUrl`, `providerCode`, `official`,
and `recommendation.recommendationIndex`.

### Trap — preferred prefix is not the Identifiers.org namespace

Bioregistry `preferred_prefix` is the form OLS wants. It is not the MIRIAM
compact-identifier namespace, and not every prefix has one:

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
transport failure.

## ZOOMA

Annotate: `https://www.ebi.ac.uk/spot/zooma/v2/api/services/annotate`.
No API key. Slow — budget tens of seconds; the client uses a 60 s timeout.

| Parameter | Effect |
| --- | --- |
| `propertyValue` | The free-text string. |
| `propertyType` | Optional slot (`organism part`, `cell type`, `disease`). Helps when the same word is used in several roles. |
| `filter` | **Required.** `required:[none],ontologies:[uberon]` or comma-separated OLS ids. |

Hits carry `confidence` (`HIGH` / `GOOD` / `MEDIUM` / `LOW`), `semanticTags`
(IRIs, not CURIEs), and `provenance.evidence` (`ZOOMA_INFERRED_FROM_CURATED`
or `OLS_TEXT_TAGGER`).

`map_terms.py` refuses to run without `--ontology`, converts IRIs with
`iri_to_curie`, and labels HIGH/GOOD as `zooma_safe` and the rest as
`zooma_weak`.

### Trap — unfiltered annotate is unusable

```
propertyValue=liver
  -> 118 hits, HIGH: FOODON:03309772, XAO:0000133, UBERON:0002107, BTO:0000759, …
propertyValue=liver&propertyType=organism+part&filter=required:[none],ontologies:[uberon]
  -> 10 hits, first tag UBERON:0002107
```

An earlier check of the unfiltered call also returned
`https://w3id.org/gold.vocab/Liver`. Never call annotate without an ontology
filter.

### Trap — HIGH is not "write this ID"

`PBMC` filtered to `cl` returns `CL:2000001` at HIGH and several other cell
types at MEDIUM. Still run `validate_terms.py` on the CURIE: ZOOMA does not
report obsolescence, defining ontology, or branch membership, and its IRIs
still need the EFO / Orphanet / OBO split that `iri_to_curie` already knows.

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
