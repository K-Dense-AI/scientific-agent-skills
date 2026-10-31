"""Small FCS fixtures verify the documented reader/writer interpretation."""

import io
import re
import struct
import sys
from pathlib import Path

import pytest

flowio = pytest.importorskip("flowio")
np = pytest.importorskip("numpy")

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "flowio"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))


def fcs_bytes(values, labels, *, datatype="I", version="3.1", extra=None, nextdata=0):
    """Independent fixed-offset fixture; deliberately bypass the upstream writer."""
    bits, code = {"I": (16, "H"), "D": (64, "d"), "F": (32, "f")}[datatype]
    data = struct.pack("<" + code * len(values), *values)
    metadata = {
        "BEGINANALYSIS": "0", "ENDANALYSIS": "0", "BEGINDATA": "00000000",
        "ENDDATA": "00000000", "BYTEORD": "1,2,3,4", "DATATYPE": datatype,
        "MODE": "L", "NEXTDATA": f"{nextdata:08d}", "PAR": str(len(labels)),
        "TOT": str(len(values) // len(labels)),
    }
    for i, label in enumerate(labels, 1):
        metadata.update({f"P{i}B": str(bits), f"P{i}N": label, f"P{i}E": "0,0",
                         f"P{i}R": "65536", f"P{i}G": "1"})
    metadata.update(extra or {})

    def text_segment():
        return ("/" + "".join(f"${key}/{value}/" for key, value in metadata.items())).encode()

    start = 256 + len(text_segment())
    stop = start + len(data) - 1
    metadata.update(BEGINDATA=f"{start:08d}", ENDDATA=f"{stop:08d}")
    header = f"FCS{version}    " + "".join(f"{value:8d}" for value in (256, start - 1, start, stop, 0, 0))
    return header.encode().ljust(256, b" ") + text_segment() + data


@pytest.mark.parametrize("version", ["2.0", "3.0", "3.1"])
def test_integer_decoding_and_preprocessing_are_distinct(version):
    raw = fcs_bytes([65535, 512, 10], ["FSC-A", "FL1-A", "Time"], version=version,
                    extra={"P1R": "1024", "P1G": "2", "P2R": "1024",
                           "P2E": "2,0", "P3G": "10", "TIMESTEP": "0.5"})
    flow = flowio.FlowData(io.BytesIO(raw))
    # Range masking already removes upper integer bits; zero log intercept -> 1.
    np.testing.assert_array_equal(flow.as_array(False), [[1023, 512, 10]])
    np.testing.assert_allclose(flow.as_array(True), [[511.5, 10, 5]])
    assert flow.channels[3]["png"] == 1.0
    assert flow.text["p3g"] == "10"


def test_multiple_datasets_from_path_and_handle_closure(tmp_path):
    first = fcs_bytes([10, 20], ["FSC-A", "FL1-A"])
    first = fcs_bytes([10, 20], ["FSC-A", "FL1-A"], nextdata=len(first))
    second = fcs_bytes([30, 40], ["FSC-A", "FL1-A"])
    path = tmp_path / "legacy.lmd"
    path.write_bytes(first + second)
    datasets = flowio.read_multiple_data_sets(path)
    assert len(datasets) == 2
    np.testing.assert_array_equal(datasets[1].as_array(False), [[30, 40]])
    handle = io.BytesIO(first + second)
    with pytest.raises(ValueError, match="closed"):
        flowio.read_multiple_data_sets(handle)
    assert handle.closed


def test_null_time_keeps_column_but_disables_time_classification():
    flow = flowio.FlowData(io.BytesIO(fcs_bytes([10], ["Time"],
        extra={"P1G": "2", "TIMESTEP": "0.5"})), null_channel_list=["Time", "missing"])
    assert flow.time_index is None
    assert flow.null_channels == ["Time", "missing"]
    np.testing.assert_array_equal(flow.as_array(), [[5]])  # gain only, no timestep


def test_nonfloat_rewrite_preserves_scaled_values(tmp_path):
    flow = flowio.FlowData(io.BytesIO(fcs_bytes([20, 10], ["FL1-A", "Time"],
        extra={"P1G": "2", "TIMESTEP": "0.5"})))
    output = tmp_path / "converted.fcs"
    flow.write_fcs(output)
    reopened = flowio.FlowData(output)
    assert reopened.data_type == "F"
    np.testing.assert_allclose(reopened.as_array(), [[10, 5]])
    assert "timestep" not in reopened.text


def test_float_rewrite_drops_gain_and_timestep_unless_explicit(tmp_path):
    flow = flowio.FlowData(io.BytesIO(fcs_bytes([20, 10], ["FL1-A", "Time"],
        datatype="F", extra={"P1G": "2", "TIMESTEP": "0.5"})))
    output = tmp_path / "copy.fcs"
    flow.write_fcs(output)
    reopened = flowio.FlowData(output)
    np.testing.assert_array_equal(reopened.as_array(False), flow.as_array(False))
    np.testing.assert_array_equal(reopened.as_array(), [[20, 10]])
    np.testing.assert_array_equal(flow.as_array(), [[10, 5]])


def test_writer_metadata_normalization_and_selected_defaults(tmp_path):
    path = tmp_path / "created.fcs"
    with path.open("xb") as handle:
        flowio.create_fcs(handle, [1, 2], ["A", "B"], opt_channel_names=["CD3", None],
                         metadata_dict={"$DATE": "30-SEP-2026", "CYT": "Synthetic",
                                        "custom": "a$b", "spill": "2,A,B,1,0,0,1"})
    flow = flowio.FlowData(path)
    assert flow.text["date"] == "30-SEP-2026"
    assert flow.text["custom"] == "ab"
    assert flow.pns_labels == ["CD3", ""]
    assert flow.analysis == {}
    copy = tmp_path / "selected.fcs"
    flow.write_fcs(copy)
    selected = flowio.FlowData(copy)
    assert "spillover" in selected.text and "custom" not in selected.text
    minimized = tmp_path / "minimal.fcs"
    flow.write_fcs(minimized, metadata={})
    assert "date" not in flowio.FlowData(minimized).text


def test_double_data_has_usable_finite_mean(tmp_path):
    # Exercise a real $DATATYPE=D input through the complete inspector CLI.
    import inspect_fcs
    path = tmp_path / "double.fcs"
    path.write_bytes(fcs_bytes([1e308, 1e308], ["FL1-A"], datatype="D"))
    output = tmp_path / "stats.json"
    assert inspect_fcs.main([str(path), "--stats", "--output", str(output)]) == 0
    import json
    stats = json.loads(output.read_text())["datasets"][0]["statistics"][0]
    assert stats["mean"] == 1e308


def test_off_by_one_and_header_discrepancy_recovery_are_explicit():
    raw = fcs_bytes([1, 2], ["A"], datatype="F")
    stop = int(raw[34:42])
    off_by_one = (raw[:34] + f"{stop + 1:8d}".encode() + raw[42:]).replace(
        f"$ENDDATA/{stop:08d}/".encode(), f"$ENDDATA/{stop + 1:08d}/".encode()
    )
    with pytest.raises(flowio.exceptions.FCSParsingError, match="off by 1"):
        flowio.FlowData(io.BytesIO(off_by_one))
    with pytest.warns(UserWarning, match="reviewed"):
        recovered = flowio.FlowData(io.BytesIO(off_by_one), ignore_offset_error=True)
    np.testing.assert_array_equal(recovered.as_array(False), [[1], [2]])

    bad_header = raw[:34] + f"{stop - 4:8d}".encode() + raw[42:]
    with pytest.raises(flowio.exceptions.DataOffsetDiscrepancyError):
        flowio.FlowData(io.BytesIO(bad_header))
    text_recovery = flowio.FlowData(io.BytesIO(bad_header), ignore_offset_discrepancy=True)
    np.testing.assert_array_equal(text_recovery.as_array(False), [[1], [2]])
    header_recovery = flowio.FlowData(io.BytesIO(bad_header), use_header_offsets=True)
    # Choosing HEADER truncates a row without checking $TOT: validate values/counts.
    assert header_recovery.as_array(False).shape == (1, 1)
    assert header_recovery.event_count == 2


def test_truncated_second_dataset_fails_cleanly(tmp_path):
    import inspect_fcs
    first = fcs_bytes([1], ["A"])
    first = fcs_bytes([1], ["A"], nextdata=len(first))
    second = fcs_bytes([2, 3, 4], ["A"])
    path = tmp_path / "truncated.lmd"
    path.write_bytes(first + second[:-2])
    assert inspect_fcs.main([str(path), "--stats"]) == 2


@pytest.mark.parametrize("heading", ["## 3. Build a DataFrame", "## 4. Export CSV Safely"])
def test_table_recipes_reject_inconsistent_counts_before_export(tmp_path, monkeypatch, heading):
    pytest.importorskip("pandas")
    monkeypatch.chdir(tmp_path)
    # The released reader returns three rows even though TEXT declares one.
    Path("sample.fcs").write_bytes(fcs_bytes([1, 2, 3], ["A"], extra={"TOT": "1"}))
    text = (SKILL_ROOT / "references/workflows.md").read_text()
    section = text.split(heading, 1)[1].split("\n## ", 1)[0]
    code = re.search(r"```python\n(.*?)```", section, re.S).group(1)
    with pytest.raises(ValueError, match="DATA shape disagrees"):
        exec(compile(code, "workflows.md", "exec"), {})
    assert not Path("sample.events.csv").exists()
    assert not Path("sample.events.json").exists()
