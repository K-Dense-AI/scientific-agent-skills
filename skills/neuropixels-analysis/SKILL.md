---
name: neuropixels-analysis
description: Analyze Neuropixels extracellular recordings end-to-end with SpikeInterface. Covers loading SpikeGLX/Open Ephys/NWB data, preprocessing, drift/motion correction, Kilosort4 (and CPU) spike sorting, quality metrics, and unit curation (threshold-based, model-based UnitRefine, and AI-assisted visual review). Use when working with Neuropixels 1.0/2.0 recordings, spike sorting, or extracellular electrophysiology analysis.
license: MIT license
required_environment_variables: [{"name": "ANTHROPIC_API_KEY", "prompt": "For optional Claude API calls.", "required_for": "optional features"}]
metadata: {"version": "2.1", "skill-author": "K-Dense Inc.", "openclaw": {"primaryEnv": "ANTHROPIC_API_KEY", "envVars": [{"name": "ANTHROPIC_API_KEY", "required": false, "description": "For optional Claude API calls."}]}}
---

# Neuropixels Data Analysis

## Overview

Toolkit for analyzing Neuropixels high-density neural recordings using current best
practices from [SpikeInterface](https://spikeinterface.readthedocs.io/), the Allen
Institute, and the International Brain Laboratory (IBL). It covers the full workflow from
raw data to publication-ready curated units.

All examples use the real SpikeInterface API (`spikeinterface.full as si`) plus the
companion curation module (`spikeinterface.curation as sc`). The skill ships runnable
scripts in `scripts/` and a copy-and-edit template in `assets/` that implement this
workflow directly on top of SpikeInterface — there is no separate package to install
beyond the dependencies listed under [Installation](#installation).

## When to Use This Skill

This skill should be used when:
- Working with Neuropixels recordings (`.ap.bin`, `.lf.bin`, `.meta` files)
- Loading data from SpikeGLX, Open Ephys, or NWB formats
- Preprocessing neural recordings (filtering, common reference, bad-channel detection)
- Detecting and correcting motion/drift
- Running spike sorting (Kilosort4, SpykingCircus2, Mountainsort5, Tridesclous2)
- Computing quality metrics (SNR, ISI violations, presence ratio, amplitude cutoff)
- Curating units (threshold-based, model-based, or AI-assisted)
- Creating visualizations and exporting to Phy or NWB

## Supported Hardware & Formats

| Probe | Electrodes | Channels | Notes |
|-------|-----------|----------|-------|
| Neuropixels 1.0 | 960 | 384 | Use `phase_shift` for ADC correction |
| Neuropixels 2.0 (single) | 1280 | 384 | Denser geometry |
| Neuropixels 2.0 (4-shank) | 5120 | 384 | Multi-region recording |

| Format | Extension | Reader |
|--------|-----------|--------|
| SpikeGLX | `.ap.bin`, `.lf.bin`, `.meta` | `si.read_spikeglx()` |
| Open Ephys | `.continuous`, `.oebin` | `si.read_openephys()` |
| NWB | `.nwb` | `si.read_nwb()` |

## Quick Start

### Import and configure parallel processing

```python
import spikeinterface.full as si

# Global job kwargs are reused by all parallelizable steps
si.set_global_job_kwargs(n_jobs=-1, chunk_duration="1s", progress_bar=True)
```

### Loading data

```python
# Inspect available streams first
stream_names, stream_ids = si.get_neo_streams("spikeglx", "/path/to/run_g0/")
print(stream_names)  # e.g. ['imec0.ap', 'imec0.lf', 'nidq']

# SpikeGLX (most common) — select the AP stream by name
recording = si.read_spikeglx("/path/to/run_g0/", stream_name="imec0.ap", load_sync_channel=False)

# Open Ephys
recording = si.read_openephys("/path/to/Record_Node_101/")

# For quick iteration, slice the first 60 s
fs = recording.get_sampling_frequency()
recording_sub = recording.frame_slice(0, int(60 * fs))
```

### Full pipeline (bundled script)

The repository ships an end-to-end pipeline built on SpikeInterface:

```bash
python scripts/neuropixels_pipeline.py /path/to/spikeglx/data output/ --sorter kilosort4 --curation allen
```

It performs load → preprocess → drift check → optional motion correction → sorting →
postprocessing → quality metrics → curation → export. Read the steps below to run them
interactively or customize the pipeline.

## Standard Analysis Workflow

### 1. Preprocessing

Recommended chain, following the SpikeInterface Neuropixels how-to (IBL-style destriping
with channel removal + common reference):

```python
rec = si.highpass_filter(recording, freq_min=400.0)
bad_channel_ids, channel_labels = si.detect_bad_channels(rec)
rec = rec.remove_channels(bad_channel_ids)
rec = si.phase_shift(rec)  # ADC phase correction (Neuropixels 1.0)
rec = si.common_reference(rec, operator="median", reference="global")
```

Save the preprocessed recording (Kilosort needs a binary file, and it speeds up reuse):

```python
rec = rec.save(folder="preprocessed/", format="binary")
```

### 2. Check and correct drift

Always inspect drift before sorting:

```python
from spikeinterface.sortingcomponents.peak_detection import detect_peaks
from spikeinterface.sortingcomponents.peak_localization import localize_peaks

noise_levels = si.get_noise_levels(rec, return_in_uV=False)
peaks = detect_peaks(rec, method="locally_exclusive", noise_levels=noise_levels,
                     detect_threshold=5, radius_um=50.0)
peak_locations = localize_peaks(rec, peaks, method="center_of_mass")

# Visualize the drift raster
si.plot_drift_raster_map(peaks=peaks, peak_locations=peak_locations,
                         recording=rec, clim=(-50, 50))
```

Apply correction if needed (presets: `rigid_fast`, `kilosort_like`,
`nonrigid_accurate`, `nonrigid_fast_and_accurate`, `dredge`, `dredge_fast`):

```python
rec_corrected = si.correct_motion(rec, preset="nonrigid_fast_and_accurate", folder="motion/")
```

### 3. Spike sorting

```python
# Kilosort4 (recommended, requires a CUDA GPU)
sorting = si.run_sorter("kilosort4", rec_corrected, folder="ks4_output")

# CPU alternatives (internally developed, no external install)
sorting = si.run_sorter("spykingcircus2", rec_corrected, folder="sc2_output")
sorting = si.run_sorter("tridesclous2", rec_corrected, folder="tdc2_output")
sorting = si.run_sorter("mountainsort5", rec_corrected, folder="ms5_output")

# External sorters can run in containers without local install
sorting = si.run_sorter("kilosort2_5", rec_corrected, folder="ks25_output", docker_image=True)

print(si.installed_sorters())
```

> Note: `run_sorter` uses the `folder=` argument. The older `output_folder=` is deprecated.

### 4. Postprocessing

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

metric_names = ["firing_rate", "presence_ratio", "snr", "isi_violation", "amplitude_cutoff"]
analyzer.compute("quality_metrics", metric_names=metric_names)
metrics = analyzer.get_extension("quality_metrics").get_data()
```

### 5. Curation by metric thresholds

```python
# Allen-style query (note: column is isi_violations_ratio)
query = "(amplitude_cutoff < 0.1) & (isi_violations_ratio < 0.5) & (presence_ratio > 0.9)"
good_unit_ids = metrics.query(query).index.values
```

For reusable, multi-threshold logic with `allen` / `ibl` / `strict` presets, use the
bundled `scripts/compute_metrics.py`. See
[references/AUTOMATED_CURATION.md](references/AUTOMATED_CURATION.md) for details and the
Bombcell / UnitMatch tools.

### 6. Model-based curation (UnitRefine)

SpikeInterface can apply pretrained machine-learning classifiers from Hugging Face via the
`spikeinterface.curation` module. The UnitRefine models were trained on real Neuropixels
data (V1, SC, ALM):

```python
import spikeinterface.curation as sc

# 1) noise vs neural
noise_labels = sc.model_based_label_units(
    sorting_analyzer=analyzer,
    repo_id="SpikeInterface/UnitRefine_noise_neural_classifier",
    trust_model=True,
)
neural = analyzer.remove_units(noise_labels[noise_labels["prediction"] == "noise"].index)

# 2) single-unit (sua) vs multi-unit (mua) on the surviving units
sua_mua_labels = sc.model_based_label_units(
    sorting_analyzer=neural,
    repo_id="SpikeInterface/UnitRefine_sua_mua_classifier",
    trust_model=True,
)
```

Each call returns a DataFrame with `prediction` and `probability` (confidence) per unit.
`trust_model=True` (or an explicit `trusted=[...]` list) is required to load the `.skops`
model — only load models from sources you trust. Models trained on other brain
areas/datasets may not transfer; validate against a manually labelled subset.

### 7. AI-assisted curation (for uncertain units)

When running inside an agent such as Cursor or Claude Code, the agent can directly inspect
waveform/correlogram plots and give an expert read — no API setup required. Generate plots
and ask the agent to assess isolation quality.

For programmatic vision-model access, **read API keys from the environment — never hardcode
credentials in analysis scripts** (they leak into version control and logs):

```python
import os
from anthropic import Anthropic

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])  # set this in your shell, not in code
```

See [references/AI_CURATION.md](references/AI_CURATION.md) for the full pattern (rendering a
unit summary image, building the prompt, and parsing the response).

### 8. Export results

```python
# Keep only good units, then export
analyzer_clean = analyzer.select_units(good_unit_ids, folder="analyzer_clean/", format="binary_folder")

# Phy for manual review
si.export_to_phy(analyzer_clean, output_folder="phy_export/",
                 compute_pc_features=True, compute_amplitudes=True)

# Figures report
si.export_report(analyzer_clean, "report/", format="png")

# NWB
from spikeinterface.exporters import export_to_nwb
export_to_nwb(analyzer_clean, "output.nwb")

# Metrics table
metrics.to_csv("quality_metrics.csv")
```

## Common Pitfalls and Best Practices

1. **Always check drift** before spike sorting — drift > ~10 μm meaningfully degrades quality.
2. **Use `phase_shift`** for Neuropixels 1.0 to correct ADC sampling offsets.
3. **Save the preprocessed recording** with `rec.save(folder=...)` to avoid recomputation (Kilosort also needs a binary file).
4. **Use a GPU** for Kilosort4 — it is far faster than CPU sorters.
5. **Review uncertain units** — automated/model-based curation is a starting point, not a verdict.
6. **Combine approaches** — thresholds for clear cases, model/AI for borderline units.
7. **Document thresholds and model repo IDs** for reproducibility.
8. **Export to Phy** for critical experiments — human oversight is valuable.

## Key Parameters to Adjust

### Preprocessing
- `freq_min`: highpass cutoff (300–400 Hz typical)
- `detect_bad_channels`: returns `(bad_channel_ids, channel_labels)`

### Motion Correction
- `preset`: `nonrigid_fast_and_accurate` (balanced), `nonrigid_accurate` (severe drift), `dredge` (state of the art)

### Spike Sorting (Kilosort4)
- `batch_size`: samples per batch (60000 default)
- `nblocks`: drift blocks (increase for long, drifty recordings)
- `Th_universal` / `Th_learned`: detection thresholds (lower = more spikes)

### Quality Metrics
- `snr`: signal-to-noise cutoff (3–5 typical)
- `isi_violations_ratio`: refractory violations (0.01–0.5)
- `presence_ratio`: recording coverage (0.5–0.95)

## Bundled Resources

### scripts/explore_recording.py
Quick inspection of a recording (streams, channels, duration, bad channels):
```bash
python scripts/explore_recording.py /path/to/data
```

### scripts/preprocess_recording.py
Automated preprocessing:
```bash
python scripts/preprocess_recording.py /path/to/data --output preprocessed/
```

### scripts/run_sorting.py
Run spike sorting:
```bash
python scripts/run_sorting.py preprocessed/ --sorter kilosort4 --output sorting/
```

### scripts/compute_metrics.py
Compute quality metrics and apply curation:
```bash
python scripts/compute_metrics.py sorting/ preprocessed/ --output metrics/ --curation allen
```

### scripts/export_to_phy.py
Export to Phy for manual curation:
```bash
python scripts/export_to_phy.py metrics/analyzer --output phy_export/
```

### scripts/neuropixels_pipeline.py
Complete end-to-end pipeline (see [Quick Start](#full-pipeline-bundled-script)).

### assets/analysis_template.py
Complete, editable analysis template. Copy and customize:
```bash
cp assets/analysis_template.py my_analysis.py
# Edit the PARAMETERS section, then run
python my_analysis.py
```

## Detailed Reference Guides

| Topic | Reference |
|-------|-----------|
| Full workflow | [references/standard_workflow.md](references/standard_workflow.md) |
| API reference (SpikeInterface) | [references/api_reference.md](references/api_reference.md) |
| Plotting guide | [references/plotting_guide.md](references/plotting_guide.md) |
| Preprocessing | [references/PREPROCESSING.md](references/PREPROCESSING.md) |
| Spike sorting | [references/SPIKE_SORTING.md](references/SPIKE_SORTING.md) |
| Motion correction | [references/MOTION_CORRECTION.md](references/MOTION_CORRECTION.md) |
| Quality metrics | [references/QUALITY_METRICS.md](references/QUALITY_METRICS.md) |
| Automated & model-based curation | [references/AUTOMATED_CURATION.md](references/AUTOMATED_CURATION.md) |
| AI-assisted curation | [references/AI_CURATION.md](references/AI_CURATION.md) |
| Waveform analysis | [references/ANALYSIS.md](references/ANALYSIS.md) |

## Installation

Requires Python ≥ 3.10. Using [uv](https://docs.astral.sh/uv/) is recommended.

```bash
# Core packages (SpikeInterface bundles the curation/model tooling)
uv pip install "spikeinterface[full]" probeinterface neo

# Spike sorters
uv pip install kilosort          # Kilosort4 (CUDA GPU required)
uv pip install spykingcircus     # SpykingCircus (legacy; SpykingCircus2 ships with SpikeInterface)
uv pip install mountainsort5     # Mountainsort5 (CPU)

# Model-based curation (UnitRefine) downloads from Hugging Face
uv pip install "huggingface_hub" skops

# Optional: AI-assisted visual curation
uv pip install anthropic

# Optional: IBL tools and Bombcell
uv pip install ibl-neuropixel ibllib bombcell
```

For reproducible environments, pin versions (current as of 2026-06: `spikeinterface==0.104.3`,
`kilosort==4.1.7`, `probeinterface==0.3.2`, `neo==0.14.4`). Unpinned installs are fine for
quick experimentation but should be pinned in production pipelines.

## Project Structure

```
project/
├── raw_data/
│   └── recording_g0/
│       └── recording_g0_imec0/
│           ├── recording_g0_t0.imec0.ap.bin
│           └── recording_g0_t0.imec0.ap.meta
├── preprocessed/           # Saved preprocessed recording
├── motion/                 # Motion estimation results
├── sorting_output/         # Spike sorter output
├── analyzer/               # SortingAnalyzer (waveforms, metrics)
├── phy_export/             # For manual curation
├── ai_curation/            # AI analysis reports
└── results/
    ├── quality_metrics.csv
    ├── curation_labels.json
    └── output.nwb
```

## Additional Resources

- **SpikeInterface Docs**: https://spikeinterface.readthedocs.io/
- **Neuropixels Tutorial**: https://spikeinterface.readthedocs.io/en/stable/how_to/analyze_neuropixels.html
- **Model-based Curation Tutorial**: https://spikeinterface.readthedocs.io/en/stable/tutorials/curation/plot_1_automated_curation.html
- **UnitRefine Models (Hugging Face)**: https://huggingface.co/SpikeInterface
- **Kilosort4 GitHub**: https://github.com/MouseLand/Kilosort
- **IBL Neuropixel Tools**: https://github.com/int-brain-lab/ibl-neuropixel
- **Allen Institute ecephys**: https://github.com/AllenInstitute/ecephys_spike_sorting
- **Bombcell (Automated QC)**: https://github.com/Julie-Fabre/bombcell
- **Awesome Neuropixels**: https://github.com/Julie-Fabre/awesome_neuropixels
