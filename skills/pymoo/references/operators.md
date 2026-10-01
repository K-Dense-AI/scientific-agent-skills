# Genetic operators (pymoo 0.6.2)

Use instantiated operators. Historical strings such as `"real_sbx"`,
`"real_random"`, and `"real_pm"` are not accepted by current GA execution.

## Continuous variables

```python
from pymoo.algorithms.soo.nonconvex.ga import GA
from pymoo.operators.sampling.lhs import LHS
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM

algorithm = GA(pop_size=40, sampling=LHS(),
               crossover=SBX(prob=0.9, eta=15),
               mutation=PM(prob=0.9, prob_var=None, eta=20),
               eliminate_duplicates=True)
```

- Sampling: `FloatRandomSampling()` or `LHS()`. LHS stratifies marginal samples;
  it does not guarantee superior optimizer performance.
- SBX `prob` is the probability of applying crossover to a mating. Its separate
  `prob_var` controls variable exchange (default 0.5). Larger `eta` tends to
  produce offspring closer to their parents.
- PM `prob` is the probability of mutating an **individual**, default 0.9.
  `prob_var` is the per-variable mutation probability. `None` gives
  `min(0.5, 1/problem.n_var)` in 0.6.2. `PM(prob=None)` is not the default-rate
  recipe and can fail during mutation. Larger `eta` concentrates perturbations.
- DE uses its own variation. Configure `DE(variant="DE/rand/1/bin", CR=0.7, F=0.5)`
  from `pymoo.algorithms.soo.nonconvex.de`; do not substitute a string for GA's
  crossover object.

## Binary variables

```python
from pymoo.operators.sampling.rnd import BinaryRandomSampling
from pymoo.operators.crossover.pntx import TwoPointCrossover
from pymoo.operators.mutation.bitflip import BitflipMutation

binary_ga = GA(pop_size=40, sampling=BinaryRandomSampling(),
               crossover=TwoPointCrossover(),
               mutation=BitflipMutation(prob=1.0, prob_var=0.05))
```

`SinglePointCrossover`, `TwoPointCrossover`, `PointCrossover(n_points=...)`,
`UniformCrossover`, and `HalfUniformCrossover` cover common binary recombination.
`UniformCrossover(prob=0.9)` applies crossover to 90% of matings; the internal
per-gene swap probability is fixed at 0.5. `BitflipMutation.prob_var`, not `prob`,
is the per-bit probability. Bitflip expects Boolean decision arrays.

## Integers and mixed variables

```python
from pymoo.operators.sampling.rnd import IntegerRandomSampling
from pymoo.operators.repair.rounding import RoundingRepair

integer_ga = GA(pop_size=40, sampling=IntegerRandomSampling(),
    crossover=SBX(prob=0.9, eta=15, vtype=float, repair=RoundingRepair()),
    mutation=PM(eta=20, vtype=float, repair=RoundingRepair()))
```

Use integral bounds; rounding alone does not impose nonlinear constraints.
For heterogeneous variables, define `vars` using `Real`, `Integer`, `Choice`,
`Binary` and use `MixedVariableGA` or explicit mixed mating. Merely setting a
problem's type does not replace incompatible continuous operators.

## Permutations

```python
from pymoo.operators.sampling.rnd import PermutationRandomSampling
from pymoo.operators.crossover.ox import OrderCrossover
from pymoo.operators.mutation.inversion import InversionMutation

permutation_ga = GA(pop_size=40, sampling=PermutationRandomSampling(),
                    crossover=OrderCrossover(), mutation=InversionMutation())
```

`EdgeRecombinationCrossover` is also available in
`pymoo.operators.crossover.erx`. PMX and scramble mutation are not shipped
operators in 0.6.2; implement and validate a custom operator if required. Preserve
one occurrence of each item, and separately repair domain constraints such as
route precedence.

## Selection and repair

GA and NSGA-II supply algorithm-specific tournament comparators. A bare
`TournamentSelection()` raises an error; a custom instance requires `func_comp`.
For the standard single-objective comparator:

```python
from pymoo.algorithms.soo.nonconvex.ga import comp_by_cv_and_fitness
from pymoo.operators.selection.tournament import TournamentSelection
selection = TournamentSelection(func_comp=comp_by_cv_and_fitness, pressure=2)
```

Use a multi-objective comparator for multi-objective survival/ranking.
`RandomSelection()` from `pymoo.operators.selection.rnd` selects uniformly.

```python
import numpy as np
from pymoo.core.repair import Repair

class BoxRepair(Repair):
    def _do(self, problem, X, **kwargs):
        return np.clip(X, problem.xl, problem.xu)
```

This repairs bounds only. A custom operator should accept `**kwargs`; randomized
operators should use the supplied `random_state` (a NumPy Generator in 0.6.2),
not an unseeded global RNG. Validate bounds, types, and problem-specific invariants
after operator changes, then compare matched budgets over multiple seeds.

Sources reviewed 2026-10-01: [selection](https://pymoo.org/operators/selection.html),
[crossover](https://pymoo.org/operators/crossover.html),
[mutation](https://pymoo.org/operators/mutation.html),
[discrete variables](https://pymoo.org/customization/discrete.html), and released
0.6.2 operator source. Code recipes were instantiated and exercised on toy inputs.
