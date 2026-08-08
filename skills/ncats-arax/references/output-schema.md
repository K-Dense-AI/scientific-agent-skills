# ARAX artifact and output contract

## Contents

- [Artifact sets](#artifact-sets)
- [Exact byte preservation](#exact-byte-preservation)
- [Query summary](#query-summary)
- [Normalization and preflight summaries](#normalization-and-preflight-summaries)
- [Provenance interpretation](#provenance-interpretation)
- [Truncation and completeness](#truncation-and-completeness)
- [Manifest](#manifest)
- [Warnings and exit codes](#warnings-and-exit-codes)

## Artifact sets

Every graph query requires a new or empty output directory and writes:

```text
request.json
response.json
summary.json
manifest.json
```

Normalization writes the exact entity response, a bounded normalization summary, and a manifest.
Preflight writes the exact OpenAPI response, a service summary, and a manifest only when an output
directory is requested. GET commands do not create a fictitious `request.json`; the corresponding
manifest file, byte, and hash fields are null. Offline `summarize` writes nothing.

Reject an existing nonempty directory before network access. Write artifacts through a private
temporary file, flush and `fsync`, set mode `0600` where supported, and atomically replace the final
path. Write the manifest last.

## Exact byte preservation

Serialize a POST body once with sorted keys, compact separators, UTF-8, and `ensure_ascii=False`.
Save and send that same byte string. Request `Accept-Encoding: identity`, save the raw response
before JSON parsing, and hash request and response bytes with SHA-256.

Read at most 26,214,401 response bytes. If the extra byte exists, treat the response as oversized,
save no partial `response.json`, retain the request when applicable, write a terminal manifest, and
exit 6. A bounded HTTP-error body is preserved exactly. A bounded malformed JSON response is also
preserved, but no misleading summary is produced.

## Query summary

`summary.json` is a normalized bounded view; `response.json` remains authoritative.

```json
{
  "schema_version": "1.0",
  "query": {
    "kind": "one-hop|two-hop",
    "mode": "lookup|federated",
    "provider_ids": [],
    "expand_order": "right-first|left-first|null",
    "qnode_ids": {},
    "result_limit": 20
  },
  "service": {
    "base_url": null,
    "arax_version": null,
    "trapi_version": null,
    "biolink_version": null
  },
  "counts": {
    "results_returned": 0,
    "results_summarized": 0,
    "analyses_summarized": 0,
    "bound_edges_summarized": 0,
    "knowledge_graph_nodes": 0,
    "knowledge_graph_edges": 0,
    "server_total_results_count": null
  },
  "truncation_status": "no|possible|confirmed",
  "completeness": "complete|partial|unknown",
  "results": [],
  "warnings": []
}
```

Keep response order. A result contains its one-based unscored `position`, bounded description,
normalized node bindings, and separate analyses. Each analysis contains its resource ID, returned
score, support-graph IDs, and bound-edge objects grouped by query-edge key.

A bound-edge object contains the returned edge ID, physical subject/predicate/object and names,
query-direction match flag, qualifiers, full source objects, role-derived source ID lists,
publication IDs and availability, and support-graph IDs and status.

## Normalization and preflight summaries

A normalization summary records the input, expected category, whether free-text confirmation is
required, service versions, canonical identifier/name/category, category-count mapping, total
synonym count, bounded candidate preview, and warnings.

A preflight summary records service versions plus Boolean checks for ARAX identity, `/query`, and
version compatibility. Neither summary claims graph results.

## Provenance interpretation

Use each analysis's `edge_bindings` to select knowledge-graph edges. Do not include unrelated graph
edges. Preserve multiple analyses separately and retain all entries from each bound edge's
`sources`, including `resource_id`, `resource_role`, `upstream_resource_ids`, and
`source_record_urls`. Derive unique, first-seen resource ID lists for primary, aggregator, and
supporting-data roles without discarding the full objects.

Preserve returned qualifiers as type/value pairs. Preserve physical edge direction and set
`matches_query_direction: false` rather than rewriting a reversed edge.

V1 recognizes `biolink:publications` edge attributes. Accept a string or list of strings and
deduplicate in first-seen order. Missing recognized metadata means:

```text
publication_ids: []
publication_availability: not_returned
```

It never means that no publications exist.

Use `analysis.support_graphs` as the support-graph references. If none are returned, report
`not_returned`; if all appear in `message.auxiliary_graphs`, report `available`; if a referenced ID
is absent, report `missing` and warn.

## Truncation and completeness

- Fewer results than the requested limit: `no`, unless logs or counts show removal.
- Exactly the limit: `possible` and `RESULT_LIMIT_REACHED`.
- More than the limit, an explicit pruning/removal log, or a larger server total: `confirmed`.

Keep only the first requested number of results in the normalized summary while preserving the
entire size-bounded raw response.

Federated KP timeout, provider error, or malformed-provider evidence yields `completeness: partial`,
`result_status: partial`, retained artifacts, and exit 7. Otherwise a valid parsed response is
`complete`; raw malformed responses produce no summary.

## Manifest

The manifest records run UUID, UTC timestamps, command, execution/result status, privacy
acknowledgment, fixed client identity, service versions, request/response method, URL, filenames,
byte counts, hashes, elapsed time, applied limits, attempt counts, artifact names, bounded error,
and warnings. Fields for artifacts that do not exist are null rather than false filenames.

Execution statuses are `success`, `http_error`, and `client_error`. Result statuses are `results`,
`no_results`, `partial`, and `not_available`.

## Warnings and exit codes

Warnings are objects with a stable `code`, bounded sanitized `message`, and a small scalar
`context`. Supported codes:

```text
PUBLIC_QUERY
NORMALIZATION_REQUIRES_CONFIRMATION
NORMALIZATION_CATEGORY_MISMATCH
NO_RESULTS
NO_PUBLICATIONS_RETURNED
NO_PRIMARY_SOURCE_RETURNED
UNSCORED_RESPONSE_ORDER
RESULT_LIMIT_REACHED
INTERNAL_PRUNING_DETECTED
KP_TIMEOUT
KP_ERROR
MALFORMED_KP_RESPONSE
MISSING_AUXILIARY_GRAPH
REVERSED_EDGE_BINDING
UNTESTED_SERVICE_VERSION
NONPRODUCTION_ENDPOINT
```

Exit codes:

| Code | Meaning |
| ---: | --- |
| 0 | Complete success, including a valid zero-result graph response |
| 2 | Invalid CLI input, unsupported saved request, or local validation failure |
| 3 | Service preflight or unsupported-version failure |
| 4 | Normalization returned no usable result |
| 5 | Transport or HTTP failure |
| 6 | Malformed, oversized, or artifact-integrity failure |
| 7 | Partial federated response with retained artifacts |

Text output prints at most the bounded result set and ten publication IDs per edge, labels every
position unscored, includes all source-role IDs, and points to `summary.json` and `response.json`.
Use "ARAX returned" and "not returned under these constraints," never proof, absence, or ranking
language.
