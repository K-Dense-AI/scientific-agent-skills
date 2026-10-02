# Spectra, band power, and time-frequency analysis

Checked against MNE-Python 1.13.2. The blocks run in order on cleaned continuous
recordings: a resting-state file for spectra and an oddball task for time-frequency power.

## Power spectral density

```python
import mne
import numpy as np
from scipy.integrate import trapezoid

raw = mne.io.read_raw("sub-01_task-rest_desc-clean_eeg.fif", preload=True)
sfreq = raw.info["sfreq"]
spectrum = raw.compute_psd(
    method="welch", fmin=1.0, fmax=45.0, n_fft=int(4 * sfreq), picks="eeg", exclude="bads"
)
psds, freqs = spectrum.get_data(return_freqs=True)   # V²/Hz, (n_channels, n_freqs)
print(psds.shape, f"resolution {freqs[1] - freqs[0]:.2f} Hz")
fig = spectrum.plot(dB=True, show=False)
```

- **Welch**: `n_fft` sets the resolution (`sfreq / n_fft`); `n_per_seg` (default `n_fft`) and
  `n_overlap` (default 0) set the averaging. Longer segments resolve peaks better and
  average fewer windows. **Multitaper** (`method="multitaper"`, the default for epochs)
  trades resolution for variance through `bandwidth`; good for short data.
- `Raw.compute_psd` skips `BAD` annotations (`reject_by_annotation=True`). Bad channels are
  included unless `exclude="bads"`.
- Values are V²/Hz. Multiply by 1e12 for µV²/Hz; `10 * log10(psd * 1e12)` is dB re 1 µV²/Hz.
- Spectrum objects: `get_data()`, `.freqs`, `.plot()`, `.plot_topomap(bands=...)`,
  `.to_data_frame()`; epoch spectra have `.average()`.

For resting-state data, compute the spectrum per segment so artifactual segments can be
dropped first:

```python
segments = mne.make_fixed_length_epochs(raw, duration=4.0, overlap=2.0, preload=True)
segments.drop_bad(reject=dict(eeg=250e-6))
segment_spectrum = segments.compute_psd(
    method="welch", fmin=1.0, fmax=45.0, n_fft=int(4 * sfreq), n_per_seg=int(4 * sfreq),
    picks="eeg",
)
mean_spectrum = segment_spectrum.average()
print(len(segments), "segments,", mean_spectrum)
```

## Band power

Integrate the PSD over the band (the frequency step carries the units):

```python
bands = {"delta": (1, 4), "theta": (4, 8), "alpha": (8, 13), "beta": (13, 30)}
psd_uv = mean_spectrum.get_data() * 1e12                # µV²/Hz
f = mean_spectrum.freqs
absolute = {
    name: trapezoid(psd_uv[:, (f >= lo) & (f <= hi)], f[(f >= lo) & (f <= hi)], axis=1)
    for name, (lo, hi) in bands.items()
}
span = (f >= 1) & (f <= 30)
total = trapezoid(psd_uv[:, span], f[span], axis=1)
relative = {name: power / total for name, power in absolute.items()}
alpha_map = mean_spectrum.plot_topomap(bands={"Alpha (8-13 Hz)": (8, 13)}, show=False)
print({name: float(np.median(values)) for name, values in relative.items()})
```

- Report absolute power (µV²), relative power (fraction of a stated total range), or log
  power, and the band edges: conventions differ (alpha 8-12 vs 8-13 Hz). Individualized
  bands relative to the individual alpha frequency follow Klimesch (1999).
- Band power mixes oscillations with the aperiodic 1/f background, and a change in the 1/f
  slope moves every band. `specparam` (formerly FOOOF; Donoghue et al., 2020) separates the
  two. Its 2.0 line is still in release candidates, so pin the exact version you use.
- Reference choice changes topographies and asymmetry indices; state it.

`scripts/band_power.py` does the segmenting, robust segment rejection, band table, the
individual alpha frequency (peak and centre of gravity over posterior channels, flagged
when the maximum sits on the search-range edge), alpha asymmetry `ln(right) - ln(left)`,
and warns when a band extends past the recording's filter edges.

## Time-frequency power and inter-trial coherence

Epoch with padding: a Morlet wavelet lasts `n_cycles / f` seconds, and the first and last
half-wavelet of every epoch are edge-contaminated.

```python
task = mne.io.read_raw("sub-01_task-oddball_desc-clean_eeg.fif", preload=True)
events, event_id = mne.events_from_annotations(task)
tf_epochs = mne.Epochs(
    task, events, event_id, tmin=-1.0, tmax=1.5, baseline=None, reject=dict(eeg=150e-6),
    preload=True,
)
freqs = np.arange(4.0, 31.0, 1.0)
n_cycles = freqs / 2.0            # 0.5 s wavelets at every frequency
power, itc = tf_epochs["target"].compute_tfr(
    "morlet", freqs=freqs, n_cycles=n_cycles, average=True, return_itc=True, decim=2
)
power.apply_baseline(baseline=(-0.5, -0.1), mode="logratio")
power.crop(-0.5, 1.0)             # drop the edge-contaminated padding
itc.crop(-0.5, 1.0)
fig = power.plot(picks="Pz", show=False)
topo = power.plot_topomap(tmin=0.2, tmax=0.5, fmin=8.0, fmax=12.0, show=False)
print(power, itc.data.max())
```

- `compute_tfr` replaced `tfr_morlet`/`tfr_multitaper` (still available as legacy
  functions). `average=False` returns an `EpochsTFR` of single-trial power for statistics;
  it is memory-hungry, so use `decim` and fewer frequencies.
- Resolution trade-off: more cycles give sharper frequency and blurrier time.
  `n_cycles = freqs / 2` keeps a constant 0.5 s window; a constant `n_cycles = 7` shrinks the
  window at high frequencies. For gamma, `method="multitaper"` with `time_bandwidth=4.0`
  is steadier.
- Baseline modes: `"mean"` (subtract), `"ratio"`, `"logratio"` (log10 of the ratio; ×10 for
  dB), `"percent"`, `"zscore"`, `"zlogratio"`. Choose the baseline away from the epoch edges.
- **Induced vs evoked:** power of single trials contains both. Subtract the evoked
  response first for induced-only power: `tf_epochs.copy().subtract_evoked()`.
- **ITC** (0-1) measures phase consistency across trials; it is only defined for
  `average=True` with `return_itc=True` and is biased upward with few trials.

## Connectivity

Spectral and time-resolved connectivity (coherence, wPLI, Granger) live in the separate
`mne-connectivity` package. Volume conduction inflates zero-lag measures between nearby
sensors; prefer lag-insensitive measures (imaginary coherence, wPLI) or source space.
