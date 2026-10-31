# Motion and drift correction

Reviewed against SpikeInterface 0.105.0 on 2026-10-01. Examples with real
recordings are illustrative; tiny synthetic checks validate API/data contracts,
not the accuracy of a drift estimate.

## Inspect before choosing correction

Use filtered, referenced, **unwhitened** traces with verified contact positions in
micrometers. Select one AP stream and one continuous segment. A cloud of peaks
spanning the probe is population depth, not motion: look for changes over time
in coherent bands. Changing firing rates can confound registration. Separate
shanks before estimating motion when they do not share a displacement field.

```python
import spikeinterface.full as si
from spikeinterface.sortingcomponents.peak_detection import detect_peaks
from spikeinterface.sortingcomponents.peak_localization import localize_peaks

noise = si.get_noise_levels(rec, return_in_uV=False)
peaks = detect_peaks(rec, method='locally_exclusive', method_kwargs={'noise_levels': noise, 'detect_threshold': 5, 'radius_um': 50}, job_kwargs={'n_jobs': 1})
locations = localize_peaks(rec, peaks, method='center_of_mass', job_kwargs={'n_jobs': 1})
si.plot_drift_raster_map(peaks=peaks, peak_locations=locations, recording=rec)
```

Peak fields are `sample_index`, `channel_index`, `amplitude`, `segment_index`.
Sample indices are local to each segment; convert to seconds with that segment's
sampling rate/time origin, rather than overlaying segments at zero.

## Estimate, inspect, then interpolate

`estimate_motion` returns a `Motion` object, not three arrays. `win_scale_um`
controls window size; the older `win_sigma_um` examples are unsupported.

```python
from spikeinterface.sortingcomponents.motion import estimate_motion, interpolate_motion

motion = estimate_motion(rec, peaks, locations, method="decentralized",
                         direction="y", rigid=True, bin_s=2.0,
                         progress_bar=True)
si.plot_motion(motion)
motion.save("motion_estimate/")
motion = si.load("motion_estimate/")
rec_corrected = interpolate_motion(rec, motion, border_mode="remove_channels")
```

The temporal samples and displacements are `motion.temporal_bins_s[segment]`
and `motion.displacement[segment]`; spatial bins are `motion.spatial_bins_um`.
`remove_channels` can change the contact set. Recheck channel IDs, geometry and
probe mapping after interpolation. `force_extrapolate` retains edge contacts but
can extrapolate outside measured support; inspect those channels separately.

## Preset workflow

```python
rec_corrected, motion_info = si.correct_motion(
    rec, preset="nonrigid_fast_and_accurate", folder="motion/",
    output_motion_info=True, n_jobs=1, chunk_duration="1s",
)
si.plot_motion_info(motion_info, recording=rec)
```

In 0.105.0, supported presets are `dredge`, `dredge_fast` (upstream default),
`medicine`, `nonrigid_accurate`, `nonrigid_fast_and_accurate`, `rigid_fast`, and
`kilosort_like`. Names are not guarantees of accuracy. Evaluate residual drift,
waveform stability, edge effects, and unit yield on the experiment. Some methods
need optional dependencies. The bundled pipeline deliberately retains its
explicit `nonrigid_fast_and_accurate` preset for reproducibility.

For estimation only:

```python
motion, motion_info = si.compute_motion(
    rec, preset="nonrigid_fast_and_accurate", output_motion_info=True,
    folder="motion_only/", n_jobs=1,
)
```

There is no `dredge_lfp` preset in this API. LFP registration is a distinct DREDge
workflow: consult its upstream examples, validate filtering, electrode positions
and alignment between AP and LF clocks, then verify the sign/units/time domain
before transferring motion. Do not substitute LF data into an AP peak pipeline.
There is also no public `estimate_motion_from_sorting` helper in this release.

## Avoid applying two motion corrections

```python
sorting = si.run_sorter("kilosort4", rec_corrected, folder="ks4/",
                         do_correction=False)
sorting_cpu = si.run_sorter("spykingcircus2", rec_corrected, folder="sc2/",
                             apply_motion_correction=False)
```

Kilosort 2.5/3 use `do_correction=False` too. Spykingcircus2's
`apply_preprocessing=False` does not disable its separate motion stage. If using
uncorrected input, choose the sorter's own correction instead. Inspect before and
after plots using identical limits; residual activity bands and registration
uncertainty matter more than a universal micrometer cutoff.

Sources: [motion guide](https://spikeinterface.readthedocs.io/en/stable/modules/motion_correction.html),
[API](https://spikeinterface.readthedocs.io/en/stable/api.html),
[DREDge](https://github.com/evarol/DREDge).
