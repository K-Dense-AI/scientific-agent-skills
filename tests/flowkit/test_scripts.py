"""Known-population cytometry tests, including an actual synthetic FlowJo export."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest
import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "flowkit"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import analyze_gates

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

fk = pytest.importorskip("flowkit")
flowio = pytest.importorskip("flowio")
np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")


def write_sample(path, sample_id=None):
    # Exactly four events in Cells; three of those in Positive after compensation.
    truth = np.array([[-10, 0], [10, 20], [100, 10], [200, 50], [500, 100], [800, 200]])
    spill = np.array([[1.0, 0.1], [0.2, 1.0]])
    events = np.column_stack(([10, 100, 150, 200, 250, 500], truth @ spill))
    with path.open("wb") as handle:
        flowio.create_fcs(
            handle, events.ravel(), ["FSC-A", "FL1-A", "FL2-A"],
            metadata_dict={"fil": sample_id or path.name},
        )
    return path


def strategy():
    result = fk.GatingStrategy()
    result.add_comp_matrix("spill", fk.Matrix(
        np.array([[1, .1], [.2, 1]]), ["FL1-A", "FL2-A"], fluorochromes=["FITC", "PE"]
    ))
    transform = fk.transforms.LogicleTransform(262144, .5, 4.5, 0)
    result.add_transform("logicle", transform)
    result.add_gate(fk.gates.RectangleGate("Cells", [
        fk.Dimension("FSC-A", range_min=50, range_max=300)
    ]), ("root",))
    lo, hi = transform.apply(np.array([50.0, 600.0]))
    result.add_gate(fk.gates.RectangleGate("Positive", [
        fk.Dimension("FL1-A", compensation_ref="spill", transformation_ref="logicle",
                     range_min=float(lo), range_max=float(hi))
    ]), ("root", "Cells"))
    return result


@pytest.fixture
def inputs(tmp_path):
    sample = write_sample(tmp_path / "sample.fcs")
    xml = tmp_path / "gates.xml"
    with xml.open("wb") as handle:
        fk.export_gatingml(strategy(), handle)
    return sample, xml


def run_analysis(tmp_path, inputs, **overrides):
    sample, xml = inputs
    options = dict(fcs_paths=[sample], definition=xml, mode="gatingml", output_dir=tmp_path / "out")
    options.update(overrides)
    manifest = analyze_gates.analyze(**options)
    return manifest, pd.read_csv(options["output_dir"] / "gate_report.csv")


def test_compensation_transform_hierarchy_and_denominators(tmp_path, inputs):
    manifest, report = run_analysis(tmp_path, inputs)
    rows = report.set_index("gate_name")
    assert rows.loc["Cells", "count"] == 4
    assert rows.loc["Positive", "count"] == 3
    assert rows.loc["Positive", "absolute_percent"] == pytest.approx(50)
    assert rows.loc["Positive", "relative_percent"] == pytest.approx(75)
    assert json.loads(rows.loc["Positive", "gate_path"]) == ["root", "Cells"]
    assert manifest["samples"][0]["event_count"] == 6
    assert manifest["samples"][0]["sha256"] == hashlib.sha256(inputs[0].read_bytes()).hexdigest()
    assert manifest["definition"]["sha256"] == hashlib.sha256(inputs[1].read_bytes()).hexdigest()
    assert json.loads((tmp_path / "out" / "provenance.json").read_text()) == manifest


def test_membership_keeps_event_order_and_matches_report(inputs):
    sample = fk.Sample(inputs[0])
    session = fk.Session(strategy(), [sample])
    session.analyze_samples(use_mp=False)
    mask = session.get_gate_membership(sample.id, "Positive", ("root", "Cells"))
    np.testing.assert_array_equal(mask, [False, False, True, True, True, False])
    parent = session.get_gate_membership(sample.id, "Cells", ("root",))
    assert np.all(~mask | parent)
    sample.apply_compensation(session.get_comp_matrix("spill"))
    intensity = sample.get_channel_events("FL1-A", source="comp")[mask]
    assert np.median(intensity) == pytest.approx(200)
    assert sample.get_channel_events("FL1-A", source="comp")[0] == pytest.approx(-10)


def test_batch_reports_each_sample(tmp_path, inputs):
    second = write_sample(tmp_path / "second.fcs")
    manifest, report = run_analysis(tmp_path, inputs, fcs_paths=[inputs[0], second])
    assert set(report.sample_id) == {"sample.fcs", "second.fcs"}
    assert len(manifest["samples"]) == 2
    assert len(report) == 4


def test_duplicate_fil_rejected_instead_of_silent_sample_loss(tmp_path, inputs):
    duplicate = write_sample(tmp_path / "renamed.fcs", sample_id="sample.fcs")
    with pytest.raises(ValueError, match="Duplicate sample ID"):
        run_analysis(tmp_path, inputs, fcs_paths=[inputs[0], duplicate])
    assert not (tmp_path / "out").exists()
    _, report = run_analysis(tmp_path, inputs, fcs_paths=[inputs[0], duplicate], filename_as_id=True)
    assert set(report.sample_id) == {"sample.fcs", "renamed.fcs"}


def test_existing_output_is_preserved(tmp_path, inputs):
    destination = tmp_path / "out"
    destination.mkdir()
    sentinel = destination / "gate_report.csv"
    sentinel.write_text("previous results")
    with pytest.raises(FileExistsError):
        run_analysis(tmp_path, inputs)
    assert sentinel.read_text() == "previous results"


def test_empty_strategy_rejected(tmp_path, inputs):
    from lxml import etree
    tree = etree.parse(str(inputs[1]))
    root = tree.getroot()
    for element in list(root):
        if etree.QName(element).localname.endswith("Gate"):
            root.remove(element)
    tree.write(str(inputs[1]))
    with pytest.raises(ValueError, match="no gates"):
        run_analysis(tmp_path, inputs)


def test_imported_flowjo_polygon_has_known_50_events(tmp_path):
    sample = FIXTURES / "data_set_simple_line_100.fcs"
    wsp = FIXTURES / "simple_poly_and_rect_v2_poly50.wsp"
    _, report = run_analysis(tmp_path, (sample, wsp), mode="workspace", group="my_group")
    rows = report.set_index("gate_name")
    assert rows.loc["poly1", "count"] == 50
    assert rows.loc["poly1", "absolute_percent"] == pytest.approx(50)
    assert rows.loc["rect1", "count"] == 0


def test_missing_workspace_member_is_not_silently_dropped(tmp_path):
    sample = FIXTURES / "data_set_simple_line_100.fcs"
    text = (FIXTURES / "simple_poly_and_rect_v2_poly50.wsp").read_text()
    # A second expected sample has gating metadata but no supplied FCS.
    from lxml import etree
    root = etree.fromstring(text.encode())
    original = root.find("SampleList/Sample")
    import copy
    missing = copy.deepcopy(original)
    missing.find("DataSet").set("sampleID", "2")
    missing.find("SampleNode").set("sampleID", "2")
    missing.find("SampleNode").set("name", "missing.fcs")
    for keyword in missing.findall("Keywords/Keyword"):
        if keyword.get("name", "").lower() == "$fil":
            keyword.set("value", "missing.fcs")
    root.find("SampleList").append(missing)
    group = root.find("Groups/GroupNode[@name='my_group']/Group/SampleRefs")
    etree.SubElement(group, "SampleRef", sampleID="2")
    wsp = tmp_path / "incomplete.wsp"
    wsp.write_bytes(etree.tostring(root))
    with pytest.raises(ValueError, match="missing IDs=.*missing.fcs"):
        run_analysis(tmp_path, (sample, wsp), mode="workspace", group="my_group")
    assert not (tmp_path / "out").exists()


def test_unmatched_workspace_input_rejected(tmp_path, inputs):
    wsp = FIXTURES / "simple_poly_and_rect_v2_poly50.wsp"
    with pytest.raises(ValueError, match="unexpected IDs"):
        run_analysis(tmp_path, (inputs[0], wsp), mode="workspace", group="my_group")


def test_cli_writes_report(tmp_path, inputs):
    result = subprocess.run(
        [sys.executable, str(SKILL_ROOT / "scripts" / "analyze_gates.py"),
         "--gatingml", str(inputs[1]), "--fcs", str(inputs[0]),
         "--output-dir", str(tmp_path / "cli")],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "Analyzed 1 samples" in result.stdout
    assert len(pd.read_csv(tmp_path / "cli" / "gate_report.csv")) == 2


@pytest.mark.parametrize("filename", ["SKILL.md", "references/workspaces-and-results.md"])
def test_documented_python_workflows_run(tmp_path, filename):
    if filename == "SKILL.md":
        write_sample(tmp_path / "sample.fcs")
    else:
        shutil.copyfile(FIXTURES / "data_set_simple_line_100.fcs", tmp_path / "data_set_simple_line_100.fcs")
        shutil.copyfile(FIXTURES / "simple_poly_and_rect_v2_poly50.wsp", tmp_path / "study.wsp")
    code = re.findall(r"```python\n(.*?)```", (SKILL_ROOT / filename).read_text(), re.S)
    assert len(code) == 1
    script = tmp_path / "example.py"
    script.write_text(code[0])
    result = subprocess.run(
        [sys.executable, str(script)], cwd=tmp_path, capture_output=True, text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    if filename == "SKILL.md":
        _, report = run_analysis(tmp_path, (tmp_path / "sample.fcs", tmp_path / "gates.xml"))
        assert report.set_index("gate_name").loc["Positive", "count"] == 3
