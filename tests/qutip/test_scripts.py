"""Dependency-free tests for QuTiP skill CLI safety and planners."""

from __future__ import annotations

import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "qutip"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import _common  # noqa: E402
import convergence_sweep  # noqa: E402
import qobj_model_validator  # noqa: E402
import result_audit  # noqa: E402
import solver_config_planner  # noqa: E402
import steady_state_spectrum_planner  # noqa: E402
import two_level_simulation  # noqa: E402


class CommonSafetyTests(unittest.TestCase):
    def test_strict_json_rejects_urls_duplicates_nan_and_symlinks(self) -> None:
        with self.assertRaises(_common.CliError):
            _common.load_json_object("https://example.invalid/model.json")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            duplicate = root / "duplicate.json"
            duplicate.write_text('{"value": 1, "value": 2}', encoding="utf-8")
            with self.assertRaises(_common.CliError):
                _common.load_json_object(duplicate)

            nonfinite = root / "nonfinite.json"
            nonfinite.write_text('{"value": NaN}', encoding="utf-8")
            with self.assertRaises(_common.CliError):
                _common.load_json_object(nonfinite)

            regular = root / "regular.json"
            regular.write_text("{}", encoding="utf-8")
            symlink = root / "symlink.json"
            try:
                symlink.symlink_to(regular)
            except OSError:
                self.skipTest("symlinks unavailable")
            with self.assertRaises(_common.CliError):
                _common.load_json_object(symlink)

    def test_private_output_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            _common.emit_json({"ok": True}, output=output)
            self.assertEqual(json.loads(output.read_text()), {"ok": True})
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            with self.assertRaises(_common.CliError):
                _common.emit_json({"ok": False}, output=output)

    def test_limits_and_nonfinite_values_are_enforced(self) -> None:
        with self.assertRaises(_common.CliError):
            _common.bounded_dimensions([8, 9])
        with self.assertRaises(_common.CliError):
            _common.finite_float(float("inf"), name="value")
        with self.assertRaises(_common.CliError):
            _common.parse_csv_ints(
                "10,10",
                name="counts",
                minimum=1,
                maximum=100,
            )


class HelpTests(unittest.TestCase):
    def test_every_cli_has_dependency_free_help(self) -> None:
        modules = (
            convergence_sweep,
            qobj_model_validator,
            result_audit,
            solver_config_planner,
            steady_state_spectrum_planner,
            two_level_simulation,
        )
        for module in modules:
            with self.subTest(module=module.__name__):
                help_text = module.build_parser().format_help()
                self.assertIn("usage:", help_text)
                self.assertIn("--help", help_text)
                self.assertNotIn("Traceback", help_text)


class PlannerTests(unittest.TestCase):
    def test_lindblad_and_stochastic_solver_selection(self) -> None:
        parser = solver_config_planner.build_parser()
        lindblad = solver_config_planner.create_plan(
            parser.parse_args(
                ["--model", "lindblad", "--collapse-channels", "2"]
            )
        )
        self.assertEqual(lindblad["recommended_solver"], "mesolve")
        self.assertEqual(lindblad["status"], "ready_for_model_construction")

        stochastic = solver_config_planner.create_plan(
            parser.parse_args(
                [
                    "--model",
                    "diffusive",
                    "--initial-state",
                    "density",
                    "--trajectories",
                    "25",
                ]
            )
        )
        self.assertEqual(stochastic["recommended_solver"], "smesolve")
        self.assertEqual(stochastic["call_configuration"]["ntraj"], 25)
        self.assertFalse(stochastic["call_configuration"]["heterodyne"])

    def test_specialized_plans_surface_missing_assumptions(self) -> None:
        parser = solver_config_planner.build_parser()
        bloch_redfield = solver_config_planner.create_plan(
            parser.parse_args(["--model", "bloch-redfield"])
        )
        self.assertEqual(bloch_redfield["recommended_solver"], "brmesolve")
        self.assertIn(
            "weak-coupling assumption has not been confirmed",
            bloch_redfield["warnings"],
        )

        floquet = solver_config_planner.create_plan(
            parser.parse_args(["--model", "periodic-open"])
        )
        self.assertIn("positive --period", " ".join(floquet["warnings"]))

    def test_steady_spectrum_plan_computes_bounded_fft_grid(self) -> None:
        parser = steady_state_spectrum_planner.build_parser()
        report = steady_state_spectrum_planner.create_plan(
            parser.parse_args(
                [
                    "--stationary-confirmed",
                    "--tau-max",
                    "10",
                    "--tau-points",
                    "101",
                ]
            )
        )
        self.assertEqual(report["status"], "ready_to_implement")
        fft = report["spectrum_plans"][1]
        self.assertAlmostEqual(fft["tau_grid"]["step"], 0.1)
        self.assertAlmostEqual(
            fft["derived_angular_frequency_limits"]["nyquist"],
            10.0 * 3.141592653589793,
        )

    def test_planners_reject_unbounded_requests(self) -> None:
        parser = steady_state_spectrum_planner.build_parser()
        with self.assertRaises(_common.CliError):
            steady_state_spectrum_planner.create_plan(
                parser.parse_args(["--dimension", "65"])
            )


class PortableAuditTests(unittest.TestCase):
    def test_simulation_report_audit_passes_without_qutip(self) -> None:
        document = {
            "report_type": "qutip.two_level_simulation",
            "schema_version": 1,
            "qutip_version": "5.3.1",
            "configuration": {"solver": "mesolve"},
            "model": {"assumptions": ["a", "b", "c"]},
            "times": [0.0, 1.0, 2.0],
            "expectations": {"excited_population": [1.0, 0.5, 0.25]},
            "analytic_reference": {
                "applicable": True,
                "excited_population": [1.0, 0.5, 0.25],
                "max_abs_error": 0.0,
            },
            "trajectory_statistics": {
                "trajectories_run": None,
                "seeds": None,
            },
            "checks": {},
            "solver": {"stats": {"run time": 0.01}},
        }
        audit = result_audit.audit_document(document, tolerance=1.0e-8)
        self.assertEqual(audit["status"], "pass")
        self.assertEqual(audit["summary"]["errors"], 0)

    def test_audit_rejects_out_of_range_population(self) -> None:
        document = {
            "report_type": "qutip.two_level_simulation",
            "schema_version": 1,
            "qutip_version": "5.3.1",
            "configuration": {"solver": "mesolve"},
            "model": {"assumptions": ["a", "b", "c"]},
            "times": [0.0, 1.0],
            "expectations": {"excited_population": [1.0, 1.2]},
            "analytic_reference": {"applicable": False},
            "trajectory_statistics": {},
            "checks": {},
            "solver": {"stats": {"run time": 0.01}},
        }
        audit = result_audit.audit_document(document, tolerance=1.0e-6)
        self.assertEqual(audit["status"], "fail")


if __name__ == "__main__":
    unittest.main()
