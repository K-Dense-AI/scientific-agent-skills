"""Deduplication must only reserve identities of retained bibliography entries."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "citation-management"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from format_bibtex import BibTeXFormatter


def entry(key, doi=None, title="A paper"):
    fields = {"title": title}
    if doi is not None:
        fields["doi"] = doi
    return {"type": "article", "key": key, "fields": fields}


@pytest.mark.parametrize("later_doi", ["10.1234/second", "  10.1234/SECOND  "])
def test_rejected_key_does_not_reserve_its_doi(later_doi):
    first = entry("shared", "10.1234/first", "First paper")
    discarded = entry("shared", "10.1234/second", "Second paper")
    second = entry("other", later_doi, "Second paper")
    assert BibTeXFormatter().deduplicate_entries([first, discarded, second]) == [first, second]


@pytest.mark.parametrize("discarded_doi", [None, "", "   ", "10.1234/second"])
def test_duplicate_key_keeps_first_entry(discarded_doi):
    first = entry("shared", "10.1234/first")
    discarded = entry("shared", discarded_doi)
    assert BibTeXFormatter().deduplicate_entries([first, discarded]) == [first]


def test_missing_citation_key_is_still_rejected():
    with pytest.raises(KeyError, match="key"):
        BibTeXFormatter().deduplicate_entries([{"type": "article", "fields": {"doi": "10.1234/a"}}])


def test_duplicate_doi_does_not_reserve_rejected_key():
    first = entry("first", "10.1234/paper")
    duplicate = entry("second", "  10.1234/PAPER  ")
    other = entry("second", "10.1234/other")
    assert BibTeXFormatter().deduplicate_entries([first, duplicate, other]) == [first, other]


@pytest.mark.parametrize("doi", [None, "", "   "])
def test_entries_without_dois_remain_distinct(doi):
    entries = [entry("first", doi), entry("second", doi)]
    assert BibTeXFormatter().deduplicate_entries(entries) == entries


def test_distinct_papers_with_same_title_are_not_merged():
    entries = [entry("first", "10.1234/a"), entry("second", "10.1234/b")]
    assert BibTeXFormatter().deduplicate_entries(entries) == entries


@pytest.mark.parametrize("mode", ["stdout", "output", "in-place"])
def test_cli_retains_distinct_paper_after_key_collision(tmp_path, mode):
    formatter = BibTeXFormatter()
    entries = [
        entry("shared", "10.1234/first", "First paper"),
        entry("shared", "https://doi.org/10.1234/SECOND", "Second paper"),
        entry("other", "10.1234/second", "Second paper"),
    ]
    original = "\n\n".join(formatter.format_entry(item) for item in entries) + "\n"
    source = tmp_path / "input.bib"
    source.write_text(original, encoding="utf-8")
    destination = tmp_path / "output.bib"
    arguments = [sys.executable, str(SKILL_ROOT / "scripts" / "format_bibtex.py"), str(source), "--deduplicate"]
    if mode == "output":
        arguments += ["--output", str(destination)]
    elif mode == "in-place":
        arguments += ["--in-place"]
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    if mode == "stdout":
        destination.write_text(result.stdout, encoding="utf-8")
    elif mode == "in-place":
        destination = source
    retained = formatter.parse_bibtex_file(str(destination))
    assert [(item["key"], item["fields"]["doi"], item["fields"]["title"]) for item in retained] == [
        ("shared", "10.1234/first", "First paper"),
        ("other", "10.1234/second", "Second paper"),
    ]
    assert "Duplicate citation key found: shared" in result.stderr
    assert "Duplicate DOI found" not in result.stderr
    if mode != "in-place":
        assert source.read_text(encoding="utf-8") == original
