#!/usr/bin/env python3
"""
Signal Processing for Spectra

Apply a configurable chain of signal-processing steps to all (or selected MS-level)
spectra in an MS file: smoothing, centroiding (peak picking), normalization, and
intensity/S-N thresholding. Steps run in the order listed below.

Steps (enable with flags):
    --smooth gauss|sgolay   Smooth profile data
    --pick                  Centroid profile data (PeakPickerHiRes)
    --normalize to_one|to_TIC   Normalize intensities
    --threshold FLOAT       Remove peaks below absolute intensity
    --sn FLOAT              Remove peaks below this signal-to-noise ratio

Usage:
    python process_spectra.py raw.mzML centroided.mzML --smooth gauss --pick
    python process_spectra.py data.mzML out.mzML --normalize to_one --threshold 100
    python process_spectra.py data.mzML out.mzML --ms-level 1 --sn 2.0
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
    parser = argparse.ArgumentParser(description="Apply signal processing to spectra.")
    parser.add_argument("input", help="Input mzML/mzXML file")
    parser.add_argument("output", help="Output mzML file")
    parser.add_argument("--ms-level", type=int, help="Process only this MS level (others passed through)")
    parser.add_argument("--smooth", choices=["gauss", "sgolay"], help="Smoothing filter")
    parser.add_argument("--gaussian-width", type=float, default=0.2, help="Gaussian width (default 0.2)")
    parser.add_argument("--pick", action="store_true", help="Centroid via PeakPickerHiRes")
    parser.add_argument("--signal-to-noise", type=float, default=0.0,
                        help="PeakPicker S/N threshold (0 = off, default)")
    parser.add_argument("--normalize", choices=["to_one", "to_TIC"], help="Normalization method")
    parser.add_argument("--threshold", type=float, help="Remove peaks below this absolute intensity")
    parser.add_argument("--sn", type=float, help="Remove peaks below this S/N (SignalToNoiseEstimatorMedian)")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: file not found: {args.input}")
        sys.exit(1)

    exp = ms.MSExperiment()
    ms.FileHandler().loadExperiment(args.input, exp)
    print(f"Loaded {exp.getNrSpectra()} spectra")

    levels = [args.ms_level] if args.ms_level else []

    # 1. Smoothing
    if args.smooth == "gauss":
        f = ms.GaussFilter()
        p = f.getParameters()
        p.setValue("gaussian_width", args.gaussian_width)
        f.setParameters(p)
        f.filterExperiment(exp)
        print(f"Applied Gaussian smoothing (width={args.gaussian_width})")
    elif args.smooth == "sgolay":
        f = ms.SavitzkyGolayFilter()
        f.filterExperiment(exp)
        print("Applied Savitzky-Golay smoothing")

    # 2. Peak picking / centroiding
    if args.pick:
        picker = ms.PeakPickerHiRes()
        p = picker.getParameters()
        p.setValue("signal_to_noise", args.signal_to_noise)
        if levels:
            p.setValue("ms_levels", levels)
        picker.setParameters(p)
        out = ms.MSExperiment()
        picker.pickExperiment(exp, out, True)
        exp = out
        print("Centroided with PeakPickerHiRes")

    # 3. Normalization
    if args.normalize:
        norm = ms.Normalizer()
        p = norm.getParameters()
        p.setValue("method", args.normalize)
        norm.setParameters(p)
        norm.filterPeakMap(exp)
        print(f"Normalized ({args.normalize})")

    # 4. S/N filtering (per spectrum)
    if args.sn is not None:
        sn_est = ms.SignalToNoiseEstimatorMedian()
        kept_total = 0
        for spec in exp:
            if levels and spec.getMSLevel() not in levels:
                continue
            sn_est.init(spec)
            mz, inten = spec.get_peaks()
            keep = [i for i in range(len(mz)) if sn_est.getSignalToNoise(i) >= args.sn]
            spec.set_peaks(([mz[i] for i in keep], [inten[i] for i in keep]))
            kept_total += len(keep)
        print(f"S/N filter (>= {args.sn}): kept {kept_total} peaks")

    # 5. Absolute intensity threshold
    if args.threshold is not None:
        kept_total = 0
        for spec in exp:
            if levels and spec.getMSLevel() not in levels:
                continue
            mz, inten = spec.get_peaks()
            keep = inten >= args.threshold
            spec.set_peaks((mz[keep], inten[keep]))
            kept_total += int(keep.sum())
        print(f"Intensity threshold (>= {args.threshold}): kept {kept_total} peaks")

    ms.MzMLFile().store(args.output, exp)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
