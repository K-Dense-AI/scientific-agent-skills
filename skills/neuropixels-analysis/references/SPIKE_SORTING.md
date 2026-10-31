# Spike sorting

SpikeInterface 0.105.0 wrapper contracts reviewed 2026-10-01. Sorter invocations
below are illustrative: no Kilosort, MATLAB, CUDA, container image or large real
recording was run in this audit. Synthetic tests cover wrapper routing and
postprocessing, not sorter accuracy or performance.

## Choose an implementation and its environment

| Sorter | Requirements and scope |
|---|---|
| Kilosort4 | External `kilosort` and PyTorch; CUDA recommended for Neuropixels-scale work. The SI wrapper also supports `torch_device="cpu"`. |
| Kilosort3 / 2.5 | Legacy external MATLAB or compiled/container environment, with its CUDA requirements. |
| Spykingcircus2 / Tridesclous2 | Implemented in SpikeInterface, but require optional sorting dependencies. They are not the legacy `spykingcircus` package. |
| Mountainsort5 | External `mountainsort5` package; CPU workflow. |

Install only the selected sorter in an isolated environment, following its upstream
instructions. `si.available_sorters()` lists wrappers; `si.installed_sorters()` is
an installation check, not a successful runtime test. Kilosort4's full parameter
list is assembled from the installed Kilosort package. Without it,
`si.get_default_sorter_params("kilosort4")` is incomplete and emits a warning.

## Kilosort4

```python
import spikeinterface.full as si
# Requires a working Kilosort4 installation and a validated AP recording.
params = si.get_default_sorter_params("kilosort4")
print(params)
sorting = si.run_sorter("kilosort4", rec, folder="ks4_output/",
                        do_CAR=False,  # Already referenced externally.
                        do_correction=True,  # Only if input was not motion-corrected.
                        verbose=True)
```

The wrapper obtains sample rate and channel count from the recording. `batch_size`
is in samples; `nblocks` configures internal registration; `Th_universal` and
`Th_learned` are detection thresholds. Do not copy obsolete `spkTh`, `nfilt_factor`
or `save_extra_kwargs` into KS4. Its wrapper calls the last option `save_extra_vars`.
Do not set `skip_kilosort_preprocessing=True` solely because filtering was done:
that also affects whitening and must match the sorter's input assumptions.
The current wrapper can use a binary file or an extractor (`use_binary_file`);
a manual binary cache is a performance/storage choice.

For externally corrected input, set `do_correction=False` (also for KS2.5/KS3).
Kilosort3 uses `car=False`, not the KS4 `do_CAR` spelling. Inspect the wrapper
parameters after any version change. Do not infer duplicate neuron identity from
unit counts or fix apparent over-splitting merely by increasing template spacing.

## CPU options

```python
# Referenced and filtered input; retain the sorter's whitening.
sorting_sc2 = si.run_sorter("spykingcircus2", rec_corrected, folder="sc2/",
                            apply_preprocessing=False, apply_motion_correction=False)
sorting_ms5 = si.run_sorter("mountainsort5", rec_corrected, folder="ms5/",
                            filter=False, whiten=True, scheme="2")
```

Spykingcircus2 detection and selection parameters are nested dictionaries in
0.105.0, not top-level `detect_threshold`/`selection_method`. Get the current
schema first and change only the relevant nested entries. Filtering, referencing,
whitening and motion correction are separate stages; disable only those already
performed. The bundled preprocessing script does **not** whiten.

## Comparisons, segments, and unit identity

```python
comparison = si.compare_multiple_sorters([sorting_a, sorting_b], name_list=["A", "B"])
consensus = comparison.get_agreement_sorting(minimum_agreement_count=2)
```

Agreement does not prove correctness; sorters can share errors. There is no
`si.create_ensemble_sorting` convenience API in this release. Compare matched
spike trains and waveforms, and check the units missed by consensus.

Kilosort4's wrapper requires one segment. To concatenate recordings, first verify
identical sample rate, contact mapping and preprocessing; preserve each original
boundary and time origin. Use `si.concatenate_recordings(recordings)` and
`si.split_sorting(sorting, recording_concat)` when splitting the result back.
Discontinuous sessions need an explicit plan for gaps/artifacts. Independently
sorted chunks do not preserve unit IDs across chunks. For a single recording,
use `recording.frame_slice(start_frame, end_frame)`, not `split_by_times`.

## Save, review, and reload

```python
sorting.save(folder="sorting/")
sorting = si.load("sorting/")
# Or read the wrapper's original output:
sorting = si.read_sorter_folder("ks4_output/")
```

Compute a SortingAnalyzer as described in [ANALYSIS.md](ANALYSIS.md), then export
all units for manual Phy review. `si.read_phy("phy_export/")` returns the curated
sorting including splits/merges; inspect `get_property_keys()` and cluster-group
properties rather than assuming `quality`. Recompute analyzer extensions after
manual changes. There is no `si.apply_phy_curation` helper in this release.

Container invocation uses `docker_image=True` or an explicitly pinned supported
image, or `singularity_image=...`; it still needs the host runtime/GPU setup.
A mutable `latest` tag is not a reproducible environment.

Sources: [SI sorter API](https://spikeinterface.readthedocs.io/en/stable/api.html),
[KS4 wrapper](https://github.com/SpikeInterface/spikeinterface/blob/0.105.0/src/spikeinterface/sorters/external/kilosort4.py),
[Kilosort installation](https://kilosort.readthedocs.io/en/latest/README.html),
[Kilosort parameters](https://github.com/MouseLand/Kilosort/blob/main/kilosort/parameters.py).

SpikeInterface 0.105.0 has an observed `read_phy` bug for exported nonnumeric
unit IDs (`np.isnan` TypeError). Phy export preserves `cluster_si_unit_ids.tsv`;
keep that mapping and use a validated importer/fixed release for string-ID
readback. Numeric-ID Phy export/reload was tested on synthetic data.
