#!/usr/bin/env python3
"""
Adduct Detection / Feature Decharging

Group features that are different ionization forms (adducts/charge variants) of
the same neutral compound using MetaboliteFeatureDeconvolution. Annotates each
feature with its inferred adduct and neutral mass, and writes the decharged
feature map plus a consensus map of grouped adduct families.

Adducts use OpenMS deconvolution syntax 'Elements:Charge:Probability', where
the charge is given as '+'/'-' signs (e.g. 'Ca:++:0.5' is +2) and losses are
written like 'H-2O-1'. Example: 'H:+:0.4'. This differs from the bracket
notation (e.g. [M+H]+) used elsewhere.

Usage:
    python detect_adducts.py features.featureXML --out-features decharged.featureXML
    python detect_adducts.py features.featureXML --negative
    python detect_adducts.py features.featureXML --adducts "H:+:0.6,Na:+:0.2,K:+:0.2"
"""

import argparse
import os
import sys

try:
    import pyopenms as ms
except ImportError:
    print("Error: pyopenms not installed. Install with: uv pip install pyopenms")
    sys.exit(1)

# 'Elements:Charge:Probability' (OpenMS deconvolution syntax)
DEFAULT_POS = "H:+:0.4,Na:+:0.25,NH4:+:0.25,K:+:0.1,H-2O-1:0:0.05"
DEFAULT_NEG = "H-1:-:0.6,Cl:-:0.2,H-3O-1:-:0.1,CH2O2H-1:-:0.1"


def main():
    parser = argparse.ArgumentParser(description="Detect adducts / decharge a feature map.")
    parser.add_argument("input", help="Input featureXML")
    parser.add_argument("--out-features", help="Output decharged featureXML (default: <input>_decharged.featureXML)")
    parser.add_argument("--out-consensus", help="Optional consensusXML of adduct groups")
    parser.add_argument("--negative", action="store_true", help="Negative ionization mode")
    parser.add_argument("--adducts", help="Comma-separated potential adducts (overrides defaults)")
    parser.add_argument("--charge-min", type=int, default=1)
    parser.add_argument("--charge-max", type=int, default=1)
    parser.add_argument("--mass-max-diff", type=float, default=0.05, help="Max mass difference (Da)")
    parser.add_argument("--rt-max-diff", type=float, default=10.0, help="Max RT difference (s)")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: file not found: {args.input}")
        sys.exit(1)

    fm = ms.FeatureMap()
    ms.FeatureXMLFile().load(args.input, fm)
    print(f"Loaded {fm.size()} features")

    adducts = args.adducts
    if adducts is None:
        adducts = DEFAULT_NEG if args.negative else DEFAULT_POS

    mfd = ms.MetaboliteFeatureDeconvolution()
    p = mfd.getDefaults()
    p.setValue("potential_adducts", [a.strip().encode() for a in adducts.split(",")])
    p.setValue("charge_min", args.charge_min)
    p.setValue("charge_max", args.charge_max)
    p.setValue("mass_max_diff", args.mass_max_diff)
    p.setValue("retention_max_diff", args.rt_max_diff)
    p.setValue("negative_mode", "true" if args.negative else "false")
    mfd.setParameters(p)

    fm_out = ms.FeatureMap()
    groups = ms.ConsensusMap()
    edges = ms.ConsensusMap()
    mfd.compute(fm, fm_out, groups, edges)

    annotated = sum(1 for f in fm_out if f.metaValueExists("dc_charge_adducts"))
    print(f"Decharged feature map: {fm_out.size()} features ({annotated} adduct-annotated)")
    print(f"Adduct groups: {groups.size()}")

    out_features = args.out_features or os.path.splitext(args.input)[0] + "_decharged.featureXML"
    ms.FeatureXMLFile().store(out_features, fm_out)
    print(f"Wrote {out_features}")

    if args.out_consensus:
        ms.ConsensusXMLFile().store(args.out_consensus, groups)
        print(f"Wrote {args.out_consensus}")


if __name__ == "__main__":
    main()
