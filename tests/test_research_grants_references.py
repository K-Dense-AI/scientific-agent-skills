import re
from pathlib import Path


def test_research_grants_markdown_references_exist():
    skill_dir = Path(__file__).resolve().parents[1] / "scientific-skills" / "research-grants"
    references = set()
    for markdown_file in (skill_dir / "SKILL.md", skill_dir / "references" / "README.md"):
        text = markdown_file.read_text(encoding="utf-8")
        references.update(re.findall(r"`(references/[^`]+\.md)`", text))

    missing = sorted(ref for ref in references if not (skill_dir / ref).exists())

    assert missing == []
