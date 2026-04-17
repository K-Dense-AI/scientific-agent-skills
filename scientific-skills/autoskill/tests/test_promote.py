from pathlib import Path

import pytest

from promote import promote, PromoteError, main as promote_main


def _stage_proposed_skill(proposed_root: Path, kind: str, name: str,
                          body: str = "---\nname: s\ndescription: d\n---\n# x") -> Path:
    skill_dir = proposed_root / kind / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(body)
    return skill_dir


def test_promotes_new_skill_into_skills_dir(tmp_path: Path):
    proposed = tmp_path / "_proposed" / "2026-04-17T09-00"
    _stage_proposed_skill(proposed, "new-skills", "zotero-pubmed-helper")
    skills_dir = tmp_path / "scientific-skills"
    skills_dir.mkdir()

    target = promote(proposed, skills_dir, "zotero-pubmed-helper")

    assert target == skills_dir / "zotero-pubmed-helper"
    assert (target / "SKILL.md").exists()
    assert not (proposed / "new-skills" / "zotero-pubmed-helper").exists()


def test_promotes_composition_recipe_into_skills_dir(tmp_path: Path):
    proposed = tmp_path / "_proposed" / "2026-04-17T09-00"
    _stage_proposed_skill(proposed, "composition-recipes", "lit-review-flow")
    skills_dir = tmp_path / "scientific-skills"
    skills_dir.mkdir()

    target = promote(proposed, skills_dir, "lit-review-flow")

    assert (target / "SKILL.md").exists()


def test_preserves_nested_files(tmp_path: Path):
    proposed = tmp_path / "_proposed" / "ts"
    skill = _stage_proposed_skill(proposed, "new-skills", "my-skill")
    (skill / "references").mkdir()
    (skill / "references" / "notes.md").write_text("note")
    skills_dir = tmp_path / "scientific-skills"
    skills_dir.mkdir()

    target = promote(proposed, skills_dir, "my-skill")

    assert (target / "references" / "notes.md").read_text() == "note"


def test_raises_when_proposed_skill_is_missing(tmp_path: Path):
    proposed = tmp_path / "_proposed" / "ts"
    proposed.mkdir(parents=True)
    skills_dir = tmp_path / "scientific-skills"
    skills_dir.mkdir()

    with pytest.raises(PromoteError, match="not found"):
        promote(proposed, skills_dir, "ghost")


def test_cli_promotes_successfully(tmp_path: Path, capsys):
    proposed = tmp_path / "_proposed" / "2026-04-17T09-00"
    _stage_proposed_skill(proposed, "new-skills", "my-new-skill")
    skills_dir = tmp_path / "scientific-skills"
    skills_dir.mkdir()

    rc = promote_main([
        "--proposed", str(proposed),
        "--skills-dir", str(skills_dir),
        "--name", "my-new-skill",
    ])

    assert rc == 0
    assert (skills_dir / "my-new-skill" / "SKILL.md").exists()
    out = capsys.readouterr().out + capsys.readouterr().err
    assert "my-new-skill" in (out or "")


def test_cli_returns_nonzero_with_friendly_error_on_promote_failure(tmp_path: Path, capsys):
    proposed = tmp_path / "_proposed" / "ts"
    proposed.mkdir(parents=True)
    skills_dir = tmp_path / "scientific-skills"
    skills_dir.mkdir()

    rc = promote_main([
        "--proposed", str(proposed),
        "--skills-dir", str(skills_dir),
        "--name", "ghost",
    ])

    assert rc != 0
    captured = capsys.readouterr()
    assert "ghost" in captured.err
    # Should be a friendly message, not a stacktrace.
    assert "Traceback" not in captured.err


def test_raises_when_target_already_exists(tmp_path: Path):
    proposed = tmp_path / "_proposed" / "ts"
    _stage_proposed_skill(proposed, "new-skills", "existing")
    skills_dir = tmp_path / "scientific-skills"
    skills_dir.mkdir()
    (skills_dir / "existing").mkdir()

    with pytest.raises(PromoteError, match="already exists"):
        promote(proposed, skills_dir, "existing")
