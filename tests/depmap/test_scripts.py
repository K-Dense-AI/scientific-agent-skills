"""DepMap catalogue and scientific data-contract regression tests."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")
pytest.importorskip("scipy")

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "depmap"
spec = importlib.util.spec_from_file_location("depmap_data", SKILL_ROOT / "scripts" / "depmap_data.py")
depmap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(depmap)


def test_catalogue_accepts_row_specific_missing_urls():
    response = MagicMock(headers={"Content-Type": "text/csv"})
    response.read.return_value = (
        "release,release_date,filename,url,md5_hash\n"
        "DepMap Public 26Q1,2026-04-01,Model.csv,,abc\n"
        "DepMap Public 24Q4,2024-12-16,Model.csv,https://example.org/data,def\n"
    ).encode()
    response.__enter__.return_value = response
    with patch.object(depmap, "urlopen", return_value=response) as get:
        table = depmap.fetch_catalogue()
    get.assert_called_once_with(depmap.CATALOGUE_URL, timeout=60)
    assert depmap.select_file(table, "DepMap Public 26Q1", "Model.csv")["url"] == ""
    assert len(table) == 2


@pytest.mark.parametrize("content_type,body", [
    ("text/html", "verification page"),
    ("text/csv", " <!DOCTYPE html><html>Verification</html>"),
    ("text/csv", "wrong,header\na,b\n"),
])
def test_catalogue_rejects_html_and_schema_drift(content_type, body):
    response = MagicMock(headers={"Content-Type": content_type})
    response.read.return_value = body.encode()
    response.__enter__.return_value = response
    with patch.object(depmap, "urlopen", return_value=response), pytest.raises(ValueError):
        depmap.fetch_catalogue()


def test_catalogue_selection_does_not_choose_ambiguous_file():
    table = pd.DataFrame([{"release": "A", "filename": "Model.csv"}] * 2)
    with pytest.raises(ValueError, match="found 2"):
        depmap.select_file(table, "A", "Model.csv")
    with pytest.raises(ValueError, match="found 0"):
        depmap.select_file(table, "B", "Model.csv")


def test_md5_verifies_local_identity(tmp_path):
    path = tmp_path / "download.csv"
    path.write_bytes(b"abc")
    assert depmap.verify_md5(path, "900150983cd24fb0d6963f7d28e17f72") == "900150983cd24fb0d6963f7d28e17f72"
    with pytest.raises(ValueError, match="mismatch"):
        depmap.verify_md5(path, "0" * 32)
    with pytest.raises(ValueError, match="valid published"):
        depmap.verify_md5(path, "")


def test_gene_labels_preserve_colliding_symbols(tmp_path):
    path = tmp_path / "effects.csv"
    path.write_text("ModelID,GENE (1),GENE (2)\nACH-000001,-1,0\nACH-000002,,-0.5\n")
    effect = depmap.load_gene_effect(path)
    assert list(effect.columns) == ["GENE (1)", "GENE (2)"]
    assert pd.isna(effect.iloc[1, 0])
    assert depmap.gene_column(effect, "2") == "GENE (2)"
    with pytest.raises(ValueError, match="2 columns"):
        depmap.gene_column(effect, "GENE")


@pytest.mark.parametrize("contents", [
    "ModelID,G (1),G (1)\nACH-000001,0,1\n",
    "ModelID,G (1)\nACH-000001,0\nACH-000001,1\n",
    "ScreenID,G (1)\nSC-000001.AV01,0\n",
    "ModelID,G (1)\nACH-000001,inf\n",
    "ModelID,G (1)\nACH-000001,not-a-score\n",
    "ModelID,G\nACH-000001,0\n",
])
def test_matrix_refuses_silent_identifier_or_numeric_corruption(tmp_path, contents):
    path = tmp_path / "effects.csv"
    path.write_text(contents)
    with pytest.raises(ValueError):
        depmap.load_gene_effect(path)


def test_models_and_profile_join_preserve_observed_denominator(tmp_path):
    path = tmp_path / "Model.csv"
    path.write_text("ModelID,CellLineName,OncotreeLineage,OncotreePrimaryDisease\n"
                    "ACH-000001,A,Lung,Adenocarcinoma\nACH-000002,B,Skin,Melanoma\nACH-000003,C,Lung,Adenocarcinoma\n")
    models = depmap.load_models(path)
    effects = pd.DataFrame({"KRAS (3845)": [-0.7, np.nan]}, index=["ACH-000001", "ACH-000002"])
    profile = depmap.gene_profile(effects, models, "KRAS")
    assert list(profile.index) == ["ACH-000001"]
    assert profile.iloc[0]["CellLineName"] == "A"
    with pytest.raises(ValueError, match="lack"):
        depmap.gene_profile(effects, models.drop("ACH-000002"), "KRAS")


def test_default_rows_exclude_repeated_conditions_and_missing_flags():
    raw = pd.DataFrame({"ModelID": ["A", "A", "B", "B", "C"],
                        "IsDefaultEntryForModel": ["Yes", "No", "true", "false", None],
                        "SequencingID": ["s1", "s2", "s3", "s4", "s5"]})
    selected = depmap.default_model_rows(raw)
    assert selected["SequencingID"].to_dict() == {"A": "s1", "B": "s3"}
    raw.loc[1, "IsDefaultEntryForModel"] = "Yes"
    with pytest.raises(ValueError):
        depmap.default_model_rows(raw)
    raw.loc[1, "IsDefaultEntryForModel"] = "sometimes"
    with pytest.raises(ValueError, match="Unrecognized"):
        depmap.default_model_rows(raw)


def test_biomarker_missing_is_never_assayed_negative():
    effects = pd.DataFrame({"TARGET (1)": [-1.0, -1.2, 0, 0.2, -100, -200],
                            "OTHER (2)": [0, 0.1, -1, -1.1, -100, -200]})
    status = pd.Series([1, 1, 0, 0, np.nan, np.nan])
    result = depmap.biomarker_scan(effects, status, min_n=2).set_index("gene")
    assert len(result) == 2  # All eligible genes, not just selected candidates.
    target = result.loc["TARGET (1)"]
    assert target["n_mutated"] == target["n_assayed_negative"] == 2
    assert target["mean_assayed_negative"] == pytest.approx(0.1)
    assert target["effect_size"] == pytest.approx(1.2)
    assert target["pval"] == pytest.approx(1 / 6)
    assert target["qval"] == pytest.approx(1 / 3)
    assert result.loc["OTHER (2)", "qval"] == 1


def test_biomarker_empty_family_and_invalid_calls():
    effects = pd.DataFrame({"G (1)": [-1, np.nan, 0, 0.1]})
    assert depmap.biomarker_scan(effects, pd.Series([1, 1, 0, 0]), min_n=2).empty
    with pytest.raises(ValueError, match="0, 1"):
        depmap.biomarker_scan(effects, pd.Series([1, 2, 0, 0]), min_n=2)
    with pytest.raises(ValueError, match="unique"):
        depmap.biomarker_scan(effects, pd.Series([1, 0], index=[0, 0]), min_n=2)


def test_coessentiality_reports_pairwise_n_and_excludes_constant_sparse_genes():
    effects = pd.DataFrame({"T (1)": [0, 1, 2, 3, 4, 5],
                            "POS (2)": [0, 1, 2, 3, np.nan, np.nan],
                            "NEG (3)": [5, 4, 3, 2, 1, 0],
                            "CONSTANT (4)": [1] * 6,
                            "SPARSE (5)": [0, 1, np.nan, np.nan, np.nan, np.nan]})
    result = depmap.coessentiality(effects, "T", min_n=4).set_index("gene")
    assert list(result.index) == ["POS (2)", "NEG (3)"]
    assert result.loc["POS (2)", "n"] == 4
    assert result.loc["NEG (3)", "r"] == pytest.approx(-1)
    assert depmap.coessentiality(effects, "T", min_n=500).empty
