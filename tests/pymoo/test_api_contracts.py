"""Native 0.6.2 contracts: numerical errors need numerical regression checks."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("pymoo")
dill = pytest.importorskip("dill")
matplotlib = pytest.importorskip("matplotlib")
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from pymoo.algorithms.moo.moead import MOEAD
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.algorithms.soo.nonconvex.ga import GA
from pymoo.algorithms.soo.nonconvex.de import DE
from pymoo.algorithms.soo.nonconvex.pso import PSO
from pymoo.core.callback import Callback
from pymoo.core.individual import calc_cv
from pymoo.core.population import Population
from pymoo.core.problem import ElementwiseProblem
from pymoo.optimize import minimize
from pymoo.problems import get_problem
from pymoo.termination import get_termination
from pymoo.util.ref_dirs import get_reference_directions

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pymoo"


class ImpossibleProblem(ElementwiseProblem):
    def __init__(self):
        super().__init__(n_var=1, n_obj=1, n_ieq_constr=1, xl=0, xu=1)

    def _evaluate(self, x, out, *args, **kwargs):
        out["F"] = x[0] ** 2
        out["G"] = [1.0]


class Trace(Callback):
    def __init__(self):
        super().__init__()
        self.data["evaluations"] = []

    def notify(self, algorithm):
        self.data["evaluations"].append(algorithm.evaluator.n_eval)


def test_no_feasible_result_is_none_and_least_infeasible_is_labeled():
    p = ImpossibleProblem()
    empty = minimize(p, GA(pop_size=10), ("n_gen", 2), seed=1)
    assert empty.F is None and empty.X is None and empty.CV is None
    diagnostic = minimize(p, GA(pop_size=10), ("n_gen", 2), seed=1,
                          return_least_infeasible=True)
    assert diagnostic.CV[0] == 1
    assert not diagnostic.opt.get("FEAS").any()


def test_equality_tolerance_and_inequality_sign():
    assert calc_cv(G=np.array([-3.0]), H=np.array([5e-5])) == 0
    assert calc_cv(G=np.array([0.2]), H=np.array([2e-4])) == pytest.approx(0.2001)


def test_callback_copy_checkpoint_rng_and_generation_counter():
    problem = get_problem("sphere", n_var=3)
    original = GA(pop_size=20)
    initial = minimize(problem, original, ("n_gen", 3), seed=7,
                       callback=Trace(), save_history=True)
    assert original.pop is None
    assert initial.algorithm.callback.data["evaluations"] == [20, 40, 60]
    assert [entry.n_gen for entry in initial.history] == [1, 2, 3]
    assert initial.algorithm.n_gen == 4
    restored = dill.loads(dill.dumps(initial.algorithm))
    restored.termination = get_termination("n_gen", 6)
    resumed = minimize(problem, restored, copy_algorithm=False)
    whole = minimize(problem, GA(pop_size=20), ("n_gen", 6), seed=7)
    np.testing.assert_array_equal(resumed.pop.get("X"), whole.pop.get("X"))
    np.testing.assert_array_equal(resumed.pop.get("F"), whole.pop.get("F"))
    assert resumed.algorithm.evaluator.n_eval == 120


def test_evaluation_limit_is_checked_at_batch_boundary():
    result = minimize(get_problem("sphere", n_var=2), GA(pop_size=20),
                      ("n_eval", 21), seed=3)
    assert result.algorithm.evaluator.n_eval == 40


@pytest.mark.parametrize("seed", [1, 7, 19])
@pytest.mark.parametrize("factory", [GA, DE, PSO])
def test_small_continuous_runs_respect_objective_and_bounds(factory, seed):
    p = get_problem("sphere", n_var=3)
    result = minimize(p, factory(pop_size=20), ("n_gen", 5), seed=seed)
    assert np.isfinite(result.F).all()
    assert np.all((result.X >= p.xl) & (result.X <= p.xu))
    np.testing.assert_allclose(result.F, [np.sum((result.X - 0.5)**2)])


def test_moead_directions_and_unsupported_constraints():
    directions = get_reference_directions("das-dennis", 2, n_partitions=9)
    result = minimize(get_problem("zdt1", n_var=5),
                      MOEAD(ref_dirs=directions, n_neighbors=5), ("n_gen", 3), seed=1)
    assert np.isfinite(result.F).all()
    with pytest.raises(AssertionError, match="does not support"):
        minimize(get_problem("bnh"), MOEAD(ref_dirs=directions, n_neighbors=5),
                 ("n_gen", 2), seed=1)


def test_mutation_prob_var_distinguishes_individual_and_bit_probability():
    from pymoo.operators.mutation.bitflip import BitflipMutation
    problem = get_problem("zdt5")
    X = np.zeros((5, problem.n_var), dtype=bool)
    def mutate(prob, prob_var):
        return BitflipMutation(prob=prob, prob_var=prob_var).do(
            problem, Population.new("X", X.copy()),
            random_state=np.random.default_rng(3)).get("X")
    assert not mutate(0.0, 1.0).any()
    assert not mutate(1.0, 0.0).any()
    assert mutate(1.0, 1.0).all()


def test_constraint_wrappers_require_original_feasibility_checks():
    from pymoo.constraints.as_obj import ConstraintsAsObjective
    from pymoo.constraints.as_penalty import ConstraintsAsPenalty
    p = ImpossibleProblem()
    np.testing.assert_allclose(ConstraintsAsObjective(p).evaluate(np.array([[0.5]]), return_values_of=["F", "G", "H"], return_as_dictionary=True)["F"], [[1, 0.25]])
    np.testing.assert_allclose(ConstraintsAsPenalty(p, penalty=10).evaluate(np.array([[0.5]]), return_values_of=["F", "G", "H"], return_as_dictionary=True)["F"], [[10.25]])
    assert not ConstraintsAsObjective(p).has_constraints()
    assert not ConstraintsAsPenalty(p).has_constraints()
    # The released penalty implementation is single-objective only in practice.
    with pytest.raises(ValueError):
        ConstraintsAsPenalty(get_problem("bnh")).evaluate(np.array([[1.0, 1.0], [2.0, 2.0]]), return_values_of=["F", "G", "H"])


def test_integer_operators_preserve_integral_bounds():
    from pymoo.operators.sampling.rnd import IntegerRandomSampling
    from pymoo.operators.crossover.sbx import SBX
    from pymoo.operators.mutation.pm import PM
    from pymoo.operators.repair.rounding import RoundingRepair
    problem = get_problem("sphere", n_var=3)
    problem.xl, problem.xu = np.zeros(3), np.full(3, 5)
    algorithm = GA(pop_size=10, sampling=IntegerRandomSampling(),
        crossover=SBX(vtype=float, repair=RoundingRepair()),
        mutation=PM(vtype=float, repair=RoundingRepair()))
    result = minimize(problem, algorithm, ("n_gen", 3), seed=1)
    X = result.pop.get("X")
    assert np.equal(X, np.round(X)).all()
    assert ((X >= 0) & (X <= 5)).all()


def test_permutation_operators_preserve_membership():
    from pymoo.core.problem import Problem
    from pymoo.operators.sampling.rnd import PermutationRandomSampling
    from pymoo.operators.crossover.ox import OrderCrossover
    from pymoo.operators.mutation.inversion import InversionMutation
    class SortProblem(Problem):
        def __init__(self):
            super().__init__(n_var=6, n_obj=1)
        def _evaluate(self, X, out, **kwargs):
            out["F"] = np.abs(X - np.arange(6)).sum(axis=1)
    result = minimize(SortProblem(), GA(pop_size=10, sampling=PermutationRandomSampling(),
        crossover=OrderCrossover(), mutation=InversionMutation()), ("n_gen", 3), seed=1)
    np.testing.assert_array_equal(np.sort(result.pop.get("X"), axis=1),
                                  np.tile(np.arange(6), (10, 1)))


def test_functional_problem_shape_and_maximization_conversion():
    from pymoo.problems.functional import FunctionalProblem
    p = FunctionalProblem(2, objs=[lambda x: -x.sum(), lambda x: (x**2).sum()],
                          constr_ieq=[lambda x: x.sum() - 1], xl=0, xu=1)
    F, G = p.evaluate(np.array([[0.25, 0.5]]), return_values_of=["F", "G"])
    np.testing.assert_allclose(F, [[-0.75, 0.3125]])
    np.testing.assert_allclose(G, [[-0.25]])


def test_pseudo_weights_is_not_weighted_sum():
    from pymoo.mcdm.pseudo_weights import PseudoWeights
    F = np.array([[0.0, 1.0], [0.6, 0.6], [1.0, 0.0]])
    w = np.array([0.5, 0.5])
    assert PseudoWeights(w).do(F) == 1
    assert np.argmin(F @ w) != 1


@pytest.mark.parametrize("file", ["quick_start_workflows.md", "constraints_mcdm.md",
                                   "operators.md", "parallelization.md", "lifecycle.md",
                                   "visualization.md", "algorithms.md", "problems.md"])
def test_documented_native_recipes(file, tmp_path, monkeypatch):
    """Execute displayed recipes with real native APIs, including saved figures."""
    monkeypatch.chdir(tmp_path)
    namespace = {"__name__": "__main__"}
    blocks = re.findall(r"```python\n(.*?)```", (SKILL_ROOT / "references" / file).read_text(), re.S)
    for code in blocks:
        if "# Context-dependent:" in code:
            namespace["result"] = minimize(get_problem("zdt1", n_var=5),
                NSGA2(pop_size=10), ("n_gen", 3), seed=1, save_history=True)
        exec(compile(code, file, "exec"), namespace)
    if file == "visualization.md":
        assert len(list(tmp_path.glob("*.png"))) == 8
        assert all(p.stat().st_size > 1000 for p in tmp_path.glob("*.png"))
    if file == "parallelization.md":
        p = namespace["MyProblem"]()
        X = np.array([[1, 2, 3], [2, 0, 0]])
        np.testing.assert_allclose(p.evaluate(X), namespace["problem"].evaluate(X))
    if file == "quick_start_workflows.md":
        from pymoo.algorithms.soo.nonconvex.optuna import Optuna
        result = minimize(namespace["MixedProblem"](), Optuna(), ("n_eval", 5), seed=1)
        assert np.isfinite(result.F).all()
        assert 0 <= result.X["y"] <= 2
    plt.close("all")
