# Biohub hosted inference and former Forge clients

## Authentication and clients

The current `esm==3.4.1.post1` factories default to `https://biohub.ai` for
**ESM3, ESMC and ESMFold2**. The old Forge host is historical, not a recommended
separate ESM3 route. `esm.sdk.forge` names remain for compatibility.

Pass `token=os.environ["ESM_API_KEY"]` explicitly. Factory defaults read the
environment at module import, so later environment changes are not automatically
picked up. Keys are managed in the
[Biohub developer console](https://biohub.ai/developer-console/api-keys).
Do not send unpublished sequences to hosted inference without authorization for
that data transfer. Use a fixed trusted host: SDK response paths can deserialize
binary tensor payloads and must not be directed at an arbitrary server.

| Factory | Purpose | Example model |
| --- | --- | --- |
| `esm.sdk.client` | ESM3 | `esm3-medium-2024-08` |
| `esm.sdk.esmc_client` | ESMC | `esmc-600m-2024-12` |
| `esm.sdk.esmfold2_client` | ESMFold2 | `esmfold2-fast-2026-05` |

The factories accept `model`, `url`, `token`, and `request_timeout` (seconds).
Their default timeout is `None` (unbounded), while explicit inference-client
constructors default to 60 seconds. Set a finite timeout deliberately. Explicit
`ESM3ForgeInferenceClient`, `ESMCForgeInferenceClient`, and
`SequenceStructureForgeInferenceClient` also accept `min_retry_wait`,
`max_retry_wait`, and `max_retry_attempts`.

## Released HTTP contracts

All table entries were checked in the released wheel. ESM3 protein generation,
ESMC encode/logits/decode and the folding failure path were additionally tested
with `httpx` mock transports; the other routes were source-reviewed only. No
authenticated request was made. These are single inference requests without
pagination. Use SDK serialization instead of inventing REST payloads.

| Method | HTTP route on `https://biohub.ai` | Request / response |
| --- | --- | --- |
| ESM3 `generate(ESMProtein, config)` | `POST /api/v1/generate` | JSON `model`, `inputs` tracks, generation settings at the top level; response `outputs` tracks and confidence fields becomes `ESMProtein` |
| ESM3 `generate(ESMProteinTensor, config)` | `POST /api/v1/generate_tensor` | Token-valued `inputs`; response becomes `ESMProteinTensor` |
| ESM3/ESMC `encode` | `POST /api/v1/encode` | `model`, `inputs` tracks; `outputs` token arrays and `potential_sequence_of_concern` |
| ESM3/ESMC `decode` | `POST /api/v1/decode` | `model`, token-valued `inputs`; `outputs` decoded tracks |
| ESM3/ESMC `logits` | `POST /api/v1/logits` | `model`, token-valued `inputs`, `logits_config`; `LogitsOutput` with per-track logits and optional embeddings |
| ESM3 `forward_and_sample` | `POST /api/v1/forward_and_sample` | `model`, token-valued `inputs`, `sampling_config`; sampled protein tensor and optional statistics |
| ESMFold2 `fold_all_atom` | `POST /api/v1/fold_all_atom` | Serialized `all_atom_input`, `model`, folding settings; complex state and confidence values become `MolecularComplexResult` |

Authorization is `Bearer <token>`. The transport prefixes `/api/v1/`, submits
JSON, and unwraps a `data` envelope where applicable. Tensor-heavy responses
may use binary formats; `logits()` defaults to requesting bytes with
`return-bytes: true` and an SDK-specific `Accept` header. Do not assume all
responses are ordinary JSON arrays or bypass the SDK decoder.

## Error and retry behavior

Many SDK methods catch HTTP failures and **return `ESMProteinError`**. Others can
raise it. Network failures are wrapped as error code 500; deterministic request
serialization/response-parsing failures become 400. A `requests.HTTPError`
handler is insufficient: the released transport uses `httpx` and SDK errors.

```python
from esm.sdk.api import ESMProteinError

def require_success(result):
    if isinstance(result, ESMProteinError):
        raise result
    return result
```

The SDK retries errors 429, 500, 502, 503 and 504, whether returned or raised,
using bounded exponential jitter (default five attempts). Do not add unbounded
outer retries. A timeout does not establish that the server did no work; retrying
a stochastic inference can produce another result and consume resources. A
finite per-request timeout is not a global batch deadline. Never use a paid
inference call merely to claim a token is valid.

## Bounded concurrent generation

Illustrative authenticated inference. Each request owns its generation config;
`asyncio.gather` preserves input order and failures remain linked to IDs.

```python
import asyncio
import os
from esm.sdk.forge import ESM3ForgeInferenceClient
from esm.sdk.api import ESMProtein, ESMProteinError, GenerationConfig

async def generate_many(records, concurrency=4):
    if concurrency < 1:
        raise ValueError("concurrency must be positive")
    semaphore = asyncio.Semaphore(concurrency)
    async with ESM3ForgeInferenceClient(
        model="esm3-medium-2024-08", url="https://biohub.ai",
        token=os.environ["ESM_API_KEY"], request_timeout=120,
        max_retry_attempts=3,
    ) as client:
        async def run_one(record):
            record_id, prompt = record
            masks = prompt.count("_")
            if masks == 0:
                raise ValueError("Sequence generation needs masked positions")
            async with semaphore:
                result = await client.async_generate(
                    ESMProtein(sequence=prompt),
                    GenerationConfig(track="sequence", num_steps=min(20, masks)),
                )
            if isinstance(result, ESMProteinError):
                return record_id, {"error_code": result.error_code}
            return record_id, {"sequence": result.sequence}
        return await asyncio.gather(*(run_one(record) for record in records))
```

Use bounded chunks for very large iterables rather than creating millions of
pending tasks. The SDK also supplies `parallel_executor()` with
`execute_batch(user_func=..., ...)`; `batch_executor` is deprecated. These are
concurrent on-demand requests, distinct from the newer submitted batch-job API.
The submitted max-accuracy batch workflow is outside the recipes audited here.

Save successful records and failures separately with input IDs, model ID and
complete settings. Cache keys must include every conditioning track, checkpoint
or hosted revision, SDK version, and config. Do not log keys or sensitive sequence
payloads. Inspect current account quotas in the console; no fixed RPM, prices,
SageMaker deployment availability or enterprise data-residency promises are
asserted here.

Sources: [factories](https://github.com/Biohub/esm/blob/main/esm/sdk/__init__.py),
[client serialization](https://github.com/Biohub/esm/blob/main/esm/sdk/forge.py),
[transport](https://github.com/Biohub/esm/blob/main/esm/sdk/base_forge_client.py),
[retry rules](https://github.com/Biohub/esm/blob/main/esm/sdk/retry.py),
[parallel executor](https://github.com/Biohub/esm/blob/main/esm/utils/forge_context_manager.py).
