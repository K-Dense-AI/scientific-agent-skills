#!/usr/bin/env python3
"""Generate a deterministic local Markdown preregistration scaffold."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path
from typing import Any

from _common import (
    ValidationError,
    error_exit,
    read_json,
    read_markdown,
    write_markdown,
)
from validate_hypothesis_schema import load_hypothesis_record, validate_record

TEMPLATE_PATH = (
    Path(__file__).resolve().parents[1]
    / "assets"
    / "preregistration_scaffold_template.md"
)
PLACEHOLDER_RE = re.compile(r"\{\{[A-Z0-9_]+\}\}")
MARKDOWN_SPECIAL_RE = re.compile(r"([\\`*_[\]{}#+|])")


def _safe_text(value: Any) -> str:
    """Render bounded input as inert one-line Markdown text."""
    text = " ".join(str(value).split())
    text = html.escape(text, quote=False)
    return MARKDOWN_SPECIAL_RE.sub(r"\\\1", text)


def _bullet(label: str, value: Any) -> str:
    return f"- **{_safe_text(label)}:** {_safe_text(value)}"


def _render_ethics(record: dict[str, Any]) -> str:
    ethics = record["ethics_and_feasibility"]
    lines = [
        _bullet(field.replace("_", " "), ethics[field])
        for field in (
            "human_subjects_gate",
            "animal_research_gate",
            "biosafety_gate",
            "dual_use_gate",
            "regulatory_gate",
            "data_governance_gate",
            "feasibility_status",
        )
    ]
    reviews = ethics["required_reviews"] or ["None declared"]
    blocks = ethics["unresolved_blocks"] or ["None declared"]
    lines.append(_bullet("required reviews", "; ".join(reviews)))
    lines.append(_bullet("unresolved blocks", "; ".join(blocks)))
    return "\n".join(lines)


def _render_evidence(record: dict[str, Any]) -> str:
    evidence = record["evidence"]
    lines = [
        _bullet("search boundary ID", evidence["search_boundary_id"]),
        _bullet("evidence ledger path", evidence["ledger_path"]),
        _bullet("declared source IDs", "; ".join(evidence["source_ids"])),
        _bullet("evidence limitations", "; ".join(evidence["evidence_limitations"])),
    ]
    return "\n".join(lines)


def _render_observation(record: dict[str, Any]) -> str:
    observation = record["observation"]
    return "\n".join(
        [
            _bullet("statement", observation["statement"]),
            _bullet("provenance", observation["provenance"]),
            _bullet("source IDs", "; ".join(observation["source_ids"])),
            _bullet("uncertainties", "; ".join(observation["uncertainties"])),
        ]
    )


def _render_question(record: dict[str, Any]) -> str:
    question = record["research_question"]
    return "\n".join(
        _bullet(field.replace("_", " "), question[field])
        for field in (
            "statement",
            "framework",
            "question_type",
            "population_or_system",
            "intervention_or_exposure",
            "comparator",
            "outcome",
            "timeframe",
        )
    )


def _render_hypotheses(record: dict[str, Any]) -> str:
    sections: list[str] = []
    for hypothesis in record["hypotheses"]:
        sections.extend(
            [
                f"### {_safe_text(hypothesis['hypothesis_id'])}",
                "",
                _bullet("status", hypothesis["status"]),
                _bullet("candidate statement", hypothesis["statement"]),
                _bullet("proposed mechanism", hypothesis["mechanism"]),
                _bullet("rival IDs", "; ".join(hypothesis["rival_hypothesis_ids"])),
                _bullet("assumptions", "; ".join(hypothesis["assumptions"])),
                _bullet(
                    "boundary conditions", "; ".join(hypothesis["boundary_conditions"])
                ),
                _bullet("uncertainties", "; ".join(hypothesis["uncertainties"])),
                _bullet("source IDs", "; ".join(hypothesis["source_ids"])),
                "",
            ]
        )
    return "\n".join(sections).rstrip()


def _render_estimands(record: dict[str, Any]) -> str:
    if not record["causal_estimands"]:
        return "- Not applicable to the declared non-causal question."
    sections: list[str] = []
    for estimand in record["causal_estimands"]:
        sections.extend(
            [
                f"### {_safe_text(estimand['estimand_id'])}",
                "",
                _bullet(
                    "linked hypothesis IDs",
                    "; ".join(estimand["linked_hypothesis_ids"]),
                ),
                _bullet("population", estimand["population"]),
                _bullet(
                    "intervention or exposure", estimand["intervention_or_exposure"]
                ),
                _bullet("comparator", estimand["comparator"]),
                _bullet("outcome", estimand["outcome"]),
                _bullet("time horizon", estimand["time_horizon"]),
                _bullet("population summary", estimand["population_summary"]),
                _bullet(
                    "intercurrent-event strategy",
                    estimand["intercurrent_event_strategy"],
                ),
                _bullet(
                    "identification assumptions",
                    "; ".join(estimand["identification_assumptions"]),
                ),
                "",
            ]
        )
    return "\n".join(sections).rstrip()


def _render_predictions(record: dict[str, Any]) -> str:
    sections: list[str] = []
    for prediction in record["predictions"]:
        sections.extend(
            [
                f"### {_safe_text(prediction['prediction_id'])} "
                f"({_safe_text(prediction['hypothesis_id'])})",
                "",
                _bullet("statement", prediction["statement"]),
                _bullet("conditions", prediction["conditions"]),
                _bullet("observable", prediction["observable"]),
                _bullet("expected pattern", prediction["expected_pattern"]),
                _bullet("falsifier", prediction["falsifier"]),
                _bullet(
                    "rival hypothesis IDs",
                    "; ".join(prediction["rival_hypothesis_ids"]),
                ),
                _bullet("measurement IDs", "; ".join(prediction["measurement_ids"])),
                _bullet("analysis IDs", "; ".join(prediction["analysis_ids"])),
                "",
            ]
        )
    return "\n".join(sections).rstrip()


def _render_nulls_and_controls(record: dict[str, Any]) -> str:
    sections = ["### Null hypotheses", ""]
    for null in record["null_hypotheses"]:
        sections.extend(
            [
                _bullet(
                    null["null_id"],
                    f"{null['statement']} | Rule: "
                    f"{null['rejection_or_compatibility_rule']}",
                ),
                "",
            ]
        )
    sections.extend(["### Negative controls", ""])
    for control in record["negative_controls"]:
        sections.extend(
            [
                _bullet(
                    control["control_id"],
                    f"{control['control_type']} | Rationale: {control['rationale']} "
                    f"| Expected: {control['expected_result']} | Failure: "
                    f"{control['failure_implication']}",
                ),
                "",
            ]
        )
    return "\n".join(sections).rstrip()


def _render_operationalizations(record: dict[str, Any]) -> str:
    sections: list[str] = []
    for measurement in record["operationalizations"]:
        sections.extend(
            [
                f"### {_safe_text(measurement['measurement_id'])}",
                "",
                _bullet("construct", measurement["construct"]),
                _bullet("variable and role", f"{measurement['variable']} / {measurement['role']}"),
                _bullet(
                    "operational definition", measurement["operational_definition"]
                ),
                _bullet(
                    "instrument or method", measurement["instrument_or_method"]
                ),
                _bullet("unit", measurement["unit"]),
                _bullet("timing", measurement["timing"]),
                _bullet("population or system", measurement["population_or_system"]),
                _bullet(
                    "validity evidence source IDs",
                    "; ".join(measurement["validity_evidence_source_ids"]),
                ),
                _bullet("reliability plan", measurement["reliability_plan"]),
                _bullet("missingness plan", measurement["missingness_plan"]),
                _bullet(
                    "blinding or masking", measurement["blinding_or_masking"]
                ),
                _bullet("threshold rationale", measurement["threshold_rationale"]),
                "",
            ]
        )
    return "\n".join(sections).rstrip()


def _render_analyses(record: dict[str, Any]) -> str:
    sections: list[str] = []
    for analysis in record["analysis_plan"]["analyses"]:
        sections.extend(
            [
                f"### {_safe_text(analysis['analysis_id'])}",
                "",
                _bullet("mode", analysis["exploratory_or_confirmatory"]),
                _bullet("prediction IDs", "; ".join(analysis["prediction_ids"])),
                _bullet("estimand IDs", "; ".join(analysis["estimand_ids"]) or "None"),
                _bullet("analysis population", analysis["analysis_population"]),
                _bullet("method", analysis["method"]),
                _bullet(
                    "effect or summary measure",
                    analysis["effect_or_summary_measure"],
                ),
                _bullet("uncertainty method", analysis["uncertainty_method"]),
                _bullet("missing-data plan", analysis["missing_data_plan"]),
                _bullet("multiplicity plan", analysis["multiplicity_plan"]),
                _bullet(
                    "sensitivity analyses",
                    "; ".join(analysis["sensitivity_analyses"]),
                ),
                _bullet("decision rule", analysis["decision_rule"]),
                "",
            ]
        )
    return "\n".join(sections).rstrip()


def _render_ai_use(record: dict[str, Any]) -> str:
    ai_use = record["ai_use"]
    return "\n".join(
        [
            _bullet("AI used", str(ai_use["used"]).lower()),
            _bullet(
                "sensitive or unpublished data sent externally",
                str(
                    ai_use["sensitive_or_unpublished_data_sent_externally"]
                ).lower(),
            ),
            _bullet(
                "local policy checked", str(ai_use["local_policy_checked"]).lower()
            ),
            _bullet(
                "citation verification required",
                str(ai_use["citation_verification_required"]).lower(),
            ),
            _bullet(
                "human accountable", str(ai_use["human_accountable"]).lower()
            ),
            _bullet("diversity mitigation", ai_use["diversity_mitigation"]),
        ]
    )


def generate(
    record: dict[str, Any], template_path: Path = TEMPLATE_PATH
) -> str:
    """Render all candidates into a local draft without ranking or selection."""
    validation = validate_record(record)
    if not validation["valid"]:
        codes = sorted({item["code"] for item in validation["errors"]})
        raise ValidationError(
            "hypothesis record is invalid; resolve these controls first: "
            + ", ".join(codes)
        )
    if validation["unresolved_gate_fields"]:
        raise ValidationError(
            "hypothesis record has unresolved safety or feasibility gates: "
            + ", ".join(validation["unresolved_gate_fields"])
        )

    template = read_markdown(template_path)
    replacements = {
        "{{PROJECT_ID}}": _safe_text(record["project_id"]),
        "{{HUMAN_OWNER}}": _safe_text(record["human_owner"]),
        "{{RECORD_STATUS}}": _safe_text(record["status"]),
        "{{UPDATED_ON}}": _safe_text(record["updated_on"]),
        "{{ETHICS_AND_FEASIBILITY}}": _render_ethics(record),
        "{{EVIDENCE_BOUNDARY}}": _render_evidence(record),
        "{{OBSERVATION}}": _render_observation(record),
        "{{RESEARCH_QUESTION}}": _render_question(record),
        "{{HYPOTHESES}}": _render_hypotheses(record),
        "{{ESTIMANDS}}": _render_estimands(record),
        "{{PREDICTIONS}}": _render_predictions(record),
        "{{NULLS_AND_CONTROLS}}": _render_nulls_and_controls(record),
        "{{OPERATIONALIZATIONS}}": _render_operationalizations(record),
        "{{ANALYSES}}": _render_analyses(record),
        "{{AI_USE}}": _render_ai_use(record),
        "{{DEVIATION_PLAN}}": _safe_text(
            record["analysis_plan"]["deviation_reporting"]
        ),
    }
    rendered = template
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    unresolved = sorted(set(PLACEHOLDER_RE.findall(rendered)))
    if unresolved:
        raise ValidationError(
            "scaffold template contains unresolved placeholders: "
            + ", ".join(unresolved)
        )
    return rendered.rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a private local Markdown preregistration scaffold from a "
            "valid hypothesis record; no upload or registration occurs."
        )
    )
    parser.add_argument("record", help="Local hypothesis record JSON")
    parser.add_argument("-o", "--output", required=True, help="Output Markdown path")
    parser.add_argument(
        "--force", action="store_true", help="Replace an existing output file"
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        record = load_hypothesis_record(read_json(args.record))
        destination = write_markdown(
            generate(record), args.output, force=args.force
        )
        print(f"Created local preregistration scaffold: {destination}")
        return 0
    except ValidationError as exc:
        return error_exit(exc)


if __name__ == "__main__":
    raise SystemExit(main())
