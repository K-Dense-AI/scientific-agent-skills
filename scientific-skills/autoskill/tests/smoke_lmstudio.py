"""Real smoke test against a live LM Studio server.

Not part of the pytest suite — requires LM Studio running on localhost:1234
with Gemma-4-31B-it loaded. Run manually:

    pipenv run python scientific-skills/autoskill/tests/smoke_lmstudio.py
"""

import json
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR.parent / "scripts"))

from backends import LocalBackend
from match_skills import load_skill_descriptions, top_k_matches
from synthesize import synthesize


def main() -> int:
    backend = LocalBackend(endpoint="http://localhost:1234/v1", model="gemma-4-31b-it")

    repo_skills_dir = THIS_DIR.parent.parent
    all_skills = load_skill_descriptions(repo_skills_dir)
    print(f"loaded {len(all_skills)} skills from {repo_skills_dir}")

    # Real sentence-transformers embedder.
    print("loading sentence-transformers/all-MiniLM-L6-v2 ...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    def embedder(text: str):
        return list(map(float, model.encode(text)))

    cluster = {
        "apps": ["Chrome", "Zotero"],
        "session_count": 4,
        "total_duration_seconds": 7200,
        "example_titles": ["PubMed search: tumor microenvironment", "bioRxiv preprint"],
    }
    query = ("apps: " + ", ".join(cluster["apps"]) +
             " | titles: " + "; ".join(cluster["example_titles"]))

    top_k = top_k_matches(query, all_skills, embedder=embedder, k=5)
    print("real top-5 matches from embedding search:")
    for s in top_k:
        print(f"  {s['score']:.3f}  {s['name']}")

    result = synthesize(cluster, top_k, backend=backend)
    print("\n--- VERDICT ---")
    print(json.dumps(result, indent=2)[:1000])

    assert result["verdict"] in {"reuse", "compose", "novel"}, result
    print("\nOK: real sentence-transformers top-k + real Gemma-4-31B-it produced a valid verdict.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
