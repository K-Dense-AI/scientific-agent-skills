# Epochs, evoked responses, and ERP measures

Checked against MNE-Python 1.13.2. The blocks run in order on a cleaned oddball recording
(`standard`/`target` annotations), such as the output of `scripts/preprocess_eeg.py`.

## Epoching

```python
import mne
import numpy as np

raw = mne.io.read_raw("sub-01_task-oddball_desc-clean_eeg.fif", preload=True)
events, event_id = mne.events_from_annotations(raw)
epochs = mne.Epochs(
    raw,
    events,
    event_id=event_id,
    tmin=-0.2,
    tmax=0.8,
    baseline=(None, 0),          # epoch start .. 0 s
    picks=["eeg", "eog"],
    reject=dict(eeg=100e-6),     # peak-to-peak, volts
    flat=dict(eeg=1e-6),
    reject_by_annotation=True,   # drop epochs touching BAD spans
    preload=True,
)
print(epochs)
print(f"{epochs.drop_log_stats():.1f}% dropped")
```

- `tmin`/`tmax` are seconds around the event. Time-frequency work needs extra padding on
  both sides for the wavelet length (`spectral-and-tfr.md`).
- `baseline=(None, 0)` (the default) subtracts each channel's mean from the epoch start to
  0 s, per epoch. `baseline=None` keeps the data as filtered; choose before looking at the
  results. `epochs.apply_baseline((-0.2, 0))` applies one later.
- `reject`/`flat` are peak-to-peak limits per channel type **in volts**. 75-150 µV after ICA
  is common, but the right value depends on the data: check the drop log and report
  retained trials per condition. `reject_tmin`/`reject_tmax` restrict the window checked.
  `scripts/erp_analysis.py --reject-uv auto` derives a robust per-recording limit.
- Rejecting on `eog` after ICA throws away the trials ICA just repaired; only do it if you
  did not remove ocular components.
- `event_repeated="error"` (default) refuses two events on one sample; use `"drop"` or
  `"merge"` deliberately. `on_missing` controls event_id keys with no events.
- Channels in `info["bads"]` stay in the epochs, flagged, and are ignored by `reject`.

## Selecting and balancing epochs

```python
target = epochs["target"]                         # by name
both = epochs[["standard", "target"]]             # several names
print(len(target), len(both))
```

- Names containing `/` act as tags: with `event_id={"auditory/left": 1, "visual/left": 3}`,
  `epochs["left"]` selects both. Avoid names that are tags of each other unless you mean it.
- Trial variables belong in `epochs.metadata` (a pandas DataFrame, one row per epoch);
  select with query strings such as `epochs["rt > 0.4 and correct"]`.
  `mne.epochs.make_metadata()` builds metadata from the events around each trial.

```python
balanced = epochs.copy()
balanced.equalize_event_counts(["standard", "target"])   # in place; method="mintime"
print({name: len(balanced[name]) for name in ("standard", "target")})
```

Equalize when comparing peak amplitudes or noise-sensitive measures between conditions
with different trial counts; mean amplitude is unbiased by trial count and does not need it.

`epochs.drop_log` holds one tuple per original event: `()` kept, channel names that
exceeded `reject`/`flat`, `BAD_…` annotation labels, `"IGNORED"` for events outside
`event_id`, or `"NO_DATA"` near the recording edges. `epochs.plot_drop_log()` draws it.

## Evoked responses

```python
evokeds = {name: epochs[name].average() for name in ("standard", "target")}
difference = mne.combine_evoked([evokeds["target"], evokeds["standard"]], weights=[1, -1])
print(difference.nave, difference.comment)
```

- `epochs.average(by_event_type=True)` returns a list with one Evoked per condition.
- `combine_evoked(..., weights="nave")` pools conditions weighted by trial count;
  `weights="equal"` averages them; `[1, -1]` makes a difference wave. `evoked.nave` tracks
  the effective number of trials.
- Group level: `mne.grand_average(list_of_subject_evokeds)` interpolates bad channels first
  (`interpolate_bads=True`).
- Global field power: `evoked.copy().pick("eeg").data.std(axis=0)` after an average
  reference, or `plot_compare_evokeds(..., combine="gfp")`.

## Plotting

```python
figures = mne.viz.plot_compare_evokeds(evokeds, picks="Pz", show=False)
joint = evokeds["target"].plot_joint(times=[0.1, 0.35], show=False)
topo = difference.plot_topomap(times=[0.35], average=0.1, ch_type="eeg", show=False)
image = epochs["target"].plot_image(picks="Pz", show=False)
```

`plot_compare_evokeds` draws confidence bands when each condition is a list of evokeds
(for example one per subject), `combine="mean"` averages a channel group, and
`average=` in `plot_topomap` averages a window around each time.

## Measuring components

Rules that keep ERP measures honest (Luck, 2014; Luck et al., 2021):

1. Fix the measurement window and electrodes **before** looking at condition differences:
   from prior work or from the average of all conditions (a collapsed localizer). Choosing
   the window where the difference is largest and then testing it is double dipping.
2. Prefer **mean amplitude** in the window. It is not biased by the number of trials.
   Peak amplitude grows as trials decrease (noise adds peaks) and peak latency is noisy.
3. For latency, prefer the **50% fractional-area latency**; for latency differences between
   conditions, score jackknife sub-averages (Kiesel et al., 2008).
4. Report the **standardized measurement error (SME)** of each mean amplitude: the SD of
   single-trial window means divided by sqrt(N). It is the data-quality number to compare
   across participants, conditions, and pipelines.

MNE 1.13 added these measures to `mne.stats.erp` (they return pandas DataFrames in volts and
seconds):

```python
from mne.stats import erp

target_evoked = evokeds["target"]
peak = erp.compute_peak(target_evoked, start=0.25, stop=0.45, picks="Pz", mode="pos")
area = erp.compute_area(target_evoked, start=0.25, stop=0.45, picks="Pz", mode="pos")
latency = erp.compute_frac_area_latency(
    target_evoked, frac=0.5, start=0.25, stop=0.45, picks="Pz", mode="pos"
)
sme = erp.compute_sme(epochs["target"].copy().pick("Pz"), start=0.25, stop=0.45)
mean_uv = target_evoked.copy().pick("Pz").crop(0.25, 0.45).data.mean() * 1e6
print(peak, latency, f"mean {mean_uv:.2f} uV, SME {sme[0] * 1e6:.2f} uV", sep="\n")
```

- `compute_sme` takes its window through `Epochs.get_data(tmin, tmax)`, which **excludes the
  sample at `stop`**, while `compute_peak`, `compute_area`, and `compute_frac_*` include it.
  Expect small differences, or pass `stop + 0.5 / sfreq` to `compute_sme` for a closed
  window. `scripts/erp_analysis.py` uses closed windows for every measure, and its test
  suite checks agreement with these functions.
- `mode="pos"`/`"neg"` search one polarity; with `strict=True` a window without that
  polarity raises. A peak on the window edge is not a peak: widen the window or use the
  mean amplitude.
- Before 1.13: `evoked.copy().pick("Pz").get_peak(tmin=0.25, tmax=0.45, mode="pos",
  return_amplitude=True)` returns `(channel, latency, amplitude)`. Without the `pick` it
  searches every channel.

`scripts/erp_analysis.py` produces all of the above per condition, difference wave, ROI,
and window in one tidy CSV, plus single-trial window means for mixed-effects models.

## Data frames

```python
wide = difference.to_data_frame(picks=["Cz", "Pz"])            # time + one column per channel, µV
long = epochs.to_data_frame(picks=["Pz"], long_format=True)    # one row per sample
print(wide.head(2), long.columns.tolist(), sep="\n")
```

`to_data_frame` scales EEG to µV by default (`scalings`). Long format feeds seaborn and
mixed models; for trial-level ERP statistics, window means per trial are usually what you
want (`scripts/erp_analysis.py --single-trial`).

## Saving

```python
epochs.save("sub-01_task-oddball_epo.fif", overwrite=True)
mne.write_evokeds("sub-01_task-oddball_ave.fif", list(evokeds.values()), overwrite=True)
reloaded = mne.read_evokeds("sub-01_task-oddball_ave.fif", condition="target")
```

File names should end in `-epo.fif`/`_epo.fif` and `-ave.fif`/`_ave.fif`. FIF stores
float32 by default, so reloaded values differ from memory in the seventh significant digit.
