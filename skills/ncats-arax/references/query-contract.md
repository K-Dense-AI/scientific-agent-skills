# ARAX query contract

## Contents

- [Service boundary](#service-boundary)
- [Supported query shapes](#supported-query-shapes)
- [Validation](#validation)
- [Fixed operations](#fixed-operations)
- [Limits and retries](#limits-and-retries)
- [Version and endpoint policy](#version-and-endpoint-policy)
- [Excluded escape hatches](#excluded-escape-hatches)

## Service boundary

Use `https://arax.transltr.io/api/arax/v1.4` by default. A networked command first retrieves
`/openapi.json`, verifies an ARAX title and `/query`, and records the advertised ARAX and TRAPI
versions. Normalization uses `/entity`; graph lookup uses `/query`.

Every normalization or graph request requires `--acknowledge-public-query`. This is an explicit
acknowledgment that query and caller metadata may be visible through service facilities. The
`store=false` operation reduces intentional response storage but is not a privacy guarantee.

## Supported query shapes

### One hop

Use two qnodes (`n0`, `n1`) and one qedge (`e0`). Require one category on each qnode, one to five
predicates, and at least one pinned endpoint. Each qnode has at most one CURIE. Omit `ids` from an
unpinned qnode.

### Two hops

Use three qnodes (`n0`, `n1`, `n2`) and two qedges (`e0`, `e1`). Pin `n0` and `n2` with exactly one
CURIE each. Type every qnode. Keep `n1` unpinned. Each edge has one to five predicates.

For either shape, an edge may have zero to six qualifiers. Combine them in one
`qualifier_constraints` entry containing one AND-conjoined `qualifier_set`. Omit the whole field
when no qualifier is supplied. Do not repeat a qualifier type on the same edge.

## Validation

CURIEs follow this conservative form:

```text
^[A-Za-z][A-Za-z0-9._-]*:[^\s]+$
```

They must be no more than 200 characters and contain no controls, NUL, tabs, or newlines.

Categories, predicates, and qualifier types follow:

```text
^biolink:[A-Za-z][A-Za-z0-9._-]*$
```

Provider identifiers are interpolated into an ARAXi action and therefore use the stricter form:

```text
^infores:[A-Za-z0-9._-]+$
```

Do not maintain a local Biolink model or provider registry. Shape validation is local; ARAX remains
the semantic authority. Reject duplicate predicates, qualifier types, provider IDs, and repeated
scalar endpoint options.

## Fixed operations

Lookup mode fixes the provider to `infores:rtx-kg2`. Federated mode requires two to five explicit,
distinct provider identifiers and emits them in one list-valued `kp=` argument. Never omit `kp` and
never generate duplicate `kp=` arguments.

One hop expands `e0`. Two-hop right-first expands `e1` and then `e0`; left-first reverses only those
two actions. Append exactly:

```text
scoreless_resultify(ignore_edge_direction=true)
filter_results(action=limit_number_of_results,max_results=<1-50>,prune_kg=true)
return(response=true,store=false)
```

Each expansion fixes:

```text
kp_timeout=30,return_minimal_metadata=false
```

Always send `stream_progress: false` and the constant submitter
`scientific-agent-skills-ncats-arax`. Never put a user name, project name, or query term into the
submitter or User-Agent.

## Limits and retries

| Control | Value |
| --- | ---: |
| OpenAPI/entity HTTP timeout | 30 seconds |
| Lookup query HTTP timeout | 120 seconds |
| Federated query HTTP timeout | 180 seconds |
| ARAX KP timeout | 30 seconds |
| Lookup default result limit | 20 |
| Federated default result limit | 50 |
| Hard result limit | 50 |
| Provider count | 2-5 in federation |
| Predicates per edge | 1-5 |
| Qualifiers per edge | 0-6 |
| Raw response limit | 25 MiB (26,214,400 bytes) |

Retry OpenAPI and entity GET requests once after HTTP 429, 502, 503, 504, or a transport timeout.
Honor `Retry-After` for at most 10 seconds; otherwise wait one second. Never retry POST `/query`.
A failed POST may have been processed and must be rerun only by an explicit user decision.

Use these headers:

```text
Accept: application/json
Accept-Encoding: identity
Content-Type: application/json        # POST only
User-Agent: scientific-agent-skills-ncats-arax/1.0
```

## Version and endpoint policy

The tested target is ARAX 1.5.4 with TRAPI 1.5.0. Parse the common response fields for TRAPI 1.5
and 1.6, warning whenever the version is not the tested value. Refuse an unknown or missing TRAPI
series unless `--allow-untested-version` is explicit. Record `biolink_version` from each query
response rather than assuming it.

Accept only HTTPS base URLs without credentials, query strings, or fragments. Reject localhost and
literal private, loopback, link-local, or reserved addresses. A URL other than the production base
requires `--allow-nonproduction-endpoint`, must still identify ARAX through OpenAPI, and receives a
warning. Reject cross-origin and protocol-downgrade redirects. Never fall back automatically to
`arax.ncats.io` or another ARA.

## Excluded escape hatches

Expose no raw JSON submission, query-file, generic node/edge list, workflow, operations, action,
overlay, ranking, inference, creative-query, link-prediction, Pathfinder, ARS, all-provider,
batching, stdin-list, cache, database, daemon, server, SDK, MCP, or third-hop option.

The offline summarizer validates the saved request against this same topology and operation
contract. It refuses unsupported requests rather than becoming a back door for broader ARAX use.
