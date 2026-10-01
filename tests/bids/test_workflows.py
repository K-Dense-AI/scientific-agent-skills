"""Small real-library checks for the documented BIDS workflows; no scanner data."""
from pathlib import Path
import json
import re
import runpy

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "bids"


def test_pybids_inheritance_derivatives_and_explicit_cache_rebuild(tmp_path):
    bids = pytest.importorskip("bids")
    nib = pytest.importorskip("nibabel")
    np = pytest.importorskip("numpy")
    root = tmp_path / "raw"
    func = root / "sub-01" / "func"
    func.mkdir(parents=True)
    (root / "dataset_description.json").write_text(json.dumps({"Name": "Synthetic", "BIDSVersion": "1.11.2"}))
    (root / "task-rest_bold.json").write_text(json.dumps({"TaskName": "Eyes open rest", "RepetitionTime": 2.0}))
    image = func / "sub-01_task-rest_bold.nii.gz"
    nib.save(nib.Nifti1Image(np.zeros((2, 2, 2, 3), dtype=np.float32), np.eye(4)), image)
    (func / "sub-01_task-rest_bold.json").write_text(json.dumps({"EchoTime": 0.03}))
    cache = tmp_path / "cache"
    layout = bids.BIDSLayout(root, database_path=cache)
    assert layout.get_subjects() == ["01"]
    assert layout.get(suffix="bold", extension=".nii.gz", return_type="filename") == [str(image)]
    assert layout.get_metadata(str(image))["RepetitionTime"] == 2.0
    assert layout.get_metadata(str(image))["EchoTime"] == 0.03
    assert layout.build_path({"subject": "01", "session": "pre", "task": "rest", "suffix": "bold", "datatype": "func", "extension": ".nii.gz"}).endswith("sub-01/ses-pre/func/sub-01_ses-pre_task-rest_bold.nii.gz")
    second = func / "sub-01_task-rest_run-2_bold.nii.gz"
    nib.save(nib.load(image), second)
    stale = bids.BIDSLayout(root, database_path=cache)
    assert len(stale.get(suffix="bold", extension=".nii.gz")) == 1
    rebuilt = bids.BIDSLayout(root, database_path=cache, reset_database=True)
    assert len(rebuilt.get(suffix="bold", extension=".nii.gz")) == 2
    assert len(rebuilt.to_df().query("subject == '01'")) >= 2
    derivative = root / "derivatives" / "example"
    target = derivative / "sub-01" / "func"
    target.mkdir(parents=True)
    (derivative / "dataset_description.json").write_text(json.dumps({"Name": "example", "BIDSVersion": "1.11.2", "DatasetType": "derivative", "GeneratedBy": [{"Name": "example", "Version": "1"}]}))
    (target / "sub-01_task-rest_desc-confounds_timeseries.tsv").write_text("framewise_displacement\n0\n")
    both = bids.BIDSLayout(root, derivatives=[derivative])
    assert len(both.get(subject="01", desc="confounds", suffix="timeseries", extension=".tsv")) == 1


def test_documented_heudiconv_heuristic_uses_real_seqinfo_fields(tmp_path):
    pytest.importorskip("heudiconv")
    from heudiconv.utils import SeqInfo
    text = (SKILL_ROOT / "references" / "conversion_tools.md").read_text()
    code = re.findall(r"```python\n(.*?)```", text, re.S)[0]
    script = tmp_path / "heuristic.py"
    script.write_text(code)
    heuristic = runpy.run_path(str(script))
    values = {field: None for field in SeqInfo._fields}
    values.update(protocol_name="fieldmap", series_description="phase", image_type=("ORIGINAL", "PRIMARY", "P"), series_id="phase1", dim3=64, dim4=1)
    mapping = heuristic["infotodict"]([SeqInfo(**values)])
    matches = [key for key, series in mapping.items() if series]
    assert len(matches) == 1
    assert matches[0][0].endswith("_phasediff")
    for session in ("", "ses-pre"):
        prefix = "sub-01" + ("_" + session if session else "")
        path = matches[0][0].format(bids_subject_session_dir="sub-01" + ("/" + session if session else ""), bids_subject_session_prefix=prefix, item=1)
        assert "__" not in path
        assert "run-01_phasediff" in path


def test_dcm2bids_description_ids_resolve_intendedfor(tmp_path):
    pytest.importorskip("dcm2bids")
    from dcm2bids.acquisition import Acquisition
    from dcm2bids.participant import Participant
    from dcm2bids.sidecar import Sidecar
    text = (SKILL_ROOT / "references" / "conversion_tools.md").read_text()
    config = json.loads(re.findall(r"```json\n(.*?)```", text, re.S)[0])
    fieldmap = next(x for x in config["descriptions"] if x["suffix"] == "phasediff")
    source = tmp_path / "fieldmap.json"
    source.write_text(json.dumps({"EchoTime1": 0.00492, "EchoTime2": 0.00738}))
    acquisition = Acquisition(Participant("01"), src_sidecar=Sidecar(str(source)), bids_uri="URI", **fieldmap)
    refs = {"id_bold_rest": ["sub-01/func/sub-01_task-rest_bold.nii.gz"], "id_bold_nback": ["sub-01/func/sub-01_task-nback_bold.nii.gz"]}
    data = acquisition.dstSidecarData(refs)
    assert set(data["IntendedFor"]) == {"bids::" + x for paths in refs.values() for x in paths}
    assert all("{subject}" not in path for path in data["IntendedFor"])
