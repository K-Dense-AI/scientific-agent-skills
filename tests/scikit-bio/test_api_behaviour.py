"""Native tiny fixtures for the scientific contracts used by the skill."""
from io import StringIO
from pathlib import Path
from functools import partial

import numpy as np
import pandas as pd
import pytest

skbio = pytest.importorskip('skbio')
from skbio import DNA, RNA, Protein, Table, TreeNode, DistanceMatrix, TabularMSA
from skbio.alignment import (pair_align, pair_align_nucl, pair_align_prot,
                             multi_align_nucl, align_score, align_dists,
                             PairAlignPath, AlignPath)
from skbio.diversity import alpha_diversity, beta_diversity, block_beta_diversity
from skbio.stats import subsample_counts
from skbio.stats.distance import permanova, permdisp, anosim, mantel, bioenv
from skbio.stats.ordination import pcoa, cca, rda, ca
from skbio.tree import nj, upgma, gme, bme, nni, rf_dists

SKILL_ROOT = Path(__file__).resolve().parents[2] / 'skills' / 'scikit-bio'
FIXTURES = Path(__file__).parent / 'fixtures'


def community():
    counts = np.array([[10, 5, 0, 3], [8, 6, 0, 4], [9, 4, 1, 4],
                       [0, 3, 10, 5], [1, 2, 8, 7], [0, 4, 9, 5]])
    return pd.DataFrame(counts, index=list('abcdef'), columns=list('ABCD'))


def test_sequence_operations_and_metadata():
    dna = DNA('ATGAAATAG', metadata={'id': 'coding'})
    assert str(dna.reverse_complement()) == 'CTATTTCAT'
    assert str(dna.transcribe()) == 'AUGAAAUAG'
    assert str(dna.transcribe().translate(genetic_code=11)) == 'MK*'
    assert list(dna.find_with_regex('(ATG.{3})')) == [slice(0, 6)]
    assert dna.kmer_frequencies(3)['ATG'] == 1
    assert DNA('ACN').has_degenerates()
    assert str(DNA('AC--GT').degap()) == 'ACGT'
    dna.interval_metadata.add([(0, 3)], metadata={'type': 'start'})
    assert dna.interval_metadata.num_interval_features == 1
    with pytest.raises(ValueError):
        dna.interval_metadata.add([(5, 15)])


def test_sequence_distance_requires_k():
    from skbio.sequence.distance import kmer_distance
    a, b = DNA('ATCGATCG'), DNA('ATCG--CG')
    assert a.distance(b) == .25
    value = a.distance(b, metric=partial(kmer_distance, k=3))
    assert 0 <= value <= 1


def test_fastq_quality_and_fasta_roundtrip(tmp_path):
    seqs = list(skbio.io.read(FIXTURES / 'reads.fastq', format='fastq',
                              constructor=DNA, phred_offset=33))
    assert len(seqs) == 2
    np.testing.assert_array_equal(seqs[0].positional_metadata['quality'], [40]*4)
    np.testing.assert_array_equal(seqs[1].positional_metadata['quality'], [0,10,20,30])
    dst = tmp_path / 'reads.fasta'
    skbio.io.write((seq for seq in seqs), format='fasta', into=dst)
    result = list(skbio.io.read(dst, format='fasta', constructor=DNA))
    assert [str(x) for x in result] == ['ACGT','AGGT']
    assert [x.metadata['id'] for x in result] == ['read1','read2']
    with pytest.raises(ValueError):
        list(skbio.io.read(FIXTURES / 'reads.fastq', format='fastq', constructor=DNA))


def test_alignment_terminal_and_affine_gap_conventions():
    assert pair_align('ACG', 'TACG').score == 3
    assert pair_align('ACG', 'TACG', free_ends=False).score == 1
    result = pair_align('ACG', 'TACG', free_ends=False, gap_cost=(5, 2))
    assert result.score == -4  # 3 matches - (5 + one-base gap * 2)
    assert align_score((result.paths[0], ('ACG','TACG')),
                        free_ends=False, gap_cost=(5,2)) == result.score
    assert result.paths[0].to_cigar() == '1I3M'
    assert PairAlignPath.from_cigar('1I3M').to_cigar() == '1I3M'
    assert AlignPath.from_aligned(['ACG','A-G','AC-']).shape == (3,3)


@pytest.mark.parametrize('wrapper,seqs,scoring', [
    (pair_align_nucl, (DNA('ATCGATCG'),DNA('ATCGGGGATCG')), ((2,-3),(5,2))),
    (pair_align_prot, (Protein('ACDEFGHIKLMNPQRSTVWY'),Protein('ACDEFMNPQRSTVWY')),
     ('BLOSUM62',(11,1))),
])
def test_alignment_wrapper_rescores(wrapper,seqs,scoring):
    result=wrapper(*seqs)
    msa=TabularMSA.from_path_seqs(result.paths[0], seqs)
    assert msa.shape.sequence == 2
    assert align_score((result.paths[0],seqs), sub_score=scoring[0], gap_cost=scoring[1]) == result.score


def test_msa_filter_entropy_and_distances():
    from scipy.stats import entropy
    msa=TabularMSA([DNA('ATCG--'),DNA('ATGG--'),DNA('ATCGAT')], index=list('abc'))
    assert str(msa.consensus()) == 'ATCG--'
    keep=msa.gap_frequencies(axis='sequence',relative=True) <= .5
    filtered=msa.iloc[:,keep]
    assert filtered.shape.position == 4
    values=[entropy(list(col.frequencies().values()),base=2) for col in msa.iter_positions()]
    assert values[0] == 0
    assert values[2] > 0
    assert np.isnan(msa.conservation()[-1])
    dm=align_dists(filtered, metric='hamming')
    assert dm.ids == tuple('abc')
    assert dm['a','b'] == .25


def test_progressive_msa_native():
    seqs=[DNA('ATCG'),DNA('ATGG'),DNA('ATCGA')]
    result=multi_align_nucl(seqs)
    msa=TabularMSA.from_path_seqs(result.path,seqs)
    assert [str(s.degap()) for s in msa] == [str(s) for s in seqs]


def test_diversity_has_analytic_reference_and_dispatch():
    df=pd.DataFrame([[2,2,0,0],[0,0,2,2]],index=['x','y'],columns=list('ABCD'))
    assert list(alpha_diversity('sobs',df)) == [2,2]
    np.testing.assert_allclose(alpha_diversity('shannon',df),np.log(2))
    np.testing.assert_allclose(alpha_diversity('hill',df,order=2),[2,2])
    assert beta_diversity('braycurtis',df)['x','y'] == 1
    assert beta_diversity('jaccard',df)['x','y'] == 1
    table=Table(df.to_numpy().T,observation_ids=df.columns,sample_ids=df.index)
    np.testing.assert_allclose(beta_diversity('braycurtis',table).data,
                               beta_diversity('braycurtis',df).data)
    # Shannon is scale invariant; floating abundances are accepted, not rounded.
    np.testing.assert_allclose(alpha_diversity('shannon',df/4),np.log(2))


def test_phylogenetic_diversity_identity_and_lengths():
    tree=TreeNode.read(FIXTURES/'tree.nwk')
    counts=np.array([[1,0,0,0],[0,0,1,0]])
    pd_value=alpha_diversity('faith_pd',counts,tree=tree,taxa=list('ABCD'))
    np.testing.assert_allclose(pd_value,[3,3])
    dm=beta_diversity('unweighted_unifrac',counts,tree=tree,taxa=list('ABCD'))
    assert dm[0,1] == 1
    weighted=beta_diversity('weighted_unifrac',counts,tree=tree,taxa=list('ABCD'))
    assert weighted[0,1] == 6  # unnormalized branch-length units, not [0,1]
    normalized=beta_diversity('weighted_unifrac',counts,tree=tree,taxa=list('ABCD'),normalized=True)
    assert normalized[0,1] == 1
    with pytest.raises(skbio.tree.MissingNodeError):
        alpha_diversity('faith_pd',counts,tree=tree,taxa=list('ABCE'))


def test_complete_block_distances_equal_driver():
    df=community()
    from scipy.spatial.distance import braycurtis
    block=block_beta_diversity(braycurtis,df.to_numpy(),ids=df.index,k=2)
    np.testing.assert_allclose(block.data,beta_diversity('braycurtis',df).data)


def test_rarefaction_depth_and_reproducibility():
    counts=community().to_numpy()
    depth=int(counts.sum(axis=1).min())
    rng=np.random.default_rng(42)
    results=np.array([subsample_counts(row,n=depth,seed=rng) for row in counts])
    assert np.all(results.sum(axis=1) == depth)
    assert np.all(results <= counts)
    np.testing.assert_array_equal(subsample_counts(counts[0],10,seed=42),
                                   subsample_counts(counts[0],10,seed=42))
    with pytest.raises(ValueError):
        subsample_counts(counts[0],n=1000)


@pytest.mark.parametrize('method',[nj,upgma,gme,bme])
def test_tree_construction(method):
    dm=DistanceMatrix([[0,2,6,6],[2,0,6,6],[6,6,0,2],[6,6,2,0]],ids=list('ABCD'))
    tree=method(dm)
    assert {n.name for n in tree.tips()} == set('ABCD')
    np.testing.assert_allclose(tree.cophenet().filter(dm.ids).data,dm.data)
    if method in (gme,bme):
        refined=nni(tree,dm)
        np.testing.assert_allclose(refined.cophenet().filter(dm.ids).data,dm.data)


def test_tree_manipulation_and_comparisons(tmp_path):
    tree=TreeNode.read(FIXTURES/'tree.nwk')
    assert tree.find('A').distance(tree.find('C')) == 6
    assert {n.name for n in tree.lca(['A','B']).tips()} == {'A','B'}
    subset=tree.shear(['A','B','C'])
    assert tree.count(tips=True) == 4
    assert subset.count(tips=True) == 3
    assert tree.compare_rfd(tree.copy()) == 0
    assert tree.compare_wrfd(tree.copy()) == 0
    assert abs(tree.compare_cophenet(tree.copy())) < 1e-12
    assert rf_dists([tree,tree.copy()])[0,1] == 0
    assert tree.root_at_midpoint().count(tips=True) == 4
    path=tmp_path/'tree.nwk'; tree.write(path,format='newick')
    assert TreeNode.read(path).compare_rfd(tree) == 0
    node=TreeNode(name='E',length=1); tree.append(node)
    assert tree.remove(node)
    assert 'A' in tree.ascii_art()
    assert len(list(tree.preorder())) == len(list(tree.traverse()))


def test_ordination_ids_and_euclidean_geometry(tmp_path):
    from scipy.spatial.distance import pdist,squareform
    data=np.array([[0,0],[1,0],[0,1],[1,1]],dtype=float)
    dm=DistanceMatrix(squareform(pdist(data)),ids=list('abcd'))
    result=pcoa(dm,dimensions=2)
    np.testing.assert_allclose(pdist(result.samples),pdist(data),atol=1e-12)
    assert result.samples.index.tolist() == list('abcd')
    assert result.proportion_explained.sum() == pytest.approx(1)
    path=tmp_path/'ordination.txt'; result.write(path)
    reread=skbio.OrdinationResults.read(path)
    np.testing.assert_allclose(result.samples,reread.samples)


@pytest.mark.parametrize('method',[cca,rda])
def test_constrained_ordination_preserves_feature_ids(method):
    df=community()
    env=pd.DataFrame({'pH':[6.5,6.7,6.8,7.0,7.2,7.3]},index=df.index)
    result=method(df.to_numpy(),env.to_numpy(),sample_ids=df.index.tolist(),
                   feature_ids=df.columns.tolist(),constraint_ids=['pH'])
    assert result.samples.index.tolist() == df.index.tolist()
    assert result.features.index.tolist() == df.columns.tolist()
    assert result.biplot_scores.index.tolist() == ['pH']
    assert np.isfinite(result.samples.to_numpy()).all()
    assert ca(df).samples.shape[0] == len(df)


@pytest.mark.parametrize('test',[permanova,anosim,permdisp])
def test_permutation_tests_align_metadata_by_id_and_reproduce(test):
    dm=beta_diversity('euclidean',community())
    md=pd.DataFrame({'group':['one']*3+['two']*3},index=dm.ids)
    kwargs={'dimensions':0} if test is permdisp else {}
    a=test(dm,md,column='group',permutations=19,seed=42,**kwargs)
    b=test(dm,md.iloc[::-1],column='group',permutations=19,seed=42,**kwargs)
    pd.testing.assert_series_equal(a,b)
    assert a['sample size'] == 6
    assert a['p-value'] >= .05
    assert np.isfinite(a['test statistic'])


def test_mantel_ids_and_bioenv():
    dm=beta_diversity('euclidean',community())
    r,p,n=mantel(dm,dm.filter(dm.ids[::-1]),permutations=19,seed=42)
    assert r == pytest.approx(1)
    assert n == 6
    assert p >= .05
    result=bioenv(dm,pd.DataFrame({'gradient':np.arange(6)},index=dm.ids))
    assert len(result) == 1


def test_biom_orientation_filtering_and_roundtrip(tmp_path):
    df=community()
    table=Table(df.to_numpy().T,observation_ids=df.columns,sample_ids=df.index)
    subset=table.filter(['a','d'],axis='sample',inplace=False)
    assert table.shape == (4,6)
    assert subset.shape == (4,2)
    norm=table.norm(axis='sample',inplace=False)
    np.testing.assert_allclose(norm.sum(axis='sample'),np.ones(6))
    path=tmp_path/'table.biom'; subset.write(path,format='biom')
    result=Table.read(path,format='biom')
    np.testing.assert_array_equal(result.matrix_data.toarray(),df.loc[['a','d']].to_numpy().T)
    assert list(result.ids(axis='sample')) == ['a','d']


def test_distance_matrix_constraints():
    dm=DistanceMatrix([[0,1,2],[1,0,3],[2,3,0]],ids=list('ABC'))
    assert dm['A','C'] == 2
    np.testing.assert_array_equal(dm.condensed_form(),[1,2,3])
    assert list(dm.to_data_frame().index) == list('ABC')
    with pytest.raises(skbio.stats.distance.DistanceMatrixError):
        DistanceMatrix([[0,1],[2,0]])
    pwm=skbio.PairwiseMatrix([[0,1],[2,0]])
    assert pwm[1,0] == 2


def test_embedding_residue_vs_sequence_and_ordination():
    from skbio.embedding import (ProteinEmbedding,ProteinVector,embed_vec_to_numpy,
        embed_vec_to_distances,embed_vec_to_dataframe,embed_vec_to_ordination)
    embedding=ProteinEmbedding(np.array([[1.,0.],[0.,1.],[1.,1.]]),'ACD')
    vectors=[ProteinVector(embedding.embedding.mean(axis=0),'ACD'),
             ProteinVector([0.,1.],'ACE'),ProteinVector([1.,0.],'ACF')]
    matrix=embed_vec_to_numpy(vectors)
    assert matrix.shape == (3,2)
    assert list(embed_vec_to_dataframe(vectors).index) == ['ACD','ACE','ACF']
    dm=embed_vec_to_distances(vectors,metric='euclidean')
    assert dm['ACE','ACF'] == pytest.approx(np.sqrt(2))
    assert pcoa(dm).samples.shape[0] == 3
    assert embed_vec_to_ordination(vectors).short_method_name == 'SVD'
    with pytest.raises(ValueError):
        ProteinEmbedding(np.ones((2,4)),'ACD')


def test_differential_abundance_counts_and_seed():
    from skbio.stats.composition import dirmult_ttest,ancom,dirmult_lme
    table=community()
    grouping=pd.Series(['control']*3+['caseA']*3,index=table.index)
    result=dirmult_ttest(table,grouping,treatment='caseA',reference='control',draws=8,seed=42)
    same=dirmult_ttest(table,grouping,treatment='caseA',reference='control',draws=8,seed=42)
    pd.testing.assert_frame_equal(result,same)
    assert result.index.tolist() == table.columns.tolist()
    assert (result['T-statistic'].loc['A'] < 0)  # lower in caseA
    # ANCOM needs strictly positive compositions; this explicit pseudocount is illustrative.
    ancom_result,percentiles=ancom(table+1,grouping)
    assert ancom_result.index.tolist() == table.columns.tolist()
    md=pd.DataFrame({'time':[0.,1.,2.,0.,1.,2.],
                     'subject':['one']*3+['two']*3},index=table.index)
    lme=dirmult_lme(table,md,formula='time',grouping='subject',draws=2,seed=42)
    assert len(lme) == 4


def test_signed_embedding_distance_requires_general_distance_path():
    from skbio.embedding import ProteinVector,embed_vec_to_distances,embed_vec_to_numpy
    from scipy.spatial.distance import pdist,squareform
    vectors=[ProteinVector([-1.,0.],'ACD'),ProteinVector([1.,0.],'ACE')]
    with pytest.raises(ValueError,match='negative'):
        embed_vec_to_distances(vectors)
    dm=DistanceMatrix(squareform(pdist(embed_vec_to_numpy(vectors))),ids=['p1','p2'])
    assert dm['p1','p2'] == 2


@pytest.mark.parametrize('method',['eigh','fsvd'])
def test_permdisp_small_matrix_dimension_boundary(method):
    dm=beta_diversity('euclidean',community())
    with pytest.raises(ValueError,match='cannot extend distance matrix size'):
        permdisp(dm,['a']*3+['b']*3,method=method,permutations=0,seed=42)
    result=permdisp(dm,['a']*3+['b']*3,method=method,dimensions=0,
                    permutations=0,seed=42)
    assert np.isfinite(result['test statistic'])


def test_partial_beta_matrix_has_uncomputed_zero_sentinels():
    from scipy.spatial.distance import braycurtis
    from skbio.diversity import partial_beta_diversity
    df=community()
    dm=partial_beta_diversity(braycurtis,df,ids=df.index,id_pairs=[('a','b')])
    assert dm['a','b'] > 0
    assert dm['a','d'] == 0
    assert beta_diversity('braycurtis',df)['a','d'] > 0


@pytest.mark.parametrize('name',['mixup','aitchison_mixup','compos_cutmix','phylomix'])
def test_augmentation_is_seeded_synthetic_data(name):
    func=getattr(skbio.table,name)
    df=community()+1  # strictly positive for Aitchison geometry
    labels=np.array([0]*3+[1]*3)
    kwargs={'tree':TreeNode.read(FIXTURES/'tree.nwk')} if name=='phylomix' else {}
    matrix,output_labels=func(df,n=2,labels=labels,seed=42,**kwargs)
    same,same_labels=func(df,n=2,labels=labels,seed=42,**kwargs)
    np.testing.assert_allclose(matrix,same)
    np.testing.assert_allclose(output_labels,same_labels)
    assert matrix.shape == (2,4)
    assert output_labels.shape == (2,2)
    assert np.isfinite(matrix).all()
    if name in ('aitchison_mixup','compos_cutmix'):
        np.testing.assert_allclose(matrix.sum(axis=1),1)


def test_plot_and_legacy_biom_json_roundtrip(tmp_path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from biom import load_table
    table=Table(community().to_numpy().T,observation_ids=list('ABCD'),sample_ids=list('abcdef'))
    path=tmp_path/'table.json'
    path.write_text(table.to_json('scikit-bio skill synthetic test'))
    restored=load_table(str(path))
    np.testing.assert_allclose(beta_diversity('euclidean',restored).data,
                               beta_diversity('euclidean',community()).data)
    result=pcoa(beta_diversity('euclidean',community()),dimensions=3)
    metadata=pd.DataFrame({'bodysite':['a']*3+['b']*3},index=list('abcdef'))
    fig=result.plot(metadata,column='bodysite')
    fig.savefig(tmp_path/'ordination.png')
    assert (tmp_path/'ordination.png').stat().st_size > 1000
    plt.close(fig)
