# Preprocessing: filters, bad channels, ICA, reference

Checked against MNE-Python 1.13.2. The blocks below form one runnable sequence on a
continuous EEG recording with a `VEOG` channel.

## Order of operations

1. Read; set channel types and montage; fix units (see `io-and-channels.md`).
2. Mark known bad channels and bad spans (inspect first: `scripts/inspect_recording.py`).
3. Band-pass the continuous data (notch only if line noise reaches the pass band).
4. Resample, after the low-pass, if needed; convert stim events to annotations first.
5. Fit ICA on a 1 Hz high-passed **copy** with bad channels excluded; apply it to the
   step-3 data.
6. Interpolate bad channels.
7. Re-reference (the average reference should not contain bad channels).
8. Epoch, reject, average (`epochs-and-erps.md`).

`scripts/preprocess_eeg.py` runs steps 1-7 with logged, tested defaults.

## Filtering

```python
import mne
import numpy as np

raw = mne.io.read_raw("sub-01_task-oddball_eeg.fif", preload=True)
raw.filter(l_freq=0.1, h_freq=40.0, picks=["eeg", "eog"])
```

- **Pass `picks`.** With `picks=None`, `filter()` touches data channels (EEG, MEG, sEEG,
  ECoG, fNIRS) but **not EOG, ECG or EMG**. Unfiltered EOG then drifts and ruins any
  `reject=dict(eog=...)`.
- Defaults: zero-phase (non-causal) FIR, `firwin` design, Hamming window. Transition
  widths are `l_trans_bandwidth = min(max(0.25 * l_freq, 2), l_freq)` and
  `h_trans_bandwidth = min(max(0.25 * h_freq, 2), sfreq / 2 - h_freq)`; the filter lasts
  about `3.3 / transition` seconds, so a 0.1 Hz high-pass is a 33 s filter. Recordings
  shorter than that need a higher cutoff.
- Inspect a design before trusting it:

```python
kernel = mne.filter.create_filter(None, raw.info["sfreq"], l_freq=0.1, h_freq=40.0)
print(kernel.size / raw.info["sfreq"], "s")   # filter length
fig = mne.viz.plot_filter(kernel, raw.info["sfreq"], show=False)
```

- **ERP high-pass: 0.1 Hz or lower.** Cutoffs of 0.3-1 Hz distort slow components (P3,
  N400, LPP) and can create artifactual effects of the opposite sign (Tanner et al., 2015).
  Use 1 Hz only on the copy that trains ICA. Resting-state spectra tolerate 0.5-1 Hz.
- Low-pass 30-40 Hz for ERPs; keep more bandwidth for spectral, gamma, or decoding work.
- Filter continuous data, never short epochs (edge artifacts). `phase="minimum"` gives a
  causal filter when onset latencies must not be smeared backwards; `method="iir"` with
  `iir_params=dict(order=4, ftype="butter")` is filtered forward-backward by default.
- `skip_by_annotation` defaults to `("edge", "bad_acq_skip")`; add `"boundary"` for
  EEGLAB files whose data were cut, so filters do not ring across discontinuities.

## Line noise

A 40 Hz low-pass already removes 50/60 Hz. Notch only when the analysis band includes it:

```python
raw_broad = mne.io.read_raw("sub-01_task-oddball_eeg.fif", preload=True)
raw_broad.notch_filter(np.arange(50, raw_broad.info["sfreq"] / 2, 50), picks=["eeg", "eog"])
```

`method="spectrum_fit"` fits and subtracts sinusoids (useful for non-stationary hum).
ZapLine (in `meegkit`, not MNE) handles hum with harmonics and spatial structure.

## Resampling

```python
raw_100 = raw_broad.copy().filter(None, 30.0).resample(sfreq=100.0)
```

Resample after low-pass filtering, and only with events stored as annotations (see
`io-and-channels.md`); `raw.resample(sfreq, events=events)` returns resampled events if you
keep an array. For epochs, `decim=n` in `mne.Epochs` or `epochs.decimate(n)` is cheaper;
keep the low-pass at or below a third of the final rate to avoid aliasing.

## Bad channels

Mark what you know, then look:

```python
raw.info["bads"] = ["FC5", "T8"]                # persists in saved files
print(raw.info["bads"])
lof_bads, lof_scores = mne.preprocessing.find_bad_channels_lof(
    raw, picks="eeg", return_scores=True
)
```

- `raw.plot()` lets you click channels bad in an interactive session.
- `find_bad_channels_lof` (Local Outlier Factor) flags channels whose signal features are
  outliers; confirm hits visually.
- `scripts/preprocess_eeg.py` combines three transparent criteria: flat (robust SD below
  0.5 µV), deviant (robust z of log amplitude > 5 **and** > 2× the median), and poorly
  correlated (98th-percentile |r| with other channels < 0.4 in more than 20% of 1 s
  windows, after PREP; PREP itself uses 1% inside its robust-reference loop). Those
  defaults were checked on simulated data with known bad channels and on PhysioNet
  EEGBCI recordings. A quality gate stops the run when more than 25% of channels fail.
- MEG: `mne.preprocessing.find_bad_channels_maxwell(raw)` before Maxwell filtering.
- Whether `picks="eeg"` includes channels in `info["bads"]` differs between functions:
  `ICA.fit` drops them, `mne.Epochs` keeps them (flagged), and `get_data` gained an
  `exclude` parameter in 1.13. Pass `exclude="bads"` or explicit names when it matters.

## Bad spans

```python
breaks = mne.preprocessing.annotate_break(raw, min_break_duration=15.0)
jumps, jump_bads = mne.preprocessing.annotate_amplitude(raw, peak=dict(eeg=100e-6))
raw.set_annotations(raw.annotations + breaks + jumps)
```

- `annotate_amplitude` compares **sample-to-sample differences** `|x[i+1] - x[i]|`, not a
  windowed peak-to-peak: it catches steps and spikes but not slow, large deflections, and
  its thresholds are far smaller than epoch `reject` values. Channels exceeding the limit
  for more than `bad_percent` of the recording are returned as bads instead.
- `annotate_muscle_zscore` looks at 110-140 Hz by default, so it needs a sampling rate
  above ~300 Hz (or a lower `filter_freq`).
- Manual spans: `mne.Annotations(onset, duration, "BAD_manual")` or `raw.plot()`.

## ICA

Fit on a 1 Hz high-passed copy (slow drifts violate ICA's assumptions), apply to the data
you analyse.

```python
raw_ica = raw.copy().filter(l_freq=1.0, h_freq=None, picks=["eeg", "eog"])
ica = mne.preprocessing.ICA(
    n_components=0.99,                       # enough components for 99% of variance
    method="picard",
    fit_params=dict(ortho=False, extended=True),
    random_state=97,
    max_iter="auto",
)
ica.fit(raw_ica, picks="eeg", reject=dict(eeg=500e-6))   # bads are excluded automatically
print(ica.n_components_, ica.get_explained_variance_ratio(raw_ica))

eog_indices, eog_scores = ica.find_bads_eog(raw_ica, ch_name="VEOG")
ica.exclude = [int(i) for i in eog_indices]
print("ocular components:", ica.exclude, np.round(np.abs(eog_scores)[ica.exclude], 2))
ica.apply(raw)                              # in place, on the 0.1-40 Hz data
```

- **Methods.** `picard` (package `python-picard`) with `ortho=False, extended=True` fits the
  extended-Infomax model, fast and reliably convergent. `infomax` with
  `fit_params=dict(extended=True)` is the same model, built in and slower. `fastica`
  (scikit-learn, the default) often stops at `max_iter` on EEG with a `ConvergenceWarning`.
  1.13 adds `jamica` (needs its own package).
- **Components.** A float keeps the components explaining that variance fraction; an int
  must stay below the data rank, which interpolation, average referencing, and Maxwell
  filtering all reduce.
- **Ocular detection.** `find_bads_eog` returns Pearson correlations with the EOG signal
  (filtered 1-10 Hz) and flags components whose score is an outlier (`measure="zscore"`,
  `threshold=3.0`). Without an EOG channel pass frontal proxies: `ch_name=["Fp1", "Fp2"]`,
  and check the hits, because frontal brain components also correlate with Fp1/Fp2.
- **Cardiac.** `find_bads_ecg(raw_ica, ch_name="ECG", method="ctps")` needs an ECG channel
  for EEG (synthetic ECG is built only from MEG magnetometers).
- **Muscle.** `find_bads_muscle(raw_ica)` scores spectral slope, peripherality, and
  topographic smoothness; it needs channel positions.
- **Review before excluding.** `ica.plot_components()`, `ica.plot_properties(raw_ica,
  picks=ica.exclude)`, `ica.plot_sources(raw_ica)`, and `ica.plot_overlay(raw_ica,
  exclude=ica.exclude)`. `scripts/preprocess_eeg.py` also logs the blink-locked amplitude
  at frontal channels before and after ICA; a small reduction means the excluded
  "ocular" component probably is not one.
- Save with `ica.save("sub-01_ica.fif", overwrite=True)`; reload with
  `mne.preprocessing.read_ica`.

### ICLabel

`mne-icalabel` classifies components into brain, muscle, eye, heart, line noise, channel
noise, and other. It expects extended-Infomax ICA on data that are **average-referenced and
filtered 1-100 Hz**, and works less reliably otherwise:

```python
from mne_icalabel import label_components

raw_iclabel = mne.io.read_raw("sub-01_task-oddball_eeg.fif", preload=True)
raw_iclabel.filter(1.0, 100.0, picks="eeg").set_eeg_reference("average")
ica_iclabel = mne.preprocessing.ICA(
    n_components=15, method="picard", fit_params=dict(ortho=False, extended=True),
    random_state=97, max_iter="auto",
)
ica_iclabel.fit(raw_iclabel, picks="eeg")
labels = label_components(raw_iclabel, ica_iclabel, method="iclabel")
print(list(zip(labels["labels"], np.round(labels["y_pred_proba"], 2)))[:5])
```

Exclude by label and probability (for example eye blink or muscle above 0.8), still after
a look at the components.

### Alternatives

- **EOG regression** (`mne.preprocessing.EOGRegression`) subtracts the EOG channels'
  propagation estimated by least squares. It needs good EOG channels, refuses EEG that has
  no reference set, and also removes the brain signal the EOG channels pick up:

```python
raw_filtered = raw_broad.copy().filter(0.3, 40.0, picks=["eeg", "eog"])  # drifts bias the fit
raw_filtered.set_eeg_reference("average")                               # required first
eog_weights = mne.preprocessing.EOGRegression(picks="eeg", picks_artifact="eog").fit(raw_filtered)
raw_regressed = eog_weights.apply(raw_filtered, copy=True)
```

- **SSP** projectors (`compute_proj_eog`, `compute_proj_ecg`) are the MEG classic; add them
  with `raw.add_proj(projs)`.

## Interpolation and re-referencing

```python
raw.interpolate_bads(reset_bads=True, mode="accurate")   # spherical splines; needs positions
raw.set_eeg_reference("average", projection=False)      # returns raw, not a tuple
```

- Interpolate after ICA and before the average reference. Channels still in
  `info["bads"]` are left out of the average automatically.
- `projection=True` stores the average reference as a projector instead of applying it;
  inverse modelling requires the average-reference projector (`source-localization.md`).
- Other references: linked mastoids `raw.set_eeg_reference(["TP9", "TP10"])` (only if they
  were recorded as channels); restore an implicit online reference with
  `mne.add_reference_channels(raw, "FCz")` before re-referencing; bipolar derivations with
  `mne.set_bipolar_reference(raw, anode=["Fp1"], cathode=["F7"])`; reference-free CSD
  (surface Laplacian) with `mne.preprocessing.compute_current_source_density(raw)`; REST
  with `set_eeg_reference("REST", forward=fwd)`.
- The method `inst.set_eeg_reference()` returns the instance; the function
  `mne.set_eeg_reference(inst)` returns `(inst, ref_data)`. Since 1.13, several channel
  types passed together (for example `ch_type=["ecog", "seeg"]`) are referenced
  independently.

## MEG specifics

Maxwell filtering (SSS/tSSS) removes external interference and can compensate head
movement. Since 1.11 its defaults are `st_overlap=True` and `mc_interp="hann"`. After SSS
the data rank drops to roughly 60-80, so pass `n_components` below it for ICA and
`rank="info"` for covariance estimation. Illustrative, it needs MEGIN/Elekta data and the
site calibration files:

```python
# not run: requires MEGIN/Elekta MEG data with fine-calibration and cross-talk files
bads, _ = mne.preprocessing.find_bad_channels_maxwell(meg_raw, calibration=cal, cross_talk=ct)
meg_raw.info["bads"] += bads
meg_sss = mne.preprocessing.maxwell_filter(meg_raw, calibration=cal, cross_talk=ct, st_duration=10.0)
```

## Quality-control report

```python
report = mne.Report(title="sub-01 preprocessing")
report.add_raw(raw, title="Cleaned data", psd=True)
report.add_ica(ica, title="ICA", inst=raw_ica, picks=ica.exclude or [0])
report.save("sub-01_report.html", open_browser=False, overwrite=True)
```

Reports embed figures in one HTML file; add epochs (`add_epochs`), evoked responses
(`add_evokeds`), custom figures (`add_figure`), and notes (`add_html`).
