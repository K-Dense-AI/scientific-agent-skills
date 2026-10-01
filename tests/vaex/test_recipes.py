"""Execute the maintained synthetic recipes and check scientific data invariants."""
from pathlib import Path
import re

import pytest

vaex = pytest.importorskip('vaex')
np = pytest.importorskip('numpy')
pa = pytest.importorskip('pyarrow')

SKILL_ROOT = Path(__file__).resolve().parents[2] / 'skills' / 'vaex'

# Only explicitly illustrative external-data/service/frontend blocks are excluded.
RECIPES = [
    ('SKILL.md', ()),
    ('references/core_dataframes.md', (1,)),
    ('references/data_processing.md', ()),
    ('references/performance.md', ()),
    ('references/io_operations.md', (3, 4)),
    ('references/visualization.md', (2,)),
    ('references/machine_learning.md', ()),
]


@pytest.mark.parametrize('relative,illustrative', RECIPES)
def test_documented_synthetic_recipes(relative, illustrative, tmp_path, monkeypatch):
    """Every runnable block includes independent numerical/schema assertions."""
    monkeypatch.chdir(tmp_path)
    if 'machine_learning' in relative:
        pytest.importorskip('vaex.ml')
        pytest.importorskip('sklearn')
        pytest.importorskip('numba')
        pytest.importorskip('xgboost')
    if 'visualization' in relative:
        mpl = pytest.importorskip('matplotlib')
        mpl.use('Agg', force=True)
    if 'performance' in relative:
        pytest.importorskip('cachetools')
    text = (SKILL_ROOT / relative).read_text()
    blocks = re.findall(r'^```python\n(.*?)^```', text, flags=re.M | re.S)
    namespace = {'__name__': '__vaex_recipe__'}
    for index, source in enumerate(blocks):
        if index not in illustrative:
            exec(compile(source, f'{relative}:block-{index}', 'exec'), namespace)
    if 'visualization' in relative:
        from PIL import Image
        for name in ['vaex-histogram.png', 'vaex-scatter.png', 'vaex-grids.png']:
            with Image.open(tmp_path / name) as image:
                assert image.width > 300 and image.height > 200
                assert np.asarray(image).std() > 10


def test_grid_orientation_and_edge_population():
    x = np.array([0., 0.5, 1.5, 2., 2.5, 3., np.nan])
    y = np.array([0., 1.5, 0.5, 1.5, 2., 1., 1.])
    frame = vaex.from_arrays(x=x, y=y)
    observed = frame.count(binby=['x', 'y'], limits=[[0, 3], [0, 2]], shape=(3, 2))
    eligible = np.isfinite(x) & (x >= 0) & (x < 3) & (y >= 0) & (y < 2)
    expected, _, _ = np.histogram2d(x[eligible], y[eligible], bins=[np.arange(4), np.arange(3)])
    np.testing.assert_array_equal(observed, expected)
    assert observed.sum() == 4


def test_arrow_null_nan_and_population_variance():
    frame = vaex.from_arrays(value=pa.array([1., None, np.nan, 3.]))
    assert frame.value.count() == 2
    assert frame.value.isna().sum() == 2
    assert frame.value.ismissing().sum() == 1
    assert frame.value.isnan().sum() == 1
    assert frame.value.var() == 1


def test_filtered_duplicate_join_contract():
    left = vaex.from_arrays(key=np.array([1, 2, 3]), value=np.array([10, 20, 30]))
    right = vaex.from_arrays(key=np.array([1, 2, 2]), label=np.array(['a', 'b', 'c']))
    with pytest.raises(ValueError):
        left.join(right, on='key', how='left')
    fixed = left[left.key == 2].extract()
    result = fixed.join(right, on='key', how='inner', allow_duplication=True)
    assert sorted(result['label'].tolist()) == ['b', 'c']
    assert result.value.tolist() == [20, 20]


def test_hdf5_append_means_another_group(tmp_path):
    pytest.importorskip('vaex.hdf5')
    first = vaex.from_arrays(x=np.array([1, 2]))
    second = vaex.from_arrays(x=np.array([3, 4, 5]))
    path = str(tmp_path / 'groups.hdf5')
    first.export_hdf5(path)
    second.export_hdf5(path, mode='a', group='/other')
    assert vaex.open(path).x.tolist() == [1, 2]
    assert vaex.open(path, group='/other').x.tolist() == [3, 4, 5]


def test_trusted_model_state_does_not_import_training_filter(tmp_path):
    ml = pytest.importorskip('vaex.ml')
    pytest.importorskip('sklearn')
    from sklearn.linear_model import LinearRegression
    from vaex.ml.sklearn import Predictor
    frame = vaex.from_arrays(x=np.arange(10.), target=2 * np.arange(10.))
    train = frame[frame.x < 6]
    scaler = ml.StandardScaler(features=['x'], prefix='s_')
    scaled = scaler.fit_transform(train)
    predictor = Predictor(features=['s_x'], target='target', model=LinearRegression())
    predictor.fit(scaled)
    path = str(tmp_path / 'model.json')
    predictor.transform(scaled).state_write(path)
    target = frame[frame.x >= 6].copy()
    target.state_load(path, set_filter=False, trusted=True)
    assert target.x.tolist() == [6., 7., 8., 9.]
    np.testing.assert_allclose(target.prediction.to_numpy(), [12., 14., 16., 18.])


@pytest.mark.parametrize('module,class_name,params', [
    ('xgboost', 'XGBoostModel', {'objective': 'reg:squarederror', 'nthread': 2, 'max_depth': 2}),
    ('lightgbm', 'LightGBMModel', {'objective': 'regression', 'verbosity': -1, 'num_threads': 2, 'min_data_in_leaf': 2}),
    ('catboost', 'CatBoostModel', {'loss_function': 'RMSE', 'depth': 2, 'thread_count': 2, 'allow_writing_files': False}),
])
def test_released_boosting_wrappers(module, class_name, params):
    pytest.importorskip(module)
    adapter = pytest.importorskip('vaex.ml.' + module)
    x = np.linspace(-1, 1, 24)
    frame = vaex.from_arrays(x=x, target=2*x+1)
    options = {'prediction_type': 'RawFormulaVal'} if module == 'catboost' else {}
    model = getattr(adapter, class_name)(features=['x'], target='target', params=params,
                                        num_boost_round=3, prediction_name='result', **options)
    model.fit(frame)
    predictions = model.transform(frame).result.to_numpy()
    assert predictions.shape == (24,)
    assert np.isfinite(predictions).all()
    assert np.std(predictions) > 0


def test_target_encoder_unseen_policy_and_training_mapping():
    ml = pytest.importorskip('vaex.ml')
    train = vaex.from_arrays(category=np.array(['A', 'A', 'B', 'B']),
                             target=np.array([0, 1, 1, 1]))
    test = vaex.from_arrays(category=np.array(['A', 'new']))
    encoder = ml.BayesianTargetEncoder(features=['category'], target='target', weight=0, unseen='nan')
    encoder.fit(train)
    values = encoder.transform(test).mean_encoded_category.to_numpy()
    assert values[0] == 0.5
    assert np.isnan(values[1])
    woe = ml.WeightOfEvidenceEncoder(features=['category'], target='target')
    woe.fit(train)
    assert np.isfinite(woe.transform(train).woe_encoded_category.to_numpy()).all()


def test_predictor_probability_class_axis():
    pytest.importorskip('vaex.ml')
    pytest.importorskip('sklearn')
    from sklearn.linear_model import LogisticRegression
    from vaex.ml.sklearn import Predictor
    x = np.linspace(-2, 2, 20)
    frame = vaex.from_arrays(x=x, target=(x > 0).astype(int))
    estimator = LogisticRegression()
    predictor = Predictor(features=['x'], target='target', model=estimator,
                          prediction_type='predict_proba')
    predictor.fit(frame)
    probabilities = predictor.transform(frame).prediction.to_numpy()
    assert estimator.classes_.tolist() == [0, 1]
    assert probabilities.shape == (20, 2)
    np.testing.assert_allclose(probabilities.sum(axis=1), 1)
    assert probabilities[-1, 1] > probabilities[0, 1]


def test_vectorized_apply_and_dask_array_are_bounded_by_requested_rows():
    frame = vaex.from_arrays(x=np.arange(6.), y=np.arange(6.) ** 2)
    frame['result'] = frame.apply(lambda x, y: x + y, arguments=[frame.x, frame.y], vectorize=True)
    np.testing.assert_allclose(frame.result.to_numpy(), np.arange(6.) + np.arange(6.) ** 2)
    array = frame[['x', 'y']].to_dask_array()
    np.testing.assert_allclose(array[:3].compute(), [[0, 0], [1, 1], [2, 4]])
