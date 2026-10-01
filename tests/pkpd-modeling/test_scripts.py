"""Tests for the pkpd-modeling skill scripts.

The value of this skill rests entirely on the numbers being right, so the tests
check against things that are true independently of the implementation:

* closed-form identities every linear PK model must satisfy (AUC = D/CL,
  Vss = sum of volumes, MRT = Vss/CL, the Bateman function, the flip-flop
  limit);
* analytical profiles with known parameters, which NCA and the compartmental
  fitter must recover;
* published reference values -- the PowerTOST bioequivalence sample-size table,
  the EMA ABEL cap, and the FDA body-surface-area conversion factors;
* hand-computable regressions for the concentration-QTc model.

Everything runs offline.

    uv run --with pytest python -m pytest tests/pkpd-modeling -q
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pytest

import skill_contract

# The scripts import scipy indirectly through `_models`. Guarding here turns a
# bare project-environment run into a clean skip instead of a pytest
# INTERNALERROR; the real run is `tests/run_all.py --isolated pkpd-modeling`.
np = pytest.importorskip("numpy", reason="pkpd-modeling needs numpy")
pytest.importorskip("scipy", reason="pkpd-modeling needs scipy")

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pkpd-modeling"
SCRIPTS = SKILL_ROOT / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

sys.path.insert(0, str(SCRIPTS))

import _common  # noqa: E402
import _models  # noqa: E402
import allometry_and_fih  # noqa: E402
import bioequivalence  # noqa: E402
import ddi_static  # noqa: E402
import exposure_response  # noqa: E402
import nca  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)


def run_script(name: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / f"{name}.py"), *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=SCRIPTS,
    )


def write_csv(directory: Path, name: str, header: str, rows) -> Path:
    path = directory / name
    lines = [header] + [",".join(str(v) for v in row) for row in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# ------------------------------------------------------------------ structure


class TestSkillStructure(unittest.TestCase):
    def test_frontmatter(self) -> None:
        self.assertEqual(skill_contract.structure.frontmatter_problems(SKILL_ROOT), [])

    def test_length(self) -> None:
        self.assertEqual(skill_contract.structure.length_problems(SKILL_ROOT), [])

    def test_no_stray_tests(self) -> None:
        self.assertEqual(skill_contract.structure.stray_test_problems(SKILL_ROOT), [])

    def test_no_bytecode(self) -> None:
        self.assertEqual(skill_contract.structure.bytecode_problems(SKILL_ROOT), [])

    def test_scripts_compile(self) -> None:
        self.assertEqual(skill_contract.structure.compile_problems(SKILL_ROOT), [])

    def test_internal_links_resolve(self) -> None:
        self.assertEqual(skill_contract.structure.link_problems(SKILL_ROOT), [])

    def test_every_referenced_file_exists(self) -> None:
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        missing = []
        for kind in ("references", "assets"):
            for line in text.splitlines():
                marker = f"`{kind}/"
                if marker in line:
                    name = line.split(marker, 1)[1].split("`", 1)[0]
                    if not (SKILL_ROOT / kind / name).is_file():
                        missing.append(f"{kind}/{name}")
        self.assertEqual(missing, [], f"SKILL.md references files that do not exist: {missing}")

    def test_every_script_is_documented(self) -> None:
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        undocumented = [
            path.name
            for path in sorted(SCRIPTS.glob("*.py"))
            if not path.name.startswith("_") and path.name not in text
        ]
        self.assertEqual(undocumented, [])


# ------------------------------------------------------------- model library


class TestDispositionIdentities(unittest.TestCase):
    """Identities that hold for every linear mammillary model."""

    def test_one_compartment_matches_closed_form(self) -> None:
        d = _models.disposition(cl=5.0, v1=20.0)
        t = np.array([0.0, 1.0, 4.0, 12.0])
        np.testing.assert_allclose(_models.conc_bolus(t, 100.0, d), 100 / 20 * np.exp(-0.25 * t))

    def test_auc_equals_dose_over_clearance(self) -> None:
        for cl, v1, q, vp in [(5.0, 20.0, (), ()), (3.0, 10.0, (2.0,), (25.0,)), (4.0, 8.0, (3.0, 1.0), (20.0, 60.0))]:
            with self.subTest(compartments=1 + len(q)):
                d = _models.disposition(cl, v1, q, vp)
                self.assertAlmostEqual(500 * d.auc_unit_dose, 500 / cl, places=6)

    def test_vss_and_mrt(self) -> None:
        d = _models.disposition(4.0, 8.0, (3.0, 1.0), (20.0, 60.0))
        self.assertAlmostEqual(d.vss, 88.0, places=9)
        self.assertAlmostEqual(d.mrt_iv, 88.0 / 4.0, places=5)

    def test_initial_concentration_is_dose_over_v1(self) -> None:
        d = _models.disposition(3.0, 10.0, (2.0,), (25.0,))
        self.assertAlmostEqual(float(_models.conc_bolus(np.array([0.0]), 500.0, d)[0]), 50.0, places=9)

    def test_oral_matches_bateman(self) -> None:
        cl, v, ka, f = 5.0, 20.0, 1.2, 0.8
        d = _models.disposition(cl, v)
        t = np.array([0.5, 1.0, 2.0, 6.0, 24.0])
        k = cl / v
        expected = f * 100 * ka / (v * (ka - k)) * (np.exp(-k * t) - np.exp(-ka * t))
        np.testing.assert_allclose(_models.conc_oral(t, 100.0, ka, d, f=f), expected)

    def test_absorption_singularity_uses_the_limit(self) -> None:
        """ka == k is the flip-flop boundary; the naive formula divides by zero."""
        cl, v = 5.0, 20.0
        k = cl / v
        d = _models.disposition(cl, v)
        t = np.array([0.5, 1.0, 4.0])
        result = _models.conc_oral(t, 100.0, k, d, f=1.0)
        np.testing.assert_allclose(result, 100 * k * t * np.exp(-k * t) / v)
        self.assertTrue(np.all(np.isfinite(result)))

    def test_infusion_reaches_rate_over_clearance(self) -> None:
        d = _models.disposition(5.0, 20.0, (3.0,), (40.0,))
        css = _models.conc_infusion(np.array([500.0]), 100.0 * 500.0, 500.0, d)[0]
        self.assertAlmostEqual(float(css), 100.0 / 5.0, places=6)

    def test_steady_state_metrics_match_brute_force_superposition(self) -> None:
        d = _models.disposition(5.0, 20.0, (3.0,), (40.0,))
        tau = 12.0
        metrics = _models.steady_state_metrics(d, 100.0, tau)
        regimen = _models.build_regimen(100.0, interval=tau, n_doses=400)
        grid = np.linspace(399 * tau, 400 * tau, 20001)
        profile = _models.simulate_linear(grid, regimen, d)
        self.assertAlmostEqual(metrics["cmax_ss_bolus"], float(profile.max()), places=6)
        self.assertAlmostEqual(metrics["cmin_ss_bolus"], float(profile.min()), places=6)
        self.assertAlmostEqual(metrics["cavg_ss"], float(np.trapezoid(profile, grid)) / tau, places=4)

    def test_michaelis_menten_reduces_to_linear_at_high_km(self) -> None:
        t = np.linspace(0, 24, 121)
        linear = _models.conc_bolus(t, 100.0, _models.disposition(5.0, 20.0))
        nonlinear = _models.simulate_michaelis_menten(
            t, [_models.Dose(0.0, 100.0)], vmax=5.0 * 1e7, km=1e7, v1=20.0
        )
        np.testing.assert_allclose(linear, nonlinear, rtol=1e-4)

    def test_michaelis_menten_is_not_dose_proportional(self) -> None:
        t = np.linspace(0, 48, 97)
        low = _models.simulate_michaelis_menten(t, [_models.Dose(0.0, 100.0)], vmax=20.0, km=1.0, v1=20.0)
        high = _models.simulate_michaelis_menten(t, [_models.Dose(0.0, 200.0)], vmax=20.0, km=1.0, v1=20.0)
        auc_low = float(np.trapezoid(low, t))
        auc_high = float(np.trapezoid(high, t))
        self.assertGreater(auc_high / auc_low, 2.2, "saturable elimination must give more than proportional AUC")

    def test_effect_compartment_matches_analytical_solution(self) -> None:
        t = np.linspace(0, 50, 501)
        k, ke0 = 0.2, 0.7
        conc = 5 * np.exp(-k * t)
        expected = 5 * ke0 / (ke0 - k) * (np.exp(-k * t) - np.exp(-ke0 * t))
        np.testing.assert_allclose(_models.effect_compartment(t, conc, ke0), expected, atol=2e-3)

    def test_effect_compartment_equilibrates_to_constant_input(self) -> None:
        t = np.linspace(0, 50, 501)
        ce = _models.effect_compartment(t, np.full_like(t, 10.0), ke0=0.5)
        self.assertAlmostEqual(float(ce[-1]), 10.0, places=6)

    def test_indirect_response_starts_at_baseline(self) -> None:
        d = _models.disposition(5.0, 20.0)
        t = np.linspace(0, 72, 145)

        def conc(time: float) -> float:
            return float(_models.conc_bolus(np.array([time]), 100.0, d)[0])

        response = _models.indirect_response(t, conc, kin=10.0, kout=0.1, idr_type=1, max_effect=0.9, c50=1.0)
        self.assertAlmostEqual(float(response[0]), 100.0, places=4)
        self.assertLess(float(response.min()), 100.0, "inhibition of production must lower the response")
        self.assertGreater(float(response[-1]), float(response.min()), "response must recover towards baseline")

    def test_tmdd_target_is_suppressed_by_drug_and_recovers(self) -> None:
        """A large bolus binds essentially all target under QSS, then it recovers.

        Free target at t=0 is near zero, not at the ksyn/kdeg baseline: the
        quasi-steady-state assumption binds instantaneously. What must hold is
        that free target plus complex accounts for the target present, and that
        free target returns towards baseline as drug is cleared.
        """
        baseline = 0.1 / 0.1
        t = np.linspace(0, 400, 801)
        result = _models.simulate_tmdd(
            t, [_models.Dose(0.0, 100.0)], cl=0.2, v1=3.0, kon=1.0, koff=0.01,
            kint=0.1, ksyn=0.1, kdeg=0.1, approximation="qss",
        )
        self.assertLess(float(result["free_target"][0]), 0.01 * baseline)
        self.assertAlmostEqual(float(result["free_target"][0] + result["complex"][0]), baseline, places=6)
        self.assertGreater(float(result["free_target"][-1]), 0.5 * baseline)
        np.testing.assert_allclose(
            result["total_drug"], result["free_drug"] + result["complex"], rtol=1e-6, atol=1e-9
        )

    def test_tmdd_without_drug_sits_at_the_target_baseline(self) -> None:
        t = np.linspace(0, 50, 101)
        result = _models.simulate_tmdd(
            t, [_models.Dose(0.0, 0.0)], cl=0.2, v1=3.0, kon=1.0, koff=0.01,
            kint=0.1, ksyn=0.4, kdeg=0.2, approximation="qss",
        )
        np.testing.assert_allclose(result["free_target"], 0.4 / 0.2, rtol=1e-6)
        np.testing.assert_allclose(result["free_drug"], 0.0, atol=1e-12)

    def test_disposition_rejects_mismatched_peripherals(self) -> None:
        with self.assertRaises(ValueError):
            _models.disposition(5.0, 20.0, q=(3.0,), vp=())


# --------------------------------------------------------------------- NCA


def analytical_oral_profile(tmp: Path) -> Path:
    """A noiseless one-compartment oral profile with known parameters."""
    d = _models.disposition(cl=5.0, v1=20.0)
    t = np.array([0, 0.25, 0.5, 1, 1.5, 2, 3, 4, 6, 8, 12, 16, 24, 36, 48], dtype=float)
    c = _models.conc_oral(t, 100.0, 1.2, d)
    return write_csv(tmp, "oral.csv", "id,time,conc", [(1, ti, f"{ci:.10g}") for ti, ci in zip(t, c)])


class TestNCA(unittest.TestCase):
    def test_recovers_known_parameters(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = analytical_oral_profile(Path(tmpdir))
            result = run_script("nca", "-i", str(path), "--dose", "100", "--format", "json")
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            row = payload["tables"][0]["rows"][0]
            self.assertAlmostEqual(row["lambda_z"], 0.25, places=8)
            self.assertAlmostEqual(row["t_half"], math.log(2) / 0.25, places=6)
            # AUCinf is slightly low because the trapezoidal rule under-reads
            # the absorption phase on this sampling schedule; CL/F inherits it.
            self.assertAlmostEqual(row["auc_inf_obs"], 20.0, delta=0.2)
            self.assertAlmostEqual(row["cl_f"], 5.0, delta=0.05)
            self.assertAlmostEqual(row["vz_f"], 20.0, delta=0.2)
            self.assertLess(row["pct_auc_extrap"], 1.0)

    def test_lambda_z_excludes_tmax(self) -> None:
        time = np.array([0.0, 1.0, 2.0, 4.0, 8.0, 12.0, 24.0])
        conc = np.array([0.0, 5.0, 9.0, 6.0, 3.0, 1.5, 0.2])
        blq = np.zeros_like(time, dtype=bool)
        lz = nca.estimate_lambda_z(time, conc, blq, tmax=2.0)
        self.assertIsNotNone(lz.t_first)
        self.assertGreater(lz.t_first, 2.0)

    def test_lambda_z_refuses_with_too_few_points(self) -> None:
        time = np.array([0.0, 1.0, 2.0, 4.0])
        conc = np.array([0.0, 5.0, 9.0, 6.0])
        lz = nca.estimate_lambda_z(time, conc, np.zeros(4, dtype=bool), tmax=2.0)
        self.assertIsNone(lz.lam)
        self.assertIn("need 3", lz.reason)

    def test_log_down_trapezoid_is_below_linear_on_a_declining_curve(self) -> None:
        time = np.array([0.0, 4.0, 8.0, 12.0])
        conc = 10 * np.exp(-0.3 * time)
        linear, _ = nca.cumulative_auc(time, conc, "linear")
        logdown, _ = nca.cumulative_auc(time, conc, "linup-logdown")
        self.assertLess(logdown[-1], linear[-1])
        exact = 10 / 0.3 * (1 - math.exp(-0.3 * 12))
        self.assertAlmostEqual(logdown[-1], exact, places=9)

    def test_aumc_log_down_matches_the_analytical_integral(self) -> None:
        t0, t1, c0 = 2.0, 6.0, 8.0
        k = 0.25
        c1 = c0 * math.exp(-k * (t1 - t0))
        _, aumc = nca._segment(t0, t1, c0, c1, "linup-logdown")
        grid = np.linspace(t0, t1, 200001)
        expected = float(np.trapezoid(grid * c0 * np.exp(-k * (grid - t0)), grid))
        self.assertAlmostEqual(aumc, expected, places=6)

    def test_partial_auc_matches_full_auc_over_the_whole_range(self) -> None:
        time = np.array([0.0, 1.0, 2.0, 4.0, 8.0])
        conc = np.array([0.0, 5.0, 9.0, 6.0, 3.0])
        cumulative, _ = nca.cumulative_auc(time, conc, "linup-logdown")
        self.assertAlmostEqual(nca.partial_auc(time, conc, 0.0, 8.0, "linup-logdown"), cumulative[-1], places=9)

    def test_blq_rules_change_the_result_as_documented(self) -> None:
        rows = [("A", 0, "BLQ"), ("A", 1, 5.0), ("A", 2, 9.0), ("A", 4, 6.0), ("A", 8, 3.0), ("A", 12, "BLQ")]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_csv(Path(tmpdir), "blq.csv", "id,time,conc", rows)
            zero = json.loads(
                run_script("nca", "-i", str(path), "--dose", "50", "--lloq", "1", "--blq-rule", "zero", "--format", "json").stdout
            )["tables"][0]["rows"][0]
            half = json.loads(
                run_script("nca", "-i", str(path), "--dose", "50", "--lloq", "1", "--blq-rule", "half-lloq", "--format", "json").stdout
            )["tables"][0]["rows"][0]
            self.assertGreater(half["auc_last"], zero["auc_last"])

    def test_flags_excessive_extrapolation(self) -> None:
        # Truncated profile: a large fraction of AUCinf comes from the tail.
        d = _models.disposition(cl=1.0, v1=40.0)
        t = np.array([0.0, 1.0, 2.0, 4.0, 6.0])
        c = _models.conc_bolus(t, 100.0, d)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_csv(Path(tmpdir), "trunc.csv", "id,time,conc", [(1, a, f"{b:.8g}") for a, b in zip(t, c)])
            result = run_script("nca", "-i", str(path), "--dose", "100", "--route", "iv-bolus")
            self.assertEqual(result.returncode, 1)
            self.assertIn("extrapolated", result.stderr)

    def test_steady_state_parameters(self) -> None:
        d = _models.disposition(cl=5.0, v1=40.0)
        tau = 12.0
        regimen = _models.build_regimen(500.0, interval=tau, n_doses=40)
        t = np.array([0, 0.5, 1, 2, 4, 6, 8, 10, 12], dtype=float) + 39 * tau
        c = _models.simulate_linear(t, regimen, d)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_csv(Path(tmpdir), "ss.csv", "id,time,conc", [(1, a - 39 * tau, f"{b:.8g}") for a, b in zip(t, c)])
            payload = json.loads(
                run_script("nca", "-i", str(path), "--dose", "500", "--tau", "12", "--route", "iv-bolus", "--format", "json").stdout
            )
            row = payload["tables"][0]["rows"][0]
            self.assertAlmostEqual(row["auc_tau"], 100.0, delta=1.0)
            self.assertAlmostEqual(row["cavg_ss"], 100.0 / 12.0, delta=0.1)

    def test_rejects_missing_dose(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_csv(Path(tmpdir), "nodose.csv", "id,time,conc", [(1, 0, 1.0), (1, 1, 2.0)])
            result = run_script("nca", "-i", str(path))
            self.assertEqual(result.returncode, _common.EXIT_INPUT)


# ------------------------------------------------------- compartmental fits


class TestCompartmentalFitting(unittest.TestCase):
    @staticmethod
    def two_compartment_data(tmp: Path) -> Path:
        d = _models.disposition(4.0, 12.0, (6.0,), (40.0,))
        t = np.array([0.083, 0.25, 0.5, 1, 1.5, 2, 3, 4, 6, 8, 12, 16, 24, 36, 48])
        rng = np.random.default_rng(7)
        c = _models.conc_bolus(t, 500.0, d) * np.exp(rng.normal(0, 0.08, len(t)))
        return write_csv(tmp, "two.csv", "time,conc", [(a, f"{b:.8g}") for a, b in zip(t, c)])

    def test_recovers_two_compartment_parameters(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self.two_compartment_data(Path(tmpdir))
            payload = json.loads(
                run_script(
                    "fit_compartmental", "-i", str(path), "--dose", "500",
                    "--route", "iv-bolus", "--model", "2cmt", "--format", "json",
                ).stdout
            )
            estimates = {r["parameter"]: r["estimate"] for r in payload["tables"][0]["rows"]}
            self.assertAlmostEqual(estimates["CL"], 4.0, delta=0.4)
            self.assertAlmostEqual(estimates["V1"], 12.0, delta=1.5)
            self.assertAlmostEqual(estimates["Q2"], 6.0, delta=1.5)
            self.assertAlmostEqual(estimates["V2"], 40.0, delta=5.0)

    def test_flags_unidentifiable_third_compartment(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self.two_compartment_data(Path(tmpdir))
            result = run_script(
                "fit_compartmental", "-i", str(path), "--dose", "500",
                "--route", "iv-bolus", "--model", "3cmt",
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("RSE", result.stderr)

    def test_f_test_rejects_the_third_compartment_and_accepts_the_second(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self.two_compartment_data(Path(tmpdir))
            payload = json.loads(
                run_script(
                    "fit_compartmental", "-i", str(path), "--dose", "500",
                    "--route", "iv-bolus", "--compare", "1cmt,2cmt,3cmt", "--format", "json",
                ).stdout
            )
            comparison = next(t for t in payload["tables"] if "model comparison" in t["title"])
            rows = {r["model"]: r for r in comparison["rows"]}
            self.assertLess(rows["2cmt"]["f_p_value"], 0.001)
            self.assertGreater(rows["3cmt"]["f_p_value"], 0.05)
            self.assertLess(rows["2cmt"]["bic"], rows["3cmt"]["bic"])

    def test_flags_structural_misspecification_via_runs_test(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self.two_compartment_data(Path(tmpdir))
            result = run_script(
                "fit_compartmental", "-i", str(path), "--dose", "500", "--route", "iv-bolus", "--model", "1cmt"
            )
            self.assertIn("residual signs are not random", result.stderr)


# --------------------------------------------------------- bioequivalence


class TestBioequivalence(unittest.TestCase):
    def test_sample_size_matches_published_table(self) -> None:
        """PowerTOST reference values: 2x2 crossover, GMR 0.95, 80% power."""
        for cv, expected in [(0.15, 12), (0.20, 20), (0.25, 28), (0.30, 40), (0.35, 52), (0.40, 66)]:
            with self.subTest(cv=cv):
                n, power = bioequivalence.sample_size(cv, 0.95, 0.80, "2x2")
                self.assertEqual(n, expected)
                self.assertGreaterEqual(power, 0.80)

    def test_power_is_monotone_in_sample_size(self) -> None:
        powers = [bioequivalence.tost_power(n, 0.30, 0.95) for n in (20, 30, 40, 60)]
        self.assertEqual(powers, sorted(powers))

    def test_abel_cap_is_exact(self) -> None:
        rv = bioequivalence.ReferenceVariability(s2wr=bioequivalence.s2_from_cv(0.50), df=30, n_subjects=30)
        low, high, widened = bioequivalence.abel_limits(rv)
        self.assertTrue(widened)
        self.assertAlmostEqual(100 * low, 69.84, places=2)
        self.assertAlmostEqual(100 * high, 143.19, places=2)

    def test_abel_does_not_widen_below_30_percent(self) -> None:
        rv = bioequivalence.ReferenceVariability(s2wr=bioequivalence.s2_from_cv(0.25), df=30, n_subjects=30)
        low, high, widened = bioequivalence.abel_limits(rv)
        self.assertFalse(widened)
        self.assertEqual((low, high), (0.80, 1.25))

    def test_cv_roundtrip(self) -> None:
        for cv in (0.1, 0.25, 0.5, 0.8):
            self.assertAlmostEqual(bioequivalence.cv_from_s2(bioequivalence.s2_from_cv(cv)), cv, places=12)

    def test_crossover_removes_the_period_effect(self) -> None:
        """A pure period effect must cancel, leaving the GMR at 1."""
        records = []
        for i in range(1, 21):
            sequence = "RT" if i % 2 else "TR"
            base = 100.0 * math.exp(0.3 * (i - 10) / 10)
            for period in (1, 2):
                treatment = sequence[period - 1]
                value = base * (1.20 if period == 2 else 1.0)  # 20% period effect, no treatment effect
                records.append(
                    {
                        "subject": str(i),
                        "treatment": treatment,
                        "value": value,
                        "logvalue": math.log(value),
                        "sequence": sequence,
                        "period": str(period),
                    }
                )
        result = bioequivalence.crossover_2x2(records)
        self.assertAlmostEqual(result.gmr, 1.0, places=9)

    def test_scaling_refused_without_a_replicate_design(self) -> None:
        rows = [(i, "RT" if i % 2 else "TR", p, ("RT" if i % 2 else "TR")[p - 1], 100 + i) for i in range(1, 13) for p in (1, 2)]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_csv(Path(tmpdir), "be.csv", "subject,sequence,period,treatment,value", rows)
            result = run_script("bioequivalence", "-i", str(path), "--design", "2x2", "--scaling", "abel")
            self.assertEqual(result.returncode, _common.EXIT_INPUT)
            self.assertIn("replicate", result.stderr)

    def test_reference_variability_needs_replicated_reference(self) -> None:
        records = [
            {"subject": "1", "treatment": "R", "logvalue": 1.0},
            {"subject": "1", "treatment": "T", "logvalue": 1.1},
        ]
        with self.assertRaises(_common.InputError):
            bioequivalence.reference_variability(records)

    def test_rsabe_bound_passes_when_difference_is_small_and_cvwr_high(self) -> None:
        rv = bioequivalence.ReferenceVariability(s2wr=bioequivalence.s2_from_cv(0.45), df=40, n_subjects=40)
        passing = bioequivalence.rsabe_bound(estimate=math.log(0.98), se=0.05, df_point=40, rv=rv)
        self.assertTrue(passing["passes_scaled_criterion"])
        failing = bioequivalence.rsabe_bound(estimate=math.log(0.60), se=0.05, df_point=40, rv=rv)
        self.assertFalse(failing["passes_scaled_criterion"])

    def test_nti_limits_applied(self) -> None:
        rows = [(i, "RT" if i % 2 else "TR", p, ("RT" if i % 2 else "TR")[p - 1], 100 + (i % 3)) for i in range(1, 25) for p in (1, 2)]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_csv(Path(tmpdir), "nti.csv", "subject,sequence,period,treatment,value", rows)
            payload = json.loads(
                run_script("bioequivalence", "-i", str(path), "--design", "2x2", "--nti", "--format", "json").stdout
            )
            self.assertEqual(payload["scalars"]["acceptance_limits_pct"], "90.00-111.11")


# --------------------------------------------------- allometry and FIH dose


class TestAllometryAndFIH(unittest.TestCase):
    def test_fda_conversion_factors(self) -> None:
        """FDA 2005 guidance Table 1: divide animal mg/kg by these to get HED."""
        for species, divisor in [("mouse", 12.3), ("rat", 6.2), ("dog", 1.85), ("monkey", 3.08), ("rabbit", 3.08)]:
            with self.subTest(species=species):
                hed = allometry_and_fih.hed_mg_per_kg(10.0, species)
                self.assertAlmostEqual(10.0 / hed, divisor, places=1)

    def test_mrsd_uses_the_most_sensitive_species(self) -> None:
        result = run_script("allometry_and_fih", "--fih", "--noael", "rat=50,dog=10", "--safety-factor", "10", "--format", "json")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["scalars"]["lowest_hed_species"], "dog")
        self.assertAlmostEqual(payload["scalars"]["mrsd_mg_kg"], 10.0 * 20 / 37 / 10, places=6)

    def test_maturation_is_monotone_and_bounded(self) -> None:
        values = [allometry_and_fih.maturation_fraction(pma) for pma in (30, 40, 54.2, 80, 200)]
        self.assertEqual(values, sorted(values))
        self.assertAlmostEqual(values[2], 0.5, places=6)
        self.assertLess(values[-1], 1.0)
        self.assertGreater(values[-1], 0.95)

    def test_allometric_scaling(self) -> None:
        self.assertAlmostEqual(allometry_and_fih.allometric(5.0, 70.0, 35.0, 0.75), 5.0 * 0.5**0.75, places=12)

    def test_neonate_without_maturation_raises_a_finding(self) -> None:
        result = run_script("allometry_and_fih", "--scale", "--cl", "5", "--weight-from", "70", "--weight-to", "6")
        self.assertEqual(result.returncode, 1)
        self.assertIn("maturation", result.stderr)

    def test_exponent_regression_recovers_a_known_slope(self) -> None:
        weights = np.array([0.02, 0.15, 1.8, 10.0, 70.0])
        values = 0.5 * weights**0.75
        fit = allometry_and_fih.fit_exponent(weights, values)
        self.assertAlmostEqual(fit["exponent"], 0.75, places=8)
        self.assertAlmostEqual(fit["coefficient"], 0.5, places=8)
        self.assertAlmostEqual(fit["r2"], 1.0, places=10)

    def test_rule_of_exponents_bands(self) -> None:
        self.assertIn("simple allometry", allometry_and_fih.rule_of_exponents(0.65))
        self.assertIn("lifespan", allometry_and_fih.rule_of_exponents(0.85))
        self.assertIn("brain-weight", allometry_and_fih.rule_of_exponents(1.10))

    def test_unknown_species_rejected(self) -> None:
        with self.assertRaises(_common.InputError):
            allometry_and_fih.hed_mg_per_kg(10.0, "capybara")


# ----------------------------------------------------------- DDI static


class TestDDIStatic(unittest.TestCase):
    def test_basic_reversible_ratio(self) -> None:
        self.assertAlmostEqual(ddi_static.r1_reversible(0.1, 0.5), 1.2, places=12)

    def test_tdi_ratio_reduces_to_one_without_inactivation(self) -> None:
        self.assertAlmostEqual(ddi_static.r2_time_dependent(0.0, 1.0, 0.05, 0.0005), 1.0, places=12)

    def test_induction_ratio_below_one(self) -> None:
        r3 = ddi_static.r3_induction(10.0, emax=5.0, ec50=1.0)
        self.assertLess(r3, 1.0)
        self.assertGreater(r3, 0.0)

    def test_mechanistic_static_model_matches_hand_calculation(self) -> None:
        result = ddi_static.mechanistic_static(ih=0.1, ig=1.6, fm=0.9, fg=0.7, ki=0.5)
        self.assertAlmostEqual(result["Ah_reversible"], 1 / 1.2, places=12)
        self.assertAlmostEqual(result["Ag_reversible"], 1 / 4.2, places=12)
        self.assertAlmostEqual(result["hepatic_component"], 1 / (0.9 / 1.2 + 0.1), places=12)
        self.assertAlmostEqual(result["gut_component"], 1 / ((1 / 4.2) * 0.3 + 0.7), places=12)
        self.assertAlmostEqual(result["auc_ratio"], result["gut_component"] * result["hepatic_component"], places=12)

    def test_auc_ratio_cannot_exceed_the_fm_ceiling(self) -> None:
        for fm in (0.5, 0.7, 0.9):
            result = ddi_static.mechanistic_static(ih=1e6, ig=0.0, fm=fm, fg=1.0, ki=0.5)
            self.assertLessEqual(result["auc_ratio"], 1 / (1 - fm) + 1e-6)
            self.assertAlmostEqual(result["maximum_possible_auc_ratio"], 1 / (1 - fm), places=9)

    def test_no_perpetrator_gives_unity(self) -> None:
        result = ddi_static.mechanistic_static(ih=0.0, ig=0.0, fm=0.9, fg=0.7, ki=0.5)
        self.assertAlmostEqual(result["auc_ratio"], 1.0, places=12)

    def test_classification_bands(self) -> None:
        self.assertIn("strong inhibitor", ddi_static.classify(6.0))
        self.assertIn("moderate inhibitor", ddi_static.classify(3.0))
        self.assertIn("weak inhibitor", ddi_static.classify(1.5))
        self.assertIn("0.8-1.25", ddi_static.classify(1.0))
        self.assertIn("strong inducer", ddi_static.classify(0.1))


# ------------------------------------------------------- exposure-response


class TestExposureResponse(unittest.TestCase):
    def test_emax_recovers_known_parameters(self) -> None:
        conc = np.array([0, 0.5, 1, 2, 4, 8, 16, 32, 64, 128], dtype=float)
        response = _models.emax(conc, e0=5.0, emax_value=100.0, ec50=8.0)
        fit = exposure_response.fit_emax(conc, response, sigmoid=False)
        self.assertAlmostEqual(fit["e0"], 5.0, places=4)
        self.assertAlmostEqual(fit["emax"], 100.0, places=3)
        self.assertAlmostEqual(fit["ec50"], 8.0, places=4)

    def test_sigmoid_emax_recovers_the_hill_coefficient(self) -> None:
        conc = np.logspace(-1, 2.5, 24)
        response = _models.emax(conc, e0=2.0, emax_value=50.0, ec50=10.0, hill=2.5)
        fit = exposure_response.fit_emax(conc, response, sigmoid=True)
        self.assertAlmostEqual(fit["hill"], 2.5, places=3)
        self.assertAlmostEqual(fit["ec50"], 10.0, places=3)

    def test_flags_a_plateau_outside_the_data(self) -> None:
        conc = np.linspace(0.1, 3.0, 12)
        response = _models.emax(conc, e0=0.0, emax_value=100.0, ec50=50.0)
        rows = [(f"{c:.6g}", f"{r:.6g}") for c, r in zip(conc, response)]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_csv(Path(tmpdir), "er.csv", "exposure,response", rows)
            result = run_script("exposure_response", "--emax", "-i", str(path))
            self.assertEqual(result.returncode, 1)
            self.assertIn("Emax", result.stderr)

    def test_cqtc_matches_ordinary_least_squares(self) -> None:
        conc = np.array([0.0, 50.0, 100.0, 150.0, 200.0, 250.0])
        delta = 1.0 + 0.02 * conc
        fit = exposure_response.fit_cqtc(conc, delta, cmax=200.0)
        self.assertAlmostEqual(fit["slope_ms_per_conc"], 0.02, places=10)
        self.assertAlmostEqual(fit["intercept_ms"], 1.0, places=10)
        self.assertAlmostEqual(fit["predicted_delta_delta_qtc_ms"], 5.0, places=10)

    def test_cqtc_flags_extrapolation_and_the_10ms_threshold(self) -> None:
        conc = np.array([0.0, 50.0, 100.0, 150.0, 200.0, 250.0])
        delta = 1.0 + 0.06 * conc
        fit = exposure_response.fit_cqtc(conc, delta, cmax=400.0)
        self.assertEqual(fit["extrapolated_beyond_observed"], 1.0)
        self.assertEqual(fit["upper_bound_exceeds_10ms"], 1.0)

    def test_logistic_slope_sign(self) -> None:
        rng = np.random.default_rng(3)
        conc = rng.uniform(0, 100, 300)
        response = (rng.uniform(0, 1, 300) < 1 / (1 + np.exp(-(conc - 50) / 15))).astype(float)
        fit = exposure_response.fit_logistic(conc, response)
        self.assertGreater(fit["slope"], 0.0)
        self.assertAlmostEqual(fit["exposure_at_50pct_probability"], 50.0, delta=12.0)

    def test_logistic_rejects_non_binary(self) -> None:
        with self.assertRaises(_common.InputError):
            exposure_response.fit_logistic(np.array([1.0, 2.0]), np.array([0.0, 3.0]))

    def test_quartile_summary_is_ordered(self) -> None:
        exposure = np.arange(1.0, 41.0)
        response = 2.0 * exposure
        rows = exposure_response.quartile_summary(exposure, response, 4)
        self.assertEqual(len(rows), 4)
        self.assertEqual([r["n"] for r in rows], [10, 10, 10, 10])
        means = [r["mean_response"] for r in rows]
        self.assertEqual(means, sorted(means))


# ------------------------------------------------------ popPK dataset check


class TestPopPKDatasetCheck(unittest.TestCase):
    def test_catches_planted_defects(self) -> None:
        result = run_script("check_popk_dataset", "-i", str(FIXTURES / "broken_nmdata.csv"), "--covariates", "WT,CRCL", "--format", "json")
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        checks = {row["check"] for row in payload["tables"][0]["rows"]}
        for expected in (
            "non-numeric DV",
            "TIME not sorted",
            "subject with no dose",
            "covariate WT missing",
            "duplicate TIME within a subject",
        ):
            self.assertIn(expected, checks)

    def test_clean_dataset_passes(self) -> None:
        result = run_script("check_popk_dataset", "-i", str(FIXTURES / "clean_nmdata.csv"), "--covariates", "WT")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("all checks passed", result.stdout)

    def test_addl_without_ii_is_an_error(self) -> None:
        rows = [
            ("1", 0, 100, ".", 1, 1, 1, 5),
            ("1", 1, ".", 5.0, 0, 0, 1, ""),
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_csv(Path(tmpdir), "addl.csv", "ID,TIME,AMT,DV,EVID,MDV,CMT,ADDL", rows)
            result = run_script("check_popk_dataset", "-i", str(path), "--format", "json")
            payload = json.loads(result.stdout)
            checks = {row["check"] for row in payload["tables"][0]["rows"]}
            self.assertIn("ADDL without II", checks)

    def test_strict_mode_fails_on_warnings(self) -> None:
        result = run_script("check_popk_dataset", "-i", str(FIXTURES / "clean_nmdata.csv"), "--strict")
        self.assertIn(result.returncode, (0, 1))


# --------------------------------------------------------- TDM and simulation


class TestTDMAndSimulation(unittest.TestCase):
    def test_map_recovers_a_known_individual(self) -> None:
        """Levels simulated from known individual parameters must be recovered."""
        cl_true, v_true = 5.0, 50.0
        dose, interval, infusion = 1000.0, 12.0, 1.0
        disp = _models.disposition(cl_true, v_true)
        regimen = _models.build_regimen(dose, interval=interval, n_doses=20, duration=infusion)
        times = np.array([2.0, 11.0])
        observed = _models.simulate_linear(times + 19 * interval, regimen, disp)
        args = [
            "tdm_bayes", "--custom", "--cl-pop", "4.0", "--v-pop", "45.0",
            "--omega-cl", "0.5", "--omega-v", "0.5", "--prop-error", "0.05", "--add-error", "0.1",
            "--dose", str(dose), "--interval", str(interval), "--infusion", str(infusion),
            "--doses-given", "20", "--format", "json",
        ]
        for time, conc in zip(times, observed):
            args.extend(["--level", f"{conc:.6f}@{time}"])
        payload = json.loads(run_script(*args).stdout)
        self.assertAlmostEqual(payload["scalars"]["individual_cl"], cl_true, delta=0.4)
        self.assertAlmostEqual(payload["scalars"]["individual_v"], v_true, delta=6.0)

    def test_single_level_raises_a_finding(self) -> None:
        result = run_script(
            "tdm_bayes", "--custom", "--cl-pop", "4", "--v-pop", "45",
            "--dose", "1000", "--interval", "12", "--level", "12@11",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("single concentration", result.stderr)

    def test_level_beyond_the_interval_rejected(self) -> None:
        result = run_script(
            "tdm_bayes", "--custom", "--cl-pop", "4", "--v-pop", "45",
            "--dose", "1000", "--interval", "12", "--level", "12@20",
        )
        self.assertEqual(result.returncode, _common.EXIT_INPUT)

    def test_simulate_regimen_matches_closed_form_steady_state(self) -> None:
        payload = json.loads(
            run_script(
                "simulate_regimen", "--cl", "5", "--v", "40", "--dose", "500",
                "--interval", "12", "--n-doses", "10", "--steady-state", "--format", "json",
            ).stdout
        )
        summary = next(t for t in payload["tables"] if "dosing-interval" in t["title"])
        last = next(r for r in summary["rows"] if str(r["interval"]).startswith("last"))
        self.assertAlmostEqual(last["auc_tau"], 100.0, places=4)
        self.assertAlmostEqual(last["cmax"], 12.5 / (1 - math.exp(-0.125 * 12)), places=4)
        self.assertAlmostEqual(last["cmin"], last["cmax"] * math.exp(-0.125 * 12), places=4)

    def test_accumulation_ratio_is_consistent_across_metrics(self) -> None:
        payload = json.loads(
            run_script(
                "simulate_regimen", "--cl", "5", "--v", "40", "--dose", "500",
                "--interval", "12", "--n-doses", "10", "--format", "json",
            ).stdout
        )
        summary = next(t for t in payload["tables"] if "dosing-interval" in t["title"])
        row = next(r for r in summary["rows"] if str(r["interval"]).startswith("accumulation"))
        expected = 1 / (1 - math.exp(-0.125 * 12))
        for key in ("auc_tau", "cmax", "cmin", "cavg"):
            self.assertAlmostEqual(row[key], expected, places=4, msg=key)

    def test_monte_carlo_attainment_is_a_fraction(self) -> None:
        payload = json.loads(
            run_script(
                "simulate_regimen", "--cl", "5", "--v", "40", "--dose", "500", "--interval", "12",
                "--n-doses", "10", "--simulate", "400", "--omega-cl", "0.35", "--target-trough", "4.0",
                "--format", "json",
            ).stdout
        )
        attainment = next(t for t in payload["tables"] if "target attainment" in t["title"])
        fraction = attainment["rows"][0]["fraction_attaining"]
        self.assertGreaterEqual(fraction, 0.0)
        self.assertLessEqual(fraction, 1.0)

    def test_regimen_comparison_preserves_cavg_for_equal_daily_dose(self) -> None:
        payload = json.loads(
            run_script("simulate_regimen", "--cl", "5", "--v", "40", "--compare", "500@12,250@6", "--format", "json").stdout
        )
        rows = payload["tables"][0]["rows"]
        self.assertAlmostEqual(rows[0]["cavg_ss"], rows[1]["cavg_ss"], places=9)
        self.assertGreater(rows[0]["ptf_pct"], rows[1]["ptf_pct"])

    def test_mismatched_peripheral_arguments_rejected(self) -> None:
        result = run_script("simulate_regimen", "--cl", "5", "--v", "40", "--q", "3", "--dose", "100")
        self.assertEqual(result.returncode, _common.EXIT_INPUT)


# ------------------------------------------------------------- CLI contract


class TestCLIContract(unittest.TestCase):
    """Every script shares one exit-code and stream contract."""

    def test_json_output_is_parseable_and_self_contained(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = analytical_oral_profile(Path(tmpdir))
            result = run_script("nca", "-i", str(path), "--dose", "100", "--format", "json")
            payload = json.loads(result.stdout)
            for key in ("scalars", "tables", "findings", "notes"):
                self.assertIn(key, payload)
            self.assertEqual(result.stderr, "", "json format must not also write to stderr")

    def test_tsv_output_has_no_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = analytical_oral_profile(Path(tmpdir))
            result = run_script("nca", "-i", str(path), "--dose", "100", "--format", "tsv")
            self.assertNotIn("note:", result.stdout)
            self.assertIn("note:", result.stderr)

    def test_missing_input_file_exits_two(self) -> None:
        result = run_script("nca", "-i", "/nonexistent/nope.csv", "--dose", "100")
        self.assertEqual(result.returncode, _common.EXIT_INPUT)
        self.assertIn("error:", result.stderr)

    def test_duplicate_columns_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "dupe.csv"
            path.write_text("time,conc,conc\n0,1,2\n1,2,3\n", encoding="utf-8")
            with self.assertRaises(_common.InputError):
                _common.read_table(path)

    def test_comment_lines_and_blank_lines_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "commented.csv"
            path.write_text("# provenance header\n\ntime,conc\n0,1\n1,2\n", encoding="utf-8")
            rows = _common.read_table(path)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["time"], "0")

    def test_tsv_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "data.tsv"
            path.write_text("time\tconc\n0\t1\n1\t2\n", encoding="utf-8")
            rows = _common.read_table(path)
            self.assertEqual(rows[1]["conc"], "2")

    def test_column_names_are_case_insensitive(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "upper.csv"
            path.write_text("TIME,CONC\n0,1\n1,2\n", encoding="utf-8")
            rows = _common.read_table(path)
            self.assertIn("time", rows[0])

    def test_report_exit_codes(self) -> None:
        report = _common.Report()
        report.table("t", [{"a": 1}])
        self.assertEqual(report.emit("json", stream=open("/dev/null", "w")), _common.EXIT_OK)
        report.finding("something")
        self.assertEqual(report.emit("json", stream=open("/dev/null", "w")), _common.EXIT_FINDINGS)


if __name__ == "__main__":
    unittest.main()


class TestRefreshRegressions(unittest.TestCase):
    """Independent arithmetic and fail-closed checks for clinically relevant errors."""

    def payload(self, script, *args):
        result = run_script(script, *args, "--format", "json")
        self.assertIn(result.returncode, (0, 1), result.stderr)
        return json.loads(result.stdout)

    def test_m12_tdi_uses_five_times_unbound_cmax(self):
        payload = self.payload("ddi_static", "--basic", "--tdi", "--imax", "2", "--fu", "0.1", "--ki-inact", "1", "--kinact", "0.02", "--kdeg", "0.001")
        row = payload["tables"][0]["rows"][0]
        self.assertAlmostEqual(row["value"], 11.0)  # I=1, kobs=.01/min

    def test_inlet_converts_minutes_to_hours(self):
        value = ddi_static.inlet_concentration(imax=2, fu=.1, dose=100, fa=.8, fg=.5, ka=.1, blood_ratio=1)
        self.assertAlmostEqual(value, .1 * (2 + .8*.5*6*100/97))

    def test_mate_cutoff_differs_from_oat_oct(self):
        results = []
        for transporter in ("mate", "renal", "systemic-efflux"):
            p = self.payload("ddi_static", "--basic", "--transporter", transporter, "--transporter-ki", "1", "--imax", ".3", "--fu", ".1")
            results.append(p["tables"][0]["rows"][0]["triggers_study"])
        self.assertEqual(results, [True, False, True])

    def test_fu_floor_requires_measured_reliability(self):
        args = ("--basic", "--ki", "1", "--imax", "1", "--fu", ".001")
        floor = self.payload("ddi_static", *args)
        measured = self.payload("ddi_static", *args, "--fu-validated")
        self.assertEqual(floor["scalars"]["imax_unbound"], .01)
        self.assertEqual(measured["scalars"]["imax_unbound"], .001)

    def test_combined_gut_hepatic_ceiling(self):
        fit = ddi_static.mechanistic_static(ih=1e10, ig=1e10, fm=.8, fg=.5, ki=1)
        self.assertAlmostEqual(fit["maximum_possible_auc_ratio"], 10)
        self.assertAlmostEqual(fit["hepatic_only_auc_ceiling"], 5)
        self.assertAlmostEqual(fit["auc_ratio"], 10, places=6)

    def test_msm_invalid_fractions_rejected(self):
        for fm, fg in ((1.1,.5), (.5,0), (.5,1.1)):
            with self.assertRaises(_common.InputError):
                ddi_static.mechanistic_static(ih=1, ig=1, fm=fm, fg=fg)

    def test_msm_uses_inlet_and_enterocyte_concentrations(self):
        p = self.payload("ddi_static", "--msm", "--ki", ".5", "--imax", "2", "--fu", ".1", "--dose", "100", "--fm", ".8", "--fg", ".5")
        # Default Fa=Fg_perpetrator=RB=1, ka=.1/min, Qh=97, Qen=18 L/h.
        values = p["scalars"]
        self.assertAlmostEqual(values["msm_hepatic_inlet_unbound"], .1*(2+600/97))
        self.assertAlmostEqual(values["msm_enterocyte_concentration"], 600/18)

    def test_manual_lambda_predicts_at_actual_last_quantifiable_time(self):
        t = np.arange(0., 7.)
        c = 10*np.exp(-.2*t)
        fit = nca.estimate_lambda_z(t, c, np.zeros(len(t), dtype=bool), 0., manual=(1.,4.))
        self.assertAlmostEqual(fit.clast_pred, c[-1], places=12)
        self.assertEqual(fit.t_last, 4.)

    def test_manual_rising_terminal_slope_not_reported_as_half_life(self):
        t = np.arange(5.)
        c = np.array([100,1,2,3,4.])
        fit = nca.estimate_lambda_z(t, c, np.zeros(5,dtype=bool), 0., manual=(1,4))
        self.assertIsNone(fit.lam)

    def test_partial_auc_cannot_extrapolate_unobserved_early_or_late_area(self):
        t=np.array([1.,2.,3.]); c=np.array([3.,2.,1.])
        for start,end in ((0,2),(1,4)):
            with self.assertRaises(_common.InputError):
                nca.partial_auc(t,c,start,end,"linear")

    def test_nca_steady_state_withholds_single_dose_parameters(self):
        with tempfile.TemporaryDirectory() as td:
            path=write_csv(Path(td),"ss.csv","time,conc", [(t, 10*math.exp(-.2*t)) for t in range(13)])
            p=self.payload("nca","-i",str(path),"--dose","100","--route","iv-bolus","--tau","12")
            row=p["tables"][0]["rows"][0]
            self.assertIn("auc_tau",row)
            self.assertIn("cl_ss",row)
            for key in ("auc_inf_obs","auc_inf_pred","cl","vz","vss"):
                self.assertNotIn(key,row)

    def test_nca_rejects_negative_concentration_and_duplicate_time(self):
        for rows in ([(0,10),(1,-2),(2,1)], [(0,10),(1,5),(1,4)]):
            with tempfile.TemporaryDirectory() as td:
                path=write_csv(Path(td),"bad.csv","time,conc",rows)
                result=run_script("nca","-i",str(path),"--dose","100")
                self.assertEqual(result.returncode,2,result.stderr)
                self.assertNotIn("Traceback",result.stderr)

    def test_multicompartment_auc_accumulation_uses_interval_auc(self):
        d=_models.disposition(5,20,(3,),(100,))
        tau=12.; t=np.linspace(0,tau,100001)
        first_auc=float(np.trapezoid(_models.conc_bolus(t,100,d),t))
        expected=(100/5)/first_auc
        self.assertAlmostEqual(_models.steady_state_metrics(d,100,tau)["accumulation_ratio_auc"],expected,places=8)

    def test_unsupported_oral_closed_form_summary_is_rejected(self):
        result=run_script("simulate_regimen","--cl","5","--v","40","--dose","100","--interval","12","--route","oral","--ka","1","--steady-state")
        self.assertEqual(result.returncode,2)

    def test_transit_cannot_silently_ignore_post_transit_ka(self):
        with self.assertRaises(ValueError):
            _models.conc_transit(np.array([0.,1.,2.]),100,2,3,_models.disposition(5,20),ka=1.)

    def test_exact_tdm_steady_state_for_extremely_long_half_life(self):
        import tdm_bayes
        fit=tdm_bayes.exposure_metrics(cl=.001,v=100,dose=10,interval=12,infusion=1)
        self.assertAlmostEqual(fit["auc_24h"],20000.,places=7)

    def test_strict_json_uses_null_for_missing_diagnostics(self):
        p=_common._json_finite({"x":float("nan"),"y":np.array([1.,float("inf")])})
        self.assertEqual(p,{"x":None,"y":[1.,None]})
        json.dumps(p,allow_nan=False)

    def test_nonfinite_csv_and_cli_inputs_are_rejected(self):
        with self.assertRaises(_common.InputError):
            _common.parse_float("inf","concentration")
        result=run_script("simulate_regimen","--cl","nan","--v","40","--dose","100","--interval","12")
        self.assertEqual(result.returncode,2)

    def test_fda_scalar_bound_includes_bias_correction_and_upper_chi_quantile(self):
        from scipy.stats import chi2,t
        est,se,df=.05,.07,24
        rv=bioequivalence.ReferenceVariability(s2wr=.16,df=22,n_subjects=24)
        x=est*est-se*se; y=-(math.log(1.25)/.25)**2*.16
        bx=(abs(est)+t.ppf(.95,df)*se)**2; by=y*22/chi2.ppf(.95,22)
        expected=x+y+math.hypot(bx-x,by-y)
        result=bioequivalence.rsabe_bound(est,se,df,rv)
        self.assertAlmostEqual(result["criterion_point_estimate"],x+y)
        self.assertAlmostEqual(result["criterion_95_upper_bound"],expected)

    def test_replicate_analysis_and_power_fail_closed(self):
        result=run_script("bioequivalence","--design","replicate","--power","--cv",".3")
        self.assertEqual(result.returncode,2)
        with self.assertRaises(_common.InputError):
            bioequivalence.tost_power(24,.3,.95,"replicate")

    def test_sequence_period_mismatch_is_rejected(self):
        records=[{"subject":str(i),"sequence":seq,"period":str(j+1),"treatment":trt,"logvalue":1.} for i,seq in enumerate(("RT","TR")) for j,trt in enumerate(seq)]
        records[0]["sequence"]="TR"
        with self.assertRaises(_common.InputError):
            bioequivalence.crossover_2x2(records)

    def test_parallel_repeated_subjects_are_rejected(self):
        records=[{"subject":"1","treatment":trt,"logvalue":1.} for trt in ("T","T","R","R")]
        with self.assertRaises(_common.InputError):
            bioequivalence.parallel_design(records)

    def test_logistic_separation_is_rejected(self):
        with self.assertRaises(_common.InputError):
            exposure_response.fit_logistic(np.arange(6.),np.array([0.,0.,0.,1.,1.,1.]))

    def test_constant_exposure_has_no_estimable_qtc_slope(self):
        with self.assertRaises(_common.InputError):
            exposure_response.fit_cqtc(np.ones(5),np.arange(5.),cmax=1.)

    def test_reset_and_constant_ss_infusion_are_valid_events(self):
        import check_popk_dataset as checker
        rows=[dict(ID="1",TIME="0",DV=".",AMT="0",EVID="1",MDV="1",RATE="5",SS="1",II="0"),
              dict(ID="1",TIME="5",DV="1",AMT="0",EVID="0",MDV="0",RATE="0",SS="0",II="0"),
              dict(ID="1",TIME="0",DV=".",AMT="100",EVID="4",MDV="1",RATE="-1",SS="0",II="0"),
              dict(ID="1",TIME="2",DV="2",AMT="0",EVID="0",MDV="0",RATE="0",SS="0",II="0")]
        args=checker.build_parser().parse_args(["-i","unused.csv"])
        findings,_=checker.check_dataset(rows,args)
        checks={v["check"] for v in findings.items if v["severity"]=="error"}
        self.assertFalse({"SS without II","dose without AMT","TIME not monotonic","invalid RATE"}&checks,checks)

    def test_dataset_nonfinite_rate_and_discontinuous_ids_are_flagged(self):
        import check_popk_dataset as checker
        rows=[dict(ID=str(i),TIME="0",DV="1",AMT="0",EVID="0",MDV="0",RATE="inf") for i in (1,2,1)]
        args=checker.build_parser().parse_args(["-i","unused.csv"])
        findings,_=checker.check_dataset(rows,args)
        checks={v["check"] for v in findings.items}
        self.assertTrue({"invalid RATE","noncontiguous ID"}<=checks)

    def test_emax_rank_deficiency_with_two_distinct_exposures(self):
        x=np.array([0.,0.,0.,0.,1.,1.,1.,1.])
        fit=exposure_response.fit_emax(x,1.+2*x,sigmoid=True)
        self.assertFalse(fit["identifiable_local_covariance"])
        self.assertTrue(math.isnan(fit["se_emax"]))

    def test_qss_high_target_root_preserves_drug_mass(self):
        total_drug=np.array([0.,1e-6,1.]); total_target=1e12; kss=1.
        free=_models._qss_free(total_drug,total_target,kss)
        complex_=total_target*free/(kss+free)
        np.testing.assert_allclose(free+complex_,total_drug,rtol=1e-12,atol=0)
        self.assertGreater(free[-1],0.)
