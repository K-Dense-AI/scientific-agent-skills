"""JATS contributor roles using synthetic article metadata, without network calls."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "paper-lookup"
SCRIPT = SKILL_ROOT / "scripts" / "jats_to_text.py"
spec = importlib.util.spec_from_file_location("jats_authors", SCRIPT)
assert spec is not None and spec.loader is not None
jats = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jats)


def contributor(given: str, surname: str, role: str | None = "author") -> str:
    attribute = f' contrib-type="{role}"' if role is not None else ""
    return (
        f"<contrib{attribute}><name><surname>{surname}</surname>"
        f"<given-names>{given}</given-names></name></contrib>"
    )


def article(contributors: str, *, journal_contributors: str = "", body: bool = True) -> str:
    journal_group = (
        f"<contrib-group>{journal_contributors}</contrib-group>"
        if journal_contributors else ""
    )
    return (
        "<article><front><journal-meta><journal-title-group>"
        "<journal-title>Synthetic Journal</journal-title></journal-title-group>"
        f"{journal_group}</journal-meta>"
        "<article-meta><title-group><article-title>Synthetic study</article-title>"
        f"</title-group><contrib-group>{contributors}</contrib-group>"
        "</article-meta></front>"
        + ("<body><p>Synthetic research text.</p></body>" if body else "")
        + "</article>"
    )


@pytest.mark.parametrize("role", ["editor", "translator", "research-assistant"])
def test_explicit_non_author_contributors_are_not_authors(role):
    xml = article(
        contributor("First", "Author")
        + contributor("Other", "Contributor", role)
        + contributor("Last", "Author")
    )
    assert jats.extract_metadata(jats.parse(xml))["authors"] == [
        "First Author", "Last Author"
    ]


def test_untyped_article_contributors_keep_legacy_behavior():
    xml = article(contributor("Untyped", "Contributor", None))
    assert jats.extract_metadata(jats.parse(xml))["authors"] == ["Untyped Contributor"]


def test_journal_contributors_are_not_article_authors():
    xml = article(
        contributor("Article", "Author"),
        journal_contributors=contributor("Journal", "Contributor", None),
    )
    assert jats.extract_metadata(jats.parse(xml))["authors"] == ["Article Author"]


@pytest.mark.parametrize("wrapper", ["collab", "collab-wrap"])
@pytest.mark.parametrize("role", [None, "author"], ids=["untyped", "author"])
def test_nested_article_collaboration_contributors_remain_visible(wrapper, role):
    # JATS permits contributor groups inside both collaboration wrappers. The
    # second member cannot be found through the outer contributor's first-name
    # lookup, so it must still be visited as a contributor in its own right.
    group_name = (
        "Synthetic collaboration" if wrapper == "collab"
        else "<collab-name>Synthetic collaboration</collab-name>"
    )
    members = contributor("First", "Member", role) + contributor("Last", "Member", role)
    nested = (
        f'<contrib contrib-type="author"><{wrapper}>{group_name}'
        f"<contrib-group>{members}</contrib-group></{wrapper}></contrib>"
    )
    authors = jats.extract_metadata(jats.parse(article(nested)))["authors"]
    assert "First Member" in authors
    assert authors[-1] == "Last Member"


@pytest.mark.parametrize("wrapper", ["bare", "pmc-articleset"])
@pytest.mark.parametrize("body", [False, True])
def test_cli_reports_article_authors_without_changing_body_status(tmp_path, wrapper, body):
    xml = article(
        contributor("Article", "Author") + contributor("Article", "Editor", "editor"),
        journal_contributors=contributor("Journal", "Editor", "editor"),
        body=body,
    )
    if wrapper != "bare":
        xml = f"<{wrapper}>{xml}</{wrapper}>"
    path = tmp_path / "synthetic.xml"
    path.write_text(xml, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(path)],
        capture_output=True, text=True, timeout=10, check=False,
    )
    assert result.returncode == (0 if body else 2), result.stderr
    payload = json.loads(result.stdout)
    assert payload["metadata"]["authors"] == ["Article Author"]
    assert payload["metadata"]["title"] == "Synthetic study"
    assert payload["metadata"]["journal"] == "Synthetic Journal"
    assert payload["full_text_available"] is body
