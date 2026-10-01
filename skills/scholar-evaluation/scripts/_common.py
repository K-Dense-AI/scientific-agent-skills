#!/usr/bin/env python3
"""Bounded, dependency-free helpers for local scholar-evaluation records."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "2.0"
NOTICE = (
    "DESCRIPTIVE DEVELOPMENTAL ASSESSMENT ONLY - NOT A DECISION "
    "RECOMMENDATION - QUALIFIED HUMAN REVIEW REQUIRED"
)
PROHIBITED_USES = {
    "admissions",
    "awards",
    "discipline",
    "funding",
    "hiring",
    "promotion",
    "tenure",
    "other_high_impact_personnel_decision",
}
ALLOWED_PURPOSE = "developmental_review_of_scholarly_work"
ALLOWED_UNIT = "scholarly_work"
ALLOWED_CLASSIFICATIONS = (
    "synthetic",
    "public_scholarly_work",
    "deidentified_low_stakes",
)
RATING_STATUSES = ("rated", "missing", "not_applicable")

MAX_INPUT_BYTES = 2 * 1024 * 1024
MAX_OUTPUT_BYTES = 2 * 1024 * 1024
MAX_TEXT_CHARS = 4_000
MAX_LIST_ITEMS = 1_000
MAX_OBJECT_FIELDS = 100
MAX_DEPTH = 20
MAX_TOTAL_NODES = 25_000
MAX_CRITERIA = 50
MAX_EVALUATIONS = 50
MAX_CSV_ROWS = 20_000

IDENTIFIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._:-]{1,95}$")
PRIVATE_FIELD_KEYS = {
    "applicant_name",
    "application_text",
    "candidate_name",
    "cv_text",
    "date_of_birth",
    "dob",
    "document_text",
    "email",
    "full_name",
    "home_address",
    "person_name",
    "phone",
    "private_application",
    "raw_application",
    "resume_text",
    "social_security_number",
    "ssn",
}
PROXY_TERMS = (
    "journal impact factor",
    "impact factor",
    "h-index",
    "h index",
    "citation count",
    "altmetric",
    "conference ranking",
    "journal ranking",
    "institution prestige",
    "journal prestige",
    "venue prestige",
    "university ranking",
)


class ValidationError(ValueError):
    """A deterministic input failure that never includes a supplied value."""

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


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError("JSON_DUPLICATE_KEY")
        result[key] = value
    return result


def _check_local_file(path: Path, suffix: str) -> None:
    if path.suffix.lower() != suffix:
        raise ValidationError("INPUT_SUFFIX_NOT_ALLOWED")
    if not path.exists():
        raise ValidationError("INPUT_NOT_FOUND")
    if path.is_symlink():
        raise ValidationError("INPUT_SYMLINK_NOT_ALLOWED")
    if not path.is_file():
        raise ValidationError("INPUT_NOT_REGULAR_FILE")
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ValidationError("INPUT_TOO_LARGE")


def _scan_structure(value: Any, path: str = "$") -> None:
    nodes = 0
    stack: list[tuple[Any, str, int]] = [(value, path, 0)]
    while stack:
        current, current_path, depth = stack.pop()
        nodes += 1
        if nodes > MAX_TOTAL_NODES:
            raise ValidationError("STRUCTURE_TOO_LARGE", current_path)
        if depth > MAX_DEPTH:
            raise ValidationError("STRUCTURE_TOO_DEEP", current_path)
        if isinstance(current, dict):
            if len(current) > MAX_OBJECT_FIELDS:
                raise ValidationError("OBJECT_TOO_LARGE", current_path)
            for key, child in current.items():
                if not isinstance(key, str):
                    raise ValidationError("OBJECT_KEY_NOT_TEXT", current_path)
                normalized = key.strip().lower()
                if normalized in PRIVATE_FIELD_KEYS:
                    raise ValidationError("PRIVATE_FIELD_NOT_ALLOWED", f"{current_path}.{key}")
                stack.append((child, f"{current_path}.{key}", depth + 1))
        elif isinstance(current, list):
            if len(current) > MAX_LIST_ITEMS:
                raise ValidationError("LIST_TOO_LARGE", current_path)
            for index, child in enumerate(current):
                stack.append((child, f"{current_path}[{index}]", depth + 1))
        elif isinstance(current, str) and len(current) > MAX_TEXT_CHARS:
            raise ValidationError("TEXT_TOO_LONG", current_path)
        elif current is not None and not isinstance(
            current, (str, int, float, bool)
        ):
            raise ValidationError("VALUE_TYPE_NOT_ALLOWED", current_path)
        if isinstance(current, float) and not math.isfinite(current):
            raise ValidationError("NUMBER_NOT_FINITE", current_path)


def read_json(path: Path | str) -> Any:
    """Read bounded JSON with duplicate-key and private-field rejection."""

    local_path = Path(path)
    _check_local_file(local_path, ".json")
    try:
        data = json.loads(
            local_path.read_text(encoding="utf-8"),
            object_pairs_hook=_pairs_no_duplicates,
        )
    except UnicodeDecodeError as error:
        raise ValidationError("INPUT_NOT_UTF8") from error
    except (json.JSONDecodeError, RecursionError) as error:
        raise ValidationError("JSON_INVALID") from error
    _scan_structure(data)
    return data


def read_csv_text(path: Path | str) -> str:
    """Read a bounded UTF-8 CSV file after local-path checks."""

    local_path = Path(path)
    _check_local_file(local_path, ".csv")
    try:
        return local_path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValidationError("INPUT_NOT_UTF8") from error


def write_json(
    value: dict[str, Any], output: Path | None, *, force: bool = False
) -> None:
    """Write deterministic JSON locally or print it to standard output."""

    rendered = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if len(rendered.encode("utf-8")) > MAX_OUTPUT_BYTES:
        raise ValidationError("OUTPUT_TOO_LARGE")
    if output is None:
        print(rendered, end="")
        return
    if output.suffix.lower() != ".json":
        raise ValidationError("OUTPUT_SUFFIX_NOT_ALLOWED")
    if output.is_symlink():
        raise ValidationError("OUTPUT_SYMLINK_NOT_ALLOWED")
    if output.exists() and not force:
        raise ValidationError("OUTPUT_EXISTS")
    if not output.parent.exists() or not output.parent.is_dir():
        raise ValidationError("OUTPUT_PARENT_NOT_FOUND")
    output.write_text(rendered, encoding="utf-8")


def failure_report(error: ValidationError) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "error",
        "issues": [Issue(error.code, error.path).as_dict()],
    }


def is_number(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def is_identifier(value: Any) -> bool:
    return isinstance(value, str) and bool(IDENTIFIER_RE.fullmatch(value))


def is_nonempty_text(value: Any, maximum: int = MAX_TEXT_CHARS) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= maximum


def is_reference(value: Any) -> bool:
    if not is_nonempty_text(value, 500):
        return False
    lowered = value.strip().lower()
    return not (
        lowered.startswith(("http://", "https://", "file://"))
        or "\n" in value
        or "\r" in value
    )


def is_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return len(value) == 10


def exact_keys(
    value: Any,
    expected: Iterable[str],
    path: str,
    issues: list[Issue],
) -> bool:
    if not isinstance(value, dict):
        issues.append(Issue("SCHEMA_OBJECT_REQUIRED", path))
        return False
    expected_set = set(expected)
    actual_set = set(value)
    for missing in sorted(expected_set - actual_set):
        issues.append(Issue("SCHEMA_REQUIRED_FIELD", f"{path}.{missing}"))
    for unknown in sorted(actual_set - expected_set):
        issues.append(Issue("SCHEMA_UNKNOWN_FIELD", f"{path}.{unknown}"))
    return not (expected_set - actual_set)


def validate_identifier(
    value: Any, path: str, issues: list[Issue], code: str = "IDENTIFIER_INVALID"
) -> None:
    if not is_identifier(value):
        issues.append(Issue(code, path))


def validate_reference(
    value: Any, path: str, issues: list[Issue], *, allow_empty: bool = False
) -> None:
    if allow_empty and value == "":
        return
    if not is_reference(value):
        issues.append(Issue("LOCAL_REFERENCE_INVALID", path))


def validate_text(
    value: Any, path: str, issues: list[Issue], *, allow_empty: bool = False
) -> None:
    if allow_empty and value == "":
        return
    if not is_nonempty_text(value):
        issues.append(Issue("TEXT_INVALID", path))


def validate_bool(value: Any, path: str, issues: list[Issue]) -> None:
    if not isinstance(value, bool):
        issues.append(Issue("BOOLEAN_REQUIRED", path))


def validate_text_list(
    value: Any,
    path: str,
    issues: list[Issue],
    *,
    minimum: int = 0,
    maximum: int = 100,
    references: bool = False,
) -> None:
    if not isinstance(value, list):
        issues.append(Issue("LIST_REQUIRED", path))
        return
    if not minimum <= len(value) <= maximum:
        issues.append(Issue("LIST_LENGTH_INVALID", path))
    for index, item in enumerate(value):
        if references:
            validate_reference(item, f"{path}[{index}]", issues)
        else:
            validate_text(item, f"{path}[{index}]", issues)


def _validate_scale(scale: Any, issues: list[Issue]) -> tuple[float, float, float]:
    path = "$.scale"
    expected = {"minimum", "maximum", "step", "anchors"}
    if not exact_keys(scale, expected, path, issues):
        return 0.0, 0.0, 1.0
    minimum = scale.get("minimum")
    maximum = scale.get("maximum")
    step = scale.get("step")
    if not is_number(minimum) or not is_number(maximum) or not is_number(step):
        issues.append(Issue("SCALE_NUMBER_REQUIRED", path))
        return 0.0, 0.0, 1.0
    minimum_f = float(minimum)
    maximum_f = float(maximum)
    step_f = float(step)
    if minimum_f < 0 or maximum_f <= minimum_f or maximum_f - minimum_f > 10:
        issues.append(Issue("SCALE_BOUNDS_INVALID", path))
    if step_f <= 0 or step_f > maximum_f - minimum_f:
        issues.append(Issue("SCALE_STEP_INVALID", f"{path}.step"))
    anchors = scale.get("anchors")
    if not isinstance(anchors, list) or not 2 <= len(anchors) <= 21:
        issues.append(Issue("SCALE_ANCHORS_INVALID", f"{path}.anchors"))
        return minimum_f, maximum_f, step_f
    anchor_scores: list[float] = []
    for index, anchor in enumerate(anchors):
        anchor_path = f"{path}.anchors[{index}]"
        if not exact_keys(anchor, {"score", "label", "description"}, anchor_path, issues):
            continue
        score = anchor.get("score")
        if not is_number(score):
            issues.append(Issue("ANCHOR_SCORE_INVALID", f"{anchor_path}.score"))
        else:
            anchor_scores.append(float(score))
        validate_text(anchor.get("label"), f"{anchor_path}.label", issues)
        validate_text(anchor.get("description"), f"{anchor_path}.description", issues)
    if anchor_scores:
        if len(anchor_scores) != len(set(anchor_scores)):
            issues.append(Issue("ANCHOR_SCORE_DUPLICATE", f"{path}.anchors"))
        if min(anchor_scores) != minimum_f or max(anchor_scores) != maximum_f:
            issues.append(Issue("ANCHOR_BOUNDS_MISSING", f"{path}.anchors"))
        ordered = sorted(anchor_scores)
        if any(
            not math.isclose(right - left, step_f, rel_tol=1e-9, abs_tol=0.0)
            for left, right in zip(ordered, ordered[1:])
        ):
            issues.append(Issue("ANCHOR_STEP_MISMATCH", f"{path}.anchors"))
    return minimum_f, maximum_f, step_f


def _validate_proxy_absence(value: Any, path: str, issues: list[Issue]) -> None:
    strings: list[str] = []
    stack = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, str):
            strings.append(current.lower())
        elif isinstance(current, list):
            stack.extend(current)
        elif isinstance(current, dict):
            stack.extend(current.values())
    combined = "\n".join(strings)
    if any(term in combined for term in PROXY_TERMS):
        issues.append(Issue("PROXY_METRIC_CRITERION_PROHIBITED", path))


def validate_rubric(rubric: Any) -> list[Issue]:
    """Validate the strict local rubric schema."""

    issues: list[Issue] = []
    top_keys = {
        "schema_version",
        "rubric_id",
        "title",
        "intended_use",
        "construct",
        "provenance",
        "scale",
        "criteria",
        "rater_protocol",
        "governance",
    }
    if not exact_keys(rubric, top_keys, "$", issues):
        return issues
    if rubric.get("schema_version") != SCHEMA_VERSION:
        issues.append(Issue("SCHEMA_VERSION_UNSUPPORTED", "$.schema_version"))
    validate_identifier(rubric.get("rubric_id"), "$.rubric_id", issues)
    validate_text(rubric.get("title"), "$.title", issues)

    intended = rubric.get("intended_use")
    if exact_keys(
        intended,
        {"purpose", "unit_of_assessment", "allowed_contexts", "prohibited_uses"},
        "$.intended_use",
        issues,
    ):
        if intended.get("purpose") != ALLOWED_PURPOSE:
            issues.append(Issue("PURPOSE_NOT_ALLOWED", "$.intended_use.purpose"))
        if intended.get("unit_of_assessment") != ALLOWED_UNIT:
            issues.append(
                Issue("UNIT_OF_ASSESSMENT_NOT_ALLOWED", "$.intended_use.unit_of_assessment")
            )
        validate_text_list(
            intended.get("allowed_contexts"),
            "$.intended_use.allowed_contexts",
            issues,
            minimum=1,
            maximum=20,
        )
        prohibited = intended.get("prohibited_uses")
        validate_text_list(
            prohibited,
            "$.intended_use.prohibited_uses",
            issues,
            minimum=len(PROHIBITED_USES),
            maximum=30,
        )
        prohibited_set = (
            set(prohibited)
            if isinstance(prohibited, list)
            and all(isinstance(item, str) for item in prohibited)
            else set()
        )
        if isinstance(prohibited, list) and not PROHIBITED_USES.issubset(
            prohibited_set
        ):
            issues.append(
                Issue("PROHIBITED_USES_INCOMPLETE", "$.intended_use.prohibited_uses")
            )

    construct = rubric.get("construct")
    if exact_keys(
        construct,
        {"label", "definition", "boundaries", "limitations"},
        "$.construct",
        issues,
    ):
        validate_text(construct.get("label"), "$.construct.label", issues)
        validate_text(construct.get("definition"), "$.construct.definition", issues)
        validate_text_list(
            construct.get("boundaries"),
            "$.construct.boundaries",
            issues,
            minimum=1,
            maximum=20,
        )
        validate_text_list(
            construct.get("limitations"),
            "$.construct.limitations",
            issues,
            minimum=1,
            maximum=20,
        )

    provenance = rubric.get("provenance")
    if exact_keys(
        provenance,
        {
            "rubric_version",
            "owner_role",
            "source_ids",
            "content_validity_status",
            "content_validity_evidence_ref",
            "last_reviewed_date",
        },
        "$.provenance",
        issues,
    ):
        validate_text(provenance.get("rubric_version"), "$.provenance.rubric_version", issues)
        validate_text(provenance.get("owner_role"), "$.provenance.owner_role", issues)
        validate_text_list(
            provenance.get("source_ids"),
            "$.provenance.source_ids",
            issues,
            minimum=1,
            maximum=50,
            references=True,
        )
        validity_status = provenance.get("content_validity_status")
        if validity_status not in ("not_established", "pilot_evidence", "documented"):
            issues.append(
                Issue(
                    "CONTENT_VALIDITY_STATUS_INVALID",
                    "$.provenance.content_validity_status",
                )
            )
        validate_reference(
            provenance.get("content_validity_evidence_ref"),
            "$.provenance.content_validity_evidence_ref",
            issues,
            allow_empty=validity_status == "not_established",
        )
        if validity_status != "documented":
            issues.append(
                Issue(
                    "CONTENT_VALIDITY_NOT_DOCUMENTED",
                    "$.provenance.content_validity_status",
                    "warning",
                )
            )
        if not is_date(provenance.get("last_reviewed_date")):
            issues.append(Issue("DATE_INVALID", "$.provenance.last_reviewed_date"))

    scale_object = rubric.get("scale")
    minimum, maximum, step = _validate_scale(scale_object, issues)
    raw_scale_anchors = (
        scale_object.get("anchors") if isinstance(scale_object, dict) else []
    )
    if not isinstance(raw_scale_anchors, list):
        raw_scale_anchors = []
    scale_anchor_scores = {
        float(anchor["score"])
        for anchor in raw_scale_anchors
        if isinstance(anchor, dict) and is_number(anchor.get("score"))
    }

    criteria = rubric.get("criteria")
    criterion_ids: set[str] = set()
    total_weight = 0.0
    if not isinstance(criteria, list) or not 1 <= len(criteria) <= MAX_CRITERIA:
        issues.append(Issue("CRITERIA_INVALID", "$.criteria"))
    else:
        for index, criterion in enumerate(criteria):
            path = f"$.criteria[{index}]"
            if not exact_keys(
                criterion,
                {
                    "criterion_id",
                    "label",
                    "construct_component",
                    "weight",
                    "required",
                    "anchors",
                    "evidence_requirements",
                    "limitations",
                },
                path,
                issues,
            ):
                continue
            criterion_id = criterion.get("criterion_id")
            validate_identifier(criterion_id, f"{path}.criterion_id", issues)
            if isinstance(criterion_id, str):
                if criterion_id in criterion_ids:
                    issues.append(Issue("CRITERION_ID_DUPLICATE", f"{path}.criterion_id"))
                criterion_ids.add(criterion_id)
            validate_text(criterion.get("label"), f"{path}.label", issues)
            validate_text(
                criterion.get("construct_component"),
                f"{path}.construct_component",
                issues,
            )
            validate_bool(criterion.get("required"), f"{path}.required", issues)
            weight = criterion.get("weight")
            if not is_number(weight) or not 0 < float(weight) <= 1:
                issues.append(Issue("CRITERION_WEIGHT_INVALID", f"{path}.weight"))
            else:
                total_weight += float(weight)
            validate_text_list(
                criterion.get("evidence_requirements"),
                f"{path}.evidence_requirements",
                issues,
                minimum=1,
                maximum=20,
            )
            validate_text_list(
                criterion.get("limitations"),
                f"{path}.limitations",
                issues,
                minimum=1,
                maximum=20,
            )
            anchors = criterion.get("anchors")
            criterion_anchor_scores: set[float] = set()
            if not isinstance(anchors, list) or not 2 <= len(anchors) <= 21:
                issues.append(Issue("CRITERION_ANCHORS_INVALID", f"{path}.anchors"))
            else:
                for anchor_index, anchor in enumerate(anchors):
                    anchor_path = f"{path}.anchors[{anchor_index}]"
                    if not exact_keys(
                        anchor, {"score", "description"}, anchor_path, issues
                    ):
                        continue
                    if not is_number(anchor.get("score")):
                        issues.append(
                            Issue("ANCHOR_SCORE_INVALID", f"{anchor_path}.score")
                        )
                    else:
                        anchor_score = float(anchor["score"])
                        if anchor_score in criterion_anchor_scores:
                            issues.append(Issue("ANCHOR_SCORE_DUPLICATE", f"{anchor_path}.score"))
                        criterion_anchor_scores.add(anchor_score)
                    validate_text(
                        anchor.get("description"),
                        f"{anchor_path}.description",
                        issues,
                    )
            if criterion_anchor_scores != scale_anchor_scores:
                issues.append(Issue("CRITERION_ANCHORS_INCOMPLETE", f"{path}.anchors"))
            _validate_proxy_absence(criterion, path, issues)
    if criteria and not math.isclose(total_weight, 1.0, abs_tol=1e-9):
        issues.append(Issue("CRITERION_WEIGHTS_MUST_SUM_TO_ONE", "$.criteria"))

    protocol = rubric.get("rater_protocol")
    if exact_keys(
        protocol,
        {
            "minimum_raters",
            "training_required",
            "training_ref",
            "calibration_required",
            "calibration_ref",
            "agreement_method",
            "inter_rater_reliability_status",
            "inter_rater_reliability_ref",
            "drift_monitoring_required",
            "drift_review_ref",
        },
        "$.rater_protocol",
        issues,
    ):
        minimum_raters = protocol.get("minimum_raters")
        if (
            not isinstance(minimum_raters, int)
            or isinstance(minimum_raters, bool)
            or not 2 <= minimum_raters <= 50
        ):
            issues.append(
                Issue("MINIMUM_RATERS_INVALID", "$.rater_protocol.minimum_raters")
            )
        for field in (
            "training_required",
            "calibration_required",
            "drift_monitoring_required",
        ):
            validate_bool(protocol.get(field), f"$.rater_protocol.{field}", issues)
            if protocol.get(field) is not True:
                issues.append(
                    Issue("RATER_CONTROL_MUST_BE_REQUIRED", f"$.rater_protocol.{field}")
                )
        for field in ("training_ref", "calibration_ref", "drift_review_ref"):
            validate_reference(protocol.get(field), f"$.rater_protocol.{field}", issues)
        if protocol.get("agreement_method") != (
            "exact_within_step_and_mean_absolute_difference"
        ):
            issues.append(
                Issue(
                    "AGREEMENT_METHOD_INVALID", "$.rater_protocol.agreement_method"
                )
            )
        reliability_status = protocol.get("inter_rater_reliability_status")
        if reliability_status not in (
            "not_established",
            "pilot_evidence",
            "documented",
        ):
            issues.append(
                Issue(
                    "INTER_RATER_RELIABILITY_STATUS_INVALID",
                    "$.rater_protocol.inter_rater_reliability_status",
                )
            )
        validate_reference(
            protocol.get("inter_rater_reliability_ref"),
            "$.rater_protocol.inter_rater_reliability_ref",
            issues,
            allow_empty=reliability_status == "not_established",
        )
        if reliability_status != "documented":
            issues.append(
                Issue(
                    "INTER_RATER_RELIABILITY_NOT_DOCUMENTED",
                    "$.rater_protocol.inter_rater_reliability_status",
                    "warning",
                )
            )

    governance = rubric.get("governance")
    governance_bool_fields = (
        "accountable_committee_required",
        "conflict_disclosure_required",
        "recusal_required",
        "appeal_process_required",
        "accessibility_accommodations_required",
        "data_protection_review_required",
        "subgroup_bias_review_required",
    )
    governance_ref_fields = (
        "committee_owner_role",
        "appeal_process_ref",
        "accessibility_process_ref",
        "data_protection_process_ref",
        "subgroup_review_ref",
        "review_cycle_ref",
    )
    if exact_keys(
        governance,
        set(governance_bool_fields) | set(governance_ref_fields),
        "$.governance",
        issues,
    ):
        for field in governance_bool_fields:
            validate_bool(governance.get(field), f"$.governance.{field}", issues)
            if governance.get(field) is not True:
                issues.append(
                    Issue("GOVERNANCE_CONTROL_MUST_BE_REQUIRED", f"$.governance.{field}")
                )
        for field in governance_ref_fields:
            validate_reference(governance.get(field), f"$.governance.{field}", issues)

    if maximum <= minimum or step <= 0:
        issues.append(Issue("SCALE_UNUSABLE", "$.scale"))
    return issues


def scale_values(rubric: dict[str, Any]) -> set[float]:
    return {
        float(anchor["score"])
        for anchor in rubric["scale"]["anchors"]
        if is_number(anchor["score"])
    }


def validate_evaluation(
    evaluation: Any, rubric: dict[str, Any]
) -> list[Issue]:
    """Validate one strict scholarly-work evaluation record."""

    issues: list[Issue] = []
    if not exact_keys(
        evaluation,
        {
            "schema_version",
            "evaluation_id",
            "rubric_id",
            "work_id",
            "data_classification",
            "purpose",
            "ratings",
        },
        "$",
        issues,
    ):
        return issues
    if evaluation.get("schema_version") != SCHEMA_VERSION:
        issues.append(Issue("SCHEMA_VERSION_UNSUPPORTED", "$.schema_version"))
    validate_identifier(evaluation.get("evaluation_id"), "$.evaluation_id", issues)
    validate_identifier(evaluation.get("rubric_id"), "$.rubric_id", issues)
    validate_identifier(evaluation.get("work_id"), "$.work_id", issues)
    if evaluation.get("rubric_id") != rubric.get("rubric_id"):
        issues.append(Issue("RUBRIC_ID_MISMATCH", "$.rubric_id"))
    if evaluation.get("data_classification") not in ALLOWED_CLASSIFICATIONS:
        issues.append(Issue("DATA_CLASSIFICATION_NOT_ALLOWED", "$.data_classification"))
    if evaluation.get("purpose") != ALLOWED_PURPOSE:
        issues.append(Issue("PURPOSE_NOT_ALLOWED", "$.purpose"))

    criteria = {criterion["criterion_id"]: criterion for criterion in rubric["criteria"]}
    accepted_scores = scale_values(rubric)
    maximum_uncertainty = float(rubric["scale"]["maximum"]) - float(
        rubric["scale"]["minimum"]
    )
    ratings = evaluation.get("ratings")
    seen: set[str] = set()
    if not isinstance(ratings, list) or not 1 <= len(ratings) <= MAX_CRITERIA:
        issues.append(Issue("RATINGS_INVALID", "$.ratings"))
        return issues
    for index, rating in enumerate(ratings):
        path = f"$.ratings[{index}]"
        if not exact_keys(
            rating,
            {
                "criterion_id",
                "status",
                "score",
                "uncertainty",
                "evidence_ids",
                "rationale_ref",
            },
            path,
            issues,
        ):
            continue
        criterion_id = rating.get("criterion_id")
        validate_identifier(criterion_id, f"{path}.criterion_id", issues)
        if isinstance(criterion_id, str):
            if criterion_id in seen:
                issues.append(Issue("RATING_DUPLICATE", f"{path}.criterion_id"))
            seen.add(criterion_id)
            if criterion_id not in criteria:
                issues.append(Issue("CRITERION_UNKNOWN", f"{path}.criterion_id"))
        status = rating.get("status")
        if status not in RATING_STATUSES:
            issues.append(Issue("RATING_STATUS_INVALID", f"{path}.status"))
        evidence_ids = rating.get("evidence_ids")
        if not isinstance(evidence_ids, list) or len(evidence_ids) > 100:
            issues.append(Issue("EVIDENCE_IDS_INVALID", f"{path}.evidence_ids"))
            evidence_ids = []
        else:
            hashable_evidence_ids = [
                evidence_id
                for evidence_id in evidence_ids
                if isinstance(evidence_id, str)
            ]
            if len(hashable_evidence_ids) != len(set(hashable_evidence_ids)):
                issues.append(Issue("EVIDENCE_ID_DUPLICATE", f"{path}.evidence_ids"))
            for evidence_index, evidence_id in enumerate(evidence_ids):
                validate_identifier(
                    evidence_id,
                    f"{path}.evidence_ids[{evidence_index}]",
                    issues,
                    "EVIDENCE_ID_INVALID",
                )
        validate_reference(rating.get("rationale_ref"), f"{path}.rationale_ref", issues)
        if status == "rated":
            score = rating.get("score")
            uncertainty = rating.get("uncertainty")
            if not is_number(score) or float(score) not in accepted_scores:
                issues.append(Issue("SCORE_NOT_ON_SCALE", f"{path}.score"))
            if (
                not is_number(uncertainty)
                or not 0 <= float(uncertainty) <= maximum_uncertainty
            ):
                issues.append(Issue("UNCERTAINTY_INVALID", f"{path}.uncertainty"))
            if not evidence_ids:
                issues.append(Issue("RATED_EVIDENCE_REQUIRED", f"{path}.evidence_ids"))
        elif status in ("missing", "not_applicable"):
            if rating.get("score") is not None:
                issues.append(Issue("UNRATED_SCORE_MUST_BE_NULL", f"{path}.score"))
            if rating.get("uncertainty") is not None:
                issues.append(
                    Issue("UNRATED_UNCERTAINTY_MUST_BE_NULL", f"{path}.uncertainty")
                )
            if evidence_ids:
                issues.append(
                    Issue("UNRATED_EVIDENCE_MUST_BE_EMPTY", f"{path}.evidence_ids")
                )
    missing_criteria = set(criteria) - seen
    for criterion_id in sorted(missing_criteria):
        issues.append(Issue("CRITERION_RATING_REQUIRED", f"$.ratings.{criterion_id}"))
    return issues


def error_issues(issues: Iterable[Issue]) -> list[Issue]:
    return [issue for issue in issues if issue.level == "error"]


def require_valid(issues: Iterable[Issue]) -> None:
    errors = error_issues(issues)
    if errors:
        raise ValidationError(errors[0].code, errors[0].path)


def rounded(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 6)


def weights_by_criterion(rubric: dict[str, Any]) -> dict[str, float]:
    return {
        criterion["criterion_id"]: float(criterion["weight"])
        for criterion in rubric["criteria"]
    }


def score_evaluation(
    rubric: dict[str, Any],
    evaluation: dict[str, Any],
    *,
    weights: dict[str, float] | None = None,
    round_output: bool = True,
) -> dict[str, Any]:
    """Calculate bounded descriptive rubric math without a recommendation."""

    selected_weights = weights or weights_by_criterion(rubric)
    output_number = rounded if round_output else lambda value: value
    scale_minimum = float(rubric["scale"]["minimum"])
    scale_maximum = float(rubric["scale"]["maximum"])
    rating_by_id = {
        rating["criterion_id"]: rating for rating in evaluation["ratings"]
    }
    criteria_output: list[dict[str, Any]] = []
    weighted_sum = 0.0
    lower_sum = 0.0
    upper_sum = 0.0
    rated_weight = 0.0
    missing_weight = 0.0
    not_applicable_weight = 0.0
    for criterion in rubric["criteria"]:
        criterion_id = criterion["criterion_id"]
        rating = rating_by_id[criterion_id]
        weight = float(selected_weights[criterion_id])
        status = rating["status"]
        item: dict[str, Any] = {
            "criterion_id": criterion_id,
            "status": status,
            "weight": output_number(weight),
            "score": None,
            "uncertainty": None,
            "weighted_contribution": None,
            "lower_contribution": None,
            "upper_contribution": None,
        }
        if status == "rated":
            score = float(rating["score"])
            uncertainty = float(rating["uncertainty"])
            lower = max(scale_minimum, score - uncertainty)
            upper = min(scale_maximum, score + uncertainty)
            contribution = weight * score
            weighted_sum += contribution
            lower_sum += weight * lower
            upper_sum += weight * upper
            rated_weight += weight
            item.update(
                {
                    "score": output_number(score),
                    "uncertainty": output_number(uncertainty),
                    "weighted_contribution": output_number(contribution),
                    "lower_contribution": output_number(weight * lower),
                    "upper_contribution": output_number(weight * upper),
                }
            )
        elif status == "missing":
            missing_weight += weight
        else:
            not_applicable_weight += weight
        criteria_output.append(item)
    applicable_weight = rated_weight + missing_weight
    normalized = weighted_sum / rated_weight if rated_weight else None
    lower_score = lower_sum / rated_weight if rated_weight else None
    upper_score = upper_sum / rated_weight if rated_weight else None
    coverage = rated_weight / applicable_weight if applicable_weight else None
    warnings: list[str] = []
    if missing_weight > 0:
        warnings.append("MISSING_RATINGS_EXCLUDED_FROM_NORMALIZED_SCORE")
    if not_applicable_weight > 0:
        warnings.append("NOT_APPLICABLE_RATINGS_EXCLUDED")
    if coverage is None or coverage < 1.0:
        warnings.append("INCOMPLETE_APPLICABLE_COVERAGE")
    if normalized is None:
        warnings.append("NO_NORMALIZED_SCORE_AVAILABLE")
    return {
        "schema_version": SCHEMA_VERSION,
        "report_type": "bounded_descriptive_rubric_score",
        "notice": NOTICE,
        "evaluation_id": evaluation["evaluation_id"],
        "work_id": evaluation["work_id"],
        "rubric_id": rubric["rubric_id"],
        "scale": {"minimum": scale_minimum, "maximum": scale_maximum},
        "formula": (
            "normalized_score = sum(score_i * weight_i for rated criteria) "
            "/ sum(weight_i for rated criteria); missing and not_applicable "
            "criteria are reported and excluded"
        ),
        "criteria": criteria_output,
        "aggregates": {
            "total_weight": output_number(sum(selected_weights.values())),
            "applicable_weight": output_number(applicable_weight),
            "rated_weight": output_number(rated_weight),
            "missing_weight": output_number(missing_weight),
            "not_applicable_weight": output_number(not_applicable_weight),
            "coverage_of_applicable_weight": output_number(coverage),
            "weighted_sum": output_number(weighted_sum),
            "normalized_score": output_number(normalized),
            "uncertainty_interval": {
                "lower": output_number(lower_score),
                "upper": output_number(upper_score),
                "method": (
                    "weighted aggregation of criterion-level bounded uncertainty "
                    "intervals; not a confidence interval"
                ),
            },
        },
        "warnings": warnings,
        "decision_recommendation_provided": False,
    }
