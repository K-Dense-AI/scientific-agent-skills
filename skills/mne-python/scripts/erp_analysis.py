#!/usr/bin/env python3
"""Epoch continuous EEG, average ERPs per condition, and measure components.

For every condition (and A-B difference wave) x region of interest x window it
reports mean amplitude, peak amplitude and latency (flagging peaks on the window
edge), 50% fractional-area latency, and the standardized measurement error (SME)
of the mean amplitude (Luck et al., 2021). Trial counts and rejection reasons
are logged per condition. Inputs are usually the output of preprocess_eeg.py.

Examples:
    python erp_analysis.py clean_eeg.fif --out-dir erp --list-events
    python erp_analysis.py clean_eeg.fif --out-dir erp \\
        --condition standard=standard --condition target=target \\
        --roi parietal=P3,Pz,P4 --channels Cz \\
        --window N1=0.08:0.14:neg --window P3=0.30:0.50:pos \\
        --contrast target-standard --single-trial
    python erp_analysis.py raw.fif --out-dir erp --stim-channel "STI 014" \\
        --condition "left=1|3" --condition "right=2|4" --window P1=0.08:0.13:pos
"""

from __future__ import annotations

import argparse
import csv
import math
import warnings
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from _common import (
    TESTED_MNE_VERSION,
    CliError,
    Window,
    checked_input,
    import_mne,
    parse_condition,
    parse_group,
    parse_name_list,
    parse_threshold_uv,
    parse_window,
    prepare_outputs,
    recording_stem,
    robust_ceiling,
    rounded,
    run_cli,
    split_contrast,
    write_json,
)

MEASURE_COLUMNS = (
    "source", "kind", "roi", "channels", "window", "tmin_s", "tmax_s", "polarity",
    "mean_amplitude_uv", "peak_amplitude_uv", "peak_latency_ms", "peak_at_window_edge",
    "frac_area_latency_ms", "sme_uv", "n_trials",
)  # fmt: skip
TRIAL_COLUMNS = ("condition", "epoch", "onset_s", "roi", "window", "mean_amplitude_uv")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("recording", help="continuous (cleaned) recording readable by MNE")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--prefix", help="output name stem (default: from the input name)")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--list-events", action="store_true", help="print event labels and exit")

    events = parser.add_argument_group("events and epochs")
    events.add_argument(
        "--condition",
        action="append",
        default=[],
        help="NAME=LABEL[|LABEL...]; default: one condition per annotation label",
    )
    events.add_argument("--stim-channel", help="read events from this stim channel (labels = codes)")
    events.add_argument("--tmin", type=float, default=-0.2)
    events.add_argument("--tmax", type=float, default=0.8)
    events.add_argument("--baseline", nargs=2, type=float, metavar=("BMIN", "BMAX"))
    events.add_argument("--no-baseline", action="store_true")
    events.add_argument(
        "--reject-uv",
        default="100",
        help="EEG peak-to-peak limit in uV (default 100), 'auto' (robust outliers), or 0 (off)",
    )
    events.add_argument("--flat-uv", type=float, default=1.0, help="EEG minimum p2p; 0 off")
    events.add_argument("--reject-eog-uv", type=float, default=0.0, help="EOG p2p; 0 off (default)")
    events.add_argument("--equalize", action="store_true", help="equalize trial counts (mintime)")

    measures = parser.add_argument_group("measurements")
    measures.add_argument("--roi", action="append", default=[], help="NAME=CH1,CH2 (averaged)")
    measures.add_argument("--channels", help="single-channel ROIs, comma separated")
    measures.add_argument("--window", action="append", default=[], help="NAME=TMIN:TMAX[:pos|neg|abs]")
    measures.add_argument("--contrast", action="append", default=[], help="A-B difference wave")
    measures.add_argument("--single-trial", action="store_true", help="per-epoch window means CSV")

    output = parser.add_argument_group("output")
    output.add_argument("--no-figures", action="store_true")
    output.add_argument("--report", action="store_true", help="also write an HTML report")
    return parser


# --------------------------------------------------------------------------
# Measures (pure NumPy; mirror mne.stats.erp in MNE >= 1.13)
# --------------------------------------------------------------------------


def window_mask(times: Any, sfreq: float, tmin: float, tmax: float) -> Any:
    """Samples inside [tmin, tmax] after snapping both to the sample grid (as MNE does)."""
    lo = round(tmin * sfreq) / sfreq - 0.5 / sfreq
    hi = round(tmax * sfreq) / sfreq + 0.5 / sfreq
    return (times >= lo) & (times <= hi)


def measure_wave(wave: Any, times: Any, polarity: str) -> dict[str, Any]:
    """Mean, peak and 50% fractional-area latency of one waveform segment (volts, s)."""
    import numpy as np
    from scipy.integrate import cumulative_trapezoid

    if polarity == "pos":
        k, rectified = int(np.argmax(wave)), np.clip(wave, 0.0, None)
    elif polarity == "neg":
        k, rectified = int(np.argmin(wave)), np.clip(-wave, 0.0, None)
    else:
        k, rectified = int(np.argmax(np.abs(wave))), np.abs(wave)
    area = cumulative_trapezoid(rectified, times, initial=0.0)
    frac = float("nan")
    if area[-1] > 0:
        frac = float(times[np.flatnonzero(area / area[-1] >= 0.5)[0]])
    return {
        "mean": float(np.mean(wave)),
        "peak": float(wave[k]),
        "peak_latency": float(times[k]),
        "peak_at_edge": k in (0, len(wave) - 1),
        "frac_area_latency": frac,
    }


def sme(values: Any) -> float:
    """Standardized measurement error of a mean: SD / sqrt(N) (ddof=0, as mne.stats.erp)."""
    import numpy as np

    values = np.asarray(values, dtype=float)
    return float(np.std(values) / math.sqrt(values.size)) if values.size else float("nan")


# --------------------------------------------------------------------------
# Pipeline
# --------------------------------------------------------------------------


def read_events(raw: Any, args: argparse.Namespace, mne: Any) -> tuple[Any, dict[str, int], str]:
    import numpy as np

    if args.stim_channel:
        if args.stim_channel not in raw.ch_names:
            raise CliError(f"--stim-channel {args.stim_channel!r} is not in the recording")
        events = mne.find_events(raw, stim_channel=args.stim_channel, shortest_event=1, verbose="ERROR")
        labels = {str(int(code)): int(code) for code in np.unique(events[:, 2])}
        return events, labels, f"stim channel {args.stim_channel}"
    try:
        events, labels = mne.events_from_annotations(raw, verbose="ERROR")
    except ValueError:
        events, labels = np.zeros((0, 3), dtype=int), {}
    return events, {str(k): int(v) for k, v in labels.items()}, "annotations"


def list_events(raw: Any, args: argparse.Namespace, mne: Any) -> None:
    events, labels, source = read_events(raw, args, mne)
    counts = Counter(int(code) for code in events[:, 2])
    print(f"events from {source}:")
    if not labels:
        print("  (none)")
    for label, code in sorted(labels.items(), key=lambda item: -counts[item[1]]):
        print(f"  {label!r}: {counts[code]}")
    stim = [n for n, t in zip(raw.ch_names, raw.get_channel_types()) if t == "stim"]
    if stim and not args.stim_channel:
        print(f"stim channels (use --stim-channel): {stim}")


def select_conditions(
    events: Any, labels: dict[str, int], args: argparse.Namespace
) -> tuple[Any, dict[str, int], dict[str, list[str]]]:
    """Re-code events so each condition has one integer id; labels may be merged."""
    import numpy as np

    if args.condition:
        wanted = [parse_condition(text) for text in args.condition]
    else:
        wanted = [(label, [label]) for label in sorted(labels)]
    if not wanted:
        raise CliError("no event labels found; use --list-events, --stim-channel or --condition")
    event_id: dict[str, int] = {}
    members: dict[str, list[str]] = {}
    owner: dict[int, str] = {}
    blocks = []
    for new_code, (name, selectors) in enumerate(wanted, start=1):
        if name in event_id:
            raise CliError(f"condition {name!r} given twice")
        codes = []
        for selector in selectors:
            label = selector if selector in labels else selector.strip()
            if label not in labels:
                raise CliError(
                    f"event label {selector!r} (condition {name!r}) not found; "
                    f"available: {sorted(labels)}"
                )
            code = labels[label]
            if code in owner:
                raise CliError(f"label {label!r} is used by both {owner[code]!r} and {name!r}")
            owner[code] = name
            codes.append(code)
        block = events[np.isin(events[:, 2], codes)].copy()
        block[:, 2] = new_code
        blocks.append(block)
        event_id[name] = new_code
        members[name] = [selector.strip() for selector in selectors]
    selected = np.concatenate(blocks) if blocks else np.zeros((0, 3), dtype=int)
    selected = selected[np.argsort(selected[:, 0], kind="stable")]
    if len(np.unique(selected[:, 0])) != len(selected):
        raise CliError("two selected events share a sample; separate them into one condition")
    return selected, event_id, members


def make_epochs(
    raw: Any, events: Any, event_id: dict[str, int], args: argparse.Namespace, mne: Any
) -> tuple[Any, float | None]:
    """Epochs plus the EEG peak-to-peak limit actually applied (uV, or None)."""
    import numpy as np

    kinds = set(raw.get_channel_types())
    picks = [kind for kind in ("eeg", "eog") if kind in kinds]
    if "eeg" not in picks:
        raise CliError("the recording has no EEG channels")
    limit = parse_threshold_uv(args.reject_uv, what="--reject-uv")
    reject: dict[str, float] = {}
    if isinstance(limit, float):
        reject["eeg"] = limit * 1e-6
    if args.reject_eog_uv > 0 and "eog" in picks:
        reject["eog"] = args.reject_eog_uv * 1e-6
    flat = {"eeg": args.flat_uv * 1e-6} if args.flat_uv > 0 else None
    if args.no_baseline:
        baseline = None
    elif args.baseline:
        baseline = tuple(args.baseline)
        if not args.tmin <= baseline[0] < baseline[1] <= args.tmax:
            raise CliError("--baseline must lie inside [--tmin, --tmax]")
    else:
        baseline = (None, 0.0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        epochs = mne.Epochs(
            raw, events, event_id, tmin=args.tmin, tmax=args.tmax, baseline=baseline,
            picks=picks, reject=reject or None, flat=flat, reject_by_annotation=True,
            preload=True, event_repeated="error", verbose="ERROR",
        )
    if limit == "auto" and len(epochs):
        good = [n for n, t in zip(epochs.ch_names, epochs.get_channel_types())
                if t == "eeg" and n not in epochs.info["bads"]]
        p2p = np.ptp(epochs.get_data(picks=good), axis=2).max(axis=1)
        limit = robust_ceiling(p2p) * 1e6
        epochs.drop_bad(reject={"eeg": limit * 1e-6}, verbose="ERROR")
    return epochs, limit


def drop_summary(epochs: Any, events: Any, event_id: dict[str, int]) -> dict[str, Any]:
    names = {code: name for name, code in event_id.items()}
    kept = set(int(i) for i in epochs.selection)
    summary = {name: {"n_events": 0, "n_kept": 0, "reasons": Counter()} for name in event_id}
    for index, code in enumerate(events[:, 2]):
        entry = summary[names[int(code)]]
        entry["n_events"] += 1
        if index in kept:
            entry["n_kept"] += 1
        else:
            entry["reasons"].update(epochs.drop_log[index] or ("unknown",))
    for entry in summary.values():
        entry["n_dropped"] = entry["n_events"] - entry["n_kept"]
        entry["percent_dropped"] = rounded(100 * entry["n_dropped"] / max(entry["n_events"], 1), 1)
        entry["reasons"] = dict(entry["reasons"].most_common())
    return summary


def build_rois(epochs: Any, args: argparse.Namespace, notes: list[str]) -> dict[str, list[str]]:
    eeg = [n for n, t in zip(epochs.ch_names, epochs.get_channel_types()) if t == "eeg"]
    bads = set(epochs.info["bads"])
    requested: dict[str, list[str]] = {}
    for text in args.roi:
        name, channels = parse_group(text, what="--roi")
        requested[name] = channels
    for channel in parse_name_list(args.channels):
        requested[channel] = [channel]
    if not requested:
        requested = {channel: [channel] for channel in eeg if channel not in bads}
    rois: dict[str, list[str]] = {}
    for name, channels in requested.items():
        unknown = [c for c in channels if c not in eeg]
        if unknown:
            raise CliError(f"ROI {name!r}: {unknown} are not EEG channels of this recording")
        good = [c for c in channels if c not in bads]
        if len(good) < len(channels):
            notes.append(f"ROI {name!r}: dropped bad channels {sorted(set(channels) - set(good))}")
        if not good:
            raise CliError(f"ROI {name!r} has no good channels left")
        rois[name] = good
    return rois


def measure_all(
    epochs: Any, evokeds: dict[str, Any], contrasts: dict[str, tuple[str, str]],
    rois: dict[str, list[str]], windows: list[Window], event_id: dict[str, int],
    first_samp: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    import numpy as np

    times, sfreq = epochs.times, epochs.info["sfreq"]
    masks = {w.name: window_mask(times, sfreq, w.tmin, w.tmax) for w in windows}
    rows: list[dict[str, Any]] = []
    trials: list[dict[str, Any]] = []
    single: dict[tuple[str, str, str], Any] = {}
    onsets = (epochs.events[:, 0] - first_samp) / sfreq  # seconds from the first sample
    for condition, code in event_id.items():
        index = np.flatnonzero(epochs.events[:, 2] == code)
        if not index.size:
            continue
        for roi, channels in rois.items():
            data = epochs.get_data(picks=channels, item=index).mean(axis=1)
            for w in windows:
                values = data[:, masks[w.name]].mean(axis=1)
                single[(condition, roi, w.name)] = values
                for epoch, value in zip(index, values):
                    trials.append(
                        {
                            "condition": condition,
                            "epoch": int(epochs.selection[epoch]),
                            "onset_s": rounded(onsets[epoch], 4),
                            "roi": roi,
                            "window": w.name,
                            "mean_amplitude_uv": rounded(value * 1e6, 4),
                        }
                    )
    sources = [
        (name, evoked, "condition")
        for name, evoked in evokeds.items()
        if not name.startswith("__contrast__")
    ]
    sources += [(name, evokeds[f"__contrast__{name}"], "contrast") for name in contrasts]
    for source, evoked, kind in sources:
        for roi, channels in rois.items():
            wave = evoked.get_data(picks=channels).mean(axis=0)
            for w in windows:
                m = masks[w.name]
                result = measure_wave(wave[m], times[m], w.polarity)
                if kind == "condition":
                    values = single[(source, roi, w.name)]
                    error, n_trials = sme(values), int(values.size)
                else:
                    a, b = contrasts[source]
                    va, vb = single[(a, roi, w.name)], single[(b, roi, w.name)]
                    error = math.sqrt(sme(va) ** 2 + sme(vb) ** 2)
                    n_trials = int(min(va.size, vb.size))
                rows.append(
                    {
                        "source": source,
                        "kind": kind,
                        "roi": roi,
                        "channels": " ".join(channels),
                        "window": w.name,
                        "tmin_s": w.tmin,
                        "tmax_s": w.tmax,
                        "polarity": w.polarity,
                        "mean_amplitude_uv": rounded(result["mean"] * 1e6, 4),
                        "peak_amplitude_uv": rounded(result["peak"] * 1e6, 4),
                        "peak_latency_ms": rounded(result["peak_latency"] * 1e3, 2),
                        "peak_at_window_edge": result["peak_at_edge"],
                        "frac_area_latency_ms": rounded(result["frac_area_latency"] * 1e3, 2),
                        "sme_uv": rounded(error * 1e6, 4),
                        "n_trials": n_trials,
                    }
                )
    return rows, trials


def write_csv(path: Path, columns: Sequence[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            writer.writerow({key: ("" if row.get(key) is None else row.get(key)) for key in columns})


def make_figures(
    evokeds: dict[str, Any], contrasts: dict[str, tuple[str, str]], rois: dict[str, list[str]],
    windows: list[Window], out_dir: Path, stem: str, mne: Any,
) -> list[tuple[str, Path]]:
    import matplotlib.pyplot as plt

    figures: list[tuple[str, Path]] = []
    conditions = {name: ev for name, ev in evokeds.items() if not name.startswith("__contrast__")}
    shown_rois = list(rois.items())[:6]
    for roi, channels in shown_rois:
        fig, ax = plt.subplots(figsize=(7, 3.8), layout="constrained")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mne.viz.plot_compare_evokeds(
                conditions, picks=channels, combine="mean" if len(channels) > 1 else None,
                axes=ax, show=False, legend="upper left",
                title=roi if channels == [roi] else f"{roi} ({', '.join(channels)})",
            )
        for w in windows:
            ax.axvspan(w.tmin, w.tmax, color="#f2c94c", alpha=0.18, lw=0)
        path = out_dir / f"{stem}_erp_{_safe(roi)}.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        figures.append((f"ERP {roi}", path))
    first = next(iter(evokeds.values()))
    eeg_locs = [
        ch["loc"][:3] for ch, kind in zip(first.info["chs"], first.get_channel_types()) if kind == "eeg"
    ]
    has_positions = all(all(v == v for v in loc) and any(loc) for loc in eeg_locs)
    if windows and has_positions:
        topo_sources = dict(conditions)
        topo_sources.update({f"{a} - {b}": evokeds[f"__contrast__{name}"] for name, (a, b) in contrasts.items()})
        for name, evoked in topo_sources.items():
            centers = [(w.tmin + w.tmax) / 2 for w in windows]
            widths = [w.tmax - w.tmin for w in windows]
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fig = evoked.copy().pick("eeg").plot_topomap(
                    times=centers, average=widths, ch_type="eeg", show=False, colorbar=True
                )
            for ax, w in zip(fig.axes, windows):
                ax.set_title(f"{w.name}\n{w.tmin * 1e3:.0f}-{w.tmax * 1e3:.0f} ms", fontsize=9)
            fig.suptitle(name)
            path = out_dir / f"{stem}_topomap_{_safe(name)}.png"
            fig.savefig(path, dpi=150)
            plt.close(fig)
            figures.append((f"Topography {name}", path))
    return figures


def _safe(text: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in text).strip("_") or "x"


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.tmin < 0 < args.tmax:
        raise CliError("--tmin must be negative and --tmax positive (seconds)")
    windows = [parse_window(text) for text in args.window]
    for w in windows:
        if w.tmin < args.tmin or w.tmax > args.tmax:
            raise CliError(f"window {w.name} lies outside the epoch [{args.tmin}, {args.tmax}] s")
    if len({w.name for w in windows}) != len(windows):
        raise CliError("window names must be unique")
    path = checked_input(args.recording)
    mne = import_mne()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            raw = mne.io.read_raw(path, preload=True)
        except Exception as error:
            raise CliError(f"MNE could not read {path.name}: {error}") from error
    if args.list_events:
        list_events(raw, args, mne)
        return 0

    stem = recording_stem(path, args.prefix)
    out_dir = Path(args.out_dir)
    outputs = {
        "epochs": out_dir / f"{stem}_epo.fif",
        "evoked": out_dir / f"{stem}_ave.fif",
        "measures": out_dir / f"{stem}_erp_measures.csv",
        "summary": out_dir / f"{stem}_erp_summary.json",
    }
    if args.single_trial:
        outputs["trials"] = out_dir / f"{stem}_erp_single_trials.csv"
    if args.report:
        outputs["report"] = out_dir / f"{stem}_erp_report.html"
    prepare_outputs(out_dir, outputs.values(), args.overwrite)

    events, labels, source = read_events(raw, args, mne)
    selected, event_id, members = select_conditions(events, labels, args)
    contrasts = {text: split_contrast(text, event_id) for text in args.contrast}
    epochs, reject_limit = make_epochs(raw, selected, event_id, args, mne)
    summary = drop_summary(epochs, selected, event_id)
    notes: list[str] = []
    if args.equalize:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            epochs.equalize_event_counts(list(event_id), method="mintime")
        for name, code in event_id.items():
            summary[name]["n_after_equalize"] = int((epochs.events[:, 2] == code).sum())
    if not len(epochs):
        raise CliError("every epoch was rejected; check units, --reject-uv and bad channels")
    for name, entry in summary.items():
        if entry["percent_dropped"] and entry["percent_dropped"] > 25:
            notes.append(f"{name}: {entry['percent_dropped']}% of epochs rejected")

    import numpy as np

    evokeds: dict[str, Any] = {}
    for name, code in event_id.items():
        index = np.flatnonzero(epochs.events[:, 2] == code)
        if not index.size:
            notes.append(f"{name}: no epochs survived; condition skipped")
            continue
        evoked = epochs[index].average()
        evoked.comment = name
        evokeds[name] = evoked
    for text, (a, b) in contrasts.items():
        if a not in evokeds or b not in evokeds:
            raise CliError(f"contrast {text!r} needs epochs in both {a!r} and {b!r}")
        difference = mne.combine_evoked([evokeds[a], evokeds[b]], weights=[1, -1])
        difference.comment = f"{a} - {b}"
        evokeds[f"__contrast__{text}"] = difference

    rois = build_rois(epochs, args, notes)
    rows, trials = measure_all(epochs, evokeds, contrasts, rois, windows, event_id, raw.first_samp)
    for row in rows:
        if row["peak_at_window_edge"]:
            notes.append(
                f"{row['source']}/{row['roi']}/{row['window']}: peak on the window edge; "
                "prefer the mean amplitude or widen the window"
            )
            break

    epochs.save(outputs["epochs"], overwrite=True, verbose="ERROR")
    mne.write_evokeds(outputs["evoked"], list(evokeds.values()), overwrite=True, verbose="ERROR")
    write_csv(outputs["measures"], MEASURE_COLUMNS, rows)
    if args.single_trial:
        write_csv(outputs["trials"], TRIAL_COLUMNS, trials)
    figures = [] if args.no_figures else make_figures(evokeds, contrasts, rois, windows, out_dir, stem, mne)

    if args.report:
        report = mne.Report(title=f"ERP analysis: {stem}", verbose="ERROR")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            report.add_epochs(epochs, title="Epochs", psd=False)
            report.add_evokeds(
                [ev for ev in evokeds.values()],
                titles=[ev.comment for ev in evokeds.values()],
                n_time_points=5,
            )
        for title, figure in figures:
            report.add_image(figure, title=title)
        report.save(outputs["report"], open_browser=False, overwrite=True, verbose="ERROR")

    write_json(
        outputs["summary"],
        {
            "input": path.name,
            "software": {"mne": mne.__version__, "tested_mne": TESTED_MNE_VERSION},
            "events_source": source,
            "conditions": {name: {"labels": members[name], "id": code} for name, code in event_id.items()},
            "contrasts": {text: {"plus": a, "minus": b} for text, (a, b) in contrasts.items()},
            "epoch": {
                "tmin_s": args.tmin,
                "tmax_s": args.tmax,
                "baseline_s": None if args.no_baseline else (args.baseline or [None, 0.0]),
                "reject_eeg_uv": {"requested": args.reject_uv, "applied": rounded(reject_limit, 2)},
                "flat_eeg_uv": args.flat_uv or None,
                "reject_eog_uv": args.reject_eog_uv or None,
                "sfreq_hz": epochs.info["sfreq"],
                "equalized": args.equalize,
            },
            "trials": summary,
            "rois": rois,
            "windows": [w.__dict__ for w in windows],
            "measures": rows,
            "figures": [p.name for _, p in figures],
            "notes": notes,
            "outputs": {key: p.name for key, p in outputs.items()},
        },
    )
    kept = ", ".join(f"{n} {e['n_kept']}/{e['n_events']}" for n, e in summary.items())
    print(f"epochs kept: {kept}")
    print(f"wrote {len(rows)} measurements to {outputs['measures']}")
    for note in notes:
        print(f"note: {note}")
    return 0


if __name__ == "__main__":
    run_cli(main)
