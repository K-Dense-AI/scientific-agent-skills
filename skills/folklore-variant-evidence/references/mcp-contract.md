# Folklore Clinical Variant Interpretation MCP public contract

Use this reference when constructing calls or interpreting public results. The
public adapter repository is the source for the exact live schemas:
<https://github.com/helena-bioinformatics/folklore-mcp>.

## Connection

- Endpoint: `https://api.helena.bio/folklore/v1/mcp`
- Authentication: none
- Transport: stateless Streamable HTTP
- Publisher: Helena Bioinformatics
- Registry identity: `io.github.helena-bioinformatics/folklore`

Verify tools with `tools/list` at call time. Do not infer tool availability from
this skill alone.

## `search_variant_evidence`

Required input:

```yaml
assembly: GRCh38
query: <one public germline nuclear SNV or simple indel>
```

The `query` may be a coordinate, genomic/coding/protein HGVS, SPDI, rsID, or a
returned `canonical_key` in this form:

```text
GRCh38:chrN:position:REF:ALT
```

The six public outcome states are:

- `resolved`
- `ambiguous`
- `not_found`
- `invalid_request`
- `unsupported`
- `resolution_unavailable`

Do not collapse these states. In particular, never convert `ambiguous` into
`resolved`, and never convert `resolution_unavailable` into `not_found`.

## `search_variant_literature`

Use only after resolution when composing an automatic workflow:

```yaml
assembly: GRCh38
query: <returned canonical_key>
question: <optional public scientific focus>
limit: <1 to 25>
```

The response preserves the variant result and returns literature only when the
variant resolution permits it. Publication match types are `exact_variant`,
`variant_alias`, and `gene_association`.

## `get_publication_details`

Input one PMID returned by a literature tool, as digits without a `PMID:`
prefix. Preserve the returned bibliographic metadata, source URLs, retraction
status, gene mentions, and variant mentions.

## `search_literature_corpus`

Use for source-linked scientific-literature discovery with a natural-language
question, publication identifier, gene, variant, phenotype, HPO, or OMIM
concept. Inspect the live input schema for current bounds and optional controls.
Keep all queries public and nonsensitive.

## Gene-disease assertions in adapter 1.5.0

Request examples (not captured scientific results):

```json
{"name":"get_gene_disease_associations","arguments":{"gene":"BRCA1","limit":20,"offset":0}}
{"name":"search_disease_genes","arguments":{"disease":"Marfan","limit":20,"offset":0}}
```

The gene lookup accepts an exact gene symbol or HGNC identifier. Disease lookup accepts an exact MONDO identifier or a disease-name substring. Both have limit 1–50 and offset 0–1000. Preserve distinct disease matches and returned pagination; one page is not an exhaustive catalogue.

Successful structured output directly carries query, associations, pagination, source, warnings and usage_boundary. Read JSON-RPC and adapter errors before interpreting output. The source is ClinGen Gene-Disease Validity; preserve assertion-specific inheritance, assessment, source links and dates. Missing source values stay unavailable. No result does not establish no association, and association validity is not variant pathogenicity.

## Interpretation boundary

- Folklore Clinical Variant Interpretation MCP accepts no patient, phenotype,
  family, segregation, or private case data.
- Results support qualified professional review.
- Results are not a diagnosis or treatment recommendation.
- Literature associations do not alter an ACMG/AMP classification.
- An empty bounded result does not establish universal absence.
