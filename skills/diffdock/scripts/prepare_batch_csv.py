#!/usr/bin/env python3
"""
DiffDock Batch CSV Preparation and Validation Script

This script helps prepare and validate CSV files for DiffDock batch processing.
It checks for required columns, validates file paths, and ensures SMILES strings
are properly formatted.

Usage:
    python prepare_batch_csv.py input.csv --validate
    python prepare_batch_csv.py --create --output batch_input.csv
"""

import argparse
import csv
import re
import os
import sys
import pandas as pd
from pathlib import Path

try:
    from rdkit import Chem
    from rdkit import RDLogger
    RDLogger.DisableLog('rdApp.*')
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False
    print("[WARN] RDKit not available. SMILES-only rows cannot pass validation.")


def validate_smiles(smiles_string):
    """Validate a SMILES string using RDKit."""
    if not RDKIT_AVAILABLE:
        return False, "RDKit not available; chemistry validation was not performed"

    try:
        mol = Chem.MolFromSmiles(smiles_string)
        if mol is None or mol.GetNumAtoms() == 0:
            return False, "Invalid SMILES structure"
        return True, "Valid SMILES"
    except Exception as e:
        return False, str(e)


def validate_file_path(file_path, base_dir=None):
    """Validate that a file path exists."""
    if pd.isna(file_path) or file_path == "":
        return True, "Empty (will use protein_sequence)"

    # Handle relative paths
    if base_dir:
        full_path = Path(base_dir) / file_path
    else:
        full_path = Path(file_path)

    if full_path.is_file():
        return True, f"File exists: {full_path}"
    else:
        return False, f"File not found: {full_path}"


def validate_csv(csv_path, base_dir=None):
    """
    Validate a DiffDock batch input CSV file.

    Args:
        csv_path: Path to CSV file
        base_dir: Inference working directory for relative paths (default: current directory)

    Returns:
        bool: True if validation passes
        list: List of validation messages
    """
    messages = []
    valid = True

    # Read CSV
    try:
        with open(csv_path, newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle, strict=True)
            header = next(reader)
            if len(header) != len(set(header)):
                raise ValueError("Duplicate CSV column names")
            for line_number, fields in enumerate(reader, 2):
                if len(fields) != len(header):
                    raise ValueError(f"CSV row {line_number} has {len(fields)} fields; expected {len(header)}")
        df = pd.read_csv(csv_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        messages.append(f"[OK] Successfully read CSV with {len(df)} rows")
    except Exception as e:
        messages.append(f"[FAIL] Error reading CSV: {e}")
        return False, messages

    # Check required columns
    required_cols = ['complex_name', 'protein_path', 'ligand_description', 'protein_sequence']
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        messages.append(f"[FAIL] Missing required columns: {', '.join(missing_cols)}")
        valid = False
    else:
        messages.append("[OK] All required columns present")

    # Set base directory
    if base_dir is None:
        base_dir = Path.cwd()

    if df.empty:
        messages.append("[FAIL] CSV contains no complexes")
        valid = False
    seen_names = set()

    # Validate each row. The per-row checks index the required columns
    # directly, so they can only run once every one of them is present --
    # otherwise a CSV missing a column raises KeyError instead of reporting it.
    rows = [] if missing_cols else df.iterrows()
    for idx, row in rows:
        row_msgs = []

        # Names become output directory names and ESM labels upstream.
        name = row['complex_name']
        if not name:
            row_msgs.append("Missing complex_name")
            valid = False
        elif not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", name) or name in {"NA", "N/A", "NULL", "null", "None", "NaN", "nan"}:
            row_msgs.append("Unsafe complex_name; use a letter/underscore followed by letters, digits, _, . or - (not an NA token)")
            valid = False
        if name in seen_names:
            row_msgs.append("Duplicate complex_name would overwrite output")
            valid = False
        seen_names.add(name)

        # Check that either protein_path or protein_sequence is provided
        has_protein_path = not pd.isna(row['protein_path']) and row['protein_path'] != ""
        has_protein_seq = not pd.isna(row['protein_sequence']) and row['protein_sequence'] != ""

        if not has_protein_path and not has_protein_seq:
            row_msgs.append("Must provide either protein_path or protein_sequence")
            valid = False
        elif has_protein_path and has_protein_seq:
            row_msgs.append("Warning: Both protein_path and protein_sequence provided, will use protein_path")

        # Validate protein path if provided
        if has_protein_path:
            file_valid, msg = validate_file_path(row['protein_path'], base_dir)
            if not file_valid:
                row_msgs.append(f"Protein file issue: {msg}")
                valid = False

        if has_protein_seq and not has_protein_path:
            sequence = row['protein_sequence']
            if not re.fullmatch(r"[ACDEFGHIKLMNPQRSTVWYXBZUO]+(?::[ACDEFGHIKLMNPQRSTVWYXBZUO]+)*", sequence):
                row_msgs.append("Invalid protein_sequence; provide full uppercase amino-acid sequence, no ellipsis")
                valid = False
            elif any(len(chain) > 1022 for chain in sequence.split(':')):
                row_msgs.append("Protein chain exceeds upstream inference ESM truncation length (1022 residues)")
                valid = False

        # Upstream tries SMILES first: / and backslash encode stereochemistry.
        ligand_desc = row['ligand_description']
        if not ligand_desc:
            row_msgs.append("Missing ligand_description")
            valid = False
        else:
            smiles_valid, msg = validate_smiles(ligand_desc)
            if not smiles_valid:
                suffix = Path(ligand_desc).suffix
                if suffix in {'.sdf', '.mol2', '.pdb', '.pdbqt'}:
                    file_valid, file_msg = validate_file_path(ligand_desc, base_dir)
                    if not file_valid:
                        row_msgs.append(f"Ligand file issue: {file_msg}")
                        valid = False
                else:
                    row_msgs.append(f"SMILES issue: {msg}")
                    valid = False

        if row_msgs:
            messages.append(f"\nRow {idx + 1} ({row.get('complex_name', 'unnamed')}):")
            for msg in row_msgs:
                messages.append(f"  - {msg}")

    # Summary
    messages.append(f"\n{'='*60}")
    if valid:
        messages.append("[OK] CSV validation PASSED - input paths and SMILES checked; docking and file chemistry not validated")
    else:
        messages.append("[FAIL] CSV validation FAILED - please fix issues above")

    return valid, messages


def create_template_csv(output_path, num_examples=3):
    """Create a template CSV file with example entries."""

    if num_examples < 1:
        raise ValueError("num_examples must be at least 1")
    examples = {
        'complex_name': ['example1', 'example2', 'example3'][:num_examples],
        'protein_path': ['protein1.pdb', '', 'protein3.pdb'][:num_examples],
        'ligand_description': [
            'CC(=O)Oc1ccccc1C(=O)O',  # Aspirin SMILES
            'COc1ccc(C#N)cc1',  # Example SMILES
            'ligand.sdf'  # Example file path
        ][:num_examples],
        'protein_sequence': [
            '',  # Empty - using PDB file
            'MSKGEELFTGVVPILVELDGDVNGHKFSVSGEGEGDATYGKLTLKFICTTGKLPVPWPTLVTTFSYGVQCFSRYPDHMKQHDFFKSAMPEGYVQERTIFFKDDGNYKTRAEVKFEGDTLVNRIELKGIDFKEDGNILGHKLEYNYNSHNVYIMADKQKNGIKVNFKIRHNIEDGSVQLADHYQQNTPIGDGPVLLPDNHYLSTQSALSKDPNEKRDHMVLLEFVTAAGITHGMDELYK',  # GFP sequence
            ''  # Empty - using PDB file
        ][:num_examples]
    }

    df = pd.DataFrame(examples)
    df.to_csv(output_path, index=False)

    return df


def main():
    parser = argparse.ArgumentParser(
        description='Prepare and validate DiffDock batch CSV files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate existing CSV
  python prepare_batch_csv.py input.csv --validate

  # Create template CSV
  python prepare_batch_csv.py --create --output batch_template.csv

  # Create template with 2 example rows
  python prepare_batch_csv.py --create --output template.csv --num-examples 2

  # Validate with custom base directory for relative paths
  python prepare_batch_csv.py input.csv --validate --base-dir /path/to/data/
        """
    )

    parser.add_argument('csv_file', nargs='?', help='CSV file to validate')
    parser.add_argument('--validate', action='store_true',
                        help='Validate the CSV file')
    parser.add_argument('--create', action='store_true',
                        help='Create a template CSV file')
    parser.add_argument('--output', '-o', help='Output path for template CSV')
    parser.add_argument('--num-examples', type=int, default=3,
                        help='Number of example rows in template, 1-3 (default: 3)')
    parser.add_argument('--base-dir', help='Planned inference working directory for relative paths (default: current directory)')

    args = parser.parse_args()

    # Create template
    if args.create:
        output_path = args.output or 'diffdock_batch_template.csv'
        df = create_template_csv(output_path, args.num_examples)
        print(f"[OK] Created template CSV: {output_path}")
        print(f"\nTemplate contents:")
        print(df.to_string(index=False))
        print(f"\nEdit this file with your protein-ligand pairs and run with:")
        print(f"  python -m inference --config default_inference_args.yaml \\")
        print(f"    --protein_ligand_csv {output_path} --out_dir results/")
        return 0

    # Validate CSV
    if args.validate or args.csv_file:
        if not args.csv_file:
            print("Error: CSV file required for validation")
            parser.print_help()
            return 1

        if not os.path.exists(args.csv_file):
            print(f"Error: CSV file not found: {args.csv_file}")
            return 1

        print(f"Validating: {args.csv_file}")
        print("="*60)

        valid, messages = validate_csv(args.csv_file, args.base_dir)

        for msg in messages:
            print(msg)

        return 0 if valid else 1

    # No action specified
    parser.print_help()
    return 1


if __name__ == '__main__':
    sys.exit(main())
