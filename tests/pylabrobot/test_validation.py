"""Fail closed for malformed input and unknown destination state."""
from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from unittest.mock import patch

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pylabrobot"
sys.path.insert(0, str(SKILL_ROOT))
from scripts import _common, inspect_backends

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def manifest():
    return json.loads((FIXTURES / "protocol_manifest.json").read_text())


@pytest.mark.parametrize("kind", [[], {}, None, True])
def test_nonstring_resource_kind_is_validation_error(kind):
    data = manifest()
    data["resources"][0]["kind"] = kind
    with pytest.raises(_common.ValidationError, match="kind"):
        _common.validate_manifest(data)


def test_unrepresentable_numeric_value_is_validation_error():
    data = manifest()
    data["deck"]["size_mm"]["x"] = 10 ** 1000
    with pytest.raises(_common.ValidationError, match="bounded"):
        _common.validate_manifest(data)


def test_overdeep_json_is_validation_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("deep.json").write_text('{"x":' + '[' * 2000 + '0' + ']' * 2000 + '}')
    with pytest.raises(_common.ValidationError, match="nesting"):
        _common.load_json("deep.json")


def test_unknown_destination_is_not_assumed_empty():
    data = manifest()
    data["resources"][1]["initial_volumes_uL"] = {}
    rows = _common.load_csv(str(FIXTURES.relative_to(Path.cwd()) / "transfers.csv"))
    with pytest.raises(_common.ValidationError, match="destination requires declared starting volume"):
        _common.plan_transfers(_common.validate_manifest(data), _common.validate_transfers(rows))


def test_declared_destination_volume_is_included_in_capacity_check():
    data = manifest()
    data["resources"][1]["initial_volumes_uL"]["A1"] = 350
    rows = _common.load_csv(str(FIXTURES.relative_to(Path.cwd()) / "transfers.csv"))
    with pytest.raises(_common.ValidationError, match="destination well capacity"):
        _common.plan_transfers(_common.validate_manifest(data), _common.validate_transfers(rows))


def test_strict_inspector_fails_if_package_absent():
    with patch.object(inspect_backends, "version", side_effect=PackageNotFoundError), redirect_stdout(io.StringIO()) as out:
        assert inspect_backends.main(["--strict"]) == 4
    assert json.loads(out.getvalue())["installed"] is False


def test_overlong_csv_field_is_validation_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("large.csv").write_text(",".join(_common.TRANSFER_HEADERS) + "\n" + "x" * 200000 + "\n")
    with pytest.raises(_common.ValidationError, match="CSV structure or field length"):
        _common.load_csv("large.csv")
