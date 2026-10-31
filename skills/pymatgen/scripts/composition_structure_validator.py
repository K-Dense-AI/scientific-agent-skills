#!/usr/bin/env python3
"""Validate a composition or local periodic structure without modifying it."""

from __future__ import annotations

import argparse
import math
from typing import Any

from _common import (
    ABSOLUTE_MAX_PAIRWISE_SITES,
    CliError,
    DEFAULT_MAX_INPUT_BYTES,
    DEFAULT_MAX_OUTPUT_BYTES,
    DEFAULT_MAX_SITES,
    checked_output_file,
    emit_json,
    load_structure,
    positive_int,
    structure_oxidation_summary,
    write_json_new,
)


def validate_composition(
    formula: str,
    *,
    guess_oxidation_states: bool,
) -> dict[str, Any]:
    """Parse a strict formula and optionally run a bounded oxidation-state guess."""
    if len(formula) > 500:
        raise CliError("formula exceeds 500 characters")
    from pymatgen.core import Composition

    try:
        composition = Composition(formula, strict=True)
    except (TypeError, ValueError) as exc:
        raise CliError(f"invalid strict composition: {exc}") from exc
    errors: list[str] = []
    warnings_list: list[str] = []
    if composition.num_atoms <= 0:
        errors.append("composition_has_no_positive_amount")
    if any(float(amount) <= 0 for amount in composition.values()):
        errors.append("non_positive_species_amount")
    species_have_oxidation = [
        hasattr(specie, "oxi_state") for specie in composition
    ]
    explicit_charge = (
        sum(
            float(amount) * float(specie.oxi_state)
            for specie, amount in composition.items()
        )
        if all(species_have_oxidation)
        else None
    )
    if not all(species_have_oxidation):
        warnings_list.append("oxidation_states_not_fully_explicit")
    guesses: list[dict[str, float]] | None = None
    if guess_oxidation_states:
        if len(composition.elements) > 6 or composition.num_atoms > 100:
            raise CliError(
                "oxidation-state guessing is limited to 6 elements and 100 atoms"
            )
        raw_guesses = composition.oxi_state_guesses()
        guesses = [
            {str(element): float(state) for element, state in guess.items()}
            for guess in raw_guesses[:20]
        ]
        if len(raw_guesses) > 20:
            warnings_list.append("oxidation_state_guesses_truncated_to_20")
    return {
        "ok": not errors,
        "kind": "composition",
        "input_formula": formula,
        "formula": composition.formula,
        "reduced_formula": composition.reduced_formula,
        "hill_formula": composition.hill_formula,
        "chemical_system": composition.chemical_system,
        "num_atoms_in_formula": float(composition.num_atoms),
        "mass_amu": float(composition.weight),
        "amounts": {
            str(specie): float(amount)
            for specie, amount in sorted(
                composition.items(), key=lambda item: str(item[0])
            )
        },
        "formal_charge_from_explicit_oxidation_states": explicit_charge,
        "oxidation_state_guesses": guesses,
        "oxidation_state_guess_requested": guess_oxidation_states,
        "errors": errors,
        "warnings": warnings_list,
        "chemical_validity_established": False,
    }


def minimum_distance(structure: Any, limit: int) -> tuple[float | None, list[int] | None]:
    """Find a minimum pair distance when the quadratic calculation is bounded."""
    if len(structure) < 2 or len(structure) > limit:
        return None, None
    best = math.inf
    pair: list[int] | None = None
    for first in range(len(structure)):
        for second in range(first + 1, len(structure)):
            distance = float(structure.get_distance(first, second))
            if distance < best:
                best = distance
                pair = [first, second]
    return (best if math.isfinite(best) else None), pair


def validate_structure(structure: Any, args: argparse.Namespace) -> dict[str, Any]:
    """Check representation invariants and common structural hazards."""
    errors: list[str] = []
    warnings_list: list[str] = []
    lattice = structure.lattice
    if not math.isfinite(float(structure.volume)) or structure.volume <= 0:
        errors.append("non_positive_or_non_finite_lattice_volume")
    if any(
        not math.isfinite(float(value))
        for row in lattice.matrix
        for value in row
    ):
        errors.append("non_finite_lattice_component")
    occupancy_issues: list[dict[str, Any]] = []
    outside_unit_cell = 0
    for index, site in enumerate(structure):
        occupancy = sum(float(value) for value in site.species.values())
        if occupancy <= 0 or occupancy > 1 + args.occupancy_tolerance:
            occupancy_issues.append(
                {"site_index": index, "occupancy_sum": occupancy}
            )
        if any(not math.isfinite(float(value)) for value in site.frac_coords):
            errors.append(f"non_finite_fractional_coordinate_at_site_{index}")
        if any(float(value) < 0 or float(value) >= 1 for value in site.frac_coords):
            outside_unit_cell += 1
    if occupancy_issues:
        errors.append("site_occupancy_outside_allowed_range")
    if not structure.is_ordered:
        warnings_list.append(
            "partial_occupancies_or_disorder_present; downstream methods may reject it"
        )
    if outside_unit_cell:
        warnings_list.append(
            f"{outside_unit_cell} sites have fractional coordinates outside [0, 1); "
            "they may be periodic images, but coordinate convention must be explicit"
        )
    oxidation = structure_oxidation_summary(structure)
    if not oxidation["all_decorated"]:
        warnings_list.append("oxidation_states_are_not_fully_explicit")
    distance, pair = minimum_distance(structure, args.max_distance_sites)
    if distance is None and len(structure) > args.max_distance_sites:
        warnings_list.append(
            "minimum-distance check omitted because the quadratic site limit was exceeded"
        )
    elif distance is not None and distance < args.min_distance:
        errors.append("sites_closer_than_minimum_distance")
    return {
        "ok": not errors,
        "kind": "periodic_structure",
        "units": {
            "length": "angstrom",
            "angle": "degree",
            "volume": "angstrom^3",
            "density": "g/cm^3",
        },
        "formula": structure.composition.reduced_formula,
        "site_count": len(structure),
        "ordered": bool(structure.is_ordered),
        "periodic_boundary_conditions": [
            bool(value) for value in structure.lattice.pbc
        ],
        "lattice": {
            "matrix_rows_angstrom": [
                [float(value) for value in row] for row in lattice.matrix
            ],
            "volume_angstrom_cubed": float(structure.volume),
            "density_g_cm3": float(structure.density),
        },
        "coordinates_interpreted_as": "fractional",
        "sites_outside_canonical_unit_cell": outside_unit_cell,
        "occupancy_tolerance": args.occupancy_tolerance,
        "occupancy_issues": occupancy_issues[:100],
        "occupancy_issues_omitted": max(0, len(occupancy_issues) - 100),
        "oxidation_states": oxidation,
        "minimum_periodic_distance_angstrom": distance,
        "minimum_distance_pair": pair,
        "minimum_distance_includes_self_images": False,
        "minimum_allowed_distance_angstrom": args.min_distance,
        "errors": errors,
        "warnings": warnings_list,
        "scientific_validity_established": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a composition or bounded local periodic structure. "
            "No files are modified and oxidation states are never guessed implicitly."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    composition = subparsers.add_parser("composition", help="Validate a formula")
    composition.add_argument("formula")
    composition.add_argument(
        "--guess-oxidation-states",
        action="store_true",
        help="Explicitly run pymatgen's bounded oxidation-state guesser",
    )
    composition.add_argument("--output", help="New JSON output; default stdout")

    structure = subparsers.add_parser(
        "structure", help="Validate a local periodic structure"
    )
    structure.add_argument("structure_file")
    structure.add_argument("--structure-index", type=int, default=0)
    structure.add_argument("--output", help="New JSON output; default stdout")
    structure.add_argument("--min-distance", type=float, default=0.5)
    structure.add_argument("--occupancy-tolerance", type=float, default=1e-6)
    structure.add_argument(
        "--max-input-bytes",
        type=positive_int,
        default=DEFAULT_MAX_INPUT_BYTES,
    )
    structure.add_argument(
        "--max-sites", type=positive_int, default=DEFAULT_MAX_SITES
    )
    structure.add_argument(
        "--max-distance-sites", type=positive_int, default=500
    )
    for child in (composition, structure):
        child.add_argument(
            "--max-output-bytes",
            type=positive_int,
            default=DEFAULT_MAX_OUTPUT_BYTES,
        )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        input_paths: tuple[Any, ...] = ()
        if args.command == "composition":
            report = validate_composition(
                args.formula,
                guess_oxidation_states=args.guess_oxidation_states,
            )
        else:
            if args.structure_index < 0:
                raise CliError("--structure-index must be non-negative")
            if not math.isfinite(args.min_distance) or args.min_distance <= 0:
                raise CliError("--min-distance must be finite and positive")
            if (
                not math.isfinite(args.occupancy_tolerance)
                or args.occupancy_tolerance < 0
            ):
                raise CliError(
                    "--occupancy-tolerance must be finite and non-negative"
                )
            if args.max_distance_sites > ABSOLUTE_MAX_PAIRWISE_SITES:
                raise CliError(
                    f"--max-distance-sites may not exceed "
                    f"{ABSOLUTE_MAX_PAIRWISE_SITES}"
                )
            structure, input_path, parse_report = load_structure(
                args.structure_file,
                structure_index=args.structure_index,
                max_bytes=args.max_input_bytes,
                max_sites=args.max_sites,
            )
            report = validate_structure(structure, args)
            report["input"] = parse_report
            input_paths = (input_path,)
        if args.output:
            output_path = checked_output_file(
                args.output,
                input_paths=input_paths,
            )
            write_json_new(
                output_path,
                report,
                max_bytes=args.max_output_bytes,
            )
            emit_json(
                {
                    "ok": report["ok"],
                    "output": output_path.name,
                    "overwrote_existing": False,
                }
            )
        else:
            emit_json(report)
        return 0 if report["ok"] else 2
    except (CliError, ImportError, OSError, RuntimeError, TypeError, ValueError) as exc:
        emit_json({"ok": False, "error": f"{type(exc).__name__}: {exc}"[:1000]})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
