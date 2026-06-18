#!/usr/bin/env python3
"""
Visualize MS Data

Quick plots for inspecting MS data and results:
    spectrum     single MS spectrum (peak/stick plot) by index or RT
    tic          total ion chromatogram
    featuremap   2D feature map (RT vs m/z, sized/colored by intensity)
    map2d        2D heatmap of MS1 signal (RT vs m/z)

Usage:
    python plot_ms_data.py spectrum data.mzML --index 0 --out spec.png
    python plot_ms_data.py tic data.mzML --out tic.png
    python plot_ms_data.py featuremap features.featureXML --out fmap.png
    python plot_ms_data.py map2d data.mzML --out map.png
"""

import argparse
import os
import sys

try:
    import pyopenms as ms
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    print("Error: pyopenms/matplotlib not installed. Install with: uv pip install pyopenms matplotlib")
    sys.exit(1)


def load_exp(path):
    exp = ms.MSExperiment()
    ms.FileHandler().loadExperiment(path, exp)
    return exp


def plot_spectrum(args):
    exp = load_exp(args.input)
    if args.rt is not None:
        spec = min((s for s in exp), key=lambda s: abs(s.getRT() - args.rt))
    else:
        spec = exp.getSpectrum(args.index)
    mz, inten = spec.get_peaks()
    plt.figure(figsize=(10, 5))
    plt.vlines(mz, 0, inten, linewidth=0.8)
    plt.xlabel("m/z")
    plt.ylabel("Intensity")
    plt.title(f"Spectrum (MS{spec.getMSLevel()}, RT={spec.getRT():.1f}s, {len(mz)} peaks)")
    plt.tight_layout()


def plot_tic(args):
    exp = load_exp(args.input)
    rts, tic = [], []
    for s in exp:
        if s.getMSLevel() != 1:
            continue
        _, inten = s.get_peaks()
        rts.append(s.getRT())
        tic.append(float(inten.sum()) if len(inten) else 0.0)
    plt.figure(figsize=(10, 5))
    plt.plot(rts, tic, linewidth=1)
    plt.xlabel("Retention time (s)")
    plt.ylabel("Total ion current")
    plt.title("Total Ion Chromatogram")
    plt.tight_layout()


def plot_featuremap(args):
    fm = ms.FeatureMap()
    ms.FeatureXMLFile().load(args.input, fm)
    df = fm.get_df()
    plt.figure(figsize=(10, 6))
    sizes = 10 + 40 * (df["intensity"] / df["intensity"].max())
    sc = plt.scatter(df["rt"], df["mz"], s=sizes, c=np.log10(df["intensity"] + 1),
                     cmap="viridis", alpha=0.7)
    plt.colorbar(sc, label="log10(intensity)")
    plt.xlabel("Retention time (s)")
    plt.ylabel("m/z")
    plt.title(f"Feature map ({fm.size()} features)")
    plt.tight_layout()


def plot_map2d(args):
    exp = load_exp(args.input)
    rts, mzs, ints = [], [], []
    for s in exp:
        if s.getMSLevel() != 1:
            continue
        mz, inten = s.get_peaks()
        rt = s.getRT()
        for m, it in zip(mz, inten):
            rts.append(rt); mzs.append(m); ints.append(it)
    plt.figure(figsize=(10, 6))
    sc = plt.scatter(rts, mzs, c=np.log10(np.array(ints) + 1), s=2,
                     cmap="inferno", alpha=0.5)
    plt.colorbar(sc, label="log10(intensity)")
    plt.xlabel("Retention time (s)")
    plt.ylabel("m/z")
    plt.title("MS1 signal map")
    plt.tight_layout()


PLOTS = {"spectrum": plot_spectrum, "tic": plot_tic,
         "featuremap": plot_featuremap, "map2d": plot_map2d}


def main():
    parser = argparse.ArgumentParser(description="Visualize MS data.")
    parser.add_argument("kind", choices=list(PLOTS), help="Plot type")
    parser.add_argument("input", help="Input file")
    parser.add_argument("--index", type=int, default=0, help="Spectrum index (spectrum plot)")
    parser.add_argument("--rt", type=float, help="Select spectrum nearest this RT (spectrum plot)")
    parser.add_argument("--out", required=True, help="Output image path (PNG/PDF/SVG)")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: file not found: {args.input}")
        sys.exit(1)

    PLOTS[args.kind](args)
    plt.savefig(args.out, dpi=150)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
