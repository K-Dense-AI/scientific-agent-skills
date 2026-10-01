# Pymoo Algorithms Reference

Reference for pymoo 0.6.2. Selection guidance is heuristic; compare seeds at matched evaluation budgets. Continuous defaults do not automatically support every variable type.

## Single-Objective Optimization Algorithms

### Genetic Algorithm (GA)
**Purpose:** General-purpose single-objective evolutionary optimization
**Best for:** Continuous problems with default operators; discrete types require compatible operators
**Algorithm type:** (μ+λ) genetic algorithm

**Key parameters:**
- `pop_size`: Population size (default: 100)
- `sampling`: Initial population generation strategy
- `selection`: Parent selection mechanism (default: Tournament)
- `crossover`: Recombination operator (default: SBX)
- `mutation`: Variation operator (default: Polynomial)
- `eliminate_duplicates`: Remove redundant solutions (default: True)
- `n_offsprings`: Offspring per generation

**Usage:**
```python
from pymoo.algorithms.soo.nonconvex.ga import GA
algorithm = GA(pop_size=100, eliminate_duplicates=True)
```

### Differential Evolution (DE)
**Purpose:** Single-objective continuous optimization
**Best for:** Continuous parameter optimization with good global search
**Algorithm type:** Population-based differential evolution

**Variants:** Multiple DE strategies available (rand/1/bin, best/1/bin, etc.)

### Particle Swarm Optimization (PSO)
**Purpose:** Single-objective optimization through swarm intelligence
**Best for:** Continuous problems, fast convergence on smooth landscapes

### CMA-ES
**Purpose:** Covariance Matrix Adaptation Evolution Strategy
**Best for:** Continuous optimization, particularly for noisy or ill-conditioned problems

### Pattern Search
**Purpose:** Direct search method
**Best for:** Problems where gradient information is unavailable

### Nelder-Mead
**Purpose:** Simplex-based optimization
**Best for:** Local optimization of continuous functions

### MixedVariableGA
**Purpose:** Single-objective optimization with mixed variable types
**Best for:** Problems with continuous, integer, binary, and categorical variables

**Usage:**
```python
from pymoo.core.mixed import MixedVariableGA
from pymoo.core.variable import Real, Integer, Choice, Binary

# Define problem with vars dict (see mixed-variable docs)
algorithm = MixedVariableGA(pop_size=20)
```

For multi-objective mixed-variable problems, pass a survival operator:
```python
from pymoo.operators.survival.rank_and_crowding import RankAndCrowding
algorithm = MixedVariableGA(pop_size=20, survival=RankAndCrowding())
```

### Optuna (Mixed-Variable SOO)
**Purpose:** Single-objective mixed-variable search via Optuna wrapper
**Best for:** Hyperparameter-style mixed search when Optuna's TPE/samplers are preferred

**Usage:**
```python
from pymoo.algorithms.soo.nonconvex.optuna import Optuna
algorithm = Optuna()
```

Requires Optuna installed separately: `uv pip install optuna`

## Multi-Objective Optimization Algorithms

### NSGA-II (Non-dominated Sorting Genetic Algorithm II)
**Purpose:** Multi-objective optimization with 2-3 objectives
**Best for:** Bi- and tri-objective problems requiring well-distributed Pareto fronts
**Selection strategy:** Non-dominated sorting + crowding distance

**Key features:**
- Fast non-dominated sorting
- Crowding distance for diversity
- Elitist approach
- Binary tournament mating selection

**Key parameters:**
- `pop_size`: Population size (default: 100)
- `sampling`: Initial population strategy
- `crossover`: Default SBX for continuous
- `mutation`: Default Polynomial Mutation
- `survival`: RankAndCrowding

**Usage:**
```python
from pymoo.algorithms.moo.nsga2 import NSGA2
algorithm = NSGA2(pop_size=100)
```

**When to use:**
- 2-3 objectives
- Need for distributed solutions across Pareto front
- Standard multi-objective benchmark

### SPEA2 (Strength Pareto Evolutionary Algorithm 2)
**Purpose:** Multi-objective optimization using strength and density survival
**Best for:** Bi- and tri-objective problems; alternative to NSGA-II for strength/density selection
**Selection strategy:** Strength-based fitness + k-nearest-neighbor density estimation

**Key features:**
- Strength/density survival in the current population; no separate persistent external archive is configured by this constructor
- Strength value measures how many solutions a point dominates
- Improved in pymoo 0.6.1.6

**Usage:**
```python
from pymoo.algorithms.moo.spea2 import SPEA2
algorithm = SPEA2(pop_size=100)
```

**When to use:**
- 2-3 objectives
- Prefer strength/density survival over crowding distance
- Compare against NSGA-II on benchmark problems

### NSGA-III
**Purpose:** Many-objective optimization (4+ objectives)
**Best for:** Problems with 4 or more objectives requiring uniform Pareto front coverage
**Selection strategy:** Reference direction-based diversity maintenance

**Key features:**
- Reference directions guide population
- Maintains diversity in high-dimensional objective spaces
- Niche preservation through reference points
- Underrepresented reference direction selection

**Key parameters:**
- `ref_dirs`: Reference directions (REQUIRED)
- `pop_size`: Defaults to number of reference directions
- `crossover`: Default SBX
- `mutation`: Default Polynomial Mutation

**Usage:**
```python
from pymoo.algorithms.moo.nsga3 import NSGA3
from pymoo.util.ref_dirs import get_reference_directions

ref_dirs = get_reference_directions("das-dennis", 4, n_partitions=3)  # n_dim is positional
algorithm = NSGA3(ref_dirs=ref_dirs)
```

**NSGA-II vs NSGA-III:**
- Use NSGA-II for 2-3 objectives
- Use NSGA-III for 4+ objectives
- NSGA-III aims to spread candidates over chosen directions; coverage is not guaranteed
- NSGA-II has lower computational overhead

### R-NSGA-II (Reference Point Based NSGA-II)
**Purpose:** Multi-objective optimization with preference articulation
**Best for:** When decision maker has preferred regions of Pareto front

### U-NSGA-III (Unified NSGA-III)
**Purpose:** Improved version handling various scenarios
**Best for:** Many-objective problems with additional robustness

### MOEA/D (Multi-Objective Evolutionary Algorithm based on Decomposition)
**Purpose:** Decomposition-based multi-objective optimization
**Best for:** Unconstrained problems where decomposition into scalar subproblems is effective

Supply `ref_dirs` explicitly (the constructor uses their count). The 0.6.2 implementation rejects constraints. Choose `n_neighbors` no greater than the direction count and compatible with parent selection. Transforming constraints into objectives changes the problem and requires final feasibility checks.

### AGE-MOEA
**Purpose:** Adaptive geometry estimation
**Best for:** Multi and many-objective problems with adaptive mechanisms

### RVEA (Reference Vector guided Evolutionary Algorithm)
**Purpose:** Reference vector-based many-objective optimization
**Best for:** Many-objective problems with adaptive reference vectors

### SMS-EMOA
**Purpose:** S-Metric Selection Evolutionary Multi-objective Algorithm
**Best for:** Problems where hypervolume indicator is critical
**Selection:** Uses dominated hypervolume contribution

## Dynamic Multi-Objective Algorithms

### D-NSGA-II
**Purpose:** Dynamic multi-objective problems
**Best for:** Time-varying objective functions or constraints

### KGB-DMOEA
**Purpose:** Knowledge-guided dynamic multi-objective optimization
**Best for:** Dynamic problems leveraging historical information

## Constrained Optimization

### SRES (Stochastic Ranking Evolution Strategy)
**Purpose:** Single-objective constrained optimization
**Best for:** Heavily constrained problems

### ISRES (Improved SRES)
**Purpose:** Enhanced constrained optimization
**Best for:** Complex constraint landscapes

## Algorithm Selection Guidelines

**For single-objective problems:**
- Start with GA for general problems
- Use DE for continuous optimization
- Try PSO for faster convergence on smooth problems
- Use CMA-ES for difficult/noisy landscapes

**For multi-objective problems:**
- 2-3 objectives: NSGA-II or SPEA2
- 4+ objectives: NSGA-III
- Preference articulation: R-NSGA-II
- Decomposition-friendly: MOEA/D
- Hypervolume focus: SMS-EMOA

**For constrained problems:**
- Check algorithm support: feasibility-based survival is common, but MOEA/D rejects constrained problems
- Heavy constraints: SRES/ISRES
- Penalty methods for algorithm compatibility

**For dynamic problems:**
- Time-varying: D-NSGA-II
- Historical knowledge useful: KGB-DMOEA

For Das-Dennis directions, `get_reference_directions("das-dennis", m, n_partitions=p)` creates `C(p+m-1,m-1)` points on the simplex. With five objectives, p=3 gives 35 directions whereas p=12 gives 1820; NSGA-III defaults its population to this count. Reference directions are not feasible decision vectors or guaranteed Pareto points. NSGA-III also works with two/three objectives; four objectives is a routing heuristic, not an API minimum.

Reviewed 2026-10-01 against [algorithm catalogue](https://pymoo.org/algorithms/list.html), [NSGA-III](https://pymoo.org/algorithms/moo/nsga3.html), [MOEA/D](https://pymoo.org/algorithms/moo/moead.html), [mixed variables](https://pymoo.org/customization/mixed.html), and released source. GA/DE/PSO, mixed/Optuna, NSGA-II/III, and MOEA/D received bounded native checks; the other algorithms are documentation/source-reviewed choices, not performance-validated recommendations.
