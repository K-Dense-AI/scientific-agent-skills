"""Exercise documented workflows and non-ASCII output round trips."""

import builtins
import csv
import re
import shlex
import sys
from pathlib import Path

import pytest

pytest.importorskip('rdkit')
from rdkit import Chem

SKILL_ROOT = Path(__file__).resolve().parents[2] / 'skills' / 'rdkit'
sys.path.insert(0, str(SKILL_ROOT / 'scripts'))
import molecular_properties
import similarity_search
import substructure_filter
from _common import read_molecule_records


def workflow_example(heading):
    text = (SKILL_ROOT / 'references/workflows_and_best_practices.md').read_text(encoding='utf-8')
    section = text.split(heading, 1)[1]
    return re.search(r'```python\n(.*?)```', section, re.S).group(1)


def test_documented_druglikeness_rejects_empty_and_invalid_input():
    namespace = {}
    exec(workflow_example('### Drug-likeness Analysis'), namespace)
    analyze = namespace['analyze_druglikeness']
    assert analyze('') is None
    assert analyze('not-a-smiles') is None
    assert analyze('CCO')['Lipinski'] is True
    assert analyze('CCO')['MW'] == pytest.approx(46.069, abs=0.001)


def test_documented_cache_preserves_properties_and_stereochemistry(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    original = Chem.MolFromSmiles('C[C@H](O)C(=O)[O-].[Na+]')
    original.SetProp('_Name', 'sample-name')
    original.SetProp('source_id', 'source-42')
    original.GetAtomWithIdx(0).SetProp('source_atom', 'atom-0')
    original.GetBondWithIdx(0).SetProp('source_bond', 'bond-0')
    namespace = {'mols': [original]}
    exec(workflow_example('**Use safe storage formats:**'), namespace)
    restored, = namespace['mols']
    assert restored.GetProp('_Name') == 'sample-name'
    assert restored.GetProp('source_id') == 'source-42'
    assert restored.GetAtomWithIdx(0).GetProp('source_atom') == 'atom-0'
    assert restored.GetBondWithIdx(0).GetProp('source_bond') == 'bond-0'
    assert Chem.MolToSmiles(restored) == Chem.MolToSmiles(original)


def test_all_text_writers_round_trip_unicode_under_legacy_default(tmp_path, monkeypatch):
    real_open = builtins.open

    def legacy_open(file, mode='r', *args, **kwargs):
        # Model a non-UTF-8 host even when CI itself uses UTF-8.
        if 'b' not in mode and not args and kwargs.get('encoding') is None:
            kwargs['encoding'] = 'cp1252'
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, 'open', legacy_open)
    name = '\u4e59\u9187 \U0001f9ea'
    molecule = Chem.MolFromSmiles('CCO')
    molecule.SetProp('_Name', name)
    output = tmp_path / 'molecules.smi'
    substructure_filter.write_molecules([molecule], output)
    records = list(read_molecule_records(output))
    assert records[0][1].GetProp('_Name') == name
    assert Chem.MolToSmiles(records[0][1]) == 'CCO'

    properties = molecular_properties.calculate_properties(molecule)
    properties['Name'] = name
    molecular_properties.write_csv([properties], tmp_path / 'properties.csv')
    similarity_search.write_results([
        {'index': 1, 'name': name, 'smiles': 'CCO', 'similarity': 1.0}
    ], tmp_path / 'hits.csv')
    substructure_filter.write_report([
        {'index': 1, 'smiles': 'CCO', 'status': 'included', 'matches': [name]}
    ], tmp_path / 'report.csv')
    for filename, column in [('properties.csv', 'Name'), ('hits.csv', 'Name'),
                             ('report.csv', 'Matches')]:
        with (tmp_path / filename).open(encoding='utf-8', newline='') as stream:
            assert next(csv.DictReader(stream))[column] == name


def test_documented_aromatic_amine_cli_excludes_near_negatives(tmp_path, monkeypatch):
    # Execute the actual advertised command, replacing only its file paths.
    monkeypatch.setattr(sys, 'argv', ['substructure_filter.py', '--help'])
    from contextlib import redirect_stdout
    from io import StringIO
    output = StringIO()
    with redirect_stdout(output), pytest.raises(SystemExit) as result:
        substructure_filter.main()
    assert result.value.code == 0
    command = next(line.strip() for line in output.getvalue().splitlines()
                   if line.strip().startswith('python ') and 'aromatic_amines.smi' in line)
    source, destination = tmp_path / 'input.smi', tmp_path / 'output.smi'
    source.write_text(
        'Nc1ccccc1 aniline\nCN(C)c1ccccc1 tertiary\n'
        'N#Cc1ccccc1 nitrile\nCC(=O)Nc1ccccc1 amide\n'
        'c1ccccc1.CN disconnected\nC[NH2+]c1ccccc1 ammonium\n'
        'CS(=O)(=O)Nc1ccccc1 sulfonamide\n', encoding='utf-8')
    args = shlex.split(command)[1:]
    args[1] = str(source)
    args[args.index('-o') + 1] = str(destination)
    monkeypatch.setattr(sys, 'argv', args)
    substructure_filter.main()
    retained = [m.GetProp('_Name') for _, m in read_molecule_records(destination)]
    assert retained == ['aniline', 'tertiary']
