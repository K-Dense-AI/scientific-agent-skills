from pathlib import Path
import importlib.util
import json

import pytest
import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "nwb-conversion"
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)
np = pytest.importorskip("numpy")
tifffile = pytest.importorskip("tifffile")
pytest.importorskip("neuroconv")
pytest.importorskip("nwbinspector")
spec = importlib.util.spec_from_file_location("convert_session", SKILL_ROOT / "scripts" / "convert_session.py")
converter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(converter)


@pytest.fixture
def session(tmp_path):
    images = np.arange(8 * 7 * 9, dtype="uint16").reshape(8, 7, 9)
    tifffile.imwrite(tmp_path / "imaging.tif", images, photometric="minisblack")
    times = [0, .1, .2, .31, .4, .5, .6, .7]
    (tmp_path / "frames.csv").write_text("time_s\n" + "\n".join(map(str, times)) + "\n")
    (tmp_path / "position.csv").write_text("time_s,x,y\n0,10,20\n0.2,11,21\n0.4,12,22\n0.6,13,23\n")
    config = json.loads((SKILL_ROOT / "assets" / "session-template.json").read_text())
    path = tmp_path / "session.json"
    path.write_text(json.dumps(config))
    return path


def test_real_tiff_csv_roundtrip_and_schema(session, tmp_path):
    report = converter.convert(session, tmp_path / "session.nwb")
    assert report["schema_errors"] == []
    assert report["roundtrip"]["frame_count"] == 8
    assert report["roundtrip"]["all_frames_equal"]
    assert isinstance(report["inspector_findings"], list)
    from pynwb import NWBHDF5IO
    with NWBHDF5IO(str(tmp_path / "session.nwb"), "r") as io:
        nwb = io.read()
        assert nwb.acquisition["Imaging"].data.shape == (8, 9, 7)
        assert nwb.acquisition["Imaging"].imaging_plane.location == "synthetic test plane"
        np.testing.assert_allclose(nwb.processing["behavior"]["Position"]["Position"].data[0], [.1, .2])
    with pytest.raises(FileExistsError):
        converter.convert(session, tmp_path / "session.nwb")


def test_clock_drift_is_fit_from_pulse_evidence(session, tmp_path):
    (tmp_path / "pulses.csv").write_text("device_time_s,reference_time_s\n0,0.05\n0.3,0.3503\n0.6,0.6506\n")
    config = json.loads(session.read_text())
    config["synchronization"] = {"pulse_pairs_csv": "pulses.csv", "max_residual_s": .0001}
    session.write_text(json.dumps(config))
    result = converter.convert(session, tmp_path / "aligned.nwb")
    assert result["alignment"]["slope"] == pytest.approx(1.001)
    assert result["alignment"]["offset_s"] == pytest.approx(.05)
    assert result["alignment"]["max_residual_s"] < 1e-12


def test_reject_false_clock_mapping_and_unsorted_samples(tmp_path):
    (tmp_path / "pulses.csv").write_text("device_time_s,reference_time_s\n0,0\n1,1.2\n2,2\n")
    with pytest.raises(ValueError, match="Clock fit failed"):
        converter.align_behavior(np.array([0., 1.]), {"pulse_pairs_csv": "pulses.csv", "max_residual_s": .001}, tmp_path)
    with pytest.raises(ValueError, match="either"):
        converter.align_behavior(np.array([0., 1.]), {}, tmp_path)
    (tmp_path / "bad.csv").write_text("time_s\n0\n0\n")
    with pytest.raises(ValueError, match="strictly increasing"):
        converter.read_numeric_csv(tmp_path / "bad.csv", ["time_s"])


def test_reject_missing_frames_and_timezone(session, tmp_path):
    config = json.loads(session.read_text())
    config["session_start_time"] = "2020-01-01T12:00:00"
    session.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="timezone"):
        converter.convert(session, tmp_path / "bad.nwb")
    config["session_start_time"] += "+00:00"
    session.write_text(json.dumps(config))
    (tmp_path / "frames.csv").write_text("time_s\n0\n1\n")
    with pytest.raises(ValueError, match="one grayscale"):
        converter.convert(session, tmp_path / "bad.nwb")


def test_normal_length_stack_has_no_critical_inspector_findings(session, tmp_path):
    images = np.arange(16 * 7 * 9, dtype="uint16").reshape(16, 7, 9)
    tifffile.imwrite(tmp_path / "imaging.tif", images, photometric="minisblack")
    (tmp_path / "frames.csv").write_text("time_s\n" + "\n".join(str(i * .1) for i in range(16)) + "\n")
    report = converter.convert(session, tmp_path / "normal.nwb")
    assert report["schema_errors"] == []
    assert report["roundtrip"]["all_frames_equal"]
    assert report["inspector_requires_review"] is False


def test_reject_other_acquisition_modality(session, tmp_path):
    config = json.loads(session.read_text())
    config["imaging"]["modality"] = "widefield"
    session.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="two-photon"):
        converter.convert(session, tmp_path / "wrong-modality.nwb")
