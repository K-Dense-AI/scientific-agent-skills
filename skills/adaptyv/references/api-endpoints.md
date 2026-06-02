# Adaptyv Bio Foundry API — Complete Endpoint Reference

Base URL: `https://foundry-api-public.adaptyvbio.com/api/v1`
OpenAPI spec: `GET /openapi.json`

## Table of Contents

- [Experiments](#experiments)
- [Sequences](#sequences)
- [Results](#results)
- [Targets](#targets)
- [Quotes](#quotes)
- [Tokens](#tokens)
- [Updates](#updates)
- [Feedback](#feedback)

---

## Experiments

### POST /experiments — Create experiment

Creates a new experiment. Starts in `Draft` status by default.

**Request body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Human-readable name |
| `experiment_spec` | ExperimentSpec | Yes | Experiment definition (see below) |
| `skip_draft` | boolean | No (default false) | Bypass Draft, go straight to WaitingForConfirmation |
| `auto_accept_quote` | boolean | No (default false) | Auto-accept quote and create invoice |
| `webhook_url` | string/null | No | URL for status-change POST notifications |

**ExperimentSpec:**

| Field | Type | Required | Description |
|---|---|---|---|
| `experiment_type` | string | Yes | `affinity`, `screening`, `thermostability`, `fluorescence`, or `expression` |
| `method` | string | Required for binding types | `bli` or `spr` |
| `target_id` | uuid | Required for binding types | Target UUID from catalog |
| `sequences` | object | Yes | Map of name → amino acid string or rich object |
| `n_replicates` | integer | Recommended (default 3) | Technical replicates (min 1) |
| `antigen_concentrations` | number[] | No (affinity only) | Defaults to `[1000.0, 316.2, 100.0, 31.6, 0.0]` nM |
| `parameters` | object | No | Experiment-specific settings |

**Field requirements by experiment type:**

| Field | Affinity | Screening | Thermostability | Fluorescence | Expression |
|---|---|---|---|---|---|
| `experiment_type` | required | required | required | required | required |
| `method` | required | required | — | — | — |
| `target_id` | required | required | — | — | — |
| `sequences` | required | required | required | required | required |
| `n_replicates` | recommended | recommended | optional | optional | optional |
| `antigen_concentrations` | optional | — | — | — | — |

**Response (201):**

| Field | Type | Description |
|---|---|---|
| `experiment_id` | string | UUID of new experiment |
| `error` | string/null | Error message if validation fails |
| `stripe_hosted_invoice_url` | string/null | Present when `auto_accept_quote` created an invoice |
| `stripe_invoice_id` | string/null | Stripe invoice ID |

**Status codes:** 201, 400, 401, 403, 404

---

### GET /experiments — List experiments

Lists experiments accessible to caller, sorted by creation date (newest first).

**Query params:** `limit`, `offset`, `filter`, `search`, `sort`

**Response item:**

| Field | Type | Description |
|---|---|---|
| `id` | uuid | Unique identifier |
| `code` | string | e.g., "EXP-2024-001" |
| `name` | string/null | Human-readable name |
| `status` | ExperimentStatus | Current lifecycle status |
| `experiment_type` | ExperimentType | affinity/screening/thermostability/fluorescence/expression |
| `results_status` | ResultsStatus | none/partial/all |
| `created_at` | datetime | ISO 8601 |
| `experiment_url` | string | URL to Foundry portal |
| `stripe_invoice_url` | string/null | Invoice URL |
| `stripe_quote_url` | string/null | Quote URL |

**Status codes:** 200, 401

---

### GET /experiments/{experiment_id} — Get experiment

Returns full metadata for a single experiment.

**Path param:** `experiment_id` (uuid)

**Response:**

| Field | Type | Description |
|---|---|---|
| `id` | uuid | Unique identifier |
| `code` | string | Experiment code |
| `status` | ExperimentStatus | Current status |
| `experiment_spec` | ExperimentSpec | Full experiment definition |
| `results_status` | ResultsStatus | none/partial/all |
| `created_at` | datetime | ISO 8601 |
| `experiment_url` | string | Portal URL |
| `costs` | object | Cost breakdown |

**Status codes:** 200, 401, 404, 500

---

### PATCH /experiments/{experiment_id} — Update experiment

Modify an existing experiment. Draft experiments allow full edits; after quote generation, only `name`, `description`, and `webhook_url` are editable.

**Path param:** `experiment_id` (uuid)

**Request body:** All fields optional — only provided fields are updated.

**Status codes:** 200, 400, 401, 404, 409

---

### POST /experiments/{experiment_id}/submit — Submit experiment

Submits a draft experiment for review. Advances from `Draft` to `WaitingForConfirmation`.

**Path param:** `experiment_id` (uuid)

**Response:**

| Field | Type | Description |
|---|---|---|
| `experiment_id` | string | Experiment UUID |

**Status codes:** 200, 401, 403, 404, 409, 500

---

### POST /experiments/cost-estimate — Estimate cost

Calculates cost without creating an experiment.

**Request body:**
```json
{
  "experiment_spec": {
    "experiment_type": "screening",
    "method": "bli",
    "target_id": "...",
    "sequences": {"seq1": "MKTL..."},
    "n_replicates": 3
  }
}
```

**Response:**

| Field | Type | Description |
|---|---|---|
| `pricing_version` | string | e.g., "v1_2026-01-20" |
| `assay` | object | Per-type costs with base and replicate pricing |
| `materials` | object | Target material costs (binding experiments) |
| `total_cents` | integer | Sum in USD cents |

All prices exclude VAT; taxes calculated at invoicing. Targets without self-service pricing return incomplete estimates.

**Status codes:** 200, 400, 401

---

### GET /experiments/{experiment_id}/quote — Get quote

Returns quote metadata (totals, currency, status, expiration).

**Path param:** `experiment_id` (uuid)

**Response:**

| Field | Type | Description |
|---|---|---|
| `experiment_id` | string | Experiment UUID |
| `stripe_quote_url` | string | Stripe quote URL |
| `amount_total` | int64 | Total in smallest currency unit |
| `amount_subtotal` | int64 | Subtotal |
| `currency` | string | ISO currency code (e.g., "usd") |
| `status` | string | Quote status |
| `expires_at` | datetime/null | Expiration time |

**Status codes:** 200, 401, 403, 404, 500

---

### GET /experiments/{experiment_id}/quote/pdf — Get quote PDF

Returns the quote as a PDF file (`application/pdf`).

**Path param:** `experiment_id` (uuid)

**Status codes:** 200, 401, 403, 404, 500

---

### POST /experiments/{experiment_id}/quote/confirm — Accept quote (by experiment)

Accepts Stripe quote, creates draft invoice, transitions to `WaitingForMaterials`.

**Path param:** `experiment_id` (uuid)

**Request body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `purchase_order_number` | string/null | No | PO number for your records |
| `notes` | string/null | No | Reserved |

**Response:**

| Field | Type | Description |
|---|---|---|
| `id` | string | Quote ID |
| `status` | StripeQuoteStatus | New status |
| `hosted_invoice_url` | string/null | Stripe payment URL |
| `invoice_id` | string/null | Generated invoice ID |

**Status codes:** 200, 401, 403, 404, 409

---

### GET /experiments/{experiment_id}/invoice — Get invoice

Returns invoice metadata including hosted payment URL.

**Path param:** `experiment_id` (uuid)

**Status codes:** 200, 401, 403, 404, 500

---

### GET /experiments/{experiment_id}/results — List results for experiment

Returns all analysis results for a specific experiment.

**Path param:** `experiment_id` (uuid)
**Query params:** `limit`, `offset`, `filter`, `sort`

**Status codes:** 200, 400, 401, 403, 404

---

### GET /experiments/{experiment_id}/sequences — List sequences for experiment

Returns all sequences for a specific experiment, sorted newest first.

**Path param:** `experiment_id` (uuid)
**Query params:** `limit`, `offset`, `search`, `sort`

**Status codes:** 200, 400, 401, 403, 404

---

### GET /experiments/{experiment_id}/updates — List experiment updates

Returns updates for one experiment, oldest first. Types: `status_change`, `progress`, `error`.

**Path param:** `experiment_id` (uuid)
**Query params:** `limit`, `offset`, `filter`, `sort`

Filter example: `filter=eq(type,status_change)`

---

## Sequences

### GET /sequences — List sequences

Returns sequences from all experiments, sorted newest first.

**Query params:** `limit`, `offset`, `search`, `sort`, `experiment_id` (filter by experiment UUID)

**Response item:**

| Field | Type | Description |
|---|---|---|
| `id` | uuid | Unique identifier |
| `name` | string/null | Optional name |
| `aa_preview` | string/null | Truncated preview (first 50 chars) |
| `length` | int32 | Sequence length in amino acids |
| `experiment_id` | uuid | Parent experiment |
| `experiment_code` | string | Human-readable experiment code |
| `is_control` | boolean | Whether this is a control |
| `created_at` | datetime | Creation timestamp |

**Status codes:** 200, 401

---

### GET /sequences/{sequence_id} — Get sequence

Returns full details including complete amino acid string.

**Path param:** `sequence_id` (uuid)

**Response:**

| Field | Type | Description |
|---|---|---|
| `id` | uuid | Unique identifier |
| `aa_string` | string/null | Complete amino acid sequence |
| `length` | int32 | Length in amino acids |
| `is_control` | boolean | Control flag |
| `metadata` | object | Sequence-level annotations |
| `experiment` | object | Parent experiment reference |
| `created_at` | datetime | Creation timestamp |

**Status codes:** 200, 401, 403, 404, 500

---

### POST /sequences — Add sequences to experiment

Appends sequences to a **Draft** experiment identified by its human-readable code.

**Request body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `experiment_code` | string | Yes | e.g., "PROJ-001" |
| `sequences` | array | Yes | Array of sequence entries |

**Each sequence entry:**

| Field | Type | Required | Description |
|---|---|---|---|
| `aa_string` | string | Yes | Amino acid sequence |
| `name` | string | No | Human-readable name |
| `control` | boolean | No | Whether this is a control |
| `metadata` | object | No | Annotations |

**Response (201):**

| Field | Type | Description |
|---|---|---|
| `added_count` | int32 | Number of sequences added |
| `experiment_id` | string | Experiment UUID |
| `experiment_code` | string | Experiment code |
| `sequence_ids` | array | IDs of added sequences |

**Status codes:** 201, 400, 404, 409 (experiment not in Draft), 500

---

## Results

### GET /results — List results

Lists completed analysis results, sorted newest first. Results appear when `results_status` reaches `partial` or `all`.

**Query params:** `limit`, `offset`, `filter`, `search`, `sort`

**Response item:**

| Field | Type | Description |
|---|---|---|
| `id` | uuid | Result identifier |
| `title` | string | Human-readable title |
| `experiment_id` | uuid | Associated experiment |
| `result_type` | string | e.g., "affinity", "thermostability" |
| `summary` | array | Key results (type-specific, see below) |
| `metadata` | object | Extended metadata (e.g., instrument info) |
| `data_package_url` | string/null | Download URL for raw data package |
| `created_at` | datetime | When result was generated |

**AffinityResult summary fields:** `kd_mean`, `kd_std`, `kon_mean`, `kon_log_std`, `koff_mean`, `koff_std`, `replicates` (array with per-replicate `kd`, `kon`, `koff`, `binding_strength`, `kon_method`, `koff_method`, `replicate` index), `sequence`, `target_id`

**ThermostabilityResult summary fields:** Tm values and melting curves

**Status codes:** 200, 401

---

### GET /results/{result_id} — Get result

Returns detailed result data including full summary array.

**Path param:** `result_id` (uuid)

**Status codes:** 200, 401, 403, 404, 500

---

## Targets

### GET /targets — List targets

Lists validated antigens available for experiments.

**Query params:**

| Parameter | Type | Description |
|---|---|---|
| `limit` | int | Max items (1-100, default 50) |
| `offset` | int | Skip count |
| `search` | string | Free-text search on product name |
| `sort` | string | Sort expression |
| `selfservice_only` | boolean | Only targets with self-service pricing |
| `show_conjugated` | boolean | Include conjugated targets (default: unconjugated only) |
| `detailed` | boolean | Populate `details` block with enrichment data |

**Response item:**

| Field | Type | Description |
|---|---|---|
| `id` | uuid | Target UUID (use as `experiment_spec.target_id`) |
| `name` | string | Target name |
| `vendor_name` | string | Vendor name |
| `catalog_number` | string | Vendor catalog/SKU number |
| `url` | string | Target URL |
| `pricing` | object/null | Self-service pricing (null = custom quote required) |
| `details` | object/null | Enrichment data (gene names, structures, sequence, bioactivity) |

**Status codes:** 200, 401

---

### GET /targets/{target_id} — Get target

Returns catalog record for a single target.

**Path param:** `target_id` (uuid)

**Status codes:** 200, 400, 401, 403, 404, 500

---

### POST /targets/request-custom — Submit custom target request

Submit a new custom target for staff review. At least one of `sequence` or `pdb_id` must be provided.

**Request body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Display name |
| `product_id` | string | Yes | Must be unique within organization |
| `sequence` | string/null | At least one | Amino acid sequence |
| `pdb_id` | string/null | At least one | PDB identifier |
| `pdb_file` | string/null | No | PDB file content |
| `molecular_weight` | number/null | No | Weight in kDa |
| `note` | string/null | No | Additional notes |

**Status codes:** 201, 400, 401, 403, 500

---

### GET /targets/request-custom — List custom target requests

Returns custom target requests for your organization, sorted newest first.

**Query params:** `limit`, `offset`, `filter`, `sort`

Filter example: `filter=eq(status,pending_review)`

---

### GET /targets/request-custom/{request_id} — Get custom target request

**Path param:** `request_id` (uuid)

**Response:**

| Field | Type | Description |
|---|---|---|
| `id` | uuid | Request identifier |
| `name` | string | Target name |
| `product_id` | string | Your product ID |
| `status` | string | e.g., "pending_review" |
| `material_id` | string/null | Linked catalog ID if approved |
| `molecular_weight` | number/null | Weight in kDa |
| `note` | string/null | User notes |
| `created_at` | datetime | Created |
| `updated_at` | datetime | Last updated |

**Status codes:** 200, 401, 403, 404, 500

---

## Quotes

### GET /quotes — List quotes

Returns all quotes for caller's organization.

**Query params:** `limit`, `offset`, `filter`, `sort`

**Response item:**

| Field | Type | Description |
|---|---|---|
| `id` | string | Quote identifier |
| `quote_number` | string | Human-readable quote number |
| `organization_id` | uuid | Organization |
| `amount_cents` | int | Amount in cents |
| `currency` | string | ISO 4217 code |
| `status` | StripeQuoteStatus | Quote status |
| `valid_until` | datetime | Expiration |
| `created_at` | datetime | Creation timestamp |

---

### GET /quotes/{quote_id} — Get quote

Returns full quote document with itemized pricing.

**Path param:** `quote_id` (string, e.g., "qt_1Abc2DefGhi")

**Response:**

| Field | Type | Description |
|---|---|---|
| `id` | string | Quote identifier |
| `quote_number` | string | Reference number |
| `organization_id` | uuid | Organization |
| `organization_name` | string | Organization name |
| `line_items` | array | Itemized pricing |
| `subtotal_cents` | int | Subtotal in cents |
| `tax_cents` | int | Tax in cents |
| `total_cents` | int | Total in cents |
| `currency` | string | ISO 4217 |
| `status` | StripeQuoteStatus | Current status |
| `valid_until` | datetime | Expiration |
| `notes` | string | Special pricing info |
| `terms_and_conditions` | string | Terms |
| `stripe_quote_url` | string | Stripe URL |
| `created_at` | datetime | Created |

**Status codes:** 200, 401, 403, 404, 500

---

### POST /quotes/{quote_id}/confirm — Accept quote

Finalizes quote, creates draft invoice, advances experiment to `WaitingForMaterials`.

**Path param:** `quote_id` (string)

**Request body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `purchase_order_number` | string/null | No | PO number |
| `notes` | string/null | No | Reserved |

**Response:** `id`, `status`, `hosted_invoice_url`, `invoice_id`

**Status codes:** 200, 403, 404, 409, 500

---

### POST /quotes/{quote_id}/reject — Reject quote

Cancels quote; linked experiment reverts to `Draft`.

**Path param:** `quote_id` (string)

**Request body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `reason` | QuoteRejectionReason | Yes | Primary reason |
| `feedback` | string/null | No | Additional feedback |

**Response:** `id`, `status` (canceled)

**Status codes:** 200, 403, 404, 409, 500

---

## Tokens

### GET /tokens — List tokens

Returns all tokens (root and attenuated) the caller owns.

**Query params:** `limit`, `offset`

**Response item:**

| Field | Type | Description |
|---|---|---|
| `id` | string | Token identifier |
| `name` | string | Human-readable label |
| `kind` | string | "root" or "attenuated" |
| `created_at` | datetime | Created |
| `expires_at` | datetime/null | Expiration (null = no expiry) |
| `revoked_at` | datetime/null | Revocation timestamp |
| `parent_token_id` | string/null | Parent (null for root) |
| `root_token_id` | string/null | Root of derivation tree |
| `attenuation_spec` | object/null | Restrictions (null for root) |

---

### POST /tokens/attenuate — Attenuate token

Creates a restricted version of an existing token using Biscuit cryptographic attenuation.

**Request body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `token` | string | Yes | Existing token (`abs0_{slug}{biscuit_base64}`) |
| `attenuation` | AttenuationSpec | Yes | Restrictions to apply |
| `name` | string | Yes | Human-readable label |
| `attenuated_parent_token_id` | uuid/null | No | Parent ID for chained attenuation |

**Restriction types:** Organization, Resource (experiments/results), Action (read/create/update), Expiry

**Response (201):** `id` (database ID), `token` (new attenuated token string)

**Status codes:** 201, 400, 401, 403

---

### POST /tokens/revoke — Revoke token and lineage

Revokes the calling token's root and all attenuated descendants. Idempotent.

**Response:**

| Field | Type | Description |
|---|---|---|
| `token_id` | string | Root token ID revoked |
| `revoked_at` | datetime | Revocation timestamp |
| `children_revoked` | int64 | Child tokens newly revoked |

**Status codes:** 200, 403, 404

---

## Updates

### GET /updates — List updates

Returns the experiment update feed (newest first): status changes, progress, errors.

**Query params:** `limit`, `offset`, `filter`, `sort`

**Filter examples:**
- `filter=eq(experiment_id,<uuid>)`
- `filter=in(experiment_id,uuid1,uuid2)`
- `filter=eq(type,status_change)`

**Response item:**

| Field | Type | Description |
|---|---|---|
| `id` | string | Update identifier |
| `experiment_id` | uuid | Associated experiment |
| `experiment_code` | string | Human-readable code |
| `name` | string | Update description |
| `timestamp` | datetime | When the update occurred |

---

## Feedback

### POST /feedback/submit — Submit feedback

For bug reports, feature requests, or general feedback.

**Request body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `request_uuid` | uuid | Yes | UUID from the problematic API request |
| `feedback_type` | FeedbackType | Yes | `feature_request`, `feedback`, or `bug_report` |
| `title` | string/null | No | Short title |
| `json_body` | object/null | At least one | Structured error details |
| `human_note` | string/null | At least one | Free-form description |

**Response (201):** `reference` (feedback reference), `message` (confirmation)

**Status codes:** 201, 400, 401, 500
