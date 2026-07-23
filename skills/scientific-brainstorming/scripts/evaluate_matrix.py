"""Calculate a transparent weighted idea matrix with sensitivity analysis."""

from __future__ import annotations

import argparse
import csv
import io
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from _common import (
    CliError,
    bounded_float,
    emit_json,
    finite_number,
    read_bounded_text,
    read_json,
    require_identifier,
    require_text,
    rounded,
)

MAX_CRITERIA = 25
MAX_ROWS = 1_000
MAX_COLUMNS = 200
MAX_CSV_FIELD_CHARS = 100_000


@dataclass(frozen=True)
class Criterion:
    """One explicit criterion in the disclosed additive model."""

    name: str
    description: str
    weight: float
    direction: str
    minimum: float
    maximum: float

    def normalize(self, value: float) -> float:
        """Map a bounded raw score to zero through one."""

        if self.direction == "higher":
            return (value - self.minimum) / (self.maximum - self.minimum)
        return (self.maximum - value) / (self.maximum - self.minimum)


@dataclass(frozen=True)
class Rating:
    """One central rating and its raw plausible interval."""

    score: float
    low: float
    high: float


@dataclass(frozen=True)
class IdeaRow:
    """Validated ratings and qualitative context for one idea."""

    idea_id: str
    ratings: Mapping[str, Rating]
    qualitative: Mapping[str, str]


def load_criteria(raw_path: str) -> list[Criterion]:
    """Load and validate the explicit criteria configuration."""

    _, document = read_json(raw_path, label="criteria configuration")
    if not isinstance(document, dict):
        raise CliError("criteria configuration must be a JSON object")
    if document.get("schema_version") != "1.0":
        raise CliError("criteria configuration schema_version must be '1.0'")
    raw_criteria = document.get("criteria")
    if not isinstance(raw_criteria, list) or not raw_criteria:
        raise CliError("criteria configuration must contain a non-empty list")
    if len(raw_criteria) > MAX_CRITERIA:
        raise CliError(
            f"criteria count is {len(raw_criteria)}; limit is {MAX_CRITERIA}"
        )

    result: list[Criterion] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_criteria):
        label = f"criteria[{index}]"
        if not isinstance(raw, dict):
            raise CliError(f"{label} must be an object")
        name = require_identifier(raw.get("name"), f"{label}.name")
        if name in seen:
            raise CliError(f"duplicate criterion name: {name}")
        seen.add(name)
        description = require_text(
            raw.get("description"),
            f"{label}.description",
            maximum=500,
        )
        weight = finite_number(raw.get("weight"), f"{label}.weight")
        if weight <= 0 or weight > 1_000_000:
            raise CliError(f"{label}.weight must be greater than 0 and at most 1000000")
        direction = raw.get("direction")
        if direction not in {"higher", "lower"}:
            raise CliError(f"{label}.direction must be 'higher' or 'lower'")
        minimum = finite_number(raw.get("minimum"), f"{label}.minimum")
        maximum = finite_number(raw.get("maximum"), f"{label}.maximum")
        if minimum >= maximum:
            raise CliError(f"{label}.minimum must be less than maximum")
        result.append(
            Criterion(
                name=name,
                description=description,
                weight=weight,
                direction=direction,
                minimum=minimum,
                maximum=maximum,
            )
        )
    return result


def _parse_bounded_score(
    raw: str | None,
    *,
    label: str,
    criterion: Criterion,
) -> float:
    if raw is None or not raw.strip():
        raise CliError(f"{label} must contain a score")
    score = finite_number(raw, label)
    if not criterion.minimum <= score <= criterion.maximum:
        raise CliError(
            f"{label}={score} is outside [{criterion.minimum}, {criterion.maximum}]"
        )
    return score


def load_scores(raw_path: str, criteria: Sequence[Criterion]) -> list[IdeaRow]:
    """Load bounded CSV ratings and preserve qualitative columns."""

    _, text = read_bounded_text(
        raw_path,
        label="scores CSV",
        suffixes={".csv"},
        encoding="utf-8-sig",
    )
    csv.field_size_limit(MAX_CSV_FIELD_CHARS)
    reader = csv.DictReader(io.StringIO(text, newline=""))
    fieldnames = reader.fieldnames
    if not fieldnames:
        raise CliError("scores CSV has no header")
    if len(fieldnames) > MAX_COLUMNS:
        raise CliError(f"scores CSV has more than {MAX_COLUMNS} columns")
    if any(name is None or not name.strip() for name in fieldnames):
        raise CliError("scores CSV contains an empty column name")
    if len(set(fieldnames)) != len(fieldnames):
        raise CliError("scores CSV column names must be unique")

    required = {"idea_id", "qualitative_review", "uncertainties"}
    required.update(criterion.name for criterion in criteria)
    missing = sorted(required - set(fieldnames))
    if missing:
        raise CliError(f"scores CSV is missing required columns: {', '.join(missing)}")

    interval_columns: set[str] = set()
    for criterion in criteria:
        low_name = f"{criterion.name}_low"
        high_name = f"{criterion.name}_high"
        has_low = low_name in fieldnames
        has_high = high_name in fieldnames
        if has_low != has_high:
            raise CliError(
                f"uncertainty columns for {criterion.name} must include both "
                f"{low_name} and {high_name}"
            )
        if has_low:
            interval_columns.update({low_name, high_name})

    numeric_columns = {criterion.name for criterion in criteria} | interval_columns
    qualitative_columns = [
        name for name in fieldnames if name not in numeric_columns and name != "idea_id"
    ]

    rows: list[IdeaRow] = []
    seen_ids: set[str] = set()
    for row_index, raw_row in enumerate(reader, start=2):
        if row_index > MAX_ROWS + 1:
            raise CliError(f"scores CSV exceeds the limit of {MAX_ROWS} data rows")
        if None in raw_row:
            raise CliError(f"row {row_index} has more values than header columns")
        idea_id = require_identifier(raw_row.get("idea_id"), f"row {row_index}.idea_id")
        if idea_id in seen_ids:
            raise CliError(f"duplicate idea_id in scores CSV: {idea_id}")
        seen_ids.add(idea_id)

        ratings: dict[str, Rating] = {}
        for criterion in criteria:
            score = _parse_bounded_score(
                raw_row.get(criterion.name),
                label=f"row {row_index}.{criterion.name}",
                criterion=criterion,
            )
            low_name = f"{criterion.name}_low"
            high_name = f"{criterion.name}_high"
            if low_name in interval_columns:
                raw_low = raw_row.get(low_name)
                raw_high = raw_row.get(high_name)
                low_blank = raw_low is None or not raw_low.strip()
                high_blank = raw_high is None or not raw_high.strip()
                if low_blank != high_blank:
                    raise CliError(
                        f"row {row_index} must provide both {low_name} and "
                        f"{high_name}, or leave both blank"
                    )
                if low_blank:
                    low = high = score
                else:
                    low = _parse_bounded_score(
                        raw_low,
                        label=f"row {row_index}.{low_name}",
                        criterion=criterion,
                    )
                    high = _parse_bounded_score(
                        raw_high,
                        label=f"row {row_index}.{high_name}",
                        criterion=criterion,
                    )
            else:
                low = high = score
            if not low <= score <= high:
                raise CliError(
                    f"row {row_index}.{criterion.name} requires low <= score <= high"
                )
            ratings[criterion.name] = Rating(score=score, low=low, high=high)

        qualitative: dict[str, str] = {}
        for name in qualitative_columns:
            allow_empty = name not in {"qualitative_review", "uncertainties"}
            qualitative[name] = require_text(
                raw_row.get(name, ""),
                f"row {row_index}.{name}",
                maximum=10_000,
                allow_empty=allow_empty,
            )
        rows.append(
            IdeaRow(
                idea_id=idea_id,
                ratings=ratings,
                qualitative=qualitative,
            )
        )

    if not rows:
        raise CliError("scores CSV must contain at least one data row")
    return rows


def _normalized_weights(
    criteria: Sequence[Criterion],
    *,
    override: Mapping[str, float] | None = None,
) -> dict[str, float]:
    raw = {
        criterion.name: (
            override[criterion.name] if override is not None else criterion.weight
        )
        for criterion in criteria
    }
    total = sum(raw.values())
    if total <= 0:
        raise CliError("sum of weights must be positive")
    return {name: value / total for name, value in raw.items()}


def _score(
    row: IdeaRow,
    criteria: Sequence[Criterion],
    weights: Mapping[str, float],
) -> float:
    return 100.0 * sum(
        weights[criterion.name] * criterion.normalize(row.ratings[criterion.name].score)
        for criterion in criteria
    )


def _ranks(scores: Mapping[str, float]) -> dict[str, int]:
    """Assign deterministic ordinal ranks; lexical idea ID breaks ties."""

    order = sorted(scores, key=lambda idea_id: (-scores[idea_id], idea_id))
    return {idea_id: index + 1 for index, idea_id in enumerate(order)}


def calculate_matrix(
    criteria: Sequence[Criterion],
    rows: Sequence[IdeaRow],
    *,
    weight_delta: float,
) -> dict[str, Any]:
    """Calculate disclosed scores, intervals, and local weight sensitivity."""

    if not 0 <= weight_delta <= 0.5:
        raise CliError("weight_delta must be between 0 and 0.5")

    base_weights = _normalized_weights(criteria)
    base_scores = {row.idea_id: _score(row, criteria, base_weights) for row in rows}
    base_ranks = _ranks(base_scores)

    scenario_scores: list[dict[str, float]] = []
    scenario_ranks: list[dict[str, int]] = []
    scenario_names: list[str] = []
    if weight_delta > 0:
        for criterion in criteria:
            for sign, factor in (
                ("minus", 1.0 - weight_delta),
                ("plus", 1.0 + weight_delta),
            ):
                raw_weights = {
                    item.name: (
                        item.weight * factor
                        if item.name == criterion.name
                        else item.weight
                    )
                    for item in criteria
                }
                weights = _normalized_weights(criteria, override=raw_weights)
                scores = {row.idea_id: _score(row, criteria, weights) for row in rows}
                scenario_scores.append(scores)
                scenario_ranks.append(_ranks(scores))
                scenario_names.append(f"{criterion.name}:{sign}")

    results: list[dict[str, Any]] = []
    warnings: list[str] = []
    for row in sorted(rows, key=lambda item: item.idea_id):
        interval_low = 0.0
        interval_high = 0.0
        criterion_details: dict[str, Any] = {}
        for criterion in criteria:
            rating = row.ratings[criterion.name]
            normalized_score = criterion.normalize(rating.score)
            if criterion.direction == "higher":
                normalized_low = criterion.normalize(rating.low)
                normalized_high = criterion.normalize(rating.high)
            else:
                normalized_low = criterion.normalize(rating.high)
                normalized_high = criterion.normalize(rating.low)
            weight = base_weights[criterion.name]
            interval_low += 100.0 * weight * normalized_low
            interval_high += 100.0 * weight * normalized_high
            criterion_details[criterion.name] = {
                "raw_score": rating.score,
                "raw_interval": [rating.low, rating.high],
                "normalized_score": rounded(normalized_score),
                "normalized_interval": [
                    rounded(normalized_low),
                    rounded(normalized_high),
                ],
                "normalized_weight": rounded(weight),
                "contribution_to_score": rounded(100.0 * weight * normalized_score),
            }

        sensitivity_scores = [scores[row.idea_id] for scores in scenario_scores] or [
            base_scores[row.idea_id]
        ]
        sensitivity_ranks = [ranks[row.idea_id] for ranks in scenario_ranks] or [
            base_ranks[row.idea_id]
        ]
        rank_min = min(sensitivity_ranks)
        rank_max = max(sensitivity_ranks)
        if rank_min != rank_max:
            warnings.append(
                f"{row.idea_id} changes rank from {rank_min} to {rank_max} "
                "under one-at-a-time weight perturbations"
            )
        results.append(
            {
                "idea_id": row.idea_id,
                "base_score": rounded(base_scores[row.idea_id]),
                "base_presentation_rank": base_ranks[row.idea_id],
                "input_uncertainty_score_interval": [
                    rounded(interval_low),
                    rounded(interval_high),
                ],
                "weight_sensitivity_score_range": [
                    rounded(min(sensitivity_scores)),
                    rounded(max(sensitivity_scores)),
                ],
                "weight_sensitivity_rank_range": [rank_min, rank_max],
                "criteria": criterion_details,
                "qualitative": dict(row.qualitative),
            }
        )

    return {
        "schema_version": "1.0",
        "method": {
            "name": "weighted-additive-normalized-matrix",
            "formula": (
                "score_i = 100 * sum_j(normalized_weight_j * "
                "direction_normalized_rating_ij)"
            ),
            "higher_normalization": "(x - minimum) / (maximum - minimum)",
            "lower_normalization": "(maximum - x) / (maximum - minimum)",
            "supplied_weights": {
                criterion.name: criterion.weight for criterion in criteria
            },
            "normalized_weights": {
                name: rounded(value) for name, value in base_weights.items()
            },
            "criteria": [
                {
                    "name": criterion.name,
                    "description": criterion.description,
                    "direction": criterion.direction,
                    "minimum": criterion.minimum,
                    "maximum": criterion.maximum,
                }
                for criterion in criteria
            ],
            "weight_sensitivity": {
                "type": "one-at-a-time proportional perturbation",
                "delta": weight_delta,
                "scenario_count": len(scenario_names),
                "scenarios": scenario_names,
                "weights_renormalized_in_each_scenario": True,
            },
            "tie_rule": (
                "Scores are ordered descending for presentation; exact ties are "
                "broken by lexical idea_id. Rank is not a decision."
            ),
        },
        "results": results,
        "warnings": warnings,
        "decision": None,
        "notice": (
            "No idea was selected and no scientific conclusion was made. "
            "Review qualitative reasons, uncertainty, dissent, evidence, and "
            "noncompensatory feasibility/ethics/safety gates."
        ),
        "limitations": [
            (
                "The additive model permits compensation across criteria; keep "
                "hard gates outside the score."
            ),
            (
                "Input intervals are combined as simultaneous criterion-wise "
                "bounds and are not calibrated probability intervals."
            ),
            (
                "Weight sensitivity changes one weight at a time and does not "
                "cover all plausible weights, criterion dependence, scale "
                "uncertainty, or model-form uncertainty."
            ),
            (
                "Ratings and weights are judgments, not empirical measurements "
                "of scientific truth."
            ),
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Calculate a disclosed weighted matrix from bounded CSV ratings, "
            "including input intervals and local weight sensitivity. No network, "
            "LLM, or automatic scientific decision is used."
        )
    )
    parser.add_argument("scores", help="Input ratings .csv file")
    parser.add_argument(
        "--config",
        required=True,
        help="Explicit criteria and weights .json file",
    )
    parser.add_argument(
        "--weight-delta",
        type=bounded_float(0.0, 0.5),
        default=0.10,
        help=(
            "Proportional one-at-a-time weight perturbation from 0 through 0.5 "
            "(default: 0.10)"
        ),
    )
    parser.add_argument(
        "--output",
        help="Optional result .json file in an existing directory",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Explicitly replace an existing regular output file",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run matrix evaluation."""

    args = build_parser().parse_args(argv)
    try:
        criteria = load_criteria(args.config)
        rows = load_scores(args.scores, criteria)
        result = calculate_matrix(
            criteria,
            rows,
            weight_delta=args.weight_delta,
        )
        emit_json(result, args.output, force=args.force)
    except CliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
