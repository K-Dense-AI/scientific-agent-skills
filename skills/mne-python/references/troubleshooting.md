# Troubleshooting

Messages are quoted from MNE-Python 1.13.2 (first line only).

| Message | Cause | Fix |
| --- | --- | --- |
| `RuntimeError: By default, MNE does not load data into main memory ... inst.filter requires raw data to be loaded.` | Lazy read (`preload=False`) | `mne.io.read_raw(path, preload=True)` or `raw.load_data()`; crop first for long files. |
| `ValueError: DigMontage is only a subset of info. There is 1 channel position not present in the DigMontage.` | A channel name is not in the montage (case, `EEG ` prefix, `-REF` suffix, padding dots, vendor names) | Rename (`rename_channels`), `match_case=False`, or `on_missing="warn"` for channels that truly have no position. `scripts/inspect_recording.py` lists the renames. |
| `FutureWarning: Montage name 'standard_1020' is deprecated and will be removed in MNE 1.14. Use 'colin27_1020' instead.` | 1.13 montage rename | Use `colin27_1020` / `colin27_1005` (same positions). |
| `ValueError: No stim channels found, but the raw object has annotations. Consider using mne.events_from_annotations to convert these to events.` | Events are annotations (EDF, BrainVision, EEGLAB, GDF) | `events, event_id = mne.events_from_annotations(raw)`. |
| `ValueError: No matching events found for foo (event id 99)` | `event_id` has a code absent from `events` | Print `np.unique(events[:, 2])` and the `event_id` returned by `events_from_annotations`; codes are not your labels. `on_missing="warn"` if a condition may legitimately be empty. |
| `RuntimeError: Event time samples were not unique. Consider setting the event_repeated parameter.` | Two events on one sample | Decide: `event_repeated="drop"` (keep first) or `"merge"` (combined code), or fix the event list. |
| `RuntimeWarning: All epochs were dropped!` then `RuntimeError: epochs.average() can't run because this Epochs-object is empty.` | Rejection thresholds wrong for the data: units (µV stored as V), unfiltered drift, a dead or noisy channel, EOG rejection after ICA | Check `epochs.plot_drop_log()`; verify units with `scripts/inspect_recording.py`; high-pass first; mark bad channels; drop `eog` from `reject`; or `--reject-uv auto` in `scripts/erp_analysis.py`. |
| `RuntimeWarning: filter_length (8251) is longer than the signal (2501), distortion is likely.` | High-pass too low for a short recording or segment (0.1 Hz needs ~33 s) | Filter the continuous recording before cropping or epoching, or raise `l_freq`. |
| `RuntimeWarning: Channel(s) ['T8'] have invalid sensor position(s) and cannot be interpolated.` / `RuntimeError: Cannot fit headshape without digitization, info["dig"] is None` | Interpolation without positions | `raw.set_montage(...)` first; channels without a position stay bad (`interpolate_bads(exclude=[...])`). |
| `ValueError: No negative values encountered. Cannot operate in neg mode.` | `get_peak(mode="neg")` / `mne.stats.erp` with `strict=True` on a window without that polarity | Widen or move the window, use the mean amplitude, or `strict=False`. |
| `RuntimeWarning: This filename (...) does not conform to MNE naming conventions.` | FIF name suffix | Raw `*_raw.fif` / `*_eeg.fif`, epochs `*_epo.fif`, evoked `*_ave.fif`, ICA `*_ica.fif`. |
| `ConvergenceWarning: FastICA did not converge.` (scikit-learn) | FastICA hit `max_iter` | `method="picard"` with `fit_params=dict(ortho=False, extended=True)`; fewer components; fit on 1 Hz high-passed data without bad channels. |
| `ssl.SSLCertVerificationError ... CERTIFICATE_VERIFY_FAILED` during `mne.datasets.*` | Python without a CA bundle (common with python.org builds on macOS) | Run `Install Certificates.command`, or `export SSL_CERT_FILE="$(python -c 'import certifi; print(certifi.where())')"`. |
| `RuntimeError: Could not use input() to get a response to: ... as the default EEGBCI dataset path in the mne-python config [y]/n?` | A dataset fetcher asks interactively whether to save its path; non-interactive agents crash or hang | Pass `update_path=False` (or `True`) to `load_data`/`data_path`, or set the path once with `mne.set_config`. |
| `RuntimeError: No average reference for the EEG channels has been set. Use inst.set_eeg_reference(projection=True) to do so.` | `EOGRegression` and inverse modelling need referenced EEG | `raw.set_eeg_reference("average")` (or `projection=True` for source work) before the call. |
| `ModuleNotFoundError: nibabel is required to Reading labels from parcellations` | FreeSurfer surfaces and annotations need nibabel | `pip install nibabel`. |
| `ValueError: source space does not contain any vertices for 1 label:` | The `unknown` (medial-wall) label of `aparc` has no source vertices | Drop labels whose name starts with `unknown`, or `extract_label_time_course(..., allow_empty=True)`. |

## Silent problems (no error at all)

- **Microvolts stored as volts.** Everything runs; thresholds reject nothing or everything,
  topographies look fine. `scripts/inspect_recording.py` flags the scale.
- **EOG/ECG/trigger channels typed as EEG** after EDF/BrainVision/EEGLAB import enter the
  average reference and ICA. Set types first.
- **`raw.filter()` without `picks`** leaves EOG/ECG unfiltered.
- **`raw.set_annotations(raw.annotations + other)` on a cropped recording without a
  measurement date** moves every existing annotation by `raw.first_time` (MNE 1.13).
  Append in place instead (`io-and-channels.md`).
- **Dropping stim channels before every one of them is converted** loses the triggers. An
  unrelated annotation, such as a recording-start comment, is no evidence that they were.
- **`annotate_amplitude(peak=...)`** thresholds sample-to-sample jumps, not peak-to-peak.
- **`match_alias=True`** places `T5`/`T6` at T9/T10 instead of P7/P8.
- **Event codes from `events_from_annotations`** are assigned in sorted label order, not
  parsed from numeric labels (except BrainVision `Stimulus/S  n`).
- **Condition names with `/`** select by tag: `epochs["left"]` matches `"audio/left"` too.
- **Trial-count differences** bias peak amplitudes; equalize or use mean amplitude.
- **Baseline windows** that overlap the epoch edge in time-frequency analysis carry wavelet
  edge artifacts; pad the epochs and crop after the transform.
- **BioSemi triggers** include status bits above bit 16 unless `mask=2**16 - 1`.
- **Float32 FIF storage** changes values in the seventh significant digit on reload; do not
  test saved data for exact equality.

## Performance

- Crop, pick, and resample (after low-pass) early; `preload=False` plus `raw.crop()` keeps
  memory low for inspection.
- `n_jobs=-1` parallelizes filtering, TFR, and some decoders; ICA speeds up with `decim`.
- Time-frequency: `decim`, fewer frequencies, `average=True` unless single trials are needed.
