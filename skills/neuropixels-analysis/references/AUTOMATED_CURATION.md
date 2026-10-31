# Automated and model-assisted curation

Reviewed 2026-10-01 against SpikeInterface 0.105.0 and the linked upstream
workflows. Threshold screening is tested on synthetic metrics. UnitRefine,
Bombcell and UnitMatch were checked against documentation/source only; no model
download, prediction, or real-data classification was run.

## Reproducible threshold screening

Compute dependencies and metrics in [QUALITY_METRICS.md](QUALITY_METRICS.md), then
use `scripts/compute_metrics.py` or its `curate_units` function. The `allen`,
legacy `ibl`, and `strict` names denote **local presets**, not complete Allen/IBL
pipelines. Missing/nonfinite evidence remains `unsorted`. Keep full metrics, labels,
parameters and original units alongside any selected subset. Validate a sample
of accepted and rejected units manually; visual consensus is not ground truth.

## UnitRefine

The SpikeInterface curation module can load classifiers hosted on Hugging Face.
The two UnitRefine models separate noise/neural, then SUA/MUA. Their required
feature set and extraction parameters are part of the trained model contract.

```python
import spikeinterface.curation as sc

# Prerequisite: analyzer extensions and metrics match the model's model_info.json.
# Inspect the upstream model card before explicitly trusting its serialized types.
labels = sc.model_based_label_units(
    sorting_analyzer=analyzer,
    repo_id="SpikeInterface/UnitRefine_noise_neural_classifier",
    trust_model=True,
    enforce_metric_params=True,
)
# labels is a DataFrame: prediction and probability, indexed by unit ID.
neural = analyzer.remove_units(labels.index[labels["prediction"] == "noise"])
sua_mua = sc.model_based_label_units(
    sorting_analyzer=neural,
    repo_id="SpikeInterface/UnitRefine_sua_mua_classifier",
    trust_model=True,
    enforce_metric_params=True,
)
```

The checked public model metadata specifies SI 0.102.0 and scikit-learn 1.4.2;
`metric_params` is empty for both repositories, so enforcement cannot establish
training-parameter equivalence. Prediction compatibility with 0.105.0 was not tested.
Before using the example, inspect the model card/feature names and compute the
required quality/template metrics, including `spike_locations`/PCA dependencies
when called for. Missing features and version differences must be resolved, not
imputed silently. SI 0.104+ changed template-metric naming (the loader includes compatibility mappings): old UnitRefine models
can request names from an older release. Use the model's compatible environment
or validated feature mapping; do not rename incompatible quantities to satisfy a
column check. `sc.load_model(repo_id=..., trusted=[...])` returns `(model, model_info)`.
`trust_model=True` trusts serialized model types; it is an explicit trust decision,
not a routine security bypass. Record repository revision/download hashes, software
versions, feature extraction settings and classifier probabilities. Probability
is not guaranteed calibrated confidence on a new probe, brain region or animal.

## Bombcell

Install `bombcell` in its own environment (upstream examples use Python 3.11).
Use the current acquisition-specific demo to configure raw-data layout, scaling,
sync channels, sample rate and Kilosort outputs. The checked Python workflow is:

```python
from pathlib import Path
import bombcell as bc

ks_dir = "kilosort_output/"
param = bc.get_default_parameters(ks_dir, raw_file="recording.ap.bin",
                                  meta_file="recording.ap.meta", kilosort_version=4)
quality_metrics, param, unit_type, unit_type_string = bc.run_bombcell(
    ks_dir, Path(ks_dir) / "bombcell", param,
)
```

This is source-verified and illustrative. The return is a four-value tuple, not a
`results["unit_labels"]` dictionary; the raw binary is configured in `param`, not
passed as the second `run_bombcell` argument. There is no verified
`run_bombcell_phy` convenience API. Do not assume any generic Phy export contains
every required Kilosort array/raw waveform field. Join classifications by the
original cluster ID, never row position. Inspect the actual label mapping and
`splitGoodAndMua_NonSomatic` setting: non-somatic waveforms can be separated from
noise, MUA and single somatic units. Waveform classes alone do not prove cell type.

## UnitMatch

The current Python distribution/import is **UnitMatchPy**, not `unitmatch` or
`from unitmatch import UnitMatch`. Its official notebooks use modules such as
`UnitMatchPy.utils`, `UnitMatchPy.overlord`, `UnitMatchPy.bayes_functions` and
`UnitMatchPy.assign_unique_id`. Follow the [current example notebook](https://github.com/EnnyvanBeest/UnitMatch/blob/main/UnitMatchPy/Demo%20Notebooks/UMPy_example.ipynb)
with per-unit raw waveforms, channel positions, session indices and curated IDs.
Do not invent a `UnitMatch(...).run()` interface.

Cross-session matching is probabilistic: keep the session/cluster-to-unique-ID
mapping, rejected matches, probability threshold and within-session validation.
Waveform/position similarity alone does not establish longitudinal identity. The
DeepUnitMatch pretrained model documented upstream is restricted to NP2 four-shank
probes; it is not a general substitute for the standard UnitMatch workflow.

## Manual review and edits

```python
from spikeinterface.curation import CurationSorting
curation = CurationSorting(sorting)
curation.remove_units(noise_unit_ids)
sorting_curated = curation.sorting
```

Similarity matrices include the diagonal and symmetric duplicate pairs. Restrict
to upper-triangle candidates and inspect cross-correlograms, refractory violations,
location and amplitude continuity before merging. Similar templates can belong
to different neurons. Recompute affected metrics after edits.

For Phy, export the full analyzer with screening labels so reviewers can inspect
neighbors; curated `read_phy` output can contain new IDs from splits/merges.
Do not splice labels onto the old sorting by row number or retain stale extensions.

Sources: [SI curation tutorial](https://spikeinterface.readthedocs.io/en/stable/tutorials/curation/plot_1_automated_curation.html),
[UnitRefine model cards](https://huggingface.co/SpikeInterface),
[Bombcell SpikeGLX demo](https://github.com/Julie-Fabre/bombcell/blob/main/py_bombcell/demos/BC_demo_spikeGLX.ipynb),
[UnitMatchPy README](https://github.com/EnnyvanBeest/UnitMatch/tree/main/UnitMatchPy).
