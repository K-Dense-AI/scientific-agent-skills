"""An STL with no triangles must not pass the manufacturing pre-flight."""

from __future__ import annotations

import importlib.util
import json
import struct
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "fictiv"
SCRIPT = SKILL_ROOT / "scripts" / "check_cad_file.py"
spec = importlib.util.spec_from_file_location("empty_stl_checker", SCRIPT)
assert spec is not None and spec.loader is not None
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


@pytest.fixture(params=["ascii", "binary", "truncated_binary"])
def empty_stl(request, tmp_path):
    path = tmp_path / f"{request.param}.stl"
    if request.param == "ascii":
        path.write_text("solid empty\nendsolid empty\n", encoding="ascii")
    else:
        # A zero-count binary header, or a header declaring a missing facet.
        count = 0 if request.param == "binary" else 1
        path.write_bytes(b"\0" * 80 + struct.pack("<I", count))
    return path


def test_no_triangles_is_blocking(empty_stl):
    result = checker.check(str(empty_stl), "3dp")
    assert result["info"]["triangles"] == 0
    assert "no triangles found in STL" in result["blocking"]


@pytest.mark.parametrize("json_output", [False, True])
def test_cli_rejects_stl_without_triangles(empty_stl, json_output):
    args = [sys.executable, str(SCRIPT), str(empty_stl), "--process", "3dp"]
    if json_output:
        args.append("--json")
    result = subprocess.run(args, capture_output=True, text=True, timeout=10)
    assert result.returncode == 1, result.stderr
    if json_output:
        assert "no triangles found in STL" in json.loads(result.stdout)[0]["blocking"]
    else:
        assert "[BLOCKED]" in result.stdout
        assert "no triangles found in STL" in result.stdout


def test_skipped_large_mesh_inspection_is_not_treated_as_empty(monkeypatch, tmp_path):
    path = tmp_path / "large.stl"
    path.write_bytes(b"placeholder")
    monkeypatch.setattr(checker, "inspect_stl", lambda _: {
        "encoding": "binary", "triangles": 3_000_001,
        "note": "too many triangles to check watertightness quickly",
    })
    result = checker.check(str(path), "3dp")
    assert result["blocking"] == []
    assert "watertight" not in result["info"]
