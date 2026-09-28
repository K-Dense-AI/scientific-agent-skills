#!/usr/bin/env python3
"""Resting-state spectral summary: band power, individual alpha frequency, asymmetry.

Cuts the recording into fixed-length segments, drops segments that overlap BAD
annotations or exceed a peak-to-peak limit, averages the per-segment PSD (Welch
or multitaper), and reports for every good EEG channel and band the absolute
power (uV^2), relative power, and log10 power; the individual alpha frequency
(peak and centre of gravity) over posterior channels; and alpha asymmetry
indices, ln(right) - ln(left), for homologous pairs such as F4:F3.

Examples:
    python band_power.py clean_eeg.fif --out-dir spectral
    python band_power.py rest.edf --out-dir spectral --segment 4 --overlap 2 \\
        --band theta=4:8 --band alpha=8:13 --band beta=13:30 --asymmetry F4:F3
"""

from __future__ import annotations

import argparse
import csv
import math
import warnings
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from _common import (
    TESTED_MNE_VERSION,
    CliError,
    checked_input,
    import_mne,
    parse_band,
    parse_name_list,
    parse_threshold_uv,
    prepare_outputs,
    recording_stem,
    robust_ceiling,
    rounded,
    run_cli,
    write_json,
)

DEFAULT_BANDS = ("delta=1:4", "theta=4:8", "alpha=8:13", "beta=13:30", "gamma=30:45")
POSTERIOR = ("O1", "Oz", "O2", "PO3", "POz", "PO4", "PO7", "PO8", "P3", "Pz", "P4")
DEFAULT_PAIRS = ("F4:F3", "F8:F7", "P4:P3", "O2:O1")
BAND_COLUMNS = ("channel", "band", "fmin_hz", "fmax_hz", "abs_power_uv2", "rel_power", "log10_abs_power")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("recording", help="continuous recording readable by MNE (ideally cleaned)")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--prefix", help="output name stem (default: from the input name)")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--crop", nargs=2, type=float, metavar=("TMIN", "TMAX"))
    parser.add_argument("--segment", type=float, default=4.0, help="segment length in s (default 4)")
    parser.add_argument("--overlap", type=float, default=2.0, help="segment overlap in s (default 2)")
    parser.add_argument(
        "--reject-uv",
        default="auto",
        help="segment peak-to-peak limit in uV, 'auto' (robust outliers, default), or 0 (off)",
    )
    parser.add_argument("--method", choices=("welch", "multitaper"), default="welch")
    parser.add_argument("--band", action="append", default=[], help="NAME=FMIN:FMAX (repeatable)")
    parser.add_argument("--iaf-channels", help="channels for the alpha peak (default: posterior)")
    parser.add_argument("--iaf-range", nargs=2, type=float, default=(7.0, 14.0), metavar=("FMIN", "FMAX"))
    parser.add_argument("--asymmetry", action="append", default=[], help="RIGHT:LEFT channel pair")
    parser.add_argument("--asymmetry-band", default="alpha")
    parser.add_argument("--save-psd", action="store_true", help="also write the PSD as long CSV")
    parser.add_argument("--no-figures", action="store_true")
    return parser


def band_table(psd: Any, freqs: Any, bands: list[tuple[str, float, float]]) -> tuple[Any, Any]:
    """Absolute band power (trapezoid over PSD) and the total over the band span."""
    import numpy as np
    from scipy.integrate import trapezoid

    absolute = np.zeros((psd.shape[0], len(bands)))
    for j, (name, lo, hi) in enumerate(bands):
        mask = (freqs >= lo - 1e-9) & (freqs <= hi + 1e-9)
        if mask.sum() < 2:
            raise CliError(f"band {name} ({lo}-{hi} Hz) is narrower than the frequency resolution")
        absolute[:, j] = trapezoid(psd[:, mask], freqs[mask], axis=1)
    lo = min(b[1] for b in bands)
    hi = max(b[2] for b in bands)
    span = (freqs >= lo - 1e-9) & (freqs <= hi + 1e-9)
    total = trapezoid(psd[:, span], freqs[span], axis=1)
    return absolute, total


def alpha_peak(psd: Any, freqs: Any, fmin: float, fmax: float) -> dict[str, Any]:
    """Peak alpha frequency and centre of gravity of a (channel-averaged) PSD."""
    import numpy as np

    mask = (freqs >= fmin) & (freqs <= fmax)
    f, p = freqs[mask], psd[mask]
    if f.size < 3:
        raise CliError("--iaf-range is narrower than the frequency resolution")
    k = int(np.argmax(p))
    edges = 0.5 * (p[0] + p[-1])
    result = {
        "range_hz": [fmin, fmax],
        "center_of_gravity_hz": rounded(float(np.sum(f * p) / np.sum(p)), 3),
        "peak_hz": None,
        "peak_prominence_db": rounded(10 * math.log10(p[k] / edges), 2) if edges > 0 else None,
    }
    if 0 < k < f.size - 1:
        result["peak_hz"] = rounded(float(f[k]), 3)
    else:
        result["note"] = "maximum on the range edge: no clear alpha peak"
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    bands = [parse_band(text) for text in (args.band or DEFAULT_BANDS)]
    if len({b[0] for b in bands}) != len(bands):
        raise CliError("band names must be unique")
    if not 0 <= args.overlap < args.segment:
        raise CliError("--overlap must be >= 0 and shorter than --segment")
    path = checked_input(args.recording)
    stem = recording_stem(path, args.prefix)
    out_dir = Path(args.out_dir)
    outputs = {
        "bands": out_dir / f"{stem}_band_power.csv",
        "summary": out_dir / f"{stem}_spectral_summary.json",
    }
    if args.save_psd:
        outputs["psd"] = out_dir / f"{stem}_psd.csv"
    if not args.no_figures:
        outputs["psd_figure"] = out_dir / f"{stem}_psd.png"
        outputs["topomaps"] = out_dir / f"{stem}_band_topomaps.png"
    prepare_outputs(out_dir, outputs.values(), args.overwrite)

    mne = import_mne()
    import numpy as np

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            raw = mne.io.read_raw(path, preload=True)
        except Exception as error:
            raise CliError(f"MNE could not read {path.name}: {error}") from error
    if args.crop:
        raw.crop(args.crop[0], min(args.crop[1], raw.times[-1]))
    sfreq = raw.info["sfreq"]
    fmax = max(b[2] for b in bands)
    if fmax >= sfreq / 2:
        raise CliError(f"bands reach {fmax} Hz, at or above Nyquist ({sfreq / 2:g} Hz)")
    eeg = [n for n, t in zip(raw.ch_names, raw.get_channel_types()) if t == "eeg"]
    good = [n for n in eeg if n not in raw.info["bads"]]
    if not good:
        raise CliError("no good EEG channels")
    notes = []
    lowpass, highpass = raw.info["lowpass"], raw.info["highpass"]
    for name, lo, hi in bands:
        if lowpass and hi > lowpass:
            notes.append(f"band {name} ({lo:g}-{hi:g} Hz) extends past the {lowpass:g} Hz low-pass; "
                         "its power is filter-attenuated")
        if highpass and lo < highpass:
            notes.append(f"band {name} ({lo:g}-{hi:g} Hz) starts below the {highpass:g} Hz high-pass")

    epochs = mne.make_fixed_length_epochs(
        raw, duration=args.segment, overlap=args.overlap, reject_by_annotation=True,
        preload=True, verbose="ERROR",
    )
    n_segments = len(epochs.drop_log)
    n_annot = sum(1 for log in epochs.drop_log if log)
    if not len(epochs):
        raise CliError("no segment is free of BAD annotations")
    reject = parse_threshold_uv(args.reject_uv, what="--reject-uv")
    limit_uv = None
    if reject == "auto":
        p2p = np.ptp(epochs.get_data(picks=good), axis=2).max(axis=1)
        limit_uv = robust_ceiling(p2p) * 1e6
    elif reject is not None:
        limit_uv = float(reject)
    if limit_uv is not None:
        epochs.drop_bad(reject={"eeg": limit_uv * 1e-6}, verbose="ERROR")
    if not len(epochs):
        raise CliError("no segment survived rejection; check units, --reject-uv and bad channels")

    starts = (epochs.events[:, 0] - raw.first_samp) / sfreq
    covered, end = 0.0, -math.inf
    for start in np.sort(starts):  # union of the kept segments (they overlap)
        covered += args.segment - max(0.0, min(args.segment, end - start))
        end = start + args.segment
    n_fft = int(round(args.segment * sfreq))
    kwargs: dict[str, Any] = {"n_fft": n_fft, "n_per_seg": n_fft, "n_overlap": 0} if args.method == "welch" else {}
    fmin = min(b[1] for b in bands)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        spectrum = epochs.compute_psd(method=args.method, fmin=fmin, fmax=fmax, picks=good, verbose="ERROR", **kwargs)
    psd = spectrum.get_data().mean(axis=0) * 1e12  # V^2/Hz -> uV^2/Hz
    freqs = spectrum.freqs
    absolute, total = band_table(psd, freqs, bands)
    relative = absolute / total[:, None]

    rows = []
    for i, channel in enumerate(good):
        for j, (name, lo, hi) in enumerate(bands):
            rows.append(
                {
                    "channel": channel, "band": name, "fmin_hz": lo, "fmax_hz": hi,
                    "abs_power_uv2": rounded(absolute[i, j], 6),
                    "rel_power": rounded(relative[i, j], 6),
                    "log10_abs_power": rounded(math.log10(absolute[i, j]), 6) if absolute[i, j] > 0 else None,
                }
            )
    with outputs["bands"].open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(BAND_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)
    if args.save_psd:
        with outputs["psd"].open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["channel", "freq_hz", "psd_uv2_per_hz"])
            for i, channel in enumerate(good):
                writer.writerows([channel, rounded(f, 4), rounded(v, 8)] for f, v in zip(freqs, psd[i]))

    iaf_names = parse_name_list(args.iaf_channels) or [c for c in POSTERIOR if c in good]
    missing = [c for c in iaf_names if c not in good]
    if missing:
        raise CliError(f"--iaf-channels not among the good EEG channels: {missing}")
    iaf = None
    if iaf_names:
        mean_psd = psd[[good.index(c) for c in iaf_names]].mean(axis=0)
        iaf = alpha_peak(mean_psd, freqs, *args.iaf_range)
        iaf["channels"] = iaf_names

    band_names = [b[0] for b in bands]
    asymmetry: dict[str, Any] = {}
    pairs = args.asymmetry or [p for p in DEFAULT_PAIRS if all(c in good for c in p.split(":"))]
    if pairs and args.asymmetry_band not in band_names:
        raise CliError(f"--asymmetry-band {args.asymmetry_band!r} is not one of {band_names}")
    for pair in pairs:
        right, _, left = pair.partition(":")
        if right not in good or left not in good:
            raise CliError(f"--asymmetry {pair!r}: both channels must be good EEG channels")
        j = band_names.index(args.asymmetry_band)
        asymmetry[pair] = rounded(
            math.log(absolute[good.index(right), j]) - math.log(absolute[good.index(left), j]), 4
        )

    if covered < 60:
        notes.append("less than 60 s of clean data; spectral estimates will be noisy")
    figures = [] if args.no_figures else _figures(raw, good, psd, freqs, bands, relative, iaf, outputs, mne)
    summary = {
        "input": path.name,
        "software": {"mne": mne.__version__, "tested_mne": TESTED_MNE_VERSION},
        "method": args.method,
        "segment_s": args.segment,
        "overlap_s": args.overlap,
        "frequency_resolution_hz": rounded(freqs[1] - freqs[0], 4),
        "segments": {
            "total": n_segments,
            "dropped_by_annotation": n_annot,
            "dropped_by_amplitude": n_segments - n_annot - len(epochs),
            "kept": len(epochs),
            "kept_seconds": rounded(covered, 1),
        },
        "reject_eeg_uv": {"requested": args.reject_uv, "applied": rounded(limit_uv, 2)},
        "channels": good,
        "excluded_bads": [n for n in eeg if n not in good],
        "bands": {name: [lo, hi] for name, lo, hi in bands},
        "mean_relative_power": {name: rounded(relative[:, j].mean(), 5) for j, name in enumerate(band_names)},
        "individual_alpha_frequency": iaf,
        "asymmetry": {"band": args.asymmetry_band, "index_ln_right_minus_ln_left": asymmetry} if asymmetry else None,
        "figures": figures,
        "notes": notes,
    }
    summary["outputs"] = {
        key: p.name for key, p in outputs.items() if p.exists() or key == "summary"
    }
    write_json(outputs["summary"], summary)
    kept = summary["segments"]
    print(f"segments kept {kept['kept']}/{kept['total']} ({kept['kept_seconds']} s); "
          f"resolution {summary['frequency_resolution_hz']} Hz")
    print("mean relative power: " + ", ".join(f"{k} {v:.3f}" for k, v in summary["mean_relative_power"].items()))
    if iaf:
        print(f"alpha peak {iaf['peak_hz']} Hz, centre of gravity {iaf['center_of_gravity_hz']} Hz "
              f"({', '.join(iaf['channels'])})")
    if asymmetry:
        print(f"{args.asymmetry_band} asymmetry: {asymmetry}")
    for note in notes:
        print(f"note: {note}")
    return 0


def _figures(raw, good, psd, freqs, bands, relative, iaf, outputs, mne) -> list[str]:
    import matplotlib.pyplot as plt
    import numpy as np

    written = []
    fig, ax = plt.subplots(figsize=(7, 3.8), layout="constrained")
    db = 10 * np.log10(psd)
    ax.plot(freqs, db.T, color="#b8c2cc", lw=0.6)
    ax.plot(freqs, np.median(db, axis=0), color="#1f5fbf", lw=2, label="median")
    for k, (name, lo, hi) in enumerate(bands):
        ax.axvspan(lo, hi, color="#f2c94c" if k % 2 else "#9ad0c2", alpha=0.15, lw=0)
        ax.text((lo + hi) / 2, 1.0, name, transform=ax.get_xaxis_transform(), ha="center", va="bottom", fontsize=8)
    if iaf and iaf.get("peak_hz"):
        ax.axvline(iaf["peak_hz"], color="#d64545", lw=1, ls="--", label=f"alpha peak {iaf['peak_hz']:g} Hz")
    ax.set(xlabel="Frequency (Hz)", ylabel="PSD (dB re 1 µV²/Hz)", xlim=(freqs[0], freqs[-1]))
    ax.legend(frameon=False, loc="upper right")
    ax.grid(alpha=0.25)
    fig.savefig(outputs["psd_figure"], dpi=150)
    plt.close(fig)
    written.append(outputs["psd_figure"].name)

    info = raw.copy().pick(good).info
    positions = [ch["loc"][:3] for ch in info["chs"]]
    if all(np.all(np.isfinite(p)) and np.any(p) for p in positions) and len(good) >= 4:
        fig, axes = plt.subplots(1, len(bands), figsize=(2.3 * len(bands), 2.6), layout="constrained")
        for ax, (name, _, _), values in zip(np.atleast_1d(axes), bands, relative.T):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                image, _ = mne.viz.plot_topomap(values, info, axes=ax, show=False, cmap="viridis")
            ax.set_title(name)
            fig.colorbar(image, ax=ax, shrink=0.7, format="%.2f")
        fig.suptitle("Relative power")
        fig.savefig(outputs["topomaps"], dpi=150)
        plt.close(fig)
        written.append(outputs["topomaps"].name)
    return written


if __name__ == "__main__":
    run_cli(main)
