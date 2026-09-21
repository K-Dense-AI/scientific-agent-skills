"""Tests for the sentinel2-parcel-timeseries scripts.

Two kinds of error matter here, and neither raises on its own. On the data
side, a wrong reflectance offset or a cloud pixel counted as clear still gives
plausible-looking numbers, so the assertions check exact values on small
synthetic rasters. On the validation side, a protocol that lets a parcel into
both train and test still returns an AUC, so the assertions check the
properties the protocol promises: parcels never shared between folds, scores
aggregated per parcel, and a leaky pixel split visibly inflated on a signal-free
data set.

No test touches the network: the STAC search and loading are exercised by
hand, as documented in SKILL.md.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import pytest

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "sentinel2-parcel-timeseries"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

np = pytest.importorskip("numpy", reason="sentinel2-parcel-timeseries needs numpy")

import s2_parcel_timeseries as s2  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)


def cv():
    """Import the validation module, skipping when scikit-learn is absent."""
    pytest.importorskip("sklearn", reason="parcel_group_cv needs scikit-learn")
    import parcel_group_cv

    return parcel_group_cv


def item(tile: str, day: str, cloud: float = 10.0) -> SimpleNamespace:
    return SimpleNamespace(properties={"s2:mgrs_tile": tile, "datetime": f"{day}T11:00:00Z",
                                       "eo:cloud_cover": cloud})


class ReflectanceTests(unittest.TestCase):
    def test_offset_applies_from_baseline_04_00(self) -> None:
        self.assertEqual(s2.baseline_offset("04.00"), 1000.0)
        self.assertEqual(s2.baseline_offset("05.10"), 1000.0)
        self.assertEqual(s2.baseline_offset("03.01"), 0.0)
        self.assertEqual(s2.baseline_offset("02.14"), 0.0)

    def test_same_reflectance_either_side_of_the_baseline_change(self) -> None:
        # 0.05 reflectance is DN 1500 after the change and DN 500 before it.
        after = s2.to_reflectance(np.array([1500.0]), "05.10")
        before = s2.to_reflectance(np.array([500.0]), "03.00")
        np.testing.assert_allclose(after, [0.05])
        np.testing.assert_allclose(before, [0.05])

    def test_zero_and_nan_are_no_data(self) -> None:
        out = s2.to_reflectance(np.array([0.0, np.nan, 3000.0]), "05.10")
        self.assertTrue(np.isnan(out[0]) and np.isnan(out[1]))
        self.assertAlmostEqual(out[2], 0.2)

    def test_values_below_the_offset_clip_to_zero(self) -> None:
        self.assertEqual(s2.to_reflectance(np.array([900.0]), "05.10")[0], 0.0)

    def test_unknown_baseline_is_refused_not_guessed(self) -> None:
        for baseline in (None, ""):
            with self.subTest(baseline=baseline):
                with self.assertRaisesRegex(ValueError, "baseline unknown"):
                    s2.to_reflectance(np.array([1500.0]), baseline)

    def test_ndvi_on_offset_dn_would_be_biased(self) -> None:
        # The documented example: red 0.05, NIR 0.30 is NDVI 0.714, but 0.455 on raw DN.
        good = s2.ndvi(s2.to_reflectance(np.array([1500.0]), "05.10"),
                       s2.to_reflectance(np.array([4000.0]), "05.10"))
        raw = s2.ndvi(np.array([1500.0]), np.array([4000.0]))
        self.assertAlmostEqual(good[0], 0.25 / 0.35)
        self.assertAlmostEqual(raw[0], 2500 / 5500)

    def test_ndvi_zero_denominator_is_nan(self) -> None:
        self.assertTrue(np.isnan(s2.ndvi(np.array([0.0]), np.array([0.0]))[0]))


class MaskTests(unittest.TestCase):
    def test_only_vegetation_and_bare_soil_are_clear(self) -> None:
        scl = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, np.nan])
        clear = s2.clear_mask(scl)
        self.assertEqual(scl[clear].tolist(), [4.0, 5.0])

    def test_classes_can_be_widened(self) -> None:
        self.assertTrue(s2.clear_mask(np.array([7.0]), classes=(4, 5, 7))[0])


class ItemSelectionTests(unittest.TestCase):
    def test_most_frequent_tile_is_kept(self) -> None:
        items = [item("30STD", "2024-06-01"), item("30STD", "2024-06-06"),
                 item("29SQU", "2024-06-01")]
        tile, kept = s2.choose_tile(items)
        self.assertEqual(tile, "30STD")
        self.assertEqual(len(kept), 2)

    def test_ties_are_broken_alphabetically(self) -> None:
        items = [item("30STD", "2024-06-01"), item("29SQU", "2024-06-01")]
        self.assertEqual(s2.choose_tile(items)[0], "29SQU")

    def test_forced_tile_must_exist(self) -> None:
        with self.assertRaisesRegex(ValueError, "not found"):
            s2.choose_tile([item("30STD", "2024-06-01")], tile="31ABC")

    def test_one_item_per_day_keeps_the_clearest(self) -> None:
        items = [item("30STD", "2024-06-06", 40.0), item("30STD", "2024-06-01", 5.0),
                 item("30STD", "2024-06-06", 2.0)]
        kept = s2.one_item_per_date(items)
        self.assertEqual([k.properties["datetime"][:10] for k in kept], ["2024-06-01", "2024-06-06"])
        self.assertEqual(kept[1].properties["eo:cloud_cover"], 2.0)


class ParcelStatsTests(unittest.TestCase):
    """Two parcels on a 4 x 4 grid, two dates; parcel B is cloudy on the second date."""

    def setUp(self) -> None:
        self.labels = np.array([[1, 1, 0, 2],
                                [1, 1, 0, 2],
                                [0, 0, 0, 2],
                                [0, 0, 0, 2]])
        red = np.full((2, 4, 4), 0.05)
        nir = np.full((2, 4, 4), 0.30)
        nir[0, 0, 0] = 0.50                      # one brighter pixel in parcel A, date 1
        self.reflectance = {"B04": red, "B08": nir}
        self.scl = np.full((2, 4, 4), 4.0)
        self.scl[1, :3, 3] = 9.0                 # 3 of B's 4 pixels cloudy on date 2
        self.scl[0, 1, 1] = 8.0                  # one cloudy pixel in A on date 1

    def rows(self, **kwargs):
        return s2.parcel_stats(self.labels, ["A", "B"], self.reflectance, self.scl,
                               ["2024-06-01", "2024-06-06"], **kwargs)

    def test_cloudy_parcel_date_is_dropped(self) -> None:
        kept = {(r["parcel_id"], r["date"]) for r in self.rows()}
        self.assertEqual(kept, {("A", "2024-06-01"), ("B", "2024-06-01"),
                                ("A", "2024-06-06")})

    def test_threshold_controls_the_drop(self) -> None:
        kept = {(r["parcel_id"], r["date"]) for r in self.rows(min_clear=0.25)}
        self.assertIn(("B", "2024-06-06"), kept)

    def test_statistics_use_clear_pixels_only(self) -> None:
        row = next(r for r in self.rows() if r["parcel_id"] == "A" and r["date"] == "2024-06-01")
        self.assertEqual((row["n_pixels"], row["n_clear"]), (4, 3))
        self.assertAlmostEqual(row["clear_fraction"], 0.75)
        # clear pixels: NIR 0.50, 0.30, 0.30 (the cloudy 0.30 pixel is excluded)
        self.assertAlmostEqual(row["B08_mean"], (0.50 + 0.30 + 0.30) / 3)
        expected = np.mean([(0.50 - 0.05) / 0.55, 0.25 / 0.35, 0.25 / 0.35])
        self.assertAlmostEqual(row["ndvi_mean"], expected)

    def test_parcel_without_pixels_yields_no_rows(self) -> None:
        rows = s2.parcel_stats(self.labels, ["A", "B", "C"], self.reflectance, self.scl,
                               ["2024-06-01", "2024-06-06"])
        self.assertNotIn("C", {r["parcel_id"] for r in rows})


class ParcelValidationTests(unittest.TestCase):
    def test_parcel_scores_are_pixel_means(self) -> None:
        m = cv()
        names, score, label = m.parcel_table(np.array([0.2, 0.4, 0.9, 0.7]),
                                             np.array([0, 0, 1, 1]),
                                             np.array(["a", "a", "b", "b"]))
        self.assertEqual(names.tolist(), ["a", "b"])
        np.testing.assert_allclose(score, [0.3, 0.8])
        self.assertEqual(label.tolist(), [0, 1])

    def test_mixed_labels_in_a_parcel_are_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "several labels"):
            cv().parcel_table(np.zeros(2), np.array([0, 1]), np.array(["a", "a"]))

    def test_parcel_auc_differs_from_pixel_auc(self) -> None:
        m = cv()
        # parcel a (label 0) has one very high pixel; per parcel it is still below b and c
        prob = np.array([0.1, 0.1, 0.95, 0.6, 0.6, 0.7, 0.7])
        y = np.array([0, 0, 0, 1, 1, 1, 1])
        groups = np.array(["a", "a", "a", "b", "b", "c", "c"])
        from sklearn.metrics import roc_auc_score

        self.assertLess(roc_auc_score(y, prob), 1.0)
        self.assertEqual(m.parcel_auc(prob, y, groups), 1.0)

    def test_no_parcel_is_in_train_and_test(self) -> None:
        m = cv()
        X, y, groups = m.synthetic_parcels(n_parcels=6, pixels=5, seed=1)
        seen = []

        def spy(X_train, y_train, X_test):
            seen.append(len(X_test))
            return np.full(len(X_test), 0.5)

        prob = m.leave_one_parcel_out(X, y, groups, spy)
        self.assertEqual(seen, [5] * 6)          # one fold per parcel, whole parcel held out
        self.assertFalse(np.isnan(prob).any())

    def test_leaky_split_is_inflated_on_signal_free_parcels(self) -> None:
        m = cv()
        X, y, groups = m.synthetic_parcels(n_parcels=12, pixels=20, seed=0)
        model = m.make_model("logistic")
        honest = m.parcel_auc(m.leave_one_parcel_out(X, y, groups, model), y, groups)
        leaky = m.parcel_auc(m.random_pixel_cv(X, y, model), y, groups)
        self.assertGreater(leaky, 0.9)
        self.assertLess(honest, 0.75)

    def test_real_signal_is_found_by_the_honest_protocol(self) -> None:
        m = cv()
        X, y, groups = m.synthetic_parcels(n_parcels=12, pixels=20, seed=0)
        X = X.copy()
        X[:, 0] += 3.0 * y                        # label now shifts one feature
        model = m.make_model("logistic")
        self.assertGreater(m.parcel_auc(m.leave_one_parcel_out(X, y, groups, model), y, groups), 0.9)

    def test_permutation_p_value_is_a_probability(self) -> None:
        m = cv()
        X, y, groups = m.synthetic_parcels(n_parcels=8, pixels=5, seed=2)
        p, null = m.permutation_pvalue(X, y, groups, m.make_model("logistic"), observed=0.99,
                                       n_permutations=5, seed=0)
        self.assertEqual(len(null), 5)
        self.assertTrue(1 / 6 <= p <= 1.0)

    def test_permutations_keep_labels_constant_within_parcels(self) -> None:
        m = cv()
        X, y, groups = m.synthetic_parcels(n_parcels=6, pixels=4, seed=3)

        def check(X_train, y_train, X_test):
            return np.full(len(X_test), 0.5)

        # parcel_auc inside permutation_pvalue raises if a permuted parcel has mixed labels
        m.permutation_pvalue(X, y, groups, check, observed=0.5, n_permutations=3)

    def test_one_parcel_per_class_is_refused(self) -> None:
        m = cv()
        X = np.random.default_rng(0).normal(size=(6, 2))
        y = np.array([0, 0, 0, 1, 1, 1])
        groups = np.array(["a", "a", "a", "b", "b", "b"])
        with self.assertRaises(SystemExit):
            m.report(X, y, groups, "logistic", 0, False, 0)

    def test_feature_regex_selects_columns(self) -> None:
        m = cv()
        pd = pytest.importorskip("pandas")
        import tempfile

        table = pd.DataFrame({"parcel_id": ["a", "a", "b", "b"], "label": [0, 0, 1, 1],
                              "ndvi_m04": [0.1, np.nan, 0.3, 0.4], "ndvi_m07": [0.5, 0.6, 0.7, 0.8],
                              "note": ["x", "y", "z", "w"]})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pixels.csv"
            table.to_csv(path, index=False)
            X, y, groups, used = m.load_csv(str(path), "parcel_id", "label", "_m04$")
        self.assertEqual(used, ["ndvi_m04"])
        self.assertFalse(np.isnan(X).any())      # missing value filled
        self.assertEqual(groups.tolist(), ["a", "a", "b", "b"])


if __name__ == "__main__":
    unittest.main()
