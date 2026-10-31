import math
from pathlib import Path

import yaml


def _parse_frontmatter(content: str) -> dict:
    if not content.startswith("---\n"):
        return {}
    _, _, rest = content.partition("---\n")
    block, _, _ = rest.partition("\n---")
    parsed = yaml.safe_load(block)
    return parsed if isinstance(parsed, dict) else {}


def load_skill_descriptions(skills_dir):
    skills_dir = Path(skills_dir)
    skills = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        fm = _parse_frontmatter(skill_md.read_text())
        if all(isinstance(fm.get(key), str) and fm[key].strip() for key in ("name", "description")):
            skills.append({"name": fm["name"], "description": fm["description"]})
    return skills


def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def top_k_matches(query, skills, embedder, k):
    q = embedder(query)
    scored = [
        {"name": s["name"], "description": s["description"],
         "score": _cosine(q, embedder(s["description"]))}
        for s in skills
    ]
    scored.sort(key=lambda r: r["score"], reverse=True)
    return scored[:k]
