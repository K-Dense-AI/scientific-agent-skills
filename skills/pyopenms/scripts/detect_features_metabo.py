#!/usr/bin/env python3
"""
Untargeted Metabolomics Feature Detection

Run the standard OpenMS small-molecule feature-finding pipeline on centroided
LC-MS data:

    MassTraceDetection -> ElutionPeakDetection -> FeatureFindingMetabo

Outputs a featureXML and (optionally) a CSV table of detected features.
This is the recommended entry point for untargeted metabolomics preprocessing.

Usage:
    python detect_features_metabo.py sample.mzML
    python detect_features_metabo.py sample.mzML --out-features feats.featureXML --out-csv feats.csv
    python detect_features_metabo.py sample.mzML --ppm 5 --noise 5000 --charge-low 1 --charge-high 3
"""

import argparse
import os
import sys

try:
    import pyopenms as ms
except ImportError:
    print("Error: pyopenms not installed. Install with: uv pip install pyopenms")
    sys.exit(1)


def detect_features(exp, ppm=10.0, noise=1000.0, charge_low=1, charge_high=3,
                    remove_single=True, iso_model="metabolites (5% RMS)"):
    """Run MTD -> EPD -> FFM. Returns a FeatureMap."""
    exp.sortSpectra(True)

    # 1. Mass trace detection
    mtd = ms.MassTraceDetection()
    p = mtd.getDefaults()
    p.setValue("mass_error_ppm", float(ppm))
    p.setValue("noise_threshold_int", float(noise))
    mtd.setParameters(p)
    mass_traces = []
    mtd.run(exp, mass_traces, 0)

    # 2. Elution peak detection
    epd = ms.ElutionPeakDetection()
    p = epd.getDefaults()
    p.setValue("width_filtering", "fixed")
    epd.setParameters(p)
    mt_split = []
    epd.detectPeaks(mass_traces, mt_split)

    # 3. Feature assembly (isotope/charge resolution)
    ffm = ms.FeatureFindingMetabo()
    p = ffm.getDefaults()
    p.setValue("isotope_filtering_model", iso_model)
    p.setValue("remove_single_traces", "true" if remove_single else "false")
    p.setValue("charge_lower_bound", int(charge_low))
    p.setValue("charge_upper_bound", int(charge_high))
    p.setValue("report_convex_hulls", "true")
    ffm.setParameters(p)
    fm = ms.FeatureMap()
    chrom_out = []
    ffm.run(mt_split, fm, chrom_out)
    fm.setUniqueIds()
    return fm, len(mass_traces)


def main():
    parser = argparse.ArgumentParser(description="Untargeted metabolomics feature detection.")
    parser.add_argument("input", help="Centroided mzML file")
    parser.add_argument("--out-features", help="Output featureXML (default: <input>.featureXML)")
    parser.add_argument("--out-csv", help="Optional CSV table of features")
    parser.add_argument("--ppm", type=float, default=10.0, help="Mass trace m/z tolerance in ppm (default 10)")
    parser.add_argument("--noise", type=float, default=1000.0, help="Noise intensity threshold (default 1000)")
    parser.add_argument("--charge-low", type=int, default=1, help="Lower charge bound (default 1)")
    parser.add_argument("--charge-high", type=int, default=3, help="Upper charge bound (default 3)")
    parser.add_argument("--keep-singletons", action="store_true",
                        help="Keep single-trace features (default: remove)")
    parser.add_argument("--iso-model", default="metabolites (5% RMS)",
                        help="Isotope filtering model (e.g. 'none', 'metabolites (5%% RMS)')")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: file not found: {args.input}")
        sys.exit(1)

    exp = ms.MSExperiment()
    ms.FileHandler().loadExperiment(args.input, exp)
    print(f"Loaded {exp.getNrSpectra()} spectra from {args.input}")

    fm, n_traces = detect_features(
        exp, ppm=args.ppm, noise=args.noise,
        charge_low=args.charge_low, charge_high=args.charge_high,
        remove_single=not args.keep_singletons, iso_model=args.iso_model,
    )
    print(f"Mass traces: {n_traces}")
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
