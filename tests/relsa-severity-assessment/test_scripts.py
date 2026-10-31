"""Tests for the relsa-severity-assessment scripts.

The anchor is external: the RELSA R package publishes a rendered worked example
(the "RELSA Score" vignette at https://talbotsr.com/RELSA/, from the `surgery`
dataset, animal Ca_001) that prints its own normalized values, RELSA weights,
and scores. `RParityTests` pins the Python port against those printed numbers
rather than against whatever this implementation happens to produce, so a
regression in the algorithm fails the suite even if it is internally
consistent.

The upstream dataset is not redistributed here (it is GPL-3). Instead the test
supplies the vignette's own published normalized table plus the reference
model's `maxsev` vector, which is all the score calculation consumes.

Everything else tests the guardrails that make a wrong severity score loud
instead of silent: directionality mismatches, zero baselines, degenerate
reference sets, and variable composition changing along a trajectory.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
import unittest
import warnings
from pathlib import Path

import pytest

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "relsa-severity-assessment"
SCRIPTS = SKILL_ROOT / "scripts"
EXAMPLE = SKILL_ROOT / "assets" / "example_cohort.csv"
sys.path.insert(0, str(SCRIPTS))

pytest.importorskip("numpy", reason="relsa-severity-assessment needs numpy")
pytest.importorskip("pandas", reason="relsa-severity-assessment needs pandas")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import _common  # noqa: E402
import relsa_score  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

# --------------------------------------------------------------------------- #
# Ground truth from the R package's rendered vignette (surgery, animal Ca_001)
# --------------------------------------------------------------------------- #
R_VARIABLES = ["bwc", "burON", "hr", "hrv", "temp", "act"]
R_TURNED = ["hr", "temp"]

# The vignette's printed table of normalized values, days -1 to 4.
R_NORMALIZED = [
    (-1, [100.00, 100.00, 100.00, 100.00, 100.00, 100.00]),
    (0, [87.50, 62.12, 145.65, 16.50, 98.83, 11.79]),
    (1, [90.76, 135.72, 128.96, 38.96, 102.42, 38.25]),
    (2, [92.93, 137.62, 118.63, 54.44, 101.44, 33.02]),
    (3, [94.02, None, 106.30, 56.89, 100.27, 26.88]),
    (4, [94.02, 96.13, 115.87, 57.39, 101.29, 36.37]),
]

# The vignette's printed RELSA weight matrix.
R_WEIGHTS = {
    -1: [0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
    0: [0.81, 0.38, 0.85, 0.91, 0.00, 0.92],
    1: [0.60, 0.00, 0.54, 0.66, 0.55, 0.65],
    2: [0.46, 0.00, 0.35, 0.50, 0.33, 0.70],
    3: [0.39, None, 0.12, 0.47, 0.06, 0.76],
    4: [0.39, 0.04, 0.30, 0.46, 0.29, 0.67],
}

# The vignette's printed RELSA scores.
R_RELSA = {-1: 0.00, 0: 0.73, 1: 0.55, 2: 0.44, 3: 0.44, 4: 0.41}

# Extrema of the normalized reference set (all 28 surgery animals), which is the
# only thing the score calculation needs from the reference cohort.
R_MAXSEV = {
    "bwc": 84.5454545454546,
    "burON": 0.0,
    "hr": 153.39232571392373,
    "hrv": 8.092355935881447,
    "temp": 104.41252267854198,
    "act": 4.3397095244614246,
}


def r_reference() -> "relsa_score.ReferenceModel":
    return relsa_score.ReferenceModel(
        variables=tuple(R_VARIABLES),
        turned=tuple(R_TURNED),
        maxsev=dict(R_MAXSEV),
        maxdelta={k: abs(100.0 - v) for k, v in R_MAXSEV.items()},
        n_animals=28,
        n_rows=840,
        label="RELSA surgery reference (vignette)",
    )


def r_normalized_frame() -> pd.DataFrame:
    rows = []
    for day, values in R_NORMALIZED:
        row = {"id": "Ca_001", "time": day}
        row.update(dict(zip(R_VARIABLES, [np.nan if v is None else v for v in values])))
        rows.append(row)
    return pd.DataFrame(rows)


class RParityTests(unittest.TestCase):
    """The port must reproduce the R package's published output to 2 dp."""

    def setUp(self) -> None:
        self.scored = relsa_score.relsa_scores(r_normalized_frame(), r_reference())
        self.by_day = self.scored.set_index("time")

    def test_weights_match_the_published_matrix(self) -> None:
        for day, expected in R_WEIGHTS.items():
            for variable, value in zip(R_VARIABLES, expected):
                got = self.by_day.loc[day, variable]
                if value is None:
                    self.assertTrue(
                        pd.isna(got), f"{variable} day {day}: expected NA, got {got}"
                    )
                else:
                    self.assertAlmostEqual(
                        float(got), value, places=9,
                        msg=f"{variable} day {day}: R={value} py={got}",
                    )

    def test_relsa_scores_match_the_published_values(self) -> None:
        for day, expected in R_RELSA.items():
            self.assertAlmostEqual(
                float(self.by_day.loc[day, "relsa"]), expected, places=9,
                msg=f"day {day}",
            )

    def test_missing_variable_is_dropped_from_the_mean_not_zeroed(self) -> None:
        # Day 3 has burON missing: 5 variables enter the score, not 6.
        self.assertEqual(int(self.by_day.loc[3, "n_vars"]), 5)
        self.assertEqual(int(self.by_day.loc[0, "n_vars"]), 6)
        # Zeroing it would have given sqrt(0.9686/6) = 0.402, not 0.44.
        self.assertAlmostEqual(float(self.by_day.loc[3, "relsa"]), 0.44, places=9)

    def test_baseline_row_scores_zero_rather_than_missing(self) -> None:
        self.assertAlmostEqual(float(self.by_day.loc[-1, "relsa"]), 0.0, places=12)

    def test_root_mean_square_not_arithmetic_mean(self) -> None:
        # Day 0 weights: RMS = 0.73, arithmetic mean would be 0.645.
        weights = [w for w in R_WEIGHTS[0]]
        rms = math.sqrt(sum(w**2 for w in weights) / len(weights))
        self.assertAlmostEqual(rms, 0.73, places=2)
        self.assertAlmostEqual(float(self.by_day.loc[0, "relsa"]), 0.73, places=9)

    def test_full_precision_stays_close_to_the_rounded_score(self) -> None:
        unrounded = relsa_score.relsa_scores(
            r_normalized_frame(), r_reference(), round_digits=None
        ).set_index("time")
        for day, expected in R_RELSA.items():
            # Skipping the R-compatible 2-dp rounding shifts scores by <= 0.01.
            self.assertAlmostEqual(
                float(unrounded.loc[day, "relsa"]), expected, delta=0.01,
                msg=f"day {day}",
            )


class DirectionalityTests(unittest.TestCase):
    def _frame(self, rising: bool) -> pd.DataFrame:
        # One animal whose single variable either rises or falls from baseline.
        values = [100.0, 130.0, 160.0] if rising else [100.0, 80.0, 60.0]
        return pd.DataFrame({"id": "A", "time": [-1, 0, 1], "marker": values})

    def test_turned_variable_registers_an_increase(self) -> None:
        frame = self._frame(rising=True)
        reference = relsa_score.build_reference(frame, ["marker"], turned=["marker"])
        scored = relsa_score.relsa_scores(frame, reference)
        self.assertAlmostEqual(float(scored["relsa"].iloc[-1]), 1.0, places=6)
        self.assertGreater(float(scored["relsa"].iloc[1]), 0.0)

    def test_rising_variable_left_unturned_scores_zero_throughout(self) -> None:
        # The silent failure this skill warns about: wrong directionality does not
        # error, it erases the variable's contribution. A second animal dips
        # slightly below baseline so the reference set is not degenerate.
        frame = pd.DataFrame({
            "id": ["A", "A", "A", "B", "B", "B"],
            "time": [-1, 0, 1, -1, 0, 1],
            "marker": [100.0, 130.0, 160.0, 100.0, 98.0, 99.0],
        })
        reference = relsa_score.build_reference(frame, ["marker"], turned=[])
        scored = relsa_score.relsa_scores(frame, reference)
        rising = scored[scored["id"] == "A"]
        self.assertTrue((rising["relsa"].fillna(0) == 0).all())
        # No warning is possible here: animal B does fall below baseline, so the
        # reference set is self-consistent. Directionality cannot be inferred from
        # the data in general -- in the published models activity legitimately
        # swings further above baseline than below -- which is why it has to be
        # declared, and why declaring it wrongly is silent.
        self.assertGreater(float(scored[scored["id"] == "B"]["relsa"].max()), 0.0)

    def test_all_rising_variable_left_unturned_is_rejected_outright(self) -> None:
        # When nothing in the reference set ever falls, the degenerate denominator
        # is caught rather than producing a scale of zeros.
        frame = self._frame(rising=True)
        with self.assertRaises(_common.RelsaDataError):
            relsa_score.build_reference(frame, ["marker"], turned=[])

    def test_variable_that_only_ever_rises_and_is_not_turned_warns(self) -> None:
        # The realistic mistake: a biomarker left out of --turned. Its baseline row
        # is absent, so every observed value is above 100 and the mismatch is
        # detectable rather than merely suspicious.
        frame = pd.DataFrame({
            "id": ["A", "A", "B", "B"],
            "time": [0, 1, 0, 1],
            "il6": [150.0, 200.0, 140.0, 180.0],
        })
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            relsa_score.build_reference(frame, ["il6"], turned=[])
            messages = " ".join(str(w.message) for w in caught)
        self.assertIn("opposite direction", messages)

    def test_recovery_below_baseline_is_floored_at_zero(self) -> None:
        frame = pd.DataFrame(
            {"id": "A", "time": [-1, 0, 1], "weight": [100.0, 80.0, 110.0]}
        )
        reference = relsa_score.build_reference(frame, ["weight"])
        scored = relsa_score.relsa_scores(frame, reference)
        self.assertAlmostEqual(float(scored["relsa"].iloc[2]), 0.0, places=9)


class ReferenceModelTests(unittest.TestCase):
    def test_reference_extrema_use_min_or_max_by_direction(self) -> None:
        frame = pd.DataFrame({
            "id": ["A", "A", "B", "B"],
            "time": [-1, 0, -1, 0],
            "falls": [100.0, 70.0, 100.0, 85.0],
            "rises": [100.0, 140.0, 100.0, 120.0],
        })
        reference = relsa_score.build_reference(
            frame, ["falls", "rises"], turned=["rises"]
        )
        self.assertAlmostEqual(reference.maxsev["falls"], 70.0)
        self.assertAlmostEqual(reference.maxdelta["falls"], 30.0)
        self.assertAlmostEqual(reference.maxsev["rises"], 140.0)
        self.assertAlmostEqual(reference.maxdelta["rises"], 40.0)

    def test_flat_variable_in_reference_set_is_rejected(self) -> None:
        frame = pd.DataFrame({"id": "A", "time": [-1, 0], "flat": [100.0, 100.0]})
        with self.assertRaises(_common.RelsaDataError) as ctx:
            relsa_score.build_reference(frame, ["flat"])
        self.assertIn("never deviate", str(ctx.exception))

    def test_reference_model_round_trips_through_json(self) -> None:
        reference = r_reference()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ref.json"
            reference.to_json(path)
            restored = relsa_score.ReferenceModel.from_json(path)
        self.assertEqual(restored.variables, reference.variables)
        self.assertEqual(restored.turned, reference.turned)
        for key, value in reference.maxdelta.items():
            self.assertAlmostEqual(restored.maxdelta[key], value)

    def test_test_set_missing_a_reference_variable_errors(self) -> None:
        frame = pd.DataFrame({"id": "A", "time": [-1, 0], "bwc": [100.0, 80.0]})
        with self.assertRaises(_common.RelsaDataError) as ctx:
            relsa_score.relsa_scores(frame, r_reference())
        self.assertIn("not in the data", str(ctx.exception))


class DataPreparationTests(unittest.TestCase):
    def test_normalization_is_per_animal_and_lands_on_100(self) -> None:
        frame = pd.DataFrame({
            "id": ["A", "A", "B", "B"],
            "time": [-1, 0, -1, 0],
            "weight": [20.0, 18.0, 30.0, 27.0],
        })
        out = relsa_score.prepare(frame, normalize=["weight"], baseline_time=-1)
        self.assertAlmostEqual(float(out["weight"].iloc[0]), 100.0)
        self.assertAlmostEqual(float(out["weight"].iloc[1]), 90.0)
        self.assertAlmostEqual(float(out["weight"].iloc[2]), 100.0)
        self.assertAlmostEqual(float(out["weight"].iloc[3]), 90.0)

    def test_baseline_window_averages_several_time_points(self) -> None:
        frame = pd.DataFrame({
            "id": "A", "time": [-2, -1, 0], "weight": [22.0, 18.0, 20.0],
        })
        out = relsa_score.prepare(frame, normalize=["weight"], baseline_time=[-2, -1])
        self.assertAlmostEqual(float(out["weight"].iloc[2]), 100.0)  # 20 / mean(22,18)

    def test_zero_baseline_yields_nan_and_warns(self) -> None:
        frame = pd.DataFrame({"id": "A", "time": [-1, 0], "score": [0.0, 3.0]})
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            out = relsa_score.prepare(frame, normalize=["score"], baseline_time=-1)
            messages = " ".join(str(w.message) for w in caught)
        self.assertTrue(out["score"].isna().all())
        self.assertIn("score_to_percent", messages)

    def test_score_to_percent_maps_the_scale_not_the_ratio(self) -> None:
        mapped = _common.score_to_percent([0, 2, 4, 8], max_score=8)
        np.testing.assert_allclose(mapped, [100.0, 125.0, 150.0, 200.0])

    def test_score_to_percent_honours_a_nonzero_healthy_score(self) -> None:
        mapped = _common.score_to_percent([2, 5, 8], max_score=8, baseline_score=2)
        np.testing.assert_allclose(mapped, [100.0, 150.0, 200.0])

    def test_score_to_percent_handles_a_lower_is_worse_scale(self) -> None:
        # A nesting score where a well-built nest is 5 and no nest is 0.
        mapped = _common.score_to_percent([5, 2.5, 0], max_score=0, baseline_score=5)
        np.testing.assert_allclose(mapped, [100.0, 150.0, 200.0])

    def test_score_to_percent_rejects_a_zero_width_scale(self) -> None:
        with self.assertRaises(_common.RelsaDataError):
            _common.score_to_percent([0, 1], max_score=3, baseline_score=3)

    def test_duplicate_id_time_rows_are_fatal(self) -> None:
        frame = pd.DataFrame({"id": "A", "time": [0, 0], "weight": [100.0, 99.0]})
        with self.assertRaises(_common.RelsaDataError) as ctx:
            _common.validate(frame, ["weight"])
        self.assertIn("(id, time)", str(ctx.exception))

    def test_changing_variable_composition_warns(self) -> None:
        # The published-sepsis trap: a variable measured only at the last time point.
        frame = pd.DataFrame({
            "id": "A",
            "time": [-1, 0, 1],
            "temp": [100.0, 90.0, 85.0],
            "bwc": [np.nan, np.nan, 95.0],
        })
        reference = relsa_score.ReferenceModel(
            variables=("temp", "bwc"), turned=(),
            maxsev={"temp": 80.0, "bwc": 80.0},
            maxdelta={"temp": 20.0, "bwc": 20.0},
            n_animals=1, n_rows=3,
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            relsa_score.relsa_scores(frame, reference)
            messages = " ".join(str(w.message) for w in caught)
        self.assertIn("measured variables changes", messages)

    def test_time_column_alias_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "d.csv"
            path.write_text("id,day,weight\nA,-1,20\nA,0,18\n")
            frame = _common.read_relsa_table(path)
        self.assertIn("time", frame.columns)
        self.assertNotIn("day", frame.columns)


class MetricsTests(unittest.TestCase):
    def test_metrics_match_hand_computed_values(self) -> None:
        metrics = _common.forecast_metrics(
            actual=[0.50, 0.80, 0.90],
            predicted=[0.60, 0.80, 0.70],
            lower=[0.40, 0.70, 0.85],
            upper=[0.80, 0.90, 0.95],
        )
        self.assertEqual(metrics.n, 3)
        # residuals 0.10, 0.00, 0.20 -> sqrt((0.01 + 0 + 0.04)/3)
        self.assertAlmostEqual(metrics.rmse, math.sqrt(0.05 / 3), places=12)
        self.assertAlmostEqual(metrics.picp, 100.0, places=9)
        self.assertAlmostEqual(metrics.mpiw, (0.40 + 0.20 + 0.10) / 3, places=12)

    def test_picp_counts_values_outside_the_interval(self) -> None:
        metrics = _common.forecast_metrics(
            actual=[0.5, 0.5], predicted=[0.5, 0.5],
            lower=[0.4, 0.6], upper=[0.6, 0.7],
        )
        self.assertAlmostEqual(metrics.picp, 50.0, places=9)

    def test_metrics_without_an_interval_report_nan_coverage(self) -> None:
        metrics = _common.forecast_metrics(actual=[1.0, 2.0], predicted=[1.0, 2.0])
        self.assertAlmostEqual(metrics.rmse, 0.0)
        self.assertTrue(math.isnan(metrics.picp))
        self.assertTrue(math.isnan(metrics.mpiw))


class ThresholdTests(unittest.TestCase):
    def setUp(self) -> None:
        pytest.importorskip("scipy", reason="kde_thresholds needs scipy")
        import kde_thresholds

        self.kde = kde_thresholds

    def test_bw_nrd0_matches_the_r_formula(self) -> None:
        # x = 1..10: sd = 3.02765, IQR = 4.5 -> 0.9 * min(sd, 4.5/1.349) * 10^-0.2
        expected = 0.9 * 3.0276503540974917 * 10 ** -0.2
        self.assertAlmostEqual(
            self.kde.bw_nrd0(np.arange(1.0, 11.0)), expected, places=12
        )

    def test_bimodal_scores_yield_a_threshold_between_the_modes(self) -> None:
        rng = np.random.default_rng(11)
        scores = np.concatenate([
            rng.normal(0.15, 0.05, 200), rng.normal(0.85, 0.05, 200)
        ])
        result = self.kde.find_thresholds(scores, n_thresholds=1)
        self.assertEqual(len(result.thresholds), 1)
        self.assertGreater(result.thresholds[0], 0.3)
        self.assertLess(result.thresholds[0], 0.7)

    def test_unimodal_scores_yield_no_threshold(self) -> None:
        # Tail wiggle in the density estimate produces a minimum isolating a
        # single observation; the zone-mass filter must reject it.
        rng = np.random.default_rng(3)
        scores = rng.normal(0.4, 0.1, 300)
        result = self.kde.find_thresholds(scores)
        self.assertEqual(result.thresholds, [])
        self.assertEqual(result.zone_names(), ["all"])
        unfiltered = self.kde.find_thresholds(scores, min_zone_fraction=0.0)
        self.assertEqual(len(unfiltered.thresholds), 1)
        self.assertEqual(min(unfiltered.zone_counts.values()), 1)

    def test_zone_assignment_and_names(self) -> None:
        result = self.kde.ThresholdResult(
            thresholds=[0.337, 0.643], modes=[], bandwidth=0.07, n=4,
            grid=np.linspace(0, 1, 5), density=np.ones(5),
        )
        self.assertEqual(result.zone_names(), ["normal", "attention", "danger"])
        self.assertEqual(
            result.assign([0.10, 0.40, 0.90, float("nan")]),
            ["normal", "attention", "danger", "undefined"],
        )

    def test_thresholds_are_bandwidth_dependent(self) -> None:
        # The skill's central caveat: a wider bandwidth can erase the minima.
        rng = np.random.default_rng(5)
        scores = np.concatenate([
            rng.normal(0.15, 0.05, 150), rng.normal(0.75, 0.05, 150)
        ])
        narrow = self.kde.find_thresholds(scores, bandwidth=0.03)
        wide = self.kde.find_thresholds(scores, bandwidth=0.5)
        self.assertGreaterEqual(len(narrow.thresholds), 1)
        self.assertEqual(wide.thresholds, [])


class ForecastTests(unittest.TestCase):
    def setUp(self) -> None:
        pytest.importorskip("statsmodels", reason="forecast_relsa needs statsmodels")
        import forecast_relsa

        self.forecast = forecast_relsa
        warnings.simplefilter("ignore")

    def test_interpolation_hits_the_observed_points(self) -> None:
        grid, values = self.forecast.interpolate_series([0, 1, 2], [0.0, 0.5, 0.4], step=0.1)
        self.assertAlmostEqual(float(grid[0]), 0.0)
        self.assertAlmostEqual(float(values[0]), 0.0)
        self.assertAlmostEqual(float(values[10]), 0.5, places=9)
        self.assertAlmostEqual(float(values[20]), 0.4, places=9)
        self.assertAlmostEqual(float(values[5]), 0.25, places=9)

    def test_forecast_of_a_linear_ramp_continues_the_ramp(self) -> None:
        times = list(range(-1, 6))
        values = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        result = self.forecast.forecast_animal(times, values, target_times=[6], animal="A")
        self.assertAlmostEqual(float(result.predicted[0]), 0.7, delta=0.08)
        self.assertLessEqual(float(result.lower[0]), float(result.predicted[0]))
        self.assertGreaterEqual(float(result.upper[0]), float(result.predicted[0]))

    def test_relsa_forecast_and_interval_are_non_negative(self) -> None:
        times = list(range(-1, 5))
        values = [0.6, 0.5, 0.4, 0.3, 0.2, 0.1]
        result = self.forecast.forecast_animal(times, values, target_times=[5], animal="A")
        self.assertGreaterEqual(float(result.lower[0]), 0.0)
        self.assertGreaterEqual(float(result.predicted[0]), 0.0)

    def test_target_before_the_last_observation_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.forecast.forecast_animal([0, 1, 2], [0.1, 0.2, 0.3], target_times=[1])

    def test_short_series_records_a_warning_note(self) -> None:
        result = self.forecast.forecast_animal(
            [0, 1, 2], [0.2, 0.4, 0.6], target_times=[3], animal="A"
        )
        self.assertTrue(any("observed points" in note for note in result.warnings))

    def test_interpolation_note_is_recorded_when_interpolating(self) -> None:
        result = self.forecast.forecast_animal(
            list(range(6)), [0.1, 0.2, 0.3, 0.4, 0.5, 0.6], target_times=[6]
        )
        self.assertTrue(any("interpolated" in note for note in result.warnings))
        bare = self.forecast.forecast_animal(
            list(range(6)), [0.1, 0.2, 0.3, 0.4, 0.5, 0.6], target_times=[6],
            interpolate_step=None,
        )
        self.assertFalse(any("interpolated" in note for note in bare.warnings))

    def test_auto_arima_selects_differencing_for_a_trending_series(self) -> None:
        trend = np.linspace(0, 2, 60) + np.random.default_rng(0).normal(0, 0.01, 60)
        fit = self.forecast.auto_arima(trend, max_p=2, max_q=2)
        self.assertGreaterEqual(fit.order[1], 1)
        self.assertTrue(math.isfinite(fit.aicc))
        self.assertIn("ARIMA", fit.label())

    def test_predict_endpoint_scores_against_the_actual_value(self) -> None:
        frame = pd.DataFrame({
            "id": "A",
            "time": list(range(-1, 6)),
            "relsa": [0.0, 0.2, 0.4, 0.6, 0.7, 0.8, 0.9],
        })
        forecasts = self.forecast.predict_endpoint(frame, endpoints={"A": 5})
        self.assertEqual(len(forecasts), 1)
        metrics = forecasts[0].metrics()
        self.assertEqual(metrics.n, 1)
        self.assertLess(metrics.rmse, 0.2)
        self.assertAlmostEqual(float(forecasts[0].actual[0]), 0.9)

    def test_summarize_reports_per_animal_rows_and_an_overall_row(self) -> None:
        frame = pd.DataFrame({
            "id": ["A"] * 7 + ["B"] * 7,
            "time": list(range(-1, 6)) * 2,
            "relsa": [0.0, 0.2, 0.4, 0.6, 0.7, 0.8, 0.9,
                      0.0, 0.1, 0.3, 0.4, 0.6, 0.7, 0.8],
        })
        forecasts = self.forecast.predict_endpoint(frame, endpoints={"A": 5, "B": 5})
        summary = self.forecast.summarize(forecasts)
        self.assertIn("OVERALL", set(summary["id"]))
        self.assertEqual(int(summary.loc[summary["id"] == "OVERALL", "n"].iloc[0]), 2)
        for column in ("rmse", "picp", "mpiw"):
            self.assertIn(column, summary.columns)

    def test_rolling_forecast_produces_one_row_per_step(self) -> None:
        times = list(range(-1, 6))
        values = [0.0, 0.2, 0.35, 0.5, 0.62, 0.75, 0.85]
        table = self.forecast.rolling_forecast(times, values, min_train=4, animal="A")
        self.assertEqual(len(table), len(times) - 4)
        self.assertTrue(set(["predicted", "lower", "upper", "actual"]) <= set(table.columns))


@unittest.skipUnless(EXAMPLE.exists(), "example cohort asset missing")
class EndToEndCliTests(unittest.TestCase):
    """The commands documented in SKILL.md must run as written."""

    def setUp(self) -> None:
        pytest.importorskip("scipy", reason="needs scipy")
        pytest.importorskip("statsmodels", reason="needs statsmodels")

    def _run(self, *args: str, cwd: Path) -> subprocess.CompletedProcess:
        result = subprocess.run(
            [sys.executable, *args], cwd=cwd, capture_output=True, text=True, timeout=600
        )
        self.assertEqual(
            result.returncode, 0, f"failed: {args}\n{result.stdout}\n{result.stderr}"
        )
        return result

    def test_documented_pipeline_runs_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            self._run(
                str(SCRIPTS / "relsa_score.py"), str(EXAMPLE),
                "--variables", "weight,temp,score,il6",
                "--normalize", "weight,temp,il6",
                "--turned", "il6",
                "--score-scale", "score=8",
                "--baseline-time", "-1",
                "--reference-group", "condition=endpoint",
                "--save-reference", "reference.json",
                "--out", "relsa_scores.csv",
                cwd=work,
            )
            scores = pd.read_csv(work / "relsa_scores.csv")
            self.assertEqual(len(scores), 54)
            self.assertIn("relsa", scores.columns)
            # This synthetic fixture co-locates all extrema, so its maximum is 1.
            self.assertAlmostEqual(float(scores["relsa"].max()), 1.0, places=2)
            reference = json.loads((work / "reference.json").read_text())
            self.assertEqual(sorted(reference["turned"]), ["il6", "score"])

            self._run(
                str(SCRIPTS / "forecast_relsa.py"), "relsa_scores.csv",
                "--animals", "M01,M02",
                "--endpoints", "M01=5", "--endpoints", "M02=6",
                "--group-col", "condition",
                "--out", "forecasts.csv", "--summary-out", "summary.csv",
                cwd=work,
            )
            forecasts = pd.read_csv(work / "forecasts.csv")
            self.assertEqual(len(forecasts), 2)
            self.assertTrue((forecasts["lower"] <= forecasts["predicted"]).all())
            self.assertTrue((forecasts["predicted"] <= forecasts["upper"]).all())
            summary = pd.read_csv(work / "summary.csv")
            self.assertIn("OVERALL", set(summary["id"]))

            result = self._run(
                str(SCRIPTS / "kde_thresholds.py"), "relsa_scores.csv",
                "--group", "treatment=treated", "--n-thresholds", "2",
                "--json", "zones.json", "--label-out", "zoned.csv",
                cwd=work,
            )
            self.assertIn("bandwidth", result.stdout)
            zones = json.loads((work / "zones.json").read_text())
            self.assertIn("thresholds", zones)
            self.assertIn("zone", pd.read_csv(work / "zoned.csv").columns)

    def test_score_scale_is_required_for_a_zero_baseline_score(self) -> None:
        # Without --score-scale the 0-baseline clinical score cannot be normalized,
        # and the run must say so rather than quietly producing a score.
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "relsa_score.py"), str(EXAMPLE),
                 "--variables", "score", "--normalize", "score",
                 "--baseline-time", "-1", "--out", "out.csv"],
                cwd=tmp, capture_output=True, text=True, timeout=300,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("no finite values", result.stderr + result.stdout)

class RefreshRegressionTests(unittest.TestCase):
    def test_reference_extrema_need_not_cooccur(self):
        frame = pd.DataFrame({"id": "A", "time": [0, 1],
                              "x": [80., 100.], "y": [100., 80.]})
        ref = relsa_score.build_reference(frame, ["x", "y"])
        values = relsa_score.relsa_scores(frame, ref, round_digits=None).relsa
        np.testing.assert_allclose(values, np.sqrt(0.5))

    def test_common_affine_score_scaling_cancels_before_rounding(self):
        scores = []
        for maximum in (8, 16):
            frame = pd.DataFrame({"id": "A", "time": [0, 1, 2],
                                  "s": _common.score_to_percent([0, 2, 4], maximum)})
            ref = relsa_score.build_reference(frame, ["s"], turned=["s"])
            scores.append(relsa_score.relsa_scores(frame, ref, round_digits=None).relsa)
        np.testing.assert_allclose(*scores)

    def test_integer_measurements_normalize_and_earliest_time_is_baseline(self):
        frame = pd.DataFrame({"id": "A", "time": [2, 0, 1], "x": [17, 23, 19]})
        got = relsa_score.prepare(frame, ["x"])
        np.testing.assert_allclose(got.x, np.array([17, 23, 19]) / 23 * 100)

    def test_id_csv_roundtrip_preserves_leading_zeros_and_na(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.csv"
            path.write_text("id,time,x\n001,0,100\nNA,0,90\n")
            self.assertEqual(_common.read_relsa_table(path).id.tolist(), ["001", "NA"])

    def test_invalid_identity_time_and_measurements_fail(self):
        for replacement in ({"id": [None, "A"]}, {"time": [0, np.inf]},
                            {"x": [100, np.inf]}, {"x": ["bad", "90"]}):
            frame = pd.DataFrame({"id": ["A", "A"], "time": [0, 1], "x": [100, 90]})
            for key, value in replacement.items():
                frame[key] = value
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                _common.validate(frame, ["x"])

    def test_unknown_turn_and_invalid_reference_fail(self):
        frame = pd.DataFrame({"id": "A", "time": [0, 1], "x": [100., 80.]})
        with self.assertRaises(ValueError):
            relsa_score.build_reference(frame, ["x"], turned=["typo"])
        with self.assertRaises(ValueError):
            relsa_score.ReferenceModel(("x",), (), {"x": 80}, {"x": 0}, 1, 2)

    def test_score_mapping_rejects_outside_declared_scale(self):
        for values, maximum in (([0, 9], 8), ([0, np.inf], 8), ([0, 1], np.nan)):
            with self.assertRaises(ValueError):
                _common.score_to_percent(values, maximum)

    def test_metric_interval_validation_and_common_evaluation_set(self):
        for lo, hi in (([0], [1, 2]), ([2, 0], [1, 2]), (None, [1, 2])):
            with self.assertRaises(ValueError):
                _common.forecast_metrics([1, 1], [1, 1], lo, hi)
        got = _common.forecast_metrics([1, 1], [1, np.nan], [0, 0], [2, 100])
        self.assertEqual(got.mpiw, 2)
        self.assertEqual(got.picp, 100)

    def test_constant_kde_has_no_threshold_and_validates_options(self):
        from kde_thresholds import find_thresholds
        got = find_thresholds([0., 0., 0.])
        self.assertEqual(got.thresholds, [])
        self.assertTrue(np.isfinite(got.density).all())
        for options in ({"bandwidth": -1}, {"bandwidth": 0}, {"grid_size": 2},
                        {"n_thresholds": -1}, {"min_zone_fraction": 2}):
            with self.assertRaises(ValueError):
                find_thresholds([0., 1., 2.], **options)

    def test_forecast_rejects_off_grid_and_irregular_time(self):
        from forecast_relsa import forecast_animal, interpolate_series
        with self.assertRaisesRegex(ValueError, "align"):
            forecast_animal([0, 1, 2], [.1, .2, .4], target_times=[2.05])
        with self.assertRaisesRegex(ValueError, "uneven"):
            forecast_animal([0, 1, 3, 4], [.1, .2, .4, .5], target_times=[5], interpolate_step=None)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            forecast_animal([0, 0, 1], [.1, .2, .4], target_times=[2])
        with self.assertRaisesRegex(ValueError, "align"):
            interpolate_series([0, .25], [.1, .2], step=.1)

    def test_rolling_sorts_before_splitting_and_never_uses_future(self):
        from unittest.mock import patch
        import forecast_relsa as fr
        calls = []
        def fake(times, values, target_times, **kwargs):
            calls.append((list(times), target_times))
            fit = fr.ArimaFit((0, 0, 0), False, 0, 0, len(times))
            return fr.Forecast("A", fit, np.array(target_times), np.array([.5]), np.array([.1]), np.array([.9]))
        with patch.object(fr, "forecast_animal", side_effect=fake):
            fr.rolling_forecast([3, 0, 2, 1], [.4, .1, .3, .2], min_train=2)
        self.assertEqual(calls, [([0., 1.], [2.]), ([0., 1., 2.], [3.])])

    def test_cli_external_reference_maps_scores_and_reuses_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            data = work / "tiny.csv"
            data.write_text("id,time,weight,score\n001,0,23,0\n001,1,19,2\n001,2,17,4\n")
            def run(*args):
                result = subprocess.run([sys.executable, str(SCRIPTS / "relsa_score.py"),
                                         str(data), *args], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            options = ["--variables", "weight,score", "--normalize", "weight",
                       "--score-scale", "score=8", "--baseline-time", "0"]
            run(*options, "--out", str(work / "internal.csv"))
            run(*options, "--reference-data", str(data), "--out", str(work / "external.csv"),
                "--save-reference", str(work / "ref.json"))
            run("--load-reference", str(work / "ref.json"), "--out", str(work / "loaded.csv"))
            for file in ("external.csv", "loaded.csv"):
                pd.testing.assert_frame_equal(pd.read_csv(work / "internal.csv"), pd.read_csv(work / file))
            conflict = subprocess.run([sys.executable, str(SCRIPTS / "relsa_score.py"), str(data),
                                       "--load-reference", str(work / "ref.json"), "--normalize", "score"],
                                      capture_output=True, text=True)
            self.assertNotEqual(conflict.returncode, 0)
            self.assertIn("conflicts", conflict.stderr)


class ArimaSelectionRegressionTests(unittest.TestCase):
    def test_nonconverged_candidate_is_rejected_and_native_aicc_is_used(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from forecast_relsa import _fit_one
        for converged in (False, True):
            result = SimpleNamespace(aic=8., aicc=19., nobs=12,
                                     mle_retvals={"converged": converged})
            with patch("statsmodels.tsa.statespace.sarimax.SARIMAX") as model:
                model.return_value.fit.return_value = result
                fit = _fit_one(np.arange(12.), (1, 1, 0), False)
            if converged:
                self.assertEqual(fit.aicc, 19.)
            else:
                self.assertIsNone(fit)

    def test_second_differences_never_include_a_constant(self):
        from unittest.mock import patch
        import forecast_relsa as fr
        attempted = []
        def fit(series, order, drift):
            attempted.append(drift)
            return fr.ArimaFit(order, drift, sum(order), 0., len(series))
        with patch.object(fr, "_fit_one", side_effect=fit):
            fr.auto_arima(np.arange(12.), d=2)
        self.assertTrue(attempted)
        self.assertFalse(any(attempted))

    def test_interval_denominator_and_json_threshold_precision(self):
        from kde_thresholds import ThresholdResult
        metrics = _common.forecast_metrics([1., 2.], [1., 2.], [0., np.nan], [2., np.nan])
        self.assertEqual(metrics.n, 2)
        self.assertEqual(metrics.n_interval, 1)
        boundary = .123456789
        result = ThresholdResult([boundary], [], .1, 2, np.array([0., 1.]), np.ones(2))
        self.assertEqual(result.as_dict()["thresholds"], [boundary])
        self.assertEqual(result.as_dict()["zones"]["normal"]["high"], boundary)


if __name__ == "__main__":
    unittest.main()
