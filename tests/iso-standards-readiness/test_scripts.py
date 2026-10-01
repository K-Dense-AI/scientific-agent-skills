from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2] / "skills" / "iso-standards-readiness"
SCRIPTS = ROOT / "scripts"
CLI_NAMES = (
    "gap_analyzer.py",
    "validate_scope_intake.py",
    "audit_document_records.py",
    "check_capa.py",
    "check_traceability.py",
    "check_qmsr_transition.py",
    "validate_evidence_manifest.py",
    "check_supplier_controls.py",
)


def source(identifier: str = "SRC-1") -> dict[str, str]:
    return {
        "id": identifier,
        "title": f"Official source {identifier}",
        "version_or_date": "2026-07-23",
        "url": "https://www.fda.gov/medical-devices",
        "accessed": "2026-07-23",
    }


def evidence(identifier: str = "EV-1") -> list[dict[str, str]]:
    return [
        {
            "id": identifier,
            "type": "record",
            "location": f"records/{identifier}.md",
            "revision_or_date": "2026-07-22",
        }
    ]


def approval() -> dict[str, str]:
    return {"status": "approved", "by": "Authorized QA", "date": "2026-07-23"}


def controlled(
    *,
    identifier: str,
    status: str = "approved",
    source_id: str = "SRC-1",
) -> dict[str, Any]:
    return {
        "owner": "Accountable QA",
        "status": status,
        "evidence": evidence(f"EV-{identifier}"),
        "approval": approval(),
        "source_refs": [source(source_id)],
    }


def metadata(identifier_key: str, identifier: str) -> dict[str, Any]:
    return {
        identifier_key: identifier,
        "review_date": "2026-07-23",
        **controlled(identifier=f"META-{identifier}"),
    }


def scope_data() -> dict[str, Any]:
    site = {
        "id": "SITE-1",
        "name": "Example Site",
        "address": "1 Controlled Way",
        "activities": ["design-and-development"],
        **controlled(identifier="SITE-1"),
    }
    product = {
        "id": "PROD-1",
        "family": "Example device family",
        "intended_use": "Controlled intended use reference IU-1",
        "classification_or_rationale": "Decision record CLASS-1",
        "market_ids": ["US"],
        **controlled(identifier="PROD-1"),
    }
    market = {
        "id": "US",
        "jurisdiction": "United States",
        "applicability": "applicable",
        "decision_rationale": "Authorized decision APP-US-1",
        **controlled(identifier="MARKET-US"),
    }
    return {
        "metadata": metadata("intake_id", "INTAKE-1"),
        "organization": {
            "legal_name": "Example Medical Devices Inc.",
            "declared_lifecycle_role": "Declared manufacturer role",
            "authorized_management_representative": "Management Representative",
            "raqa_owner": "RAQA Director",
            "applicability_decision_owner": "Regulatory Counsel",
        },
        "scope": {
            "lifecycle_activities": ["design-and-development"],
            "sites": [site],
            "products": [product],
            "markets": [market],
            "outsourced_processes": [],
        },
    }


def document_data() -> dict[str, Any]:
    document = {
        "id": "SOP-1",
        "title": "Controlled Process",
        "document_type": "procedure",
        "revision": "2",
        "status": "effective",
        "effective_date": "2026-07-20",
        "change_summary": "Approved change CHG-1",
        "training_impact": "Training record TR-1",
        "owner": "Document Owner",
        "evidence": evidence("DOC-1"),
        "approval": approval(),
        "source_refs": [source()],
    }
    record = {
        "id": "REC-1",
        "record_type": "Process record",
        "status": "active",
        "retention_period": "Per approved schedule RET-1",
        "retention_basis": "Authorized legal and product review RET-BASIS-1",
        "storage_and_integrity_controls": "Validated repository controls VAL-1",
        "retrieval_method": "Controlled index and access",
        "disposition_method": "Authorized destruction record",
        "owner": "Record Owner",
        "evidence": evidence("REC-1"),
        "approval": approval(),
        "source_refs": [source()],
    }
    external = {
        "id": "EXT-1",
        "title": "Official current source",
        "publisher": "FDA",
        "version_or_date": "2026-07-23",
        "status": "current",
        "last_currency_review": "2026-07-23",
        "owner": "Source Owner",
        "evidence": evidence("EXT-1"),
        "approval": approval(),
        "source_refs": [source()],
    }
    return {
        "metadata": metadata("register_id", "DOC-REG-1"),
        "documents": [document],
        "records": [record],
        "external_sources": [external],
    }


def capa_data() -> dict[str, Any]:
    capa = {
        "id": "CAPA-1",
        "owner": "CAPA Owner",
        "status": "closed",
        "source_event": "NCR-1",
        "problem_statement": "Defined nonconformity",
        "scope": "Products and processes reviewed",
        "correction_or_containment": "Containment record CONT-1",
        "evidence": evidence("CAPA-1"),
        "source_refs": [source()],
        "approval": approval(),
        "risk_assessment": {
            "patient_and_user_impact": "Impact assessment RISK-1",
            "product_and_process_impact": "Product/process assessment RISK-2",
            "reportability_review": "Authorized decision REG-1",
            "decision": "control-and-monitor",
            "decision_rationale": "Approved rationale",
            "owner": "Risk Owner",
            "evidence": evidence("RISK-1"),
            "approval": approval(),
        },
        "investigation": {
            "method": "Evidence-driven investigation method",
            "root_cause_or_justified_conclusion": "Supported conclusion",
            "systemic_extent_review": "Similar products and processes reviewed",
            "owner": "Investigation Owner",
            "evidence": evidence("INV-1"),
            "approval": approval(),
        },
        "actions": [
            {
                "id": "ACTION-1",
                "description": "Action tied to supported cause",
                "owner": "Action Owner",
                "due_date": "2026-06-01",
                "implemented_date": "2026-05-20",
                "evidence": evidence("ACTION-1"),
                "approval": approval(),
            }
        ],
        "change_control_refs": ["CHG-1"],
        "effectiveness": {
            "plan": "Review defined outcome after implementation",
            "objective_acceptance_criteria": "Zero recurrence in approved sample",
            "baseline": "Two events in prior approved window",
            "sample_or_observation_window": "Three approved production lots",
            "due_date": "2026-07-01",
            "owner": "Effectiveness Owner",
            "independent_reviewer": "Independent QA Reviewer",
            "result": "effective",
            "conclusion": "Criteria met in evidence EFF-1",
            "review_date": "2026-07-02",
            "evidence": evidence("EFF-1"),
            "approval": approval(),
        },
        "closure_date": "2026-07-03",
        "closure_summary": "All approved closure gates completed",
    }
    return {"metadata": metadata("register_id", "CAPA-REG-1"), "capas": [capa]}


def traceability_data() -> dict[str, Any]:
    definitions = (
        ("IU-1", "intended-use"),
        ("HZ-1", "hazard"),
        ("RE-1", "risk-evaluation"),
        ("RC-1", "risk-control"),
        ("DI-1", "design-input"),
        ("DO-1", "design-output"),
        ("VER-1", "verification"),
        ("VAL-1", "validation"),
        ("PC-1", "production-control"),
        ("PMS-1", "postmarket-signal"),
        ("CHG-1", "change-control"),
    )
    artifacts = [
        {
            "id": identifier,
            "type": artifact_type,
            "title": f"Controlled {artifact_type}",
            **controlled(identifier=identifier, status="verified"),
        }
        for identifier, artifact_type in definitions
    ]
    row = {
        "id": "TRACE-1",
        "product_id": "PROD-1",
        "owner": "Traceability Owner",
        "status": "verified",
        "linkage_rationale": "Approved end-to-end linkage",
        "links": {
            "intended_use": ["IU-1"],
            "hazard_or_signal": ["HZ-1"],
            "risk_evaluation": ["RE-1"],
            "risk_control": ["RC-1"],
            "design_input": ["DI-1"],
            "design_output": ["DO-1"],
            "verification": ["VER-1"],
            "validation": ["VAL-1"],
            "production_control": ["PC-1"],
            "postmarket_source": ["PMS-1"],
        },
        "change_control_refs": ["CHG-1"],
        "open_gaps": [],
        "evidence": evidence("TRACE-1"),
        "approval": approval(),
        "source_refs": [source()],
    }
    return {
        "metadata": metadata("matrix_id", "TRACE-MATRIX-1"),
        "artifacts": artifacts,
        "rows": [row],
    }


def qmsr_data() -> dict[str, Any]:
    from_catalog = (
        "qmsr-source-basis",
        "applicability-owner",
        "fda-supplemental-provisions",
        "legacy-qsr-reference-disposition",
        "pre-effective-date-record-review",
        "inspection-accessible-records",
        "inspection-process-training",
        "qsit-retirement",
        "complaint-and-servicing-records",
        "labeling-and-packaging-controls",
        "software-validation-impact",
        "supplier-and-outsourced-process-controls",
        "certificate-claims-review",
        "change-control-approval",
    )
    items = [
        {
            "id": identifier,
            "owner": "QMSR Owner",
            "status": "evidence-ready",
            "assessment": f"Approved assessment for {identifier}",
            "evidence": evidence(f"Q-{index}"),
            "approval": approval(),
            "source_refs": [source(f"QSRC-{index}")],
        }
        for index, identifier in enumerate(from_catalog)
    ]
    return {
        "metadata": metadata("checklist_id", "QMSR-1"),
        "qmsr_basis": {
            "as_of": "2026-07-23",
            "effective_date": "2026-02-02",
            "current_part_820_title": "Quality Management System Regulation",
            "inspection_compliance_program": "7382.850",
            "owner": "Regulatory Owner",
            "evidence": evidence("QBASIS"),
            "approval": approval(),
            "source_refs": [source("FDA"), source("ECFR"), source("CP")],
        },
        "items": items,
        "attestations": {
            "iso_certificate_not_treated_as_fda_compliance": True,
            "checklist_not_treated_as_compliance_determination": True,
            "legacy_qsr_clause_map_not_used_as_current_requirements": True,
            "applicability_decisions_owned_by_authorized_humans": True,
            "owner": "Regulatory Owner",
            "evidence": evidence("ATTEST"),
            "approval": approval(),
        },
    }


def manifest_data(
    local_path: str = "evidence.md",
    digest: str | None = None,
    domain: str = "document-and-record-control",
) -> dict[str, Any]:
    entry = {
        "id": "MAN-ENTRY-1",
        "domain": domain,
        "title": "Controlled document evidence",
        "owner": "Evidence Owner",
        "status": "verified",
        "revision_or_date": "2026-07-23",
        "classification": "internal",
        "local_path": local_path,
        "evidence": evidence("MAN-1"),
        "approval": approval(),
        "source_refs": [source()],
    }
    if digest is not None:
        entry["sha256"] = digest
    return {
        "metadata": metadata("manifest_id", "MANIFEST-1"),
        "audit_context": {
            "purpose": "internal-audit",
            "scope": "Site, product, process, and period defined",
            "sampling_plan": "Risk-based approved sample plan",
            "limitations": "Limited to supplied controlled export",
            "owner": "Audit Owner",
            "evidence": evidence("CTX-1"),
            "approval": approval(),
            "source_refs": [source()],
        },
        "expected_domains": [domain],
        "entries": [entry],
        "open_gaps": [],
    }


def supplier_data() -> dict[str, Any]:
    control_names = (
        "selection_and_initial_evaluation",
        "purchasing_requirements",
        "change_notification",
        "incoming_or_acceptance_verification",
        "performance_monitoring",
        "reevaluation",
        "nonconformity_and_capa",
        "quality_agreement",
        "subtier_controls",
        "business_continuity",
    )
    controls = {
        name: {
            "status": "verified",
            "owner": "Supplier Quality",
            "method": f"Approved risk-based method for {name}",
            "evidence": evidence(f"SUP-{index}"),
            "approval": approval(),
            "source_refs": [source(f"SSRC-{index}")],
        }
        for index, name in enumerate(control_names)
    }
    supplier = {
        "id": "SUPPLIER-1",
        "name": "Example Supplier Inc.",
        "owner": "Supplier Owner",
        "status": "approved",
        "criticality": "critical",
        "product_service_or_process": "Critical outsourced process",
        "risk_rationale": "Approved criticality assessment",
        "next_review_date": "2027-07-23",
        "evidence": evidence("SUPPLIER-1"),
        "approval": approval(),
        "source_refs": [source()],
        **controls,
    }
    return {
        "metadata": metadata("register_id", "SUP-REG-1"),
        "control_methodology": {
            "risk_method": "Approved supplier criticality method",
            "approval_authority": "Supplier Quality Director",
            "monitoring_and_escalation": "Metrics, changes, CAPA, and escalation",
            "owner": "Supplier Quality",
            "evidence": evidence("METH-1"),
            "approval": approval(),
            "source_refs": [source()],
        },
        "suppliers": [supplier],
    }


class CLITests(unittest.TestCase):
    maxDiff = None

    def run_cli(
        self,
        script: str,
        *arguments: str,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [sys.executable, str(SCRIPTS / script), *arguments],
            cwd=str(cwd or ROOT),
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )

    def write_json(self, directory: Path, name: str, data: Any) -> Path:
        path = directory / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def assert_valid(self, script: str, data: dict[str, Any]) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_json(Path(temp), "input.json", data)
            result = self.run_cli(script, str(path))
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads(result.stdout)
            self.assertEqual(report["result"], "complete-for-human-review")
            self.assertEqual(report["findings"], [])
            self.assertIn("does not establish", report["disclaimer"])

    def test_all_help_commands(self) -> None:
        for script in CLI_NAMES:
            with self.subTest(script=script):
                result = self.run_cli(script, "--help")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage:", result.stdout)

    def test_valid_scope(self) -> None:
        self.assert_valid("validate_scope_intake.py", scope_data())

    def test_valid_document_register(self) -> None:
        self.assert_valid("audit_document_records.py", document_data())

    def test_valid_capa(self) -> None:
        self.assert_valid("check_capa.py", capa_data())

    def test_valid_traceability(self) -> None:
        self.assert_valid("check_traceability.py", traceability_data())

    def test_valid_qmsr(self) -> None:
        self.assert_valid("check_qmsr_transition.py", qmsr_data())

    def test_valid_supplier_controls(self) -> None:
        self.assert_valid("check_supplier_controls.py", supplier_data())

    def test_manifest_and_gap_analyzer(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            content = "# Controlled synthetic evidence\n"
            (directory / "evidence.md").write_text(content, encoding="utf-8")
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            manifest = self.write_json(
                directory,
                "manifest.json",
                manifest_data(digest=digest),
            )
            for script in ("validate_evidence_manifest.py", "gap_analyzer.py"):
                with self.subTest(script=script):
                    result = self.run_cli(
                        script,
                        str(manifest),
                        "--base-dir",
                        str(directory),
                        "--verify-files",
                    )
                    self.assertEqual(
                        result.returncode,
                        0,
                        result.stderr + result.stdout,
                    )
                    report = json.loads(result.stdout)
                    self.assertNotIn("compliance_percentage", result.stdout)
                    self.assertEqual(report["findings"], [])
            gap_report = json.loads(
                self.run_cli("gap_analyzer.py", str(manifest)).stdout
            )
            self.assertIn("domains", gap_report)
            self.assertIn("no filename/keyword scoring", gap_report["method"])

    def test_closed_capa_without_effectiveness_fails(self) -> None:
        data = capa_data()
        data["capas"][0]["effectiveness"]["result"] = "pending"
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_json(Path(temp), "capa.json", data)
            result = self.run_cli("check_capa.py", str(path))
            self.assertEqual(result.returncode, 1)
            report = json.loads(result.stdout)
            self.assertTrue(
                any(item["code"] == "CLOSURE_BLOCKED" for item in report["findings"])
            )

    def test_undetermined_applicability_fails(self) -> None:
        data = scope_data()
        data["scope"]["markets"][0]["applicability"] = "undetermined"
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_json(Path(temp), "scope.json", data)
            result = self.run_cli("validate_scope_intake.py", str(path))
            self.assertEqual(result.returncode, 1)
            self.assertIn("HUMAN_DECISION_REQUIRED", result.stdout)

    def test_duplicate_json_key_is_input_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "duplicate.json"
            path.write_text('{"metadata": {}, "metadata": {}}', encoding="utf-8")
            result = self.run_cli("gap_analyzer.py", str(path))
            self.assertEqual(result.returncode, 2)
            self.assertIn("duplicate JSON key", result.stderr)

    def test_nonfinite_and_overflow_json_numbers_are_input_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "nonfinite.json"
            for number in ("NaN", "Infinity", "-Infinity", "1e999", "-1e999"):
                with self.subTest(number=number):
                    path.write_text('{"nested": [{"value": ' + number + ' }]}', encoding="utf-8")
                    result = self.run_cli("gap_analyzer.py", str(path))
                    self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                    self.assertIn("non-finite JSON number", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)

    def test_dates_require_calendar_format(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            for invalid in ("20260723", "2026-W30-4", "2026-02-30"):
                with self.subTest(date=invalid):
                    data = scope_data()
                    data["metadata"]["review_date"] = invalid
                    path = self.write_json(Path(temp), "input.json", data)
                    result = self.run_cli("validate_scope_intake.py", str(path))
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn("DATE_INVALID", result.stdout)

    def test_qmsr_organization_review_date_is_not_the_skill_release_date(self) -> None:
        data = qmsr_data()
        data["qmsr_basis"]["as_of"] = "2026-09-30"
        self.assert_valid("check_qmsr_transition.py", data)

    def test_malformed_gap_entry_produces_findings_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            for key, value in (("domain", []), ("domain", {}), ("status", {})):
                with self.subTest(key=key, value=value):
                    data = manifest_data()
                    data["entries"][0][key] = value
                    path = self.write_json(Path(temp), "input.json", data)
                    result = self.run_cli("gap_analyzer.py", str(path))
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn("CHOICE_INVALID", result.stdout)
                    self.assertNotIn("Traceback", result.stderr)

    def test_gap_domain_does_not_call_malformed_evidence_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            for key, value in (("evidence", [{}]), ("source_refs", [{}]), ("approval", {"status": "approved"})):
                with self.subTest(field=key):
                    data = manifest_data()
                    data["entries"][0][key] = value
                    path = self.write_json(Path(temp), "input.json", data)
                    result = self.run_cli("gap_analyzer.py", str(path))
                    self.assertEqual(result.returncode, 1, result.stderr)
                    report = json.loads(result.stdout)
                    domain = next(row for row in report["domains"] if row["domain"] == "document-and-record-control")
                    self.assertEqual(domain["status"], "evidence-incomplete")

    def test_gap_domain_hash_mismatch_blocks_evidence_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / "evidence.md").write_text("Changed local evidence", encoding="utf-8")
            path = self.write_json(directory, "input.json", manifest_data(digest="0" * 64))
            result = self.run_cli("gap_analyzer.py", str(path), "--base-dir", str(directory), "--verify-files")
            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            self.assertTrue(any(row["code"] == "HASH_MISMATCH" for row in report["findings"]))
            domain = next(row for row in report["domains"] if row["domain"] == "document-and-record-control")
            self.assertEqual(domain["status"], "evidence-incomplete")

    def test_output_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_json(Path(temp), "scope.json", scope_data())
            first = self.run_cli("validate_scope_intake.py", str(path))
            second = self.run_cli("validate_scope_intake.py", str(path))
            self.assertEqual(first.returncode, 0)
            self.assertEqual(first.stdout, second.stdout)

    def test_evidence_path_traversal_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            manifest = self.write_json(
                directory,
                "manifest.json",
                manifest_data(local_path="../outside.md"),
            )
            result = self.run_cli(
                "validate_evidence_manifest.py",
                str(manifest),
                "--base-dir",
                str(directory),
                "--verify-files",
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("must be relative and contained", result.stderr)

    def test_refuses_overwrite_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            input_path = self.write_json(directory, "scope.json", scope_data())
            output_path = directory / "report.json"
            output_path.write_text("existing", encoding="utf-8")
            result = self.run_cli(
                "validate_scope_intake.py",
                str(input_path),
                "--output",
                str(output_path),
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(output_path.read_text(encoding="utf-8"), "existing")

    def test_distributed_json_templates_fail_closed(self) -> None:
        cases = {
            "scope-intake-template.json": "validate_scope_intake.py",
            "document-register-template.json": "audit_document_records.py",
            "capa-record-template.json": "check_capa.py",
            "traceability-matrix-template.json": "check_traceability.py",
            "qmsr-transition-template.json": "check_qmsr_transition.py",
            "evidence-manifest-template.json": "validate_evidence_manifest.py",
            "supplier-controls-template.json": "check_supplier_controls.py",
        }
        for template, script in cases.items():
            with self.subTest(template=template):
                result = self.run_cli(
                    script,
                    str(ROOT / "assets" / "templates" / template),
                )
                self.assertEqual(result.returncode, 1, result.stderr + result.stdout)
                report = json.loads(result.stdout)
                self.assertEqual(report["result"], "gaps-found")

    def test_standard_specific_templates_fail_closed(self) -> None:
        cases = {
            "scope-intake-template.json": "iso-13485",
            "laboratory-scope-intake-template.json": "iso-17025",
            "medical-laboratory-scope-intake-template.json": "iso-15189",
        }
        for template, standard in cases.items():
            with self.subTest(template=template):
                result = self.run_cli(
                    "validate_scope_intake.py",
                    str(ROOT / "assets" / "templates" / template),
                    "--standard",
                    standard,
                )
                self.assertEqual(result.returncode, 1, result.stderr + result.stdout)
                report = json.loads(result.stdout)
                self.assertEqual(report["result"], "gaps-found")
                self.assertEqual(report["standard"], standard)

    def test_unknown_standard_is_refused(self) -> None:
        for script in (
            "validate_scope_intake.py",
            "validate_evidence_manifest.py",
            "gap_analyzer.py",
        ):
            with self.subTest(script=script):
                with tempfile.TemporaryDirectory() as temp:
                    path = self.write_json(Path(temp), "input.json", manifest_data())
                    result = self.run_cli(script, str(path), "--standard", "iso-99999")
                    self.assertEqual(result.returncode, 2, result.stdout)
                    self.assertIn("invalid choice", result.stderr)

    def test_laboratory_profile_uses_its_own_domains(self) -> None:
        data = manifest_data(domain="metrological-traceability")
        data["audit_context"]["purpose"] = "accreditation-assessment-readiness"
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_json(Path(temp), "manifest.json", data)
            result = self.run_cli("gap_analyzer.py", str(path), "--standard", "iso-17025")
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads(result.stdout)
            self.assertEqual(report["standard"], "iso-17025")
            domains = {row["domain"]: row["status"] for row in report["domains"]}
            self.assertEqual(
                domains["metrological-traceability"],
                "evidence-present-for-human-review",
            )
            self.assertIn("reporting-and-decision-rules", domains)
            self.assertNotIn("postmarket-and-vigilance", domains)

    def test_device_domain_is_refused_under_laboratory_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_json(Path(temp), "manifest.json", manifest_data())
            result = self.run_cli(
                "validate_evidence_manifest.py",
                str(path),
                "--standard",
                "iso-15189",
            )
            self.assertEqual(result.returncode, 1)
            report = json.loads(result.stdout)
            codes = {item["code"] for item in report["findings"]}
            self.assertIn("CHOICE_INVALID", codes)
            self.assertIn("VALUE_UNKNOWN", codes)

if __name__ == "__main__":
    unittest.main()
