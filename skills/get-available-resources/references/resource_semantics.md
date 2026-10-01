# Resource Semantics

Research and behavior cut-off: **2026-10-01**. See
[`sources.md`](sources.md) for the official documentation used.

## Core rule: inventory is not entitlement

Never treat a host-wide count as a promise that the current process can use it.
Interpret usable resources as the intersection of independently observed
constraints:

1. host inventory;
2. process affinity or processor-group scope;
3. cgroup/container constraints;
4. scheduler allocation;
5. accelerator visibility and device permissions; and
6. application runtime compatibility.

Missing evidence means **unknown**, not unlimited. Scheduler variables can
describe an allocation without proving that affinity or cgroup enforcement is
enabled. Conversely, a cgroup or affinity mask can be stricter than the
scheduler request.

## CPU

### Physical and logical CPUs

- A logical CPU is an operating-system scheduling unit. Simultaneous
  multithreading can expose multiple logical CPUs on one physical core.
- A physical-core count describes topology, not the number of independent
  workers the process may start.
- `psutil.cpu_count(logical=True)`, macOS `hw.logicalcpu`, and POSIX
  `SC_NPROCESSORS_ONLN` provide host/system inventory. They can exceed the
  CPUs usable by the process. `os.cpu_count()` is a fallback: Python 3.13+
  `-X cpu_count` or `PYTHON_CPU_COUNT` overrides both Python CPU-count APIs.
  The detector prefers independent inventory and keeps Python process count
  as a separate planning input.
- `os.process_cpu_count()` (Python 3.13+) is process-aware. On supported
  platforms, affinity APIs provide a more explicit process constraint.
- On Windows systems with multiple processor groups, a system-wide logical
  count and one process/thread group's usable count can differ. Windows 11
  and Server 2022 default affinity spans groups; do not assume every modern
  Windows process is capped at 64 logical CPUs.

The detector reports host logical and physical counts separately. It never
derives physical cores from a logical count.

### Affinity, cpusets, and quotas

- Process affinity limits the logical CPUs on which a process may execute.
- Linux `cpuset.cpus.effective` reports CPUs actually granted after parent
  constraints. The requested `cpuset.cpus` can differ.
- `/proc/self/status` exposes `Cpus_allowed_list`, but the detector prefers
  affinity APIs and cgroup effective cpusets.
- cgroup v2 `cpu.max` is `$MAX $PERIOD`. `max` means no local bandwidth limit.
  A finite ratio is CPU-time capacity, possibly fractional; it is not a core
  topology count.
- Parent cgroups also constrain children, so the detector takes the most
  restrictive finite visible ancestor quota. Membership is resolved through
  `/proc/self/mountinfo` cgroup2 root/mountpoint fields. A namespace or delegated
  mount may hide stronger ancestors. Missing files are not evidence of
  unlimited capacity; cgroup v1 is outside the collector's implemented scope.

For a `cpu.max` ratio of 1.5, the snapshot reports
`capacity_cores: 1.5` and a conservative CPU-bound worker ceiling of 1. A
workload may choose more threads for latency hiding, but it should expect
throttling and must not describe those threads as 1.5 physical cores.

### Python worker pools

- Current Python `multiprocessing.Pool` and `ProcessPoolExecutor` defaults use
  `os.process_cpu_count()` when available.
- Python 3.14 no longer uses `fork` as the default start method on any platform.
  Code that depends on a particular start method must request it deliberately.
- Process workers do not make each worker's native-library threads disappear.
  BLAS/OpenMP threads multiplied by process workers commonly oversubscribe an
  allocation.
- Windows `ProcessPoolExecutor` has a documented maximum of 61 workers.

Use the workload planner's worker and threads-per-worker values as conservative
ceilings, then benchmark a real representative workload. Do not run a synthetic
stress test merely to discover capacity.

## Memory

### Host and effective memory

- `psutil.virtual_memory().total` and `.available` describe system-visible
  memory, not necessarily the process limit.
- Linux `/proc/meminfo` `MemAvailable` is the standard-library fallback for a
  host-availability estimate.
- cgroup v2 `memory.current` is current cgroup usage.
- `memory.high` is a throttle/reclaim pressure boundary. Exceeding it does not
  itself invoke the cgroup OOM killer, and the value can be breached.
- `memory.max` is the hard cgroup limit. If usage cannot be reduced at that
  boundary, the cgroup OOM killer can run.
- Parent memory limits are hierarchical. Shared ancestor usage can reduce what
  remains for a child, so effective remaining memory is the minimum finite
  `limit - current` observed through the ancestor chain.
- Slurm memory variables describe requested/allocated memory, but strict
  enforcement depends on site configuration.

The detector keeps host total/available values, cgroup values, scheduler values,
and the conservative effective values distinct. A point-in-time "available"
value can change immediately and is not a reservation.

### macOS unified memory

On Apple silicon, CPU and integrated GPU share unified memory. Do not add a
fictional GPU VRAM amount to system RAM. The snapshot marks the memory model as
`unified_cpu_gpu` and leaves dedicated GPU memory null. Metal framework support
and model/operator support still require application-specific checks.

## Accelerators

Accelerator usability has separate layers:

1. **Hardware or management visibility** — a management query returns a device.
2. **Allocation visibility** — scheduler and named visibility variables permit
   a device or a subset.
3. **Device permission** — the process/container can open the required device
   interfaces.
4. **Driver/runtime compatibility** — driver, CUDA/ROCm/Metal runtime, and
   framework versions are compatible.
5. **Workload compatibility** — the requested operation and data type are
   implemented on that backend.

`nvidia-smi` success confirms NVIDIA management visibility only. It does not
prove that CUDA libraries exist or are compatible. NVIDIA documents driver and
runtime compatibility as a separate requirement.

AMD SMI or ROCm SMI success likewise does not prove HIP/ROCm runtime usability.
New deployments should prefer `amd-smi`; `rocm-smi` is retained as a read-only
fallback. The fixed AMD query selects `--asic --vram`, avoiding unrelated
static fields. Current JSON nests VRAM size as `{value, unit}`; legacy ROCm SMI
uses a flat byte field. AMD SMI labels binary MiB values `MB`, confirmed in its
source conversion. The detector exposes this as `reported_total_bytes` and
leaves dedicated memory null because APU/shared-memory topology is unresolved.
On Linux, AMD recommends `ROCR_VISIBLE_DEVICES`; on Windows it recommends
`HIP_VISIBLE_DEVICES`.

An Apple integrated GPU is a Metal candidate, not a CUDA GPU. AMD SMI records
are ROCm candidates; macOS display records are Metal candidates regardless of
hardware vendor. Neural engines, TPUs, FPGAs, and other accelerators
must also remain distinct from CUDA devices if another inventory source adds
them.

The detector reads only these accelerator variable names and redacts their
values:

- `NVIDIA_VISIBLE_DEVICES`
- `CUDA_VISIBLE_DEVICES`
- `ROCR_VISIBLE_DEVICES`
- `HIP_VISIBLE_DEVICES`

Counts derived from those values are only upper bounds. Environment variables
are not a security boundary and can be reset by an application; device
namespace/cgroup controls are stronger isolation.

Management counts describe records in a particular query. A physical NVIDIA
GPU can expose several MIG devices, and AMD partition modes can also change
runtime enumeration. Use the workload framework in its actual allocation to
count usable devices; do not infer it from these candidate counts.

## Slurm and other schedulers

The detector allowlists named Slurm variables and never dumps the environment.
It records field names, parsed bounded counts, and memory quantities, but not
job IDs, GPU UUIDs, node names, submit hosts, or paths.

Important scopes:

- `SLURM_CPUS_PER_TASK`: requested CPUs per task; suitable as a per-process
  upper bound for one task process.
- `SLURM_CPUS_ON_NODE`: CPUs allocated to the current batch step on the node;
  it can be shared among tasks.
- `SLURM_JOB_CPUS_PER_NODE`: a per-node allocation list, not a process count.
- `SLURM_TASKS_PER_NODE`: compressed counts such as `1(x2),4`; resolve the
  current entry with `SLURM_NODEID`. Without that index, only a uniform list
  is interpretable. Never substitute the first node's task count. The node ID
  itself is not emitted. Requested `SLURM_NTASKS_PER_NODE` is a fallback only
  when the allocation list is absent. Step overrides and heterogeneous job
  components still require application/site-specific interpretation.
- `SLURM_MEM_PER_CPU`: memory per allocated CPU. It becomes a per-task bound
  only when CPUs per task is known.
- `SLURM_MEM_PER_NODE`: shared per-node memory upper bound.
- `SLURM_GPUS_PER_TASK`: requested GPUs per task.
- `SLURM_GPUS_ON_NODE`: GPUs allocated to the batch step on the node.

Slurm CPU confinement requires site configuration such as task affinity or
`task/cgroup` with core constraints. Memory requests are not strictly enforced
unless the site enables an enforcement mechanism. Use affinity and cgroup
observations as enforcement evidence; do not trust visible node inventory.

For other schedulers, use their documented allocation API or variables and the
same rule: allocation metadata and kernel enforcement are different facts.
Do not guess from generic environment names.

## Containers and OCI

Docker containers have no CPU or memory limit by default. When configured,
Docker maps CPU and memory flags to cgroup controls. OCI runtime configuration
also defines CPU, memory, and device constraints.

Inside a container:

- host inventory may remain visible;
- a CPU quota can be smaller than the visible CPU set;
- a cpuset can be smaller than the quota's apparent capacity;
- cgroup memory can be smaller than host RAM;
- GPU management tools can see a different set from the application runtime;
  and
- mounted-volume capacity can differ from writable quota.

Always report observed cgroup controls and uncertainty. A container marker
without a finite cgroup value does not imply a finite limit.

## Disk

Capacity, free blocks, user-writable blocks, path permission, filesystem quota,
and actual ability to complete a write are different:

- capacity is the filesystem's total size;
- POSIX `f_bfree` includes blocks reserved from an unprivileged user;
- `shutil.disk_usage().free` uses `f_bavail` on POSIX, so the detector reads
  `statvfs` to keep filesystem free and user-available values separate;
- POSIX `f_bavail` estimates blocks available to the current user;
- `os.access(..., os.W_OK)` is a non-writing permission check, not proof that a
  future write will succeed;
- project/user quotas and remote storage policies can be stricter than block
  counts.

The detector does not create a probe file. It redacts the absolute working path
and labels the scope as the working filesystem.
