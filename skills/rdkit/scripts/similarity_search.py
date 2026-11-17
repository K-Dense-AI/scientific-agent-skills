#!/usr/bin/env python3
"""
Molecular Similarity Search

Perform fingerprint-based similarity screening against a database of molecules.
Supports multiple fingerprint types and similarity metrics.

Usage:
    python similarity_search.py "CCO" database.smi --threshold 0.7
    python similarity_search.py query.smi database.sdf --method morgan --output hits.csv
"""

import argparse
import sys
import math
import json
from itertools import islice
from pathlib import Path

try:
    from rdkit import Chem, rdBase
    from rdkit.Chem import MACCSkeys, rdFingerprintGenerator
    from rdkit import DataStructs
except ImportError:
    print("Error: RDKit not installed. Install with: uv pip install rdkit")
    sys.exit(1)


from _common import read_molecule_records, molecule_smiles


FINGERPRINT_METHODS = {
    'morgan': 'Morgan fingerprint (ECFP-like)',
    'rdkit': 'RDKit topological fingerprint',
    'maccs': 'MACCS structural keys',
    'atompair': 'Atom pair fingerprint',
    'torsion': 'Topological torsion fingerprint'
}


def create_generator(method='morgan', radius=2, n_bits=2048, include_chirality=False):
    """Create one reusable generator; MACCS uses its dedicated API instead."""
    method = method.lower()
    if radius < 0 or n_bits <= 0:
        raise ValueError("radius must be nonnegative and n_bits must be positive")
    if include_chirality and method in {'rdkit', 'maccs'}:
        raise ValueError(f"{method} does not support include_chirality")

    if method == 'morgan':
        return rdFingerprintGenerator.GetMorganGenerator(radius=radius, fpSize=n_bits, includeChirality=include_chirality)
    elif method == 'rdkit':
        return rdFingerprintGenerator.GetRDKitFPGenerator(maxPath=7, fpSize=n_bits)
    elif method == 'maccs':
        return None
    elif method == 'atompair':
        return rdFingerprintGenerator.GetAtomPairGenerator(fpSize=n_bits, includeChirality=include_chirality)
    elif method == 'torsion':
        return rdFingerprintGenerator.GetTopologicalTorsionGenerator(fpSize=n_bits, includeChirality=include_chirality)
    else:
        raise ValueError(f"Unknown fingerprint method: {method}")


def generate_fingerprint(mol, method='morgan', radius=2, n_bits=2048,
                         include_chirality=False):
    """Generate one fingerprint; search separately checks for all-zero vectors."""
    if mol is None or mol.GetNumAtoms() == 0:
        return None
    generator = create_generator(method, radius, n_bits, include_chirality)
    return generator.GetFingerprint(mol) if generator is not None else MACCSkeys.GenMACCSKeys(mol)


def load_molecules(file_path):
    """Load molecules from file."""
    return [
        {'index': index,
         'name': mol.GetProp('_Name') if mol.HasProp('_Name') else f'Mol_{index}',
         'smiles': molecule_smiles(mol), 'mol': mol}
        for index, mol in read_molecule_records(file_path)
    ]


def similarity_search(query_mol, database, method='morgan', threshold=0.7,
                     radius=2, n_bits=2048, metric='tanimoto', include_chirality=False,
                     batch_size=1000, num_threads=1, metadata=None):
    """
    Perform similarity search.

    Args:
        query_mol: Query molecule (RDKit Mol object)
        database: Iterable of database entries, in source order
        method: Fingerprint method
        threshold: Similarity threshold (0-1)
        radius: Morgan fingerprint radius
        n_bits: Fingerprint size
        metric: Similarity metric (tanimoto, dice, cosine)
        batch_size: Maximum database entries per fingerprint batch
        num_threads: Positive thread count for generator batch APIs (not MACCS)
        metadata: Optional dict populated with effective parameters and counts

    Returns:
        List of hits with similarity scores
    """
    if not math.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("threshold must be finite and between 0 and 1")
    if (not isinstance(batch_size, int) or batch_size <= 0 or
            not isinstance(num_threads, int) or num_threads <= 0):
        raise ValueError("batch_size and num_threads must be positive integers")
    if query_mol is None or query_mol.GetNumAtoms() == 0:
        raise ValueError("Invalid or empty query molecule")

    method, metric = method.lower(), metric.lower()
    generator = create_generator(method, radius, n_bits, include_chirality)
    query_fp = (generator.GetFingerprint(query_mol) if generator is not None
                else MACCSkeys.GenMACCSKeys(query_mol))
    if query_fp.GetNumOnBits() == 0:
        raise ValueError(f"Query has an all-zero {method} fingerprint; choose a suitable fingerprint method")

    # Choose similarity function
    if metric.lower() == 'tanimoto':
        sim_func = DataStructs.BulkTanimotoSimilarity
    elif metric.lower() == 'dice':
        sim_func = DataStructs.BulkDiceSimilarity
    elif metric.lower() == 'cosine':
        sim_func = DataStructs.BulkCosineSimilarity
    else:
        raise ValueError(f"Unknown similarity metric: {metric}")

    # Batch fingerprints without changing source order or tie ordering.
    hits = []
    counts = {'input_records': 0, 'invalid_molecules': 0, 'zero_fingerprints': 0,
              'scored_records': 0}
    zero_indices = []
    entries = iter(database)
    while batch := list(islice(entries, batch_size)):
        counts['input_records'] += len(batch)
        valid = [entry for entry in batch
                 if entry['mol'] is not None and entry['mol'].GetNumAtoms() > 0]
        counts['invalid_molecules'] += len(batch) - len(valid)
        if not valid:
            continue
        mols = [entry['mol'] for entry in valid]
        fps = (generator.GetFingerprints(mols, numThreads=num_threads) if generator is not None
               else [MACCSkeys.GenMACCSKeys(mol) for mol in mols])
        scored, nonzero = [], []
        for entry, fp in zip(valid, fps):
            if fp.GetNumOnBits() == 0:
                zero_indices.append(entry['index'])
                counts['zero_fingerprints'] += 1
            else:
                scored.append(entry)
                nonzero.append(fp)
        counts['scored_records'] += len(scored)
        for db_entry, similarity in zip(scored, sim_func(query_fp, nonzero)):
            if similarity >= threshold:
                hits.append({
                    'index': db_entry['index'],
                    'name': db_entry['name'],
                    'smiles': db_entry['smiles'],
                    'similarity': similarity
                })

    # Sort by similarity (descending)
    hits.sort(key=lambda x: x['similarity'], reverse=True)
    if zero_indices:
        print(f"[WARN] Skipped {len(zero_indices)} all-zero {method} database fingerprints",
              file=sys.stderr)
    if metadata is not None:
        metadata.clear()
        metadata.update({
            'schema_version': 1,
            'rdkit_version': rdBase.rdkitVersion,
            'query_smiles': molecule_smiles(query_mol),
            'fingerprint': {
                'method': method, 'representation': 'bit',
                'radius': radius if method == 'morgan' else None,
                'bits': query_fp.GetNumBits(), 'include_chirality': include_chirality,
                'generator_info': generator.GetInfoString() if generator is not None else None,
                'implementation': 'rdFingerprintGenerator' if generator is not None else 'MACCSkeys.GenMACCSKeys',
            },
            'metric': metric, 'threshold': threshold,
            'batch_size': batch_size,
            'num_threads': num_threads if generator is not None else 1,
            'requested': {'radius': radius, 'bits': n_bits, 'num_threads': num_threads},
            'zero_fingerprint_policy': {'query': 'error', 'database': 'skip'},
            'zero_fingerprint_source_indices': zero_indices,
            'counts': {**counts, 'hits': len(hits)},
        })

    return hits


def write_results(hits, output_file):
    """Write results to CSV file."""
    import csv

    with open(output_file, 'w', newline='') as f:
        fieldnames = ['Rank', 'Index', 'Name', 'SMILES', 'Similarity']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for rank, hit in enumerate(hits, 1):
            writer.writerow({
                'Rank': rank,
                'Index': hit['index'],
                'Name': hit['name'],
                'SMILES': hit['smiles'],
                'Similarity': f"{hit['similarity']:.4f}"
            })


def print_results(hits, max_display=20):
    """Print results to console."""
    if not hits:
        print("\nNo hits found above threshold")
        return

    print(f"\nFound {len(hits)} similar molecules:")
    print("="*80)
    print(f"{'Rank':<6} {'Index':<8} {'Similarity':<12} {'Name':<20} {'SMILES'}")
    print("-"*80)

    for rank, hit in enumerate(hits[:max_display], 1):
        name = hit['name'][:18] + '..' if len(hit['name']) > 20 else hit['name']
        smiles = hit['smiles'][:40] + '...' if len(hit['smiles']) > 43 else hit['smiles']
        print(f"{rank:<6} {hit['index']:<8} {hit['similarity']:<12.4f} {name:<20} {smiles}")

    if len(hits) > max_display:
        print(f"\n... and {len(hits) - max_display} more")

    print("="*80)


def main():
    parser = argparse.ArgumentParser(
        description='Molecular similarity search using fingerprints',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available fingerprint methods:
{chr(10).join(f'  {k:12s} - {v}' for k, v in FINGERPRINT_METHODS.items())}

Similarity metrics:
  tanimoto    - Tanimoto coefficient (default)
  dice        - Dice coefficient
  cosine      - Cosine similarity

Examples:
  # Search with SMILES query
  python similarity_search.py "CCO" database.smi --threshold 0.7

  # Use different fingerprint
  python similarity_search.py query.smi database.sdf --method maccs

  # Save results
  python similarity_search.py "c1ccccc1" database.smi --output hits.csv

  # Adjust Morgan radius
  python similarity_search.py "CCO" database.smi --method morgan --radius 3
        """
    )

    parser.add_argument('query', help='Query SMILES or file')
    parser.add_argument('database', help='Database file (SDF or SMILES)')
    parser.add_argument('--method', '-m', default='morgan',
                       choices=FINGERPRINT_METHODS.keys(),
                       help='Fingerprint method (default: morgan)')
    parser.add_argument('--threshold', '-t', type=float, default=0.7,
                       help='Similarity threshold (default: 0.7)')
    parser.add_argument('--radius', '-r', type=int, default=2,
                       help='Morgan fingerprint radius (default: 2)')
    parser.add_argument('--bits', '-b', type=int, default=2048,
                       help='Fingerprint size (default: 2048)')
    parser.add_argument('--chirality', action='store_true',
                       help='Include chirality (Morgan, atom pair, torsion only)')
    parser.add_argument('--metric', default='tanimoto',
                       choices=['tanimoto', 'dice', 'cosine'],
                       help='Similarity metric (default: tanimoto)')
    parser.add_argument('--output', '-o', help='Output CSV and <output>.metadata.json sidecar')
    parser.add_argument('--batch-size', type=int, default=1000,
                       help='Database entries per fingerprint batch (default: 1000)')
    parser.add_argument('--num-threads', type=int, default=1,
                       help='Fingerprint batch threads (positive; MACCS remains single-threaded)')
    parser.add_argument('--max-display', type=int, default=20,
                       help='Maximum hits to display (default: 20)')

    args = parser.parse_args()

    if not math.isfinite(args.threshold) or not 0 <= args.threshold <= 1:
        parser.error("threshold must be finite and between 0 and 1")
    if args.radius < 0 or args.bits <= 0 or args.max_display <= 0:
        parser.error("radius must be nonnegative; bits and max-display must be positive")
    if args.chirality and args.method in {'rdkit', 'maccs'}:
        parser.error(f"{args.method} does not support --chirality")
    if args.batch_size <= 0 or args.num_threads <= 0:
        parser.error('batch-size and num-threads must be positive')

    # Load query
    query_path = Path(args.query)
    if query_path.exists():
        # Query is a file
        query_mols = load_molecules(args.query)
        if not query_mols:
            print("Error: No valid molecules in query file")
            sys.exit(1)
        if len(query_mols) != 1:
            parser.error('Query file must contain exactly one valid molecule')
        query_mol = query_mols[0]['mol']
        query_smiles = query_mols[0]['smiles']
    else:
        # Query is SMILES string
        query_mol = Chem.MolFromSmiles(args.query)
        query_smiles = args.query
        if query_mol is None or query_mol.GetNumAtoms() == 0:
            print(f"Error: Failed to parse query SMILES: {args.query}")
            sys.exit(1)

    print(f"Query: {query_smiles}")
    print(f"RDKit: {rdBase.rdkitVersion}; method={args.method}; radius={args.radius}; "
          f"bits={167 if args.method == 'maccs' else args.bits}; "
          f"chirality={args.chirality}; metric={args.metric}")
    print(f"Threshold: {args.threshold}")
    print(f"Loading database: {args.database}...")

    # Load database
    database = load_molecules(args.database)
    if not database:
        print("Error: No valid molecules in database")
        sys.exit(1)

    print(f"Loaded {len(database)} molecules")
    print("Searching...")

    # Perform search
    metadata = {}
    try:
        hits = similarity_search(
            query_mol, database, method=args.method, threshold=args.threshold,
            radius=args.radius, n_bits=args.bits, metric=args.metric,
            include_chirality=args.chirality, batch_size=args.batch_size,
            num_threads=args.num_threads, metadata=metadata
        )
    except ValueError as error:
        parser.error(str(error))

    # Output results
    if args.output:
        write_results(hits, args.output)
        metadata['database_file'] = str(args.database)
        metadata['csv_similarity_decimal_places'] = 4
        metadata_path = Path(str(args.output) + '.metadata.json')
        metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + '\n',
                                 encoding='utf-8')
        print(f"\nResults written to: {args.output}")
        print(f"Search metadata written to: {metadata_path}")

    print_results(hits, args.max_display)


if __name__ == '__main__':
    main()
