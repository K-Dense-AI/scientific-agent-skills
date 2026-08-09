"""Core hydraulics tests for the microfluidic-design skill.

Everything runs offline against hand-checkable analytical values: the exact
rectangular-resistance series against the published square-channel coefficient,
network reduction against series/parallel algebra, and the CLI output contract
(pure JSON on stdout, caveats on stderr, exit codes 0/1/2).

    uv run --with pytest python -m pytest tests/microfluidic-design -q
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

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "microfluidic-design"
SCRIPTS_DIR = SKILL_ROOT / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load_script(name: str):
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


common = _load_script("_common")


def run_script(name: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / f"{name}.py"), *args],
        capture_output=True, text=True, check=False,
    )


# ---------------------------------------------------------------- structure


class TestSkillStructure(unittest.TestCase):
    def test_skill_md_frontmatter(self):
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        front = text[4:text.index("\n---\n", 4)]
        self.assertIn("name: microfluidic-design", front)
        self.assertRegex(front, r'\n  version: "\d+\.\d+"\n')
        for line in front.splitlines():
            if line.startswith("allowed-tools:"):
                self.assertNotIn(",", line)
                self.assertNotIn("[", line)

    def test_skill_md_under_500_lines(self):
        lines = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8").splitlines()
        self.assertLess(len(lines), 500, f"SKILL.md has {len(lines)} lines")

    def test_referenced_files_exist(self):
        for rel in (
            "references/governing-equations.md",
            "references/mixing-and-mass-transport.md",
            "references/droplet-design.md",
            "references/particle-and-cell-manipulation.md",
            "references/electrokinetics.md",
            "references/acoustofluidics.md",
            "references/capillary-and-paper.md",
            "references/centrifugal-and-digital.md",
            "references/valves-pumps-flow-control.md",
            "references/thermal-design.md",
            "references/cell-culture-organ-on-chip.md",
            "references/sensing-and-detection.md",
            "references/fabrication-methods.md",
            "references/source-ledger.md",
            "assets/design-checklist.md",
            "assets/example-network.json",
            "assets/fluid-and-material-data.md",
        ):
            self.assertTrue((SKILL_ROOT / rel).is_file(), f"missing {rel}")


# ------------------------------------------------------------- unit parsing


class TestUnits(unittest.TestCase):
    def test_common_units(self):
        self.assertAlmostEqual(common.parse_quantity("100um", "length"), 100e-6)
        self.assertAlmostEqual(common.parse_quantity("10 uL/min", "flow"), 1e-8 / 60)
        self.assertAlmostEqual(common.parse_quantity("5 kPa", "pressure"), 5000.0)
        self.assertAlmostEqual(common.parse_quantity("0.89 mPa.s", "viscosity"), 8.9e-4)
        self.assertAlmostEqual(common.parse_quantity("5 mN/m", "tension"), 5e-3)
        self.assertAlmostEqual(common.parse_quantity("3000 rpm", "spin"),
                               3000 * 2 * math.pi / 60)
        self.assertAlmostEqual(common.parse_quantity("100 V/cm", "efield"), 1e4)

    def test_unknown_unit_raises(self):
        with self.assertRaises(common.InputError):
            common.parse_quantity("5 parsec", "length")

    def test_fluid_table(self):
        fluid = common.fluid_properties("water", 25.0)
        self.assertAlmostEqual(fluid["viscosity"], 0.890e-3)
        self.assertAlmostEqual(fluid["density"], 997.0)


# --------------------------------------------------------------- resistance


class TestResistance(unittest.TestCase):
    MU, L = 1e-3, 1e-2

    def test_square_channel_coefficient(self):
        """Bruus 2008: square channel R = 28.4 * mu * L / h^4 (3 sig figs)."""
        h = 100e-6
        coeff = common.rect_resistance(self.MU, self.L, h, h) * h ** 4 / (self.MU * self.L)
        self.assertAlmostEqual(coeff, 28.45, delta=0.03)

    def test_wide_channel_limit(self):
        h, w = 50e-6, 100 * 50e-6
        exact = common.rect_resistance(self.MU, self.L, w, h)
        plate = 12 * self.MU * self.L / (w * h ** 3)
        self.assertLess(abs(exact / plate - 1.0), 0.01)

    def test_symmetry_under_swap(self):
        a = common.rect_resistance(self.MU, self.L, 200e-6, 50e-6)
        b = common.rect_resistance(self.MU, self.L, 50e-6, 200e-6)
        self.assertEqual(a, b)

    def test_approximation_error_small_at_half_aspect(self):
        exact = common.rect_resistance(self.MU, self.L, 100e-6, 50e-6)
        approx = common.rect_resistance_approx(self.MU, self.L, 100e-6, 50e-6)
        self.assertLess(abs(approx / exact - 1.0), 0.005)

    def test_circular_hagen_poiseuille(self):
        r = 50e-6
        self.assertAlmostEqual(common.circ_resistance(self.MU, self.L, r),
                               8 * self.MU * self.L / (math.pi * r ** 4))

    def test_wall_shear_hand_value(self):
        # tau = 6 mu Q / (w h^2)
        tau = common.wall_shear(1e-3, 1e-9, 1e-3, 1e-4)
        self.assertAlmostEqual(tau, 6 * 1e-3 * 1e-9 / (1e-3 * 1e-8))


class TestChannelCli(unittest.TestCase):
    def _json(self, *args: str) -> tuple[dict, subprocess.CompletedProcess]:
        result = run_script("channel_resistance", *args, "--format", "json")
        payload = json.loads(result.stdout) if result.stdout else {}
        return payload, result

    def test_target_shear_round_trip(self):
        payload, result = self._json(
            "channel", "--width", "1mm", "--height", "100um", "--length", "1cm",
            "--fluid", "water", "--temp", "37", "--target-shear", "1 Pa")
        self.assertEqual(result.returncode, 0)
        self.assertAlmostEqual(payload["wall_shear_pa"], 1.0, places=9)
        # Q = tau w h^2 / (6 mu)
        q_expect = 1.0 * 1e-3 * (1e-4) ** 2 / (6 * 0.6913e-3)
        self.assertAlmostEqual(payload["flow_rate_ul_min"],
                               q_expect / (1e-9 / 60), places=4)

    def test_pressure_flow_consistency(self):
        payload, _ = self._json(
            "channel", "--width", "200um", "--height", "50um", "--length", "5mm",
            "--flow-rate", "1 uL/min")
        r = payload["resistance_pa_s_per_m3"]
        self.assertAlmostEqual(payload["pressure_drop_pa"], r * (1e-9 / 60), places=6)

    def test_solve_for_height_from_shear(self):
        payload, result = self._json(
            "channel", "--width", "1mm", "--length", "1cm",
            "--height", "1um",  # placeholder, replaced by the solver
            "--flow-rate", "10 uL/min", "--target-shear", "2 Pa",
            "--solve-for", "height")
        self.assertEqual(result.returncode, 0)
        h_expect = math.sqrt(6 * 0.890e-3 * (1e-8 / 60) / (1e-3 * 2.0))
        self.assertAlmostEqual(payload["height_m"], h_expect, places=9)

    def test_turbulent_exit_1(self):
        _, result = self._json(
            "channel", "--width", "1mm", "--height", "1mm", "--length", "1cm",
            "--flow-rate", "500 mL/min")
        self.assertEqual(result.returncode, 1)
        self.assertIn("design-fail", result.stderr)

    def test_stdout_is_pure_json(self):
        _, result = self._json(
            "channel", "--width", "1mm", "--height", "100um", "--length", "1cm",
            "--flow-rate", "1 uL/min")
        json.loads(result.stdout)  # raises if caveats leaked to stdout
        self.assertIn("caveat", result.stderr)

    def test_unknown_unit_exit_2(self):
        _, result = self._json(
            "channel", "--width", "1 furlong", "--height", "100um",
            "--length", "1cm", "--flow-rate", "1 uL/min")
        self.assertEqual(result.returncode, 2)


# ------------------------------------------------------------------ network


def _write_netlist(tmp_path: Path, channels, bcs) -> Path:
    path = tmp_path / "net.json"
    path.write_text(json.dumps({
        "fluid": "water", "temperature_c": 25.0,
        "boundary_conditions": bcs, "channels": channels,
    }))
    return path


class TestNetwork(unittest.TestCase):
    def _solve(self, path: Path) -> tuple[dict, subprocess.CompletedProcess]:
        result = run_script("channel_resistance", "network",
                            "--netlist", str(path), "--format", "json")
        return (json.loads(result.stdout) if result.stdout else {}), result

    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_parallel_halves_resistance(self):
        r = common.rect_resistance(0.890e-3, 1e-2, 200e-6, 50e-6)
        path = _write_netlist(self.tmp_path, [
            {"id": "a", "from": "in", "to": "out", "width": "200um",
             "height": "50um", "length": "1cm"},
            {"id": "b", "from": "in", "to": "out", "width": "200um",
             "height": "50um", "length": "1cm"},
        ], {"in": {"pressure": "1 kPa"}, "out": {"pressure": "0 Pa"}})
        payload, result = self._solve(path)
        self.assertEqual(result.returncode, 0)
        total = sum(c["flow_ul_min"] for c in payload["channels"]
                    if c["from"] == "in")
        expected = 1000.0 / (r / 2.0) / (1e-9 / 60)
        self.assertAlmostEqual(total, expected, places=4)

    def test_series_doubles_resistance(self):
        path = _write_netlist(self.tmp_path, [
            {"id": "a", "from": "in", "to": "mid", "resistance": 1e12},
            {"id": "b", "from": "mid", "to": "out", "resistance": 1e12},
        ], {"in": {"pressure": "2 kPa"}, "out": {"pressure": "0 Pa"}})
        payload, _ = self._solve(path)
        mid = next(n for n in payload["node_pressures"] if n["node"] == "mid")
        self.assertAlmostEqual(mid["pressure_kpa"], 1.0, places=9)
        q = payload["channels"][0]["flow_ul_min"]
        self.assertAlmostEqual(q, 2000.0 / 2e12 / (1e-9 / 60), places=6)

    def test_flow_source_round_trip(self):
        path = _write_netlist(self.tmp_path, [
            {"id": "a", "from": "in", "to": "out", "resistance": 3e12},
        ], {"in": {"flow_rate": "1 uL/min"}, "out": {"pressure": "0 Pa"}})
        payload, _ = self._solve(path)
        node = next(n for n in payload["node_pressures"] if n["node"] == "in")
        self.assertAlmostEqual(node["pressure_kpa"],
                               (1e-9 / 60) * 3e12 / 1e3, places=6)

    def test_missing_pressure_reference_exit_1(self):
        path = _write_netlist(self.tmp_path, [
            {"id": "a", "from": "in", "to": "out", "resistance": 1e12},
        ], {"in": {"flow_rate": "1 uL/min"}})
        _, result = self._solve(path)
        self.assertEqual(result.returncode, 1)

    def test_bad_netlist_exit_2(self):
        result = run_script("channel_resistance", "network",
                            "--netlist", str(FIXTURES / "bad-netlist.json"))
        self.assertEqual(result.returncode, 2)

    def test_shipped_example_network_solves(self):
        result = run_script("channel_resistance", "network", "--netlist",
                            str(SKILL_ROOT / "assets" / "example-network.json"),
                            "--format", "json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        flows = {c["channel"]: c["flow_ul_min"] for c in payload["channels"]}
        self.assertAlmostEqual(flows["feed"],
                               flows["chamber_a"] + flows["chamber_b"], places=6)


# ------------------------------------------------------- dimensionless & mixing


class TestDimensionless(unittest.TestCase):
    def test_reynolds_hand_value(self):
        result = run_script(
            "dimensionless_numbers", "--width", "100um", "--height", "100um",
            "--velocity", "1 mm/s", "--fluid", "water", "--temp", "25",
            "--format", "json")
        payload = json.loads(result.stdout)
        re = next(r for r in payload["numbers"] if r["number"] == "Re")
        self.assertAlmostEqual(re["value"], 997.0 * 1e-3 * 1e-4 / 0.890e-3,
                               places=6)

    def test_debye_hand_value(self):
        result = run_script(
            "dimensionless_numbers", "--width", "100um", "--height", "100um",
            "--velocity", "1 mm/s", "--ionic-strength", "100 mM",
            "--format", "json")
        payload = json.loads(result.stdout)
        row = next(r for r in payload["numbers"] if r["number"] == "lambda_D_nm")
        self.assertAlmostEqual(row["value"], 0.304 / math.sqrt(0.1), places=3)


class TestMixing(unittest.TestCase):
    def test_mixing_length_equals_u_times_t(self):
        mixing = _load_script("mixing_length")
        d, w = 4.25e-10, 100e-6
        t = mixing.mixing_time(d, w, 0.1)
        self.assertAlmostEqual(
            t, (w ** 2 / (math.pi ** 2 * d)) * math.log(8 / (math.pi ** 2 * 0.1)))
        result = run_script(
            "mixing_length", "length", "--width", "100um", "--height", "50um",
            "--flow-rate", "0.3 uL/min", "--diffusivity", "fluorescein",
            "--format", "json")
        payload = json.loads(result.stdout)
        u = (0.3e-9 / 60) / (100e-6 * 50e-6)
        self.assertAlmostEqual(payload["mixing_length_m"], u * t, places=6)

    def test_transferred_fraction_limits(self):
        mixing = _load_script("mixing_length")
        # t=0: nothing transferred; t->inf: half transferred.
        self.assertAlmostEqual(mixing.transferred_fraction(1e-9, 1e-4, 0.0), 0.0,
                               places=3)
        self.assertAlmostEqual(mixing.transferred_fraction(1e-9, 1e-4, 1e6), 0.5,
                               places=6)

    def test_budget_fail_exit_1(self):
        result = run_script(
            "mixing_length", "length", "--width", "100um", "--height", "50um",
            "--flow-rate", "3 uL/min", "--diffusivity", "fluorescein",
            "--available-length", "1 cm")
        self.assertEqual(result.returncode, 1)


class TestCliHelpContract(
        skill_contract.cli.help_test_case(SKILL_ROOT)):
    pass


if __name__ == "__main__":
    unittest.main()
