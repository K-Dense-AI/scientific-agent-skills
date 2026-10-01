"""Synthetic local-only tests for the MATLAB helper CLIs."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "matlab"
SCRIPTS = SKILL_ROOT / "scripts"
CLI_NAMES = (
    "generate_function_scaffold.py",
    "inventory_mat_file.py",
    "plan_batch_command.py",
    "plan_python_compatibility.py",
    "reproducibility_report.py",
    "scan_m_code.py",
    "validate_project_manifest.py",
)


def run_cli(
    name: str, *arguments: object, cwd: Path | None = None
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
        timeout=45,
    )


def parsed(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"stdout is not JSON\nstdout={result.stdout}\nstderr={result.stderr}"
        ) from exc


def valid_manifest() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "project_name": "synthetic-project",
        "runtime": "matlab",
        "matlab_release": "R2026a",
        "octave_version": None,
        "entry_points": [{"kind": "function", "path": "src/analyzeSignal.m"}],
        "test_paths": ["tests"],
        "required_products": [
            {
                "license_status": "unknown",
                "minimum_release": "R2026a",
                "name": "MATLAB",
                "purpose": "Base runtime",
            }
        ],
        "optional_products": [],
        "octave_packages": [],
        "startup_actions": [],
        "shutdown_actions": [],
        "external_interfaces": [],
        "generated_artifacts": ["results/report.json"],
        "notes": ["synthetic fixture"],
    }


class DependencyFreeHelpTests(unittest.TestCase):
    def test_all_cli_helps_succeed(self) -> None:
        for name in CLI_NAMES:
            with self.subTest(name=name):
                result = run_cli(name, "--help")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage:", result.stdout.casefold())


class CommandPlannerTests(unittest.TestCase):
    def test_octave_literals_preserve_text_and_scalar_object_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "analyze.m").write_text("function analyze(x)\nend\n")
            payload = {"empty": [], "labels": ["a", "b"],
                       "path": "C:\\new\\it's\\data"}
            result = run_cli("plan_batch_command.py", "octave", "function",
                             "analyze.m", "--root", root,
                             "--arg-json", json.dumps(payload))
            self.assertEqual(result.returncode, 0, result.stderr)
            statement = parsed(result)["statement"]
            self.assertEqual(statement, "analyze(struct('empty', {{}}, "
                             "'labels', {{'a', 'b'}}, "
                             "'path', {'C:\\new\\it''s\\data'}))")
            self.assertNotIn("\n", statement)

    def test_matlab_cell_fields_do_not_expand_structs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "analyze.m").write_text("function analyze(x)\nend\n")
            result = run_cli("plan_batch_command.py", "matlab", "function",
                             "analyze.m", "--root", root,
                             "--arg-json", '{"empty":[],"mixed":[1,"a"]}')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(parsed(result)["statement"],
                             'analyze(struct("empty", {{}}, "mixed", {{1, "a"}}))')

    def test_matlab_script_and_function_plans_never_execute(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source = root / "analyzeSignal.m"
            source.write_text(
                "function y = analyzeSignal(x)\ny = x;\nend\n",
                encoding="utf-8",
            )
            script = run_cli(
                "plan_batch_command.py",
                "matlab",
                "script",
                source.name,
                "--root",
                root,
            )
            self.assertEqual(script.returncode, 0, script.stderr)
            script_plan = parsed(script)
            self.assertFalse(script_plan["executes"])
            self.assertEqual(script_plan["command_argv"][-2], "-batch")
            self.assertIn("run(", str(script_plan["statement"]))

            function = run_cli(
                "plan_batch_command.py",
                "matlab",
                "function",
                source.name,
                "--root",
                root,
                "--arg-json",
                '{"value":3}',
            )
            self.assertEqual(function.returncode, 0, function.stderr)
            function_plan = parsed(function)
            self.assertIn("struct(", str(function_plan["statement"]))
            self.assertFalse(function_plan["network_accessed"])

    def test_octave_plan_uses_no_init_and_traversal_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "main.m").write_text("x = 1;\n", encoding="utf-8")
            octave = run_cli(
                "plan_batch_command.py",
                "octave",
                "script",
                "main.m",
                "--root",
                root,
            )
            self.assertEqual(octave.returncode, 0, octave.stderr)
            argv = parsed(octave)["command_argv"]
            self.assertIn("--no-init-all", argv)

            outside = root.parent / "outside-matlab-skill-test.m"
            outside.write_text("x = 1;\n", encoding="utf-8")
            try:
                rejected = run_cli(
                    "plan_batch_command.py",
                    "matlab",
                    "script",
                    "../outside-matlab-skill-test.m",
                    "--root",
                    root,
                )
                self.assertEqual(rejected.returncode, 2)
            finally:
                outside.unlink(missing_ok=True)


class StaticScannerTests(unittest.TestCase):
    def test_risk_surfaces_and_opaque_mex_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "unsafe.m").write_text(
                "function unsafe(name)\n"
                "eval(name);\n"
                "system('echo unsafe');\n"
                "data = load('unknown.mat');\n"
                "end\n",
                encoding="utf-8",
            )
            (root / "extension.mexa64").write_bytes(b"synthetic")
            result = run_cli(
                "scan_m_code.py",
                ".",
                "--root",
                root,
                "--recursive",
            )
            self.assertEqual(result.returncode, 1, result.stderr)
            report = parsed(result)
            rules = {finding["rule"] for finding in report["findings"]}
            self.assertTrue(
                {"dynamic_eval", "shell_execution", "mat_load", "mex_binary"}
                <= rules
            )
            self.assertFalse(report["content_emitted"])

    def test_generated_scaffolds_are_clean_at_high_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            generated = run_cli(
                "generate_function_scaffold.py",
                "analyzeSignal",
                "--root",
                root,
                "--write",
            )
            self.assertEqual(generated.returncode, 0, generated.stderr)
            report = parsed(generated)
            self.assertTrue(report["wrote_files"])
            scan = run_cli(
                "scan_m_code.py",
                ".",
                "--root",
                root,
                "--recursive",
            )
            self.assertEqual(scan.returncode, 0, scan.stderr)
            self.assertEqual(parsed(scan)["summary"]["high"], 0)


class ManifestAndReproducibilityTests(unittest.TestCase):
    def test_manifest_validates_without_claiming_license_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "analyzeSignal.m").write_text(
                "function y = analyzeSignal(x)\ny=x;\nend\n",
                encoding="utf-8",
            )
            manifest = root / "project-manifest.json"
            manifest.write_text(
                json.dumps(valid_manifest()), encoding="utf-8"
            )
            result = run_cli(
                "validate_project_manifest.py",
                manifest.name,
                "--root",
                root,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = parsed(result)
            self.assertFalse(report["license_verified"])
            self.assertEqual(report["runtime"], "matlab")

    def test_reproducibility_report_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source = root / "analysis.m"
            source.write_text("function y=analysis(x)\ny=x;\nend\n", encoding="utf-8")
            arguments = (
                "--root",
                root,
                "--file",
                source.name,
                "--runtime",
                "matlab",
                "--runtime-version",
                "R2026a",
                "--rng-algorithm",
                "twister",
                "--rng-seed",
                1729,
                "--absolute-tolerance",
                1e-12,
                "--relative-tolerance",
                1e-9,
                "--tolerance-rationale",
                "synthetic deterministic fixture",
            )
            first = run_cli("reproducibility_report.py", *arguments)
            second = run_cli("reproducibility_report.py", *arguments)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(first.stdout, second.stdout)
            report = parsed(first)
            self.assertFalse(report["environment_dumped"])
            self.assertEqual(len(report["named_files"]), 1)


class PythonCompatibilityTests(unittest.TestCase):
    def test_newer_release_does_not_reuse_r2026a_engine_pin(self) -> None:
        result = run_cli("plan_python_compatibility.py", "--matlab-release",
                         "R2026b", "--python-version", "3.14")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(parsed(result)["ok"])

    def test_r2026a_exact_support_and_engine_version(self) -> None:
        result = run_cli(
            "plan_python_compatibility.py",
            "--python-version",
            "3.13.4",
            "--engine-version",
            "26.1.12",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = parsed(result)
        self.assertTrue(report["software_compatible"])
        self.assertFalse(report["ready_to_launch"])
        self.assertFalse(report["executes"])

    def test_unsupported_python_fails_closed(self) -> None:
        result = run_cli(
            "plan_python_compatibility.py",
            "--python-version",
            "3.14",
        )
        self.assertEqual(result.returncode, 1)
        self.assertFalse(parsed(result)["ok"])


class MatInventoryTests(unittest.TestCase):
    def test_optional_h5py_null_and_scalar_shapes_remain_distinct(self) -> None:
        try:
            import h5py
        except ImportError as exc:
            raise unittest.SkipTest("h5py is optional") from exc
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            path = root / "shapes.mat"
            with h5py.File(path, "w") as handle:
                handle.create_dataset("null", dtype="f8")
                handle.create_dataset("scalar", data=1.0)
                handle.create_dataset("zero_length", shape=(0,), dtype="f8")
            result = run_cli("inventory_mat_file.py", path.name, "--root", root,
                             "--backend", "hdf5")
            self.assertEqual(result.returncode, 0, result.stderr)
            records = parsed(result)["records"]
            self.assertEqual([record["shape"] for record in records],
                             [None, [], [0]])
            self.assertEqual([record["null_dataspace"] for record in records],
                             [True, False, False])
            self.assertTrue(all(not record["values_loaded"] for record in records))

    def test_header_only_inventory_and_pickle_refusal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            mat = root / "synthetic.mat"
            mat.write_bytes(
                b"MATLAB 5.0 MAT-file, synthetic metadata only"
                + b" " * 256
            )
            result = run_cli(
                "inventory_mat_file.py",
                mat.name,
                "--root",
                root,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = parsed(result)
            self.assertEqual(
                report["header"]["detected_kind"], "matlab_level5_v6_or_v7"
            )
            self.assertFalse(report["values_loaded"])
            self.assertFalse(report["safe_to_load"])

            disguised = root / "disguised.mat"
            disguised.write_bytes(b"\x80\x05synthetic-not-a-real-pickle")
            rejected = run_cli(
                "inventory_mat_file.py",
                disguised.name,
                "--root",
                root,
            )
            self.assertEqual(rejected.returncode, 1)
            self.assertEqual(
                parsed(rejected)["header"]["detected_kind"],
                "python_pickle_signature_refused",
            )

    def test_optional_scipy_metadata_smoke(self) -> None:
        try:
            import scipy.io
        except ImportError as exc:
            raise unittest.SkipTest("SciPy is optional") from exc
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            path = root / "scipy-synthetic.mat"
            scipy.io.savemat(path, {"numeric_fixture": [[1.0, 2.0]]})
            result = run_cli(
                "inventory_mat_file.py",
                path.name,
                "--root",
                root,
                "--backend",
                "scipy",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = parsed(result)
            self.assertEqual(report["backend"], "scipy.io.whosmat")
            self.assertEqual(report["records"][0]["class"], "double")
            self.assertFalse(report["records"][0]["values_loaded"])

    def test_optional_h5py_metadata_smoke(self) -> None:
        try:
            import h5py
        except ImportError as exc:
            raise unittest.SkipTest("h5py is optional") from exc
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            path = root / "hdf5-synthetic.mat"
            with h5py.File(path, "w") as handle:
                handle.create_dataset("numeric_fixture", data=[[1.0, 2.0]])
            result = run_cli(
                "inventory_mat_file.py",
                path.name,
                "--root",
                root,
                "--backend",
                "hdf5",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = parsed(result)
            self.assertEqual(report["backend"], "h5py-metadata")
            self.assertEqual(report["records"][0]["kind"], "dataset")
            self.assertFalse(report["records"][0]["values_loaded"])


if __name__ == "__main__":
    unittest.main()
