#!/usr/bin/env python
"""
Neuropixels Analysis Template

Complete analysis workflow from raw data to curated units.
Illustrative template: copy, customize, and validate on your own recording and sorter.

Usage:
    1. Copy this file to your analysis directory
    2. Copy the skill scripts/ alongside it as neuropixels_scripts/
    3. Update the PARAMETERS section
    4. Run: python analysis_template.py
"""

# =============================================================================
# PARAMETERS - Customize these for your analysis
# =============================================================================

# Input/Output paths
DATA_PATH = '/path/to/your/spikeglx/data/'
OUTPUT_DIR = 'analysis_output/'
DATA_FORMAT = 'spikeglx'  # 'spikeglx', 'openephys', or 'nwb'
STREAM_NAME = 'imec0.ap'    # Select the exact AP stream discovered in acquisition metadata

# Preprocessing parameters
FREQ_MIN = 300           # Highpass filter (Hz)
FREQ_MAX = 6000          # Lowpass filter (Hz)
APPLY_PHASE_SHIFT = True
APPLY_CMR = True
DETECT_BAD_CHANNELS = True

# Motion correction
CORRECT_MOTION = True
MOTION_PRESET = 'nonrigid_accurate'  # 'kilosort_like', 'nonrigid_fast_and_accurate'

# Spike sorting
SORTER = 'kilosort4'     # 'kilosort4', 'spykingcircus2', 'mountainsort5'
SORTER_PARAMS = {
    'batch_size': 30000,
    'nblocks': 1,        # Internal Kilosort correction only when CORRECT_MOTION=False
}

# Quality metrics and curation
CURATION_METHOD = 'allen'  # 'allen', 'ibl', 'strict'

# Processing
N_JOBS = -1              # -1 = all cores

# =============================================================================
# ANALYSIS PIPELINE - Usually no need to modify below
# =============================================================================

from pathlib import Path
import json
import sys

# When used inside this skill, use ../scripts; when copied, use the bundled copy.
script_dir = Path(__file__).resolve().parents[1] / "scripts"
if not (script_dir / "compute_metrics.py").is_file():
    script_dir = Path(__file__).resolve().parent / "neuropixels_scripts"
sys.path.insert(0, str(script_dir))
from compute_metrics import curate_units, METRIC_NAMES
from _common import validate_recording, apply_phase_correction, reference_by_shank

import spikeinterface.full as si
from spikeinterface.exporters import export_to_phy


def main():
    """Run the full analysis pipeline."""

    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # 1. LOAD DATA
    # =========================================================================
    print("=" * 60)
    print("1. LOADING DATA")
    print("=" * 60)

    if DATA_FORMAT == 'spikeglx':
        recording = si.read_spikeglx(DATA_PATH, stream_name=STREAM_NAME)
    elif DATA_FORMAT == 'openephys':
        recording = si.read_openephys(DATA_PATH, stream_name=STREAM_NAME)
    elif DATA_FORMAT == 'nwb':
        recording = si.read_nwb(DATA_PATH)
    else:
        raise ValueError(f"Unknown format: {DATA_FORMAT}")

    validate_recording(recording)
    si.set_global_job_kwargs(n_jobs=N_JOBS, chunk_duration="1s")

    print(f"Recording: {recording.get_num_channels()} channels")
    print(f"Duration: {recording.get_total_duration():.1f} seconds")
    print(f"Sampling rate: {recording.get_sampling_frequency()} Hz")

    # =========================================================================
    # 2. PREPROCESSING
    # =========================================================================
    print("\n" + "=" * 60)
    print("2. PREPROCESSING")
    print("=" * 60)

    rec = recording

    # Bandpass filter
    print(f"Applying bandpass filter ({FREQ_MIN}-{FREQ_MAX} Hz)...")
    rec = si.bandpass_filter(rec, freq_min=FREQ_MIN, freq_max=FREQ_MAX)

    # Phase shift correction
    if APPLY_PHASE_SHIFT:
        print("Applying phase shift correction...")
        rec = apply_phase_correction(rec)

    # Bad channel detection
    if DETECT_BAD_CHANNELS:
        print("Detecting bad channels...")
        bad_ids, _ = si.detect_bad_channels(rec)
        if len(bad_ids) > 0:
            print(f"  Removing {len(bad_ids)} bad channels")
            rec = rec.remove_channels(bad_ids)

    # Common median reference
    if APPLY_CMR:
        print("Applying common median reference...")
        rec = reference_by_shank(rec)

    # Save preprocessed
    print("Saving preprocessed recording...")
    rec = rec.save(folder=output_path / 'preprocessed', n_jobs=N_JOBS)

    # =========================================================================
    # 3. MOTION CORRECTION
    # =========================================================================
    if CORRECT_MOTION:
        print("\n" + "=" * 60)
        print("3. MOTION CORRECTION")
        print("=" * 60)

        print(f"Estimating and correcting motion (preset: {MOTION_PRESET})...")
        rec = si.correct_motion(
            rec,
            preset=MOTION_PRESET,
            folder=output_path / 'motion',
        )

    # =========================================================================
    # 4. SPIKE SORTING
    # =========================================================================
    print("\n" + "=" * 60)
    print("4. SPIKE SORTING")
    print("=" * 60)

    print(f"Running {SORTER}...")
    sorter_params = SORTER_PARAMS.copy()
    if CORRECT_MOTION:
        # Disable the sorter's own motion stage after external interpolation.
        if SORTER in {"kilosort2_5", "kilosort3", "kilosort4"}:
            sorter_params["do_correction"] = False
        elif SORTER == "spykingcircus2":
            sorter_params["apply_motion_correction"] = False
    sorting = si.run_sorter(
        SORTER,
        rec,
        folder=output_path / f'{SORTER}_output',
        verbose=True,
        **sorter_params,
    )

    print(f"Found {len(sorting.unit_ids)} units")

    # =========================================================================
    # 5. POSTPROCESSING
    # =========================================================================
    print("\n" + "=" * 60)
    print("5. POSTPROCESSING")
    print("=" * 60)

    print("Creating SortingAnalyzer...")
    analyzer = si.create_sorting_analyzer(
        sorting,
        rec,
        format='binary_folder',
        folder=output_path / 'analyzer',
        sparse=True,
    )

    print("Computing extensions...")
    analyzer.compute('random_spikes', max_spikes_per_unit=500)
    analyzer.compute('waveforms', ms_before=1.0, ms_after=2.0)
    analyzer.compute('templates', operators=['average', 'std'])
    analyzer.compute('noise_levels')
    analyzer.compute('spike_amplitudes')
    analyzer.compute('amplitude_scalings')
    analyzer.compute('correlograms', window_ms=50.0, bin_ms=1.0)
    analyzer.compute('unit_locations', method='monopolar_triangulation')

    # =========================================================================
    # 6. QUALITY METRICS
    # =========================================================================
    print("\n" + "=" * 60)
    print("6. QUALITY METRICS")
    print("=" * 60)

    print("Computing quality metrics...")
    metrics = si.compute_quality_metrics(
        analyzer,
        metric_names=METRIC_NAMES,
        n_jobs=N_JOBS,
    )

    metrics.to_csv(output_path / 'quality_metrics.csv')
    print(f"Saved metrics to: {output_path / 'quality_metrics.csv'}")

    # Print summary
    print("\nMetrics summary:")
    for col in ['snr', 'isi_violations_ratio', 'presence_ratio', 'firing_rate']:
        if col in metrics.columns:
            print(f"  {col}: {metrics[col].median():.4f} (median)")

    # =========================================================================
    # 7. CURATION
    # =========================================================================
    print("\n" + "=" * 60)
    print("7. CURATION")
    print("=" * 60)

    labels = curate_units(metrics, method=CURATION_METHOD)

    # Save labels
    with open(output_path / 'curation_labels.json', 'w') as f:
        json.dump({str(uid): label for uid, label in labels.items()}, f, indent=2)

    # Count
    good_count = sum(1 for v in labels.values() if v == 'good')
    mua_count = sum(1 for v in labels.values() if v == 'mua')
    noise_count = sum(1 for v in labels.values() if v == 'noise')

    print(f"\nCuration results:")
    print(f"  Good: {good_count}")
    print(f"  MUA: {mua_count}")
    print(f"  Noise: {noise_count}")
    print(f"  Total: {len(labels)}")

    # =========================================================================
    # 8. EXPORT
    # =========================================================================
    print("\n" + "=" * 60)
    print("8. EXPORT")
    print("=" * 60)

    analyzer.sorting.set_property('curation_label', [labels[uid] for uid in analyzer.sorting.unit_ids])
    good_ids = [uid for uid, label in labels.items() if label == 'good']
    sorting.select_units(good_ids).save(folder=output_path / 'sorting_curated')
    print("Exporting all units with screening labels to Phy...")
    export_to_phy(
        analyzer,
        output_folder=output_path / 'phy_export',
        copy_binary=True,
        additional_properties=['curation_label'],
    )

    print(f"\nAnalysis complete!")
    print(f"Results saved to: {output_path}")
    print(f"\nTo open in Phy:")
    print(f"  phy template-gui {output_path / 'phy_export' / 'params.py'}")


if __name__ == '__main__':
    main()
