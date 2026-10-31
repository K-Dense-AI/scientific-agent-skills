#!/usr/bin/env python3
"""Create a schedule from explicitly supplied dates only."""

from __future__ import annotations

import argparse
import sys
from datetime import date

from check_consistency import check_consistency

from _common import (
    NOTICE,
    SCHEMA_VERSION,
    Issue,
    ValidationError,
    atomic_write_json,
    error_report,
    load_package,
    parse_iso_datetime,
    print_report,
    report_payload,
    safe_output_file,
    validate_package_structure,
)


def _date_bound(value: str | None, code: str) -> date | None:
    if value is None:
        return None
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError
        return parsed
    except ValueError as exc:
        raise ValidationError(code) from exc


def build_schedule(
    documents: dict[str, dict],
    *,
    from_date: str | None = None,
    through_date: str | None = None,
) -> tuple[dict, dict]:
    issues = validate_package_structure(documents)
    if issues:
        return (
            report_payload(
                "explicit_date_schedule",
                issues,
                counts={"structural_issues": len(issues)},
            ),
            {},
        )

    consistency = check_consistency(documents)
    if consistency["status"] == "fail":
        return (
            report_payload(
                "explicit_date_schedule",
                [Issue(item["code"], item["path"], item["level"])
                 for item in consistency["issues"]],
                counts={"consistency_issues": len(consistency["issues"])},
            ),
            {},
        )

    lower = _date_bound(from_date, "FROM_DATE_INVALID")
    upper = _date_bound(through_date, "THROUGH_DATE_INVALID")
    if lower and upper and lower > upper:
        raise ValidationError("DATE_FILTER_ORDER_INVALID")

    events: list[dict] = []

    def add_event(
        value: str | None,
        *,
        event_type: str,
        document_type: str,
        record_index: int | None,
        date_field: str,
    ) -> None:
        if value is None:
            return
        event_date = value[:10]
        parsed = date.fromisoformat(event_date)
        if lower and parsed < lower:
            return
        if upper and parsed > upper:
            return
        events.append(
            {
                "date": event_date,
                "event_type": event_type,
                "source_document_type": document_type,
                "record_index": record_index,
                "date_field": date_field,
            }
        )

    interventions = documents[
        "clinician_authored_intervention_record"
    ]["interventions"]
    for index, record in enumerate(interventions):
        add_event(
            record["start_date"],
            event_type="intervention_start_as_supplied",
            document_type="clinician_authored_intervention_record",
            record_index=index,
            date_field="start_date",
        )
        add_event(
            record["end_date"],
            event_type="intervention_end_as_supplied",
            document_type="clinician_authored_intervention_record",
            record_index=index,
            date_field="end_date",
        )

    planning = documents["goals_monitoring_checkpoint_record"]
    for index, record in enumerate(planning["goals"]):
        add_event(
            record["target_date"],
            event_type="goal_target_date_as_supplied",
            document_type="goals_monitoring_checkpoint_record",
            record_index=index,
            date_field="goals.target_date",
        )
        if record["target_date"] is None:
            issues.append(
                Issue(
                    "GOAL_HAS_NO_EXPLICIT_TARGET_DATE",
                    (
                        "goals_monitoring_checkpoint_record:"
                        f"$.goals[{index}].target_date"
                    ),
                    "warning",
                )
            )
    for index, record in enumerate(planning["monitoring_items"]):
        add_event(
            record["next_due_date"],
            event_type="monitoring_due_date_as_supplied",
            document_type="goals_monitoring_checkpoint_record",
            record_index=index,
            date_field="monitoring_items.next_due_date",
        )
        if record["frequency_as_supplied"] and record["next_due_date"] is None:
            issues.append(
                Issue(
                    "FREQUENCY_TEXT_NOT_EXPANDED_WITHOUT_EXPLICIT_DATE",
                    (
                        "goals_monitoring_checkpoint_record:"
                        f"$.monitoring_items[{index}].next_due_date"
                    ),
                    "warning",
                )
            )
    for index, record in enumerate(planning["checkpoints"]):
        add_event(
            record["checkpoint_date"],
            event_type="checkpoint_date_as_supplied",
            document_type="goals_monitoring_checkpoint_record",
            record_index=index,
            date_field="checkpoints.checkpoint_date",
        )

    transition = documents["transition_reconciliation_record"][
        "transition"
    ]
    add_event(
        transition["handoff_date"],
        event_type="transition_handoff_date_as_supplied",
        document_type="transition_reconciliation_record",
        record_index=None,
        date_field="transition.handoff_date",
    )

    intended = documents["intended_use_handoff_record"]
    for field, event_type in (
        ("sent_at", "documentation_handoff_sent_as_supplied"),
    ):
        timestamp = intended["handoff"][field]
        if timestamp is not None and parse_iso_datetime(timestamp) is not None:
            add_event(
                timestamp,
                event_type=event_type,
                document_type="intended_use_handoff_record",
                record_index=None,
                date_field=f"handoff.{field}",
            )

    events.sort(
        key=lambda item: (
            item["date"],
            item["event_type"],
            item["source_document_type"],
            -1 if item["record_index"] is None else item["record_index"],
        )
    )
    if not events:
        issues.append(Issue("NO_EXPLICIT_DATES_IN_FILTER", "$"))

    schedule = {
        "schema_version": SCHEMA_VERSION,
        "document_type": "explicit_date_schedule",
        "status": "DRAFT_NOT_FOR_CLINICAL_USE",
        "notice": NOTICE,
        "dates_inferred": False,
        "recurrences_generated": False,
        "clinical_intervals_generated": False,
        "filters": {
            "from_date": from_date,
            "through_date": through_date,
        },
        "events": events,
    }
    issues.sort(key=lambda item: (item.path, item.code))
    report = report_payload(
        "explicit_date_schedule",
        issues,
        counts={"events": len(events)},
        extra={
            "dates_inferred": False,
            "recurrences_generated": False,
            "clinical_content_interpreted": False,
        },
    )
    return report, schedule


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Write a local JSON schedule containing only dates explicitly "
            "supplied by authorized clinicians. Frequencies are never expanded."
        )
    )
    parser.add_argument("package", help="Complete local package directory")
    parser.add_argument(
        "--output",
        required=True,
        help="New local .json output; existing files are rejected",
    )
    parser.add_argument(
        "--from-date",
        help="Optional inclusive YYYY-MM-DD filter; no default is inferred",
    )
    parser.add_argument(
        "--through-date",
        help="Optional inclusive YYYY-MM-DD filter; no default is inferred",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        documents, _ = load_package(args.package)
        report, schedule = build_schedule(
            documents,
            from_date=args.from_date,
            through_date=args.through_date,
        )
        if report["status"] == "pass":
            output = safe_output_file(args.output)
            atomic_write_json(output, schedule)
            report["output_filename"] = output.name
    except ValidationError as exc:
        report = error_report("explicit_date_schedule", exc)
    print_report(report)
    return 1 if report["status"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
