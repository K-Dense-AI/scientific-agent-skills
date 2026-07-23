"""Synthetic tests for the standard-library scientific brainstorming CLIs."""

from __future__ import annotations

import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import evaluate_matrix
import session_scaffold
import validate_register
from _common import MAX_INPUT_BYTES, CliError, read_json, write_json


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
        self.assertLess(low, first["base_score"])
        self.assertLessEqual(first["base_score"], high)

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


if __name__ == "__main__":
    unittest.main()
