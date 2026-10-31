# Folklore Clinical Variant Interpretation MCP public contract

Use this reference when constructing calls or interpreting public results.
The original seven-tool execution review was performed 2026-09-30 against adapter 1.5.0, official source commit
`fef7220d66f99c3c021f8eee1cdd6b8ea4b0a64b`, and live discovery/calls. Discover the
live schemas rather than assuming the published adapter source and deployment
are identical.

The four-tool public gene extension was reviewed 2026-10-31 against current
adapter 1.6.0 `tools/list` schemas and the publisher's public gene guide at
`55a332c6dd6bd4650e921c12ac145b8e0f90476a`. Its
separate 2026-10-30 release acceptance flow exercised BRCA1 identity/profile,
section continuation, live literature and ABC1 ambiguity. Older execution
observations below retain their original date; they were not all rerun here.

## Connection

- Endpoint: `https://api.helena.bio/folklore/v1/mcp`
- Authentication: none
- Transport: stateless Streamable HTTP
- Publisher: Helena Bioinformatics
- Registry identity: `io.github.helena-bioinformatics/folklore`
- Reviewed modern protocol: `2026-07-28`

Verify tools with `tools/list` at call time. Do not infer tool availability from
this skill alone.

For direct JSON-RPC POST requests, use `Content-Type: application/json` and
`Accept: application/json, text/event-stream`. Send `MCP-Protocol-Version` plus
`Mcp-Method` equal to the body `method`; for `tools/call`, send `Mcp-Name` equal
to `params.name`. Include the protocol version and client capabilities in
`params._meta`, as in the skill's curl example. The discovery request is:

```bash
curl --silent --show-error --fail-with-body --max-time 60 \
  -X POST https://api.helena.bio/folklore/v1/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'MCP-Protocol-Version: 2026-07-28' \
  -H 'Mcp-Method: tools/list' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{}}}}'
```

`server/discover` is an optional preflight using the same pattern with that
method in both header and body. It reports supported versions and server
metadata, without a stateful initialization exchange. This modern recipe does
not establish compatibility with every legacy MCP client.

## Read the correct response envelope

First handle HTTP failure or a JSON-RPC `error`; then inspect MCP `result.isError`
and `result.structuredContent`. Call that structured object `s` below. Handle any
non-null `s.adapter_error` before reading scientific fields; preserve its `code`,
`message` and `retryable`. Invalid inputs can fail validation before reaching a
scientific status. Retry only a retryable failure, with bounded backoff and any
`Retry-After` guidance. A live HTTP 429 with JSON-RPC code `-32029` was observed;
there is no verified universal request quota to hardcode.

| Tool | Successful structured content |
|---|---|
| `search_variant_evidence` | `s.result.status`; identity at `s.result.identity`; interpretation at `s.result.interpretation`; outer `record_url`, `usage_boundary`, `adapter_error` |
| `search_variant_literature` | Direct `s.status`, `s.variant_result`, and nullable `s.literature`; no extra `s.result` wrapper |
| `get_publication_details` | `s.publication` and `s.usage_boundary`; no scientific `status` field |
| `search_literature_corpus` | `s.results`, `returned_count`, pagination and retrieval metadata; no scientific `status` field |
| Both gene-disease tools | Direct `s.status` (`ok` or `not_found`), `associations`, `pagination`, `source`, `warnings`, `usage_boundary` |
| `resolve_gene` | `s.result.status`, `identity_snapshot_id`, `candidates`, `candidate_total`, `complete` |
| `get_gene_profile` | `s.result.gene_id`, `snapshot_id`, `identity`, `sources`, `sections`; no required scientific `status` field |
| `get_gene_section` | `s.result.status`, `coverage`, `data`, `pagination`, with the same gene/snapshot/section |
| `search_gene_literature` | `s.result.records`, `captured_at`, `capture_sha256`, `returned`, `has_more`, `next_cursor`; no required scientific `status` field |

The evidence envelope has `contract_version: "1"` and its scientific result has
`search_contract_version: "1.0"`. Literature/details/corpus use
`contract_version: "1.0"`; gene-disease uses camel-case `contractVersion: "1.0"`.
Do not impose the evidence envelope on the other tools. Adapter failures for
literature/details/corpus can use the evidence-style envelope with `result: null`;
gene-disease failures contain `adapter_error` and `usage_boundary` directly.
Unrecognized status values or missing required fields are a contract problem,
not an empty result. Each new gene tool has `contract_version: "1"` with
`result`, nullable `record_url`, `usage_boundary` and nullable `adapter_error`.
Handle a non-null adapter error before scientific fields; `result` can be null
on failure. Preserve `available_snapshot_id` if returned, but resolve again
instead of silently substituting it. The usage boundary explicitly requires
professional gene-reference review and excludes patient evaluation, diagnosis,
treatment decisions and changes to variant pathogenicity classification.

Preserve complete structured content. The evidence and literature text fallbacks
for the original variant tools are summaries and need not contain all provenance
or candidate data. The four new gene tools instead return the same complete
envelope as JSON text for text-only clients.

## Public gene profiles in adapter 1.6.0

`resolve_gene` accepts only `query`: one printable public symbol, previous symbol,
alias, HGNC, Ensembl or NCBI Gene identifier, 1–128 characters. Preserve `exact`,
`alias`, `ambiguous`, `not_found` and `withdrawn`, the complete returned candidate
set and its completeness/count metadata. Require explicit selection for
ambiguity; do not choose a replacement for a withdrawn identity. Gene-plus-HGVS
expressions use the variant workflow instead.

After resolution, select `s.result.candidates[].identity.gene_id` and pass
`s.result.identity_snapshot_id` as `snapshot_id`. `gene_id` is a canonical
`HGNC:` identifier with a positive integer; snapshots are 64 lowercase hexadecimal
characters. Both fields are required for each of the other three new tools.
Do not fabricate values or carry a snapshot from another gene/profile.

`get_gene_profile` preserves these thirteen sections: `overview`,
`disease_validity`, `structure`, `constraint`, `dosage`, `mechanisms`,
`clinical_variants`, `clinical_variant_consequences`, `expression`, `gwas`,
`phenotypes`, `protein_pathways` and `literature`.

`get_gene_section` additionally requires one `section` from that set. Optional
`limit` is 1–50 (default 20); optional `cursor` is the returned opaque continuation
for that exact gene, snapshot and section. Preserve source assemblies/releases,
assertions, links, coverage, limitations, nulls, `total`, `observed_total` and
count units. An unknown total is not zero; overlapping clinical axes are not
additive, and mirrored assertions are not independent votes. Native GRCh37
transcript rows are reference evidence, not newly supported variant inputs.
Unavailable/unintegrated evidence differs from a source having no record.
For `snapshot_unavailable`, restart resolution and reload the entire profile;
never mix pages from different snapshots or construct/repair opaque cursors.

`search_gene_literature` takes the same resolved gene/snapshot, optional `limit`
1–25 (default 20), `sort` of `relevance`, `newest` or `oldest` (default relevance),
and an optional opaque cursor from the same gene/snapshot/sort capture. Preserve
`captured_at`, `capture_sha256`, records, match labels, source links, degradation
and continuation fields. Abstracts are excluded: do not append/hydrate them into
this capture. Live query-matched discovery is not guaranteed exact gene filtering
or curated gene-disease evidence; keep it separate from the immutable profile's
literature section. Gene validity, dosage, constraint and GWAS do not by
themselves establish variant pathogenicity or a patient diagnosis.

## `search_variant_evidence`

Required input:

```yaml
assembly: GRCh38
query: <one public germline nuclear SNV or simple indel>
```

`query` is 1–512 characters. `assembly` defaults to `GRCh38`, but send it
explicitly for reproducibility. The schema forbids additional arguments.
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
For ambiguity, preserve `total_candidate_count` and `candidates_truncated`;
the candidate list may contain only the first ten. For resolution, reuse
`s.result.identity.canonical_key`. Check `s.result.interpretation.status`:
`success` permits reading the returned classification, whereas `unavailable`
requires preserving its error despite a resolved identity.

## `search_variant_literature`

Use only after resolution when composing an automatic workflow:

```yaml
assembly: GRCh38
query: <returned canonical_key>
question: <optional public scientific focus>
limit: <1 to 25>
```

The optional `question` is 3–500 characters, `limit` defaults to 10, and there is
no cursor/offset argument for this tool. The response preserves the variant
result at `s.variant_result` and returns literature at `s.literature` only when
variant resolution permits it. Preserve `candidate_count`, aliases, corpus
provenance and limitations; `limit` does not make a page exhaustive. Publication
match types are `exact_variant`, `variant_alias`, and `gene_association`.

## `get_publication_details`

Input `{"pmid":"<returned PMID>"}`, a string of 1–12 digits without a `PMID:`
prefix. Preserve `publication.is_retracted`, bibliographic metadata, source URLs,
gene mentions, and variant mentions. A `publication_not_found` adapter error
means no record in this service's corpus, not that the PMID does not exist in
PubMed. A missing abstract or full-text URL is not a missing publication.

## `search_literature_corpus`

Use for source-linked scientific-literature discovery with a natural-language
question, publication identifier, gene, variant, phenotype, HPO, or OMIM
concept. Arguments are `query` (3–200 characters), `limit` (1–25, default 20),
`sort` (`relevance`, `newest`, `oldest`; default `relevance`) and optional `cursor`.
Keep all queries public and nonsensitive.

Use `has_more` and the opaque `next_cursor` for continuation with the same query
and sort order. Stop if continuation is absent; report a contradictory pagination
state rather than inventing a cursor. Keep result `match_types`, scores and
`article_entities` with their source/normalization metadata; these are retrieval
signals, not pathogenicity probabilities. Corpus match types are not restricted
to the three variant-literature types above.

Report `semantic_index_used` and any `semantic_degraded_reason`. The live service
also advertised and returned `graph_used`, `graph_version`, and
`graph_degraded_reason` on the review date, although the pinned public adapter's
corpus model did not declare them. Retain such fields as returned metadata; do
not assume their presence or infer graph/semantic success from HTTP 200 alone.

## Gene-disease assertions in adapter 1.5.0

Request examples (not captured scientific results):

```json
{"name":"get_gene_disease_associations","arguments":{"gene":"BRCA1","limit":20,"offset":0}}
```

```json
{"name":"search_disease_genes","arguments":{"disease":"Marfan","limit":20,"offset":0}}
```

The gene lookup accepts an exact gene symbol or HGNC identifier (1–64
characters). Disease lookup accepts an exact `MONDO:` plus seven digits or a
public disease-name substring (3–160 characters). Both have limit 1–50 (default
20) and offset 0–1000 (default 0). Preserve distinct disease matches and follow
`pagination.nextOffset` while present. Do not invent offsets beyond 1000. When
the ceiling prevents completion, `nextOffset` can be null while rows remain;
preserve the warning and compare `offset + len(associations)` with `total` before
calling retrieval complete. An out-of-range page can be empty with `status: ok`
when `total > 0`; `not_found` means `total == 0`.

Successful structured output directly carries query, associations, pagination, source, warnings and usage_boundary. Read JSON-RPC and adapter errors before interpreting output. The source is ClinGen Gene-Disease Validity; preserve assertion-specific inheritance, assessment, source links and dates. Missing source values stay unavailable. No result does not establish no association, and association validity is not variant pathogenicity.

Record `source.version`, `source.snapshotSha256`, and `source.downloadUrl`.
These describe the deployed local snapshot and do not guarantee the newest
ClinGen release. Preserve source assertions separately, including disputed
assessments; avoid collapsing them into a single gene-wide classification.

## Reviewed sources and execution scope

- [Public gene workflow, 1.6.0](https://github.com/helena-bioinformatics/folklore-mcp/blob/55a332c6dd6bd4650e921c12ac145b8e0f90476a/docs/PUBLIC_GENE_PROFILES.md)
- [Public server card and input schemas](https://folklore.helena.bio/.well-known/mcp/server-card.json)
- [Hosted technical guide](https://folklore.helena.bio/integrations/mcp)
- [Protocol compatibility](https://github.com/helena-bioinformatics/folklore-mcp/blob/fef7220d66f99c3c021f8eee1cdd6b8ea4b0a64b/docs/COMPATIBILITY.md)
- [Tool response construction](https://github.com/helena-bioinformatics/folklore-mcp/blob/fef7220d66f99c3c021f8eee1cdd6b8ea4b0a64b/src/folklore_mcp_service/presentation/mcp.py)
- [Variant contracts](https://github.com/helena-bioinformatics/folklore-mcp/blob/fef7220d66f99c3c021f8eee1cdd6b8ea4b0a64b/src/folklore_mcp_service/domain/contracts.py)
- [Literature contracts](https://github.com/helena-bioinformatics/folklore-mcp/blob/fef7220d66f99c3c021f8eee1cdd6b8ea4b0a64b/src/folklore_mcp_service/domain/literature_contracts.py)
- [Gene-disease contracts](https://github.com/helena-bioinformatics/folklore-mcp/blob/fef7220d66f99c3c021f8eee1cdd6b8ea4b0a64b/src/folklore_mcp_service/domain/gene_disease_contracts.py)

The 2026-09-30 live read-only public requests verified discovery, ambiguity, resolved identity,
variant-linked literature, publication details, both gene-disease tools, and
corpus/gene pagination. Eleven successful captured responses passed validation
against their live tool output schemas; invalid-argument calls returned typed
adapter errors separately.
The unavailable/degraded branches and the gene-disease pagination ceiling were
source-reviewed, not forced in the live service. These checks establish observed
protocol behavior, not clinical accuracy, source completeness, or host UI support.

## Interpretation boundary

- Folklore Clinical Variant Interpretation MCP accepts no patient, phenotype,
  family, segregation, or private case data.
- Results support qualified professional review.
- Results are not a diagnosis or treatment recommendation.
- Literature associations do not alter an ACMG/AMP classification.
- An empty bounded result does not establish universal absence.
