"""Current-package mechanics. Tiny native models are not forecast-accuracy evidence."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import types
from unittest import mock

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "timesfm-forecasting"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")
import forecast_csv as fc
import check_system as cs


def example(relative):
    spec = importlib.util.spec_from_file_location(Path(relative).stem, SKILL_ROOT / "examples" / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("values", [[], [np.nan, np.nan], [1, np.inf], [1, np.nan], [np.nan, 1]])
def test_invalid_histories_reject_without_moving_origin(values):
    with pytest.raises(ValueError):
        fc.prepare_inputs(pd.DataFrame({"y": values}), ["y"], "interpolate")


def test_missing_requires_explicit_policy():
    df = pd.DataFrame({"y": [1, np.nan, 3]})
    with pytest.raises(ValueError):
        fc.prepare_inputs(df, ["y"])
    np.testing.assert_array_equal(fc.prepare_inputs(df, ["y"], "interpolate")[0], [1, 2, 3])


@pytest.mark.parametrize("text", [
    "date,y,y\n2026-01-01,1,2\n",  # duplicate raw headers
    "date,y\n2026-01-01,1\n2026-01-01,2\n",  # duplicate dates
    "date,y\n2026-01-01,1\n2026-01-03,2\n",  # missing day
    "date,y\nbad,1\n",  # invalid timestamp
])
def test_grid_failures(text, tmp_path):
    path = tmp_path / "x.csv"
    path.write_text(text)
    with pytest.raises(ValueError):
        fc.load_csv(str(path), "date", ["y"], "D")


def test_sorted_month_grid_and_short_frequency(tmp_path):
    path = tmp_path / "x.csv"
    path.write_text("date,y\n2026-02-01,2\n2026-01-01,1\n")
    with pytest.raises(ValueError):
        fc.load_csv(str(path), "date", ["y"])
    frame, _, _ = fc.load_csv(str(path), "date", ["y"], "MS")
    assert list(frame.y) == [1, 2]
    assert frame.attrs["frequency"] == "MS"


def test_available_ram_not_total_controls_verdict():
    with mock.patch.object(cs, "_get_total_ram_gb", return_value=128), mock.patch.object(cs, "_get_available_ram_gb", return_value=1):
        assert cs.check_ram(cs.MODEL_PROFILES["v2.5"]).status == "fail"


def test_macos_page_size_is_read_from_vm_stat():
    output = 'Mach Virtual Memory Statistics: (page size of 16384 bytes)\nPages free: 65536.\nPages inactive: 65536.\n'
    with mock.patch.object(sys, "platform", "darwin"), mock.patch("subprocess.run", return_value=types.SimpleNamespace(stdout=output)):
        assert cs._get_available_ram_gb() == 2.0


def test_explicit_hub_cache_checks_nearest_existing_volume(tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path / "new" / "hub"))
    with mock.patch("shutil.disk_usage", return_value=types.SimpleNamespace(free=10 * 1024**3)) as measured:
        cs.check_disk(cs.MODEL_PROFILES["v2.5"])
    assert measured.call_args.args[0] == str(tmp_path)


def test_config_real_dataclass_and_limits():
    pytest.importorskip("timesfm")
    config = fc.forecast_config(129, 33)
    assert (config.max_horizon, config.max_context) == (256, 64)
    assert not config.infer_is_positive
    for args in [(0, 512, 1), (1025, 512, 1), (128, 16384, 1), (12, 512, 0)]:
        with pytest.raises(ValueError):
            fc.forecast_config(*args)


def test_model_output_rejects_nonfinite_crossed_or_wrong_median():
    q = np.tile(np.arange(10.0), (1, 3, 1))
    point = q[..., 5].copy()
    fc.validate_forecast(point, q, 1, 3)
    for broken in (q[..., :9], q * np.nan):
        with pytest.raises(ValueError):
            fc.validate_forecast(point, broken, 1, 3)
    q[..., 1] = 99
    with pytest.raises(ValueError):
        fc.validate_forecast(point, q, 1, 3)


def model25_stub(backcast=False):
    """Real 2.5 compile/preprocessing with controlled torch decoder, no large allocation."""
    torch = pytest.importorskip("torch")
    timesfm = pytest.importorskip("timesfm")
    cls = timesfm.TimesFM_2p5_200M_torch
    model = cls.__new__(cls)

    def decode(horizon, inputs, masks):
        batch, length = inputs.shape
        # Median residual prediction 0; ordered spread demonstrates native postprocessing.
        deciles = torch.arange(10, dtype=torch.float32) - 5
        pf = deciles.repeat(batch, length // 32, 128, 1)
        spread = deciles.repeat(batch, 1024, 1)
        return pf, spread, None

    model.model = types.SimpleNamespace(device_count=1, p=32, o=128, os=1024, q=10,
        config=types.SimpleNamespace(context_limit=16384), device=torch.device("cpu"), decode=decode)
    model.compile(timesfm.ForecastConfig(max_context=64, max_horizon=128,
        per_core_batch_size=2, normalize_inputs=False, return_backcast=backcast,
        force_flip_invariance=False, infer_is_positive=False,
        use_continuous_quantile_head=True, fix_quantile_crossing=True))
    return model


def test_native_25_preprocess_output_and_list_mutation():
    model = model25_stub()
    histories = [np.arange(48, dtype=np.float32)]
    point, q = model.forecast(horizon=12, inputs=histories)
    assert len(histories) == 2  # upstream adds padding to caller list
    assert point.shape == (1, 12) and q.shape == (1, 12, 10)
    np.testing.assert_array_equal(point, q[..., 5])
    assert np.all(np.diff(q[..., 1:], axis=-1) >= 0)
    model = model25_stub(backcast=True)
    point, q = model.forecast(horizon=12, inputs=[np.arange(48, dtype=float)])
    assert point.shape == (1, 32 + 12)


@pytest.mark.parametrize("mode", ["xreg + timesfm", "timesfm + xreg"])
def test_native_xreg_returns_combined_quantiles_and_known_linear_trend(mode):
    pytest.importorskip("jax")
    pytest.importorskip("sklearn")
    model = model25_stub(backcast=True)
    x = np.arange(60, dtype=float)
    point, q = model.forecast_with_covariates(
        inputs=[3 + 2 * x[:48]], dynamic_numerical_covariates={"x": [x]},
        xreg_mode=mode, force_on_cpu=True, normalize_xreg_target_per_input=False,
    )
    assert isinstance(point, list) and isinstance(q, list)
    assert np.asarray(q).shape == (1, 12, 10)
    np.testing.assert_allclose(point[0], 3 + 2 * x[48:], rtol=1e-5, atol=1e-3)
    np.testing.assert_allclose(point[0], q[0][..., 5])


def test_native_3_tiny_random_save_load_univariate_multivariate_and_covariates(tmp_path):
    torch = pytest.importorskip("torch")
    from timesfm3 import TimesFM3Forecaster, TimesFM3Torch, ResidualBlockConfig, StackedTransformersConfig, TransformerConfig
    torch.manual_seed(2)
    model = TimesFM3Torch(
        input_patch_len=8, output_patch_len=16,
        quantiles=[i / 10 for i in range(1, 10)],
        residual_block_config=ResidualBlockConfig(hidden_dims=16, output_dims=16, use_bias=False, activation="relu"),
        transformer_config=StackedTransformersConfig(num_layers=1, transformer=TransformerConfig(
            model_dims=16, hidden_dims=16, num_heads=2, attention_norm="rms", feedforward_norm="rms",
            qk_norm="rms", use_rope_seq=True, use_rope_var=True, use_bias=False, ff_activation="relu", deterministic=True)),
    )
    model.save_pretrained(tmp_path)
    forecaster = TimesFM3Forecaster.from_pretrained(str(tmp_path), device="cpu", per_core_batch_size=1, local_files_only=True)
    target = np.sin(np.arange(32) / 4).astype(np.float32)
    out = forecaster.predict(target, horizon=20, return_quantiles=True)
    assert out.forecast.shape == (20,) and out.quantiles.shape == (20, 9)
    assert np.isfinite(out.quantiles).all()
    np.testing.assert_allclose(out.forecast, out.quantiles[:, 4])
    outputs = list(forecaster.predict_batch([target, target[:24]], horizon=8))
    assert len(outputs) == 2 and outputs[1].forecast.shape == (8,) and outputs[0].quantiles is None
    out = forecaster.predict(np.stack([target, target * 2]), horizon=20,
        past_only_covariates=np.ones((1, 32), dtype=np.float32),
        past_future_covariates=np.sin(np.arange(52) / 7)[None, :].astype(np.float32), return_quantiles=True)
    assert out.forecast.shape == (2, 20) and out.quantiles.shape == (2, 20, 9)
    assert np.isfinite(out.quantiles).all() and np.all(np.diff(out.quantiles, axis=-1) >= 0)


def test_covariate_generator_preserves_store_identity():
    pytest.importorskip("matplotlib")
    module = example("covariates-forecasting/demo_covariates.py")
    data = module.generate_sales_data()
    kw = module.build_covariates(data)
    assert [len(v) for v in kw["inputs"]] == [24, 24, 24]
    prices = kw["dynamic_numerical_covariates"]["price"]
    assert all(len(p) == 36 for p in prices)
    assert prices[0].mean() > prices[1].mean() > prices[2].mean()
    np.testing.assert_array_equal(kw["inputs"][0], data["stores"]["store_A"]["sales"][:24])


def test_anomaly_bands_and_small_synthetic_horizon():
    pytest.importorskip("matplotlib")
    module = example("anomaly-detection/detect_anomalies.py")
    q = np.tile(np.arange(10.0)[:, None], (1, 3))
    records = module.detect_forecast_anomalies(np.array([0., 1.5, 5.]), np.ones(3) * 5, q,
        ["2026-01", "2026-02", "2026-03"], [])
    assert [r["severity"] for r in records] == ["CRITICAL", "WARNING", "NORMAL"]
    assert len(module.build_synthetic_future(np.ones(12), 2)[0]) == 2


def test_example_forecast_and_animation_mapping_without_pretrained_weights(tmp_path):
    pytest.importorskip("timesfm")
    run = example("global-temperature/run_forecast.py")
    anim = example("global-temperature/generate_animation_data.py")
    for module in (run, anim):
        with mock.patch.object(module, "run_preflight"), mock.patch.object(module, "load_model", side_effect=lambda **kw: model25_stub()):
            payload = module.run(tmp_path)
        assert payload["schema_version"] == "2.5-deciles-v1"
    animation = json.loads((tmp_path / "animation_data.json").read_text())
    assert len(animation["animation_steps"]) == 25
    for step in animation["animation_steps"]:
        assert pd.Timestamp(step["forecast_dates"][0]) > pd.Timestamp(step["last_historical_date"])
        assert step["q10"][0] == -4 and step["q90"][0] == 4
    output = json.loads((tmp_path / "forecast_output.json").read_text())
    assert set(output["forecast"]["quantiles"]) == {f"{i*10}%" for i in range(1,10)}


def test_native_25_tiny_random_transformer_inference():
    """Exercise real tokenizer/attention/decode with test-only reduced hidden sizes."""
    torch = pytest.importorskip("torch")
    import dataclasses
    import timesfm
    from timesfm.timesfm_2p5 import timesfm_2p5_torch as backend
    original = backend.TimesFM_2p5_200M_torch_module.config
    tiny = dataclasses.replace(original,
        tokenizer=dataclasses.replace(original.tokenizer, hidden_dims=16, output_dims=16),
        stacked_transformers=dataclasses.replace(original.stacked_transformers, num_layers=1,
            transformer=dataclasses.replace(original.stacked_transformers.transformer,
                model_dims=16, hidden_dims=16, num_heads=2)),
        output_projection_point=dataclasses.replace(original.output_projection_point, input_dims=16, hidden_dims=16),
        output_projection_quantiles=dataclasses.replace(original.output_projection_quantiles, input_dims=16, hidden_dims=16),
    )
    torch.manual_seed(4)
    with mock.patch.object(backend.TimesFM_2p5_200M_torch_module, "config", tiny), mock.patch.object(torch.cuda, "is_available", return_value=False):
        model = timesfm.TimesFM_2p5_200M_torch(torch_compile=False)
        model.model.eval()
        model.compile(fc.forecast_config(horizon=129, max_context=64))
        x = np.sin(np.arange(48) / 4).astype(np.float32)
        point, q = model.forecast(horizon=129, inputs=[x])
        fc.validate_forecast(point, q, 1, 129)
        neg, _ = model.forecast(horizon=129, inputs=[-x])
        np.testing.assert_allclose(neg, -point, atol=1e-5)


def test_cli_exports_aligned_dates_and_reproducibility_metadata(tmp_path, monkeypatch):
    path = tmp_path / "input.csv"
    output = tmp_path / "forecast.csv"
    path.write_text("date,y\n2026-01-03,3\n2026-01-01,1\n2026-01-02,2\n")
    monkeypatch.setattr(sys, "argv", ["forecast_csv.py", str(path), "--date-col", "date", "--value-cols", "y", "--horizon", "12", "--output", str(output)])
    with mock.patch.object(fc, "run_preflight"), mock.patch.object(fc, "load_model", return_value=model25_stub()):
        fc.main()
    written = pd.read_csv(output)
    assert written.date.iloc[0] == "2026-01-04" and len(written) == 12
    metadata = json.loads(Path(str(output) + ".metadata.json").read_text())
    assert metadata["revision"] == fc.MODEL_REVISION
    assert metadata["forecast_origin"].startswith("2026-01-03")
    assert metadata["frequency"] == "D" and metadata["config"]["max_horizon"] == 128


def test_bad_cli_input_never_loads_model(tmp_path, monkeypatch):
    path = tmp_path / "input.csv"
    path.write_text("date,y\n2026-01-01,1\n2026-01-01,2\n")
    monkeypatch.setattr(sys, "argv", ["forecast_csv.py", str(path), "--date-col", "date", "--horizon", "12"])
    with mock.patch.object(fc, "load_model") as load, pytest.raises(SystemExit):
        fc.main()
    load.assert_not_called()
