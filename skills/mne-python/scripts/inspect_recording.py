#!/usr/bin/env python3
"""Triage an EEG recording before analysis: what is in it, and what looks wrong.

Opens any format MNE reads (FIF, EDF/BDF, BrainVision, EEGLAB, EGI .mff, CNT,
GDF, ...) read-only and reports channels by type, sampling rate, duration,
acquisition filters, channel names that look like EOG/ECG/stim but are typed as
EEG, the built-in montages that best match the channel names (with the renames
that fix mismatches), annotations and stim-channel events, a units sanity check
(microvolts stored as volts is the most common silent error), flat,
extreme-amplitude, clipped and non-finite channels, 50/60 Hz line noise, and
concrete next steps. No paths, measurement dates or subject_info are printed.

Examples:
    python inspect_recording.py sub-01_task-rest_eeg.edf
    python inspect_recording.py recording.vhdr --json triage.json
    python inspect_recording.py raw.fif --max-seconds 300 --format json
"""

from __future__ import annotations

import argparse
import warnings
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from _common import (
    VOLTAGE_TYPES,
    CliError,
    checked_input,
    import_mne,
    line_noise_db,
    match_montage_names,
    robust_std,
    robust_z,
    rounded,
    run_cli,
    suggest_channel_type,
    to_jsonable,
    units_verdict,
    write_json,
)

FLAT_UV = 0.5
# A channel is "extreme" only when it is a robust outlier AND more than twice the
# median amplitude: when channels are very similar, z-scores alone flag the blink
# (Fp1/Fp2) and alpha (O1/O2) channels that merely carry the most brain signal.
EXTREME_Z = 5.0
EXTREME_RATIO = 2.0
CLIP_FRACTION = 0.005
LINE_DB = 6.0
# Montages that describe positions rather than a vendor cap win ties in name matching.
GENERIC_MONTAGES = (
    "colin27_1005", "standard_1005", "colin27_1020", "standard_1020",
    "fsaverage_1005", "spherical_1005",
)  # fmt: skip
PLACEHOLDERS = {"", "x", "xx", "unknown", "anonymous", "n/a", "none", "0"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("recording", help="file (or .mff/.ds directory) readable by mne.io.read_raw")
    parser.add_argument(
        "--max-seconds",
        type=float,
        default=120.0,
        help="seconds of data used for the signal-quality checks (default 120)",
    )
    parser.add_argument("--montage", help="also score this built-in montage name")
    parser.add_argument("--json", dest="json_path", help="write the full report as JSON")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="stdout format")
    return parser


def _read(mne: Any, path: Path) -> tuple[Any, list[str]]:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            raw = mne.io.read_raw(path, preload=False)
        except Exception as error:  # readers raise many types; report them uniformly
            raise CliError(f"MNE could not read {path.name}: {error}") from error
    notes = sorted(
        {
            str(item.message).splitlines()[0][:200]
            for item in caught
            if "naming conventions" not in str(item.message)
        }
    )
    return raw, notes


def _montage_scores(mne: Any, eeg_names: list[str], extra: str | None) -> list[dict[str, Any]]:
    names = list(mne.channels.get_builtin_montages())
    if extra and extra not in names:
        names.append(extra)
    scores = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for name in names:
            try:
                montage = mne.channels.make_standard_montage(name)
            except Exception as error:
                if name == extra:
                    raise CliError(f"unknown montage {extra!r}: {error}") from error
                continue
            renames, unmatched = match_montage_names(eeg_names, montage.ch_names)
            matched = len(eeg_names) - len(unmatched)
            scores.append(
                {
                    "montage": name,
                    "matched": matched,
                    "fraction": rounded(matched / len(eeg_names), 3),
                    "montage_size": len(montage.ch_names),
                    "renames": renames,
                    "unmatched": unmatched,
                }
            )
    def rank(item: dict[str, Any]) -> tuple:
        name = item["montage"]
        generic = GENERIC_MONTAGES.index(name) if name in GENERIC_MONTAGES else len(GENERIC_MONTAGES)
        return (-item["matched"], generic, item["montage_size"], name)

    scores.sort(key=rank)
    return scores


def _identifying_subject_info(info: Any) -> bool:
    """True when subject_info holds more than reader placeholders ('X', sex 0)."""
    subject = info.get("subject_info") or {}
    for key, value in subject.items():
        if key == "sex" or value is None:
            continue
        if str(value).strip().lower() not in PLACEHOLDERS:
            return True
    return False


def _stim_events(mne: Any, raw: Any, stim: list[str]) -> dict[str, Any] | None:
    if not stim:
        return None
    channel = next((name for name in ("STI101", "STI 014") if name in stim), stim[0])
    try:
        events = mne.find_events(raw, stim_channel=channel, shortest_event=1, verbose="ERROR")
    except Exception as error:
        return {"channel": channel, "error": str(error)[:200]}
    counts = Counter(int(code) for code in events[:, 2])
    return {
        "channel": channel,
        "n_events": int(len(events)),
        "codes": {str(code): count for code, count in sorted(counts.items())},
    }


def _quality(mne: Any, raw: Any, picks: list[str], seconds: float) -> dict[str, Any]:
    import numpy as np

    sfreq = raw.info["sfreq"]
    tmax = min(seconds, raw.times[-1])
    segment = raw.copy().pick(picks).crop(0.0, tmax).load_data()
    data = segment.get_data()
    finite_rows = np.all(np.isfinite(data), axis=1)
    nonfinite = [name for name, ok in zip(picks, finite_rows) if not ok]
    result: dict[str, Any] = {
        "analysed_seconds": rounded(segment.times[-1] + 1.0 / sfreq, 2),
        "channels_analysed": len(picks),
        "nonfinite_channels": nonfinite,
    }
    names = [name for name, ok in zip(picks, finite_rows) if ok]
    data = data[finite_rows]
    if data.shape[1] < int(10 * sfreq) or not names:
        result["note"] = "fewer than 10 s of finite data; signal checks skipped"
        return result

    h_freq = min(40.0, 0.45 * sfreq)
    filtered = mne.filter.filter_data(data, sfreq, 1.0, h_freq, verbose="ERROR")
    sd = robust_std(filtered, axis=1)
    usable = sd > 0
    median_sd = float(np.median(sd[usable])) if usable.any() else None
    units = units_verdict(median_sd)
    scale = units.get("suggested_scale") or 1.0
    sd_uv = sd * scale * 1e6

    flat = [name for name, value in zip(names, sd_uv) if value < FLAT_UV]
    live = [i for i, name in enumerate(names) if name not in flat]
    z = robust_z(np.log(sd_uv[live])) if len(live) >= 5 else np.zeros(len(live))
    ratio = sd_uv[live] / np.median(sd_uv[live]) if live else np.zeros(0)
    extreme = [
        names[i] for i, value, r in zip(live, z, ratio) if value > EXTREME_Z and r > EXTREME_RATIO
    ]

    clipped = []
    for name, row in zip(names, data):
        if name in flat:
            continue
        span = row.max() - row.min()
        tolerance = 1e-6 * span if span > 0 else 0.0
        at_rail = np.mean((row >= row.max() - tolerance) | (row <= row.min() + tolerance))
        if at_rail > CLIP_FRACTION:
            clipped.append(name)

    line: dict[str, Any] = {"threshold_db": LINE_DB}
    n_fft = int(min(4 * sfreq, data.shape[1]))
    psd, freqs = mne.time_frequency.psd_array_welch(
        data, sfreq, fmin=1.0, fmax=min(130.0, sfreq / 2), n_fft=n_fft, verbose="ERROR"
    )
    spectrum = np.median(psd, axis=0)
    for f0 in (50.0, 60.0):
        if f0 + 6.0 < sfreq / 2:
            line[f"{int(f0)}_hz_db"] = rounded(line_noise_db(freqs, spectrum, f0), 1)
    heights = {f0: line.get(f"{f0}_hz_db") for f0 in (50, 60)}
    present = {f0: h for f0, h in heights.items() if h is not None and h >= LINE_DB}
    line["detected_hz"] = max(present, key=present.get) if present else None

    result.update(
        {
            "robust_sd_uv_as_stored": {n: rounded(v, 3) for n, v in zip(names, sd * 1e6)},
            "units_check": units,
            "flat_channels": flat,
            "extreme_channels": extreme,
            "possibly_clipped_channels": clipped,
            "line_noise": line,
        }
    )
    return result


def inspect(raw: Any, path: Path, args: argparse.Namespace, mne: Any, notes: list[str]) -> dict:
    info = raw.info
    sfreq = info["sfreq"]
    kinds = raw.get_channel_types()
    by_type: dict[str, list[str]] = {}
    for name, kind in zip(raw.ch_names, kinds):
        by_type.setdefault(kind, []).append(name)

    type_suggestions = {
        name: guess
        for name, kind in zip(raw.ch_names, kinds)
        if kind in ("eeg", "misc") and (guess := suggest_channel_type(name)) and guess != kind
    }
    eeg_names = [n for n in by_type.get("eeg", []) if n not in type_suggestions]
    with_positions = 0
    for ch in info["chs"]:
        loc = ch["loc"][:3]
        if ch["ch_name"] in eeg_names and all(v == v for v in loc) and any(v != 0 for v in loc):
            with_positions += 1

    report: dict[str, Any] = {
        "file": {
            "name": path.name,
            "reader": type(raw).__name__,
            "size_bytes": path.stat().st_size if path.is_file() else None,
        },
        "mne_version": mne.__version__,
        "reader_warnings": notes,
        "recording": {
            "sfreq_hz": sfreq,
            "n_samples": raw.n_times,
            "duration_s": rounded(raw.n_times / sfreq, 3),
            "n_channels": len(raw.ch_names),
            "channel_types": {kind: len(names) for kind, names in sorted(by_type.items())},
            "channels_by_type": by_type,
            "bads_in_file": list(info["bads"]),
        },
        "acquisition": {
            "highpass_hz": info["highpass"],
            "lowpass_hz": info["lowpass"],
            "line_freq_hz": info["line_freq"],
            "custom_ref_applied": bool(info["custom_ref_applied"]),
            "n_projectors": len(info["projs"]),
        },
        "privacy": {
            "meas_date_present": info["meas_date"] is not None,
            "subject_info_present": _identifying_subject_info(info),
            "experimenter_present": bool(info.get("experimenter")),
        },
        "channel_type_suggestions": type_suggestions,
    }

    montage: dict[str, Any] = {"eeg_channels": len(eeg_names), "with_positions": with_positions}
    if eeg_names:
        scores = _montage_scores(mne, eeg_names, args.montage)
        montage["best_matches"] = [
            {k: s[k] for k in ("montage", "matched", "fraction", "montage_size")}
            for s in scores[:3]
        ]
        if scores and scores[0]["matched"]:
            best = scores[0]
            montage.update(
                suggested=best["montage"], renames=best["renames"], unmatched=best["unmatched"]
            )
        if args.montage:
            chosen = next(s for s in scores if s["montage"] == args.montage)
            montage["requested"] = {k: chosen[k] for k in ("montage", "matched", "unmatched")}
    report["montage"] = montage

    annotations = raw.annotations
    counts = Counter(str(d) for d in annotations.description)
    is_bad = [str(d).upper().startswith(("BAD", "EDGE")) for d in annotations.description]
    report["annotations"] = {
        "count": len(annotations),
        "n_unique": len(counts),
        "descriptions": dict(counts.most_common(40)),
        "bad_or_edge_duration_s": rounded(sum(d for d, b in zip(annotations.duration, is_bad) if b), 3),
    }
    report["events"] = {
        "stim": _stim_events(mne, raw, by_type.get("stim", [])),
        "annotation_labels": {d: c for d, c in counts.items() if not d.upper().startswith(("BAD", "EDGE"))},
    }

    picks = [n for kind in VOLTAGE_TYPES for n in by_type.get(kind, []) if n not in type_suggestions]
    report["quality"] = (
        _quality(mne, raw, picks, args.max_seconds)
        if picks
        else {"note": "no EEG/iEEG voltage channels; signal checks skipped"}
    )
    report["recommendations"] = _recommend(report, by_type)
    return report


def _recommend(report: dict[str, Any], by_type: dict[str, list[str]]) -> list[str]:
    tips: list[str] = []
    quality = report["quality"]
    units = quality.get("units_check", {})
    if units.get("status") in ("too_large", "too_small"):
        tips.append(
            f"UNITS: median robust SD is {units['median_robust_sd_uv']:.3g} uV as stored, which is "
            f"not scalp-EEG scale. MNE expects volts; rescale before anything else: "
            f"raw.apply_function(lambda x: x * {units['suggested_scale']:g}, picks='eeg')"
        )
    if report["channel_type_suggestions"]:
        tips.append(f"Set channel types: raw.set_channel_types({report['channel_type_suggestions']})")
    montage = report["montage"]
    if montage.get("eeg_channels") and montage.get("with_positions", 0) < montage["eeg_channels"]:
        if montage.get("suggested"):
            best = montage["best_matches"][0]
            renames = montage.get("renames") or {}
            step = f"raw.rename_channels({renames}); " if renames and len(renames) <= 12 else ""
            if len(renames) > 12:
                tips.append(f"{len(renames)} channel names differ from the montage only by case/prefix/suffix")
            tips.append(
                f"No positions for all EEG channels. Best montage: {best['montage']} "
                f"({best['matched']}/{montage['eeg_channels']} names). "
                f"{step}raw.set_montage('{best['montage']}', match_case=False, on_missing='warn')"
            )
        else:
            tips.append("No channel positions and no built-in montage matches; load the cap's "
                        "digitization with mne.channels.read_custom_montage()")
    if montage.get("unmatched"):
        tips.append(f"Channels without a montage position: {montage['unmatched'][:10]}")
    for key, label in (("flat_channels", "flat"), ("extreme_channels", "extreme-amplitude"),
                       ("possibly_clipped_channels", "possibly clipped"), ("nonfinite_channels", "non-finite")):
        if quality.get(key):
            tips.append(f"Inspect {label} channels {quality[key]}; if confirmed: raw.info['bads'] += {quality[key]}")
    line = quality.get("line_noise", {})
    if line.get("detected_hz"):
        tips.append(
            f"Line noise at {line['detected_hz']} Hz. A 40 Hz low-pass removes it for ERPs; for "
            f"broadband analyses use raw.notch_filter(np.arange({line['detected_hz']}, sfreq / 2, "
            f"{line['detected_hz']}))"
        )
    stim = report["events"]["stim"]
    labels = report["events"]["annotation_labels"]
    if stim and stim.get("n_events"):
        tips.append(f"Events on stim channel: mne.find_events(raw, stim_channel='{stim['channel']}')")
    elif labels:
        tips.append("Events are annotations: events, event_id = mne.events_from_annotations(raw)")
    elif by_type.get("eeg"):
        tips.append("No events found: resting-state data, or triggers stored elsewhere")
    acquisition = report["acquisition"]
    if not acquisition["highpass_hz"]:
        tips.append("Data are DC/unfiltered: high-pass 0.1 Hz for ERPs (1 Hz on a copy for ICA)")
    if report["recording"]["sfreq_hz"] > 1000:
        tips.append("High sampling rate: after low-pass filtering, raw.resample(250-500) speeds everything up")
    if report["privacy"]["subject_info_present"]:
        tips.append("File carries subject_info; strip identifiers before sharing: raw.anonymize()")
    if report["reader_warnings"]:
        tips.append("Review reader_warnings; they often explain odd channels or events")
    return tips


def _text(report: dict[str, Any]) -> str:
    rec, acq, q = report["recording"], report["acquisition"], report["quality"]
    lines = [
        f"{report['file']['name']}  [{report['file']['reader']}, MNE {report['mne_version']}]",
        f"  {rec['n_channels']} channels {rec['channel_types']}, {rec['sfreq_hz']:g} Hz, "
        f"{rec['duration_s']:.1f} s",
        f"  acquisition filters: highpass {acq['highpass_hz']} Hz, lowpass {acq['lowpass_hz']} Hz; "
        f"bads in file: {rec['bads_in_file'] or 'none'}",
    ]
    montage = report["montage"]
    if montage.get("best_matches"):
        best, *others = montage["best_matches"]
        also = f"; also {', '.join(o['montage'] for o in others)}" if others else ""
        lines.append(
            f"  montage: {montage['with_positions']}/{montage['eeg_channels']} EEG channels have "
            f"positions; best name match {best['montage']} "
            f"({best['matched']}/{montage['eeg_channels']}){also}"
        )
    ann = report["annotations"]
    lines.append(f"  annotations: {ann['count']} ({ann['n_unique']} labels)")
    stim = report["events"]["stim"]
    if stim:
        lines.append(f"  stim events on {stim['channel']}: {stim.get('codes', stim.get('error'))}")
    if "units_check" in q:
        units = q["units_check"]
        lines.append(
            f"  units: {units['status']} (median robust SD {units.get('median_robust_sd_uv', 0):.3g} uV as stored)"
        )
        line = q["line_noise"]
        lines.append(
            f"  line noise: 50 Hz {line.get('50_hz_db')} dB, 60 Hz {line.get('60_hz_db')} dB "
            f"-> {line['detected_hz'] or 'none'}"
        )
        lines.append(
            f"  flat {q['flat_channels'] or '-'} | extreme {q['extreme_channels'] or '-'} | "
            f"clipped {q['possibly_clipped_channels'] or '-'} | non-finite {q['nonfinite_channels'] or '-'}"
        )
    elif "note" in q:
        lines.append(f"  quality: {q['note']}")
    if report["recommendations"]:
        lines.append("next steps:")
        lines.extend(f"  - {tip}" for tip in report["recommendations"])
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    import json

    args = build_parser().parse_args(argv)
    if args.max_seconds <= 0:
        raise CliError("--max-seconds must be positive")
    path = checked_input(args.recording)
    mne = import_mne()
    raw, notes = _read(mne, path)
    report = inspect(raw, path, args, mne, notes)
    if args.json_path:
        write_json(Path(args.json_path), report)
    if args.format == "json":
        print(json.dumps(to_jsonable(report), indent=2, sort_keys=True))
    else:
        print(_text(report))
    return 0


if __name__ == "__main__":
    run_cli(main)
