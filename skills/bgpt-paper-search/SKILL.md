---
name: bgpt-paper-search
description: Searches BGPT scientific papers by topic or DOI and retrieves claim-level evidence extracted from full text, including experiments, reported statistics, scope, limitations, and provenance. Use for literature reviews, evidence synthesis, and finding experimental details beyond abstracts.
license: MIT
compatibility: Requires a configured remote BGPT MCP connection and internet access to bgpt.pro. A stdio bridge additionally needs Node.js/npm. Paid access requires a BGPT API key configured as an Authorization header.
metadata:
  version: "1.3"
  skill-author: BGPT
  website: https://bgpt.pro/mcp/
  last-reviewed: "2026-09-30"
---

# BGPT Paper Search

## When to use

Use BGPT to find full-text-derived evidence for a research question or a known
DOI. It returns extracted claims and their supporting experiments, rather than
only bibliographic metadata. Use these records to build a traceable evidence
table; they are not a complete systematic-review search or a validated
risk-of-bias assessment.

## Connect

Configure BGPT in the host before use; installing this skill does not register
an MCP server. The provider supports both transports:

| Transport | Endpoint |
| --- | --- |
| Streamable HTTP | `https://bgpt.pro/mcp/stream` |
| SSE | `https://bgpt.pro/mcp/sse` |

Use the host's native remote-MCP configuration when supported. For a host that
uses `mcpServers` JSON and requires a local stdio bridge, this configuration uses
`mcp-remote` (adapt it to the host's actual settings format):

```json
{
  "mcpServers": {
    "bgpt": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://bgpt.pro/mcp/stream", "--transport", "http-only"]
    }
  }
}
```

The published `bgpt-mcp` 1.1.0 npm package is a thin SSE wrapper around
`mcp-remote`, not a local paper database. Its bundled README predates the current
tool contract and pricing. Prefer the native connection or configurable bridge
above. The linked BGPT GitHub repository was unavailable at review time; use
[the current provider documentation](https://bgpt.pro/mcp/) and live tool schema.

Free access needs no key. For paid usage, configure `Authorization: Bearer <key>`
in the host's remote-server headers, using its credential storage. For the bridge,
[`mcp-remote` supports `--header-file`](https://github.com/punkpeye/mcp-remote#custom-headers)
with a local credential file. Do not put `api_key` in an MCP tool call: neither
current tool declares that argument. Authenticate through the connection.

## Search and DOI lookup

Discover the connected server's tools before calling them. The live BGPT 2.14.7
schema reviewed on 2026-09-30 exposes:

| Tool / argument | Contract |
| --- | --- |
| `search_papers.query` | Required string. Use short English search terms. |
| `num_results` | Integer, 1–100; default 16. Set it explicitly to control result use. |
| `days_back` | Optional integer; papers published within the last N days. Omit for all dates. |
| `min_citations` | Optional integer; minimum number of **references cited by the paper**, not citations received. |
| `study_type` | Optional string: `primary study`, `systematic review`, `meta-analysis`, `narrative review`, `protocol`, `dataset`, `commentary`, or `other`. |
| `output_format` | `evidence` (default), `full`, or `legacy`. |
| `lookup_paper.doi` | Required DOI string; also accepts `output_format`. A found paper counts as one result. |

Use the filter arguments instead of putting years or filters into the query.
No Boolean-query grammar, offset, page, or cursor is documented by this schema.
A result limit is not pagination: do not invent continuation arguments or claim
the search enumerates every matching paper. For broader coverage, run explicit
question variants and deduplicate by DOI while retaining the query history.

Search example verified with one public result (invoke through the connected
tool interface):

```json
{"query": "CRISPR human cells", "num_results": 1, "output_format": "full"}
```

Illustrative filtered search (filters were schema-checked, not executed):

```json
{"query": "CRISPR delivery neurons", "num_results": 5, "days_back": 90, "study_type": "primary study", "output_format": "evidence"}
```

For a paper already identified, call `lookup_paper` with its bare DOI rather
than hoping a title search returns that exact paper:

```json
{"doi": "10.1016/j.ymeth.2015.10.014", "output_format": "evidence"}
```

Do not interpret a connection, quota, or tool error as an empty evidence set.
The provider publishes a result allowance, but no numeric request-rate limit
on the reviewed page; avoid assuming unlimited request throughput.

## Read the result contract

Search returns an envelope with a `results` list and `count`; record the returned
`query` too, since the service may rewrite search terms. DOI lookup returns `found`
and a single `result`; handle not-found before reading it. Inspect the MCP
result for tool errors before interpreting the envelope.

- `evidence` gives compact evidence records; empty optional fields may be absent.
- `full` adds legacy paper metadata to the evidence record.
- `legacy` requests the older paper metadata representation. Do not assume every
  paper has all previously advertised fields or a quality score.

The provider says evidence/full formats omit papers without extracted evidence.
However, the live smoke test returned a record with `schema_version: "legacy"`,
`extraction_status: "legacy"`, and an empty `evidence_units` list in both formats.
A returned record therefore does not guarantee claim-level provenance. An empty
search or unfound DOI also does not establish that the paper does not exist.
Retain `doi`, `title`, `publication_date`, and `publication_name` when available,
then inspect `central_claim` and `evidence.evidence_units`. Each unit links its
claim to an experiment, reported statistics, demonstrated scope, and provenance.
Keep the schema version: older records can have a different shape. Legacy full
metadata can contain nulls, numeric strings, and serialized text instead of
native lists; preserve the raw values and never execute them as code.

The provider documents V4 limits of five evidence units per record, two provenance
passages per unit, and 320 characters per passage. These are bounded extractions,
not the complete article. Check `extraction_status`, `normalization_warnings`,
and `evidence.record_provenance`, including truncation information, before synthesis.

## Evidence checks

For each extracted result, retain the DOI and source section, table, or figure.
Verify sample sizes, units, experimental arms, reported statistics, and uncertainty
against the paper before using them in a synthesis. Distinguish author-reported
limitations from extraction-generated interpretations. Preserve contradictory
or mixed evidence and demonstrated scope. If legacy quality scores are present,
use them only as screening aids, not as a study-specific risk-of-bias assessment.

## Allowance and review scope

At the review date the provider advertises 50 free **results** per network,
then $0.02 per returned result. A successful DOI lookup counts as one result;
unfound lookups cost none. Recheck the allowance and pricing before a large
batch. Do not repeatedly retry a quota-exhausted request.

Sources: [provider setup, record formats, and billing](https://bgpt.pro/mcp/),
[live MCP endpoint](https://bgpt.pro/mcp/stream),
[published BGPT wrapper metadata](https://registry.npmjs.org/bgpt-mcp/latest),
and [bridge documentation](https://github.com/punkpeye/mcp-remote).
The tool schemas, one-result full search, matching evidence-format DOI lookup,
and SSE handshake were checked with unauthenticated requests. The public
search/lookup returned a legacy-schema record, not a V4 fixture. Paid
authentication, filtered search behavior, and host-specific configuration were
not tested.
