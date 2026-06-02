import math
from pathlib import Path


def _parse_frontmatter(content: str) -> dict:
    if not content.startswith("---"):
        return {}
    _, _, rest = content.partition("---\n")
    block, _, _ = rest.partition("\n---")
    out = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


def load_skill_descriptions(skills_dir):
    skills_dir = Path(skills_dir)
    skills = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        fm = _parse_frontmatter(skill_md.read_text())
        if "name" in fm and "description" in fm:
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
