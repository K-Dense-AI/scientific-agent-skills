#!/usr/bin/env python3
"""
Theoretical Fragment Spectrum Generator

Generate a theoretical fragment-ion spectrum (b/y, optionally a/c/x/z and
losses) for a peptide using TheoreticalSpectrumGenerator. Prints annotated
fragment ions and optionally writes the spectrum to mzML and/or a CSV peak list.

Usage:
    python theoretical_spectrum.py DFPIANGER
    python theoretical_spectrum.py PEPTIDEK --charge 2 --ions b y a --losses
    python theoretical_spectrum.py DFPIANGER --out-mzml theo.mzML --out-csv peaks.csv
"""

import argparse
import sys

try:
    import pyopenms as ms
except ImportError:
    print("Error: pyopenms not installed. Install with: uv pip install pyopenms")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Generate a theoretical peptide spectrum.")
    parser.add_argument("peptide", help="Amino-acid sequence (OpenMS mod syntax allowed)")
    parser.add_argument("--charge", type=int, default=1, help="Max fragment charge (default 1)")
    parser.add_argument("--ions", nargs="+", default=["b", "y"],
                        choices=["a", "b", "c", "x", "y", "z"], help="Ion series (default b y)")
    parser.add_argument("--losses", action="store_true", help="Include neutral losses")
    parser.add_argument("--precursor", action="store_true", help="Include precursor peaks")
    parser.add_argument("--out-mzml", help="Write spectrum to mzML")
    parser.add_argument("--out-csv", help="Write annotated peak list to CSV")
    args = parser.parse_args()

    seq = ms.AASequence.fromString(args.peptide)
    tsg = ms.TheoreticalSpectrumGenerator()
    p = tsg.getParameters()
    for ion in ["a", "b", "c", "x", "y", "z"]:
        p.setValue(f"add_{ion}_ions", "true" if ion in args.ions else "false")
    p.setValue("add_losses", "true" if args.losses else "false")
    p.setValue("add_precursor_peaks", "true" if args.precursor else "false")
    p.setValue("add_metainfo", "true")
    tsg.setParameters(p)

    spec = ms.MSSpectrum()
    tsg.getSpectrum(spec, seq, 1, args.charge)
    print(f"Peptide: {seq.toString()}  ({len(spec)} fragment peaks)")

    mz, inten = spec.get_peaks()
    names = [spec.getStringDataArrays()[0][i].decode() if spec.getStringDataArrays() else ""
             for i in range(len(mz))]
    rows = sorted(zip(mz, inten, names), key=lambda r: r[0])
    for m, _, name in rows:
        print(f"  {name:12s} m/z {m:.4f}")

    if args.out_mzml:
        exp = ms.MSExperiment()
        exp.addSpectrum(spec)
        ms.MzMLFile().store(args.out_mzml, exp)
        print(f"Wrote {args.out_mzml}")

    if args.out_csv:
        import csv
        with open(args.out_csv, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["ion", "mz", "intensity"])
            for m, it, name in rows:
                w.writerow([name, f"{m:.5f}", f"{it:.3f}"])
        print(f"Wrote {args.out_csv}")


if __name__ == "__main__":
    main()
