import json

import pytest

from synthesize import synthesize, SynthesisError


class StubBackend:
    def __init__(self, response: str):
        self.response = response
        self.last_prompt = None

    def __call__(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self.response


def _cluster():
    return {
        "apps": ["Chrome", "Zotero"],
        "session_count": 4,
        "total_duration_seconds": 7200,
        "example_titles": ["PubMed search", "bioRxiv preprint"],
    }


def _top_k():
    return [
        {"name": "literature-review", "description": "Systematic literature reviews", "score": 0.82},
        {"name": "citation-management", "description": "Find and format citations", "score": 0.71},
    ]


def test_prompt_includes_cluster_and_candidate_skills():
    backend = StubBackend(json.dumps({"verdict": "reuse", "target": "literature-review"}))
    synthesize(_cluster(), _top_k(), backend=backend)

    assert "Chrome" in backend.last_prompt
    assert "Zotero" in backend.last_prompt
    assert "literature-review" in backend.last_prompt
    assert "citation-management" in backend.last_prompt


def test_parses_reuse_verdict():
    backend = StubBackend(json.dumps({"verdict": "reuse", "target": "literature-review"}))
    result = synthesize(_cluster(), _top_k(), backend=backend)

    assert result["verdict"] == "reuse"
    assert result["target"] == "literature-review"
    assert result.get("skill_body") is None


def test_parses_compose_verdict_and_returns_skill_body():
    body = "---\nname: lit-review-flow\ndescription: chain lit review + citations\n---\n# flow"
    backend = StubBackend(json.dumps({
        "verdict": "compose",
        "name": "lit-review-flow",
        "skill_body": body,
    }))
    result = synthesize(_cluster(), _top_k(), backend=backend)

    assert result["verdict"] == "compose"
    assert result["name"] == "lit-review-flow"
    assert result["skill_body"] == body


def test_parses_novel_verdict_and_returns_skill_body():
    body = "---\nname: zotero-pubmed-helper\ndescription: new thing\n---\n# new"
    backend = StubBackend(json.dumps({
        "verdict": "novel",
        "name": "zotero-pubmed-helper",
        "skill_body": body,
    }))
    result = synthesize(_cluster(), _top_k(), backend=backend)

    assert result["verdict"] == "novel"
    assert result["skill_body"].startswith("---\nname: zotero-pubmed-helper")


def test_tolerates_json_wrapped_in_markdown_fence():
    payload = json.dumps({"verdict": "reuse", "target": "literature-review"})
    backend = StubBackend(f"Sure, here:\n```json\n{payload}\n```\n")
    result = synthesize(_cluster(), _top_k(), backend=backend)
    assert result["verdict"] == "reuse"


def test_raises_on_unparseable_response():
    backend = StubBackend("not json at all, no way to parse")
    with pytest.raises(SynthesisError):
        synthesize(_cluster(), _top_k(), backend=backend)


def test_raises_on_unknown_verdict():
    backend = StubBackend(json.dumps({"verdict": "weird"}))
    with pytest.raises(SynthesisError):
        synthesize(_cluster(), _top_k(), backend=backend)
