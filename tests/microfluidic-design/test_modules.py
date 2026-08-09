"""Module tests for the microfluidic-design skill: droplets, separation,
electrokinetics, capillary/centrifugal/EWOD, valves, thermal, oxygen,
fabrication rules, and the DXF/SVG layout writer.

Each formula is pinned to a hand-computed value so upstream edits that change
the physics fail loudly.

    uv run --with pytest python -m pytest tests/microfluidic-design -q
"""

from __future__ import annotations

import importlib.util
import json
import math
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "microfluidic-design"
SCRIPTS_DIR = SKILL_ROOT / "scripts"


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


def run_json(name: str, *args: str) -> tuple[dict, subprocess.CompletedProcess]:
    result = run_script(name, *args, "--format", "json")
    return (json.loads(result.stdout) if result.stdout else {}), result


# ----------------------------------------------------------------- droplets


class TestDroplets(unittest.TestCase):
    BASE = ("--geometry", "t-junction", "--width", "50um", "--height", "50um",
            "--interfacial-tension", "5 mN/m", "--fluid", "hfe-7500")

    def test_capillary_number_and_regimes(self):
        # Ca = mu_c * u_c / gamma with u_c = Q_c/(w h)
        payload, result = run_json(
            "droplet_generator", *self.BASE,
            "--continuous-flow", "5 uL/min", "--dispersed-flow", "0.5 uL/min")
        self.assertEqual(result.returncode, 0)
        u_c = (5e-9 / 60) / (50e-6 * 50e-6)
        self.assertAlmostEqual(payload["capillary_number"],
                               1.24e-3 * u_c / 5e-3, places=9)
        self.assertEqual(payload["regime"], "squeezing")
        _, jet = run_json(
            "droplet_generator", *self.BASE,
            "--continuous-flow", "200 uL/min", "--dispersed-flow", "1 uL/min")
        self.assertEqual(jet.returncode, 1)  # jetting regime is a design fail

    def test_garstecki_plug_length(self):
        payload, _ = run_json(
            "droplet_generator", *self.BASE,
            "--continuous-flow", "5 uL/min", "--dispersed-flow", "0.5 uL/min")
        self.assertAlmostEqual(payload["plug_length_um"],
                               50 * (1 + 1.1 * 0.1), places=6)

    def test_poisson_fractions(self):
        payload, _ = run_json(
            "droplet_generator", *self.BASE,
            "--continuous-flow", "5 uL/min", "--dispersed-flow", "0.5 uL/min",
            "--cell-concentration", "1e6 1/mL")
        stats = payload["poisson"][0]
        lam = stats["lambda_cells_per_droplet"]
        self.assertAlmostEqual(stats["empty_fraction"], math.exp(-lam), places=9)
        self.assertAlmostEqual(stats["single_cell_fraction"],
                               lam * math.exp(-lam), places=9)

    def test_frequency_is_qd_over_volume(self):
        payload, _ = run_json(
            "droplet_generator", *self.BASE,
            "--continuous-flow", "5 uL/min", "--dispersed-flow", "0.5 uL/min")
        vol = payload["plug_volume_pl"] * 1e-15
        self.assertAlmostEqual(payload["generation_frequency_hz"],
                               (0.5e-9 / 60) / vol, places=6)


# --------------------------------------------------------------- separation


class TestSeparation(unittest.TestCase):
    def test_dld_davis_formula(self):
        payload, result = run_json("particle_separation", "dld",
                                   "--gap", "10um", "--row-shift-fraction", "0.1")
        self.assertEqual(result.returncode, 0)
        self.assertAlmostEqual(payload["critical_diameter_um"],
                               1.4 * 10 * 0.1 ** 0.48, places=6)

    def test_dld_inverse_round_trip(self):
        payload, _ = run_json("particle_separation", "dld",
                              "--critical-diameter", "5um",
                              "--row-shift-fraction", "0.1")
        gap_um = payload["gap_um"]
        self.assertAlmostEqual(1.4 * gap_um * 0.1 ** 0.48, 5.0, places=6)

    def test_dld_clogging_gate(self):
        _, result = run_json("particle_separation", "dld", "--gap", "10um",
                             "--row-shift-fraction", "0.1",
                             "--max-particle", "12um")
        self.assertEqual(result.returncode, 1)

    def test_inertial_gate_and_focus_length(self):
        _, small = run_json("particle_separation", "inertial",
                            "--width", "100um", "--height", "50um",
                            "--flow-rate", "100 uL/min",
                            "--particle-diameter", "2um")
        self.assertEqual(small.returncode, 1)  # a/Dh < 0.07
        payload, ok = run_json("particle_separation", "inertial",
                               "--width", "100um", "--height", "50um",
                               "--flow-rate", "100 uL/min",
                               "--particle-diameter", "10um")
        self.assertEqual(ok.returncode, 0)
        # L_f = pi mu H^2 / (rho U_max a^2 f_L), H = min(w,h), U_max = 1.5 U
        u_max = 1.5 * (100e-9 / 60) / (100e-6 * 50e-6)
        expect = math.pi * 0.890e-3 * (50e-6) ** 2 / (
            997.0 * u_max * (10e-6) ** 2 * 0.05)
        self.assertAlmostEqual(payload["focusing_length_mm"], expect * 1e3,
                               places=4)

    def test_acoustic_resonance_and_contrast(self):
        payload, _ = run_json("particle_separation", "acoustic",
                              "--width", "375um", "--height", "150um",
                              "--particle", "polystyrene-bead",
                              "--particle-diameter", "7um")
        self.assertAlmostEqual(payload["resonance_frequency_mhz"],
                               1497.0 / (2 * 375e-6) / 1e6, places=4)
        # Polystyrene in water: positive contrast, toward the node.
        self.assertGreater(payload["acoustic_contrast_factor"], 0.1)
        self.assertLess(payload["acoustic_contrast_factor"], 0.4)

    def test_acoustic_slow_migration_gate(self):
        _, result = run_json("particle_separation", "acoustic",
                             "--width", "375um", "--height", "150um",
                             "--particle", "polystyrene-bead",
                             "--particle-diameter", "2um",
                             "--flow-rate", "500 uL/min", "--length", "5 mm")
        self.assertEqual(result.returncode, 1)

    def test_sheath_width(self):
        payload, _ = run_json("particle_separation", "sheath",
                              "--width", "100um", "--sample-flow", "1 uL/min",
                              "--sheath-flow", "9 uL/min")
        self.assertAlmostEqual(payload["focused_stream_width_um"], 10.0, places=6)

    def test_trap_ratio_gate(self):
        base = ("--trap-width", "20um", "--trap-height", "25um",
                "--trap-length", "50um")
        _, bad = run_json("particle_separation", "trap", *base,
                          "--bypass-width", "100um", "--bypass-height", "50um",
                          "--bypass-length", "100um")
        self.assertEqual(bad.returncode, 1)
        _, good = run_json("particle_separation", "trap", *base,
                           "--bypass-width", "30um", "--bypass-height", "25um",
                           "--bypass-length", "2mm")
        self.assertEqual(good.returncode, 0)


# ----------------------------------------------------------- electrokinetics


class TestElectrokinetics(unittest.TestCase):
    def test_smoluchowski_hand_value(self):
        payload, result = run_json(
            "electrokinetics", "eof", "--zeta", "-50 mV", "--width", "100um",
            "--height", "50um", "--length", "3cm", "--efield", "100 V/cm",
            "--conductivity", "0.05 S/m")
        self.assertEqual(result.returncode, 0)
        u = 8.8541878128e-12 * 78.4 * 0.05 * 1e4 / 0.890e-3
        self.assertAlmostEqual(payload["eof_velocity_mm_s"], u * 1e3, places=6)

    def test_joule_gate(self):
        _, result = run_json(
            "electrokinetics", "eof", "--zeta", "-50 mV", "--width", "1mm",
            "--height", "500um", "--length", "3cm", "--efield", "500 V/cm",
            "--conductivity", "1.6 S/m", "--substrate", "pdms")
        self.assertEqual(result.returncode, 1)

    def test_clausius_mossotti_bounds(self):
        ek = _load_script("electrokinetics")
        for freq in (1e3, 1e6, 1e9):
            cm = ek.clausius_mossotti(2.55, 0.01, 78.4, 1.6, freq)
            self.assertGreaterEqual(cm, -0.5)
            self.assertLessEqual(cm, 1.0)
        # Low frequency is conductivity-dominated: sigma_p << sigma_m -> negative.
        self.assertLess(ek.clausius_mossotti(2.55, 0.01, 78.4, 1.6, 1e3), 0)

    def test_debye_hand_value(self):
        payload, _ = run_json("electrokinetics", "debye",
                              "--ionic-strength", "100 mM")
        self.assertAlmostEqual(payload["debye_length_nm"],
                               0.304 / math.sqrt(0.1), places=3)


# ------------------------------------------- capillary / centrifugal / EWOD


class TestPassiveAndDigital(unittest.TestCase):
    def test_young_laplace_hand_value(self):
        cap = _load_script("capillary_design")
        # theta = 110 deg on all walls, w = 100 um, h = 50 um, gamma = 72 mN/m
        dp = cap.rect_capillary_pressure(72e-3, 100e-6, 50e-6, 110, 110, 110)
        expect = 72e-3 * (2 * math.cos(math.radians(110)) / 50e-6
                          + 2 * math.cos(math.radians(110)) / 100e-6)
        self.assertAlmostEqual(dp, expect)
        self.assertLess(dp, 0)  # hydrophobic: a barrier

    def test_burst_gate(self):
        _, result = run_json(
            "capillary_design", "pressure", "--width", "100um",
            "--height", "50um", "--theta-top", "110",
            "--applied-pressure", "5 kPa")
        self.assertEqual(result.returncode, 1)

    def test_washburn_time(self):
        payload, _ = run_json(
            "capillary_design", "filling", "--width", "200um",
            "--height", "50um", "--contact-angle", "30",
            "--target-length", "2 cm", "--fluid", "water", "--temp", "25")
        coeff = payload["washburn_coefficient_m2_s"]
        self.assertAlmostEqual(payload["time_to_fill_s"],
                               (2e-2) ** 2 / coeff, places=6)

    def test_centrifugal_pressure_and_burst_round_trip(self):
        cen = _load_script("centrifugal_design")
        omega = 3000 * 2 * math.pi / 60
        dp = cen.spin_pressure(997.0, omega, 20e-3, 30e-3)
        self.assertAlmostEqual(dp, 997.0 * omega ** 2 * 25e-3 * 10e-3)
        rpm = cen.burst_rpm(997.0, dp, 20e-3, 30e-3)
        self.assertAlmostEqual(rpm, 3000.0, places=6)

    def test_sequence_gate(self):
        args = ("centrifugal_design", "sequence",
                "--valve", "a,3kPa,20mm,24mm", "--valve", "b,1kPa,25mm,30mm")
        _, result = run_json(*args)
        self.assertEqual(result.returncode, 1)  # b bursts before a

    def test_ewod_lippmann_young(self):
        payload, result = run_json(
            "digital_microfluidics", "actuation", "--voltage", "40 V",
            "--dielectric-thickness", "1um", "--tension", "40 mN/m")
        self.assertEqual(result.returncode, 0)
        ew = 8.8541878128e-12 * 3.15 * 40 ** 2 / (2 * 1e-6 * 40e-3)
        self.assertAlmostEqual(payload["electrowetting_number"], ew, places=6)

    def test_ewod_breakdown_gate(self):
        _, result = run_json(
            "digital_microfluidics", "actuation", "--voltage", "150 V",
            "--dielectric-thickness", "0.5um")
        self.assertEqual(result.returncode, 1)


# ----------------------------------------------- valves / thermal / oxygen


class TestValvesThermalOxygen(unittest.TestCase):
    def test_quake_plate_theory_value(self):
        payload, result = run_json(
            "valve_pump_design", "quake", "--control-width", "100um",
            "--flow-height", "10um", "--membrane-thickness", "10um",
            "--youngs-modulus", "1 MPa", "--chambers", "16")
        self.assertEqual(result.returncode, 0)
        p = 10e-6 * 1e6 * (10e-6) ** 3 / (0.00406 * (100e-6) ** 4)
        self.assertAlmostEqual(payload["estimated_closing_pressure_kpa"],
                               p / 1e3, places=4)
        self.assertEqual(payload["multiplexer_control_lines"], 8)

    def test_quake_rectangular_profile_fails(self):
        _, result = run_json(
            "valve_pump_design", "quake", "--control-width", "100um",
            "--flow-height", "10um", "--membrane-thickness", "10um",
            "--flow-profile", "rectangular")
        self.assertEqual(result.returncode, 1)

    def test_rc_time_constant(self):
        payload, _ = run_json("valve_pump_design", "flow-control",
                              "--resistance", "1e12", "--compliance", "1e-12",
                              "--pulsation-frequency", "0.5 Hz")
        self.assertAlmostEqual(payload["rc_time_constant_s"], 1.0)
        self.assertAlmostEqual(payload["pulsation_attenuation_factor"],
                               1 / math.sqrt(1 + (2 * math.pi * 0.5) ** 2),
                               places=9)

    def test_thermal_transient_and_pcr(self):
        payload, _ = run_json("thermal_design", "transient",
                              "--substrate", "glass",
                              "--substrate-thickness", "500um")
        alpha = 1.1 / (2230 * 830)
        self.assertAlmostEqual(payload["time_constant_s"],
                               (500e-6) ** 2 / alpha, places=6)
        pcr, result = run_json("thermal_design", "pcr", "--width", "100um",
                               "--height", "100um", "--flow-rate", "1 uL/min")
        self.assertEqual(result.returncode, 0)
        u = (1e-9 / 60) / (1e-4 * 1e-4)
        zone = next(z for z in pcr["zones"] if z["zone"] == "extension")
        self.assertAlmostEqual(zone["zone_length_mm"], u * 30 * 1e3, places=6)

    def test_oxygen_budget_gate(self):
        payload, ok = run_json("oxygen_transport", "--flow-rate", "10 uL/min",
                               "--cells", "1e5", "--ocr", "30")
        self.assertEqual(ok.returncode, 0)
        self.assertAlmostEqual(payload["demand_mol_s"], 1e5 * 30e-18, places=25)
        q = 10e-9 / 60
        self.assertAlmostEqual(payload["convective_supply_mol_s"],
                               q * (0.2 - 0.05), places=18)
        _, starved = run_json("oxygen_transport", "--flow-rate", "0.1 uL/min",
                              "--cells", "1e6", "--ocr", "300")
        self.assertEqual(starved.returncode, 1)

    def test_hypoxia_pdms_roof_fails(self):
        _, result = run_json("oxygen_transport", "--flow-rate", "1 uL/min",
                             "--cells", "1e6", "--ocr", "300", "--hypoxia",
                             "--chamber-width", "1mm", "--chamber-length", "10mm",
                             "--pdms-roof-thickness", "2mm")
        self.assertEqual(result.returncode, 1)


# --------------------------------------------------- fabrication and layout


class TestFabrication(unittest.TestCase):
    def test_pdms_sag_fails(self):
        _, result = run_json("fabrication_check", "--process", "pdms-softlith",
                             "--width", "500um", "--height", "20um")
        self.assertEqual(result.returncode, 1)

    def test_compliant_design_passes(self):
        payload, result = run_json(
            "fabrication_check", "--process", "pdms-softlith",
            "--width", "100um", "--height", "50um",
            "--operating-pressure", "50 kPa", "--port-diameter", "1.5mm")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(payload["fail_count"], 0)
        statuses = {c["rule"]: c["status"] for c in payload["checks"]}
        self.assertEqual(statuses["bond-pressure"], "PASS")

    def test_netlist_check(self):
        _, result = run_json(
            "fabrication_check", "--process", "pdms-softlith", "--netlist",
            str(SKILL_ROOT / "assets" / "example-network.json"))
        self.assertEqual(result.returncode, 0)


class TestMaskLayout(unittest.TestCase):
    def test_dld_dxf_and_svg(self):
        with tempfile.TemporaryDirectory() as tmp:
            dxf = Path(tmp) / "out.dxf"
            svg = Path(tmp) / "out.svg"
            payload, result = run_json(
                "mask_layout", "--output", str(dxf), "--svg", str(svg),
                "dld", "--gap", "12um", "--post-diameter", "20um",
                "--row-shift-fraction", "0.1", "--rows", "10", "--columns", "15")
            self.assertEqual(result.returncode, 0, result.stderr)
            text = dxf.read_text()
            self.assertIn("SECTION", text)
            self.assertIn("ENTITIES", text)
            self.assertIn("POLYLINE", text)
            self.assertTrue(text.rstrip().endswith("EOF"))
            self.assertEqual(text.count("CIRCLE"), 10 * 15)
            self.assertEqual(payload["circles"], 150)
            ET.parse(svg)  # well-formed XML

    def test_straight_channel_vertex_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            dxf = Path(tmp) / "out.dxf"
            payload, _ = run_json(
                "mask_layout", "--output", str(dxf),
                "straight", "--width", "100um", "--length", "8mm")
            self.assertAlmostEqual(payload["min_feature_um"], 100.0, places=6)
            lines = dxf.read_text().splitlines()
            # First VERTEX x/y: group code 10 then value, 20 then value.
            idx = lines.index("VERTEX")
            values = {lines[i]: lines[i + 1] for i in (idx + 1, idx + 3, idx + 5)}
            self.assertAlmostEqual(float(values["10"]), 0.0)
            self.assertAlmostEqual(float(values["20"]), -0.05)  # -w/2 in mm

    def test_bad_extension_exit_2(self):
        _, result = run_json("mask_layout", "--output", "layout.gds",
                             "straight", "--width", "100um", "--length", "8mm")
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
