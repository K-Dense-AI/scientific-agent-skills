from pathlib import Path

from match_skills import load_skill_descriptions, top_k_matches


SKILL_TEMPLATE = """---
name: {name}
description: {description}
---

# {name}
"""


def _write_skill(root: Path, name: str, description: str) -> None:
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(SKILL_TEMPLATE.format(name=name, description=description))


def test_load_skill_descriptions_reads_frontmatter(tmp_path: Path):
    _write_skill(tmp_path, "literature-review", "Systematic literature reviews across databases.")
    _write_skill(tmp_path, "latex-posters", "Create conference posters in LaTeX.")

    skills = load_skill_descriptions(tmp_path)
    by_name = {s["name"]: s for s in skills}

    assert set(by_name) == {"literature-review", "latex-posters"}
    assert by_name["literature-review"]["description"].startswith("Systematic literature reviews")


def test_load_skill_descriptions_skips_directories_without_skill_md(tmp_path: Path):
    _write_skill(tmp_path, "real-skill", "A real skill.")
    (tmp_path / "empty-dir").mkdir()

    skills = load_skill_descriptions(tmp_path)
    assert [s["name"] for s in skills] == ["real-skill"]


def _keyword_embedder(text: str):
    # deterministic, tiny vector indexed by known keywords
    keywords = ["paper", "poster", "molecule"]
    return [1.0 if k in text.lower() else 0.0 for k in keywords]


def test_top_k_matches_ranks_by_cosine_similarity():
    skills = [
        {"name": "literature-review", "description": "search and summarize papers"},
        {"name": "latex-posters", "description": "create academic posters"},
        {"name": "rdkit", "description": "molecule cheminformatics"},
    ]
    query = "I spent time reading papers"

    results = top_k_matches(query, skills, embedder=_keyword_embedder, k=2)

    assert len(results) == 2
    assert results[0]["name"] == "literature-review"
    assert results[0]["score"] > results[1]["score"]


def test_top_k_matches_returns_all_when_k_exceeds_skills():
    skills = [
        {"name": "a", "description": "paper work"},
        {"name": "b", "description": "poster work"},
    ]
    results = top_k_matches("paper", skills, embedder=_keyword_embedder, k=10)
    assert len(results) == 2


def test_top_k_matches_handles_zero_vectors_without_crashing():
    skills = [{"name": "a", "description": "unrelated text"}]
    results = top_k_matches("unrelated text query", skills,
                            embedder=lambda _: [0.0, 0.0, 0.0], k=1)
    assert len(results) == 1
    assert results[0]["score"] == 0.0
