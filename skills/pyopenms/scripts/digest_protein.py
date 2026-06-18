#!/usr/bin/env python3
"""
In-Silico Protein Digestion

Digest protein sequences (FASTA or a single sequence) with a configurable
protease, producing theoretical peptides with masses and m/z. Useful for
targeted method design and search-space estimation.

Usage:
    python digest_protein.py proteins.fasta --out peptides.csv
    python digest_protein.py --sequence MKWVTFISLLLLFSSAYS --enzyme Trypsin --missed 2
    python digest_protein.py proteins.fasta --min-length 7 --max-length 40 --charges 1 2 3
"""

import argparse
import os
import sys

try:
    import pyopenms as ms
except ImportError:
    print("Error: pyopenms not installed. Install with: uv pip install pyopenms")
    sys.exit(1)

PROTON = 1.0072764665789


def read_fasta(path):
    entries = []
    fe = ms.FASTAFile()
    seqs = []
    fe.load(path, seqs)
    for s in seqs:
        entries.append((s.identifier, s.sequence))
    return entries


def digest(seq_str, enzyme, missed, min_len, max_len):
    dig = ms.ProteaseDigestion()
    dig.setEnzyme(enzyme)
    dig.setMissedCleavages(missed)
    out = []
    dig.digest(ms.AASequence.fromString(seq_str), out, min_len, max_len)
    return out


def main():
    parser = argparse.ArgumentParser(description="In-silico protein digestion.")
    parser.add_argument("fasta", nargs="?", help="FASTA file (optional if --sequence given)")
    parser.add_argument("--sequence", help="Single protein sequence")
    parser.add_argument("--enzyme", default="Trypsin", help="Protease (default Trypsin)")
    parser.add_argument("--missed", type=int, default=2, help="Max missed cleavages (default 2)")
    parser.add_argument("--min-length", type=int, default=6, help="Min peptide length (default 6)")
    parser.add_argument("--max-length", type=int, default=40, help="Max peptide length (default 40)")
    parser.add_argument("--charges", type=int, nargs="+", default=[1, 2], help="m/z charge states")
    parser.add_argument("--out", help="Output CSV of peptides")
    args = parser.parse_args()

    proteins = []
    if args.fasta:
        if not os.path.exists(args.fasta):
            print(f"Error: file not found: {args.fasta}")
            sys.exit(1)
        proteins = read_fasta(args.fasta)
    elif args.sequence:
        proteins = [("input", args.sequence)]
    else:
        parser.error("provide a FASTA file or --sequence")

    rows = []
    seen = set()
    for prot_id, seq in proteins:
        for pep in digest(seq, args.enzyme, args.missed, args.min_length, args.max_length):
            pep_str = pep.toString()
            key = (prot_id, pep_str)
            if key in seen:
                continue
            seen.add(key)
            mono = pep.getMonoWeight()
            row = {"protein": prot_id, "peptide": pep_str, "length": pep.size(),
                   "mono_mass": round(mono, 5)}
            for z in args.charges:
                row[f"mz_z{z}"] = round((mono + z * PROTON) / z, 5)
            rows.append(row)

    print(f"Proteins: {len(proteins)}  Unique peptides: {len(rows)}")
    for r in rows[:10]:
        print(f"  {r['peptide']}  ({r['length']} aa, {r['mono_mass']} Da)")
    if len(rows) > 10:
        print(f"  ... and {len(rows) - 10} more")

    if args.out:
        import csv
        with open(args.out, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["protein", "peptide"])
            w.writeheader()
            w.writerows(rows)
        print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
