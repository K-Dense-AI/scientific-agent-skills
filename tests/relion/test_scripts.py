from pathlib import Path
import importlib.util
import os
import subprocess
import numpy as np
import mrcfile
import pandas as pd
import pytest
import starfile
import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / 'skills' / 'relion'
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)
spec = importlib.util.spec_from_file_location('spa_workflow', SKILL_ROOT/'scripts'/'spa_workflow.py')
spa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(spa)


def write_map(path, data, pixel=1.5):
    with mrcfile.new(path, overwrite=True) as handle:
        handle.set_data(np.asarray(data, dtype=np.float32))
        if path.suffix == '.mrcs' and handle.data.ndim == 3:
            handle.set_image_stack()
        handle.voxel_size = pixel


def star_fixture(tmp_path):
    write_map(tmp_path/'particles.mrcs', np.ones((4, 8, 8)))
    optics = pd.DataFrame({'rlnOpticsGroup': [1], 'rlnVoltage': [300.], 'rlnSphericalAberration': [2.7],
                           'rlnAmplitudeContrast': [.1], 'rlnImagePixelSize': [1.5],
                           'rlnImageSize': [8], 'rlnImageDimensionality': [2]})
    particles = pd.DataFrame({'rlnOpticsGroup': [1]*4, 'rlnImageName': [f'{k}@particles.mrcs' for k in range(1,5)],
                              'rlnDefocusU': [10000.]*4, 'rlnDefocusV': [11000.]*4,
                              'rlnDefocusAngle': [0.]*4, 'rlnRandomSubset': [1,2,1,2]})
    path = tmp_path/'particles.star'
    starfile.write({'optics': optics, 'particles': particles}, path)
    return path, optics, particles


def half_maps(tmp_path):
    rng = np.random.default_rng(13)
    z,y,x = np.indices((32,32,32)); signal=np.exp(-((z-16)**2+(y-16)**2+(x-16)**2)/32)
    a, b = signal+rng.normal(0,.05,signal.shape), signal+rng.normal(0,.05,signal.shape)
    first, second = tmp_path/'half1.mrc', tmp_path/'half2.mrc'
    write_map(first, a); write_map(second, b)
    return first, second


def test_optics_particle_stack_and_half_set_mapping(tmp_path):
    path, _, _ = star_fixture(tmp_path)
    result = spa.validate_star(path, tmp_path)
    assert result['particles'] == 4
    assert result['half_sets'] == {'1': 2, '2': 2}
    assert result['pixel_sizes_angstrom'] == [1.5]
    assert result['stack_checks_performed'] is True


def test_padded_relion_indices_and_project_relative_paths(tmp_path):
    path, optics, particles = star_fixture(tmp_path)
    particles['rlnImageName'] = [f'{k:08d}@particles.mrcs' for k in range(1, 5)]
    job = tmp_path/'Extract'/'job010'; job.mkdir(parents=True)
    path = job/'particles.star'
    starfile.write({'optics': optics, 'particles': particles}, path)
    original = path.read_bytes()
    assert spa.validate_star(path, tmp_path)['particles'] == 4
    assert path.read_bytes() == original  # Validation never rewrites acquisition/half-set metadata.
    particles.loc[1, 'rlnImageName'] = '1@./particles.mrcs'
    starfile.write({'optics': optics, 'particles': particles}, path, overwrite=True)
    with pytest.raises(ValueError, match='Duplicate'):
        spa.validate_star(path, tmp_path)


def test_metadata_only_explicitly_reports_skipped_stacks(tmp_path):
    path, _, _ = star_fixture(tmp_path)
    (tmp_path/'particles.mrcs').unlink()
    result = spa.validate_star(path, tmp_path, check_stacks=False)
    assert result['stack_checks_performed'] is False
    with pytest.raises(OSError):
        spa.validate_star(path, tmp_path)


def test_star_loop_blocks_required(tmp_path):
    path = tmp_path/'scalar.star'
    starfile.write({'optics': {'rlnOpticsGroup': 1}, 'particles': {'rlnOpticsGroup': 1}}, path)
    with pytest.raises(ValueError, match='loop tables'):
        spa.validate_star(path, tmp_path)


@pytest.mark.parametrize('kind', ['undefined_optics', 'duplicate', 'bad_index', 'zero_index', 'defocus_sign', 'nan', 'single_half', 'nonfinite_offset'])
def test_invalid_star_scientific_contracts(tmp_path, kind):
    path, optics, particles = star_fixture(tmp_path)
    if kind == 'undefined_optics': particles.loc[0, 'rlnOpticsGroup'] = 2
    if kind == 'duplicate': particles.loc[0, 'rlnImageName'] = '2@./particles.mrcs'
    if kind == 'bad_index': particles.loc[0, 'rlnImageName'] = '9@particles.mrcs'
    if kind == 'zero_index': particles.loc[0, 'rlnImageName'] = '00000000@particles.mrcs'
    if kind == 'defocus_sign': particles.loc[0, 'rlnDefocusU'] = -1
    if kind == 'nan': optics.loc[0, 'rlnImagePixelSize'] = float('nan')
    if kind == 'single_half': particles['rlnRandomSubset'] = 1
    if kind == 'nonfinite_offset': particles['rlnOriginXAngst'] = float('inf')
    starfile.write({'optics': optics, 'particles': particles}, path, overwrite=True)
    with pytest.raises(ValueError):
        spa.validate_star(path, tmp_path)


@pytest.mark.parametrize('kind', ['axes', 'complex'])
def test_rejects_incompatible_particle_stack(tmp_path, kind):
    path, _, _ = star_fixture(tmp_path)
    with mrcfile.open(tmp_path/'particles.mrcs', mode='r+') as handle:
        if kind == 'axes':
            handle.header.mapc = 2; handle.header.mapr = 1
        else:
            handle.set_data(handle.data.astype(np.complex64))
    with pytest.raises(ValueError, match='axes|real-space'):
        spa.validate_star(path, tmp_path)


def test_float16_relion_particle_stack_supported(tmp_path):
    path, _, _ = star_fixture(tmp_path)
    with mrcfile.open(tmp_path/'particles.mrcs', mode='r+') as handle:
        handle.set_data(handle.data.astype(np.float16))
    assert spa.validate_star(path, tmp_path)['particles'] == 4


def test_fsc_detects_shared_signal_and_noise_floor(tmp_path):
    first, second = half_maps(tmp_path)
    result = spa.fsc(first, second, tmp_path/'fsc.tsv')
    frame = pd.read_csv(tmp_path/'fsc.tsv', sep='\t')
    assert frame.fsc.iloc[1] > .99
    assert abs(frame.fsc.iloc[-5:].mean()) < .05
    assert result['unmasked_diagnostic_fsc_0143_angstrom'] > result['nyquist_angstrom']
    assert result['shells'] == 17


def test_independence_and_grid_failures(tmp_path):
    first, second = half_maps(tmp_path)
    with pytest.raises(ValueError, match='identical'):
        spa.check_halves(first, first)
    with mrcfile.open(second, mode='r+') as handle:
        handle.voxel_size = 2.
    with pytest.raises(ValueError, match='disagree'):
        spa.check_halves(first, second)


@pytest.mark.parametrize('kind', ['start', 'cell_angles', 'axes', 'complex', 'origin'])
def test_map_coordinate_and_real_space_failures(tmp_path, kind):
    first, second = half_maps(tmp_path)
    with mrcfile.open(second, mode='r+') as handle:
        if kind == 'start': handle.header.nxstart = 1
        if kind == 'cell_angles': handle.header.cellb.alpha = 80
        if kind == 'axes': handle.header.mapc = 2; handle.header.mapr = 1
        if kind == 'complex': handle.set_data(handle.data.astype(np.complex64))
        if kind == 'origin': handle.header.origin.x = 1
    with pytest.raises(ValueError):
        spa.check_halves(first, second)


def test_version_gate_rejects_substring_match_and_preserves_old_output(tmp_path, monkeypatch):
    calls = []
    def fake_run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, 'RELION version 5.0.10\n', '')
    monkeypatch.setattr(spa.subprocess, 'run', fake_run)
    output = tmp_path/'new'
    with pytest.raises(ValueError, match='targets'):
        spa.run_native_command(['relion_postprocess'], output, tmp_path, 'relion_postprocess')
    assert calls == [['relion_postprocess', '--version']]
    assert not output.exists()
    output.mkdir(); (output/'run.log').write_text('prior job')
    with pytest.raises(ValueError, match='empty output'):
        spa.run_native_command(['relion_postprocess'], output, tmp_path, 'relion_postprocess')
    assert (output/'run.log').read_text() == 'prior job'
    assert len(calls) == 1


@pytest.mark.parametrize('option,value', [('--initial-lowpass', 'nan'), ('--initial-lowpass', 'inf'), ('--seed', '-1')])
def test_refine_rejects_invalid_parameters_before_native_launch(tmp_path, monkeypatch, option, value):
    import sys
    path, _, _ = star_fixture(tmp_path)
    reference = tmp_path/'reference.mrc'; write_map(reference, np.ones((8, 8, 8)))
    monkeypatch.setattr(sys, 'argv', ['spa_workflow.py', 'refine', '--star', str(path), '--project', str(tmp_path),
                                   '--reference', str(reference), '--diameter', '9', '--output', str(tmp_path/'out'),
                                   option, value])
    def unexpected_launch(*args):
        pytest.fail('Invalid parameters must not launch native software')
    monkeypatch.setattr(spa, 'run_native_command', unexpected_launch)
    with pytest.raises(SystemExit) as exc:
        spa.main()
    assert exc.value.code == 1


def test_hard_mask_is_not_accepted_for_postprocessing(tmp_path):
    first, second = half_maps(tmp_path)
    mask = np.zeros((32,32,32)); mask[8:24,8:24,8:24] = 1
    path = tmp_path/'mask.mrc'; write_map(path, mask)
    with pytest.raises(ValueError, match='soft edge'):
        spa.check_halves(first, second, path)


def test_native_relion_fsc_agrees_with_local_diagnostic(tmp_path):
    executable = os.environ.get('RELION_IMAGE_HANDLER_TEST_EXECUTABLE')
    if not executable:
        pytest.skip('Set RELION_IMAGE_HANDLER_TEST_EXECUTABLE for RELION5.0.1 CPU integration')
    first, second = half_maps(tmp_path)
    result = subprocess.run([executable, '--i', str(first), '--fsc', str(second), '--angpix', '1.5'],
                            text=True, capture_output=True, check=True, cwd=tmp_path)
    native = tmp_path/'native.star'; native.write_text(result.stdout)
    frame = starfile.read(native)
    spa.fsc(first, second, tmp_path/'local.tsv')
    local = pd.read_csv(tmp_path/'local.tsv', sep='\t')
    # RELION stores one rFFT half-plane; small differences may arise from shell weighting.
    assert np.max(abs(frame['rlnFourierShellCorrelation'].to_numpy()[1:] - local.fsc.to_numpy()[1:])) < .06


def test_native_relion_postprocess_runs_with_soft_mask(tmp_path):
    executable = os.environ.get('RELION_POSTPROCESS_TEST_EXECUTABLE')
    if not executable:
        pytest.skip('Set RELION_POSTPROCESS_TEST_EXECUTABLE for RELION5.0.1 postprocessing integration')
    first, second = half_maps(tmp_path)
    z,y,x = np.indices((32,32,32)); radius=np.sqrt((z-16)**2+(y-16)**2+(x-16)**2)
    mask = np.where(radius<=8, 1, np.where(radius>=12, 0, .5+.5*np.cos(np.pi*(radius-8)/4)))
    mask_path = tmp_path/'soft_mask.mrc'; write_map(mask_path, mask)
    import sys
    subprocess.run([sys.executable, str(SKILL_ROOT/'scripts'/'spa_workflow.py'), 'postprocess',
                    '--half1', str(first), '--half2', str(second), '--mask', str(mask_path),
                    '--output', str(tmp_path/'postprocess'), '--executable', executable],
                   capture_output=True, text=True, check=True, cwd=tmp_path)
    result = starfile.read(tmp_path/'postprocess'/'postprocess.star', always_dict=True)
    assert np.isfinite(result['general']['rlnFinalResolution'])
    assert result['general']['rlnFinalResolution'] > 3


def test_native_mpi_refinement_smoke_preserves_halves(tmp_path):
    executable = os.environ.get('RELION_REFINE_TEST_EXECUTABLE')
    if not executable:
        pytest.skip('Set RELION_REFINE_TEST_EXECUTABLE for tiny RELION5.0.1 MPI runtime smoke')
    # Symmetric smooth signal with noise is a launcher fixture, not a physical CTF simulation.
    rng = np.random.default_rng(17)
    z,y,x = np.indices((16,16,16))
    reference = np.exp(-((z-8)**2+(y-8)**2+(x-8)**2)/8)
    projection = reference.sum(axis=0); projection /= projection.std()
    images = np.stack([projection+rng.normal(0,1,(16,16)) for _ in range(32)])
    write_map(tmp_path/'initial.mrc', reference); write_map(tmp_path/'particles.mrcs', images)
    optics = pd.DataFrame({'rlnOpticsGroupName': ['optics1'], 'rlnOpticsGroup': [1],
                          'rlnVoltage': [300.], 'rlnSphericalAberration': [2.7], 'rlnAmplitudeContrast': [.1],
                          'rlnImagePixelSize': [1.5], 'rlnImageSize': [16], 'rlnImageDimensionality': [2]})
    particles = pd.DataFrame({'rlnOpticsGroup': [1]*32, 'rlnImageName': [f'{k}@particles.mrcs' for k in range(1,33)],
                             'rlnDefocusU': [10000.]*32, 'rlnDefocusV': [10000.]*32, 'rlnDefocusAngle': [0.]*32})
    starfile.write({'optics': optics, 'particles': particles}, tmp_path/'particles.star')
    import sys, json
    result = subprocess.run([sys.executable, str(SKILL_ROOT/'scripts'/'spa_workflow.py'), 'refine',
                             '--star', str(tmp_path/'particles.star'), '--reference', str(tmp_path/'initial.mrc'),
                             '--project', str(tmp_path), '--diameter', '18', '--initial-lowpass', '12',
                             '--threads', '1', '--output', str(tmp_path/'result'), '--executable', executable],
                            capture_output=True, text=True, check=True, timeout=180, cwd=tmp_path)
    report = json.loads(result.stdout)
    assert report['refined_particles']['particles'] == 32
    assert set(report['refined_particles']['half_sets']) == {'1', '2'}
    for k in (1,2):
        data, pixel, _ = spa.read_map(tmp_path/'result'/f'run_half{k}_class001_unfil.mrc')
        assert data.shape == (16,16,16) and pixel == 1.5
