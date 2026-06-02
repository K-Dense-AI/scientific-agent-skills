---
name: adaptyv
author: "K-Dense, Inc."
description: "How to use the Adaptyv Bio Foundry API and Python SDK for protein experiment design, submission, and results retrieval. Use this skill whenever the user mentions Adaptyv, Foundry API, protein binding assays, protein screening experiments, BLI/SPR assays, thermostability assays, or wants to submit protein sequences for experimental characterization. Also trigger when code imports `adaptyv`, `adaptyv_sdk`, or `FoundryClient`, or references `foundry-api-public.adaptyvbio.com`."
license: MIT
compatibility: Requires Python 3.10+, an Adaptyv Foundry account, and an API key from foundry.adaptyvbio.com. Install adaptyv-sdk from GitHub with uv pip install.
metadata:
  version: "1.2"
  skill-author: K-Dense Inc.
---

# Adaptyv Bio Foundry API

Adaptyv Bio is a cloud lab that turns protein sequences into experimental data. Users submit amino acid sequences via API or UI; Adaptyv's automated lab runs assays (binding, thermostability, expression, fluorescence) and delivers results in ~21 days.

**Official docs:** [docs.adaptyvbio.com/api-reference](https://docs.adaptyvbio.com/api-reference) · [llms.txt index](https://docs.adaptyvbio.com/llms.txt) · [OpenAPI spec](https://foundry-api-public.adaptyvbio.com/api/v1/openapi.json)

## Quick Start

**Base URL:** `https://foundry-api-public.adaptyvbio.com/api/v1`

**Authentication:** Bearer token in the `Authorization` header. Tokens are obtained from [foundry.adaptyvbio.com](https://foundry.adaptyvbio.com/) sidebar.

When writing code, always read the API key from the environment variable `ADAPTYV_API_KEY` or from a `.env` file — never hardcode tokens. Check for a `.env` file in the project root first; if one exists, use a library like `python-dotenv` to load it.

The [official API docs](https://docs.adaptyvbio.com/api-reference/api-introduction) use `FOUNDRY_API_TOKEN` in curl examples; that is the same bearer token — prefer `ADAPTYV_API_KEY` in Python and new shell scripts for consistency with the SDK.

```bash
export ADAPTYV_API_KEY="abs0_..."
curl https://foundry-api-public.adaptyvbio.com/api/v1/targets?limit=3 \
  -H "Authorization: Bearer $ADAPTYV_API_KEY"
```

Every request except `GET /openapi.json` requires authentication. Store tokens in environment variables or `.env` files — never commit them to source control.

## Python SDK

**Version note:** `adaptyv-sdk` **0.1.0** (beta) is not yet on PyPI — install from GitHub:

```bash
uv pip install "git+https://github.com/adaptyvbio/adaptyv-sdk.git"
```

In a project with `pyproject.toml`:

```bash
uv add "adaptyv-sdk @ git+https://github.com/adaptyvbio/adaptyv-sdk.git"
```

**Environment variables** (set in shell or `.env` file):

```bash
ADAPTYV_API_KEY=your_api_key
ADAPTYV_API_URL=https://foundry-api-public.adaptyvbio.com/api/v1
ADAPTYV_ORGANIZATION_ID=your_org_id  # optional
```

The `@lab.experiment` decorator and `FoundryClient` both read `ADAPTYV_API_KEY` and `ADAPTYV_API_URL` from the environment when not passed explicitly.

### Decorator Pattern

```python
from adaptyv import lab

@lab.experiment(target="PD-L1", experiment_type="screening", method="bli")
def design_binders():
    return {"design_a": "MVKVGVNG...", "design_b": "MKVLVAG..."}

result = design_binders()
print(f"Experiment: {result.experiment_url}")
```

### Client Pattern

```python
import os
from adaptyv import FoundryClient

client = FoundryClient(
    api_key=os.environ["ADAPTYV_API_KEY"],
    base_url=os.environ.get(
        "ADAPTYV_API_URL",
        "https://foundry-api-public.adaptyvbio.com/api/v1",
    ),
)

# Browse targets
targets = client.targets.list(search="EGFR", selfservice_only=True)

# Estimate cost
estimate = client.experiments.cost_estimate({
    "experiment_spec": {
        "experiment_type": "screening",
        "method": "bli",
        "target_id": "target-uuid",
        "sequences": {"seq1": "EVQLVESGGGLVQ..."},
        "n_replicates": 3
    }
})

# Create and submit
exp = client.experiments.create({...})
client.experiments.submit(exp.experiment_id)

# Later: retrieve results
results = client.experiments.get_results(exp.experiment_id)
```

## Experiment Types

| Type | Method | Measures | Requires Target |
|---|---|---|---|
| `affinity` | `bli` or `spr` | KD, kon, koff kinetics | Yes |
| `screening` | `bli` or `spr` | Yes/no binding | Yes |
| `thermostability` | — | Melting temperature (Tm) | No |
| `expression` | — | Expression yield | No |
| `fluorescence` | — | Fluorescence intensity | No |

## Experiment Lifecycle

```
Draft → WaitingForConfirmation → QuoteSent → WaitingForMaterials → InQueue → InProduction → DataAnalysis → InReview → Done
```

| Status | Who Acts | Description |
|---|---|---|
| `Draft` | You | Editable, no cost commitment |
| `WaitingForConfirmation` | Adaptyv | Under review, quote being prepared |
| `QuoteSent` | You | Review and confirm the quote |
| `WaitingForMaterials` | Adaptyv | Gene fragments and target ordered |
| `InQueue` | Adaptyv | Materials arrived, queued for lab |
| `InProduction` | Adaptyv | Assay running |
| `DataAnalysis` | Adaptyv | Raw data processing and QC |
| `InReview` | Adaptyv | Final validation |
| `Done` | You | Results available |
| `Canceled` | Either | Experiment canceled |

The `results_status` field on an experiment tracks: `none`, `partial`, or `all`.

## Common Workflows

### 1. Submit a Binding Screen (Step by Step)

```python
# 1. Find a target
targets = client.targets.list(search="EGFR", selfservice_only=True)
target_id = targets.items[0].id

# 2. Preview cost
estimate = client.experiments.cost_estimate({
    "experiment_spec": {
        "experiment_type": "screening",
        "method": "bli",
        "target_id": target_id,
        "sequences": {"seq1": "EVQLVESGGGLVQ...", "seq2": "MKVLVAG..."},
        "n_replicates": 3
    }
})

# 3. Create experiment (starts as Draft)
exp = client.experiments.create({
    "name": "EGFR binder screen batch 1",
    "experiment_spec": {
        "experiment_type": "screening",
        "method": "bli",
        "target_id": target_id,
        "sequences": {"seq1": "EVQLVESGGGLVQ...", "seq2": "MKVLVAG..."},
        "n_replicates": 3
    }
})

# 4. Submit for review
client.experiments.submit(exp.experiment_id)

# 5. Poll or use webhooks until Done
# 6. Retrieve results
results = client.experiments.get_results(exp.experiment_id)
```

### 2. Automated Pipeline (Skip Draft + Auto-Accept Quote)

```python
exp = client.experiments.create({
    "name": "Auto pipeline run",
    "experiment_spec": {...},
    "skip_draft": True,
    "auto_accept_quote": True,
    "webhook_url": "https://my-server.com/webhook"
})
# Webhook fires on each status transition; poll or wait for Done
```

### 3. Using Webhooks

Pass `webhook_url` when creating an experiment. Adaptyv POSTs to that URL on every status transition with the experiment ID, previous status, and new status.

## Sequences

- Simple format: `{"seq1": "EVQLVESGGGLVQPGGSLRLSCAAS"}`
- Rich format: `{"seq1": {"aa_string": "EVQLVESGGGLVQ...", "control": false, "metadata": {"type": "scfv"}}}`
- Multi-chain: use colon separator — `"MVLS:EVQL"`
- Valid amino acids: A, C, D, E, F, G, H, I, K, L, M, N, P, Q, R, S, T, V, W, Y (case-insensitive, stored uppercase)
- Sequences can only be added to experiments in `Draft` status

## Filtering, Sorting, and Pagination

All list endpoints support pagination (`limit` 1-100, default 50; `offset`), search (free-text on name fields), and sorting.

**Filtering** uses s-expression syntax via the `filter` query parameter:
- Comparison: `eq(field,value)`, `neq`, `gt`, `gte`, `lt`, `lte`, `contains(field,substring)`
- Range/set: `between(field,lo,hi)`, `in(field,v1,v2,...)`
- Logic: `and(expr1,expr2,...)`, `or(...)`, `not(expr)`
- Null: `is_null(field)`, `is_not_null(field)`
- JSONB: `at(field,key)` — e.g., `eq(at(metadata,score),42)`
- Cast: `float()`, `int()`, `text()`, `timestamp()`, `date()`

**Sorting** uses `asc(field)` or `desc(field)`, comma-separated (max 8):
```
sort=desc(created_at),asc(name)
```

**Example:** `filter=and(gte(created_at,2026-01-01),eq(status,done))`

## Error Handling

All errors return:
```json
{
  "error": "Human-readable description",
  "request_id": "req_019462a4-b1c2-7def-8901-23456789abcd"
}
```
The `request_id` is also in the `x-request-id` response header — include it when contacting support.

## Token Management

Tokens use Biscuit-based cryptographic attenuation. You can create restricted tokens scoped by organization, resource type, actions (read/create/update), and expiry via `POST /tokens/attenuate`. Revoking a token (`POST /tokens/revoke`) revokes it and all its descendants.

## Detailed API Reference

For the full list of all 32 endpoints with request/response schemas, read `references/api-endpoints.md`.
