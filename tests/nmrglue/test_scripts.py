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
