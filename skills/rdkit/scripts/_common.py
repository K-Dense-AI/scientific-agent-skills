"""Shared, source-index-preserving molecular file reader (no standardization)."""

import sys
from pathlib import Path
from rdkit import Chem

SOURCE_INDEX = "_SkillRDKitSourceIndex"


def read_molecule_records(file_path):
    """Yield (one-based source record, sanitized nonempty Mol).

    SMILES input has no header; first field is SMILES and optional remainder is
    the name. CXSMILES extensions are parsed before names. Blank/comment lines
    are ignored but physical line IDs are retained.
    SDF IDs are supplier record numbers. Invalid records are logged to stderr.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    suffix = path.suffix.lower()
    if suffix in {".smi", ".smiles", ".txt"}:
        with path.open(encoding="utf-8") as stream:
            for index, line in enumerate(stream, 1):
                fields = line.strip().split(maxsplit=1)
                if not fields or fields[0].startswith("#"):
                    continue
                params = Chem.SmilesParserParams()
                params.parseName = True
                mol = Chem.MolFromSmiles(line.strip(), params)
                if mol is None or mol.GetNumAtoms() == 0:
                    print(f"[FAIL] Invalid molecule at record {index}", file=sys.stderr)
                    continue
                mol.SetIntProp(SOURCE_INDEX, index)
                yield index, mol
    elif suffix == ".mol":
        mol = Chem.MolFromMolFile(str(path))
        if mol is None or mol.GetNumAtoms() == 0:
            print("[FAIL] Invalid molecule at record 1", file=sys.stderr)
            return
        mol.SetIntProp(SOURCE_INDEX, 1)
        yield 1, mol
    elif suffix == ".sdf":
        with Chem.SDMolSupplier(str(path)) as supplier:
            for index, mol in enumerate(supplier, 1):
                if mol is None or mol.GetNumAtoms() == 0:
                    print(f"[FAIL] Invalid molecule at record {index}", file=sys.stderr)
                    continue
                # Overwrite any input property with the actual source record.
                mol.SetIntProp(SOURCE_INDEX, index)
                yield index, mol
    else:
        raise ValueError(f"Unsupported file format: {suffix}")


def molecule_smiles(mol):
    """Preserve enhanced stereo groups when plain isomeric SMILES is insufficient."""
    if mol.GetStereoGroups():
        return Chem.MolToCXSmiles(
            mol, Chem.SmilesWriteParams(), flags=Chem.CXSmilesFields.CX_ENHANCEDSTEREO
        )
    return Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)
