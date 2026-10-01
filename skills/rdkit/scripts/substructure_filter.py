#!/usr/bin/env python3
"""
Substructure Filter

Filter molecules based on substructure patterns using SMARTS.
Supports inclusion and exclusion filters, and custom pattern libraries.

Usage:
    python substructure_filter.py molecules.smi --pattern "c1ccccc1" --output filtered.smi
    python substructure_filter.py database.sdf --exclude "C(=O)Cl" --filter-type functional-groups
"""

import argparse
import sys
from pathlib import Path

try:
    from rdkit import Chem
except ImportError:
    print("Error: RDKit not installed. Install with: uv pip install rdkit")
    sys.exit(1)


from _common import SOURCE_INDEX, read_molecule_records, molecule_smiles


# Neutral functional-group motifs; not universal chemistry or toxicity classifiers.
PATTERN_LIBRARIES = {
    'functional-groups': {
        'alcohol': '[OX2H1][CX4]',
        'aldehyde': '[CX3H1](=O)[#6]',
        'ketone': '[#6][CX3](=O)[#6]',
        'carboxylic_acid': 'C(=O)[OH]',
        'ester': '[CX3](=O)[OX2H0][#6]',
        'amide': 'C(=O)N',
        'amine': '[NX3;$(N-[#6]);!$(N-C=O);!$(N-S(=O)=O);!$(N-P=O);!$(N=*)]',
        'ether': '[#6][OX2H0;!$(O-C=O)][#6]',
        'nitrile': 'C#N',
        'nitro': '[N+](=O)[O-]',
        'halide': '[CX4][F,Cl,Br,I]',
        'thiol': '[#6][SX2H1]',
        'sulfide': '[#6][SX2H0][#6]',
    },
    'rings': {
        'benzene': 'c1ccccc1',
        'pyridine': 'n1ccccc1',
        'pyrrole': 'n1cccc1',
        'furan': 'o1cccc1',
        'thiophene': 's1cccc1',
        'imidazole': 'n1cncc1',
        'indole': 'c1ccc2[nH]ccc2c1',
        'naphthalene': 'c1ccc2ccccc2c1',
    },
    'pains': {
        'rhodanine': 'O=C1CSC(=S)N1',
        'catechol': 'c1ccc(O)c(O)c1',
        'quinone': 'O=C1C=CC(=O)C=C1',
        'michael_acceptor': 'C=CC(=O)',
        'alkyl_halide': '[C][I,Br]',
    },
    'privileged': {
        'biphenyl': 'c1ccccc1-c2ccccc2',
        'piperazine': 'N1CCNCC1',
        'piperidine': 'N1CCCCC1',
        'morpholine': 'N1CCOCC1',
    }
}


def load_molecules(file_path, keep_props=True):
    """Load molecules from file."""
    # keep_props retained for callers; RDKit reads SDF properties by default.
    return [mol for _, mol in read_molecule_records(file_path)]


def create_pattern_query(pattern_string):
    """Create SMARTS query from string or SMILES."""
    # Try as SMARTS first
    query = Chem.MolFromSmarts(pattern_string)
    if query is not None and query.GetNumAtoms() > 0:
        return query

    # Try as SMILES
    query = Chem.MolFromSmiles(pattern_string)
    if query is not None and query.GetNumAtoms() > 0:
        return query

    print(f"Error: Invalid pattern: {pattern_string}")
    return None


def filter_molecules(molecules, include_patterns=None, exclude_patterns=None,
                    match_all_include=False, use_chirality=False):
    """
    Filter molecules based on substructure patterns.

    Args:
        molecules: List of RDKit Mol objects
        include_patterns: List of (name, pattern) tuples to include
        exclude_patterns: List of (name, pattern) tuples to exclude
        match_all_include: If True, molecule must match ALL include patterns

    Returns:
        Tuple of (filtered_molecules, match_info)
    """
    for patterns in (include_patterns, exclude_patterns):
        for name, pattern in patterns or []:
            if pattern is None or pattern.GetNumAtoms() == 0:
                raise ValueError(f"Invalid or empty query: {name}")
    filtered = []
    match_info = []

    for idx, mol in enumerate(molecules):
        if mol is None:
            continue

        source_index = mol.GetIntProp(SOURCE_INDEX) if mol.HasProp(SOURCE_INDEX) else idx + 1

        # Check exclusion patterns first
        excluded = False
        exclude_matches = []
        if exclude_patterns:
            for name, pattern in exclude_patterns:
                if mol.HasSubstructMatch(pattern, useChirality=use_chirality):
                    excluded = True
                    exclude_matches.append(name)

        if excluded:
            match_info.append({
                'index': source_index,
                'smiles': molecule_smiles(mol),
                'status': 'excluded',
                'matches': exclude_matches
            })
            continue

        # Check inclusion patterns
        if include_patterns:
            include_matches = []
            for name, pattern in include_patterns:
                if mol.HasSubstructMatch(pattern, useChirality=use_chirality):
                    include_matches.append(name)

            # Decide if molecule passes inclusion filter
            if match_all_include:
                passed = len(include_matches) == len(include_patterns)
            else:
                passed = len(include_matches) > 0

            if passed:
                filtered.append(mol)
                match_info.append({
                    'index': source_index,
                    'smiles': molecule_smiles(mol),
                    'status': 'included',
                    'matches': include_matches
                })
            else:
                match_info.append({
                    'index': source_index,
                    'smiles': molecule_smiles(mol),
                    'status': 'no_match',
                    'matches': []
                })
        else:
            # No inclusion patterns, keep all non-excluded
            filtered.append(mol)
            match_info.append({
                'index': source_index,
                'smiles': molecule_smiles(mol),
                'status': 'included',
                'matches': []
            })

    return filtered, match_info


def write_molecules(molecules, output_file):
    """Write molecules to file."""
    output_path = Path(output_file)

    if output_path.suffix.lower() in ['.sdf']:
        writer = Chem.SDWriter(str(output_path))
        for mol in molecules:
            writer.write(mol)
        writer.close()
    elif output_path.suffix.lower() in ['.smi', '.smiles', '.txt']:
        with open(output_path, 'w') as f:
            for mol in molecules:
                smiles = molecule_smiles(mol)
                name = mol.GetProp('_Name') if mol.HasProp('_Name') else ''
                f.write(f"{smiles} {name}\n")
    else:
        raise ValueError(f'Unsupported output format: {output_path.suffix}')

    print(f"Wrote {len(molecules)} molecules to {output_file}")


def write_report(match_info, output_file):
    """Write detailed match report."""
    import csv

    with open(output_file, 'w', newline='') as f:
        fieldnames = ['Index', 'SMILES', 'Status', 'Matches']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for info in match_info:
            writer.writerow({
                'Index': info['index'],
                'SMILES': info['smiles'],
                'Status': info['status'],
                'Matches': ', '.join(info['matches'])
            })


def print_summary(total, filtered, match_info):
    """Print filtering summary."""
    print("\n" + "="*60)
    print("Filtering Summary")
    print("="*60)
    print(f"Total molecules:     {total}")
    print(f"Passed filter:       {len(filtered)}")
    print(f"Filtered out:        {total - len(filtered)}")
    print(f"Pass rate:           {len(filtered)/total*100:.1f}%")

    # Count by status
    status_counts = {}
    for info in match_info:
        status = info['status']
        status_counts[status] = status_counts.get(status, 0) + 1

    print("\nBreakdown:")
    for status, count in status_counts.items():
        print(f"  {status:15s}: {count}")

    print("="*60)


def main():
    parser = argparse.ArgumentParser(
        description='Filter molecules by substructure patterns',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Pattern libraries:
  --filter-type functional-groups    Common functional groups
  --filter-type rings               Ring systems
  --filter-type pains               Five illustrative alerts, NOT the RDKit PAINS catalogue
  --filter-type privileged          Privileged structures

Examples:
  # Include molecules with benzene ring
  python substructure_filter.py molecules.smi --pattern "c1ccccc1" -o filtered.smi

  # Exclude reactive groups
  python substructure_filter.py database.sdf --exclude "C(=O)Cl" -o clean.sdf

  # Filter by functional groups
  python substructure_filter.py molecules.smi --filter-type functional-groups -o fg.smi

  # Exclude illustrative alert motifs (not a toxicity or PAINS verdict)
  python substructure_filter.py compounds.smi --filter-type pains --exclude-mode -o clean.smi

  # Multiple patterns
  python substructure_filter.py mol.smi --pattern "c1ccccc1" --pattern "N" --match-all -o aromatic_amines.smi
        """
    )

    parser.add_argument('input', nargs='?', help='Input file (SDF or SMILES)')
    parser.add_argument('--pattern', '-p', action='append',
                       help='SMARTS/SMILES pattern to include (can specify multiple)')
    parser.add_argument('--exclude', '-e', action='append',
                       help='SMARTS/SMILES pattern to exclude (can specify multiple)')
    parser.add_argument('--filter-type', choices=PATTERN_LIBRARIES.keys(),
                       help='Use predefined pattern library')
    parser.add_argument('--exclude-mode', action='store_true',
                       help='Use filter-type patterns for exclusion instead of inclusion')
    parser.add_argument('--match-all', action='store_true',
                       help='Molecule must match ALL include patterns')
    parser.add_argument('--chirality', action='store_true',
                       help='Require specified query stereochemistry')
    parser.add_argument('--output', '-o', help='Output file')
    parser.add_argument('--report', '-r', help='Write detailed report to CSV')
    parser.add_argument('--list-patterns', action='store_true',
                       help='List available pattern libraries and exit')

    args = parser.parse_args()

    # List patterns mode
    if args.list_patterns:
        print("\nAvailable Pattern Libraries:")
        print("="*60)
        for lib_name, patterns in PATTERN_LIBRARIES.items():
            print(f"\n{lib_name}:")
            for name, pattern in patterns.items():
                print(f"  {name:25s}: {pattern}")
        sys.exit(0)

    if not args.input:
        parser.error("input is required unless --list-patterns is used")

    # Load molecules
    print(f"Loading molecules from: {args.input}")
    molecules = load_molecules(args.input)
    if not molecules:
        print("Error: No valid molecules loaded")
        sys.exit(1)

    print(f"Loaded {len(molecules)} molecules")

    # Prepare patterns
    include_patterns = []
    exclude_patterns = []

    # Add custom include patterns
    if args.pattern:
        for pattern_str in args.pattern:
            query = create_pattern_query(pattern_str)
            if query is None:
                parser.error(f'Invalid include pattern: {pattern_str}')
            include_patterns.append(('custom', query))

    # Add custom exclude patterns
    if args.exclude:
        for pattern_str in args.exclude:
            query = create_pattern_query(pattern_str)
            if query is None:
                parser.error(f'Invalid exclude pattern: {pattern_str}')
            exclude_patterns.append(('custom', query))

    # Add library patterns
    if args.filter_type:
        lib_patterns = PATTERN_LIBRARIES[args.filter_type]
        for name, pattern_str in lib_patterns.items():
            query = create_pattern_query(pattern_str)
            if query:
                if args.exclude_mode:
                    exclude_patterns.append((name, query))
                else:
                    include_patterns.append((name, query))

    if not include_patterns and not exclude_patterns:
        print("Error: No patterns specified")
        sys.exit(1)

    # Print filter configuration
    print(f"\nFilter configuration:")
    if include_patterns:
        print(f"  Include patterns: {len(include_patterns)}")
        if args.match_all:
            print("  Mode: Match ALL")
        else:
            print("  Mode: Match ANY")
    if exclude_patterns:
        print(f"  Exclude patterns: {len(exclude_patterns)}")

    # Perform filtering
    print("\nFiltering...")
    filtered, match_info = filter_molecules(
        molecules,
        include_patterns=include_patterns if include_patterns else None,
        exclude_patterns=exclude_patterns if exclude_patterns else None,
        match_all_include=args.match_all,
        use_chirality=args.chirality
    )

    # Print summary
    print_summary(len(molecules), filtered, match_info)

    # Write output
    if args.output:
        write_molecules(filtered, args.output)

    if args.report:
        write_report(match_info, args.report)
        print(f"Detailed report written to: {args.report}")


if __name__ == '__main__':
    main()
