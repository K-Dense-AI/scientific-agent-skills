"""Synthetic, dependency-free tests for the hypothesis-generation local CLIs."""

from __future__ import annotations

import ast
import csv
from datetime import date
import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "hypothesis-generation"
SCRIPTS = SKILL_ROOT / "scripts"
ASSETS = SKILL_ROOT / "assets"
sys.path.insert(0, str(SCRIPTS))

from _common import (  # noqa: E402
    MAX_INPUT_BYTES,
    MAX_JSON_DEPTH,
    ValidationError,
    read_json,
    require_iso_date,
    write_json_report,
)
from audit_evidence_ledger import (  # noqa: E402
    audit as audit_evidence,
)
from audit_evidence_ledger import load_ledger, load_search_boundary  # noqa: E402
from check_falsification_controls import audit as audit_controls  # noqa: E402
from check_falsification_controls import load_checklist as load_controls  # noqa: E402
from check_operationalization import audit as audit_operationalization  # noqa: E402
from check_operationalization import load_checklist as load_operationalization  # noqa: E402
from generate_preregistration_scaffold import generate as generate_scaffold  # noqa: E402
from lint_causal_claims import lint as lint_claims  # noqa: E402
from validate_hypothesis_schema import (  # noqa: E402
    load_hypothesis_record,
    validate_record,
)
from validate_prediction_matrix import load_matrix, validate_matrix  # noqa: E402

import skill_contract


def load_asset_json(name: str) -> dict:
    return json.loads((ASSETS / name).read_text(encoding="utf-8"))


def valid_record() -> dict:
    return load_hypothesis_record(load_asset_json("hypothesis_record_template.json"))


def assert_no_decision_keys(test: unittest.TestCase, report: dict) -> None:
    forbidden = {"score", "rank", "ranking", "selected_hypothesis", "winner"}
    stack: list[object] = [report]
    observed: set[str] = set()
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            observed.update(str(key).casefold() for key in value)
            stack.extend(value.values())
        elif isinstance(value, list):
            stack.extend(value)
    test.assertTrue(forbidden.isdisjoint(observed), forbidden & observed)


class HypothesisSchemaTests(unittest.TestCase):
    def test_template_is_valid_and_keeps_candidates_distinct(self) -> None:
        record = valid_record()
        report = validate_record(record)
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["status"], "VALID_FOR_HUMAN_REVIEW")
        self.assertEqual(report["counts"]["hypotheses"], 2)
        self.assertEqual(report["counts"]["predictions"], 2)
        self.assertTrue(
            {
                "observation",
                "research_question",
                "hypotheses",
                "causal_estimands",
                "predictions",
                "alternative_explanations",
                "null_hypotheses",
                "negative_controls",
                "operationalizations",
                "analysis_plan",
                "evidence",
            }.issubset(record)
        )
        self.assertTrue(
            all(item["status"] == "candidate" for item in record["hypotheses"])
        )
        assert_no_decision_keys(self, report)

    def test_non_candidate_status_is_rejected(self) -> None:
        raw = load_asset_json("hypothesis_record_template.json")
        raw["hypotheses"][0]["status"] = "proven"
        with self.assertRaises(ValidationError):
            load_hypothesis_record(raw)

    def test_causal_question_requires_estimand(self) -> None:
        raw = load_asset_json("hypothesis_record_template.json")
        raw["causal_estimands"] = []
        report = validate_record(load_hypothesis_record(raw))
        self.assertFalse(report["valid"])
        self.assertIn(
            "CAUSAL_QUESTION_REQUIRES_ESTIMAND",
            {item["code"] for item in report["errors"]},
        )

    def test_external_sensitive_data_declaration_blocks_record(self) -> None:
        raw = load_asset_json("hypothesis_record_template.json")
        raw["ai_use"]["sensitive_or_unpublished_data_sent_externally"] = True
        report = validate_record(load_hypothesis_record(raw))
        self.assertFalse(report["valid"])
        self.assertIn(
            "EXTERNAL_SENSITIVE_DATA_NOT_SUPPORTED",
            {item["code"] for item in report["errors"]},
        )


class OperationalizationTests(unittest.TestCase):
    def test_template_is_valid_with_visible_measurement_gaps(self) -> None:
        checklist = load_operationalization(
            load_asset_json("operationalization_template.json")
        )
        report = audit_operationalization(checklist)
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["status"], "VALID_WITH_MEASUREMENT_GAPS")
        self.assertIn("M-OUTCOME", report["gap_fields_by_measurement_id"])
        assert_no_decision_keys(self, report)

    def test_applicable_measurement_requires_validity_source(self) -> None:
        raw = load_asset_json("operationalization_template.json")
        raw["items"][0]["validity_evidence_source_ids"] = []
        report = audit_operationalization(load_operationalization(raw))
        self.assertFalse(report["valid"])
        self.assertIn(
            "VALIDITY_SOURCE_REQUIRED", {item["code"] for item in report["errors"]}
        )


class PredictionMatrixTests(unittest.TestCase):
    def test_template_cross_checks_against_record(self) -> None:
        rows = load_matrix(str(ASSETS / "prediction_rival_matrix_template.csv"))
        report = validate_matrix(rows, valid_record())
        self.assertTrue(report["valid"], report["errors"])
        self.assertTrue(report["record_cross_check_performed"])
        self.assertEqual(set(report["prediction_ids"]), {"P1", "P2"})
        assert_no_decision_keys(self, report)

    def test_identical_focal_and_rival_expectations_are_rejected(self) -> None:
        rows = load_matrix(str(ASSETS / "prediction_rival_matrix_template.csv"))
        rows[0]["expected_if_rivals"] = rows[0]["expected_if_focal"]
        report = validate_matrix(rows)
        self.assertFalse(report["valid"])
        self.assertIn(
            "FOCAL_AND_RIVAL_EXPECTATIONS_IDENTICAL",
            {item["code"] for item in report["errors"]},
        )

    def test_csv_requires_exact_header(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "matrix.csv"
            path.write_text("prediction_id,hypothesis_id\nP1,H1\n", encoding="utf-8")
            with self.assertRaises(ValidationError):
                load_matrix(str(path))


class CausalClaimLintTests(unittest.TestCase):
    def test_unmarked_causal_language_is_invalid(self) -> None:
        report = lint_claims("Condition X causes outcome Y.\n")
        self.assertFalse(report["valid"])
        self.assertEqual(report["errors"][0]["code"], "UNMARKED_CAUSAL_LANGUAGE")
        self.assertNotIn("Condition X", json.dumps(report))

    def test_fully_annotated_causal_claim_is_structurally_valid(self) -> None:
        line = (
            "[claim:causal][estimand:E1][identification:"
            "observational_assumption_dependent][confounding:unresolved]"
            "[selection:assessed][collider:assessed]"
            "[reverse-causation:assessed] Under the stated assumptions, "
            "condition X reduces outcome Y."
        )
        report = lint_claims(line)
        self.assertTrue(report["valid"], report["errors"])
        self.assertIn(
            "UNRESOLVED_CONFOUNDING_RISK",
            {item["code"] for item in report["warnings"]},
        )
        assert_no_decision_keys(self, report)

    def test_associational_tag_cannot_hide_causal_verb(self) -> None:
        report = lint_claims(
            "[claim:associational] Condition X causes outcome Y.\n"
        )
        self.assertFalse(report["valid"])
        self.assertIn(
            "CAUSAL_LANGUAGE_IN_NONCAUSAL_CLAIM",
            {item["code"] for item in report["errors"]},
        )


class FalsificationControlTests(unittest.TestCase):
    def test_template_is_valid_pending_human_review(self) -> None:
        checklist = load_controls(
            load_asset_json("falsification_controls_template.json")
        )
        report = audit_controls(checklist, valid_record())
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["status"], "VALID_PENDING_HUMAN_REVIEW")
        self.assertEqual(set(report["hypothesis_ids"]), {"H1", "H2"})
        assert_no_decision_keys(self, report)

    def test_identical_discriminating_expectations_are_invalid(self) -> None:
        raw = load_asset_json("falsification_controls_template.json")
        test = raw["hypotheses"][0]["discriminating_tests"][0]
        test["rival_expected"] = test["focal_expected"]
        report = audit_controls(load_controls(raw))
        self.assertFalse(report["valid"])
        self.assertIn(
            "FOCAL_AND_RIVAL_EXPECTATIONS_IDENTICAL",
            {item["code"] for item in report["errors"]},
        )


class EvidenceLedgerTests(unittest.TestCase):
    def test_synthetic_ledger_and_boundary_cross_check(self) -> None:
        ledger = load_ledger(str(ASSETS / "evidence_ledger_template.csv"))
        boundary = load_search_boundary(
            load_asset_json("search_boundary_template.json")
        )
        report = audit_evidence(ledger, boundary, valid_record())
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["novelty_status"], "not_assessed")
        self.assertTrue(report["record_cross_check_performed"])
        self.assertIn(
            "NO_CHALLENGING_SOURCE_DECLARED",
            {item["code"] for item in report["warnings"]},
        )
        assert_no_decision_keys(self, report)

    def test_comprehensive_search_label_still_requires_human_review(self) -> None:
        boundary_raw = load_asset_json("search_boundary_template.json")
        boundary_raw["novelty_status"] = (
            "supported_by_documented_comprehensive_search"
        )
        report = audit_evidence(
            load_ledger(str(ASSETS / "evidence_ledger_template.csv")),
            load_search_boundary(boundary_raw),
        )
        self.assertIn(
            "NOVELTY_STATUS_REQUIRES_QUALIFIED_HUMAN_REVIEW",
            {item["code"] for item in report["warnings"]},
        )


class ScaffoldTests(unittest.TestCase):
    def test_scaffold_contains_all_candidates_without_selection(self) -> None:
        rendered = generate_scaffold(valid_record())
        self.assertIn("UNREGISTERED DRAFT", rendered)
        self.assertIn("### H1", rendered)
        self.assertIn("### H2", rendered)
        self.assertIn("does not rank or select", rendered)
        self.assertNotIn("selected hypothesis", rendered.casefold())

    def test_record_date_is_not_presented_as_generation_timestamp(self) -> None:
        record = valid_record()
        record["updated_on"] = "2024-02-29"
        rendered = generate_scaffold(record)
        self.assertIn("record last updated 2024-02-29", rendered)
        self.assertNotIn("Generated locally on 2024-02-29", rendered)

    def test_unresolved_gate_blocks_scaffold(self) -> None:
        raw = load_asset_json("hypothesis_record_template.json")
        ethics = raw["ethics_and_feasibility"]
        ethics["human_subjects_gate"] = "requires_review"
        ethics["required_reviews"] = ["Authorized human-subjects determination"]
        ethics["unresolved_blocks"] = ["Do not begin before determination"]
        record = load_hypothesis_record(raw)
        self.assertTrue(validate_record(record)["valid"])
        with self.assertRaisesRegex(ValidationError, "unresolved safety"):
            generate_scaffold(record)


class FileSafetyAndStaticTests(unittest.TestCase):
    def test_dates_require_calendar_form_and_valid_day(self) -> None:
        self.assertEqual(require_iso_date("2024-02-29", "date"), "2024-02-29")
        for value in ("20261001", "2026-W40-4", "2026-02-29", "2026-13-01"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                require_iso_date(value, "date")

    def test_nonstandard_json_numbers_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "constant.json"
            for constant in ("NaN", "Infinity", "-Infinity"):
                path.write_text('{"value":' + constant + '}', encoding="utf-8")
                with self.subTest(constant=constant), self.assertRaisesRegex(
                    ValidationError, "nonstandard numeric constant"
                ):
                    read_json(path)

    def test_excessive_json_nesting_is_a_validation_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested.json"
            depth = MAX_JSON_DEPTH + 1
            path.write_text("[" * depth + "0" + "]" * depth, encoding="utf-8")
            with self.assertRaisesRegex(ValidationError, "nesting"):
                read_json(path)

    def test_duplicate_json_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"a": 1, "a": 2}', encoding="utf-8")
            with self.assertRaisesRegex(ValidationError, "duplicate key"):
                read_json(path)

    def test_oversized_json_is_rejected_before_parsing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "oversized.json"
            path.write_bytes(b" " * (MAX_INPUT_BYTES + 1))
            with self.assertRaises(ValidationError):
                read_json(path)

    def test_symlink_input_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "input.json"
            target.write_text("{}", encoding="utf-8")
            link = root / "link.json"
            try:
                link.symlink_to(target)
            except OSError:
                self.skipTest("symlinks unavailable")
            with self.assertRaises(ValidationError):
                read_json(link)

    def test_private_output_refuses_implicit_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            write_json_report({"valid": True}, output)
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            with self.assertRaises(ValidationError):
                write_json_report({"valid": False}, output)
            write_json_report({"valid": False}, output, force=True)
            self.assertEqual(json.loads(output.read_text()), {"valid": False})

    def test_scripts_have_no_network_dynamic_execution_or_secret_access(self) -> None:
        banned_import_roots = {
            "aiohttp",
            "dill",
            "httpx",
            "marshal",
            "pickle",
            "requests",
            "shelve",
            "socket",
            "subprocess",
            "urllib",
            "webbrowser",
        }
        banned_calls = {"eval", "exec", "compile", "__import__"}
        for path in sorted(SCRIPTS.glob("*.py")):
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    roots = {alias.name.split(".")[0] for alias in node.names}
                    self.assertTrue(
                        roots.isdisjoint(banned_import_roots),
                        f"{path.name}: banned import {roots & banned_import_roots}",
                    )
                elif isinstance(node, ast.ImportFrom) and node.module:
                    root = node.module.split(".")[0]
                    self.assertNotIn(root, banned_import_roots, path.name)
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, banned_calls, path.name)
                elif isinstance(node, ast.Attribute):
                    self.assertFalse(
                        isinstance(node.value, ast.Name)
                        and node.value.id == "os"
                        and node.attr in {"environ", "getenv"},
                        f"{path.name}: environment access",
                    )
            lowered = source.casefold()
            self.assertNotIn("openrouter", lowered, path.name)
            self.assertNotIn(".env", lowered, path.name)
            self.assertNotIn("api_key", lowered, path.name)

    def test_assets_parse_and_source_ledger_is_dated(self) -> None:
        for path in ASSETS.glob("*.json"):
            json.loads(path.read_text(encoding="utf-8"))
        with (ASSETS / "source_ledger.csv").open(
            "r", encoding="utf-8", newline=""
        ) as handle:
            rows = list(csv.DictReader(handle))
        self.assertGreaterEqual(len(rows), 30)
        for row in rows:
            self.assertEqual(date.fromisoformat(row["verified_on"]).isoformat(), row["verified_on"])
        self.assertTrue(all(row["url"].startswith("https://") for row in rows))
        self.assertEqual(
            len(rows), len({row["source_id"] for row in rows})
        )

    def test_skill_frontmatter_and_progressive_disclosure(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertLess(len(skill.splitlines()), 500)
        self.assertRegex(skill, r'\n  version: "\d+\.\d+"\n')
        self.assertIn("license: MIT", skill)
        self.assertIn("compatibility:", skill)
        self.assertNotIn("OPENROUTER", skill)
        self.assertNotIn("Nano Banana", skill)
        self.assertNotIn("MANDATORY: Every", skill)
        self.assertNotIn("scientific-schematics", skill)

    def test_removed_external_schematic_and_latex_assets_stay_absent(self) -> None:
        self.assertFalse((SCRIPTS / "generate_schematic.py").exists())
        self.assertFalse((SCRIPTS / "generate_schematic_ai.py").exists())
        self.assertFalse((ASSETS / "hypothesis_report_template.tex").exists())
        self.assertFalse((ASSETS / "hypothesis_generation.sty").exists())
        self.assertFalse((ASSETS / "FORMATTING_GUIDE.md").exists())
        self.assertFalse(list(SKILL_ROOT.rglob("*.pyc")))


# The shared --help contract: every argparse CLI this skill ships answers --help
# without doing any work. It skips when the skill's packages are absent and runs
# for real under `python tests/run_all.py --isolated`.
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

if __name__ == "__main__":
    unittest.main()
