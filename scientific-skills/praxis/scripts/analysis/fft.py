"""FFT, inverse FFT, power spectrum, and frequency-domain filtering.

Low-pass, high-pass, band-pass, and notch filters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Union

import numpy as np
from scipy.fft import fft, ifft, fftfreq
from scipy.signal import butter, filtfilt, iirnotch

from scripts.core.utils import validate_array


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class FFTResult:
    """Result of FFT analysis."""
    freq: np.ndarray          # Frequency array (Hz)
    amplitude: np.ndarray     # Amplitude spectrum
    phase: np.ndarray         # Phase spectrum (radians)
    power: np.ndarray         # Power spectrum (amplitude^2)
    complex_spectrum: np.ndarray  # Full complex FFT result
    sample_rate: float        # Sampling rate (Hz)
    dominant_freq: float      # Frequency of highest amplitude peak
    dominant_amplitude: float # Amplitude at dominant frequency

    def report(self) -> str:
        lines = [
            "[Praxis] FFT Analysis",
            f"  Points: {len(self.freq) * 2}",
            f"  Sample rate: {self.sample_rate:.2f} Hz",
            f"  Frequency resolution: {self.freq[1] - self.freq[0]:.4f} Hz",
            f"  Dominant frequency: {self.dominant_freq:.4f} Hz",
            f"  Dominant amplitude: {self.dominant_amplitude:.4e}",
        ]
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.report()


# ---------------------------------------------------------------------------
# FFT Analysis
# ---------------------------------------------------------------------------

def compute_fft(
    y: Any,
    *,
    sample_rate: Optional[float] = None,
    x: Optional[Any] = None,
    window: Optional[str] = None,
    remove_dc: bool = True,
) -> FFTResult:
    """Compute the FFT of a signal.

    Parameters
    ----------
    y : array-like
        Input signal.
    sample_rate : float, optional
        Sampling rate in Hz. Calculated from *x* if not given.
    x : array-like, optional
        Time/x array. Used to calculate sample_rate if not given.
    window : str, optional
        Window function: 'hann', 'hamming', 'blackman', 'bartlett'.
    remove_dc : bool
        Remove DC component (mean) before FFT.

    Returns
    -------
    FFTResult
    """
    y = validate_array(y, "y")

    # Determine sample rate
    if sample_rate is None:
        if x is not None:
            x = validate_array(x, "x")
            dt = np.mean(np.diff(x))
            sample_rate = 1.0 / abs(dt)
        else:
            sample_rate = 1.0  # Default: normalised frequency

    n = len(y)

    # Remove DC
    if remove_dc:
        y = y - np.mean(y)

    # Apply window
    if window is not None:
        w = _get_window(window, n)
        y = y * w

    # Compute FFT
    Y = fft(y)
    freq = fftfreq(n, d=1.0 / sample_rate)

    # Take positive frequencies only
    pos_mask = freq >= 0
    freq_pos = freq[pos_mask]
    Y_pos = Y[pos_mask]

    amplitude = 2.0 * np.abs(Y_pos) / n
    phase = np.angle(Y_pos)
    power = amplitude ** 2

    # Dominant frequency (excluding DC)
    if len(amplitude) > 1:
        idx = np.argmax(amplitude[1:]) + 1
        dominant_freq = freq_pos[idx]
        dominant_amp = amplitude[idx]
    else:
        dominant_freq = 0.0
        dominant_amp = 0.0

    result = FFTResult(
        freq=freq_pos,
        amplitude=amplitude,
        phase=phase,
        power=power,
        complex_spectrum=Y,
        sample_rate=sample_rate,
        dominant_freq=dominant_freq,
        dominant_amplitude=dominant_amp,
    )

    print(result.report())
    return result


def compute_ifft(spectrum: np.ndarray) -> np.ndarray:
    """Compute the inverse FFT to reconstruct a time-domain signal.

    Parameters
    ----------
    spectrum : np.ndarray
        Complex FFT spectrum (full, including negative frequencies).

    Returns
    -------
    np.ndarray
        Reconstructed real-valued signal.
    """
    return np.real(ifft(spectrum))


def power_spectrum(
    y: Any,
    *,
    sample_rate: Optional[float] = None,
    x: Optional[Any] = None,
    window: str = "hann",
    normalise: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute the power spectral density.

    Parameters
    ----------
    y : array-like
    sample_rate : float, optional
    x : array-like, optional
    window : str
    normalise : bool
        Normalise to unit total power.

    Returns
    -------
    (frequencies, psd)
    """
    result = compute_fft(y, sample_rate=sample_rate, x=x, window=window)
    psd = result.power
    if normalise and np.sum(psd) > 0:
        psd = psd / np.sum(psd)
    return result.freq, psd


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def filter_signal(
    y: Any,
    filter_type: str,
    cutoff: Union[float, tuple[float, float]],
    *,
    sample_rate: Optional[float] = None,
    x: Optional[Any] = None,
    order: int = 4,
    quality_factor: float = 30.0,
) -> np.ndarray:
    """Apply a frequency-domain filter to a signal.

    Parameters
    ----------
    y : array-like
        Input signal.
    filter_type : str
        'lowpass', 'highpass', 'bandpass', 'bandstop', 'notch'.
    cutoff : float or (float, float)
        Cutoff frequency in Hz. For bandpass/bandstop, provide (low, high).
    sample_rate : float, optional
        Sampling rate. Calculated from *x* if not given.
    x : array-like, optional
        Time array.
    order : int
        Butterworth filter order.
    quality_factor : float
        Q factor for notch filter.

    Returns
    -------
    np.ndarray
        Filtered signal.
    """
    y = validate_array(y, "y")

    # Determine sample rate
    if sample_rate is None:
        if x is not None:
            x = validate_array(x, "x")
            dt = np.mean(np.diff(x))
            sample_rate = 1.0 / abs(dt)
        else:
            raise ValueError("Provide sample_rate or x array.")

    nyquist = sample_rate / 2.0
    filter_type = filter_type.lower().replace("-", "").replace("_", "")

    # Map to scipy btype names
    btype_map = {"lowpass": "low", "highpass": "high", "bandpass": "bandpass", "bandstop": "bandstop"}

    if filter_type == "notch":
        if isinstance(cutoff, (list, tuple)):
            cutoff = cutoff[0]
        b, a = iirnotch(cutoff, quality_factor, sample_rate)
    elif filter_type in ("lowpass", "highpass"):
        if isinstance(cutoff, (list, tuple)):
            cutoff = cutoff[0]
        wn = cutoff / nyquist
        if wn >= 1.0:
            raise ValueError(f"Cutoff ({cutoff} Hz) must be below Nyquist ({nyquist} Hz).")
        b, a = butter(order, wn, btype=btype_map[filter_type])
    elif filter_type in ("bandpass", "bandstop"):
        if not isinstance(cutoff, (list, tuple)) or len(cutoff) != 2:
            raise ValueError(f"Bandpass/bandstop requires (low, high) cutoff, got {cutoff}.")
        wn = [c / nyquist for c in cutoff]
        if any(w >= 1.0 for w in wn):
            raise ValueError(f"Cutoff frequencies must be below Nyquist ({nyquist} Hz).")
        btype = "bandpass" if filter_type == "bandpass" else "bandstop"
        b, a = butter(order, wn, btype=btype)
    else:
        raise ValueError(
            f"Unknown filter type: '{filter_type}'. "
            "Use 'lowpass', 'highpass', 'bandpass', 'bandstop', or 'notch'."
        )

    filtered = filtfilt(b, a, y)
    print(f"[Praxis] Filter: {filter_type}, cutoff={cutoff} Hz, order={order}")
    return filtered


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_window(name: str, n: int) -> np.ndarray:
    """Return a window function array."""
    windows = {
        "hann": np.hanning,
        "hanning": np.hanning,
        "hamming": np.hamming,
        "blackman": np.blackman,
        "bartlett": np.bartlett,
    }
    func = windows.get(name.lower())
    if func is None:
        raise ValueError(f"Unknown window: '{name}'. Use hann, hamming, blackman, bartlett.")
    return func(n)
