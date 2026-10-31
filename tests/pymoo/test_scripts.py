"""Tests for the pymoo optimisation examples.

The examples are worth testing at two levels. The problem definitions are pure
arithmetic with hand-computable answers -- `MyBiObjectiveProblem` at (0, 0) must
be (0, 2), and `ConstrainedProblem` must call (1.0, 0.0) feasible and (0.1, 0.0)
infeasible -- so a transcription slip in an objective or a sign flip in a
constraint conversion is caught exactly. The optimisation runs are then checked
against properties that hold by construction rather than against a converged
result: pymoo's `sphere` has its minimum at x = 0.5 with value 0, ZDT1's true
front satisfies f2 = 1 - sqrt(f1), every feasible DTLZ2 point has ||f|| >= 1,
and any NSGA-II result set must be mutually non-dominated. The guard that
matters most is `get_reference_directions`, whose dimension argument is
positional -- passing it by keyword raises TypeError, which made the
many-objective example unrunnable.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pytest

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pymoo"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

np = pytest.importorskip("numpy", reason="pymoo scripts need numpy")
pytest.importorskip("pymoo", reason="pymoo scripts need pymoo")
matplotlib = pytest.importorskip("matplotlib", reason="the examples plot their results")
matplotlib.use("Agg")

from pymoo.algorithms.moo.nsga2 import NSGA2  # noqa: E402
from pymoo.algorithms.moo.nsga3 import NSGA3  # noqa: E402
from pymoo.algorithms.soo.nonconvex.ga import GA  # noqa: E402
from pymoo.optimize import minimize  # noqa: E402
from pymoo.problems import get_problem  # noqa: E402
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting  # noqa: E402
from pymoo.util.ref_dirs import get_reference_directions  # noqa: E402

import custom_problem_example  # noqa: E402
import decision_making_example  # noqa: E402

# Imported for the side effect of importing: these three modules do their work
# inside functions, so a broken import line here fails at collection time rather
# than 30 seconds into the demo run below.
import many_objective_example  # noqa: E402,F401
import multi_objective_example  # noqa: E402,F401
import single_objective_example  # noqa: E402,F401

# The bounded demos exercise the complete entry points, including plots.
DemoBlockTests = skill_contract.cli.demo_test_case(
    SKILL_ROOT,
    (
        "single_objective_example.py",
        "multi_objective_example.py",
        "custom_problem_example.py",
        "decision_making_example.py",
        "many_objective_example.py",
    ),
)


def is_non_dominated(front: "np.ndarray") -> bool:
    """True when no row in `front` is dominated by another."""
    fronts = NonDominatedSorting().do(front)
    return len(fronts[0]) == len(front)


class BiObjectiveProblemDefinitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.problem = custom_problem_example.MyBiObjectiveProblem()

    def test_the_declared_shape_matches_the_docstring(self) -> None:
        self.assertEqual(self.problem.n_var, 2)
        self.assertEqual(self.problem.n_obj, 2)
        self.assertEqual(self.problem.n_ieq_constr, 0)
        np.testing.assert_allclose(self.problem.xl, [0.0, 0.0])
        np.testing.assert_allclose(self.problem.xu, [5.0, 5.0])

    def test_the_objectives_are_the_two_squared_distances(self) -> None:
        # f1 = |x|^2 and f2 = |x - (1, 1)|^2, so the corners are exact.
        evaluated = self.problem.evaluate(
            np.array([[0.0, 0.0], [1.0, 1.0], [0.5, 0.5], [2.0, 3.0]])
        )
        np.testing.assert_allclose(
            evaluated,
            [[0.0, 2.0], [2.0, 0.0], [0.5, 0.5], [13.0, 5.0]],
        )

    def test_the_two_objectives_genuinely_conflict(self) -> None:
        # The origin minimises f1 and (1, 1) minimises f2; if one point were
        # best at both there would be nothing to trade off.
        origin, unit = self.problem.evaluate(np.array([[0.0, 0.0], [1.0, 1.0]]))
        self.assertLess(origin[0], unit[0])
        self.assertGreater(origin[1], unit[1])


class ConstrainedProblemDefinitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.problem = custom_problem_example.ConstrainedProblem()

    def test_two_inequality_constraints_are_declared_over_the_stated_box(self) -> None:
        self.assertEqual(self.problem.n_ieq_constr, 2)
        np.testing.assert_allclose(self.problem.xl, [0.1, 0.0])
        np.testing.assert_allclose(self.problem.xu, [1.0, 5.0])

    def test_a_feasible_point_evaluates_to_non_positive_constraints(self) -> None:
        # At (1.0, 0.0): f = (1, (1+0)/1) = (1, 1); g1 = -(0 + 9 - 6) = -3 and
        # g2 = -(-0 + 9 - 1) = -8, so both original inequalities hold.
        objectives, constraints = self.problem.evaluate(
            np.array([[1.0, 0.0]]), return_values_of=["F", "G"]
        )
        np.testing.assert_allclose(objectives, [[1.0, 1.0]])
        np.testing.assert_allclose(constraints, [[-3.0, -8.0]])
        self.assertTrue(np.all(constraints <= 0.0))

    def test_a_point_violating_both_constraints_is_reported_infeasible(self) -> None:
        # At (0.1, 0.0): g1 = -(0 + 0.9 - 6) = 5.1 and g2 = -(-0 + 0.9 - 1) = 0.1,
        # both positive, so the sign conversion in the docstring is the real one.
        constraints = self.problem.evaluate(
            np.array([[0.1, 0.0]]), return_values_of=["G"]
        )
        np.testing.assert_allclose(constraints, [[5.1, 0.1]])
        self.assertTrue(np.all(constraints > 0.0))

    def test_the_search_returns_only_feasible_solutions(self) -> None:
        result = minimize(
            custom_problem_example.ConstrainedProblem(),
            NSGA2(pop_size=20),
            ("n_gen", 10),
            seed=1,
            verbose=False,
        )
        # The example reads feasibility off column 0 of CV, so it must exist.
        self.assertEqual(result.CV.shape[1], 1)
        np.testing.assert_allclose(result.CV[:, 0], 0.0)


class SingleObjectiveExampleTests(unittest.TestCase):
    def test_pymoos_sphere_has_its_optimum_at_one_half(self) -> None:
        # pymoo's Sphere is sum (x_i - 0.5)^2 on [0, 1]^n: zero at 0.5 and
        # n * 0.25 at the origin. The GA below is judged against that.
        problem = get_problem("sphere", n_var=5)
        np.testing.assert_allclose(problem.xl, np.zeros(5))
        np.testing.assert_allclose(problem.xu, np.ones(5))
        self.assertEqual(problem.n_obj, 1)
        np.testing.assert_allclose(problem.evaluate(np.full((1, 5), 0.5)), [[0.0]])
        np.testing.assert_allclose(problem.evaluate(np.zeros((1, 5))), [[1.25]])

    def test_a_short_genetic_algorithm_run_approaches_the_known_optimum(self) -> None:
        problem = get_problem("sphere", n_var=5)
        result = minimize(problem, GA(pop_size=30), ("n_gen", 25), seed=1, verbose=False)
        self.assertLess(float(result.F[0]), 0.01)
        np.testing.assert_allclose(result.X, np.full(5, 0.5), atol=0.1)

    def test_the_example_reports_the_evaluation_budget_it_used(self) -> None:
        # pop_size * n_gen evaluations, which is what the example prints.
        result = minimize(
            get_problem("sphere", n_var=3), GA(pop_size=20), ("n_gen", 5), seed=1, verbose=False
        )
        self.assertEqual(result.algorithm.evaluator.n_eval, 100)

    def test_the_same_seed_gives_the_same_answer(self) -> None:
        runs = [
            minimize(
                get_problem("sphere", n_var=5), GA(pop_size=20), ("n_gen", 5), seed=7, verbose=False
            ).F
            for _ in range(2)
        ]
        np.testing.assert_allclose(runs[0], runs[1])


class MultiObjectiveExampleTests(unittest.TestCase):
    def test_zdt1_is_the_thirty_variable_bi_objective_benchmark(self) -> None:
        problem = get_problem("zdt1")
        self.assertEqual((problem.n_var, problem.n_obj), (30, 2))

    def test_the_analytic_front_satisfies_f2_equals_one_minus_root_f1(self) -> None:
        # ZDT1's true front is a published closed form; the example plots it as
        # the reference curve, so it must be the real one.
        front = get_problem("zdt1").pareto_front()
        np.testing.assert_allclose(front[:, 1], 1.0 - np.sqrt(front[:, 0]), atol=1e-9)

    def test_an_nsga2_run_returns_a_mutually_non_dominated_set(self) -> None:
        result = minimize(
            get_problem("zdt1"), NSGA2(pop_size=20, eliminate_duplicates=True),
            ("n_gen", 10), seed=1, verbose=False,
        )
        self.assertEqual(result.F.shape[1], 2)
        self.assertLessEqual(len(result.F), 20)
        self.assertTrue(is_non_dominated(result.F))

    def test_no_solution_can_beat_the_analytic_front(self) -> None:
        # Nothing feasible lies below f2 = 1 - sqrt(f1); a result that did would
        # mean the problem or the front is wrong.
        result = minimize(
            get_problem("zdt1"), NSGA2(pop_size=20), ("n_gen", 10), seed=2, verbose=False
        )
        self.assertTrue(np.all(result.F[:, 1] >= 1.0 - np.sqrt(result.F[:, 0]) - 1e-9))


class ManyObjectiveExampleTests(unittest.TestCase):
    def test_das_dennis_directions_take_the_dimension_positionally(self) -> None:
        # The regression this guards: get_reference_directions("das-dennis",
        # n_obj=5, ...) raises TypeError because the factory's first argument is
        # n_dim, which made the many-objective example unrunnable.
        with self.assertRaises(TypeError):
            get_reference_directions("das-dennis", n_obj=5, n_partitions=6)
        directions = get_reference_directions("das-dennis", 5, n_partitions=6)
        # C(p + m - 1, m - 1) = C(10, 4) = 210 simplex-lattice points.
        self.assertEqual(directions.shape, (210, 5))
        np.testing.assert_allclose(directions.sum(axis=1), 1.0, atol=1e-12)

    def test_more_partitions_give_more_directions(self) -> None:
        counts = [
            len(get_reference_directions("das-dennis", 3, n_partitions=p))
            for p in (4, 6, 8)
        ]
        # C(p + 2, 2) for three objectives: 15, 28, 45.
        self.assertEqual(counts, [15, 28, 45])

    def test_every_feasible_dtlz2_point_lies_on_or_outside_the_unit_sphere(self) -> None:
        # DTLZ2 scales the unit sphere by 1 + g with g >= 0, so ||f|| >= 1 with
        # equality exactly on the Pareto front.
        problem = get_problem("dtlz2", n_obj=3)
        front = problem.pareto_front()
        np.testing.assert_allclose(np.linalg.norm(front, axis=1), 1.0, atol=1e-9)
        rng = np.random.default_rng(0)
        random_points = problem.evaluate(rng.random((20, problem.n_var)))
        self.assertTrue(np.all(np.linalg.norm(random_points, axis=1) >= 1.0 - 1e-9))

    def test_nsga3_optimises_a_three_objective_problem_towards_the_sphere(self) -> None:
        directions = get_reference_directions("das-dennis", 3, n_partitions=6)
        result = minimize(
            get_problem("dtlz2", n_obj=3),
            NSGA3(ref_dirs=directions, eliminate_duplicates=True),
            ("n_gen", 15),
            seed=1,
            verbose=False,
        )
        self.assertEqual(result.F.shape[1], 3)
        self.assertTrue(is_non_dominated(result.F))
        # Optimisation shrinks 1 + g towards 1; it must not run away from it.
        self.assertLess(float(np.linalg.norm(result.F, axis=1).min()), 1.5)


class PseudoWeightDecisionTests(unittest.TestCase):
    """A five-point synthetic front where the right answer is obvious."""

    def setUp(self) -> None:
        from pymoo.mcdm.pseudo_weights import PseudoWeights

        self.PseudoWeights = PseudoWeights
        self.front = np.array(
            [[0.0, 1.0], [0.25, 0.75], [0.5, 0.5], [0.75, 0.25], [1.0, 0.0]]
        )

    def test_weighting_one_objective_selects_the_best_point_in_it(self) -> None:
        self.assertEqual(self.PseudoWeights(np.array([0.9, 0.1])).do(self.front), 0)
        self.assertEqual(self.PseudoWeights(np.array([0.1, 0.9])).do(self.front), 4)

    def test_equal_weights_select_the_balanced_compromise(self) -> None:
        self.assertEqual(self.PseudoWeights(np.array([0.5, 0.5])).do(self.front), 2)


class DecisionMakingExampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = minimize(
            get_problem("zdt1"), NSGA2(pop_size=24), ("n_gen", 12), seed=1, verbose=False
        )

    def test_the_selection_indexes_into_both_result_arrays_consistently(self) -> None:
        index, variables, objectives = decision_making_example.apply_pseudo_weights(
            self.result, np.array([0.5, 0.5])
        )
        np.testing.assert_allclose(objectives, self.result.F[index])
        np.testing.assert_allclose(variables, self.result.X[index])

    def test_shifting_the_weights_moves_the_choice_along_the_front(self) -> None:
        _, _, prefer_first = decision_making_example.apply_pseudo_weights(
            self.result, np.array([0.9, 0.1])
        )
        _, _, prefer_second = decision_making_example.apply_pseudo_weights(
            self.result, np.array([0.1, 0.9])
        )
        # Weighting f1 must not pick a solution that is worse in f1 than the
        # one chosen when f1 barely matters.
        self.assertLess(prefer_first[0], prefer_second[0])
        self.assertGreater(prefer_first[1], prefer_second[1])

    def test_the_extreme_solutions_are_the_per_objective_minima(self) -> None:
        best_f1, best_f2 = decision_making_example.find_extreme_solutions(self.result)
        self.assertEqual(best_f1, int(np.argmin(self.result.F[:, 0])))
        self.assertEqual(best_f2, int(np.argmin(self.result.F[:, 1])))
        # On a two-objective front the extremes cannot be the same point.
        self.assertNotEqual(best_f1, best_f2)


if __name__ == "__main__":
    unittest.main()


def test_selection_rejects_nonfinite_infeasible_and_degenerate_fronts():
    from types import SimpleNamespace
    select = decision_making_example.apply_pseudo_weights
    def result(F, CV=None):
        return SimpleNamespace(F=F, X=None if F is None else np.zeros((len(F), 2)), CV=CV)
    with pytest.raises(ValueError, match="No feasible"):
        select(result(None), [0.5, 0.5])
    with pytest.raises(ValueError, match="finite"):
        select(result(np.array([[0, np.nan], [1, 0]])), [0.5, 0.5])
    with pytest.raises(ValueError, match="infeasible"):
        select(result(np.array([[0, 1], [1, 0]]), np.ones((2, 1))), [0.5, 0.5])
    misaligned = result(np.array([[0, 1], [1, 0]]))
    misaligned.X = np.zeros((1, 2))
    with pytest.raises(ValueError, match="aligned"):
        select(misaligned, [0.5, 0.5])
    with pytest.raises(ValueError, match="per candidate"):
        select(result(np.array([[0, 1], [1, 0]]), np.zeros(2)), [0.5, 0.5])
    with pytest.raises(ValueError, match="constant"):
        select(result(np.array([[1, 1], [1, 1]])), [0.5, 0.5])
    with pytest.raises(ValueError, match="dominated"):
        select(result(np.array([[0, 0], [1, 1]])), [0.5, 0.5])
    with pytest.raises(ValueError, match="sum to one"):
        select(result(np.array([[0, 1], [1, 0]])), [1, 1])
    i, _, F = select(result(np.array([[3.0, 4.0]])), [0.5, 0.5])
    assert i == 0
    np.testing.assert_array_equal(F, [3, 4])
