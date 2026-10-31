import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest
import skill_contract

np = pytest.importorskip("numpy")
pytest.importorskip("nmrglue")
pytest.importorskip("scipy")
SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "nmrglue"
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)
spec = importlib.util.spec_from_file_location("nmr_process_1d", SKILL_ROOT / "scripts" / "process_1d.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def example():
    config = json.loads((SKILL_ROOT / "assets" / "processing.json").read_text())
    t = np.arange(8192) / config["spectral_width_hz"]
    fid = sum(a * np.exp(-np.pi * 2 * t) * np.exp(-2j * np.pi * (ppm - 5) * 400 * t)
              for ppm, a in [(3, 1), (7, 2)])
    return fid, config


def test_known_two_line_spectrum_orientation_and_area_ratio():
    fid, config = example()
    result = module.process(fid, config)
    assert np.all(np.diff(result["ppm"]) < 0)
    assert sorted(p["ppm"] for p in result["peaks"]) == pytest.approx([3, 7], abs=0.001)
    a, b = [r["area_signal_ppm"] for r in result["integrals"]]
    assert a > 0
    assert b / a == pytest.approx(2, rel=0.001)
    assert result["acquisition_time_s"] == 2.048
    # Infinite-time causal Lorentzian, first point halved: integral is SW/(2*obs)*amplitude.
    assert a == pytest.approx(5, rel=0.01)


def test_positive_complex_convention_and_phase_recovery():
    fid, config = example()
    expected = module.process(fid, config)
    config["fid_sign"] = "+i"
    config["phase0_deg"] = -30
    actual = module.process((fid * np.exp(1j * np.pi / 6)).conj(), config)
    np.testing.assert_allclose(actual["real"], expected["real"], atol=1e-11)


def test_linear_baseline_removes_added_constant():
    fid, config = example()
    # A real offset at t=0 transforms to a constant baseline.
    noisy = fid.copy()
    noisy[0] += 20
    config.update(baseline="linear", baseline_regions_ppm=[[0.2, 0.8], [9.2, 9.8]])
    result = module.process(noisy, config)
    assert np.median(result["baseline"]) == pytest.approx(10, abs=0.02)
    assert result["integrals"][1]["area_signal_ppm"] / result["integrals"][0]["area_signal_ppm"] == pytest.approx(2, rel=0.002)


@pytest.mark.parametrize("change", [{"spectral_width_hz": 0}, {"fid_sign": "unknown"},
                                      {"integration_regions_ppm": [[-1, 2]]},
                                      {"zero_fill_points": 15}, {"line_broadening_hz": -1},
                                      {"baseline": "linear", "baseline_regions_ppm": []}])
def test_invalid_scientific_settings_rejected(change):
    fid, config = example()
    config.update(change)
    with pytest.raises(ValueError):
        module.process(fid, config)


def test_nonfinite_and_real_fids_rejected():
    fid, config = example()
    with pytest.raises(ValueError):
        module.process(fid.real, config)
    fid[10] = np.nan
    with pytest.raises(ValueError):
        module.process(fid, config)


def test_cli_writes_spectrum_and_provenance(tmp_path):
    fid, config = example()
    np.savez(tmp_path / "fid.npz", fid=fid)
    (tmp_path / "settings.json").write_text(json.dumps(config))
    command = [sys.executable, str(SKILL_ROOT / "scripts" / "process_1d.py"), str(tmp_path / "fid.npz"),
               str(tmp_path / "settings.json"), str(tmp_path / "result")]
    outcome = subprocess.run(command, capture_output=True, text=True, timeout=60)
    assert outcome.returncode == 0, outcome.stderr
    report = json.loads((tmp_path / "result" / "report.json").read_text())
    assert len(report["input_sha256"]) == 64
    assert len(report["peaks"]) == 2
    assert len((tmp_path / "result" / "spectrum.csv").read_text().splitlines()) == 32769
    assert subprocess.run(command, capture_output=True, text=True, timeout=60).returncode != 0


def write_synthetic_nmrpipe(path, fid, config, frequency_domain=False):
    import nmrglue as ng
    universal = ng.fileiobase.create_blank_udic(1)
    universal[0].update(size=len(fid), complex=True, time=not frequency_domain,
                        freq=frequency_domain, sw=config["spectral_width_hz"],
                        obs=config["observation_mhz"], car=config["carrier_ppm"] * config["observation_mhz"],
                        label=config["nucleus"], encoding="direct")
    header = ng.pipe.create_dic(universal)
    ng.pipe.write(str(path), header, fid.astype(np.complex64))


def test_nmrpipe_roundtrip_and_cli_calibrated_spectrum(tmp_path):
    fid, config = example()
    pipe_path = tmp_path / "synthetic.fid"
    write_synthetic_nmrpipe(pipe_path, fid, config)
    decoded, metadata = module.load_fid(pipe_path, config, "nmrpipe")
    np.testing.assert_array_equal(decoded, fid.astype(np.complex64))
    assert metadata["header"]["FDF2FTFLAG"] == 0
    config_path = tmp_path / "settings.json"
    config_path.write_text(json.dumps(config))
    result = subprocess.run([sys.executable, str(SKILL_ROOT / "scripts" / "process_1d.py"), str(pipe_path),
                             str(config_path), str(tmp_path / "result"), "--input-format", "nmrpipe"],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    report = json.loads((tmp_path / "result" / "report.json").read_text())
    assert report["input"]["format"] == "nmrpipe"
    assert sorted(p["ppm"] for p in report["peaks"]) == pytest.approx([3, 7], abs=0.001)
    areas = [r["area_signal_ppm"] for r in report["integrals"]]
    assert areas[1] / areas[0] == pytest.approx(2, rel=0.001)


def test_nmrpipe_frequency_domain_rejected(tmp_path):
    fid, config = example()
    pipe_path = tmp_path / "spectrum.ft1"
    write_synthetic_nmrpipe(pipe_path, fid, config, frequency_domain=True)
    with pytest.raises(ValueError, match="time-domain"):
        module.load_fid(pipe_path, config, "nmrpipe")


@pytest.mark.parametrize("key", ["spectral_width_hz", "observation_mhz", "carrier_ppm"])
def test_nmrpipe_header_mismatch_rejected(tmp_path, key):
    fid, config = example()
    pipe_path = tmp_path / "fid.pipe"
    write_synthetic_nmrpipe(pipe_path, fid, config)
    config[key] *= 1.1
    with pytest.raises(ValueError, match="disagrees"):
        module.load_fid(pipe_path, config, "nmrpipe")


@pytest.mark.parametrize("field,value,message", [
    ("FDF2TDSIZE", 4096, "FDF2TDSIZE"),
    ("FDF2TDSIZE", 16384, "FDF2TDSIZE"),
    ("FDF2CENTER", 4000, "centered axis"),
    ("FDF2ORIG", 100, "centered axis"),
])
def test_nmrpipe_preprocessed_or_inconsistent_axis_rejected(tmp_path, field, value, message):
    import nmrglue as ng
    fid, config = example()
    pipe_path = tmp_path / "fid.pipe"
    write_synthetic_nmrpipe(pipe_path, fid, config)
    header, data = ng.pipe.read(str(pipe_path))
    header[field] = value
    ng.pipe.write(str(pipe_path), header, data, overwrite=True)
    with pytest.raises(ValueError, match=message):
        module.load_fid(pipe_path, config, "nmrpipe")


@pytest.mark.parametrize("size,carrier", [(8191, 5.0), (8192, 4.998789)])
def test_nmrpipe_canonical_odd_length_and_float32_origin_rounding(tmp_path, size, carrier):
    fid, config = example()
    config["carrier_ppm"] = carrier
    path = tmp_path / "fid.pipe"
    write_synthetic_nmrpipe(path, fid[:size], config)
    decoded, _ = module.load_fid(path, config, "nmrpipe")
    np.testing.assert_array_equal(decoded, fid[:size].astype(np.complex64))


def test_empty_nmrpipe_rejected_before_axis_calculation(tmp_path):
    import nmrglue as ng
    fid, config = example()
    path = tmp_path / "fid.pipe"
    write_synthetic_nmrpipe(path, fid, config)
    header, _ = ng.pipe.read(str(path))
    header.update(FDSIZE=0, FDF2TDSIZE=0)
    ng.pipe.write(str(path), header, np.empty(0, dtype=np.complex64), overwrite=True)
    with pytest.raises(ValueError, match="at least 16"):
        module.load_fid(path, config, "nmrpipe")


def test_upstream_native_generated_nmrpipe_fixture():
    import hashlib
    pipe_path = Path(__file__).parent / "fixtures" / "nmrpipe_1d_time.fid"
    assert hashlib.sha256(pipe_path.read_bytes()).hexdigest() == "3f88650d2135a3e4bd57ef15e0a03ba16b5788ae343e44a5e8251a9dbaa23d64"
    _, config = example()
    config.update(spectral_width_hz=50000.0, observation_mhz=500.0,
                  carrier_ppm=99.0, nucleus="H1", zero_fill_points=16,
                  first_point_scale=1.0, line_broadening_hz=0.0,
                  integration_regions_ppm=[])
    fid, metadata = module.load_fid(pipe_path, config, "nmrpipe")
    np.testing.assert_array_equal(fid, np.r_[1-1j, 2-2j, np.zeros(14)])
    assert metadata["header"]["FDF2TDSIZE"] == 16
    result = module.process(fid, config)
    np.testing.assert_allclose(result["ppm"], 149.0 - np.arange(16) * 6.25)
    # Independent analytic transform of the two nonzero samples, in fftshift order.
    k = np.arange(-8, 8)
    expected = (1-1j) + (2-2j) * np.exp(-2j * np.pi * k / 16)
    np.testing.assert_allclose(result["real"], expected.real, atol=1e-14)
    np.testing.assert_allclose(result["imaginary"], expected.imag, atol=1e-14)


def test_first_order_phase_and_sloping_baseline_recovery():
    _, config = example()
    size = 512
    ppm = 10 - np.arange(size) * 10 / size
    target = np.exp(-((ppm - 3) / 0.1)**2) + 2 * np.exp(-((ppm - 7) / 0.1)**2)
    baseline = 0.2 * ppm - 0.7
    phase = np.deg2rad(25 - 80 * np.arange(size) / size)
    fid = np.fft.ifft(np.fft.ifftshift((target + baseline) * np.exp(-1j * phase)))
    config.update(zero_fill_points=size, first_point_scale=1.0, line_broadening_hz=0.0,
                  phase0_deg=25, phase1_deg=-80, baseline="linear",
                  baseline_regions_ppm=[[0.2, 0.8], [9.2, 9.8]])
    result = module.process(fid, config)
    np.testing.assert_allclose(result["real"], target, atol=2e-15)
    np.testing.assert_allclose(result["baseline"], baseline, atol=2e-15)
    np.testing.assert_allclose(result["imaginary"], 0, atol=2e-15)


def test_negative_areas_and_reversed_bounds_are_preserved():
    fid, config = example()
    expected = module.process(fid, config)
    config["integration_regions_ppm"] = [region[::-1] for region in config["integration_regions_ppm"]]
    actual = module.process(-fid, config)
    np.testing.assert_allclose([r["area_signal_ppm"] for r in actual["integrals"]],
                               [-r["area_signal_ppm"] for r in expected["integrals"]])
    assert actual["peaks"] == []
