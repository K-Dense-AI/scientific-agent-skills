#!/usr/bin/env python3
"""Regenerate `synthetic_actives.csv`, the fixture the test suite is built on.

The fixture is synthetic on purpose.  Real bioactivity tables carry licence and
provenance questions that have no place in a test suite, and a real table cannot
be tuned to make the point unambiguously: here the activity of a compound is
decided by its Bemis-Murcko scaffold family plus a small substituent effect and
a seeded noise term, so a random split can learn the families while a scaffold
split is forced to extrapolate to families it has never seen.

That is the situation the skill exists to expose.  Running this generator again
with the same seed reproduces the checked-in CSV, so the provenance claim is
verifiable rather than asserted.

Fragments are joined with RDKit through a dummy atom rather than by substituting
into a SMILES template: appending `Br` to `c1cnc[nH]1` by string concatenation
puts the bromine on a ring nitrogen and yields a molecule RDKit refuses, which
is exactly the kind of table the skill tells you to clean before modelling.

Usage:

    python make_synthetic_actives.py --output synthetic_actives.csv
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path


#: One ring system per family, carrying a single `[*]` attachment point.  Every
#: member of a family shares one Bemis-Murcko scaffold -- the decorations below
#: are all acyclic, so they drop out of the scaffold -- which is what makes the
#: scaffold split mean what it says.
FAMILIES: tuple[tuple[str, str, float], ...] = (
    ("benzamide", "[*]c1ccccc1C(=O)N", 5.1),
    ("pyridine", "[*]c1ccncc1", 5.8),
    ("naphthalene", "[*]c1ccc2ccccc2c1", 6.6),
    ("indole", "[*]c1ccc2[nH]ccc2c1", 7.4),
    ("quinoline", "[*]c1ccc2ncccc2c1", 8.1),
    ("thiophene", "[*]c1ccsc1", 4.6),
    ("imidazole", "[*]c1cnc[nH]1", 5.5),
    ("piperidine", "[*]C1CCNCC1", 4.1),
    ("morpholine", "[*]C1COCCN1", 6.1),
    ("benzofuran", "[*]c1ccc2occc2c1", 7.0),
    ("pyrazole", "[*]c1cc[nH]n1", 6.9),
    ("pyrimidine", "[*]c1cncnc1", 7.7),
)

#: Decorations, each with its own `[*]` attachment point.  `None` leaves the
#: parent ring unsubstituted.  All are acyclic so they do not alter the scaffold.
DECORATIONS: tuple[tuple[str | None, float], ...] = (
    (None, 0.0),
    ("[*]C", 0.12),
    ("[*]CC", 0.22),
    ("[*]F", 0.31),
    ("[*]Cl", 0.38),
    ("[*]O", -0.24),
    ("[*]OC", -0.15),
    ("[*]N", -0.31),
    ("[*]C(=O)O", -0.08),
    ("[*]C#N", 0.27),
    ("[*]C(F)(F)F", 0.44),
    ("[*]CO", -0.19),
    ("[*]S", 0.16),
    ("[*]Br", 0.35),
    ("[*]CC(C)C", 0.29),
    ("[*]NC(=O)C", -0.05),
)

NOISE_SIGMA = 0.25

#: Families appear over time, so a time split holds out the later chemistry the
#: same way a scaffold split holds out unseen scaffolds.
FIRST_YEAR = 2015

#: A share of compounds is measured twice, which is what makes the group split
#: -- and the CLI's duplicate handling -- worth exercising.
REPEAT_FRACTION = 0.15


def get_rdkit() -> tuple[object, object]:
    """Import RDKit or exit with an install hint."""

    try:
        from rdkit import Chem  # noqa: PLC0415 - optional at import time
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise SystemExit(
            "this generator needs RDKit; install with `uv pip install rdkit`"
        ) from exc
    return Chem, Chem.RWMol


def join(core_smiles: str, decoration: str | None, Chem: object) -> str:
    """Attach ``decoration`` to ``core_smiles`` through their dummy atoms."""

    core = Chem.MolFromSmiles(core_smiles)
    if core is None:
        raise SystemExit(f"core {core_smiles!r} is not a valid SMILES")

    if decoration is None:
        editable = Chem.RWMol(core)
        for atom in editable.GetAtoms():
            if atom.GetAtomicNum() == 0:
                editable.RemoveAtom(atom.GetIdx())
                break
        molecule = editable.GetMol()
        Chem.SanitizeMol(molecule)
        return Chem.MolToSmiles(molecule)

    fragment = Chem.MolFromSmiles(decoration)
    if fragment is None:
        raise SystemExit(f"decoration {decoration!r} is not a valid SMILES")

    combined = Chem.RWMol(Chem.CombineMols(core, fragment))
    dummies = [atom.GetIdx() for atom in combined.GetAtoms() if atom.GetAtomicNum() == 0]
    if len(dummies) != 2:
        raise SystemExit(
            f"joining {core_smiles!r} and {decoration!r} expected 2 attachment points, "
            f"found {len(dummies)}"
        )
    combined.AddBond(dummies[0], dummies[1], Chem.BondType.SINGLE)
    for index in sorted(dummies, reverse=True):
        combined.RemoveAtom(index)
    molecule = combined.GetMol()
    Chem.SanitizeMol(molecule)
    return Chem.MolToSmiles(molecule)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", default="synthetic_actives.csv")
    parser.add_argument("--seed", type=int, default=20_260_930)
    parser.add_argument(
        "--force", action="store_true", help="overwrite an existing output file"
    )
    arguments = parser.parse_args()

    Chem, _ = get_rdkit()
    generator = random.Random(arguments.seed)

    rows: list[tuple[str, float, str, int]] = []
    for family_index, (name, core, base) in enumerate(FAMILIES):
        year = FIRST_YEAR + family_index
        for decoration, effect in DECORATIONS:
            smiles = join(core, decoration, Chem)
            activity = base + effect + generator.gauss(0.0, NOISE_SIGMA)
            rows.append((smiles, round(activity, 3), name, year))
            if generator.random() < REPEAT_FRACTION:
                # A repeat measurement of the same compound: legitimate data, and
                # exactly what a random split leaks across the fold.
                repeat = activity + generator.gauss(0.0, NOISE_SIGMA)
                rows.append((smiles, round(repeat, 3), name, year))

    generator.shuffle(rows)

    destination = Path(arguments.output)
    if destination.exists() and not arguments.force:
        raise SystemExit(f"{destination} exists; pass --force to overwrite it")
    lines = ["smiles,pIC50,series,year"]
    lines.extend(f"{smiles},{activity},{series},{year}" for smiles, activity, series, year in rows)
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} rows to {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
