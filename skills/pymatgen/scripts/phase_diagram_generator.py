#!/usr/bin/env python3
"""Build a local phase diagram from a strict, provenance-bearing JSON dataset."""

from __future__ import annotations

import argparse
import math
import tempfile
from pathlib import Path
from typing import Any

from _common import (
    ABSOLUTE_MAX_OUTPUT_BYTES,
    CliError,
    DEFAULT_MAX_INPUT_BYTES,
    DEFAULT_MAX_OUTPUT_BYTES,
    atomic_link_from_temp,
    checked_output_file,
    emit_json,
    finite_float,
    load_strict_json,
    positive_int,
    write_json_new,
)


TOP_LEVEL_KEYS = {
    "schema_version",
    "energy_unit",
    "energy_basis",
    "provenance",
    "entries",
}
PROVENANCE_KEYS = {
    "source",
    "method",
    "retrieved_at",
    "database_version",
    "license",
    "citation",
    "notes",
}
ENTRY_KEYS = {"entry_id", "composition", "energy_eV", "provenance"}


def validate_provenance(value: Any, label: str) -> dict[str, str]:
    """Validate a small string-only provenance object."""
    if not isinstance(value, dict):
        raise CliError(f"{label} must be an object")
    unknown = set(value) - PROVENANCE_KEYS
    if unknown:
        raise CliError(f"{label} has unknown keys: {sorted(unknown)}")
    if not isinstance(value.get("source"), str) or not value["source"].strip():
        raise CliError(f"{label}.source must be a non-empty string")
    result: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(item, str) or len(item) > 2000:
            raise CliError(f"{label}.{key} must be a string of at most 2000 chars")
        result[key] = item
    return result


def entries_from_payload(
    payload: Any,
    *,
    max_entries: int,
) -> tuple[list[Any], dict[str, Any]]:
    """Validate the strict schema and construct plain ComputedEntry objects."""
    if not isinstance(payload, dict):
        raise CliError("top-level JSON value must be an object")
    missing = TOP_LEVEL_KEYS - set(payload)
    unknown = set(payload) - TOP_LEVEL_KEYS
    if missing or unknown:
        raise CliError(
            f"top-level keys mismatch; missing={sorted(missing)}, "
            f"unknown={sorted(unknown)}"
        )
    if payload["schema_version"] != "1.0":
        raise CliError("schema_version must be exactly '1.0'")
    if payload["energy_unit"] != "eV":
        raise CliError("energy_unit must be exactly 'eV'")
    if payload["energy_basis"] != "total_per_entry":
        raise CliError("energy_basis must be exactly 'total_per_entry'")
    dataset_provenance = validate_provenance(
        payload["provenance"], "provenance"
    )
    rows = payload["entries"]
    if not isinstance(rows, list) or not rows:
        raise CliError("entries must be a non-empty array")
    if len(rows) > max_entries:
        raise CliError(f"entries exceeds the {max_entries}-entry limit")

    from pymatgen.core import Composition
    from pymatgen.entries.computed_entries import ComputedEntry

    entries: list[Any] = []
    seen_ids: set[str] = set()
    provenance_by_id: dict[str, dict[str, str]] = {}
    for index, row in enumerate(rows):
        label = f"entries[{index}]"
        if not isinstance(row, dict) or set(row) != ENTRY_KEYS:
            actual = sorted(row) if isinstance(row, dict) else type(row).__name__
            raise CliError(f"{label} must contain exactly {sorted(ENTRY_KEYS)}; got {actual}")
        entry_id = row["entry_id"]
        if (
            not isinstance(entry_id, str)
            or not entry_id.strip()
            or len(entry_id) > 200
        ):
            raise CliError(f"{label}.entry_id must be a short non-empty string")
        if entry_id in seen_ids:
            raise CliError(f"duplicate entry_id: {entry_id!r}")
        seen_ids.add(entry_id)
        formula = row["composition"]
        if not isinstance(formula, str) or len(formula) > 500:
            raise CliError(f"{label}.composition must be a formula string")
        try:
            composition = Composition(formula, strict=True)
        except (TypeError, ValueError) as exc:
            raise CliError(f"{label}.composition is invalid: {exc}") from exc
        if composition.num_atoms <= 0:
            raise CliError(f"{label}.composition must contain positive amounts")
        energy = finite_float(row["energy_eV"], f"{label}.energy_eV")
        entry_provenance = validate_provenance(
            row["provenance"], f"{label}.provenance"
        )
        provenance_by_id[entry_id] = entry_provenance
        entries.append(
            ComputedEntry(
                composition,
                energy,
                entry_id=entry_id,
                data={"provenance": entry_provenance},
            )
        )
    return entries, {
        "dataset": dataset_provenance,
        "entries": provenance_by_id,
    }


def phase_report(
    entries: list[Any],
    provenance: dict[str, Any],
    *,
    analyze: list[str],
    max_report_entries: int,
) -> tuple[dict[str, Any], Any]:
    """Construct a phase diagram and a bounded scientific report."""
    from pymatgen.analysis.phase_diagram import PhaseDiagram
    from pymatgen.core import Composition

    diagram = PhaseDiagram(entries)
    stable = set(diagram.stable_entries)
    ordered_entries = sorted(
        entries,
        key=lambda item: (
            item.composition.reduced_formula,
            float(item.energy_per_atom),
            str(item.entry_id),
        ),
    )
    rows: list[dict[str, Any]] = []
    for entry in ordered_entries[:max_report_entries]:
        rows.append(
            {
                "entry_id": str(entry.entry_id),
                "formula": entry.composition.reduced_formula,
                "energy_eV_total": float(entry.energy),
                "energy_eV_per_atom": float(entry.energy_per_atom),
                "formation_energy_eV_per_atom": float(
                    diagram.get_form_energy_per_atom(entry)
                ),
                "energy_above_hull_eV_per_atom": float(
                    diagram.get_e_above_hull(entry)
                ),
                "on_computed_convex_hull": entry in stable,
            }
        )

    analyses: list[dict[str, Any]] = []
    for formula in analyze:
        try:
            composition = Composition(formula, strict=True)
            decomposition = diagram.get_decomposition(composition)
            matches = [
                entry
                for entry in entries
                if entry.composition.fractional_composition
                == composition.fractional_composition
            ]
            analyses.append(
                {
                    "query": formula,
                    "reduced_formula": composition.reduced_formula,
                    "matching_entries": [
                        {
                            "entry_id": str(entry.entry_id),
                            "energy_above_hull_eV_per_atom": float(
                                diagram.get_e_above_hull(entry)
                            ),
                        }
                        for entry in sorted(
                            matches,
                            key=lambda item: (
                                float(item.energy_per_atom),
                                str(item.entry_id),
                            ),
                        )
                    ],
                    "computed_hull_decomposition": [
                        {
                            "entry_id": str(entry.entry_id),
                            "formula": entry.composition.reduced_formula,
                            "fraction": float(fraction),
                        }
                        for entry, fraction in sorted(
                            decomposition.items(),
                            key=lambda item: str(item[0].entry_id),
                        )
                    ],
                }
            )
        except (TypeError, ValueError) as exc:
            analyses.append(
                {
                    "query": formula,
                    "error": f"{type(exc).__name__}: {exc}"[:500],
                }
            )

    report = {
        "ok": True,
        "analysis": "local_computed_phase_diagram",
        "units": {
            "input_energy": "eV total per entry",
            "reported_normalized_energy": "eV/atom",
        },
        "chemical_system": "-".join(str(element) for element in diagram.elements),
        "elements": [str(element) for element in diagram.elements],
        "entry_count": len(entries),
        "stable_entry_count": len(stable),
        "entries": rows,
        "entries_omitted": max(0, len(entries) - max_report_entries),
        "composition_analyses": analyses,
        "provenance": provenance["dataset"],
        "interpretation_limits": [
            "The hull is conditional on this exact entry set and energy model.",
            "Energies from incompatible methods or correction schemes must not be mixed.",
            "Computed stability is not experimental truth or a synthesis guarantee.",
            "Finite-temperature, pressure, kinetic, disorder, and uncertainty effects are absent unless encoded upstream.",
        ],
        "experimental_validity_established": False,
    }
    return report, diagram


def write_plot_new(
    diagram: Any,
    output_path: Path,
    *,
    show_unstable: float,
    max_bytes: int,
) -> None:
    """Render to a sibling temporary file, then link without overwriting."""
    suffix = output_path.suffix.casefold()
    if suffix not in {".png", ".pdf", ".svg"}:
        raise CliError("plot output suffix must be .png, .pdf, or .svg")
    from pymatgen.analysis.phase_diagram import PDPlotter

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=".pymatgen-phase-",
            suffix=suffix,
            dir=output_path.parent,
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
        # Matplotlib exports locally without Plotly's optional Kaleido/browser stack.
        plotter = PDPlotter(diagram, show_unstable=show_unstable, backend="matplotlib")
        plotter.write_image(
            str(temporary_path),
            image_format=suffix.removeprefix("."),
        )
        if temporary_path.stat().st_size > max_bytes:
            raise CliError(f"plot exceeds the {max_bytes}-byte limit")
        atomic_link_from_temp(temporary_path, output_path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build an offline phase diagram from strict JSON total energies. "
            "This script never queries Materials Project."
        )
    )
    parser.add_argument("entries_json", help="Strict local entries dataset")
    parser.add_argument(
        "--analyze",
        action="append",
        default=[],
        help="Formula to decompose or match (repeatable, maximum 20)",
    )
    parser.add_argument("--output", help="New JSON report; default is stdout")
    parser.add_argument("--plot", help="New .png, .pdf, or .svg plot")
    parser.add_argument(
        "--show-unstable",
        type=float,
        default=0.2,
        help="Plot unstable entries up to this eV/atom (default: 0.2)",
    )
    parser.add_argument(
        "--max-input-bytes",
        type=positive_int,
        default=DEFAULT_MAX_INPUT_BYTES,
    )
    parser.add_argument("--max-entries", type=positive_int, default=5000)
    parser.add_argument("--max-report-entries", type=positive_int, default=200)
    parser.add_argument(
        "--max-output-bytes",
        type=positive_int,
        default=DEFAULT_MAX_OUTPUT_BYTES,
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if len(args.analyze) > 20:
            raise CliError("--analyze may be repeated at most 20 times")
        if not math.isfinite(args.show_unstable) or args.show_unstable < 0:
            raise CliError("--show-unstable must be finite and non-negative")
        if args.max_entries > 10_000:
            raise CliError("--max-entries may not exceed 10000")
        if args.max_report_entries > 1_000:
            raise CliError("--max-report-entries may not exceed 1000")
        if args.max_output_bytes > ABSOLUTE_MAX_OUTPUT_BYTES:
            raise CliError(
                f"--max-output-bytes may not exceed {ABSOLUTE_MAX_OUTPUT_BYTES}"
            )
        payload, input_path = load_strict_json(
            args.entries_json,
            max_bytes=args.max_input_bytes,
        )
        entries, provenance = entries_from_payload(
            payload,
            max_entries=args.max_entries,
        )
        report, diagram = phase_report(
            entries,
            provenance,
            analyze=args.analyze,
            max_report_entries=args.max_report_entries,
        )
        report["input"] = {
            "name": input_path.name,
            "bytes": input_path.stat().st_size,
            "network_accessed": False,
        }
        created: list[str] = []
        if args.output:
            output_path = checked_output_file(
                args.output,
                input_paths=(input_path,),
            )
            write_json_new(
                output_path,
                report,
                max_bytes=args.max_output_bytes,
            )
            created.append(output_path.name)
        if args.plot:
            plot_path = checked_output_file(
                args.plot,
                input_paths=(input_path,),
            )
            if len(diagram.elements) > 4:
                raise CliError("plotting is limited to at most four elements")
            write_plot_new(
                diagram,
                plot_path,
                show_unstable=args.show_unstable,
                max_bytes=args.max_output_bytes,
            )
            created.append(plot_path.name)
        if created:
            emit_json(
                {
                    "ok": True,
                    "created": created,
                    "overwrote_existing": False,
                    "network_accessed": False,
                    "entry_count": len(entries),
                }
            )
        else:
            emit_json(report)
        return 0
    except (CliError, ImportError, OSError, RuntimeError, TypeError, ValueError) as exc:
        emit_json(
            {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}"[:1000],
                "network_accessed": False,
            }
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
