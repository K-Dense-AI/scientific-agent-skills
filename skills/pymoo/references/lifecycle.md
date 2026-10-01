# Execution, termination, and reproducibility (pymoo 0.6.2)

## Bounded runs and callbacks

`minimize` deep-copies the algorithm and termination by default. Inspect the state
at `result.algorithm`, not the original object. For fresh runs use a fresh
algorithm or the default copy behavior; reusing an already initialized algorithm
can resume it instead of starting over.

```python
import numpy as np
from pymoo.algorithms.soo.nonconvex.ga import GA
from pymoo.core.callback import Callback
from pymoo.optimize import minimize
from pymoo.problems import get_problem
from pymoo.termination.default import DefaultSingleObjectiveTermination

class Progress(Callback):
    def __init__(self):
        super().__init__()
        self.data["trace"] = []

    def notify(self, algorithm):
        self.data["trace"].append((algorithm.n_gen,
            algorithm.evaluator.n_eval, float(algorithm.opt.get("F").min())))

problem = get_problem("sphere", n_var=3)
termination = DefaultSingleObjectiveTermination(
    xtol=1e-8, cvtol=1e-6, ftol=1e-6, period=10,
    n_max_gen=20, n_max_evals=400)
result = minimize(problem, GA(pop_size=20), termination,
                  seed=7, callback=Progress(), save_history=False)
trace = result.algorithm.callback.data["trace"]
assert trace[-1][1] == result.algorithm.evaluator.n_eval
assert result.algorithm.n_gen == trace[-1][0] + 1
```

`n_gen` counts the initialization as the first generation. After a completed run
the algorithm's counter has advanced to the next iteration; callback/history
entries contain the completed generation numbers. `save_history=True` stores deep
copies and can be costly; callbacks can retain only scalar diagnostics.

Valid `get_termination` names include `n_gen`, `n_eval`/`n_evals`, `time`, `fmin`,
`soo`, and `moo`. `get_termination("f_tol", ...)` is obsolete. For multi-objective
tolerance stopping use `DefaultMultiObjectiveTermination(ftol=..., period=...,
n_max_gen=..., n_max_evals=...)` or compose the explicit termination classes.

Termination is checked at iteration boundaries: evaluation/time limits may be
exceeded by a generation or a slow objective call. They do not interrupt a running
external simulator. The default combined criteria use OR logic. Larger tolerance
values make convergence stopping easier; they do **not** disable a criterion,
despite conflicting prose on the current upstream termination page. For a pure
budget use `("n_gen", N)` or `("n_eval", N)` directly. MOO objective termination
tracks normalized ideal/nadir changes and inter-generation IGD; it is not an HV
or global-optimality test.

## Resume an algorithm checkpoint

Install optional `dill` (`uv pip install dill`) for the upstream checkpoint recipe.
The 0.6.2 algorithm contains decorated functions that failed standard-library
`pickle` in the tested stack; the `dill` round trip below was tested against an
uninterrupted run. Only load checkpoints you trust, and record the
package versions, problem code, transforms, seed protocol, and objective inputs.
Python object serialization is not a portable cross-version interchange format.

```python
import dill
from pathlib import Path
from pymoo.termination import get_termination

first = minimize(problem, GA(pop_size=20), ("n_gen", 3), seed=7)
checkpoint_path = Path("checkpoint.pkl")
checkpoint_path.write_bytes(dill.dumps(first.algorithm))
checkpoint = dill.loads(checkpoint_path.read_bytes())
checkpoint.termination = get_termination("n_gen", 6)  # new total generation limit
resumed = minimize(problem, checkpoint, copy_algorithm=False)
assert resumed.algorithm.evaluator.n_eval == 120
```

Save `result.algorithm` when default copying is enabled. Alternatively set
`copy_algorithm=False` on the initial call and save that actual running object.
Replace an already satisfied termination object before resuming. Preserve the
algorithm's RNG state; do not reseed workers or regenerate stochastic objective
outputs accidentally. A table of `X/F/G/H` is biased initialization, not a full
checkpoint: it lacks algorithm and RNG state. Re-evaluate any imported table if
its problem/units/constraints differ. Serial checkpoint equality was tested; live
workers, remote solvers, and changes of dependency versions were not.

## Validation before scientific use

1. Evaluate known feasible/infeasible points and analytic objective values.
2. Check finite outputs, bounds, types, constraint signs, and shape contracts.
3. Inspect raw residuals and the feasible-run rate; failed or infeasible runs are
   part of the result, not observations to discard silently.
4. For multi-objective output, verify nondominance within the returned set and
   compare against a credible analytic/reference front if one exists.
5. Compare repeated seeds at equal evaluation budgets and common normalization.
   Report spread, evaluation count, time, and indicator/reference-point choices.
   Seed equality in one pinned environment does not imply cross-version or
   parallel stochastic reproducibility.

Sources reviewed 2026-10-01: [minimize](https://pymoo.org/interface/minimize.html),
[callback](https://pymoo.org/interface/callback.html),
[termination](https://pymoo.org/interface/termination.html),
[checkpoint](https://pymoo.org/misc/checkpoint.html), and released source under
`pymoo/core/algorithm.py`, `pymoo/termination/`, and `pymoo/optimize.py`.
