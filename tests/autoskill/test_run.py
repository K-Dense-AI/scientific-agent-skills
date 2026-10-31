import json
from pathlib import Path

import httpx
import pytest

from run import run, ScreenpipeUnreachable


SKILL_TEMPLATE = "---\nname: {name}\ndescription: {description}\n---\n# {name}\n"


def _write_skill(root: Path, name: str, description: str) -> None:
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(SKILL_TEMPLATE.format(name=name, description=description))


def _screenpipe_client_with_events(events):
    def handler(request):
        data = [
            {"type": "OCR", "content": {
                "timestamp": e["ts"], "app_name": e["app"],
                "window_name": e.get("window_title", ""), "text": e.get("text", "")
            }}
            for e in events
        ]
        return httpx.Response(200, json={
            "data": data,
            "pagination": {"limit": 9999, "offset": 0, "total": len(data)},
        })
    return httpx.Client(transport=httpx.MockTransport(handler), base_url="http://screenpipe.test")


def _keyword_embedder(text):
    keywords = ["paper", "pubmed", "literature", "figure", "schematic", "slide"]
    return [1.0 if k in text.lower() else 0.0 for k in keywords]


class StubBackend:
    def __init__(self, response_fn):
        self.response_fn = response_fn
        self.calls = 0

    def __call__(self, prompt):
        self.calls += 1
        return self.response_fn(prompt, self.calls)


def _base_config():
    return {
        "cluster": {"min_session_minutes": 0, "idle_gap_minutes": 10, "min_cluster_size": 2},
    }


def _events_two_sessions(app="Chrome"):
    # two sessions of the same app, separated by > idle_gap
    left = [{"ts": f"2026-04-17T10:{m:02d}:00Z", "app": app, "window_title": "PubMed",
             "text": "literature search"} for m in range(0, 10)]
    right = [{"ts": f"2026-04-17T12:{m:02d}:00Z", "app": app, "window_title": "bioRxiv",
              "text": "literature search"} for m in range(0, 10)]
    return left + right


def test_cli_rejects_remote_plaintext_screenpipe_before_client(tmp_path, monkeypatch):
    import yaml
    from run import main

    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump({"screenpipe": {"url": "http://remote.example"}}))
    monkeypatch.setenv("SCREENPIPE_TOKEN", "test-token")
    def forbidden(*args, **kwargs):
        raise AssertionError("must reject before creating a client")
    monkeypatch.setattr("run.httpx.Client", forbidden)
    with pytest.raises(ValueError, match="plaintext HTTP"):
        main(["--start", "s", "--end", "e", "--config", str(config_path), "--dry-run"])


def test_run_writes_report_into_timestamped_proposed_dir(tmp_path):
    skills_dir = tmp_path / "skills"
    _write_skill(skills_dir, "literature-review", "literature pubmed papers")

    backend = StubBackend(lambda prompt, n: json.dumps({"verdict": "reuse", "target": "literature-review"}))

    out = run(
        _base_config(),
        start_time="2026-04-17T00:00:00Z", end_time="2026-04-17T23:59:59Z",
        out_dir=tmp_path / "_proposed",
        screenpipe_client=_screenpipe_client_with_events(_events_two_sessions()),
        backend=backend,
        embedder=_keyword_embedder,
        skills_dir=skills_dir,
        now=lambda: "2026-04-17T14-30-00",
    )

    assert out == tmp_path / "_proposed" / "2026-04-17T14-30-00"
    assert (out / "report.md").exists()
    report = (out / "report.md").read_text()
    assert "literature-review" in report
    assert "reuse" in report


def test_run_writes_new_skill_draft_for_novel_verdict(tmp_path):
    skills_dir = tmp_path / "skills"
    _write_skill(skills_dir, "unrelated", "totally unrelated")

    body = "---\nname: new-thing\ndescription: new\n---\n# new"
    backend = StubBackend(lambda prompt, n: json.dumps({
        "verdict": "novel", "name": "new-thing", "skill_body": body,
    }))

    out = run(
        _base_config(),
        start_time="s", end_time="e",
        out_dir=tmp_path / "_proposed",
        screenpipe_client=_screenpipe_client_with_events(_events_two_sessions()),
        backend=backend, embedder=_keyword_embedder, skills_dir=skills_dir,
        now=lambda: "ts",
    )

    assert (out / "new-skills" / "new-thing" / "SKILL.md").read_text() == body


def test_run_writes_composition_recipe_for_compose_verdict(tmp_path):
    skills_dir = tmp_path / "skills"
    _write_skill(skills_dir, "literature-review", "literature")

    body = "---\nname: lit-flow\ndescription: chain\n---\n# chain"
    backend = StubBackend(lambda prompt, n: json.dumps({
        "verdict": "compose", "name": "lit-flow", "skill_body": body,
    }))

    out = run(
        _base_config(),
        start_time="s", end_time="e",
        out_dir=tmp_path / "_proposed",
        screenpipe_client=_screenpipe_client_with_events(_events_two_sessions()),
        backend=backend, embedder=_keyword_embedder, skills_dir=skills_dir,
        now=lambda: "ts",
    )

    assert (out / "composition-recipes" / "lit-flow" / "SKILL.md").read_text() == body


@pytest.mark.parametrize("verdict", ["compose", "novel"])
def test_model_name_cannot_write_outside_proposal_tree(tmp_path, verdict):
    from synthesize import SynthesisError

    skills_dir = tmp_path / "skills"
    _write_skill(skills_dir, "unrelated", "unrelated")
    escape = tmp_path / "escaped"
    backend = StubBackend(lambda prompt, n: json.dumps({
        "verdict": verdict, "name": str(escape), "skill_body": "malicious draft",
    }))
    with pytest.raises(SynthesisError, match="valid skill name"):
        run(
            _base_config(), start_time="s", end_time="e", out_dir=tmp_path / "proposed",
            screenpipe_client=_screenpipe_client_with_events(_events_two_sessions()),
            backend=backend, embedder=_keyword_embedder, skills_dir=skills_dir, now=lambda: "ts",
        )
    assert not escape.exists()
    assert not list((tmp_path / "proposed").rglob("SKILL.md"))


def test_run_dry_run_does_not_call_backend(tmp_path):
    skills_dir = tmp_path / "skills"
    _write_skill(skills_dir, "literature-review", "literature")
    backend = StubBackend(lambda *a: pytest.fail("backend must not be called in dry-run"))

    out = run(
        _base_config(),
        start_time="s", end_time="e",
        out_dir=tmp_path / "_proposed",
        screenpipe_client=_screenpipe_client_with_events(_events_two_sessions()),
        backend=backend, embedder=_keyword_embedder, skills_dir=skills_dir,
        now=lambda: "ts",
        dry_run=True,
    )

    assert backend.calls == 0
    plan = (out / "plan.md").read_text()
    assert "Chrome" in plan
    assert "session" in plan.lower()


def test_run_redacts_secrets_from_event_text_before_any_llm_call(tmp_path):
    skills_dir = tmp_path / "skills"
    _write_skill(skills_dir, "unrelated", "unrelated")

    events = [{"ts": f"2026-04-17T10:{m:02d}:00Z", "app": "Chrome",
               "window_title": "Gmail",
               "text": "email alice@example.com key sk-abcdefghijklmnopqrstuvwxyz012345"}
              for m in range(0, 10)]
    events += [{"ts": f"2026-04-17T12:{m:02d}:00Z", "app": "Chrome",
                "window_title": "Gmail",
                "text": "email alice@example.com key sk-abcdefghijklmnopqrstuvwxyz012345"}
               for m in range(0, 10)]

    seen_prompts = []

    def capture(prompt, n):
        seen_prompts.append(prompt)
        return json.dumps({"verdict": "reuse", "target": "unrelated"})

    backend = StubBackend(capture)

    run(
        _base_config(),
        start_time="s", end_time="e",
        out_dir=tmp_path / "_proposed",
        screenpipe_client=_screenpipe_client_with_events(events),
        backend=backend, embedder=_keyword_embedder, skills_dir=skills_dir,
        now=lambda: "ts",
    )

    assert seen_prompts, "backend should have been called"
    for prompt in seen_prompts:
        assert "alice@example.com" not in prompt
        assert "sk-abcdefghijklmnopqrstuvwxyz012345" not in prompt


def test_app_and_title_patterns_are_redacted_in_dry_run_plan(tmp_path):
    events = _events_two_sessions(app="alice@example.com")
    for event in events:
        event["window_title"] = "LM_API_TOKEN=synthetic-auth-value"
    out = run(_base_config(), start_time="s", end_time="e", out_dir=tmp_path,
              screenpipe_client=_screenpipe_client_with_events(events),
              backend=None, embedder=None, skills_dir=tmp_path, now=lambda: "plan", dry_run=True)
    text = (out / "plan.md").read_text()
    assert "alice@example.com" not in text
    assert "synthetic-auth-value" not in text
    assert "[REDACTED:email]" in text


def test_cli_passes_offline_embedding_choice_without_loading_weights(tmp_path, monkeypatch):
    import sys
    import types
    import yaml
    from run import main
    calls = []
    class FakeModel:
        def __init__(self, *args, **kwargs):
            calls.append((args, kwargs))
    monkeypatch.setitem(sys.modules, "sentence_transformers",
                        types.SimpleNamespace(SentenceTransformer=FakeModel))
    monkeypatch.setattr("backends.make_backend", lambda _: None)
    client = _screenpipe_client_with_events([])
    monkeypatch.setattr("run.httpx.Client", lambda **kwargs: client)
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump({"embeddings": {
        "model": "cached-fixture-model", "local_files_only": True}}))
    assert main(["--start", "s", "--end", "e", "--config", str(path),
                 "--out", str(tmp_path / "out"), "--skills-dir", str(tmp_path)]) == 0
    assert calls == [(('cached-fixture-model',), {"local_files_only": True})]


def test_run_raises_actionable_error_when_screenpipe_unreachable(tmp_path):
    skills_dir = tmp_path / "skills"
    _write_skill(skills_dir, "any", "any")

    def handler(request):
        raise httpx.ConnectError("Connection refused")

    dead_client = httpx.Client(transport=httpx.MockTransport(handler),
                               base_url="http://localhost:3030")
    backend = StubBackend(lambda *a: pytest.fail("backend must not be called when screenpipe is down"))

    with pytest.raises(ScreenpipeUnreachable, match="screenpipe"):
        run(
            _base_config(),
            start_time="s", end_time="e",
            out_dir=tmp_path / "_proposed",
            screenpipe_client=dead_client,
            backend=backend, embedder=_keyword_embedder, skills_dir=skills_dir,
            now=lambda: "ts",
        )


def test_run_skips_clusters_below_min_cluster_size(tmp_path):
    skills_dir = tmp_path / "skills"
    _write_skill(skills_dir, "any", "any")
    # only one session => no cluster meets min_cluster_size=2
    events = [{"ts": f"2026-04-17T10:{m:02d}:00Z", "app": "Lonely",
               "window_title": "", "text": ""} for m in range(0, 10)]

    backend = StubBackend(lambda *a: pytest.fail("backend must not be called when no clusters"))

    out = run(
        _base_config(),
        start_time="s", end_time="e",
        out_dir=tmp_path / "_proposed",
        screenpipe_client=_screenpipe_client_with_events(events),
        backend=backend, embedder=_keyword_embedder, skills_dir=skills_dir,
        now=lambda: "ts",
    )

    assert backend.calls == 0
    assert "no clusters" in (out / "report.md").read_text().lower()
