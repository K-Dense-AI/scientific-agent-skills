# EBI OLS4 API reference

Reviewed 2026-10-01 against the [official OpenAPI description](https://www.ebi.ac.uk/ols4/v3/api-docs),
[compatibility API guide](https://www.ebi.ac.uk/ols4/ols3help),
[current implementation](https://github.com/EBISPOT/ols4/tree/dev/backend/src/main/java/uk/ac/ebi/spot/ols/controller/api/v1),
and unauthenticated public requests. The bundled client uses the OLS3-compatible `/api`
interface; `/api/v2` is a different response contract. No API key is needed.

Base URL: `https://www.ebi.ac.uk/ols4/api`. Send a descriptive User-Agent, keep concurrency low,
and back off on 429 or transient server errors. Treat HTML or malformed JSON as service failure,
not an empty scientific result. The client retries transient failures three times.

## `GET /search` — text to candidates

| Parameter | Effect |
| --- | --- |
| `q` | Required query text. |
| `ontology` | Comma-separated OLS ids (`uberon`, `ordo`), selecting ontology documents, including imports. |
| `type` | Entity type; the helper requests `class`. |
| `queryFields` | `label,synonym` for a restricted lexical search; omitted for all indexed fields. |
| `exact` | Match mode, not proof of exact label equality; check the returned strings locally. |
| `obsoletes` | Current v1 implementation filters on this boolean: `false` current-only, `true` obsolete-only. |
| `local` | `true` excludes imported copies; not enabled by the bundled search by default. |
| `allChildrenOf` | Term IRI, encoded once by query serialization. Hierarchical descendants include is-a, part-of, develops-from. |
| `childrenOf` | Current v1 implementation uses the same hierarchical-ancestor filter as `allChildrenOf`; do not assume direct-child-only semantics. |
| `rows`, `start` | Page length and zero-based result offset, not a page number. |
| `fieldList` | Fields to return, comma-separated. |
| `groupField` | Current implementation groups by IRI for any value other than `false`; the helper instead deduplicates locally. |

Response: `response.numFound`, `response.start`, `response.docs`. The helper requests `iri`,
`obo_id`, `label`, `synonym`, scoped `exact_synonyms`, `related_synonyms`, `broad_synonyms`,
`narrow_synonyms`, `ontology_name`, `is_defining_ontology`, `type`, `short_form`.
The plural scoped synonym fields are now supported. `synonym` is their combined lexical list.

A live snapshot illustrates why local classification matters:

```text
q=liver&ontology=uberon&exact=true                   -> 161 hits
q=liver&ontology=uberon&exact=true&queryFields=label -> 1 hit
```

`iecur` and `jecur` are **related** synonyms of liver in the reviewed release. Matching their
spelling does not make the synonym relation exact. `--exact-only` retains exact labels and
explicit exact-synonym matches, rejecting other scopes and partial matches.

`is_obsolete` and `term_replaced_by` are still omitted from search records, even if requested.
The public description says `obsoletes=true` includes obsolete terms, but the current source
and live probe show an obsolete-only filter. `search(..., include_obsolete=True)` therefore
merges a current-only query and an obsolete-only query (up to `rows` from each).

`ontology=uberon&q=hepatocyte` returns imported `CL:0000182`; adding `local=true` removes it.
A search restricted to an ontology document does not enforce a required CURIE namespace.
Use term validation with `--expect-ontology` before accepting the result.

The same IRI can occur in several ontology documents. Deduplicate and prefer defining copies,
but remember that a bounded search can miss competing exact matches or the defining copy.
Do not treat the first result or an exact spelling as an automatic annotation decision.

## `GET /ontologies/{ontology}/terms?obo_id={CURIE}` — term detail

Returns `_embedded.terms`; a missing term can return 404. Inspect `is_obsolete`,
`term_replaced_by`, `is_defining_ontology`, the definition, and `obo_synonym` (including scope).
OLS is a lookup index of ontology releases, not proof that an annotation fits a sample.

```text
EFO:0001067 -> obsolete_parasitic infection
is_obsolete: true
term_replaced_by: http://purl.obolibrary.org/obo/MONDO_0005135
```

Replacement values are IRIs. The helper converts only recognized OBO/EFO/Orphanet namespaces;
unknown replacement IRIs remain visible unchanged. Never split an arbitrary URL's last
underscore and assume it is an ontology CURIE. Replacements and `consider` annotations need
separate review; do not assume they are semantically interchangeable with the obsolete term.

## `GET /terms?iri={IRI}` — copies and index fallback

A missing `obo_id` index entry is not proof of nonexistence. The client tries known IRI patterns,
queries OLS, follows all HAL `_links.next` pages, and prefers the home defining copy.
`_resolved_via` and `_home_ontology` record that choice.

`MONDO:0000001` now resolves directly by `obo_id`; the older index-hole example is fixed.
`Orphanet:558` still required IRI fallback at review. `ORPHA:558` (Bioregistry's preferred form)
and `Orphanet:558` use home ontology `ordo` and the same Orphanet IRI template.
An imported-only result warns; it does not prove the source ontology deleted the term.
A failed fallback means not found **in this OLS lookup**, not in every ontology source.

| Namespace | Candidate IRI pattern, requiring subsequent OLS confirmation |
| --- | --- |
| OBO | `http://purl.obolibrary.org/obo/{PREFIX}_{local}` |
| EFO | `http://www.ebi.ac.uk/efo/EFO_{local}` |
| Orphanet / ORPHA | `http://www.orpha.net/ORDO/Orphanet_{local}` |

Other namespace conventions need a registry-supplied or original IRI, not speculative rewriting.

## Hierarchy and release provenance

Follow term `_links.hierarchicalAncestors.href` for all hierarchical relations; follow
`_links.ancestors.href` for subclass/is-a ancestry only. The client follows pagination,
upgrades service-generated HTTP links to HTTPS, and fails on incomplete traversal rather than
returning a false `wrong_branch`. An empty ancestor set is meaningful only after a successful
complete response. `validate_terms.py --branch-relation is-a` selects subclass-only checks;
the default and search `--branch` include hierarchical relations.

A part of an organ is not necessarily a subclass of that organ. CARO also places cell under
anatomical structure, so even a valid ancestry test cannot enforce a tissue-only namespace.
Use both branch and namespace constraints. The validator accepts the branch root itself;
search descendant filtering need not include the root. The root must be current.

`GET /ontologies/{id}/terms/roots` is a presentation of ontology roots, which may include imported
upper-level terms. Use explicit schema-approved roots instead of interpreting this as a category
contract. `GET /ontologies/{id}` provides `config.versionIri`, `config.version`, `loaded`, and
`updated` (nullable). Preserve these, lookup time, original input, selected IRI and raw responses.
OLS's currently loaded release can differ from a submission schema's pinned release.

## Related services

See `companion-apis.md` for Bioregistry, Identifiers.org, ZOOMA and Ontobee.
[OxO2](https://github.com/EBISPOT/oxo2) is now live at `https://www.ebi.ac.uk/spot/oxo/`;
the legacy `/api/search` route returned HAL JSON in this review. The blanket statement that
OxO is retired and every API route returns HTML is incorrect. This skill does not implement
an OxO client. For cross-ontology work inspect the current service contract, mapping predicate,
provenance and inference distance, or use a published SSSOM mapping set. Bare database xrefs
are leads, not guaranteed `skos:exactMatch` assertions.
