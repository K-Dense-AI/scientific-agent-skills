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
    python process_spectra.py data.mzML out.mzML --normalize to_one --threshold 0.01
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
    parser.add_argument("--gaussian-width", type=float, default=0.2, help="Gaussian width in m/z (Th; default 0.2)")
    parser.add_argument("--pick", action="store_true", help="Centroid via PeakPickerHiRes")
    parser.add_argument("--signal-to-noise", type=float, default=0.0,
                        help="PeakPicker S/N threshold (0 = off, default)")
    parser.add_argument("--normalize", choices=["to_one", "to_TIC"], help="Normalization method")
    parser.add_argument("--threshold", type=float, help="Remove peaks below this absolute intensity")
    parser.add_argument("--sn", type=float, help="Remove peaks below this S/N (SignalToNoiseEstimatorMedian)")
    parser.add_argument("--assume-profile", action="store_true", help="Allow smoothing/picking unknown spectrum type after independent verification")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: file not found: {args.input}")
        sys.exit(1)

    exp = ms.MSExperiment()
    ms.FileHandler().loadExperiment(args.input, exp)
    print(f"Loaded {exp.getNrSpectra()} spectra")

    # Work on copies and explicitly replace the experiment spectra. Iterating
    # an MSExperiment does not promise writable references to its C++ storage.
    processed = []
    for original in exp:
        spec = ms.MSSpectrum(original)
        if args.ms_level is not None and spec.getMSLevel() != args.ms_level:
            processed.append(spec)
            continue
        spec.sortByPosition()
        if args.smooth or args.pick:
            kind = spec.getType()
            if kind == ms.SpectrumSettings.SpectrumType.CENTROID:
                parser.error("smoothing/peak picking requires profile spectra; select a profile MS level")
            if kind == ms.SpectrumSettings.SpectrumType.UNKNOWN and not args.assume_profile:
                parser.error("spectrum type unknown; verify profile acquisition before --assume-profile")
        if args.smooth:
            smoother = ms.GaussFilter() if args.smooth == "gauss" else ms.SavitzkyGolayFilter()
            if args.smooth == "gauss":
                p = smoother.getParameters()
                p.setValue("gaussian_width", args.gaussian_width)
                smoother.setParameters(p)
            smoother.filter(spec)
        if args.pick:
            picker = ms.PeakPickerHiRes()
            p = picker.getParameters()
            p.setValue("signal_to_noise", args.signal_to_noise)
            picker.setParameters(p)
            picked = ms.MSSpectrum()
            picker.pick(spec, picked)
            spec = picked
        if args.normalize:
            normalizer = ms.Normalizer()
            p = normalizer.getParameters()
            p.setValue("method", args.normalize)
            normalizer.setParameters(p)
            normalizer.filterSpectrum(spec)
        if args.sn is not None:
            estimator = ms.SignalToNoiseEstimatorMedian()
            estimator.init(spec)
            spec.select([i for i in range(len(spec)) if estimator.getSignalToNoise(i) >= args.sn])
        if args.threshold is not None:
            _, intensity = spec.get_peaks()
            spec.select((intensity >= args.threshold).nonzero()[0].tolist())
        processed.append(spec)
    exp.setSpectra(processed)

    ms.MzMLFile().store(args.output, exp)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
