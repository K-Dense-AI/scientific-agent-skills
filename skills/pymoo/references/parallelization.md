# Parallel evaluation (pymoo 0.6.2)

Use a runner when individual evaluations dominate overhead. `ElementwiseProblem`
sets `elementwise=True`; no `elementwise_evaluation` argument is needed. Its
`_evaluate` receives one candidate, while the runner schedules multiple candidates.
Vectorized `Problem` evaluates a matrix directly and may be faster for NumPy models.

## Threads or processes

```python
from multiprocessing.pool import ThreadPool
from pymoo.algorithms.soo.nonconvex.ga import GA
from pymoo.core.problem import ElementwiseProblem
from pymoo.optimize import minimize
from pymoo.parallelization.starmap import StarmapParallelization

class MyProblem(ElementwiseProblem):
    def __init__(self, **kwargs):
        super().__init__(n_var=3, n_obj=1, xl=-5, xu=5, **kwargs)

    def _evaluate(self, x, out, *args, **kwargs):
        out["F"] = (x**2).sum()

if __name__ == "__main__":
    with ThreadPool(2) as pool:
        problem = MyProblem(elementwise_runner=StarmapParallelization(pool.starmap))
        result = minimize(problem, GA(pop_size=20), ("n_gen", 5), seed=1)
```

The native test checks serial/thread equality on deterministic evaluations.
For CPU-bound Python functions, substitute `multiprocessing.get_context("spawn").Pool(2)`
inside the main guard. Keep worker classes/functions at importable module scope.
That process-pool variant is illustrative; it was not executed in this refresh.
Threads suit I/O and native code that releases the GIL. Avoid nested oversubscription
from BLAS or model runtimes. Context managers release workers on exceptions.

## Joblib

```python
from pymoo.parallelization.joblib import JoblibParallelization
runner = JoblibParallelization(n_jobs=2, backend="threading")
problem = MyProblem(elementwise_runner=runner)
result = minimize(problem, GA(pop_size=20), ("n_gen", 5), seed=1)
```

Install `joblib` separately. The constructor accepts `n_jobs` and joblib keyword
arguments; it does not take a lambda that manually wraps `Parallel`. The default
backend is joblib's process-based `loky`. Threading was executed here; distributed
and GPU evaluation require separate validation for the user's model and resources.

Optimizer seeds do not automatically seed stochastic external simulations or
worker-local RNGs. Supply deterministic per-evaluation seeds when appropriate and
record the evaluation protocol. Serialization of an algorithm does not preserve
live pools, remote clients, or external simulator state; recreate those resources
when resuming a checkpoint.

Sources: [Starmap](https://pymoo.org/parallelization/starmap.html),
[Joblib](https://pymoo.org/parallelization/joblib.html), and released 0.6.2 source;
reviewed 2026-10-01.
