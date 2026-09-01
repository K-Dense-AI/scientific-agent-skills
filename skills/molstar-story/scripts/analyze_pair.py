#!/usr/bin/env python3
"""Align one PDB complex to another and quantify residue-level state changes."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import shutil
import statistics
from typing import Iterable

try:
    import numpy as np
except ImportError as exc:  # pragma: no cover - depends on the caller's runtime
    raise SystemExit(
        "NumPy is required for analyze_pair.py; install NumPy instead of "
        "silently changing the alignment method"
    ) from exc


RANGE_RE = re.compile(r"^(-?\d+):(-?\d+)$")


@dataclass(frozen=True)
class Atom:
    line_index: int
    record: str
    name: str
    altloc: str
    resname: str
    chain: str
    resseq: int
    icode: str
    element: str
    coord: np.ndarray


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path, help="reference-state PDB")
    parser.add_argument("mobile", type=Path, help="mobile-state PDB")
    parser.add_argument("--reference-chain", required=True)
    parser.add_argument("--mobile-chain", required=True)
    parser.add_argument(
        "--align-range",
        action="append",
        required=True,
        metavar="START:END",
        help="inclusive author-residue range used for the C-alpha fit; repeatable",
    )
    parser.add_argument(
        "--segments-tsv",
        type=Path,
        help="optional TSV with name, start, and end author-residue columns",
    )
    parser.add_argument(
        "--mobile-ligand-resname",
        action="append",
        default=[],
        help="optional ligand residue name in the mobile PDB; repeatable",
    )
    parser.add_argument("--contact-cutoff", type=float, default=4.0)
    parser.add_argument("--top", type=int, default=12)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def infer_element(atom_name: str) -> str:
    text = atom_name.strip()
    return (text[0] if text else "").upper()


def parse_pdb(path: Path) -> tuple[list[str], list[Atom]]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines(True)
    model_records = sum(line.startswith("MODEL ") for line in lines)
    if model_records > 1:
        raise ValueError(f"multiple MODEL records are not supported: {path}")
    atoms: list[Atom] = []
    for index, line in enumerate(lines):
        record = line[:6].strip()
        if record not in {"ATOM", "HETATM"}:
            continue
        if len(line) < 54:
            raise ValueError(f"short coordinate record at {path}:{index + 1}")
        try:
            coord = np.array(
                [float(line[30:38]), float(line[38:46]), float(line[46:54])],
                dtype=float,
            )
            resseq = int(line[22:26])
        except ValueError as exc:
            raise ValueError(f"invalid PDB coordinate at {path}:{index + 1}") from exc
        name = line[12:16].strip()
        atoms.append(
            Atom(
                line_index=index,
                record=record,
                name=name,
                altloc=line[16:17].strip(),
                resname=line[17:20].strip(),
                chain=line[21:22],
                resseq=resseq,
                icode=line[26:27].strip(),
                element=(line[76:78].strip().upper() if len(line) >= 78 else "")
                or infer_element(name),
                coord=coord,
            )
        )
    if not atoms:
        raise ValueError(f"no ATOM/HETATM records found: {path}")
    return lines, atoms


def parse_ranges(values: Iterable[str]) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for value in values:
        match = RANGE_RE.fullmatch(value)
        if not match:
            raise ValueError(f"invalid residue range {value!r}; expected START:END")
        start, end = (int(part) for part in match.groups())
        if start > end:
            raise ValueError(f"range start exceeds end: {value}")
        ranges.append((start, end))
    return ranges


def in_ranges(resseq: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= resseq <= end for start, end in ranges)


def residue_ca(atoms: list[Atom], chain: str) -> dict[tuple[int, str], Atom]:
    selected: dict[tuple[int, str], Atom] = {}
    for atom in atoms:
        if (
            atom.record != "ATOM"
            or atom.chain != chain
            or atom.name != "CA"
            or atom.altloc not in {"", "A"}
        ):
            continue
        key = (atom.resseq, atom.icode)
        previous = selected.get(key)
        if previous is None or (previous.altloc == "A" and atom.altloc == ""):
            selected[key] = atom
    return selected


def fit_transform(mobile: np.ndarray, reference: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mobile_center = mobile.mean(axis=0)
    reference_center = reference.mean(axis=0)
    covariance = (mobile - mobile_center).T @ (reference - reference_center)
    left, _singular, right_t = np.linalg.svd(covariance)
    correction = np.eye(3)
    if np.linalg.det(left @ right_t) < 0:
        correction[-1, -1] = -1
    rotation = left @ correction @ right_t
    translation = reference_center - mobile_center @ rotation
    return rotation, translation


def rmsd(first: np.ndarray, second: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.sum((first - second) ** 2, axis=1))))


def load_segments(path: Path | None) -> list[dict[str, object]]:
    if path is None:
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"name", "start", "end"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError("segments TSV must contain name, start, and end columns")
        segments = []
        for row_number, row in enumerate(reader, start=2):
            name = (row.get("name") or "").strip()
            if not name:
                raise ValueError(f"empty segment name at {path}:{row_number}")
            try:
                start, end = int(row["start"]), int(row["end"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid segment range at {path}:{row_number}") from exc
            if start > end:
                raise ValueError(f"segment start exceeds end at {path}:{row_number}")
            segments.append({"name": name, "start": start, "end": end})
    return segments


def transform_atoms(atoms: list[Atom], rotation: np.ndarray, translation: np.ndarray) -> dict[int, np.ndarray]:
    return {atom.line_index: atom.coord @ rotation + translation for atom in atoms}


def write_aligned_pdb(
    path: Path,
    lines: list[str],
    transformed: dict[int, np.ndarray],
    rotation: np.ndarray,
    translation: np.ndarray,
) -> None:
    output = [
        "REMARK 950 DERIVED MOBILE COMPLEX ALIGNED TO REFERENCE\n",
        "REMARK 950 ROW-VECTOR FORMULA: X_ALIGNED = X_MOBILE * R + T\n",
        "REMARK 950 R " + " ".join(f"{value:.9f}" for value in rotation.reshape(-1)) + "\n",
        "REMARK 950 T " + " ".join(f"{value:.9f}" for value in translation) + "\n",
    ]
    for index, line in enumerate(lines):
        record = line[:6].strip()
        if record in {"ATOM", "HETATM"}:
            coord = transformed[index]
            base = line.rstrip("\n").ljust(80)
            output.append(
                f"{base[:30]}{coord[0]:8.3f}{coord[1]:8.3f}{coord[2]:8.3f}{base[54:].rstrip()}\n"
            )
        elif record in {"TER", "CONECT", "END"}:
            output.append(line if line.endswith("\n") else line + "\n")
    if not output[-1].startswith("END"):
        output.append("END\n")
    path.write_text("".join(output), encoding="utf-8")


def round_float(value: float) -> float:
    return round(float(value), 6)


def residue_label(row: dict[str, object]) -> str:
    insertion = str(row["icode"] or "")
    return f"{row['reference_resname']}{row['auth_seq_id']}{insertion}"


def segment_summaries(
    residues: list[dict[str, object]], segments: list[dict[str, object]]
) -> list[dict[str, object]]:
    summaries = []
    for segment in segments:
        members = [
            row
            for row in residues
            if int(segment["start"]) <= int(row["auth_seq_id"]) <= int(segment["end"])
        ]
        values = [float(row["ca_displacement_A"]) for row in members]
        if not values:
            summaries.append({**segment, "count": 0})
            continue
        maximum = max(members, key=lambda row: float(row["ca_displacement_A"]))
        summaries.append(
            {
                **segment,
                "count": len(values),
                "mean_A": round_float(statistics.fmean(values)),
                "median_A": round_float(statistics.median(values)),
                "max_A": round_float(max(values)),
                "max_residue": residue_label(maximum),
            }
        )
    return summaries


def ligand_contacts(
    atoms: list[Atom],
    receptor_chain: str,
    ligand_resnames: set[str],
    cutoff: float,
) -> list[dict[str, object]]:
    if not ligand_resnames:
        return []
    ligand = [
        atom
        for atom in atoms
        if atom.record == "HETATM"
        and atom.resname.upper() in ligand_resnames
        and atom.element not in {"H", "D"}
    ]
    if not ligand:
        raise ValueError(
            "no heavy-atom HETATM records matched mobile ligand residue names: "
            + ", ".join(sorted(ligand_resnames))
        )
    receptor = [
        atom
        for atom in atoms
        if atom.record == "ATOM"
        and atom.chain == receptor_chain
        and atom.element not in {"H", "D"}
        and atom.altloc in {"", "A"}
    ]
    best: dict[tuple[int, str, str], tuple[float, Atom, Atom]] = {}
    for receptor_atom in receptor:
        distances = np.linalg.norm(
            np.stack([item.coord for item in ligand]) - receptor_atom.coord,
            axis=1,
        )
        ligand_atom = ligand[int(np.argmin(distances))]
        distance = float(np.min(distances))
        if distance > cutoff:
            continue
        key = (receptor_atom.resseq, receptor_atom.icode, receptor_atom.resname)
        if key not in best or distance < best[key][0]:
            best[key] = (distance, receptor_atom, ligand_atom)
    contacts = []
    for key, (distance, receptor_atom, ligand_atom) in sorted(best.items()):
        contacts.append(
            {
                "receptor_chain": receptor_atom.chain,
                "auth_seq_id": key[0],
                "icode": key[1],
                "receptor_resname": key[2],
                "receptor_atom": receptor_atom.name,
                "ligand_chain": ligand_atom.chain,
                "ligand_auth_seq_id": ligand_atom.resseq,
                "ligand_icode": ligand_atom.icode,
                "ligand_resname": ligand_atom.resname,
                "ligand_atom": ligand_atom.name,
                "min_distance_A": round_float(distance),
            }
        )
    return contacts


def write_tsv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    if len(args.reference_chain) != 1 or len(args.mobile_chain) != 1:
        raise SystemExit("PDB chain IDs must be exactly one character")
    if args.contact_cutoff <= 0:
        raise SystemExit("--contact-cutoff must be positive")
    if args.top <= 0:
        raise SystemExit("--top must be positive")

    reference = args.reference.expanduser().resolve()
    mobile = args.mobile.expanduser().resolve()
    if not reference.is_file() or not mobile.is_file():
        raise SystemExit(f"input PDB missing: reference={reference} mobile={mobile}")
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    reference_output = output_dir / "reference.pdb"
    mobile_output = output_dir / "mobile_aligned.pdb"
    if reference in {reference_output, mobile_output} or mobile in {reference_output, mobile_output}:
        raise SystemExit("input PDB must not be one of the fixed derived output paths")

    try:
        ranges = parse_ranges(args.align_range)
        segments = load_segments(args.segments_tsv.expanduser().resolve() if args.segments_tsv else None)
        reference_lines, reference_atoms = parse_pdb(reference)
        mobile_lines, mobile_atoms = parse_pdb(mobile)
        reference_ca = residue_ca(reference_atoms, args.reference_chain)
        mobile_ca = residue_ca(mobile_atoms, args.mobile_chain)
        common = sorted(set(reference_ca) & set(mobile_ca))
        fit_keys = [key for key in common if in_ranges(key[0], ranges)]
        if len(fit_keys) < 3:
            raise ValueError(
                f"alignment selection has {len(fit_keys)} matched C-alpha atoms; need at least 3"
            )
        reference_fit = np.stack([reference_ca[key].coord for key in fit_keys])
        mobile_fit = np.stack([mobile_ca[key].coord for key in fit_keys])
        rotation, translation = fit_transform(mobile_fit, reference_fit)
        mobile_fit_aligned = mobile_fit @ rotation + translation
        transformed = transform_atoms(mobile_atoms, rotation, translation)

        residues: list[dict[str, object]] = []
        for key in common:
            ref_atom, mob_atom = reference_ca[key], mobile_ca[key]
            mobile_coord = mob_atom.coord @ rotation + translation
            names = [
                str(segment["name"])
                for segment in segments
                if int(segment["start"]) <= key[0] <= int(segment["end"])
            ]
            residues.append(
                {
                    "reference_chain": args.reference_chain,
                    "mobile_chain": args.mobile_chain,
                    "auth_seq_id": key[0],
                    "icode": key[1],
                    "reference_resname": ref_atom.resname,
                    "mobile_resname": mob_atom.resname,
                    "ca_displacement_A": round_float(np.linalg.norm(mobile_coord - ref_atom.coord)),
                    "reference_x": round_float(ref_atom.coord[0]),
                    "reference_y": round_float(ref_atom.coord[1]),
                    "reference_z": round_float(ref_atom.coord[2]),
                    "mobile_aligned_x": round_float(mobile_coord[0]),
                    "mobile_aligned_y": round_float(mobile_coord[1]),
                    "mobile_aligned_z": round_float(mobile_coord[2]),
                    "segments": ";".join(names),
                }
            )

        contacts = ligand_contacts(
            mobile_atoms,
            args.mobile_chain,
            {name.upper() for name in args.mobile_ligand_resname},
            args.contact_cutoff,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    shutil.copyfile(reference, reference_output)
    write_aligned_pdb(mobile_output, mobile_lines, transformed, rotation, translation)

    displacement_path = output_dir / "per_residue_displacement.tsv"
    displacement_fields = list(residues[0])
    write_tsv(displacement_path, residues, displacement_fields)
    contact_path = output_dir / "ligand_contacts.tsv"
    if contacts:
        write_tsv(contact_path, contacts, list(contacts[0]))
    elif contact_path.exists():
        contact_path.unlink()

    top_residues = sorted(
        residues, key=lambda row: float(row["ca_displacement_A"]), reverse=True
    )[: args.top]
    mismatches = [
        {
            "auth_seq_id": row["auth_seq_id"],
            "icode": row["icode"],
            "reference_resname": row["reference_resname"],
            "mobile_resname": row["mobile_resname"],
        }
        for row in residues
        if row["reference_resname"] != row["mobile_resname"]
    ]
    metrics_path = output_dir / "comparison_metrics.json"
    metrics = {
        "schema_version": 1,
        "reference": {
            "path": str(reference),
            "sha256": sha256(reference),
            "chain": args.reference_chain,
        },
        "mobile": {
            "path": str(mobile),
            "sha256": sha256(mobile),
            "chain": args.mobile_chain,
        },
        "mapping_contract": (
            "C-alpha atoms matched by identical author residue number and insertion code; "
            "no sequence alignment or renumbering"
        ),
        "alignment": {
            "atom": "CA",
            "ranges": [{"start": start, "end": end} for start, end in ranges],
            "matched_atom_count": len(fit_keys),
            "matched_residue_keys": [
                {"auth_seq_id": key[0], "icode": key[1]} for key in fit_keys
            ],
            "residue_name_mismatches": mismatches,
            "rmsd_before_A": round_float(rmsd(mobile_fit, reference_fit)),
            "rmsd_after_A": round_float(rmsd(mobile_fit_aligned, reference_fit)),
            "row_vector_formula": "x_aligned = x_mobile @ rotation_row + translation",
            "rotation_row": [[round_float(value) for value in row] for row in rotation],
            "rotation_column": [
                [round_float(value) for value in row] for row in rotation.T
            ],
            "translation": [round_float(value) for value in translation],
        },
        "comparison": {
            "matched_residue_count": len(residues),
            "top_residues": top_residues,
            "segments": segment_summaries(residues, segments),
        },
        "ligand_contacts": {
            "mobile_resnames": sorted({name.upper() for name in args.mobile_ligand_resname}),
            "cutoff_A": args.contact_cutoff,
            "count": len(contacts),
            "contacts": contacts,
        },
        "software": {"numpy_version": np.__version__},
        "claim_boundary": (
            "Rigid-fit and endpoint geometry only; this analysis does not establish a "
            "physical transition pathway, ligand causality, thermodynamics, or kinetics"
        ),
    }
    metrics["outputs"] = {
        path.name: {"bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in [reference_output, mobile_output, displacement_path]
        + ([contact_path] if contacts else [])
    }
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "alignment_rmsd_A": metrics["alignment"]["rmsd_after_A"],
                "alignment_atoms": len(fit_keys),
                "matched_residues": len(residues),
                "top_residue": residue_label(top_residues[0]),
                "top_displacement_A": top_residues[0]["ca_displacement_A"],
                "ligand_contact_residues": len(contacts),
                "output_dir": str(output_dir),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
