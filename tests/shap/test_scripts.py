"""Tests for the SHAP tabular report generator.

The report's one substantive claim is additivity: with an interventional
TreeExplainer in probability space, a row's base value plus its SHAP values must
reconstruct the model's predicted probability for that row. That identity is a
theorem about Shapley values, not a property of this code, which makes it the
right thing to assert -- and the script itself validates it, so the tests check
that the validation is real by verifying the reconstruction independently.

The rest guards the parts that silently produce a wrong report rather than
crashing: `select_output` picking the wrong class slice out of a
(samples, features, outputs) array, the CLI's numeric bounds accepting a zero
background, `save_axis` leaking figures, and the exported CSVs disagreeing with
the values they were built from.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pytest

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "shap"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

np = pytest.importorskip("numpy", reason="shap scripts need numpy")
pd = pytest.importorskip("pandas", reason="shap scripts need pandas")
shap = pytest.importorskip("shap", reason="shap scripts need shap")
pytest.importorskip("sklearn", reason="shap scripts need scikit-learn")
matplotlib = pytest.importorskip("matplotlib", reason="the report exports figures")
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from sklearn.datasets import load_breast_cancer  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402

import tabular_report  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

REPORT = SCRIPTS / "tabular_report.py"


class ArgumentBoundTests(unittest.TestCase):
    def test_a_positive_integer_is_accepted_and_zero_is_not(self) -> None:
        # --background-size 0 would build an empty background, which makes every
        # SHAP value meaningless rather than merely wrong.
        self.assertEqual(tabular_report.positive_int("3"), 3)
        for value in ("0", "-2"):
            with self.subTest(value=value):
                with self.assertRaises(argparse.ArgumentTypeError):
                    tabular_report.positive_int(value)

    def test_zero_is_a_valid_class_index_but_a_negative_one_is_not(self) -> None:
        self.assertEqual(tabular_report.nonnegative_int("0"), 0)
        with self.assertRaises(argparse.ArgumentTypeError):
            tabular_report.nonnegative_int("-1")

    def test_tolerances_must_be_strictly_positive(self) -> None:
        self.assertEqual(tabular_report.positive_float("1e-6"), 1e-6)
        for value in ("0", "-1e-6", "nan", "inf", "-inf"):
            with self.subTest(value=value):
                with self.assertRaises(argparse.ArgumentTypeError):
                    tabular_report.positive_float(value)


class SingleOutputStub:
    """Stands in for an Explanation whose values have the given shape."""

    def __init__(self, shape: tuple[int, ...]) -> None:
        self.values = np.zeros(shape)


class OutputSelectionTests(unittest.TestCase):
    def test_a_two_dimensional_explanation_is_returned_unchanged_for_class_zero(self) -> None:
        stub = SingleOutputStub((4, 3))
        self.assertIs(tabular_report.select_output(stub, 0), stub)

    def test_a_two_dimensional_explanation_rejects_any_other_class(self) -> None:
        with self.assertRaisesRegex(ValueError, "produced one output"):
            tabular_report.select_output(SingleOutputStub((4, 3)), 1)

    def test_an_unexpected_rank_names_the_shape_it_got(self) -> None:
        with self.assertRaisesRegex(ValueError, r"received \(4,\)"):
            tabular_report.select_output(SingleOutputStub((4,)), 0)
        with self.assertRaisesRegex(ValueError, r"received \(2, 3, 4, 5\)"):
            tabular_report.select_output(SingleOutputStub((2, 3, 4, 5)), 0)

    def test_a_class_index_past_the_last_output_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "outside 2 outputs"):
            tabular_report.select_output(SingleOutputStub((4, 3, 2)), 2)

    def test_negative_output_index_cannot_silently_select_last_class(self) -> None:
        with self.assertRaisesRegex(ValueError, "zero or greater"):
            tabular_report.select_output(SingleOutputStub((4, 3, 2)), -1)

    def test_output_names_fall_back_to_a_positional_label(self) -> None:
        explanation = shap.Explanation(
            values=np.zeros((2, 3)), base_values=np.zeros(2), output_names=None
        )
        self.assertEqual(tabular_report.output_name(explanation, 1), "class_1")

    def test_a_named_output_keeps_its_name(self) -> None:
        explanation = shap.Explanation(
            values=np.zeros((2, 3)), base_values=np.zeros(2), output_names="malignant"
        )
        self.assertEqual(tabular_report.output_name(explanation, 0), "malignant")


class ExplanationTests(unittest.TestCase):
    """One small interventional TreeExplainer, reused across the assertions."""

    @classmethod
    def setUpClass(cls) -> None:
        frame, target = load_breast_cancer(as_frame=True, return_X_y=True)
        cls.features = frame.iloc[:120, :6]
        cls.model = RandomForestClassifier(
            n_estimators=20, min_samples_leaf=3, random_state=0
        ).fit(cls.features, target.iloc[:120])
        background = shap.sample(cls.features, 20, random_state=0)
        explainer = shap.TreeExplainer(
            cls.model,
            data=background,
            feature_perturbation="interventional",
            model_output="probability",
        )
        cls.explained = cls.features.iloc[:10]
        cls.all_outputs = explainer(cls.explained)

    def test_the_explainer_produces_one_slice_per_class(self) -> None:
        self.assertEqual(
            np.shape(self.all_outputs.values), (10, 6, len(self.model.classes_))
        )

    def test_selecting_a_class_takes_that_slice_and_no_other(self) -> None:
        for class_index in range(len(self.model.classes_)):
            with self.subTest(class_index=class_index):
                selected = tabular_report.select_output(self.all_outputs, class_index)
                np.testing.assert_allclose(
                    np.asarray(selected.values),
                    np.asarray(self.all_outputs.values)[:, :, class_index],
                )
                self.assertEqual(np.shape(selected.base_values), (10,))

    def test_shap_values_reconstruct_the_predicted_probability(self) -> None:
        # The defining property: base value + contributions = model output. The
        # script asserts this with np.testing.assert_allclose; here the target
        # is recomputed from predict_proba so the check is independent.
        for class_index in range(len(self.model.classes_)):
            with self.subTest(class_index=class_index):
                selected = tabular_report.select_output(self.all_outputs, class_index)
                reconstructed = np.asarray(selected.base_values, dtype=float) + np.asarray(
                    selected.values, dtype=float
                ).sum(axis=1)
                predicted = self.model.predict_proba(self.explained)[:, class_index]
                np.testing.assert_allclose(reconstructed, predicted, rtol=1e-5, atol=1e-6)

    def test_the_two_class_slices_are_mirror_images(self) -> None:
        # Binary probabilities sum to one, so each feature's contribution to
        # class 1 must be the negative of its contribution to class 0.
        values = np.asarray(self.all_outputs.values, dtype=float)
        np.testing.assert_allclose(values[:, :, 0], -values[:, :, 1], atol=1e-9)

    def test_the_base_value_is_the_background_mean_prediction(self) -> None:
        # With an interventional masker the base value is the model's average
        # output over the background sample, and it is identical for every row.
        selected = tabular_report.select_output(self.all_outputs, 1)
        base_values = np.asarray(selected.base_values, dtype=float)
        np.testing.assert_allclose(base_values, base_values[0])
        background = shap.sample(self.features, 20, random_state=0)
        self.assertAlmostEqual(
            float(base_values[0]),
            float(self.model.predict_proba(background)[:, 1].mean()),
            places=5,
        )


class FigureExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.addCleanup(plt.close, "all")

    def test_saving_an_axis_writes_a_file_and_leaves_no_open_figure(self) -> None:
        # A report that exports four figures without closing them exhausts
        # matplotlib's figure warning threshold and leaks memory.
        figure, axis = plt.subplots()
        axis.plot([0, 1], [0, 1])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "figure.png"
            tabular_report.save_axis(axis, path)
            self.assertGreater(path.stat().st_size, 0)
        self.assertEqual(plt.get_fignums(), [])

    def test_a_missing_axis_falls_back_to_the_current_figure(self) -> None:
        # Some shap.plots helpers return None and draw into gcf().
        plt.figure()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "current.png"
            tabular_report.save_axis(None, path)
            self.assertGreater(path.stat().st_size, 0)
        self.assertEqual(plt.get_fignums(), [])


class ReportRunTests(unittest.TestCase):
    """One end-to-end CLI run, shared by the assertions about its output."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._directory = tempfile.TemporaryDirectory()
        cls.output = Path(cls._directory.name) / "report"
        completed = subprocess.run(
            [
                sys.executable, str(REPORT),
                "--output-dir", str(cls.output),
                "--background-size", "150",
                "--explain-size", "12",
                "--max-display", "5",
                "--seed", "7",
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if completed.returncode != 0:
            raise AssertionError(
                f"tabular_report.py exited {completed.returncode}:\n{completed.stderr}"
            )
        cls.stdout = completed.stdout
        cls.metadata = json.loads((cls.output / "metadata.json").read_text())

    @classmethod
    def tearDownClass(cls) -> None:
        cls._directory.cleanup()

    def test_every_documented_artefact_is_written(self) -> None:
        expected = {
            "bar.png",
            "beeswarm.png",
            "feature_importance.csv",
            "first_row_contributions.csv",
            "metadata.json",
            "prediction_reconstruction.csv",
            "scatter-top-feature.png",
            "waterfall-first-row.png",
        }
        self.assertEqual({path.name for path in self.output.iterdir()}, expected)
        for path in self.output.iterdir():
            with self.subTest(artefact=path.name):
                self.assertGreater(path.stat().st_size, 0)

    def test_the_metadata_records_the_run_it_actually_did(self) -> None:
        self.assertEqual(self.metadata["seed"], 7)
        self.assertEqual(self.metadata["background_rows"], 150)
        self.assertEqual(self.metadata["background_requested_rows"], 150)
        self.assertEqual(self.metadata["explained_rows"], 12)
        # Breast cancer ships 30 features and 2 classes.
        self.assertEqual(self.metadata["feature_count"], 30)
        self.assertEqual(self.metadata["all_output_shape"], [12, 30, 2])
        self.assertEqual(self.metadata["selected_output_shape"], [12, 30])
        self.assertEqual(self.metadata["output_units"], "class probability")
        self.assertEqual(self.metadata["feature_perturbation"], "interventional")
        self.assertEqual(self.metadata["selected_class_meaning"], "benign")
        self.assertEqual(self.metadata["selected_output_name"], "benign")

    def test_the_additivity_error_is_inside_the_tolerance_it_reports(self) -> None:
        self.assertLess(
            self.metadata["max_abs_additivity_error"],
            self.metadata["additivity_atol"] + self.metadata["additivity_rtol"],
        )

    def test_the_reconstruction_csv_adds_up_row_by_row(self) -> None:
        frame = pd.read_csv(self.output / "prediction_reconstruction.csv")
        self.assertEqual(len(frame), 12)
        np.testing.assert_allclose(
            frame["reconstructed_output"], frame["prediction"], atol=1e-6
        )
        np.testing.assert_allclose(
            frame["reconstruction_error"],
            frame["reconstructed_output"] - frame["prediction"],
            atol=1e-12,
        )
        # Probability-space output: every prediction is a probability.
        self.assertTrue(((frame["prediction"] >= 0) & (frame["prediction"] <= 1)).all())
        np.testing.assert_allclose(
            frame["base_value"], self.metadata["background_mean_prediction"], atol=1e-6
        )

    def test_the_importance_table_is_ranked_by_mean_absolute_shap(self) -> None:
        frame = pd.read_csv(self.output / "feature_importance.csv")
        self.assertEqual(len(frame), 30)
        self.assertTrue(frame["mean_abs_shap"].is_monotonic_decreasing)
        self.assertTrue((frame["mean_abs_shap"] >= 0).all())
        # The signed mean can never exceed the absolute mean in magnitude.
        self.assertTrue((frame["mean_signed_shap"].abs() <= frame["mean_abs_shap"] + 1e-12).all())
        self.assertEqual(frame.loc[0, "feature"], self.metadata["top_feature"])

    def test_the_first_row_breakdown_is_ordered_by_contribution_size(self) -> None:
        frame = pd.read_csv(self.output / "first_row_contributions.csv")
        self.assertEqual(len(frame), 30)
        self.assertTrue(frame["shap_value"].abs().is_monotonic_decreasing)
        # Those contributions are the ones that reconstruct row 0's prediction.
        reconstruction = pd.read_csv(self.output / "prediction_reconstruction.csv")
        self.assertAlmostEqual(
            float(reconstruction.loc[0, "base_value"] + frame["shap_value"].sum()),
            float(reconstruction.loc[0, "prediction"]),
            places=5,
        )

    def test_the_run_prints_its_metadata_and_where_it_wrote(self) -> None:
        self.assertIn("shap_version", self.stdout)
        self.assertIn(str(self.output.resolve()), self.stdout)


class ReportFailureTests(unittest.TestCase):
    def test_a_class_index_outside_the_model_is_rejected_before_any_work(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            completed = subprocess.run(
                [
                    sys.executable, str(REPORT),
                    "--output-dir", directory,
                    "--class-index", "7",
                    "--background-size", "5",
                    "--explain-size", "5",
                ],
                capture_output=True,
                text=True,
                timeout=600,
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("--class-index 7 is outside model classes", completed.stderr)

    def test_an_upstream_additivity_failure_prevents_report_artifacts(self) -> None:
        # This frozen 0.52.0 breast-cancer configuration encounters a native
        # split-threshold discrepancy. The report must reject it, not export
        # an apparently successful decomposition by loosening tolerances.
        with tempfile.TemporaryDirectory() as directory:
            completed = subprocess.run(
                [sys.executable, str(REPORT), "--output-dir", directory,
                 "--seed", "3", "--background-size", "150", "--explain-size", "2"],
                capture_output=True, text=True, timeout=120,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("Not equal to tolerance", completed.stderr)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_a_negative_background_size_is_refused_by_the_parser(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(REPORT), "--background-size", "-1"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("greater than zero", completed.stderr)


if __name__ == "__main__":
    unittest.main()
