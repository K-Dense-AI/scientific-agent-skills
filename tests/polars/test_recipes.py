"""Bounded native regressions for the Polars skill's corrected recipes."""
from datetime import date, datetime
from io import StringIO
from pathlib import Path
import json
import math
import sqlite3

import pytest

pl = pytest.importorskip("polars")
from polars.testing import assert_frame_equal
import polars.selectors as cs

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "polars"


def test_csv_schema_keeps_ids_and_rejects_invalid_measurement(tmp_path):
    path = tmp_path / "measurements.csv"
    path.write_text("sample_id,value,date\n001,2.5,2026-01-01\n002,NA,2026-01-02\n", encoding="utf-8")
    lf = pl.scan_csv(path, schema_overrides={"sample_id": pl.String, "value": pl.Float64,
                                           "date": pl.Date}, null_values="NA")
    assert lf.collect_schema() == {"sample_id": pl.String, "value": pl.Float64, "date": pl.Date}
    query = lf.filter(pl.col("date") >= pl.date(2026, 1, 1)).select("sample_id", "value")
    expected = pl.DataFrame({"sample_id": ["001", "002"], "value": [2.5, None]})
    assert_frame_equal(query.collect(), expected)
    assert_frame_equal(query.collect(engine="streaming"), expected)
    assert "PROJECT" in query.explain()
    path.write_text("sample_id,value\n003,broken\n", encoding="utf-8")
    with pytest.raises(pl.exceptions.ComputeError):
        pl.read_csv(path, schema_overrides={"value": pl.Float64})
    raw = pl.read_csv(path, infer_schema=False)
    parsed = raw.with_columns(value=pl.col("value").cast(pl.Float64, strict=False))
    failed = raw.filter(raw["value"].is_not_null() & parsed["value"].is_null())
    assert failed["sample_id"].to_list() == ["003"]


def test_csv_record_skipping_and_thread_option(tmp_path):
    path = tmp_path / "records.csv"
    path.write_text('"preamble\ncontinued",ignored\nsample_id,value\n001,2\n002,3\n')
    df = pl.read_csv(path, skip_rows=1, schema_overrides={"sample_id": pl.String}, n_threads=2)
    assert df["sample_id"].to_list() == ["001", "002"]
    out = tmp_path / "out.csv"
    df.write_csv(out, include_header=True, line_terminator="\n", null_value="")
    assert_frame_equal(pl.read_csv(out, schema_overrides={"sample_id": pl.String}), df)


def test_duplicate_raw_headers_need_upstream_validation():
    raw = "sample_id,sample_id\n001,002\n"
    # The parser changes the duplicate header, so resulting column uniqueness is insufficient.
    df = pl.read_csv(StringIO(raw), infer_schema=False)
    assert len(set(df.columns)) == 2
    import csv
    header = next(csv.reader(StringIO(raw)))
    assert len(set(header)) != len(header)


def test_null_nan_and_nonfinite_counts():
    df = pl.DataFrame({"x": [1.0, None, float("nan"), float("inf")]})
    summary = df.select(rows=pl.len(), observed=pl.col("x").count(),
                        nulls=pl.col("x").null_count(), nans=pl.col("x").is_nan().sum(),
                        finite=pl.col("x").is_finite().sum())
    assert summary.row(0) == (4, 3, 1, 1, 1)
    assert math.isnan(df.fill_null(0)["x"][2])
    assert df.with_columns(pl.col("x").fill_nan(None)).null_count()["x"][0] == 2
    assert pl.Series([1, 1, None]).n_unique() == 2


def test_scientific_aggregation_conventions():
    df = pl.DataFrame({"x": [0.0, 10.0]})
    summary = df.select(sample_sd=pl.col("x").std(ddof=1),
                        population_sd=pl.col("x").std(ddof=0),
                        median=pl.col("x").median(),
                        nearest=pl.col("x").quantile(0.5, interpolation="nearest"))
    assert summary.row(0) == pytest.approx((math.sqrt(50), 5, 5, 10))
    with pytest.raises(pl.exceptions.InvalidOperationError):
        pl.Series([128]).cast(pl.Int8)


def test_filter_does_not_move_across_mean():
    lf = pl.LazyFrame({"category": ["A", "A", "B", "B"], "value": [0, 200, 110, 130]})
    other = pl.LazyFrame({"category": ["A", "B"], "other_col": [1, 2]})
    original = (lf.group_by("category").agg(pl.col("value").mean())
                .join(other, on="category").filter(pl.col("value") > 100)
                .select("category", "value"))
    revised = (lf.select("category", "value").group_by("category")
               .agg(pl.col("value").mean()).filter(pl.col("value") > 100)
               .join(other.select("category", "other_col"), on="category")
               .select("category", "value"))
    assert_frame_equal(original.collect(), revised.collect())
    assert revised.collect()["category"].to_list() == ["B"]
    incorrect = lf.filter(pl.col("value") > 100).group_by("category").agg(pl.col("value").mean())
    assert incorrect.collect().height == 2


def test_context_dependencies_and_lazy_pipe():
    df = pl.DataFrame({"value": [4, 6]})
    with pytest.raises(pl.exceptions.ColumnNotFoundError):
        df.with_columns(doubled=pl.col("value") * 2, plus_one=pl.col("doubled") + 1)
    result = df.with_columns(doubled=pl.col("value") * 2).with_columns(plus_one=pl.col("doubled") + 1)
    assert result["plus_one"].to_list() == [9, 13]
    def add_double(lf):
        return lf.with_columns(doubled=pl.col("value") * 2)
    query = df.lazy().pipe(add_double).filter(pl.col("doubled") > 10)
    assert query.collect()["value"].to_list() == [6]


def test_when_masks_elementwise_cast_but_not_arbitrary_invalid_branches():
    df = pl.DataFrame({"x": ["1", "bad"]})
    masked = df.select(pl.when(pl.col("x") != "bad").then(pl.col("x").cast(pl.Int64)).otherwise(None))
    assert masked["x"].to_list() == [1, None]
    with pytest.raises(pl.exceptions.OutOfBoundsError):
        df.select(pl.when(pl.col("x") != "bad").then(pl.col("x").gather(100)).otherwise(None))
    assert df.select(pl.col("x").cast(pl.Int64, strict=False))["x"].to_list() == [1, None]


def test_join_cardinality_null_policy_coalesce():
    left = pl.DataFrame({"id": ["A", "B", None], "x": [1, 2, 3]})
    right = pl.DataFrame({"id": ["A", "A", None], "y": [4, 5, 6]})
    with pytest.raises(pl.exceptions.ComputeError):
        left.join(right, on="id", validate="m:1")
    assert left.join(right, on="id").height == 2
    assert left.join(right, on="id", nulls_equal=True).height == 3
    assert left.join(right, on="id", how="anti")["id"].to_list() == ["B", None]
    full = left.join(pl.DataFrame({"id": ["C"], "y": [7]}), on="id", how="full", coalesce=True)
    assert "id_right" not in full.columns
    assert set(full["id"].drop_nulls()) == {"A", "B", "C"}


def test_asof_matching_types_sortedness_and_tolerance():
    quotes = pl.DataFrame({"timestamp": [1., 2., 3., 4., 5.], "stock": ["A"] * 5,
                           "quote": [100, 101, 102, 103, 104]})
    trades = pl.DataFrame({"timestamp": [1.5, 3.5, 4.2], "stock": ["A"] * 3,
                           "trade": [50, 75, 100]})
    # Grouped sort cannot be checked by Polars, so sort both inputs explicitly.
    with pytest.warns(UserWarning, match="Sortedness"):
        result = trades.sort("stock", "timestamp").join_asof(
            quotes.sort("stock", "timestamp"), on="timestamp", by="stock",
            strategy="backward", tolerance=0.6)
    assert result["quote"].to_list() == [100, 102, 103]
    result = trades.drop("stock").sort("timestamp").join_asof(
        quotes.drop("stock").sort("timestamp"), on="timestamp", tolerance=0.1)
    assert result["quote"].null_count() == 3
    with pytest.raises(pl.exceptions.SchemaError):
        trades.drop("stock").join_asof(quotes.drop("stock").with_columns(pl.col("timestamp").cast(pl.Int64)), on="timestamp")


def test_horizontal_concat_padding_strict_and_vertical_coercion():
    a = pl.DataFrame({"a": [1, 2]})
    b = pl.DataFrame({"b": [3]})
    assert pl.concat([a, b], how="horizontal_extend")["b"].to_list() == [3, None]
    with pytest.raises(pl.exceptions.ShapeError):
        pl.concat([a, b], how="horizontal", strict=True)
    assert pl.concat([a, pl.DataFrame({"a": [3.5]})], how="vertical_relaxed").schema["a"] == pl.Float64


def test_eager_lazy_pivot_and_selector_unpivot():
    df = pl.DataFrame({"date": ["Jan", "Jan", "Feb", "Feb"], "product": ["A", "B", "A", "B"],
                       "sales": [100, 150, 120, 160]})
    eager = df.pivot(on="product", values="sales", index="date")
    lazy = df.lazy().pivot(on="product", on_columns=["A", "B"], values="sales", index="date").collect()
    assert_frame_equal(eager.sort("date"), lazy.sort("date"))
    with pytest.raises(pl.exceptions.ComputeError):
        pl.concat([df, df.head(1)]).pivot(on="product", values="sales", index="date")
    wide = pl.DataFrame({"id": [1, 2], "sales_Q1": [100, 200], "sales_Q2": [150, 250], "other": [3, 4]})
    long = wide.unpivot(index="id", on=cs.matches("^sales_.*$"))
    assert long.height == 4
    assert set(long["variable"]) == {"sales_Q1", "sales_Q2"}


def test_explode_window_needs_select_not_with_columns():
    df = pl.DataFrame({"category": ["A", "B", "A"], "value": [1, 10, 3]})
    expr = pl.col("value").mean().over("category", mapping_strategy="explode")
    assert df.select(group_mean=expr)["group_mean"].to_list() == [2, 10]
    with pytest.raises(pl.exceptions.ShapeError):
        df.with_columns(group_mean=expr)
    assert df.with_columns(group_mean=pl.col("value").mean().over("category"))["group_mean"].to_list() == [2, 10, 2]


def test_time_rolling_calendar_offsets_and_ordered_rank():
    df = pl.DataFrame({"date": [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 10)],
                       "value": [2., 4., 8.]})
    result = df.with_columns(rolling_avg=pl.col("value").rolling_mean_by("date", window_size="7d", min_samples=1, closed="right"))
    assert result["rolling_avg"].to_list() == [2, 3, 8]
    assert pl.select(pl.lit(date(2026, 1, 31)).dt.offset_by("1mo")).item() == date(2026, 2, 28)
    subjects = pl.DataFrame({"subject": ["A", "A", "B"], "timestamp": [2, 1, 1], "value": [20, 10, 99]})
    ranked = subjects.with_columns(row_num=pl.col("timestamp").rank(method="ordinal").over("subject"),
                                    lag=pl.col("value").shift(1).over("subject", order_by="timestamp"))
    assert ranked["row_num"].to_list() == [2, 1, 1]
    assert ranked["lag"].to_list() == [10, None, None]


def test_selectors_strings_nested_and_distinct_aliases():
    df = pl.DataFrame({"name": ["é", "abcd"], "sales_x": [1, 2], "x_total": [3, 4], "net_revenue": [5, 6]})
    assert df.sort(pl.col("name").str.len_chars())["name"].to_list() == ["é", "abcd"]
    assert df.select(pl.col("^sales.*$"), pl.col("^.*_total$"), pl.col("^.*revenue.*$")).width == 3
    result = df.select((pl.col("sales_x") * 10).alias("scaled"),
                       pl.col("sales_x").log().alias("log_value"),
                       pl.col("sales_x").sqrt().alias("sqrt_value"))
    assert result.columns == ["scaled", "log_value", "sqrt_value"]
    df = pl.DataFrame({"email": ["x@gmail.com", "x@gmailXcom"]})
    assert df.filter(pl.col("email").str.contains("@gmail.com", literal=True)).height == 1
    nested = pl.DataFrame({"id": [1], "items": [[{"x": 2}, {"x": 3}]]})
    assert nested.explode("items", empty_as_null=True).unnest("items")["x"].to_list() == [2, 3]


def test_local_json_ndjson_and_ipc_formats(tmp_path):
    df = pl.read_json(StringIO('[{"col1": 1, "col2": "a"}, {"col1": 2, "col2": "b"}]'))
    path = tmp_path / "data.json"
    df.write_json(path)
    assert_frame_equal(pl.read_json(path), df)
    assert isinstance(json.loads(path.read_text()), list)
    path = tmp_path / "data.ndjson"
    df.write_ndjson(path)
    assert_frame_equal(pl.scan_ndjson(path).collect(), df)
    for filename, writer, reader in [("data.arrow", "write_ipc", pl.read_ipc),
                                      ("data.arrows", "write_ipc_stream", pl.read_ipc_stream)]:
        path = tmp_path / filename
        getattr(df, writer)(path, compression="zstd")
        # Disable memory mapping for compressed IPC files to avoid a harmless warning.
        got = reader(path, memory_map=False) if reader is pl.read_ipc else reader(path)
        assert_frame_equal(got, df)
    assert_frame_equal(pl.scan_ipc(tmp_path / "data.arrow").collect(), df)


def test_parquet_sink_and_explicit_hive(tmp_path):
    df = pl.DataFrame({"year": [2026, 2026], "month": [1, 2], "sample_id": ["001", "002"], "value": [2., 3.]})
    output = tmp_path / "result.parquet"
    df.lazy().filter(pl.col("value") > 2).sink_parquet(output)
    assert_frame_equal(pl.read_parquet(output), df.tail(1))
    partitioned = tmp_path / "partitions"
    df.write_parquet(partitioned, partition_by=["year", "month"])
    result = pl.scan_parquet(str(partitioned / "**/*.parquet"), hive_partitioning=True).collect().sort("sample_id")
    assert_frame_equal(result.select(df.columns), df)


def test_excel_workbook_sheet_ids_and_fastexcel_options(tmp_path):
    xlsxwriter = pytest.importorskip("xlsxwriter")
    pytest.importorskip("fastexcel")
    df = pl.DataFrame({"sample_id": [f"S{i}" for i in range(8)], "value": list(range(8))})
    path = tmp_path / "output.xlsx"
    with xlsxwriter.Workbook(path) as writer:
        df.write_excel(workbook=writer, worksheet="Sheet1")
        df.head(2).write_excel(workbook=writer, worksheet="Sheet2")
    assert_frame_equal(pl.read_excel(path, sheet_id=1), df)
    sheets = pl.read_excel(path, sheet_id=0)
    assert set(sheets) == {"Sheet1", "Sheet2"}
    assert_frame_equal(sheets["Sheet2"], df.head(2))
    subset = pl.read_excel(path, sheet_name="Sheet1", columns=["sample_id", "value"],
                          engine="calamine", read_options={"n_rows": 2, "skip_rows": 5}, has_header=True)
    assert_frame_equal(subset, df.slice(5, 2))


def test_sqlite_parameter_binding_batches_and_write_policy(tmp_path):
    sqlalchemy = pytest.importorskip("sqlalchemy")
    pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    path = tmp_path / "study.sqlite"
    engine = sqlalchemy.create_engine(f"sqlite:///{path}")
    df = pl.DataFrame({"sample_id": ["001", "002", "003"], "value": [10, 30, 40]})
    assert df.write_database("observations", connection=engine, if_table_exists="fail") == 3
    with pytest.raises(ValueError):
        df.write_database("observations", connection=engine, if_table_exists="fail")
    with sqlite3.connect(path) as connection:
        result = pl.read_database("SELECT * FROM observations WHERE value > ?", connection=connection,
                                  execute_options={"parameters": [25]})
        assert_frame_equal(result, df.tail(2))
        batches = list(pl.read_database("SELECT * FROM observations ORDER BY sample_id", connection=connection,
                                        iter_batches=True, batch_size=2))
        assert [b.height for b in batches] == [2, 1]
        assert_frame_equal(pl.concat(batches), df)
    engine.dispose()


def test_sql_context_is_local_lazy_and_equivalent():
    df = pl.DataFrame({"sample_id": ["A", "A", "B"], "value": [1., 3., 10.]})
    with pl.SQLContext(observations=df.lazy(), eager=False) as ctx:
        result = ctx.execute("SELECT sample_id, AVG(value) AS mean_value FROM observations GROUP BY sample_id")
    assert isinstance(result, pl.LazyFrame)
    expected = df.group_by("sample_id").agg(mean_value=pl.col("value").mean()).sort("sample_id")
    assert_frame_equal(result.collect().sort("sample_id"), expected)


def test_numpy_arrow_and_pandas_preserve_orientation_and_nulls():
    np = pytest.importorskip("numpy")
    pa = pytest.importorskip("pyarrow")
    pd = pytest.importorskip("pandas")
    arr = np.array([[1, 2], [3, 4], [5, 6]])
    df = pl.DataFrame(arr, schema=["col1", "col2"], orient="row")
    assert df.shape == (3, 2)
    np.testing.assert_array_equal(df.to_numpy(), arr)
    pd_df = pd.DataFrame({"col": pd.Series([1, None, 3], dtype="Int64")})
    frame = pl.from_arrow(pa.Table.from_pandas(pd_df, preserve_index=False))
    assert frame.schema["col"] == pl.Int64
    assert frame["col"].to_list() == [1, None, 3]
    restored = frame.to_pandas(use_pyarrow_extension_array=True)
    assert restored["col"].isna().tolist() == [False, True, False]
    assert_frame_equal(pl.from_pandas(restored), frame)
    rows = pl.DataFrame([("Alice", 25), ("Bob", 30)], schema=["name", "age"], orient="row")
    assert rows.row(1) == ("Bob", 30)


def test_pandas_migration_changes_null_join_and_group_semantics():
    pd = pytest.importorskip("pandas")
    left = pd.DataFrame({"id": ["A", None], "x": [1, 2]})
    right = pd.DataFrame({"id": [None], "y": [3]})
    assert len(left.merge(right, on="id")) == 1
    assert pl.from_pandas(left).join(pl.from_pandas(right), on="id").height == 0
    assert left.groupby("id")["x"].sum().shape[0] == 1
    assert pl.from_pandas(left).group_by("id").agg(pl.col("x").sum()).height == 2
