#!/usr/bin/env python3
# Author: Narvik Aghamalian
"""Simulate a 32-channel scalp-EEG oddball recording with known ground truth.

The signal mixes spatially correlated 1/f background activity, posterior alpha,
N1/P3 event-related components for 'standard' and 'target' trials, eye blinks
(also on a VEOG channel), line noise, and one flat plus one noisy channel. A JSON
sidecar records everything that was injected, so a pipeline can be validated
against known answers before it touches real data.

Examples:
    python simulate_eeg.py --out sim_raw.fif
    python simulate_eeg.py --out sim.edf --ecg --events annotations
    python simulate_eeg.py --out sim_raw.fif --microvolts-as-volts  # units bug
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from _common import (
    TESTED_MNE_VERSION,
    CliError,
    default_montage_name,
    import_mne,
    prepare_outputs,
    run_cli,
    write_json,
)

CHANNELS = (
    "Fp1", "Fp2", "AF3", "AF4", "F7", "F3", "Fz", "F4", "F8", "FC5", "FC1",
    "FC2", "FC6", "T7", "C3", "Cz", "C4", "T8", "CP5", "CP1", "CP2", "CP6",
    "P7", "P3", "Pz", "P4", "P8", "PO3", "PO4", "O1", "Oz", "O2",
)  # fmt: skip
FORMATS = {".fif": "fif", ".edf": "edf", ".vhdr": "brainvision", ".set": "eeglab"}
EXPORT_PACKAGES = {"edf": "edfio", "brainvision": "pybv", "eeglab": "eeglabio"}
BAD_CHANNELS = {"FC5": "noisy", "T8": "flat"}
EVENT_CODES = {"standard": 1, "target": 2}
# name -> (latency s, temporal SD s, peak channel, spatial SD m, amplitude uV per condition)
COMPONENTS = {
    "N1": (0.100, 0.025, "Cz", 0.05, {"standard": -5.0, "target": -5.0}),
    "P3": (0.350, 0.070, "Pz", 0.06, {"standard": 2.5, "target": 10.0}),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--out", required=True, help="output recording (.fif, .edf, .vhdr, .set)")
    parser.add_argument("--truth", help="ground-truth JSON (default: <out>_truth.json)")
    parser.add_argument("--duration", type=float, default=240.0, help="seconds (default 240)")
    parser.add_argument("--sfreq", type=float, default=250.0, help="Hz (default 250)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--line-freq", type=float, default=50.0, help="Hz; 0 disables")
    parser.add_argument("--alpha-freq", type=float, default=10.0, help="Hz (default 10)")
    parser.add_argument("--target-prob", type=float, default=0.2)
    parser.add_argument("--blink-rate", type=float, default=12.0, help="blinks per minute")
    parser.add_argument(
        "--events",
        choices=("annotations", "stim"),
        default="annotations",
        help="store events as annotations or on a 'STI 014' stim channel",
    )
    parser.add_argument("--ecg", action="store_true", help="add an ECG channel and cardiac field")
    parser.add_argument("--no-bad-channels", action="store_true")
    parser.add_argument("--dc-offset-mv", type=float, default=0.0, help="max per-channel DC offset")
    parser.add_argument(
        "--microvolts-as-volts",
        action="store_true",
        help="store microvolt numbers labelled as volts (the classic units bug)",
    )
    parser.add_argument("--overwrite", action="store_true")
    return parser


def _pink_noise(rng: Any, np: Any, n_signals: int, n_samples: int, sfreq: float) -> Any:
    """Unit-variance noise with a 1/f power spectrum above 0.5 Hz."""
    freqs = np.fft.rfftfreq(n_samples, 1.0 / sfreq)
    shape = 1.0 / np.sqrt(np.maximum(freqs, 0.5))
    shape[0] = 0.0
    spectrum = rng.standard_normal((n_signals, freqs.size)) + 1j * rng.standard_normal(
        (n_signals, freqs.size)
    )
    signals = np.fft.irfft(spectrum * shape, n=n_samples, axis=-1)
    return signals / signals.std(axis=1, keepdims=True)


def _gaussian_topography(np: Any, xyz: Any, center: Any, width: float, ref: int) -> Any:
    weights = np.exp(-np.sum((xyz - center) ** 2, axis=1) / (2 * width**2))
    return weights / weights[ref]


def _event_onsets(rng: Any, duration: float) -> list[float]:
    onsets, t = [], 3.0
    while t < duration - 3.0:
        onsets.append(round(t, 4))
        t += rng.uniform(1.0, 1.4)
    return onsets


def _blink_onsets(rng: Any, np: Any, duration: float, rate: float) -> list[float]:
    count = rng.poisson(rate * duration / 60.0)
    candidates = np.sort(rng.uniform(1.0, duration - 1.5, size=count))
    onsets: list[float] = []
    for t in candidates:
        if not onsets or t - onsets[-1] > 1.0:
            onsets.append(round(float(t), 4))
    return onsets


def simulate(args: argparse.Namespace, mne: Any) -> tuple[Any, dict[str, Any]]:
    import numpy as np

    rng = np.random.default_rng(args.seed)
    sfreq, n_samples = args.sfreq, int(round(args.duration * args.sfreq))
    times = np.arange(n_samples) / sfreq
    montage_name = default_montage_name(mne)
    montage = mne.channels.make_standard_montage(montage_name)
    positions = montage.get_positions()["ch_pos"]
    xyz = np.array([positions[name] for name in CHANNELS])
    index = {name: i for i, name in enumerate(CHANNELS)}
    uv = 1e-6

    # Spatially correlated 1/f background. A 6 cm Gaussian kernel gives the
    # 0.7-0.8 neighbour correlations that volume conduction produces on the scalp.
    distance = np.linalg.norm(xyz[:, None, :] - xyz[None, :, :], axis=-1)
    eigval, eigvec = np.linalg.eigh(np.exp(-(distance**2) / (2 * 0.06**2)))
    mixing = eigvec @ np.diag(np.sqrt(np.clip(eigval, 0.0, None)))
    eeg = 8.0 * uv * (mixing @ _pink_noise(rng, np, len(CHANNELS), n_samples, sfreq))

    # Posterior alpha with a slow amplitude envelope and slight phase diffusion.
    alpha_topo = _gaussian_topography(np, xyz, positions["Oz"], 0.05, index["Oz"])
    envelope = 1.0 + 0.5 * np.sin(2 * np.pi * 0.07 * times + rng.uniform(0, 2 * np.pi))
    phase = 2 * np.pi * args.alpha_freq * times + np.cumsum(rng.normal(0, 0.005, n_samples))
    eeg += np.outer(alpha_topo, 10.0 * uv * envelope * np.sin(phase))

    # Event-related components with trial-to-trial amplitude and latency jitter.
    onsets = _event_onsets(rng, args.duration)
    labels = np.array(["standard"] * len(onsets), dtype=object)
    n_target = max(1, round(args.target_prob * len(onsets)))
    labels[rng.choice(len(onsets), n_target, replace=False)] = "target"
    lags = np.arange(-int(0.1 * sfreq), int(0.8 * sfreq)) / sfreq
    topographies = {
        name: _gaussian_topography(np, xyz, positions[peak], spread, index[peak])
        for name, (_, _, peak, spread, _) in COMPONENTS.items()
    }
    for onset, label in zip(onsets, labels):
        samples = int(round(onset * sfreq)) + np.round(lags * sfreq).astype(int)
        for name, (latency, width, _, _, amplitude) in COMPONENTS.items():
            gain = amplitude[label] * max(0.2, rng.normal(1.0, 0.2))
            peak = latency + rng.normal(0.0, 0.015)
            wave = gain * uv * np.exp(-0.5 * ((lags - peak) / width) ** 2)
            eeg[:, samples] += np.outer(topographies[name], wave)

    # Eye blinks: 400 ms Hann-shaped deflections, 150 uV at Fp1/Fp2. The VEOG
    # channel sees the blinks at 1.3x plus some frontal brain activity.
    frontal = eeg[[index["Fp1"], index["Fp2"]]].mean(axis=0)
    eye = positions["Fpz"] + np.array([0.0, 0.03, -0.03])
    blink_topo = np.exp(-np.sum((xyz - eye) ** 2, axis=1) / (2 * 0.045**2))
    blink_topo /= blink_topo[[index["Fp1"], index["Fp2"]]].mean()
    blink_train = np.zeros(n_samples)
    blinks = _blink_onsets(rng, np, args.duration, args.blink_rate)
    shape = np.hanning(int(0.4 * sfreq))
    for onset in blinks:
        start = int(round(onset * sfreq))
        blink_train[start : start + shape.size] += 150.0 * uv * shape
    eeg += np.outer(blink_topo, blink_train)
    veog = 1.3 * blink_train + 0.5 * frontal + rng.normal(0.0, 2.0 * uv, n_samples)

    # Line noise with channel-specific gain.
    if args.line_freq > 0:
        hum = np.sin(2 * np.pi * args.line_freq * times + rng.uniform(0, 2 * np.pi))
        eeg += np.outer(4.0 * uv * rng.uniform(0.5, 1.5, len(CHANNELS)), hum)
        veog += 4.0 * uv * hum

    eeg += rng.normal(0.0, 1.0 * uv, eeg.shape)

    data = [eeg, veog[None, :]]
    names, types = list(CHANNELS), ["eeg"] * len(CHANNELS)
    names.append("VEOG")
    types.append("eog")

    truth_ecg = None
    if args.ecg:
        beats, t = [], 0.5
        while t < args.duration - 0.5:
            beats.append(t)
            t += 60.0 / 70.0 * rng.uniform(0.95, 1.05)
        qrs = np.zeros(n_samples)
        wave = np.zeros(n_samples)
        for beat in beats:
            qrs += np.exp(-0.5 * ((times - beat) / 0.012) ** 2)
            wave += 0.2 * np.exp(-0.5 * ((times - beat - 0.25) / 0.04) ** 2)
        ecg = 1000.0 * uv * (qrs + wave) + rng.normal(0.0, 20.0 * uv, n_samples)
        cardiac_topo = xyz[:, 0] / np.abs(xyz[:, 0]).max()
        data[0] = data[0] + np.outer(3.0 * uv * cardiac_topo, qrs)
        data.append(ecg[None, :])
        names.append("ECG")
        types.append("ecg")
        truth_ecg = {"channel": "ECG", "heart_rate_bpm": 70, "n_beats": len(beats)}

    if not args.no_bad_channels:
        data[0][index["FC5"]] += rng.normal(0.0, 50.0 * uv, n_samples)
        data[0][index["T8"]] = rng.normal(0.0, 0.02 * uv, n_samples)

    stacked = np.vstack(data)
    voltage_rows = [i for i, kind in enumerate(types) if kind in ("eeg", "eog", "ecg")]
    if args.dc_offset_mv > 0:
        offsets = rng.uniform(-args.dc_offset_mv, args.dc_offset_mv, len(voltage_rows))
        stacked[voltage_rows] += offsets[:, None] * 1e-3
    if args.microvolts_as_volts:
        stacked[voltage_rows] *= 1e6

    if args.events == "stim":
        stim = np.zeros((1, n_samples))
        for onset, label in zip(onsets, labels):
            start = int(round(onset * sfreq))
            stim[0, start : start + 3] = EVENT_CODES[label]
        stacked = np.vstack([stacked, stim])
        names.append("STI 014")
        types.append("stim")

    info = mne.create_info(names, sfreq, types)
    if args.line_freq > 0:
        info["line_freq"] = args.line_freq
    raw = mne.io.RawArray(stacked, info, verbose="ERROR")
    raw.set_montage(montage)
    if args.events == "annotations":
        raw.set_annotations(
            mne.Annotations(onsets, [0.0] * len(onsets), [str(label) for label in labels])
        )

    counts = {name: int(np.sum(labels == name)) for name in EVENT_CODES}
    truth = {
        "generator": {
            "script": "simulate_eeg.py",
            "seed": args.seed,
            "mne_version": mne.__version__,
            "tested_mne_version": TESTED_MNE_VERSION,
        },
        "sfreq": sfreq,
        "duration_s": args.duration,
        "n_samples": n_samples,
        "montage": montage_name,
        "channels": {kind: [n for n, t in zip(names, types) if t == kind] for kind in set(types)},
        "units": "uV_labelled_as_V" if args.microvolts_as_volts else "V",
        "dc_offset_mv": args.dc_offset_mv,
        "events": {
            "source": args.events,
            "codes": EVENT_CODES,
            "counts": counts,
            "onsets_s": {
                name: [t for t, label in zip(onsets, labels) if label == name]
                for name in EVENT_CODES
            },
        },
        "erp_components": {
            name: {
                "latency_s": latency,
                "width_s": width,
                "peak_channel": peak,
                "amplitude_uv": amplitude,
            }
            for name, (latency, width, peak, _, amplitude) in COMPONENTS.items()
        },
        "alpha": {"freq_hz": args.alpha_freq, "peak_channel": "Oz", "amplitude_uv": 10.0},
        "blinks": {
            "count": len(blinks),
            "amplitude_uv": 150.0,
            "duration_s": 0.4,
            "channels": ["Fp1", "Fp2", "VEOG"],
            "onsets_s": blinks,
        },
        "line_noise": {"freq_hz": args.line_freq, "amplitude_uv": 4.0}
        if args.line_freq > 0
        else None,
        "bad_channels": {} if args.no_bad_channels else dict(BAD_CHANNELS),
        "ecg": truth_ecg,
    }
    return raw, truth


def _validate(args: argparse.Namespace) -> str:
    fmt = FORMATS.get(Path(args.out).suffix.lower())
    if fmt is None:
        raise CliError(f"--out must end with one of {sorted(FORMATS)}")
    if args.duration < 30:
        raise CliError("--duration must be at least 30 seconds")
    if args.sfreq < 100:
        raise CliError("--sfreq must be at least 100 Hz")
    if args.line_freq and not 0 < args.line_freq < args.sfreq / 2:
        raise CliError("--line-freq must be below the Nyquist frequency")
    if not 6.0 <= args.alpha_freq <= 14.0:
        raise CliError("--alpha-freq must lie between 6 and 14 Hz")
    if not 0.0 < args.target_prob < 1.0:
        raise CliError("--target-prob must lie strictly between 0 and 1")
    return fmt


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    fmt = _validate(args)
    out = Path(args.out)
    truth_path = Path(args.truth) if args.truth else out.with_name(out.stem + "_truth.json")
    prepare_outputs(out.parent, [out, truth_path], args.overwrite)
    mne = import_mne()
    raw, truth = simulate(args, mne)
    if fmt == "fif":
        raw.save(out, overwrite=True, verbose="ERROR")
    else:
        try:
            mne.export.export_raw(out, raw, fmt=fmt, overwrite=True, verbose="ERROR")
        except (ImportError, ModuleNotFoundError) as error:
            raise CliError(
                f"exporting {fmt} needs the {EXPORT_PACKAGES[fmt]} package: "
                f"pip install {EXPORT_PACKAGES[fmt]} ({error})"
            ) from error
    truth["file"] = out.name
    write_json(truth_path, truth)
    counts = truth["events"]["counts"]
    print(
        f"wrote {out} ({fmt}, {len(raw.ch_names)} channels, {args.duration:g} s, "
        f"{counts['standard']} standard / {counts['target']} target events, "
        f"{truth['blinks']['count']} blinks) and {truth_path}"
    )
    return 0


if __name__ == "__main__":
    run_cli(main)
