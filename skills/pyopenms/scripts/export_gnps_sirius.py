#!/usr/bin/env python3
"""
Export for GNPS (FBMN) and SIRIUS

Generate the input files required by downstream annotation tools:

    gnps    Feature-Based Molecular Networking: writes an MGF of MS2 spectra
            (from a consensusXML linked across samples) plus the GNPS
            quantification table.
    sirius  Writes a SIRIUS .ms file (and compound-info TSV) from mzML +
            featureXML input for formula/structure elucidation.

Usage:
    python export_gnps_sirius.py gnps study.consensusXML --mzml s1.mzML s2.mzML --out-prefix gnps_out
    python export_gnps_sirius.py sirius sample.mzML --featurexml sample.featureXML --out sample.ms
"""

import argparse
import os
import sys

try:
    import pyopenms as ms
except ImportError:
    print("Error: pyopenms not installed. Install with: uv pip install pyopenms")
    sys.exit(1)


def export_gnps(args):
    cm = ms.ConsensusMap()
    ms.ConsensusXMLFile().load(args.consensus, cm)
    print(f"Loaded {cm.size()} consensus features")

    mgf_out = f"{args.out_prefix}.mgf"
    quant_out = f"{args.out_prefix}_quant.txt"

    mzml_paths = [p.encode() for p in args.mzml]
    ms.GNPSMGFFile().store(args.consensus.encode(), mzml_paths, mgf_out)
    print(f"Wrote {mgf_out}")

    ms.GNPSQuantificationFile().store(cm, quant_out)
    print(f"Wrote {quant_out}")
    print("Upload both to GNPS Feature-Based Molecular Networking.")


def export_sirius(args):
    out_ms = args.out or os.path.splitext(args.input)[0] + ".ms"
    out_info = args.compound_info or os.path.splitext(out_ms)[0] + "_compounds.tsv"

    exporter = ms.SiriusExportAlgorithm()
    feature_files = [args.featurexml.encode()] if args.featurexml else []
    try:
        exporter.run([args.input.encode()], feature_files, out_ms, out_info)
    except RuntimeError as e:
        if "SourceFile" in str(e):
            print("Error: the mzML lacks proper SourceFile annotation required by SIRIUS export.")
            print("This is normal for synthetic/hand-built mzML. Re-export the file through")
            print("OpenMS FileConverter (or any real instrument export) so it carries source")
            print("metadata, then retry. Vendor-converted mzML files already satisfy this.")
            sys.exit(2)
        raise
    print(f"Wrote {out_ms}")
    print(f"Wrote {out_info}")
    print("Run SIRIUS on the .ms file for formula/structure elucidation.")


def main():
    parser = argparse.ArgumentParser(description="Export for GNPS FBMN or SIRIUS.")
    sub = parser.add_subparsers(dest="mode", required=True)

    g = sub.add_parser("gnps", help="Export GNPS FBMN inputs")
    g.add_argument("consensus", help="consensusXML linked across samples")
    g.add_argument("--mzml", nargs="+", required=True, help="Source mzML files (with MS2)")
    g.add_argument("--out-prefix", default="gnps_export", help="Output prefix")

    s = sub.add_parser("sirius", help="Export SIRIUS .ms file")
    s.add_argument("input", help="mzML file (with MS2)")
    s.add_argument("--featurexml", help="Optional featureXML to group spectra")
    s.add_argument("--out", help="Output .ms path")
    s.add_argument("--compound-info", help="Output compound-info TSV path")

    args = parser.parse_args()
    if args.mode == "gnps":
        export_gnps(args)
    else:
        export_sirius(args)


if __name__ == "__main__":
    main()
