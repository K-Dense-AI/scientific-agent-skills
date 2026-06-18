#!/usr/bin/env python3
"""
Multi-Sample Align, Link, and Quantify

End-to-end untargeted quantification across multiple LC-MS samples:

    1. Detect features in each mzML (FeatureFindingMetabo)   [or load .featureXML]
    2. Align retention times (MapAlignmentAlgorithmPoseClustering)
    3. Link features into a consensus map (FeatureGroupingAlgorithmQT)
    4. Export consensusXML + a wide quantification matrix (CSV)

Accepts either mzML files (features detected here) or pre-computed .featureXML files.

Usage:
    python align_link_quantify.py s1.mzML s2.mzML s3.mzML --out-prefix study
    python align_link_quantify.py *.featureXML --out-prefix study --rt-tol 20 --mz-tol 10
"""

import argparse
import os
import sys

try:
    import pyopenms as ms
except ImportError:
    print("Error: pyopenms not installed. Install with: uv pip install pyopenms")
    sys.exit(1)

# Reuse the metabolomics detector if available alongside this script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from detect_features_metabo import detect_features
except Exception:
    detect_features = None


def load_or_detect(path, ppm, noise):
    if path.lower().endswith(".featurexml"):
        fm = ms.FeatureMap()
        ms.FeatureXMLFile().load(path, fm)
        return fm
    exp = ms.MSExperiment()
    ms.FileHandler().loadExperiment(path, exp)
    if detect_features is None:
        raise RuntimeError("detect_features_metabo.py not importable; pass .featureXML inputs instead.")
    fm, _ = detect_features(exp, ppm=ppm, noise=noise)
    return fm


def align(feature_maps):
    """Align all maps to the one with the most features (in place)."""
    ref_idx = max(range(len(feature_maps)), key=lambda i: feature_maps[i].size())
    aligner = ms.MapAlignmentAlgorithmPoseClustering()
    aligner.setReference(feature_maps[ref_idx])
    transformer = ms.MapAlignmentTransformer()
    for i, fm in enumerate(feature_maps):
        if i == ref_idx:
            continue
        trafo = ms.TransformationDescription()
        try:
            aligner.align(fm, trafo)
            transformer.transformRetentionTimes(fm, trafo, True)
        except Exception as e:
            print(f"  warning: alignment failed for map {i}: {e}")
    return ref_idx


def link(feature_maps, filenames, rt_tol, mz_tol, mz_unit):
    grouper = ms.FeatureGroupingAlgorithmQT()
    p = grouper.getParameters()
    p.setValue("distance_RT:max_difference", float(rt_tol))
    p.setValue("distance_MZ:max_difference", float(mz_tol))
    p.setValue("distance_MZ:unit", mz_unit)
    grouper.setParameters(p)

    consensus = ms.ConsensusMap()
    headers = consensus.getColumnHeaders()
    for i, fm in enumerate(feature_maps):
        h = ms.ColumnHeader()
        h.filename = filenames[i]
        h.size = fm.size()
        h.unique_id = fm.getUniqueId()
        headers[i] = h
    consensus.setColumnHeaders(headers)
    grouper.group(feature_maps, consensus)
    consensus.setUniqueIds()
    return consensus


def main():
    parser = argparse.ArgumentParser(description="Align, link, and quantify across samples.")
    parser.add_argument("inputs", nargs="+", help="mzML and/or featureXML files (2+)")
    parser.add_argument("--out-prefix", default="consensus", help="Output file prefix")
    parser.add_argument("--rt-tol", type=float, default=20.0, help="Max RT difference for linking (s)")
    parser.add_argument("--mz-tol", type=float, default=10.0, help="Max m/z difference for linking")
    parser.add_argument("--mz-unit", choices=["ppm", "Da"], default="ppm", help="m/z unit (default ppm)")
    parser.add_argument("--ppm", type=float, default=10.0, help="ppm for feature detection (mzML inputs)")
    parser.add_argument("--noise", type=float, default=1000.0, help="Noise threshold for detection")
    args = parser.parse_args()

    if len(args.inputs) < 2:
        print("Error: provide at least 2 input files.")
        sys.exit(1)

    feature_maps = []
    for path in args.inputs:
        if not os.path.exists(path):
            print(f"Error: file not found: {path}")
            sys.exit(1)
        print(f"Processing {path}...")
        fm = load_or_detect(path, args.ppm, args.noise)
        fm.setUniqueIds()
        print(f"  {fm.size()} features")
        feature_maps.append(fm)

    print("Aligning retention times...")
    ref_idx = align(feature_maps)
    print(f"  reference map: {args.inputs[ref_idx]}")

    print("Linking features...")
    consensus = link(feature_maps, args.inputs, args.rt_tol, args.mz_tol, args.mz_unit)
    print(f"  {consensus.size()} consensus features")

    out_cxml = f"{args.out_prefix}.consensusXML"
    ms.ConsensusXMLFile().store(out_cxml, consensus)
    print(f"Wrote {out_cxml}")

    # Quantification matrix: rows = consensus features, columns = samples.
    # Concatenate positionally (index may be non-unique on degenerate maps).
    import pandas as pd
    intensity_df = consensus.get_intensity_df().reset_index(drop=True)
    meta_df = consensus.get_metadata_df().reset_index(drop=True)
    matrix = pd.concat([meta_df, intensity_df], axis=1)
    out_csv = f"{args.out_prefix}_quant_matrix.csv"
    matrix.to_csv(out_csv, index_label="consensus_id")
    print(f"Wrote {out_csv} ({matrix.shape[0]} features x {intensity_df.shape[1]} samples)")


if __name__ == "__main__":
    main()
