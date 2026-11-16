#!/usr/bin/env python3
"""Validate and standardize retrosynthesis targets with RDKit before a search.

Reads a SMILES file (one molecule per line, optional whitespace-separated ID),
writes the accepted targets as canonical isomeric SMILES, one per line, in the
format `aizynthcli --smiles` expects, and writes a CSV report that keeps every
input row, including rejected ones, so batch results can be joined back to the
original IDs.

Example:
    python prepare_targets.py targets.smi clean.smi --report targets_report.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from rdkit import Chem, RDLogger
from rdkit.Chem.MolStandardize import rdMolStandardize

# Elements well covered by USPTO-derived reaction templates. Anything else is
# flagged, not rejected: the search may still run, but expect few templates.
COMMON_ELEMENTS = frozenset({"H", "B", "C", "N", "O", "F", "Si", "P", "S", "Cl", "Se", "Br", "I"})

REPORT_FIELDS = ["line", "id", "input_smiles", "smiles", "inchikey", "heavy_atoms", "status", "flags", "message"]


def read_records(path: Path):
    """Yield (line_number, id, smiles) for each non-blank, non-comment line."""
    with path.open(encoding="utf-8") as handle:
        for number, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(maxsplit=1)
            identifier = parts[1].strip() if len(parts) > 1 else f"line{number}"
            yield number, identifier, parts[0]


def stereo_flags(mol):
    """Flags for stereo elements that the SMILES leaves undefined."""
    flags = []
    undefined_centers = 0
    undefined_bonds = 0
    for info in Chem.FindPotentialStereo(mol):
        if info.specified != Chem.StereoSpecified.Unspecified:
            continue
        if info.type == Chem.StereoType.Atom_Tetrahedral:
            undefined_centers += 1
        elif info.type == Chem.StereoType.Bond_Double:
            undefined_bonds += 1
    if undefined_centers:
        flags.append(f"undefined_stereocenters={undefined_centers}")
    if undefined_bonds:
        flags.append(f"undefined_double_bond_stereo={undefined_bonds}")
    return flags


def prepare(smiles: str, keep_salts: bool = False, neutralize: bool = True):
    """Return (mol, flags) for a usable target, or (None, reason) when rejected."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None, "RDKit could not parse or sanitize the SMILES"
    if mol.GetNumAtoms() == 0:
        return None, "empty molecule"
    flags = []
    fragments = Chem.GetMolFrags(mol)
    if len(fragments) > 1:
        if keep_salts:
            flags.append(f"multiple_fragments={len(fragments)}")
        else:
            mol = rdMolStandardize.LargestFragmentChooser(preferOrganic=True).choose(mol)
            flags.append(f"kept_largest_of_{len(fragments)}_fragments")
    if neutralize:
        before = Chem.MolToSmiles(mol)
        mol = rdMolStandardize.Uncharger().uncharge(mol)
        if Chem.MolToSmiles(mol) != before:
            flags.append("neutralized")
    net_charge = Chem.GetFormalCharge(mol)
    if net_charge:
        flags.append(f"net_charge={net_charge:+d}")
    unusual = sorted({atom.GetSymbol() for atom in mol.GetAtoms()} - COMMON_ELEMENTS)
    if unusual:
        flags.append("uncommon_elements=" + "/".join(unusual))
    if any(atom.GetIsotope() for atom in mol.GetAtoms()):
        flags.append("isotopes")
    if any(atom.GetNumRadicalElectrons() for atom in mol.GetAtoms()):
        flags.append("radicals")
    flags.extend(stereo_flags(mol))
    if mol.GetNumHeavyAtoms() < 6:
        flags.append("very_small")
    return mol, flags


def run(input_path: Path, output_path: Path, report_path: Path, keep_salts: bool, neutralize: bool):
    rows, accepted, seen = [], [], {}
    for number, identifier, smiles in read_records(input_path):
        row = {"line": number, "id": identifier, "input_smiles": smiles, "smiles": "", "inchikey": "",
               "heavy_atoms": "", "status": "rejected", "flags": "", "message": ""}
        mol, result = prepare(smiles, keep_salts=keep_salts, neutralize=neutralize)
        if mol is None:
            row["message"] = result
        else:
            canonical = Chem.MolToSmiles(mol)
            row.update(smiles=canonical, inchikey=Chem.MolToInchiKey(mol), heavy_atoms=mol.GetNumHeavyAtoms(),
                       flags=";".join(result))
            if canonical in seen:
                row.update(status="duplicate", message=f"same canonical SMILES as line {seen[canonical]}")
            else:
                seen[canonical] = number
                row["status"] = "ok"
                accepted.append(canonical)
        rows.append(row)

    output_path.write_text("".join(f"{smi}\n" for smi in accepted), encoding="utf-8")
    with report_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return rows, accepted


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("input", type=Path, help="SMILES file: one SMILES per line, optional ID after whitespace")
    parser.add_argument("output", type=Path, help="accepted targets, one canonical SMILES per line")
    parser.add_argument("--report", type=Path, default=None,
                        help="CSV report of every input row (default: <output>.report.csv)")
    parser.add_argument("--keep-salts", action="store_true",
                        help="keep all fragments instead of the largest organic fragment")
    parser.add_argument("--no-neutralize", action="store_true", help="do not neutralize charges")
    args = parser.parse_args(argv)

    if not args.input.is_file():
        parser.error(f"input file not found: {args.input}")
    report = args.report or args.output.with_name(args.output.name + ".report.csv")
    RDLogger.DisableLog("rdApp.*")
    rows, accepted = run(args.input, args.output, report, args.keep_salts, not args.no_neutralize)
    flagged = sum(1 for row in rows if row["status"] == "ok" and row["flags"])
    rejected = sum(1 for row in rows if row["status"] == "rejected")
    duplicates = sum(1 for row in rows if row["status"] == "duplicate")
    print(f"[OK] {len(accepted)} targets written to {args.output}")
    print(f"-> flagged {flagged}, rejected {rejected}, duplicates {duplicates}; report: {report}")
    if not accepted:
        print("[FAIL] no usable targets", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
