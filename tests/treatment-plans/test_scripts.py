"""Synthetic, dependency-free tests for treatment-plan documentation CLIs."""

from __future__ import annotations

import ast
import copy
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "treatment-plans"
SCRIPTS = SKILL_ROOT / "scripts"
ASSETS = SKILL_ROOT / "assets"
sys.path.insert(0, str(SCRIPTS))

import _common  # noqa: E402
import check_completeness  # noqa: E402
import check_consistency  # noqa: E402
import generate_template  # noqa: E402
import privacy_process_check  # noqa: E402
import timeline_generator  # noqa: E402
import validate_treatment_plan  # noqa: E402
import validate_traceability  # noqa: E402


def load_asset(name: str) -> dict:
    return json.loads((ASSETS / name).read_text(encoding="utf-8"))


def complete_synthetic_documents() -> dict[str, dict]:
    documents: dict[str, dict] = {}
    document_ids = {
        "source_fact_manifest": "DOC-SOURCE-001",
        "clinician_authored_intervention_record": "DOC-INTERVENTION-001",
        "goals_monitoring_checkpoint_record": "DOC-PLANNING-001",
        "informed_preference_shared_decision_record": "DOC-DECISION-001",
        "transition_reconciliation_record": "DOC-TRANSITION-001",
        "intended_use_handoff_record": "DOC-HANDOFF-001",
    }
    for document_type, (template_name, _) in _common.TEMPLATE_FILES.items():
        document = copy.deepcopy(load_asset(template_name))
        document["document_id"] = document_ids[document_type]
        document["created_at"] = "2026-07-23T12:00:00+00:00"
        documents[document_type] = document

    documents["source_fact_manifest"]["facts"] = [
        {
            "fact_id": "FACT-SYNTHETIC-001",
            "fact_kind": "clinician_authored_decision",
            "statement_as_supplied": (
                "Synthetic clinician-authored documentation statement."
            ),
            "source": {
                "source_type": "signed_clinician_record",
                "title": "Synthetic signed source record",
                "locator": "LOCAL-SYNTHETIC-SOURCE-001",
                "version_or_date": "2026-07-23",
            },
            "verification": {
                "status": "verified",
                "verified_by_role": "authorized licensed clinician",
                "verified_at": "2026-07-23T13:00:00+00:00",
            },
            "applicability": {
                "status": "not_applicable_local_record",
                "confirmed_by_role": "",
                "confirmed_at": None,
            },
        }
    ]

    documents["clinician_authored_intervention_record"]["interventions"] = [
        {
            "intervention_id": "INTERVENTION-SYNTHETIC-001",
            "intervention_kind": "care_coordination",
            "clinical_decision_status": (
                "supplied_and_verified_by_authorized_clinician"
            ),
            "clinician_authored_action": (
                "Synthetic clinician-authored coordination action."
            ),
            "parameters_as_supplied": [],
            "source_fact_ids": ["FACT-SYNTHETIC-001"],
            "owner_role": "authorized licensed clinician",
            "start_date": "2026-07-24",
            "end_date": "2026-07-25",
            "verification": {
                "status": "verified",
                "verified_by_role": "authorized licensed clinician",
                "verified_at": "2026-07-23T14:00:00+00:00",
            },
        }
    ]

    planning = documents["goals_monitoring_checkpoint_record"]
    planning["goals"] = [
        {
            "goal_id": "GOAL-SYNTHETIC-001",
            "statement_as_supplied": "Synthetic clinician-supplied goal.",
            "measurement_as_supplied": "Synthetic documented measure.",
            "target_as_supplied": "Synthetic documented target.",
            "target_date": "2026-08-01",
            "source_fact_ids": ["FACT-SYNTHETIC-001"],
            "verified_by_role": "authorized licensed clinician",
        }
    ]
    planning["monitoring_items"] = [
        {
            "monitoring_id": "MONITORING-SYNTHETIC-001",
            "item_as_supplied": "Synthetic clinician-supplied monitoring item.",
            "method_as_supplied": "Synthetic documented method.",
            "frequency_as_supplied": "Synthetic supplied frequency text.",
            "next_due_date": "2026-07-26",
            "owner_role": "authorized licensed clinician",
            "source_fact_ids": ["FACT-SYNTHETIC-001"],
        }
    ]
    planning["checkpoints"] = [
        {
            "checkpoint_id": "CHECKPOINT-SYNTHETIC-001",
            "checkpoint_date": "2026-07-27",
            "purpose_as_supplied": "Synthetic supplied checkpoint purpose.",
            "owner_role": "authorized licensed clinician",
            "linked_goal_ids": ["GOAL-SYNTHETIC-001"],
            "linked_intervention_ids": ["INTERVENTION-SYNTHETIC-001"],
            "source_fact_ids": ["FACT-SYNTHETIC-001"],
        }
    ]

    documents["informed_preference_shared_decision_record"]["entries"] = [
        {
            "decision_id": "DECISION-SYNTHETIC-001",
            "decision_topic_as_documented": "Synthetic documented topic.",
            "options_as_documented": [
                {
                    "option_id": "OPTION-SYNTHETIC-001",
                    "option_as_documented": "Synthetic documented option.",
                    "source_fact_ids": ["FACT-SYNTHETIC-001"],
                }
            ],
            "benefits_harms_uncertainty_documented": True,
            "preference_as_documented": "Synthetic documented preference.",
            "outcome_as_documented": "Synthetic clinician-documented outcome.",
            "outcome_source_fact_ids": ["FACT-SYNTHETIC-001"],
            "decision_status": "documented_by_authorized_clinician",
            "participant_roles": [
                "synthetic participant",
                "authorized licensed clinician",
            ],
            "documented_by_role": "authorized licensed clinician",
            "documented_at": "2026-07-24T10:00:00+00:00",
            "acknowledgment_status": "acknowledged",
        }
    ]

    transition = documents["transition_reconciliation_record"]
    transition["transition"] = {
        "from_setting_as_documented": "synthetic sending setting",
        "to_setting_as_documented": "synthetic receiving setting",
        "handoff_date": "2026-07-28",
        "responsible_sender_role": "authorized sender",
        "responsible_receiver_role": "authorized receiver",
    }
    transition["medication_reconciliation"] = {
        "status": "completed_by_authorized_clinician",
        "source_list_fact_ids": ["FACT-SYNTHETIC-001"],
        "destination_list_fact_ids": ["FACT-SYNTHETIC-001"],
        "discrepancy_status": "none_documented",
        "completed_by_role": "authorized medication reviewer",
        "completed_at": "2026-07-27T12:00:00+00:00",
    }
    transition["handoff_items"] = [
        {
            "item_id": "HANDOFF-SYNTHETIC-001",
            "category": "other_clinician_supplied",
            "summary_as_supplied": "Synthetic clinician-supplied handoff item.",
            "source_fact_ids": ["FACT-SYNTHETIC-001"],
            "owner_role": "authorized sender",
            "recipient_role": "authorized receiver",
            "acknowledgment_status": "acknowledged",
        }
    ]
    transition["unresolved_items"] = []

    handoff = documents["intended_use_handoff_record"]
    handoff["intended_use"]["intended_users"] = ["authorized clinician"]
    handoff["intended_use"]["intended_setting"] = "synthetic test setting"
    handoff["privacy_process"].update(
        {
            "local_authorization_confirmed": True,
            "authorized_environment_reference": "LOCAL-SYNTHETIC-ENV",
            "minimum_necessary_confirmed": True,
            "no_external_tools_confirmed": True,
            "no_prompt_log_example_copy_confirmed": True,
            "privacy_review_status": "not_applicable_synthetic",
            "retention_policy_reference": "LOCAL-SYNTHETIC-RETENTION",
            "data_disposition_status": "completed_under_local_policy",
        }
    )
    handoff["local_governance"] = {
        "institution_or_organization_reference": "LOCAL-SYNTHETIC-ORG",
        "clinical_owner_role": "authorized clinical owner",
        "policy_references": ["LOCAL-SYNTHETIC-POLICY"],
        "records_owner_role": "authorized records owner",
        "change_control_owner_role": "authorized change owner",
    }
    handoff["emergency_routing"].update(
        {
            "local_process_reference": "LOCAL-SYNTHETIC-ESCALATION",
            "verified_by_role": "authorized clinical owner",
        }
    )
    handoff["reporting_routes"] = {
        "local_patient_safety_route": "not_applicable_synthetic",
        "product_event_route": "not_applicable_synthetic",
        "privacy_incident_route": "LOCAL-SYNTHETIC-INCIDENT-ROUTE",
        "responsible_role": "authorized governance owner",
    }
    handoff["handoff"] = {
        "sender_role": "authorized sender",
        "recipient_role": "authorized receiver",
        "sent_at": "2026-07-29T12:00:00+00:00",
        "acknowledgment_status": "acknowledged",
        "unresolved_items_routed": True,
    }
    handoff["clinician_signoff"].update(
        {
            "status": "signed",
            "signer_role": "authorized licensed clinician",
            "credential_authority_reference": "LOCAL-SYNTHETIC-CREDENTIAL",
            "signed_at": "2026-07-28T10:00:00+00:00",
        }
    )
    handoff["release_gate"] = {
        "status": "released_for_authorized_documentation_handoff",
        "released_by_role": "authorized licensed clinician",
        "released_at": "2026-07-28T11:00:00+00:00",
        "blocker_codes": [],
    }
    return documents


def write_package(root: Path, documents: dict[str, dict]) -> None:
    for document_type, (_, filename) in _common.TEMPLATE_FILES.items():
        (root / filename).write_text(
            json.dumps(documents[document_type], indent=2) + "\n",
            encoding="utf-8",
        )


class StaticSafetyTests(unittest.TestCase):
    def test_scripts_have_no_network_dynamic_or_process_features(self) -> None:
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

    def test_old_specialty_and_schematic_files_are_absent(self) -> None:
        self.assertEqual(list(ASSETS.glob("*.tex")), [])
        self.assertEqual(list(ASSETS.glob("*.sty")), [])
        self.assertFalse((SCRIPTS / "generate_schematic.py").exists())
        self.assertFalse((SCRIPTS / "generate_schematic_ai.py").exists())

    def test_assets_are_generic_json_only(self) -> None:
        names = {path.name for path in ASSETS.iterdir() if path.is_file()}
        expected = {value[0] for value in _common.TEMPLATE_FILES.values()}
        self.assertEqual(names, expected)
        prohibited = {
            "diabetes",
            "depression",
            "hypertension",
            "metformin",
            "sertraline",
            "gabapentin",
        }
        for path in ASSETS.glob("*.json"):
            text = path.read_text(encoding="utf-8").lower()
            self.assertFalse(prohibited & set(re.findall(r"[a-z]+", text)))
            self.assertIn(_common.NOTICE.lower(), text)

    def test_skill_is_versioned_and_under_500_lines(self) -> None:
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertLess(len(text.splitlines()), 500)
        self.assertRegex(text, r'\nmetadata:\n  version: "\d+\.\d+"\n')
        self.assertIn("license: MIT", text)
        self.assertNotIn("OPENROUTER", text)

    def test_all_script_help_commands_are_dependency_free(self) -> None:
        modules = (
            check_completeness,
            check_consistency,
            generate_template,
            privacy_process_check,
            timeline_generator,
            validate_treatment_plan,
            validate_traceability,
        )
        for module in modules:
            help_text = module.build_parser().format_help()
            self.assertIn("usage:", help_text.lower(), module.__name__)


class StructureAndBoundsTests(unittest.TestCase):
    def test_malformed_enum_members_are_reported_without_crashing(self) -> None:
        for value in ([], {}, 1, None):
            document = load_asset("intended_use_handoff_template.json")
            document["intended_use"]["prohibited_uses"][0] = value
            codes = {issue.code for issue in _common.validate_document(document)}
            self.assertIn("SCHEMA_TYPE_STRING", codes)
            self.assertIn("PROHIBITED_USE_SET_CHANGED", codes)

    def test_parser_failures_are_minimized(self) -> None:
        cases = (
            ('{"nested":' + '[' * 2000 + '0' + ']' * 2000 + '}',
             "JSON_MAX_DEPTH_EXCEEDED"),
            ('{"number":' + '9' * 10000 + '}', "JSON_NUMBER_INVALID"),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            for content, code in cases:
                path.write_text(content, encoding="utf-8")
                with self.assertRaisesRegex(_common.ValidationError, code):
                    _common.read_json(path)

    def test_unknown_keys_and_document_types_are_not_echoed(self) -> None:
        document = load_asset("source_fact_manifest_template.json")
        marker = "SYNTHETIC-PRIVATE-KEY-OR-TYPE"
        document[marker] = True
        self.assertNotIn(marker, str(_common.validate_document(document)))
        document["document_type"] = marker
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "record.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            report = validate_treatment_plan.validate_target(str(path))
        self.assertEqual(report["status"], "fail")
        self.assertNotIn(marker, json.dumps(report))

    def test_datetime_requires_extended_calendar_format(self) -> None:
        for value in (
            "2026-W30-4T12:00:00+00:00", "20260723T12:00:00+00:00",
            "2026-07-23X12:00:00+00:00", "2026-07-23T12:00:00",
            "2026-07-23T12:00:00+00:99", "2026-07-23T12:00:00+24:00",
        ):
            self.assertIsNone(_common.parse_iso_datetime(value))
        for value in ("2026-07-23T12:00:00Z", "2026-07-23T12:00:00.123-07:00"):
            self.assertIsNotNone(_common.parse_iso_datetime(value))

    def test_blank_required_text_is_rejected(self) -> None:
        document = complete_synthetic_documents()["clinician_authored_intervention_record"]
        document["interventions"][0]["owner_role"] = "   "
        self.assertIn("SCHEMA_STRING_BLANK", {
            issue.code for issue in _common.validate_document(document)
        })

    def test_forward_slash_network_path_is_rejected(self) -> None:
        with self.assertRaisesRegex(_common.ValidationError, "NETWORK_SHARE_PATH_REJECTED"):
            _common.read_json("//host/share/record.json")

    def test_competing_output_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "result.json"
            real_link = _common.os.link

            def competing_writer(source, target):
                Path(target).write_text("existing output", encoding="utf-8")
                return real_link(source, target)

            with patch.object(_common.os, "link", side_effect=competing_writer):
                with self.assertRaisesRegex(_common.ValidationError, "OUTPUT_ALREADY_EXISTS"):
                    _common.atomic_write_json(destination, {"synthetic": True})
            self.assertEqual(destination.read_text(), "existing output")
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

    def test_template_is_structurally_valid_but_incomplete(self) -> None:
        document = load_asset("source_fact_manifest_template.json")
        self.assertEqual(_common.validate_document(document), [])
        documents = {
            document_type: load_asset(template_name)
            for document_type, (template_name, _) in _common.TEMPLATE_FILES.items()
        }
        report = check_completeness.check_completeness(documents)
        self.assertEqual(report["status"], "fail")
        codes = {issue["code"] for issue in report["issues"]}
        self.assertIn("SOURCE_FACTS_REQUIRED", codes)
        self.assertIn("CLINICIAN_SIGNOFF_PENDING", codes)

    def test_complete_synthetic_package_passes_all_checks(self) -> None:
        documents = complete_synthetic_documents()
        with tempfile.TemporaryDirectory() as directory:
            write_package(Path(directory), documents)
            structure = validate_treatment_plan.validate_target(directory)
        self.assertEqual(structure["status"], "pass", structure["issues"])
        for report in (
            validate_traceability.validate_traceability(documents),
            check_completeness.check_completeness(documents),
            privacy_process_check.check_privacy_process(documents),
            check_consistency.check_consistency(documents),
        ):
            self.assertEqual(report["status"], "pass", report["issues"])

    def test_unknown_field_fails_closed(self) -> None:
        document = load_asset("source_fact_manifest_template.json")
        document["unexpected"] = True
        codes = {issue.code for issue in _common.validate_document(document)}
        self.assertIn("SCHEMA_UNKNOWN_FIELD", codes)

    def test_duplicate_json_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text(
                '{"document_type":"source_fact_manifest",'
                '"document_type":"source_fact_manifest"}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                _common.ValidationError, "JSON_DUPLICATE_KEY"
            ):
                _common.read_json(path)

    def test_excessive_json_depth_is_rejected(self) -> None:
        nested: dict = {}
        cursor = nested
        for _ in range(_common.MAX_DEPTH + 2):
            cursor["nested"] = {}
            cursor = cursor["nested"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "deep.json"
            path.write_text(json.dumps(nested), encoding="utf-8")
            with self.assertRaisesRegex(
                _common.ValidationError, "JSON_MAX_DEPTH_EXCEEDED"
            ):
                _common.read_json(path)

    def test_url_input_path_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            _common.ValidationError, "NONLOCAL_OR_EMPTY_PATH"
        ):
            _common.read_json("https://example.invalid/record.json")

    def test_symlink_input_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.json"
            link = root / "link.json"
            target.write_text("{}", encoding="utf-8")
            link.symlink_to(target)
            with self.assertRaisesRegex(
                _common.ValidationError, "SYMLINK_INPUT_REJECTED"
            ):
                _common.read_json(link)


class WorkflowTests(unittest.TestCase):
    def test_schedule_rejects_mixed_subjects_and_reversed_dates(self) -> None:
        documents = complete_synthetic_documents()
        documents["source_fact_manifest"]["subject_ref"] = "SYNTHETIC-OTHER"
        report, schedule = timeline_generator.build_schedule(documents)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(schedule, {})
        documents = complete_synthetic_documents()
        documents["clinician_authored_intervention_record"]["interventions"][0]["end_date"] = "2026-07-01"
        report, schedule = timeline_generator.build_schedule(documents)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(schedule, {})

    def test_schedule_filters_require_full_calendar_dates(self) -> None:
        for value in ("20260723", "2026-W30-4"):
            with self.assertRaisesRegex(_common.ValidationError, "FROM_DATE_INVALID"):
                timeline_generator.build_schedule(complete_synthetic_documents(), from_date=value)

    def test_completeness_does_not_claim_handoff_authority(self) -> None:
        report = check_completeness.check_completeness(complete_synthetic_documents())
        self.assertTrue(report["documentation_declarations_complete"])
        self.assertFalse(report["handoff_authorized_by_script"])
        self.assertNotIn("ready_for_authorized_documentation_handoff", report)

    def test_generator_creates_six_blocked_templates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "package"
            report = generate_template.generate_package(
                str(destination),
                subject_ref="SYNTHETIC-CASE-XYZ",
                classification="synthetic",
            )
            self.assertEqual(report["status"], "pass")
            self.assertEqual(
                {path.name for path in destination.glob("*.json")},
                {value[1] for value in _common.TEMPLATE_FILES.values()},
            )
            loaded, _ = _common.load_package(destination)
            self.assertEqual(
                loaded["intended_use_handoff_record"]["release_gate"]["status"],
                "blocked",
            )

    def test_generator_requires_explicit_real_patient_acknowledgment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "package"
            with self.assertRaisesRegex(
                _common.ValidationError, "REAL_PATIENT_LOCAL_ACK_REQUIRED"
            ):
                generate_template.generate_package(
                    str(destination),
                    subject_ref="LOCAL-CASE-001",
                    classification="real_patient_minimum_necessary",
                )

    def test_traceability_fails_unknown_fact_without_echoing_content(self) -> None:
        documents = complete_synthetic_documents()
        secret_text = "SYNTHETIC-CONFIDENTIAL-CONTENT"
        documents["clinician_authored_intervention_record"]["interventions"][0][
            "clinician_authored_action"
        ] = secret_text
        documents["clinician_authored_intervention_record"]["interventions"][0][
            "source_fact_ids"
        ] = ["UNKNOWN-SYNTHETIC-FACT"]
        report = validate_traceability.validate_traceability(documents)
        self.assertEqual(report["status"], "fail")
        self.assertNotIn(secret_text, json.dumps(report))
        self.assertIn(
            "UNKNOWN_SOURCE_FACT_REFERENCE",
            {issue["code"] for issue in report["issues"]},
        )

    def test_timeline_uses_only_explicit_dates(self) -> None:
        documents = complete_synthetic_documents()
        report, schedule = timeline_generator.build_schedule(documents)
        self.assertEqual(report["status"], "pass", report["issues"])
        self.assertEqual(len(schedule["events"]), 7)
        self.assertFalse(schedule["dates_inferred"])
        self.assertFalse(schedule["recurrences_generated"])
        serialized = json.dumps(schedule)
        self.assertNotIn(
            documents["clinician_authored_intervention_record"][
                "interventions"
            ][0]["clinician_authored_action"],
            serialized,
        )

    def test_timeline_does_not_expand_frequency_text(self) -> None:
        documents = complete_synthetic_documents()
        monitoring = documents["goals_monitoring_checkpoint_record"][
            "monitoring_items"
        ][0]
        monitoring["next_due_date"] = None
        report, schedule = timeline_generator.build_schedule(documents)
        codes = {issue["code"] for issue in report["issues"]}
        self.assertIn(
            "FREQUENCY_TEXT_NOT_EXPANDED_WITHOUT_EXPLICIT_DATE", codes
        )
        event_types = {event["event_type"] for event in schedule["events"]}
        self.assertNotIn("monitoring_due_date_as_supplied", event_types)

    def test_consistency_rejects_reversed_supplied_dates(self) -> None:
        documents = complete_synthetic_documents()
        intervention = documents["clinician_authored_intervention_record"][
            "interventions"
        ][0]
        intervention["start_date"] = "2026-07-26"
        intervention["end_date"] = "2026-07-25"
        report = check_consistency.check_consistency(documents)
        self.assertIn(
            "INTERVENTION_DATE_ORDER_INVALID",
            {issue["code"] for issue in report["issues"]},
        )

    def test_patient_derived_package_requires_qualified_privacy_review(self) -> None:
        documents = complete_synthetic_documents()
        for document in documents.values():
            document["data_classification"] = "deidentified_qualified_review"
            document["subject_ref"] = "LOCAL-CASE-001"
        privacy = documents["intended_use_handoff_record"]["privacy_process"]
        privacy["data_classification"] = "deidentified_qualified_review"
        privacy["privacy_review_status"] = "pending"
        report = privacy_process_check.check_privacy_process(documents)
        self.assertIn(
            "QUALIFIED_PRIVACY_REVIEW_REQUIRED",
            {issue["code"] for issue in report["issues"]},
        )
        self.assertFalse(report["deidentification_determined"])


if __name__ == "__main__":
    unittest.main()
