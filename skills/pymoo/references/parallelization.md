# Pymoo Parallelization Reference

Reference for parallel evaluation of expensive `ElementwiseProblem` instances.

## When to Use

Use parallelization when `_evaluate` is the bottleneck (simulations, ML inference, external solvers). Pymoo evaluates one solution per `_evaluate` call for `ElementwiseProblem`; pass a runner to evaluate multiple solutions concurrently.

**Requirements:**
- Subclass `ElementwiseProblem` (not vectorized `Problem`)
- Set `elementwise_evaluation=True` (default for `ElementwiseProblem`)
- Pass `elementwise_runner` to the problem constructor

## Starmap Interface (Threads or Processes)

Uses Python's `multiprocessing.Pool.starmap` interface via `StarmapParallelization`.

```python
import multiprocessing
from multiprocessing.pool import ThreadPool

from pymoo.algorithms.soo.nonconvex.ga import GA
from pymoo.core.problem import ElementwiseProblem
from pymoo.optimize import minimize
from pymoo.parallelization.starmap import StarmapParallelization


class MyProblem(ElementwiseProblem):
    def __init__(self, elementwise_runner=None, **kwargs):
        super().__init__(
            n_var=10, n_obj=1, xl=-5, xu=5,
            elementwise_runner=elementwise_runner,
            **kwargs,
        )

    def _evaluate(self, x, out, *args, **kwargs):
        out["F"] = (x ** 2).sum()


# Thread pool (shared memory; good for I/O-bound evaluation)
n_threads = 4
pool = ThreadPool(n_threads)
runner = StarmapParallelization(pool.starmap)
problem = MyProblem(elementwise_runner=runner)

result = minimize(problem, GA(), ("n_gen", 50), seed=1)
pool.close()

# Process pool (separate memory; good for CPU-bound evaluation)
n_processes = 4
pool = multiprocessing.Pool(n_processes)
runner = StarmapParallelization(pool.starmap)
problem = MyProblem(elementwise_runner=runner)

result = minimize(problem, GA(), ("n_gen", 50), seed=1)
pool.close()
```

## Joblib Interface

Alternative using the joblib library:

```python
from joblib import Parallel, delayed
from pymoo.parallelization.joblib import JoblibParallelization

runner = JoblibParallelization(lambda func, X: Parallel(n_jobs=4)(delayed(func)(x) for x in X))
problem = MyProblem(elementwise_runner=runner)
```

Install joblib if needed: `uv pip install joblib`

## Notes

- Always close the pool after `minimize()` completes
- Process pools require picklable problem definitions (avoid lambdas in class bodies)
- Parallelization speedup depends on evaluation cost vs. overhead
- For vectorized problems (`Problem` subclass evaluating batches), implement batching inside `_evaluate` instead

**Documentation:** https://pymoo.org/parallelization/starmap.html
