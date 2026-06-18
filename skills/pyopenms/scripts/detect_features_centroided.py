#!/usr/bin/env python3
"""
Peptide/Centroided Feature Detection

Detect features in centroided (peak-picked) LC-MS data using
FeatureFinderAlgorithmPicked -- the modern replacement for the removed
FeatureFinderCentroided. Suited to peptide/proteomics data with defined
isotope patterns and charge states.

Outputs a featureXML and optionally a CSV table.

Usage:
    python detect_features_centroided.py centroided.mzML
    python detect_features_centroided.py data.mzML --out-csv feats.csv --charge-low 2 --charge-high 5
"""

import argparse
import os
import sys

try:
    import pyopenms as ms
except ImportError:
    print("Error: pyopenms not installed. Install with: uv pip install pyopenms")
    sys.exit(1)


def detect_features(exp, mz_tol_ppm=10.0, charge_low=1, charge_high=4, min_spectra=7):
    exp.sortSpectra(True)
    exp.updateRanges()
    ff = ms.FeatureFinderAlgorithmPicked()
    params = ff.getDefaults()
    params.setValue("mass_trace:mz_tolerance", mz_tol_ppm / 1e6 * 400.0)  # approx Da at m/z 400
    params.setValue("mass_trace:min_spectra", int(min_spectra))
    params.setValue("isotopic_pattern:charge_low", int(charge_low))
    params.setValue("isotopic_pattern:charge_high", int(charge_high))
    ff.setParameters(params)

    features = ms.FeatureMap()
    seeds = ms.FeatureMap()
    ff.run(exp, features, params, seeds)
    features.setUniqueIds()
    return features


def main():
    parser = argparse.ArgumentParser(description="Centroided/peptide feature detection.")
    parser.add_argument("input", help="Centroided mzML file")
    parser.add_argument("--out-features", help="Output featureXML (default: <input>.featureXML)")
    parser.add_argument("--out-csv", help="Optional CSV table of features")
    parser.add_argument("--mz-tol-ppm", type=float, default=10.0, help="m/z tolerance in ppm (default 10)")
    parser.add_argument("--charge-low", type=int, default=1, help="Lower charge bound (default 1)")
    parser.add_argument("--charge-high", type=int, default=4, help="Upper charge bound (default 4)")
    parser.add_argument("--min-spectra", type=int, default=7, help="Min scans per feature (default 7)")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: file not found: {args.input}")
        sys.exit(1)

    exp = ms.MSExperiment()
    ms.FileHandler().loadExperiment(args.input, exp)
    print(f"Loaded {exp.getNrSpectra()} spectra from {args.input}")

    fm = detect_features(exp, mz_tol_ppm=args.mz_tol_ppm, charge_low=args.charge_low,
                         charge_high=args.charge_high, min_spectra=args.min_spectra)
    print(f"Features detected: {fm.size()}")

    out_features = args.out_features or os.path.splitext(args.input)[0] + ".featureXML"
    ms.FeatureXMLFile().store(out_features, fm)
    print(f"Wrote {out_features}")

    if args.out_csv:
        df = fm.get_df()
        df.to_csv(args.out_csv, index=False)
        print(f"Wrote {args.out_csv} ({len(df)} rows)")


if __name__ == "__main__":
    main()
