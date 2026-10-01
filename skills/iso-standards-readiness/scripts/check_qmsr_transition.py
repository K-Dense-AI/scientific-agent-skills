#!/usr/bin/env python3
"""Check documented evidence for the post-effective-date FDA QMSR transition."""

from __future__ import annotations

from typing import Any

from _catalog import QMSR_TRANSITION_ITEMS
from _common import (
    Review,
    finish,
    guarded_main,
    load_json,
    require_root_object,
    standard_parser,
)

ITEM_STATUSES = {
    "not-started",
    "in-progress",
    "evidence-ready",
    "not-applicable",
}


def validate(data: dict[str, Any]) -> tuple[Review, dict[str, int]]:
    review = Review()
    metadata = review.object(data.get("metadata"), "metadata")
    if metadata is not None:
        review.controlled_item(metadata, "metadata", require_approved=True)
        review.text(metadata, "checklist_id", "metadata", max_chars=120)
        review.date(metadata, "review_date", "metadata")

    basis = review.object(data.get("qmsr_basis"), "qmsr_basis")
    if basis is not None:
        # The organization's source-review date is independent of this skill's
        # research baseline. Currency itself requires controlled human review.
        review.date(basis, "as_of", "qmsr_basis")
        effective = review.date(basis, "effective_date", "qmsr_basis")
        if effective != "2026-02-02":
            review.add(
                "EFFECTIVE_DATE",
                "qmsr_basis.effective_date",
                "current QMSR effective date must be recorded as 2026-02-02",
                "blocker",
            )
        title = review.text(
            basis,
            "current_part_820_title",
            "qmsr_basis",
            max_chars=200,
        )
        if title != "Quality Management System Regulation":
            review.add(
                "CURRENT_TITLE",
                "qmsr_basis.current_part_820_title",
                "must identify current Part 820 as Quality Management System Regulation",
            )
        program = review.text(
            basis,
            "inspection_compliance_program",
            "qmsr_basis",
            max_chars=120,
        )
        if program != "7382.850":
            review.add(
                "INSPECTION_PROGRAM",
                "qmsr_basis.inspection_compliance_program",
                "must identify current FDA Compliance Program 7382.850",
            )
        review.text(basis, "owner", "qmsr_basis", max_chars=200)
        review.evidence(basis, "qmsr_basis")
        review.approval(basis, "qmsr_basis", require_approved=True)
        review.source_refs(basis, "qmsr_basis", min_items=3)

    items = review.list(data.get("items"), "items", min_items=1) or []
    seen: set[str] = set()
    ready = 0
    for index, value in enumerate(items):
        path = f"items[{index}]"
        item = review.object(value, path)
        if item is None:
            continue
        identifier = review.text(item, "id", path, max_chars=120)
        if identifier:
            seen.add(identifier)
            if identifier not in QMSR_TRANSITION_ITEMS:
                review.add(
                    "ITEM_UNKNOWN",
                    f"{path}.id",
                    "item is not in the versioned transition catalog",
                )
        review.text(item, "owner", path, max_chars=200)
        status = review.choice(item, "status", ITEM_STATUSES, path)
        review.text(item, "assessment", path, max_chars=3_000)
        review.evidence(
            item,
            path,
            min_items=1 if status in {"evidence-ready", "not-applicable"} else 0,
        )
        review.source_refs(item, path)
        review.approval(
            item,
            path,
            require_approved=status in {"evidence-ready", "not-applicable"},
        )
        if status == "evidence-ready":
            ready += 1
        if status == "not-applicable":
            review.text(item, "rationale", path, max_chars=2_000)
    review.unique_ids(items, "items")

    missing = sorted(set(QMSR_TRANSITION_ITEMS) - seen)
    for identifier in missing:
        review.add(
            "ITEM_MISSING",
            "items",
            f"missing transition evidence item: {identifier}",
        )

    attestations = review.object(data.get("attestations"), "attestations")
    required_attestations = (
        "iso_certificate_not_treated_as_fda_compliance",
        "checklist_not_treated_as_compliance_determination",
        "legacy_qsr_clause_map_not_used_as_current_requirements",
        "applicability_decisions_owned_by_authorized_humans",
    )
    if attestations is not None:
        for key in required_attestations:
            if attestations.get(key) is not True:
                review.add(
                    "ATTESTATION_REQUIRED",
                    f"attestations.{key}",
                    "must be explicitly true and supported by controlled evidence",
                    "blocker",
                )
        review.text(attestations, "owner", "attestations", max_chars=200)
        review.evidence(attestations, "attestations")
        review.approval(attestations, "attestations", require_approved=True)

    return review, {
        "catalog_items": len(QMSR_TRANSITION_ITEMS),
        "evidence_ready": ready,
        "items_submitted": len(items),
    }


def main() -> int:
    parser = standard_parser(
        "Check QMSR transition evidence using the current post-2026 Part 820 model.",
        "Path to the local QMSR-transition JSON file",
    )
    args = parser.parse_args()
    data = require_root_object(load_json(args.input))
    review, metrics = validate(data)
    return finish("check_qmsr_transition", review, args, metrics=metrics)


if __name__ == "__main__":
    guarded_main(main)
