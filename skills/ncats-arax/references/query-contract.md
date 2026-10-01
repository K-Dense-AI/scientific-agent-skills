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
`/openapi.json`, verifies an ARAX title, `POST /query`, and `GET /entity`, and records the advertised
ARAX and TRAPI versions. Normalization uses `/entity`; graph lookup uses `/query`.

| Endpoint | Request and response contract |
| --- | --- |
| `GET /openapi.json` | OpenAPI object; ARAX version is `info.version`, TRAPI version is `info.x-trapi.version` (title fallback). No biomedical term is submitted. |
| `GET /entity?q=<term>` | URL-encoded `q`; the API permits repeated `q` but this client submits one. Response is keyed by input term, with `id.identifier`, `id.name`, `id.category`, `categories`, `nodes`, and `total_synonyms`. Unknown terms may have no usable record. |
| `POST /query` | JSON `message.query_graph`, ARAX-specific `operations.actions`, `stream_progress: false`, and `submitter`. Response is a TRAPI envelope with `message`, optional `status`, `description`, `logs`, and version fields. |

Entity synonym entries use `label` for their display name; the client also accepts older `name`
entries. The canonical display name remains `id.name`. This is ARAX's entity response contract,
not the SRI Node Normalizer's direct response schema.

These routes require no API key in the deployed OpenAPI. The fixed result limit is an ARAXi
filter, not pagination: the client does not follow pages or promise a complete enumeration of
all matching graph paths. The API's broader pagination and asynchronous fields are not used.

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

The client requires strict JSON. On 2026-09-30, `/entity?q=primary+myelofibrosis` returned `NaN`
inside auxiliary knowledge-graph attributes and was correctly retained as a malformed response
(exit 6). The worked example uses a successfully tested entity. If this happens for another
term, inspect the raw artifact and curate the CURIE independently; do not treat it as no match.

Use these headers:

```text
Accept: application/json
Accept-Encoding: identity
Content-Type: application/json        # POST only
User-Agent: scientific-agent-skills-ncats-arax/1.1
```

## Version and endpoint policy

Production OpenAPI and all eight live smoke tests were verified on 2026-09-30 against ARAX 1.5.4
with TRAPI 1.5.0. The `/v1.4` URL component is not the advertised TRAPI version. Parse the common response fields for TRAPI 1.5
and 1.6, warning whenever the version is not the tested value. Refuse an unknown or missing TRAPI
series unless `--allow-untested-version` is explicit. Record `biolink_version` from each query
response rather than assuming it.

Accept only HTTPS base URLs without credentials, query strings, or fragments. Reject localhost and
literal private, loopback, link-local, or reserved addresses. A URL other than the production base
requires `--allow-nonproduction-endpoint`, must still identify ARAX through OpenAPI, and receives a
warning. Reject cross-origin and protocol-downgrade redirects. Never fall back automatically to
`arax.ncats.io` or another ARA.

The operations were checked against the [deployed OpenAPI](https://arax.transltr.io/api/arax/v1.4/openapi.json),
[ARAX query execution](https://github.com/RTXteam/RTX/blob/master/code/ARAX/ARAXQuery/ARAX_query.py),
[expander](https://github.com/RTXteam/RTX/blob/master/code/ARAX/ARAXQuery/ARAX_expander.py), and
[result filter](https://github.com/RTXteam/RTX/blob/master/code/ARAX/ARAXQuery/ARAX_filter_results.py).
`scoreless_resultify` is supported by the query dispatcher even though the DSL guide documents
`resultify` more prominently; `resultify` additionally triggers ranking and is not interchangeable.
Provider availability is chosen from ARAX's current registry by version and maturity; the
MolePro example is a tested selection, not a permanently available provider list.

## Excluded escape hatches

Expose no raw JSON submission, query-file, generic node/edge list, workflow, operations, action,
overlay, ranking, inference, creative-query, link-prediction, Pathfinder, ARS, all-provider,
batching, stdin-list, cache, database, daemon, server, SDK, MCP, or third-hop option.

The offline summarizer validates the saved request against this same topology and operation
contract. It refuses unsupported requests rather than becoming a back door for broader ARAX use.
