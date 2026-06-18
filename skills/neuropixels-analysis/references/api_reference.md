# API Reference (SpikeInterface)

Quick reference for the SpikeInterface functions used throughout this skill. Import with:

```python
import spikeinterface.full as si
import spikeinterface.curation as sc
import spikeinterface.widgets as sw
```

All examples target SpikeInterface ≥ 0.104. Set global parallelization once:

```python
si.set_global_job_kwargs(n_jobs=-1, chunk_duration="1s", progress_bar=True)
```

## Loading

### Inspect streams

```python
stream_names, stream_ids = si.get_neo_streams("spikeglx", "/path/to/run_g0/")
# stream_names -> ['imec0.ap', 'imec0.lf', 'nidq']
```

### Readers

```python
si.read_spikeglx(folder_path, stream_name="imec0.ap", load_sync_channel=False)
si.read_openephys(folder_path, stream_name=None)
si.read_nwb(file_path)
```

Prefer `stream_name` (a value from `get_neo_streams`) over `stream_id`.

### Recording introspection

```python
recording.get_num_channels()
recording.get_total_duration()        # seconds
recording.get_sampling_frequency()    # Hz
recording.get_channel_locations()
recording.get_probe()
recording.frame_slice(start_frame, end_frame)
```

## Preprocessing

```python
si.highpass_filter(recording, freq_min=400.0)
si.bandpass_filter(recording, freq_min=300.0, freq_max=6000.0)
si.phase_shift(recording)                                  # ADC phase correction (NP 1.0)
si.detect_bad_channels(recording)                          # -> (bad_channel_ids, channel_labels)
recording.remove_channels(bad_channel_ids)
si.common_reference(recording, operator="median", reference="global")
si.highpass_spatial_filter(recording)                      # IBL-style destriping
si.get_noise_levels(recording, return_in_uV=False)
recording.save(folder="preprocessed/", format="binary")
```

> `detect_bad_channels` returns a 2-tuple; always unpack both values.

## Drift detection and motion correction

```python
from spikeinterface.sortingcomponents.peak_detection import detect_peaks
from spikeinterface.sortingcomponents.peak_localization import localize_peaks

peaks = detect_peaks(rec, method="locally_exclusive", noise_levels=noise_levels,
                     detect_threshold=5, radius_um=50.0)
peak_locations = localize_peaks(rec, peaks, method="center_of_mass")

# One-call correction with a preset
rec_corrected = si.correct_motion(rec, preset="nonrigid_fast_and_accurate", folder="motion/")
```

**Presets:** `rigid_fast`, `kilosort_like`, `nonrigid_accurate`,
`nonrigid_fast_and_accurate` (recommended default), `dredge`, `dredge_fast`.

## Spike sorting

```python
si.installed_sorters()
si.available_sorters()
si.get_default_sorter_params("kilosort4")

sorting = si.run_sorter(
    "kilosort4",            # sorter name
    recording,
    folder="ks4_output",   # NOT output_folder (deprecated)
    verbose=True,
    # sorter-specific kwargs, e.g. Th_universal=9, Th_learned=8, nblocks=5, batch_size=60000
)

# Containerized external sorters (no local install needed)
si.run_sorter("kilosort2_5", recording, folder="ks25/", docker_image=True)

# Read a sorter folder back
sorting = si.read_sorter_folder("ks4_output")
```

**Sorting introspection:**

```python
sorting.unit_ids
sorting.get_total_num_spikes()
sorting.get_unit_spike_train(unit_id)
sorting.select_units(unit_ids)
sorting.to_spike_vector()
```

## Postprocessing: SortingAnalyzer

```python
analyzer = si.create_sorting_analyzer(
    sorting, recording,
    sparse=True,
    format="binary_folder",   # or "memory" / "zarr"
    folder="analyzer/",
)

# Extensions (order matters: random_spikes -> waveforms -> templates -> ...)
analyzer.compute("random_spikes", method="uniform", max_spikes_per_unit=500)
analyzer.compute("waveforms", ms_before=1.0, ms_after=2.0)
analyzer.compute("templates", operators=["average", "std"])
analyzer.compute("noise_levels")
analyzer.compute("spike_amplitudes")
analyzer.compute("correlograms", window_ms=50.0, bin_ms=1.0)
analyzer.compute("unit_locations", method="monopolar_triangulation")
analyzer.compute("spike_locations", method="center_of_mass")
analyzer.compute("template_similarity")
analyzer.compute("principal_components", n_components=5, mode="by_channel_local")

# Or compute several at once
analyzer.compute(["random_spikes", "waveforms", "templates", "noise_levels"])

# Access extension data
analyzer.get_extension("quality_metrics").get_data()
analyzer.get_extension("templates").get_unit_template(unit_id, operator="average")

# Persist / reload / subset
si.load_sorting_analyzer("analyzer/")
analyzer.select_units(unit_ids, folder="analyzer_clean/", format="binary_folder")
analyzer.remove_units(unit_ids)
```

## Quality metrics

```python
metric_names = ["firing_rate", "presence_ratio", "snr", "isi_violation",
                "amplitude_cutoff", "amplitude_cv", "sliding_rp_violation"]
analyzer.compute("quality_metrics", metric_names=metric_names)
metrics = analyzer.get_extension("quality_metrics").get_data()

# Equivalent standalone helper
metrics = si.compute_quality_metrics(analyzer, metric_names=metric_names)
```

**Common columns:** `snr`, `firing_rate`, `presence_ratio`, `amplitude_cutoff`,
`isi_violations_ratio`, `isi_violations_count`. PCA-based metrics
(`isolation_distance`, `l_ratio`, `d_prime`, `nn_hit_rate`) require
`analyzer.compute("principal_components")` first.

## Curation

### Threshold-based

```python
query = "(amplitude_cutoff < 0.1) & (isi_violations_ratio < 0.5) & (presence_ratio > 0.9)"
good_unit_ids = metrics.query(query).index.values
clean = sorting.select_units(good_unit_ids)
```

### Model-based (UnitRefine / Hugging Face)

```python
import spikeinterface.curation as sc

labels = sc.model_based_label_units(
    sorting_analyzer=analyzer,
    repo_id="SpikeInterface/UnitRefine_noise_neural_classifier",
    trust_model=True,
)
# labels -> DataFrame with 'prediction' and 'probability' columns

# Load a model object explicitly (e.g. to inspect feature_names_in_)
model, model_info = sc.load_model(repo_id="SpikeInterface/toy_tetrode_model", trusted=["numpy.dtype"])
```

### Manual edits

```python
from spikeinterface.curation import CurationSorting
cur = CurationSorting(sorting)
cur.remove_units(noise_unit_ids)
sorting_curated = cur.sorting
```

## Visualization (widgets)

```python
sw.plot_probe_map(recording, with_channel_ids=True)
sw.plot_traces({"filtered": rec1, "cmr": rec2}, backend="matplotlib", clim=(-50, 50))
si.plot_drift_raster_map(peaks=peaks, peak_locations=peak_locations, recording=rec, clim=(-50, 50))
sw.plot_unit_waveforms(analyzer, unit_ids=[0])
sw.plot_unit_templates(analyzer, unit_ids=[0, 1, 2])
sw.plot_autocorrelograms(analyzer, unit_ids=[0])
sw.plot_amplitudes(analyzer, unit_ids=[0], plot_histograms=True)
sw.plot_unit_locations(analyzer)
si.plot_sorting_summary(analyzer, backend="sortingview")  # web-based viewer
```

See [plotting_guide.md](plotting_guide.md) for publication-quality figure recipes.

## Export

```python
si.export_to_phy(analyzer, output_folder="phy_export/",
                 compute_pc_features=True, compute_amplitudes=True, copy_binary=True)
si.export_report(analyzer, "report/", format="png")

from spikeinterface.exporters import export_to_nwb
export_to_nwb(analyzer, "output.nwb")

si.read_phy("phy_export/")   # load Phy curation back
```

> Note: `export_to_phy` / `export_report` take `output_folder` — this is correct and
> distinct from `run_sorter`/`create_sorting_analyzer`, which take `folder`.
