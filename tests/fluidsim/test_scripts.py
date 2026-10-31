"""Dependency-free synthetic tests for the FluidSim skill CLIs."""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "fluidsim"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import _schema  # noqa: E402
import budget_summary  # noqa: E402
import grid_resource_estimator  # noqa: E402
import output_inventory  # noqa: E402
import restart_compatibility  # noqa: E402
import simulation_dry_run  # noqa: E402


CLI_NAMES = (
    "solver_config_validator.py",
    "grid_resource_estimator.py",
    "simulation_dry_run.py",
    "output_inventory.py",
    "budget_summary.py",
    "restart_compatibility.py",
)


def run_script(
    name: str, *arguments: str, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *map(str, arguments)],
        check=False,
        capture_output=True,
        cwd=cwd,
        env=environment,
        text=True,
        timeout=30,
    )


def write_config(root: Path, config: dict | None = None) -> Path:
    path = root / "config.json"
    path.write_text(
        json.dumps(config or _schema.example_config(), allow_nan=False),
        encoding="utf-8",
    )
    return path


class HelpAndSchemaTests(unittest.TestCase):
    def test_all_helps_are_dependency_free(self) -> None:
        for name in CLI_NAMES:
            with self.subTest(name=name):
                result = run_script(name, "--help")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage:", result.stdout.casefold())

    def test_example_is_valid_and_scientifically_nonconclusive(self) -> None:
        report = _schema.validate_config(_schema.example_config())
        self.assertTrue(report["ok"], report["errors"])
        self.assertFalse(report["physical_validity_established"])
        self.assertFalse(report["numerical_convergence_established"])

    def test_strict_json_rejects_duplicate_and_nonfinite_values(self) -> None:
        for text in ('{"x": 1, "x": 2}', '{"x": NaN}'):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / "bad.json").write_text(text, encoding="utf-8")
                result = run_script(
                    "solver_config_validator.py",
                    "--config",
                    "bad.json",
                    cwd=root,
                )
                self.assertEqual(result.returncode, 2)
                self.assertFalse(json.loads(result.stdout)["ok"])

    def test_old_cfl_name_and_path_traversal_fail_closed(self) -> None:
        config = _schema.example_config()
        config["parameters"]["time_stepping"]["CFL"] = 0.5
        with self.assertRaises(Exception):
            _schema.validate_config(config)
        config = _schema.example_config()
        config["execution"]["output_root"] = "../escape"
        report = _schema.validate_config(config)
        self.assertFalse(report["ok"])


class PlanningTests(unittest.TestCase):
    def test_resource_estimate_is_bounded_and_not_runtime_claim(self) -> None:
        config = _schema.example_config()
        report = grid_resource_estimator.estimate(
            config,
            precision_bytes=8,
            workspace_factor=8.0,
            safety_factor=1.5,
            compression_ratio=1.0,
        )
        self.assertEqual(report["grid"]["shape"], [32, 32])
        self.assertGreater(report["estimates"]["peak_memory_bytes"], 0)
        self.assertFalse(report["runtime_estimated"])

    def test_generated_script_defaults_to_dry_run(self) -> None:
        config = _schema.example_config()
        script = simulation_dry_run.render_script(config)
        ast.parse(script)
        self.assertIn("from fluidsim.solvers.ns2d.solver import Simul", script)
        self.assertNotIn("subprocess", script)
        self.assertNotIn("import_module", script)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            generated = root / "run_ns2d.py"
            generated.write_text(script, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(generated)],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["dry_run"])

    def test_generator_writes_only_reviewed_local_script(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_config(root)
            result = run_script(
                "simulation_dry_run.py",
                "--config",
                "config.json",
                "--output",
                "run.py",
                cwd=root,
            )
            report = json.loads(result.stdout)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / "run.py").is_file())
            self.assertFalse(report["commands_executed"])
            self.assertFalse(report["mpi_launched"])
            self.assertFalse(report["job_submitted"])


class OutputTests(unittest.TestCase):
    def test_plain_output_inventory_does_not_need_h5py(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "stdout.txt").write_text("bounded\n", encoding="utf-8")
            report = output_inventory.inventory(
                root,
                root=root,
                max_files=10,
                max_hdf5_files=0,
                max_datasets=10,
                max_attributes=10,
                max_depth=4,
            )
        self.assertEqual(report["file_count"], 1)
        self.assertFalse(report["arrays_loaded"])

    def test_scalar_json_lines_and_text_are_aggregated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            json_path = root / "spatial_means.json"
            json_path.write_text(
                '{"t": 0.0, "E": 1.0}\n{"t": 1.0, "E": 3.0}\n',
                encoding="utf-8",
            )
            json_report = budget_summary.summarize_scalar_file(
                json_path, max_records=10
            )
            self.assertEqual(json_report["metrics"]["E"]["mean"], 2.0)
            text_path = root / "spatial_means.txt"
            text_path.write_text(
                "time = 0\nE = 2\n time = 1\nE = 4\n",
                encoding="utf-8",
            )
            text_report = budget_summary.summarize_scalar_file(
                text_path, max_records=10
            )
            self.assertEqual(text_report["metrics"]["E"]["last"], 4.0)
            self.assertFalse(text_report["raw_records_emitted"])

    def test_hdf5_metadata_and_bounded_spectrum_when_available(self) -> None:
        try:
            import h5py
            import numpy as np
        except ImportError:
            self.skipTest("optional h5py/NumPy unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            external = root / "external.h5"
            with h5py.File(external, "w") as handle:
                handle.create_dataset("private", data=np.arange(3))
            state = root / "state_phys_t000.000.nc"
            with h5py.File(state, "w") as handle:
                group = handle.create_group("state_phys")
                group.attrs["time"] = 0.0
                group.create_dataset("rot", data=np.zeros((4, 4)))
                handle["outside"] = h5py.ExternalLink(
                    "external.h5", "/private"
                )
            metadata = output_inventory.inspect_hdf5_metadata(
                state, max_datasets=10, max_attributes=10, max_depth=8
            )
            self.assertTrue(metadata["hdf5_readable"])
            self.assertEqual(metadata["links"]["external_not_followed"], 1)
            self.assertEqual(metadata["datasets"][0]["shape"], [4, 4])

            spectra = root / "spectra2D.h5"
            with h5py.File(spectra, "w") as handle:
                handle.create_dataset("times", data=np.array([0.0, 1.0]))
                handle.create_dataset(
                    "spectrum2D_E", data=np.arange(16).reshape(2, 8)
                )
            summary = budget_summary.summarize_spectral_file(
                spectra, max_datasets=10, max_values=4
            )
            spectrum = summary["datasets"]["/spectrum2D_E"]
            self.assertEqual(spectrum["sampled_values"], 4)
            self.assertIsNone(spectrum["sum"])


class RestartTests(unittest.TestCase):
    def _target(self, digest: str) -> dict:
        config = _schema.example_config()
        config["parameters"]["init_fields"] = {
            "type": "from_file",
            "from_file": {"path": "state.nc"},
        }
        config["provenance"]["restart"] = {
            "path": "state.nc",
            "sha256": digest,
            "source_fluidsim": "0.9.0",
        }
        return config

    def _manifest(self, digest: str) -> dict:
        base = _schema.example_config()
        return {
            "schema_version": "1.1",
            "solver": "ns2d",
            "parameters": {
                "oper": deepcopy(base["parameters"]["oper"]),
                "nu_2": base["parameters"]["nu_2"],
                "time_stepping": {"t_end": 0.05, "type_time_scheme": "RK4"},
                "forcing": {"enable": False, "type": ""},
            },
            "state": {
                "datasets": ["rot"],
                "dataset_metadata": {"rot": {"shape": [32, 32], "numeric": True}},
                "iteration": 5,
                "state_parameters_present": True,
                "time": 0.05,
            },
            "provenance": {
                "fluidfft": "0.4.5",
                "fluidsim": "0.9.0",
                "state_sha256": digest,
            },
        }

    def test_manifest_compatibility_and_grid_mismatch(self) -> None:
        digest = "a" * 64
        source = self._manifest(digest)
        target = self._target(digest)
        report = restart_compatibility.compare(source, target)
        self.assertTrue(report["compatible_for_mechanical_restart"], report)
        self.assertFalse(report["physical_validity_established"])
        target["parameters"]["oper"]["nx"] = 64
        mismatch = restart_compatibility.compare(source, target)
        self.assertFalse(mismatch["compatible_for_mechanical_restart"])
        self.assertTrue(
            any(
                item["code"] == "grid_or_domain_mismatch"
                for item in mismatch["blockers"]
            )
        )


if __name__ == "__main__":
    unittest.main()
