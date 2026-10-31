"""Execute Dask documentation recipes against independent numerical references."""
from pathlib import Path
import re

import pytest

np = pytest.importorskip('numpy')
dask = pytest.importorskip('dask')
da = pytest.importorskip('dask.array')
dd = pytest.importorskip('dask.dataframe')
db = pytest.importorskip('dask.bag')
pd = pytest.importorskip('pandas')

SKILL_ROOT = Path(__file__).resolve().parents[2] / 'skills' / 'dask'


def recipe(relative_path, heading):
    text = (SKILL_ROOT / relative_path).read_text()
    section = text.split(heading + '\n', 1)[1]
    return re.search(r'```python\n(.*?)```', section, re.S).group(1)


def run(code, **variables):
    namespace = {'np': np, 'dask': dask, 'da': da, 'dd': dd, 'db': db, **variables}
    exec(compile(code, '<dask-recipe>', 'exec'), namespace)
    return namespace


def test_delayed_block_assembly():
    out = run(recipe('references/arrays.md', '### From Functions'))
    expected = np.block([[np.full((4, 5), i * 10 + j) for j in range(3)] for i in range(2)])
    np.testing.assert_array_equal(out['x'].compute(), expected)
    assert out['x'].chunks == ((4, 4), (5, 5, 5))


def test_block_means_preserve_each_chunk_and_unequal_sizes():
    data = np.arange(35).reshape(5, 7)
    x = da.from_array(data, chunks=(3, 4))
    out = run(recipe('references/arrays.md', '### map_blocks with Different Output Shape'), x=x)
    expected = [[data[:3, :4].mean(), data[:3, 4:].mean()],
                [data[3:, :4].mean(), data[3:, 4:].mean()]]
    np.testing.assert_allclose(out['result'].compute(), expected)
    assert out['result'].shape == (2, 2)
    assert out['result'].mean().compute() != x.mean().compute()


def test_overlap_gaussian_matches_scipy_at_edges_and_seams(tmp_path, monkeypatch):
    zarr = pytest.importorskip('zarr')
    scipy = pytest.importorskip('scipy.ndimage')
    monkeypatch.chdir(tmp_path)
    data = np.zeros((2, 33, 35), dtype=np.uint16)
    data[0, 15:18, 16:19] = 500
    data[0, 0, 0] = 1000
    data[1, -1, -1] = 2000
    da.to_zarr(da.from_array(data, chunks=(1, 16, 17)), 'images.zarr', mode='w-')
    out = run(recipe('references/arrays.md', '### Image Processing'))
    expected = scipy.gaussian_filter(data.astype(float), sigma=(0, 2, 2),
                                     radius=(0, 8, 8), mode='reflect')
    np.testing.assert_allclose(out['filtered'].compute(), expected, rtol=1e-12, atol=1e-12)
    assert out['filtered'].dtype == np.dtype('float64')


def test_exact_svd_qr_reconstruct_input():
    out = run(recipe('references/arrays.md', '### Linear Algebra'))
    expected = out['A'].compute()
    np.testing.assert_allclose((out['U_computed'] * out['s_computed']) @ out['Vt_computed'],
                               expected, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(out['Q_computed'] @ out['R_computed'], expected, atol=1e-12)


def test_zarr_hdf5_roundtrips_and_no_overwrite(tmp_path, monkeypatch):
    pytest.importorskip('zarr')
    h5py = pytest.importorskip('h5py')
    monkeypatch.chdir(tmp_path)
    x = da.from_array(np.arange(120).reshape(12, 10), chunks=(4, 5))
    code = recipe('references/arrays.md', '### To Disk')
    run(code, x=x)
    np.testing.assert_array_equal(da.from_zarr('output.zarr').compute(), x.compute())
    with h5py.File('output.hdf5') as f:
        np.testing.assert_array_equal(f['data'][:], x.compute())
    with pytest.raises((FileExistsError, ValueError)):
        da.to_zarr(x, 'output.zarr', mode='w-')


def test_normalization_constant_array(tmp_path, monkeypatch):
    pytest.importorskip('zarr')
    monkeypatch.chdir(tmp_path)
    da.to_zarr(da.full((6, 8), 7., chunks=(3, 4)), 'large_dataset.zarr', mode='w-')
    run(recipe('SKILL.md', '### Large-Scale Array Computation'))
    np.testing.assert_array_equal(da.from_zarr('normalized.zarr').compute(), np.zeros((6, 8)))


def test_time_series_sorts_unsorted_input_before_resampling(tmp_path, monkeypatch):
    pytest.importorskip('pyarrow')
    monkeypatch.chdir(tmp_path)
    Path('timeseries').mkdir()
    pdf = pd.DataFrame({'timestamp': pd.date_range('2026-01-01', periods=12, freq='20min'),
                        'value': np.arange(12, dtype=float)}).sample(frac=1, random_state=12)
    dd.from_pandas(pdf, npartitions=3, sort=False).to_parquet('timeseries/input.parquet')
    # The reference glob addresses files, so create the same layout as the recipe.
    for part in Path('timeseries/input.parquet').glob('*.parquet'):
        part.rename(Path('timeseries') / part.name)
    out = run(recipe('references/dataframes.md', '### Time Series Analysis'))
    expected = pdf.set_index('timestamp').sort_index().resample('1h').mean()
    pd.testing.assert_frame_equal(out['result'], expected, check_freq=False)


def test_bag_foldby_combines_values_across_partitions():
    records = [{'category': 'a', 'value': 2}, {'category': 'b', 'value': 3},
               {'category': 'a', 'value': 7}, {'category': 'b', 'value': 11}]
    with dask.config.set(scheduler='synchronous'):
        out = run(recipe('references/bags.md', '### FoldBy (Preferred for Aggregations)'),
                  parsed=db.from_sequence(records, partition_size=1))
    assert dict(out['result']) == {'a': 9, 'b': 14}


def test_custom_json_source_defers_loading(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path('data').mkdir()
    source = Path('data/a.json')
    source.write_text('{"value": 1}')
    out = run(recipe('references/bags.md', '### From Custom Sources'))
    source.write_text('{"value": 9}')
    assert out['bag'].compute(scheduler='synchronous') == [{'value': 9}]


@pytest.fixture
def client():
    distributed = pytest.importorskip('distributed')
    with distributed.Client(n_workers=1, threads_per_worker=1, processes=False,
                            dashboard_address=None) as client:
        yield client


def test_nested_tasks_complete_with_one_worker_slot(client):
    out = run(recipe('references/futures.md', '### Dynamic Task Submission'), client=client)
    assert out['result'] == sum(range(16))


def test_scatter_list_as_single_future(client):
    values = [1, 4, 9]
    [future] = client.scatter([values])
    assert client.submit(sum, future).result(timeout=10) == 14


def test_actor_waits_for_state_changes(client):
    code = recipe('references/futures.md', '### Creating Actors')
    code = code.replace('client = Client()', '# Use bounded test client')
    out = run(code, client=client)
    assert out['result'] == 2


def test_plugin_registration(client):
    from distributed import WorkerPlugin
    class ResourcePlugin(WorkerPlugin):
        def setup(self, worker):
            worker.recipe_resource = 42
    client.register_plugin(ResourcePlugin(), name='recipe-resource')
    assert set(client.run(lambda dask_worker: dask_worker.recipe_resource).values()) == {42}


def test_dask_ml_scaler_and_xarray():
    preprocessing = pytest.importorskip('dask_ml.preprocessing')
    xr = pytest.importorskip('xarray')
    source = np.arange(60, dtype=float).reshape(20, 3)
    x = da.from_array(source, chunks=(5, 3))
    scaled = preprocessing.StandardScaler().fit_transform(x)
    np.testing.assert_allclose(scaled.compute(), (source - source.mean(0)) / source.std(0))
    wrapped = xr.DataArray(x, dims=['sample', 'feature'])
    np.testing.assert_allclose(wrapped.mean('sample').compute(), source.mean(0))


def test_distributed_queue_event_and_variable_recipes():
    distributed = pytest.importorskip('distributed')
    # Blocking consumers/waiters need a second worker thread to run the producer/setter.
    with distributed.Client(n_workers=1, threads_per_worker=2, processes=False,
                            dashboard_address=None) as client:
        out = run(recipe('references/futures.md', '**Queues**:'), client=client)
        assert out['results'] == list(range(10))
        out = run(recipe('references/futures.md', '**Events**:').replace('time.sleep(5)', 'time.sleep(0.01)'),
                  client=client)
        assert out['result'] == 'Event occurred'
        out = run(recipe('references/futures.md', '**Variables**:'), client=client)
        assert out['future'].result(timeout=10) == 42
        out['var'].delete()


def test_performance_report_writes_html(client, tmp_path, monkeypatch):
    pytest.importorskip('bokeh')
    monkeypatch.chdir(tmp_path)
    run(recipe('references/schedulers.md', '### Performance Profiling'),
        computation=da.arange(100, chunks=10).sum())
    assert '<html' in Path('performance.html').read_text().lower()


def test_guarded_process_scheduler_and_worker(tmp_path):
    pytest.importorskip('distributed')
    import os
    import subprocess
    import sys
    code = '''from dask import delayed
from distributed import Client

def square(x):
    return x*x

if __name__ == '__main__':
    assert delayed(square)(5).compute(scheduler='processes', num_workers=1) == 25
    with Client(n_workers=1, threads_per_worker=1, dashboard_address=None) as c:
        assert c.submit(square, 6).result(timeout=15) == 36
    print('[OK] guarded process execution')
'''
    script = tmp_path / 'guarded.py'
    script.write_text(code)
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True,
                            timeout=60, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    assert result.returncode == 0, result.stderr
    assert '[OK]' in result.stdout


def test_dataframe_etl_and_schema(tmp_path, monkeypatch):
    pytest.importorskip('pyarrow')
    monkeypatch.chdir(tmp_path)
    Path('raw_data').mkdir()
    pdf = pd.DataFrame({'status': ['valid', 'invalid', 'valid', 'valid'],
                        'category': ['a', 'b', 'a', 'b'],
                        'amount': ['2', '3', '4', '5'], 'quantity': [1, 1, 2, 3],
                        'important_col': [1., 2., 3., np.nan]})
    pdf.iloc[:2].to_csv('raw_data/a.csv', index=False)
    pdf.iloc[2:].to_csv('raw_data/b.csv', index=False)
    run(recipe('references/dataframes.md', '### ETL Pipeline'))
    got = dd.read_parquet('output/summary.parquet').compute()
    # Multi-aggregation Parquet columns must have a stable serializable schema.
    assert got.shape == (1, 3)
    assert got.loc['a'].to_dict() == {'amount_sum': 6., 'amount_mean': 3., 'quantity_count': 2}


def test_bag_cleaning_preserves_list_column(tmp_path, monkeypatch):
    import json
    pytest.importorskip('pyarrow')
    monkeypatch.chdir(tmp_path)
    Path('raw_data').mkdir()
    records = [{'id': '1', 'timestamp': '2026-01-01', 'value': '2', 'tags': ['x', 'y']},
               {'id': '2', 'timestamp': '2026-01-02', 'value': '-1'},
               {'id': '3', 'timestamp': '2026-01-03', 'value': '3', 'tags': []}]
    Path('raw_data/records.json').write_text('\n'.join(map(json.dumps, records)))
    with dask.config.set(scheduler='synchronous'):
        run(recipe('references/bags.md', '### Data Cleaning Pipeline'))
        got = dd.read_parquet('cleaned_data/').compute()
    assert got['id'].tolist() == [1, 3]
    assert [list(tags) for tags in got['tags']] == [['x', 'y'], []]
