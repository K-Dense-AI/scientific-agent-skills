"""Synthetic tests for the standard-library scientific brainstorming CLIs."""

from __future__ import annotations

import json
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "scientific-brainstorming"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import evaluate_matrix
import session_scaffold
import validate_register
from _common import MAX_INPUT_BYTES, CliError, read_json, write_json

import skill_contract


def populated_register() -> dict:
    """Return a small valid synthetic register."""

    document = session_scaffold.build_scaffold(
        session_id="test-session",
        title="Synthetic session",
        question="Which synthetic mechanism should be checked?",
        participant_ids=["P01", "P02"],
        session_date="2026-07-23",
    )
    document["assumptions"] = [
        {
            "id": "A001",
            "statement": "The synthetic measurement reflects the construct.",
            "category": "measurement",
            "status": "untested",
            "test_or_check": "Compare with an orthogonal synthetic measure.",
            "owner_id": "P01",
            "evidence_refs": [],
        }
    ]
    document["ideas"] = [
        {
            "id": "I001",
            "statement": "Test a synthetic alternative mechanism.",
            "provenance": {
                "origin": "human",
                "contributor_ids": ["P01"],
                "recorded_stage": "independent",
                "source_refs": [],
                "ai_tool": None,
            },
            "assumption_ids": ["A001"],
            "predicted_observations": ["The synthetic signal changes direction."],
            "uncertainties": ["Synthetic measurement error is unknown."],
            "evidence_status": "not-checked",
            "status": "candidate",
        }
    ]
    return document


class ScaffoldTests(unittest.TestCase):
    def test_scaffold_is_deterministic_and_has_required_order(self):
        first = session_scaffold.build_scaffold(
            session_id="session-1",
            title="Title",
            question="Question?",
            participant_ids=["P01", "P02"],
            session_date="2026-07-23",
            constraints=["Budget is bounded"],
        )
        second = session_scaffold.build_scaffold(
            session_id="session-1",
            title="Title",
            question="Question?",
            participant_ids=["P01", "P02"],
            session_date="2026-07-23",
            constraints=["Budget is bounded"],
        )
        self.assertEqual(first, second)
        self.assertEqual(first["session"]["date"], "2026-07-23")
        stages = [entry["stage"] for entry in first["workflow"]]
        self.assertLess(
            stages.index("independent-generation"),
            stages.index("structured-sharing"),
        )
        self.assertEqual(first["ideas"], [])
        self.assertEqual(first["decision_log"], [])

    def test_scaffold_rejects_duplicate_participant_ids(self):
        with self.assertRaises(CliError):
            session_scaffold.build_scaffold(
                session_id="session-1",
                title="Title",
                question="Question?",
                participant_ids=["P01", "P01"],
            )


class SafeOutputTests(unittest.TestCase):
    def test_private_json_output_refuses_implicit_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output.json"
            write_json(str(output), {"ok": True})
            self.assertEqual(json.loads(output.read_text()), {"ok": True})
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            with self.assertRaises(CliError):
                write_json(str(output), {"ok": False})
            write_json(str(output), {"ok": False}, force=True)
            self.assertEqual(json.loads(output.read_text()), {"ok": False})

    def test_output_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real = root / "real.json"
            real.write_text("{}")
            link = root / "link.json"
            try:
                link.symlink_to(real)
            except OSError:
                self.skipTest("symlinks unavailable")
            with self.assertRaises(CliError):
                write_json(str(link), {"ok": True}, force=True)


class SafeInputTests(unittest.TestCase):
    def test_duplicate_json_keys_cannot_silently_replace_weights_or_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "duplicate.json"
            for text in ('{"weight": 1, "weight": 9}',
                         '{"provenance": {"origin": "human", "origin": "mixed"}}'):
                with self.subTest(text=text):
                    source.write_text(text, encoding="utf-8")
                    with self.assertRaisesRegex(CliError, "duplicate JSON key"):
                        read_json(str(source))

    def test_json_input_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real = root / "real.json"
            real.write_text("{}")
            link = root / "link.json"
            try:
                link.symlink_to(real)
            except OSError:
                self.skipTest("symlinks unavailable")
            with self.assertRaises(CliError):
                read_json(str(link))

    def test_oversized_input_is_rejected_before_parsing(self):
        with tempfile.TemporaryDirectory() as directory:
            oversized = Path(directory) / "oversized.json"
            oversized.write_bytes(b" " * (MAX_INPUT_BYTES + 1))
            with self.assertRaises(CliError):
                read_json(str(oversized))


class RegisterValidationTests(unittest.TestCase):
    def test_malformed_enum_objects_produce_structured_errors(self):
        fields = [
            ("assumptions", "category"), ("assumptions", "status"),
            ("ideas", "evidence_status"), ("ideas", "status"),
            ("provenance", "origin"), ("provenance", "recorded_stage"),
        ]
        for section, field in fields:
            for value in ([], {}):
                with self.subTest(section=section, field=field, value=value):
                    document = populated_register()
                    record = (document["ideas"][0]["provenance"]
                              if section == "provenance" else document[section][0])
                    record[field] = value
                    report = validate_register.validate_register(document)
                    self.assertFalse(report["valid"])
                    self.assertEqual(len(report["errors"]), 1)
                    self.assertTrue(report["errors"][0]["path"].endswith(field))

    def test_valid_register_passes_without_warnings(self):
        report = validate_register.validate_register(populated_register())
        self.assertTrue(report["valid"])
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["warnings"], [])
        self.assertEqual(report["statistics"]["ideas"], 1)

    def test_missing_ai_provenance_and_assumption_are_errors(self):
        document = populated_register()
        idea = document["ideas"][0]
        idea["provenance"]["origin"] = "ai-assisted"
        idea["provenance"]["ai_tool"] = None
        idea["assumption_ids"] = ["A999"]
        report = validate_register.validate_register(document)
        self.assertFalse(report["valid"])
        messages = " ".join(item["message"] for item in report["errors"])
        self.assertIn("must be a string", messages)
        self.assertIn("missing assumption ID", messages)

    def test_duplicate_warning_disclaims_semantic_equivalence(self):
        document = populated_register()
        duplicate = json.loads(json.dumps(document["ideas"][0]))
        duplicate["id"] = "I002"
        duplicate["statement"] = "  TEST a synthetic alternative mechanism. "
        duplicate["provenance"]["contributor_ids"] = ["P02"]
        document["ideas"].append(duplicate)
        report = validate_register.validate_register(document)
        self.assertTrue(report["valid"])
        messages = " ".join(item["message"] for item in report["warnings"])
        self.assertIn("not a claim of semantic equivalence", messages)


class MatrixTests(unittest.TestCase):
    def _write_inputs(self, root: Path) -> tuple[Path, Path]:
        config = root / "criteria.json"
        config.write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "criteria": [
                        {
                            "name": "information_gain",
                            "description": "Synthetic discriminating value",
                            "weight": 3,
                            "direction": "higher",
                            "minimum": 1,
                            "maximum": 5,
                        },
                        {
                            "name": "burden",
                            "description": "Synthetic resource burden",
                            "weight": 2,
                            "direction": "lower",
                            "minimum": 1,
                            "maximum": 5,
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        scores = root / "scores.csv"
        scores.write_text(
            "idea_id,information_gain,information_gain_low,"
            "information_gain_high,burden,burden_low,burden_high,"
            "qualitative_review,uncertainties,evidence_status\n"
            "I001,5,4,5,5,4,5,High information gain,High burden,"
            "search-incomplete\n"
            "I002,1,1,2,1,1,2,Low information gain,Transfer unknown,mixed\n",
            encoding="utf-8",
        )
        return config, scores

    def test_matrix_discloses_formula_context_and_no_decision(self):
        with tempfile.TemporaryDirectory() as directory:
            config, scores = self._write_inputs(Path(directory))
            criteria = evaluate_matrix.load_criteria(str(config))
            rows = evaluate_matrix.load_scores(str(scores), criteria)
            result = evaluate_matrix.calculate_matrix(
                criteria,
                rows,
                weight_delta=0.5,
            )
        by_id = {item["idea_id"]: item for item in result["results"]}
        self.assertAlmostEqual(by_id["I001"]["base_score"], 60.0)
        self.assertAlmostEqual(by_id["I002"]["base_score"], 40.0)
        self.assertEqual(
            by_id["I001"]["qualitative"]["qualitative_review"],
            "High information gain",
        )
        self.assertEqual(result["decision"], None)
        self.assertIn("No idea was selected", result["notice"])
        self.assertIn("formula", result["method"])
        self.assertNotEqual(
            by_id["I001"]["weight_sensitivity_rank_range"][0],
            by_id["I001"]["weight_sensitivity_rank_range"][1],
        )

    def test_matrix_preserves_input_uncertainty_interval(self):
        with tempfile.TemporaryDirectory() as directory:
            config, scores = self._write_inputs(Path(directory))
            criteria = evaluate_matrix.load_criteria(str(config))
            rows = evaluate_matrix.load_scores(str(scores), criteria)
            result = evaluate_matrix.calculate_matrix(
                criteria,
                rows,
                weight_delta=0.1,
            )
        first = {item["idea_id"]: item for item in result["results"]}["I001"]
        low, high = first["input_uncertainty_score_interval"]
        self.assertEqual([low, high], [45.0, 70.0])
        self.assertEqual(first["criteria_without_uncertainty_bounds"], [])
        self.assertTrue(first["criteria"]["burden"]["bounds_supplied"])

    def test_missing_bounds_are_disclosed_without_changing_central_scores(self):
        with tempfile.TemporaryDirectory() as directory:
            config, scores = self._write_inputs(Path(directory))
            criteria = evaluate_matrix.load_criteria(str(config))
            for csv_text in (
                "idea_id,information_gain,burden,qualitative_review,uncertainties\n"
                "I001,5,5,Useful,Unknown\n",
                "idea_id,information_gain,information_gain_low,information_gain_high,"
                "burden,burden_low,burden_high,qualitative_review,uncertainties\n"
                "I001,5,,,5,,,Useful,Unknown\n",
            ):
                with self.subTest(csv=csv_text):
                    scores.write_text(csv_text, encoding="utf-8")
                    rows = evaluate_matrix.load_scores(str(scores), criteria)
                    result = evaluate_matrix.calculate_matrix(criteria, rows, weight_delta=0)
                    first = result["results"][0]
                    self.assertEqual(first["base_score"], 60.0)
                    self.assertEqual(first["input_uncertainty_score_interval"], [60.0, 60.0])
                    self.assertEqual(first["criteria_without_uncertainty_bounds"],
                                     ["information_gain", "burden"])
                    self.assertFalse(first["criteria"]["burden"]["bounds_supplied"])
                    self.assertTrue(result["warnings"])
                    self.assertIsNone(result["decision"])

    def test_reserved_and_generated_column_collisions_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            config, _ = self._write_inputs(Path(directory))
            original = json.loads(config.read_text())
            for name in ("idea_id", "qualitative_review", "uncertainties",
                         "information_gain_low", "information_gain_high"):
                with self.subTest(name=name):
                    document = json.loads(json.dumps(original))
                    document["criteria"][1]["name"] = name
                    config.write_text(json.dumps(document), encoding="utf-8")
                    with self.assertRaisesRegex(CliError, "ambiguous CSV column"):
                        evaluate_matrix.load_criteria(str(config))

    def test_overflowing_scale_and_malformed_direction_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            config, _ = self._write_inputs(Path(directory))
            original = json.loads(config.read_text())
            for updates in ({"minimum": -1e308, "maximum": 1e308},
                            {"minimum": -(10 ** 400)}, {"direction": []}):
                with self.subTest(updates=updates):
                    document = json.loads(json.dumps(original))
                    document["criteria"][0].update(updates)
                    config.write_text(json.dumps(document), encoding="utf-8")
                    with self.assertRaises(CliError):
                        evaluate_matrix.load_criteria(str(config))

    def test_csv_parser_failure_is_reported_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            config, scores = self._write_inputs(Path(directory))
            scores.write_text("x" * (evaluate_matrix.MAX_CSV_FIELD_CHARS + 1))
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "evaluate_matrix.py"), str(scores),
                 "--config", str(config)], capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("error:", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_matrix_rejects_out_of_range_score(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, scores = self._write_inputs(root)
            scores.write_text(
                scores.read_text().replace("I001,5,4,5", "I001,9,4,5"),
                encoding="utf-8",
            )
            criteria = evaluate_matrix.load_criteria(str(config))
            with self.assertRaises(CliError):
                evaluate_matrix.load_scores(str(scores), criteria)


# The shared --help contract: every argparse CLI this skill ships answers --help
# without doing any work. It skips when the skill's packages are absent and runs
# for real under `python tests/run_all.py --isolated`.
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

if __name__ == "__main__":
    unittest.main()
