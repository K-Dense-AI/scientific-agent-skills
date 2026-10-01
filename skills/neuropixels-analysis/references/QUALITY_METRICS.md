# Quality metrics and screening

Targets SpikeInterface 0.105.0; reviewed 2026-10-01. An apparently clean unit is
not proof of a single neuron. Inspect waveforms, refractory behavior, stability,
spike counts, artifacts and neighboring units together.

## Compute metrics with their dependencies

```python
import spikeinterface.full as si

analyzer = si.create_sorting_analyzer(sorting, recording, sparse=True)
analyzer.compute("random_spikes", max_spikes_per_unit=500, seed=42)
analyzer.compute("waveforms", ms_before=1.0, ms_after=2.0)
analyzer.compute("templates", operators=["average", "std"])
analyzer.compute("noise_levels")
analyzer.compute("spike_amplitudes")
analyzer.compute("amplitude_scalings")
analyzer.compute("quality_metrics",
    metric_names=["firing_rate", "snr", "isi_violation", "presence_ratio", "amplitude_cutoff"],
    metric_params={"isi_violation": {"isi_threshold_ms": 1.5, "min_isi_ms": 0.0},
                   "presence_ratio": {"bin_duration_s": 60.0}},
)
qm = analyzer.get_extension("quality_metrics").get_data()
```

The default presence bin is 60 s: shorter recordings return NaN. Short smoke
fixtures may use shorter bins, but this changes the scientific quantity. An
amplitude cutoff can also be NaN when too few spikes support the histogram.
Never fill these values with a passing score. The bundled classifiers leave any
missing/nonfinite required metric `unsorted`.

## Metric names differ from result columns

Pass the left column to `metric_names`; query the returned right-hand columns.
Inspect `si.get_quality_metric_list()` and `si.get_default_quality_metrics_params()`
for the installed release. Version 0.105 uses nested `metric_params`.

| Metric name | Result column(s) | Additional requirement |
|---|---|---|
| `isi_violation` | `isi_violations_ratio`, `isi_violations_count` | Spike times, recording duration |
| `amplitude_cv` | `amplitude_cv_median`, `amplitude_cv_range` | Spike amplitudes, enough spikes/bins |
| `drift` | `drift_ptp`, `drift_std`, `drift_mad` | `spike_locations` extension |
| `mahalanobis` | `isolation_distance`, `l_ratio` | `principal_components` extension |
| `nearest_neighbor` | `nn_hit_rate`, `nn_miss_rate` | Principal components |
| `silhouette` | Method-dependent silhouette column | Principal components |
| `synchrony` | `sync_spike_2`, `sync_spike_4`, `sync_spike_8` by default | Spike times |
| `snr` | `snr` | Templates and noise levels |
| `amplitude_cutoff` | `amplitude_cutoff` | `amplitude_scalings` (current preferred dependency) |
| `presence_ratio` | `presence_ratio` | Explicit bin duration |
| `firing_rate` | `firing_rate` | Duration in seconds |

```python
analyzer.compute("principal_components", n_components=3, mode="by_channel_local")
analyzer.compute("spike_locations", method="center_of_mass")
analyzer.compute("quality_metrics", metric_names=["mahalanobis", "nearest_neighbor", "drift"],
                 metric_params={"nearest_neighbor": {"n_neighbors": 4}}, n_jobs=1)
```

NaN or inf from sparse clusters, rank-deficient PCA, too few spikes, or too little
recording is a reason to inspect the data, not a threshold to relax automatically.
Do not compute every expensive metric by default.

## Interpret the measurements

- ISI violation **ratio is rate-normalized**, not the fraction of all spikes that
  violate a refractory period and not a percentage contamination estimate. It can
  exceed 1. The chosen refractory/censor windows depend on physiology and sorter
  duplicate handling; 1.5 ms is a convention, not a universal neuronal constant.
- Presence ratio is the fraction of bins meeting an activity criterion. It depends
  on bin size, rate and duration; absence may be real stimulus/state dependence.
- Amplitude cutoff estimates missing spikes under distribution assumptions. Drift,
  multimodality and censoring can make it misleading. It is not a direct recall measurement.
- SNR is template amplitude divided by estimated channel noise; it does not measure
  isolation by itself. Use matched physical scaling and preprocessing.
- Drift from sorted spikes can be confounded by activity changes and incorrect
  assignments. Spatial extent of different neurons is not temporal drift.
- Waveform shape alone does not establish molecular cell type or somatic origin.

## Institutional criteria versus local presets

The AllenSDK Visual Coding tutorial documents default filtering at
`amplitude_cutoff < 0.1`, `presence_ratio > 0.9`, `isi_violations < 0.5`.
SpikeInterface names the last output `isi_violations_ratio`. Allen data releases
and pipelines can use different metrics/parameters; state exactly what was used.

The bundled `allen` preset adds SNR > 3 and is therefore **Allen-inspired**. The
legacy `ibl` name is a local tighter screen, **not** the IBL classifier. IBL's
`brainbox.metrics.single_units.quick_unit_metrics` uses sliding-RP, noise-cutoff
and amplitude criteria; its pass indicator and contamination measures are not
interchangeable with SpikeInterface's Hill ISI ratio.

All three bundled entry points use the same screening behavior:

| Local preset | SNR > | Presence > | ISI ratio < | Amplitude cutoff < | Rate > |
|---|---:|---:|---:|---:|---:|
| `allen` | 3 | 0.9 | 0.5 | 0.1 | — |
| `ibl` (legacy name) | 4 | 0.9 | 0.1 | 0.1 | 0.1 Hz |
| `strict` | 5 | 0.95 | 0.01 | 0.01 | — |

Boundaries fail strict inequalities. Finite SNR < 1.5 is flagged `noise`; excess
ISI ratio is flagged `mua` (strict preset uses > 0.05 for this flag); otherwise
failed screens remain `unsorted`, including low completeness without contamination.
These are screening labels to review, not validated diagnoses.

```python
# Run from the skill root so bundled helpers are importable.
import sys
sys.path.insert(0, "scripts")
from compute_metrics import curate_units
labels = curate_units(qm, method="allen")
good_ids = [uid for uid, label in labels.items() if label == "good"]
```

Keep all metrics and labels, selected IDs, parameter values, package versions,
recording duration, and a review rationale. Never discard the uncurated result.

Sources: [SpikeInterface API](https://spikeinterface.readthedocs.io/en/stable/api.html),
[AllenSDK quality metrics](https://allensdk.readthedocs.io/en/latest/_static/examples/nb/ecephys_quality_metrics.html),
[IBL single-unit metrics](https://docs.internationalbrainlab.org/_autosummary/brainbox.metrics.single_units.html).
