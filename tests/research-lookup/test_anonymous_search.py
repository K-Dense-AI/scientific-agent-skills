"""Exercise the existing lookup entrypoint through the real MCP protocol client."""
import asyncio
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

httpx = pytest.importorskip("httpx")
pytest.importorskip("mcp")
SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "research-lookup"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
import anonymous_search
from research_lookup import ResearchLookup, build_parser

CLIENT = httpx.AsyncClient
SOURCE = {"url": "https://example.org/paper", "title": "Paper", "excerpts": ["Search evidence"]}


class Fixture:
    def __init__(self, *, error=None, status=200, malformed=False, empty=False, stall=False):
        self.calls = []
        self.requests = []
        self.error, self.status = error, status
        self.malformed, self.empty, self.stall = malformed, empty, stall
        self.searches = 0

    async def handle(self, request):
        self.requests.append(request)
        if request.method != "POST":
            return httpx.Response(405)
        message = json.loads(request.content)
        self.calls.append(message)
        method = message["method"]
        if method.startswith("notifications/"):
            return httpx.Response(202)
        if method == "initialize":
            result = {"protocolVersion": message["params"]["protocolVersion"], "capabilities": {"tools": {}},
                      "serverInfo": {"name": "fixture", "version": "1"}}
        elif method == "tools/list":
            result = {"tools": [{"name": n, "inputSchema": {"type": "object"}}
                                for n in ["web_search", "web_fetch"]]}
        else:
            name = message["params"]["name"]
            if self.stall:
                await asyncio.Event().wait()
            if self.status != 200:
                return httpx.Response(self.status, headers={"location": "https://other.example/"})
            if name == "web_search":
                self.searches += 1
                data = {"results": [] if self.empty else [SOURCE], "session_id": f"task-{self.searches}"}
            else:
                data = {"results": [{**SOURCE, "excerpts": ["Fetched evidence"]}],
                        "errors": [{"url": "https://example.org/unavailable", "error_type": "unavailable"}]}
            result = {"content": [{"type": "text", "text": "bad-json" if self.malformed else json.dumps(data)}]}
            if self.error == name:
                result = {"content": [{"type": "text", "text": "tool failure"}], "isError": True}
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": message["id"], "result": result})

    @contextmanager
    def installed(self):
        def client(**kwargs):
            return CLIENT(transport=httpx.MockTransport(self.handle), **kwargs)
        with patch("httpx.AsyncClient", side_effect=client):
            yield self

    def tools(self):
        return [c["params"] for c in self.calls if c["method"] == "tools/call"]


def make_lookup(**kwargs):
    with patch("research_lookup.shutil.which", return_value=None), patch.dict(os.environ, {}, clear=True):
        return ResearchLookup(force_backend="mcp", academic=False, **kwargs)


def test_keyless_lookup_returns_sources_fetches_and_partial_errors():
    fixture = Fixture()
    with fixture.installed(), patch.dict(os.environ, {"PARALLEL_API_KEY": "must-not-send"}):
        result = make_lookup().lookup("official guidance")
    assert result["success"], result
    assert result["backend"] == "mcp"
    assert result["citations"][0]["url"] == SOURCE["url"]
    assert "Fetched evidence" in result["response"]
    assert "unavailable" in result["response"]
    assert "packet" not in result
    assert [c["name"] for c in fixture.tools()] == ["web_search", "web_fetch"]
    for request in fixture.requests:
        assert str(request.url) == anonymous_search.MCP_URL
        assert request.headers["User-Agent"] == anonymous_search.USER_AGENT
        assert request.headers["Accept-Encoding"] == "identity"
        assert "authorization" not in request.headers
    assert fixture.tools()[1]["arguments"]["session_id"] == "task-1"


def test_independent_queries_do_not_share_task_id():
    fixture = Fixture()
    with fixture.installed():
        results = make_lookup().batch_lookup(["question one", "question two"], delay=0)
    assert all(r["success"] for r in results)
    searches = [c for c in fixture.tools() if c["name"] == "web_search"]
    fetches = [c for c in fixture.tools() if c["name"] == "web_fetch"]
    assert all("session_id" not in c["arguments"] for c in searches)
    assert [c["arguments"]["session_id"] for c in fetches] == ["task-1", "task-2"]


@pytest.mark.parametrize("fixture", [Fixture(error="web_search"), Fixture(error="web_fetch"),
    Fixture(status=401), Fixture(status=429), Fixture(status=302), Fixture(malformed=True)])
def test_errors_are_not_empty_success_or_paid_fallback(fixture):
    with fixture.installed(), patch.object(ResearchLookup, "_perplexity_lookup") as fallback:
        result = make_lookup().lookup("guidance")
    assert not result["success"]
    fallback.assert_not_called()
    assert all(str(r.url) == anonymous_search.MCP_URL for r in fixture.requests)


def test_no_extract_and_empty_search_do_not_fetch():
    for fixture, options in [(Fixture(), {"extract_limit": 0}), (Fixture(empty=True), {})]:
        with fixture.installed():
            result = make_lookup(**options).lookup("guidance")
        assert result["success"]
        assert len(fixture.tools()) == 1


@pytest.mark.parametrize("options", [dict(include_domains=["example.org"]), dict(after_date="2026-01-01"),
    dict(manuscript_context={"study": "private"}), dict(previous_interaction_id="previous"),
    dict(search_mode="advanced"), dict(search_mode="basic"), dict(allow_perplexity_fallback=True), dict(extract_limit=11)])
def test_unsupported_controls_fail_before_transmission(options):
    fixture = Fixture()
    with fixture.installed():
        result = make_lookup(**options).lookup("guidance")
    assert not result["success"]
    assert not fixture.requests


def test_academic_mode_requires_explicit_opt_out():
    with patch("research_lookup.shutil.which", return_value=None):
        result = ResearchLookup(force_backend="mcp").lookup("papers")
    assert not result["success"]
    assert "--no-academic" in result["error"]


def test_default_and_explicit_authenticated_routes_unchanged():
    with patch("research_lookup.shutil.which", return_value="parallel-cli"):
        assert ResearchLookup()._select_backend("guidance") == "search"
        assert ResearchLookup(force_backend="parallel")._select_backend("guidance") == "research"
    args = build_parser().parse_args(["guidance", "--force-backend", "mcp", "--no-academic"])
    assert args.force_backend == "mcp" and args.academic is False


def test_total_timeout_is_bounded():
    with Fixture(stall=True).installed():
        with pytest.raises(TimeoutError):
            anonymous_search.lookup("guidance", timeout=0.03)


@pytest.mark.parametrize("streamed", [False, True])
def test_oversized_response_fails_without_fetch(streamed):
    class Oversized(Fixture):
        async def handle(self, request):
            response = await super().handle(request)
            if self.calls[-1]["method"] == "tools/call":
                payload = b" " * (4 * 1024 * 1024 + 1)
                if streamed:
                    class Body(httpx.AsyncByteStream):
                        async def __aiter__(self):
                            yield payload
                    return httpx.Response(200, stream=Body())
                return httpx.Response(200, content=payload)
            return response
    fixture = Oversized()
    with fixture.installed():
        result = make_lookup(cli_timeout=0.3).lookup("guidance")
    assert not result["success"]
    assert len(fixture.tools()) == 1


def test_compressed_response_cannot_bypass_size_limit():
    import gzip

    class Compressed(Fixture):
        async def handle(self, request):
            response = await super().handle(request)
            if self.calls[-1]["method"] == "tools/call":
                message = json.loads(request.content)
                source = {**SOURCE, "excerpts": ["x" * (4 * 1024 * 1024 + 1)]}
                body = json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": {
                    "content": [{"type": "text", "text": json.dumps({"results": [source]})}]
                }}).encode()

                class Body(httpx.AsyncByteStream):
                    async def __aiter__(self):
                        yield gzip.compress(body)

                return httpx.Response(200, headers={"content-type": "application/json", "content-encoding": "gzip"}, stream=Body())
            return response

    fixture = Compressed()
    with fixture.installed():
        result = make_lookup(extract_limit=0).lookup("guidance")
    assert not result["success"]


@pytest.mark.parametrize("options", [dict(target_references=100), dict(extract_batch_size=5)])
def test_unsupported_academic_tuning_fails_before_transmission(options):
    fixture = Fixture()
    with fixture.installed():
        result = make_lookup(**options).lookup("guidance")
    assert not result["success"]
    assert not fixture.requests
