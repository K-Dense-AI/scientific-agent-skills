"""Synthetic, dependency-free tests for the peer-review local CLIs."""

from __future__ import annotations

import ast
import csv
import json
import stat
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "peer-review"
SCRIPTS = SKILL_ROOT / "scripts"
ASSETS = SKILL_ROOT / "assets"
sys.path.insert(0, str(SCRIPTS))

from _common import (  # noqa: E402
    MAX_INPUT_BYTES,
    ValidationError,
    read_json,
    write_json_report,
)
from audit_citations import audit as audit_citations  # noqa: E402
from audit_citations import load_references  # noqa: E402
from audit_statistics_reproducibility import (  # noqa: E402
    audit as audit_statistics,
)
from audit_statistics_reproducibility import load_checklist  # noqa: E402
from generate_review_scaffold import generate as generate_scaffold  # noqa: E402
from lint_review import lint as lint_review  # noqa: E402
from select_reporting_guidelines import (  # noqa: E402
    assess as assess_reporting,
)
from select_reporting_guidelines import (  # noqa: E402
    load_catalog,
    load_coverage,
    load_profile,
)
from validate_claim_evidence import load_matrix  # noqa: E402
from validate_claim_evidence import validate_matrix  # noqa: E402
from validate_review_intake import validate_intake  # noqa: E402

import skill_contract


def load_asset_json(name: str) -> dict:
    return json.loads((ASSETS / name).read_text(encoding="utf-8"))


def ready_intake() -> dict:
    intake = load_asset_json("review_intake_template.json")
    intake["authorization"]["documented"] = True
    intake["authorization"]["local_processing_authorized"] = True
    intake["reviewer"]["human_accountable"] = True
    intake["reviewer"]["conflict_status"] = "none_identified"
    intake["venue_policy"]["checked"] = True
    intake["venue_policy"]["peer_review_model"] = "double_anonymized"
    intake["venue_policy"]["confidential_editor_notes_supported"] = True
    intake["ai_use"]["policy"] = "prohibited"
    intake["handling"]["deletion_or_retention_record_planned"] = True
    return intake


class IntakeTests(unittest.TestCase):
    def test_template_is_safely_blocked(self) -> None:
        report = validate_intake(load_asset_json("review_intake_template.json"))
        self.assertFalse(report["valid"])
        self.assertEqual(report["status"], "BLOCKED")
        codes = {item["code"] for item in report["errors"]}
        self.assertIn("AUTHORIZATION_NOT_DOCUMENTED", codes)
        self.assertIn("CONFLICTS_NOT_ASSESSED", codes)

    def test_completed_local_intake_is_ready(self) -> None:
        report = validate_intake(ready_intake())
        self.assertTrue(report["valid"], report["errors"])
        self.assertFalse(
            report["handling_assertions"]["external_service_use_authorized_by_this_report"]
        )
        self.assertFalse(report["handling_assertions"]["data_reuse_authorized"])

    def test_external_service_and_reuse_are_blocked(self) -> None:
        intake = ready_intake()
        intake["handling"]["external_service_use"] = True
        intake["handling"]["data_reuse_permitted"] = True
        report = validate_intake(intake)
        codes = {item["code"] for item in report["errors"]}
        self.assertIn("EXTERNAL_SERVICE_NOT_SUPPORTED", codes)
        self.assertIn("DATA_REUSE_PROHIBITED", codes)

    def test_disclosed_conflict_requires_actual_editor_clearance(self) -> None:
        intake = ready_intake()
        intake["reviewer"]["conflict_status"] = "disclosed_to_editor"
        intake["reviewer"]["conflicts"] = ["Synthetic declared competing interest"]
        report = validate_intake(intake)
        self.assertFalse(report["valid"])
        self.assertIn("EDITOR_CONFLICT_CLEARANCE_REQUIRED", {e["code"] for e in report["errors"]})
        intake["reviewer"]["conflict_status"] = "editor_cleared"
        self.assertTrue(validate_intake(intake)["valid"])


class ReportingGuidelineTests(unittest.TestCase):
    def test_rct_profile_selects_current_consort(self) -> None:
        profile = load_profile(load_asset_json("study_profile_template.json"))
        report = assess_reporting(profile, load_catalog())
        selected = {item["id"] for item in report["selected_guidelines"]}
        self.assertIn("CONSORT-2025", selected)
        self.assertNotIn("CONSORT-AI-2020", selected)

    def test_ai_rct_adds_extension(self) -> None:
        raw_profile = load_asset_json("study_profile_template.json")
        raw_profile["features"] = ["ai_intervention"]
        report = assess_reporting(load_profile(raw_profile), load_catalog())
        selected = {item["id"] for item in report["selected_guidelines"]}
        self.assertEqual(selected, {"CONSORT-2025", "CONSORT-AI-2020"})

    def test_ai_protocol_selects_protocol_base_and_extension(self) -> None:
        profile = load_asset_json("study_profile_template.json")
        profile.update(report_kind="protocol", features=["ai_intervention"])
        report = assess_reporting(load_profile(profile), load_catalog())
        self.assertEqual({g["id"] for g in report["selected_guidelines"]}, {"SPIRIT-2025", "SPIRIT-AI-2020"})

    def test_non_prediction_llm_study_selects_llm_guideline_only(self) -> None:
        profile = load_asset_json("study_profile_template.json")
        profile.update(study_types=["llm_study"], features=["large_language_model"])
        report = assess_reporting(load_profile(profile), load_catalog())
        self.assertEqual({g["id"] for g in report["selected_guidelines"]}, {"TRIPOD-LLM-2025"})

    def test_abstract_does_not_reuse_full_report_item_counts(self) -> None:
        profile = load_asset_json("study_profile_template.json")
        profile["report_kind"] = "abstract"
        report = assess_reporting(load_profile(profile), load_catalog())
        self.assertEqual(report["selected_guidelines"], [])
        self.assertIn("NO_BUNDLED_GUIDELINE_MATCH", {w["code"] for w in report["warnings"]})

    def test_coverage_is_complete_record_but_not_quality_score(self) -> None:
        profile = load_profile(load_asset_json("study_profile_template.json"))
        rows = load_coverage(ASSETS / "reporting_checklist_template.csv")
        report = assess_reporting(profile, load_catalog(), rows)
        consort = next(
            item
            for item in report["coverage"]
            if item["guideline_id"] == "CONSORT-2025"
        )
        self.assertTrue(consort["coverage_record_complete"])
        self.assertEqual(len(consort["reporting_gap_item_ids"]), 30)
        serialized = json.dumps(report).lower()
        self.assertNotIn("quality_score", serialized)
        self.assertIn("not scores", report["notice"])

    def test_reported_item_without_location_is_invalid(self) -> None:
        profile = load_profile(load_asset_json("study_profile_template.json"))
        rows = load_coverage(ASSETS / "reporting_checklist_template.csv")
        rows[0]["status"] = "reported"
        report = assess_reporting(profile, load_catalog(), rows)
        self.assertFalse(report["valid"])
        self.assertIn(
            "COVERAGE_LOCATION_REQUIRED",
            {item["code"] for item in report["errors"]},
        )


class ClaimEvidenceTests(unittest.TestCase):
    def test_template_matrix_is_structurally_valid_with_gaps(self) -> None:
        report = validate_matrix(
            load_matrix(ASSETS / "claim_evidence_matrix_template.csv")
        )
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["status"], "VALID_WITH_ALIGNMENT_GAPS")
        self.assertIn("CLAIM-SYN-002", report["claim_ids_requiring_resolution"])
        self.assertNotIn(
            "Synthetic broad generalization claim", json.dumps(report)
        )

    def test_supported_claim_without_evidence_is_invalid(self) -> None:
        rows = load_matrix(ASSETS / "claim_evidence_matrix_template.csv")
        rows[0]["evidence_ids"] = []
        report = validate_matrix(rows)
        self.assertFalse(report["valid"])
        self.assertIn(
            "SUPPORTED_CLAIM_HAS_NO_EVIDENCE",
            {item["code"] for item in report["errors"]},
        )


class StatisticsReproducibilityTests(unittest.TestCase):
    def test_template_is_valid_without_becoming_a_score(self) -> None:
        checklist = load_checklist(
            load_asset_json("statistical_reproducibility_template.json")
        )
        report = audit_statistics(checklist)
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["status"], "VALID_WITH_REVIEW_GAPS")
        self.assertNotIn("score", report)
        self.assertNotIn("quality_score", report)
        self.assertIn("not a", report["notice"])

    def test_missing_core_item_is_invalid(self) -> None:
        raw = load_asset_json("statistical_reproducibility_template.json")
        raw["items"] = raw["items"][1:]
        report = audit_statistics(load_checklist(raw))
        self.assertFalse(report["valid"])
        self.assertIn(
            "CORE_ITEM_MISSING", {item["code"] for item in report["errors"]}
        )

    def test_verified_item_requires_evidence_location(self) -> None:
        raw = load_asset_json("statistical_reproducibility_template.json")
        raw["items"][0]["status"] = "verified_present"
        report = audit_statistics(load_checklist(raw))
        self.assertFalse(report["valid"])
        self.assertIn(
            "EVIDENCE_LOCATION_REQUIRED",
            {item["code"] for item in report["errors"]},
        )


class CitationTests(unittest.TestCase):
    def _write_references(self, root: Path) -> Path:
        references = root / "references.csv"
        references.write_text(
            "reference_id,title,authors,year,doi,url,verification_status\n"
            "ref-one,Private synthetic title,Example Group,2026,"
            "10.1234/synthetic,https://example.invalid/ref-one,verified_primary\n",
            encoding="utf-8",
        )
        return references

    def test_matching_citation_is_valid_without_prose_echo(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manuscript = "A synthetic statement [@ref-one].\n"
            references = self._write_references(root)
            report = audit_citations(manuscript, load_references(str(references)))
        self.assertTrue(report["valid"])
        self.assertEqual(report["citation_occurrence_count"], 1)
        self.assertNotIn("Private synthetic title", json.dumps(report))

    def test_missing_reference_reports_only_identifier_and_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            references = self._write_references(root)
            report = audit_citations(
                "Confidential synthetic prose [@missing-ref].\n",
                load_references(str(references)),
            )
        self.assertFalse(report["valid"])
        self.assertEqual(report["missing_reference_ids"], ["missing-ref"])
        self.assertEqual(report["missing_reference_line_numbers"], {"missing-ref": [1]})
        self.assertNotIn("Confidential synthetic prose", json.dumps(report))


class ScaffoldAndLintTests(unittest.TestCase):
    def test_scaffold_requires_ready_intake(self) -> None:
        with self.assertRaisesRegex(ValidationError, "intake is blocked"):
            generate_scaffold(load_asset_json("review_intake_template.json"))

    def test_scaffold_has_separate_channels_and_no_manuscript_prose(self) -> None:
        rendered = generate_scaffold(ready_intake())
        self.assertIn("# Comments to authors", rendered)
        self.assertIn("# Confidential comments to editor", rendered)
        self.assertLess(
            rendered.index("# Comments to authors"),
            rendered.index("# Confidential comments to editor"),
        )
        self.assertNotIn("manuscript title", rendered.lower())

    def test_complete_structured_review_passes_lint(self) -> None:
        review = """# Comments to authors

### Major comment M1
- Location: Methods paragraph 2
- Observation: The analysis unit is not defined.
- Evidence or criterion: Three measurements are listed per synthetic unit.
- Why it matters: Dependence can change uncertainty estimates.
- Requested action: Define the unit and explain how dependence was handled.

### Minor comment m1
- Location: Figure 1 legend
- Observation: The uncertainty interval is unnamed.
- Evidence or criterion: The legend contains an interval without a definition.
- Why it matters: Readers cannot interpret the interval.
- Requested action: Name the interval and calculation method.

# Confidential comments to editor

No separate process concern is recorded.
"""
        report = lint_review(review)
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["structured_comment_count"], 2)

    def test_abuse_decision_and_missing_action_are_flagged_without_echo(self) -> None:
        review = """# Comments to authors

### Major comment M1
- Location: Results
- Observation: This ridiculous analysis is incomplete.
- Evidence or criterion: Synthetic criterion
- Why it matters: Interpretation is limited.
- Requested action:

# Confidential comments to editor

We recommend reject.
"""
        report = lint_review(review)
        codes = {item["code"] for item in report["errors"]}
        self.assertIn("ABUSIVE_OR_DISMISSIVE_LANGUAGE", codes)
        self.assertIn("EDITORIAL_DECISION_LANGUAGE", codes)
        self.assertIn("ACTIONABILITY_FIELD_EMPTY", codes)
        self.assertNotIn("ridiculous", json.dumps(report).lower())


class FileSafetyAndStaticTests(unittest.TestCase):
    def test_private_output_refuses_implicit_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            write_json_report({"valid": True}, output)
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            with self.assertRaises(ValidationError):
                write_json_report({"valid": False}, output)
            write_json_report({"valid": False}, output, force=True)
            self.assertEqual(json.loads(output.read_text()), {"valid": False})

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
            lowered = source.lower()
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
        self.assertGreaterEqual(len(rows), 25)
        for row in rows:
            verified = date.fromisoformat(row["verified_on"])
            checked = date.fromisoformat(row["checked_on"])
            self.assertLessEqual(verified, checked)
            self.assertLessEqual(checked, date.today())
        self.assertTrue(all(row["url"].startswith("https://") for row in rows))

    def test_skill_frontmatter_and_progressive_disclosure(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertLess(len(skill.splitlines()), 500)
        self.assertRegex(skill, r'\n  version: "\d+\.\d+"\n')
        self.assertIn("license: MIT", skill)
        self.assertIn("compatibility:", skill)
        self.assertNotIn("OPENROUTER", skill)
        self.assertNotIn("generate_schematic", skill)
        self.assertNotIn("scientific-schematics", skill)
        self.assertNotIn("venue-templates", skill)

    def test_no_bytecode_or_removed_schematic_scripts(self) -> None:
        self.assertFalse(list(SKILL_ROOT.rglob("*.pyc")))
        self.assertFalse((SCRIPTS / "generate_schematic.py").exists())
        self.assertFalse((SCRIPTS / "generate_schematic_ai.py").exists())


# The shared --help contract: every argparse CLI this skill ships answers --help
# without doing any work. It skips when the skill's packages are absent and runs
# for real under `python tests/run_all.py --isolated`.
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

if __name__ == "__main__":
    unittest.main()
