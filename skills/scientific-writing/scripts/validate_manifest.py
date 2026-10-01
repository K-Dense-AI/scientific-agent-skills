"""Validate bounded manuscript and source manifests without network access."""

from __future__ import annotations

import argparse
import re
from typing import Any

from _common import (
    InputError,
    Issue,
    emit_report,
    is_nonempty_string,
    is_iso_date,
    is_placeholder,
    issue,
    read_json,
    require_list,
    require_object,
    run,
)

TOOL = "validate_manifest"
ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._-]{1,63}$")
EVIDENCE_ID_RE = re.compile(r"^E[0-9]{3,8}$")
SOURCE_TYPES = {
    "journal_article",
    "book",
    "chapter",
    "conference_paper",
    "dataset",
    "software",
    "preprint",
    "report",
    "policy",
    "guideline",
    "registry",
    "webpage",
    "other",
}
CONFIDENTIALITY = {"public", "restricted", "sensitive", "proprietary"}
DRAFT_STATUSES = {"draft", "internal_review", "submission_candidate", "submitted"}
STATEMENT_STATUSES = {"not_applicable", "missing", "draft", "verified"}
MANUSCRIPT_FIELDS = {
    "schema_version",
    "document_id",
    "study_design",
    "draft_status",
    "submission_ready",
    "registries",
    "reporting_guidelines",
    "human_verification",
    "confidentiality_review",
    "required_statements",
}
SOURCE_FIELDS = {
    "evidence_id",
    "source_type",
    "title",
    "authors",
    "year",
    "identifiers",
    "locator",
    "confidentiality",
    "verification",
}
IDENTIFIER_FIELDS = {"doi", "pmid", "pmcid", "isbn", "url"}
VERIFICATION_FIELDS = {"status", "source_opened", "verified_by", "verified_on"}


def _check_unknown_fields(
    obj: dict[str, Any],
    allowed: set[str],
    *,
    location: str,
    issues: list[Issue],
) -> None:
    for key in sorted(set(obj) - allowed):
        issues.append(
            issue("error", "UNKNOWN_SCHEMA_FIELD", location=location, item_id=key)
        )


def _missing_or_placeholder(
    obj: dict[str, Any],
    key: str,
    *,
    location: str,
    issues: list[Issue],
) -> None:
    value = obj.get(key)
    if not is_nonempty_string(value) or is_placeholder(value):
        issues.append(
            issue("error", "MISSING_VERIFIED_VALUE", location=location, item_id=key)
        )


def _validate_human_gate(
    value: Any,
    *,
    location: str,
    submission_ready: bool,
    issues: list[Issue],
) -> None:
    gate = require_object(value, location)
    completed = gate.get("completed")
    if not isinstance(completed, bool):
        issues.append(issue("error", "GATE_COMPLETED_NOT_BOOLEAN", location=location))
        return
    if completed:
        _missing_or_placeholder(gate, "verified_by", location=location, issues=issues)
        verified_on = gate.get("verified_on")
        if not is_iso_date(verified_on):
            issues.append(
                issue("error", "INVALID_VERIFICATION_DATE", location=location)
            )
    elif submission_ready:
        issues.append(issue("error", "SUBMISSION_GATE_INCOMPLETE", location=location))


def validate_manuscript_manifest(data: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    _check_unknown_fields(
        data,
        MANUSCRIPT_FIELDS,
        location="root",
        issues=issues,
    )
    if data.get("schema_version") != "1.0":
        issues.append(
            issue("error", "UNSUPPORTED_SCHEMA_VERSION", location="schema_version")
        )

    document_id = data.get("document_id")
    if not isinstance(document_id, str) or not ID_RE.fullmatch(document_id):
        issues.append(issue("error", "INVALID_DOCUMENT_ID", location="document_id"))
    _missing_or_placeholder(data, "study_design", location="root", issues=issues)

    draft_status = data.get("draft_status")
    if draft_status not in DRAFT_STATUSES:
        issues.append(issue("error", "INVALID_DRAFT_STATUS", location="draft_status"))
    submission_ready = data.get("submission_ready")
    if not isinstance(submission_ready, bool):
        issues.append(
            issue("error", "SUBMISSION_READY_NOT_BOOLEAN", location="submission_ready")
        )
        submission_ready = False

    paths = require_object(data.get("registries"), "registries")
    for key in (
        "source_manifest",
        "claim_evidence",
        "consistency_manifest",
        "authorship_manifest",
        "reporting_coverage",
    ):
        _missing_or_placeholder(paths, key, location="registries", issues=issues)

    guidelines = require_list(data.get("reporting_guidelines"), "reporting_guidelines")
    if submission_ready and not guidelines:
        issues.append(
            issue(
                "error",
                "NO_REPORTING_GUIDELINE_RECORDED",
                location="reporting_guidelines",
            )
        )
    for index, guideline_id in enumerate(guidelines):
        if not isinstance(guideline_id, str) or not ID_RE.fullmatch(guideline_id):
            issues.append(
                issue(
                    "error",
                    "INVALID_GUIDELINE_ID",
                    location=f"reporting_guidelines[{index}]",
                )
            )

    _validate_human_gate(
        data.get("human_verification"),
        location="human_verification",
        submission_ready=bool(submission_ready),
        issues=issues,
    )
    confidentiality = require_object(
        data.get("confidentiality_review"), "confidentiality_review"
    )
    _validate_human_gate(
        confidentiality,
        location="confidentiality_review",
        submission_ready=bool(submission_ready),
        issues=issues,
    )
    if not isinstance(confidentiality.get("policy_checked"), bool):
        issues.append(
            issue(
                "error", "POLICY_CHECKED_NOT_BOOLEAN", location="confidentiality_review"
            )
        )
    elif submission_ready and not confidentiality["policy_checked"]:
        issues.append(
            issue(
                "error", "POLICY_REVIEW_INCOMPLETE", location="confidentiality_review"
            )
        )
    if not isinstance(confidentiality.get("external_services_authorized"), bool):
        issues.append(
            issue(
                "error",
                "EXTERNAL_AUTHORIZATION_NOT_BOOLEAN",
                location="confidentiality_review",
            )
        )

    statements = require_object(data.get("required_statements"), "required_statements")
    for key in (
        "ethics",
        "consent",
        "funding",
        "conflicts",
        "data_availability",
        "code_availability",
        "author_contributions",
        "ai_disclosure",
    ):
        status = statements.get(key)
        if status not in STATEMENT_STATUSES:
            issues.append(issue("error", "INVALID_STATEMENT_STATUS", location=key))
        elif submission_ready and status in {"missing", "draft"}:
            issues.append(issue("error", "UNVERIFIED_REQUIRED_STATEMENT", location=key))

    if submission_ready and draft_status not in {"submission_candidate", "submitted"}:
        issues.append(issue("error", "READY_STATUS_MISMATCH", location="draft_status"))
    return issues


def validate_source_manifest(
    data: dict[str, Any],
    *,
    require_verified: bool,
) -> list[Issue]:
    issues: list[Issue] = []
    _check_unknown_fields(
        data,
        {"schema_version", "sources"},
        location="root",
        issues=issues,
    )
    if data.get("schema_version") != "1.0":
        issues.append(
            issue("error", "UNSUPPORTED_SCHEMA_VERSION", location="schema_version")
        )
    sources = require_list(data.get("sources"), "sources")
    seen_ids: set[str] = set()
    for index, raw_source in enumerate(sources):
        location = f"sources[{index}]"
        source = require_object(raw_source, location)
        _check_unknown_fields(
            source,
            SOURCE_FIELDS,
            location=location,
            issues=issues,
        )
        evidence_id = source.get("evidence_id")
        if not isinstance(evidence_id, str) or not EVIDENCE_ID_RE.fullmatch(
            evidence_id
        ):
            issues.append(issue("error", "INVALID_EVIDENCE_ID", location=location))
            evidence_id = None
        elif evidence_id in seen_ids:
            issues.append(
                issue(
                    "error",
                    "DUPLICATE_EVIDENCE_ID",
                    location=location,
                    item_id=evidence_id,
                )
            )
        else:
            seen_ids.add(evidence_id)

        if source.get("source_type") not in SOURCE_TYPES:
            issues.append(
                issue(
                    "error",
                    "INVALID_SOURCE_TYPE",
                    location=location,
                    item_id=evidence_id,
                )
            )
        _missing_or_placeholder(source, "title", location=location, issues=issues)
        authors = require_list(source.get("authors"), f"{location}.authors")
        for author in authors:
            if not is_nonempty_string(author) or is_placeholder(author):
                issues.append(
                    issue(
                        "error",
                        "INVALID_SOURCE_AUTHOR",
                        location=location,
                        item_id=evidence_id,
                    )
                )

        year = source.get("year")
        if year is not None and (
            not isinstance(year, int)
            or isinstance(year, bool)
            or not 1000 <= year <= 2100
        ):
            issues.append(
                issue(
                    "error",
                    "INVALID_SOURCE_YEAR",
                    location=location,
                    item_id=evidence_id,
                )
            )

        identifiers = require_object(
            source.get("identifiers"), f"{location}.identifiers"
        )
        _check_unknown_fields(
            identifiers,
            IDENTIFIER_FIELDS,
            location=f"{location}.identifiers",
            issues=issues,
        )
        if not any(is_nonempty_string(value) for value in identifiers.values()):
            issues.append(
                issue(
                    "warning",
                    "NO_SOURCE_IDENTIFIER",
                    location=location,
                    item_id=evidence_id,
                )
            )
        if not is_nonempty_string(source.get("locator")) or is_placeholder(
            source.get("locator")
        ):
            issues.append(
                issue(
                    "error",
                    "MISSING_SOURCE_LOCATOR",
                    location=location,
                    item_id=evidence_id,
                )
            )

        confidentiality = source.get("confidentiality")
        if confidentiality not in CONFIDENTIALITY:
            issues.append(
                issue(
                    "error",
                    "INVALID_CONFIDENTIALITY_CLASS",
                    location=location,
                    item_id=evidence_id,
                )
            )

        verification = require_object(
            source.get("verification"), f"{location}.verification"
        )
        _check_unknown_fields(
            verification,
            VERIFICATION_FIELDS,
            location=f"{location}.verification",
            issues=issues,
        )
        status = verification.get("status")
        if status not in {"unverified", "verified", "rejected"}:
            issues.append(
                issue(
                    "error",
                    "INVALID_VERIFICATION_STATUS",
                    location=location,
                    item_id=evidence_id,
                )
            )
        if status == "verified":
            _missing_or_placeholder(
                verification,
                "verified_by",
                location=location,
                issues=issues,
            )
            verified_on = verification.get("verified_on")
            if not is_iso_date(verified_on):
                issues.append(
                    issue(
                        "error",
                        "INVALID_VERIFICATION_DATE",
                        location=location,
                        item_id=evidence_id,
                    )
                )
            if verification.get("source_opened") is not True:
                issues.append(
                    issue(
                        "error",
                        "SOURCE_NOT_OPENED_FOR_VERIFICATION",
                        location=location,
                        item_id=evidence_id,
                    )
                )
        elif require_verified:
            issues.append(
                issue(
                    "error",
                    "SOURCE_NOT_VERIFIED",
                    location=location,
                    item_id=evidence_id,
                )
            )
    return issues


def detect_kind(data: dict[str, Any]) -> str:
    if "sources" in data:
        return "source"
    if "document_id" in data:
        return "manuscript"
    raise InputError("unable to infer manifest kind")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a local JSON manuscript or source manifest. "
            "No network calls or identifier resolution are performed."
        )
    )
    parser.add_argument("manifest", help="UTF-8 JSON manifest (maximum 5 MB)")
    parser.add_argument(
        "--kind",
        choices=("auto", "manuscript", "source"),
        default="auto",
        help="manifest schema to validate (default: infer from keys)",
    )
    parser.add_argument(
        "--require-verified",
        action="store_true",
        help="for source manifests, fail if any source is not verified",
    )
    return parser


def cli() -> int:
    args = build_parser().parse_args()
    data = require_object(read_json(args.manifest))
    kind = detect_kind(data) if args.kind == "auto" else args.kind
    if kind == "manuscript":
        issues = validate_manuscript_manifest(data)
        records = 1
    else:
        issues = validate_source_manifest(data, require_verified=args.require_verified)
        records = len(require_list(data.get("sources"), "sources"))
    return emit_report(TOOL, issues, summary={"kind": kind, "records": records})


if __name__ == "__main__":
    run(TOOL, cli)
