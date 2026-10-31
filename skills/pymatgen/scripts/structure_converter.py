#!/usr/bin/env python3
"""Convert one local periodic structure with explicit loss acknowledgement."""

from __future__ import annotations

import argparse
import warnings

from _common import (
    CliError,
    DEFAULT_MAX_INPUT_BYTES,
    DEFAULT_MAX_OUTPUT_BYTES,
    DEFAULT_MAX_SITES,
    checked_output_file,
    emit_json,
    load_structure,
    positive_int,
    structure_oxidation_summary,
    write_text_new,
)


FORMATS = ("cif", "cssr", "json", "poscar", "xsf", "xyz")
NONPERIODIC_TARGETS = {"xyz"}
LIMITED_TARGETS = {"cssr", "poscar", "xsf", "xyz"}


def conversion_risks(structure: object, output_format: str) -> list[str]:
    """Describe representation that a target format may not preserve."""
    risks: list[str] = []
    oxidation = structure_oxidation_summary(structure)
    site_properties = sorted(structure.site_properties)
    if output_format != "json" and oxidation["decorated_species_components"]:
        risks.append("oxidation-state decoration may not round-trip")
    if output_format != "json" and site_properties:
        risks.append(
            "site properties may be omitted or represented format-specifically: "
            + ", ".join(site_properties[:20])
        )
    if output_format in NONPERIODIC_TARGETS:
        risks.append("target does not preserve lattice vectors or periodicity")
    if output_format in LIMITED_TARGETS and not structure.is_ordered:
        risks.append("target cannot faithfully represent partial occupancies/disorder")
    return risks


def render_structure(
    structure: object,
    *,
    output_format: str,
    coordinate_mode: str,
) -> str:
    """Render a structure without giving pymatgen an output path."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        if output_format == "poscar":
            from pymatgen.io.vasp import Poscar

            text = Poscar(structure).get_str(direct=coordinate_mode == "direct")
        elif output_format == "xyz":
            if coordinate_mode != "not-applicable":
                raise CliError("--coordinate-mode is only meaningful for POSCAR output")
            from pymatgen.io.xyz import XYZ

            # Structure.to() does not register XYZ; this writer explicitly drops PBC.
            text = str(XYZ(structure))
        else:
            if coordinate_mode != "not-applicable":
                raise CliError(
                    "--coordinate-mode is only meaningful for POSCAR output"
                )
            text = structure.to(fmt=output_format)
    if caught:
        messages = "; ".join(str(item.message) for item in caught[:10])
        raise CliError(f"writer emitted warnings; conversion stopped: {messages}")
    return text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Convert one bounded local periodic structure. The original and any "
            "existing output are never overwritten."
        )
    )
    parser.add_argument("input", help="Existing local structure file")
    parser.add_argument("output", help="New output file")
    parser.add_argument(
        "--output-format",
        required=True,
        choices=FORMATS,
        help="Explicit target format; filename inference is not used",
    )
    parser.add_argument(
        "--coordinate-mode",
        choices=("direct", "cartesian", "not-applicable"),
        default="not-applicable",
        help="POSCAR coordinate mode; use not-applicable for other formats",
    )
    parser.add_argument(
        "--structure-index",
        type=int,
        default=0,
        help="Zero-based structure index for a multi-block CIF (default: 0)",
    )
    parser.add_argument(
        "--allow-lossy",
        action="store_true",
        help="Acknowledge every representation risk listed in the report",
    )
    parser.add_argument(
        "--acknowledge-parser-warnings",
        action="store_true",
        help="Continue only after reviewing warnings emitted while parsing",
    )
    parser.add_argument(
        "--max-input-bytes",
        type=positive_int,
        default=DEFAULT_MAX_INPUT_BYTES,
    )
    parser.add_argument(
        "--max-output-bytes",
        type=positive_int,
        default=DEFAULT_MAX_OUTPUT_BYTES,
    )
    parser.add_argument(
        "--max-sites",
        type=positive_int,
        default=DEFAULT_MAX_SITES,
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.structure_index < 0:
            raise CliError("--structure-index must be non-negative")
        if args.output_format == "poscar" and args.coordinate_mode == "not-applicable":
            raise CliError("POSCAR output requires --coordinate-mode direct|cartesian")
        structure, input_path, parse_report = load_structure(
            args.input,
            structure_index=args.structure_index,
            max_bytes=args.max_input_bytes,
            max_sites=args.max_sites,
        )
        output_path = checked_output_file(
            args.output,
            input_paths=(input_path,),
        )
        parser_warnings = [
            *parse_report["python_warnings"],
            *parse_report["parser_warnings"],
        ]
        if parser_warnings and not args.acknowledge_parser_warnings:
            raise CliError(
                "parser warnings require --acknowledge-parser-warnings after review: "
                + "; ".join(parser_warnings[:10])
            )
        risks = conversion_risks(structure, args.output_format)
        if risks and not args.allow_lossy:
            raise CliError(
                "conversion may be lossy; review the I/O plan and rerun with "
                "--allow-lossy: "
                + "; ".join(risks)
            )
        if not structure.is_ordered and args.output_format in LIMITED_TARGETS:
            raise CliError(
                f"{args.output_format} cannot faithfully encode this disordered "
                "structure; choose JSON or CIF"
            )
        text = render_structure(
            structure,
            output_format=args.output_format,
            coordinate_mode=args.coordinate_mode,
        )
        write_text_new(
            output_path,
            text,
            max_bytes=args.max_output_bytes,
        )
        parse_report["warnings_acknowledged"] = bool(
            args.acknowledge_parser_warnings
        )
        emit_json(
            {
                "ok": True,
                "action": "structure_conversion",
                "input": parse_report,
                "output": {
                    "name": output_path.name,
                    "format": args.output_format,
                    "coordinate_mode": args.coordinate_mode,
                    "bytes": output_path.stat().st_size,
                    "created": True,
                    "overwrote_existing": False,
                },
                "structure": {
                    "formula": structure.composition.reduced_formula,
                    "sites": len(structure),
                    "ordered": structure.is_ordered,
                    "periodic_boundary_conditions": list(structure.lattice.pbc),
                    "oxidation_states": structure_oxidation_summary(structure),
                },
                "representation_risks": risks,
                "losses_acknowledged": bool(args.allow_lossy),
                "scientific_equivalence_verified": False,
            }
        )
        return 0
    except (CliError, ImportError, OSError, RuntimeError, TypeError, ValueError) as exc:
        emit_json(
            {
                "ok": False,
                "error": str(exc),
                "output_created": False,
                "hint": (
                    "Install the pinned snapshot with uv if pymatgen is missing."
                ),
            }
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
