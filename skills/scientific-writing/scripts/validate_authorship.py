"""Validate human authorship, CRediT roles, accountability, and AI disclosure."""

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

TOOL = "validate_authorship"
AUTHOR_ID_RE = re.compile(r"^A[0-9]{3,8}$")
CONTRIBUTOR_ID_RE = re.compile(r"^K[0-9]{3,8}$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
CREDIT_ROLES = {
    "conceptualization",
    "data curation",
    "formal analysis",
    "funding acquisition",
    "investigation",
    "methodology",
    "project administration",
    "resources",
    "software",
    "supervision",
    "validation",
    "visualization",
    "writing – original draft",
    "writing – review & editing",
}
AUTHORSHIP_CRITERIA = {
    "substantial_contribution",
    "drafted_or_critically_revised",
    "final_approval",
    "accountable_for_work",
}
DISCLOSURE_LOCATIONS = {"cover_letter", "acknowledgments", "methods", "other"}
MATERIAL_CLASSES = {
    "none",
    "public_text",
    "unpublished_manuscript",
    "peer_review_material",
    "source_documents",
    "sensitive_data",
    "phi",
    "proprietary_content",
}
RESTRICTED_MATERIAL_CLASSES = MATERIAL_CLASSES - {"none", "public_text"}


def _validate_roles(
    roles_value: Any,
    *,
    item_id: str,
    issues: list[Issue],
) -> None:
    roles = require_list(roles_value, f"{item_id}.credit_roles")
    if not roles:
        issues.append(issue("error", "NO_CREDIT_ROLE", item_id=item_id))
    normalized: set[str] = set()
    for role in roles:
        if not isinstance(role, str) or role.casefold() not in CREDIT_ROLES:
            issues.append(issue("error", "INVALID_CREDIT_ROLE", item_id=item_id))
        elif role.casefold() in normalized:
            issues.append(issue("error", "DUPLICATE_CREDIT_ROLE", item_id=item_id))
        else:
            normalized.add(role.casefold())


def validate_people(data: dict[str, Any]) -> tuple[list[Issue], set[str]]:
    issues: list[Issue] = []
    author_ids: set[str] = set()
    for index, raw_author in enumerate(require_list(data.get("authors"), "authors")):
        author = require_object(raw_author, f"authors[{index}]")
        author_id = author.get("author_id")
        if not isinstance(author_id, str) or not AUTHOR_ID_RE.fullmatch(author_id):
            issues.append(
                issue("error", "INVALID_AUTHOR_ID", location=f"authors[{index}]")
            )
            continue
        if author_id in author_ids:
            issues.append(issue("error", "DUPLICATE_AUTHOR_ID", item_id=author_id))
            continue
        author_ids.add(author_id)
        if author.get("is_human") is not True:
            issues.append(
                issue("error", "NONHUMAN_AUTHOR_PROHIBITED", item_id=author_id)
            )
        if not is_nonempty_string(author.get("name")) or is_placeholder(
            author.get("name")
        ):
            issues.append(issue("error", "MISSING_AUTHOR_NAME", item_id=author_id))
        criteria = require_object(
            author.get("authorship_criteria"),
            f"{author_id}.authorship_criteria",
        )
        for criterion in AUTHORSHIP_CRITERIA:
            if criteria.get(criterion) is not True:
                issues.append(
                    issue(
                        "error",
                        "AUTHORSHIP_CRITERION_NOT_MET",
                        location=criterion,
                        item_id=author_id,
                    )
                )
        _validate_roles(author.get("credit_roles"), item_id=author_id, issues=issues)

    if not author_ids:
        issues.append(issue("error", "NO_HUMAN_AUTHORS", location="authors"))

    contributor_ids: set[str] = set()
    for index, raw_contributor in enumerate(
        require_list(data.get("contributors", []), "contributors")
    ):
        contributor = require_object(raw_contributor, f"contributors[{index}]")
        contributor_id = contributor.get("contributor_id")
        if (
            not isinstance(contributor_id, str)
            or not CONTRIBUTOR_ID_RE.fullmatch(contributor_id)
            or contributor_id in contributor_ids
        ):
            issues.append(
                issue(
                    "error",
                    "INVALID_OR_DUPLICATE_CONTRIBUTOR_ID",
                    location=f"contributors[{index}]",
                )
            )
            continue
        contributor_ids.add(contributor_id)
        if contributor.get("is_human") is not True:
            issues.append(
                issue("error", "NONHUMAN_CONTRIBUTOR_RECORD", item_id=contributor_id)
            )
        _validate_roles(
            contributor.get("credit_roles"),
            item_id=contributor_id,
            issues=issues,
        )
    return issues, author_ids


def validate_accountability(
    data: dict[str, Any],
    author_ids: set[str],
) -> list[Issue]:
    issues: list[Issue] = []
    corresponding = data.get("corresponding_author_id")
    if corresponding not in author_ids:
        issues.append(issue("error", "INVALID_CORRESPONDING_AUTHOR"))
    accountability = require_object(data.get("accountability"), "accountability")
    if accountability.get("all_authors_approved") is not True:
        issues.append(
            issue("error", "FINAL_APPROVAL_INCOMPLETE", location="accountability")
        )
    guarantors = require_list(
        accountability.get("guarantor_author_ids"), "guarantor_author_ids"
    )
    if not guarantors:
        issues.append(
            issue("error", "NO_ACCOUNTABILITY_GUARANTOR", location="accountability")
        )
    for guarantor in guarantors:
        if guarantor not in author_ids:
            issues.append(
                issue("error", "INVALID_GUARANTOR_AUTHOR", item_id=str(guarantor))
            )
    return issues


def validate_ai_disclosure(data: dict[str, Any]) -> tuple[list[Issue], int]:
    issues: list[Issue] = []
    ai_use = require_object(data.get("ai_use"), "ai_use")
    used = ai_use.get("used")
    if not isinstance(used, bool):
        issues.append(issue("error", "AI_USED_NOT_BOOLEAN", location="ai_use"))
        used = False
    tools = require_list(ai_use.get("tools"), "ai_use.tools")
    if used and not tools:
        issues.append(issue("error", "AI_USE_WITHOUT_TOOL_RECORD", location="ai_use"))
    if not used and tools:
        issues.append(issue("error", "AI_TOOL_RECORDED_WHEN_UNUSED", location="ai_use"))

    if ai_use.get("human_verification_complete") is not True:
        issues.append(issue("error", "AI_OUTPUT_NOT_HUMAN_VERIFIED", location="ai_use"))
    if ai_use.get("journal_policy_checked") is not True:
        issues.append(
            issue("error", "JOURNAL_AI_POLICY_NOT_CHECKED", location="ai_use")
        )
    locations = require_list(ai_use.get("disclosed_in"), "ai_use.disclosed_in")
    if used and not locations:
        issues.append(issue("error", "AI_USE_NOT_DISCLOSED", location="ai_use"))
    for location in locations:
        if location not in DISCLOSURE_LOCATIONS:
            issues.append(
                issue("error", "INVALID_AI_DISCLOSURE_LOCATION", location="ai_use")
            )

    for index, raw_tool in enumerate(tools):
        tool = require_object(raw_tool, f"ai_use.tools[{index}]")
        tool_id = f"tool:{index + 1}"
        for key in ("name", "version", "provider", "purpose"):
            if not is_nonempty_string(tool.get(key)) or is_placeholder(tool.get(key)):
                issues.append(
                    issue(
                        "error",
                        "INCOMPLETE_AI_TOOL_RECORD",
                        location=key,
                        item_id=tool_id,
                    )
                )
        material_class = tool.get("materials_sent")
        if material_class not in MATERIAL_CLASSES:
            issues.append(issue("error", "INVALID_AI_MATERIAL_CLASS", item_id=tool_id))
        if not isinstance(tool.get("external_service"), bool):
            issues.append(
                issue("error", "EXTERNAL_SERVICE_NOT_BOOLEAN", item_id=tool_id)
            )
        if (
            tool.get("external_service") is True
            and material_class in RESTRICTED_MATERIAL_CLASSES
        ):
            if tool.get("explicit_authorization") is not True:
                issues.append(
                    issue(
                        "error",
                        "RESTRICTED_EXTERNAL_TRANSFER_UNAUTHORIZED",
                        item_id=tool_id,
                    )
                )
            if tool.get("policy_reviewed") is not True:
                issues.append(
                    issue(
                        "error",
                        "RESTRICTED_EXTERNAL_TRANSFER_POLICY_UNREVIEWED",
                        item_id=tool_id,
                    )
                )
    return issues, len(tools)


def validate_declarations(data: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    declarations = require_object(data.get("declarations"), "declarations")
    for declaration_id in (
        "ai_use",
        "author_contributions",
        "conflicts",
        "funding",
    ):
        declaration = require_object(
            declarations.get(declaration_id),
            f"declarations.{declaration_id}",
        )
        if declaration.get("status") not in {"verified", "not_applicable"}:
            issues.append(
                issue("error", "DECLARATION_NOT_VERIFIED", item_id=declaration_id)
            )
        if not SHA256_RE.fullmatch(str(declaration.get("content_sha256", ""))):
            issues.append(
                issue("error", "INVALID_DECLARATION_HASH", item_id=declaration_id)
            )
        if not is_nonempty_string(declaration.get("verified_by")) or is_placeholder(
            declaration.get("verified_by")
        ):
            issues.append(
                issue("error", "DECLARATION_VERIFIER_MISSING", item_id=declaration_id)
            )
        if not is_iso_date(declaration.get("verified_on")):
            issues.append(
                issue("error", "INVALID_DECLARATION_DATE", item_id=declaration_id)
            )
    return issues


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a local authorship JSON record against human accountability, "
            "CRediT role names, AI disclosure, and restricted-material transfer gates."
        )
    )
    parser.add_argument(
        "authorship", help="UTF-8 JSON authorship and disclosure record"
    )
    return parser


def cli() -> int:
    args = build_parser().parse_args()
    data = require_object(read_json(args.authorship), "authorship")
    if data.get("schema_version") != "1.0":
        raise InputError("unsupported authorship schema version")
    issues, author_ids = validate_people(data)
    issues.extend(validate_accountability(data, author_ids))
    ai_issues, tool_count = validate_ai_disclosure(data)
    issues.extend(ai_issues)
    issues.extend(validate_declarations(data))
    return emit_report(
        TOOL,
        issues,
        summary={
            "authors": len(author_ids),
            "ai_tools": tool_count,
            "credit_taxonomy": "ANSI/NISO Z39.104-2022",
        },
    )


if __name__ == "__main__":
    run(TOOL, cli)
