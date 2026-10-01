"""Small CPU fixtures exercise scientific data contracts, not sorter accuracy."""
import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / 'skills' / 'neuropixels-analysis'
sys.path.insert(0, str(SKILL_ROOT / 'scripts'))
si = pytest.importorskip('spikeinterface.full')
np = pytest.importorskip('numpy')
pd = pytest.importorskip('pandas')
pytest.importorskip('numba')
pytest.importorskip('sklearn')
from probeinterface import Probe
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import _common
import compute_metrics
import preprocess_recording
import explore_recording
import export_to_phy
import run_sorting


@pytest.fixture
def calibrated_recording():
    rec = si.generate_recording(num_channels=8, durations=[2.0], sampling_frequency=10000.0, seed=12)
    probe = rec.get_probe()
    probe.set_shank_ids(['0'] * 8)
    rec.set_probe(probe)
    rec.set_channel_gains(2.0)
    rec.set_channel_offsets(0.0)
    rec.set_property('inter_sample_shift', np.linspace(0, 0.8, 8))
    return rec


def test_missing_metrics_and_string_ids_are_not_auto_accepted():
    row = dict(snr=10., isi_violations_ratio=0., presence_ratio=.99, amplitude_cutoff=.001, firing_rate=2.)
    for value in (np.nan, np.inf, -np.inf):
        for field in row:
            data = pd.DataFrame([{**row, field: value}], index=['unit-A'])
            assert compute_metrics.curate_units(data, 'ibl') == {'unit-A': 'unsorted'}
    data = pd.DataFrame([row], index=['unit-A'])
    assert compute_metrics.curate_units(data, 'allen') == {'unit-A': 'good'}
    assert compute_metrics.curate_units(data.drop(columns=['presence_ratio'])) == {'unit-A': 'unsorted'}
    with pytest.raises(ValueError, match='unknown curation method'):
        compute_metrics.curate_units(data, 'aleln')


def test_per_shank_reference_uses_device_mapping():
    traces = np.array([[100., 101., 10., 12.], [200., 202., 20., 24.]], dtype='float32')
    rec = si.NumpyRecording(traces, sampling_frequency=30000, channel_ids=['A','B','C','D'])
    probe = Probe(ndim=2, si_units='um')
    probe.set_contacts(np.array([[0.,0.], [0.,20.], [200.,0.], [200.,20.]]), shapes='circle', shape_params={'radius':5})
    probe.set_shank_ids(['left','left','right','right'])
    probe.set_device_channel_indices([2,3,0,1])
    rec.set_probe(probe)
    result = _common.reference_by_shank(rec).get_traces()
    np.testing.assert_allclose(result, [[-.5,.5,-1,1],[-1,1,-2,2]])
    assert rec.channel_ids.tolist() == ['A','B','C','D']


def test_recording_contract_rejects_uncalibrated_or_multisegment(calibrated_recording):
    _common.validate_recording(calibrated_recording)
    rec = si.generate_recording(num_channels=8, durations=[1.,1.], sampling_frequency=10000)
    with pytest.raises(ValueError, match='one recording segment'):
        _common.validate_recording(rec)
    calibrated_recording.delete_property('gain_to_uV')
    with pytest.raises(ValueError, match='calibrated'):
        _common.validate_recording(calibrated_recording)


def test_phase_shift_requires_real_timing_metadata(calibrated_recording):
    shifted = _common.apply_phase_correction(calibrated_recording)
    assert np.isfinite(shifted.get_traces(end_frame=100)).all()
    calibrated_recording.delete_property('inter_sample_shift')
    with pytest.raises(ValueError, match='inter_sample_shift'):
        _common.apply_phase_correction(calibrated_recording)


def test_preprocessing_roundtrip_and_parent_paths(calibrated_recording, tmp_path):
    inp = tmp_path/'input'
    calibrated_recording.save(folder=inp, n_jobs=1)
    rec = preprocess_recording.preprocess_recording(str(inp), str(tmp_path/'out'),
                 freq_min=300, freq_max=3000, detect_bad=False, n_jobs=1)
    direct = _common.load_saved(tmp_path/'out'/'preprocessed', 'preprocessed')
    parent = _common.load_saved(tmp_path/'out', 'preprocessed')
    np.testing.assert_array_equal(direct.channel_ids, parent.channel_ids)
    np.testing.assert_allclose(rec.get_traces(end_frame=100), direct.get_traces(end_frame=100))
    with pytest.raises(ValueError, match='Nyquist'):
        preprocess_recording.preprocess_recording(str(inp), str(tmp_path/'invalid'), freq_max=6000, n_jobs=1)


def test_short_trace_plot_clamps_to_available_samples(calibrated_recording, tmp_path):
    explore_recording.plot_traces(calibrated_recording, duration=10., output_path=tmp_path/'trace.png')
    assert len(plt.gcf().axes[0].lines[0].get_xdata()) == calibrated_recording.get_num_samples()
    plt.close('all')


def test_sorter_defaults_match_current_wrappers():
    for name in ('kilosort3','spykingcircus2','mountainsort5'):
        assert set(run_sorting.SORTER_DEFAULTS[name]) <= set(si.get_default_sorter_params(name))
    assert run_sorting.SORTER_DEFAULTS['mountainsort5']['whiten'] is True


@pytest.mark.parametrize('string_ids', [False, True])
def test_analyzer_metrics_phy_roundtrip_and_template(tmp_path, string_ids):
    si.set_global_job_kwargs(n_jobs=1, progress_bar=False)
    rec, sorting = si.generate_ground_truth_recording(durations=[3.], num_channels=8,
        sampling_frequency=30000, num_units=3, seed=42)
    if string_ids:
        sorting = sorting.rename_units(['alpha','beta','gamma'])
    first, second = sorting.unit_ids[:2]
    rec.save(folder=tmp_path/'recording'/'preprocessed', n_jobs=1)
    sorting.save(folder=tmp_path/'sorter'/'sorting')
    analyzer, metrics, labels = compute_metrics.compute_metrics(
        tmp_path/'sorter', tmp_path/'recording', tmp_path/'metrics', n_jobs=1)
    assert set(metrics.index) == set(sorting.unit_ids)
    assert 'isi_violations_ratio' in metrics
    assert metrics.presence_ratio.isna().all()  # Default 60s bin exceeds fixture duration.
    assert set(labels.values()) == {'unsorted'}
    analyzer.compute('quality_metrics', metric_names=['presence_ratio'],
                     metric_params={'presence_ratio': {'bin_duration_s': 1.}})
    assert np.isfinite(analyzer.get_extension('quality_metrics').get_data()['presence_ratio']).all()
    assert analyzer.get_extension('waveforms').get_waveforms_one_unit(first).ndim == 3
    # Actual widgets used by the skill, including corrected density-map spelling.
    si.plot_unit_waveforms_density_map(analyzer, unit_ids=[first])
    si.plot_unit_waveforms(analyzer, unit_ids=[first], plot_channels=True)
    si.plot_crosscorrelograms(analyzer, unit_ids=[first,second])
    si.plot_unit_summary(analyzer, unit_id=first)
    plt.close('all')
    export_to_phy.export_phy(tmp_path/'metrics'/'analyzer', tmp_path/'phy', n_jobs=1)
    if string_ids:
        mapping = pd.read_csv(tmp_path/'phy'/'cluster_si_unit_ids.tsv', sep='\t')
        assert mapping.si_unit_id.tolist() == sorting.unit_ids.tolist()
        # Confirm and document the upstream0.105 readback limitation; export is valid.
        with pytest.raises(TypeError, match='isnan'):
            si.read_phy(tmp_path/'phy')
    else:
        loaded = si.read_phy(tmp_path/'phy')
        assert loaded.count_total_num_spikes() == sorting.count_total_num_spikes()
        assert loaded.get_sampling_frequency() == sorting.get_sampling_frequency()
    # Template uses the same classifier even when copied logic elsewhere changes.
    spec = importlib.util.spec_from_file_location('analysis_template', SKILL_ROOT/'assets'/'analysis_template.py')
    template = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(template)
    assert template.curate_units is compute_metrics.curate_units


def test_motion_object_interpolation_roundtrip(calibrated_recording, tmp_path):
    from spikeinterface.core import Motion
    from spikeinterface.sortingcomponents.motion import interpolate_motion
    motion = Motion(np.zeros((4,1)), np.array([.25,.75,1.25,1.75]), np.array([70.]), direction='y')
    motion.save(tmp_path/'motion')
    loaded = si.load(tmp_path/'motion')
    result = interpolate_motion(calibrated_recording, loaded, border_mode='force_extrapolate')
    assert result.get_num_samples() == calibrated_recording.get_num_samples()
    np.testing.assert_array_equal(result.channel_ids, calibrated_recording.channel_ids)
    assert np.isfinite(result.get_traces(end_frame=100)).all()


def test_peak_localization_and_estimated_motion_contract(tmp_path):
    from spikeinterface.sortingcomponents.peak_detection import detect_peaks
    from spikeinterface.sortingcomponents.peak_localization import localize_peaks
    from spikeinterface.sortingcomponents.motion import estimate_motion, interpolate_motion
    from spikeinterface.core import Motion
    rec, _ = si.generate_ground_truth_recording(durations=[4.], num_channels=8,
                         sampling_frequency=30000, num_units=3, seed=19)
    noise = si.get_noise_levels(rec, return_in_uV=False)
    peaks = detect_peaks(rec, method='locally_exclusive', method_kwargs={'noise_levels': noise, 'detect_threshold': 4, 'radius_um': 50}, job_kwargs={'n_jobs': 1})
    assert len(peaks) > 0
    assert set(peaks.dtype.names) == {'sample_index','channel_index','amplitude','segment_index'}
    locations = localize_peaks(rec, peaks, method='center_of_mass', job_kwargs={'n_jobs': 1})
    motion = estimate_motion(rec, peaks, locations, method='decentralized', rigid=True,
                             bin_s=1., conv_engine='numpy', max_displacement_um=20.)
    assert isinstance(motion, Motion)
    assert motion.displacement[0].shape[1] == 1
    assert np.isfinite(motion.displacement[0]).all()
    rec2 = interpolate_motion(rec, motion, border_mode='force_extrapolate')
    assert np.isfinite(rec2.get_traces(end_frame=100)).all()
    si.plot_motion(motion)
    si.plot_drift_raster_map(peaks=peaks, peak_locations=locations, recording=rec)
    plt.close('all')
