"""Dependency-free help checks and pinned-runtime synthetic CLI tests."""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pymatgen"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import mp_query  # noqa: E402
import artifact_manifest  # noqa: E402
import composition_structure_validator  # noqa: E402
import io_conversion_plan  # noqa: E402
import phase_diagram_generator  # noqa: E402
import structure_analyzer  # noqa: E402
import structure_converter  # noqa: E402
import symmetry_sensitivity_report  # noqa: E402


CLI_NAMES = (
    "artifact_manifest.py",
    "composition_structure_validator.py",
    "io_conversion_plan.py",
    "mp_query.py",
    "phase_diagram_generator.py",
    "structure_analyzer.py",
    "structure_converter.py",
    "symmetry_sensitivity_report.py",
)
MODULES = {
    "artifact_manifest.py": artifact_manifest,
    "composition_structure_validator.py": composition_structure_validator,
    "io_conversion_plan.py": io_conversion_plan,
    "mp_query.py": mp_query,
    "phase_diagram_generator.py": phase_diagram_generator,
    "structure_analyzer.py": structure_analyzer,
    "structure_converter.py": structure_converter,
    "symmetry_sensitivity_report.py": symmetry_sensitivity_report,
}


class CliResult:
    def __init__(self, returncode: int, stdout: str, stderr: str):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def run_script(
    name: str,
    *arguments: str,
    cwd: Path | None = None,
    timeout: int = 60,
) -> CliResult:
    del timeout
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment.pop("MP_API_KEY", None)
    stdout = io.StringIO()
    stderr = io.StringIO()
    previous = Path.cwd()
    try:
        if cwd is not None:
            os.chdir(cwd)
        with (
            mock.patch.object(sys, "argv", [name, *map(str, arguments)]),
            mock.patch.dict(os.environ, environment, clear=True),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            try:
                status = MODULES[name].main()
            except SystemExit as exc:
                status = int(exc.code or 0)
    finally:
        os.chdir(previous)
    return CliResult(status, stdout.getvalue(), stderr.getvalue())


def payload(result: CliResult) -> dict:
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"invalid JSON\nstdout={result.stdout}\nstderr={result.stderr}"
        ) from exc


class DependencyFreeTests(unittest.TestCase):
    def test_all_helps_work_without_importing_optional_packages(self) -> None:
        for name in CLI_NAMES:
            with self.subTest(name=name):
                result = run_script(name, "--help")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage:", result.stdout.casefold())

    def test_io_plan_is_nonexecuting_and_discloses_loss(self) -> None:
        result = run_script(
            "io_conversion_plan.py",
            "--input",
            "input.cif",
            "--output",
            "output.xyz",
            "--input-format",
            "cif",
            "--output-format",
            "xyz",
            "--periodic",
        )
        report = payload(result)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(report["executed"])
        self.assertFalse(report["files_opened"])
        self.assertTrue(report["representation_risks"])

    def test_mp_query_defaults_to_plan_and_never_reads_key(self) -> None:
        result = run_script(
            "mp_query.py",
            "--chemsys",
            "Li-Fe-O",
            "--energy-above-hull",
            "0",
            "0.05",
            "--fields",
            "formula_pretty,energy_above_hull,origins",
            "--limit",
            "10",
        )
        report = payload(result)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(report["execute_requested"])
        self.assertFalse(report["network_will_be_accessed"])
        self.assertEqual(report["query"]["limit"], 10)
        self.assertIn("material_id", report["query"]["effective_fields"])

    def test_execute_without_named_key_fails_before_output_or_network(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = run_script(
                "mp_query.py",
                "--material-id",
                "mp-149",
                "--fields",
                "formula_pretty",
                "--limit",
                "1",
                "--execute",
                "--output",
                "result.json",
                cwd=root,
            )
            report = payload(result)
            self.assertEqual(result.returncode, 2)
            self.assertIn("MP_API_KEY", report["error"])
            self.assertFalse((root / "result.json").exists())
            self.assertFalse(report["api_key_logged"])


class PinnedRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            from pymatgen.core import Lattice, Structure
        except ImportError as exc:
            raise unittest.SkipTest("pinned pymatgen runtime not installed") from exc
        cls.Lattice = Lattice
        cls.Structure = Structure

    def write_structure(self, root: Path) -> Path:
        from pymatgen.io.cif import CifWriter

        structure = self.Structure(
            self.Lattice.cubic(5.64),
            ["Na", "Cl"],
            [[0, 0, 0], [0.5, 0.5, 0.5]],
        )
        path = root / "synthetic.cif"
        CifWriter(structure).write_file(path)
        return path

    def test_structure_tools_on_synthetic_crystal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_structure(root)
            analyzer = run_script(
                "structure_analyzer.py",
                "synthetic.cif",
                "--symmetry",
                "--max-site-records",
                "10",
                cwd=root,
            )
            analysis = payload(analyzer)
            self.assertEqual(analyzer.returncode, 0, analyzer.stderr)
            self.assertEqual(analysis["composition"]["reduced_formula"], "NaCl")
            self.assertEqual(analysis["sites"]["coordinate_mode"], "fractional")
            self.assertEqual(analysis["symmetry"]["space_group_symbol"], "Pm-3m")

            validator = run_script(
                "composition_structure_validator.py",
                "structure",
                "synthetic.cif",
                cwd=root,
            )
            validation = payload(validator)
            self.assertEqual(validator.returncode, 0, validator.stderr)
            self.assertTrue(validation["ok"])
            self.assertEqual(validation["periodic_boundary_conditions"], [True] * 3)

            symmetry = run_script(
                "symmetry_sensitivity_report.py",
                "synthetic.cif",
                "--symprec",
                "0.001,0.01,0.1",
                "--angle-tolerance",
                "1,5",
                cwd=root,
            )
            sensitivity = payload(symmetry)
            self.assertEqual(symmetry.returncode, 0, symmetry.stderr)
            self.assertEqual(sensitivity["symmetry"]["combinations"], 6)

    def test_composition_conversion_phase_diagram_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_structure(root)
            composition = run_script(
                "composition_structure_validator.py",
                "composition",
                "Fe2O3",
                cwd=root,
            )
            composition_report = payload(composition)
            self.assertEqual(composition.returncode, 0, composition.stderr)
            self.assertEqual(composition_report["reduced_formula"], "Fe2O3")
            self.assertFalse(
                composition_report["oxidation_state_guess_requested"]
            )

            converted = run_script(
                "structure_converter.py",
                "synthetic.cif",
                "POSCAR.new",
                "--output-format",
                "poscar",
                "--coordinate-mode",
                "direct",
                "--allow-lossy",
                "--acknowledge-parser-warnings",
                cwd=root,
            )
            conversion_report = payload(converted)
            self.assertEqual(converted.returncode, 0, converted.stderr)
            self.assertTrue((root / "POSCAR.new").is_file())
            self.assertFalse(conversion_report["output"]["overwrote_existing"])

            phase_data = {
                "schema_version": "1.0",
                "energy_unit": "eV",
                "energy_basis": "total_per_entry",
                "provenance": {
                    "source": "synthetic unit test",
                    "method": "invented values; not scientific data",
                },
                "entries": [
                    {
                        "entry_id": "local-Li",
                        "composition": "Li",
                        "energy_eV": -1.0,
                        "provenance": {"source": "synthetic unit test"},
                    },
                    {
                        "entry_id": "local-O2",
                        "composition": "O2",
                        "energy_eV": -2.0,
                        "provenance": {"source": "synthetic unit test"},
                    },
                    {
                        "entry_id": "local-Li2O",
                        "composition": "Li2O",
                        "energy_eV": -4.0,
                        "provenance": {"source": "synthetic unit test"},
                    },
                ],
            }
            (root / "entries.json").write_text(
                json.dumps(phase_data, allow_nan=False),
                encoding="utf-8",
            )
            phase = run_script(
                "phase_diagram_generator.py",
                "entries.json",
                "--analyze",
                "Li2O",
                cwd=root,
            )
            phase_report = payload(phase)
            self.assertEqual(phase.returncode, 0, phase.stderr)
            self.assertEqual(phase_report["chemical_system"], "Li-O")
            self.assertEqual(phase_report["stable_entry_count"], 3)
            self.assertFalse(phase_report["experimental_validity_established"])

            manifest = run_script(
                "artifact_manifest.py",
                "--artifact",
                "entries.json",
                "--artifact",
                "POSCAR.new",
                "--output",
                "manifest.json",
                "--workflow",
                "synthetic pymatgen test",
                cwd=root,
            )
            manifest_report = payload(manifest)
            self.assertEqual(manifest.returncode, 0, manifest.stderr)
            self.assertEqual(manifest_report["artifact_count"], 2)
            self.assertTrue((root / "manifest.json").is_file())

    def test_strict_phase_json_rejects_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "bad.json").write_text(
                '{"schema_version":"1.0","schema_version":"1.0"}',
                encoding="utf-8",
            )
            result = run_script(
                "phase_diagram_generator.py",
                "bad.json",
                cwd=root,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("duplicate JSON key", payload(result)["error"])

    def test_mocked_mp_execute_is_bounded_redacted_and_records_db(self) -> None:
        class FakeSummary:
            available_fields = ["material_id", "formula_pretty"]
            kwargs: dict | None = None

            def search(self, **kwargs):
                self.kwargs = kwargs
                return [{"material_id": "mp-149", "formula_pretty": "Si"}]

        class FakeMaterials:
            def __init__(self):
                self.summary = FakeSummary()

        class FakeMPRester:
            instance = None

            def __init__(self, **kwargs):
                self.kwargs = kwargs
                self.db_version = "synthetic-db-version"
                self.materials = FakeMaterials()
                FakeMPRester.instance = self

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

        args = mp_query.build_parser().parse_args(
            [
                "--material-id",
                "mp-149",
                "--fields",
                "formula_pretty",
                "--limit",
                "1",
                "--execute",
                "--output",
                "result.json",
            ]
        )
        contract = mp_query.query_contract(args)
        with (
            tempfile.TemporaryDirectory() as temporary,
            mock.patch.dict(
                os.environ,
                {"MP_API_KEY": "synthetic-test-secret"},
                clear=True,
            ),
            mock.patch("mp_api.client.MPRester", FakeMPRester),
        ):
            output = Path(temporary) / "result.json"
            report = mp_query.execute_query(args, contract, output)
            text = output.read_text(encoding="utf-8")
        self.assertEqual(report["returned"], 1)
        self.assertEqual(
            report["provenance"]["database_version"],
            "synthetic-db-version",
        )
        self.assertNotIn("synthetic-test-secret", text)
        instance = FakeMPRester.instance
        self.assertIsNotNone(instance)
        self.assertFalse(instance.kwargs["include_user_agent"])
        self.assertFalse(instance.kwargs["notify_db_version"])
        self.assertEqual(instance.kwargs["endpoint"], "https://api.materialsproject.org/")
        self.assertEqual(instance.materials.summary.kwargs["num_chunks"], 1)
        self.assertEqual(instance.materials.summary.kwargs["chunk_size"], 1)


if __name__ == "__main__":
    unittest.main()
