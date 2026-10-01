"""Execute the documented small-molecule workflows against the installed Datamol stack."""
from pathlib import Path
import re
import sys
import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / 'skills' / 'datamol'
dm = pytest.importorskip('datamol')
np = pytest.importorskip('numpy')
pd = pytest.importorskip('pandas')


def run_blocks(name, namespace=None, exclude=()):
    namespace = {} if namespace is None else namespace
    path = SKILL_ROOT / 'references' / name
    blocks = re.findall(r'```python\n(.*?)\n```', path.read_text(), re.S)
    for index, code in enumerate(blocks):
        if index not in exclude:
            exec(compile(code, f'{path.name}:block{index + 1}', 'exec'), namespace)
    return namespace


def test_core_api_returns_and_identity():
    scope = run_blocks('core_api.md')
    assert scope['cross'].shape == (1, 3)
    assert sorted(i for c in scope['cluster_indices'] for i in c) == [0, 1, 2]
    for index, molecule in zip(scope['picked_indices'], scope['picked_molecules']):
        assert dm.to_smiles(molecule) == dm.to_smiles(scope['mols'][index])
    mol = scope['mols'][0]
    assert dm.to_smiles(dm.to_mol(dm.to_binary(mol))) == dm.to_smiles(mol)
    assert dm.to_smiles(dm.from_dict(dm.to_dict([mol]))[0]) == dm.to_smiles(mol)
    assert dm.from_inchi(dm.to_inchi(mol)) is not None
    assert dm.from_smarts('[#6]') is not None
    assert isinstance(dm.from_selfies(dm.to_selfies(mol)), str)
    assert dm.to_smiles(dm.sanitize_mol(mol)) == dm.to_smiles(mol)
    assert dm.to_smiles(dm.remove_hs(dm.add_hs(mol))) == dm.to_smiles(mol)
    for scheme in ['all', 'no_stereo', 'no_tautomers']:
        assert dm.hash_mol(mol, hash_scheme=scheme)
    assert dm.to_graph(mol).number_of_nodes() == mol.GetNumAtoms()
    assert dm.get_all_path_between(mol, 0, 2)
    frame = dm.to_df(scope['mols'], mol_column='mol')
    assert len(dm.from_df(frame, mol_column='mol')) == 3


@pytest.mark.skipif(sys.platform == 'win32', reason='Datamol disables FreeSASA on Windows')
def test_core_workflows(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    scope = run_blocks('core_workflows.md')
    assert scope['fps'].shape == (6, 2048)
    assert np.isfinite(scope['sasa_values']).all()
    assert set(scope['train_indices']) | set(scope['test_indices']) == set(range(6))


@pytest.mark.skipif(sys.platform == 'win32', reason='Datamol disables FreeSASA on Windows')
def test_conformer_geometry_and_clusters():
    scope = run_blocks('conformers_module.md')
    mol = scope['mol_3d']
    if mol.GetNumConformers() > 1:
        rms = dm.conformers.rmsd(mol)
        assert rms.shape == (mol.GetNumConformers(),) * 2
        assert np.allclose(rms, rms.T) and np.allclose(np.diag(rms), 0)
        assert np.min(rms[np.triu_indices(len(rms), k=1)]) >= 0.5 - 1e-6
    assert mol.GetNumConformers() == sum(m.GetNumConformers() for m in scope['cluster_molecules'])
    assert np.allclose(dm.conformers.center_of_mass(scope['moved'], use_atoms=False, conf_id=0), 0, atol=1e-6)
    assert scope['sasa_values'].min() > 0
    for selected in scope['centroid_molecule'].GetConformers():
        source_id = selected.GetIntProp('source_conformer_id')
        original = mol.GetConformer(source_id)
        assert np.allclose(selected.GetPositions(), original.GetPositions())
        assert selected.GetDoubleProp('rdkit_UFF_energy') == original.GetDoubleProp('rdkit_UFF_energy')
    assert all(m.GetProp('source_id') == 'compound-001' for m in scope['cluster_molecules'])
    # Widget construction only; this does not exercise a notebook renderer.
    widget = dm.viz.conformers(mol, n_confs=None)
    assert widget is not None


def test_descriptor_meaning_and_real_image_encoding(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    scope = run_blocks('descriptors_viz.md')
    assert scope['descriptors']['mw'] == pytest.approx(46.069, abs=.01)
    defaults = dm.descriptors.compute_many_descriptors(scope['mols'][0])
    assert defaults['mw'] == pytest.approx(46.041865, abs=1e-5)
    assert {'clogp', 'n_lipinski_hbd', 'n_lipinski_hba', 'n_aromatic_heterocycles'} <= defaults.keys()
    assert not {'logp', 'hbd', 'hba'} & defaults.keys()
    assert (tmp_path / 'molecules.png').read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    assert '<svg' in (tmp_path / 'molecules.svg').read_text()
    assert dm.descriptors.n_rigid_bonds(dm.to_mol('C1CCCCC1')) == 6
    assert dm.descriptors.n_aromatic_atoms_proportion(dm.to_mol('c1ccccc1')) == 1
    assert dm.descriptors.n_charged_atoms(dm.to_mol('[NH4+]')) == 1


def test_fragment_identity_and_scaffold_semantics():
    scope = run_blocks('fragments_scaffolds.md')
    assert any('*' in s for s in scope['brics_smiles'])
    assert scope['scaffold_counts']['c1ccccc1'] == 2
    assert dm.to_smiles(dm.to_scaffold_murcko(dm.to_mol('CCCC'))) == ''
    assert scope['fragment_score'](dm.to_mol('CC'), set()) == 0
    assert all(isinstance(s, str) for s in scope['fragment_counts'])
    pairs = dm.fragment.mmpa_frag(dm.to_mol('CCOC'))
    assert pairs and all(isinstance(pair, tuple) and all(isinstance(x, str) for x in pair) for pair in pairs)
    fuzzy = dm.scaffold.fuzzy_scaffolding(scope['mols'], n_atom_cuttoff=3)
    assert len(fuzzy) == 3 and isinstance(fuzzy[0], set)
    assert isinstance(fuzzy[1], pd.DataFrame) and isinstance(fuzzy[2], pd.DataFrame)


def test_reaction_groups_and_toy_regression():
    scope = run_blocks('reactions_data.md')
    assert len(scope['predictions']) == len(scope['test']) > 0
    assert np.isfinite(scope['mae'])
    assert isinstance(scope['groups'][0], list)
    cases = [('amide_rxn', ['CN', 'CC(=O)O'], 'CNC(C)=O'),
             ('suzuki_rxn', ['Brc1ccccc1', 'OB(O)c1ccccc1'], 'c1ccc(-c2ccccc2)cc1'),
             ('esterification', ['CCO', 'CC(=O)Cl'], 'CCOC(C)=O')]
    for name, inputs, expected in cases:
        groups = dm.reactions.apply_reaction(scope[name], tuple(dm.to_mol(x) for x in inputs))
        actual = {dm.to_smiles(p) for group in groups for p in group if p is not None}
        assert dm.to_smiles(dm.to_mol(expected)) in actual
    flat = dm.reactions.apply_reaction(scope['rxn'], (dm.to_mol('CC(=O)O'),), product_index=0)
    assert isinstance(flat[0], dm.Mol)
    for dataset in [dm.data.freesolv, dm.data.cdk2, dm.data.solubility]:
        assert isinstance(dataset(as_df=False)[0], dm.Mol)
    assert dm.data.freesolv().shape == (642, 4)
    assert len(dm.data.cdk2()) == 47


def test_pipeline_rows_empty_inputs_and_similarity():
    scope = run_blocks('workflow_patterns.md')
    prepare, select = scope['prepare_library'], scope['select_diverse']
    bad = pd.DataFrame({'source_id': ['bad'], 'mol': [None]})
    accepted, rejected = prepare(bad)
    assert accepted.empty and len(rejected) == 1 and select(accepted).empty
    large = pd.DataFrame({'source_id': ['large'], 'mol': [dm.to_mol('C' * 60)]}, index=[19])
    accepted, _ = prepare(large)
    assert not accepted['passes_screen'].any() and select(accepted).empty
    rank = scope['similarity_ranking']
    mols = [dm.to_mol(x) for x in ['CCO', 'c1ccccc1', 'CCCO']]
    indices, values = rank([mols[0]], mols, limit=2)
    assert indices[0] == 0 and values[0] == pytest.approx(1)
    assert np.all(np.diff(values) <= 0)
    with pytest.raises(ValueError): rank([], mols)
    with pytest.raises(ValueError): select(accepted, limit=0)
    with pytest.raises(ValueError): scope['sar_table'](mols, [1])
    assert len(scope['sar_table'](mols, [1, 2, 3])) == 3


def test_local_io_and_invalid_record_retention(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'molecules.smi').write_text('CCO a\nnot_a_smiles bad\nCCC b\n')
    scope = run_blocks('io_module.md', exclude=(2,))  # remote paths are illustrative only
    assert scope['rejected']['id'].tolist() == ['bad']
    assert scope['accepted']['id'].tolist() == ['a', 'b']
    assert len(scope['restored']) == 2
    mols = [dm.to_mol('CCO'), dm.to_mol('CCC')]
    dm.to_sdf(mols, 'valid.sdf')
    assert isinstance(dm.read_sdf('valid.sdf'), list)
    frame = dm.open_df('valid.sdf', mol_column='mol')
    assert len(frame) == 2 and 'mol' in frame
    for name in ['roundtrip.sdf', 'roundtrip.csv.gz', 'roundtrip.json', 'roundtrip.xlsx']:
        source = frame if name.endswith('.sdf') else frame.drop(columns='mol')
        dm.save_df(source, name)
        assert len(dm.open_df(name)) == 2
    csv = dm.read_csv('roundtrip.csv.gz', smiles_column='smiles', mol_column='mol')
    xlsx = dm.read_excel('roundtrip.xlsx', smiles_column='smiles', mol_column='mol')
    assert all(m is not None for m in csv['mol']) and all(m is not None for m in xlsx['mol'])
    assert dm.read_molblock(dm.to_molblock(mols[0])) is not None
    molecule_3d = dm.conformers.generate(mols[0], n_confs=1)
    assert dm.read_pdbblock(dm.to_pdbblock(molecule_3d)) is not None


def test_source_ids_survive_sdf_failure_and_selection(tmp_path):
    first, last = dm.to_mol('CCO'), dm.to_mol('CCC')
    first.SetProp('source_id', 'first')
    last.SetProp('source_id', 'last')
    good = tmp_path / 'valid.sdf'
    dm.to_sdf([first, last], good)
    records = good.read_text().split('$$$$\n')
    damaged = tmp_path / 'damaged.sdf'
    damaged.write_text(records[0] + '$$$$\n' + 'invalid\nrecord\n\nnot counts\nM  END\n$$$$\n' + records[1] + '$$$$\n')
    raw = dm.read_sdf(damaged, as_df=True, mol_column='mol', discard_invalid=False)
    assert len(raw) == 3 and raw['mol'].isna().sum() == 1
    scope = run_blocks('workflow_patterns.md')
    accepted, rejected = scope['prepare_library'](raw)
    assert len(rejected) == 1
    selection = scope['select_diverse'](accepted, limit=2)
    by_id = dict(zip(selection['source_id'], selection['source_smiles']))
    assert by_id == {'first': 'CCO', 'last': 'CCC'}


def test_small_parallel_batch_and_format_readers(tmp_path):
    mols = dm.parallelized(dm.to_mol, ['CCO', 'CCC'], n_jobs=2)
    assert [dm.to_smiles(m) for m in mols] == ['CCO', 'CCC']
    result = dm.descriptors.batch_compute_many_descriptors(
        mols, properties_fn={'mw': 'MolWt'}, add_properties=False, n_jobs=2, batch_size=2,
    )
    assert result['mw'].tolist() == pytest.approx([46.069, 44.097], abs=.001)
    mol = mols[0]
    for operation in [dm.fix_mol, dm.fix_valence, dm.fix_valence_charge, dm.reorder_atoms]:
        assert dm.to_smiles(operation(dm.copy_mol(mol))) == 'CCO'
    assert dm.to_smarts(mol)
    assert dm.standardize_smiles('OCC') == 'CCO'
    mol2 = tmp_path / 'ethanol.mol2'
    mol2.write_text('''@<TRIPOS>MOLECULE
ethanol
3 2 0 0 0
SMALL
NO_CHARGES

@<TRIPOS>ATOM
1 C1 0.000 0.000 0.000 C.3 1 ETH 0.000
2 C2 1.500 0.000 0.000 C.3 1 ETH 0.000
3 O3 2.900 0.000 0.000 O.3 1 ETH 0.000
@<TRIPOS>BOND
1 1 2 1
2 2 3 1
''')
    parsed = dm.read_mol2file(mol2)
    assert isinstance(parsed, list) and len(parsed) == 1 and parsed[0].GetNumAtoms() == 3
    three_d = dm.conformers.generate(mol, n_confs=1)
    pdb = tmp_path / 'ethanol.pdb'
    pdb.write_text(dm.to_pdbblock(three_d))
    assert dm.read_pdbfile(pdb).GetNumAtoms() == mol.GetNumAtoms()
