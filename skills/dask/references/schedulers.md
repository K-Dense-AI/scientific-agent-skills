# Dask Schedulers

Reviewed with Dask/distributed 2026.8.0. File paths, deployment settings, and undefined application functions are illustrative; executed local checks and current official sources are in [review.md](review.md).

## Overview

Dask provides multiple task schedulers, each suited to different workloads. The scheduler determines how tasks are executed: sequentially, in parallel threads, in parallel processes, or distributed across a cluster.

## Scheduler Types

In scripts, guard process scheduler execution and local process-cluster creation with `if __name__ == "__main__":`. Array/DataFrame defaults below apply when no active distributed client or explicit configuration overrides them. Close both client and any separately created cluster when finished.

### Single-Machine Schedulers

#### 1. Local Threads (Default)

**Description**: The threaded scheduler executes computations with a local `concurrent.futures.ThreadPoolExecutor`.

**When to Use**:
- Numeric computations in NumPy, Pandas, scikit-learn
- Libraries that release the GIL (Global Interpreter Lock)
- Operations benefit from shared memory access
- Default for Dask Arrays and DataFrames

**Characteristics**:
- Low overhead
- Shared memory between threads
- Best for GIL-releasing operations
- Poor for pure Python code (GIL contention)

**Example**:
```python
import dask.array as da

# Uses threads by default
x = da.random.random((10000, 10000), chunks=(1000, 1000))
result = x.mean().compute()  # Computed with threads
```

**Explicit Configuration**:
```python
import dask

# Set globally
dask.config.set(scheduler='threads')

# Or per-compute
result = x.mean().compute(scheduler='threads')
```

#### 2. Local Processes

**Description**: Multiprocessing scheduler that uses `concurrent.futures.ProcessPoolExecutor`.

**When to Use**:
- Pure Python code with GIL contention
- Text processing and Python collections
- Operations that benefit from process isolation
- CPU-bound Python code

**Characteristics**:
- Bypasses GIL limitations
- Incurs data transfer costs between processes
- Higher overhead than threads
- Ideal for linear workflows with small inputs/outputs

**Example**:
```python
import dask.bag as db

# Good for Python object processing
bag = db.read_text('data/*.txt')
result = bag.map(complex_python_function).compute(scheduler='processes')
```

**Explicit Configuration**:
```python
import dask

# Set globally
dask.config.set(scheduler='processes')

# Or per-compute
result = computation.compute(scheduler='processes')
```

**Limitations**:
- Data must be serializable (pickle)
- Overhead from process creation
- Memory overhead from data copying

#### 3. Single Thread (Synchronous)

**Description**: The single-threaded synchronous scheduler executes all computations in the local thread with no parallelism at all.

**When to Use**:
- Debugging with pdb
- Profiling with standard Python tools
- Understanding errors in detail
- Development and testing

**Characteristics**:
- No parallelism
- Easy debugging
- Low scheduler overhead
- Serial execution; random functions and side effects still need reproducibility controls

**Example**:
```python
import dask

# Enable for debugging
dask.config.set(scheduler='synchronous')

# Now can use pdb
result = computation.compute()  # Runs in single thread
```

**Debugging with IPython**:
```python
# In IPython/Jupyter
%pdb on

dask.config.set(scheduler='synchronous')
result = problematic_computation.compute()  # Drops into debugger on error
```

### Distributed Schedulers

#### 4. Local Distributed

**Description**: Despite its name, this scheduler runs effectively on personal machines using the distributed scheduler infrastructure.

**When to Use**:
- Need diagnostic dashboard
- Asynchronous APIs
- Better data locality handling than multiprocessing
- Development before scaling to cluster
- Want distributed features on single machine

**Characteristics**:
- Provides dashboard for monitoring
- Better memory management
- More overhead than threads/processes
- Can scale to cluster later

**Example**:
```python
from dask.distributed import Client
import dask.dataframe as dd

# Create local cluster
client = Client(n_workers=2, threads_per_worker=2)  # Explicit resource budget

# Use distributed scheduler
ddf = dd.read_csv('data.csv')
result = ddf.groupby('category')['value'].mean().compute()

# View dashboard
print(client.dashboard_link)

# Clean up
client.close()
```

**Configuration Options**:
```python
# Control resources
client = Client(
    n_workers=4,
    threads_per_worker=2,
    memory_limit='4GB'
)
```

#### 5. Cluster Distributed

**Description**: For scaling across multiple machines using the distributed scheduler.

**When to Use**:
- Data exceeds single machine capacity
- Need computational power beyond one machine
- Production deployments
- Cluster computing environments (HPC, cloud)

**Characteristics**:
- Scales to hundreds of machines
- Requires cluster setup
- Network communication overhead
- Advanced features (adaptive scaling, task prioritization)

**Example with Dask-Jobqueue (HPC)**:
```python
from dask_jobqueue import SLURMCluster
from dask.distributed import Client

# Create cluster on HPC with SLURM
cluster = SLURMCluster(
    cores=24,
    memory='100GB',
    walltime='02:00:00',
    queue='regular'
)

# Scale to 10 jobs
cluster.scale(jobs=10)

# Connect client
client = Client(cluster)

# Run computation
result = computation.compute()

client.close()
cluster.close()  # Release the jobs owned by this cluster
```

**Example with Dask on Kubernetes**:
```python
from dask_kubernetes.operator import KubeCluster
from dask.distributed import Client

# Illustrative: requires installed Dask Operator/CRDs and authorized kubeconfig.
# Use an image with matching dask/distributed and workload dependencies.
cluster = KubeCluster(name='research-dask', image=validated_worker_image)
cluster.scale(20)  # 20 workers

client = Client(cluster)
result = computation.compute()

client.close()
cluster.close()
```

Both deployment recipes require site-specific configuration and were not deployed in this review.

## Scheduler Configuration

### Global Configuration

```python
import dask

# Set scheduler globally for session
dask.config.set(scheduler='threads')
dask.config.set(scheduler='processes')
dask.config.set(scheduler='synchronous')
```

### Context Manager

```python
import dask

# Temporarily use different scheduler
with dask.config.set(scheduler='processes'):
    result = computation.compute()

# Back to default scheduler
result2 = computation2.compute()
```

### Per-Compute

```python
# Specify scheduler per compute call
result = computation.compute(scheduler='threads')
result = computation.compute(scheduler='processes')
result = computation.compute(scheduler='synchronous')
```

### Distributed Client

```python
from dask.distributed import Client

# Using client automatically sets distributed scheduler
client = Client()

# All computations use distributed scheduler
result = computation.compute()

client.close()
```

## Choosing the Right Scheduler

### Decision Matrix

| Workload Type | Recommended Scheduler | Rationale |
|--------------|----------------------|-----------|
| NumPy/Pandas operations | Threads (default) | GIL-releasing, shared memory |
| Pure Python objects | Processes | Avoids GIL contention |
| Text/log processing | Processes | Python-heavy operations |
| Debugging | Synchronous | Easy debugging, deterministic |
| Need dashboard | Local Distributed | Monitoring and diagnostics |
| Multi-machine | Cluster Distributed | Exceeds single machine capacity |
| Small data, quick tasks | Threads | Lowest overhead |
| Large data, single machine | Local Distributed | Better memory management |

### Performance Considerations

**Threads**:
- Low overhead; measure with representative tasks
- Best for: Numeric operations
- Memory: Shared
- GIL: Affected by GIL

**Processes**:
- Includes process startup and serialization costs
- Best for: Python operations
- Memory: Copied between processes
- GIL: Not affected

**Synchronous**:
- Low overhead; no concurrent execution
- Best for: Debugging
- Memory: No parallelism
- GIL: Not relevant

**Distributed**:
- Overhead: ~1 ms per task
- Best for: Complex workflows, monitoring
- Memory: Managed by scheduler
- GIL: Workers can use threads or processes

## Thread Configuration for Distributed Scheduler

### Setting Thread Count

```python
from dask.distributed import Client

# Control thread/worker configuration
client = Client(
    n_workers=4,           # Number of worker processes
    threads_per_worker=2   # Threads per worker process
)
```

### Recommended Configuration

**For Numeric Workloads**:
- Aim for roughly 4 threads per process
- Balance between parallelism and overhead
- Example: 8 cores → 2 workers with 4 threads each

**For Python Workloads**:
- Use more workers with fewer threads
- Example: 8 cores → 8 workers with 1 thread each

### Configuration via dask.config

Prefer `dask.config` over shell environment variables so worker settings stay explicit in code:

```python
import dask

dask.config.set({
    "distributed.worker.memory.target": 0.60,
    "distributed.worker.memory.spill": 0.70,
})
```

When creating a `Client`, pass resource limits directly:

```python
from dask.distributed import Client

client = Client(n_workers=4, threads_per_worker=2, memory_limit='4GB')
```

Upstream also supports `DASK_*` environment variables (for example `DASK_SCHEDULER_ADDRESS` when connecting to an existing cluster). Set only the specific variables documented for your deployment — do not copy entire `.env` files into the environment.

## Common Patterns

### Development to Production

```python
# Development: Use local distributed for testing
from dask.distributed import Client
client = Client(processes=False)  # In-process for debugging

# Production: Scale to cluster
from dask.distributed import Client
client = Client('scheduler-address:8786')
```

### Mixed Workloads

```python
import dask
import dask.dataframe as dd

# Use threads for DataFrame operations
ddf = dd.read_parquet('data.parquet')
result1 = ddf['value'].mean().compute(scheduler='threads')

# Use processes for Python code
import dask.bag as db
bag = db.read_text('logs/*.txt')
result2 = bag.map(parse_log).compute(scheduler='processes')
```

### Debugging Workflow

```python
import dask

# Step 1: Debug with synchronous scheduler
dask.config.set(scheduler='synchronous')
result = problematic_computation.compute()

# Step 2: Test with threads
dask.config.set(scheduler='threads')
result = computation.compute()

# Step 3: Scale with distributed
from dask.distributed import Client
client = Client()
result = computation.compute()
```

## Monitoring and Diagnostics

### Dashboard Access (Distributed Only)

```python
from dask.distributed import Client

client = Client()

# Get dashboard URL
print(client.dashboard_link)
# Opens dashboard in browser showing:
# - Task progress
# - Worker status
# - Memory usage
# - Task stream
# - Resource utilization
```

### Performance Profiling

```python
# Full report captures only the work inside the context. Requires Bokeh.
from dask.distributed import performance_report

with performance_report(filename='performance.html'):
    result = computation.compute()
# client.profile(filename='profile.html') gives statistical stack profiling only.
```

### Resource Monitoring

```python
# Check worker info
client.scheduler_info()

# Get current tasks
client.who_has()

# Host RAM percentage (not each worker's managed-memory usage)
def host_memory_percent():
    import psutil
    return psutil.virtual_memory().percent
client.run(host_memory_percent)
```

## Advanced Configuration

### Custom Executors

```python
from concurrent.futures import ThreadPoolExecutor
import dask

# Use custom thread pool
with ThreadPoolExecutor(max_workers=4) as executor:
    with dask.config.set(pool=executor):
        result = computation.compute(scheduler='threads')
```

### Adaptive Scaling (Distributed)

```python
from dask.distributed import Client

client = Client()

# Enable adaptive scaling
client.cluster.adapt(minimum=2, maximum=10)

# Cluster scales based on workload
result = computation.compute()
```

### Worker Plugins

```python
from dask.distributed import Client, WorkerPlugin

class CustomPlugin(WorkerPlugin):
    def setup(self, worker):
        # Initialize worker-specific resources
        worker.custom_resource = initialize_resource()

client = Client()
client.register_plugin(CustomPlugin(), name='custom-resource')
```

## Troubleshooting

### Slow Performance with Threads
**Problem**: Pure Python code slow with threaded scheduler
**Solution**: Switch to processes or distributed scheduler

### Memory Errors with Processes
**Problem**: Data too large to pickle/copy between processes
**Solution**: Use threaded or distributed scheduler

### Debugging Difficult
**Problem**: Can't use pdb with parallel schedulers
**Solution**: Use synchronous scheduler for debugging

### Task Overhead High
**Problem**: Many tiny tasks causing overhead
**Solution**: Use threaded scheduler (lowest overhead) or increase chunk sizes
