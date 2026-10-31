# ECG and cardiac processing

Checked **2026-10-01** against NeuroKit2 0.2.13 stable source/runtime,
the live ECG API, and current psychophysiology measurement guidance.

## Acquisition contract

Record lead/configuration, electrode placement, reference/ground, hardware gain and
filters, ADC resolution/range, physical unit, native sampling rate, timestamp clock,
posture/task, medication and relevant population variables, and artifact annotations.
Do not infer millivolts from a column named `ECG`.

Sampling must support the intended endpoint. Rate/R-peak timing and P–QRS–T morphology
have different bandwidth and precision needs. Psychophysiology guidance commonly uses
at least 125 Hz and regards 500 Hz as conservative for HRV timing, but this is not a
universal validation threshold. Validate the complete acquisition and detector on
representative signals; morphology/delineation often uses 250–1000 Hz.

## `ecg_process()` in stable 0.2.13

```python
signals, info = nk.ecg_process(
    ecg,
    sampling_rate=250,
    method="neurokit",
)
```

The stable source performs:

1. `signal_sanitize()` (index reset only);
2. `ecg_clean()` with the selected method;
3. `ecg_peaks(..., correct_artifacts=True)`;
4. interpolated rate;
5. default `ecg_quality(..., method="averageQRS")`;
6. DWT delineation; and
7. atrial/ventricular phase.

The pinned default probe observed these 19 columns:

```text
ECG_Raw, ECG_Clean, ECG_Rate, ECG_Quality, ECG_R_Peaks,
ECG_P_Peaks, ECG_P_Onsets, ECG_P_Offsets, ECG_Q_Peaks,
ECG_R_Onsets, ECG_R_Offsets, ECG_S_Peaks, ECG_T_Peaks,
ECG_T_Onsets, ECG_T_Offsets, ECG_Phase_Atrial,
ECG_Phase_Completion_Atrial, ECG_Phase_Ventricular,
ECG_Phase_Completion_Ventricular
```

This is a verified default schema, not a universal promise. Persist
`list(signals.columns)` and `sorted(info)`.

`info` is a flat dict. In the default pinned run it included corrected and uncorrected
R-peaks, `ECG_fixpeaks_*` diagnostics, sampling rate, methods, and delineated wave
indices. It is not nested under an `ECG` key.

## Cleaning and R-peak methods

High-level methods documented for `ecg_process()` include `neurokit`,
`pantompkins1985`, `hamilton2002`, `elgendi2010`, and `engzeemod2012`.
`ecg_clean()` and lower-level peak detection expose additional methods. A cleaning
method and detector encode different assumptions; do not select whichever produces
the expected group effect.

In stable `ecg_process()`, `**kwargs` are forwarded only to `ecg_clean()`. They do not
configure the R-peak detector, correction, quality method, or delineation. Use the
lower-level functions when those settings matter, and preserve their parameters.

For custom control:

```python
clean = nk.ecg_clean(ecg, sampling_rate=250, method="neurokit")
markers, peak_info = nk.ecg_peaks(
    clean,
    sampling_rate=250,
    method="neurokit",
    correct_artifacts=False,
)
```

Validate:

- R-peak precision, false positives, missed beats, and ectopy;
- performance during motion, changing rate, and low-amplitude QRS;
- lead polarity and possible inversion;
- filter edge regions and discontinuities; and
- failure modes by participant, condition, device, and population.

## Peak correction

`ecg_process()` always requests Lipponen–Tarvainen correction in 0.2.13. Inspect:

```python
uncorrected = info["ECG_R_Peaks_Uncorrected"]
corrected = info["ECG_R_Peaks"]
categories = {
    key: info.get(f"ECG_fixpeaks_{key}", [])
    for key in ["ectopic", "missed", "extra", "longshort"]
}
```

Correction can improve a tachogram but can also alter HRV. Report corrected proportions,
categories, thresholds/method, excluded segments, and sensitivity with uncorrected or
alternative policies. Do not assume an algorithm can distinguish ectopic from erroneous
detection without waveform review or appropriate labels.

## ECG quality is method-dependent

```python
quality = nk.ecg_quality(
    clean,
    rpeaks=peak_info["ECG_R_Peaks"],
    sampling_rate=250,
    method="averageQRS",
)
```

Stable options include `averageQRS`, `templatematch`, `zhao2018`,
`dissimilarity`, and `ho2025`.

- `averageQRS`: continuous array scaled 0–1 by this implementation.
- `templatematch`: continuous morphology-template correlation; it is relative to the
  recording.
- `zhao2018`: one classification string (`Unacceptable`, `Barely acceptable`, or
  `Excellent`).
- `dissimilarity`: direction/scale differs from similarity scores.
- `ho2025`: beat/interval-oriented quality based on detector agreement.

There is no universal `>0.6` acceptance rule across these methods. A quality output is
not device validation. Define thresholds on independent labeled data and preserve the
method name and scale.

## Delineation return order

```python
delineation_signals, waves = nk.ecg_delineate(
    clean,
    rpeaks=peak_info["ECG_R_Peaks"],
    sampling_rate=250,
    method="dwt",
)
```

The first object is a same-length marker DataFrame; the second is a dict of wave sample
indices. Stable methods include `peak`, `prominence`, `cwt`, and `dwt`. Missing wave
indices may be NaN. Validate every wave endpoint needed for an interval/morphology
claim; R-peak accuracy does not validate P/T delineation.

## Phase and event-related analysis

`ECG_Phase_Atrial` and `ECG_Phase_Ventricular` are binary phase labels;
completion columns are fractions from 0 to 1. Their validity depends on delineation.
For cardiac-locked stimuli, characterize trigger latency/jitter independently of
software phase estimates.

`ecg_eventrelated()` and `ecg_intervalrelated()` inspect available columns. Their output
columns are conditional. Use explicit dispatch and save observed columns:

```python
features = nk.ecg_analyze(
    epochs,
    sampling_rate=250,
    method="event-related",
)
```

## ECG-derived respiration

`ecg_rsp()` takes a heart-rate series, not raw/clean ECG:

```python
edr = nk.ecg_rsp(signals["ECG_Rate"], sampling_rate=250, method="vangent2019")
```

EDR is a proxy and depends on ECG morphology/rate modulation. It is not interchangeable
with a calibrated respiration sensor for RSA, tidal volume, or respiratory diagnosis.

## Bounded pipeline

```bash
python skills/neurokit2/scripts/ecg_hrv_pipeline.py \
  --input deidentified.csv --column ECG --root . --deidentified \
  --sampling-rate 250 --method neurokit --domains time \
  --signals-output ecg_processed.csv --output ecg_report.json
```

The helper rejects missing/non-finite samples instead of silently interpolating them,
reports observed schemas and correction categories, and gates longer HRV domains.

## Sources checked 2026-10-01

- [Official ECG API](https://neuropsychology.github.io/NeuroKit/functions/ecg.html)
- [Stable v0.2.13 `ecg_process` source](https://github.com/neuropsychology/NeuroKit/blob/v0.2.13/neurokit2/ecg/ecg_process.py)
- [Quigley et al. (2024), HR/HRV measurement guidelines](https://doi.org/10.1111/psyp.14604)
- [Laborde et al. (2017), HRV planning/reporting](https://doi.org/10.3389/fpsyg.2017.00213)
- [Lipponen & Tarvainen (2019), correction algorithm](https://doi.org/10.1080/03091902.2019.1640306)
- [Pan & Tompkins (1985)](https://doi.org/10.1109/TBME.1985.325532)
