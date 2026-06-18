#!/usr/bin/env python3
"""
Extract Ion Chromatograms (XIC/EIC) and TIC/BPC

Build chromatograms from MS1 data: total ion chromatogram (TIC), base peak
chromatogram (BPC), and extracted ion chromatograms (XIC) for target m/z values
within a ppm tolerance. Writes a tidy CSV (rt, trace, intensity) and optionally
a PNG plot.

Usage:
    python extract_chromatograms.py data.mzML --tic --bpc --out chrom.csv
    python extract_chromatograms.py data.mzML --mz 300.15 450.22 --ppm 10 --out xic.csv --plot xic.png
"""

import argparse
import os
import sys

try:
    import pyopenms as ms
    import numpy as np
except ImportError:
    print("Error: pyopenms/numpy not installed. Install with: uv pip install pyopenms")
    sys.exit(1)


def collect_ms1(exp):
    rts, mz_arrays, int_arrays = [], [], []
    for spec in exp:
        if spec.getMSLevel() != 1:
            continue
        mz, inten = spec.get_peaks()
        rts.append(spec.getRT())
        mz_arrays.append(mz)
        int_arrays.append(inten)
    return rts, mz_arrays, int_arrays


def main():
    parser = argparse.ArgumentParser(description="Extract TIC/BPC/XIC chromatograms.")
    parser.add_argument("input", help="Input mzML/mzXML")
    parser.add_argument("--tic", action="store_true", help="Compute total ion chromatogram")
    parser.add_argument("--bpc", action="store_true", help="Compute base peak chromatogram")
    parser.add_argument("--mz", type=float, nargs="+", help="Target m/z values for XIC")
    parser.add_argument("--ppm", type=float, default=10.0, help="XIC m/z tolerance in ppm (default 10)")
    parser.add_argument("--out", help="Output CSV (tidy: rt, trace, intensity)")
    parser.add_argument("--plot", help="Output PNG plot")
    args = parser.parse_args()

    if not (args.tic or args.bpc or args.mz):
        parser.error("request at least one of --tic, --bpc, or --mz")
    if not os.path.exists(args.input):
        print(f"Error: file not found: {args.input}")
        sys.exit(1)

    exp = ms.MSExperiment()
    ms.FileHandler().loadExperiment(args.input, exp)
    rts, mz_arrays, int_arrays = collect_ms1(exp)
    rts = np.array(rts)
    print(f"Collected {len(rts)} MS1 scans")

    traces = {}
    if args.tic:
        traces["TIC"] = np.array([a.sum() if len(a) else 0.0 for a in int_arrays])
    if args.bpc:
        traces["BPC"] = np.array([a.max() if len(a) else 0.0 for a in int_arrays])
    if args.mz:
        for target in args.mz:
            tol = target * args.ppm / 1e6
            trace = np.empty(len(rts))
            for i, (mz, inten) in enumerate(zip(mz_arrays, int_arrays)):
                mask = np.abs(mz - target) <= tol
                trace[i] = inten[mask].sum() if mask.any() else 0.0
            traces[f"XIC_{target:.4f}"] = trace
            apex = trace.argmax() if len(trace) else 0
            print(f"  XIC m/z {target:.4f}: apex RT {rts[apex]:.1f}s, max {trace[apex]:.3e}")

    if args.out:
        import csv
        with open(args.out, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["rt", "trace", "intensity"])
            for name, trace in traces.items():
                for rt, val in zip(rts, trace):
                    w.writerow([f"{rt:.3f}", name, f"{val:.4f}"])
        print(f"Wrote {args.out}")

    if args.plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        plt.figure(figsize=(10, 5))
        for name, trace in traces.items():
            plt.plot(rts, trace, label=name, linewidth=1)
        plt.xlabel("Retention time (s)")
        plt.ylabel("Intensity")
        plt.legend()
        plt.title("Chromatograms")
        plt.tight_layout()
        plt.savefig(args.plot, dpi=150)
        print(f"Wrote {args.plot}")


if __name__ == "__main__":
    main()
