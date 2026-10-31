"""Numerical and boundary tests for descriptive statistical diagnostics.

Seeded samples exercise upstream decisions without claiming that any finite
sample proves a population distribution. Boundary regressions cover invalid
inputs, missing-row identity, within-group screening and OLS requirements.
Agg checks exercise plotting mechanics, not scientific visual interpretation.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pytest

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "statistical-analysis"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

np = pytest.importorskip("numpy", reason="statistical-analysis needs numpy")
pd = pytest.importorskip("pandas", reason="statistical-analysis needs pandas")
pytest.importorskip("scipy", reason="statistical-analysis needs scipy")
matplotlib = pytest.importorskip("matplotlib", reason="assumption_checks imports matplotlib")
matplotlib.use("Agg")

import assumption_checks  # noqa: E402

RNG = np.random.default_rng(20260727)
NORMAL = RNG.normal(0, 1, 300)
SKEWED = RNG.lognormal(0, 1, 300)


class NormalityTests(unittest.TestCase):
    def test_a_normal_sample_is_reported_as_normal(self) -> None:
        result = assumption_checks.check_normality(NORMAL, plot=False)
        self.assertTrue(result["is_normal"])
        self.assertGreater(result["p_value"], 0.05)

    def test_a_lognormal_sample_is_reported_as_non_normal(self) -> None:
        result = assumption_checks.check_normality(SKEWED, plot=False)
        self.assertFalse(result["is_normal"])
        self.assertLess(result["p_value"], 0.05)

    def test_the_verdict_follows_the_supplied_alpha(self) -> None:
        # Same data, stricter threshold: the decision must move with alpha
        # rather than being hardcoded at .05.
        borderline = RNG.normal(0, 1, 300)
        lenient = assumption_checks.check_normality(borderline, alpha=1e-9, plot=False)
        self.assertTrue(lenient["is_normal"])
        strict = assumption_checks.check_normality(borderline, alpha=0.999, plot=False)
        self.assertFalse(strict["is_normal"])

    def test_the_result_carries_the_test_name_and_a_recommendation(self) -> None:
        normal = assumption_checks.check_normality(NORMAL, plot=False)
        self.assertEqual(normal["test"], "Shapiro-Wilk")
        self.assertEqual(normal["n"], len(NORMAL))
        self.assertIn("parametric", normal["recommendation"])

        skewed = assumption_checks.check_normality(SKEWED, plot=False)
        self.assertIn("non-parametric", skewed["recommendation"])

    def test_lists_and_series_are_accepted_as_well_as_arrays(self) -> None:
        for data in (list(NORMAL), pd.Series(NORMAL), NORMAL):
            with self.subTest(kind=type(data).__name__):
                self.assertTrue(
                    assumption_checks.check_normality(data, plot=False)["is_normal"]
                )


class PerGroupNormalityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = pd.DataFrame(
            {
                "value": np.concatenate([RNG.normal(0, 1, 200), RNG.lognormal(0, 1, 200)]),
                "group": ["normal"] * 200 + ["skewed"] * 200,
            }
        )

    def test_each_group_gets_its_own_verdict(self) -> None:
        result = assumption_checks.check_normality_per_group(
            self.frame, "value", "group", plot=False
        )
        self.assertEqual(len(result), 2)
        verdicts = dict(zip(result["Group"], result["Normal"]))
        self.assertEqual(verdicts["normal"], "Yes")
        self.assertEqual(verdicts["skewed"], "No")

    def test_the_result_is_a_frame_with_one_row_and_an_n_per_group(self) -> None:
        result = assumption_checks.check_normality_per_group(
            self.frame, "value", "group", plot=False
        )
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(set(result["Group"]), {"normal", "skewed"})
        self.assertEqual(list(result["N"]), [200, 200])


class VarianceTests(unittest.TestCase):
    def _frame(self, spread: float) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "value": np.concatenate(
                    [RNG.normal(0, 1, 200), RNG.normal(0, spread, 200)]
                ),
                "group": ["a"] * 200 + ["b"] * 200,
            }
        )

    def test_equal_variances_pass_levene(self) -> None:
        result = assumption_checks.check_homogeneity_of_variance(
            self._frame(1.0), "value", "group", plot=False
        )
        self.assertTrue(result["is_homogeneous"])

    def test_a_tenfold_spread_difference_fails_levene(self) -> None:
        result = assumption_checks.check_homogeneity_of_variance(
            self._frame(10.0), "value", "group", plot=False
        )
        self.assertFalse(result["is_homogeneous"])
        self.assertLess(result["p_value"], 0.05)

    def test_more_than_two_groups_are_supported(self) -> None:
        frame = pd.DataFrame(
            {
                "value": np.concatenate([RNG.normal(0, 1, 100) for _ in range(3)]),
                "group": ["a"] * 100 + ["b"] * 100 + ["c"] * 100,
            }
        )
        result = assumption_checks.check_homogeneity_of_variance(
            frame, "value", "group", plot=False
        )
        self.assertTrue(result["is_homogeneous"])


class OutlierTests(unittest.TestCase):
    def test_the_iqr_method_finds_a_planted_extreme_value(self) -> None:
        data = np.concatenate([RNG.normal(0, 1, 200), [50.0]])
        result = assumption_checks.detect_outliers(data, method="iqr", plot=False)
        self.assertGreaterEqual(result["n_outliers"], 1)

    def test_the_zscore_method_finds_the_same_value(self) -> None:
        data = np.concatenate([RNG.normal(0, 1, 200), [50.0]])
        result = assumption_checks.detect_outliers(data, method="zscore", plot=False)
        self.assertGreaterEqual(result["n_outliers"], 1)

    def test_a_higher_threshold_flags_fewer_points(self) -> None:
        data = np.concatenate([RNG.normal(0, 1, 300), [6.0, 8.0, 12.0]])
        mild = assumption_checks.detect_outliers(
            data, method="iqr", threshold=1.5, plot=False
        )
        extreme = assumption_checks.detect_outliers(
            data, method="iqr", threshold=3.0, plot=False
        )
        self.assertGreaterEqual(mild["n_outliers"], extreme["n_outliers"])

    def test_clean_data_yields_no_extreme_outliers(self) -> None:
        result = assumption_checks.detect_outliers(
            RNG.normal(0, 1, 200), method="zscore", threshold=5.0, plot=False
        )
        self.assertEqual(result["n_outliers"], 0)

    def test_the_reported_percentage_matches_the_count(self) -> None:
        data = np.concatenate([RNG.normal(0, 1, 99), [50.0]])
        result = assumption_checks.detect_outliers(data, method="zscore", plot=False)
        self.assertAlmostEqual(
            result["pct_outliers"], 100 * result["n_outliers"] / len(data), places=6
        )


class LinearityTests(unittest.TestCase):
    def test_a_straight_line_relationship_is_reported_as_linear(self) -> None:
        x = np.linspace(0, 10, 200)
        y = 3 * x + RNG.normal(0, 0.1, 200)
        result = assumption_checks.check_linearity(x, y)
        self.assertGreater(abs(result["r"]), 0.99)

    def test_a_quadratic_relationship_is_distinguished_from_a_linear_one(self) -> None:
        x = np.linspace(-5, 5, 200)
        linear = assumption_checks.check_linearity(
            x, 2 * x + RNG.normal(0, 0.1, 200)
        )
        curved = assumption_checks.check_linearity(
            x, x**2 + RNG.normal(0, 0.1, 200)
        )
        self.assertGreater(abs(linear["r"]), abs(curved["r"]))


class ComprehensiveCheckTests(unittest.TestCase):
    def test_the_combined_check_reports_on_every_assumption(self) -> None:
        frame = pd.DataFrame(
            {
                "value": np.concatenate([RNG.normal(0, 1, 100), RNG.normal(1, 1, 100)]),
                "group": ["a"] * 100 + ["b"] * 100,
            }
        )
        result = assumption_checks.comprehensive_assumption_check(
            frame, "value", "group"
        )
        self.assertIsInstance(result, dict)
        self.assertTrue(result)


class DiagnosticBoundaryTests(unittest.TestCase):
    def test_invalid_normality_inputs_are_not_certified(self):
        for sample in ([], [1, 2], [1, 1, 1], [1, np.inf, 2], [[1, 2, 3]]):
            with self.subTest(sample=sample), self.assertRaises(ValueError):
                assumption_checks.check_normality(sample, plot=False)
        for alpha in (0, 1, -0.1, np.nan):
            with self.assertRaises(ValueError):
                assumption_checks.check_normality(NORMAL, alpha=alpha, plot=False)

    def test_large_shapiro_sample_has_no_binary_verdict(self):
        with pytest.warns(UserWarning, match='5000'):
            result = assumption_checks.check_normality(np.linspace(-2, 2, 5001), plot=False)
        self.assertIsNone(result['is_normal'])
        self.assertFalse(result['p_value_reliable'])

    def test_missing_positions_and_series_labels_are_preserved(self):
        sample = pd.Series([np.nan, 0, 0, 0, 0, 100], index=list('abcdef'))
        result = assumption_checks.detect_outliers(sample, plot=False)
        np.testing.assert_array_equal(result['outlier_indices'], [5])
        np.testing.assert_array_equal(result['outlier_labels'], ['f'])
        self.assertEqual(result['n_missing'], 1)
        self.assertEqual(result['pct_outliers'], 20)

    def test_zscore_default_is_three_and_constant_input_is_unflagged(self):
        result = assumption_checks.detect_outliers([2, 2, 2], method='zscore', plot=False)
        self.assertEqual(result['threshold'], 3)
        self.assertEqual(result['n_outliers'], 0)
        for threshold in (0, -1, np.inf):
            with self.assertRaises(ValueError):
                assumption_checks.detect_outliers(NORMAL, threshold=threshold, plot=False)

    def test_group_labels_variances_and_missing_counts_align(self):
        frame = pd.DataFrame({'g': pd.Categorical(['z'] * 5 + ['a'] * 5,
                              categories=['a', 'unused', 'z']),
                              'v': [1, 2, 4, 8, np.nan, 10, 20, 40, 80, np.nan]})
        result = assumption_checks.check_homogeneity_of_variance(frame, 'v', 'g', plot=False)
        self.assertEqual(result['groups'], ['z', 'a'])
        self.assertEqual(result['n_missing'], 2)
        np.testing.assert_allclose(result['variances'][1] / result['variances'][0], 100)
        normality = assumption_checks.check_normality_per_group(frame, 'v', 'g', plot=False)
        self.assertEqual(normality['N_missing'].tolist(), [1, 1])
        frame.loc[0, 'g'] = None
        with self.assertRaises(ValueError):
            assumption_checks.check_normality_per_group(frame, 'v', 'g', plot=False)

    def test_degenerate_variance_diagnostic_rejects(self):
        for frame in (pd.DataFrame({'g': ['a'] * 3, 'v': [1, 2, 3]}),
                      pd.DataFrame({'g': ['a'] * 3 + ['b'] * 3, 'v': [1] * 3 + [2] * 3})):
            with self.assertRaises(ValueError):
                assumption_checks.check_homogeneity_of_variance(frame, 'v', 'g', plot=False)

    def test_linearity_uses_complete_pairs(self):
        result = assumption_checks.check_linearity([0, 1, np.nan, 3, 4],
                                                   [0, 2, 999, np.nan, 8], plot=False)
        self.assertEqual(result['n'], 3)
        self.assertEqual(result['n_missing'], 2)
        self.assertAlmostEqual(result['r'], 1)
        with self.assertRaises(ValueError):
            assumption_checks.check_linearity([0, 1], [1, 2, 3], plot=False)

    def test_group_outliers_do_not_compare_against_pooled_location(self):
        frame = pd.DataFrame({'g': ['a'] * 50 + ['b'] * 5,
                              'v': np.r_[np.arange(50), np.arange(1000, 1005)]})
        result = assumption_checks.comprehensive_assumption_check(frame, 'v', 'g', plot=False)
        self.assertEqual(result['outliers_per_group']['b']['n_outliers'], 0)


class RegressionDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.sm = pytest.importorskip('statsmodels.api')
        self.x = np.linspace(-3, 3, 80)
        self.y = 1 + 2 * self.x + np.random.default_rng(71).normal(size=80)

    def test_native_ols_diagnostics_match_upstream_and_do_not_test_independence(self):
        from statsmodels.stats.diagnostic import het_breuschpagan
        from statsmodels.stats.stattools import durbin_watson
        model = self.sm.OLS(self.y, self.sm.add_constant(self.x)).fit()
        result = assumption_checks.check_regression_diagnostics(model, plot=False)
        np.testing.assert_allclose(result['heteroscedasticity']['p_value'],
                                   het_breuschpagan(model.resid, model.model.exog)[1])
        self.assertIsNone(result['autocorrelation']['statistic'])
        ordered = assumption_checks.check_regression_diagnostics(model, ordered=True, plot=False)
        self.assertAlmostEqual(ordered['autocorrelation']['statistic'], durbin_watson(model.resid))
        self.assertIsNone(ordered['autocorrelation']['ok'])
        self.assertEqual(len(result['vif']), 1)

    def test_invalid_regression_designs_reject(self):
        designs = [self.x[:, None], np.column_stack([np.ones(80), self.x, self.x])]
        for design in designs:
            with self.assertRaises(ValueError):
                assumption_checks.check_regression_diagnostics(self.sm.OLS(self.y, design).fit(), plot=False)
        with self.assertRaises(ValueError):
            assumption_checks.check_regression_diagnostics(
                self.sm.OLS(1 + self.x, self.sm.add_constant(self.x)).fit(), plot=False)

    def test_plotting_paths_close_their_figure(self):
        import matplotlib.pyplot as plt
        before = plt.get_fignums()
        model = self.sm.OLS(self.y, self.sm.add_constant(self.x)).fit()
        assumption_checks.check_regression_diagnostics(model, plot=True)
        assumption_checks.detect_outliers(NORMAL, plot=True)
        self.assertEqual(plt.get_fignums(), before)


class CurrentEffectApiTests(unittest.TestCase):
    def test_signed_pooled_and_paired_effects_match_definitions(self):
        pg = pytest.importorskip('pingouin')
        from scipy import stats
        x, y = np.array([1., 2, 3, 5]), np.array([4., 5, 7, 9, 12])
        sp = np.sqrt(((len(x) - 1) * x.var(ddof=1) + (len(y) - 1) * y.var(ddof=1))
                     / (len(x) + len(y) - 2))
        signed = pg.compute_effsize(x, y, eftype='cohen')
        self.assertAlmostEqual(signed, (x.mean() - y.mean()) / sp)
        self.assertAlmostEqual(pg.ttest(x, y)['cohen_d'].iloc[0], abs(signed))
        post = np.array([2., 4, 3, 8])
        dz = pg.compute_effsize(x, post, paired=True, eftype='cohen_dz')
        self.assertAlmostEqual(dz, stats.ttest_rel(x, post).statistic / np.sqrt(len(x)))
        self.assertNotAlmostEqual(dz, pg.compute_effsize(x, post, paired=True, eftype='cohen'))

    def test_welch_and_one_sided_bayesfactor_contracts(self):
        pg = pytest.importorskip('pingouin')
        from scipy import stats
        x, y = np.array([1., 2, 3, 5]), np.array([1., 4, 20, 21])
        result = pg.ttest(x, y, correction=True)
        self.assertAlmostEqual(result['T'].iloc[0], stats.ttest_ind(x, y, equal_var=False).statistic)
        self.assertNotIn('BF10', pg.ttest(x, y, alternative='greater'))
        with self.assertRaises((ValueError, AssertionError)):
            pg.bayesfactor_ttest(1., 4, 4, alternative='greater')


DemoBlockTests = skill_contract.cli.demo_test_case(SKILL_ROOT, ('assumption_checks.py',))


if __name__ == "__main__":
    unittest.main()
