---
name: folklore-variant-evidence
description: "Provides ACMG/AMP germline variant classification, gene profiles, disease associations and literature through Folklore MCP. Used for one public GRCh38 germline nuclear SNV or simple indel smaller than 50 bp, public gene identity/profile review, ClinGen assertions, and source-linked literature. Preserves explicit resolution states, ambiguous-identity selection, snapshot continuity and provenance."
license: MIT
compatibility: Requires network access to api.helena.bio (stateless Streamable HTTP MCP, no credentials) and a host supporting its advertised protocol, or curl for direct JSON-RPC POST requests.
metadata:
  version: "1.4"
  last-reviewed: "2026-11-01"
  skill-author: "Helena Bioinformatics"
  website: "https://folklore.helena.bio"
  github: "https://github.com/helena-bioinformatics/folklore-mcp"
---

# Folklore Variant Evidence

Folklore MCP 1.7.0 provides ACMG/AMP germline variant classification, gene
profiles, disease associations and literature through eleven tools. Classify one
public GRCh38 germline nuclear SNV or simple indel smaller than 50 bp with
`classify_germline_variant`. Resolve public genes into source-qualified profiles,
retrieve ClinGen assertions, and explore source-linked literature. Preserve
explicit outcome states, identity selections, source provenance and snapshots.
This MIT collection skill has its own version, separate from the Apache-2.0
adapter and the publisher's skill.

Folklore Clinical Variant Interpretation MCP is published by Helena
Bioinformatics. Its hosted endpoint is:

```text
https://api.helena.bio/folklore/v1/mcp
```

No account or API key is required. The public Apache-2.0 adapter and contract are
available at <https://github.com/helena-bioinformatics/folklore-mcp>.

## Minimal connection example

Illustrative request for a host without native MCP support; this updated
example was schema-reviewed, not executed as a scientific call:

```bash
curl --silent --show-error --fail-with-body --max-time 60 \
  -X POST https://api.helena.bio/folklore/v1/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'MCP-Protocol-Version: 2026-07-28' \
  -H 'Mcp-Method: tools/call' \
  -H 'Mcp-Name: classify_germline_variant' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{}},"name":"classify_germline_variant","arguments":{"assembly":"GRCh38","query":"rs80357914"}}}'
```

The routing headers must match the JSON-RPC method and tool name. A successful
HTTP response is not sufficient: inspect JSON-RPC `error`, then
`result.structuredContent.adapter_error`, then this tool's
`result.structuredContent.result.status`. Other tools use different response
shapes; use the [contract table](references/mcp-contract.md).

Inspect the returned outcome before continuing. This example can return
`ambiguous` with multiple candidates: stop and request an unambiguous public
variant notation instead of selecting a candidate automatically.

## Select the right skill

Use this skill when the task is one public variant to structured Folklore
evidence, explicit resolution-state handling, variant-linked literature, public
gene identity/profile review, or ClinGen gene-to-disease/disease-to-gene assertions.

- Use `database-lookup` for broad direct queries across ClinVar, dbSNP, gnomAD,
  Ensembl VEP, COSMIC, or multiple databases.
- Use `genomic-coordinates` first when the assembly, coordinate convention,
  contig name, or variant representation is uncertain.
- Do not use this skill for VCF annotation, batch processing, somatic variants,
  structural variants, polygenic scores, or patient-specific interpretation.

Folklore Clinical Variant Interpretation MCP complements those skills with one
source-linked public evidence contract. It does not replace direct database
review or qualified clinical judgment.

## Enforce the input boundary

Before a variant tool call:

1. Extract exactly one public variant identifier or notation.
2. Require GRCh38 and a germline nuclear SNV or simple insertion/deletion shorter
   than 50 base pairs. An unsupported assembly may be rejected by the input
   schema before any scientific `unsupported` status exists.
3. Remove or refuse patient names, case identifiers, phenotypes, family history,
   segregation evidence, clinical records, uploaded files, and other private or
   patient-specific context.
4. If the task depends on patient context, stop and explain that Folklore
   Clinical Variant Interpretation MCP does not accept or evaluate it.
5. Never transform a patient-specific request into a public variant query while
   implying that the result answers the patient-specific question.

Accepted public variant forms include genomic coordinates, genomic/coding/
protein HGVS, SPDI, rsID, or a `canonical_key` returned by Folklore Clinical
Variant Interpretation MCP.

## Verify the live tool catalog

Connect to the hosted endpoint and call `tools/list`. Verify the available tools
instead of relying on model memory. The documented public catalog contains:

- `classify_germline_variant`
- `search_variant_literature`
- `get_publication_details`
- `search_literature_corpus`
- `get_gene_disease_associations`
- `search_disease_genes`
- `resolve_gene`
- `get_gene_profile`
- `get_gene_section`
- `search_gene_literature`

These are ten scientific tools. The separate eleventh tool `support_helena` is
not scientific evidence; use it only when explicitly requested.

If discovery or a tool call fails, preserve the failure as an availability
problem. Do not reinterpret it as lack of scientific evidence.

Read [the public MCP contract](references/mcp-contract.md) before composing tool
calls or interpreting response states.

## Resolve a public gene and review its profile

1. Call `resolve_gene` with one printable public gene symbol, previous symbol,
   alias, HGNC, Ensembl or NCBI Gene identifier (1–128 characters). Gene-plus-HGVS
   expressions belong in `classify_germline_variant`. Send no patient narrative.
2. Read transport/JSON-RPC errors and `adapter_error` first. Preserve resolver
   statuses `exact`, `alias`, `ambiguous`, `not_found` and `withdrawn`. Show every
   returned candidate for ambiguity and require explicit selection. Never choose
   the most familiar gene, substitute a withdrawn identity or interpret a bounded
   miss as biological absence.
3. Use the selected candidate's `identity.gene_id` and the resolver's
   `identity_snapshot_id` as `snapshot_id` for `get_gene_profile`. Preserve the
   returned identity, snapshot, sources and all thirteen sections; do not infer a
   variant classification from gene-disease validity, constraint, dosage or GWAS.
4. Continue a section with `get_gene_section`, the same gene/snapshot/section and
   its opaque returned cursor. `limit` is 1–50, default 20. Preserve assertions,
   assemblies, releases, source links, coverage, limitations, nulls, `total`,
   `observed_total` and count units. Do not sum overlapping axes or count mirrored
   assertions as independent votes. Unavailable or unintegrated evidence differs
   from a source having no record. Native GRCh37 transcript evidence does not
   expand the GRCh38 variant-input boundary.
5. For `snapshot_unavailable`, restart resolution and reload the whole profile.
   Do not combine snapshots, reuse mismatched cursors, or repair a cursor/hash.

Illustrative `tools/call` parameter templates, not captured scientific results.
First resolve:

```json
{"name":"resolve_gene","arguments":{"query":"BRCA1"}}
```

After selecting the returned identity, read its profile:

```json
{"name":"get_gene_profile","arguments":{"gene_id":"HGNC:1100","snapshot_id":"<returned identity_snapshot_id>"}}
```

Read an initial section page (no cursor):

```json
{"name":"get_gene_section","arguments":{"gene_id":"HGNC:1100","snapshot_id":"<same returned snapshot_id>","section":"structure","limit":20}}
```

Replace every placeholder with the selected resolver's actual values; do not
send fabricated snapshots or assume an arbitrary query resolves to HGNC:1100.
The reference lists sections, envelopes and pagination contracts. Gene profiles
are public reference evidence for professional review, not patient diagnosis,
treatment recommendations or variant pathogenicity classifications.

### Separate live gene literature

Call `search_gene_literature` with the selected `gene_id` and `snapshot_id`.
`limit` is 1–25, default 20; `sort` is `relevance`, `newest` or `oldest`. Continue
only with the returned opaque cursor for the same gene/snapshot/sort capture.
Preserve capture time/hash, publications, source links, match labels, degradation
and pagination. Query-matched discovery is not guaranteed exact gene filtering
or curated gene-disease evidence. Keep this abstract-free live capture separate
from the immutable profile's literature section; do not append abstracts to it
or treat either source as a change to variant classification.

## Retrieve gene-disease assertions

Use `get_gene_disease_associations` for one exact gene symbol or HGNC identifier, or `search_disease_genes` for an exact MONDO identifier or public disease-name substring. Both accept `limit` (default 20, 1–50) and `offset` (default 0, 0–1000). See the reference for request examples. This is a separate source lookup and requires no variant input or assembly.

Preserve each returned disease identity, inheritance, evidence assessment, source
URL, date, `source.version` and `source.snapshotSha256`. This is a local ClinGen
snapshot, not a guarantee of the latest ClinGen release. Follow
`pagination.nextOffset` while it is present; preserve pagination-ceiling warnings.
An empty page after the total has been passed does not mean the initial query had
no matches. Do not combine distinct diseases or silently choose among name matches.
Gene-disease validity does not classify a particular variant. A `not_found`
response means no matching assertion in the available source, not no association.
No patient, phenotype, family, segregation, private case data or sequencing files
may be sent. Qualified professional review remains required.

## Run the variant-classification workflow

### 1. Resolve and classify the variant

Call `classify_germline_variant` with:

```text
assembly: GRCh38
query: <one public variant identifier or notation>
```

Do not add phenotype, disease, patient, family, or treatment context to this
call. Preserve the returned contract fields, source links and scientific
limitations.

### 2. Branch on the returned status

Read transport/JSON-RPC errors and `adapter_error` first. For
`classify_germline_variant`, let `envelope = result.structuredContent`; only if
`envelope.result` is non-null, branch on `envelope.result.status`. An
`invalid_arguments` adapter error is distinct from scientific `invalid_request`.
Preserve `isError` and any typed failure, including `resolution_unavailable`.
Treat the status as a control-flow value, not prose:

| Status | Required action |
|---|---|
| `resolved` | Reuse the returned `canonical_key`; review the structured interpretation, provenance, source links, and limitations. |
| `ambiguous` | Show the returned candidates and ask for an explicit public variant selection. Never choose a candidate automatically. |
| `not_found` | Report that no result was found within this service and query scope. Do not claim universal absence. |
| `invalid_request` | Report the validation problem and request a corrected public variant. Do not silently reinterpret the input. |
| `unsupported` | State the relevant service boundary and stop. Do not force the query into a supported form. |
| `resolution_unavailable` | Report a temporary resolution or availability failure. Do not treat it as evidence absence. |

Only a `resolved` result may proceed automatically into a variant-linked
literature workflow. Its canonical key is `envelope.result.identity.canonical_key`.
If `envelope.result.interpretation.status` is `unavailable`, preserve its typed
error; identity resolution has succeeded, but classification has not. Do not read
or invent a classification for that outcome.

### 3. Review the evidence without overclaiming

For a resolved result:

- Present the returned variant identity and `canonical_key`.
- Preserve the automated variant-level ACMG/AMP decision-support result exactly
  as returned.
- Cite the returned public sources and provenance.
- Keep submitted ClinVar assertions separate from Folklore's automated result,
  as required by the [upstream interpretation guidance](https://github.com/helena-bioinformatics/folklore-mcp).
  If they disagree, report each assertion with its source/date and preserve
  the disagreement; do not present a merged consensus classification.
- Separate returned facts from the agent's synthesis.
- State that qualified professional review is required.
- Do not turn the result into a diagnosis, individual risk estimate, treatment
  recommendation, or standalone clinical report.

## Chain into literature

### Variant-linked literature

After a resolved evidence call, pass the returned `canonical_key` to
`search_variant_literature`. Keep `assembly` as `GRCh38`. An optional `question`
may narrow the literature focus, but it must remain a public scientific question
and must not contain patient context.

Distinguish each result's match type:

- `exact_variant`: direct match to the resolved variant
- `variant_alias`: match through a reported alias
- `gene_association`: broader gene-level association, not variant-specific proof

Literature associations do not alter the returned ACMG/AMP classification.

### Publication details

Call `get_publication_details` only with a PMID returned by the literature tools.
Preserve PubMed URLs, DOI/PMCID fields when present, retraction status, and the
distinction between gene mentions and variant mentions.

### Semantic corpus search

Use `search_literature_corpus` for a public natural-language scientific question
or for discovery by publication identifier, gene, variant, phenotype, HPO, or
OMIM concept. Treat results as source-linked candidates for professional review.
A zero-result response means no result was returned for that bounded query, not
that no relevant publication exists anywhere.

The query is 3–200 characters, with `limit` 1–25 and `sort` set to `relevance`,
`newest`, or `oldest`. For another page, reuse the returned opaque `next_cursor`
with the same query and sort; do not construct an offset. Keep `match_types` and
`article_entities` distinct from variant-literature match types. Report
`semantic_index_used` and `semantic_degraded_reason`; a returned lexical match
does not prove semantic retrieval worked. Preserve additional retrieval metadata
returned by the live service.

Do not place patient information into a corpus query, even if the query is not
variant-specific.

## Report a reproducible result

Include:

1. The exact public query and `GRCh38` assembly for variant calls; for gene
   profiles, the selected gene identity, snapshot and native source assemblies.
2. The returned outcome fields and, for a resolved variant, the `canonical_key`.
3. The structured evidence or literature result without changing its meaning.
4. Source links and publication identifiers.
5. Match type for literature results.
6. Access date and any availability limitation.
7. For gene results, distinguish immutable reference snapshots from live
   literature captures. Report variant classifications as returned, with their
   scope, sources and scientific limitations. Gene evidence alone does not
   classify a variant; patient diagnosis requires a separate clinical workflow.

## Illustrative ambiguity smoke test

The following template describes an ambiguity test; it was not rerun for the
2026-11-01 documentation update:

```text
Call classify_germline_variant with assembly GRCh38 and query rs80357914. If the
result is ambiguous, list the returned candidates and stop for explicit
selection. Do not select a candidate or call downstream literature tools.
```

The ambiguity branch passes only if an ambiguous response causes the workflow to
stop without automatic candidate selection. If the live response changes, record
the actual status; a resolved response does not test ambiguity handling.

On 2026-09-30, live discovery reported adapter 1.5.0 and protocol 2026-07-28.
The rsID example returned `ambiguous`; a separate public HGVS query resolved and
was chained through its returned key to literature and a returned PMID. Corpus
cursor pagination and gene-disease offset pagination were exercised. These are
dated protocol checks, not validation of clinical accuracy. See the reference
for exact response shapes and source/live differences.

On 2026-10-31, current public discovery advertised adapter 1.6.0 and all eleven
tools. The public gene guide and new four input/output schemas were reviewed;
the release's 2026-10-30 public acceptance flow exercised BRCA1 resolution,
profile/section continuation, live gene literature and preserved ABC1 ambiguity.
This does not repeat the older seven-tool execution checks or validate clinical
accuracy. No synthetic patient data or inferred scientific result is required.

On 2026-11-01, the public server card advertised adapter 1.7.0 and eleven tools.
This schema review updated the current tool name to `classify_germline_variant`,
the VUS prompt name to `assess_vus`, and response contract versions to `2`.
No scientific calls were executed for this update. The older dated execution
observations above remain historical evidence.

## Official references

- Integration setup: <https://folklore.helena.bio/integrations>
- Technical guide: <https://folklore.helena.bio/integrations/mcp>
- Public adapter and contract: <https://github.com/helena-bioinformatics/folklore-mcp>
- Public gene workflow: <https://github.com/helena-bioinformatics/folklore-mcp/blob/main/docs/PUBLIC_GENE_PROFILES.md>
- Official MCP Registry identity: `io.github.helena-bioinformatics/folklore`
