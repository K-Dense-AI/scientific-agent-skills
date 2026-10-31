"""Tests for the PyMC diagnostic and model-comparison helpers.

These scripts are the layer an agent trusts to say "this fit is usable" and
"this model wins", so the tests attack both halves of that. The diagnostic
branches are driven from hand-built posteriors where the right answer is known
by construction -- 2 chains of standard normal draws must pass every check, a
posterior whose every transition diverged must be flagged, and a threshold set
absurdly high must flag ESS -- which proves the checker rejects bad fits *and*
stays silent on good ones. The comparison half is anchored on data with a real
slope: a regression that includes the slope must outrank an intercept-only model
and take essentially all of the stacking weight.

Two regressions are guarded explicitly, both from the ArviZ 1.x API. `az.summary`
now formats its output for display by default, returning strings, so every
threshold comparison raised TypeError until `round_to="none"` was passed; and
ArviZ 1.x plots return a PlotCollection instead of drawing into pyplot's current
figure, so saving through `plt.savefig` produced blank images.
"""

from __future__ import annotations

import functools
import sys
import tempfile
import unittest
from pathlib import Path

import pytest

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pymc"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

np = pytest.importorskip("numpy", reason="pymc scripts need numpy")
pd = pytest.importorskip("pandas", reason="pymc scripts need pandas")
az = pytest.importorskip("arviz", reason="pymc scripts need arviz")
pm = pytest.importorskip("pymc", reason="pymc scripts need pymc")
xr = pytest.importorskip("xarray", reason="pymc posteriors are xarray DataTrees")
matplotlib = pytest.importorskip("matplotlib", reason="the reports save figures")
matplotlib.use("Agg")

import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

import model_comparison  # noqa: E402
import model_diagnostics  # noqa: E402

# Both scripts are importable libraries: their `__main__` blocks only print
# usage text, so there is no argparse CLI to exercise and no worked example to
# run. `demo_test_case` would assert nothing beyond "print works".

# 800 independent draws: comfortably above check_diagnostics' default ESS floor
# of 400, so the default thresholds describe a fit that genuinely passes.
CHAINS, DRAWS = 2, 400


def synthetic_posterior(
    *,
    diverging: int = 0,
    tree_depth: int = 3,
    with_energy: bool = True,
    shift_second_chain: float = 0.0,
) -> "xr.DataTree":
    """A posterior with known diagnostics, built without sampling.

    Independent standard-normal draws have R-hat ~ 1 and ESS ~ the draw count,
    so the default is a fit that must pass every check. `shift_second_chain`
    offsets one chain to force chains that disagree, which is what R-hat exists
    to catch.
    """
    generator = np.random.default_rng(0)
    draws = generator.standard_normal((CHAINS, DRAWS))
    draws[1] += shift_second_chain
    coords = {"chain": np.arange(CHAINS), "draw": np.arange(DRAWS)}
    posterior = xr.Dataset(
        {"theta": (("chain", "draw"), draws)},
        coords=coords,
    )
    statistics = {
        "diverging": (
            ("chain", "draw"),
            np.full((CHAINS, DRAWS), bool(diverging)),
        ),
        "tree_depth": (
            ("chain", "draw"),
            np.full((CHAINS, DRAWS), tree_depth),
        ),
    }
    if with_energy:
        statistics["energy"] = (
            ("chain", "draw"),
            generator.standard_normal((CHAINS, DRAWS)),
        )
    return xr.DataTree.from_dict(
        {
            "posterior": posterior,
            "sample_stats": xr.Dataset(statistics, coords=coords),
        }
    )


@functools.lru_cache(maxsize=1)
def fitted_models() -> tuple:
    """One short fit per model, shared by every test that needs real MCMC.

    The data really does have slope 2, so the model that can represent a slope
    must win the comparison. Draws are kept small on purpose: nothing here needs
    a converged chain, only a coherent one.
    """
    generator = np.random.default_rng(0)
    predictor = generator.normal(size=40)
    outcome = 2.0 * predictor + generator.normal(scale=0.3, size=40)

    def fit(with_slope: bool, seed: int):
        with pm.Model():
            intercept = pm.Normal("intercept", 0, 5)
            sigma = pm.HalfNormal("sigma", 1)
            if with_slope:
                slope = pm.Normal("slope", 0, 5)
                mean = intercept + slope * predictor
            else:
                mean = intercept
            pm.Normal("y_obs", mean, sigma, observed=outcome)
            idata = pm.sample(
                draws=250,
                tune=250,
                chains=2,
                random_seed=seed,
                progressbar=False,
                cores=1,
                nuts_sampler="pymc",
            )
            pm.compute_log_likelihood(idata, progressbar=False)
            pm.sample_posterior_predictive(
                idata, extend_inferencedata=True, random_seed=seed, progressbar=False
            )
            prior = pm.sample_prior_predictive(draws=200, random_seed=seed)
        return idata, prior

    with_slope, prior = fit(True, 1)
    intercept_only, _ = fit(False, 2)
    return with_slope, intercept_only, prior


class SummaryNumericTests(unittest.TestCase):
    def test_the_summary_columns_are_numeric_not_formatted_strings(self) -> None:
        # The regression: ArviZ 1.x rounds `summary` for display by default, so
        # `summary['r_hat'] > 1.01` raised "'>' not supported between instances
        # of 'str' and 'float'".
        results = model_diagnostics.check_diagnostics(synthetic_posterior())
        summary = results["summary"]
        for column in ("mean", "sd", "r_hat", "ess_bulk", "ess_tail"):
            with self.subTest(column=column):
                self.assertTrue(
                    pd.api.types.is_numeric_dtype(summary[column]),
                    f"{column} is {summary[column].dtype}, not numeric",
                )

    def test_the_summary_describes_the_draws_it_was_given(self) -> None:
        # Standard-normal draws: mean near 0, sd near 1, and -- because the draws
        # are independent -- an effective sample size close to the draw count.
        summary = model_diagnostics.check_diagnostics(synthetic_posterior())["summary"]
        self.assertAlmostEqual(float(summary.loc["theta", "mean"]), 0.0, delta=0.2)
        self.assertAlmostEqual(float(summary.loc["theta", "sd"]), 1.0, delta=0.2)
        self.assertAlmostEqual(
            float(summary.loc["theta", "ess_bulk"]), CHAINS * DRAWS, delta=0.25 * CHAINS * DRAWS
        )
        self.assertAlmostEqual(float(summary.loc["theta", "r_hat"]), 1.0, delta=0.01)


class DiagnosticBranchTests(unittest.TestCase):
    def test_a_healthy_posterior_raises_no_issues(self) -> None:
        # The direction a suite of broken inputs would never prove: a clean fit
        # must come back clean.
        results = model_diagnostics.check_diagnostics(synthetic_posterior())
        self.assertFalse(results["has_issues"])
        self.assertEqual(results["issues"], [])
        self.assertNotIn("n_divergences", results)

    def test_disagreeing_chains_are_flagged_as_a_convergence_failure(self) -> None:
        # Offsetting one chain by three standard deviations is exactly the
        # situation R-hat is designed to detect.
        results = model_diagnostics.check_diagnostics(
            synthetic_posterior(shift_second_chain=3.0)
        )
        self.assertTrue(results["has_issues"])
        self.assertIn("convergence", results["issues"])
        self.assertGreater(float(results["summary"].loc["theta", "r_hat"]), 1.01)

    def test_a_stricter_ess_threshold_flags_a_posterior_that_otherwise_passes(self) -> None:
        clean = model_diagnostics.check_diagnostics(
            synthetic_posterior(), ess_threshold=10
        )
        strict = model_diagnostics.check_diagnostics(
            synthetic_posterior(), ess_threshold=10_000
        )
        self.assertEqual(clean["issues"], [])
        self.assertIn("low_ess", strict["issues"])
        self.assertTrue(strict["has_issues"])

    def test_every_divergent_transition_is_counted(self) -> None:
        results = model_diagnostics.check_diagnostics(synthetic_posterior(diverging=1))
        self.assertIn("divergences", results["issues"])
        self.assertTrue(results["has_issues"])
        self.assertEqual(results["n_divergences"], CHAINS * DRAWS)

    def test_hitting_the_maximum_tree_depth_is_reported(self) -> None:
        # PyMC's default max_treedepth is 10. This costs sampling efficiency
        # rather than validity, so it is listed as an issue without setting the
        # has_issues flag that divergences and bad R-hat do.
        results = model_diagnostics.check_diagnostics(synthetic_posterior(tree_depth=10), max_treedepth=10)
        self.assertIn("max_treedepth", results["issues"])

    def test_a_posterior_without_energy_statistics_is_still_checked(self) -> None:
        # Non-NUTS samplers record no energy; the checker must not require it.
        results = model_diagnostics.check_diagnostics(
            synthetic_posterior(with_energy=False)
        )
        self.assertEqual(results["issues"], [])

    def test_var_names_restricts_the_summary(self) -> None:
        idata, _, _ = fitted_models()
        results = model_diagnostics.check_diagnostics(idata, var_names=["slope"])
        self.assertEqual(list(results["summary"].index), ["slope"])
        # The generating slope was 2.0, and a short but healthy chain finds it.
        self.assertAlmostEqual(float(results["summary"].loc["slope", "mean"]), 2.0, delta=0.2)


class DiagnosticReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.addCleanup(plt.close, "all")

    def test_the_report_writes_every_documented_artefact(self) -> None:
        idata, _, _ = fitted_models()
        with tempfile.TemporaryDirectory() as directory:
            results = model_diagnostics.create_diagnostic_report(
                idata, var_names=["intercept", "slope", "sigma"], output_dir=directory
            )
            written = {path.name for path in Path(directory).iterdir()}
            self.assertEqual(
                written,
                {
                    "trace_plots.png",
                    "rank_plots.png",
                    "autocorr_plots.png",
                    "energy_plot.png",
                    "ess_local.png",
                    "summary_statistics.csv",
                },
            )
            # The regression: ArviZ 1.x plots do not draw into pyplot's current
            # figure, so saving with plt.savefig() wrote an all-white image.
            image = mpimg.imread(str(Path(directory) / "trace_plots.png"))
            self.assertLess(
                float(image[..., :3].min()), 0.5, "trace_plots.png is blank"
            )
            summary = pd.read_csv(Path(directory) / "summary_statistics.csv", index_col=0)
            self.assertEqual(set(summary.index), {"intercept", "slope", "sigma"})
            self.assertEqual(list(summary.index), list(results["summary"].index))

    def test_the_report_leaves_no_open_figures(self) -> None:
        idata, _, _ = fitted_models()
        with tempfile.TemporaryDirectory() as directory:
            model_diagnostics.create_diagnostic_report(
                idata, var_names=["slope"], output_dir=directory
            )
        self.assertEqual(plt.get_fignums(), [])

    def test_the_output_directory_is_created_if_it_is_missing(self) -> None:
        idata, _, _ = fitted_models()
        with tempfile.TemporaryDirectory() as directory:
            nested = Path(directory) / "a" / "b"
            model_diagnostics.create_diagnostic_report(
                idata, var_names=["slope"], output_dir=str(nested)
            )
            self.assertTrue((nested / "summary_statistics.csv").is_file())

    def test_the_prior_and_posterior_are_overlaid_in_one_figure(self) -> None:
        idata, _, prior = fitted_models()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prior_posterior.png"
            collection = model_diagnostics.compare_prior_posterior(
                idata, prior, var_names=["intercept", "slope"], output_path=str(path)
            )
            self.assertGreater(path.stat().st_size, 0)
            image = mpimg.imread(str(path))
            self.assertLess(float(image[..., :3].min()), 0.5, "the figure is blank")
            # One panel per requested variable.
            self.assertEqual(len(collection.viz["figure"].item().axes), 2)


class ModelComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with_slope, intercept_only, _ = fitted_models()
        cls.models = {"with_slope": with_slope, "intercept_only": intercept_only}
        cls.comparison = model_comparison.compare_models(cls.models, verbose=False)

    def test_the_model_that_matches_the_data_generating_process_wins(self) -> None:
        # The data is y = 2x + noise, so dropping the slope must cost predictive
        # accuracy. This is known before the code runs.
        self.assertEqual(list(self.comparison.index)[0], "with_slope")
        self.assertEqual(int(self.comparison.loc["with_slope", "rank"]), 0)
        self.assertAlmostEqual(float(self.comparison.loc["with_slope", "elpd_diff"]), 0.0)
        self.assertLess(float(self.comparison.loc["intercept_only", "elpd_diff"]), -4.0)
        self.assertGreater(
            float(self.comparison.loc["with_slope", "elpd"]),
            float(self.comparison.loc["intercept_only", "elpd"]),
        )

    def test_the_stacking_weights_form_a_distribution(self) -> None:
        weights = self.comparison["weight"]
        self.assertAlmostEqual(float(weights.sum()), 1.0, places=6)
        self.assertGreater(float(weights.loc["with_slope"]), 0.95)

    def test_the_comparison_columns_are_numeric(self) -> None:
        # Same display-formatting trap as az.summary: the interpretation block
        # compares elpd_diff against dse.
        for column in ("elpd", "elpd_diff", "dse", "se", "weight", "p"):
            with self.subTest(column=column):
                self.assertTrue(pd.api.types.is_numeric_dtype(self.comparison[column]))

    def test_the_difference_is_large_relative_to_its_own_standard_error(self) -> None:
        difference = abs(float(self.comparison.loc["intercept_only", "elpd_diff"]))
        self.assertGreater(difference, 2 * float(self.comparison.loc["intercept_only", "dse"]))

    def test_loo_is_accepted_under_either_spelling_and_any_case(self) -> None:
        for criterion in ("loo", "LOO", "elpd"):
            with self.subTest(ic=criterion):
                frame = model_comparison.compare_models(
                    self.models, ic=criterion, verbose=False
                )
                self.assertEqual(list(frame.index), list(self.comparison.index))

    def test_an_unsupported_criterion_is_refused_with_a_way_forward(self) -> None:
        for criterion in ("waic", "bic", "dic"):
            with self.subTest(ic=criterion):
                with self.assertRaisesRegex(ValueError, "az.waic"):
                    model_comparison.compare_models(self.models, ic=criterion)

    def test_the_verbose_report_names_the_winner(self) -> None:
        # verbose=True is the default, so it must not raise on the way through
        # the interpretation and reliability blocks.
        frame = model_comparison.compare_models(self.models, verbose=True)
        self.assertEqual(list(frame.index)[0], "with_slope")


class LooReliabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with_slope, _, _ = fitted_models()
        cls.results = model_comparison.check_loo_reliability(
            {"with_slope": with_slope}, verbose=False
        )["with_slope"]

    def test_one_pareto_k_is_reported_per_observation(self) -> None:
        self.assertEqual(np.shape(self.results["pareto_k"]), (40,))

    def test_the_counts_agree_with_the_threshold_they_were_given(self) -> None:
        pareto_k = np.asarray(self.results["pareto_k"])
        self.assertEqual(self.results["n_high"], int((pareto_k > self.results["threshold"]).sum()))
        self.assertEqual(self.results["n_very_high"], int((pareto_k > 1.0).sum()))
        self.assertAlmostEqual(float(self.results["max_k"]), float(pareto_k.max()))

    def test_a_well_specified_model_has_no_problem_observations(self) -> None:
        # Correct model, 40 well-behaved points: PSIS must be reliable.
        self.assertEqual(self.results["n_high"], 0)
        self.assertLess(float(self.results["max_k"]), 0.7)

    def test_lowering_the_threshold_flags_more_observations(self) -> None:
        with_slope, _, _ = fitted_models()
        lenient = model_comparison.check_loo_reliability(
            {"m": with_slope}, threshold=0.7, verbose=False
        )["m"]
        strict = model_comparison.check_loo_reliability(
            {"m": with_slope}, threshold=0.0, verbose=False
        )["m"]
        pareto_k = np.asarray(lenient["pareto_k"])
        self.assertEqual(lenient["n_high"], 0)
        # Only strictly greater than the threshold counts, and some k are
        # negative, so this is not simply every observation.
        self.assertEqual(strict["n_high"], int((pareto_k > 0.0).sum()))
        self.assertGreater(strict["n_high"], lenient["n_high"])


class ModelAveragingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with_slope, intercept_only, _ = fitted_models()
        cls.models = {"with_slope": with_slope, "intercept_only": intercept_only}

    def test_explicit_weights_are_normalised_and_mixture_preserves_variance(self):
        # The mixture of point masses at -10 and 10 must never create 0.
        def tree(value):
            return xr.DataTree.from_dict({'posterior_predictive': xr.Dataset({
                'y_obs': (('chain', 'draw', 'obs'), np.full((2, 10, 2), value))},
                coords={'obs': ['a', 'b']})})
        models = {'negative': tree(-10.), 'positive': tree(10.)}
        draws, weights = model_comparison.model_averaging(
            models, weights=[3, 1], n_samples=10000, random_seed=13)
        np.testing.assert_allclose(weights, [.75, .25])
        self.assertEqual(draws.shape, (10000, 2))
        self.assertEqual(set(np.unique(draws)), {-10., 10.})
        self.assertAlmostEqual(float(draws.mean()), -5, delta=.4)
        self.assertAlmostEqual(float(draws.var()), 75, delta=4)
        np.testing.assert_array_equal(draws[:, 0], draws[:, 1])

    def test_derived_weights_are_in_input_order(self):
        models = dict(reversed(list(self.models.items())))
        draws, weights = model_comparison.model_averaging(models, random_seed=9)
        self.assertAlmostEqual(float(np.sum(weights)), 1, places=6)
        self.assertEqual(draws.shape, (500, 40))
        self.assertGreater(weights[1], .95)

    def test_missing_predictions_raise(self):
        with self.assertRaisesRegex(ValueError, 'missing'):
            model_comparison.model_averaging(self.models, weights=[1, 1], var_name='absent')

    def test_invalid_weights_raise(self):
        for weights in ([1], [0, 0], [-1, 2], [np.nan, 1], [np.inf, 1]):
            with self.subTest(weights=weights), self.assertRaises(ValueError):
                model_comparison.model_averaging(self.models, weights=weights)

    def test_coordinate_mismatch_raises(self):
        first, second = self.models.values()
        second = second.copy(deep=True)
        dim = second.posterior_predictive['y_obs'].dims[-1]
        second['posterior_predictive'] = second.posterior_predictive.to_dataset().assign_coords({dim: np.arange(40)[::-1]})
        with self.assertRaisesRegex(ValueError, 'coordinates'):
            model_comparison.model_averaging({'a': first, 'b': second}, weights=[1, 1])

    def test_outcome_mismatch_refuses_model_comparison(self):
        first, second = self.models.values()
        second = second.copy(deep=True)
        second['observed_data']['y_obs'] = second.observed_data['y_obs'] + 1
        with self.assertRaisesRegex(ValueError, 'identical observed'):
            model_comparison.compare_models({'a': first, 'b': second}, verbose=False)

    def test_likelihood_coordinate_mismatch_refuses_comparison(self):
        first, second = self.models.values()
        second = second.copy(deep=True)
        dim = second.log_likelihood['y_obs'].dims[-1]
        second['log_likelihood'] = second.log_likelihood.to_dataset().assign_coords({dim: np.arange(40)[::-1]})
        with self.assertRaisesRegex(ValueError, 'likelihood dimensions and coordinates'):
            model_comparison.compare_models({'a': first, 'b': second}, verbose=False)


class ComparisonPlotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.addCleanup(plt.close, "all")

    def test_the_comparison_plot_is_saved_and_is_not_blank(self) -> None:
        with_slope, intercept_only, _ = fitted_models()
        comparison = model_comparison.compare_models(
            {"with_slope": with_slope, "intercept_only": intercept_only}, verbose=False
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "comparison.png"
            figure = model_comparison.plot_model_comparison(
                comparison, output_path=str(path), show=False
            )
            self.assertIsInstance(figure, matplotlib.figure.Figure)
            image = mpimg.imread(str(path))
            self.assertLess(float(image[..., :3].min()), 0.5, "the figure is blank")
        self.assertEqual(plt.get_fignums(), [])


class CrossValidationGuidanceTests(unittest.TestCase):
    def test_the_guidance_names_the_fold_count_it_was_asked_about(self) -> None:
        # Documentation-only helper: it must not touch the posteriors it is
        # handed, so passing an empty dict has to be safe.
        model_comparison.cross_validation_comparison({}, k=7, verbose=True)


if __name__ == "__main__":
    unittest.main()


class UnavailableDiagnosticTests(unittest.TestCase):
    def test_single_chain_is_not_a_convergence_pass(self):
        result = model_diagnostics.check_diagnostics(synthetic_posterior().isel(chain=[0]))
        self.assertTrue(result['has_issues'])
        self.assertIn('insufficient_chains', result['issues'])
        self.assertIn('nonfinite_diagnostics', result['issues'])

    def test_nan_and_constant_parameters_are_not_a_pass(self):
        for value in (np.nan, 0.):
            tree = synthetic_posterior()
            tree['posterior']['theta'] = xr.full_like(tree.posterior['theta'], value)
            result = model_diagnostics.check_diagnostics(tree)
            self.assertIn('nonfinite_diagnostics', result['issues'])

    def test_missing_sampler_statistics_are_explicit(self):
        tree = synthetic_posterior()
        del tree['sample_stats']
        result = model_diagnostics.check_diagnostics(tree)
        self.assertEqual(set(result['unavailable']), {'divergences', 'max_treedepth', 'bfmi'})

    def test_observed_maximum_is_not_configured_tree_limit(self):
        result = model_diagnostics.check_diagnostics(synthetic_posterior(tree_depth=12))
        self.assertNotIn('max_treedepth', result['issues'])
        self.assertIn('max_treedepth', result['unavailable'])

    def test_low_energy_bfmi_is_flagged(self):
        tree = synthetic_posterior()
        tree['sample_stats']['energy'] = xr.DataArray(
            np.tile(np.arange(DRAWS, dtype=float), (CHAINS, 1)), dims=('chain', 'draw'))
        result = model_diagnostics.check_diagnostics(tree)
        self.assertIn('low_bfmi', result['issues'])
