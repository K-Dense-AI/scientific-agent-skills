"""Batched/scalar equivalence, zero-vector policy, and exported provenance."""

import csv
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

pytest.importorskip('rdkit')
from rdkit import Chem, DataStructs, rdBase

SKILL_ROOT = Path(__file__).resolve().parents[2] / 'skills' / 'rdkit'
sys.path.insert(0, str(SKILL_ROOT / 'scripts'))
import similarity_search as search


def entries(smiles):
    return [{'index': 2 * i + 1, 'name': f'mol-{i}', 'smiles': smi,
             'mol': Chem.MolFromSmiles(smi)} for i, smi in enumerate(smiles)]


@pytest.mark.parametrize('method', search.FINGERPRINT_METHODS)
@pytest.mark.parametrize('metric', ['tanimoto', 'dice', 'cosine'])
def test_batches_and_threads_match_scalar_scores_and_stable_order(method, metric):
    database = entries(['CCCCO', 'c1ccccc1', 'CCCCO', 'CCCCN', 'CC(=O)Oc1ccccc1C(=O)O'])
    query = database[0]['mol']
    qfp = search.generate_fingerprint(query, method)
    scalar = getattr(DataStructs, metric.capitalize() + 'Similarity')
    expected = [(row['index'], scalar(qfp, search.generate_fingerprint(row['mol'], method)))
                for row in database]
    expected.sort(key=lambda pair: pair[1], reverse=True)
    for threshold in (0.0, 0.3, 1.0):
        for batch_size, threads in [(1, 1), (2, 2), (100, 2)]:
            actual = search.similarity_search(query, iter(database), method=method,
                                              metric=metric, threshold=threshold,
                                              batch_size=batch_size, num_threads=threads)
            selected = [(index, score) for index, score in expected if score >= threshold]
            assert [hit['index'] for hit in actual] == [index for index, _ in selected]
            assert [hit['similarity'] for hit in actual] == pytest.approx([score for _, score in selected])


@pytest.mark.parametrize('method', ['morgan', 'atompair', 'torsion'])
def test_batch_chirality_agrees_with_scalar(method):
    database = entries(['CC[C@H](F)CO', 'CC[C@@H](F)CO'])
    query = database[0]['mol']
    fps = [search.generate_fingerprint(row['mol'], method, include_chirality=True) for row in database]
    expected = {row['index']: DataStructs.TanimotoSimilarity(fps[0], fp)
                for row, fp in zip(database, fps)}
    hits = search.similarity_search(query, database, method=method, threshold=0,
                                    include_chirality=True, batch_size=1, num_threads=2)
    assert {hit['index']: hit['similarity'] for hit in hits} == pytest.approx(expected)


def test_search_reuses_one_generator_and_bounds_batches(monkeypatch):
    real_factory = search.create_generator
    created, sizes, threads = [], [], []

    class ObservedGenerator:
        def __init__(self, real):
            self.real = real

        def GetFingerprint(self, molecule):
            return self.real.GetFingerprint(molecule)

        def GetFingerprints(self, molecules, numThreads):
            sizes.append(len(molecules))
            threads.append(numThreads)
            return self.real.GetFingerprints(molecules, numThreads=numThreads)

    def factory(*args):
        created.append(args)
        return ObservedGenerator(real_factory(*args))

    monkeypatch.setattr(search, 'create_generator', factory)
    database = entries(['CCCCO'] * 5)
    assert len(search.similarity_search(database[0]['mol'], iter(database),
                                       batch_size=2, num_threads=2)) == 5
    assert len(created) == 1
    assert sizes == [2, 2, 1]
    assert threads == [2, 2, 2]


@pytest.mark.parametrize('method,smiles', [('torsion', 'CCO'), ('rdkit', 'C'), ('atompair', 'C')])
def test_zero_query_is_an_error_not_a_no_hit_search(method, smiles):
    query = Chem.MolFromSmiles(smiles)
    with pytest.raises(ValueError, match='all-zero'):
        search.similarity_search(query, [], method=method)


@pytest.mark.parametrize('metric', ['tanimoto', 'dice', 'cosine'])
def test_zero_database_entries_skipped_at_zero_threshold_with_provenance(metric, capsys):
    database = entries(['CCO', 'CCCCO', '', 'CCN', 'CCCCN'])
    database.insert(1, {'index': 99, 'mol': None})
    metadata = {}
    hits = search.similarity_search(Chem.MolFromSmiles('CCCCO'), database,
                                    method='torsion', metric=metric, threshold=0,
                                    batch_size=1, metadata=metadata)
    assert {hit['index'] for hit in hits} == {3, 9}
    assert metadata['zero_fingerprint_source_indices'] == [1, 7]
    assert metadata['counts'] == {'input_records': 6, 'invalid_molecules': 2,
                                  'zero_fingerprints': 2, 'scored_records': 2, 'hits': 2}
    assert 'Skipped 2 all-zero' in capsys.readouterr().err


def test_empty_and_all_zero_database_have_completed_metadata():
    for database in ([], entries(['CCO'])):
        metadata = {}
        assert search.similarity_search(Chem.MolFromSmiles('CCCCO'), database,
                                        method='torsion', metadata=metadata) == []
        assert metadata['counts']['scored_records'] == 0
        assert metadata['counts']['hits'] == 0


@pytest.mark.parametrize('options', [{'batch_size': 0}, {'batch_size': -1},
                                    {'batch_size': 1.5}, {'num_threads': 0}, {'num_threads': -1}])
def test_invalid_batch_options_are_rejected(options):
    with pytest.raises(ValueError, match='positive integers'):
        search.similarity_search(Chem.MolFromSmiles('CCCCO'), [], **options)


def cli(*args):
    return subprocess.run([sys.executable, '-B', str(SKILL_ROOT / 'scripts/similarity_search.py'),
                           *map(str, args)], capture_output=True, text=True, encoding='utf-8',
                          env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1'})


@pytest.mark.parametrize('method', ['morgan', 'maccs', 'torsion'])
def test_cli_sidecar_records_effective_configuration_and_replays_hits(tmp_path, method):
    source = tmp_path / 'database.smi'
    source.write_text('# source IDs\nCCCCO alcohol\ninvalid bad\nCCO small\nCCCCN amine\n', encoding='utf-8')
    output = tmp_path / 'hits.csv'
    result = cli('CCCCO', source, '--method', method, '--bits', '512', '--radius', '3',
                 '--metric', 'dice', '--threshold', '0', '--batch-size', '2',
                 '--num-threads', '2', '-o', output)
    assert result.returncode == 0, result.stderr
    metadata = json.loads(Path(str(output) + '.metadata.json').read_text(encoding='utf-8'))
    fp = metadata['fingerprint']
    assert metadata['schema_version'] == 1
    assert metadata['rdkit_version'] == rdBase.rdkitVersion
    assert fp['bits'] == (167 if method == 'maccs' else 512)
    assert fp['radius'] == (3 if method == 'morgan' else None)
    assert metadata['num_threads'] == (1 if method == 'maccs' else 2)
    assert metadata['requested'] == {'radius': 3, 'bits': 512, 'num_threads': 2}
    assert metadata['counts']['input_records'] == 3  # not physical lines or invalid input
    assert metadata['database_file'] == str(source)
    assert metadata['zero_fingerprint_policy'] == {'query': 'error', 'database': 'skip'}
    if method == 'maccs':
        assert fp['generator_info'] is None
    else:
        gen = search.create_generator(method, radius=3, n_bits=512)
        assert fp['generator_info'] == gen.GetInfoString()
    if method == 'torsion':
        assert metadata['zero_fingerprint_source_indices'] == [4]
    replay = search.similarity_search(Chem.MolFromSmiles(metadata['query_smiles']),
                                      search.load_molecules(source), method=fp['method'],
                                      radius=fp['radius'] if fp['radius'] is not None else 2,
                                      n_bits=fp['bits'], include_chirality=fp['include_chirality'],
                                      metric=metadata['metric'], threshold=metadata['threshold'])
    with output.open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert [int(row['Index']) for row in rows] == [hit['index'] for hit in replay]
    assert [row['Similarity'] for row in rows] == [f"{hit['similarity']:.4f}" for hit in replay]


def test_cli_no_hits_writes_metadata_but_invalid_query_does_not_overwrite(tmp_path):
    source = tmp_path / 'database.smi'
    source.write_text('c1ccccc1 benzene\n', encoding='utf-8')
    output = tmp_path / 'hits.csv'
    assert cli('CCCCO', source, '--threshold', '1', '-o', output).returncode == 0
    sidecar = Path(str(output) + '.metadata.json')
    assert json.loads(sidecar.read_text(encoding='utf-8'))['counts']['hits'] == 0
    before = output.read_bytes(), sidecar.read_bytes()
    result = cli('CCO', source, '--method', 'torsion', '-o', output)
    assert result.returncode != 0 and 'all-zero' in result.stderr
    assert (output.read_bytes(), sidecar.read_bytes()) == before


@pytest.mark.parametrize('flag', ['--num-threads', '--batch-size'])
def test_cli_invalid_batch_argument_fails_before_output(tmp_path, flag):
    output = tmp_path / 'hits.csv'
    result = cli('CCCCO', tmp_path / 'missing.smi', flag, '0', '-o', output)
    assert result.returncode != 0 and 'must be positive' in result.stderr
    assert not output.exists() and not Path(str(output) + '.metadata.json').exists()
