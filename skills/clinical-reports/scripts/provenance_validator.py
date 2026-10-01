#!/usr/bin/env python3
"""Validate source-fact-to-claim traceability without opening source records."""

from __future__ import annotations

import argparse
import re
import sys
from typing import Any

sys.dont_write_bytecode = True

from _common import (  # noqa: E402
    SHA256_RE,
    ValidationError,
    error_report,
    load_json_object,
    parse_iso_date,
    require_bool,
    require_data_class,
    require_exact_keys,
    require_identifier,
    require_string,
    write_json_report,
)

TOOL = "provenance_validator"
LOCAL_LOCATOR_RE = re.compile(r"^local:[A-Za-z0-9_./:-]{1,280}$")
SOURCE_KINDS = {
    "synthetic_record",
    "deidentified_record",
    "aggregate_output",
    "protocol",
    "statistical_analysis_plan",
    "published_source",
    "authorized_system_record",
}
FACT_FIELDS = {
    "fact_id",
    "source_record_kind",
    "record_locator",
    "field_path",
    "value_hash_sha256",
    "verification_status",
    "verified_by_role",
    "verified_at",
    "source_version",
}
CLAIM_FIELDS = {
    "claim_id",
    "artifact_field_path",
    "fact_ids",
    "support_status",
}
TOP_LEVEL_FIELDS = {
    "schema_version",
    "artifact_kind",
    "manifest_status",
    "safety_notice",
    "data_classification",
    "authorized_purpose",
    "authorization_verified",
    "facts",
    "claims",
    "review",
}


def validate_provenance(data: dict[str, Any]) -> dict[str, Any]:
    """Validate bounded metadata links while preserving source separation."""
    errors: list[str] = []
    warnings: list[str] = []
    try:
        require_exact_keys(data, TOP_LEVEL_FIELDS, "manifest")
        if data.get("schema_version") != "2.0":
            raise ValidationError("schema_version must be 2.0")
        if data.get("manifest_status") != "BLOCKED_INCOMPLETE":
            raise ValidationError("manifest_status must remain BLOCKED_INCOMPLETE")
        require_string(data.get("safety_notice"), "safety_notice", max_length=1000)
    except ValidationError as exc:
        errors.append(str(exc))
    if data.get("artifact_kind") != "provenance_manifest":
        errors.append("artifact_kind must be provenance_manifest")
    try:
        require_data_class(data.get("data_classification"))
        require_string(data.get("authorized_purpose"), "authorized_purpose")
        if not require_bool(data.get("authorization_verified"), "authorization_verified"):
            errors.append("authorization_verified must be true")
    except ValidationError as exc:
        errors.append(str(exc))

    facts = data.get("facts")
    claims = data.get("claims")
    if not isinstance(facts, list) or not facts:
        errors.append("facts must be a non-empty array")
        facts = []
    if not isinstance(claims, list) or not claims:
        errors.append("claims must be a non-empty array")
        claims = []
    if len(facts) > 10_000:
        errors.append("facts may contain at most 10,000 items")
    if len(claims) > 10_000:
        errors.append("claims may contain at most 10,000 items")

    fact_ids: set[str] = set()
    for index, fact in enumerate(facts[:10_000]):
        try:
            fact = require_exact_keys(fact, FACT_FIELDS, f"facts[{index}]")
        except ValidationError as exc:
            errors.append(str(exc))
            continue
        try:
            fact_id = require_identifier(fact.get("fact_id"), f"facts[{index}].fact_id")
            if fact_id in fact_ids:
                errors.append(f"duplicate fact_id: {fact_id}")
            fact_ids.add(fact_id)
            if (
                not isinstance(fact.get("source_record_kind"), str)
                or fact.get("source_record_kind") not in SOURCE_KINDS
            ):
                errors.append(f"facts[{index}].source_record_kind is invalid")
            locator = require_string(
                fact.get("record_locator"),
                f"facts[{index}].record_locator",
                max_length=286,
            )
            if not LOCAL_LOCATOR_RE.fullmatch(locator):
                errors.append(
                    f"facts[{index}].record_locator must be a local: locator"
                )
            require_string(
                fact.get("field_path"),
                f"facts[{index}].field_path",
                max_length=300,
            )
            value_hash = require_string(
                fact.get("value_hash_sha256"),
                f"facts[{index}].value_hash_sha256",
                max_length=64,
            )
            if not SHA256_RE.fullmatch(value_hash):
                errors.append(f"facts[{index}].value_hash_sha256 is invalid")
            if fact.get("verification_status") != "verified":
                errors.append(f"facts[{index}] is not verified")
            require_string(
                fact.get("verified_by_role"),
                f"facts[{index}].verified_by_role",
                max_length=100,
            )
            parse_iso_date(fact.get("verified_at"), f"facts[{index}].verified_at")
            require_string(
                fact.get("source_version"),
                f"facts[{index}].source_version",
                max_length=100,
            )
        except ValidationError as exc:
            errors.append(str(exc))

    claim_ids: set[str] = set()
    referenced_facts: set[str] = set()
    for index, claim in enumerate(claims[:10_000]):
        try:
            claim = require_exact_keys(claim, CLAIM_FIELDS, f"claims[{index}]")
        except ValidationError as exc:
            errors.append(str(exc))
            continue
        try:
            claim_id = require_identifier(
                claim.get("claim_id"),
                f"claims[{index}].claim_id",
            )
            if claim_id in claim_ids:
                errors.append(f"duplicate claim_id: {claim_id}")
            claim_ids.add(claim_id)
            require_string(
                claim.get("artifact_field_path"),
                f"claims[{index}].artifact_field_path",
                max_length=300,
            )
            links = claim.get("fact_ids")
            if not isinstance(links, list) or not links:
                errors.append(f"claims[{index}].fact_ids must be a non-empty array")
                links = []
            for linked in links:
                linked_id = require_identifier(linked, f"claims[{index}].fact_ids")
                referenced_facts.add(linked_id)
                if linked_id not in fact_ids:
                    errors.append(
                        f"claims[{index}] references unknown fact_id {linked_id}"
                    )
            if claim.get("support_status") != "supported_by_verified_facts":
                errors.append(f"claims[{index}] is not marked supported_by_verified_facts")
        except ValidationError as exc:
            errors.append(str(exc))

    unused = sorted(fact_ids - referenced_facts)
    if unused:
        warnings.append(f"{len(unused)} verified facts are not linked to a claim")

    review = data.get("review")
    try:
        review = require_exact_keys(
            review,
            {
                "source_owner_review",
                "quality_review",
                "privacy_review",
                "release_authorized",
            },
            "review",
        )
        for field in ("source_owner_review", "quality_review", "privacy_review"):
            if review.get(field) != "completed":
                warnings.append(f"review.{field} remains required")
        if review.get("release_authorized") is not False:
            errors.append("review.release_authorized must remain false")
    except ValidationError as exc:
        errors.append(str(exc))

    return {
        "tool": TOOL,
        "status": "BLOCKED" if errors else "TRACEABILITY_COMPLETE_REVIEW_REQUIRED",
        "fact_count": len(facts),
        "claim_count": len(claims),
        "linked_fact_count": len(referenced_facts),
        "errors": errors,
        "warnings": warnings,
        "limitations": [
            "Source records were not opened and hash values were not recomputed.",
            "Traceability metadata does not establish source truth or clinical correctness.",
        ],
        "review_required": True,
        "authorizes_clinical_use_or_submission": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check bounded local source-fact traceability metadata. "
            "Does not open source records or copy clinical content."
        )
    )
    parser.add_argument("input_file", help="Local provenance manifest (.json)")
    parser.add_argument("-o", "--output", help="Optional local JSON report")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        _, data = load_json_object(args.input_file)
        report = validate_provenance(data)
    except (OSError, ValidationError) as exc:
        report = error_report(TOOL, exc)
    try:
        write_json_report(report, args.output, overwrite=args.overwrite)
    except (OSError, ValidationError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0 if report["status"] == "TRACEABILITY_COMPLETE_REVIEW_REQUIRED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
