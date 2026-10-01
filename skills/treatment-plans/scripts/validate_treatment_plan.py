#!/usr/bin/env python3
"""Validate strict JSON structure without evaluating clinical content."""

from __future__ import annotations

import argparse
import sys

from _common import (
    TEMPLATE_FILES,
    Issue,
    ValidationError,
    error_report,
    load_target,
    print_report,
    report_payload,
    validate_document,
    validate_package_structure,
)


def validate_target(raw_path: str) -> dict:
    documents, _ = load_target(raw_path)
    if set(documents) == set(TEMPLATE_FILES):
        issues = validate_package_structure(documents)
    else:
        issues: list[Issue] = []
        for document_type, document in documents.items():
            for issue in validate_document(document):
                issues.append(
                    Issue(
                        issue.code,
                        f"{document_type if document_type in TEMPLATE_FILES else 'unknown_document_type'}:{issue.path}",
                        issue.level,
                    )
                )
        issues.sort(key=lambda item: (item.path, item.code))

    record_count = 0
    for document in documents.values():
        for field in (
            "facts",
            "interventions",
            "goals",
            "monitoring_items",
            "checkpoints",
            "entries",
            "handoff_items",
            "unresolved_items",
        ):
            value = document.get(field)
            if isinstance(value, list):
                record_count += len(value)

    return report_payload(
        "structural_validation",
        issues,
        counts={
            "documents_checked": len(documents),
            "records_checked": record_count,
            "structural_issues": len(issues),
        },
        extra={
            "clinical_content_evaluated": False,
            "unknown_fields_allowed": False,
        },
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate one local JSON record or a complete six-file package. "
            "Checks only schema, types, enums, bounds, and ISO dates."
        )
    )
    parser.add_argument(
        "path",
        help="Local .json file or complete package directory",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        report = validate_target(args.path)
    except ValidationError as exc:
        report = error_report("structural_validation", exc)
    print_report(report)
    return 1 if report["status"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
