# Modal Scaling and Concurrency

Reviewed against SDK 1.6.0 and current [scaling](https://modal.com/docs/guide/scale),
[invocation](https://modal.com/docs/guide/function-invocation-methods),
[concurrency](https://modal.com/docs/guide/concurrent-inputs),
[batching](https://modal.com/docs/guide/dynamic-batching) and
[dynamic configuration](https://modal.com/docs/guide/dynamic-function-config) guides.
Workload placeholders below are illustrative.

## Table of Contents

- [Autoscaling](#autoscaling)
- [Configuration](#configuration)
- [Parallel Execution](#parallel-execution)
- [Concurrent Inputs](#concurrent-inputs)
- [Dynamic Batching](#dynamic-batching)
- [Dynamic Autoscaler Updates](#dynamic-autoscaler-updates)
- [Limits](#limits)

## Autoscaling

Modal automatically manages a pool of containers for each function:
- Spins up containers when there's no capacity for new inputs
- Spins down idle containers to save costs
- Scales container compute to zero by default; persistent storage remains separately billed

No configuration needed for basic autoscaling — it works out of the box.

## Configuration

Fine-tune autoscaling behavior:

```python
@app.function(
    max_containers=100,     # Upper limit on container count
    min_containers=2,       # Keep 2 warm (reduces cold starts)
    buffer_containers=5,    # Reserve 5 extra for burst traffic
    scaledown_window=300,   # Wait 5 min idle before shutting down
)
def handle_request(data):
    ...
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_containers` | Platform/workspace limit | Hard cap for this Function pool |
| `min_containers` | 0 | Minimum warm containers (costs money even when idle) |
| `buffer_containers` | Server-selected when omitted | Extra idle containers while active |
| `scaledown_window` | Server-selected when omitted | Maximum idle seconds while scaling down |

SDK defaults are `None` for omitted settings, allowing platform defaults. Set values
explicitly when required. Containers can shut down sooner than the scaledown window
when overprovisioned. Warm pools reduce cold starts but cannot guarantee their absence.

### Trade-offs

- Higher `min_containers` = lower latency, higher cost
- Higher `buffer_containers` = less queuing, higher cost
- Lower `scaledown_window` = faster cost savings, more cold starts

## Parallel Execution

### `.map()` — Process Many Inputs

```python
@app.function()
def process(item):
    return heavy_computation(item)

@app.local_entrypoint()
def main():
    items = list(range(10_000))
    results = list(process.map(items))
```

Modal automatically scales containers to handle the workload. Results maintain input order.

### `.map()` Options

```python
# Unordered results (faster)
for result in process.map(items, order_outputs=False):
    handle(result)

# Collect errors instead of raising
results = list(process.map(items, return_exceptions=True))
for r in results:
    if isinstance(r, Exception):
        print(f"Error: {r}")
```

### `.starmap()` — Multi-Argument

```python
@app.function()
def add(x, y):
    return x + y

results = list(add.starmap([(1, 2), (3, 4), (5, 6)]))
# [3, 7, 11]
```

### `.spawn()` — Fire-and-Forget

```python
# Returns immediately
call = process.spawn(large_data)

# Check status or get result later
result = call.get()
```

Up to 1 million queued `.spawn()` inputs. Use a deployed Function for durable jobs,
persist the returned call ID, and retrieve outputs within 7 days of completion.
`spawn_map()` submits many inputs but returns **no result handle** in SDK 1.6.0;
each worker must persist its output if it matters.

## Concurrent Inputs

By default, each container handles one input at a time. Use `@modal.concurrent` to handle multiple:

```python
@app.function(gpu="L40S")
@modal.concurrent(max_inputs=10)
async def predict(text: str):
    result = await model.predict_async(text)
    return result
```

This is ideal for I/O-bound workloads or async inference where a single GPU can handle multiple requests.
Synchronous functions use threads; async functions share an event loop. Avoid blocking
that loop. `target_inputs` can be set below `max_inputs` to give autoscaling headroom.

### With Web Endpoints

```python
@app.function(gpu="L40S")
@modal.concurrent(max_inputs=20)
@modal.asgi_app()
def web_service():
    return fastapi_app
```

## Dynamic Batching

Collect inputs into batches for efficient GPU utilization:

```python
@app.function(gpu="L40S")
@modal.batched(max_batch_size=32, wait_ms=100)
async def batch_predict(texts: list[str]):
    # Called with up to 32 texts at once
    embeddings = model.encode(texts)
    return list(embeddings)
```

- `max_batch_size` — Maximum inputs per batch
- `wait_ms` — How long to wait for more inputs before processing
- The function receives a list and must return a list of the same length
- Callers submit individual elements, e.g. `batch_predict.remote("text")`; the decorator batches them
- A class with a batched method cannot contain other Modal methods; validate the selected configuration before enabling concurrency on a batched workload

## Dynamic Autoscaler Updates

Adjust autoscaling at runtime without redeploying:

```python
@app.function()
def scale_up_for_peak():
    process = modal.Function.from_name("my-app", "process")
    process.update_autoscaler(min_containers=10, buffer_containers=20)

@app.function()
def scale_down_after_peak():
    process = modal.Function.from_name("my-app", "process")
    process.update_autoscaler(min_containers=1, buffer_containers=2)
```

Settings revert to the decorator values on the next deployment.
`with_options()`, `with_concurrency()` and `with_batching()` instead create variants
with separate container pools. A base `max_containers` does not cap the sum of variants;
avoid high-cardinality configurations. Variants ignore base `min_containers`, and
`with_options()` does not accept that parameter.

## Limits

| Resource | Limit |
|----------|-------|
| Queued synchronous inputs | 2,000 |
| Total synchronous inputs (running + queued) | 25,000 |
| Pending `.spawn()` inputs | 1,000,000 |
| Concurrent inputs per `.map()` | 1,000 |
| Containers per Function | 4,000, subject to lower workspace/GPU quotas |
| Baseline synchronous invocation rate | 200/s |
| Baseline asynchronous invocation rate | 1,500/s |

These are documented platform limits at review time, not guaranteed capacity.
SDK calls can raise `modal.exception.ResourceExhaustedError`; Web Functions can
return HTTP 429. Use bounded backoff and idempotent work, and check workspace quotas.
