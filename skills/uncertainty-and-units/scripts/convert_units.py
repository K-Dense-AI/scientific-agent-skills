#!/usr/bin/env python3
"""Convert a quantity between units, including the conversions that need a context.

Wavelength to photon energy, mass to amount of substance, and energy to
temperature are not dimensional conversions - they are physical relations that
pint only performs inside a named context. This CLI makes the context explicit,
carries an uncertainty through the conversion's local derivative, and refuses
to hide the two unit families whose arithmetic does not mean what it looks
like: offset temperatures and logarithmic ratios.
"""

from __future__ import annotations

import argparse
import math
import sys
from typing import Any

import _common
from _common import CliError


MAX_UNIT_CHARS = 120
OFFSET_HINT = (
    "an offset unit measures a point on a scale, not an amount; differences and "
    "uncertainties belong in the matching delta_ unit"
)
LOGARITHMIC_HINT = (
    "adding two quantities in a logarithmic unit multiplies the underlying linear "
    "quantities, and pint returns the product in squared base units"
)


def checked_unit(text: str, *, label: str) -> str:
    """Reject unit strings that are empty, oversized, or obviously not units."""

    if not isinstance(text, str) or not text.strip():
        raise CliError(f"{label} must be a non-empty unit string")
    cleaned = text.strip()
    if len(cleaned) > MAX_UNIT_CHARS:
        raise CliError(f"{label} is longer than {MAX_UNIT_CHARS} characters")
    forbidden = set(";#\n\r\\'\"")
    if forbidden & set(cleaned):
        raise CliError(f"{label} contains characters that are not part of a unit")
    if "__" in cleaned or "lambda" in cleaned:
        raise CliError(f"{label} is not a valid unit expression")
    return cleaned


def parse_context_parameter(text: str, registry: Any) -> tuple[str, Any]:
    """Parse `name=value[ unit]` into a context keyword argument."""

    name, _, payload = text.partition("=")
    name = name.strip()
    if not name.isidentifier() or not payload.strip():
        raise CliError(f"context parameter {text!r} must look like mw=180.16 g/mol")
    fields = payload.strip().split(None, 1)
    magnitude = _common.finite_float(fields[0])
    if len(fields) == 1:
        return name, magnitude
    return name, registry.Quantity(magnitude, checked_unit(fields[1], label=name))


def build_registry() -> Any:
    """Create a default pint registry."""

    try:
        import pint
    except ImportError as exc:
        raise CliError(
            f"pint is unavailable; install with `{_common.PINNED_INSTALL}`"
        ) from exc
    return pint.UnitRegistry()


def is_multiplicative(registry: Any, unit: str) -> bool:
    """Report whether a unit can take part in ordinary arithmetic."""

    import pint

    try:
        registry.Quantity(1.0, unit) * 2.0
    except pint.errors.OffsetUnitCalculusError:
        return False
    except pint.errors.UndefinedUnitError as exc:
        raise CliError(f"unknown unit {unit!r}") from exc
    return True


def convert(
    registry: Any,
    value: float,
    unit: str,
    target: str,
    contexts: list[str],
    parameters: dict[str, Any],
) -> Any:
    """Convert one magnitude, applying any requested contexts."""

    import pint

    try:
        quantity = registry.Quantity(value, unit)
    except pint.errors.UndefinedUnitError as exc:
        raise CliError(f"unknown source unit {unit!r}") from exc
    try:
        return quantity.to(target, *contexts, **parameters)
    except pint.errors.UndefinedUnitError as exc:
        raise CliError(f"unknown target unit {target!r}") from exc
    except pint.errors.DimensionalityError as exc:
        raise CliError(
            f"{exc}. If the two units are related by a physical law rather than by "
            "dimensional analysis, name the context: --context spectroscopy for "
            "wavelength, frequency, wavenumber, and photon energy; "
            "--context chemistry --context-parameter 'mw=<molar mass>' for mass and "
            "amount of substance; --context boltzmann for energy and temperature"
        ) from exc
    except pint.errors.PintError as exc:
        raise CliError(f"pint could not perform the conversion: {exc}") from exc
    except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
        raise CliError(f"invalid conversion or context parameters: {exc}") from exc


def propagate(
    registry: Any,
    value: float,
    uncertainty: float,
    unit: str,
    target: str,
    contexts: list[str],
    parameters: dict[str, Any],
) -> float:
    """Carry an uncertainty through the conversion's local derivative.

    A central difference is exact for the affine conversions (including offset
    temperatures) and accurate to second order for the reciprocal relations a
    context introduces.
    """

    if uncertainty == 0:
        return 0.0
    # Keep the perturbation relative to the supplied magnitude: a fixed floor
    # of 1 made 532e-9 metres differ from 532 nanometres for reciprocal contexts.
    step = (math.ulp(1.0) ** (1.0 / 3.0)) * (abs(value) if value else 1.0)
    if step == 0 or value + step == value or value - step == value:
        raise CliError("magnitude is too small to resolve a conversion derivative")
    high = convert(registry, value + step, unit, target, contexts, parameters)
    low = convert(registry, value - step, unit, target, contexts, parameters)
    # audit-units: ignore UNIT003 -- both quantities were just converted to `target`
    derivative = (high.magnitude - low.magnitude) / (2.0 * step)
    if not math.isfinite(derivative):
        raise CliError("the conversion is not differentiable at this value")
    propagated = abs(derivative) * uncertainty
    if not math.isfinite(propagated):
        raise CliError("propagated uncertainty is not finite")
    return propagated


def run(arguments: argparse.Namespace) -> dict[str, Any]:
    """Perform the requested conversion and describe its hazards."""

    registry = build_registry()
    if arguments.list_contexts:
        defined = getattr(registry, "_contexts", {})
        return {
            "available_contexts": sorted(str(name) for name in defined),
            "note": (
                "spectroscopy (sp) relates wavelength, frequency, wavenumber, and "
                "photon energy; chemistry (chem) relates mass and amount of "
                "substance and needs mw; boltzmann relates energy and temperature"
            ),
        }

    if arguments.value is None or arguments.unit is None or arguments.to is None:
        raise CliError("--value, --unit, and --to are all required")

    unit = checked_unit(arguments.unit, label="--unit")
    target = checked_unit(arguments.to, label="--to")
    contexts = [checked_unit(item, label="--context") for item in arguments.context]
    parameters = dict(
        parse_context_parameter(item, registry)
        for item in arguments.context_parameter
    )

    result = convert(registry, arguments.value, unit, target, contexts, parameters)
    document: dict[str, Any] = {
        "input": {"value": arguments.value, "unit": unit},
        "target_unit": target,
        "contexts": contexts,
        # audit-units: ignore UNIT003 -- `result` is already in `target`
        "value": float(result.magnitude),
        "unit": str(result.units),
        "warnings": [],
    }
    if not math.isfinite(document["value"]):
        raise CliError("converted value is not finite; check the conversion domain")

    source_multiplicative = is_multiplicative(registry, unit)
    target_multiplicative = is_multiplicative(registry, target)
    if source_multiplicative and target_multiplicative and not contexts:
        one = convert(registry, 1.0, unit, target, contexts, parameters)
        # audit-units: ignore UNIT003 -- `one` is already in `target`
        document["conversion_factor"] = float(one.magnitude)

    offset_temperature = (
        (not source_multiplicative or not target_multiplicative)
        and registry.Quantity(1, unit).check("[temperature]")
        and registry.Quantity(1, target).check("[temperature]")
    )
    if offset_temperature:
        document["warnings"].append(f"{OFFSET_HINT} (in {unit} or {target})")
    for candidate in (unit, target):
        # audit-units: ignore UNIT004 -- this line is the detector, not a usage
        if "dB" in candidate or "decibel" in candidate:
            document["warnings"].append(f"{LOGARITHMIC_HINT} (in {candidate})")

    if arguments.uncertainty is not None:
        converted = propagate(
            registry,
            arguments.value,
            arguments.uncertainty,
            unit,
            target,
            contexts,
            parameters,
        )
        document["input"]["uncertainty"] = arguments.uncertainty
        document["uncertainty"] = converted
        note = "propagated through the local derivative of the conversion"
        document["uncertainty_unit"] = target
        if offset_temperature:
            difference_unit = f"delta_{target}" if not target_multiplicative else target
            document["uncertainty_unit"] = difference_unit
            note += (
                "; for an offset temperature that derivative is the scale factor "
                f"alone, so the result is {converted:.6g} {difference_unit}, not a "
                "point on the scale"
            )
        if "dB" in target or "decibel" in target:  # audit-units: ignore UNIT004 -- detector
            document["uncertainty_unit"] = "dB"  # audit-units: ignore UNIT004 -- label
            note += "; uncertainty on a logarithmic level is a level difference in dB"  # audit-units: ignore UNIT004 -- label
        document["uncertainty_note"] = note
        if contexts or not source_multiplicative or not target_multiplicative:
            document["warnings"].append(
                "a context conversion can be nonlinear, so the propagated "
                "uncertainty is a first-order approximation valid only while the "
                "conversion is locally linear across the input uncertainty; "
                "context parameters such as mw and n are treated as exact"
            )
    return document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Convert a quantity between units with pint, including context-only "
            "conversions, and carry an uncertainty through the conversion."
        )
    )
    parser.add_argument("--value", type=_common.finite_float, help="magnitude")
    parser.add_argument("--unit", help="unit of the supplied magnitude")
    parser.add_argument("--to", help="target unit")
    parser.add_argument(
        "--uncertainty",
        type=_common.non_negative_float,
        help="standard uncertainty in the source unit",
    )
    parser.add_argument(
        "--context",
        action="append",
        default=[],
        help="pint context enabling the conversion, e.g. spectroscopy; repeatable",
    )
    parser.add_argument(
        "--context-parameter",
        action="append",
        default=[],
        metavar="NAME=VALUE[ UNIT]",
        help="context keyword such as 'mw=180.16 g/mol'; repeatable",
    )
    parser.add_argument(
        "--list-contexts",
        action="store_true",
        help="list the contexts the registry defines and exit",
    )
    parser.add_argument("--output", help="write JSON output to this file")
    parser.add_argument(
        "--force", action="store_true", help="overwrite an existing output file"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        document = run(arguments)
        _common.emit_json(document, output=arguments.output, force=arguments.force)
    except CliError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
