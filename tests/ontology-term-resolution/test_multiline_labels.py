"""Quoted CSV/TSV label line breaks must not concatenate adjacent words."""

from __future__ import annotations

import csv
import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "ontology-term-resolution"
spec = importlib.util.spec_from_file_location(
    "multiline_validate_terms", SKILL_ROOT / "scripts" / "validate_terms.py"
)
assert spec is not None and spec.loader is not None
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def input_text(delimiter, *, header=True):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter=delimiter, lineterminator="\n")
    if header:
        writer.writerow(["id", "label"])
    writer.writerow(["TEST:1", "left\nventricle"])
    writer.writerow(["TEST:2", 'label with a comma, and "quotes"'])
    return stream.getvalue()


@pytest.mark.parametrize("delimiter", [",", "\t"])
@pytest.mark.parametrize("source", ["file", "stdin"])
def test_quoted_label_keeps_word_boundary(delimiter, source, tmp_path, monkeypatch):
    text = input_text(delimiter)
    if source == "stdin":
        monkeypatch.setattr(sys, "stdin", io.StringIO(text))
        path = "-"
    else:
        path = tmp_path / "metadata.txt"
        path.write_text(text, encoding="utf-8")
    args = validator.build_parser().parse_args(["--input", str(path)])
    assert validator.read_pairs(args) == [
        ("TEST:1", "left\nventricle"),
        ("TEST:2", 'label with a comma, and "quotes"'),
    ]


@pytest.mark.parametrize("delimiter", [",", "\t"])
def test_headerless_multiline_label(delimiter, monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO(input_text(delimiter, header=False)))
    args = validator.build_parser().parse_args(["--input", "-"])
    assert validator.read_pairs(args)[0] == ("TEST:1", "left\nventricle")


@pytest.mark.parametrize("actual_label, expected_code, expected_status", [
    ("left ventricle", 0, "ok"),
    ("different label", 1, "label_mismatch"),
])
def test_validation_gate_handles_multiline_label(
    actual_label, expected_code, expected_status, monkeypatch, capsys
):
    monkeypatch.setattr(sys, "stdin", io.StringIO('id,label\nTEST:1,"left\nventricle"\n'))
    monkeypatch.setattr(validator, "term_detail", lambda _: {
        "label": actual_label, "ontology_name": "test", "is_defining_ontology": True,
        "is_obsolete": False, "type": "class",
    })
    assert validator.main(["--input", "-", "--format", "json"]) == expected_code
    assert json.loads(capsys.readouterr().out)[0]["status"] == expected_status
