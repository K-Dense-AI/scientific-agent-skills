"""End-to-end tests for the autoskill pipeline.

Exercises the full chain — fetch → redact → cluster → match → synthesize → write
— with real internal modules. External dependencies (screenpipe, LLM, embeddings)
are replaced with deterministic fakes so the suite runs offline in under a second.
"""

import json
import sys
from pathlib import Path

import httpx
import pytest

# Synthetic opaque value for auth-header round-trip tests. Not a credential.
_AUTH = "fake-test-value-1234"

from backends import LocalBackend
from run import run, main


# ---------- fixtures ----------

SKILL_TEMPLATE = "---\nname: {name}\ndescription: {description}\n---\n# {name}\n"


def _write_skill(root: Path, name: str, description: str) -> None:
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(SKILL_TEMPLATE.format(name=name, description=description))


def _seed_skills_dir(root: Path) -> None:
    """A tiny but representative slice of the real scientific-skills/ layout."""
    _write_skill(root, "literature-review",
                 "Systematic literature reviews across PubMed arXiv bioRxiv with citations.")
    _write_skill(root, "citation-management",
                 "Find papers and format citations from Google Scholar and PubMed.")
    _write_skill(root, "scientific-writing",
                 "Write research manuscripts with IMRAD structure and citations.")
    _write_skill(root, "scientific-schematics",
                 "Create scientific diagrams figures and schematics for publications.")
    _write_skill(root, "latex-posters",
                 "Create academic conference posters in LaTeX.")
    _write_skill(root, "rdkit",
                 "Cheminformatics with RDKit molecules drug discovery.")


# ---------- fake screenpipe ----------

def _ocr(ts: str, app: str, title: str, text: str) -> dict:
    return {"type": "OCR", "content": {
        "timestamp": ts, "app_name": app, "window_name": title, "text": text,
    }}


def _realistic_day() -> list:
    """Three workflow patterns repeated twice each, plus noise."""
    events = []
    # Pattern 1: literature work (Chrome + Zotero) — reuse expected
    for hr in (9, 14):
        for m in range(0, 20):
            events.append(_ocr(f"2026-04-17T{hr:02d}:{m:02d}:00Z",
                               "Chrome", "PubMed", "searching papers"))
    # Pattern 2: slides + schematics (Keynote + Preview) — novel expected
    for hr in (11, 16):
        for m in range(0, 20):
            events.append(_ocr(f"2026-04-17T{hr:02d}:{m:02d}:00Z",
                               "Keynote", "deck", "slides for keynote talk"))
    # Pattern 3: manuscript + figures (VSCode + Preview) — compose expected
    for hr in (12, 17):
        for m in range(0, 20):
            events.append(_ocr(f"2026-04-17T{hr:02d}:{m:02d}:00Z",
                               "VSCode", "paper.tex", "writing manuscript with figures"))
    # Pattern 4 (lonely): should be dropped (only one session)
    for m in range(0, 10):
        events.append(_ocr(f"2026-04-17T22:{m:02d}:00Z",
                           "Lonely", "", "whatever"))
    return events


def _screenpipe_client(events: list) -> httpx.Client:
    # Paginate in chunks of 20 to exercise fetch_window's pagination loop.
    page_size = 20

    def handler(request):
        params = dict(request.url.params)
        offset = int(params.get("offset", "0"))
        chunk = events[offset:offset + page_size]
        return httpx.Response(200, json={
            "data": chunk,
            "pagination": {"limit": page_size, "offset": offset, "total": len(events)},
        })

    return httpx.Client(transport=httpx.MockTransport(handler), base_url="http://screenpipe.test")


# ---------- fake LM Studio ----------

class _FakeLMStudioHandler:
    """Returns different verdicts based on apps mentioned in the prompt."""

    def __init__(self):
        self.prompts = []

    def __call__(self, request):
        body = json.loads(request.read())
        prompt = body["messages"][0]["content"]
        self.prompts.append(prompt)

        if "Chrome" in prompt and "PubMed" in prompt:
            out = {"verdict": "reuse", "target": "literature-review"}
        elif "Keynote" in prompt:
            body = ("---\nname: keynote-talk-prep\n"
                    "description: Prepare and iterate on Keynote talks.\n---\n"
                    "# keynote-talk-prep\n")
            out = {"verdict": "novel", "name": "keynote-talk-prep", "skill_body": body}
        elif "VSCode" in prompt:
            body = ("---\nname: manuscript-with-figures\n"
                    "description: Chain scientific-writing + scientific-schematics.\n---\n"
                    "# manuscript-with-figures\n\n"
                    "Invoke scientific-writing then scientific-schematics.\n")
            out = {"verdict": "compose", "name": "manuscript-with-figures", "skill_body": body}
        else:
            out = {"verdict": "reuse", "target": "literature-review"}

        return httpx.Response(200, json={
            "choices": [{"message": {"content": json.dumps(out)}}]
        })


def _keyword_embedder(text: str):
    keywords = ["paper", "pubmed", "literature", "citation", "writing",
                "schematic", "figure", "poster", "molecule", "slides"]
    return [1.0 if k in text.lower() else 0.0 for k in keywords]


def _base_config():
    return {
        "cluster": {"min_session_minutes": 0, "idle_gap_minutes": 10, "min_cluster_size": 2},
    }


# ---------- tests ----------

def test_full_pipeline_produces_report_and_drafts(tmp_path):
    skills_dir = tmp_path / "scientific-skills"
    _seed_skills_dir(skills_dir)

    fake_lmstudio = _FakeLMStudioHandler()
    lm_client = httpx.Client(
        transport=httpx.MockTransport(fake_lmstudio),
        base_url="http://localhost:1234/v1",
    )
    backend = LocalBackend(endpoint="http://localhost:1234/v1",
                           model="Gemma-4-31B-it", client=lm_client)

    out = run(
        _base_config(),
        start_time="2026-04-17T00:00:00Z", end_time="2026-04-17T23:59:59Z",
        out_dir=tmp_path / "_proposed",
        screenpipe_client=_screenpipe_client(_realistic_day()),
        backend=backend,
        embedder=_keyword_embedder,
        skills_dir=skills_dir,
        now=lambda: "2026-04-17T18-00-00",
    )

    # Report exists and mentions all three surviving clusters.
    report = (out / "report.md").read_text()
    assert "Chrome" in report
    assert "Keynote" in report
    assert "VSCode" in report
    assert "reuse" in report
    assert "novel" in report
    assert "compose" in report
    # Lonely cluster was dropped by min_cluster_size.
    assert "Lonely" not in report

    # Novel draft landed under new-skills/.
    novel_skill = out / "new-skills" / "keynote-talk-prep" / "SKILL.md"
    assert novel_skill.exists()
    assert "keynote-talk-prep" in novel_skill.read_text()

    # Compose draft landed under composition-recipes/.
    compose_skill = out / "composition-recipes" / "manuscript-with-figures" / "SKILL.md"
    assert compose_skill.exists()
    body = compose_skill.read_text()
    assert "scientific-writing" in body
    assert "scientific-schematics" in body

    # Reuse verdict writes no draft but does cite the matched existing skill.
    assert not (out / "new-skills" / "literature-review").exists()
    assert "literature-review" in report

    # Pagination actually happened (more than one fetch).
    # 120 events / 20 per page = 6 pages → ≥6 backend-independent calls.
    # (Can't assert directly without reaching into the transport; but the test
    # would fail above if pagination were broken since clusters would be empty.)


def test_pipeline_redaction_prevents_secrets_leaving_the_host(tmp_path):
    skills_dir = tmp_path / "scientific-skills"
    _seed_skills_dir(skills_dir)

    # Plant secrets in every OCR event.
    toxic = [
        _ocr(f"2026-04-17T{hr:02d}:{m:02d}:00Z", "Chrome", "Gmail",
             "email alice@example.com password sk-abcdefghijklmnopqrstuvwxyz012345")
        for hr in (9, 14) for m in range(0, 20)
    ]

    fake_lmstudio = _FakeLMStudioHandler()
    lm_client = httpx.Client(
        transport=httpx.MockTransport(fake_lmstudio),
        base_url="http://localhost:1234/v1",
    )
    backend = LocalBackend(endpoint="http://localhost:1234/v1",
                           model="Gemma-4-31B-it", client=lm_client)

    run(
        _base_config(),
        start_time="s", end_time="e",
        out_dir=tmp_path / "_proposed",
        screenpipe_client=_screenpipe_client(toxic),
        backend=backend, embedder=_keyword_embedder, skills_dir=skills_dir,
        now=lambda: "ts",
    )

    assert fake_lmstudio.prompts, "backend should have been called"
    for prompt in fake_lmstudio.prompts:
        assert "alice@example.com" not in prompt
        assert "sk-abcdefghijklmnopqrstuvwxyz012345" not in prompt


def test_auth_token_threads_through_run_into_fetch_window(tmp_path):
    """Integration: config's screenpipe.token reaches the outgoing HTTP request."""
    skills_dir = tmp_path / "scientific-skills"
    _seed_skills_dir(skills_dir)

    seen_auth = []

    def handler(request):
        seen_auth.append(request.headers.get("authorization"))
        return httpx.Response(200, json={
            "data": [], "pagination": {"limit": 20, "offset": 0, "total": 0},
        })

    client = httpx.Client(transport=httpx.MockTransport(handler),
                          base_url="http://screenpipe.test")

    run(
        _base_config(),
        start_time="2026-04-17T00:00:00Z", end_time="2026-04-17T23:59:59Z",
        out_dir=tmp_path / "_proposed",
        screenpipe_client=client,
        backend=None, embedder=_keyword_embedder, skills_dir=skills_dir,
        screenpipe_token=_AUTH,
        now=lambda: "ts",
    )

    assert seen_auth, "screenpipe should have been called"
    assert all(h == f"Bearer {_AUTH}" for h in seen_auth), seen_auth


def test_cli_dry_run_writes_plan_without_backend_or_embedding_model(tmp_path, monkeypatch):
    """Exercises scripts/run.py's main() via argv with --dry-run.

    --dry-run is the only path that avoids loading sentence-transformers and
    instantiating a backend, so we can smoke-test the CLI offline.
    """
    skills_dir = tmp_path / "scientific-skills"
    _seed_skills_dir(skills_dir)

    # Minimal config.yaml pointing at our fake screenpipe (via localhost base_url
    # that we'll monkeypatch httpx.Client to respect).
    config = tmp_path / "config.yaml"
    config.write_text(
        "backend: local\n"
        "local:\n"
        "  endpoint: http://localhost:1234/v1\n"
        "  model: Gemma-4-31B-it\n"
        "screenpipe:\n"
        "  url: http://screenpipe.test\n"
        "cluster:\n"
        "  min_session_minutes: 0\n"
        "  idle_gap_minutes: 10\n"
        "  min_cluster_size: 2\n"
    )

    # Install a MockTransport-backed default for any httpx.Client the CLI builds.
    events = _realistic_day()

    def handler(request):
        params = dict(request.url.params)
        offset = int(params.get("offset", "0"))
        chunk = events[offset:offset + 20]
        return httpx.Response(200, json={
            "data": chunk,
            "pagination": {"limit": 20, "offset": offset, "total": len(events)},
        })

    original_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda *a, **kw: original_client(
        *a, **{**kw, "transport": httpx.MockTransport(handler)}
    ))

    # Need pyyaml for main() to load the config; install on demand and skip if unavailable.
    yaml = pytest.importorskip("yaml")

    out_dir = tmp_path / "_proposed"
    rc = main([
        "--start", "2026-04-17T00:00:00Z",
        "--end", "2026-04-17T23:59:59Z",
        "--config", str(config),
        "--skills-dir", str(skills_dir),
        "--out", str(out_dir),
        "--dry-run",
    ])
    assert rc == 0

    # One timestamped subdir was created under --out.
    subdirs = [p for p in out_dir.iterdir() if p.is_dir()]
    assert len(subdirs) == 1
    plan = (subdirs[0] / "plan.md").read_text()
    assert "Cluster" in plan
    assert "Chrome" in plan
