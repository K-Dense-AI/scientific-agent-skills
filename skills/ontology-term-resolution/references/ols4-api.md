# EBI OLS4 API reference

Base URL: `https://www.ebi.ac.uk/ols4/api`. No API key, no registration. Be polite: send a
descriptive `User-Agent`, keep concurrency low, and back off on HTTP 429.

Every behaviour recorded here was checked against the live service in July 2026. OLS4 changed
several defaults from OLS3, and the traps below are the ones that silently produce wrong answers
rather than errors.

## `/search` — text to candidate terms

| Parameter | Effect |
| --- | --- |
| `q` | The query string. |
| `ontology` | Comma-separated OLS **ontology ids** (`uberon`, not `UBERON`). Filters by ontology *document*, not by CURIE prefix — see trap 3. |
| `queryFields` | Which fields to match. Default is every indexed field. Use `label` or `label,synonym`. |
| `exact` | `true` restricts to whole-token matches — **not** to exact labels. See trap 1. |
| `obsoletes` | `true` includes obsolete terms. Default excludes them. |
| `allChildrenOf` | URL-encoded **IRI**; restricts hits to descendants of that term. |
| `childrenOf` | As above but direct children only. |
| `rows`, `start` | Paging. |
| `fieldList` | Fields to return. See trap 2 for what it will not give you. |

Response shape: `{"response": {"numFound": N, "docs": [...]}}`. Useful doc fields are `obo_id`,
`label`, `synonym`, `ontology_name`, `is_defining_ontology`, `short_form`, `iri`, `type`.

### Trap 1 — `exact=true` is exact *token*, not exact *label*

```
q=liver&ontology=uberon&exact=true                    -> numFound 161
q=liver&ontology=uberon&exact=true&queryFields=label  -> numFound 1
```

With `exact=true` alone, `caudate lobe of liver` matches because the token `liver` appears in its
label. `zzzquux` still returns 0, so the flag does something — just not what its name promises.
Restrict `queryFields` to `label` or `label,synonym`, and re-check exactness client-side anyway.
`resolve_terms.py` classifies every hit as `exact_label`, `exact_synonym`, or `partial` for
exactly this reason.

### Trap 2 — `/search` never reports obsolescence

`is_obsolete` and `term_replaced_by` are **not returned by `/search`**, even when named explicitly
in `fieldList` — the fields are dropped from the response without error. Only the term-detail
endpoint carries them. Search does exclude obsolete terms by default, so search results are safe;
but you cannot use search to check whether an ID *you already have* is still current.

### Trap 3 — `ontology=` does not mean "this prefix"

Ontologies import each other, so a filtered search returns foreign prefixes:

```
q=parasitic infection&ontology=efo  -> includes MONDO:0016472, CL:0001069
q=hepatocyte&ontology=uberon        -> CL:0000182, is_defining_ontology=false
```

Filter on the CURIE prefix yourself if the target field requires one ontology.

### Trap 4 — the same term appears once per importing ontology

A search for `liver` returns `UBERON:0002107` under `uberon` (`is_defining_ontology: true`) and
again under `cl` and `hra` (`false`). Deduplicate on `obo_id` and keep the defining copy.

## `/ontologies/{ontology}/terms?obo_id={CURIE}` — term detail

The authoritative per-term lookup, and the only one that reports obsolescence.

```
GET /ontologies/efo/terms?obo_id=EFO:0001067
  is_obsolete       true
  term_replaced_by  "http://purl.obolibrary.org/obo/MONDO_0005135"
```

`term_replaced_by` is a **full IRI**, not a CURIE. Convert by splitting on the final underscore
(`iri_to_curie` in `ols_client.py`), which also handles multi-underscore prefixes such as
`APOLLO_SV_00000001`.

A missing term returns HTTP **404** with a JSON body, so 404 is a normal answer to check for, not
an exception to crash on.

### Trap 5 — the `obo_id` index has holes

`MONDO:0000001` is defined by MONDO and imported by eleven other ontologies, yet
`?obo_id=MONDO:0000001` returns zero results — OLS never indexed its `obo_id`. Treating that as
"ID does not exist" is a false failure on a live term.

Fall back to `/terms?iri={encoded IRI}`, which returns one copy per ontology; prefer the copy whose
`ontology_name` matches the home ontology and has `is_defining_ontology: true`. `term_detail()` in
`ols_client.py` does this automatically and tags the result with `_resolved_via`.

## `/terms?iri={encoded IRI}` — cross-ontology copies

Returns every ontology's copy of one IRI. Useful for the fallback above and for seeing which
ontologies import a term. `UBERON:0002107` has 42 copies.

## Hierarchy

`_links.hierarchicalAncestors.href` on a term detail gives the transitive ancestors, paged
(`?size=500`, follow `_links.next`). Use it to check that a term sits in the branch a metadata
field requires.

Beware that CARO makes `cell` a descendant of `anatomical structure`, so `CL:0000182` (hepatocyte)
genuinely *is* under `UBERON:0000061`. A branch check alone will not keep cell types out of a
tissue column — constrain the CURIE prefix too.

`/ontologies/{id}/terms/roots` is unreliable for merged ontologies: MONDO's roots list returns bare
numeric ids and unrelated BFO/CHEBI/FOODON entries. Do not build logic on it.

## IRI patterns

Do not template IRIs when you can resolve them. The OBO PURL pattern is not universal:

| Prefix | IRI |
| --- | --- |
| most OBO prefixes | `http://purl.obolibrary.org/obo/{PREFIX}_{local}` |
| `EFO` | `http://www.ebi.ac.uk/efo/EFO_{local}` |
| `Orphanet` | `http://www.orpha.net/ORDO/Orphanet_{local}` |

## Related services

**ZOOMA, Bioregistry, Identifiers.org, and Ontobee** are documented in
`companion-apis.md`. Use `map_terms.py` (ontology filter required) when OLS
search fails on lab shorthand, and `lookup_prefix.py` for prefix/CURIE shape
and landing pages. None of them replace OLS for emitting or validating a term.

**OxO** (`https://www.ebi.ac.uk/spot/oxo/api/...`) is **retired**. It returns an HTML upgrade
notice with HTTP **200**, so a naive `curl | jq` fails confusingly rather than cleanly. For
cross-ontology mappings use the `annotation.database_cross_reference` list on the term detail
(`UBERON:0002107` carries MESH, NCIT, FMA, UMLS, EFO, and others) or a published SSSOM mapping set.
