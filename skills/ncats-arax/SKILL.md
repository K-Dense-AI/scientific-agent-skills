---
name: ncats-arax
description: Queries the NCATS Translator ARAX production API for bounded, typed, provenance-rich one-hop and endpoint-pinned two-hop biomedical knowledge-graph relationships. Use for Biolink-constrained RTX-KG2 lookup, explicit selected-provider ARAX federation, separate entity normalization, qualifier-aware graph traversal, and inspection of TRAPI edge bindings, publications, and knowledge-source provenance. Do not use for inference, ranking, open-ended pathfinding, clinical guidance, or sensitive queries.
allowed-tools: Read Bash
license: MIT
compatibility: Requires Python 3.10+ and outbound HTTPS access to arax.transltr.io. The client uses only the Python standard library and needs no API key. Queries and caller metadata may be publicly visible; never submit sensitive or patient-specific content.
metadata:
  version: "1.0"
  skill-author: neuroepithelial
---

# NCATS ARAX

Use ARAX as a constrained knowledge-graph lookup service. Submit reviewed CURIEs and explicit
Biolink types, preserve the exact TRAPI exchange, inspect query-edge bindings and provenance, and
treat every returned path as a candidate for subsequent verification.

Read [query-contract.md](references/query-contract.md) before constructing a query. Read
[output-schema.md](references/output-schema.md) when interpreting saved artifacts, warnings,
provenance, or partial results.

## Safety boundary

- Use only public, nonsensitive research questions. ARAX status facilities may expose query and
  caller metadata even when `store=false` is requested.
- Do not submit patient information, confidential research questions, unpublished compound
  programs, or proprietary target hypotheses.
- Do not present a returned path as a validated mechanism or clinical recommendation.
- Report a zero as "not returned under these constraints," never as evidence that no relationship
  exists.
- Describe position as unscored response order, never rank.
- Verify important candidates with literature and authoritative databases separately.

## Workflow

1. Normalize free text separately, then review and report the proposed CURIE and category.
2. Choose a typed one-hop query or an exactly two-hop query with both endpoints pinned.
3. Use default RTX-KG2 lookup unless the user explicitly names two to five providers.
4. Acknowledge that the biomedical query is public and choose a new or empty output directory.
5. Run the client once. Do not silently change provider selection or expansion order after a
   failure or empty result.
6. Inspect `summary.json` for bounded bindings and provenance and `response.json` for the exact
   TRAPI payload.
7. Verify scientifically important paths outside ARAX.

## Preflight

Check the production OpenAPI without making a biomedical query:

```bash
python skills/ncats-arax/scripts/arax_client.py preflight
```

The client verifies that the service identifies itself as ARAX, exposes `/query`, and reports a
supported TRAPI version. A nonproduction endpoint or untested TRAPI series requires an explicit
override; neither override changes the fixed query shapes or operations.

## Normalize an entity

Normalization is review-only and never triggers a graph query:

```bash
python skills/ncats-arax/scripts/arax_client.py normalize "primary myelofibrosis" \
  --expected-category biolink:Disease \
  --max-synonyms 10 \
  --acknowledge-public-query \
  --output-dir outputs/normalize-myelofibrosis
```

Review the canonical identifier, name, category, and synonym preview before using a CURIE. Report
all CURIEs and categories regardless of query outcome. A category warning or zero result is a
reason to curate the identifier, not to chain automatically to `/query`.

## One-hop lookup

Pin at least one endpoint and type both nodes:

```bash
python skills/ncats-arax/scripts/arax_client.py one-hop \
  --subject-id CHEBI:31690 \
  --subject-category biolink:SmallMolecule \
  --predicate biolink:affects \
  --object-id NCBIGene:25 \
  --object-category biolink:Gene \
  --qualifier biolink:object_aspect_qualifier=activity_or_abundance \
  --qualifier biolink:object_direction_qualifier=decreased \
  --acknowledge-public-query \
  --output-dir outputs/imatinib-abl1
```

Lookup mode is the default and fixes expansion to `infores:rtx-kg2`. It defaults to 20 results.
Use `--result-limit N` to request 1-50 results; 50 is the hard cap in either mode.

## Endpoint-pinned two-hop lookup

Use exactly one typed, unpinned intermediate node:

```bash
python skills/ncats-arax/scripts/arax_client.py two-hop \
  --subject-id CHEBI:66901 \
  --subject-category biolink:SmallMolecule \
  --predicate-1 biolink:affects \
  --intermediate-category biolink:Gene \
  --predicate-2 biolink:associated_with \
  --object-id MONDO:0009061 \
  --object-category biolink:Disease \
  --qualifier-1 biolink:object_aspect_qualifier=activity_or_abundance \
  --qualifier-1 biolink:object_direction_qualifier=increased \
  --expand-order right-first \
  --acknowledge-public-query \
  --output-dir outputs/ivacaftor-cystic-fibrosis
```

Right-first expansion is the default. If an empty result merits another attempt, run a new query
explicitly with `--expand-order left-first` and keep the runs separate.

## Selected-provider federation

Federation is explicit and accepts two to five named providers:

```bash
python skills/ncats-arax/scripts/arax_client.py one-hop \
  --subject-id CHEBI:31690 \
  --subject-category biolink:SmallMolecule \
  --predicate biolink:affects \
  --object-id NCBIGene:25 \
  --object-category biolink:Gene \
  --mode federated \
  --kp infores:rtx-kg2 \
  --kp infores:molepro \
  --acknowledge-public-query \
  --output-dir outputs/federated-imatinib-abl1
```

Federation defaults to the hard maximum of 50 results. Provider errors may coexist with useful
results; such a run exits 7 after retaining its artifacts and is marked partial.

## Inspect saved provenance

Rebuild a bounded summary without network access:

```bash
python skills/ncats-arax/scripts/arax_client.py summarize \
  --request outputs/ivacaftor-cystic-fibrosis/request.json \
  --response outputs/ivacaftor-cystic-fibrosis/response.json \
  --format text
```

The inspector accepts only the same constrained request shapes and fixed operations that the live
commands generate. Use `--format json` for the normalized view on standard output.

## Interpret results

- Follow each analysis's query-edge bindings; do not summarize every knowledge-graph edge.
- Preserve the physical edge subject, predicate, object, and qualifier values returned by ARAX.
  Returned predicates or qualifier aspects may be more specific than the query constraint.
- Inspect all source objects, including primary, aggregator, supporting-data, upstream-resource,
  and source-record URL fields.
- Treat `publication_availability: not_returned` as missing metadata, not evidence that no
  publications exist.
- Treat missing auxiliary-graph references and provider failures as explicit warnings.
- Consult the raw response whenever the bounded summary omits detail or the service response is
  partial, unfamiliar, or scientifically surprising.

## Deliberate exclusions

The client has no raw-query, workflow, operation, overlay, ranking, inference, link-prediction,
Pathfinder, ARS, batch, all-provider, three-hop, cache, daemon, SDK, MCP, or
natural-language-to-TRAPI surface. Do not work around those limits with direct HTTP calls under
this skill.

## Official references

- [ARAX documentation](https://ncatstranslator.github.io/TranslatorTechnicalDocumentation/architecture/ara/arax/)
- [ARAX production OpenAPI](https://arax.transltr.io/api/arax/v1.4/openapi.json)
- [ARAXi operation documentation](https://github.com/RTXteam/RTX/blob/master/code/ARAX/Documentation/DSL_Documentation.md)
- [Translator Reasoner API](https://github.com/NCATSTranslator/ReasonerAPI)
- [Biolink Model](https://biolink.github.io/biolink-model/)
