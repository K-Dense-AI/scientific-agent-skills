"""Recording contracts shared by the bundled Neuropixels commands."""
from pathlib import Path

import numpy as np
import spikeinterface.full as si


def load_saved(path, child):
    """Accept an extractor folder or a bundled command's output parent."""
    path = Path(path)
    return si.load(path / child if (path / child).is_dir() else path)


def validate_recording(recording):
    """These commands process one continuous, calibrated probe recording."""
    if recording.get_num_segments() != 1:
        raise ValueError("Select one recording segment before using this command; preserve its time origin.")
    fs = recording.get_sampling_frequency()
    if not np.isfinite(fs) or fs <= 0 or recording.get_num_samples() == 0:
        raise ValueError("Recording must have samples and a positive finite sampling frequency.")
    locations = recording.get_channel_locations()
    if locations.shape[0] != recording.get_num_channels() or not np.isfinite(locations).all():
        raise ValueError("Every channel needs a finite location in micrometers.")
    if np.unique(locations, axis=0).shape[0] != len(locations):
        raise ValueError("Channel locations must be unique; verify shank geometry and channel mapping.")
    if not recording.has_scaleable_traces():
        raise ValueError("Recording needs calibrated gain_to_uV/offset_to_uV before amplitude analysis.")


def apply_phase_correction(recording):
    """Use recorded ADC offsets, never infer them from a probe-generation label."""
    shifts = recording.get_property('inter_sample_shift')
    if shifts is None or not np.isfinite(shifts).all():
        raise ValueError("Missing inter_sample_shift metadata; verify ADC timing or explicitly skip phase correction.")
    return si.phase_shift(recording)


def reference_by_shank(recording):
    """Median reference each shank using contact-to-device indices, not channel IDs."""
    probe = recording.get_probe()  # Deliberately requires a single attached probe.
    indices = np.asarray(probe.device_channel_indices)
    if sorted(indices.tolist()) != list(range(recording.get_num_channels())):
        raise ValueError("Probe device-channel mapping must cover the selected channels exactly once.")
    if probe.shank_ids is None:
        raise ValueError("Missing probe shank_ids; annotate the verified shank assignment before referencing.")
    shanks = np.asarray(probe.shank_ids)
    groups = [recording.channel_ids[indices[shanks == shank]].tolist() for shank in np.unique(shanks)]
    if any(len(group) < 2 for group in groups):
        raise ValueError("Median reference needs at least two retained channels on every shank.")
    return si.common_reference(recording, operator='median', reference='global', groups=groups)
