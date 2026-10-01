#!/usr/bin/env python
"""
Compute quality metrics and curate units.

Usage:
    python compute_metrics.py sorting/ preprocessed/ --output metrics/
"""

import argparse
from pathlib import Path
import json

import numpy as np

from _common import load_saved, validate_recording
import spikeinterface.full as si


# Local screening presets, not reproductions of institutional pipelines.
# "ibl" is a retained legacy name, not IBL's sliding-RP/noise-cutoff classifier.
CURATION_CRITERIA = {
    'allen': {
        'snr': 3.0,
        'isi_violations_ratio': 0.5,
        'presence_ratio': 0.9,
        'amplitude_cutoff': 0.1,
    },
    'ibl': {
        'snr': 4.0,
        'firing_rate': 0.1,
        'isi_violations_ratio': 0.1,
        'presence_ratio': 0.9,
        'amplitude_cutoff': 0.1,
    },
    'strict': {
        'snr': 5.0,
        'isi_violations_ratio': 0.01,
        'presence_ratio': 0.95,
        'amplitude_cutoff': 0.01,
    },
}


METRIC_NAMES = ['snr', 'isi_violation', 'presence_ratio', 'amplitude_cutoff', 'firing_rate', 'amplitude_cv']


def curate_units(metrics, method='allen'):
    """Screen units conservatively; absent/nonfinite evidence is unresolved."""
    if method not in CURATION_CRITERIA:
        raise ValueError(f"unknown curation method {method!r}; choose allen, ibl, or strict")
    criteria = CURATION_CRITERIA[method]
    labels = {}
    for unit_id, row in metrics.iterrows():
        values = {key: row.get(key, np.nan) for key in criteria}
        if not all(np.isfinite(value) for value in values.values()):
            labels[unit_id] = 'unsorted'
        elif values['snr'] < 1.5:
            labels[unit_id] = 'noise'
        elif all(values[key] > limit if key in {'snr', 'presence_ratio', 'firing_rate'}
                 else values[key] < limit for key, limit in criteria.items()):
            labels[unit_id] = 'good'
        elif values['isi_violations_ratio'] > (0.05 if method == 'strict' else criteria['isi_violations_ratio']):
            labels[unit_id] = 'mua'
        else:
            labels[unit_id] = 'unsorted'
    return labels


def compute_metrics(
    sorting_path: str,
    recording_path: str,
    output_dir: str,
    curation_method: str = 'allen',
    n_jobs: int = -1,
):
    """Compute quality metrics and apply curation."""

    print(f"Loading sorting from: {sorting_path}")
    sorting = load_saved(sorting_path, 'sorting')

    print(f"Loading recording from: {recording_path}")
    recording = load_saved(recording_path, 'preprocessed')
    validate_recording(recording)
    si.set_global_job_kwargs(n_jobs=n_jobs, chunk_duration='1s')

    print(f"Units: {len(sorting.unit_ids)}")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Create analyzer
    print("Creating SortingAnalyzer...")
    analyzer = si.create_sorting_analyzer(
        sorting,
        recording,
        format='binary_folder',
        folder=output_path / 'analyzer',
        sparse=True,
    )

    # Compute extensions
    print("Computing waveforms...")
    analyzer.compute('random_spikes', max_spikes_per_unit=500)
    analyzer.compute('waveforms', ms_before=1.0, ms_after=2.0)
    analyzer.compute('templates', operators=['average', 'std'])

    print("Computing additional extensions...")
    analyzer.compute('noise_levels')
    analyzer.compute('spike_amplitudes')
    analyzer.compute('amplitude_scalings')
    analyzer.compute('correlograms', window_ms=50.0, bin_ms=1.0)
    analyzer.compute('unit_locations', method='monopolar_triangulation')
    analyzer.compute('template_similarity')

    # Compute quality metrics
    print("Computing quality metrics...")
    metrics = si.compute_quality_metrics(
        analyzer,
        metric_names=METRIC_NAMES,
        n_jobs=n_jobs,
    )

    # Save metrics
    metrics.to_csv(output_path / 'quality_metrics.csv')
    print(f"Saved metrics to: {output_path / 'quality_metrics.csv'}")

    labels = curate_units(metrics, method=curation_method)

    # Save labels
    with open(output_path / 'curation_labels.json', 'w') as f:
        json.dump({str(uid): label for uid, label in labels.items()}, f, indent=2)

    # Summary
    label_counts = {}
    for label in labels.values():
        label_counts[label] = label_counts.get(label, 0) + 1

    print(f"\nCuration summary:")
    print(f"  Good: {label_counts.get('good', 0)}")
    print(f"  MUA: {label_counts.get('mua', 0)}")
    print(f"  Noise: {label_counts.get('noise', 0)}")
    print(f"  Unsorted: {label_counts.get('unsorted', 0)}")
    print(f"  Total: {len(labels)}")

    # Metrics summary
    print(f"\nMetrics summary:")
    for col in ['snr', 'isi_violations_ratio', 'presence_ratio', 'firing_rate']:
        if col in metrics.columns:
            print(f"  {col}: {metrics[col].median():.4f} (median)")

    return analyzer, metrics, labels


def main():
    parser = argparse.ArgumentParser(description='Compute quality metrics')
    parser.add_argument('sorting', help='Path to sorting directory')
    parser.add_argument('recording', help='Path to preprocessed recording')
    parser.add_argument('--output', '-o', default='metrics/', help='Output directory')
    parser.add_argument('--curation', '-c', default='allen',
                       choices=['allen', 'ibl', 'strict'])
    parser.add_argument('--n-jobs', type=int, default=-1, help='Number of parallel jobs')

    args = parser.parse_args()

    compute_metrics(
        args.sorting,
        args.recording,
        args.output,
        curation_method=args.curation,
        n_jobs=args.n_jobs,
    )


if __name__ == '__main__':
    main()
