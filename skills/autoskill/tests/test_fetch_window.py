import httpx
import pytest

from fetch_window import fetch_window


def _make_client(handler):
    transport = httpx.MockTransport(handler)
    return httpx.Client(transport=transport, base_url="http://localhost:3030")


def _ocr_event(ts: str, app: str, title: str, text: str) -> dict:
    return {
        "type": "OCR",
        "content": {"timestamp": ts, "app_name": app, "window_name": title, "text": text},
    }


def test_fetch_calls_search_endpoint_with_time_window_params():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"data": [], "pagination": {"limit": 50, "offset": 0, "total": 0}})

    client = _make_client(handler)
    fetch_window(client, start_time="2026-04-17T00:00:00Z", end_time="2026-04-17T04:00:00Z")

    assert calls, "expected at least one HTTP call"
    assert calls[0].url.path == "/search"
    params = dict(calls[0].url.params)
    assert params["start_time"] == "2026-04-17T00:00:00Z"
    assert params["end_time"] == "2026-04-17T04:00:00Z"


def test_fetch_normalizes_ocr_events_into_unified_schema():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "data": [_ocr_event("2026-04-17T10:00:00Z", "VSCode", "paper.tex", "hello")],
            "pagination": {"limit": 50, "offset": 0, "total": 1},
        })

    events = fetch_window(_make_client(handler), "2026-04-17T00:00:00Z", "2026-04-17T23:59:59Z")

    assert len(events) == 1
    e = events[0]
    assert e["app"] == "VSCode"
    assert e["window_title"] == "paper.tex"
    assert e["text"] == "hello"
    assert e["content_type"] == "ocr"
    assert e["ts"] == "2026-04-17T10:00:00Z"


def test_fetch_paginates_until_all_results_collected():
    pages = [
        {"data": [_ocr_event("2026-04-17T10:00:00Z", "App", "t1", "a")] * 2,
         "pagination": {"limit": 2, "offset": 0, "total": 3}},
        {"data": [_ocr_event("2026-04-17T10:05:00Z", "App", "t2", "b")],
         "pagination": {"limit": 2, "offset": 2, "total": 3}},
    ]
    call_count = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        page = pages[call_count["n"]]
        call_count["n"] += 1
        return httpx.Response(200, json=page)

    events = fetch_window(_make_client(handler), "2026-04-17T00:00:00Z", "2026-04-17T23:59:59Z", page_size=2)

    assert call_count["n"] == 2
    assert len(events) == 3


def test_fetch_returns_empty_list_when_no_results():
    def handler(request):
        return httpx.Response(200, json={"data": [], "pagination": {"limit": 50, "offset": 0, "total": 0}})

    events = fetch_window(_make_client(handler), "2026-04-17T00:00:00Z", "2026-04-17T23:59:59Z")
    assert events == []


def test_fetch_sends_bearer_token_when_provided():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"data": [], "pagination": {"limit": 50, "offset": 0, "total": 0}})

    fetch_window(_make_client(handler), "a", "b", token="secret-123")

    assert seen[0].headers.get("authorization") == "Bearer secret-123"


def test_fetch_omits_auth_header_when_no_token():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"data": [], "pagination": {"limit": 50, "offset": 0, "total": 0}})

    fetch_window(_make_client(handler), "a", "b")

    assert "authorization" not in {k.lower() for k in seen[0].headers.keys()}


def test_fetch_raises_on_http_error():
    def handler(request):
        return httpx.Response(500, text="server down")

    with pytest.raises(httpx.HTTPStatusError):
        fetch_window(_make_client(handler), "2026-04-17T00:00:00Z", "2026-04-17T23:59:59Z")
