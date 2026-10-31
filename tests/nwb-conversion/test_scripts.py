from pathlib import Path
import importlib.util
import json
import subprocess
import sys

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
    assert report["roundtrip"]["metadata_equal"]
    assert report["roundtrip"]["provenance_equal"]
    assert report["roundtrip"]["identity_unit_scaling"]
    assert report["converter_sha256"] == converter.digest(SKILL_ROOT / "scripts" / "convert_session.py")
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
    assert result["alignment"]["device_support_s"] == [0., .6]
    assert result["alignment"]["reference_support_s"] == [.05, .6506]
    np.testing.assert_allclose(result["alignment"]["pulse_residuals_s"], 0, atol=1e-12)


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


@pytest.mark.parametrize("rows", ["0,1,2,99\n1,3,4\n", "0,1\n1,3,4\n", "0,1,nan\n1,3,4\n"])
def test_csv_never_drops_extra_or_missing_coordinates(tmp_path, rows):
    path = tmp_path / "bad-position.csv"
    path.write_text("time_s,x,y\n" + rows)
    with pytest.raises(ValueError):
        converter.read_numeric_csv(path, ["time_s", "x", "y"])


@pytest.mark.parametrize("field,value", [("num_channels", 2), ("num_planes", 2), ("num_channels", True), ("num_planes", None)])
def test_reject_undeclared_or_interleaved_layout(session, tmp_path, field, value):
    config = json.loads(session.read_text())
    config["imaging"][field] = value
    session.write_text(json.dumps(config))
    with pytest.raises(ValueError, match=field):
        converter.convert(session, tmp_path / "invalid.nwb")
    assert not (tmp_path / "invalid.nwb").exists()


@pytest.mark.parametrize("axes", ["TCYX", "TZYX"])
def test_reject_tiff_metadata_that_contradicts_single_channel_plane(session, tmp_path, axes):
    images = np.arange(4 * 2 * 7 * 9, dtype="uint16").reshape(4, 2, 7, 9)
    tifffile.imwrite(tmp_path / "imaging.tif", images, photometric="minisblack", metadata={"axes": axes})
    with pytest.raises(ValueError, match="TIFF metadata"):
        converter.convert(session, tmp_path / "invalid.nwb")


@pytest.mark.parametrize("unit,value", [("m", 10.), ("mm", .01)])
def test_coordinate_units_and_birth_date_roundtrip(session, tmp_path, unit, value):
    config = json.loads(session.read_text())
    config["position_unit"] = unit
    config["subject"]["date_of_birth"] = "2019-10-03T12:00:00+00:00"
    session.write_text(json.dumps(config))
    report = converter.convert(session, tmp_path / "birth.nwb")
    assert report["schema_errors"] == []
    from pynwb import NWBHDF5IO
    with NWBHDF5IO(str(tmp_path / "birth.nwb"), "r") as io:
        nwb = io.read()
        assert nwb.subject.date_of_birth.isoformat() == config["subject"]["date_of_birth"]
        assert nwb.timestamps_reference_time == nwb.session_start_time
        assert nwb.processing["behavior"]["Position"]["Position"].data[0, 0] == value


@pytest.mark.parametrize("field,value", [("position_reference_frame", "  "), ("position_description", ""), ("experimenter", "one name")])
def test_reject_missing_coordinate_metadata(session, tmp_path, field, value):
    config = json.loads(session.read_text())
    config[field] = value
    session.write_text(json.dumps(config))
    with pytest.raises(ValueError, match=field):
        converter.convert(session, tmp_path / "invalid.nwb")


def test_birth_date_requires_timezone(session, tmp_path):
    config = json.loads(session.read_text())
    config["subject"]["date_of_birth"] = "2019-10-03T12:00:00"
    session.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="date_of_birth needs an explicit timezone"):
        converter.convert(session, tmp_path / "invalid.nwb")


def test_clock_fit_centers_large_device_origin_and_rejects_extrapolation(tmp_path):
    (tmp_path / "sync.csv").write_text("device_time_s,reference_time_s\n1000000000,10\n1000000005,15.005\n1000000010,20.010\n")
    sync = {"pulse_pairs_csv": "sync.csv", "max_residual_s": 1e-10}
    aligned, report = converter.align_behavior(np.array([1e9, 1e9 + 2, 1e9 + 10]), sync, tmp_path)
    np.testing.assert_allclose(aligned, [10, 12.002, 20.010], atol=1e-12, rtol=0)
    assert report["slope"] == pytest.approx(1.001)
    with pytest.raises(ValueError, match="extrapolation"):
        converter.align_behavior(np.array([1e9 - 1, 1e9]), sync, tmp_path)


@pytest.mark.parametrize("times", [[0., 0.], [1., 0.], [0., float("nan")]])
def test_align_rejects_invalid_direct_timestamp_arrays(tmp_path, times):
    with pytest.raises(ValueError, match="finite and strictly increasing"):
        converter.align_behavior(times, {"shared_clock_evidence": "synthetic"}, tmp_path)


def test_validation_report_is_never_overwritten(session, tmp_path):
    report_path = tmp_path / "output.validation.json"
    report_path.write_text("existing evidence")
    with pytest.raises(FileExistsError):
        converter.convert(session, tmp_path / "output.nwb")
    assert report_path.read_text() == "existing evidence"
    assert not (tmp_path / "output.nwb").exists()
    with pytest.raises(ValueError, match="extension"):
        converter.convert(session, tmp_path / "output.json")


def test_cli_reports_inspector_review_flag(session, tmp_path):
    output = tmp_path / "cli.nwb"
    result = subprocess.run([sys.executable, str(SKILL_ROOT / "scripts" / "convert_session.py"),
                             str(session), "--output", str(output)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["inspector_requires_review"] is True
    assert summary["roundtrip"]["all_frames_equal"] is True
    report = json.loads(output.with_suffix(".validation.json").read_text())
    orientation = [f for f in report["inspector_findings"] if f["check"] == "check_data_orientation"]
    assert orientation and "review_evidence" in orientation[0]
