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

    mapped = [pid for feature in cm for pid in feature.getPeptideIdentifications()
              if pid.metaValueExists("map_index") and pid.metaValueExists("spectrum_index")]
    if not mapped:
        raise ValueError("GNPS export needs MS2 feature annotations (map_index and spectrum_index); plain linked MS1 features are insufficient.")
    on_disk = {}
    for pid in mapped:
        i = int(pid.getMetaValue("map_index"))
        if not 0 <= i < len(args.mzml):
            raise ValueError("GNPS map_index is outside the supplied mzML list; preserve sample order.")
        if i not in on_disk:
            run = ms.OnDiscMSExperiment()
            if not run.openFile(args.mzml[i]):
                raise ValueError("GNPS requires readable indexed mzML files")
            on_disk[i] = run
        j = int(pid.getMetaValue("spectrum_index"))
        if not 0 <= j < on_disk[i].getNrSpectra() or on_disk[i].getSpectrum(j).getMSLevel() != 2:
            raise ValueError("GNPS spectrum_index must address an MS2 spectrum in its source map")
    ms.GNPSMGFFile().store(args.consensus, args.mzml, mgf_out)
    print(f"Wrote {mgf_out}")

    ms.GNPSQuantificationFile().store(cm, quant_out)
    print(f"Wrote {quant_out}")
    print("Upload both to GNPS Feature-Based Molecular Networking.")


def export_sirius(args):
    out_ms = args.out or os.path.splitext(args.input)[0] + ".ms"
    out_info = args.compound_info or os.path.splitext(out_ms)[0] + "_compounds.tsv"

    exporter = ms.SiriusExportAlgorithm()
    feature_files = [args.featurexml] if args.featurexml else []
    try:
        exporter.run([args.input], feature_files, out_ms, out_info)
    except RuntimeError as e:
        if "SourceFile" in str(e):
            print("Error: the mzML lacks proper SourceFile annotation required by SIRIUS export.")
            print("This is normal for synthetic/hand-built mzML. Re-export the file through")
            print("a suitable converter and verify source format/native-ID metadata before retrying.")
            print("Do not fabricate instrument provenance; vendor conversion alone is not a guarantee.")
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
