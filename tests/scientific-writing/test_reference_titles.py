"""Unicode title regressions using synthetic, unverified source metadata."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "scientific-writing"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import check_references


def source_manifest(*titles: str) -> dict:
    return {
        "schema_version": "1.0",
        "sources": [
            {
                "evidence_id": f"E{index:03d}",
                "source_type": "other",
                "title": title,
                "authors": [],
                "year": None,
                "identifiers": {"url": f"https://example.invalid/source/{index}"},
                "locator": "Synthetic fixture",
                "confidentiality": "public",
                "verification": {"status": "unverified", "source_opened": False},
            }
            for index, title in enumerate(titles, start=1)
        ],
    }


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Α-Synuclein", "α synuclein"),
        ("细胞研究", "细胞研究"),
        ("БЕЛОК 2", "белок 2"),
        ("Protein_fold: 2026!", "protein fold 2026"),
    ],
)
def test_title_tokens_keep_unicode_alphanumerics(title, expected):
    assert check_references.normalize_title(title) == expected


@pytest.mark.parametrize(
    ("titles", "duplicate"),
    [
        (("α-synuclein aggregation", "β-synuclein aggregation"), False),
        (("细胞研究", "细胞研究"), True),
        (("细胞研究", "蛋白研究"), False),
        (("Α-Synuclein", "α synuclein"), True),
        (("कला", "कली"), False),
        (("が", "か"), False),
        (("عَلَم", "علم"), False),
        (("שָׁלוֹם", "שלום"), False),
        (("ก้", "ก๊"), False),
        (("কলা", "কলি"), False),
        (("கல்", "கலி"), False),
        (("ά", "α\u0301"), True),
        (("が", "か\u3099"), True),
        (("क़", "क\u093c"), True),
        (("café", "cafe\u0301"), True),
        (("각", "\u1100\u1161\u11a8"), True),
        (("a\u0301\u0327", "a\u0327\u0301"), True),
        # Accents remain data, not a script-specific fuzzy matching rule.
        (("café", "cafe"), False),
        (("résumé", "re sume"), False),
    ],
)
def test_unicode_title_duplicates(titles, duplicate):
    issues, count = check_references.check_sources(source_manifest(*titles))
    assert count == 2
    assert [item.code for item in issues] == (
        ["POSSIBLE_DUPLICATE_TITLE"] if duplicate else []
    )
    if duplicate:
        assert issues[0].location == "E001"
        assert issues[0].item_id == "E002"


@pytest.mark.parametrize(
    ("titles", "exit_code"),
    [
        (("α-synuclein aggregation", "β-synuclein aggregation"), 0),
        (("细胞研究", "细胞研究"), 1),
        (("कला", "कली"), 0),
        (("が", "か"), 0),
        (("ά", "α\u0301"), 1),
        (("café", "cafe"), 0),
    ],
)
def test_cli_title_check_exit_status(tmp_path, titles, exit_code):
    path = tmp_path / "sources.json"
    path.write_text(json.dumps(source_manifest(*titles)), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SKILL_ROOT / "scripts" / "check_references.py"), str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == exit_code, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == ("fail" if exit_code else "pass")
    assert report["summary"]["network_used"] is False
