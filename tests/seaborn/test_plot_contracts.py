"""Execute corrected recipes and assert scientific plotting contracts on tiny data."""
from pathlib import Path
import re

import pytest

np = pytest.importorskip('numpy')
pd = pytest.importorskip('pandas')
matplotlib = pytest.importorskip('matplotlib')
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
sns = pytest.importorskip('seaborn')
import seaborn.objects as so

SKILL_ROOT = Path(__file__).resolve().parents[2] / 'skills' / 'seaborn'


@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close('all')


def blocks(name):
    return re.findall(r'```python\n(.*?)```', (SKILL_ROOT / 'references' / name).read_text(), re.S)


def recipe(heading):
    text = (SKILL_ROOT / 'references/examples.md').read_text()
    section = text.split('### ' + heading + '\n', 1)[1].split('\n### ', 1)[0]
    return re.search(r'```python\n(.*?)```', section, re.S).group(1)


def namespace(**variables):
    return dict(np=np, pd=pd, plt=plt, sns=sns, **variables)


def run(code, ns):
    exec(compile(code, '<seaborn documented recipe>', 'exec'), ns)
    return ns


def data():
    rng = np.random.default_rng(12)
    n = 32
    x = np.tile(np.arange(1, 9), 4).astype(float)
    return pd.DataFrame({'x': x, 'y': 2 * x + rng.normal(size=n),
                         'category': np.repeat(['A', 'B'], 16),
                         'group': np.tile(np.repeat(['control', 'treated'], 8), 2),
                         'value': rng.normal(size=n)})


def test_objects_documented_recipes_render(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ns = {}
    for code in blocks('objects_interface.md'):
        run(code, ns)
    files = list(tmp_path.glob('objects-*'))
    assert len(files) == 11
    assert all(p.stat().st_size > 1000 for p in files)
    # .on(...).plot() actually adds artists, and constant alpha remains .4.
    assert len(ns['ax'].collections) == 1
    assert len(ns['ax'].lines) == 2
    assert np.allclose(ns['ax'].collections[0].get_facecolors()[:, 3], .4)


def test_gap_recipe_leaves_disconnected_observed_runs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ns = run(blocks('patterns_and_troubleshooting.md')[-1], {})
    actual = [line.get_xdata().tolist() for line in ns['ax'].lines]
    assert actual == [[0., 1.], [3., 4.]]
    assert (tmp_path / 'missing-gap.png').stat().st_size > 1000


def test_mean_and_weighted_mean_geometry():
    df = pd.DataFrame({'x': [0, 0, 1, 1], 'y': [1., 5., 2., 6.], 'weight': [1., 3., 3., 1.]})
    fig, axes = plt.subplots(1, 2)
    sns.lineplot(df, x='x', y='y', errorbar=None, ax=axes[0])
    sns.lineplot(df, x='x', y='y', weights='weight', errorbar=None, ax=axes[1])
    np.testing.assert_allclose(axes[0].lines[0].get_ydata(), [3, 4])
    np.testing.assert_allclose(axes[1].lines[0].get_ydata(), [4, 3])
    with pytest.raises(ValueError, match='mean'):
        sns.barplot(df, x='x', y='y', weights='weight', estimator='median')
    with pytest.raises(ValueError, match='ci'):
        sns.pointplot(df, x='x', y='y', weights='weight', errorbar='sd')


def test_objects_intervals_require_separate_marks():
    df = pd.DataFrame({'x': [0, 0, 1, 1], 'y': [1., 3., 4., 8.]})
    fig, axes = plt.subplots(1, 2)
    est = so.Est(errorbar='sd')
    so.Plot(df, x='x', y='y').add(so.Line(), est).on(axes[0]).plot()
    so.Plot(df, x='x', y='y').add(so.Line(), est).add(so.Band(), est).on(axes[1]).plot()
    np.testing.assert_allclose(axes[0].lines[0].get_ydata(), [2, 6])
    assert len(axes[0].patches) == 0
    assert len(axes[1].patches) == 1
    vertices = axes[1].patches[0].get_path().vertices
    assert vertices[:, 1].min() == pytest.approx(2 - np.sqrt(2))
    assert vertices[:, 1].max() == pytest.approx(6 + np.sqrt(8))


def test_percentile_range_is_iqr_only_with_explicit_percentiles():
    df = pd.DataFrame({'x': ['A'] * 5, 'y': np.arange(5.)})
    fig, ax = plt.subplots()
    so.Plot(df, x='x', y='y').add(so.Range(), so.Perc([25, 75])).on(ax).plot()
    segment = ax.collections[0].get_segments()[0]
    np.testing.assert_allclose(segment[:, 1], [1., 3.])


@pytest.mark.parametrize('name', ['stripplot', 'swarmplot', 'boxplot', 'violinplot', 'boxenplot', 'barplot', 'pointplot'])
def test_categorical_current_options(name):
    fig, ax = plt.subplots()
    kws = dict(data=data(), x='category', y='value', hue='group', ax=ax)
    if name == 'violinplot':
        kws.update(density_norm='area', common_norm=False, cut=0, split=True)
    if name == 'boxenplot':
        kws.update(width_method='area')
    if name in ('barplot', 'pointplot'):
        kws.update(errorbar=('ci', 95), n_boot=20, seed=7, err_kws={'linewidth': 1})
    if name == 'pointplot':
        kws.update(markersize=5, linestyles='none')
    assert getattr(sns, name)(**kws) is ax
    fig.canvas.draw()
    assert ax.has_data()


def test_countplot_normalizes_whole_plot():
    ax = sns.countplot(data=data(), x='category', hue='group', stat='percent')
    assert sum(p.get_height() for p in ax.patches) == pytest.approx(100.)


def test_histogram_density_common_norm():
    df = pd.DataFrame({'value': [0., 0., 1., 1., 0., 1.], 'group': ['A'] * 4 + ['B'] * 2})
    for common_norm, areas in [(False, [1., 1.]), (True, [1/3, 2/3])]:
        fig, ax = plt.subplots()
        sns.histplot(df, x='value', hue='group', bins=[-.5, .5, 1.5],
                     stat='density', common_norm=common_norm, ax=ax)
        actual = [sum(p.get_height() * p.get_width() for p in container) for container in ax.containers]
        np.testing.assert_allclose(sorted(actual), sorted(areas))


def test_grid_mapping_and_numeric_native_scale():
    df = data()
    grid = sns.FacetGrid(df, col='category', hue='group', hue_order=['control', 'treated'])
    grid.map_dataframe(sns.scatterplot, x='x', y='y').add_legend()
    assert grid.axes.shape == (1, 2)
    assert all(len(ax.collections) == 2 for ax in grid.axes.flat)
    fig, ax = plt.subplots()
    dose = pd.DataFrame({'dose': [1., 10., 100.], 'response': [2., 4., 8.]})
    sns.pointplot(dose, x='dose', y='response', native_scale=True, errorbar=None, ax=ax)
    np.testing.assert_allclose(ax.lines[0].get_xdata(), [1, 10, 100])


def test_regression_modes_and_residual_predictor():
    pytest.importorskip('statsmodels')
    df = data()
    fig, axes = plt.subplots(1, 3)
    sns.regplot(df, x='x', y='y', order=2, ci=None, ax=axes[0])
    sns.regplot(df, x='x', y='y', robust=True, ci=None, ax=axes[1])
    sns.residplot(df, x='x', y='y', lowess=True, ax=axes[2])
    np.testing.assert_allclose(axes[2].collections[0].get_offsets()[:, 0], df['x'])
    with pytest.raises(ValueError, match='Mutually exclusive'):
        sns.regplot(df, x='x', y='y', order=2, robust=True)


def test_jointplot_hue_kde_marginal_recipe():
    df = data().rename(columns={'x': 'var1', 'y': 'var2'})
    ns = run(recipe('Joint Plot with Multiple Representations'), namespace(df=df))
    assert ns['g'].ax_marg_x.has_data()
    assert ns['g'].ax_marg_y.has_data()


def test_clustermap_annotations_align_by_feature_label(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    df = pd.DataFrame({'sample_id': ['s2', 's1', 's3', 's4'],
                       'condition': ['control', 'treatment'] * 2,
                       'gene1': [1., 4., 2., 7.], 'other': [3., 2., 5., 8.],
                       'gene2': [5., 9., 8., 4.]})
    ns = run(recipe('Hierarchical Clustering Heatmap'), namespace(df=df, feature_columns=['gene1', 'other', 'gene2']))
    expected = [to_rgb('#2ca02c'), to_rgb('#d62728'), to_rgb('#2ca02c')]
    np.testing.assert_allclose(ns['g'].col_colors, expected)
    assert np.isfinite(ns['g'].data2d.to_numpy()).all()
    assert (tmp_path / 'clustermap.png').stat().st_size > 1000


def test_significance_annotations_are_computed():
    pytest.importorskip('statsmodels')
    df = pd.DataFrame({'treatment': np.repeat(['Control', 'Low', 'Medium', 'High'], 6),
                       'response': np.tile([1., 2., 3., 2., 3., 4.], 4) + np.repeat([0., .1, .5, 3.], 6)})
    ns = run(recipe('Box Plot with Significance Annotations'), namespace(df=df))
    assert np.all(ns['adjusted_p'] >= ns['raw_p'])
    assert len(ns['ax'].texts) == 2
    assert all(t.get_text().startswith('Holm p=') for t in ns['ax'].texts)


def test_dose_curve_uses_measured_coordinates_and_recovers_synthetic_ec50():
    x = np.repeat(np.geomspace(.01, 100, 12), 3)
    response = 2 + 8 / (1 + (1.5/x)**1.2)
    ns = run(recipe('Dose-Response Curve'), namespace(dose_df=pd.DataFrame({'dose': x, 'response': response})))
    assert ns['ax'].get_xscale() == 'log'
    curve_x = ns['ax'].lines[-1].get_xdata()
    assert curve_x[0] == pytest.approx(.01)
    assert curve_x[-1] == pytest.approx(100)
    assert ns['params'][2] == pytest.approx(1.5, rel=1e-4)


def test_balanced_display_sample_retains_labels_and_is_reproducible():
    code = recipe('Downsampling Strategy')
    df = pd.DataFrame({'category': np.repeat(['A', 'B', 'C'], [10, 20, 30]),
                       'x': np.arange(60), 'y': np.arange(60) ** .5})
    ns = run(code, namespace(large_df=df))
    sample = ns['smart_sample'](df, target_size=12, category_col='category', seed=7)
    assert sample.groupby('category').size().to_dict() == {'A': 4, 'B': 4, 'C': 4}
    pd.testing.assert_frame_equal(sample, ns['smart_sample'](df, 12, 'category', seed=7))
    with pytest.raises(ValueError, match='at least one'):
        ns['smart_sample'](df, 2, 'category')


def test_nested_categorical_recipe_handles_redundant_hue():
    df = data().rename(columns={'group': 'subcategory'})
    df['subcategory'] = df['category']
    ns = run(recipe('Nested Categorical Variables'), namespace(df=df))
    assert ns['axes'][1].get_legend() is None
    assert ns['axes'][1].has_data()


def test_paired_recipe_preserves_subject_identity_and_ignores_other_columns():
    df = pd.DataFrame({'subject': ['s1', 's2', 's3'], 'before': [1., 2., 3.],
                       'after': [2., 4., 5.], 'measurement': [100., 200., 300.]})
    ns = run(recipe('Before/After Comparison'), namespace(df=df))
    assert ns['df_paired'].groupby('subject').size().to_dict() == {'s1': 2, 's2': 2, 's3': 2}
    np.testing.assert_allclose(ns['df_paired']['measurement'], [1., 2., 3., 2., 4., 5.])


def test_widget_callbacks_handle_empty_filter_without_frontend(capsys):
    pytest.importorskip('ipywidgets')
    df = data()
    ns = run(recipe('Adjustable Parameters'), namespace(df=df))
    ns['plot_kde'](.8)
    ns = run(recipe('Dynamic Filtering'), namespace(df=df))
    before = len(plt.get_fignums())
    ns['filtered_plot'](())
    assert len(plt.get_fignums()) == before
    ns['filtered_plot'](('A',))
    assert len(plt.get_fignums()) > before
