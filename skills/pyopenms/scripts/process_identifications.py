#!/usr/bin/env python3
"""
Process Peptide/Protein Identifications

Post-process search-engine results (idXML): optionally re-index peptides against
a protein FASTA (assigns target/decoy + protein accessions), estimate FDR/q-values,
filter by FDR threshold, peptide length, and best-hit-per-spectrum, then export a
filtered idXML and a flat CSV of peptide hits.

Usage:
    python process_identifications.py search.idXML --out filtered.idXML --csv hits.csv
    python process_identifications.py search.idXML --fasta db.fasta --fdr 0.01 --out filt.idXML
    python process_identifications.py search.idXML --fdr 0.05 --min-length 7 --best-per-spectrum
"""

import argparse
import os
import math
import sys

try:
    import pyopenms as ms
except ImportError:
    print("Error: pyopenms not installed. Install with: uv pip install pyopenms")
    sys.exit(1)


def index_peptides(fasta, prot_ids, pep_ids, decoy_string="DECOY_"):
    fasta_entries = []
    ms.FASTAFile().load(fasta, fasta_entries)
    indexer = ms.PeptideIndexing()
    p = indexer.getParameters()
    p.setValue("decoy_string", decoy_string)
    p.setValue("missing_decoy_action", "error")
    indexer.setParameters(p)
    result = indexer.run(fasta_entries, prot_ids, pep_ids)
    if result[0] != ms.PeptideIndexing.ExitCodes.EXECUTION_OK:
        raise ValueError(f"Peptide indexing failed: {result[0]}")
    print(f"Indexed against {len(fasta_entries)} proteins")



def filter_psm_qvalues(pep_ids, threshold):
    """Target-decoy q-values for comparable top-hit PSMs from one search run."""
    if not math.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("q-value threshold must be finite and between 0 and 1")
    contexts = set()
    labels = set()
    for pid in pep_ids:
        hits = pid.getHits()
        if not hits:
            continue
        if not pid.getScoreType() or pid.getScoreType().lower() in {"q-value", "fdr"}:
            raise ValueError("FDR estimation needs original search scores, not existing q-values/FDR")
        contexts.add((pid.getIdentifier(), pid.getScoreType(), pid.isHigherScoreBetter()))
        for hit in hits:
            if not math.isfinite(hit.getScore()) or not hit.metaValueExists("target_decoy"):
                raise ValueError("Every hit needs a finite score and target_decoy annotation")
            if hit.getMetaValue("target_decoy") not in {"target", "decoy", "target+decoy"}:
                raise ValueError("Invalid target_decoy annotation")
        best = max(hits, key=lambda h: h.getScore()) if pid.isHigherScoreBetter() else min(hits, key=lambda h: h.getScore())
        labels.add(best.getMetaValue("target_decoy"))
    if len(contexts) != 1:
        raise ValueError("Process one search run with one score type/direction at a time")
    if "decoy" not in labels or not labels.intersection({"target", "target+decoy"}):
        raise ValueError("FDR estimation requires both target and decoy top-scoring PSMs")
    fdr = ms.FalseDiscoveryRate()
    p = fdr.getParameters()
    p.setValue("no_qvalues", "false")
    p.setValue("use_all_hits", "false")
    p.setValue("add_decoy_peptides", "false")
    fdr.setParameters(p)
    fdr.apply(pep_ids)
    ms.IDFilter().filterHitsByScore(pep_ids, threshold)


def main():
    parser = argparse.ArgumentParser(description="Filter and export peptide identifications.")
    parser.add_argument("input", help="Input idXML")
    parser.add_argument("--decoy-prefix", default="DECOY_", help="FASTA decoy accession prefix for re-indexing")
    parser.add_argument("--fasta", help="Protein FASTA (target+decoy) for re-indexing")
    parser.add_argument("--out", help="Output filtered idXML")
    parser.add_argument("--csv", help="Output CSV of peptide hits")
    parser.add_argument("--fdr", type=float, help="FDR/q-value threshold (requires decoys)")
    parser.add_argument("--min-length", type=int, help="Minimum peptide length")
    parser.add_argument("--max-length", type=int, help="Maximum peptide length")
    parser.add_argument("--best-per-spectrum", action="store_true",
                        help="Keep only the best hit per spectrum")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: file not found: {args.input}")
        sys.exit(1)

    # In pyOpenMS 3.5+, idXML load/store require a PeptideIdentificationList
    # (not a plain Python list) for the peptide IDs; protein IDs stay a list.
    prot_ids = []
    pep_ids = ms.PeptideIdentificationList()
    ms.IdXMLFile().load(args.input, prot_ids, pep_ids)
    print(f"Loaded {len(pep_ids)} spectra, "
          f"{sum(len(p.getHits()) for p in pep_ids)} peptide hits")

    if args.fasta:
        index_peptides(args.fasta, prot_ids, pep_ids, args.decoy_prefix)

    if args.fdr is not None:
        filter_psm_qvalues(pep_ids, args.fdr)
        print(f"Applied FDR filter (q <= {args.fdr})")

    if args.best_per_spectrum:
        ms.IDFilter().keepBestPeptideHits(pep_ids, False)
        print("Kept best hit per spectrum")

    if args.min_length is not None or args.max_length is not None:
        lo = args.min_length or 0
        hi = args.max_length or 0  # 0 = no upper bound in OpenMS
        ms.IDFilter().filterPeptidesByLength(pep_ids, lo, hi)
        print(f"Length filter ({lo}-{hi or 'inf'})")

    # Drop now-empty identifications
    ms.IDFilter().removeEmptyIdentifications(pep_ids)
    remaining = sum(len(p.getHits()) for p in pep_ids)
    print(f"Remaining: {len(pep_ids)} spectra, {remaining} peptide hits")

    if args.out:
        ms.IdXMLFile().store(args.out, prot_ids, pep_ids)
        print(f"Wrote {args.out}")

    if args.csv:
        import csv
        with open(args.csv, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["rt", "mz", "sequence", "charge", "score", "score_type",
                        "target_decoy", "accessions"])
            for pid in pep_ids:
                rt = pid.getRT()
                mz = pid.getMZ()
                st = pid.getScoreType()
                for hit in pid.getHits():
                    td = hit.getMetaValue("target_decoy") if hit.metaValueExists("target_decoy") else ""
                    accs = ";".join(a.decode() if isinstance(a, bytes) else a for a in hit.extractProteinAccessionsSet())
                    w.writerow([f"{rt:.2f}", f"{mz:.4f}", hit.getSequence().toString(),
                                hit.getCharge(), hit.getScore(), st, td, accs])
        print(f"Wrote {args.csv}")


if __name__ == "__main__":
    main()
