"""Audit claim-to-evidence mappings and local citation markers."""

from __future__ import annotations

import argparse
import hashlib
import re
from typing import Any

from _common import (
    InputError,
    Issue,
    emit_report,
    is_nonempty_string,
    issue,
    read_csv,
    read_json,
    read_text,
    require_list,
    require_object,
    run,
)
from validate_manifest import validate_source_manifest

TOOL = "audit_claims"
REQUIRED_FIELDS = {
    "claim_id",
    "section",
    "claim_kind",
    "claim_text_sha256",
    "evidence_ids",
    "verification_status",
    "uncertainty",
    "analysis_intent",
}
CLAIM_ID_RE = re.compile(r"^C[0-9]{3,8}$")
EVIDENCE_ID_RE = re.compile(r"^E[0-9]{3,8}$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
CLAIM_MARKER_RE = re.compile(r"\[claim:(C[0-9]{3,8})\]")
EVIDENCE_MARKER_RE = re.compile(
    r"\[evidence:((?:E[0-9]{3,8})(?:\s*,\s*E[0-9]{3,8})*)\]"
)
CITATION_MARKER_RE = re.compile(r"\[@(E[0-9]{3,8})\]")
NUMERIC_RE = re.compile(r"(?<![A-Za-z])(?:[<>]=?\s*)?[0-9]+(?:\.[0-9]+)?%?")
CLAIM_KINDS = {"factual", "numeric", "method", "result", "interpretive", "declaration"}
UNCERTAINTY = {"not_applicable", "not_estimated", "low", "moderate", "high"}
ANALYSIS_INTENT = {"confirmatory", "exploratory", "descriptive", "not_applicable"}


def _split_evidence_ids(value: str) -> list[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def load_sources(path: str) -> dict[str, bool]:
    data = require_object(read_json(path), "source_manifest")
    if any(
        item.severity == "error"
        for item in validate_source_manifest(data, require_verified=False)
    ):
        raise InputError("source manifest failed validation")
    sources: dict[str, bool] = {}
    for index, raw_source in enumerate(require_list(data.get("sources"), "sources")):
        source = require_object(raw_source, f"sources[{index}]")
        evidence_id = source.get("evidence_id")
        if not isinstance(evidence_id, str) or not EVIDENCE_ID_RE.fullmatch(
            evidence_id
        ):
            raise InputError("source manifest contains an invalid evidence_id")
        if evidence_id in sources:
            raise InputError("source manifest contains duplicate evidence_id values")
        verification = require_object(source.get("verification"), "verification")
        sources[evidence_id] = (
            verification.get("status") == "verified"
            and verification.get("source_opened") is True
        )
    return sources


def claim_text_hash(line: str) -> str:
    """Hash one physical claim line, excluding markers and normalizing whitespace."""
    text = CLAIM_MARKER_RE.sub("", line)
    text = EVIDENCE_MARKER_RE.sub("", text)
    text = CITATION_MARKER_RE.sub("", text)
    normalized = " ".join(text.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def load_claims(
    path: str,
    sources: dict[str, bool],
) -> tuple[dict[str, dict[str, Any]], list[Issue]]:
    fields, rows = read_csv(path)
    if set(fields) != REQUIRED_FIELDS:
        missing = ",".join(sorted(REQUIRED_FIELDS - set(fields)))
        extra = ",".join(sorted(set(fields) - REQUIRED_FIELDS))
        raise InputError(
            f"claim registry headers must match the schema; missing={missing}; extra={extra}"
        )
    issues: list[Issue] = []
    claims: dict[str, dict[str, Any]] = {}
    for row_number, row in enumerate(rows, start=2):
        location = f"row:{row_number}"
        claim_id = row["claim_id"].strip()
        if not CLAIM_ID_RE.fullmatch(claim_id):
            issues.append(issue("error", "INVALID_CLAIM_ID", location=location))
            continue
        if claim_id in claims:
            issues.append(issue("error", "DUPLICATE_CLAIM_ID", item_id=claim_id))
            continue
        claims[claim_id] = row
        if row["claim_kind"] not in CLAIM_KINDS:
            issues.append(issue("error", "INVALID_CLAIM_KIND", item_id=claim_id))
        if not is_nonempty_string(row["section"]):
            issues.append(issue("error", "MISSING_CLAIM_SECTION", item_id=claim_id))
        if not SHA256_RE.fullmatch(row["claim_text_sha256"]):
            issues.append(issue("error", "INVALID_CLAIM_TEXT_HASH", item_id=claim_id))
        if row["verification_status"] != "verified":
            issues.append(issue("error", "CLAIM_NOT_VERIFIED", item_id=claim_id))
        if row["uncertainty"] not in UNCERTAINTY:
            issues.append(
                issue("error", "INVALID_UNCERTAINTY_STATUS", item_id=claim_id)
            )
        if row["analysis_intent"] not in ANALYSIS_INTENT:
            issues.append(issue("error", "INVALID_ANALYSIS_INTENT", item_id=claim_id))

        evidence_ids = _split_evidence_ids(row["evidence_ids"])
        row["_evidence_ids"] = evidence_ids
        if not evidence_ids:
            issues.append(issue("error", "CLAIM_WITHOUT_EVIDENCE", item_id=claim_id))
        for evidence_id in evidence_ids:
            if not EVIDENCE_ID_RE.fullmatch(evidence_id):
                issues.append(
                    issue("error", "INVALID_CLAIM_EVIDENCE_ID", item_id=claim_id)
                )
            elif evidence_id not in sources:
                issues.append(
                    issue("error", "UNKNOWN_CLAIM_EVIDENCE", item_id=claim_id)
                )
            elif not sources[evidence_id]:
                issues.append(
                    issue("error", "UNVERIFIED_CLAIM_EVIDENCE", item_id=claim_id)
                )
    return claims, issues


def audit_markdown(
    text: str,
    claims: dict[str, dict[str, Any]],
    sources: dict[str, bool],
) -> tuple[list[Issue], set[str]]:
    issues: list[Issue] = []
    used_claims: set[str] = set()
    in_fence = False
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence or not stripped or stripped.startswith(("#", "<!--")):
            continue

        line_claims = CLAIM_MARKER_RE.findall(line)
        if len(line_claims) > 1:
            issues.append(
                issue("error", "MULTIPLE_CLAIMS_ON_LINE", location=f"line:{line_number}")
            )
        line_evidence: set[str] = set(CITATION_MARKER_RE.findall(line))
        for group in EVIDENCE_MARKER_RE.findall(line):
            line_evidence.update(part.strip() for part in group.split(","))

        for evidence_id in sorted(line_evidence):
            if evidence_id not in sources:
                issues.append(
                    issue(
                        "error",
                        "UNKNOWN_CITATION_MARKER",
                        location=f"line:{line_number}",
                        item_id=evidence_id,
                    )
                )
            elif not sources[evidence_id]:
                issues.append(
                    issue(
                        "error",
                        "UNVERIFIED_CITATION_MARKER",
                        location=f"line:{line_number}",
                        item_id=evidence_id,
                    )
                )

        for claim_id in line_claims:
            used_claims.add(claim_id)
            if claim_id not in claims:
                issues.append(
                    issue(
                        "error",
                        "UNKNOWN_CLAIM_MARKER",
                        location=f"line:{line_number}",
                        item_id=claim_id,
                    )
                )
                continue
            expected = set(claims[claim_id].get("_evidence_ids", []))
            if len(line_claims) == 1 and claim_text_hash(line) != claims[claim_id].get(
                "claim_text_sha256"
            ):
                issues.append(
                    issue(
                        "error",
                        "CLAIM_TEXT_HASH_MISMATCH",
                        location=f"line:{line_number}",
                        item_id=claim_id,
                    )
                )
            if not expected.issubset(line_evidence):
                issues.append(
                    issue(
                        "error",
                        "CLAIM_MARKER_MISSING_EVIDENCE_MARKER",
                        location=f"line:{line_number}",
                        item_id=claim_id,
                    )
                )

        if NUMERIC_RE.search(line) and not line_claims:
            issues.append(
                issue(
                    "error",
                    "UNTAGGED_NUMERIC_CONTENT",
                    location=f"line:{line_number}",
                )
            )
    return issues, used_claims


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit local Markdown claim markers against a CSV claim registry and "
            "verified JSON source manifest. Output never includes manuscript text."
        )
    )
    parser.add_argument("manuscript", help="UTF-8 Markdown manuscript")
    parser.add_argument("claims", help="UTF-8 CSV claim-evidence registry")
    parser.add_argument("sources", help="UTF-8 JSON source manifest")
    return parser


def cli() -> int:
    args = build_parser().parse_args()
    sources = load_sources(args.sources)
    claims, issues = load_claims(args.claims, sources)
    text = read_text(args.manuscript, {".md", ".markdown"})
    markdown_issues, used_claims = audit_markdown(text, claims, sources)
    issues.extend(markdown_issues)
    for claim_id in sorted(set(claims) - used_claims):
        issues.append(
            issue("warning", "CLAIM_NOT_USED_IN_MANUSCRIPT", item_id=claim_id)
        )
    return emit_report(
        TOOL,
        issues,
        summary={
            "claims_registered": len(claims),
            "claims_used": len(used_claims),
            "sources_registered": len(sources),
        },
    )


if __name__ == "__main__":
    run(TOOL, cli)
