#!/usr/bin/env python3
"""
Consensus Map to Quantification Matrix

Convert a consensusXML into analysis-ready tables: a wide intensity matrix
(consensus features x samples) joined with feature metadata (RT, m/z, charge,
quality), plus an optional long/tidy format. Optionally normalize intensities
across samples (median or quantile).

Usage:
    python consensus_to_matrix.py study.consensusXML --out quant.csv
    python consensus_to_matrix.py study.consensusXML --out quant.csv --normalize median
    python consensus_to_matrix.py study.consensusXML --out quant.csv --long long.csv
"""

import argparse
import os
import sys

try:
    import pyopenms as ms
except ImportError:
    print("Error: pyopenms not installed. Install with: uv pip install pyopenms")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Export a consensusXML to a quant matrix CSV.")
    parser.add_argument("input", help="Input consensusXML")
    parser.add_argument("--out", required=True, help="Output wide-matrix CSV")
    parser.add_argument("--long", help="Also write a tidy/long-format CSV")
    parser.add_argument("--normalize", choices=["median", "quantile", "none"], default="none",
                        help="Cross-sample intensity normalization (default none)")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: file not found: {args.input}")
        sys.exit(1)

    cm = ms.ConsensusMap()
    ms.ConsensusXMLFile().load(args.input, cm)
    print(f"Loaded {cm.size()} consensus features, {len(cm.getColumnHeaders())} samples")

    if args.normalize == "median":
        ms.ConsensusMapNormalizerAlgorithmMedian().normalizeMaps(
            cm, ms.NormalizationMethod.NM_SCALE, "", "")
        print("Applied median normalization")
    elif args.normalize == "quantile":
        ms.ConsensusMapNormalizerAlgorithmQuantile().normalizeMaps(cm)
        print("Applied quantile normalization")

    import pandas as pd
    # Ensure unique row identity; consensus ids may be 0/duplicated on some maps.
    cm.setUniqueIds()
    intensity_df = cm.get_intensity_df().reset_index(drop=True)
    meta_df = cm.get_metadata_df().reset_index(drop=True)
    matrix = pd.concat([meta_df, intensity_df], axis=1)
    matrix.to_csv(args.out, index_label="consensus_id")
    print(f"Wrote {args.out} ({matrix.shape[0]} features x {intensity_df.shape[1]} samples)")

    if args.long:
        long_df = intensity_df.copy()
        long_df.insert(0, "consensus_id", range(len(long_df)))
        long_df = long_df.melt(id_vars="consensus_id", var_name="sample", value_name="intensity")
        long_df.to_csv(args.long, index=False)
        print(f"Wrote {args.long} ({len(long_df)} rows)")


if __name__ == "__main__":
    main()
