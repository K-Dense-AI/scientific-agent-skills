#!/usr/bin/env python3
"""Produce a bounded JSON analysis of one local periodic structure."""

from __future__ import annotations

import argparse
import math
import warnings
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


def minimum_periodic_distance(structure: Any, max_sites: int) -> float | None:
    """Return the minimum non-self periodic distance under an explicit bound."""
    if len(structure) < 2 or len(structure) > max_sites:
        return None
    minimum = math.inf
    for first in range(len(structure)):
        for second in range(first + 1, len(structure)):
            minimum = min(minimum, float(structure.get_distance(first, second)))
    return minimum if math.isfinite(minimum) else None


def site_records(structure: Any, limit: int) -> list[dict[str, Any]]:
    """Return a bounded, explicit fractional-coordinate site table."""
    records: list[dict[str, Any]] = []
    for index, site in enumerate(structure[:limit]):
        records.append(
            {
                "index": index,
                "species": {
                    str(specie): float(occupancy)
                    for specie, occupancy in site.species.items()
                },
                "fractional_coordinates": [
                    float(value) for value in site.frac_coords
                ],
                "label": site.label,
            }
        )
    return records


def symmetry_report(
    structure: Any,
    *,
    symprec: float,
    angle_tolerance: float,
) -> dict[str, Any]:
    """Run one explicitly parameterized spglib-backed symmetry analysis."""
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

    analyzer = SpacegroupAnalyzer(
        structure,
        symprec=symprec,
        angle_tolerance=angle_tolerance,
    )
    symmetrized = analyzer.get_symmetrized_structure()
    return {
        "backend": "spglib through pymatgen",
        "symprec_angstrom": symprec,
        "angle_tolerance_degrees": angle_tolerance,
        "space_group_symbol": analyzer.get_space_group_symbol(),
        "space_group_number": analyzer.get_space_group_number(),
        "crystal_system": str(analyzer.get_crystal_system()),
        "point_group_symbol": analyzer.get_point_group_symbol(),
        "symmetry_operations": len(analyzer.get_symmetry_operations()),
        "equivalent_site_groups": len(symmetrized.equivalent_indices),
        "wyckoff_symbols_by_group": list(symmetrized.wyckoff_symbols),
        "tolerance_sensitivity_assessed": False,
    }


def neighbor_report(
    structure: Any,
    *,
    site_limit: int,
    neighbor_limit: int,
) -> dict[str, Any]:
    """Run CrystalNN for a bounded site prefix and truncate each neighbor list."""
    if not structure.is_ordered:
        raise CliError("CrystalNN report requires an ordered structure")
    from pymatgen.analysis.local_env import CrystalNN

    strategy = CrystalNN()
    rows: list[dict[str, Any]] = []
    warning_messages: list[str] = []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for index in range(min(len(structure), site_limit)):
            try:
                neighbors = strategy.get_nn_info(structure, index)
                rows.append(
                    {
                        "site_index": index,
                        "species": structure[index].species_string,
                        "coordination_number": len(neighbors),
                        "neighbors": [
                            {
                                "site_index": int(item["site_index"]),
                                "image": [int(value) for value in item["image"]],
                                "weight": float(item["weight"]),
                            }
                            for item in neighbors[:neighbor_limit]
                        ],
                        "neighbors_omitted": max(
                            0, len(neighbors) - neighbor_limit
                        ),
                    }
                )
            except (RuntimeError, TypeError, ValueError) as exc:
                rows.append(
                    {
                        "site_index": index,
                        "error": f"{type(exc).__name__}: {exc}"[:500],
                    }
                )
        warning_messages = [
            f"{item.category.__name__}: {item.message}" for item in caught[:20]
        ]
    return {
        "method": "CrystalNN",
        "sites": rows,
        "sites_omitted": max(0, len(structure) - site_limit),
        "warnings": warning_messages,
        "coordination_is_model_dependent": True,
    }


def analyze_structure(structure: Any, args: argparse.Namespace) -> dict[str, Any]:
    """Build a bounded analysis payload."""
    lattice = structure.lattice
    report: dict[str, Any] = {
        "ok": True,
        "analysis": "periodic_structure",
        "units": {
            "length": "angstrom",
            "angle": "degree",
            "volume": "angstrom^3",
            "density": "g/cm^3",
            "mass": "amu per composition represented",
        },
        "periodicity": {
            "periodic_boundary_conditions": [bool(value) for value in lattice.pbc],
            "lattice_required": True,
        },
        "composition": {
            "formula": structure.composition.formula,
            "reduced_formula": structure.composition.reduced_formula,
            "hill_formula": structure.composition.hill_formula,
            "chemical_system": structure.composition.chemical_system,
            "mass_amu": float(structure.composition.weight),
            "charge": float(structure.charge),
            "ordered": bool(structure.is_ordered),
            "oxidation_states": structure_oxidation_summary(structure),
        },
        "lattice": {
            "matrix_rows_angstrom": [
                [float(value) for value in row] for row in lattice.matrix
            ],
            "abc_angstrom": [float(value) for value in lattice.abc],
            "angles_degrees": [float(value) for value in lattice.angles],
            "volume_angstrom_cubed": float(structure.volume),
            "density_g_cm3": float(structure.density),
        },
        "sites": {
            "count": len(structure),
            "coordinate_mode": "fractional",
            "records": site_records(structure, args.max_site_records),
            "records_omitted": max(0, len(structure) - args.max_site_records),
        },
        "minimum_periodic_distance_angstrom": minimum_periodic_distance(
            structure, args.max_distance_sites
        ),
        "minimum_distance_omitted_above_sites": args.max_distance_sites,
        "minimum_distance_includes_self_images": False,
        "scientific_validity_established": False,
    }
    if args.symmetry:
        report["symmetry"] = symmetry_report(
            structure,
            symprec=args.symprec,
            angle_tolerance=args.angle_tolerance,
        )
    if args.neighbors:
        report["neighbors"] = neighbor_report(
            structure,
            site_limit=args.max_neighbor_sites,
            neighbor_limit=args.max_neighbors_per_site,
        )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze one bounded local periodic structure. JSON output is "
            "truncated by explicit site/neighbor limits."
        )
    )
    parser.add_argument("structure_file", help="Existing local structure file")
    parser.add_argument("--structure-index", type=int, default=0)
    parser.add_argument("--symmetry", action="store_true")
    parser.add_argument("--symprec", type=float, default=0.01)
    parser.add_argument("--angle-tolerance", type=float, default=5.0)
    parser.add_argument("--neighbors", action="store_true")
    parser.add_argument("--output", help="New JSON output; default is stdout")
    parser.add_argument(
        "--max-input-bytes",
        type=positive_int,
        default=DEFAULT_MAX_INPUT_BYTES,
    )
    parser.add_argument("--max-sites", type=positive_int, default=DEFAULT_MAX_SITES)
    parser.add_argument("--max-site-records", type=positive_int, default=100)
    parser.add_argument("--max-distance-sites", type=positive_int, default=500)
    parser.add_argument("--max-neighbor-sites", type=positive_int, default=100)
    parser.add_argument(
        "--max-neighbors-per-site", type=positive_int, default=24
    )
    parser.add_argument(
        "--max-output-bytes",
        type=positive_int,
        default=DEFAULT_MAX_OUTPUT_BYTES,
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.structure_index < 0:
            raise CliError("--structure-index must be non-negative")
        if not math.isfinite(args.symprec) or args.symprec <= 0:
            raise CliError("--symprec must be finite and positive")
        if not math.isfinite(args.angle_tolerance) or args.angle_tolerance < 0:
            raise CliError("--angle-tolerance must be finite and non-negative")
        if args.max_distance_sites > ABSOLUTE_MAX_PAIRWISE_SITES:
            raise CliError(
                f"--max-distance-sites may not exceed "
                f"{ABSOLUTE_MAX_PAIRWISE_SITES}"
            )
        if args.max_site_records > 10_000:
            raise CliError("--max-site-records may not exceed 10000")
        if args.max_neighbor_sites > 10_000:
            raise CliError("--max-neighbor-sites may not exceed 10000")
        if args.max_neighbors_per_site > 1_000:
            raise CliError("--max-neighbors-per-site may not exceed 1000")
        structure, input_path, parse_report = load_structure(
            args.structure_file,
            structure_index=args.structure_index,
            max_bytes=args.max_input_bytes,
            max_sites=args.max_sites,
        )
        report = analyze_structure(structure, args)
        report["input"] = parse_report
        if args.output:
            output = checked_output_file(args.output, input_paths=(input_path,))
            write_json_new(
                output,
                report,
                max_bytes=args.max_output_bytes,
            )
            emit_json(
                {
                    "ok": True,
                    "output": output.name,
                    "output_bytes": output.stat().st_size,
                    "overwrote_existing": False,
                    "sites": len(structure),
                }
            )
        else:
            emit_json(report)
        return 0
    except (CliError, ImportError, OSError, RuntimeError, TypeError, ValueError) as exc:
        emit_json({"ok": False, "error": f"{type(exc).__name__}: {exc}"[:1000]})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
