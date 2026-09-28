#!/usr/bin/env python3
"""Preprocess scalp EEG reproducibly and log every decision.

Steps, in order (all recorded in <prefix>_desc-preproc_log.json):
  1. read any MNE-supported file; optional renames, channel types, drops, crop
  2. montage: keep existing positions, else a built-in or custom montage
  3. when resampling: stim-channel events -> annotations (so they survive it)
  4. notch (only if line noise reaches the pass band), band-pass, resample
  5. bad channels: flat, deviant amplitude (robust z AND ratio to median), and
     low correlation with other channels in 1 s windows (PREP-style); a quality
     gate stops the run when too many channels are bad
  6. ICA fitted on a 1 Hz high-passed copy (Picard / extended Infomax / FastICA);
     ocular components from EOG channels or frontal proxies, cardiac components
     from an ECG channel; applied to the band-passed data; blink residual measured
  7. spherical-spline interpolation of bad channels, then re-referencing
  8. outputs: cleaned raw (FIF), ICA (FIF), JSON log, HTML report

Examples:
    python preprocess_eeg.py sub-01_eeg.vhdr --out-dir derivatives/sub-01
    python preprocess_eeg.py rec.edf --out-dir out --rename-auto --auto-channel-types \\
        --l-freq 0.1 --h-freq 40 --resample 250 --reference average
    python preprocess_eeg.py rec.bdf --out-dir out --reference M1,M2 --ica-exclude 0
"""

from __future__ import annotations

import argparse
import platform
import time
import warnings
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from _common import (
    INSTALL_HINT,
    TESTED_MNE_VERSION,
    CliError,
    checked_input,
    default_montage_name,
    import_mne,
    line_noise_db,
    match_montage_names,
    parse_mapping,
    parse_name_list,
    prepare_outputs,
    recording_stem,
    robust_std,
    robust_z,
    rounded,
    run_cli,
    sha256_file,
    suggest_channel_type,
    write_json,
)

SKIP_ANNOTATIONS = ("edge", "bad_acq_skip", "boundary")
FRONTAL_PROXIES = ("Fp1", "Fp2", "Fpz", "AF7", "AF8", "AF3", "AF4")
ICA_FIT_PARAMS = {
    "picard": {"ortho": False, "extended": True},
    "infomax": {"extended": True},
    "fastica": None,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("recording", help="file (or .mff/.ds directory) readable by mne.io.read_raw")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--prefix", help="output name stem (default: from the input name)")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--no-report", action="store_true", help="skip the HTML report")

    channels = parser.add_argument_group("channels")
    channels.add_argument("--rename", help="OLD=NEW pairs, comma separated")
    channels.add_argument(
        "--rename-auto",
        action="store_true",
        help="strip 'EEG ' prefixes / '-REF'-style suffixes and match montage spelling",
    )
    channels.add_argument("--channel-types", help="NAME=TYPE pairs, e.g. VEOG=eog,ECG=ecg")
    channels.add_argument(
        "--auto-channel-types",
        action="store_true",
        help="type EEG-typed channels named like EOG/ECG/EMG/stim/... accordingly",
    )
    channels.add_argument("--drop", help="channels to drop, comma separated")
    channels.add_argument(
        "--montage",
        default="auto",
        help="auto (keep positions, else colin27_1005), none, a built-in name, or a file",
    )
    channels.add_argument("--crop", nargs=2, type=float, metavar=("TMIN", "TMAX"))

    filters = parser.add_argument_group("filtering")
    filters.add_argument("--l-freq", type=float, default=0.1, help="high-pass Hz; 0 disables")
    filters.add_argument("--h-freq", type=float, default=40.0, help="low-pass Hz; 0 disables")
    filters.add_argument("--line-freq", default="auto", help="auto, 50, 60, or none")
    filters.add_argument("--resample", type=float, default=0.0, help="new sampling rate; 0 keeps")

    bads = parser.add_argument_group("bad channels")
    bads.add_argument("--bads", help="channels known to be bad, comma separated")
    bads.add_argument("--no-detect-bads", action="store_true")
    bads.add_argument("--flat-uv", type=float, default=0.5, help="robust SD below this is flat")
    bads.add_argument("--deviation-z", type=float, default=5.0)
    bads.add_argument("--deviation-ratio", type=float, default=2.0)
    bads.add_argument("--corr-threshold", type=float, default=0.4)
    bads.add_argument(
        "--corr-bad-fraction",
        type=float,
        default=0.2,
        help="fraction of 1 s windows below --corr-threshold that marks a channel bad "
        "(PREP uses 0.01 inside its robust-reference loop; 0.2 spares channels with "
        "intermittent muscle activity)",
    )
    bads.add_argument("--max-bad-fraction", type=float, default=0.25)

    ica = parser.add_argument_group("ICA")
    ica.add_argument("--no-ica", action="store_true")
    ica.add_argument("--ica-method", choices=("auto", "picard", "infomax", "fastica"), default="auto")
    ica.add_argument("--ica-components", default="0.99", help="int count or float variance fraction")
    ica.add_argument("--ica-seed", type=int, default=97)
    ica.add_argument("--ica-reject-uv", type=float, default=500.0, help="p2p limit for ICA training; 0 off")
    ica.add_argument("--eog-channels", help="EOG (or frontal proxy) channels for blink detection")
    ica.add_argument("--eog-threshold", type=float, default=3.0, help="z threshold (find_bads_eog)")
    ica.add_argument("--eog-min-r", type=float, default=0.3, help="minimum |r| with the EOG signal")
    ica.add_argument("--max-eog-components", type=int, default=3)
    ica.add_argument("--max-ecg-components", type=int, default=2)
    ica.add_argument("--ica-muscle", action="store_true", help="also exclude find_bads_muscle hits")
    ica.add_argument("--ica-exclude", help="component indices to exclude in addition")

    reference = parser.add_argument_group("interpolation and reference")
    reference.add_argument("--no-interpolate", action="store_true")
    reference.add_argument(
        "--reference", default="average", help="average, average-proj, none, or channel names"
    )
    return parser


class Pipeline:
    """Holds the recording, the log, and the report figures while steps run."""

    def __init__(self, args: argparse.Namespace, mne: Any, path: Path, stem: str) -> None:
        import numpy as np

        self.args, self.mne, self.np, self.path, self.stem = args, mne, np, path, stem
        self.warnings: list[str] = []
        self.figures: list[tuple[str, Any]] = []
        self.log: dict[str, Any] = {
            "status": "running",
            "input": {"name": path.name, "sha256": sha256_file(path)},
            "software": {
                "mne": mne.__version__,
                "tested_mne": TESTED_MNE_VERSION,
                "numpy": np.__version__,
                "python": platform.python_version(),
            },
            "parameters": {k: v for k, v in sorted(vars(args).items()) if k != "recording"},
        }
        self.raw: Any = None
        self.ica: Any = None
        self.raw_ica: Any = None
        self.eog_scores: Any = None

    # -- helpers -----------------------------------------------------------

    def _capture(self, caught: list[warnings.WarningMessage]) -> None:
        for item in caught:
            text = str(item.message).splitlines()[0][:240]
            if "naming conventions" not in text and text not in self.warnings:
                self.warnings.append(text)

    def names_of(self, kind: str, *, good: bool = False) -> list[str]:
        bads = set(self.raw.info["bads"])
        return [
            name
            for name, t in zip(self.raw.ch_names, self.raw.get_channel_types())
            if t == kind and not (good and name in bads)
        ]

    def has_position(self, name: str) -> bool:
        loc = self.raw.info["chs"][self.raw.ch_names.index(name)]["loc"][:3]
        return bool(self.np.all(self.np.isfinite(loc)) and self.np.any(loc != 0))

    def eeg_psd(self) -> tuple[Any, Any]:
        picks = self.names_of("eeg", good=True)
        spectrum = self.raw.compute_psd(
            method="welch",
            picks=picks,
            fmax=min(100.0, self.raw.info["sfreq"] / 2),
            n_fft=int(min(4 * self.raw.info["sfreq"], self.raw.n_times)),
            reject_by_annotation=True,
        )
        psd, freqs = spectrum.get_data(return_freqs=True)
        return freqs, self.np.median(psd, axis=0)

    # -- steps -------------------------------------------------------------

    def read(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                self.raw = self.mne.io.read_raw(self.path, preload=True)
            except Exception as error:
                raise CliError(f"MNE could not read {self.path.name}: {error}") from error
        self._capture(caught)
        raw = self.raw
        self.log["input"].update(
            reader=type(raw).__name__,
            sfreq_hz=raw.info["sfreq"],
            duration_s=rounded(raw.n_times / raw.info["sfreq"], 3),
            n_channels=len(raw.ch_names),
            bads_in_file=list(raw.info["bads"]),
        )

    def fix_channels(self) -> None:
        args, raw, mne = self.args, self.raw, self.mne
        section: dict[str, Any] = {"renamed": {}, "types_set": {}, "dropped": []}
        renames = parse_mapping(args.rename, what="--rename")
        missing = sorted(set(renames) - set(raw.ch_names))
        if missing:
            raise CliError(f"--rename names not in the recording: {missing}")
        if args.rename_auto:
            montage_name = args.montage if args.montage not in ("auto", "none") else None
            if montage_name is None or Path(montage_name).exists():
                montage_name = default_montage_name(mne)
            montage = mne.channels.make_standard_montage(montage_name)
            eeg = [n for n in self.names_of("eeg") if n not in renames and not suggest_channel_type(n)]
            automatic, _ = match_montage_names(eeg, montage.ch_names)
            taken = set(raw.ch_names) - set(automatic)
            renames.update({old: new for old, new in automatic.items() if new not in taken})
        if renames:
            raw.rename_channels(renames)
            section["renamed"] = renames

        types = parse_mapping(args.channel_types, what="--channel-types")
        if args.auto_channel_types:
            for name, kind in zip(raw.ch_names, raw.get_channel_types()):
                guess = suggest_channel_type(name) if kind in ("eeg", "misc") else None
                if guess and guess != kind:
                    types.setdefault(name, guess)
        unknown = sorted(set(types) - set(raw.ch_names))
        if unknown:
            raise CliError(f"--channel-types names not in the recording: {unknown}")
        if types:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                raw.set_channel_types(types)
            self._capture(caught)
            section["types_set"] = types

        drop = parse_name_list(args.drop)
        if drop:
            absent = sorted(set(drop) - set(raw.ch_names))
            if absent:
                raise CliError(f"--drop names not in the recording: {absent}")
            raw.drop_channels(drop)
            section["dropped"] = drop

        if args.crop:
            tmin, tmax = args.crop
            if not 0 <= tmin < tmax:
                raise CliError("--crop needs 0 <= TMIN < TMAX")
            raw.crop(tmin, min(tmax, raw.times[-1]))
            section["crop_s"] = [tmin, min(tmax, raw.times[-1])]
        if not self.names_of("eeg"):
            raise CliError("no EEG channels left; check --channel-types / --drop")
        self.log["channels"] = section

    def set_montage(self) -> None:
        args, raw, mne = self.args, self.raw, self.mne
        eeg = self.names_of("eeg")
        section: dict[str, Any] = {"requested": args.montage}
        if args.montage == "none":
            section["applied"] = None
        elif args.montage == "auto" and all(self.has_position(n) for n in eeg):
            section["applied"] = "existing positions"
        else:
            if args.montage != "auto" and Path(args.montage).exists():
                montage = mne.channels.read_custom_montage(args.montage)
                section["applied"] = Path(args.montage).name
            else:
                name = default_montage_name(mne) if args.montage == "auto" else args.montage
                try:
                    with warnings.catch_warnings(record=True) as caught:
                        warnings.simplefilter("always")
                        montage = mne.channels.make_standard_montage(name)
                    self._capture(caught)
                except ValueError as error:
                    raise CliError(f"unknown montage {name!r}: {error}") from error
                section["applied"] = name
            raw.set_montage(montage, match_case=False, on_missing="ignore")
        section["without_position"] = [n for n in eeg if not self.has_position(n)]
        if section["without_position"]:
            self.warnings.append(
                f"{len(section['without_position'])} EEG channels have no position: "
                f"{section['without_position'][:8]} (no interpolation or topomaps for them)"
            )
        self.log["montage"] = section

    def events_to_annotations(self) -> None:
        raw, mne, np = self.raw, self.mne, self.np
        stim = self.names_of("stim")
        section: dict[str, Any] = {"stim_channels": stim, "converted": 0}
        needs = bool(stim) and self.args.resample and self.args.resample < raw.info["sfreq"]
        if needs:
            channel = next((c for c in ("STI101", "STI 014") if c in stim), stim[0])
            events = mne.find_events(raw, stim_channel=channel, shortest_event=1, verbose="ERROR")
            existing = [
                d for d in raw.annotations.description
                if not str(d).lower().startswith(("bad", "edge", "boundary"))
            ]
            if len(events) and not existing:
                orig_time = raw.info["meas_date"]
                annotations = mne.annotations_from_events(
                    events,
                    raw.info["sfreq"],
                    first_samp=0 if orig_time is not None else raw.first_samp,
                    orig_time=orig_time,
                )
                raw.set_annotations(raw.annotations + annotations)
                section["converted"] = int(len(events))
                section["codes"] = {str(c): int(n) for c, n in zip(*np.unique(events[:, 2], return_counts=True))}
            elif existing:
                section["note"] = "annotations already hold events; stim channel not converted"
            raw.drop_channels(stim)
            section["dropped_after_conversion"] = stim
        self.log["events"] = section

    def filter(self) -> None:
        args, raw, np = self.args, self.raw, self.np
        sfreq = raw.info["sfreq"]
        nyquist = sfreq / 2
        l_freq = args.l_freq if args.l_freq > 0 else None
        h_freq = args.h_freq if args.h_freq > 0 else None
        if h_freq is not None and h_freq >= nyquist:
            raise CliError(f"--h-freq {h_freq} must be below Nyquist ({nyquist:g} Hz)")
        picks = [n for kind in ("eeg", "eog") for n in self.names_of(kind)]
        section: dict[str, Any] = {"picks": "eeg+eog", "design": "FIR firwin, hamming, zero-phase"}

        freqs, before = self.eeg_psd()
        self.psd_before = (freqs, before)
        line = args.line_freq.strip().lower()
        if line == "auto":
            heights = {f0: line_noise_db(freqs, before, f0) for f0 in (50.0, 60.0) if f0 + 6 < nyquist}
            present = {f0: h for f0, h in heights.items() if h is not None and h >= 6.0}
            f0 = max(present, key=present.get) if present else None
            section["line_noise_db"] = {str(int(k)): rounded(v, 1) for k, v in heights.items()}
        elif line == "none":
            f0 = None
        else:
            try:
                f0 = float(line)
            except ValueError as error:
                raise CliError("--line-freq must be auto, none, or a frequency") from error
        section["line_freq_hz"] = f0
        if f0:
            h_trans = min(max(0.25 * h_freq, 2.0), nyquist - h_freq) if h_freq else 0.0
            stop = h_freq + h_trans if h_freq else nyquist
            notches = np.arange(f0, min(stop, nyquist - 1.0), f0)
            if notches.size:
                raw.notch_filter(notches, picks=picks, skip_by_annotation=SKIP_ANNOTATIONS)
                section["notch_hz"] = notches.tolist()
            else:
                section["notch_hz"] = []
                section["notch_note"] = f"{f0:g} Hz lies in the low-pass stop band; no notch needed"
        if l_freq or h_freq:
            raw.filter(l_freq, h_freq, picks=picks, skip_by_annotation=SKIP_ANNOTATIONS)
        section["l_freq_hz"], section["h_freq_hz"] = l_freq, h_freq
        if l_freq:
            section["l_trans_bandwidth_hz"] = min(max(0.25 * l_freq, 2.0), l_freq)
        if h_freq:
            section["h_trans_bandwidth_hz"] = min(max(0.25 * h_freq, 2.0), nyquist - h_freq)

        if args.resample:
            if args.resample >= sfreq:
                self.warnings.append(f"--resample {args.resample:g} >= {sfreq:g} Hz; skipped")
            else:
                if h_freq and h_freq > args.resample / 3:
                    self.warnings.append(
                        f"low-pass {h_freq:g} Hz is above a third of the new rate {args.resample:g} Hz"
                    )
                raw.resample(args.resample)
                section["resampled_hz"] = [sfreq, args.resample]
        self.log["filtering"] = section

    def detect_bads(self) -> None:
        args, raw, np = self.args, self.raw, self.np
        manual = parse_name_list(args.bads)
        unknown = sorted(set(manual) - set(raw.ch_names))
        if unknown:
            raise CliError(f"--bads names not in the recording: {unknown}")
        section: dict[str, Any] = {"in_file": list(raw.info["bads"]), "manual": manual, "detected": {}}
        eeg = [n for n in self.names_of("eeg") if n not in raw.info["bads"] and n not in manual]
        if not args.no_detect_bads and len(eeg) >= 4:
            section["detected"] = self._detect(eeg)
        final = sorted(set(raw.info["bads"]) | set(manual) | set(section["detected"]))
        n_eeg = len(self.names_of("eeg"))
        eeg_bads = [b for b in final if b in self.names_of("eeg")]
        section["final"] = final
        section["fraction_of_eeg"] = rounded(len(eeg_bads) / n_eeg, 3)
        self.log["bad_channels"] = section
        if len(eeg_bads) / n_eeg > args.max_bad_fraction:
            self.log["status"] = "failed_quality_gate"
            raise CliError(
                f"{len(eeg_bads)}/{n_eeg} EEG channels flagged bad (> --max-bad-fraction "
                f"{args.max_bad_fraction}); check units, reference and contact quality with "
                f"inspect_recording.py before retrying"
            )
        raw.info["bads"] = final

    def _detect(self, eeg: list[str]) -> dict[str, Any]:
        args, raw, np = self.args, self.raw, self.np
        data = raw.get_data(picks=eeg, reject_by_annotation="omit")
        sd_uv = robust_std(data, axis=1) * 1e6
        flat = sd_uv < args.flat_uv
        live = np.flatnonzero(~flat)
        found: dict[str, Any] = {}
        for i in np.flatnonzero(flat):
            found[eeg[i]] = {"reasons": ["flat"], "robust_sd_uv": rounded(sd_uv[i], 3)}
        if live.size >= 4:
            z = robust_z(np.log(sd_uv[live]))
            ratio = sd_uv[live] / np.median(sd_uv[live])
            for i, zi, ri in zip(live, z, ratio):
                if zi > args.deviation_z and ri > args.deviation_ratio:
                    found[eeg[i]] = {
                        "reasons": ["deviation"],
                        "robust_sd_uv": rounded(sd_uv[i], 3),
                        "robust_z": rounded(zi, 2),
                        "ratio_to_median": rounded(ri, 2),
                    }
        if live.size >= 8:
            low = self._low_correlation_fraction(data[live])
            for i, fraction in zip(live, low):
                if fraction > args.corr_bad_fraction:
                    entry = found.setdefault(
                        eeg[i], {"reasons": [], "robust_sd_uv": rounded(sd_uv[i], 3)}
                    )
                    entry["reasons"].append("low_correlation")
                    entry["low_corr_window_fraction"] = rounded(fraction, 3)
        self.sd_uv = dict(zip(eeg, sd_uv))
        return found

    def _low_correlation_fraction(self, data: Any) -> Any:
        """Fraction of 1 s windows where a channel's 98th-percentile |r| with the
        other channels is below --corr-threshold (the PREP correlation criterion)."""
        np = self.np
        win = int(round(self.raw.info["sfreq"]))
        n_win = data.shape[1] // win
        low = np.zeros(data.shape[0])
        if n_win == 0:
            return low
        for start in range(0, n_win, 256):
            stop = min(n_win, start + 256)
            block = data[:, start * win : stop * win].reshape(data.shape[0], stop - start, win)
            block = block - block.mean(axis=2, keepdims=True)
            norm = np.linalg.norm(block, axis=2, keepdims=True)
            z = np.divide(block, norm, out=np.zeros_like(block), where=norm > 0)
            corr = np.abs(np.einsum("iwt,jwt->wij", z, z))
            idx = np.arange(data.shape[0])
            corr[:, idx, idx] = np.nan
            q98 = np.nanpercentile(corr, 98, axis=2)
            low += (q98 < self.args.corr_threshold).sum(axis=0)
        return low / n_win

    def run_ica(self) -> None:
        args, raw, mne, np = self.args, self.raw, self.mne, self.np
        good = self.names_of("eeg", good=True)
        section: dict[str, Any] = {"applied": False}
        self.log["ica"] = section
        if args.no_ica or len(good) < 4:
            section["note"] = "disabled" if args.no_ica else "fewer than 4 good EEG channels"
            return

        method = args.ica_method
        if method == "auto":
            try:
                import picard  # noqa: F401

                method = "picard"
            except ImportError:
                method = "infomax"
                self.warnings.append("python-picard not installed; using extended Infomax")
        n_components: int | float = (
            float(args.ica_components) if "." in args.ica_components else int(args.ica_components)
        )
        if isinstance(n_components, int) and n_components >= len(good):
            n_components = len(good) - 1
            self.warnings.append(f"--ica-components clamped to {n_components} (good channels - 1)")
        if isinstance(n_components, float) and not 0 < n_components < 1:
            raise CliError("--ica-components as a fraction must lie between 0 and 1")

        filter_picks = [n for kind in ("eeg", "eog") for n in self.names_of(kind)]
        raw_ica = raw.copy()
        if not args.l_freq or args.l_freq < 1.0:
            raw_ica.filter(1.0, None, picks=filter_picks, skip_by_annotation=SKIP_ANNOTATIONS)
        decim = max(1, int(round(raw.info["sfreq"] / 250.0)))
        reject = {"eeg": args.ica_reject_uv * 1e-6} if args.ica_reject_uv > 0 else None
        ica = mne.preprocessing.ICA(
            n_components=n_components,
            method=method,
            fit_params=ICA_FIT_PARAMS[method],
            random_state=args.ica_seed,
            max_iter="auto",
        )
        started = time.perf_counter()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                ica.fit(raw_ica, picks=good, decim=decim, reject=reject, reject_by_annotation=True)
            except ImportError as error:
                raise CliError(f"ICA method {method!r} needs a package: {error}; {INSTALL_HINT}") from error
        self._capture(caught)
        section.update(
            method=method,
            fit_params=ICA_FIT_PARAMS[method],
            seed=args.ica_seed,
            n_components=int(ica.n_components_),
            n_iterations=int(getattr(ica, "n_iter_", 0) or 0),
            fit_seconds=rounded(time.perf_counter() - started, 2),
            decim=decim,
            highpass_for_fit_hz=max(1.0, args.l_freq or 0.0),
            explained_variance=rounded(ica.get_explained_variance_ratio(raw_ica)["eeg"], 4),
        )

        excluded: dict[int, list[str]] = {}
        eog_names = parse_name_list(args.eog_channels) or self.names_of("eog", good=True)
        proxy = False
        if not eog_names:
            eog_names = [c for c in FRONTAL_PROXIES if c in good][:2]
            proxy = bool(eog_names)
        missing = sorted(set(eog_names) - set(raw.ch_names))
        if missing:
            raise CliError(f"--eog-channels not in the recording: {missing}")
        section["eog"] = {"channels": eog_names, "frontal_proxy": proxy, "components": {}}
        if eog_names:
            indices, scores = ica.find_bads_eog(
                raw_ica, ch_name=eog_names, threshold=args.eog_threshold, measure="zscore"
            )
            self.eog_scores = scores
            strength = np.max(np.abs(np.atleast_2d(np.asarray(scores))), axis=0)
            chosen = sorted(
                (i for i in indices if strength[i] >= args.eog_min_r),
                key=lambda i: -strength[i],
            )[: args.max_eog_components]
            for i in chosen:
                excluded.setdefault(int(i), []).append("eog")
                section["eog"]["components"][int(i)] = rounded(strength[i], 3)
        else:
            self.warnings.append("no EOG channel or frontal proxy; ocular components not searched")

        ecg_names = self.names_of("ecg", good=True)
        if ecg_names:
            indices, scores = ica.find_bads_ecg(raw_ica, ch_name=ecg_names[0], method="ctps")
            strength = np.abs(np.asarray(scores))
            chosen = sorted(indices, key=lambda i: -strength[i])[: args.max_ecg_components]
            section["ecg"] = {"channel": ecg_names[0], "components": {int(i): rounded(strength[i], 3) for i in chosen}}
            for i in chosen:
                excluded.setdefault(int(i), []).append("ecg")

        if args.ica_muscle:
            try:
                indices, scores = ica.find_bads_muscle(raw_ica)
            except Exception as error:  # needs channel positions
                self.warnings.append(f"find_bads_muscle skipped: {str(error)[:160]}")
            else:
                section["muscle"] = {int(i): rounded(scores[i], 3) for i in indices}
                for i in indices:
                    excluded.setdefault(int(i), []).append("muscle")

        manual = [int(v) for v in parse_name_list(args.ica_exclude)]
        bad_index = [i for i in manual if not 0 <= i < ica.n_components_]
        if bad_index:
            raise CliError(f"--ica-exclude indices out of range 0..{ica.n_components_ - 1}: {bad_index}")
        for i in manual:
            excluded.setdefault(i, []).append("manual")

        ica.exclude = sorted(excluded)
        section["excluded"] = {int(i): reasons for i, reasons in sorted(excluded.items())}
        blink_before = self._blink_amplitude(eog_names, good)
        ica.apply(raw)
        blink_after = self._blink_amplitude(eog_names, good, events=self._blink_events)
        section["applied"] = True
        section["blink_p2p_uv"] = {"before": blink_before, "after": blink_after}
        if blink_before and blink_after is not None:
            reduction = 1.0 - blink_after / blink_before
            section["blink_reduction"] = rounded(reduction, 3)
            ocular = [i for i, reasons in excluded.items() if "eog" in reasons]
            if ocular and reduction < 0.5:
                self.warnings.append(
                    f"excluded EOG components {ocular} reduced the blink-locked amplitude by only "
                    f"{reduction:.0%}; they may not be ocular (e.g. eyes-closed data) - review them"
                )
        self.ica, self.raw_ica = ica, raw_ica

    _blink_events: Any = None

    def _blink_amplitude(self, eog: list[str], good: list[str], events: Any = None) -> float | None:
        """Peak-to-peak (uV) of the blink-locked average at the most affected frontal channel."""
        mne, np, raw = self.mne, self.np, self.raw
        frontal = [c for c in FRONTAL_PROXIES if c in good]
        if not eog or not frontal:
            return None
        if events is None:
            try:
                events = mne.preprocessing.find_eog_events(raw, ch_name=eog[0], verbose="ERROR")
            except Exception as error:
                self.warnings.append(f"blink detection failed: {str(error)[:160]}")
                return None
            if len(events):
                # find_eog_events also fires on background peaks; keep detections at
                # least half as large as the typical (90th percentile) blink.
                trace = mne.filter.filter_data(
                    raw.get_data(picks=eog[0])[0], raw.info["sfreq"], 1.0, 10.0, verbose="ERROR"
                )
                size = np.abs(trace[events[:, 0] - raw.first_samp])
                events = events[size >= 0.5 * np.percentile(size, 90)]
            self._blink_events = events
            self.log.setdefault("ica", {})["blink_events_used"] = int(len(events))
        if events is None or len(events) < 3:
            return None
        epochs = mne.Epochs(
            raw, events, tmin=-0.5, tmax=0.5, picks=frontal, baseline=(None, -0.3),
            reject_by_annotation=True, preload=True, verbose="ERROR",
        )
        if len(epochs) < 3:
            return None
        average = epochs.average().get_data()
        return rounded(float(np.ptp(average, axis=1).max() * 1e6), 2)

    def interpolate(self) -> None:
        raw = self.raw
        eeg_bads = [b for b in raw.info["bads"] if b in self.names_of("eeg")]
        section: dict[str, Any] = {"interpolated": [], "left_bad": []}
        if eeg_bads and not self.args.no_interpolate:
            no_position = [b for b in eeg_bads if not self.has_position(b)]
            to_fix = [b for b in eeg_bads if b not in no_position]
            if to_fix:
                raw.interpolate_bads(reset_bads=True, mode="accurate", exclude=no_position)
                section["interpolated"] = to_fix
            section["left_bad"] = no_position
        else:
            section["left_bad"] = eeg_bads
        self.log["interpolation"] = section

    def rereference(self) -> None:
        raw, choice = self.raw, self.args.reference.strip()
        section: dict[str, Any] = {"requested": choice}
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            if choice.lower() == "none":
                section["applied"] = None
            elif choice.lower() == "average":
                raw.set_eeg_reference("average", projection=False)
                section["applied"] = "average (applied)"
            elif choice.lower() == "average-proj":
                raw.set_eeg_reference("average", projection=True)
                section["applied"] = "average (projector, not applied)"
            else:
                channels = parse_name_list(choice)
                missing = sorted(set(channels) - set(raw.ch_names))
                if missing:
                    raise CliError(f"--reference channels not in the recording: {missing}")
                raw.set_eeg_reference(ref_channels=channels, projection=False)
                section["applied"] = channels
        self._capture(caught)
        section["excluded_bads"] = [b for b in raw.info["bads"] if b in self.names_of("eeg")]
        self.log["reference"] = section

    # -- outputs -------------------------------------------------------------

    def make_figures(self) -> None:
        import matplotlib.pyplot as plt

        np = self.np
        freqs_a, after = self.eeg_psd()
        freqs_b, before = self.psd_before
        fig, ax = plt.subplots(figsize=(7, 3.6), layout="constrained")
        ax.plot(freqs_b, 10 * np.log10(before * 1e12), color="#9aa5b1", lw=1.4, label="before")
        ax.plot(freqs_a, 10 * np.log10(after * 1e12), color="#1f5fbf", lw=1.6, label="after")
        ax.set(xlabel="Frequency (Hz)", ylabel="Median PSD (dB re 1 µV²/Hz)",
               title="EEG spectrum before and after preprocessing")
        ax.legend(frameon=False)
        ax.grid(alpha=0.25)
        self.figures.append(("Spectrum before/after", fig))

        sd = getattr(self, "sd_uv", None)
        if sd:
            names = list(sd)
            detected = self.log["bad_channels"]["detected"]
            fig, ax = plt.subplots(figsize=(max(7, 0.22 * len(names)), 3.4), layout="constrained")
            colors = ["#d64545" if n in detected else "#1f5fbf" for n in names]
            ax.bar(range(len(names)), [sd[n] for n in names], color=colors)
            ax.set_xticks(range(len(names)), names, rotation=90, fontsize=7)
            ax.set_yscale("log")
            ax.set(ylabel="Robust SD (µV)", title="Channel amplitude (red = flagged bad)")
            ax.grid(axis="y", alpha=0.25)
            self.figures.append(("Bad-channel screen", fig))

    def save(self, outputs: dict[str, Path]) -> None:
        import html

        mne = self.mne
        self.raw.save(outputs["clean"], overwrite=True, verbose="ERROR")
        written = {"clean": outputs["clean"].name}
        if self.ica is not None:
            self.ica.save(outputs["ica"], overwrite=True, verbose="ERROR")
            written["ica"] = outputs["ica"].name
        if not self.args.no_report:
            import matplotlib.pyplot as plt

            self.make_figures()
            report = mne.Report(title=f"EEG preprocessing: {self.stem}", verbose="ERROR")
            rows = "".join(
                f"<tr><th style='text-align:left;padding-right:1em'>{html.escape(k)}</th>"
                f"<td>{html.escape(str(v))}</td></tr>"
                for k, v in self._summary().items()
            )
            report.add_html(f"<table>{rows}</table>", title="Summary")
            for title, fig in self.figures:
                report.add_figure(fig, title=title)
                plt.close(fig)
            if self.ica is not None:
                picks = list(self.ica.exclude[:6]) or list(range(min(3, self.ica.n_components_)))
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    report.add_ica(
                        self.ica, title="ICA", inst=self.raw_ica, picks=picks,
                        eog_scores=self.eog_scores, n_jobs=None,
                    )
            report.add_raw(self.raw, title="Cleaned data", psd=False)
            report.save(outputs["report"], open_browser=False, overwrite=True, verbose="ERROR")
            written["report"] = outputs["report"].name
        self.log["outputs"] = written

    def _summary(self) -> dict[str, Any]:
        log = self.log
        ica = log.get("ica", {})
        return {
            "Input": log["input"]["name"],
            "MNE": log["software"]["mne"],
            "Filter": f"{log['filtering']['l_freq_hz']}-{log['filtering']['h_freq_hz']} Hz, "
            f"notch {log['filtering'].get('notch_hz') or 'none'}",
            "Montage": log["montage"].get("applied"),
            "Bad channels": ", ".join(log["bad_channels"]["final"]) or "none",
            "Interpolated": ", ".join(log["interpolation"]["interpolated"]) or "none",
            "ICA": f"{ica.get('method')} ({ica.get('n_components')} components), "
            f"excluded {ica.get('excluded')}" if ica.get("applied") else ica.get("note"),
            "Blink p2p before/after (µV)": ica.get("blink_p2p_uv"),
            "Reference": log["reference"].get("applied"),
            "Warnings": len(self.warnings),
        }


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not 0 < args.max_bad_fraction <= 1:
        raise CliError("--max-bad-fraction must lie in (0, 1]")
    if args.l_freq and args.h_freq and args.l_freq >= args.h_freq:
        raise CliError("--l-freq must be below --h-freq")
    path = checked_input(args.recording)
    stem = recording_stem(path, args.prefix)
    out_dir = Path(args.out_dir)
    outputs = {
        "clean": out_dir / f"{stem}_desc-clean_eeg.fif",
        "ica": out_dir / f"{stem}_ica.fif",
        "log": out_dir / f"{stem}_desc-preproc_log.json",
        "report": out_dir / f"{stem}_desc-preproc_report.html",
    }
    prepare_outputs(out_dir, outputs.values(), args.overwrite)
    mne = import_mne()
    pipeline = Pipeline(args, mne, path, stem)
    try:
        pipeline.read()
        pipeline.fix_channels()
        pipeline.set_montage()
        pipeline.events_to_annotations()
        pipeline.filter()
        pipeline.detect_bads()
        pipeline.run_ica()
        pipeline.interpolate()
        pipeline.rereference()
        pipeline.save(outputs)
        pipeline.log["status"] = "ok"
    finally:
        pipeline.log["warnings"] = pipeline.warnings
        if pipeline.log["status"] == "running":
            pipeline.log["status"] = "failed"
        write_json(outputs["log"], pipeline.log)

    log = pipeline.log
    ica = log["ica"]
    print(f"saved {outputs['clean']} (+ ICA, log{'' if args.no_report else ', report'})")
    print(f"  bad channels: {log['bad_channels']['final'] or 'none'}; "
          f"interpolated: {log['interpolation']['interpolated'] or 'none'}")
    if ica.get("applied"):
        reduction = ica.get("blink_reduction")
        print(f"  ICA {ica['method']}: {ica['n_components']} components, excluded "
              f"{ica['excluded'] or 'none'}; blink reduction "
              f"{'n/a' if reduction is None else f'{reduction:.0%}'}")
    print(f"  reference: {log['reference']['applied']}; warnings: {len(pipeline.warnings)}")
    return 0


if __name__ == "__main__":
    run_cli(main)
