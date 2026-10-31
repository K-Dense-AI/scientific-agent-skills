# Neuropixels preprocessing

Targets SpikeInterface 0.105.0, ProbeInterface 0.4.0 and Neo 0.14.5; reviewed
2026-10-01. Real acquisition examples require validation on the supplied files.

## Load the correct stream and preserve its metadata

```python
import spikeinterface.full as si
names, ids = si.get_neo_streams("spikeglx", "raw_data/")
print(names, ids)
recording = si.read_spikeglx("raw_data/", stream_name="imec0.ap")  # Replace with the inspected AP name.
```

Select the inspected AP stream; never assume the first stream, `imec0.ap`, or a
384-channel count is correct for every acquisition. In 0.105, sync is a separate
stream and `read_spikeglx` no longer accepts `load_sync_channel`. Retain the `.meta`
file and check gain/offset, sampling rate, contact positions, shank IDs, channel
order, sample timing, and selected bank. Do not treat sync or auxiliary channels
as electrode signals. ProbeInterface 0.4 uses probe part numbers to obtain geometry.
For Open Ephys, inspect streams using `get_neo_streams("openephys", folder)` and
pass `stream_name` explicitly. For NWB, select the intended `electrical_series_path`.

`get_traces()` returns **samples × channels**, in stored units by default.
`return_in_uV=True` requires calibrated `gain_to_uV` and `offset_to_uV`. Geometry
is in micrometers. Channel IDs are labels, not array indices. Never set a gain of
1 merely to bypass calibration checks. Preserve discontinuities and time origins;
the bundled commands require one continuous segment and a single attached probe.
Referencing requires explicit shank IDs; the pipeline motion stage further requires
one shank. Split multishank recordings explicitly for separate motion estimates.

## Filter, remove bad channels, correct timing, reference per shank

```python
# From the skill root; these are the same checks used by the CLI.
import sys
sys.path.insert(0, "scripts")
from _common import validate_recording, apply_phase_correction, reference_by_shank

validate_recording(recording)
rec = si.highpass_filter(recording, freq_min=400.0)
bad_ids, labels = si.detect_bad_channels(rec, seed=42)
print(dict(zip(rec.channel_ids, labels)))  # labels cover ALL original channels
rec = rec.remove_channels(bad_ids)
rec = apply_phase_correction(rec)
rec = reference_by_shank(rec)
rec = rec.save(folder="preprocessed/", format="binary", n_jobs=1)
```

Apply phase correction from acquisition `inter_sample_shift` metadata, not a rule
that NP2 has one ADC. If metadata is absent, verify the probe/acquisition timing
and explicitly disable the step when appropriate. Do not fabricate timing offsets.
The helper fails rather than guessing. Removing channels retains their mapping.
Common reference `groups` expects **lists of channel IDs**, not one group label per
channel. Reference separate shanks independently; never assume `group` means shank.

A bandpass alternative is `si.bandpass_filter(rec, freq_min=300, freq_max=6000)`;
require `0 < freq_min < freq_max < fs / 2`. Use default filter margins unless
validated otherwise. AP filtering removes low frequencies; keep the original LF
stream for LFP analysis. Notch filtering at 50/60 Hz is usually irrelevant after
an AP highpass and can distort signals when applied indiscriminately.

## Optional operations

```python
# Geometry-based interpolation is an alternative to removing channels.
# Bad-channel IDs must refer to this recording, before their removal.
rec_interpolated = si.interpolate_bad_channels(recording, bad_channel_ids=bad_ids)

# Whitening is sorter-specific; do not use whitened traces for physical amplitudes.
whitened = si.whiten(rec, mode="local", radius_um=100)

# Per-segment lists of stimulus sample indices, not seconds.
artifact_clean = si.remove_artifacts(rec, [[10000, 20000]],
                                    ms_before=0.5, ms_after=3.0, mode="linear")
```

Interpolation changes neighboring noise statistics and is not always preferable
to removal. Review stimulation/saturation windows and mask invalid analysis periods;
there is no `blank_staturation` API. Spatial highpass destriping via
`si.highpass_spatial_filter` needs a depth-ordered single shank and sufficient
contacts; a common median reference alone is not full IBL destriping.

Use [MOTION_CORRECTION.md](MOTION_CORRECTION.md) for motion estimation/interpolation.
Reload a saved extractor with `si.load("preprocessed/")`. Binary caching is a
time/disk tradeoff; estimate storage before writing a full recording. The standalone
preprocessing command puts the extractor in `<output>/preprocessed/`; downstream
commands accept that folder or its parent.

Sources: [Neuropixels how-to](https://spikeinterface.readthedocs.io/en/stable/how_to/analyze_neuropixels.html),
[API](https://spikeinterface.readthedocs.io/en/stable/api.html),
[ProbeInterface catalogue](https://probeinterface.readthedocs.io/en/main/neuropixels_readers.html).
