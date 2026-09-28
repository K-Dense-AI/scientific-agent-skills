# Reading data, channels, montages, and events

Checked against MNE-Python 1.13.2. Code blocks run in order; file names are placeholders.

## Readers

`mne.io.read_raw(path)` dispatches on the extension. Call the specific reader when you
need one of its options.

| Format | Files | Reader | Watch out for |
| --- | --- | --- | --- |
| FIF (MNE, MEGIN) | `.fif`, `.fif.gz` | `read_raw_fif` | Keeps types, positions, projectors, annotations. Name files `*_raw.fif` or `*_eeg.fif`. |
| EDF / EDF+ | `.edf` | `read_raw_edf` | Every signal is typed EEG unless `eog=`, `misc=`, or `infer_types=True`. `units=` overrides a wrong header. |
| BioSemi | `.bdf` | `read_raw_bdf` | DC-coupled with large offsets; triggers live in `Status` (mask the upper bits). |
| GDF | `.gdf` | `read_raw_gdf` | Events arrive as annotations. |
| BrainVision | `.vhdr` + `.vmrk` + `.eeg` | `read_raw_brainvision` | Only `HEOGL`, `HEOGR`, `VEOGb` are typed EOG by default; markers become `Stimulus/S  1`-style annotations. |
| EEGLAB | `.set` (+ `.fdt`) | `read_raw_eeglab`, `read_epochs_eeglab` | `boundary` events mark cuts in the data; pass `montage_units` if positions look mis-scaled. |
| EGI | `.mff` folder, `.raw` | `read_raw_egi` | Names `E1…E256` match the `GSN-HydroCel-*` montages. |
| Neuroscan | `.cnt` | `read_raw_cnt` | Set `data_format` / `date_format` if autodetection fails. |
| CTF / KIT / BTi MEG | `.ds` folder, `.sqd`/`.con`, folder | `read_raw_ctf`, `read_raw_kit`, `read_raw_bti` | MEG units are T and T/m. |
| fNIRS | NIRx folder, `.snirf` | `read_raw_nirx`, `read_raw_snirf` | Analysis lives in MNE-NIRS. |
| BCI2000, MEF3 | `.dat`, `.mefd` | `read_raw_bci2k`, `read_raw_mef` | Added in 1.12. |

```python
import mne

raw = mne.io.read_raw("sub-01_task-oddball_eeg.vhdr", preload=True)
print(raw)                      # channels, duration, sfreq
print(raw.info)                 # everything MNE knows about the recording
print(raw.get_channel_types(unique=True), raw.info["sfreq"], raw.times[-1])
print(raw.annotations)          # event markers and BAD segments
```

`preload=False` (the default) reads lazily. Filtering, re-referencing, ICA application,
interpolation and resampling need the data in memory: pass `preload=True` or call
`raw.load_data()`. For a long file, crop before loading: `raw.crop(0, 300).load_data()`.

## Units: MNE stores volts

EEG, EOG, ECG, EMG, sEEG and ECoG data are volts; magnetometers tesla; gradiometers T/m.
Everything that takes an amplitude (`reject`, `flat`, thresholds in `annotate_amplitude`)
takes it in those units. Plots and `get_data(units=...)` convert on the way out.

```python
import numpy as np

cz_uv = raw.get_data(picks="Cz", units="uV")       # microvolts out
print(float(np.median(np.abs(cz_uv))))            # tens of uV is scalp EEG
```

Arrays from CSV, MATLAB, or a vendor SDK are usually microvolts. Scale them **before**
building the Raw object:

```python
data_uv = raw.get_data(picks="eeg", units="uV")   # stand-in for a microvolt array
info = mne.create_info(raw.copy().pick("eeg").ch_names, raw.info["sfreq"], ch_types="eeg")
raw_from_array = mne.io.RawArray(data_uv * 1e-6, info)   # volts
```

If a file was written with the wrong scale, the robust SD of band-passed EEG is volts-sized
instead of microvolts-sized (`scripts/inspect_recording.py` reports this as
`units_check`). Fix it once, early:

```python
wrong = raw_from_array.copy().apply_function(lambda x: x * 1e6, picks="eeg")  # the bug
fixed = wrong.copy().apply_function(lambda x: x * 1e-6, picks="eeg")         # the fix
```

`read_raw_brainvision(scale=...)` and `read_raw_edf(units=...)` fix the scale at read time.

## Channel types and names

Set channel types before filtering, bad-channel detection, ICA, or re-referencing. An EOG,
ECG, or trigger channel typed as EEG joins the average reference, the ICA decomposition,
and every EEG statistic. EDF, EEGLAB and exported BrainVision files routinely lose types.

```python
raw.set_channel_types({"VEOG": "eog"})
print(raw.get_channel_types(picks=["VEOG"]))
```

Valid types include `eeg`, `eog`, `ecg`, `emg`, `stim`, `misc`, `resp`, `gsr`,
`temperature`, `bio`, `seeg`, `ecog`, `dbs`, `mag`, `grad`, `hbo`, `hbr`.

EDF files that label signals as `EEG Fp1-REF`, `EOG ROC-REF`, `ECG EKG` can be typed and
renamed at read time: `infer_types=True` takes the type from the prefix and drops it.

```python
tuh = mne.io.read_raw_edf("tuh_style.edf", infer_types=True, preload=True)
print(tuh.ch_names[:3], tuh.get_channel_types(unique=True))  # ['FP1-REF', ...], eeg + eog
```

Then remove reference suffixes so names match a montage. `rename_channels` takes a dict or
a function:

```python
tuh.rename_channels(lambda name: name.removesuffix("-REF"))
```

PhysioNet EEGBCI files use padded labels such as `Fc5.` and `Cz..`;
`mne.datasets.eegbci.standardize(raw)` fixes them. `scripts/preprocess_eeg.py --rename-auto`
handles all of these patterns generically and logs every rename.

## Montages (channel positions)

Positions are needed for interpolation, topographic maps, CSD, adjacency in cluster
statistics, and source modelling.

**MNE 1.13 renamed the standard montages.** `standard_1005` and `standard_1020` now emit a
`FutureWarning` and are removed in 1.14; use `colin27_1005` / `colin27_1020` (same positions,
honest name for the Colin27 template head). New in 1.13: `fsaverage_1005`/`_1010`/`_1020`
(electrodes placed on the fsaverage scalp, the natural choice for template source modelling)
and idealised `spherical_1005`/`_1010`/`_1020`.

```python
print(mne.channels.get_builtin_montages())
montage = mne.channels.make_standard_montage("colin27_1005")
raw.set_montage(montage, match_case=False, on_missing="warn")
```

- `match_case=False` accepts `FP1`/`CZ` spellings.
- `on_missing="warn"` (or `"ignore"`) keeps going when some EEG channels have no position;
  those channels cannot be interpolated or drawn. Non-EEG channels (EOG, ECG, stim) never
  need a position.
- The colin27 montages include the old 10-20 names `T3`, `T4`, `T5`, `T6` at the positions of
  `T7`, `T8`, `P7`, `P8`, so old recordings match without renaming.
- **Do not use `match_alias=True` for old temporal names.** MNE's alias table
  (`mne._fiff.constants.CHANNEL_LOC_ALIASES` in 1.13) maps `T5 → T9` and `T6 → T10`,
  but in the 10-10 system T5/T6 are P7/P8. Rename explicitly if a montage lacks them.
- Vendor caps: `biosemi16…256`, `easycap-M1/M10/M43`, `GSN-HydroCel-32…257`, `EGI_256`,
  `brainproducts-RNP-BA-128`, `mgh60/70`, `artinis-*`. BioSemi BDF files often name channels
  `A1…B32`; rename them to the cap layout before matching `biosemi64`.

Digitized positions beat templates. Read them with `read_custom_montage` (`.elc`, `.sfp`,
`.loc`/`.locs`/`.eloc`, `.csd`, `.elp`, `.bvef`, `.hpts`) or the dedicated `read_dig_*`
functions, or build one from coordinates in metres:

```python
positions = montage.get_positions()["ch_pos"]
subset = {name: positions[name] for name in ("Fz", "Cz", "Pz")}
custom = mne.channels.make_dig_montage(ch_pos=subset, coord_frame="head")
print(custom)
```

Check the result visually with `raw.plot_sensors(show_names=True)`.

## Annotations and events

Annotations are time-stamped labels (`onset` in seconds, `duration`, `description`).
Descriptions starting with `BAD` mark spans that `Epochs(reject_by_annotation=True)`,
`compute_psd`, `ICA.fit` and `make_fixed_length_epochs` skip; descriptions starting with
`EDGE` or `BAD boundary` mark concatenation points that filters do not cross.

```python
bad = mne.Annotations(onset=[30.0], duration=[2.5], description=["BAD_movement"],
                      orig_time=raw.annotations.orig_time)
raw.set_annotations(raw.annotations + bad)
print(raw.annotations.to_data_frame(time_format=None).tail(3))
```

An events array is `(n_events, 3)` integers: absolute sample (it includes
`raw.first_samp`), a legacy column, and the event code.

```python
events, event_id = mne.events_from_annotations(raw)
print(event_id)   # {'standard': 1, 'target': 2}: codes are assigned, not read from labels
```

- The codes that `events_from_annotations` returns are arbitrary for ordinary labels
  (sorted order, so `'10'` can map to 1 and `'2'` to 2). Always use the returned `event_id`.
  For BrainVision files it parses `Stimulus/S  n` to `n` and `Response/R  n` to `1000 + n`.
- The default `regexp` drops `BAD…` and `EDGE…` labels. Select a subset with
  `event_id={"standard": 1, "target": 2}` or `regexp="^(standard|target)$"`.

Recordings with a trigger channel (FIF `STI 014`/`STI101`, BioSemi `Status`) need
`find_events`:

```python
stim_raw = mne.io.read_raw("sub-01_task-oddball_stim_raw.fif", preload=True)
events = mne.find_events(stim_raw, stim_channel="STI 014", shortest_event=1)
print(np.unique(events[:, 2], return_counts=True))
```

- BioSemi: `mne.find_events(raw, stim_channel="Status", mask=2**16 - 1)` keeps the trigger
  bits and drops the CMS/battery bits.
- `shortest_event` (samples) and `min_duration` (seconds) filter glitches; `consecutive`
  controls how back-to-back changes are read.

**Convert stim-channel events to annotations before resampling or cropping-and-saving.**
Annotations are times, so they survive resampling; stim channels become unreliable. The
right `first_samp` depends on whether the recording has a measurement date:

```python
orig_time = stim_raw.info["meas_date"]
annotations = mne.annotations_from_events(
    events,
    sfreq=stim_raw.info["sfreq"],
    event_desc={1: "standard", 2: "target"},
    first_samp=0 if orig_time is not None else stim_raw.first_samp,
    orig_time=orig_time,
)
stim_raw.set_annotations(annotations).drop_channels(["STI 014"])
stim_raw.resample(125.0)
events_125, event_id_125 = mne.events_from_annotations(stim_raw)
```

With a measurement date, annotation onsets count from `meas_date`, and event samples already
include `first_samp`; without one, onsets count from the first sample. Passing the wrong
`first_samp` shifts every event by `first_samp / sfreq` after any crop.

Merge codes into one condition with `mne.merge_events(events, [1, 3], 13)`, and keep
trial-level variables (response time, stimulus features) in `Epochs.metadata`;
`mne.epochs.make_metadata()` builds it from the events around each trial.

## Cropping, concatenating, anonymizing

```python
first = raw.copy().crop(tmin=0.0, tmax=60.0)
second = raw.copy().crop(tmin=60.0, tmax=120.0)
joined = mne.concatenate_raws([first, second])
print([d for d in joined.annotations.description if "boundary" in d.lower()][:2])
anonymous = joined.copy().anonymize()   # clears subject_info, shifts meas_date
```

Concatenation inserts `BAD boundary` + `EDGE boundary` annotations so filters and epochs do
not straddle the join. Crop times are seconds from the start of the (current) data.

## Exporting and BIDS

```python
raw.export("recording_export.vhdr", fmt="brainvision", overwrite=True)   # needs pybv
```

`raw.export()` / `mne.export.export_raw()` write EDF (needs `edfio`), BrainVision (`pybv`)
and EEGLAB (`eeglabio`). None of them round-trips everything: EDF loses channel types and
positions and quantizes to 16 bits (1.13 fixed a bug that altered values; pass
`physical_range` / `digital_range` if the automatic range clips), BrainVision and EEGLAB
exports come back with every channel typed EEG. Keep a FIF copy as the lossless
derivative.

For BIDS datasets use MNE-BIDS (`pip install mne-bids`), which reads sidecars, events,
channel types, and electrodes for you:

```python
from mne_bids import BIDSPath, read_raw_bids

bids_path = BIDSPath(subject="01", task="oddball", datatype="eeg", root="bids_root")
bids_raw = read_raw_bids(bids_path)
```

`write_raw_bids()` goes the other way. The `bids` skill covers dataset layout and validation.
