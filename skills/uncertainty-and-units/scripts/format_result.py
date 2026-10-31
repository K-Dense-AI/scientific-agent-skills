#!/usr/bin/env python3
"""Round and render a measurement result the way JCGM 100:2008 7.2 requires.

The uncertainty is rounded to one or two significant digits first, and the
value is then rounded to that same decimal place. Doing it in the other order,
or not at all, produces the familiar `12.34567 +/- 0.1` that claims five digits
of resolution the measurement does not have.
"""

from __future__ import annotations

import argparse
import math
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN, ROUND_HALF_UP
from typing import Any

import _common
from _common import CliError


ROUNDING_MODES = {"half-even": ROUND_HALF_EVEN, "half-up": ROUND_HALF_UP}


def _decimal(value: float, *, label: str) -> Decimal:
    """Convert a float to the shortest exact Decimal that reprs the same."""

    try:
        return Decimal(repr(float(value)))
    except (InvalidOperation, ValueError, OverflowError) as exc:
        raise CliError(f"{label} is not a finite decimal number") from exc


def round_to_uncertainty(
    value: float,
    uncertainty: float,
    *,
    significant_digits: int = 2,
    rounding: str = "half-even",
) -> dict[str, Any]:
    """Round value and uncertainty to a common decimal place.

    Returns the rounded pair plus the decimal place they share, so callers can
    render any notation from the same numbers.
    """

    if significant_digits not in (1, 2):
        raise CliError("uncertainty is reported to one or two significant digits")
    mode = ROUNDING_MODES.get(rounding)
    if mode is None:
        raise CliError(f"rounding must be one of: {', '.join(sorted(ROUNDING_MODES))}")
    if not math.isfinite(value) or not math.isfinite(uncertainty):
        raise CliError("value and uncertainty must both be finite")
    if uncertainty < 0:
        raise CliError("uncertainty must not be negative")

    exact_value = _decimal(value, label="value")
    if uncertainty == 0:
        return {
            "exact": True,
            "decimal_place": None,
            "value": exact_value,
            "uncertainty": Decimal(0),
        }

    exact_uncertainty = _decimal(uncertainty, label="uncertainty")
    exponent = exact_uncertainty.adjusted()
    place = exponent - (significant_digits - 1)
    quantum = Decimal(1).scaleb(place)
    rounded_uncertainty = exact_uncertainty.quantize(quantum, rounding=mode)

    # Rounding 0.0996 to two digits gives 0.100, which now carries three
    # digits. Recompute the place once against the carried value.
    if rounded_uncertainty.adjusted() != exponent:
        exponent = rounded_uncertainty.adjusted()
        place = exponent - (significant_digits - 1)
        quantum = Decimal(1).scaleb(place)
        rounded_uncertainty = exact_uncertainty.quantize(quantum, rounding=mode)

    rounded_value = exact_value.quantize(quantum, rounding=mode)
    return {
        "exact": False,
        "decimal_place": place,
        "value": rounded_value,
        "uncertainty": rounded_uncertainty,
    }


def _plain(number: Decimal) -> str:
    """Render a Decimal without exponent notation, keeping trailing zeros."""

    text = format(number, "f")
    return "-0" if text == "-0" else text


# Outside this decade range, positional notation degenerates into a run of
# zeros, so every rendering switches to scientific form.
POSITIONAL_RANGE = range(-6, 16)


def render(rounded: dict[str, Any], unit: str | None) -> dict[str, str]:
    """Produce the standard notations for an already-rounded pair."""

    suffix = f" {unit}" if unit else ""
    latex_unit = f"\\,\\mathrm{{{unit}}}" if unit else ""
    value = rounded["value"]
    uncertainty = rounded["uncertainty"]

    if rounded["exact"]:
        exponent = value.adjusted() if value != 0 else 0
        if exponent in POSITIONAL_RANGE:
            text = f"{_plain(value)}{suffix}"
            latex = f"${_plain(value)}{latex_unit}$"
        else:
            mantissa = _plain(value.scaleb(-exponent))
            text = f"{mantissa}e{exponent:+03d}{suffix}"
            latex = (
                f"${mantissa} \\times 10^{{{exponent}}}{latex_unit}$"
            )
        return {
            "plusminus": f"{text} (zero supplied uncertainty)",
            "ascii": f"{text} (zero supplied uncertainty)",
            "parenthetic": f"{text} (zero supplied uncertainty)",
            "scientific": f"{text} (zero supplied uncertainty)",
            "latex": latex,
        }

    place = rounded["decimal_place"]
    digits = int(uncertainty.scaleb(-place).to_integral_value())
    exponent = value.adjusted() if value != 0 else uncertainty.adjusted()
    mantissa_value = _plain(value.scaleb(-exponent))
    mantissa_uncertainty = _plain(uncertainty.scaleb(-exponent))
    scientific = f"({mantissa_value} ± {mantissa_uncertainty})e{exponent:+03d}{suffix}"
    scientific_concise = f"{mantissa_value}({digits})e{exponent:+03d}{suffix}"

    # `place > 0` puts the concise digits left of the decimal point, where they
    # are ambiguous; scientific notation removes the ambiguity.
    if exponent not in POSITIONAL_RANGE:
        return {
            "plusminus": scientific,
            "ascii": scientific.replace("±", "+/-"),
            "parenthetic": scientific_concise,
            "scientific": scientific,
            "latex": (
                f"$({mantissa_value} \\pm {mantissa_uncertainty}) "
                f"\\times 10^{{{exponent}}}{latex_unit}$"
            ),
        }

    value_text = _plain(value)
    uncertainty_text = _plain(uncertainty)
    return {
        "plusminus": f"{value_text} ± {uncertainty_text}{suffix}",
        "ascii": f"{value_text} +/- {uncertainty_text}{suffix}",
        "parenthetic": (
            scientific_concise if place > 0 else f"{value_text}({digits}){suffix}"
        ),
        "scientific": scientific,
        "latex": f"$({value_text} \\pm {uncertainty_text}){latex_unit}$",
    }


def build_statement(
    renderings: dict[str, str],
    coverage_factor: float | None,
    coverage_probability: float | None,
) -> str:
    """Write the sentence that has to accompany the number."""

    if coverage_factor is None:
        return (
            f"{renderings['plusminus']}, where the stated uncertainty is a combined "
            "standard uncertainty (coverage factor k = 1)."
        )
    probability = ""
    if coverage_probability is not None:
        probability = (
            f", with a caller-supplied coverage probability of approximately "
            f"{coverage_probability * 100:.0f}%"
        )
    return (
        f"{renderings['plusminus']}, where the stated uncertainty is an expanded "
        f"uncertainty U = k*u_c with a coverage factor k = {coverage_factor:g}"
        f"{probability}; the formatter does not verify coverage or the model assumptions."
    )


def collect_warnings(
    value: float, uncertainty: float, significant_digits: int, rounded: dict[str, Any]
) -> list[str]:
    """Flag reporting choices that mislead the reader."""

    warnings: list[str] = []
    if uncertainty == 0:
        return ["zero supplied uncertainty does not establish an exact measurement"]
    leading = _decimal(uncertainty, label="uncertainty").as_tuple().digits[0]
    if significant_digits == 1 and leading in (1, 2):
        warnings.append(
            f"the uncertainty begins with {leading}; rounding it to one significant "
            "digit changes it by a large fraction, so report two digits"
        )
    if value != 0 and uncertainty / abs(value) > 1.0:
        warnings.append(
            "the supplied uncertainty exceeds the magnitude of the estimate; "
            "retain the measured estimate and state the uncertainty type. Whether "
            "it is consistent with zero depends on the stated interval and model"
        )
    if rounded["value"] == 0 and value != 0:
        warnings.append(
            "the estimate rounds to zero at the uncertainty's decimal place; the "
            "measurement does not resolve it from zero"
        )
    return warnings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Round a value and its uncertainty to a common decimal place and render "
            "the standard notations (JCGM 100:2008 7.2.6)."
        )
    )
    parser.add_argument(
        "--value", required=True, type=_common.finite_float, help="the estimate"
    )
    parser.add_argument(
        "--uncertainty",
        required=True,
        type=_common.non_negative_float,
        help="standard or expanded uncertainty, in the same unit as the value",
    )
    parser.add_argument("--unit", help="unit label appended to every rendering")
    parser.add_argument(
        "--significant-digits",
        type=_common.bounded_int(1, 2),
        default=2,
        help="significant digits retained in the uncertainty (default 2)",
    )
    parser.add_argument(
        "--rounding",
        choices=sorted(ROUNDING_MODES),
        default="half-even",
        help="rounding mode (default half-even)",
    )
    parser.add_argument(
        "--coverage-factor",
        type=_common.positive_float,
        help="k, when the uncertainty supplied is an expanded uncertainty",
    )
    parser.add_argument(
        "--coverage-probability",
        type=_common.probability,
        help="coverage probability associated with k",
    )
    parser.add_argument(
        "--style",
        choices=("plusminus", "ascii", "parenthetic", "scientific", "latex"),
        default="plusminus",
        help="which rendering --format text prints (default plusminus)",
    )
    parser.add_argument("--format", choices=("json", "text"), default="json")
    parser.add_argument("--output", help="write JSON output to this file")
    parser.add_argument(
        "--force", action="store_true", help="overwrite an existing output file"
    )
    return parser


def run(arguments: argparse.Namespace) -> dict[str, Any]:
    """Round, render, and describe one measurement result."""

    if arguments.coverage_probability is not None and arguments.coverage_factor is None:
        raise CliError(
            "a coverage probability only means something alongside --coverage-factor"
        )
    rounded = round_to_uncertainty(
        arguments.value,
        arguments.uncertainty,
        significant_digits=arguments.significant_digits,
        rounding=arguments.rounding,
    )
    renderings = render(rounded, arguments.unit)
    document: dict[str, Any] = {
        "input": {
            "value": arguments.value,
            "uncertainty": arguments.uncertainty,
            "unit": arguments.unit,
            "significant_digits": arguments.significant_digits,
            "rounding": arguments.rounding,
        },
        "rounded_value": float(rounded["value"]),
        "rounded_uncertainty": float(rounded["uncertainty"]),
        "decimal_place": rounded["decimal_place"],
        "renderings": renderings,
        "statement": build_statement(
            renderings, arguments.coverage_factor, arguments.coverage_probability
        ),
        "warnings": collect_warnings(
            arguments.value,
            arguments.uncertainty,
            arguments.significant_digits,
            rounded,
        ),
    }
    if arguments.value != 0 and arguments.uncertainty > 0:
        document["relative_uncertainty"] = arguments.uncertainty / abs(arguments.value)
    return document


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        document = run(arguments)
        if arguments.format == "text":
            print(document["renderings"][arguments.style])
        else:
            _common.emit_json(
                document, output=arguments.output, force=arguments.force
            )
    except CliError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
