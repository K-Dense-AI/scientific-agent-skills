# Contract review — 2026-10-01

Reviewed all five original skill/reference files against the deployed OpenAPI,
current official guides, live MCP discovery, and released `gi-mcp` source.
The served API identifies itself as **2026.09.22.2 (af902d84)** with
**`x-contract-revision: 16`**; the released local adapter is **0.1.0a21**.

## Primary sources

- [Live OpenAPI](https://api.genomicintelligence.ai/v1/openapi.json): all 12
  operations, auth exceptions, literal task requests, options, response schemas,
  job status/limit semantics, extension fields, and VCF boundary.
- [REST guide](https://docs.genomicintelligence.ai/rest-api): transport,
  text-format restrictions, input/output envelopes and contract revision.
- [Task guide](https://docs.genomicintelligence.ai/tasks): interpretation,
  strand/token-span limitations, description sensitivity, composite behavior,
  and VCF workflow's unfinished scientific output.
- [Limits](https://docs.genomicintelligence.ai/reference/limits) and
  [errors](https://docs.genomicintelligence.ai/reference/errors): 20,000-site
  splice response cap, error-details exception, burst/rpm distinction,
  timeouts and retention. The splice cap is not structurally declared in the
  reviewed OpenAPI; do not infer its absence from the schema alone.
- [MCP guide](https://docs.genomicintelligence.ai/mcp), hosted
  `https://mcp.genomicintelligence.ai/mcp` self-description, and
  [gi-mcp 0.1.0a21](https://pypi.org/project/gi-mcp/0.1.0a21/): acquisition
  envelopes, demo restrictions, cached/UCSC reference sources, canonical-TSS
  fallback, and fixed minus-strand window math. Published wheel SHA-256 was
  checked before source inspection.
- Ensembl [symbol lookup](https://rest.ensembl.org/documentation/info/symbol_lookup),
  [ID lookup](https://rest.ensembl.org/documentation/info/lookup), and
  [region sequence](https://rest.ensembl.org/documentation/info/sequence_region):
  public routes, species aliases, expanded transcripts and sequence bounds.
  Current indexed official docs were readable; direct requests failed below.

## What was executed

- Public `/health`, live schema and all six `/v1/tasks/{task}/models` calls
  returned HTTP 200; discovery output was checked against the served schema.
- Empty-body unauthenticated POSTs to all eight task/workflow operations and
  GETs to both protected job endpoints returned HTTP 401 error envelopes.
  These verify auth behavior only, not predictions or input validation.
- Hosted MCP initialize, tools/resources/prompts discovery, model lookup,
  four resource reads and three reference acquisition calls succeeded at the
  transport layer. Acquisition payloads confirmed `data.ref`, lengths and HBB
  minus-strand TSS geometry. Demo recent-jobs/resource and list-jobs behavior
  returned the documented unavailable error rather than any user's history.
- Direct Ensembl HBB symbol lookup, stable-ID lookup and a 100-bp region call
  returned HTTP 500. Hosted HBB acquisition used catalog/cache; the small region
  used UCSC, so those successes do not establish Ensembl availability.
- 24 local checks exercised the documented Python blocks with mocked HTTP,
  including all six URLs/bodies, expression context/index, bounded 202-to-200
  polling, timeout/failed-job behavior, strand-dependent coordinate identity,
  and validation of recorded public responses.

- Released adapter functions were exercised with synthetic reference bytes:
  both strand-dependent TSS windows, both canonical/gene-body fallback flags,
  and IUPAC reverse-complement behavior passed without upstream requests.

## Limits of this review

No authenticated GI inference, free-demo inference, variant workflow, object
storage write, model weights or biological benchmark was run. Biological
outputs, timing claims, runtime 422s, text exports and paid tiers are supported
by the current published contract/guides, not end-to-end inference evidence.
MCP deployment and released adapter source are separate evidence; a version
number alone cannot establish that every deployment behavior matches a wheel.
Canonical transcript provenance and correct coordinate math do not validate an
active tissue-specific TSS or a model's scientific accuracy.
