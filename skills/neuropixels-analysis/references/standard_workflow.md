# Standard Neuropixels Analysis Workflow

Complete step-by-step guide for analyzing Neuropixels recordings from raw data to curated
units, using the SpikeInterface API directly.

## Overview

```
Raw Recording → Preprocessing → Motion Correction → Spike Sorting →
Postprocessing → Quality Metrics → Curation → Export
```

```python
import spikeinterface.full as si
import spikeinterface.curation as sc

si.set_global_job_kwargs(n_jobs=-1, chunk_duration="1s", progress_bar=True)
```

## 1. Data Loading

### Supported formats

```python
# Inspect streams first
stream_names, stream_ids = si.get_neo_streams("spikeglx", "/path/to/run_g0/")

# SpikeGLX (most common)
recording = si.read_spikeglx("/path/to/run_g0/", stream_name="imec0.ap", load_sync_channel=False)

# Open Ephys
recording = si.read_openephys("/path/to/experiment/")

# NWB
recording = si.read_nwb("/path/to/file.nwb")
```

### Verify recording properties

```python
print(f"Channels: {recording.get_num_channels()}")
print(f"Duration: {recording.get_total_duration():.1f}s")
print(f"Sampling rate: {recording.get_sampling_frequency()}Hz")
print(f"Probe: {recording.get_probe()}")
locations = recording.get_channel_locations()
```

## 2. Preprocessing

### Standard chain (IBL-style)

```python
rec = si.highpass_filter(recording, freq_min=400.0)
bad_channel_ids, channel_labels = si.detect_bad_channels(rec)
rec = rec.remove_channels(bad_channel_ids)
rec = si.phase_shift(rec)                                   # ADC phase (NP 1.0)
rec = si.common_reference(rec, operator="median", reference="global")
```

A bandpass alternative (some labs prefer an explicit passband):

```python
rec = si.bandpass_filter(recording, freq_min=300.0, freq_max=6000.0)
rec = si.phase_shift(rec)
bad_channel_ids, _ = si.detect_bad_channels(rec)
rec = rec.remove_channels(bad_channel_ids)
rec = si.common_reference(rec, operator="median", reference="global")
```

### Spatial destriping (strong artifacts)

```python
rec = si.highpass_filter(recording, freq_min=400.0)
rec = si.phase_shift(rec)
rec = si.highpass_spatial_filter(rec)                       # destriping
rec = si.common_reference(rec, operator="median", reference="global")
```

### Save preprocessed data

```python
rec = rec.save(folder="preprocessed/", format="binary")
```

## 3. Motion/Drift Correction

### Check whether correction is needed

```python
from spikeinterface.sortingcomponents.peak_detection import detect_peaks
from spikeinterface.sortingcomponents.peak_localization import localize_peaks

noise_levels = si.get_noise_levels(rec, return_in_uV=False)
peaks = detect_peaks(rec, method="locally_exclusive", noise_levels=noise_levels,
                     detect_threshold=5, radius_um=50.0)
peak_locations = localize_peaks(rec, peaks, method="center_of_mass")

si.plot_drift_raster_map(peaks=peaks, peak_locations=peak_locations, recording=rec, clim=(-50, 50))
```

### Apply correction

```python
# One-call correction with a preset
rec_corrected = si.correct_motion(rec, preset="nonrigid_fast_and_accurate", folder="motion/")
```

See [MOTION_CORRECTION.md](MOTION_CORRECTION.md) for the full estimate/interpolate pipeline
and DREDge usage.

## 4. Spike Sorting

### Recommended: Kilosort4

```python
sorting = si.run_sorter("kilosort4", rec_corrected, folder="sorting_KS4/", verbose=True)

# With custom parameters
sorting = si.run_sorter(
    "kilosort4", rec_corrected, folder="sorting_KS4/",
    nblocks=5,           # non-rigid drift blocks
    Th_universal=9,      # detection threshold
    Th_learned=8,
    batch_size=60000,
)
```

### Alternative sorters

```python
sorting = si.run_sorter("spykingcircus2", rec_corrected, folder="sc2/")   # CPU
sorting = si.run_sorter("tridesclous2", rec_corrected, folder="tdc2/")    # CPU
sorting = si.run_sorter("mountainsort5", rec_corrected, folder="ms5/")    # CPU
```

### Compare multiple sorters

```python
sortings = {s: si.run_sorter(s, rec_corrected, folder=f"{s}/")
            for s in ["kilosort4", "spykingcircus2"]}

comparison = si.compare_multiple_sorters(list(sortings.values()),
                                         name_list=list(sortings.keys()))
agreement = comparison.get_agreement_sorting(minimum_agreement_count=2)
```

## 5. Postprocessing

### Create analyzer and compute extensions

```python
analyzer = si.create_sorting_analyzer(sorting, rec_corrected, sparse=True,
                                      format="binary_folder", folder="analyzer/")

analyzer.compute("random_spikes", method="uniform", max_spikes_per_unit=500)
analyzer.compute("waveforms", ms_before=1.0, ms_after=2.0)
analyzer.compute("templates", operators=["average", "std"])
analyzer.compute("noise_levels")
analyzer.compute("spike_amplitudes")
analyzer.compute("correlograms", window_ms=50.0, bin_ms=1.0)
analyzer.compute("unit_locations", method="monopolar_triangulation")
analyzer.compute("template_similarity")
```

## 6. Quality Metrics

```python
metric_names = ["snr", "isi_violation", "presence_ratio", "amplitude_cutoff",
                "firing_rate", "amplitude_cv", "sliding_rp_violation"]
analyzer.compute("quality_metrics", metric_names=metric_names)
metrics = analyzer.get_extension("quality_metrics").get_data()
print(metrics.head())
```

### Key metrics

| Metric (column) | Good value | Description |
|-----------------|------------|-------------|
| `snr` | > 5 | Signal-to-noise ratio |
| `isi_violations_ratio` | < 0.5 (strict: < 0.01) | Refractory period violations |
| `presence_ratio` | > 0.9 | Fraction of recording with spikes |
| `amplitude_cutoff` | < 0.1 | Estimated missed spikes |
| `firing_rate` | > 0.1 Hz | Average firing rate |

## 7. Curation

### Threshold-based

```python
query = "(amplitude_cutoff < 0.1) & (isi_violations_ratio < 0.5) & (presence_ratio > 0.9)"
good_unit_ids = metrics.query(query).index.values
```

For `allen` / `ibl` / `strict` presets in one call, use `scripts/compute_metrics.py`.

### Model-based (UnitRefine)

```python
noise_labels = sc.model_based_label_units(
    sorting_analyzer=analyzer,
    repo_id="SpikeInterface/UnitRefine_noise_neural_classifier",
    trust_model=True,
)
neural = analyzer.remove_units(noise_labels[noise_labels["prediction"] == "noise"].index)
sua_mua = sc.model_based_label_units(
    sorting_analyzer=neural,
    repo_id="SpikeInterface/UnitRefine_sua_mua_classifier",
    trust_model=True,
)
```

### AI-assisted (uncertain units)

Read API keys from the environment — never hardcode them (see [AI_CURATION.md](AI_CURATION.md)):

```python
import os
from anthropic import Anthropic

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
uncertain = metrics.query("snr > 3 and snr < 8").index.tolist()
# Render each uncertain unit's summary image and ask the model to classify it.
```

## 8. Export Results

### Export to Phy

```python
analyzer_clean = analyzer.select_units(good_unit_ids, folder="analyzer_clean/", format="binary_folder")
si.export_to_phy(analyzer_clean, output_folder="phy_export/",
                 compute_pc_features=True, compute_amplitudes=True)
```

### Export to NWB

```python
from spikeinterface.exporters import export_to_nwb
export_to_nwb(analyzer_clean, "results.nwb")
```

### Save quality summary

```python
metrics.to_csv("quality_metrics.csv")

import json
labels = {int(uid): ("good" if uid in good_unit_ids else "other") for uid in metrics.index}
with open("curation_labels.json", "w") as f:
    json.dump(labels, f, indent=2)

si.export_report(analyzer_clean, "report/", format="png")
```

## Full Pipeline Example

```python
import spikeinterface.full as si

si.set_global_job_kwargs(n_jobs=-1, chunk_duration="1s", progress_bar=True)

# Load
recording = si.read_spikeglx("/data/experiment/", stream_name="imec0.ap", load_sync_channel=False)

# Preprocess
rec = si.highpass_filter(recording, freq_min=400.0)
bad_channel_ids, _ = si.detect_bad_channels(rec)
rec = rec.remove_channels(bad_channel_ids)
rec = si.phase_shift(rec)
rec = si.common_reference(rec, operator="median", reference="global")

# Motion correction
rec = si.correct_motion(rec, preset="nonrigid_fast_and_accurate", folder="motion/")

# Sort
sorting = si.run_sorter("kilosort4", rec, folder="ks4/")

# Postprocess + metrics
analyzer = si.create_sorting_analyzer(sorting, rec, sparse=True, format="binary_folder", folder="analyzer/")
analyzer.compute(["random_spikes", "waveforms", "templates", "noise_levels",
                  "spike_amplitudes", "correlograms", "unit_locations"])
analyzer.compute("quality_metrics",
                 metric_names=["snr", "isi_violation", "presence_ratio", "amplitude_cutoff", "firing_rate"])
metrics = analyzer.get_extension("quality_metrics").get_data()

# Curate
query = "(amplitude_cutoff < 0.1) & (isi_violations_ratio < 0.5) & (presence_ratio > 0.9)"
good_unit_ids = metrics.query(query).index.values
print(f"Good units: {len(good_unit_ids)}/{len(metrics)}")
```

Or run it as a script:

```bash
python scripts/neuropixels_pipeline.py /data/experiment/ output/ --sorter kilosort4 --curation allen
```

## Tips for Success

1. **Always visualize drift** before deciding on motion correction.
2. **Save preprocessed data** to avoid recomputing (and Kilosort needs a binary file).
3. **Compare multiple sorters** for critical experiments.
4. **Review uncertain units manually** — don't trust automated curation blindly.
5. **Document parameters and model repo IDs** for reproducibility.
6. **Use a GPU** for Kilosort4.
