from pathlib import Path
import csv
import importlib.util
import json
import os
import subprocess
import sys
import numpy as np
import pytest
import tifffile
import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / 'skills' / 'cellprofiler'
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)
spec = importlib.util.spec_from_file_location('nuclei_assay', SKILL_ROOT / 'scripts' / 'nuclei_assay.py')
assay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assay)


def fixture_manifest(tmp_path):
    yy, xx = np.indices((128, 128))
    data = np.zeros((128, 128), dtype=np.uint16)
    for cy, cx, intensity in [(30, 30, 20000), (30, 90, 30000), (90, 60, 40000)]:
        data[(yy-cy)**2+(xx-cx)**2 <= 10**2] = intensity
    tifffile.imwrite(tmp_path / 'nuclei.tif', data)
    manifest = tmp_path / 'manifest.csv'
    manifest.write_text('sample_id,image_path,plate,well,site\ncontrol,nuclei.tif,P1,A01,1\n')
    return manifest


def test_prepare_preserves_scaling_and_sample_identity(tmp_path):
    manifest = fixture_manifest(tmp_path)
    result = assay.prepare(manifest, tmp_path / 'load.csv')
    assert result['images'][0]['dtype'] == 'uint16'
    assert result['images'][0]['saturated_fraction'] == 0
    with (tmp_path / 'load.csv').open() as f:
        rows = list(csv.DictReader(f))
    assert rows[0]['Metadata_Well'] == 'A01'
    assert rows[0]['URL_DNA'] == (tmp_path / 'nuclei.tif').as_uri()


@pytest.mark.parametrize('kind', ['rgb', 'float', 'constant', 'duplicate'])
def test_invalid_images_and_duplicate_acquisition_rejected(tmp_path, kind):
    manifest = fixture_manifest(tmp_path)
    if kind == 'duplicate':
        with manifest.open('a') as f:
            f.write('duplicate,nuclei.tif,P1,A01,1\n')
    else:
        data = {'rgb': np.zeros((32, 32, 3), dtype=np.uint8),
                'float': np.ones((32, 32), dtype=np.float32),
                'constant': np.zeros((32, 32), dtype=np.uint16)}[kind]
        tifffile.imwrite(tmp_path / 'nuclei.tif', data)
    with pytest.raises(ValueError):
        assay.prepare(manifest, tmp_path / 'load.csv')


def test_measurement_consistency(tmp_path):
    write_measurements(tmp_path)
    assert assay.summarize(tmp_path, ['control'])['measurements'][0]['mean_nuclear_intensity'] == 0.5
    with pytest.raises(ValueError, match='identities'):
        assay.summarize(tmp_path, ['other'])
    path = tmp_path / 'Nuclei.csv'
    path.write_text(path.read_text().replace('0.25', 'nan'))
    with pytest.raises(ValueError, match='Nonfinite'):
        assay.summarize(tmp_path)


def write_measurements(directory):
    (directory / 'Image.csv').write_text('ImageNumber,Metadata_Sample,Count_Nuclei\n1,control,2\n')
    (directory / 'Nuclei.csv').write_text(
        'ImageNumber,ObjectNumber,Intensity_MeanIntensity_DNA,Intensity_IntegratedIntensity_DNA,AreaShape_Area\n'
        '1,1,0.25,25,100\n1,2,0.75,75,100\n')


@pytest.mark.parametrize('sample', ['001', '1e3', 'nan', 'inf'])
def test_numeric_sample_identifiers_rejected_before_loaddata_coercion(tmp_path, sample):
    manifest = fixture_manifest(tmp_path)
    manifest.write_text(manifest.read_text().replace('control,', sample + ','))
    with pytest.raises(ValueError, match='must not be numeric'):
        assay.prepare(manifest, tmp_path / 'load.csv')


@pytest.mark.parametrize('malformation', ['short_row', 'long_row', 'duplicate_header', 'whitespace'])
def test_malformed_manifest_rejected(tmp_path, malformation):
    manifest = fixture_manifest(tmp_path)
    text = manifest.read_text()
    if malformation == 'short_row':
        text = text.replace(',A01,1', ',A01')
    elif malformation == 'long_row':
        text = text.replace(',A01,1', ',A01,1,extra')
    elif malformation == 'duplicate_header':
        text = text.replace('site\n', 'well\n')
    else:
        text = text.replace('P1', ' P1')
    manifest.write_text(text)
    with pytest.raises(ValueError):
        assay.prepare(manifest, tmp_path / 'load.csv')


def test_multiple_tiff_series_are_not_silently_ignored(tmp_path):
    manifest = fixture_manifest(tmp_path)
    with tifffile.TiffWriter(tmp_path / 'nuclei.tif') as writer:
        writer.write(np.arange(32*32, dtype=np.uint16).reshape(32, 32))
        writer.write(np.arange(64*64, dtype=np.uint16).reshape(64, 64))
    with pytest.raises(ValueError, match='single TIFF plane'):
        assay.prepare(manifest, tmp_path / 'load.csv')


@pytest.mark.parametrize('destination', ['manifest.csv', 'nuclei.tif'])
def test_prepare_cannot_overwrite_inputs(tmp_path, destination):
    manifest = fixture_manifest(tmp_path)
    before = (tmp_path / destination).read_bytes()
    with pytest.raises(ValueError, match='must not overwrite'):
        assay.prepare(manifest, tmp_path / destination)
    assert (tmp_path / destination).read_bytes() == before


def test_storage_saturation_flag_and_uint8_input(tmp_path):
    manifest = fixture_manifest(tmp_path)
    image = np.zeros((32, 32), dtype=np.uint8)
    image[:4] = 255
    tifffile.imwrite(tmp_path / 'nuclei.tif', image)
    result = assay.prepare(manifest, tmp_path / 'load.csv')
    assert result['images'][0]['saturated_fraction'] == 0.125
    assert 'storage maximum' in result['warnings'][0]


def test_prepare_and_summarize_cli(tmp_path):
    manifest = fixture_manifest(tmp_path)
    script = SKILL_ROOT / 'scripts' / 'nuclei_assay.py'
    result = subprocess.run([sys.executable, str(script), 'prepare', str(manifest), str(tmp_path / 'load.csv')],
                            capture_output=True, text=True, check=True)
    assert json.loads(result.stdout)['images'][0]['sample_id'] == 'control'
    write_measurements(tmp_path)
    result = subprocess.run([sys.executable, str(script), 'summarize', str(tmp_path)],
                            capture_output=True, text=True, check=True)
    summary = json.loads(result.stdout)['measurements'][0]
    assert summary['nuclei'] == 2
    assert summary['mean_nuclear_area_pixels'] == 100


@pytest.mark.parametrize('value', ['2.5', '2.0000000000000001', 'nan', 'inf', '-1'])
def test_invalid_nuclear_counts_rejected(tmp_path, value):
    write_measurements(tmp_path)
    (tmp_path / 'Image.csv').write_text(f'ImageNumber,Metadata_Sample,Count_Nuclei\n1,control,{value}\n')
    with pytest.raises(ValueError, match='finite integer'):
        assay.summarize(tmp_path)


@pytest.mark.parametrize('photometric', ['miniswhite', 'palette'])
def test_ambiguous_tiff_photometric_interpretations_rejected(tmp_path, photometric):
    manifest = fixture_manifest(tmp_path)
    data = np.arange(32*32, dtype=np.uint8).reshape(32, 32)
    options = {'colormap': np.tile(np.arange(256, dtype=np.uint16), (3, 1))} if photometric == 'palette' else {}
    tifffile.imwrite(tmp_path / 'nuclei.tif', data, photometric=photometric, **options)
    with pytest.raises(ValueError, match='MINISBLACK'):
        assay.prepare(manifest, tmp_path / 'load.csv')


@pytest.mark.parametrize('change,error', [
    ('duplicate_object', 'Duplicate ImageNumber/ObjectNumber'),
    ('orphan', 'Orphan'),
    ('object_gap', 'rows disagree'),
    ('duplicate_image', 'Duplicate ImageNumber'),
    ('bad_area', 'nuclear areas'),
    ('bad_integrated', 'integrated intensities'),
    ('module_error', 'failed module'),
])
def test_measurement_corruption_rejected(tmp_path, change, error):
    write_measurements(tmp_path)
    obj = tmp_path / 'Nuclei.csv'
    img = tmp_path / 'Image.csv'
    if change == 'duplicate_object':
        obj.write_text(obj.read_text().replace('1,2,0.75', '1,1,0.75'))
    elif change == 'orphan':
        obj.write_text(obj.read_text().replace('1,2,0.75', '2,2,0.75'))
    elif change == 'object_gap':
        obj.write_text(obj.read_text().replace('1,2,0.75', '1,3,0.75'))
    elif change == 'duplicate_image':
        img.write_text(img.read_text() + '1,other,2\n')
    elif change == 'bad_area':
        obj.write_text(obj.read_text().replace(',100', ',0'))
    elif change == 'bad_integrated':
        obj.write_text(obj.read_text().replace(',75,', ',inf,'))
    else:
        img.write_text('ImageNumber,Metadata_Sample,Count_Nuclei,ModuleError_01LoadData\n1,control,2,1\n')
    with pytest.raises(ValueError, match=error):
        assay.summarize(tmp_path)


def test_zero_objects_retains_field_with_warning(tmp_path):
    write_measurements(tmp_path)
    (tmp_path / 'Image.csv').write_text('ImageNumber,Metadata_Sample,Count_Nuclei\n1,control,0\n')
    path = tmp_path / 'Nuclei.csv'
    path.write_text(path.read_text().splitlines()[0] + '\n')
    result = assay.summarize(tmp_path)
    assert result['measurements'][0]['mean_nuclear_intensity'] is None
    assert result['measurements'][0]['mean_nuclear_area_pixels'] is None
    assert 'zero nuclei' in result['warnings'][0]


@pytest.mark.parametrize('outcome', ['complete', 'process_failure', 'missing_marker', 'failure_marker', 'bad_csv'])
def test_run_preserves_provenance_and_requires_completion(tmp_path, monkeypatch, outcome):
    manifest = fixture_manifest(tmp_path)
    output = tmp_path / 'output'
    pipeline = SKILL_ROOT / 'assets' / 'nuclei.cppipe'

    def fake_cellprofiler(command, *, stdout, stderr, check):
        assert command[1:3] == ['-c', '-r']
        assert Path(command[command.index('-p') + 1]).read_bytes() == pipeline.read_bytes()
        assert Path(command[command.index('--data-file') + 1]).is_file()
        assert json.loads((output / 'assay_qc.json').read_text())['status'] == 'running'
        stdout.write('simulated engine log\n')
        if outcome == 'process_failure':
            raise subprocess.CalledProcessError(3, command)
        write_measurements(output)
        if outcome != 'missing_marker':
            Path(command[command.index('--done-file') + 1]).write_text(
                'Failure\n' if outcome == 'failure_marker' else 'Complete\n')
        if outcome == 'bad_csv':
            (output / 'Nuclei.csv').write_text('broken export\n')

    monkeypatch.setattr(assay.subprocess, 'run', fake_cellprofiler)
    if outcome == 'complete':
        result = assay.run(manifest, output, 'cellprofiler', pipeline)
        assert result['status'] == 'complete'
    else:
        with pytest.raises((ValueError, subprocess.CalledProcessError)):
            assay.run(manifest, output, 'cellprofiler', pipeline)
    recorded = json.loads((output / 'assay_qc.json').read_text())
    assert recorded['status'] == ('complete' if outcome == 'complete' else 'failed')
    assert len(recorded['input_qc']['images'][0]['sha256']) == 64
    assert recorded['pipeline_sha256'] == assay._sha256(output / 'pipeline.cppipe')
    assert (output / 'cellprofiler.log').read_text() == 'simulated engine log\n'


def test_real_cellprofiler_synthetic_counts_and_intensity(tmp_path):
    executable = os.environ.get('CELLPROFILER_TEST_EXECUTABLE')
    if not executable:
        pytest.skip('Set CELLPROFILER_TEST_EXECUTABLE for installed CellProfiler 4.2.8 integration')
    result = assay.run(fixture_manifest(tmp_path), tmp_path / 'output', executable,
                       SKILL_ROOT / 'assets' / 'nuclei.cppipe')
    assert result['measurements'][0]['nuclei'] == 3
    assert result['measurements'][0]['mean_nuclear_intensity'] == pytest.approx(30000/65535, abs=0.03)
    assert (tmp_path / 'output' / 'control_nuclei.png').is_file()
