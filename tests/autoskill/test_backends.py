import httpx
import pytest

from backends import ClaudeBackend, LocalBackend, make_backend


def _mock_client(handler, base_url=""):
    return httpx.Client(transport=httpx.MockTransport(handler), base_url=base_url)


def test_claude_backend_posts_to_v1_messages_with_auth_headers():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"stop_reason": "end_turn", "content": [{"type": "text", "text": "hello"}]})

    backend = ClaudeBackend(api_key="sk-test", model="claude-opus-4-7",
                            client=_mock_client(handler, base_url="https://api.anthropic.com"))
    result = backend("say hello")

    assert result == "hello"
    assert calls[0].url.path == "/v1/messages"
    assert calls[0].headers["x-api-key"] == "sk-test"
    assert calls[0].headers["anthropic-version"]
    body = calls[0].read()
    import json as _json
    payload = _json.loads(body)
    assert payload["model"] == "claude-opus-4-7"
    assert payload["messages"][0]["role"] == "user"
    assert payload["messages"][0]["content"] == "say hello"


def test_claude_backend_honors_custom_base_url_for_foundry():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"stop_reason": "end_turn", "content": [{"type": "text", "text": "ok"}]})

    backend = ClaudeBackend(api_key="k", model="claude-opus-4-7",
                            client=_mock_client(handler, base_url="https://foundry.example.com/anthropic"))
    backend("hi")

    assert str(calls[0].url).startswith("https://foundry.example.com/anthropic/v1/messages")


def test_claude_backend_raises_on_http_error():
    def handler(request):
        return httpx.Response(401, json={"error": "bad key"})

    backend = ClaudeBackend(api_key="k", model="m",
                            client=_mock_client(handler, base_url="https://api.anthropic.com"))
    with pytest.raises(httpx.HTTPStatusError):
        backend("x")


def test_local_backend_posts_to_chat_completions():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={
            "choices": [{"finish_reason": "stop", "message": {"content": "hi back"}}]
        })

    backend = LocalBackend(endpoint="http://localhost:11434/v1", model="qwen2.5:14b",
                           client=_mock_client(handler, base_url="http://localhost:11434/v1"))
    result = backend("prompt")

    assert result == "hi back"
    assert calls[0].url.path.endswith("/chat/completions")
    import json as _json
    payload = _json.loads(calls[0].read())
    assert payload["model"] == "qwen2.5:14b"
    assert payload["messages"][0]["content"] == "prompt"


def test_make_backend_returns_claude_backend_for_claude_config(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env")
    backend = make_backend({
        "backend": "claude",
        "claude": {"model": "claude-opus-4-7"},
    })
    assert isinstance(backend, ClaudeBackend)
    assert backend.api_key == "sk-env"
    assert backend.model == "claude-opus-4-7"


def test_make_backend_returns_claude_backend_with_foundry_base_url(monkeypatch):
    monkeypatch.setenv("FOUNDRY_API_KEY", "sk-foundry")
    backend = make_backend({
        "backend": "foundry",
        "foundry": {
            "endpoint": "https://foundry.example.com/anthropic",
            "model": "claude-opus-4-7",
        },
    })
    assert isinstance(backend, ClaudeBackend)
    assert backend.api_key == "sk-foundry"
    assert "foundry.example.com" in str(backend.client.base_url)


def test_make_backend_returns_local_backend_for_local_config():
    backend = make_backend({
        "backend": "local",
        "local": {"endpoint": "http://localhost:11434/v1", "model": "qwen2.5:14b"},
    })
    assert isinstance(backend, LocalBackend)
    assert backend.model == "qwen2.5:14b"


def test_make_backend_raises_on_unknown_backend():
    with pytest.raises(ValueError, match="unknown backend"):
        make_backend({"backend": "mystery"})


def test_make_backend_raises_when_anthropic_key_missing(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        make_backend({"backend": "claude", "claude": {"model": "m"}})


def test_claude_collects_text_after_thinking_blocks():
    client = _mock_client(lambda _: httpx.Response(200, json={
        "stop_reason": "end_turn", "content": [
            {"type": "thinking", "thinking": "private reasoning"},
            {"type": "text", "text": '{"verdict":'},
            {"type": "text", "text": '"reuse"}'},
        ]}), base_url="https://api.anthropic.com")
    assert ClaudeBackend("fake", "model", client=client)("prompt") == '{"verdict":"reuse"}'


@pytest.mark.parametrize("reason", [None, "max_tokens", "tool_use", "pause_turn", "refusal"])
def test_claude_does_not_accept_incomplete_or_nonfinal_results(reason):
    client = _mock_client(lambda _: httpx.Response(200, json={
        "stop_reason": reason, "content": [{"type": "text", "text": "partial"}]}),
        base_url="https://api.anthropic.com")
    with pytest.raises(RuntimeError, match="did not finish"):
        ClaudeBackend("fake", "model", client=client)("prompt")


def test_lmstudio_sends_optional_bearer_and_preserves_v1_path():
    def handler(request):
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer synthetic-token"
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop",
                             "message": {"content": "complete"}}]})
    client = _mock_client(handler, base_url="http://localhost:1234/v1")
    assert LocalBackend("http://localhost:1234/v1", "m", client=client,
                        api_key="synthetic-token")("prompt") == "complete"


@pytest.mark.parametrize("choice", [
    {"message": {"content": "partial"}},
    {"finish_reason": None, "message": {"content": "partial"}},
    {"finish_reason": "length", "message": {"content": "partial"}},
    {"finish_reason": "tool_calls", "message": {"content": None}},
    {"finish_reason": "stop", "message": {"content": None}},
])
def test_local_nontext_or_incomplete_results_fail(choice):
    client = _mock_client(lambda _: httpx.Response(200, json={"choices": [choice]}),
                          base_url="http://localhost:1234/v1")
    with pytest.raises(RuntimeError):
        LocalBackend("http://localhost:1234/v1", "m", client=client)("prompt")


def test_make_local_backend_reads_lm_api_token(monkeypatch):
    monkeypatch.setenv("LM_API_TOKEN", "synthetic-token")
    backend = make_backend({"backend": "local", "local": {
        "endpoint": "http://localhost:1234/v1", "model": "m"}})
    assert backend.api_key == "synthetic-token"
    backend.client.close()


@pytest.mark.parametrize("endpoint", ["http:///v1", "https://user:secret@example.com/v1",
                                       "https://example.com/v1?token=secret"])
def test_invalid_endpoint_errors_do_not_echo_credentials(endpoint):
    from backends import check_remote_endpoint
    with pytest.raises(ValueError) as error:
        check_remote_endpoint(endpoint, "local")
    assert "secret" not in str(error.value)


def test_claude_missing_stop_reason_is_not_a_final_response():
    client = _mock_client(lambda _: httpx.Response(200, json={
        "content": [{"type": "text", "text": "partial"}]}),
        base_url="https://api.anthropic.com")
    with pytest.raises(RuntimeError, match="did not finish"):
        ClaudeBackend("fake", "model", client=client)("prompt")
