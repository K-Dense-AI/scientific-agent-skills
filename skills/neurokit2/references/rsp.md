# Respiration

Checked **2026-10-01** against NeuroKit2 0.2.13 stable runtime/source,
the official RSP API/examples, and cardiorespiratory interpretation guidance.

## Acquisition contract and polarity

Record sensor type (belt, airflow, capnography, impedance, derived proxy), placement,
gain/range, physical unit, native rate, clock, hardware filters, calibration, and
annotations for speech, cough, sigh, breath hold, swallowing, movement, and detachment.

A belt/impedance amplitude is not tidal volume unless calibrated and validated.
Different devices have opposite polarity. NeuroKit2's documented convention labels:

- `RSP_Peaks`: exhalation onsets;
- `RSP_Troughs`: inhalation onsets; and
- `RSP_Phase`: `1` inspiration, `0` expiration.

Verify these labels against the actual device and a known breath. Invert or relabel
explicitly before interpretation if needed.

## Stable high-level pipeline

```python
signals, info = nk.rsp_process(
    rsp,
    sampling_rate=50,
    method="khodadad2018",
    method_rvt="harrison2021",
)
```

Pinned default columns:

```text
RSP_Raw, RSP_Clean, RSP_Amplitude, RSP_Rate, RSP_RVT,
RSP_Phase, RSP_Phase_Completion,
RSP_Symmetry_PeakTrough, RSP_Symmetry_RiseDecay,
RSP_Peaks, RSP_Troughs
```

`info` contained `RSP_Peaks`, `RSP_Troughs`, and `sampling_rate`. This is a
default schema observation, not a universal contract.

## Cleaning and extrema

```python
clean = nk.rsp_clean(rsp, sampling_rate=50, method="khodadad2018")
markers, extrema = nk.rsp_peaks(
    clean,
    sampling_rate=50,
    method="khodadad2018",
)
```

Stable peak methods include `khodadad2018`, `biosppy`, `scipy`, and
`schafer2008`. `rsp_fixpeaks()` is currently documented as a placeholder that does
not correct respiration extrema.

Validate extrema during irregular breathing, pauses, speech, motion, and changing
amplitude. A smooth sinusoidal simulation is not enough.

## Rate, amplitude, and phase signatures

These functions do not all accept the same peak object:

```python
rate = nk.rsp_rate(
    clean,
    troughs=extrema["RSP_Troughs"],
    sampling_rate=50,
    method="trough",
)
amplitude = nk.rsp_amplitude(
    clean,
    peaks=extrema["RSP_Peaks"],
    troughs=extrema["RSP_Troughs"],
)
phase = nk.rsp_phase(
    extrema["RSP_Peaks"],
    troughs=extrema["RSP_Troughs"],
    desired_length=len(clean),
)
```

- `rsp_rate()` takes the cleaned signal first; `method="trough"` uses inhalation
  onsets, while `method="xcorr"` estimates a windowed principal rate.
- `rsp_amplitude()` returns a same-length interpolated amplitude series.
- `rsp_phase()` takes peaks/troughs, not the cleaned signal, and returns a DataFrame
  with phase and completion.

Rates are breaths/minute. Amplitude remains in the sensor's arbitrary/calibrated unit.
Phase accuracy depends on extrema and polarity.

## RRV and RAV

```python
rrv = nk.rsp_rrv(
    signals["RSP_Rate"],
    troughs=info["RSP_Troughs"],
    sampling_rate=50,
)
rav = nk.rsp_rav(
    signals["RSP_Amplitude"],
    peaks=info,
)
```

The pinned `rsp_rrv()` output had 20 columns spanning interval, frequency, Poincaré,
and entropy metrics (`RRV_RMSSD` through `RRV_SampEn`). The pinned RAV output had
`RAV_Mean`, `RAV_SD`, `RAV_RMSSD`, and `RAV_CVSD`.

Do not interpret RRV/RAV from only a few breaths. Choose duration from the lowest
frequency and nonlinear metric being estimated, and report breath count, usable
duration, irregular-breath exclusions, and sensitivity. There is no universal
“higher is healthier” interpretation.

## Respiratory volume per time

Direct stable signature:

```text
rsp_rvt(
  rsp_signal, sampling_rate=1000, method="power2020",
  boundaries=[2.0, 0.033333...], iterations=10, ...
)
```

Direct `rsp_rvt()` defaults to `power2020`, while `rsp_process()` defaults its
`method_rvt` to `harrison2021`. Other stable option: `birn2006`.

```python
rvt = nk.rsp_rvt(
    clean,
    sampling_rate=50,
    method="harrison2021",
)
```

RVT is a derived proxy/regressor. It is not calibrated respiratory volume or minute
ventilation. For fMRI nuisance modeling, match the cited definition, acquisition,
lag/convolution, resampling, and scanner preprocessing; do not treat one method as
interchangeable with another.

## Missing data and artifacts

Respiration signals commonly contain nonstationary physiology. Do not automatically
classify sighs, pauses, speech, coughing, or swallowing as noise. Annotate them according
to the research question.

- Segment long gaps/detachment.
- Do not interpolate across apnea-like pauses or speech and then compute rate.
- Preserve raw/clean/extrema overlays.
- Track filter and window edge validity.
- Quantify missing breaths and altered intervals after exclusions.
- Verify belt slippage and baseline drift separately from breathing depth.

## Event and interval analysis

```python
epochs = nk.epochs_create(
    signals,
    events,
    sampling_rate=50,
    epochs_start=-1,
    epochs_end=8,
    baseline_correction=False,
)
event_features = nk.rsp_eventrelated(epochs)
interval_features = nk.rsp_intervalrelated(signals, sampling_rate=50)
```

Event-related features are conditional and include rate/amplitude baselines and
post-event summaries, phase/completion at onset, and RVT fields when present. Interval
analysis can append RRV/RAV and inspiration/expiration duration features. Inspect the
runtime schema.

Baseline subtraction is usually inappropriate for binary phase/peak columns. Prespecify
which continuous features, if any, are baseline corrected.

## RSA and alignment

For RSA, ECG and respiration need a shared clock and verified lag/drift:

```python
rsa = nk.hrv_rsa(
    ecg_signals,
    rsp_signals,
    rpeaks=ecg_info,
    sampling_rate=common_rate,
    continuous=False,
)
```

Measure and report respiration; spontaneous or paced breathing changes the estimand.
RSA can reflect cardiac vagal modulation under suitable conditions but is confounded by
respiratory parameters, activity, posture, age, and adrenergic influence.

## Interpretation boundary

Use this module for respiratory time-series research. It is not a validated system for
apnea detection, capnography, tidal-volume measurement, respiratory diagnosis,
biofeedback safety, patient/driver monitoring, or ventilatory control.

## Sources checked 2026-10-01

- [Official RSP API](https://neuropsychology.github.io/NeuroKit/functions/rsp.html)
- [Official RRV example](https://neuropsychology.github.io/NeuroKit/examples/rsp_rrv/rsp_rrv.html)
- [Stable v0.2.13 RSP source](https://github.com/neuropsychology/NeuroKit/tree/v0.2.13/neurokit2/rsp)
- [Grossman & Taylor (2007), respiration/RSA caveats](https://doi.org/10.1016/j.biopsycho.2005.11.014)
- [Berntson et al. (1997), HRV origins/methods/caveats](https://doi.org/10.1111/j.1469-8986.1997.tb02140.x)
- [Birn et al. (2006), RVT and fMRI](https://doi.org/10.1016/j.neuroimage.2005.11.053)
