#!/usr/bin/env python3
"""Synthetic, dependency-free tests for clinical-reports local tooling."""

from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "clinical-reports"
SCRIPTS = SKILL_ROOT / "scripts"
ASSETS = SKILL_ROOT / "assets"
sys.path.insert(0, str(SCRIPTS))

from _common import (  # noqa: E402
    ValidationError,
    load_json_object,
    local_output_path,
    parse_iso_date,
    require_data_class,
)
from check_deidentification import validate_process  # noqa: E402
from consistency_checker import validate_consistency  # noqa: E402
from format_adverse_events import (  # noqa: E402
    load_aggregate_csv,
    render_markdown,
    validate_aggregate_metadata,
)
from generate_report_template import generate_template  # noqa: E402
from provenance_validator import validate_provenance  # noqa: E402
from terminology_validator import validate_terminology_manifest  # noqa: E402
from validate_case_report import CARE_ITEMS, validate_case_manifest  # noqa: E402
from validate_trial_report import E3_SECTIONS, validate_trial_manifest  # noqa: E402

import skill_contract


def valid_case_manifest() -> dict:
    return {
        "schema_version": "2.0",
        "artifact_kind": "case_report_draft",
        "draft_status": "BLOCKED_INCOMPLETE_DRAFT_NOT_FOR_CLINICAL_USE_OR_SUBMISSION",
        "safety_notice": "Synthetic draft test; qualified review required.",
        "data_classification": "synthetic",
        "authorized_purpose": "synthetic structural test",
        "authorization_verified": True,
        "provenance_manifest": "local:synthetic-provenance.json",
        "guidance": {
            "name": "CARE",
            "checklist_version": "2013",
            "explanation_version": "2017",
            "target_journal_instructions_checked": True,
        },
        "care_items": {
            key: {
                "status": "verified_present",
                "source_fact_ids": [f"FACT-{index:02d}"],
                "rationale": None,
            }
            for index, key in enumerate(CARE_ITEMS, start=1)
        },
        "privacy": {
            "deidentification_process_record": "local:synthetic-deid.json",
            "publication_consent_record": "local:synthetic-consent-status",
            "image_or_media_included": False,
            "reidentification_risk_reviewed": True,
        },
        "review": {
            "qualified_clinical_review": "completed",
            "privacy_legal_review": "completed",
            "accountable_author_review": "completed",
            "submission_authorized": False,
        },
    }


def valid_csr_manifest() -> dict:
    return {
        "schema_version": "2.0",
        "artifact_kind": "clinical_study_report_draft",
        "draft_status": "BLOCKED_INCOMPLETE_DRAFT_NOT_FOR_FILING_OR_SUBMISSION",
        "safety_notice": "Synthetic aggregate CSR structure test; review required.",
        "data_classification": "aggregate",
        "authorized_purpose": "synthetic CSR structure test",
        "authorization_verified": True,
        "provenance_manifest": "local:synthetic-provenance.json",
        "guidance": {
            "base": "ICH E3",
            "base_version": "Step 4 1995-11-30",
            "qa_version": "R1 2012-07-06",
            "gcp_version_considered": "ICH E6(R3) consolidated 2026-06-16",
            "regional_adoption_verified": True,
        },
        "study_metadata": {
            "protocol_reference": "local:synthetic-protocol",
            "sap_reference": "local:synthetic-sap",
            "data_cut_reference": "local:synthetic-data-cut",
            "analysis_output_reference": "local:synthetic-output",
            "coding_dictionary_versions": ["MedDRA 29.0 synthetic test"],
        },
        "sections": {
            key: {
                "status": "verified_present",
                "source_fact_ids": [f"FACT-E3-{index:02d}"],
                "rationale": None,
            }
            for index, key in enumerate(E3_SECTIONS, start=1)
        },
        "review": {
            "medical_review": "completed",
            "statistical_review": "completed",
            "safety_review": "completed",
            "privacy_legal_review": "completed",
            "quality_review": "completed",
            "regulatory_review": "completed",
            "submission_authorized": False,
        },
    }


def valid_aggregate_metadata(input_name: str) -> dict:
    return {
        "schema_version": "2.0",
        "artifact_kind": "clinical_trial_safety_aggregate_draft",
        "draft_status": "BLOCKED_INCOMPLETE_NOT_AN_INDIVIDUAL_CASE_SAFETY_REPORT",
        "safety_notice": "Synthetic aggregate display only; qualified review required.",
        "data_classification": "aggregate",
        "authorized_purpose": "synthetic formatter test",
        "authorization_verified": True,
        "local_only_handling_confirmed": True,
        "analysis_metadata": {
            "protocol_reference": "local:synthetic-protocol",
            "sap_reference": "local:synthetic-sap",
            "data_cut_reference": "local:synthetic-data-cut",
            "analysis_set": "Safety set",
            "counting_rule": "synthetic subject and event counts",
            "threshold_rule": "all synthetic terms",
            "meddra_version": "29.0",
            "meddra_language": "English",
            "coding_source_reference": "local:synthetic-coding-output",
        },
        "input_csv": input_name,
        "required_columns": [
            "analysis_set",
            "treatment_group",
            "meddra_version",
            "system_organ_class",
            "preferred_term",
            "subjects_affected",
            "event_count",
            "denominator",
        ],
        "prohibited_content": ["patient-level content"],
        "provenance_manifest": "local:synthetic-provenance",
        "review": {
            "safety_coding_review": "pending",
            "statistical_review": "pending",
            "privacy_review": "pending",
            "regulatory_review": "pending",
            "submission_authorized": False,
        },
    }


class StructuralValidatorTests(unittest.TestCase):
    def test_complete_case_structure_still_requires_review(self) -> None:
        report = validate_case_manifest(valid_case_manifest())
        self.assertEqual(report["status"], "STRUCTURE_COMPLETE_REVIEW_REQUIRED")
        self.assertFalse(report["authorizes_clinical_use_or_submission"])

    def test_missing_case_item_blocks(self) -> None:
        manifest = valid_case_manifest()
        manifest["care_items"]["timeline"]["status"] = "missing"
        report = validate_case_manifest(manifest)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertTrue(any("timeline" in item for item in report["errors"]))

    def test_unknown_case_field_blocks(self) -> None:
        manifest = valid_case_manifest()
        manifest["patient_name"] = "SYNTHETIC-NOT-A-PERSON"
        report = validate_case_manifest(manifest)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertTrue(any("unknown" in item for item in report["errors"]))

    def test_complete_ich_e3_structure_still_requires_review(self) -> None:
        report = validate_trial_manifest(valid_csr_manifest())
        self.assertEqual(report["status"], "STRUCTURE_COMPLETE_REVIEW_REQUIRED")
        self.assertEqual(len(report["coverage"]), 16)

    def test_complete_consort_2025_coverage_still_requires_review(self) -> None:
        manifest = json.loads(
            (ASSETS / "clinical_trial_results_template.json").read_text(encoding="utf-8")
        )
        manifest["authorized_purpose"] = "synthetic CONSORT coverage test"
        manifest["authorization_verified"] = True
        manifest["provenance_manifest"] = "local:synthetic-provenance"
        manifest["guidance"]["statement_and_explanation_checked"] = True
        manifest["guidance"]["applicable_extensions_reviewed"] = True
        manifest["study_metadata"] = {
            key: f"local:synthetic-{key}"
            for key in (
                "protocol_reference",
                "sap_reference",
                "registry_reference",
                "data_cut_reference",
                "analysis_output_reference",
            )
        }
        for key, item in manifest["checklist_items"].items():
            item["status"] = "verified_present"
            item["source_fact_ids"] = [f"FACT-{key}"]
            item["official_item_locator"] = f"CONSORT-2025-{key}"
        manifest["participant_flow_source_fact_ids"] = ["FACT-FLOW"]
        for field in (
            "accountable_author_review",
            "methodologist_review",
            "statistical_review",
            "safety_review",
        ):
            manifest["review"][field] = "completed"
        report = validate_trial_manifest(manifest)
        self.assertEqual(report["status"], "STRUCTURE_COMPLETE_REVIEW_REQUIRED")
        self.assertEqual(len(report["coverage"]), 30)

    def test_complete_spirit_2025_coverage_still_requires_review(self) -> None:
        manifest = json.loads(
            (ASSETS / "trial_protocol_reporting_checklist.json").read_text(
                encoding="utf-8"
            )
        )
        manifest["authorized_purpose"] = "synthetic SPIRIT coverage test"
        manifest["authorization_verified"] = True
        manifest["provenance_manifest"] = "local:synthetic-provenance"
        manifest["guidance"]["statement_and_explanation_checked"] = True
        manifest["guidance"]["applicable_extensions_reviewed"] = True
        manifest["protocol_metadata"] = {
            "authorized_protocol_reference": "local:synthetic-protocol",
            "protocol_version": "SYNTHETIC-1",
            "registry_reference": "local:synthetic-registry",
            "ethics_record_reference": "local:synthetic-ethics-status",
        }
        for key, item in manifest["checklist_items"].items():
            item["status"] = "verified_present"
            item["source_fact_ids"] = [f"FACT-{key}"]
            item["official_item_locator"] = f"SPIRIT-2025-{key}"
        manifest["participant_timeline_source_fact_ids"] = ["FACT-TIMELINE"]
        for field in (
            "investigator_sponsor_review",
            "methodologist_review",
            "statistical_review",
            "safety_review",
            "ethics_regulatory_review",
        ):
            manifest["review"][field] = "completed"
        report = validate_trial_manifest(manifest)
        self.assertEqual(report["status"], "STRUCTURE_COMPLETE_REVIEW_REQUIRED")
        self.assertEqual(len(report["coverage"]), 34)


class AggregateFormatterTests(unittest.TestCase):
    def test_formats_synthetic_aggregate_rows(self) -> None:
        content = (
            "analysis_set,treatment_group,meddra_version,system_organ_class,"
            "preferred_term,subjects_affected,event_count,denominator\n"
            "Safety set,Group A,29.0,General disorders,Headache,2,3,10\n"
            "Safety set,Group B,29.0,General disorders,Headache,1,1,8\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "aggregate.csv"
            path.write_text(content, encoding="utf-8")
            rows = load_aggregate_csv(str(path))
            metadata = valid_aggregate_metadata(path.name)
            validate_aggregate_metadata(metadata, input_name=path.name)
            rendered = render_markdown(
                rows,
                metadata=metadata,
                expected_meddra_version="29.0",
            )
        self.assertIn("2/10 (20.0%)", rendered)
        self.assertIn("not an icsr", rendered.lower())
        self.assertNotIn("p-value", rendered.lower())

    def test_rejects_row_level_identifier_column(self) -> None:
        content = (
            "analysis_set,treatment_group,meddra_version,system_organ_class,"
            "preferred_term,subjects_affected,event_count,denominator,subject_id\n"
            "Safety set,Group A,29.0,General disorders,Headache,1,1,10,SYN-001\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "aggregate.csv"
            path.write_text(content, encoding="utf-8")
            with self.assertRaises(ValidationError):
                load_aggregate_csv(str(path))


class ProcessAndSchemaTests(unittest.TestCase):
    def test_terminology_local_dictionary_match_is_not_clinical_validation(self) -> None:
        manifest = {
            "schema_version": "2.0",
            "artifact_kind": "terminology_manifest",
            "manifest_status": "BLOCKED_INCOMPLETE",
            "safety_notice": "Synthetic terminology test; qualified review required.",
            "data_classification": "synthetic",
            "authorized_purpose": "synthetic terminology schema test",
            "authorization_verified": True,
            "provenance_manifest": "local:synthetic-provenance",
            "entries": [
                {
                    "system": "LOINC",
                    "system_uri": "urn:synthetic:loinc",
                    "code": "1234-5",
                    "display": "Synthetic observation",
                    "version": "2.82",
                    "language": "en",
                    "source_fact_id": "FACT-TERM-01",
                    "coding_status": "verified_by_qualified_reviewer",
                    "verified_by_role": "synthetic terminology reviewer",
                    "verified_at": "2026-07-23",
                }
            ],
        }
        dictionary = {("LOINC", "2.82", "1234-5"): "Synthetic observation"}
        report = validate_terminology_manifest(manifest, dictionary)
        self.assertEqual(
            report["status"],
            "SCHEMA_AND_LOCAL_DICTIONARY_MATCH_REVIEW_REQUIRED",
        )
        self.assertIn("does not establish clinical correctness", report["limitations"][0])

    def test_synthetic_deidentification_process_never_claims_compliance(self) -> None:
        manifest = {
            "schema_version": "2.0",
            "artifact_kind": "deidentification_process_checklist",
            "process_status": "BLOCKED_NOT_ASSESSED",
            "safety_notice": "Synthetic process test; this cannot establish compliance.",
            "data_scope": "synthetic",
            "authorized_purpose": "synthetic test",
            "authorization_verified": True,
            "local_only_handling_confirmed": True,
            "minimum_necessary_reviewed": True,
            "method": "not_applicable_synthetic_or_aggregate",
            "safe_harbor_identifiers": {
                key: "not_assessed"
                for key in (
                    "names",
                    "geographic_subdivisions",
                    "dates_and_ages",
                    "telephone_numbers",
                    "fax_numbers",
                    "email_addresses",
                    "social_security_numbers",
                    "medical_record_numbers",
                    "health_plan_numbers",
                    "account_numbers",
                    "certificate_and_license_numbers",
                    "vehicle_identifiers",
                    "device_identifiers",
                    "urls",
                    "ip_addresses",
                    "biometric_identifiers",
                    "full_face_images",
                    "other_unique_characteristics_or_codes",
                )
            },
            "actual_knowledge_review": {
                "completed_by_authorized_privacy_reviewer": False,
                "record_reference": None,
            },
            "expert_determination": {
                "completed_by_qualified_expert": False,
                "expert_documentation_reference": None,
                "anticipated_recipient_and_conditions_documented": False,
            },
            "synthetic_or_aggregate_rationale": {
                "origin_verified": True,
                "record_reference": "local:synthetic-origin",
            },
            "residual_risk_review": {
                "free_text": "not_applicable_with_rationale",
                "small_cells_and_rare_cases": "not_applicable_with_rationale",
                "images_and_metadata": "not_applicable_with_rationale",
                "linked_data_and_quasi_identifiers": "not_applicable_with_rationale",
            },
            "review": {
                "privacy_legal_review": "completed",
                "institutional_release_review": "completed",
                "release_authorized": False,
            },
        }
        report = validate_process(manifest)
        self.assertEqual(report["status"], "PROCESS_DOCUMENTED_REVIEW_REQUIRED")
        self.assertNotIn("COMPLIANT", json.dumps(report).upper())

    def test_provenance_links_verified_fact_without_content(self) -> None:
        manifest = {
            "schema_version": "2.0",
            "artifact_kind": "provenance_manifest",
            "manifest_status": "BLOCKED_INCOMPLETE",
            "safety_notice": "Synthetic traceability test; qualified review required.",
            "data_classification": "aggregate",
            "authorized_purpose": "synthetic traceability test",
            "authorization_verified": True,
            "facts": [
                {
                    "fact_id": "FACT-001",
                    "source_record_kind": "aggregate_output",
                    "record_locator": "local:synthetic/output.json",
                    "field_path": "$.counts.total",
                    "value_hash_sha256": "a" * 64,
                    "verification_status": "verified",
                    "verified_by_role": "synthetic data reviewer",
                    "verified_at": "2026-07-23",
                    "source_version": "SYNTHETIC-1",
                }
            ],
            "claims": [
                {
                    "claim_id": "CLAIM-001",
                    "artifact_field_path": "$.sections.results",
                    "fact_ids": ["FACT-001"],
                    "support_status": "supported_by_verified_facts",
                }
            ],
            "review": {
                "source_owner_review": "completed",
                "quality_review": "completed",
                "privacy_review": "completed",
                "release_authorized": False,
            },
        }
        report = validate_provenance(manifest)
        self.assertEqual(report["status"], "TRACEABILITY_COMPLETE_REVIEW_REQUIRED")

    def test_consistency_detects_denominator_mismatch(self) -> None:
        manifest = {
            "schema_version": "2.0",
            "artifact_kind": "consistency_manifest",
            "manifest_status": "BLOCKED_INCOMPLETE",
            "safety_notice": "Synthetic arithmetic test; qualified review required.",
            "data_classification": "aggregate",
            "authorized_purpose": "synthetic consistency test",
            "authorization_verified": True,
            "provenance_manifest": "local:synthetic-provenance",
            "dates": [],
            "date_ranges": [],
            "quantities": [],
            "totals": [],
            "proportions": [
                {
                    "id": "CHECK-001",
                    "numerator": 2,
                    "denominator": 10,
                    "reported_percent": 25.0,
                    "tolerance_percentage_points": 0.05,
                    "source_fact_id": "FACT-001",
                }
            ],
        }
        report = validate_consistency(manifest)
        self.assertEqual(report["status"], "DISCREPANCIES_REQUIRE_RESOLUTION")


class AssetAndGeneratorTests(unittest.TestCase):
    def test_bundled_path_references_exist(self) -> None:
        markdown_files = [SKILL_ROOT / "SKILL.md", *(SKILL_ROOT / "references").glob("*.md")]
        pattern = re.compile(r"`((?:assets|references|scripts)/[A-Za-z0-9_./-]+)`")
        for markdown in markdown_files:
            for relative in pattern.findall(markdown.read_text(encoding="utf-8")):
                self.assertTrue((SKILL_ROOT / relative).is_file(), f"{markdown.name}: {relative}")

    def test_every_json_asset_parses_and_contains_no_obvious_real_phi(self) -> None:
        email = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
        ssn = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
        phone = re.compile(r"\b\d{3}[-.]\d{3}[-.]\d{4}\b")
        for path in ASSETS.glob("*.json"):
            text = path.read_text(encoding="utf-8")
            json.loads(text)
            self.assertIsNone(email.search(text), path.name)
            self.assertIsNone(ssn.search(text), path.name)
            self.assertIsNone(phone.search(text), path.name)
            self.assertNotIn("OPENROUTER", text)

    def test_generator_copies_blocked_template_without_interpolation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "case.json"
            generated = generate_template("case-report", str(output))
            data = json.loads(generated.read_text(encoding="utf-8"))
        self.assertIn("BLOCKED", data["draft_status"])
        self.assertFalse(data["authorization_verified"])


class InputBoundaryTests(unittest.TestCase):
    def test_duplicate_csv_column_cannot_silently_replace_count(self) -> None:
        content = (
            "analysis_set,treatment_group,meddra_version,system_organ_class,"
            "preferred_term,subjects_affected,event_count,denominator,denominator\n"
            "Safety set,Group A,29.1,Synthetic SOC,Synthetic term,2,3,1,10\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "aggregate.csv"
            path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(ValidationError, "duplicate CSV"):
                load_aggregate_csv(str(path))

    def test_whitespace_csv_header_is_rejected_before_row_mapping(self) -> None:
        content = (
            "analysis_set,treatment_group,meddra_version,system_organ_class,"
            "preferred_term,subjects_affected,event_count, denominator\n"
            "Safety set,Group A,29.1,Synthetic SOC,Synthetic term,2,3,10\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "aggregate.csv"
            path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(ValidationError, "surrounding whitespace"):
                load_aggregate_csv(str(path))

    def test_recurrent_events_can_exceed_participant_denominator(self) -> None:
        content = (
            "analysis_set,treatment_group,meddra_version,system_organ_class,"
            "preferred_term,subjects_affected,event_count,denominator\n"
            "Safety set,Group A,29.1,Synthetic SOC,Synthetic term,2,15,10\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "aggregate.csv"
            path.write_text(content, encoding="utf-8")
            rows = load_aggregate_csv(str(path))
            metadata = valid_aggregate_metadata(path.name)
            metadata["analysis_metadata"]["meddra_version"] = "29.1"
            validate_aggregate_metadata(metadata, input_name=path.name)
            rendered = render_markdown(rows, metadata=metadata)
        self.assertIn("2/10 (20.0%) | 15 |", rendered)
        self.assertNotIn("150.0%", rendered)

    def test_calendar_dates_do_not_silently_accept_basic_or_week_dates(self) -> None:
        self.assertEqual(parse_iso_date("2026-09-30", "date").isoformat(), "2026-09-30")
        for value in ("20260930", "2026-W40-3", "2026-02-30", "2026-09"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                parse_iso_date(value, "date")

    def test_unhashable_data_class_is_validation_error(self) -> None:
        for value in ([], {}, ["synthetic"]):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                require_data_class(value)

    def test_unhashable_route_and_item_statuses_remain_blocked(self) -> None:
        for value in ([], {}):
            with self.subTest(value=value):
                self.assertEqual(validate_trial_manifest({"artifact_kind": value})["status"], "BLOCKED")
                case = valid_case_manifest()
                case["care_items"]["timeline"]["status"] = value
                self.assertEqual(validate_case_manifest(case)["status"], "BLOCKED")
                csr = valid_csr_manifest()
                csr["sections"]["synopsis"]["status"] = value
                self.assertEqual(validate_trial_manifest(csr)["status"], "BLOCKED")

    def test_unhashable_process_statuses_remain_blocked(self) -> None:
        template = ASSETS / "deidentification_process_checklist.json"
        for field in ("method", "safe_harbor_identifiers", "residual_risk_review"):
            with self.subTest(field=field):
                data = json.loads(template.read_text(encoding="utf-8"))
                if field == "method":
                    data[field] = []
                elif field == "safe_harbor_identifiers":
                    data["method"] = "safe_harbor"
                    data[field]["names"] = []
                else:
                    data[field]["free_text"] = []
                self.assertEqual(validate_process(data)["status"], "BLOCKED")

    def test_unhashable_source_kind_remains_blocked(self) -> None:
        data = json.loads((ASSETS / "provenance_manifest_template.json").read_text())
        data["facts"] = [{
            "fact_id": "FACT-001", "source_record_kind": [],
            "record_locator": "local:synthetic", "field_path": "$.n",
            "value_hash_sha256": "a" * 64, "verification_status": "verified",
            "verified_by_role": "synthetic reviewer", "verified_at": "2026-09-30",
            "source_version": "synthetic-1",
        }]
        self.assertEqual(validate_provenance(data)["status"], "BLOCKED")

    def test_unhashable_coding_status_remains_blocked(self) -> None:
        data = json.loads((ASSETS / "terminology_manifest_template.json").read_text())
        data["entries"] = [{
            "system": "LOINC", "system_uri": "urn:synthetic:loinc",
            "code": "1234-5", "display": "Synthetic observation", "version": "2.83",
            "language": "en", "source_fact_id": "FACT-001", "coding_status": [],
            "verified_by_role": None, "verified_at": None,
        }]
        self.assertEqual(validate_terminology_manifest(data)["status"], "BLOCKED")

    def test_unrepresentable_quantity_is_blocked_without_overflow(self) -> None:
        data = json.loads((ASSETS / "consistency_manifest_template.json").read_text())
        data["quantities"] = [{
            "id": "CHECK-001", "series_id": "SERIES-001", "value": 10 ** 400,
            "unit": "synthetic", "expected_unit": None, "source_fact_id": "FACT-001",
        }]
        report = validate_consistency(data)
        self.assertEqual(report["status"], "BLOCKED_INVALID_SCHEMA")
        self.assertTrue(any("representable" in error for error in report["errors"]))

    def test_deep_json_is_blocked_without_recursion_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "deep.json"
            path.write_text('{"x":' + '[' * 2000 + '0' + ']' * 2000 + '}')
            with self.assertRaises(ValidationError):
                load_json_object(str(path))

    def test_dangling_output_symlink_cannot_create_an_unselected_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            selected = Path(tmp) / "selected.json"
            unselected = Path(tmp) / "unselected.json"
            selected.symlink_to(unselected)
            with self.assertRaises(ValidationError):
                local_output_path(str(selected), suffixes={".json"}, overwrite=True)
            self.assertFalse(unselected.exists())


# The shared --help contract: every argparse CLI this skill ships answers --help
# without doing any work. It skips when the skill's packages are absent and runs
# for real under `python tests/run_all.py --isolated`.
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

if __name__ == "__main__":
    unittest.main()
