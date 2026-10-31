#!/usr/bin/env python3
"""
Accurate Mass Search (Metabolite Annotation)

Annotate detected features with putative metabolite identities by matching
accurate masses against the bundled HMDB databases using AccurateMassSearchEngine.
Outputs an annotated mzTab and a flat CSV of hits. By default uses the HMDB
mapping/structure files shipped with pyOpenMS.

Usage:
    python accurate_mass_search.py features.featureXML --out-mztab hits.mzTab
    python accurate_mass_search.py features.featureXML --negative --ppm 5 --csv hits.csv
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
    parser = argparse.ArgumentParser(description="Accurate-mass metabolite annotation.")
    parser.add_argument("input", help="Input featureXML (or consensusXML)")
    parser.add_argument("--out-mztab", help="Output mzTab file")
    parser.add_argument("--csv", help="Output CSV of annotation hits")
    parser.add_argument("--negative", action="store_true", help="Negative ionization mode")
    parser.add_argument("--ppm", type=float, default=5.0, help="Mass error tolerance in ppm (default 5)")
    parser.add_argument("--db-mapping", help="Custom HMDB mapping TSV (default: bundled)")
    parser.add_argument("--db-struct", help="Custom HMDB structure TSV (default: bundled)")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: file not found: {args.input}")
        sys.exit(1)

    is_consensus = args.input.lower().endswith(".consensusxml")
    if is_consensus:
        fmap = ms.ConsensusMap()
        ms.ConsensusXMLFile().load(args.input, fmap)
    else:
        fmap = ms.FeatureMap()
        ms.FeatureXMLFile().load(args.input, fmap)
    print(f"Loaded {fmap.size()} features")

    if args.ppm <= 0:
        parser.error("--ppm must be positive")
    for supplied in (args.db_mapping, args.db_struct):
        if supplied and not os.path.isfile(supplied):
            parser.error(f"database file not found: {supplied}")

    engine = ms.AccurateMassSearchEngine()
    p = engine.getDefaults()
    p.setValue("mass_error_value", args.ppm)
    p.setValue("mass_error_unit", "ppm")
    p.setValue("ionization_mode", "negative" if args.negative else "positive")
    if args.db_mapping:
        p.setValue("db:mapping", [os.path.abspath(args.db_mapping)])
    if args.db_struct:
        p.setValue("db:struct", [os.path.abspath(args.db_struct)])
    engine.setParameters(p)
    engine.init()

    mztab = ms.MzTab()
    if is_consensus:
        engine.run(fmap, mztab)
    else:
        engine.run(fmap, mztab)

    out_mztab = args.out_mztab or os.path.splitext(args.input)[0] + ".mzTab"
    ms.MzTabFile().store(out_mztab, mztab)
    print(f"Wrote {out_mztab}")

    if args.csv:
        # mzTab small-molecule section -> CSV via pandas
        import pandas as pd
        try:
            sm = mztab.getSmallMoleculeSectionRows()
            print(f"Small-molecule annotation rows: {len(sm)}")
        except Exception:
            pass
        # Re-read the mzTab text for a robust flat dump of the SML table
        rows = []
        with open(out_mztab) as fh:
            header = None
            for line in fh:
                if line.startswith("SMH"):
                    header = line.rstrip("\n").split("\t")
                elif line.startswith("SML") and header:
                    rows.append(dict(zip(header, line.rstrip("\n").split("\t"))))
        if rows:
            pd.DataFrame(rows).to_csv(args.csv, index=False)
            print(f"Wrote {args.csv} ({len(rows)} annotation rows)")
        else:
            print("No small-molecule annotations to write.")


if __name__ == "__main__":
    main()
