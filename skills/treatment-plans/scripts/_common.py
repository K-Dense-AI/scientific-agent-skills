#!/usr/bin/env python3
"""Bounded, dependency-free helpers for local treatment-plan JSON records."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "2.0"
STATUS = "DRAFT_NOT_FOR_CLINICAL_USE"
NOTICE = (
    "DRAFT — NOT MEDICAL ADVICE — DOCUMENTATION-ONLY — "
    "AUTHORIZED CLINICIAN SIGN-OFF REQUIRED"
)
EMERGENCY_STATEMENT = (
    "If a concern may be urgent or emergent, stop this documentation workflow "
    "and use the institution's current clinical escalation or emergency process; "
    "this package does not determine urgency or provide emergency instructions."
)
SIGNOFF_ATTESTATION = (
    "The signer attests only that this package accurately transcribes "
    "clinician-supplied and verified decisions for authorized documentation "
    "handoff; it is not stand-alone medical advice."
)

MAX_INPUT_BYTES = 2 * 1024 * 1024
MAX_TEXT_CHARS = 8_000
MAX_LIST_ITEMS = 500
MAX_OBJECT_FIELDS = 100
MAX_DEPTH = 20
MAX_TOTAL_NODES = 20_000

IDENTIFIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._:-]{1,95}$")
DATETIME_RE = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])"
)
BLOCKER_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,95}$")
DIRECT_IDENTIFIER_KEYS = {
    "address",
    "date_of_birth",
    "dob",
    "email",
    "fax",
    "full_name",
    "medical_record_number",
    "mrn",
    "name",
    "patient_id",
    "phone",
    "social_security_number",
    "ssn",
}
PROHIBITED_USES = {
    "diagnosis_or_assessment",
    "therapy_selection_or_recommendation",
    "medication_or_dose_decision",
    "start_stop_hold_resume_titrate_or_taper_decision",
    "interaction_allergy_or_contraindication_check",
    "triage_or_urgency_determination",
    "emergency_advice_or_safety_plan",
    "prognosis_or_outcome_prediction",
    "patient_specific_recommendation",
    "replacement_of_authorized_professional_review",
}

TEMPLATE_FILES = {
    "source_fact_manifest": (
        "source_fact_manifest_template.json",
        "source_fact_manifest.json",
    ),
    "clinician_authored_intervention_record": (
        "clinician_authored_intervention_template.json",
        "clinician_authored_intervention.json",
    ),
    "goals_monitoring_checkpoint_record": (
        "goals_monitoring_checkpoint_template.json",
        "goals_monitoring_checkpoint.json",
    ),
    "informed_preference_shared_decision_record": (
        "informed_preference_shared_decision_template.json",
        "informed_preference_shared_decision.json",
    ),
    "transition_reconciliation_record": (
        "transition_reconciliation_template.json",
        "transition_reconciliation.json",
    ),
    "intended_use_handoff_record": (
        "intended_use_handoff_template.json",
        "intended_use_handoff.json",
    ),
}


class ValidationError(ValueError):
    """A deterministic failure that never includes a clinical value."""

    def __init__(self, code: str, path: str = "$") -> None:
        super().__init__(code)
        self.code = code
        self.path = path


@dataclass(frozen=True)
class Issue:
    """A minimized validation issue."""

    code: str
    path: str
    level: str = "error"

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "level": self.level}


def _text(
    *,
    minimum: int = 0,
    maximum: int = MAX_TEXT_CHARS,
    enum: Iterable[str] | None = None,
    const: str | None = None,
    pattern: str | None = None,
    format_name: str | None = None,
) -> dict[str, Any]:
    return {
        "kind": "string",
        "minimum": minimum,
        "maximum": maximum,
        "enum": set(enum) if enum is not None else None,
        "const": const,
        "pattern": re.compile(pattern) if pattern else None,
        "format": format_name,
    }


def _boolean() -> dict[str, str]:
    return {"kind": "boolean"}


def _nullable(schema: dict[str, Any]) -> dict[str, Any]:
    return {"kind": "nullable", "schema": schema}


def _array(
    item: dict[str, Any], *, minimum: int = 0, maximum: int = MAX_LIST_ITEMS
) -> dict[str, Any]:
    return {
        "kind": "array",
        "item": item,
        "minimum": minimum,
        "maximum": maximum,
    }


def _object(properties: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {"kind": "object", "properties": properties}


IDENTIFIER = _text(minimum=2, maximum=96, pattern=IDENTIFIER_RE.pattern)
ROLE = _text(maximum=200)
NONEMPTY_ROLE = _text(minimum=1, maximum=200)
DATE = _text(minimum=10, maximum=10, format_name="date")
DATETIME = _text(minimum=20, maximum=40, format_name="datetime")
FACT_IDS = _array(IDENTIFIER, minimum=1, maximum=100)

HEADER = {
    "schema_version": _text(const=SCHEMA_VERSION),
    "document_type": _text(minimum=1, maximum=96),
    "document_id": IDENTIFIER,
    "subject_ref": IDENTIFIER,
    "data_classification": _text(
        enum={
            "synthetic",
            "deidentified_qualified_review",
            "real_patient_minimum_necessary",
        }
    ),
    "status": _text(const=STATUS),
    "notice": _text(const=NOTICE),
    "created_at": _nullable(DATETIME),
}

VERIFICATION = _object(
    {
        "status": _text(enum={"pending", "verified"}),
        "verified_by_role": ROLE,
        "verified_at": _nullable(DATETIME),
    }
)

SOURCE_FACT_SCHEMA = _object(
    {
        "fact_id": IDENTIFIER,
        "fact_kind": _text(
            enum={
                "clinician_authored_decision",
                "verified_local_record",
                "current_official_source",
                "local_policy",
            }
        ),
        "statement_as_supplied": _text(minimum=1, maximum=4_000),
        "source": _object(
            {
                "source_type": _text(
                    enum={
                        "signed_clinician_record",
                        "authorized_ehr_record",
                        "current_fda_labeling",
                        "current_rems_material",
                        "current_official_guidance",
                        "local_policy",
                    }
                ),
                "title": _text(minimum=1, maximum=500),
                "locator": _text(minimum=1, maximum=1_000),
                "version_or_date": _text(minimum=1, maximum=200),
            }
        ),
        "verification": VERIFICATION,
        "applicability": _object(
            {
                "status": _text(
                    enum={
                        "not_assessed",
                        "confirmed_by_authorized_clinician",
                        "not_applicable_local_record",
                    }
                ),
                "confirmed_by_role": ROLE,
                "confirmed_at": _nullable(DATETIME),
            }
        ),
    }
)

PARAMETER_SCHEMA = _object(
    {
        "parameter_id": IDENTIFIER,
        "label": _text(minimum=1, maximum=200),
        "value_as_supplied": _text(minimum=1, maximum=1_000),
        "source_fact_ids": FACT_IDS,
    }
)

INTERVENTION_SCHEMA = _object(
    {
        "intervention_id": IDENTIFIER,
        "intervention_kind": _text(
            enum={
                "medication",
                "procedure",
                "therapy",
                "diagnostic",
                "education",
                "care_coordination",
                "equipment_or_service",
                "other_clinician_authored",
            }
        ),
        "clinical_decision_status": _text(
            enum={
                "pending_authorized_verification",
                "supplied_and_verified_by_authorized_clinician",
            }
        ),
        "clinician_authored_action": _text(minimum=1, maximum=4_000),
        "parameters_as_supplied": _array(PARAMETER_SCHEMA, maximum=100),
        "source_fact_ids": FACT_IDS,
        "owner_role": NONEMPTY_ROLE,
        "start_date": _nullable(DATE),
        "end_date": _nullable(DATE),
        "verification": VERIFICATION,
    }
)

GOAL_SCHEMA = _object(
    {
        "goal_id": IDENTIFIER,
        "statement_as_supplied": _text(minimum=1, maximum=2_000),
        "measurement_as_supplied": _text(maximum=1_000),
        "target_as_supplied": _text(maximum=1_000),
        "target_date": _nullable(DATE),
        "source_fact_ids": FACT_IDS,
        "verified_by_role": NONEMPTY_ROLE,
    }
)

MONITORING_SCHEMA = _object(
    {
        "monitoring_id": IDENTIFIER,
        "item_as_supplied": _text(minimum=1, maximum=2_000),
        "method_as_supplied": _text(maximum=1_000),
        "frequency_as_supplied": _text(maximum=1_000),
        "next_due_date": _nullable(DATE),
        "owner_role": NONEMPTY_ROLE,
        "source_fact_ids": FACT_IDS,
    }
)

CHECKPOINT_SCHEMA = _object(
    {
        "checkpoint_id": IDENTIFIER,
        "checkpoint_date": DATE,
        "purpose_as_supplied": _text(minimum=1, maximum=2_000),
        "owner_role": NONEMPTY_ROLE,
        "linked_goal_ids": _array(IDENTIFIER, maximum=100),
        "linked_intervention_ids": _array(IDENTIFIER, maximum=100),
        "source_fact_ids": FACT_IDS,
    }
)

OPTION_SCHEMA = _object(
    {
        "option_id": IDENTIFIER,
        "option_as_documented": _text(minimum=1, maximum=2_000),
        "source_fact_ids": FACT_IDS,
    }
)

SHARED_DECISION_SCHEMA = _object(
    {
        "decision_id": IDENTIFIER,
        "decision_topic_as_documented": _text(minimum=1, maximum=2_000),
        "options_as_documented": _array(OPTION_SCHEMA, minimum=1, maximum=50),
        "benefits_harms_uncertainty_documented": _boolean(),
        "preference_as_documented": _text(maximum=2_000),
        "outcome_as_documented": _text(maximum=2_000),
        "outcome_source_fact_ids": FACT_IDS,
        "decision_status": _text(
            enum={
                "pending_clinician_documentation",
                "documented_by_authorized_clinician",
            }
        ),
        "participant_roles": _array(
            _text(minimum=1, maximum=200), minimum=1, maximum=20
        ),
        "documented_by_role": ROLE,
        "documented_at": _nullable(DATETIME),
        "acknowledgment_status": _text(
            enum={
                "pending",
                "acknowledged",
                "not_applicable_by_authorized_clinician",
            }
        ),
    }
)

HANDOFF_ITEM_SCHEMA = _object(
    {
        "item_id": IDENTIFIER,
        "category": _text(
            enum={
                "medications",
                "interventions",
                "goals",
                "monitoring",
                "pending_results",
                "appointments",
                "equipment_or_services",
                "preferences_or_access_needs",
                "local_process_reference",
                "other_clinician_supplied",
            }
        ),
        "summary_as_supplied": _text(minimum=1, maximum=2_000),
        "source_fact_ids": FACT_IDS,
        "owner_role": NONEMPTY_ROLE,
        "recipient_role": NONEMPTY_ROLE,
        "acknowledgment_status": _text(
            enum={
                "pending",
                "acknowledged",
                "not_applicable_by_authorized_role",
            }
        ),
    }
)

UNRESOLVED_ITEM_SCHEMA = _object(
    {
        "item_id": IDENTIFIER,
        "issue_as_documented": _text(minimum=1, maximum=2_000),
        "source_fact_ids": FACT_IDS,
        "routed_to_local_role": ROLE,
        "status": _text(
            enum={
                "open_unrouted",
                "open_routed",
                "acknowledged_by_owner",
                "resolved_by_authorized_professional",
            }
        ),
    }
)

DOCUMENT_SCHEMAS = {
    "source_fact_manifest": _object(
        {
            **HEADER,
            "document_type": _text(const="source_fact_manifest"),
            "facts": _array(SOURCE_FACT_SCHEMA, maximum=500),
        }
    ),
    "clinician_authored_intervention_record": _object(
        {
            **HEADER,
            "document_type": _text(
                const="clinician_authored_intervention_record"
            ),
            "interventions": _array(INTERVENTION_SCHEMA, maximum=200),
        }
    ),
    "goals_monitoring_checkpoint_record": _object(
        {
            **HEADER,
            "document_type": _text(
                const="goals_monitoring_checkpoint_record"
            ),
            "goals": _array(GOAL_SCHEMA, maximum=200),
            "monitoring_items": _array(MONITORING_SCHEMA, maximum=300),
            "checkpoints": _array(CHECKPOINT_SCHEMA, maximum=500),
        }
    ),
    "informed_preference_shared_decision_record": _object(
        {
            **HEADER,
            "document_type": _text(
                const="informed_preference_shared_decision_record"
            ),
            "entries": _array(SHARED_DECISION_SCHEMA, maximum=100),
        }
    ),
    "transition_reconciliation_record": _object(
        {
            **HEADER,
            "document_type": _text(const="transition_reconciliation_record"),
            "transition": _object(
                {
                    "from_setting_as_documented": _text(maximum=500),
                    "to_setting_as_documented": _text(maximum=500),
                    "handoff_date": _nullable(DATE),
                    "responsible_sender_role": ROLE,
                    "responsible_receiver_role": ROLE,
                }
            ),
            "medication_reconciliation": _object(
                {
                    "status": _text(
                        enum={
                            "pending_authorized_review",
                            "completed_by_authorized_clinician",
                            "not_applicable_by_authorized_clinician",
                        }
                    ),
                    "source_list_fact_ids": _array(
                        IDENTIFIER, maximum=200
                    ),
                    "destination_list_fact_ids": _array(
                        IDENTIFIER, maximum=200
                    ),
                    "discrepancy_status": _text(
                        enum={
                            "not_assessed",
                            "none_documented",
                            "routed_to_authorized_clinician",
                            "resolved_by_authorized_clinician",
                        }
                    ),
                    "completed_by_role": ROLE,
                    "completed_at": _nullable(DATETIME),
                }
            ),
            "handoff_items": _array(HANDOFF_ITEM_SCHEMA, maximum=300),
            "unresolved_items": _array(
                UNRESOLVED_ITEM_SCHEMA, maximum=200
            ),
        }
    ),
    "intended_use_handoff_record": _object(
        {
            **HEADER,
            "document_type": _text(const="intended_use_handoff_record"),
            "intended_use": _object(
                {
                    "purpose": _text(
                        const=(
                            "format_and_validate_clinician_supplied_plan_"
                            "documentation"
                        )
                    ),
                    "intended_users": _array(
                        _text(minimum=1, maximum=200), maximum=50
                    ),
                    "intended_setting": _text(maximum=500),
                    "output_role": _text(const="documentation_only"),
                    "prohibited_uses": _array(
                        _text(enum=PROHIBITED_USES),
                        minimum=len(PROHIBITED_USES),
                        maximum=len(PROHIBITED_USES),
                    ),
                }
            ),
            "privacy_process": _object(
                {
                    "data_classification": _text(
                        enum={
                            "synthetic",
                            "deidentified_qualified_review",
                            "real_patient_minimum_necessary",
                        }
                    ),
                    "local_authorization_confirmed": _boolean(),
                    "authorized_environment_reference": _text(
                        maximum=1_000
                    ),
                    "minimum_necessary_confirmed": _boolean(),
                    "no_external_tools_confirmed": _boolean(),
                    "no_prompt_log_example_copy_confirmed": _boolean(),
                    "privacy_review_status": _text(
                        enum={
                            "pending",
                            "not_applicable_synthetic",
                            "completed_by_qualified_reviewer",
                        }
                    ),
                    "privacy_reviewer_role": ROLE,
                    "reviewed_at": _nullable(DATETIME),
                    "retention_policy_reference": _text(maximum=1_000),
                    "data_disposition_status": _text(
                        enum={
                            "pending",
                            "retain_under_local_policy",
                            "delete_under_local_policy",
                            "completed_under_local_policy",
                        }
                    ),
                }
            ),
            "local_governance": _object(
                {
                    "institution_or_organization_reference": _text(
                        maximum=1_000
                    ),
                    "clinical_owner_role": ROLE,
                    "policy_references": _array(
                        _text(minimum=1, maximum=1_000), maximum=100
                    ),
                    "records_owner_role": ROLE,
                    "change_control_owner_role": ROLE,
                }
            ),
            "emergency_routing": _object(
                {
                    "statement": _text(const=EMERGENCY_STATEMENT),
                    "local_process_reference": _text(maximum=1_000),
                    "verified_by_role": ROLE,
                }
            ),
            "reporting_routes": _object(
                {
                    "local_patient_safety_route": _text(maximum=1_000),
                    "product_event_route": _text(maximum=1_000),
                    "privacy_incident_route": _text(maximum=1_000),
                    "responsible_role": ROLE,
                }
            ),
            "handoff": _object(
                {
                    "sender_role": ROLE,
                    "recipient_role": ROLE,
                    "sent_at": _nullable(DATETIME),
                    "acknowledgment_status": _text(
                        enum={"pending", "acknowledged"}
                    ),
                    "unresolved_items_routed": _boolean(),
                }
            ),
            "clinician_signoff": _object(
                {
                    "status": _text(enum={"pending", "signed"}),
                    "signer_role": ROLE,
                    "credential_authority_reference": _text(
                        maximum=1_000
                    ),
                    "signed_at": _nullable(DATETIME),
                    "attestation": _text(const=SIGNOFF_ATTESTATION),
                }
            ),
            "release_gate": _object(
                {
                    "status": _text(
                        enum={
                            "blocked",
                            "released_for_authorized_documentation_handoff",
                        }
                    ),
                    "released_by_role": ROLE,
                    "released_at": _nullable(DATETIME),
                    "blocker_codes": _array(
                        _text(
                            minimum=3,
                            maximum=96,
                            pattern=BLOCKER_RE.pattern,
                        ),
                        maximum=100,
                    ),
                }
            ),
        }
    ),
}


def _reject_nonlocal_path(raw_path: str | Path) -> Path:
    text = str(raw_path)
    lowered = text.strip().lower()
    if not lowered or "\x00" in text or "://" in lowered:
        raise ValidationError("NONLOCAL_OR_EMPTY_PATH")
    if lowered.startswith(("\\\\", "//")):
        raise ValidationError("NETWORK_SHARE_PATH_REJECTED")
    return Path(text).expanduser()


def safe_input_file(raw_path: str | Path) -> Path:
    """Resolve one bounded, regular, non-symlink local JSON file."""

    path = _reject_nonlocal_path(raw_path)
    if path.is_symlink():
        raise ValidationError("SYMLINK_INPUT_REJECTED")
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValidationError("INPUT_FILE_MISSING", path.name) from exc
    if not resolved.is_file() or resolved.suffix.lower() != ".json":
        raise ValidationError("INPUT_MUST_BE_JSON_FILE", path.name)
    if resolved.stat().st_size > MAX_INPUT_BYTES:
        raise ValidationError("INPUT_FILE_TOO_LARGE", path.name)
    return resolved


def safe_input_directory(raw_path: str | Path) -> Path:
    """Resolve one local, non-symlink directory."""

    path = _reject_nonlocal_path(raw_path)
    if path.is_symlink():
        raise ValidationError("SYMLINK_DIRECTORY_REJECTED")
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValidationError("INPUT_DIRECTORY_MISSING") from exc
    if not resolved.is_dir():
        raise ValidationError("INPUT_MUST_BE_DIRECTORY")
    return resolved


def safe_new_directory(raw_path: str | Path) -> Path:
    """Create a private directory without reusing an existing path."""

    path = _reject_nonlocal_path(raw_path)
    if path.exists() or path.is_symlink():
        raise ValidationError("OUTPUT_DIRECTORY_EXISTS")
    try:
        parent = path.parent.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValidationError("OUTPUT_PARENT_MISSING") from exc
    if not parent.is_dir():
        raise ValidationError("OUTPUT_PARENT_NOT_DIRECTORY")
    resolved = parent / path.name
    resolved.mkdir(mode=0o700)
    return resolved


def safe_output_file(raw_path: str | Path) -> Path:
    """Resolve a new local JSON output without implicit overwrite."""

    path = _reject_nonlocal_path(raw_path)
    if path.suffix.lower() != ".json":
        raise ValidationError("OUTPUT_MUST_BE_JSON")
    try:
        parent = path.parent.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValidationError("OUTPUT_PARENT_MISSING") from exc
    if not parent.is_dir():
        raise ValidationError("OUTPUT_PARENT_NOT_DIRECTORY")
    resolved = parent / path.name
    if resolved.exists() or resolved.is_symlink():
        raise ValidationError("OUTPUT_ALREADY_EXISTS", resolved.name)
    return resolved


def _duplicate_safe_object(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError("JSON_DUPLICATE_KEY")
        result[key] = value
    return result


def _reject_constant(_: str) -> None:
    raise ValidationError("JSON_NONFINITE_NUMBER")


def _check_bounds(value: Any, *, depth: int = 0, counter: list[int]) -> None:
    if depth > MAX_DEPTH:
        raise ValidationError("JSON_MAX_DEPTH_EXCEEDED")
    counter[0] += 1
    if counter[0] > MAX_TOTAL_NODES:
        raise ValidationError("JSON_NODE_LIMIT_EXCEEDED")
    if isinstance(value, dict):
        if len(value) > MAX_OBJECT_FIELDS:
            raise ValidationError("JSON_OBJECT_FIELD_LIMIT_EXCEEDED")
        for key, nested in value.items():
            if not isinstance(key, str) or len(key) > 128:
                raise ValidationError("JSON_KEY_INVALID")
            _check_bounds(nested, depth=depth + 1, counter=counter)
    elif isinstance(value, list):
        if len(value) > MAX_LIST_ITEMS:
            raise ValidationError("JSON_LIST_LIMIT_EXCEEDED")
        for nested in value:
            _check_bounds(nested, depth=depth + 1, counter=counter)
    elif isinstance(value, str):
        if len(value) > MAX_TEXT_CHARS:
            raise ValidationError("JSON_TEXT_LIMIT_EXCEEDED")


def read_json(raw_path: str | Path) -> dict[str, Any]:
    """Read strict UTF-8 JSON without exposing values in failures."""

    path = safe_input_file(raw_path)
    try:
        with path.open("rb") as handle:
            raw = handle.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise ValidationError("INPUT_FILE_TOO_LARGE", path.name)
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError("JSON_NOT_UTF8", path.name) from exc
    except OSError as exc:
        raise ValidationError("INPUT_READ_FAILED", path.name) from exc
    if "\x00" in text:
        raise ValidationError("JSON_CONTAINS_NUL", path.name)
    try:
        value = json.loads(
            text,
            object_pairs_hook=_duplicate_safe_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise ValidationError(
            "JSON_PARSE_ERROR", f"{path.name}:{exc.lineno}:{exc.colno}"
        ) from exc
    except RecursionError as exc:
        raise ValidationError("JSON_MAX_DEPTH_EXCEEDED") from exc
    except ValidationError:
        raise
    except ValueError as exc:
        raise ValidationError("JSON_NUMBER_INVALID") from exc
    if not isinstance(value, dict):
        raise ValidationError("JSON_ROOT_NOT_OBJECT", path.name)
    _check_bounds(value, counter=[0])
    return value


def load_package(
    raw_directory: str | Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, Path]]:
    """Load the six required package records by fixed local filename."""

    root = safe_input_directory(raw_directory)
    documents: dict[str, dict[str, Any]] = {}
    paths: dict[str, Path] = {}
    for expected_type, (_, filename) in TEMPLATE_FILES.items():
        path = root / filename
        if not path.exists():
            raise ValidationError("PACKAGE_FILE_MISSING", filename)
        document = read_json(path)
        documents[expected_type] = document
        paths[expected_type] = path
    return documents, paths


def load_target(
    raw_path: str | Path, *, require_package: bool = False
) -> tuple[dict[str, dict[str, Any]], dict[str, Path]]:
    """Load one record or a complete package."""

    path = _reject_nonlocal_path(raw_path)
    if path.is_dir() and not path.is_symlink():
        return load_package(path)
    if require_package:
        raise ValidationError("PACKAGE_DIRECTORY_REQUIRED")
    document = read_json(path)
    document_type = document.get("document_type")
    if not isinstance(document_type, str):
        raise ValidationError("DOCUMENT_TYPE_MISSING")
    return {document_type: document}, {document_type: safe_input_file(path)}


def _valid_iso_date(value: str) -> bool:
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def parse_iso_datetime(value: str) -> datetime | None:
    """Parse an extended calendar datetime with seconds and an explicit offset."""

    if not isinstance(value, str) or DATETIME_RE.fullmatch(value) is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _validate_schema(
    value: Any,
    schema: dict[str, Any],
    path: str,
    issues: list[Issue],
) -> None:
    kind = schema["kind"]
    if kind == "nullable":
        if value is None:
            return
        _validate_schema(value, schema["schema"], path, issues)
        return
    if kind == "object":
        if not isinstance(value, dict):
            issues.append(Issue("SCHEMA_TYPE_OBJECT", path))
            return
        properties = schema["properties"]
        for key in sorted(set(properties) - set(value)):
            issues.append(Issue("SCHEMA_REQUIRED_FIELD", f"{path}.{key}"))
        for _ in set(value) - set(properties):
            # Unknown keys may themselves contain identifying or clinical text.
            issues.append(Issue("SCHEMA_UNKNOWN_FIELD", f"{path}.[unknown_field]"))
        for key in properties.keys() & value.keys():
            _validate_schema(
                value[key], properties[key], f"{path}.{key}", issues
            )
        return
    if kind == "array":
        if not isinstance(value, list):
            issues.append(Issue("SCHEMA_TYPE_ARRAY", path))
            return
        if not schema["minimum"] <= len(value) <= schema["maximum"]:
            issues.append(Issue("SCHEMA_ARRAY_BOUNDS", path))
        for index, nested in enumerate(value):
            _validate_schema(
                nested, schema["item"], f"{path}[{index}]", issues
            )
        return
    if kind == "boolean":
        if type(value) is not bool:
            issues.append(Issue("SCHEMA_TYPE_BOOLEAN", path))
        return
    if kind == "string":
        if not isinstance(value, str):
            issues.append(Issue("SCHEMA_TYPE_STRING", path))
            return
        if not schema["minimum"] <= len(value) <= schema["maximum"]:
            issues.append(Issue("SCHEMA_STRING_BOUNDS", path))
        if schema["minimum"] and not value.strip():
            issues.append(Issue("SCHEMA_STRING_BLANK", path))
        if schema["const"] is not None and value != schema["const"]:
            issues.append(Issue("SCHEMA_CONST", path))
        if schema["enum"] is not None and value not in schema["enum"]:
            issues.append(Issue("SCHEMA_ENUM", path))
        if schema["pattern"] is not None and not schema["pattern"].fullmatch(
            value
        ):
            issues.append(Issue("SCHEMA_PATTERN", path))
        if schema["format"] == "date" and not _valid_iso_date(value):
            issues.append(Issue("SCHEMA_ISO_DATE", path))
        if schema["format"] == "datetime" and parse_iso_datetime(value) is None:
            issues.append(Issue("SCHEMA_ISO_DATETIME", path))
        return
    issues.append(Issue("SCHEMA_INTERNAL_KIND", path))


def _duplicate_field_issues(
    records: Any, field: str, path: str
) -> list[Issue]:
    if not isinstance(records, list):
        return []
    seen: set[str] = set()
    issues: list[Issue] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            continue
        value = record.get(field)
        if isinstance(value, str):
            if value in seen:
                issues.append(
                    Issue("DUPLICATE_RECORD_ID", f"{path}[{index}].{field}")
                )
            seen.add(value)
    return issues


def validate_document(
    document: dict[str, Any], expected_type: str | None = None
) -> list[Issue]:
    """Validate strict structure without evaluating clinical content."""

    document_type = document.get("document_type")
    if not isinstance(document_type, str):
        return [Issue("DOCUMENT_TYPE_MISSING", "$.document_type")]
    if expected_type is not None and document_type != expected_type:
        return [Issue("DOCUMENT_TYPE_FILENAME_MISMATCH", "$.document_type")]
    schema = DOCUMENT_SCHEMAS.get(document_type)
    if schema is None:
        return [Issue("DOCUMENT_TYPE_UNKNOWN", "$.document_type")]
    issues: list[Issue] = []
    _validate_schema(document, schema, "$", issues)

    if document_type == "source_fact_manifest":
        issues.extend(
            _duplicate_field_issues(document.get("facts"), "fact_id", "$.facts")
        )
    elif document_type == "clinician_authored_intervention_record":
        interventions = document.get("interventions")
        issues.extend(
            _duplicate_field_issues(
                interventions, "intervention_id", "$.interventions"
            )
        )
        if isinstance(interventions, list):
            for index, record in enumerate(interventions):
                if isinstance(record, dict):
                    issues.extend(
                        _duplicate_field_issues(
                            record.get("parameters_as_supplied"),
                            "parameter_id",
                            f"$.interventions[{index}].parameters_as_supplied",
                        )
                    )
    elif document_type == "goals_monitoring_checkpoint_record":
        for field, identifier_field in (
            ("goals", "goal_id"),
            ("monitoring_items", "monitoring_id"),
            ("checkpoints", "checkpoint_id"),
        ):
            issues.extend(
                _duplicate_field_issues(
                    document.get(field), identifier_field, f"$.{field}"
                )
            )
    elif document_type == "informed_preference_shared_decision_record":
        entries = document.get("entries")
        issues.extend(
            _duplicate_field_issues(entries, "decision_id", "$.entries")
        )
        if isinstance(entries, list):
            for index, record in enumerate(entries):
                if isinstance(record, dict):
                    issues.extend(
                        _duplicate_field_issues(
                            record.get("options_as_documented"),
                            "option_id",
                            f"$.entries[{index}].options_as_documented",
                        )
                    )
    elif document_type == "transition_reconciliation_record":
        for field in ("handoff_items", "unresolved_items"):
            issues.extend(
                _duplicate_field_issues(
                    document.get(field), "item_id", f"$.{field}"
                )
            )
    elif document_type == "intended_use_handoff_record":
        intended = document.get("intended_use")
        if isinstance(intended, dict):
            uses = intended.get("prohibited_uses")
            if isinstance(uses, list) and (
                any(not isinstance(item, str) for item in uses)
                or set(uses) != PROHIBITED_USES
            ):
                issues.append(
                    Issue(
                        "PROHIBITED_USE_SET_CHANGED",
                        "$.intended_use.prohibited_uses",
                    )
                )
    return sorted(issues, key=lambda item: (item.path, item.code))


def validate_package_structure(
    documents: dict[str, dict[str, Any]]
) -> list[Issue]:
    """Validate all package documents and prefix paths with document types."""

    issues: list[Issue] = []
    for expected_type in TEMPLATE_FILES:
        document = documents.get(expected_type)
        if document is None:
            issues.append(Issue("PACKAGE_DOCUMENT_MISSING", expected_type))
            continue
        for issue in validate_document(document, expected_type):
            issues.append(
                Issue(
                    issue.code,
                    f"{expected_type}:{issue.path}",
                    issue.level,
                )
            )
    return sorted(issues, key=lambda item: (item.path, item.code))


def has_errors(issues: Iterable[Issue]) -> bool:
    return any(issue.level == "error" for issue in issues)


def report_payload(
    check: str,
    issues: Iterable[Issue],
    *,
    counts: dict[str, int] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    issue_list = list(issues)
    payload: dict[str, Any] = {
        "check": check,
        "status": "fail" if has_errors(issue_list) else "pass",
        "issues": [item.as_dict() for item in issue_list],
        "counts": counts or {},
        "notice": NOTICE,
        "determinations_not_made": [
            "clinical_correctness",
            "clinical_safety",
            "diagnosis",
            "therapy_or_medication_selection",
            "dose_or_schedule",
            "interaction_or_contraindication",
            "triage_or_emergency_status",
            "prognosis",
            "privacy_or_legal_compliance",
        ],
    }
    if extra:
        payload.update(extra)
    return payload


def error_report(check: str, error: ValidationError) -> dict[str, Any]:
    return report_payload(check, [Issue(error.code, error.path)])


def print_report(report: dict[str, Any]) -> None:
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))


def atomic_write_json(destination: Path, payload: dict[str, Any]) -> Path:
    """Write private JSON atomically without implicit overwrite."""

    if destination.exists() or destination.is_symlink():
        raise ValidationError("OUTPUT_ALREADY_EXISTS", destination.name)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_name = handle.name
            json.dump(
                payload,
                handle,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_name, 0o600)
        # Publish a completed file without replacing a path created by another
        # writer after the initial existence check. Fail on filesystems without
        # hard-link support rather than fall back to a clobbering rename.
        os.link(temporary_name, destination)
        Path(temporary_name).unlink()
        return destination
    except FileExistsError as exc:
        raise ValidationError("OUTPUT_ALREADY_EXISTS", destination.name) from exc
    except OSError as exc:
        raise ValidationError("OUTPUT_WRITE_FAILED", destination.name) from exc
    finally:
        if temporary_name:
            try:
                Path(temporary_name).unlink(missing_ok=True)
            except OSError:
                pass


def copy_template_document(
    template_path: Path,
    *,
    subject_ref: str,
    classification: str,
) -> dict[str, Any]:
    document = read_json(template_path)
    document["subject_ref"] = subject_ref
    document["data_classification"] = classification
    if document.get("document_type") == "intended_use_handoff_record":
        privacy = document.get("privacy_process")
        if isinstance(privacy, dict):
            privacy["data_classification"] = classification
    return document


def direct_identifier_key_paths(
    value: Any, path: str = "$"
) -> list[str]:
    """Return paths for obvious direct-identifier field names, not values."""

    matches: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).strip().lower()
            nested_path = f"{path}.{key}"
            if normalized in DIRECT_IDENTIFIER_KEYS:
                matches.append(nested_path)
            matches.extend(direct_identifier_key_paths(nested, nested_path))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            matches.extend(
                direct_identifier_key_paths(nested, f"{path}[{index}]")
            )
    return matches


def all_fact_references(
    documents: dict[str, dict[str, Any]]
) -> list[tuple[str, str]]:
    """Collect every source-fact reference with a nonclinical field path."""

    references: list[tuple[str, str]] = []

    def collect(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                nested_path = f"{path}.{key}"
                if key.endswith("fact_ids") and isinstance(nested, list):
                    for index, identifier in enumerate(nested):
                        if isinstance(identifier, str):
                            references.append(
                                (f"{nested_path}[{index}]", identifier)
                            )
                else:
                    collect(nested, nested_path)
        elif isinstance(value, list):
            for index, nested in enumerate(value):
                collect(nested, f"{path}[{index}]")

    for document_type, document in documents.items():
        if document_type != "source_fact_manifest":
            collect(document, document_type)
    return references


def record_ids(
    document: dict[str, Any],
    list_field: str,
    id_field: str,
) -> set[str]:
    records = document.get(list_field)
    if not isinstance(records, list):
        return set()
    return {
        record[id_field]
        for record in records
        if isinstance(record, dict) and isinstance(record.get(id_field), str)
    }
