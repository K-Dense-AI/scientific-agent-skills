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
    (tmp_path / 'Image.csv').write_text('ImageNumber,Metadata_Sample,Count_Nuclei\n1,control,2\n')
    (tmp_path / 'Nuclei.csv').write_text('ImageNumber,Intensity_MeanIntensity_DNA\n1,0.25\n1,0.75\n')
    assert assay.summarize(tmp_path, ['control'])['measurements'][0]['mean_nuclear_intensity'] == 0.5
    with pytest.raises(ValueError, match='identities'):
        assay.summarize(tmp_path, ['other'])
    (tmp_path / 'Nuclei.csv').write_text('ImageNumber,Intensity_MeanIntensity_DNA\n1,nan\n1,0.75\n')
    with pytest.raises(ValueError, match='Nonfinite'):
        assay.summarize(tmp_path)


def test_real_cellprofiler_synthetic_counts_and_intensity(tmp_path):
    executable = os.environ.get('CELLPROFILER_TEST_EXECUTABLE')
    if not executable:
        pytest.skip('Set CELLPROFILER_TEST_EXECUTABLE for installed CellProfiler 4.2.8 integration')
    result = assay.run(fixture_manifest(tmp_path), tmp_path / 'output', executable,
                       SKILL_ROOT / 'assets' / 'nuclei.cppipe')
    assert result['measurements'][0]['nuclei'] == 3
    assert result['measurements'][0]['mean_nuclear_intensity'] == pytest.approx(30000/65535, abs=0.03)
    assert (tmp_path / 'output' / 'control_nuclei.png').is_file()
