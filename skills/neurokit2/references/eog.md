# Electrooculography

Checked **2026-10-01** against NeuroKit2 0.2.13 stable source/runtime
and the official EOG API/example.

## Scope and orientation

NeuroKit2's EOG pipeline is primarily a **vertical EOG blink** workflow. Stable
`eog_process()` requires blinks to be positive-going peaks. Verify channel montage,
polarity, reference, physical unit, sampling rate, hardware filters, amplifier range,
clock, and synchronization before processing.

Do not use this module as a full gaze, saccade, fixation, or sleep-scoring system.
Horizontal/vertical eye-movement interpretation and clinical/drowsiness monitoring need
separate validated methods.

## Optional MNE default

`eog_peaks()` and `eog_findpeaks()` default to `method="mne"`. In the core 0.2.13
installation, MNE is optional; the default can therefore raise an ImportError. Either
add MNE at a reviewed exact version to the project lock or choose a core method:

```python
signals, info = nk.eog_process(
    veog,
    sampling_rate=200,
    method="neurokit",
)
```

`eog_process()` forwards `**kwargs` to cleaning and peak finding. Record the explicit
method rather than relying on an environment-dependent default.

## Stable schemas

The high-level return is `(signals, info)`. Default columns are:

```text
EOG_Raw, EOG_Clean, EOG_Blinks, EOG_Rate
```

`info` has `EOG_Blinks` (sample indices) and `sampling_rate`.

Low-level interfaces differ:

```python
clean = nk.eog_clean(veog, sampling_rate=200, method="neurokit")

# Returns only an array of blink sample indices.
blink_indices = nk.eog_findpeaks(
    clean,
    sampling_rate=200,
    method="neurokit",
)

# Returns (same-length marker DataFrame, info dict).
blink_markers, blink_info = nk.eog_peaks(
    clean,
    sampling_rate=200,
    method="neurokit",
)
```

The 0.2.13 `eog_peaks()` docstring return section says array, while its tagged source
returns `(signals, info)`. The pinned source/runtime is authoritative for stable work.

Stable cleaning methods include `neurokit`, `agarwal2019`, `mne`, `brainstorm`, and
`kong1998`. Peak methods include `neurokit`, `mne`, `brainstorm`, and `blinker`.
MNE and some method paths need optional dependencies.

## Blink features

```python
features = nk.eog_features(
    clean,
    blink_info["EOG_Blinks"],
    sampling_rate=200,
)
```

`eog_features()` needs both the cleaned signal and peak-index array. It returns a dict
with event-level fields such as:

```text
Blink_LeftZeros, Blink_RightZeros, Blink_pAVR,
Blink_nAVR, Blink_BAR, Blink_Duration
```

Do not pass the processed DataFrame as the only argument. Feature validity depends on
positive orientation and accurate blink segmentation.

## Sampling and artifacts

Choose a rate from the endpoint and hardware bandwidth, not a universal number. Basic
blink timing may use lower rates than detailed eyelid velocity or saccade morphology.
Validate temporal error against labeled data at the actual rate; 200–500 Hz is common
in research but not a guarantee.

Inspect:

- saturation and clipping during large eye movements;
- baseline drift and electrode polarization;
- frontal/facial EMG and movement/cable artifacts;
- line noise and channel detachment;
- polarity and montage changes across sessions; and
- missing samples and synchronization with EEG/events.

Do not interpolate through a blink or across detachment. Preserve raw/clean overlays,
blink markers, rejected segments, and manual review outcomes.

## Event and interval analysis

```python
epochs = nk.epochs_create(
    signals,
    events,
    sampling_rate=200,
    epochs_start=-0.5,
    epochs_end=2,
    baseline_correction=False,
)
event_features = nk.eog_eventrelated(epochs)
interval_features = nk.eog_intervalrelated(signals)
```

Documented event-related fields include `EOG_Rate_Baseline`, rate min/max/mean/SD and
times, plus `EOG_Blinks_Presence`. Interval analysis returns `EOG_Peaks_N` and
`EOG_Rate_Mean` in the official example. It does not universally return blink
amplitude or duration summaries. Inspect columns at runtime.

Blink rate over short windows is unstable and task-dependent. A count/rate change does
not uniquely identify attention, fatigue, stress, dry eye, dopamine, or a neurological
condition.

## EEG integration

EOG can help identify ocular contamination in EEG, but NeuroKit2 does not provide a
complete validated correction pipeline here. With MNE:

1. synchronize and preserve dedicated EOG channels;
2. fit artifact identification/correction on appropriate data;
3. verify component or regression selection without removing neural signal;
4. compare raw and corrected ERPs/spectra/topographies; and
5. report method, channels, filters, thresholds, components, and exclusions.

Avoid circularly selecting correction settings to maximize an experimental result.

## Sources checked 2026-10-01

- [Official EOG API](https://neuropsychology.github.io/NeuroKit/functions/eog.html)
- [Official EOG example](https://neuropsychology.github.io/NeuroKit/examples/eog_analyze/eog_analyze.html)
- [Stable v0.2.13 EOG source](https://github.com/neuropsychology/NeuroKit/tree/v0.2.13/neurokit2/eog)
- [Kleifges et al. (2017), BLINKER](https://doi.org/10.3389/fnins.2017.00012)
- [Keil et al. (2014), EEG/MEG reporting guidance](https://doi.org/10.1111/psyp.12147)
