"""Real smoke test against a live LM Studio server.

Not part of the pytest suite — requires LM Studio running on localhost:1234
with a user-selected model loaded and embeddings already cached. Run manually:

    python tests/autoskill/smoke_lmstudio.py --model autoskill-local
"""

import json
import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = REPO_ROOT / "skills" / "autoskill"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from backends import LocalBackend
from match_skills import load_skill_descriptions, top_k_matches
from synthesize import synthesize


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="exact /v1/models ID")
    args = parser.parse_args()
    backend = LocalBackend(endpoint="http://localhost:1234/v1", model=args.model,
                           api_key=os.environ.get("LM_API_TOKEN"))

    repo_skills_dir = REPO_ROOT / "skills"
    all_skills = load_skill_descriptions(repo_skills_dir)
    print(f"loaded {len(all_skills)} skills from {repo_skills_dir}")

    # Real sentence-transformers embedder.
    print("loading sentence-transformers/all-MiniLM-L6-v2 ...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", local_files_only=True)

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
    print("\n[OK] real sentence-transformers top-k + selected LM Studio model produced a valid verdict.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
