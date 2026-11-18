"""`scan_skills.py` cache keys must not depend on the platform or the clock.

The security report is reused skill by skill when a skill's `content_hash` is
unchanged. That hash is committed to `docs/security-report.json` by CI (Linux),
so it must come out identical on Windows, where `str(Path)` uses backslashes.

`scan_skills` imports the scanner stack at module level. These helpers need
none of it, so the stack is stubbed and the test runs without those packages.
"""

import hashlib
import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scan_skills.py"


@pytest.fixture
def scan_skills(monkeypatch):
    for name in (
        "dotenv",
        "skill_scanner",
        "skill_scanner.core",
        "skill_scanner.core.analyzers",
        "skill_scanner.core.loader",
        "skill_scanner.core.models",
        "skill_scanner.core.scan_policy",
    ):
        monkeypatch.setitem(sys.modules, name, mock.MagicMock())
    spec = importlib.util.spec_from_file_location("scan_skills_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _skill(root: Path, body: str = "x") -> Path:
    skill = root / "demo"
    (skill / "references").mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: demo\n---\n", encoding="utf-8")
    (skill / "references" / "a.md").write_text(body, encoding="utf-8")
    return skill


def test_content_hash_uses_posix_relative_paths(scan_skills, tmp_path):
    skill = _skill(tmp_path)
    expected = hashlib.sha256()
    for rel, data in (("SKILL.md", b"---\nname: demo\n---\n"), ("references/a.md", b"x")):
        expected.update(rel.encode() + b"\0" + data + b"\0")
    assert scan_skills.content_hash(skill) == expected.hexdigest()


def test_content_hash_tracks_content_and_paths_but_not_pycache(scan_skills, tmp_path):
    base = scan_skills.content_hash(_skill(tmp_path / "one"))
    assert scan_skills.content_hash(_skill(tmp_path / "two")) == base
    assert scan_skills.content_hash(_skill(tmp_path / "three", body="y")) != base

    renamed = _skill(tmp_path / "four")
    (renamed / "references" / "a.md").rename(renamed / "references" / "b.md")
    assert scan_skills.content_hash(renamed) != base

    cached = _skill(tmp_path / "five")
    (cached / "__pycache__").mkdir()
    (cached / "__pycache__" / "m.pyc").write_bytes(b"\0")
    assert scan_skills.content_hash(cached) == base


def test_cache_invalidation_reasons(scan_skills, monkeypatch):
    monkeypatch.setattr(scan_skills, "scanner_version", lambda: "1.0")
    monkeypatch.setattr(scan_skills, "llm_model_id", lambda: "m")
    now = datetime.now(timezone.utc)

    def report(**run):
        return {"generated": now.isoformat(), "run": {"scanner_version": "1.0", "model": "m", **run}}

    reason = scan_skills.cache_invalidation_reason
    assert reason(None, 30) == "no previous report"
    assert reason(report(), 30) is None
    assert "scanner version changed" in reason(report(scanner_version="0.9"), 30)
    assert "model changed" in reason(report(model="other"), 30)
    old = (now - timedelta(days=31)).isoformat()
    assert "31 days ago" in reason(report(last_full_scan=old), 30)
    assert "unparseable" in reason(report(last_full_scan="not-a-date"), 30)
