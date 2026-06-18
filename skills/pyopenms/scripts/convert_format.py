#!/usr/bin/env python3
"""
Convert Between MS File Formats

Convert spectral data between mzML, mzXML, and MGF, with optional MS-level and
RT/intensity filtering. Uses FileHandler for transparent format detection on load.

Supported conversions (by output extension): .mzML, .mzXML, .mgf

Usage:
    python convert_format.py input.mzXML output.mzML
    python convert_format.py input.mzML peaks.mgf --ms-level 2
    python convert_format.py input.mzML out.mzML --rt-min 60 --rt-max 600 --min-intensity 500
"""

import argparse
import os
import sys

try:
    import pyopenms as ms
except ImportError:
    print("Error: pyopenms not installed. Install with: uv pip install pyopenms")
    sys.exit(1)


def load_experiment(path):
    exp = ms.MSExperiment()
    ms.FileHandler().loadExperiment(path, exp)
    return exp


def filter_experiment(exp, ms_level=None, rt_min=None, rt_max=None, min_intensity=None):
    out = ms.MSExperiment()
    for spec in exp:
        if ms_level is not None and spec.getMSLevel() != ms_level:
            continue
        rt = spec.getRT()
        if rt_min is not None and rt < rt_min:
            continue
        if rt_max is not None and rt > rt_max:
            continue
        if min_intensity is not None:
            mz, inten = spec.get_peaks()
            keep = inten >= min_intensity
            spec.set_peaks((mz[keep], inten[keep]))
        out.addSpectrum(spec)
    # carry chromatograms if no MS-level filter requested
    if ms_level is None:
        for chrom in exp.getChromatograms():
            out.addChromatogram(chrom)
    return out


def store_experiment(exp, path):
    ext = path.lower()
    if ext.endswith(".mzml"):
        ms.MzMLFile().store(path, exp)
    elif ext.endswith(".mzxml"):
        ms.MzXMLFile().store(path, exp)
    elif ext.endswith(".mgf"):
        ms.MascotGenericFile().store(path, exp)
    else:
        raise ValueError(f"Unsupported output extension: {path} (use .mzML, .mzXML, or .mgf)")


def main():
    parser = argparse.ArgumentParser(description="Convert/filter MS files between formats.")
    parser.add_argument("input", help="Input file (mzML/mzXML/...)")
    parser.add_argument("output", help="Output file (.mzML, .mzXML, or .mgf)")
    parser.add_argument("--ms-level", type=int, help="Keep only spectra at this MS level")
    parser.add_argument("--rt-min", type=float, help="Minimum retention time (s)")
    parser.add_argument("--rt-max", type=float, help="Maximum retention time (s)")
    parser.add_argument("--min-intensity", type=float, help="Drop peaks below this intensity")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: file not found: {args.input}")
        sys.exit(1)

    print(f"Loading {args.input}...")
    exp = load_experiment(args.input)
    print(f"  {exp.getNrSpectra()} spectra, {exp.getNrChromatograms()} chromatograms")

    if any(v is not None for v in (args.ms_level, args.rt_min, args.rt_max, args.min_intensity)):
        exp = filter_experiment(exp, args.ms_level, args.rt_min, args.rt_max, args.min_intensity)
        print(f"  after filtering: {exp.getNrSpectra()} spectra")

    print(f"Writing {args.output}...")
    store_experiment(exp, args.output)
    print("Done.")


if __name__ == "__main__":
    main()
