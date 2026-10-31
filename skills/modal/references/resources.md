# Modal Resource Configuration

Reviewed against SDK 1.6.0 and the official [resource guide](https://modal.com/docs/guide/resources)
and [timeout guide](https://modal.com/docs/guide/timeouts). Examples are configuration
fragments; no remote allocation or billing was measured.

## CPU

### Requesting CPU

```python
@app.function(cpu=4.0)
def compute():
    ...
```

- Values are **physical cores**, not vCPUs
- Default: 0.125 cores
- Modal auto-sets `OPENBLAS_NUM_THREADS`, `OMP_NUM_THREADS`, `MKL_NUM_THREADS` based on your CPU request

### CPU Limits

- Default soft limit: 16 physical cores above the CPU request
- Set explicit limits to prevent noisy-neighbor effects:

```python
@app.function(cpu=(1.0, 4.0))  # Request 1 core, soft limit 4 cores
def bounded_compute():
    ...
```

## Memory

### Requesting Memory

```python
@app.function(memory=16384)  # 16 GiB in MiB
def large_data():
    ...
```

- Value in **MiB** (mebibytes)
- Default: 128 MiB

### Memory Limits

Set hard memory limits to OOM-kill containers that exceed them:

```python
@app.function(memory=(8192, 16384))  # 8 GiB request, 16 GiB hard limit
def bounded_memory():
    ...
```

This prevents paying for runaway memory leaks.
A scalar `memory=8192` is a request, not an explicit hard limit. Requests/limits
are validated against platform capacity; do not assume a requested allocation is available.

## Ephemeral Disk

For temporary storage within a container's lifetime:

```python
@app.function(ephemeral_disk=102400)  # 100 GiB in MiB
def process_dataset():
    # Temporary files at /tmp or anywhere in the container filesystem
    ...
```

- Value in **MiB**
- Default: 512 GiB quota per container
- Maximum: 3,145,728 MiB (3 TiB)
- Data is lost when the container shuts down
- Use Volumes for persistent storage

Larger disk requests increase the memory request at a 20:1 ratio for billing purposes.

## Timeout

```python
@app.function(timeout=3600)  # 1 hour in seconds
def long_running():
    ...
```

- Default: 300 seconds (5 minutes)
- Maximum: 86,400 seconds (24 hours)
- Execution timeout is per attempt; configured retries get a fresh timeout
- Queue time is excluded; `startup_timeout` controls startup independently
- Expiry is approximate and eventually raises `modal.exception.FunctionTimeoutError`

## Billing

You are charged based on **whichever is higher**: your resource request or actual usage.

| Resource | Billing Basis |
|----------|--------------|
| CPU | max(requested, used) |
| Memory | max(requested, used) |
| GPU | Time GPU is allocated |
| Disk | Increases memory billing at 20:1 ratio |

### Cost Optimization Tips

- Request only what you need
- Use appropriate GPU tiers (L40S over H100 for inference)
- Set `scaledown_window` to minimize idle time
- Use `min_containers=0` when cold starts are acceptable
- Batch inputs with `.map()` instead of individual `.remote()` calls

## Complete Example

```python
@app.function(
    cpu=8.0,              # 8 physical cores
    memory=32768,         # 32 GiB
    gpu="L40S",           # L40S GPU
    ephemeral_disk=204800, # 200 GiB temp disk
    timeout=7200,         # 2 hours
    max_containers=50,
    min_containers=1,
)
def full_pipeline(data_path: str):
    ...
```
