# Adaptyv Foundry endpoint reference

Reviewed 2026-09-30 against the deployed
[OpenAPI 0.0.2 schema](https://devs.adaptyvbio.com/api/v1/openapi.json), the
[API guide](https://docs.adaptyvbio.com/api-reference/api-introduction), and
[official SDK source](https://github.com/adaptyvbio/adaptyv-sdk/tree/cdf207819ed5a58e0c127453626d2bce125c8064).
All paths below are relative to `https://devs.adaptyvbio.com/api/v1`.

## Endpoint inventory

These are the 43 operations in the reviewed schema. Schema names refer to
`components.schemas` in the linked OpenAPI document. `Page<T>` means
`{items: T[], total, count, offset}`. Most pages use inline item schemas;
use the operation's response definition when a name is not provided.
The table lists success responses; detailed constraints follow it.

| Method and path | JSON request schema | Success response |
|---|---|---|
| `GET /experiments` | `None` | `200 Page<inline item>` |
| `POST /experiments` | `CreateExpRequest` | `200 ConfirmQuoteResponse`; `201 CreateExpResponse` |
| `POST /experiments/cost-estimate` | `CostEstimateRequest` | `200 CostEstimateResponse` |
| `GET /experiments/{experiment_id}` | `None` | `200 ExpInfo` |
| `PATCH /experiments/{experiment_id}` | `ModifyExpRequest` | `200 ModifyExpResponse` |
| `GET /experiments/{experiment_id}/invoice` | `None` | `200 ExperimentInvoiceResponse` |
| `GET /experiments/{experiment_id}/quote` | `None` | `200 ExperimentQuoteResponse` |
| `POST /experiments/{experiment_id}/quote/confirm` | `ConfirmQuoteRequest` | `200 ConfirmQuoteResponse` |
| `GET /experiments/{experiment_id}/quote/pdf` | `None` | `200 PDF bytes` |
| `GET /experiments/{experiment_id}/results` | `None` | `200 Page<inline item>` |
| `GET /experiments/{experiment_id}/sequences` | `None` | `200 Page<inline item>` |
| `POST /experiments/{experiment_id}/submit` | `None` | `200 ExperimentConfirmationResponse` |
| `GET /experiments/{experiment_id}/updates` | `None` | `200 Page<inline item>` |
| `POST /feedback/submit` | `SubmitFeedbackRequest` | `201 SubmitFeedbackResponse` |
| `GET /info/health` | `None` | `200 HealthResponse` |
| `GET /info/health-db` | `None` | `200 HealthDbResponse` |
| `GET /invoices` | `None` | `200 Page<inline item>` |
| `GET /invoices/{invoice_id}` | `None` | `200 InvoiceDetailResponse` |
| `POST /invoices/{invoice_id}/pay` | `None` | `200 PayInvoiceResponse` |
| `GET /invoices/{invoice_id}/pdf` | `None` | `307 Redirect to PDF` |
| `GET /quotes` | `None` | `200 Page<inline item>` |
| `GET /quotes/{quote_id}` | `None` | `200 QuoteInfo` |
| `POST /quotes/{quote_id}/confirm` | `ConfirmQuoteRequest` | `200 ConfirmQuoteResponse` |
| `POST /quotes/{quote_id}/reject` | `RejectQuoteRequest` | `200 RejectQuoteResponse` |
| `GET /results` | `None` | `200 Page<inline item>` |
| `GET /results/{result_id}` | `None` | `200 ResultInfo` |
| `GET /sequences` | `None` | `200 Page<inline item>` |
| `POST /sequences` | `SequenceAddRequest` | `201 SequenceAddResponse` |
| `GET /sequences/{sequence_id}` | `None` | `200 SequenceInfo` |
| `GET /targets` | `None` | `200 Page<inline item>` |
| `GET /targets/request-custom` | `None` | `200 Page<inline item>` |
| `POST /targets/request-custom` | `CreateCustomTargetRequest` | `201 CreateCustomTargetResponse` |
| `GET /targets/request-custom/{request_id}` | `None` | `200 CustomTargetRequestInfo` |
| `GET /targets/{target_id}` | `None` | `200 TargetInfo` |
| `GET /tokens` | `None` | `200 Page<inline item>` |
| `POST /tokens/attenuate` | `AttenuateTokenRequest` | `201 AttenuateTokenResponse` |
| `POST /tokens/revoke` | `None` | `200 RevokeTokenResponse` |
| `GET /updates` | `None` | `200 Page<inline item>` |
| `GET /webhooks` | `None` | `200 OrgWebhook[]` |
| `POST /webhooks` | `CreateOrgWebhookRequest` | `201 OrgWebhook` |
| `DELETE /webhooks/{webhook_id}` | `None` | `204 No body` |
| `PATCH /webhooks/{webhook_id}` | `UpdateOrgWebhookRequest` | `200 OrgWebhook` |
| `GET /whoami` | `None` | `200 WhoAmIResponse` |

## Authentication and request scope

Send `Authorization: Bearer <token>` to resource endpoints and
`Content-Type: application/json` for JSON bodies. Obtain tokens through Foundry;
`GET /whoami` returns `organizations`, `permissions`, optional `user_id`,
`active_organization_id`, and `token_expires_at`. Each organization entry marks
whether it is active. Do not invent an `organization_id` create-body field from
the SDK's legacy optional argument: it is absent from current `CreateExpRequest`.
Use a token scoped to the intended organization and inspect `whoami`.

`GET /openapi.json` (schema discovery, not counted above) and the liveness probe
`GET /info/health` are public. The database probe reports 200 or 503; its
operation does not explicitly override the schema's global bearer security,
so do not rely on anonymous database-probe access.

## Pagination and query parameters

| GET endpoint | Query parameters |
|---|---|
| `/experiments` | `limit`, `offset`, `filter`, `search`, `sort` |
| `/experiments/{experiment_id}/results` | `limit`, `offset`, `filter`, `search`, `sort` |
| `/experiments/{experiment_id}/sequences` | `limit`, `offset`, `search`, `sort` |
| `/experiments/{experiment_id}/updates` | `limit`, `offset`, `filter`, `sort` |
| `/invoices` | `limit`, `offset`, `filter`, `sort` |
| `/quotes` | `limit`, `offset`, `filter`, `sort` |
| `/results` | `limit`, `offset`, `filter`, `search`, `sort` |
| `/sequences` | `limit`, `offset`, `search`, `sort`, `experiment_id` |
| `/targets` | `limit`, `offset`, `search`, `filter`, `sort`, `selfservice_only`, `show_conjugated`, `detailed` |
| `/targets/request-custom` | `limit`, `offset`, `filter`, `sort` |
| `/tokens` | `limit`, `offset` |
| `/updates` | `limit`, `offset`, `filter`, `sort` |

`limit` is 1–100 (default 50); `offset` starts at zero. Advance by the number of
returned items and stop at `total` or an empty page. `count` is the current page
size, not the total. Organization webhook listing is an array without pagination.
Search, filters, and sorting are not universal; only use listed parameters.

For filters use `filter=eq(status,draft)` or
`filter=and(gte(created_at,2026-01-01),eq(status,done))`. Canonical sort syntax is
`desc(created_at),asc(name)`; prefix and suffix forms also work. Targets support
filter/sort on `name`, `vendor_name`, `catalog_number`, and `purity` (e.g.
`gte(purity,90)`). The reviewed SDK `targets.list()` does not expose `filter`;
use REST for that parameter. Global updates are newest first; the experiment
update feed is oldest first by default.

## Experiments

### Create and estimate

`POST /experiments` requires `name` and `experiment_spec`. Optional fields:

| Field | Contract |
|---|---|
| `skip_draft` | Boolean; starts processing at `waiting_for_confirmation` instead of `draft` |
| `auto_accept_quote` | Boolean, default false; implies `skip_draft`, requires full pricing |
| `webhook_url` | HTTPS notification URL |
| `webhook_secret` | Write-only HMAC secret, minimum 32 characters; inherited if omitted |
| `payment` | Optional `{method: ...}` selector; must agree with `X-Adaptyv-Payment-Method` when both are supplied |

The ordinary 201 response has `experiment_id`, optional `error`,
`stripe_invoice_id`, and `stripe_hosted_invoice_url`. It does not promise an
experiment URL, code, or status; fetch the experiment for those. With
`auto_accept_quote` and a machine payment method the response is instead
200 `ConfirmQuoteResponse`. Automatic quote acceptance does not settle a
machine payment or emit the payment challenge; follow the returned pointer.

`ExperimentSpec` accepts:

| Field | Contract |
|---|---|
| `experiment_type` | `affinity`, `screening`, `thermostability`, `fluorescence`, `expression`, `epitope_binning`, `enzyme_activity` |
| `method` | Required for affinity/screening (`bli` or `spr`); rejected otherwise |
| `target_id` | Catalog UUID required for affinity, screening, epitope binning; rejected otherwise |
| `sequences` | Name-to-sequence map, at least one entry; epitope binning requires 4–28 entries in multiples of 4 |
| `n_replicates` | Default 3, range 1–5 per create-operation description; rejected for epitope binning |
| `antigen_concentrations` | Affinity-only, nM; defaults to `[1000.0, 316.2, 100.0, 31.6, 0.0]` |
| `parameters` | Optional settings object; readback adds `experiment_type` if absent |

Strings or `{aa_string, control?, metadata?}` are accepted as sequence values.
Use only full amino acid strings and colon-separated chains. Creation metadata
uses the strict `SequenceMetadata` schema: `type`, `VH`, `VL`, `linker`,
`framework_regions`, `tag_location`, `chain_order`; unknown fields are rejected.
`ScFv` requires `VH`/`VL`, `FAB` requires `framework_regions.ch`/`.cl`.
`SingleChain` and `IgG` need no additional format fields. REST documentation also
allows lowercase aliases `sc_fv`, `fab`, `single_chain`, `igg`; SDK enums use
`ScFv`, `FAB`, `SingleChain`, `IgG`. `scfv` is not a documented alias.

`POST /experiments/cost-estimate` takes exactly the wrapper
`{"experiment_spec": spec}`. Its response has optional `breakdown`, `incomplete`,
and `warnings`; `pricing_version`, `assay`, `materials`, `total_cents` live inside
`breakdown`, not at the top level. `materials` may be absent for non-binding
assays. An incomplete response carries assay cost plus
`materials_unavailable` and cannot be treated as a total. Estimates are USD
cents excluding VAT; inspect the actual quote before committing to a price.

### Read, edit, submit

`GET /experiments` returns identifiers, code, nullable name/type, timestamps,
wire status, results availability, portal URL and optional billing references.
`GET /experiments/{experiment_id}` adds `experiment_spec` and optional `costs`.
Its specification is `ExperimentSpecInfo`: the resolved target is
`experiment_spec.target`, with `target_catalog_id` and name, rather than the
creation field `target_id`. `stripe_quote_id` is usable with `/quotes/{quote_id}`.
The invoice reference on list/detail is not a reliable substitute for the
experiment invoice endpoint.

`PATCH /experiments/{experiment_id}` accepts optional `name`, `description`,
`target_id`, `antigen_concentrations`, `n_replicates`, `parameters`, `sequences`,
`webhook_url`. Most edits are restricted to `draft` or `in_review`; later edits
return 409. `webhook_url` can change at any status. Omitted `target_id` preserves
it; explicit JSON null clears it. `sequences` is a **replacement array** of
`SequenceEntry`, not the create-time map. The SDK uses `exclude_none` and cannot
express clearing a target with null; use REST for that operation.

`POST /experiments/{experiment_id}/submit` needs no body and returns
`experiment_id`, `previous_status`, `status`, `confirmed_at`, and optional billing
references. Its name `confirmed_at` does not imply that the quote is paid.
A 409 uses `SubmitConflictError` with conflict details; inspect the current state
before retrying.

Wire statuses: `draft`, `waiting_for_confirmation`, `quote_sent`,
`waiting_for_materials`, `in_queue`, `in_production`, `data_analysis`, `in_review`,
`done`, `canceled`. Results availability is `none`, `partial`, or `all`.

## Quotes and invoices

`GET /experiments/{experiment_id}/quote` returns `experiment_id`,
`stripe_quote_url`, `amount_total`, `amount_subtotal`, `currency`, `status`, and
optional `expires_at`/`updated_at`. Quote generation is asynchronous: 404 after
submission can mean pending, while a draft has no forthcoming quote. Poll with
a timeout or wait for `stripe_quote_id` on the experiment. The quote PDF endpoint
returns PDF bytes directly.

`GET /quotes` provides summary rows with ID, quote number, organization,
`amount_cents`, currency, status, validity/creation times, and Stripe quote URL.
`GET /quotes/{quote_id}` uses the Stripe quote ID (`qt_...`) and returns itemized
`line_items`, `subtotal_cents`, `tax_cents`, `total_cents`, organization name,
notes, terms, and quote URL.

Both quote-confirm endpoints require a JSON body; send `{}` when not supplying
`purchase_order_number` or reserved `notes`. Confirmation is **non-settling**:
it accepts the quote, prepares an open unpaid invoice, and returns
`id`, `status`, optional `invoice_id`, `hosted_invoice_url`, and `payment`.
The last field directs the client to hosted checkout or the machine-pay route.
`POST /quotes/{quote_id}/reject` takes required `reason` (`price`, `scope`,
`timeline`, `budget`, `other`) and optional `feedback`; it cancels the quote and
returns the experiment to `draft`.

`GET /experiments/{experiment_id}/invoice` returns `experiment_id`, optional
`stripe_invoice_url` and `status`. A 404 before quote confirmation means no
invoice exists yet. Organization invoice listing includes billing history;
`GET /invoices/{invoice_id}` accepts a Foundry UUID or Stripe `in_...` ID and
returns `id`, `stripe_invoice_id`, `status`, currency, optional amount,
experiment/quote links, and hosted URL. The invoice PDF endpoint returns a
**307 redirect**, not PDF bytes; follow its current Location without forwarding
the Foundry bearer token to Stripe. A draft invoice has no PDF (404).

`POST /invoices/{invoice_id}/pay` is the settlement endpoint. Its documented
machine methods are `mpp-spt` and `x402-exact`; use `payment.methods` from quote
confirmation to discover what the deployment/token allows. The explicit method
header must match the experiment's selected method (409 on mismatch). Machine
flows first receive 402 with the challenge in response headers (`WWW-Authenticate`
or `PAYMENT-REQUIRED`), then repeat with the challenge-specific credential.
Do not substitute a generic JSON body for that handshake or assume a headerless
request settles: the ordinary invoice flow only returns current state and its
hosted URL. Machine-policy tokens have additional headerless discovery behavior;
read the current operation description before implementing it. On successful
settlement capture optional `settlement_reference` immediately. Repeats return
`already_paid: true` without charging again, and do not reproduce that reference.

Payment calls and automatic quote acceptance require the user's authorized
purchase scope. This skill's examples do not execute payment or laboratory work
as a verification step.

## Sequences and results

Sequence lists return ID, optional name, `aa_preview` (first 50 characters),
length, experiment ID/code, control flag and creation time. Fetch
`GET /sequences/{sequence_id}` for `aa_string`, metadata and parent experiment.
`POST /sequences` appends only to a draft, with required `experiment_code` and
`sequences: [{aa_string, name?, control?, metadata?}, ...]`. Its 201 response
contains `added_count`, `experiment_id`, `experiment_code`, and `sequence_ids`.

Global and experiment-scoped result lists return `ResultInfo`: ID, title,
experiment ID, result type, timestamp, `summary` array, metadata, and optional
`data_package_url`. The detail endpoint returns the same complete result shape.
Fetch every page even after `results_status` is `all`.

Each summary entry has its own `result_type` discriminator. The reviewed schema
currently describes `affinity` and `thermostability` variants; it does not provide
separate typed summaries for every supported creation assay.

- Affinity entries include `sequence`, optional resolved `target` (not `target_id`),
  `binding_strength`, `positive_control`, control-relative `performance`, and
  `replicates`. KD is molar (M), kon is M^-1 s^-1, koff is s^-1. Aggregates use
  `kd_mean`/`kd_log_std`, `kon_mean`/`kon_log_std`, `koff_mean`/`koff_log_std`;
  the old `kd_std`/`koff_std` fields are absent. New optional fields include
  `kd_app`, `kon_1to1`, `koff_1to1` with confidence intervals, `binding_model`,
  `fit_quality`, expression/concentration readouts and `rmse_max_signal_pct`.
  Preserve nulls, model identity, and per-replicate QC; KD means aggregate
  strong-binding replicates only.
- Thermostability entries carry `sequence_id`, optional sequence/name,
  `tm` in degrees Celsius, `onset_pts_for_ratio`, `inflection_pts_for_ratio`,
  optional `initial_330nm` and `bli_result_id`. These describe nanoDSF readouts;
  the summary does not promise full melting curves. Use the raw package for
  underlying data.

## Targets

Catalog entries expose `id`, `name`, `vendor_name`, `catalog_number`, `url`,
optional `uniprot_id`, `pricing`, and `details`. Details are returned on detail
reads or with `detailed=true` on listing. `pricing.type` distinguishes
`per_sequence` from `per_broken_lot`; missing pricing needs a custom quote.
`selfservice_only=true` restricts to priced targets; `show_conjugated=true`
includes conjugated entries otherwise excluded. Verify the exact construct and
conjugation before using its catalog ID.

A custom-target request requires `name`, unique-in-organization `product_id`,
and at least one of `sequence` or `pdb_id`. Optional fields are `pdb_file`,
`molecular_weight` (kDa), `note`, `product_url`, `vendor`. Creation returns its
request ID/status; listing gives summary rows. Detail includes submitted fields,
status, timestamps and optional `material_id` after approval. Submission for
review is not proof that a target is immediately orderable.

## Tokens, webhooks, updates and feedback

Token listing returns flat lineage records (`id`, `name`, `kind`, timestamps,
optional `parent_token_id`, `root_token_id`, `token_type`, `attenuation_spec`).
`POST /tokens/attenuate` requires `token`, `name`, `attenuation`; optional
`attenuated_parent_token_id` identifies a chained parent. Supported restrictions
include `read_only`, `non_destructive`, `allowed_actions`, `allowed_resources`,
`allowed_org_ids`, `expires_at`, `payment_policy`. Actions include `list`, `read`,
`create`, `update`, `delete`, `issue`, `revoke`, `mint_token`; restrictions
intersect existing capabilities. Response: `id`, `token` (store securely).
Revocation takes no body and invalidates the authenticating token's **root and
all descendants**, returning `token_id`, `revoked_at`, `children_revoked`.

Organization webhook creation requires publicly routable HTTPS `url`; optional
`secret` is write-only and at least 32 characters, and `headers` adds delivery
headers. Response/list items contain `id`, `url`, `secret_set`, `headers`,
`enabled`, timestamps. PATCH supports `url`, `headers`, `enabled`, `secret`;
explicit null clears a secret. DELETE returns 204. An experiment-specific webhook
overrides organization delivery. Per-experiment secrets inherit organization then
deployment defaults when absent; provision a known secret for verifiable delivery.
See the skill for event signature, deduplication and retry handling.

Update rows contain `id`, `experiment_id`, `experiment_code`, `name`, `timestamp`.
Filters include `eq(experiment_id,<uuid>)`, `in(experiment_id,uuid1,uuid2)`, and
`eq(type,status_change)`.

Feedback submission requires `request_uuid` and `feedback_type`
(`feature_request`, `feedback`, `bug_report`); include at least one of `json_body`
or `human_note`, and optional `title`. Response: `reference`, `message`.
Preserve the request ID for debugging; never include tokens in feedback.

## Upstream discrepancies and verification boundary

The deployed schema's operation/component contracts were used over contradictory
introductory examples: some prose still shows PascalCase statuses, an API base
ending in `/openapi.json`, unsupported `adaptyv_sdk` imports, or the older filter
notation. Replicate bounds and some assay-specific requirements appear in the
create-operation description but are weaker in JSON Schema; JSON validation alone
is not enough. Sequence metadata prose uses lowercase `vh`/`vl`, while properties
are `VH`/`VL`; use the properties and SDK serialization shown above.

The payment description documents 402 challenges even though 402 is missing from
its response map. `auto_accept_quote` prose also describes legacy draft-invoice
behavior for async payment, while confirm operations specify open unpaid invoices;
inspect the returned invoice state instead of hardcoding it.

Verified: all listed paths, declared request/response schemas, query parameters,
SDK signatures/source, public schema retrieval and anonymous liveness. Authenticated
reads, lab submissions, custom targets, webhook deliveries, billing and payment
were not exercised. SDK 0.1.0's generated models omit some newer result/target
fields and its high-level convenience methods have the limitations documented in
SKILL.md; use raw REST JSON when lossless retrieval is required.
