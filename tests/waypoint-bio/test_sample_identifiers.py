"""Sample identifiers are labels, not numbers or pandas missing-value tokens."""
from pathlib import Path
import csv
import os
import subprocess
import sys

import pytest

pd = pytest.importorskip("pandas")
SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "waypoint-bio"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
import profiler_to_waypoint as converter
import vocab_coverage


@pytest.mark.parametrize("ids", [["001", "1", "1e3"], ["NA", "null", "NaN"], ["样本α", " sample ", "sample"]])
@pytest.mark.parametrize("suffix,separator", [(".csv", ","), (".tsv", "\t")])
def test_sample_rows_keep_exact_labels_and_numeric_missingness(tmp_path, ids, suffix, separator):
    path = tmp_path / ("matrix" + suffix)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter=separator)
        writer.writerow(["sample_id", "g__A", "g__B"])
        writer.writerows([[sample, 1, ""] for sample in ids])
    matrix = converter.parse_table(path, taxonomy_column=None, orientation="samples_as_rows")
    assert matrix.index.tolist() == ids
    assert matrix["g__A"].tolist() == [1, 1, 1]
    assert matrix["g__B"].tolist() == [0, 0, 0]
    assert converter.matrix_to_waypoint(matrix).index.tolist() == ids


def test_taxon_rows_preserve_numeric_and_missing_token_sample_headers(tmp_path):
    path = tmp_path / "matrix.tsv"
    path.write_text("taxonomy\t001\t1\t1e3\tNA\tnull\t样本\ng__A\t1\t2\t3\t4\t5\t6\n", encoding="utf-8")
    matrix = converter.parse_table(path, taxonomy_column=None, orientation="taxa_as_rows")
    assert matrix.index.tolist() == ["001", "1", "1e3", "NA", "null", "样本"]
    assert matrix["g__A"].tolist() == [1, 2, 3, 4, 5, 6]


@pytest.mark.parametrize("identifier", ["001", "1e3", "NA", "null", "样本", " sample "])
def test_metadata_join_matches_literal_identifiers(tmp_path, identifier):
    path = tmp_path / "labels.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sample_id", "Group", "measurement"])
        writer.writerow([identifier, "control", ""])
    frame = pd.DataFrame({"Taxa": [["g__A"]], "Relative Abundances": [[1.0]]}, index=[identifier])
    result = converter.attach_metadata(frame, path)
    assert result.index.tolist() == [identifier]
    assert result["Group"].tolist() == ["control"]
    assert result["measurement"].isna().all()


@pytest.mark.parametrize("ids", [["001", "1", "1e3"], ["NA", "null", "NaN"], ["样本α", " sample ", "sample"]])
def test_coverage_reader_preserves_exported_identifiers(tmp_path, ids):
    path = tmp_path / "dataset.csv"
    frame = pd.DataFrame({"Taxa": [["g__A"]] * len(ids), "Relative Abundances": [[1.0]] * len(ids)}, index=pd.Index(ids, name="sample_id"))
    frame.to_csv(path)
    assert vocab_coverage.load_dataframe(path).index.tolist() == ids


def test_true_duplicate_samples_are_still_rejected(tmp_path):
    path = tmp_path / "duplicate.tsv"
    path.write_text("sample_id\tg__A\n001\t1\n001\t2\n", encoding="utf-8")
    matrix = converter.parse_table(path, taxonomy_column=None, orientation="samples_as_rows")
    with pytest.raises(ValueError, match="sample IDs must be unique"):
        converter.matrix_to_waypoint(matrix)


def test_converter_cli_keeps_identifiers_and_metadata_through_coverage_read(tmp_path):
    matrix = tmp_path / "matrix.tsv"
    labels = tmp_path / "labels.csv"
    output = tmp_path / "out.csv"
    ids = ["001", "1", "1e3", "NA", "null", "样本"]
    matrix.write_text("sample_id\tg__A\tg__B\n" + "".join(f"{identifier}\t1\t3\n" for identifier in ids), encoding="utf-8")
    labels.write_text("sample_id,Group\n" + "".join(f"{identifier},group_{index}\n" for index, identifier in enumerate(ids)), encoding="utf-8")
    run = subprocess.run([sys.executable, str(SKILL_ROOT / "scripts" / "profiler_to_waypoint.py"), "--input", str(matrix), "--format", "generic", "--orientation", "samples_as_rows", "--metadata", str(labels), "--output", str(output)], capture_output=True, text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, timeout=30)
    assert run.returncode == 0, run.stderr
    assert "no metadata match" not in run.stderr
    result = vocab_coverage.load_dataframe(output)
    assert result.index.tolist() == ids
    assert result["Group"].tolist() == [f"group_{index}" for index in range(len(ids))]
    assert result["Relative Abundances"].tolist() == [[0.25, 0.75]] * len(ids)


def test_duplicate_metadata_identifiers_remain_an_error(tmp_path):
    path = tmp_path / "labels.csv"
    path.write_text("sample_id,Group\nNA,a\nNA,b\n", encoding="utf-8")
    with pytest.raises(ValueError, match="metadata sample IDs must be unique"):
        converter.attach_metadata(pd.DataFrame(index=["NA"]), path)


@pytest.mark.parametrize("missing", ["", "NA", "null"])
def test_abundance_missing_tokens_keep_existing_zero_semantics(tmp_path, missing):
    path = tmp_path / "matrix.tsv"
    path.write_text(f"sample_id\tg__A\tg__B\n001\t1\t{missing}\n", encoding="utf-8")
    matrix = converter.parse_table(path, taxonomy_column=None, orientation="samples_as_rows")
    assert matrix.loc["001"].tolist() == [1, 0]


def test_invalid_abundance_remains_an_error(tmp_path):
    path = tmp_path / "matrix.tsv"
    path.write_text("sample_id\tg__A\n001\tnot-a-count\n", encoding="utf-8")
    with pytest.raises(ValueError):
        converter.parse_table(path, taxonomy_column=None, orientation="samples_as_rows")
