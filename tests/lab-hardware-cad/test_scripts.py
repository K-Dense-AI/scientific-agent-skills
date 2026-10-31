"""Standard-library tests for the lab-hardware-cad scripts.

Everything here runs without build123d: the standards database, the fit-check
arithmetic, argument parsing, and the CLI help paths. Geometry commands are
exercised only for their guarded failure when the kernel is absent.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "lab-hardware-cad"
SCRIPTS = SKILL_ROOT / "scripts"
ASSETS = SKILL_ROOT / "assets"
REFERENCES = SKILL_ROOT / "references"

sys.path.insert(0, str(SCRIPTS))

import _common  # noqa: E402

CLI_NAMES = ("gen.py", "check.py", "snapshot.py")
FAMILY_REFERENCES = (
    "microfluidics.md",
    "optomechanics.md",
    "labware-adapters.md",
    "behavior-rigs.md",
)
CROSS_CUTTING_REFERENCES = (
    "fabrication-limits.md",
    "validation.md",
    "build123d-patterns.md",
)


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, *args],
        capture_output=True,
        text=True,
        cwd=str(SKILL_ROOT),
        timeout=120,
    )


class TestLayout(unittest.TestCase):
    def test_skill_md_exists(self):
        self.assertTrue((SKILL_ROOT / "SKILL.md").is_file())

    def test_all_references_present(self):
        for name in FAMILY_REFERENCES + CROSS_CUTTING_REFERENCES:
            with self.subTest(reference=name):
                self.assertTrue((REFERENCES / name).is_file(), f"missing {name}")

    def test_skill_md_links_every_reference(self):
        body = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for name in FAMILY_REFERENCES + CROSS_CUTTING_REFERENCES:
            with self.subTest(reference=name):
                self.assertIn(name, body, f"SKILL.md never routes to {name}")

    def test_no_script_shadows_a_stdlib_module(self):
        """A script on sys.path that shadows a stdlib module breaks the interpreter.

        Naming one `inspect.py` shadowed the stdlib `inspect`, which broke
        typing_extensions and therefore build123d itself.
        """
        stdlib = set(sys.stdlib_module_names)
        for path in SCRIPTS.glob("*.py"):
            with self.subTest(script=path.name):
                self.assertNotIn(path.stem, stdlib, f"{path.name} shadows a stdlib module")

    def test_scripts_are_executable_clis(self):
        for name in CLI_NAMES:
            with self.subTest(script=name):
                self.assertTrue((SCRIPTS / name).is_file())


class TestHelp(unittest.TestCase):
    def test_each_cli_has_help(self):
        for name in CLI_NAMES:
            with self.subTest(script=name):
                result = run_cli(str(SCRIPTS / name), "--help")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage", result.stdout.lower())

    def test_check_subcommands_have_help(self):
        for sub in ("standards", "facts", "fit", "clearance", "interfaces", "geometry", "probe", "bores"):
            with self.subTest(subcommand=sub):
                result = run_cli(str(SCRIPTS / "check.py"), sub, "--help")
                self.assertEqual(result.returncode, 0, result.stderr)


class TestStandardsDatabase(unittest.TestCase):
    def setUp(self):
        self.data = _common.load_standards()

    def test_units_are_millimetres(self):
        self.assertEqual(self.data["units"], "mm")

    def test_every_standard_is_well_formed(self):
        for key, entry in self.data["standards"].items():
            with self.subTest(standard=key):
                for field in ("title", "authority", "document", "verified", "dimensions"):
                    self.assertIn(field, entry, f"{key} missing {field}")
                self.assertIsInstance(entry["verified"], bool)
                self.assertTrue(entry["dimensions"], f"{key} has no dimensions")
                for name, dim in entry["dimensions"].items():
                    self.assertIn("nominal", dim, f"{key}.{name} has no nominal")
                    self.assertIsInstance(dim["nominal"], (int, float))

    def test_fit_checks_reference_real_dimensions(self):
        for key, entry in self.data["standards"].items():
            for check in entry.get("fit_checks", []):
                with self.subTest(standard=key, dimension=check["dimension"]):
                    self.assertIn(check["dimension"], entry["dimensions"])
                    self.assertIn(
                        check["measure"],
                        {"bbox_x", "bbox_y", "bbox_z", "bbox_min", "bbox_mid", "bbox_max"},
                    )

    def test_unverified_entries_say_so_in_their_notes(self):
        """An unverified number must be visibly flagged where it is read."""
        for key, entry in self.data["standards"].items():
            if entry["verified"]:
                continue
            notes = " ".join(
                str(dim.get("note", "")) for dim in entry["dimensions"].values()
            ).upper()
            with self.subTest(standard=key):
                self.assertIn("UNVERIFIED", notes, f"{key} is unverified but says so nowhere")

    def test_slas_footprint_matches_the_published_standard(self):
        dims = self.data["standards"]["slas-microplate-footprint"]["dimensions"]
        self.assertAlmostEqual(dims["footprint_length"]["nominal"], 127.76)
        self.assertAlmostEqual(dims["footprint_width"]["nominal"], 85.48)
        self.assertAlmostEqual(dims["corner_radius"]["nominal"], 3.18)

    def test_metric_and_imperial_grids_are_distinct(self):
        metric = self.data["standards"]["optical-breadboard-metric"]["dimensions"]
        imperial = self.data["standards"]["optical-breadboard-imperial"]["dimensions"]
        self.assertNotEqual(
            metric["grid_pitch"]["nominal"], imperial["grid_pitch"]["nominal"]
        )

    def test_get_standard_rejects_unknown_id(self):
        with self.assertRaises(_common.LabCadError):
            _common.get_standard("no-such-standard")


class TestFitArithmetic(unittest.TestCase):
    """The fit check is the skill's main safeguard; verify its arithmetic directly."""

    def _fit(self, *args: str) -> subprocess.CompletedProcess:
        return run_cli(str(SCRIPTS / "check.py"), "--json", "fit", *args)

    def test_match_intent_accepts_a_conforming_dimension(self):
        result = self._fit(
            "--standard", "slas-microplate-footprint",
            "--value", "footprint_length=127.76",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["pass"])

    def test_match_intent_rejects_an_out_of_tolerance_dimension(self):
        result = self._fit(
            "--standard", "slas-microplate-footprint",
            "--value", "footprint_length=130.0",
        )
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["pass"])

    def test_envelope_intent_requires_maximum_material_condition(self):
        """A continuous pocket must account for the overall +0.50 mm tolerance."""
        nominal = self._fit(
            "--standard", "slas-microplate-footprint", "--intent", "envelope",
            "--clearance", "0.8", "--value", "footprint_length=128.56",
        )
        self.assertEqual(nominal.returncode, 1, "nominal-sized pocket must fail envelope intent")

        max_material = self._fit(
            "--standard", "slas-microplate-footprint", "--intent", "envelope",
            "--clearance", "0.8", "--value", "footprint_length=129.06",
        )
        self.assertEqual(max_material.returncode, 0, max_material.stderr)
        self.assertTrue(json.loads(max_material.stdout)["pass"])

    def test_clearance_offset_shifts_the_expected_band(self):
        result = self._fit(
            "--standard", "slas-microplate-footprint",
            "--clearance", "1.05", "--value", "footprint_length=129.06",
        )
        payload = json.loads(result.stdout)
        self.assertTrue(payload["pass"])
        self.assertEqual(payload["clearance_applied_mm"], 1.05)

    def test_unknown_dimension_is_rejected(self):
        result = self._fit(
            "--standard", "slas-microplate-footprint", "--value", "not_a_dimension=1.0",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown dimension", result.stderr)

    def test_non_numeric_value_is_rejected(self):
        result = self._fit(
            "--standard", "slas-microplate-footprint", "--value", "footprint_length=wide",
        )
        self.assertEqual(result.returncode, 2)

    def test_standard_without_bbox_checks_explains_itself(self):
        result = self._fit("--standard", "slas-well-positions-96")
        self.assertEqual(result.returncode, 2)
        self.assertIn("--value", result.stderr)


class TestDeclaredInterfaces(unittest.TestCase):
    """The interface check is what gates fabrication for internal features.

    It runs against a manifest, so the whole path is exercisable without the
    geometry kernel.
    """

    def _manifest(self, interfaces) -> Path:
        handle = tempfile.NamedTemporaryFile(
            mode="w", suffix=".manifest.json", delete=False, encoding="utf-8"
        )
        with handle:
            json.dump({"artifact_name": "t", "interfaces": interfaces}, handle)
        path = Path(handle.name)
        self.addCleanup(path.unlink, missing_ok=True)
        return path

    def _check(self, interfaces) -> subprocess.CompletedProcess:
        return run_cli(
            str(SCRIPTS / "check.py"), "--json", "interfaces", str(self._manifest(interfaces))
        )

    def _pocket(self, value: float) -> dict:
        return {
            "feature": "plate pocket length",
            "standard": "slas-microplate-footprint",
            "dimension": "footprint_length",
            "value": value,
            "intent": "envelope",
            "clearance": 0.80,
        }

    def test_pocket_at_maximum_material_passes(self):
        result = self._check([self._pocket(129.06)])
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["pass"])
        self.assertEqual(payload["checks"][0]["feature"], "plate pocket length")

    def test_pocket_sized_from_nominal_fails(self):
        """127.76 + 0.80 ignores the plate's overall +0.50 tolerance."""
        result = self._check([self._pocket(128.56)])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["pass"])

    def test_one_failing_entry_fails_the_whole_check(self):
        result = self._check([self._pocket(129.06), self._pocket(128.56)])
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual([item["pass"] for item in payload["checks"]], [True, False])

    def test_unverified_standard_is_flagged_in_the_output(self):
        result = run_cli(
            str(SCRIPTS / "check.py"), "interfaces",
            str(self._manifest([{
                "standard": "cuvette-standard-10mm",
                "dimension": "external_width",
                "value": 12.5,
            }])),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("not verified", result.stdout)

    def test_explicit_empty_interfaces_pass_with_unchecked_warning(self):
        result = run_cli(
            str(SCRIPTS / "check.py"), "interfaces", str(self._manifest([]))
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("UNCHECKED", result.stdout)
        payload = json.loads(self._check([]).stdout)
        self.assertTrue(payload["pass"])
        self.assertEqual(payload["checks"], [])

    def test_missing_or_malformed_interfaces_are_not_empty_declarations(self):
        for payload in ({}, [], {"interfaces": None}, {"interfaces": False},
                        {"interfaces": 0}, {"interfaces": ""}, {"interfaces": {}}):
            with self.subTest(payload=payload):
                target = self._manifest([])
                target.write_text(json.dumps(payload), encoding="utf-8")
                result = run_cli(str(SCRIPTS / "check.py"), "interfaces", str(target))
                self.assertEqual(result.returncode, 2)
                self.assertIn("interfaces", result.stderr)

    def test_unsupported_target_is_rejected(self):
        result = run_cli(
            str(SCRIPTS / "check.py"), "interfaces", str(SKILL_ROOT / "SKILL.md")
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("manifest.json", result.stderr)


class TestInterfaceNormalisation(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        entry = _common.normalise_interfaces([
            {"standard": "s", "dimension": "d", "value": 1}
        ])[0]
        self.assertEqual(entry["intent"], "match")
        self.assertEqual(entry["clearance"], 0.0)
        self.assertEqual(entry["feature"], "d")
        self.assertIsInstance(entry["value"], float)

    def test_missing_keys_are_named(self):
        with self.assertRaises(_common.LabCadError) as caught:
            _common.normalise_interfaces([{"standard": "s"}])
        self.assertIn("dimension", str(caught.exception))
        self.assertIn("value", str(caught.exception))

    def test_bad_intent_is_rejected(self):
        with self.assertRaises(_common.LabCadError):
            _common.normalise_interfaces(
                [{"standard": "s", "dimension": "d", "value": 1, "intent": "loose"}]
            )

    def test_non_numeric_value_is_rejected(self):
        with self.assertRaises(_common.LabCadError):
            _common.normalise_interfaces(
                [{"standard": "s", "dimension": "d", "value": "wide"}]
            )

    def test_callable_form_wins_over_a_static_list(self):
        """A function is the documented form, because it sees --param overrides."""
        module = types.SimpleNamespace(
            INTERFACES=[{"standard": "s", "dimension": "d", "value": 1.0}],
            interfaces=lambda: [{"standard": "s", "dimension": "d", "value": 2.0}],
        )
        self.assertEqual(_common.model_interfaces(module)[0]["value"], 2.0)

    def test_a_model_declaring_nothing_returns_empty(self):
        self.assertEqual(_common.model_interfaces(types.SimpleNamespace()), [])


class TestStandardsCli(unittest.TestCase):
    def test_list_runs_without_build123d(self):
        result = run_cli(str(SCRIPTS / "check.py"), "--json", "standards", "--list")
        self.assertEqual(result.returncode, 0, result.stderr)
        listing = json.loads(result.stdout)
        self.assertTrue(any(item["id"] == "slas-microplate-footprint" for item in listing))

    def test_show_reports_the_source_document(self):
        result = run_cli(
            str(SCRIPTS / "check.py"), "standards", "--show", "cage-system-30mm"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("30.0", result.stdout)

    def test_show_unknown_standard_lists_alternatives(self):
        result = run_cli(str(SCRIPTS / "check.py"), "standards", "--show", "nope")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Available", result.stderr)


class TestHelpers(unittest.TestCase):
    def test_parse_params_coerces_types(self):
        params = _common.parse_params(["wall_t_mm=3.0", "count=4", "flag=true", "note=abc"])
        self.assertEqual(params["wall_t_mm"], 3.0)
        self.assertEqual(params["count"], 4)
        self.assertIs(params["flag"], True)
        self.assertEqual(params["note"], "abc")

    def test_parse_params_rejects_malformed_pairs(self):
        with self.assertRaises(_common.LabCadError):
            _common.parse_params(["wall_t_mm"])

    def test_measure_resolves_bbox_names(self):
        facts = {"bounding_box_mm": {"x": 10.0, "y": 20.0, "z": 5.0}}
        self.assertEqual(_common.measure(facts, "bbox_x"), 10.0)
        self.assertEqual(_common.measure(facts, "bbox_y"), 20.0)
        self.assertEqual(_common.measure(facts, "bbox_max"), 20.0)
        self.assertEqual(_common.measure(facts, "bbox_min"), 5.0)

    def test_measure_swap_xy_exchanges_axes(self):
        facts = {"bounding_box_mm": {"x": 10.0, "y": 20.0, "z": 5.0}}
        self.assertEqual(_common.measure(facts, "bbox_x", swap_xy=True), 20.0)

    def test_measure_rejects_unknown_name(self):
        facts = {"bounding_box_mm": {"x": 1.0, "y": 1.0, "z": 1.0}}
        with self.assertRaises(_common.LabCadError):
            _common.measure(facts, "bbox_w")

    def test_load_shape_rejects_unsupported_suffix(self):
        with self.assertRaises(_common.LabCadError):
            _common.load_shape(SKILL_ROOT / "SKILL.md")

    def test_run_model_rejects_a_missing_file(self):
        with self.assertRaises(_common.LabCadError):
            _common.run_model(SKILL_ROOT / "no_such_model.py")



class TestFailClosedChecks(unittest.TestCase):
    def test_booleans_and_overflow_are_not_dimensions(self):
        for value in (True, False, 10 ** 1000):
            for key in ("value", "clearance"):
                with self.subTest(value_type=type(value).__name__, key=key):
                    entry = {"standard": "s", "dimension": "d", "value": 1, key: value}
                    with self.assertRaises(_common.LabCadError):
                        _common.normalise_interfaces([entry])
            for raw in (
                {"clear": {"cylinder": value}},
                {"clear": {"box": [1, 1, value]}},
                {"clear": {"box": [1, 1, 1]}, "tol_mm3": value},
                {"bbox_z": {"max": value}},
            ):
                with self.subTest(value_type=type(value).__name__, raw_kind=list(raw)):
                    with self.assertRaises(_common.LabCadError):
                        _common.normalise_checks([raw])

    def test_bad_regions_cannot_pass_vacuously(self):
        for raw in (
            {'clear': {'box': [1, 1, 1], 'at': []}},
            {'material': {'cylinder': 1, 'at': []}},
            {'clear': {'cylinder': float('nan')}},
            {'clear': {'box': [1, 1, float('inf')]}},
            {'clear': {'cylinder': 1, 'span': [2, 2]}},
            {'clear': {'box': [1, 1, 1]}, 'tol_mm3': float('inf')},
            {'material': {'box': [1, 1, 1]}, 'min_mm3': 0},
            {'bbox_z': {'max': float('nan')}},
            {'bbox_z': {'min': None}},
            {'bbox_z': {'min': 4, 'max': 2}},
        ):
            with self.subTest(raw=raw), self.assertRaises(_common.LabCadError):
                _common.normalise_checks([raw])

    def test_nonfinite_fit_and_wrong_units_fail_cleanly(self):
        for args in (
            ('--standard', 'slas-microplate-footprint', '--value', 'footprint_length=inf'),
            ('--standard', 'slas-microplate-footprint', '--value', 'footprint_length=1000', '--clearance', 'inf'),
            ('--standard', 'sm1-lens-tube-thread', '--value', 'threads_per_inch=40'),
        ):
            result = run_cli(str(SCRIPTS / 'check.py'), 'fit', *args)
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertNotIn('Traceback', result.stderr)

    def test_slas_overall_and_local_bands_are_not_interchangeable(self):
        import check
        footprint = _common.get_standard('slas-microplate-footprint')
        self.assertFalse(check._evaluate(footprint, 'footprint_length', 128.81, .8, 'test', 'envelope')['pass'])
        self.assertTrue(check._evaluate(footprint, 'footprint_length_at_corners', 128.81, .8, 'test', 'envelope')['pass'])
        height = _common.get_standard('slas-microplate-height')
        self.assertEqual(height['fit_checks'][0]['dimension'], 'overall_plate_height')
        self.assertTrue(check._evaluate(height, 'overall_plate_height', 15.11, 0, 'test', 'match')['pass'])
        self.assertFalse(check._evaluate(height, 'plate_height', 15.11, 0, 'test', 'match')['pass'])

    def test_clearance_failures_do_not_exit_success(self):
        import check
        from contextlib import redirect_stdout
        from io import StringIO
        from unittest.mock import patch
        args = types.SimpleNamespace(a=Path('a.step'), b=Path('b.step'), min=0, as_json=True)
        with patch.object(check, 'load_shape'), patch.object(check, 'intersection_volume', return_value=0), patch.object(check, '_min_distance', return_value=None), redirect_stdout(StringIO()):
            self.assertEqual(check.cmd_clearance(args), 2)
        with patch.object(check, 'load_shape'), patch.object(check, 'intersection_volume', side_effect=_common.LabCadError('kernel failed')), self.assertRaises(_common.LabCadError):
            check.cmd_clearance(args)


if __name__ == "__main__":
    unittest.main()
