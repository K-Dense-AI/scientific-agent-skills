#!/usr/bin/env python3
"""
Inspect Mass Spectrometry Data

Load any supported MS file (mzML, mzXML, featureXML, consensusXML, idXML) and
print a structured summary: spectrum counts by MS level, RT/m/z ranges, TIC,
chromatograms, precursor info, and instrument metadata. Optionally dump a
per-spectrum table to CSV.

Usage:
    python inspect_ms_data.py data.mzML
    python inspect_ms_data.py data.mzML --spectra-csv spectra.csv
    python inspect_ms_data.py features.featureXML
    python inspect_ms_data.py ids.idXML
"""

import argparse
import os
import sys

try:
    import pyopenms as ms
except ImportError:
    print("Error: pyopenms not installed. Install with: uv pip install pyopenms")
    sys.exit(1)


def summarize_experiment(path):
    exp = ms.MSExperiment()
    ms.FileHandler().loadExperiment(path, exp)

    n_spec = exp.getNrSpectra()
    n_chrom = exp.getNrChromatograms()
    print(f"File: {path}")
    print(f"Spectra: {n_spec}")
    print(f"Chromatograms: {n_chrom}")

    if n_spec:
        levels = {}
        rts, total_tic, total_peaks = [], 0.0, 0
        mz_min, mz_max = float("inf"), float("-inf")
        n_precursors = 0
        for spec in exp:
            lvl = spec.getMSLevel()
            levels[lvl] = levels.get(lvl, 0) + 1
            rts.append(spec.getRT())
            mz, inten = spec.get_peaks()
            total_peaks += len(mz)
            if len(mz):
                total_tic += float(inten.sum())
                mz_min = min(mz_min, float(mz.min()))
                mz_max = max(mz_max, float(mz.max()))
            if spec.getPrecursors():
                n_precursors += 1
        print("\nSpectra by MS level:")
        for lvl in sorted(levels):
            print(f"  MS{lvl}: {levels[lvl]}")
        if rts:
            print(f"\nRT range: {min(rts):.1f} - {max(rts):.1f} s "
                  f"({min(rts)/60:.2f} - {max(rts)/60:.2f} min)")
        if mz_min != float("inf"):
            print(f"m/z range: {mz_min:.4f} - {mz_max:.4f}")
        print(f"Total peaks: {total_peaks}")
        print(f"Total ion current (sum): {total_tic:.3e}")
        print(f"Spectra with precursors (MSn): {n_precursors}")

    # Instrument / metadata
    instr = exp.getInstrument()
    if instr.getName():
        print(f"\nInstrument: {instr.getName()}")
    if instr.getVendor():
        print(f"Vendor: {instr.getVendor()}")
    return exp


def dump_spectra_csv(exp, out_csv):
    import csv
    with open(out_csv, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["index", "ms_level", "rt", "n_peaks", "tic",
                    "base_peak_mz", "base_peak_int", "precursor_mz", "precursor_charge"])
        for i, spec in enumerate(exp):
            mz, inten = spec.get_peaks()
            tic = float(inten.sum()) if len(inten) else 0.0
            bp_mz, bp_int = ("", "")
            if len(inten):
                j = int(inten.argmax())
                bp_mz, bp_int = f"{mz[j]:.4f}", f"{inten[j]:.1f}"
            prec_mz, prec_z = ("", "")
            if spec.getPrecursors():
                p = spec.getPrecursors()[0]
                prec_mz, prec_z = f"{p.getMZ():.4f}", p.getCharge()
            w.writerow([i, spec.getMSLevel(), f"{spec.getRT():.3f}", len(mz),
                        f"{tic:.1f}", bp_mz, bp_int, prec_mz, prec_z])
    print(f"\nWrote per-spectrum table: {out_csv}")


def summarize_feature_map(path):
    fm = ms.FeatureMap()
    ms.FeatureXMLFile().load(path, fm)
    print(f"File: {path}")
    print(f"Features: {fm.size()}")
    if fm.size():
        df = fm.get_df()
        print(f"\nColumns: {list(df.columns)}")
        print(f"RT range: {df['rt'].min():.1f} - {df['rt'].max():.1f} s")
        print(f"m/z range: {df['mz'].min():.4f} - {df['mz'].max():.4f}")
        print(f"Intensity: median={df['intensity'].median():.3e} max={df['intensity'].max():.3e}")
        if "charge" in df:
            print(f"Charge states: {sorted(df['charge'].unique().tolist())}")


def summarize_consensus_map(path):
    cm = ms.ConsensusMap()
    ms.ConsensusXMLFile().load(path, cm)
    print(f"File: {path}")
    print(f"Consensus features: {cm.size()}")
    headers = cm.getColumnHeaders()
    print(f"Samples/maps: {len(headers)}")
    for idx, h in headers.items():
        print(f"  map {idx}: {h.filename} (size={h.size}, label={h.label})")


def summarize_idxml(path):
    prot_ids = []
    pep_ids = ms.PeptideIdentificationList()  # required type in pyOpenMS 3.5+
    ms.IdXMLFile().load(path, prot_ids, pep_ids)
    print(f"File: {path}")
    print(f"Protein ID runs: {len(prot_ids)}")
    total_prot = sum(len(p.getHits()) for p in prot_ids)
    print(f"Protein hits: {total_prot}")
    print(f"Peptide identifications (spectra): {len(pep_ids)}")
    total_pep = sum(len(p.getHits()) for p in pep_ids)
    print(f"Peptide hits: {total_pep}")
    if pep_ids:
        scored = [p for p in pep_ids if p.getHits()]
        if scored:
            st = scored[0].getScoreType()
            print(f"Score type: {st}")
            print(f"Higher score better: {scored[0].isHigherScoreBetter()}")


def main():
    parser = argparse.ArgumentParser(description="Inspect a mass spectrometry data file.")
    parser.add_argument("input", help="Input file (mzML, mzXML, featureXML, consensusXML, idXML)")
    parser.add_argument("--spectra-csv", help="Write a per-spectrum summary table to this CSV path")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: file not found: {args.input}")
        sys.exit(1)

    ext = args.input.lower()
    if ext.endswith(".featurexml"):
        summarize_feature_map(args.input)
    elif ext.endswith(".consensusxml"):
        summarize_consensus_map(args.input)
    elif ext.endswith(".idxml"):
        summarize_idxml(args.input)
    else:
        exp = summarize_experiment(args.input)
        if args.spectra_csv:
            dump_spectra_csv(exp, args.spectra_csv)


if __name__ == "__main__":
    main()
