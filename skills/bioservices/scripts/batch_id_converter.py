#!/usr/bin/env python3
"""
Batch Identifier Converter

This script converts multiple identifiers between biological databases
using UniProt's mapping service. Supports batch processing with
automatic chunking and error handling.

Usage:
    python batch_id_converter.py INPUT_FILE --from DB1 --to DB2 [options]

Examples:
    python batch_id_converter.py uniprot_ids.txt --from UniProtKB_AC-ID --to KEGG
    python batch_id_converter.py gene_ids.txt --from GeneID --to UniProtKB --output mapping.csv
    python batch_id_converter.py ids.txt --from UniProtKB_AC-ID --to Ensembl --chunk-size 50

Input file format:
    One identifier per line (plain text)

Common database codes:
    UniProtKB_AC-ID  - UniProt accession/ID
    KEGG             - KEGG gene IDs
    GeneID           - NCBI Gene (Entrez) IDs
    Ensembl          - Ensembl gene IDs
    Ensembl_Protein  - Ensembl protein IDs
    RefSeq_Protein   - RefSeq protein IDs
    PDB              - Protein Data Bank IDs
    HGNC             - HGNC identifiers (not gene symbols)
"""

import sys
import argparse
import csv
import time
from pathlib import Path
from bioservices import UniProt


# Common database code mappings
DATABASE_CODES = {
    'uniprot': 'UniProtKB_AC-ID',
    'uniprotkb': 'UniProtKB_AC-ID',
    'kegg': 'KEGG',
    'geneid': 'GeneID',
    'entrez': 'GeneID',
    'ensembl': 'Ensembl',
    'ensembl_protein': 'Ensembl_Protein',
    'ensembl_transcript': 'Ensembl_Transcript',
    'refseq': 'RefSeq_Protein',
    'refseq_protein': 'RefSeq_Protein',
    'pdb': 'PDB',
    'hgnc': 'HGNC',
    'mgi': 'MGI',
    'reactome': 'Reactome',
    'string': 'STRING',
    'biogrid': 'BioGRID'
}


def normalize_database_code(code, target=False):
    """Normalize database code to official format."""
    if target and code.lower() in {"uniprot", "uniprotkb"}:
        return "UniProtKB"
    # Try exact match first
    if code in DATABASE_CODES.values():
        return code

    # Try lowercase lookup
    lowercase = code.lower()
    if lowercase in DATABASE_CODES:
        return DATABASE_CODES[lowercase]

    # Return as-is if not found (may still be valid)
    return code


def read_ids_from_file(filename):
    """Read identifiers from file (one per line)."""
    print(f"Reading identifiers from {filename}...")

    ids = []
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                ids.append(line)

    print(f"[OK] Read {len(ids)} identifier(s)")

    return ids


def mapping_to_lists(response):
    """Normalize the 1.16 mapping envelope without losing one-to-many matches.

    UniProtKB targets are records; KEGG and many other targets are strings.
    A missing/invalid envelope is a service failure, not an unmapped result.
    """
    if not isinstance(response, dict) or not ({"results", "failedIds"} & response.keys()):
        raise ValueError("UniProt mapping did not return results/failedIds")
    mapping = {}
    for row in response.get("results", []):
        source, target = row["from"], row["to"]
        if isinstance(target, dict):
            target = target.get("primaryAccession") or target.get("uniParcId") or target.get("id")
        if not isinstance(source, str) or not isinstance(target, str) or not target:
            raise ValueError("Unsupported mapping record; preserve and inspect the raw response")
        values = mapping.setdefault(source, [])
        if target not in values:
            values.append(target)
    for identifier in response.get("failedIds", []):
        mapping.setdefault(identifier, [])
    return mapping


def batch_convert(ids, from_db, to_db, chunk_size=100, delay=0.5):
    """Return mapping and unresolved IDs; [] means explicitly unmapped, None failed."""
    if chunk_size < 1 or chunk_size > 100000 or delay < 0:
        raise ValueError("chunk_size must be 1..100000 and delay nonnegative")
    u = UniProt(verbose=False)
    all_results = {}
    for i in range(0, len(ids), chunk_size):
        chunk = ids[i:i + chunk_size]
        try:
            result = mapping_to_lists(u.mapping(fr=from_db, to=to_db, query=",".join(chunk)))
            all_results.update({identifier: result.get(identifier) for identifier in chunk})
        except Exception as error:
            print(f"[FAIL] Batch lookup: {error}; retrying individual identifiers")
            for identifier in chunk:
                try:
                    result = mapping_to_lists(u.mapping(fr=from_db, to=to_db, query=identifier))
                    all_results[identifier] = result.get(identifier)
                except Exception as retry_error:
                    print(f"[FAIL] {identifier}: {retry_error}")
                    all_results[identifier] = None
                if delay:
                    time.sleep(delay)
        if delay and i + chunk_size < len(ids):
            time.sleep(delay)
    failed_ids = [identifier for identifier in dict.fromkeys(ids) if not all_results.get(identifier)]
    print(f"[OK] Mapped {sum(bool(v) for v in all_results.values())}/{len(all_results)} unique IDs")
    return all_results, failed_ids


def save_mapping_csv(mapping, output_file, from_db, to_db):
    """Save mapping results to CSV."""
    print(f"\nSaving results to {output_file}...")

    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)

        # Header
        writer.writerow(['Source_ID', 'Source_DB', 'Target_IDs', 'Target_DB', 'Mapping_Status'])

        # Data
        for source_id, target_ids in sorted(mapping.items()):
            if target_ids:
                target_str = ";".join(target_ids)
                status = "Success"
            else:
                target_str = ""
                status = "Unmapped" if target_ids == [] else "Failed"

            writer.writerow([source_id, from_db, target_str, to_db, status])

    print(f"[OK] Results saved")


def save_failed_ids(failed_ids, output_file):
    """Save failed IDs to file."""
    if not failed_ids:
        return

    print(f"\nSaving failed IDs to {output_file}...")

    with open(output_file, 'w') as f:
        for id_ in failed_ids:
            f.write(f"{id_}\n")

    print(f"[OK] Saved {len(failed_ids)} failed ID(s)")


def print_mapping_summary(mapping, from_db, to_db):
    """Print summary of mapping results."""
    print(f"\n{'='*70}")
    print("MAPPING SUMMARY")
    print(f"{'='*70}")

    total = len(mapping)
    mapped = len([v for v in mapping.values() if v])
    failed = total - mapped

    print(f"\nSource database: {from_db}")
    print(f"Target database: {to_db}")
    print(f"\nTotal identifiers: {total}")
    print(f"Successfully mapped: {mapped} ({mapped/total*100 if total else 0:.1f}%)")
    print(f"Failed to map: {failed} ({failed/total*100 if total else 0:.1f}%)")

    # Show some examples
    if mapped > 0:
        print(f"\nExample mappings (first 5):")
        count = 0
        for source_id, target_ids in mapping.items():
            if target_ids:
                target_str = ", ".join(target_ids[:3])
                if len(target_ids) > 3:
                    target_str += f" ... +{len(target_ids)-3} more"
                print(f"  {source_id} -> {target_str}")
                count += 1
                if count >= 5:
                    break

    # Show multiple mapping statistics
    multiple_mappings = [v for v in mapping.values() if v and len(v) > 1]
    if multiple_mappings:
        print(f"\nMultiple target mappings: {len(multiple_mappings)} ID(s)")
        print(f"  (These source IDs map to multiple target IDs)")

    print(f"{'='*70}")


def list_common_databases():
    """Print list of common database codes."""
    print("\nCommon Database Codes:")
    print("-" * 70)
    print(f"{'Alias':<20} {'Official Code':<30}")
    print("-" * 70)

    for alias, code in sorted(DATABASE_CODES.items()):
        if alias != code.lower():
            print(f"{alias:<20} {code:<30}")

    print("-" * 70)
    print("\nNote: Many other database codes are supported.")
    print("See UniProt documentation for complete list.")


def main():
    """Main conversion workflow."""
    parser = argparse.ArgumentParser(
        description="Batch convert biological identifiers between databases",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python batch_id_converter.py uniprot_ids.txt --from UniProtKB_AC-ID --to KEGG
  python batch_id_converter.py ids.txt --from GeneID --to UniProtKB -o mapping.csv
  python batch_id_converter.py ids.txt --from uniprot --to ensembl --chunk-size 50

Common database codes:
  UniProtKB_AC-ID, KEGG, GeneID, Ensembl, Ensembl_Protein,
  RefSeq_Protein, PDB, HGNC, Reactome

Use --list-databases to see all supported aliases.
        """
    )
    parser.add_argument("input_file", nargs="?", help="Input file with IDs (one per line)")
    parser.add_argument("--from", dest="from_db",
                       help="Source database code")
    parser.add_argument("--to", dest="to_db",
                       help="Target database code")
    parser.add_argument("-o", "--output", default=None,
                       help="Output CSV file (default: mapping_results.csv)")
    parser.add_argument("--chunk-size", type=int, default=100,
                       help="Number of IDs per batch (default: 100)")
    parser.add_argument("--delay", type=float, default=0.5,
                       help="Delay between batches in seconds (default: 0.5)")
    parser.add_argument("--save-failed", action="store_true",
                       help="Save failed IDs to separate file")
    parser.add_argument("--list-databases", action="store_true",
                       help="List common database codes and exit")

    args = parser.parse_args()

    # List databases and exit
    if args.list_databases:
        list_common_databases()
        sys.exit(0)

    if not args.input_file or not args.from_db or not args.to_db:
        parser.error("input_file, --from and --to are required unless --list-databases is used")
    if not 1 <= args.chunk_size <= 100000 or args.delay < 0:
        parser.error("--chunk-size must be 1..100000 and --delay nonnegative")

    print("=" * 70)
    print("BIOSERVICES: Batch Identifier Converter")
    print("=" * 70)

    # Normalize database codes
    from_db = normalize_database_code(args.from_db)
    to_db = normalize_database_code(args.to_db, target=True)

    if from_db != args.from_db:
        print(f"\nNote: Normalized '{args.from_db}' -> '{from_db}'")
    if to_db != args.to_db:
        print(f"Note: Normalized '{args.to_db}' -> '{to_db}'")

    # Read input IDs
    try:
        ids = read_ids_from_file(args.input_file)
    except Exception as e:
        print(f"\n[FAIL] Error reading input file: {e}")
        sys.exit(1)

    if not ids:
        print("\n[FAIL] No IDs found in input file")
        sys.exit(1)

    # Perform conversion
    mapping, failed_ids = batch_convert(
        ids,
        from_db,
        to_db,
        chunk_size=args.chunk_size,
        delay=args.delay
    )

    # Print summary
    print_mapping_summary(mapping, from_db, to_db)

    # Save results
    output_file = args.output or "mapping_results.csv"
    save_mapping_csv(mapping, output_file, from_db, to_db)

    # Save failed IDs if requested
    if args.save_failed and failed_ids:
        failed_file = str(Path(output_file).with_name(Path(output_file).stem + "_failed.txt"))
        save_failed_ids(failed_ids, failed_file)

    print(f"\n[OK] Done!")


if __name__ == "__main__":
    main()
