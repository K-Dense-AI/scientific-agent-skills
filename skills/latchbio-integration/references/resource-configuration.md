# Task Resource Configuration

This reference targets `latch==2.76.8`. Resource shapes are operational
configuration and can change independently of examples. Inspect the installed
SDK before making cost or capacity guarantees.

## Selection Strategy

1. Start with the smallest named decorator that can run the task.
2. Measure CPU, peak RSS, temporary storage, wall time, and GPU utilization.
3. Move to a larger named decorator only when evidence justifies it.
4. Use `custom_task` for CPU-only shapes not represented by a named decorator.
5. Use a named GPU decorator; `custom_task` does not accept `gpu` or
   `gpu_type` arguments.
6. Re-measure with representative scientific data before release.

## Named CPU Decorators

```python
from latch.resources.tasks import large_task, medium_task, small_task


@small_task
def parse_manifest():
    ...


@medium_task
def align_reads():
    ...


@large_task
def assemble_genome():
    ...
```

SDK 2.76.8 configures these scheduler requests:

| Decorator | CPU | RAM | Ephemeral storage |
|---|---:|---:|---:|
| `small_task` | 2 | 4 GiB | 100 GiB |
| `medium_task` | 30 | 100 GiB | 1500 GiB |
| `large_task` | 90 | 170 GiB | 4500 GiB |

The public guide may display nominal instance capacities rather than the
schedulable requests encoded in the package. The installed package determines
what registration serializes.

## Named GPU Decorators

Generic GPU shapes:

```python
from latch.resources.tasks import large_gpu_task, small_gpu_task
```

| Decorator | CPU | RAM | GPU |
|---|---:|---:|---|
| `small_gpu_task` | 7 | 30 GiB | 1× T4-class |
| `large_gpu_task` | 63 | 245 GiB | 1× A10G-class |

V100 shapes:

```python
from latch.resources.tasks import (
    v100_x1_task,
    v100_x4_task,
    v100_x8_task,
)
```

L40S shapes:

```python
from latch.resources.tasks import (
    g6e_xlarge_task,
    g6e_2xlarge_task,
    g6e_4xlarge_task,
    g6e_8xlarge_task,
    g6e_12xlarge_task,
    g6e_16xlarge_task,
    g6e_24xlarge_task,
    g6e_48xlarge_task,
)
```

Current L40S scheduler requests and limits:

| Decorator | Request CPU | Request RAM | Limit CPU | Limit RAM | GPUs |
|---|---:|---:|---:|---:|---:|
| `g6e_xlarge_task` | 2 | 28 GiB | 4 | 32 GiB | 1 |
| `g6e_2xlarge_task` | 6 | 57 GiB | 8 | 64 GiB | 1 |
| `g6e_4xlarge_task` | 14 | 115 GiB | 16 | 128 GiB | 1 |
| `g6e_8xlarge_task` | 30 | 230 GiB | 32 | 256 GiB | 1 |
| `g6e_12xlarge_task` | 46 | 345 GiB | 48 | 384 GiB | 4 |
| `g6e_16xlarge_task` | 62 | 460 GiB | 64 | 512 GiB | 1 |
| `g6e_24xlarge_task` | 94 | 691 GiB | 96 | 768 GiB | 4 |
| `g6e_48xlarge_task` | 190 | 1382 GiB | 192 | 1536 GiB | 8 |

GPU availability, quotas, and platform mapping can change. Confirm in the
current docs or with Latch support before promising a specific model to users.

## Custom CPU, Memory, and Storage

Exact stable signature:

```python
custom_task(
    cpu,
    memory,
    *,
    storage_gib=500,
    timeout=0,
    **task_options,
)
```

Example:

```python
from datetime import timedelta

from latch import custom_task


@custom_task(
    cpu=12,
    memory=48,
    storage_gib=750,
    timeout=timedelta(hours=6),
    retries=1,
)
def call_variants():
    ...
```

In SDK 2.76.8, `custom_task` accepts up to 126 CPU cores, 975 GiB RAM, and
4949 GiB ephemeral storage. Not every arbitrary combination fits a schedulable
node group; the decorator selects the smallest configured group that satisfies
all three requests.

`custom_memory_optimized_task` is deprecated. Use `custom_task`.

## Dynamic Resources

Each `cpu`, `memory`, or `storage_gib` argument may be a function of task
inputs. The resource function's annotated parameters must exist in the task
with exactly matching annotations.

```python
from latch import custom_task
from latch.types import LatchFile


def allocate_cpu(files: list[LatchFile]) -> int:
    return min(32, max(2, len(files) * 2))


def allocate_storage(files: list[LatchFile]) -> int:
    sizes = [file.size() for file in files]
    if any(size is None for size in sizes):
        raise ValueError("unable to determine every input size")
    total_bytes = sum(int(size) for size in sizes)
    estimated_gib = total_bytes / (1024**3)
    return max(100, int(estimated_gib * 2) + 1)


@custom_task(
    cpu=allocate_cpu,
    memory=64,
    storage_gib=allocate_storage,
)
def merge_files(files: list[LatchFile]) -> LatchFile:
    ...
```

Dynamic functions execute at runtime before the task launches.

Guardrails:

- Return integers.
- Bound every computed resource.
- Include overhead for decompression and intermediate files.
- Keep computation deterministic and fast.
- Do not make network calls or retrieve secrets from resource functions.
- Test the exact annotation matching during staging registration.

## Cache, Retries, and Timeout

Named decorators and non-dynamic `custom_task` accept Flyte task options:

```python
@medium_task(
    cache=True,
    cache_version="aligner-2.1-reference-v4",
    retries=2,
    timeout=7200,
)
def align_reads():
    ...
```

- Cache deterministic outputs only.
- Include tool, reference, and behavior changes in `cache_version`.
- Use retries for transient infrastructure or network errors.
- Do not retry deterministic invalid-input failures.
- A timeout can be seconds or `datetime.timedelta`.

## Temporary and Persistent Storage

Ephemeral task storage is deleted with the task environment. Use it for:

- Decompressed inputs
- Tool work directories
- Sort spills
- Intermediate indexes

Return a `LatchFile` or `LatchDir`, or upload through `LPath`, for persistent
outputs. Never assume `/tmp` or `/root` survives task completion.

Estimate storage from peak simultaneous intermediates, not final output size:

```text
requested storage
  >= staged inputs
   + decompressed expansion
   + peak tool intermediates
   + final outputs
   + safety margin
```

## Cost and Launch Safety

- Surface the chosen resource class before registration or launch.
- Obtain confirmation before starting large or GPU-backed executions.
- Prefer a representative small launch plan for validation.
- Parallelism multiplies cost; map width matters as much as per-task size.
- Cache hits can reduce cost but are not a substitute for reproducible inputs.
- Compare resource monitoring against scientific throughput, not utilization
  alone.

## Troubleshooting

### Out of memory

- Check peak RSS, not average memory.
- Identify whether an algorithm scales with records, bases, or samples.
- Increase memory only after ruling out unbounded accumulation.

### Out of storage

- Inspect hidden tool caches and decompressed inputs.
- Clean intermediates within the task when safe.
- Increase `storage_gib` based on peak use.

### CPU under-utilization

- Confirm the scientific tool received its thread/process flag.
- Avoid requesting more cores than the tool can use.
- Check I/O and memory bandwidth before scaling CPU.

### GPU under-utilization

- Verify the tool was built with the expected CUDA support.
- Check batch size, data loading, and CPU preprocessing.
- Avoid multi-GPU shapes unless the application implements distributed work.

## Official Sources

- Resource guide: https://wiki.latch.bio/workflows/sdk/python/defining-cloud-resources
- Resource monitoring: https://wiki.latch.bio/workflows/sdk/console/resource-monitoring
- Task source in the 2.76.8 release commit: https://github.com/latchbio/latch/blob/0faa9dcd8186444ac008f50adf95d43f0fa30e06/src/latch/resources/tasks.py
- Changelog in the 2.76.8 release commit: https://github.com/latchbio/latch/blob/0faa9dcd8186444ac008f50adf95d43f0fa30e06/CHANGELOG.md
