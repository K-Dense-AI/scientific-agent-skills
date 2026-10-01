"""Small known-chemistry regressions for errors that otherwise look successful."""
from pathlib import Path
import csv
import math
import os
import re
import subprocess
import sys

import pytest

pytest.importorskip('rdkit')
from rdkit import Chem, DataStructs, rdBase
from rdkit.Chem import AllChem, Descriptors, Draw, rdFingerprintGenerator, rdMolDescriptors
from rdkit.Chem.MolStandardize import rdMolStandardize as standardize

SKILL_ROOT = Path(__file__).resolve().parents[2] / 'skills' / 'rdkit'
sys.path.insert(0, str(SKILL_ROOT / 'scripts'))
import molecular_properties
import similarity_search
import substructure_filter
from _common import read_molecule_records, SOURCE_INDEX


def mol(smiles):
    result = Chem.MolFromSmiles(smiles)
    assert result is not None
    return result


def canonical(smiles):
    return Chem.MolToSmiles(mol(smiles), canonical=True, isomericSmiles=True)


@pytest.mark.parametrize('left,right,equal', [
    ('CCO', 'OCC', True),
    ('c1ccccc1', 'C1=CC=CC=C1', True),
    ('C[C@H](O)F', 'C[C@@H](O)F', False),
    ('CC(O)F', 'C[C@H](O)F', False),
    ('CC(=O)O', 'CC(=O)[O-]', False),
    ('CC=O', 'C=CO', False),
    ('CCO', '[13CH3]CO', False),
])
def test_canonicalization_preserves_chemical_distinctions(left, right, equal):
    assert (canonical(left) == canonical(right)) is equal


def test_standardization_is_an_explicit_sequence_not_ph_prediction():
    original = mol('CC(=O)[O-].[Na+]')
    clean = standardize.Cleanup(original)
    assert len(Chem.GetMolFrags(clean)) == 2
    parent = standardize.FragmentParent(clean)
    assert Chem.MolToSmiles(parent) == 'CC(=O)[O-]'
    assert Chem.MolToSmiles(standardize.Uncharger().uncharge(parent)) == 'CC(=O)O'
    assert Chem.MolToSmiles(original) == 'CC(=O)[O-].[Na+]'
    permanent = standardize.Uncharger().uncharge(mol('C[N+](C)(C)C'))
    assert Chem.GetFormalCharge(permanent) == 1


def test_tautomers_are_distinct_before_canonical_tautomer_policy():
    enum = standardize.TautomerEnumerator()
    keto, enol = mol('CC=O'), mol('C=CO')
    assert Chem.MolToSmiles(keto) != Chem.MolToSmiles(enol)
    result = enum.Enumerate(enol)
    assert result.status == standardize.TautomerEnumeratorStatus.Completed
    assert {Chem.MolToSmiles(m) for m in result} == {'CC=O', 'C=CO'}
    assert Chem.MolToSmiles(enum.Canonicalize(keto)) == Chem.MolToSmiles(enum.Canonicalize(enol))


def test_valence_failure_is_not_repaired_by_disabling_sanitization():
    assert Chem.MolFromSmiles('CO(C)C') is None
    invalid = Chem.MolFromSmiles('CO(C)C', sanitize=False)
    assert Chem.DetectChemistryProblems(invalid)
    assert Chem.SanitizeMol(invalid, catchErrors=True) != Chem.SanitizeFlags.SANITIZE_NONE


@pytest.mark.parametrize('method', ['morgan', 'torsion'])
def test_chirality_is_an_explicit_fingerprint_choice(method):
    a, b = mol('CC[C@H](F)CO'), mol('CC[C@@H](F)CO')
    plain = [similarity_search.generate_fingerprint(m, method) for m in (a, b)]
    chiral = [similarity_search.generate_fingerprint(m, method, include_chirality=True) for m in (a, b)]
    assert DataStructs.TanimotoSimilarity(*plain) == 1
    assert DataStructs.TanimotoSimilarity(*chiral) < 1


@pytest.mark.parametrize('method', ['rdkit', 'maccs'])
def test_chirality_request_cannot_silently_do_nothing(method):
    with pytest.raises(ValueError, match='include_chirality'):
        similarity_search.generate_fingerprint(mol('CCO'), method, include_chirality=True)


def test_maccs_dimension_is_fixed_and_count_fingerprints_are_distinct():
    assert len(similarity_search.generate_fingerprint(mol('CCO'), 'maccs', n_bits=512)) == 167
    gen = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)
    counts = gen.GetCountFingerprint(mol('CCCCCC'))
    assert max(counts.GetNonzeroElements().values()) > 1
    assert gen.GetFingerprint(mol('CCCCCC')).GetNumBits() == 2048


@pytest.mark.parametrize('threshold', [float('nan'), float('inf'), -0.1, 1.1])
def test_invalid_threshold_cannot_produce_plausible_empty_results(threshold):
    with pytest.raises(ValueError, match='threshold'):
        similarity_search.similarity_search(mol('CCO'), [], threshold=threshold)


def test_stereo_query_respects_chirality_flag_and_unspecified_target():
    query = substructure_filter.create_pattern_query('C[C@H](O)F')
    molecules = [mol(s) for s in ('C[C@H](O)F', 'C[C@@H](O)F', 'CC(O)F')]
    assert len(substructure_filter.filter_molecules(molecules, [('q', query)])[0]) == 3
    kept, _ = substructure_filter.filter_molecules(molecules, [('q', query)], use_chirality=True)
    assert len(kept) == 1
    assert Chem.MolToSmiles(kept[0]) == 'C[C@H](O)F'


@pytest.mark.parametrize('name,positive,negative', [
    ('alcohol', 'CCO', 'CC(=O)O'),
    ('ketone', 'CC(=O)C', 'CC(=O)O'),
    ('ketone', 'CC(=O)c1ccccc1', 'CC=O'),
    ('amine', 'CCN', 'CC(=O)N'),
    ('amine', 'CN(C)C', 'CS(=O)(=O)N'),
    ('ether', 'COC', 'CC(=O)OC'),
])
def test_functional_groups_against_near_negatives(name, positive, negative):
    query = Chem.MolFromSmarts(substructure_filter.PATTERN_LIBRARIES['functional-groups'][name])
    assert mol(positive).HasSubstructMatch(query)
    assert not mol(negative).HasSubstructMatch(query)


def test_documented_functional_group_examples_are_real_matches():
    # The published table supplies both chemical classes; this tests behavior,
    # not wording or the formatting of a generated snapshot.
    text = (SKILL_ROOT / 'references/smarts_patterns.md').read_text()
    rows = re.findall(r'^\| [^|]+ \| `([^`]+)` \| `([^`]+)` \| `([^`]+)` \|$', text, re.M)
    assert rows
    for pattern, positive, negative in rows:
        query = Chem.MolFromSmarts(pattern)
        assert query is not None, pattern
        assert mol(positive).HasSubstructMatch(query), (pattern, positive)
        assert not mol(negative).HasSubstructMatch(query), (pattern, negative)


def test_rhodanine_not_the_wrong_connectivity_is_reported():
    query = Chem.MolFromSmarts(substructure_filter.PATTERN_LIBRARIES['pains']['rhodanine'])
    assert mol('O=C1CSC(=S)N1').HasSubstructMatch(query)
    assert not mol('S1C(=O)NC(=S)C1').HasSubstructMatch(query)


def test_source_ids_survive_invalid_rows_tabs_names_and_comment_lines(tmp_path):
    source = tmp_path / 'mols.smi'
    source.write_text('# comment\nCCO\tethanol name\ninvalid bad\n\nc1ccccc1 benzene\n')
    rows = similarity_search.load_molecules(source)
    assert [r['index'] for r in rows] == [2, 5]
    assert rows[0]['name'] == 'ethanol name'
    molecules = substructure_filter.load_molecules(source)
    _, report = substructure_filter.filter_molecules(molecules)
    assert [r['index'] for r in report] == [2, 5]
    properties = molecular_properties.process_file(source, tmp_path / 'props.csv')
    assert [p['Index'] for p in properties] == [2, 5]
    assert properties[0]['RDKit_Version'] == rdBase.rdkitVersion


def test_sdf_provenance_cannot_override_actual_source_record(tmp_path):
    source = tmp_path / 'mols.sdf'
    m = mol('CCO')
    m.SetIntProp(SOURCE_INDEX, 999)
    with Chem.SDWriter(str(source)) as writer:
        writer.SetProps([SOURCE_INDEX])
        writer.write(m)
    records = list(read_molecule_records(source))
    assert records[0][1].GetIntProp(SOURCE_INDEX) == 1


def test_mol_file_is_single_molecule_input(tmp_path):
    source = tmp_path / 'ethanol.mol'
    Chem.MolToMolFile(mol('CCO'), str(source))
    assert [(i, Chem.MolToSmiles(m)) for i, m in read_molecule_records(source)] == [(1, 'CCO')]


def test_empty_molecules_cannot_yield_successful_properties_or_similarity():
    empty = mol('')
    assert molecular_properties.calculate_properties(empty) is None
    assert similarity_search.generate_fingerprint(empty) is None
    assert substructure_filter.create_pattern_query('') is None


def cli(script, *args):
    return subprocess.run([sys.executable, str(SKILL_ROOT / 'scripts' / script), *map(str, args)],
                          capture_output=True, text=True, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})


def test_invalid_exclusion_aborts_before_any_output(tmp_path):
    source, output = tmp_path / 'input.smi', tmp_path / 'output.smi'
    source.write_text('CCO ethanol\n')
    result = cli('substructure_filter.py', source, '--pattern', 'C', '--exclude', '[broken', '-o', output)
    assert result.returncode != 0
    assert 'Invalid exclude' in result.stderr
    assert not output.exists()


def test_multiquery_file_is_rejected_instead_of_silently_using_first(tmp_path):
    source = tmp_path / 'input.smi'
    source.write_text('CCO ethanol\nCCCC butane\n')
    result = cli('similarity_search.py', source, source)
    assert result.returncode != 0
    assert 'exactly one' in result.stderr


def test_single_properties_output_and_empty_file_failure(tmp_path):
    output = tmp_path / 'props.csv'
    assert cli('molecular_properties.py', 'CCO', '-o', output).returncode == 0
    with output.open() as stream:
        assert next(csv.DictReader(stream))['Molecular_Formula'] == 'C2H6O'
    invalid = tmp_path / 'invalid.smi'
    invalid.write_text('not-a-smiles\n')
    assert cli('molecular_properties.py', '-f', invalid).returncode != 0


def test_documented_conformer_workflow_checks_actual_convergence_and_units():
    m = Chem.AddHs(mol('CCCO'))
    params = AllChem.ETKDGv3()
    params.randomSeed, params.numThreads, params.trackFailures = 42, 1, True
    ids = list(AllChem.EmbedMultipleConfs(m, numConfs=5, params=params))
    assert ids
    assert AllChem.MMFFHasAllMoleculeParams(m)
    results = AllChem.MMFFOptimizeMoleculeConfs(m, numThreads=1, maxIters=500)
    energies = {i: energy for i, (status, energy) in zip(ids, results) if status == 0}
    assert energies and all(math.isfinite(e) for e in energies.values())
    best = m.GetConformer(min(energies, key=energies.get))
    distance = (best.GetAtomPosition(0) - best.GetAtomPosition(1)).Length()
    assert 1.3 < distance < 1.7  # C-C bond in angstrom, not nm
    assert AllChem.MMFFOptimizeMolecule(m, maxIters=0) == 1
    unsupported = mol('[U]')
    assert not AllChem.MMFFHasAllMoleculeParams(unsupported)
    assert not AllChem.UFFHasAllMoleculeParams(unsupported)


def test_reaction_products_require_sanitization_and_transform_only_graph():
    reaction = AllChem.ReactionFromSmarts('[C:1]=[O:2]>>[C:1][O:2]')
    products = reaction.RunReactants((mol('CC(=O)C'),))
    assert len(products) == 1
    product = products[0][0]
    Chem.SanitizeMol(product)
    assert Chem.MolToSmiles(product) == 'CC(C)O'


def test_cubane_sssr_and_symmetrized_sssr_are_not_aliases():
    cubane = mol('C12C3C4C1C5C2C3C45')
    assert len(Chem.GetSSSR(cubane)) == 5
    assert len(Chem.GetSymmSSSR(cubane)) == 6


def test_corrected_descriptor_names_and_mqn_vector():
    m = mol('CCO')
    assert Descriptors.SlogP_VSA1(m) >= 0
    assert len(rdMolDescriptors.MQNs_(m)) == 42
    assert sum(atom.GetIsAromatic() for atom in mol('c1ccccc1').GetAtoms()) == 6
    assert Descriptors.ExactMolWt(mol('[13CH3]CO')) > Descriptors.ExactMolWt(m)
    phosphorus = mol('OP(=O)(O)O')
    assert rdMolDescriptors.CalcTPSA(phosphorus, includeSandP=True) > Descriptors.TPSA(phosphorus)


def test_depicting_a_copy_preserves_3d_conformers_and_nested_grid_signature():
    m = Chem.AddHs(mol('CCO'))
    assert AllChem.EmbedMolecule(m, randomSeed=42) >= 0
    before = m.GetConformer().GetPositions().copy()
    depicted = Chem.Mol(m)
    AllChem.Compute2DCoords(depicted)
    assert not depicted.GetConformer().Is3D()
    assert m.GetConformer().Is3D()
    assert (m.GetConformer().GetPositions() == before).all()
    svg = Draw.MolsMatrixToGridImage([[mol('CCO')], [mol('c1ccccc1'), None]], useSVG=True)
    assert '<svg' in svg


def test_pains_catalogue_is_separate_from_five_demo_motifs():
    from rdkit.Chem import FilterCatalog
    params = FilterCatalog.FilterCatalogParams()
    params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS)
    catalog = FilterCatalog.FilterCatalog(params)
    assert catalog.GetNumEntries() > 400
    assert len(catalog.GetMatches(mol('CCO'))) == 0


def test_chiral_atom_pair_bit_collisions_do_not_establish_identity():
    a, b = mol('C[C@H](F)Cl'), mol('C[C@@H](F)Cl')
    gen = rdFingerprintGenerator.GetAtomPairGenerator(fpSize=2048, includeChirality=True)
    assert gen.GetSparseCountFingerprint(a) != gen.GetSparseCountFingerprint(b)
    # The folded default has a real collision in the tested release.
    assert gen.GetFingerprint(a) == gen.GetFingerprint(b)
    large = rdFingerprintGenerator.GetAtomPairGenerator(fpSize=4096, includeChirality=True)
    assert large.GetFingerprint(a) != large.GetFingerprint(b)


def test_enhanced_stereo_groups_survive_text_reader_properties_and_writer(tmp_path):
    source = tmp_path / 'stereo.smi'
    source.write_text('F[C@H](Cl)[C@@H](F)Cl |&1:1,3| mixture A\n')
    molecules = substructure_filter.load_molecules(source)
    assert len(molecules[0].GetStereoGroups()) == 1
    assert molecules[0].GetProp('_Name') == 'mixture A'
    props = molecular_properties.calculate_properties(molecules[0])
    assert len(Chem.MolFromSmiles(props['SMILES']).GetStereoGroups()) == 1
    output = tmp_path / 'roundtrip.smi'
    substructure_filter.write_molecules(molecules, output)
    loaded = substructure_filter.load_molecules(output)[0]
    assert loaded.GetProp('_Name') == 'mixture A'
    assert len(loaded.GetStereoGroups()) == 1
    assert loaded.GetStereoGroups()[0].GetGroupType() == Chem.StereoGroupType.STEREO_AND


def test_tautomer_policy_can_remove_stereo_at_a_transforming_center():
    original = mol('C[C@H](F)C=O')
    assert Chem.FindMolChiralCenters(original) == [(1, 'S')]
    canonical_tautomer = standardize.TautomerEnumerator().Canonicalize(original)
    assert Chem.MolToSmiles(canonical_tautomer) == 'CC(F)C=O'
    assert Chem.FindMolChiralCenters(canonical_tautomer, includeUnassigned=True) == [(1, '?')]
