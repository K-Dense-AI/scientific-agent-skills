#!/usr/bin/env python3
"""Shared helpers for the MNE-Python skill command-line tools.

Module scope is standard library only, so every CLI can build its parser and
answer ``--help`` before MNE, NumPy, or Matplotlib is imported. Numerical
helpers import NumPy lazily inside the function that needs it.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TESTED_MNE_VERSION = "1.13.2"
INSTALL_HINT = 'pip install "mne==1.13.2" pandas scikit-learn python-picard'

# Montage names changed in MNE 1.13: standard_1005/standard_1020 became
# colin27_1005/colin27_1020 (same positions; the old names are removed in 1.14).
PREFERRED_MONTAGES = ("colin27_1005", "standard_1005")

# Voltage channel types whose data MNE stores in volts.
VOLTAGE_TYPES = ("eeg", "seeg", "ecog", "dbs")

# Reference suffixes stripped by clean_channel_name(). Bipolar partners such as
# "-F7" are deliberately absent: "Fp1-F7" is a derivation, not a referential
# channel, and must not be renamed to "Fp1".
_REFERENCE_SUFFIX = re.compile(
    r"[\s_-]+(REF|LE|AR|AVG|A1A2|M1M2|A1|A2|M1|M2|LM|RM)$", re.IGNORECASE
)
_EEG_PREFIX = re.compile(r"^EEG[\s_:-]+", re.IGNORECASE)

# Name patterns for channels that readers such as EDF, BrainVision and EEGLAB
# commonly type as "eeg". Checked in order against the cleaned, upper-cased name.
# "E1"/"E2" (AASM EOG names) are not matched: EGI nets label electrodes E1..E256.
_TYPE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("stim", re.compile(r"^(STI ?\d*|STIM|STATUS|TRIG|TRIGGER|MARKER|EVENTS?)$")),
    ("eog", re.compile(r"EOG|^(VEO|HEO|LOC|ROC|LO1|LO2|IO1|IO2|SO1|SO2)$")),
    ("ecg", re.compile(r"ECG|EKG")),
    ("emg", re.compile(r"EMG|^CHIN")),
    ("resp", re.compile(r"^(RESP|RESPIRATION|THOR|THORAX|ABD|ABDO|ABDOMEN|NASAL|FLOW)")),
    ("gsr", re.compile(r"^(GSR|EDA)")),
    ("temperature", re.compile(r"^TEMP")),
    ("misc", re.compile(r"^(PHOTO|SPO2|SAO2|PLETH|PULSE|AUDIO|SOUND|MIC|ACC)")),
)

_POLARITIES = ("pos", "neg", "abs")


class CliError(Exception):
    """An expected, user-facing error: printed without a traceback."""


# --------------------------------------------------------------------------
# Process plumbing
# --------------------------------------------------------------------------


def run_cli(main: Callable[[Sequence[str] | None], int]) -> None:
    """Run ``main`` and turn CliError into a one-line message and exit code 2."""
    try:
        code = main(None)
    except CliError as error:
        print(f"error: {error}", file=sys.stderr)
        code = 2
    except KeyboardInterrupt:
        code = 130
    sys.exit(code)


def import_mne() -> Any:
    """Import MNE headlessly with quiet logging, or fail with an install hint."""
    os.environ.setdefault("MPLBACKEND", "Agg")
    try:
        import mne
    except ModuleNotFoundError as error:
        raise CliError(
            f"MNE-Python is not installed ({error}); install it with: {INSTALL_HINT}"
        ) from error
    mne.set_log_level("WARNING")
    return mne


def mne_version_tuple(mne: Any) -> tuple[int, int]:
    match = re.match(r"(\d+)\.(\d+)", mne.__version__)
    return (int(match.group(1)), int(match.group(2))) if match else (0, 0)


def default_montage_name(mne: Any) -> str:
    """colin27_1005 on MNE >= 1.13, standard_1005 on older releases."""
    available = set(mne.channels.get_builtin_montages())
    for name in PREFERRED_MONTAGES:
        if name in available:
            return name
    return PREFERRED_MONTAGES[-1]


# --------------------------------------------------------------------------
# Paths and outputs
# --------------------------------------------------------------------------


def checked_input(value: str) -> Path:
    """An existing local file or directory (EGI .mff and CTF .ds are directories)."""
    lowered = value.strip().lower()
    if "://" in lowered or lowered.startswith(("http:", "https:", "ftp:", "s3:", "gs:")):
        raise CliError("URLs are not accepted; download the recording first")
    path = Path(value).expanduser()
    if not path.exists():
        raise CliError(f"input not found: {value}")
    return path


def recording_stem(path: Path, prefix: str | None = None) -> str:
    """Output stem: --prefix, or the input name without MNE/BIDS suffixes."""
    if prefix:
        stem = prefix
    else:
        stem = path.name
        for suffix in (".gz", ".fif", ".edf", ".bdf", ".vhdr", ".set", ".mff", ".cnt", ".gdf"):
            if stem.lower().endswith(suffix):
                stem = stem[: -len(suffix)]
        stem = re.sub(r"([_-](raw|eeg|meg|ieeg|epo|ave))+$", "", stem, flags=re.IGNORECASE)
        stem = re.sub(r"_desc-[A-Za-z0-9]+$", "", stem)
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._-")
    if not stem:
        raise CliError("could not derive an output name; pass --prefix")
    return stem


def prepare_outputs(out_dir: Path, outputs: Iterable[Path], overwrite: bool) -> None:
    """Create ``out_dir`` and refuse to clobber existing outputs without --overwrite."""
    out_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(path.name for path in outputs if path.exists())
    if existing and not overwrite:
        raise CliError(
            f"refusing to overwrite {', '.join(existing)} in {out_dir}; pass --overwrite"
        )


def sha256_file(path: Path, chunk: int = 1 << 20) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


def to_jsonable(value: Any) -> Any:
    """Recursively convert NumPy scalars/arrays and paths; non-finite floats -> None."""
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        items = sorted(value) if isinstance(value, (set, frozenset)) else value
        return [to_jsonable(item) for item in items]
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "tolist") and not isinstance(value, (str, bytes)):
        return to_jsonable(value.tolist())
    if isinstance(value, bool) or value is None or isinstance(value, (str, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return number if math.isfinite(number) else None


def write_json(path: Path, payload: Any) -> None:
    text = json.dumps(to_jsonable(payload), indent=2, sort_keys=True, allow_nan=False)
    path.write_text(text + "\n", encoding="utf-8")


def rounded(value: Any, digits: int = 4) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return round(number, digits) if math.isfinite(number) else None


# --------------------------------------------------------------------------
# Argument parsing
# --------------------------------------------------------------------------


def parse_name_list(text: str | None) -> list[str]:
    """'Fp1, Fp2,,Fp1' -> ['Fp1', 'Fp2'] (order kept, duplicates dropped)."""
    if not text:
        return []
    names: list[str] = []
    for part in text.split(","):
        name = part.strip()
        if name and name not in names:
            names.append(name)
    return names


def parse_mapping(text: str | None, *, what: str) -> dict[str, str]:
    """'VEOG=eog, ECG=ecg' -> {'VEOG': 'eog', 'ECG': 'ecg'}."""
    mapping: dict[str, str] = {}
    for part in parse_name_list(text):
        key, sep, value = part.partition("=")
        if not sep or not key.strip() or not value.strip():
            raise CliError(f"{what} entries must look like NAME=VALUE, got {part!r}")
        mapping[key.strip()] = value.strip()
    return mapping


@dataclass(frozen=True)
class Window:
    """A named ERP measurement window in seconds, with the component polarity."""

    name: str
    tmin: float
    tmax: float
    polarity: str = "abs"


def parse_window(text: str) -> Window:
    """'P3=0.30:0.50:pos' -> Window('P3', 0.30, 0.50, 'pos'). Times are seconds."""
    name, sep, spec = text.partition("=")
    parts = spec.split(":")
    if not sep or not name.strip() or len(parts) not in (2, 3):
        raise CliError(f"--window must look like NAME=TMIN:TMAX[:pos|neg|abs], got {text!r}")
    try:
        tmin, tmax = float(parts[0]), float(parts[1])
    except ValueError as error:
        raise CliError(f"--window times must be numbers in seconds: {text!r}") from error
    polarity = parts[2].strip().lower() if len(parts) == 3 else "abs"
    if polarity not in _POLARITIES:
        raise CliError(f"--window polarity must be one of {_POLARITIES}, got {polarity!r}")
    if not tmin < tmax:
        raise CliError(f"--window needs TMIN < TMAX: {text!r}")
    if max(abs(tmin), abs(tmax)) > 60:
        raise CliError(f"--window times are in seconds, not milliseconds: {text!r}")
    return Window(name.strip(), tmin, tmax, polarity)


def parse_band(text: str) -> tuple[str, float, float]:
    """'alpha=8:13' -> ('alpha', 8.0, 13.0). Frequencies in Hz."""
    name, sep, spec = text.partition("=")
    lo, colon, hi = spec.partition(":")
    try:
        fmin, fmax = float(lo), float(hi)
    except ValueError:
        fmin = fmax = float("nan")
    if not sep or not colon or not name.strip() or not 0 <= fmin < fmax:
        raise CliError(f"--band must look like NAME=FMIN:FMAX with FMIN < FMAX, got {text!r}")
    return name.strip(), fmin, fmax


def parse_group(text: str, *, what: str) -> tuple[str, list[str]]:
    """'parietal=P3,Pz,P4' -> ('parietal', ['P3', 'Pz', 'P4'])."""
    name, sep, members = text.partition("=")
    names = parse_name_list(members)
    if not sep or not name.strip() or not names:
        raise CliError(f"{what} must look like NAME=CH1,CH2,..., got {text!r}")
    return name.strip(), names


def parse_condition(text: str) -> tuple[str, list[str]]:
    """'target=Stimulus/S  2|Stimulus/S  3' -> ('target', [...]).

    Selectors are separated by '|' because annotation labels may contain commas,
    slashes, and spaces. Surrounding whitespace of a selector is significant for
    BrainVision labels ("Stimulus/S  1"), so only the name is stripped.
    """
    name, sep, spec = text.partition("=")
    selectors = [part for part in spec.split("|") if part.strip()]
    if not sep or not name.strip() or not selectors:
        raise CliError(f"--condition must look like NAME=LABEL[|LABEL...], got {text!r}")
    return name.strip(), selectors


def split_contrast(text: str, known: Iterable[str]) -> tuple[str, str]:
    """'target-standard' -> ('target', 'standard'), splitting at the one '-'
    that leaves a known condition name on both sides (names may contain '-')."""
    names = set(known)
    candidates = [
        (text[:index].strip(), text[index + 1 :].strip())
        for index, char in enumerate(text)
        if char == "-"
    ]
    matches = [pair for pair in candidates if pair[0] in names and pair[1] in names]
    if len(matches) != 1:
        raise CliError(
            f"--contrast {text!r} must be A-B with A and B among the conditions "
            f"{sorted(names)}"
        )
    return matches[0]


# --------------------------------------------------------------------------
# Channel-name heuristics (pure functions, unit-tested)
# --------------------------------------------------------------------------


def clean_channel_name(name: str) -> str:
    """Strip an 'EEG ' prefix, a referential suffix and padding dots:
    'EEG FP1-REF' -> 'FP1', 'Fc5.' -> 'Fc5' (PhysioNet EEGBCI labels)."""
    cleaned = _EEG_PREFIX.sub("", name.strip().rstrip("."))
    cleaned = _REFERENCE_SUFFIX.sub("", cleaned)
    return cleaned.strip() or name.strip()


def suggest_channel_type(name: str) -> str | None:
    """A non-EEG channel type implied by the name, or None."""
    upper = clean_channel_name(name).upper()
    for channel_type, pattern in _TYPE_PATTERNS:
        if pattern.search(upper):
            return channel_type
    return None


def match_montage_names(
    names: Sequence[str], montage_names: Sequence[str]
) -> tuple[dict[str, str], list[str]]:
    """Map recording channel names onto montage names.

    Returns ``(renames, unmatched)`` where ``renames`` maps each channel whose
    name differs from its montage spelling (case or prefix/suffix) to that
    spelling. Exact matches need no rename and are not listed. Two channels
    that would collapse onto the same montage name are both left unmatched.
    """
    exact = set(montage_names)
    lower = {name.lower(): name for name in montage_names}
    proposals: dict[str, str] = {}
    unmatched: list[str] = []
    for name in names:
        if name in exact:
            proposals[name] = name
            continue
        target = lower.get(name.lower()) or lower.get(clean_channel_name(name).lower())
        if target is None:
            unmatched.append(name)
        else:
            proposals[name] = target
    counts: dict[str, int] = {}
    for target in proposals.values():
        counts[target] = counts.get(target, 0) + 1
    renames: dict[str, str] = {}
    for name, target in proposals.items():
        if counts[target] > 1:
            unmatched.append(name)
        elif name != target:
            renames[name] = target
    return renames, unmatched


# --------------------------------------------------------------------------
# Numerical helpers (NumPy imported lazily)
# --------------------------------------------------------------------------


def robust_std(data: Any, axis: int = -1) -> Any:
    """MAD-based standard deviation (1.4826 * median absolute deviation)."""
    import numpy as np

    array = np.asarray(data, dtype=float)
    median = np.median(array, axis=axis, keepdims=True)
    return 1.4826 * np.median(np.abs(array - median), axis=axis)


def robust_z(values: Any) -> Any:
    """Robust z-scores; zeros when the spread is zero."""
    import numpy as np

    array = np.asarray(values, dtype=float)
    median = np.median(array)
    spread = 1.4826 * np.median(np.abs(array - median))
    if not np.isfinite(spread) or spread == 0:
        return np.zeros_like(array)
    return (array - median) / spread


def parse_threshold_uv(text: str, *, what: str) -> float | str | None:
    """'auto' -> 'auto', '0'/'off' -> None, '150' -> 150.0 (microvolts)."""
    value = text.strip().lower()
    if value == "auto":
        return "auto"
    if value in ("0", "off", "none"):
        return None
    try:
        number = float(value)
    except ValueError as error:
        raise CliError(f"{what} must be 'auto', 0/off, or microvolts, got {text!r}") from error
    if number < 0:
        raise CliError(f"{what} must not be negative")
    return number or None


def robust_ceiling(values: Any, z: float = 3.0, ratio: float = 1.5) -> float:
    """Outlier ceiling for positive values such as per-epoch peak-to-peak amplitudes.

    A value is an outlier when its log is more than ``z`` robust SDs above the
    median log AND it exceeds ``ratio`` times the median, so homogeneous clean
    data do not lose epochs to a vanishingly small spread.
    """
    import numpy as np

    logs = np.log(np.asarray(values, dtype=float))
    median = float(np.median(logs))
    spread = 1.4826 * float(np.median(np.abs(logs - median)))
    return float(max(math.exp(median + z * spread), ratio * math.exp(median)))


def units_verdict(median_std_volts: float | None) -> dict[str, Any]:
    """Classify a band-passed robust SD (volts) as plausible scalp-EEG scale or not.

    Band-passed (1-40 Hz) scalp EEG has a robust SD of a few to a few tens of
    microvolts. Values of volts-to-millivolts mean the samples were stored in
    microvolts (or millivolts) but labelled as volts; the suggested factor is
    the power of 1000 that brings the median back to ~10 microvolts.
    """
    if median_std_volts is None or not math.isfinite(median_std_volts) or median_std_volts <= 0:
        return {"status": "unknown", "suggested_scale": None}
    median_uv = median_std_volts * 1e6
    if median_std_volts > 2e-3:
        exponent = round(math.log10(median_std_volts / 1e-5) / 3) * 3
        return {
            "status": "too_large",
            "median_robust_sd_uv": median_uv,
            "suggested_scale": 10.0 ** (-exponent),
        }
    if median_std_volts < 1e-7:
        exponent = round(math.log10(1e-5 / median_std_volts) / 3) * 3
        return {
            "status": "too_small",
            "median_robust_sd_uv": median_uv,
            "suggested_scale": 10.0 ** exponent,
        }
    return {"status": "plausible", "median_robust_sd_uv": median_uv, "suggested_scale": None}


def line_noise_db(freqs: Any, psd: Any, f0: float) -> float | None:
    """Height (dB) of the spectral peak at ``f0`` over its 2-6 Hz flanks."""
    import numpy as np

    freqs = np.asarray(freqs, dtype=float)
    psd = np.asarray(psd, dtype=float)
    peak_mask = np.abs(freqs - f0) <= 1.0
    flank_mask = (np.abs(freqs - f0) >= 2.0) & (np.abs(freqs - f0) <= 6.0)
    if not peak_mask.any() or flank_mask.sum() < 2:
        return None
    baseline = np.median(psd[flank_mask])
    if not np.isfinite(baseline) or baseline <= 0:
        return None
    return float(10 * np.log10(psd[peak_mask].max() / baseline))
