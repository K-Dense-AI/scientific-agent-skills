#!/usr/bin/env python3
"""
Neuropixels Data Analysis Pipeline (Best Practices Version)

Based on SpikeInterface, Allen Institute, and IBL recommendations.

Usage:
    python neuropixels_pipeline.py /path/to/spikeglx/data /path/to/output

References:
    - https://spikeinterface.readthedocs.io/en/stable/how_to/analyze_neuropixels.html
    - https://github.com/AllenInstitute/ecephys_spike_sorting
"""

import argparse
from pathlib import Path
import json
import spikeinterface.full as si
import numpy as np

from _common import validate_recording, apply_phase_correction, reference_by_shank
from compute_metrics import curate_units, METRIC_NAMES


def load_recording(data_path: str, stream_name: str = 'imec0.ap') -> si.BaseRecording:
    """Load a SpikeGLX or Open Ephys recording."""

    data_path = Path(data_path)

    # Auto-detect format
    if any(data_path.rglob('*.ap.bin')) or any(data_path.rglob('*.ap.meta')):
        # SpikeGLX format
        streams, _ = si.get_neo_streams('spikeglx', data_path)
        print(f"Available streams: {streams}")
        recording = si.read_spikeglx(data_path, stream_name=stream_name)
    elif any(data_path.rglob('*.oebin')):
        # Open Ephys format
        recording = si.read_openephys(data_path, stream_name=stream_name)
    else:
        raise ValueError(f"Unknown format in {data_path}")

    validate_recording(recording)
    print(f"Loaded recording:")
    print(f"  Channels: {recording.get_num_channels()}")
    print(f"  Duration: {recording.get_total_duration():.2f} s")
    print(f"  Sampling rate: {recording.get_sampling_frequency()} Hz")

    return recording


def preprocess(
    recording: si.BaseRecording,
    apply_phase_shift: bool = True,
    freq_min: float = 400.,
) -> tuple:
    """
    Apply standard Neuropixels preprocessing.

    Following SpikeInterface recommendations:
    1. High-pass filter at 400 Hz (not 300)
    2. Detect and remove bad channels
    3. Phase shift using acquisition ADC timing metadata
    4. Common median reference
    """
    print("Preprocessing...")

    # Step 1: High-pass filter
    validate_recording(recording)
    rec = si.highpass_filter(recording, freq_min=freq_min)
    print(f"  Applied high-pass filter at {freq_min} Hz")

    # Step 2: Detect bad channels
    bad_channel_ids, channel_labels = si.detect_bad_channels(rec)
    if len(bad_channel_ids) > 0:
        print(f"  Detected {len(bad_channel_ids)} bad channels: {bad_channel_ids}")
        rec = rec.remove_channels(bad_channel_ids)
    else:
        print("  No bad channels detected")

    # Step 3: Phase shift from acquisition timing metadata
    if apply_phase_shift:
        rec = apply_phase_correction(rec)
        print("  Applied phase shift correction")

    # Step 4: Common median reference
    rec = reference_by_shank(rec)
    print("  Applied common median reference")

    return rec, bad_channel_ids


def check_drift(recording: si.BaseRecording, output_folder: str) -> dict:
    """
    Detect peaks and check for drift before spike sorting.
    """
    print("Checking for drift...")

    from spikeinterface.sortingcomponents.peak_detection import detect_peaks
    from spikeinterface.sortingcomponents.peak_localization import localize_peaks

    job_kwargs = dict(n_jobs=8, chunk_duration='1s', progress_bar=True)

    # Get noise levels
    noise_levels = si.get_noise_levels(recording, return_in_uV=False)

    # Detect peaks
    peaks = detect_peaks(recording, method='locally_exclusive', method_kwargs={'noise_levels': noise_levels, 'detect_threshold': 5, 'radius_um': 50.0}, job_kwargs=job_kwargs)
    print(f"  Detected {len(peaks)} peaks")

    # Localize peaks
    peak_locations = localize_peaks(recording, peaks, method='center_of_mass', job_kwargs=job_kwargs)

    # Save drift plot
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(12, 6))

    # Subsample for plotting
    n_plot = min(100000, len(peaks))
    idx = np.random.choice(len(peaks), n_plot, replace=False)

    ax.scatter(
        peaks['sample_index'][idx] / recording.get_sampling_frequency(),
        peak_locations['y'][idx],
        s=1, alpha=0.1, c='k'
    )
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Depth (μm)')
    ax.set_title('Peak Activity (Check for Drift)')

    plt.savefig(f'{output_folder}/drift_check.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved drift plot to {output_folder}/drift_check.png")

    # Peak depth spread reflects the population's spatial extent, not displacement
    # over time. Use a motion estimator (correct_motion below), not depth percentiles.
    return {
        'peaks': peaks,
        'peak_locations': peak_locations,
    }


def correct_motion(
    recording: si.BaseRecording,
    output_folder: str,
    preset: str = 'nonrigid_fast_and_accurate'
) -> si.BaseRecording:
    """Apply motion correction if needed."""
    print(f"Applying motion correction (preset: {preset})...")

    probe = recording.get_probe()
    if probe.shank_ids is None or len(np.unique(probe.shank_ids)) != 1:
        raise ValueError("Motion estimation in this pipeline requires one verified shank; select channels per shank first.")

    # correct_motion returns just the corrected recording by default. Pass
    # output_motion_info=True only if you also want the motion info dict (a tuple is
    # returned in that case).
    rec_corrected = si.correct_motion(
        recording,
        preset=preset,
        folder=f'{output_folder}/motion',
        n_jobs=8,
        chunk_duration='1s',
        progress_bar=True
    )

    print("  Motion correction complete")
    return rec_corrected


def run_spike_sorting(
    recording: si.BaseRecording,
    output_folder: str,
    sorter: str = 'kilosort4',
    motion_corrected: bool = False,
) -> si.BaseSorting:
    """Run spike sorting."""
    print(f"Running spike sorting with {sorter}...")

    sorter_folder = f'{output_folder}/sorting_{sorter}'
    sorter_params = {}
    if motion_corrected:
        # SpikeInterface 0.105.0 uses different motion flags for these sorters.
        if sorter in {'kilosort2_5', 'kilosort3', 'kilosort4'}:
            sorter_params['do_correction'] = False
        elif sorter == 'spykingcircus2':
            sorter_params['apply_motion_correction'] = False

    sorting = si.run_sorter(
        sorter,
        recording,
        folder=sorter_folder,
        verbose=True,
        **sorter_params,
    )

    print(f"  Found {len(sorting.unit_ids)} units")
    print(f"  Total spikes: {sorting.count_total_num_spikes()}")

    return sorting


def postprocess(
    sorting: si.BaseSorting,
    recording: si.BaseRecording,
    output_folder: str
) -> tuple:
    """Run post-processing and compute quality metrics."""
    print("Post-processing...")

    job_kwargs = dict(n_jobs=8, chunk_duration='1s', progress_bar=True)

    # Create analyzer
    analyzer = si.create_sorting_analyzer(
        sorting, recording,
        sparse=True,
        format='binary_folder',
        folder=f'{output_folder}/analyzer'
    )

    # Compute extensions (order matters)
    print("  Computing waveforms...")
    analyzer.compute('random_spikes', method='uniform', max_spikes_per_unit=500)
    analyzer.compute('waveforms', ms_before=1.5, ms_after=2.0, **job_kwargs)
    analyzer.compute('templates', operators=['average', 'std'])
    analyzer.compute('noise_levels')

    print("  Computing spike features...")
    analyzer.compute('spike_amplitudes', **job_kwargs)
    analyzer.compute('amplitude_scalings', **job_kwargs)
    analyzer.compute('correlograms', window_ms=100, bin_ms=1)
    analyzer.compute('unit_locations', method='monopolar_triangulation')
    analyzer.compute('template_similarity')

    print("  Computing quality metrics...")
    analyzer.compute('quality_metrics', metric_names=METRIC_NAMES)

    qm = analyzer.get_extension('quality_metrics').get_data()

    return analyzer, qm


def export_results(
    analyzer,
    sorting,
    recording,
    labels: dict,
    output_folder: str
):
    """Export results to various formats."""
    print("Exporting results...")

    # Get good units
    good_ids = [u for u, l in labels.items() if l == 'good']
    sorting_good = sorting.select_units(good_ids)
    sorting_good.save(folder=Path(output_folder) / 'sorting_curated')
    analyzer.sorting.set_property('curation_label', [labels[uid] for uid in analyzer.sorting.unit_ids])

    # Export to Phy
    phy_folder = f'{output_folder}/phy_export'
    si.export_to_phy(analyzer, phy_folder,
                     compute_pc_features=True,
                     compute_amplitudes=True, additional_properties=['curation_label'])
    print(f"  Phy export: {phy_folder}")

    # Generate report
    report_folder = f'{output_folder}/report'
    si.export_report(analyzer, report_folder, format='png')
    print(f"  Report: {report_folder}")

    # Save quality metrics
    qm = analyzer.get_extension('quality_metrics').get_data()
    qm.to_csv(f'{output_folder}/quality_metrics.csv')

    # Save labels
    with open(f'{output_folder}/unit_labels.json', 'w') as f:
        json.dump({str(k): v for k, v in labels.items()}, f, indent=2)

    # Save summary
    summary = {
        'total_units': len(sorting.unit_ids),
        'good_units': len(good_ids),
        'total_spikes': int(sorting.count_total_num_spikes()),
        'duration_s': float(recording.get_total_duration()),
        'n_channels': int(recording.get_num_channels()),
    }
    with open(f'{output_folder}/summary.json', 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"  Summary: {summary}")


def run_pipeline(
    data_path: str,
    output_path: str,
    sorter: str = 'kilosort4',
    stream_name: str = 'imec0.ap',
    apply_motion_correction: bool = True,
    curation_method: str = 'allen',
    apply_phase_shift: bool = True
):
    """Run complete Neuropixels analysis pipeline."""

    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. Load data
    recording = load_recording(data_path, stream_name)

    # 2. Preprocess
    rec_preprocessed, bad_channels = preprocess(recording, apply_phase_shift=apply_phase_shift)

    # Save preprocessed
    preproc_folder = output_path / 'preprocessed'
    job_kwargs = dict(n_jobs=8, chunk_duration='1s', progress_bar=True)
    rec_preprocessed = rec_preprocessed.save(
        folder=str(preproc_folder),
        format='binary',
        **job_kwargs
    )

    # 3. Check drift
    check_drift(rec_preprocessed, str(output_path))

    # 4. Estimate and correct motion when explicitly enabled by pipeline settings.
    if apply_motion_correction:
        print("Estimating and applying motion correction...")
        rec_final = correct_motion(rec_preprocessed, str(output_path))
    else:
        print("Skipping external motion correction (disabled)")
        rec_final = rec_preprocessed

    # 5. Spike sorting
    sorting = run_spike_sorting(
        rec_final, str(output_path), sorter, motion_corrected=apply_motion_correction
    )

    # 6. Post-processing
    analyzer, qm = postprocess(sorting, rec_final, str(output_path))

    # 7. Curation
    labels = curate_units(qm, method=curation_method)

    # 8. Export
    export_results(analyzer, sorting, rec_final, labels, str(output_path))

    print("\n" + "="*50)
    print("Pipeline complete!")
    print(f"Output directory: {output_path}")
    print("="*50)

    return analyzer, sorting, qm, labels


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Neuropixels analysis pipeline (best practices)'
    )
    parser.add_argument('data_path', help='Path to SpikeGLX/OpenEphys recording')
    parser.add_argument('output_path', help='Output directory')
    parser.add_argument('--sorter', default='kilosort4',
                        choices=['kilosort4', 'kilosort3', 'spykingcircus2', 'mountainsort5'],
                        help='Spike sorter to use')
    parser.add_argument('--stream', default='imec0.ap', help='Stream name')
    parser.add_argument('--no-motion-correction', action='store_true',
                        help='Skip external motion correction; sorter defaults still apply')
    parser.add_argument('--no-phase-shift', action='store_true', help='Skip ADC phase correction after verifying acquisition timing')
    parser.add_argument('--curation', default='allen',
                        choices=['allen', 'ibl', 'strict'],
                        help='Curation method')

    args = parser.parse_args()

    run_pipeline(
        args.data_path,
        args.output_path,
        sorter=args.sorter,
        stream_name=args.stream,
        apply_motion_correction=not args.no_motion_correction,
        curation_method=args.curation,
        apply_phase_shift=not args.no_phase_shift,
    )
