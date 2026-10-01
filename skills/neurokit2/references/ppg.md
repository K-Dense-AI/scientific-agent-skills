# Photoplethysmography

Checked **2026-10-01** against NeuroKit2 0.2.13 stable runtime/source,
the official PPG API, 0.2.13 release notes, and measurement guidance.

## Acquisition contract

Record sensor mode (reflectance/transmission), wavelength(s), anatomical site,
attachment/contact pressure, device/firmware, raw unit/range, ambient-light handling,
sampling rate, clock, temperature/perfusion, activity/posture, and motion/accelerometer
channels. Validate across representative skin pigmentation, anatomy, age, vascular
state, motion, and intended population.

PPG is optical blood-volume-pulse measurement, not cardiac electrical activity.
Pulse timing and morphology depend on site and vascular/transit dynamics.

## Stable high-level pipeline

```python
signals, info = nk.ppg_process(
    ppg,
    sampling_rate=100,
    method="elgendi",
    method_quality="templatematch",
)
```

Pinned 0.2.13 default columns:

```text
PPG_Raw, PPG_Clean, PPG_Rate, PPG_Quality, PPG_Peaks
```

`info` contained `PPG_Peaks`, `sampling_rate`, and peak/correction method metadata.
The live doc's older codebook can omit `PPG_Quality`; stable runtime/source includes it.

## Cleaning and peak methods

For explicit selection:

```python
clean = nk.ppg_clean(
    ppg,
    sampling_rate=100,
    method="elgendi",
)
markers, peak_info = nk.ppg_peaks(
    clean,
    sampling_rate=100,
    method="elgendi",
    correct_artifacts=False,
)
```

Stable cleaning methods include:

- `elgendi`;
- `nabian2018` (can use expected heart rate);
- `langevin2021`;
- `goda2024`; and
- `none`.

Stable peak methods include:

- `elgendi`;
- `bishop` (peaks plus pulse onsets);
- `charlton` (MSPTDfast v2; peaks plus onsets); and
- `charlton2024` (superseded v1).

Method-dependent extra outputs are a primary reason not to hard-code one schema.
Validate peak/onset performance against labeled data at the actual site, rate,
perfusion, motion, and population.

`correct_artifacts=True` uses the cardiac peak-correction path. Retain raw/corrected
peaks and correction categories; correction cannot repair a low-quality optical
waveform.

## Quality outputs added/expanded in 0.2.13

```python
quality = nk.ppg_quality(
    clean,
    peaks=peak_info["PPG_Peaks"],
    sampling_rate=100,
    method="templatematch",
)
```

Stable quality methods and scales differ:

- `templatematch`: continuous similarity, typically 0–1;
- `dissimilarity`: unbounded, where zero is highest similarity;
- `ho2025`/interval-consistency path: binary interval quality;
- `skewness`, `kurtosis`, `entropy`: unbounded windowed metrics;
- `perfusion`: AC peak-to-peak / absolute raw DC mean × 100; requires raw PPG and
  is not bounded at 100 in the implementation; and
- `relative_power`: 0–1, requires raw PPG, and defaults to 60 s windows.

No threshold is universal across these outputs. Name the method and direction/scale.
For perfusion, a near-zero DC denominator can explode the ratio; exactly zero returns
zero in the implementation. Neither outcome establishes poor/good sensor quality.
The docstring's advertised 0–100 range is not enforced by stable source/runtime.
Short signals can be invalid for a method's default window. `ppg_process()` passes
peak indices—not the whole info dict—to quality estimation.

Quality relative to an average pulse does not prove physiological accuracy: repeated
motion-corrupted beats can be morphologically consistent. Combine morphology, motion,
contact/perfusion, missingness, detector agreement, and endpoint-specific validation.

## Sampling and preprocessing

Sampling requirements depend on endpoint:

- pulse rate needs less bandwidth than morphology, onset timing, or derivatives;
- wrist wearables commonly use lower rates than laboratory finger systems;
- resampling cannot recover missing onset precision or a dicrotic feature; and
- a nominal rate does not establish clock accuracy or anti-alias filtering.

Do not prescribe one universal minimum. Validate rate and filters for the exact
detector/feature and report native/processed rates. Process at native rate before
multimodal alignment when possible.

Motion, contact pressure, ambient light, vasoconstriction, temperature, pigmentation,
site, and clipping can all change amplitude/morphology. Preserve a quality/artifact
mask and accelerometry where available. Avoid interpolating through corrupted pulses.

## PPG-derived variability is PRV

```python
prv = nk.hrv_time(peak_info, sampling_rate=100)
```

NeuroKit2 accepts PPG peaks in HRV functions, but interpretation remains pulse-rate
variability. PRV contains pre-ejection and pulse-transit variability and can differ
from ECG HRV by site, posture, respiration, activity, temperature, and vascular state.

For an HRV-equivalence claim:

1. acquire synchronized ECG and PPG;
2. validate pulse/beat matching and lag/drift;
3. prespecify agreement metrics and acceptable error for each HRV endpoint;
4. test rest, task/activity, motion, and relevant populations/sites; and
5. report PRV terminology when equivalence is not established.

Do not infer ECG morphology, rhythm diagnosis, oxygen saturation, blood pressure, or
arterial stiffness from this basic PPG pipeline.

## Event and interval analysis

```python
epochs = nk.epochs_create(
    signals,
    events,
    sampling_rate=100,
    epochs_start=-1,
    epochs_end=10,
    baseline_correction=False,
)
event_features = nk.ppg_eventrelated(epochs)
interval_features = nk.ppg_intervalrelated(signals, sampling_rate=100)
```

Documented event fields include baseline/min/max/mean/SD rate, times, and polynomial
trend coefficients. Interval output includes mean rate and HRV-family columns.
Availability depends on input columns, duration, and release; inspect runtime output.

## Pulse morphology

`ppg_segment()` returns a dict of pulse epochs. Morphology comparisons require:

- consistent site, attachment, pressure, wavelength, and polarity;
- validated onsets/peaks and quality masks;
- appropriate baseline/amplitude normalization;
- sufficient sampling/bandwidth;
- control of heart rate and vascular state; and
- endpoint-specific evidence.

A dicrotic feature in a processed waveform does not by itself validate aortic valve
timing or arterial stiffness.

## Interpretation boundary

Use these tools for research and education. They are not validated here for arrhythmia,
oxygen saturation, blood pressure, disease detection, remote patient monitoring,
alarms, or wearable medical-device validation.

## Sources checked 2026-10-01

- [Official PPG API](https://neuropsychology.github.io/NeuroKit/functions/ppg.html)
- [Stable v0.2.13 PPG source](https://github.com/neuropsychology/NeuroKit/tree/v0.2.13/neurokit2/ppg)
- [NeuroKit2 0.2.13 release](https://github.com/neuropsychology/NeuroKit/releases/tag/v0.2.13)
- [Charlton et al. (2023), wearable PPG roadmap](https://doi.org/10.1088/1361-6579/acead2)
- [Allen (2007), PPG measurement review](https://doi.org/10.1088/0967-3334/28/3/R01)
- [Quigley et al. (2024), ECG/PPG and HRV guidance](https://doi.org/10.1111/psyp.14604)
- [Yuda et al. (2020), PRV site differences](https://pmc.ncbi.nlm.nih.gov/articles/PMC7035641/)

- [Stable `ppg_quality.py` implementation](https://github.com/neuropsychology/NeuroKit/blob/v0.2.13/neurokit2/ppg/ppg_quality.py)
