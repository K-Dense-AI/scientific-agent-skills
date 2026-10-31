"""Synthetic dependency-free tests for scholar-evaluation local tooling."""

from __future__ import annotations

import ast
import copy
from collections import Counter
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "scholar-evaluation"
SCRIPTS = SKILL_ROOT / "scripts"
ASSETS = SKILL_ROOT / "assets"
sys.path.insert(0, str(SCRIPTS))

import _common  # noqa: E402
import calculate_scores  # noqa: E402
import check_process  # noqa: E402
import check_traceability  # noqa: E402
import generate_report_scaffold  # noqa: E402
import summarize_agreement  # noqa: E402
import validate_rubric  # noqa: E402
import weight_sensitivity  # noqa: E402


def load_json_asset(name: str) -> dict:
    return json.loads((ASSETS / name).read_text(encoding="utf-8"))


def rated_evaluation(
    work_id: str = "WORK-SYNTHETIC-001",
    evaluation_id: str = "EVALUATION-SYNTHETIC-001",
    scores: list[float] | None = None,
) -> dict:
    evaluation = load_json_asset("evaluation_template.json")
    evaluation["work_id"] = work_id
    evaluation["evaluation_id"] = evaluation_id
    supplied_scores = scores or [3, 3, 3, 3, 3]
    evidence_ids = [
        "EVIDENCE-SYNTHETIC-QUESTION",
        "EVIDENCE-SYNTHETIC-LITERATURE",
        "EVIDENCE-SYNTHETIC-METHOD",
        "EVIDENCE-SYNTHETIC-ANALYSIS",
        "EVIDENCE-SYNTHETIC-TRANSPARENCY",
    ]
    for rating, score, evidence_id in zip(
        evaluation["ratings"], supplied_scores, evidence_ids, strict=True
    ):
        rating.update(
            {
                "status": "rated",
                "score": score,
                "uncertainty": 0.5,
                "evidence_ids": [evidence_id],
                "rationale_ref": f"LOCAL-RATIONALE-{rating['criterion_id']}",
            }
        )
    return evaluation


def completed_process() -> dict:
    record = load_json_asset("process_checklist_template.json")
    for section_name, field_groups in check_process.SECTION_FIELDS.items():
        for field in field_groups["booleans"]:
            record[section_name][field] = True
        for field in field_groups["references"]:
            record[section_name][field] = f"LOCAL-{section_name}-{field}"
    return record


class StaticSafetyTests(unittest.TestCase):
    def test_scripts_have_no_network_dynamic_process_or_executable_serialization(self) -> None:
        banned_import_roots = {
            "aiohttp",
            "httpx",
            "openai",
            "pickle",
            "requests",
            "socket",
            "".join(("sub", "process")),
            "urllib",
        }
        banned_calls = {
            "".join(("e", "val")),
            "".join(("e", "xec")),
            "".join(("com", "pile")),
        }
        for path in sorted(SCRIPTS.glob("*.py")):
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    roots = {alias.name.split(".")[0] for alias in node.names}
                    self.assertFalse(roots & banned_import_roots, path.name)
                if isinstance(node, ast.ImportFrom) and node.module:
                    self.assertNotIn(
                        node.module.split(".")[0],
                        banned_import_roots,
                        path.name,
                    )
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, banned_calls, path.name)
            self.assertNotIn("os.environ", source)
            self.assertNotIn("getenv(", source)
            self.assertNotIn("API_KEY", source)
            self.assertNotIn(".env", source)

    def test_external_schematic_scripts_are_absent(self) -> None:
        self.assertFalse((SCRIPTS / "generate_schematic.py").exists())
        self.assertFalse((SCRIPTS / "generate_schematic_ai.py").exists())

    def test_skill_is_versioned_and_under_500_lines(self) -> None:
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertLess(len(text.splitlines()), 500)
        self.assertRegex(text, r'\nmetadata:\n  version: "\d+\.\d+"\n')
        self.assertIn("license: MIT", text)
        self.assertIn("compatibility:", text)
        self.assertNotIn("OPENROUTER", text)

    def test_expected_assets_only(self) -> None:
        expected = {
            "evaluation_template.json",
            "evidence_manifest_template.json",
            "process_checklist_template.json",
            "ratings_template.csv",
            "rubric_template.json",
        }
        actual = {path.name for path in ASSETS.iterdir() if path.is_file()}
        self.assertEqual(actual, expected)

    def test_all_script_help_is_dependency_free(self) -> None:
        modules = (
            calculate_scores,
            check_process,
            check_traceability,
            generate_report_scaffold,
            summarize_agreement,
            validate_rubric,
            weight_sensitivity,
        )
        for module in modules:
            help_text = module.build_parser().format_help()
            self.assertIn("usage:", help_text.lower(), module.__name__)


class RubricAndInputTests(unittest.TestCase):
    def test_malformed_enum_fields_return_validation_failures(self) -> None:
        rubric = load_json_asset("rubric_template.json")
        rubric["provenance"]["content_validity_status"] = []
        rubric["rater_protocol"]["inter_rater_reliability_status"] = {}
        self.assertTrue(_common.error_issues(_common.validate_rubric(rubric)))
        rubric = load_json_asset("rubric_template.json")
        evaluation = rated_evaluation()
        evaluation["data_classification"] = []
        evaluation["ratings"][0]["status"] = {}
        self.assertTrue(_common.error_issues(_common.validate_evaluation(evaluation, rubric)))
        manifest = load_json_asset("evidence_manifest_template.json")
        manifest["evidence"][0].update(criterion_ids=None, source_type=[], access_status=[], verification_status={})
        self.assertEqual(check_traceability.check_traceability(rubric, rated_evaluation(), manifest)["status"], "fail")
        self.assertEqual(check_process.check_process([])["status"], "invalid")

    def test_anchor_steps_and_duplicates_are_rejected(self) -> None:
        rubric = load_json_asset("rubric_template.json")
        rubric["scale"]["step"] = 2
        self.assertIn("ANCHOR_STEP_MISMATCH", {issue.code for issue in _common.validate_rubric(rubric)})
        rubric = load_json_asset("rubric_template.json")
        rubric["criteria"][0]["anchors"].append(copy.deepcopy(rubric["criteria"][0]["anchors"][0]))
        self.assertIn("ANCHOR_SCORE_DUPLICATE", {issue.code for issue in _common.validate_rubric(rubric)})

    def test_nonfinite_numeric_values_fail_direct_validation(self) -> None:
        for value in (float("nan"), float("inf"), 10**1000):
            rubric = load_json_asset("rubric_template.json")
            rubric["scale"]["maximum"] = value
            self.assertTrue(_common.error_issues(_common.validate_rubric(rubric)))

    def test_template_rubric_is_structurally_valid_with_warning(self) -> None:
        rubric = load_json_asset("rubric_template.json")
        issues = _common.validate_rubric(rubric)
        self.assertEqual(_common.error_issues(issues), [])
        self.assertIn(
            "CONTENT_VALIDITY_NOT_DOCUMENTED",
            {issue.code for issue in issues},
        )
        self.assertIn(
            "INTER_RATER_RELIABILITY_NOT_DOCUMENTED",
            {issue.code for issue in issues},
        )

    def test_validator_rejects_unknown_field(self) -> None:
        rubric = load_json_asset("rubric_template.json")
        rubric["unexpected"] = True
        issues = _common.validate_rubric(rubric)
        self.assertIn("SCHEMA_UNKNOWN_FIELD", {issue.code for issue in issues})

    def test_validator_fails_closed_on_malformed_scale(self) -> None:
        rubric = load_json_asset("rubric_template.json")
        rubric["scale"] = None
        issues = _common.validate_rubric(rubric)
        self.assertIn("SCHEMA_OBJECT_REQUIRED", {issue.code for issue in issues})

    def test_validator_rejects_proxy_criterion(self) -> None:
        rubric = load_json_asset("rubric_template.json")
        rubric["criteria"][0]["label"] = "Journal impact factor"
        issues = _common.validate_rubric(rubric)
        self.assertIn(
            "PROXY_METRIC_CRITERION_PROHIBITED",
            {issue.code for issue in issues},
        )

    def test_duplicate_json_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"work_id":"A","work_id":"B"}', encoding="utf-8")
            with self.assertRaisesRegex(_common.ValidationError, "JSON_DUPLICATE_KEY"):
                _common.read_json(path)

    def test_private_application_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "private.json"
            path.write_text(
                '{"schema_version":"2.0","application_text":"private"}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                _common.ValidationError, "PRIVATE_FIELD_NOT_ALLOWED"
            ):
                _common.read_json(path)

    def test_excessive_depth_is_rejected(self) -> None:
        value: dict = {}
        cursor = value
        for _ in range(_common.MAX_DEPTH + 2):
            cursor["nested"] = {}
            cursor = cursor["nested"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "deep.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(
                _common.ValidationError, "STRUCTURE_TOO_DEEP"
            ):
                _common.read_json(path)

    def test_unrated_template_is_valid(self) -> None:
        rubric = load_json_asset("rubric_template.json")
        evaluation = load_json_asset("evaluation_template.json")
        self.assertEqual(
            _common.error_issues(_common.validate_evaluation(evaluation, rubric)),
            [],
        )


class ScoringAndTraceabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rubric = load_json_asset("rubric_template.json")

    def test_weighted_math_is_bounded_and_has_no_recommendation(self) -> None:
        evaluation = rated_evaluation(scores=[4, 3, 2, 1, 0])
        report = calculate_scores.calculate(self.rubric, evaluation)
        expected = 4 * 0.15 + 3 * 0.2 + 2 * 0.25 + 1 * 0.2
        self.assertAlmostEqual(
            report["aggregates"]["normalized_score"], expected, places=6
        )
        self.assertEqual(report["aggregates"]["coverage_of_applicable_weight"], 1)
        self.assertFalse(report["decision_recommendation_provided"])
        self.assertNotIn("quality_level", report)

    def test_missing_and_not_applicable_are_reported_not_zeroed(self) -> None:
        evaluation = rated_evaluation(scores=[4, 3, 2, 1, 0])
        evaluation["ratings"][3].update(
            {
                "status": "missing",
                "score": None,
                "uncertainty": None,
                "evidence_ids": [],
            }
        )
        evaluation["ratings"][4].update(
            {
                "status": "not_applicable",
                "score": None,
                "uncertainty": None,
                "evidence_ids": [],
            }
        )
        report = calculate_scores.calculate(self.rubric, evaluation)
        aggregates = report["aggregates"]
        self.assertAlmostEqual(aggregates["missing_weight"], 0.2)
        self.assertAlmostEqual(aggregates["not_applicable_weight"], 0.2)
        self.assertLess(aggregates["coverage_of_applicable_weight"], 1)
        self.assertIn(
            "MISSING_RATINGS_EXCLUDED_FROM_NORMALIZED_SCORE", report["warnings"]
        )

    def test_uncertainty_is_clamped_to_scale(self) -> None:
        evaluation = rated_evaluation(scores=[4, 3, 2, 1, 0])
        report = calculate_scores.calculate(self.rubric, evaluation)
        interval = report["aggregates"]["uncertainty_interval"]
        self.assertGreaterEqual(interval["lower"], 0)
        self.assertLessEqual(interval["upper"], 4)
        self.assertIn("not a confidence interval", interval["method"])

    def test_traceability_passes_and_never_copies_content(self) -> None:
        evaluation = rated_evaluation()
        manifest = load_json_asset("evidence_manifest_template.json")
        report = check_traceability.check_traceability(
            self.rubric, evaluation, manifest
        )
        self.assertEqual(report["status"], "pass", report["issues"])
        self.assertFalse(report["source_content_copied_to_output"])
        rendered = json.dumps(report)
        self.assertNotIn("LOCAL-WORK-SECTION", rendered)

    def test_unresolved_evidence_fails(self) -> None:
        evaluation = rated_evaluation()
        evaluation["ratings"][0]["evidence_ids"] = ["EVIDENCE-NOT-FOUND"]
        report = check_traceability.check_traceability(
            self.rubric,
            evaluation,
            load_json_asset("evidence_manifest_template.json"),
        )
        self.assertEqual(report["status"], "fail")
        self.assertIn(
            "EVIDENCE_REFERENCE_UNRESOLVED",
            {issue["code"] for issue in report["issues"]},
        )


class SensitivityAgreementAndProcessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rubric = load_json_asset("rubric_template.json")

    def test_agreement_tolerance_does_not_collapse_distinct_small_anchors(self) -> None:
        report = summarize_agreement._summary(Counter({1e-10: 1, 2e-10: 1}), 1e-10)
        self.assertEqual(report["exact_agreement_rate"], 0)
        self.assertEqual(report["within_one_scale_step_rate"], 0.5)

    def test_weight_sensitivity_detects_order_instability(self) -> None:
        first = rated_evaluation(
            "WORK-SYNTHETIC-A",
            "EVALUATION-SYNTHETIC-A",
            [4, 4, 1, 2, 2],
        )
        second = rated_evaluation(
            "WORK-SYNTHETIC-B",
            "EVALUATION-SYNTHETIC-B",
            [1, 1, 4, 3, 3],
        )
        report = weight_sensitivity.analyze(self.rubric, [first, second], 0.5)
        self.assertTrue(report["rank_instability_detected"])
        self.assertGreater(report["changed_pair_count"], 0)
        self.assertFalse(report["decision_recommendation_provided"])
        self.assertEqual(report["unit_of_assessment"], "scholarly_work")

    def test_agreement_summary_is_pseudonymous_and_descriptive(self) -> None:
        rows = summarize_agreement.read_rows(
            ASSETS / "ratings_template.csv", self.rubric
        )
        report = summarize_agreement.summarize(self.rubric, rows)
        self.assertGreater(report["overall"]["pair_observations"], 0)
        self.assertFalse(report["rater_identifiers_in_output"])
        rendered = json.dumps(report)
        self.assertNotIn("RATER-SYNTHETIC", rendered)
        self.assertIn("not a psychometric validation", report["limitations"][1])

    def test_agreement_keeps_rounds_separate_and_is_order_invariant(self) -> None:
        rows = [
            {"evaluation_id": evaluation_id, "work_id": "WORK-A", "rater_id": rater_id,
             "criterion_id": "question_scope", "status": "rated", "score": score}
            for evaluation_id, rater_id, score in (
                ("ROUND-A", "RATER-A", 0), ("ROUND-A", "RATER-B", 4),
                ("ROUND-B", "RATER-A", 3), ("ROUND-B", "RATER-B", 3),
            )
        ]
        report = summarize_agreement.summarize(self.rubric, rows)
        self.assertEqual(report, summarize_agreement.summarize(self.rubric, rows[::-1]))
        self.assertEqual(report["overall"]["pair_observations"], 2)
        self.assertEqual(report["overall"]["exact_agreement_rate"], 0.5)
        self.assertEqual(report["overall"]["mean_absolute_difference"], 2)
        self.assertEqual(report["criteria"][0]["evaluations_with_rater_overlap"], 2)
        self.assertEqual(report["criteria"][0]["works_with_rater_overlap"], 1)

    def test_agreement_cannot_create_pairs_across_rounds(self) -> None:
        rows = [
            {"evaluation_id": "ROUND-" + suffix, "work_id": "WORK-A", "rater_id": "RATER-" + suffix,
             "criterion_id": "question_scope", "status": "rated", "score": 3}
            for suffix in ("A", "B")
        ]
        report = summarize_agreement.summarize(self.rubric, rows)
        self.assertEqual(report["overall"]["pair_observations"], 0)
        self.assertIn("MINIMUM_RATERS_NOT_MET_FOR_SOME_CRITERIA_EVALUATIONS", report["warnings"])

    def test_agreement_histogram_handles_maximum_rows(self) -> None:
        rows = [
            {"evaluation_id": "ROUND-A", "work_id": "WORK-A", "rater_id": f"RATER-{index}",
             "criterion_id": "question_scope", "status": "rated", "score": index % 2}
            for index in range(_common.MAX_CSV_ROWS)
        ]
        overall = summarize_agreement.summarize(self.rubric, rows)["overall"]
        self.assertEqual(overall["pair_observations"], 199_990_000)
        self.assertEqual(overall["within_one_scale_step_rate"], 1)
        self.assertAlmostEqual(overall["mean_absolute_difference"], 100_000_000 / 199_990_000, places=6)

    def test_agreement_rejects_evaluation_reused_for_another_work(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ratings.csv"
            path.write_text(
                ",".join(summarize_agreement.CSV_FIELDS) + "\n"
                "ROUND-A,WORK-A,RATER-A,question_scope,rated,3\n"
                "ROUND-A,WORK-B,RATER-B,question_scope,rated,3\n"
            )
            with self.assertRaisesRegex(_common.ValidationError, "EVALUATION_WORK_MISMATCH"):
                summarize_agreement.read_rows(path, self.rubric)

    def test_sensitivity_does_not_round_before_order_comparison(self) -> None:
        weights = [0.2 + 1e-8, 0.2 - 1e-8, 0.2, 0.2, 0.2]
        for criterion, weight in zip(self.rubric["criteria"], weights, strict=True):
            criterion["weight"] = weight
        first = rated_evaluation("WORK-A", "EVAL-A", [4, 0, 2, 2, 2])
        second = rated_evaluation("WORK-B", "EVAL-B", [0, 4, 2, 2, 2])
        report = weight_sensitivity.analyze(self.rubric, [first, second], 1e-8)
        self.assertFalse(report["rank_instability_detected"])
        self.assertEqual(report["base_tied_work_pairs"], [])
        self.assertEqual(report["scenarios"][0]["item_scores"][0]["normalized_score"], 2)

    def test_sensitivity_warns_for_different_applicable_sets(self) -> None:
        first = rated_evaluation("WORK-A", "EVAL-A")
        second = rated_evaluation("WORK-B", "EVAL-B")
        second["ratings"][0].update(status="not_applicable", score=None, uncertainty=None, evidence_ids=[])
        report = weight_sensitivity.analyze(self.rubric, [first, second], 0.2)
        self.assertIn("DIFFERENT_CRITERION_STATUS_PATTERNS_LIMIT_COMPARABILITY", report["warnings"])

    def test_scaffold_requires_actual_companion_evaluation_membership(self) -> None:
        first = rated_evaluation("WORK-A", "EVAL-A")
        second = rated_evaluation("WORK-B", "EVAL-B")
        sensitivity = weight_sensitivity.analyze(self.rubric, [first, second], 0.2)
        report = generate_report_scaffold.generate_scaffold(self.rubric, first, sensitivity=sensitivity)
        self.assertEqual(report["quality_assurance"]["weight_sensitivity_status"], "provided")
        stale = copy.deepcopy(first)
        stale["evaluation_id"] = "EVAL-LATER"
        with self.assertRaisesRegex(_common.ValidationError, "COMPANION_EVALUATION_NOT_INCLUDED"):
            generate_report_scaffold.generate_scaffold(self.rubric, stale, sensitivity=sensitivity)
        agreement = summarize_agreement.summarize(
            self.rubric, summarize_agreement.read_rows(ASSETS / "ratings_template.csv", self.rubric)
        )
        with self.assertRaisesRegex(_common.ValidationError, "COMPANION_EVALUATION_NOT_INCLUDED"):
            generate_report_scaffold.generate_scaffold(self.rubric, first, agreement=agreement)

    def test_agreement_rejects_extra_csv_column(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ratings.csv"
            path.write_text(
                "evaluation_id,work_id,rater_id,criterion_id,status,score\n"
                "EVALUATION-1,WORK-1,RATER-1,question_scope,rated,3,extra\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                _common.ValidationError, "CSV_ROW_SHAPE_INVALID"
            ):
                summarize_agreement.read_rows(path, self.rubric)

    def test_unconfirmed_process_is_blocked(self) -> None:
        report = check_process.check_process(
            load_json_asset("process_checklist_template.json")
        )
        self.assertEqual(report["status"], "blocked")
        self.assertTrue(report["blockers"])

    def test_completed_low_stakes_process_passes(self) -> None:
        report = check_process.check_process(completed_process())
        self.assertEqual(report["status"], "complete_for_low_stakes_process")
        self.assertEqual(report["blockers"], [])
        self.assertEqual(report["missing_controls"], [])

    def test_high_impact_process_is_blocked(self) -> None:
        record = completed_process()
        record["high_impact_use"] = True
        report = check_process.check_process(record)
        self.assertEqual(report["status"], "blocked")
        self.assertIn("PROHIBITED_HIGH_IMPACT_USE", report["blockers"])

    def test_report_scaffold_contains_only_safe_placeholders(self) -> None:
        self.rubric["construct"]["definition"] = "SYNTHETIC-SENSITIVE-RUBRIC-TEXT"
        self.rubric["criteria"][0]["label"] = "SYNTHETIC-SENSITIVE-LABEL"
        report = generate_report_scaffold.generate_scaffold(
            self.rubric, rated_evaluation()
        )
        self.assertFalse(report["private_source_content_included"])
        self.assertFalse(report["person_ranking_provided"])
        self.assertFalse(report["decision_recommendation_provided"])
        self.assertEqual(
            report["quality_assurance"]["inter_rater_reliability_status"],
            "not_established",
        )
        rendered = json.dumps(report)
        self.assertNotIn("SYNTHETIC-SENSITIVE", rendered)
        for criterion in report["criterion_scaffold"]:
            self.assertEqual(criterion["evidence_finding_refs"], [])
            self.assertEqual(criterion["qualified_reviewer_comment_ref"], "")


class FileOutputTests(unittest.TestCase):
    def test_output_refuses_overwrite_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            _common.write_json({"status": "first"}, output)
            with self.assertRaisesRegex(_common.ValidationError, "OUTPUT_EXISTS"):
                _common.write_json({"status": "second"}, output)
            _common.write_json({"status": "second"}, output, force=True)
            self.assertEqual(
                json.loads(output.read_text(encoding="utf-8"))["status"],
                "second",
            )

    def test_validate_file_returns_minimized_report(self) -> None:
        report = validate_rubric.validate_file(ASSETS / "rubric_template.json")
        self.assertEqual(report["status"], "valid")
        self.assertEqual(report["error_count"], 0)


if __name__ == "__main__":
    unittest.main()
