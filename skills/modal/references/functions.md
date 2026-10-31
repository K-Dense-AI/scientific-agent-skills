# Modal Functions and Classes

Reviewed against Modal 1.6.0. Snippets with application-specific helpers are illustrative.
Sources: [invocation methods](https://modal.com/docs/guide/function-invocation-methods),
[lifecycle](https://modal.com/docs/guide/lifecycle-functions),
[timeouts](https://modal.com/docs/guide/timeouts), and [SDK releases](https://modal.com/docs/sdk/py/releases).

## Table of Contents

- [Functions](#functions)
- [Remote Execution](#remote-execution)
- [Classes with Lifecycle Hooks](#classes-with-lifecycle-hooks)
- [Parallel Execution](#parallel-execution)
- [Async Functions](#async-functions)
- [Local Entrypoints](#local-entrypoints)
- [Generators](#generators)

## Functions

### Basic Function

```python
import modal

app = modal.App("my-app")

@app.function()
def compute(x: int, y: int) -> int:
    return x + y
```

### Function Parameters

The `@app.function()` decorator accepts:

| Parameter | Type | Description |
|-----------|------|-------------|
| `image` | `Image` | Container image |
| `gpu` | `str` or `list[str]` | GPU type/count or ordered fallbacks |
| `cpu` | `float` or tuple | Physical-core request or `(request, limit)` |
| `memory` | `int` or tuple | MiB request or `(request, limit)` |
| `timeout` | `int` | Max execution time in seconds |
| `startup_timeout` | `int` | Separate container initialization timeout |
| `secrets` | `list[Secret]` | Secrets to inject |
| `volumes` | `dict[str, Volume]` | Volumes to mount |
| `schedule` | `Schedule` | Cron or periodic schedule |
| `max_containers` | `int` | Max container count |
| `min_containers` | `int` | Minimum warm containers |
| `retries` | `int` or `Retries` | Retry policy per input |
| `ephemeral_disk` | `int` | Disk in MiB |

Use `max_containers` to cap containers and `@modal.concurrent(max_inputs=N)` to cap
simultaneous inputs per container. The old `concurrency_limit` keyword is removed.

## Remote Execution

### `.remote()` — Synchronous Call

```python
result = compute.remote(3, 4)  # Runs in the cloud, blocks until done
```

### `.local()` — Local Execution

```python
result = compute.local(3, 4)  # Runs locally (for testing)
```

`.local()` applies no Image, GPU, Secret, Volume or concurrency configuration.

### `.spawn()` — Async Fire-and-Forget

```python
call = compute.spawn(3, 4)  # Returns immediately
# ... do other work ...
result = call.get()  # Retrieve result later
```

`.spawn()` supports up to 1 million queued asynchronous inputs. Use a deployed Function
for jobs that must survive the invoking process; an ephemeral App still ends when its
run ends. Persist `call.object_id` and later use `modal.FunctionCall.from_id(id)`.
`call.get(timeout=0)` polls and raises `TimeoutError` while pending; outputs expire
7 days after completion (`modal.exception.OutputExpiredError`). This is separate from
the Function's execution timeout. Retryable jobs must tolerate repeated execution.

## Classes with Lifecycle Hooks

Use `@app.cls()` for stateful workloads where you want to load resources once:

```python
@app.cls(gpu="L40S", image=image)
class Model:
    @modal.enter()
    def setup(self):
        """Runs once when the container starts."""
        import torch
        self.model = build_model()  # Project-defined architecture matching training
        state_dict = torch.load(
            "/weights/model_state.pt", map_location="cpu", weights_only=True
        )
        self.model.load_state_dict(state_dict)
        self.model.eval()  # PyTorch inference mode — not Python's built-in eval()

    @modal.method()
    def predict(self, text: str) -> dict:
        """Callable remotely."""
        return self.model(text)

    @modal.exit()
    def teardown(self):
        """Runs when the container shuts down."""
        cleanup_resources()
```

This lifecycle template requires the project's architecture, preprocessing, and
checkpoint to be included in the Image or mounted storage. Save a `state_dict`
and instantiate the matching model before loading it; a loaded weight dictionary
is not a callable model. For GPU inference, move both model and tensor inputs to
the same CUDA device. See the [PyTorch checkpoint guide](https://docs.pytorch.org/tutorials/beginner/saving_loading_models.html).

### Lifecycle Decorators

| Decorator | When It Runs |
|-----------|-------------|
| `@modal.enter()` | Once on container startup, before any inputs |
| `@modal.method()` | For each remote call |
| `@modal.exit()` | On shutdown/preemption, with a 30-second grace period |

Checkpoint during work; abrupt failures need not complete cleanup. For a web method,
use its web decorator instead of stacking it with `@modal.method()`.

### Calling Class Methods

```python
# Create instance and call method
model = Model()
result = model.predict.remote("Hello world")

# Parallel calls
results = list(model.predict.map(["text1", "text2", "text3"]))
```

### Parameterized Classes

SDK 1.6.0 rejects custom `__init__` methods on Modal classes. Declare parameters as
below, and initialize resources in `@modal.enter()`.

```python
@app.cls()
class Worker:
    model_name: str = modal.parameter()

    @modal.enter()
    def load(self):
        self.model = load_model(self.model_name)

    @modal.method()
    def run(self, data):
        return self.model(data)

# Different model instances autoscale independently
small = Worker(model_name="small-model")
large = Worker(model_name="large-model")
```

## Parallel Execution

### `.map()` — Parallel Processing

Process multiple inputs across containers:

```python
@app.function()
def process(item):
    return heavy_computation(item)

@app.local_entrypoint()
def main():
    items = list(range(1000))
    results = list(process.map(items))
    print(f"Processed {len(results)} items")
```

- Results are returned in the same order as inputs
- Modal autoscales containers to handle the workload
- Use `return_exceptions=True` to collect errors instead of raising

### `.starmap()` — Multi-Argument Parallel

```python
@app.function()
def add(x, y):
    return x + y

results = list(add.starmap([(1, 2), (3, 4), (5, 6)]))
# [3, 7, 11]
```

### `.map()` with `order_outputs=False`

For faster throughput when order doesn't matter:

```python
for result in process.map(items, order_outputs=False):
    handle(result)  # Results arrive as they complete
```

## Async Functions

Modal supports async/await natively:

```python
@app.function(image=modal.Image.debian_slim().uv_pip_install("httpx"))
async def fetch_data(url: str) -> str:
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=30)
        response.raise_for_status()
        return response.text
```

Async functions are especially useful with `@modal.concurrent()` for handling multiple requests per container.
From async caller code use `await fetch_data.remote.aio(url)` and
`async for result in fetch_data.map.aio(urls)`; a blocking `.remote()` call is not awaitable.

## Local Entrypoints

The `@app.local_entrypoint()` runs on your machine and orchestrates remote calls:

```python
@app.local_entrypoint()
def main():
    # This code runs locally
    data = load_local_data()

    # These calls run in the cloud
    results = list(process.map(data))

    # Back to local
    save_results(results)
```

You can also define multiple entrypoints and select by function name:

```bash
modal run script.py::train
modal run script.py::evaluate
```

## Generators

Functions can yield results as they're produced:

```python
@app.function()
def generate_data():
    for i in range(100):
        yield process(i)

@app.local_entrypoint()
def main():
    for result in generate_data.remote_gen():
        print(result)
```

## Retries

Configure automatic retries on failure:

```python
@app.function(retries=3)
def flaky_operation():
    ...
```

For more control, use `modal.Retries`:

```python
@app.function(retries=modal.Retries(max_retries=3, backoff_coefficient=2.0))
def api_call():
    ...
```

## Timeouts

Set maximum execution time:

```python
@app.function(timeout=3600)  # 1 hour
def long_training():
    ...
```

Default timeout is 300 seconds (5 minutes). Maximum is 86400 seconds (24 hours).
This applies to each execution attempt, excluding queue time. Each retry gets a new
timeout. `startup_timeout` independently bounds initialization; if omitted, `timeout`
also supplies the startup bound. After retries are exhausted, timeout surfaces as
`modal.exception.FunctionTimeoutError`.
