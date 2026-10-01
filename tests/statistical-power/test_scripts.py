"""Tests for the statistical-power calculators.

Power analysis is a place where a plausible-looking wrong answer costs real
money and real subjects, so these tests check numbers against values that can
be verified independently rather than against whatever the code happens to
return. Cohen's canonical results are the anchors: a two-sample t-test with
d = 0.5 at 80% power needs 64 per group, and Pearson r = 0.30 at 80% power
needs 85.

The three entry points (`sample_size`, `power`, `mde`) solve the same
relationship for different unknowns, so the strongest assertions are the
round trips -- feed one's output to another and you must land back where you
started.
"""

from __future__ import annotations

import math
import sys
import tempfile
import unittest
from pathlib import Path

import pytest

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "statistical-power"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

pytest.importorskip("numpy", reason="statistical-power needs numpy")
pytest.importorskip("scipy", reason="statistical-power needs scipy")
pytest.importorskip("statsmodels", reason="statistical-power needs statsmodels")

import power as power_module  # noqa: E402
import simulate_power  # noqa: E402

DemoBlockTests = skill_contract.cli.demo_test_case(SKILL_ROOT, ("power.py",))


class SampleSizeTests(unittest.TestCase):
    def test_two_sample_t_test_matches_cohens_canonical_value(self) -> None:
        # Cohen (1988): d = 0.5, alpha = .05 two-sided, power = .80 -> 64/group.
        self.assertEqual(
            power_module.sample_size("t_ind", effect_size=0.5, power=0.80), 64
        )

    def test_correlation_matches_the_published_value(self) -> None:
        # r = 0.30, alpha = .05 two-sided, power = .80 -> n = 85.
        self.assertEqual(
            power_module.sample_size("correlation", effect_size=0.30, power=0.80), 85
        )

    def test_anova_returns_total_n_not_per_group(self) -> None:
        # f = 0.25, k = 4, power = .80 -> ~180 total (45 per group).
        total = power_module.sample_size(
            "anova", effect_size=0.25, k_groups=4, power=0.80
        )
        self.assertGreater(total, 150)
        self.assertLess(total, 200)

    def test_smaller_effects_need_larger_samples(self) -> None:
        sizes = [
            power_module.sample_size("t_ind", effect_size=d, power=0.80)
            for d in (0.8, 0.5, 0.2)
        ]
        self.assertEqual(sizes, sorted(sizes))

    def test_higher_power_needs_a_larger_sample(self) -> None:
        low = power_module.sample_size("t_ind", effect_size=0.5, power=0.80)
        high = power_module.sample_size("t_ind", effect_size=0.5, power=0.95)
        self.assertGreater(high, low)

    def test_a_one_sided_test_needs_fewer_subjects(self) -> None:
        two = power_module.sample_size("t_ind", effect_size=0.5, power=0.80)
        one = power_module.sample_size(
            "t_ind", effect_size=0.5, power=0.80, alternative="larger"
        )
        self.assertLess(one, two)

    def test_round_up_is_the_default_because_a_fraction_of_a_subject_is_not_a_subject(
        self,
    ) -> None:
        rounded = power_module.sample_size("t_ind", effect_size=0.5, power=0.80)
        exact = power_module.sample_size(
            "t_ind", effect_size=0.5, power=0.80, round_up=False
        )
        self.assertIsInstance(rounded, int)
        self.assertGreaterEqual(rounded, exact)
        self.assertEqual(rounded, math.ceil(exact))

    def test_an_unequal_allocation_ratio_changes_the_first_group(self) -> None:
        balanced = power_module.sample_size("t_ind", effect_size=0.5, power=0.80)
        skewed = power_module.sample_size(
            "t_ind", effect_size=0.5, power=0.80, ratio=2.0
        )
        self.assertLess(skewed, balanced)


class RequiredArgumentTests(unittest.TestCase):
    def test_each_test_names_the_parameter_it_is_missing(self) -> None:
        cases = [
            ("anova", {"effect_size": 0.25}, "k_groups"),
            ("two_proportions", {"prop1": 0.4}, "prop1= and prop2="),
            ("one_proportion", {"prop1": 0.4}, "prop1= and prop0="),
            ("chi2", {"effect_size": 0.3}, "dof="),
            ("linear_regression", {"effect_size": 0.15}, "df_num="),
        ]
        for test, kwargs, expected in cases:
            with self.subTest(test=test):
                with self.assertRaises(ValueError) as raised:
                    power_module.sample_size(test, power=0.80, **kwargs)
                self.assertIn(expected, str(raised.exception))

    def test_an_unknown_test_is_named_in_the_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown test 'wilcoxon'"):
            power_module.sample_size("wilcoxon", effect_size=0.5)

    def test_test_names_are_case_insensitive(self) -> None:
        self.assertEqual(
            power_module.sample_size("T_IND", effect_size=0.5, power=0.80),
            power_module.sample_size("t_ind", effect_size=0.5, power=0.80),
        )

    def test_power_requires_a_sample_size(self) -> None:
        with self.assertRaisesRegex(ValueError, "nobs1=|nobs="):
            power_module.power("t_ind", effect_size=0.5)

    def test_mde_requires_a_sample_size(self) -> None:
        with self.assertRaisesRegex(ValueError, "nobs1=|nobs="):
            power_module.mde("t_ind")


class PowerTests(unittest.TestCase):
    def test_power_at_the_solved_sample_size_reaches_the_target(self) -> None:
        n = power_module.sample_size("t_ind", effect_size=0.5, power=0.80)
        achieved = power_module.power("t_ind", effect_size=0.5, nobs1=n)
        self.assertGreaterEqual(achieved, 0.80)
        self.assertLess(achieved, 0.82)  # rounding up, not wildly over

    def test_power_is_bounded_and_monotone_in_n(self) -> None:
        values = [
            power_module.power("t_ind", effect_size=0.5, nobs1=n)
            for n in (10, 30, 64, 200)
        ]
        self.assertEqual(values, sorted(values))
        self.assertTrue(all(0.0 <= value <= 1.0 for value in values))

    def test_a_zero_effect_has_power_equal_to_alpha(self) -> None:
        # With no true effect, the rejection rate is the type-I error rate.
        self.assertAlmostEqual(
            power_module.power("t_ind", effect_size=0.0, nobs1=100, alpha=0.05),
            0.05,
            places=3,
        )

    def test_correlation_power_round_trips_with_its_sample_size(self) -> None:
        n = power_module.sample_size("correlation", effect_size=0.30, power=0.80)
        self.assertGreaterEqual(
            power_module.power("correlation", effect_size=0.30, nobs=n), 0.80
        )

    def test_regression_power_is_zero_when_the_model_has_no_residual_df(self) -> None:
        # n - k_total - 1 < 1 means nothing left to test against; report 0
        # rather than raising or returning a nonsense value.
        self.assertEqual(
            power_module.power(
                "linear_regression", effect_size=0.15, nobs=5, df_num=3, k_total=5
            ),
            0.0,
        )

    def test_two_proportions_power_round_trips(self) -> None:
        n = power_module.sample_size(
            "two_proportions", prop1=0.40, prop2=0.55, power=0.80
        )
        self.assertGreaterEqual(
            power_module.power("two_proportions", prop1=0.40, prop2=0.55, nobs1=n),
            0.80,
        )


class MdeTests(unittest.TestCase):
    def test_the_mde_at_a_solved_n_recovers_the_original_effect(self) -> None:
        n = power_module.sample_size("t_ind", effect_size=0.5, power=0.80)
        detectable = power_module.mde("t_ind", nobs1=n, power=0.80)
        self.assertAlmostEqual(detectable, 0.5, delta=0.02)

    def test_a_larger_sample_detects_a_smaller_effect(self) -> None:
        small = power_module.mde("t_ind", nobs1=20, power=0.80)
        large = power_module.mde("t_ind", nobs1=200, power=0.80)
        self.assertLess(large, small)

    def test_correlation_mde_round_trips(self) -> None:
        n = power_module.sample_size("correlation", effect_size=0.30, power=0.80)
        self.assertAlmostEqual(
            power_module.mde("correlation", nobs=n, power=0.80), 0.30, delta=0.01
        )

    def test_regression_mde_round_trips(self) -> None:
        detectable = power_module.mde(
            "linear_regression", nobs=100, df_num=3, k_total=5, power=0.80
        )
        achieved = power_module.power(
            "linear_regression",
            effect_size=detectable,
            nobs=100,
            df_num=3,
            k_total=5,
        )
        self.assertAlmostEqual(achieved, 0.80, delta=0.01)


class RegressionSolverTests(unittest.TestCase):
    def test_the_sample_size_search_stops_at_the_first_adequate_n(self) -> None:
        n = power_module.sample_size(
            "linear_regression", effect_size=0.15, df_num=3, k_total=5, power=0.80
        )
        at_n = power_module._reg_power(0.15, n, 3, 5, 0.05)
        below = power_module._reg_power(0.15, n - 1, 3, 5, 0.05)
        self.assertGreaterEqual(at_n, 0.80)
        self.assertLess(below, 0.80)

    def test_an_undetectably_small_effect_does_not_loop_forever(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "did not converge"):
            power_module._reg_sample_size(1e-9, 1, 1, 0.05, 0.99)


class PowerCurveTests(unittest.TestCase):
    def test_the_curve_rises_with_sample_size_and_is_saved(self) -> None:
        import matplotlib

        matplotlib.use("Agg")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "curve.png"
            ns, powers = power_module.power_curve(
                "t_ind", effect_size=0.5, n_range=range(10, 110, 10), save=output
            )
            self.assertEqual(len(ns), len(powers))
            self.assertEqual(len(ns), 10)
            self.assertTrue(list(powers) == sorted(powers))
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 0)

    def test_per_group_tests_iterate_the_per_group_n(self) -> None:
        # For t_ind the curve must pass nobs1, so power at n=64 matches the
        # canonical per-group answer rather than a total-n reading.
        _, powers = power_module.power_curve(
            "t_ind", effect_size=0.5, n_range=[64]
        )
        self.assertAlmostEqual(float(powers[0]), 0.80, delta=0.01)


class SimulationTests(unittest.TestCase):
    def test_invalid_simulation_inputs_and_nonboolean_decisions_are_rejected(self):
        for kwargs in ({"n": 0}, {"n": -1}, {"n": 2, "n_sims": 0},
                       {"n": 2.5}, {"n": 2, "alpha": 1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                simulate_power.simulate_power(lambda n, rng: True, **kwargs)
        with self.assertRaisesRegex(TypeError, "boolean"):
            simulate_power.simulate_power(lambda n, rng: 0.03, n=2, n_sims=1)

    def test_invalid_search_bounds_never_enter_the_expansion_loop(self):
        for kwargs in ({"hi": 0}, {"lo": 0}, {"lo": 20, "hi": 10},
                       {"target_power": 0}, {"hi": 1_000_001}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                simulate_power.find_sample_size(lambda n, rng: False, **kwargs)

    def test_unreachable_target_is_reported_without_a_false_sample_size(self):
        with self.assertRaisesRegex(ValueError, "not reached"):
            simulate_power.find_sample_size(lambda n, rng: False,
                                            n_sims=1, hi=1_000_000, verbose=False)

    def test_wilson_intervals_bracket_the_estimate_and_stay_in_range(self) -> None:
        for successes, trials in ((0, 100), (50, 100), (100, 100), (1, 10)):
            with self.subTest(successes=successes, trials=trials):
                low, high = simulate_power._wilson_ci(successes, trials)
                observed = successes / trials
                self.assertLessEqual(0.0, low)
                self.assertLessEqual(high, 1.0)
                # The bound is clamped to [0, 1], so at p = 1 it lands one ulp
                # short of the observed rate; compare with a float tolerance.
                self.assertLessEqual(low, observed + 1e-12)
                self.assertLessEqual(observed, high + 1e-12)

    def test_a_zero_success_run_still_has_a_positive_upper_bound(self) -> None:
        # The interval must not collapse to (0, 0): "we saw none" is not
        # "it cannot happen".
        low, high = simulate_power._wilson_ci(0, 50)
        self.assertEqual(low, 0.0)
        self.assertGreater(high, 0.0)

    def test_simulation_reproduces_from_its_seed(self) -> None:
        generator = simulate_power.example_two_group_difference(effect=0.5)
        first = simulate_power.simulate_power(generator, n=30, n_sims=200, seed=4)
        second = simulate_power.simulate_power(generator, n=30, n_sims=200, seed=4)
        self.assertEqual(first.power, second.power)

    def test_simulated_power_tracks_the_analytic_answer(self) -> None:
        # The whole point of the simulator is to agree with theory where theory
        # applies, so it can be trusted where theory does not.
        generator = simulate_power.example_two_group_difference(effect=0.5)
        simulated = simulate_power.simulate_power(generator, n=64, n_sims=4000, seed=1)
        analytic = power_module.power("t_ind", effect_size=0.5, nobs1=64)
        self.assertAlmostEqual(simulated.power, analytic, delta=0.04)

    def test_a_null_effect_simulates_to_the_alpha_level(self) -> None:
        generator = simulate_power.example_two_group_difference(effect=0.0)
        estimate = simulate_power.simulate_power(
            generator, n=50, n_sims=4000, alpha=0.05, seed=2
        )
        self.assertAlmostEqual(estimate.power, 0.05, delta=0.02)

    def test_the_estimate_reports_its_own_uncertainty(self) -> None:
        generator = simulate_power.example_two_group_difference(effect=0.5)
        estimate = simulate_power.simulate_power(generator, n=40, n_sims=500, seed=3)
        self.assertLessEqual(estimate.ci_low, estimate.power)
        self.assertLessEqual(estimate.power, estimate.ci_high)
        self.assertEqual(estimate.n_sims, 500)

    def test_the_sample_size_search_returns_an_n_that_meets_the_target(self) -> None:
        generator = simulate_power.example_two_group_difference(effect=0.8)
        found, estimate = simulate_power.find_sample_size(
            generator, target_power=0.80, n_sims=400, hi=200, seed=5, verbose=False
        )
        self.assertIsInstance(found, int)
        self.assertGreaterEqual(estimate.power, 0.80)
        # Bisection returns the smallest adequate n, so one fewer must fall short.
        below = simulate_power.simulate_power(
            generator, n=found - 1, n_sims=400, seed=5
        )
        self.assertLess(below.power, 0.80)

    def test_the_worked_examples_all_produce_a_usable_estimate(self) -> None:
        examples = (
            simulate_power.example_two_group_difference(effect=0.6),
            simulate_power.example_logistic_regression(beta=1.0),
            simulate_power.example_cluster_randomized(effect=0.5),
        )
        for index, generator in enumerate(examples):
            with self.subTest(example=index):
                estimate = simulate_power.simulate_power(
                    generator, n=40, n_sims=200, seed=7
                )
                self.assertTrue(0.0 <= estimate.power <= 1.0)


if __name__ == "__main__":
    unittest.main()
