"""Unit tests for the analytical-method-validation skill scripts.

Everything runs offline; the scripts make no network calls. The statistical
implementations are checked against published quantiles and hand-checkable
cases, because the whole value of the skill rests on them being right.

    uv run --with pytest python -m pytest tests/analytical-method-validation -q
"""

from __future__ import annotations

import importlib.util
import json
import math
import subprocess
import sys
import unittest
from pathlib import Path

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "analytical-method-validation"
SCRIPTS_DIR = SKILL_ROOT / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load_script(name: str):
    """Load a bundled script as a module regardless of cwd."""
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


common = _load_script("_common")
catalog = _load_script("_catalog")


def run_script(name: str, *args: str) -> subprocess.CompletedProcess:
    """Invoke a script as a subprocess and capture its streams."""
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / f"{name}.py"), *args],
        capture_output=True,
        text=True,
        check=False,
    )


# ---------------------------------------------------------------- structure


class TestSkillStructure(unittest.TestCase):
    def test_skill_md_frontmatter(self):
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        end = text.index("\n---\n", 4)
        front = text[4:end]
        self.assertIn("name: analytical-method-validation", front)
        self.assertRegex(front, r'\n  version: "\d+\.\d+"\n')
        # allowed-tools must be a space-separated string, not a YAML list
        for line in front.splitlines():
            if line.startswith("allowed-tools:"):
                self.assertNotIn(",", line)
                self.assertNotIn("[", line)

    def test_skill_md_under_500_lines(self):
        lines = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8").splitlines()
        self.assertLess(len(lines), 500, f"SKILL.md has {len(lines)} lines")

    def test_referenced_files_exist(self):
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for rel in ("references/framework-selection.md", "references/ich-q2r2.md",
                    "references/ich-m10-bioanalytical.md", "references/compendial-and-clsi.md",
                    "references/statistics.md", "references/source-ledger.md",
                    "assets/validation-protocol-template.md",
                    "assets/validation-report-template.md"):
            self.assertIn(rel, text, f"{rel} not referenced from SKILL.md")
            self.assertTrue((SKILL_ROOT / rel).is_file(), f"{rel} missing")

    def test_no_bytecode_shipped(self):
        self.assertEqual(list(SKILL_ROOT.rglob("*.pyc")), [])
        self.assertEqual(list(SKILL_ROOT.rglob("__pycache__")), [])

    def test_no_tests_inside_skill(self):
        self.assertEqual(list(SKILL_ROOT.rglob("test_*.py")), [])

    def test_no_techniques_attributed_to_q2r2_that_it_never_mentions(self):
        """Guard against secondary-source claims leaking in as primary-source facts.

        Trade summaries of the Q2(R1) -> Q2(R2) revision commonly list Raman
        spectroscopy. The adopted guideline text does not contain the word, so the
        skill must not attribute it to Q2(R2).
        """
        for path in SKILL_ROOT.rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("Raman", text, f"{path.name} attributes Raman to ICH guidance")

    def test_paywalled_standards_are_not_quoted_with_numbers(self):
        """USP/CLSI/ISO content must be referenced, never reproduced.

        A numeric threshold sitting next to a paywalled designation is the shape of
        an accidental reproduction, so the reference file states scope only.
        """
        text = (SKILL_ROOT / "references" / "compendial-and-clsi.md").read_text(encoding="utf-8")
        self.assertIn("does not reproduce", text)
        for banned in ("tailing factor limit", "%RSD limit of", "must not exceed 2.0"):
            self.assertNotIn(banned, text)


# ---------------------------------------------------------------- distributions


class TestDistributions(unittest.TestCase):
    def test_t_quantiles(self):
        for p, df, want in [
            (0.975, 1, 12.706205),
            (0.975, 5, 2.570582),
            (0.975, 9, 2.262157),
            (0.95, 10, 1.812461),
            (0.995, 20, 2.845340),
            (0.975, 100, 1.983972),
        ]:
            self.assertAlmostEqual(common.t_ppf(p, df), want, places=4)

    def test_t_cdf_symmetry(self):
        self.assertAlmostEqual(common.t_cdf(0.0, 7), 0.5, places=10)
        self.assertAlmostEqual(
            common.t_cdf(-1.3, 12) + common.t_cdf(1.3, 12), 1.0, places=10
        )

    def test_chi2_quantiles(self):
        for p, df, want in [
            (0.025, 9, 2.700389),
            (0.975, 9, 19.022768),
            (0.95, 1, 3.841459),
            (0.05, 20, 10.850811),
            (0.5, 4, 3.356694),
        ]:
            self.assertAlmostEqual(common.chi2_ppf(p, df), want, places=3)

    def test_f_distribution(self):
        # F(1,1) upper 5% point is 161.4476
        self.assertAlmostEqual(common.f_sf(161.4476, 1, 1), 0.05, places=5)
        # median-ish symmetry check
        self.assertAlmostEqual(common.f_sf(1.0, 5, 5), 0.5, places=6)
        self.assertAlmostEqual(common.f_sf(4.0, 2, 10), 0.052922, places=5)
        self.assertAlmostEqual(common.f_sf(0.0, 3, 5), 1.0, places=12)

    def test_f_sf_does_not_underflow_to_zero(self):
        """A validation report must not print a lack-of-fit p-value of exactly 0.

        Computing 1 - cdf underflows well before the true tail probability does.
        """
        for f, df1, df2 in [(1e8, 3, 5), (1e3, 1, 200), (1e6, 10, 100)]:
            tail = common.f_sf(f, df1, df2)
            self.assertGreater(tail, 0.0, f"F={f} df=({df1},{df2}) underflowed")
            self.assertLess(tail, 1e-15)
        # And it still agrees with 1 - cdf where that is accurate.
        for f, df1, df2 in [(4.0, 2, 10), (2.5, 3, 12), (1.0, 5, 5)]:
            self.assertAlmostEqual(
                common.f_sf(f, df1, df2), 1.0 - common.f_cdf(f, df1, df2), places=12
            )

    def test_betainc_edges(self):
        self.assertEqual(common.betainc(2.0, 3.0, 0.0), 0.0)
        self.assertEqual(common.betainc(2.0, 3.0, 1.0), 1.0)
        # I_x(a,b) + I_(1-x)(b,a) == 1
        self.assertAlmostEqual(
            common.betainc(2.5, 4.5, 0.3) + common.betainc(4.5, 2.5, 0.7), 1.0, places=12
        )

    def test_bad_probabilities_raise(self):
        with self.assertRaises(common.InputError):
            common.t_ppf(0.0, 5)
        with self.assertRaises(common.InputError):
            common.chi2_ppf(1.0, 5)


# ---------------------------------------------------------------- regression


class TestRegression(unittest.TestCase):
    def test_exact_line(self):
        fit = common.fit_linear([1, 2, 3, 4], [3, 5, 7, 9])
        self.assertAlmostEqual(fit.slope, 2.0, places=12)
        self.assertAlmostEqual(fit.intercept, 1.0, places=12)
        self.assertAlmostEqual(fit.r_squared, 1.0, places=12)
        self.assertAlmostEqual(fit.residual_sd, 0.0, places=10)

    def test_known_least_squares(self):
        fit = common.fit_linear([1, 2, 3, 4, 5], [2.1, 4.0, 6.2, 7.9, 10.1])
        self.assertAlmostEqual(fit.slope, 1.99, places=10)
        self.assertAlmostEqual(fit.intercept, 0.09, places=10)
        lo, hi = fit.slope_ci()
        self.assertLess(lo, 1.99)
        self.assertGreater(hi, 1.99)

    def test_weighting_changes_the_fit(self):
        xs = [1, 2, 5, 10, 20]
        ys = [1.0, 2.1, 5.2, 9.5, 21.0]
        unweighted = common.fit_linear(xs, ys)
        weighted = common.fit_linear(xs, ys, [1.0 / (x * x) for x in xs])
        self.assertNotAlmostEqual(unweighted.slope, weighted.slope, places=6)

    def test_too_few_points(self):
        with self.assertRaises(common.InputError):
            common.fit_linear([1, 2], [1, 2])

    def test_collinear_x_raises(self):
        with self.assertRaises(common.InputError):
            common.fit_linear([3, 3, 3], [1, 2, 3])

    def test_lack_of_fit_detects_curvature(self):
        xs = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]
        quad = [x * x for x in xs]
        ys = [q + (0.05 if i % 2 else -0.05) for i, q in enumerate(quad)]
        lof = common.lack_of_fit(xs, ys, common.fit_linear(xs, ys))
        self.assertTrue(lof["applicable"])
        self.assertLess(lof["p_value"], 0.001)

    def test_lack_of_fit_passes_linear_data(self):
        xs = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]
        ys = [2 * x + (0.02 if i % 2 else -0.02) for i, x in enumerate(xs)]
        lof = common.lack_of_fit(xs, ys, common.fit_linear(xs, ys))
        self.assertTrue(lof["applicable"])
        self.assertGreater(lof["p_value"], 0.05)

    def test_lack_of_fit_needs_replicates(self):
        xs = [1, 2, 3, 4, 5]
        ys = [2, 4, 6, 8, 10.1]
        lof = common.lack_of_fit(xs, ys, common.fit_linear(xs, ys))
        self.assertFalse(lof["applicable"])
        self.assertIn("replicates", lof["reason"])

    def test_runs_test_flags_curvature(self):
        xs = list(range(1, 13))
        ys = [x * x for x in xs]
        runs = common.runs_test(common.fit_linear(xs, ys).residuals)
        self.assertLess(runs["p_value"], 0.05)

    def test_runs_test_small_sample_is_honest(self):
        runs = common.runs_test([1.0, -1.0, 1.0])
        self.assertTrue(math.isnan(runs["p_value"]))
        self.assertIn("too few", runs["note"])

    def test_heteroscedasticity_ratio(self):
        xs = list(range(1, 13))
        resid = [0.01 * (1 if i % 2 else -1) for i in range(6)] + [
            1.0 * (1 if i % 2 else -1) for i in range(6)
        ]
        het = common.heteroscedasticity(xs, resid)
        self.assertTrue(het["applicable"])
        self.assertGreater(het["variance_ratio_high_over_low"], 100)


# ---------------------------------------------------------------- precision


class TestVarianceComponents(unittest.TestCase):
    def test_balanced_hand_check(self):
        groups = {"d1": [10.0, 10.2, 9.8], "d2": [10.5, 10.6, 10.4], "d3": [9.6, 9.5, 9.7]}
        comp = common.one_way_components(groups)
        self.assertEqual(comp.n_total, 9)
        self.assertEqual(comp.n_groups, 3)
        self.assertTrue(comp.balanced)
        self.assertAlmostEqual(comp.n_effective, 3.0, places=12)
        self.assertAlmostEqual(comp.ms_within, 0.02, places=12)
        self.assertAlmostEqual(comp.ms_between, 0.61, places=12)
        # s2_between = (0.61 - 0.02)/3
        self.assertAlmostEqual(comp.sd_between ** 2, (0.61 - 0.02) / 3.0, places=12)
        self.assertAlmostEqual(
            comp.sd_intermediate ** 2, 0.02 + (0.61 - 0.02) / 3.0, places=12
        )
        self.assertGreater(comp.sd_intermediate, comp.sd_repeatability)

    def test_between_variance_truncated_at_zero(self):
        # Groups deliberately indistinguishable: MS_between < MS_within
        groups = {"a": [1.0, 3.0, 2.0], "b": [2.0, 1.0, 3.0], "c": [3.0, 2.0, 1.0]}
        comp = common.one_way_components(groups)
        self.assertEqual(comp.sd_between, 0.0)
        self.assertAlmostEqual(comp.sd_intermediate, comp.sd_repeatability, places=12)

    def test_unbalanced_effective_n(self):
        groups = {"a": [1.0, 1.1, 0.9, 1.05], "b": [2.0, 2.1], "c": [3.0, 3.1, 2.9]}
        comp = common.one_way_components(groups)
        self.assertFalse(comp.balanced)
        self.assertGreater(comp.n_effective, 1.0)
        self.assertLess(comp.n_effective, 4.0)

    def test_needs_two_groups(self):
        with self.assertRaises(common.InputError):
            common.one_way_components({"only": [1.0, 2.0, 3.0]})

    def test_sd_confidence_interval_brackets(self):
        lo, hi = common.sd_confidence_interval(1.0, 9, 0.90)
        self.assertLess(lo, 1.0)
        self.assertGreater(hi, 1.0)
        # chi2 interval for sd=1, df=9 at 90%
        self.assertAlmostEqual(lo, math.sqrt(9 / common.chi2_ppf(0.95, 9)), places=10)


# ---------------------------------------------------------------- comparison


class TestMethodComparison(unittest.TestCase):
    def test_deming_recovers_unit_slope(self):
        xs = list(range(1, 21))
        ys = [x + (0.05 if i % 2 else -0.05) for i, x in enumerate(xs)]
        res = common.deming(xs, ys, 1.0)
        self.assertAlmostEqual(res["slope"], 1.0, places=2)
        self.assertAlmostEqual(res["intercept"], 0.0, places=1)

    def test_deming_lambda_affects_slope(self):
        xs = [1, 2, 3, 4, 5, 6, 7, 8]
        ys = [1.2, 1.9, 3.4, 3.8, 5.5, 5.9, 7.6, 7.9]
        a = common.deming(xs, ys, 1.0)["slope"]
        b = common.deming(xs, ys, 4.0)["slope"]
        self.assertNotAlmostEqual(a, b, places=6)

    def test_deming_lambda_direction_matches_documentation(self):
        """lambda = var(y error)/var(x error), pinned by the unambiguous limits.

        Large lambda means x is effectively error-free, so the fit must converge
        on the OLS slope of y on x. Small lambda means y is error-free, so it must
        converge on the inverse regression. Documenting this backwards would send
        a user with unequal precision in exactly the wrong direction.
        """
        xs = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        ys = [1.2, 1.9, 3.4, 3.8, 5.5, 5.9, 7.6, 7.9, 9.3, 10.4]
        xb, yb = common.mean(xs), common.mean(ys)
        sxx = math.fsum((x - xb) ** 2 for x in xs)
        syy = math.fsum((y - yb) ** 2 for y in ys)
        sxy = math.fsum((x - xb) * (y - yb) for x, y in zip(xs, ys))
        ols_y_on_x = sxy / sxx
        inverse = syy / sxy
        self.assertAlmostEqual(common.deming(xs, ys, 1e9)["slope"], ols_y_on_x, places=6)
        self.assertAlmostEqual(common.deming(xs, ys, 1e-9)["slope"], inverse, places=6)
        # lambda = 1 is orthogonal regression, between the two.
        orth = common.deming(xs, ys, 1.0)["slope"]
        self.assertLess(ols_y_on_x, orth)
        self.assertLess(orth, inverse)

    def test_deming_rejects_bad_lambda(self):
        with self.assertRaises(common.InputError):
            common.deming([1, 2, 3], [1, 2, 3], 0.0)

    def test_passing_bablok_exact_line(self):
        xs = [1, 2, 3, 4, 5, 6, 7]
        ys = [2 * x + 1 for x in xs]
        res = common.passing_bablok(xs, ys)
        self.assertAlmostEqual(res["slope"], 2.0, places=10)
        self.assertAlmostEqual(res["intercept"], 1.0, places=10)

    def test_passing_bablok_resists_one_outlier(self):
        xs = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        ys = [float(x) for x in xs]
        ys[4] = 50.0  # gross outlier
        pb = common.passing_bablok(xs, ys)
        ols = common.fit_linear(xs, ys)
        self.assertAlmostEqual(pb["slope"], 1.0, places=6)
        self.assertGreater(abs(ols.slope - 1.0), abs(pb["slope"] - 1.0))

    def test_passing_bablok_needs_five_points(self):
        with self.assertRaises(common.InputError):
            common.passing_bablok([1, 2, 3], [1, 2, 3])

    def test_passing_bablok_ci_order_statistics(self):
        """Pin the 1-based-to-0-based conversion of the M1/M2 order statistics.

        M1 and M2 are both 1-based positions in the shifted slope list, so both
        convert with the same -1. Applying the offset to only one end silently
        narrows the interval on the low side.
        """
        xs = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120]
        deltas = [1.2, -0.8, 0.5, -1.5, 2.0, -0.3, 1.1, -2.2, 0.9, -1.0, 1.8, -0.6]
        ys = [1.05 * x + 2 + d for x, d in zip(xs, deltas)]
        res = common.passing_bablok(xs, ys)

        slopes = sorted(
            (ys[j] - ys[i]) / (xs[j] - xs[i])
            for i in range(len(xs))
            for j in range(i + 1, len(xs))
            if xs[j] != xs[i]
        )
        n_slopes = len(slopes)
        shift = sum(1 for s in slopes if s < -1.0)
        c = common.z_ppf(0.975) * math.sqrt(
            len(xs) * (len(xs) - 1.0) * (2.0 * len(xs) + 5.0) / 18.0
        )
        m1 = int(round((n_slopes - c) / 2.0))
        m2 = n_slopes - m1 + 1
        self.assertAlmostEqual(res["slope_ci95"][0], slopes[m1 + shift - 1], places=12)
        self.assertAlmostEqual(res["slope_ci95"][1], slopes[m2 + shift - 1], places=12)
        self.assertLessEqual(res["slope_ci95"][0], res["slope"])
        self.assertLessEqual(res["slope"], res["slope_ci95"][1])

    def test_passing_bablok_ci_contains_estimate_across_shapes(self):
        for n in (7, 8, 11, 12, 19, 20):
            xs = [10.0 + 5 * i for i in range(n)]
            ys = [1.03 * x + 1 + (0.7 if i % 3 == 0 else -0.4) for i, x in enumerate(xs)]
            res = common.passing_bablok(xs, ys)
            lo, hi = res["slope_ci95"]
            self.assertLessEqual(lo, res["slope"], f"n={n}")
            self.assertLessEqual(res["slope"], hi, f"n={n}")

    def test_bland_altman_bias_and_loa(self):
        xs = [10.0] * 6
        ys = [11.0, 11.0, 11.0, 11.0, 11.0, 11.0]
        ba = common.bland_altman(xs, ys)
        self.assertAlmostEqual(ba["bias"], 1.0, places=12)
        self.assertAlmostEqual(ba["sd_differences"], 0.0, places=12)

    def test_bland_altman_relative(self):
        ba = common.bland_altman([100.0, 200.0, 400.0], [110.0, 220.0, 440.0], relative=True)
        # Each pair is a 10% increase: (110-100)/105 = 9.5238% of the pair mean.
        self.assertAlmostEqual(ba["bias"], 9.523809523, places=6)
        self.assertAlmostEqual(ba["sd_differences"], 0.0, places=9)

    def test_bland_altman_needs_three_pairs(self):
        with self.assertRaises(common.InputError):
            common.bland_altman([100.0, 200.0], [110.0, 220.0])

    def test_tost_equivalent(self):
        res = common.tost_paired([0.1, -0.2, 0.05, 0.0, 0.15], margin=2.0)
        self.assertTrue(res["equivalent"])
        self.assertLess(res["p_value"], 0.05)

    def test_tost_not_equivalent_when_biased(self):
        res = common.tost_paired([1.9, 2.1, 2.0, 1.95, 2.05], margin=2.0)
        self.assertFalse(res["equivalent"])
        self.assertGreater(res["p_value"], 0.05)

    def test_tost_ci_is_1_minus_2alpha(self):
        diffs = [0.5, 0.6, 0.4, 0.55, 0.45, 0.5]
        res = common.tost_paired(diffs, margin=1.0, alpha=0.05)
        lo, hi = res["ci_1_minus_2alpha"]
        sd = common.sample_sd(diffs)
        se = sd / math.sqrt(len(diffs))
        expected_half = common.t_ppf(0.95, len(diffs) - 1) * se
        self.assertAlmostEqual(hi - res["mean_difference"], expected_half, places=10)
        self.assertAlmostEqual(res["mean_difference"] - lo, expected_half, places=10)

    def test_tost_rejects_bad_margin(self):
        with self.assertRaises(common.InputError):
            common.tost_paired([0.1, 0.2], margin=0.0)


# ---------------------------------------------------------------- catalogue


class TestCatalogue(unittest.TestCase):
    def test_m10_modalities_differ(self):
        cc = catalog.M10_CRITERIA["chromatographic"]
        lba = catalog.M10_CRITERIA["lba"]
        self.assertEqual(cc["accuracy_tolerance_pct"], 15.0)
        self.assertEqual(lba["accuracy_tolerance_pct"], 20.0)
        self.assertEqual(cc["accuracy_tolerance_lloq_pct"], 20.0)
        self.assertEqual(lba["accuracy_tolerance_lloq_pct"], 25.0)
        self.assertEqual(cc["isr_tolerance_pct"], 20.0)
        self.assertEqual(lba["isr_tolerance_pct"], 30.0)

    def test_total_error_is_lba_only(self):
        self.assertIsNone(catalog.M10_CRITERIA["chromatographic"]["total_error_pct"])
        self.assertEqual(catalog.M10_CRITERIA["lba"]["total_error_pct"], 30.0)
        self.assertEqual(catalog.M10_CRITERIA["lba"]["total_error_pct_at_limits"], 40.0)

    def test_m10_run_structure(self):
        cc = catalog.M10_CRITERIA["chromatographic"]
        lba = catalog.M10_CRITERIA["lba"]
        self.assertEqual(cc["qc_levels_accuracy_precision"], 4)
        self.assertEqual(lba["qc_levels_accuracy_precision"], 5)
        self.assertEqual(cc["ap_replicates_per_run"], 5)
        self.assertEqual(lba["ap_replicates_per_run"], 3)
        self.assertEqual(cc["ap_min_runs"], 3)
        self.assertEqual(lba["ap_min_runs"], 6)
        for crit in (cc, lba):
            self.assertEqual(crit["calibration_min_levels"], 6)
            self.assertAlmostEqual(crit["calibration_min_pass_fraction"], 0.75)
            self.assertAlmostEqual(crit["isr_pass_fraction"], 2 / 3)

    def test_q2r2_table1_limit_test_needs_dl_not_ql(self):
        limit = catalog.Q2R2_TESTS_BY_ATTRIBUTE["impurity-limit"]
        quant = catalog.Q2R2_TESTS_BY_ATTRIBUTE["impurity-quantitative"]
        self.assertEqual(limit["lower-range-limit"], "required-DL")
        self.assertEqual(quant["lower-range-limit"], "required-QL")
        self.assertEqual(limit["accuracy"], "not-normally")
        self.assertEqual(quant["accuracy"], "required")

    def test_q2r2_identity_only_needs_specificity(self):
        ident = catalog.Q2R2_TESTS_BY_ATTRIBUTE["identity"]
        self.assertEqual(ident["specificity"], "required")
        for key, value in ident.items():
            if key != "specificity":
                self.assertEqual(value, "not-normally")

    def test_attribute_aliases_resolve(self):
        self.assertEqual(catalog.resolve_attribute("Content"), "assay")
        self.assertEqual(catalog.resolve_attribute("related-substances"), "impurity-quantitative")
        self.assertEqual(catalog.resolve_attribute("limit-test"), "impurity-limit")
        with self.assertRaises(KeyError):
            catalog.resolve_attribute("nonsense")

    def test_paywalled_frameworks_marked_not_reproducible(self):
        for key in ("usp-1220", "usp-1225", "usp-1226", "clsi", "iso-17025"):
            self.assertFalse(catalog.FRAMEWORKS[key]["reproducible"], key)
        for key in ("ich-q2r2", "ich-m10"):
            self.assertTrue(catalog.FRAMEWORKS[key]["reproducible"], key)

    def test_q2r2_response_requires_five_levels(self):
        self.assertIn("5", catalog.Q2R2_STUDY_DESIGN["response"]["requirement"])

    def test_dl_ql_factors_documented(self):
        sd_slope = catalog.DL_QL_APPROACHES["sd-and-slope"]
        self.assertIn("3.3", sd_slope["dl"])
        self.assertIn("10", sd_slope["ql"])


# ---------------------------------------------------------------- CLI


class TestPlanValidation(unittest.TestCase):
    def test_list_frameworks(self):
        res = run_script("plan_validation.py".removesuffix(".py"), "--list-frameworks",
                         "--format", "json")
        self.assertEqual(res.returncode, 0, res.stderr)
        rows = json.loads(res.stdout)
        keys = {r["key"] for r in rows}
        self.assertIn("ich-q2r2", keys)
        self.assertIn("ich-m10", keys)

    def test_q2r2_assay_plan(self):
        res = run_script("plan_validation", "--framework", "ich-q2r2",
                         "--attribute", "assay", "--format", "json")
        self.assertEqual(res.returncode, 0, res.stderr)
        rows = json.loads(res.stdout)
        chars = {r["characteristic"] for r in rows}
        self.assertIn("specificity", chars)
        self.assertIn("intermediate-precision", chars)
        self.assertIn("robustness", chars)

    def test_identity_plan_marks_most_tests_not_required(self):
        res = run_script("plan_validation", "--framework", "ich-q2r2",
                         "--attribute", "identity", "--format", "json")
        rows = {r["characteristic"]: r["required"] for r in json.loads(res.stdout)}
        self.assertEqual(rows["specificity"], "conduct")
        self.assertIn("not normally", rows["accuracy"])

    def test_m10_requires_modality(self):
        res = run_script("plan_validation", "--framework", "ich-m10")
        self.assertEqual(res.returncode, 2)
        self.assertIn("modality", res.stderr)

    def test_m10_lba_plan_includes_total_error(self):
        res = run_script("plan_validation", "--framework", "ich-m10",
                         "--modality", "lba", "--format", "json")
        items = {r["item"] for r in json.loads(res.stdout)}
        self.assertIn("total error", items)

    def test_m10_chromatographic_plan_excludes_total_error(self):
        res = run_script("plan_validation", "--framework", "ich-m10",
                         "--modality", "chromatographic", "--format", "json")
        items = {r["item"] for r in json.loads(res.stdout)}
        self.assertNotIn("total error", items)

    def test_unknown_framework_exits_2(self):
        res = run_script("plan_validation", "--framework", "nope")
        self.assertEqual(res.returncode, 2)

    def test_protocol_skeleton_has_pre_stated_criteria_section(self):
        res = run_script("plan_validation", "--framework", "ich-q2r2",
                         "--attribute", "impurity", "--protocol")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("Pre-stated acceptance criteria", res.stdout)
        self.assertIn("BEFORE data collection", res.stdout)

    def test_paywalled_framework_refuses_to_supply_design(self):
        res = run_script("plan_validation", "--framework", "usp-1225", "--format", "json")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("copyrighted", res.stderr)
        rows = json.loads(res.stdout)
        self.assertIn("obtain_from", rows[0])


class TestCheckResponse(unittest.TestCase):
    def test_good_curve_no_findings(self):
        res = run_script("check_response", "-i", str(FIXTURES / "calibration_good.csv"),
                         "--max-back-calc-error", "2")
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_curved_response_flagged(self):
        res = run_script("check_response", "-i", str(FIXTURES / "calibration_curved.csv"),
                         "--max-back-calc-error", "2")
        self.assertEqual(res.returncode, 1)
        self.assertIn("lack-of-fit", res.stderr)

    def test_curved_response_has_high_r_squared(self):
        """The whole point: r-squared passes while the model is unusable."""
        res = run_script("check_response", "-i", str(FIXTURES / "calibration_curved.csv"),
                         "--format", "json")
        payload = json.loads(res.stdout)[0]
        self.assertGreater(payload["summary"]["coefficient of determination (r2)"], 0.98)
        self.assertLess(payload["summary"]["lack-of-fit p"], 0.001)
        worst = max(abs(r["relative_error_pct"]) for r in payload["levels"])
        self.assertGreater(worst, 5.0)

    def test_too_few_levels_flagged(self):
        res = run_script("check_response", "-i", str(FIXTURES / "calibration_three_levels.csv"))
        self.assertEqual(res.returncode, 1)
        self.assertIn("recommends at least 5", res.stderr)

    def test_missing_column_exits_2(self):
        res = run_script("check_response", "-i", str(FIXTURES / "bad_columns.csv"))
        self.assertEqual(res.returncode, 2)
        self.assertIn("missing required column", res.stderr)

    def test_weighting_option_accepted(self):
        res = run_script("check_response", "-i", str(FIXTURES / "calibration_good.csv"),
                         "--weight", "1/x2", "--format", "json")
        payload = json.loads(res.stdout)[0]
        self.assertEqual(payload["summary"]["weighting"], "1/x2")


class TestCheckAccuracyPrecision(unittest.TestCase):
    def test_between_day_shift_inflates_intermediate_precision(self):
        res = run_script("check_accuracy_precision", "-i", str(FIXTURES / "ap_between_day.csv"),
                         "--format", "json")
        payload = json.loads(res.stdout)[0]
        rows = payload["precision"]
        rep = [r for r in rows if r["level"] == "100"
               and r["component"].startswith("repeatability")][0]
        inter = [r for r in rows if r["level"] == "100"
                 and r["component"].startswith("intermediate")][0]
        self.assertGreater(inter["rsd_pct"], 10 * rep["rsd_pct"])

    def test_precision_is_reported_per_level(self):
        res = run_script("check_accuracy_precision", "-i", str(FIXTURES / "ap_between_day.csv"),
                         "--format", "json")
        rows = json.loads(res.stdout)[0]["precision"]
        levels = {r["level"] for r in rows}
        self.assertIn("80", levels)
        self.assertIn("100", levels)
        self.assertIn("120", levels)
        # Per-level RSD must not be inflated by the 80/100/120 range itself.
        for r in rows:
            if r["component"].startswith("repeatability"):
                self.assertLess(r["rsd_pct"], 5.0)

    def test_accuracy_reports_confidence_interval(self):
        res = run_script("check_accuracy_precision", "-i", str(FIXTURES / "ap_between_day.csv"),
                         "--format", "json")
        acc = json.loads(res.stdout)[0]["accuracy"]
        for row in acc:
            self.assertIn("ci95_low", row)
            self.assertIn("ci95_high", row)
            self.assertLess(row["ci95_low"], row["mean_recovery_pct"])
            self.assertGreater(row["ci95_high"], row["mean_recovery_pct"])

    def test_require_ci_within_limit_is_stricter(self):
        lenient = run_script("check_accuracy_precision", "-i",
                             str(FIXTURES / "ap_between_day.csv"), "--accuracy-limit", "1.0")
        strict = run_script("check_accuracy_precision", "-i",
                            str(FIXTURES / "ap_between_day.csv"), "--accuracy-limit", "1.0",
                            "--require-ci-within-limit")
        # The mean is inside +/-1%, so lenient passes; the CI is not, so strict fails.
        self.assertEqual(lenient.returncode, 0, lenient.stderr)
        self.assertEqual(strict.returncode, 1)
        self.assertIn("CI", strict.stderr)

    def test_no_group_column_only_repeatability(self):
        res = run_script("check_accuracy_precision", "-i", str(FIXTURES / "ap_no_group.csv"),
                         "--format", "json")
        self.assertEqual(res.returncode, 0, res.stderr)
        rows = json.loads(res.stdout)[0]["precision"]
        self.assertTrue(all("repeatability" in r["component"] for r in rows))
        self.assertIn("intermediate precision", res.stderr)

    def test_zero_level_rejected(self):
        res = run_script("check_accuracy_precision", "-i", str(FIXTURES / "ap_zero_level.csv"))
        self.assertEqual(res.returncode, 2)

    def test_six_at_one_level_satisfies_option_b(self):
        """Q2(R2) 3.3.2.1 offers two alternatives; either is sufficient.

        Six determinations at 100% of the test concentration is option (b).
        Demanding nine unconditionally raises a finding against a design the
        guideline explicitly permits.
        """
        res = run_script("check_accuracy_precision", "-i", str(FIXTURES / "ap_no_group.csv"),
                         "--design-check", "assay")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("option (b)", res.stderr)

    def test_nine_across_range_satisfies_option_a(self):
        res = run_script("check_accuracy_precision", "-i", str(FIXTURES / "ap_between_day.csv"),
                         "--design-check", "assay")
        self.assertIn("option (a)", res.stderr)

    def test_design_meeting_neither_option_is_flagged(self):
        res = run_script("check_accuracy_precision", "-i", str(FIXTURES / "ap_thin_design.csv"),
                         "--design-check", "assay")
        self.assertEqual(res.returncode, 1)
        self.assertIn("neither", res.stderr)


class TestCheckDetectionLimits(unittest.TestCase):
    def test_multiple_approaches_reported(self):
        res = run_script("check_detection_limits", "--calibration",
                         str(FIXTURES / "lowrange_calibration.csv"),
                         "--blanks", str(FIXTURES / "blanks.csv"), "--format", "json")
        payload = json.loads(res.stdout)[0]
        approaches = [e["approach"] for e in payload["estimates"]]
        self.assertGreaterEqual(len(approaches), 3)
        self.assertTrue(any("blanks" in a for a in approaches))
        self.assertTrue(any("residual SD" in a for a in approaches))

    def test_dl_ql_factor_relationship(self):
        res = run_script("check_detection_limits", "--calibration",
                         str(FIXTURES / "lowrange_calibration.csv"), "--format", "json")
        for est in json.loads(res.stdout)[0]["estimates"]:
            if math.isfinite(est["sigma"]):
                self.assertAlmostEqual(est["QL"] / est["DL"], 10.0 / 3.3, places=6)

    def test_ql_above_reporting_threshold_flagged(self):
        res = run_script("check_detection_limits", "--calibration",
                         str(FIXTURES / "lowrange_calibration.csv"),
                         "--confirm-ql", "0.10", "--reporting-threshold", "0.05")
        self.assertEqual(res.returncode, 1)
        self.assertIn("reporting threshold", res.stderr)

    def test_ql_confirmation_evaluated(self):
        res = run_script("check_detection_limits", "--calibration",
                         str(FIXTURES / "lowrange_calibration.csv"),
                         "--confirm-ql", "0.05",
                         "--confirm-data", str(FIXTURES / "ql_confirmation.csv"),
                         "--format", "json")
        payload = json.loads(res.stdout)[0]
        metrics = {r["metric"]: r["value"] for r in payload["confirmation"]}
        self.assertIn("bias vs claimed QL (%)", metrics)
        self.assertIn("RSD (%)", metrics)

    def test_confirm_data_without_claim_exits_2(self):
        res = run_script("check_detection_limits", "--calibration",
                         str(FIXTURES / "lowrange_calibration.csv"),
                         "--confirm-data", str(FIXTURES / "ql_confirmation.csv"))
        self.assertEqual(res.returncode, 2)

    def test_threshold_check_uses_the_conservative_estimate(self):
        """With no claimed QL, the compliance check must not pick the flattering estimate.

        The fixture's QL estimates straddle 0.010. Taking the smallest would report
        no findings on a procedure whose conservative limit fails.
        """
        res = run_script("check_detection_limits", "--calibration",
                         str(FIXTURES / "lowrange_calibration.csv"),
                         "--blanks", str(FIXTURES / "blanks.csv"),
                         "--reporting-threshold", "0.010", "--format", "json")
        payload = json.loads(res.stdout)[0]
        qls = [e["QL"] for e in payload["estimates"]]
        self.assertLess(min(qls), 0.010)
        self.assertGreater(max(qls), 0.010)
        self.assertEqual(res.returncode, 1)
        self.assertIn("straddle", res.stderr)
        self.assertIn("conservative", res.stderr)

    def test_explicit_claim_overrides_the_conservative_default(self):
        res = run_script("check_detection_limits", "--calibration",
                         str(FIXTURES / "lowrange_calibration.csv"),
                         "--blanks", str(FIXTURES / "blanks.csv"),
                         "--confirm-ql", "0.005", "--reporting-threshold", "0.010")
        self.assertNotIn("straddle", res.stderr)
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_signal_to_noise_requires_level(self):
        res = run_script("check_detection_limits", "--calibration",
                         str(FIXTURES / "lowrange_calibration.csv"),
                         "--signal-to-noise", "12")
        self.assertEqual(res.returncode, 2)


class TestCheckBioanalyticalRun(unittest.TestCase):
    def test_per_level_qc_rule_catches_failing_level(self):
        res = run_script("check_bioanalytical_run", "--modality", "chromatographic",
                         "--run", str(FIXTURES / "m10_run_high_qc_fails.csv"))
        self.assertEqual(res.returncode, 1)
        self.assertIn("50% at each level", res.stderr)

    def test_same_run_passes_lba_tolerances(self):
        """The identical run passes under LBA tolerances -- the modality matters."""
        cc = run_script("check_bioanalytical_run", "--modality", "chromatographic",
                        "--run", str(FIXTURES / "m10_run_high_qc_fails.csv"))
        lba = run_script("check_bioanalytical_run", "--modality", "lba",
                         "--run", str(FIXTURES / "m10_run_high_qc_fails.csv"))
        self.assertEqual(cc.returncode, 1)
        self.assertEqual(lba.returncode, 0, lba.stderr)

    def test_modality_is_mandatory(self):
        res = run_script("check_bioanalytical_run", "--run",
                         str(FIXTURES / "m10_run_high_qc_fails.csv"))
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("modality", res.stderr.lower())

    def test_isr_chromatographic_vs_lba(self):
        cc = run_script("check_bioanalytical_run", "--modality", "chromatographic",
                        "--isr", str(FIXTURES / "m10_isr.csv"))
        lba = run_script("check_bioanalytical_run", "--modality", "lba",
                         "--isr", str(FIXTURES / "m10_isr.csv"))
        # Differences sit between 20% and 30%, so this fails CC and passes LBA.
        self.assertEqual(cc.returncode, 1)
        self.assertEqual(lba.returncode, 0, lba.stderr)

    def test_total_error_rejected_for_chromatographic(self):
        res = run_script("check_bioanalytical_run", "--modality", "chromatographic",
                         "--total-error", str(FIXTURES / "m10_total_error.csv"))
        self.assertEqual(res.returncode, 2)
        self.assertIn("ligand binding", res.stderr)

    def test_total_error_applied_for_lba(self):
        res = run_script("check_bioanalytical_run", "--modality", "lba",
                         "--total-error", str(FIXTURES / "m10_total_error.csv"),
                         "--format", "json")
        rows = json.loads(res.stdout)[0]["total_error"]
        lloq = [r for r in rows if r["label"].lower() == "lloq"][0]
        mid = [r for r in rows if r["label"].lower() == "medium"][0]
        self.assertEqual(lloq["limit_pct"], 40.0)
        self.assertEqual(mid["limit_pct"], 30.0)

    def test_anchor_points_excluded_from_calibration_count(self):
        res = run_script("check_bioanalytical_run", "--modality", "lba",
                         "--run", str(FIXTURES / "m10_run_lba_anchor.csv"),
                         "--format", "json")
        rows = json.loads(res.stdout)[0]["run"]
        anchors = [r for r in rows if r["label"] == "ANCHOR"]
        self.assertTrue(anchors)
        self.assertEqual(anchors[0]["within"], "excluded")

    def test_criteria_listing(self):
        res = run_script("check_bioanalytical_run", "--modality", "lba", "--criteria",
                         "--format", "json")
        self.assertEqual(res.returncode, 0, res.stderr)
        names = {r["criterion"] for r in json.loads(res.stdout)}
        self.assertIn("total_error_pct", names)

    def test_bad_type_column_exits_2(self):
        res = run_script("check_bioanalytical_run", "--modality", "chromatographic",
                         "--run", str(FIXTURES / "m10_run_bad_type.csv"))
        self.assertEqual(res.returncode, 2)


class TestCompareMethods(unittest.TestCase):
    def test_equivalent_at_two_percent(self):
        res = run_script("compare_methods", "-i", str(FIXTURES / "transfer_paired.csv"),
                         "--margin", "2", "--relative", "--format", "json")
        payload = json.loads(res.stdout)[0]
        self.assertTrue(payload["tost"]["equivalent"])

    def test_not_equivalent_at_one_percent(self):
        res = run_script("compare_methods", "-i", str(FIXTURES / "transfer_paired.csv"),
                         "--margin", "1", "--relative")
        self.assertEqual(res.returncode, 1)
        self.assertIn("equivalence NOT demonstrated", res.stderr)

    def test_t_test_significant_while_tost_equivalent(self):
        """The core teaching case: both statements are true and only one answers the question."""
        res = run_script("compare_methods", "-i", str(FIXTURES / "transfer_paired.csv"),
                         "--margin", "2", "--relative", "--format", "json")
        payload = json.loads(res.stdout)[0]
        self.assertLess(payload["paired_t_p_value"], 0.05)
        self.assertTrue(payload["tost"]["equivalent"])

    def test_deming_and_ols_both_reported(self):
        res = run_script("compare_methods", "-i", str(FIXTURES / "transfer_paired.csv"),
                         "--margin", "5", "--relative", "--format", "json")
        payload = json.loads(res.stdout)[0]
        self.assertIn("ols_slope", payload)
        self.assertIn("slope", payload["deming"])
        self.assertIn("slope", payload["passing_bablok"])

    def test_margin_is_required(self):
        res = run_script("compare_methods", "-i", str(FIXTURES / "transfer_paired.csv"))
        self.assertEqual(res.returncode, 2)

    def test_too_few_pairs_exits_2(self):
        res = run_script("compare_methods", "-i", str(FIXTURES / "transfer_two_pairs.csv"),
                         "--margin", "2")
        self.assertEqual(res.returncode, 2)


# ---------------------------------------------------------------- I/O


class TestInputHandling(unittest.TestCase):
    def test_json_csv_and_tsv_normalize_the_same_record(self):
        record = {" level ": 0, " response ": " 10100 ", " sample ": " sample A ", " note ": None}
        expected = [{"level": "0", "response": "10100", "sample": "sample A", "note": ""}]
        for payload in ([record], {"rows": [record]}, {"data": [record]}):
            with self.subTest(payload=payload):
                rows = common.parse_rows(json.dumps(payload))
                self.assertEqual(rows, expected)
                common.require_columns(rows, ["level", "response"])
        for delimiter in (",", "\t"):
            with self.subTest(delimiter=delimiter):
                text = delimiter.join(record) + "\n"
                text += delimiter.join(("0", " 10100 ", " sample A ", "")) + "\n"
                self.assertEqual(common.parse_rows(text), expected)

    def test_padded_json_produces_the_same_analysis_as_csv(self):
        rows = common.parse_rows((FIXTURES / "calibration_good.csv").read_text())
        padded = [{f" {key} ": f" {value} " for key, value in row.items()} for row in rows]
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "check_response.py"), "-i", "-", "--format", "json"],
            input=json.dumps(padded), capture_output=True, text=True, check=False,
        )
        baseline = run_script("check_response", "-i", str(FIXTURES / "calibration_good.csv"),
                              "--format", "json")
        self.assertEqual(baseline.returncode, 0, baseline.stderr)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), json.loads(baseline.stdout))

    def test_json_input_accepted(self):
        res = run_script("check_response", "-i", str(FIXTURES / "calibration_good.json"),
                         "--format", "json")
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_tsv_input_accepted(self):
        res = run_script("check_response", "-i", str(FIXTURES / "calibration_good.tsv"),
                         "--format", "json")
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_non_numeric_value_names_the_row(self):
        res = run_script("check_response", "-i", str(FIXTURES / "calibration_nonnumeric.csv"))
        self.assertEqual(res.returncode, 2)
        self.assertIn("not numeric", res.stderr)

    def test_ragged_csv_and_tsv_name_the_data_row(self):
        for delimiter, suffix in ((",", ".csv"), ("\t", ".tsv")):
            with self.subTest(suffix=suffix):
                text = delimiter.join(("level", "response")) + "\n"
                text += delimiter.join(("50", "10100")) + "\n"
                text += delimiter.join(("100", "20100", "extra")) + "\n"
                with self.assertRaisesRegex(
                    common.InputError, "row 2: more fields than the header"
                ):
                    common.parse_rows(text, path_hint="calibration" + suffix)

    def test_ragged_and_short_rows_are_cli_input_errors(self):
        for row, message in (("100,20100,extra", "more fields than the header"),
                             ("100", "not numeric")):
            with self.subTest(row=row):
                res = subprocess.run(
                    [sys.executable, str(SCRIPTS_DIR / "check_response.py"), "-i", "-"],
                    input="level,response\n50,10100\n" + row + "\n",
                    capture_output=True, text=True, check=False,
                )
                self.assertEqual(res.returncode, 2, res.stderr)
                self.assertIn(message, res.stderr)
                self.assertNotIn("Traceback", res.stderr)
                self.assertEqual(res.stdout, "")

    def test_missing_file_exits_2(self):
        res = run_script("check_response", "-i", str(FIXTURES / "does_not_exist.csv"))
        self.assertEqual(res.returncode, 2)

    def test_oversize_json_is_refused_not_truncated(self):
        """Silently dropping rows would give a clean result computed on part of the study."""
        payload = [{"level": 50 + (i % 5) * 25, "response": 10000 + i} for i in range(common.MAX_ROWS + 5)]
        with self.assertRaises(common.InputError) as ctx:
            common.parse_rows(json.dumps(payload))
        self.assertIn("more than", str(ctx.exception))

    def test_json_row_cap_boundary_is_accepted(self):
        payload = [{"level": 50 + (i % 5) * 25, "response": 10000 + i} for i in range(common.MAX_ROWS)]
        rows = common.parse_rows(json.dumps(payload))
        self.assertEqual(len(rows), common.MAX_ROWS)

    def test_empty_json_array_rejected(self):
        with self.assertRaises(common.InputError):
            common.parse_rows("[]")

    def test_omitted_input_does_not_block_on_a_terminal(self):
        """An omitted --input must error, not wait forever on a tty."""
        import unittest.mock as mock

        with mock.patch.object(sys, "stdin") as fake:
            fake.isatty.return_value = True
            with self.assertRaises(common.InputError) as ctx:
                common.read_input(None)
        self.assertIn("--input", str(ctx.exception))
        fake.read.assert_not_called()

    def test_stdout_carries_data_stderr_carries_notes(self):
        res = run_script("check_response", "-i", str(FIXTURES / "calibration_good.csv"),
                         "--format", "tsv")
        self.assertIn("statistic", res.stdout)
        self.assertNotIn("note:", res.stdout)
        self.assertIn("note:", res.stderr)


# The shared --help contract: every argparse CLI this skill ships answers --help
# without doing any work. It skips when the skill's packages are absent and runs
# for real under `python tests/run_all.py --isolated`.
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

if __name__ == "__main__":
    unittest.main()
