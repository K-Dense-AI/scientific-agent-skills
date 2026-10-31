"""Small synthetic conversions and offline provider contracts for MarkItDown 0.1.8."""

from __future__ import annotations

import asyncio
import base64
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import parse_qs, urlparse

import pytest

md = pytest.importorskip("markitdown")
SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "markitdown"


@pytest.fixture(autouse=True)
def block_real_network(monkeypatch):
    import socket

    def denied(*args, **kwargs):
        raise AssertionError("Network is forbidden in synthetic conversion tests")

    monkeypatch.setattr(socket.socket, "connect", denied)


@pytest.fixture
def image_bytes():
    Image = pytest.importorskip("PIL.Image")
    stream = io.BytesIO()
    Image.new("RGB", (48, 32), "white").save(stream, format="PNG")
    return stream.getvalue()


@pytest.fixture
def corpus(tmp_path, image_bytes):
    fitz = pytest.importorskip("pymupdf")
    docx = pytest.importorskip("docx")
    pptx = pytest.importorskip("pptx")
    openpyxl = pytest.importorskip("openpyxl")
    image = tmp_path / "figure.png"
    image.write_bytes(image_bytes)
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Synthetic PDF sentinel")
    pdf.save(tmp_path / "Smith_2026_Sentinel.pdf")
    pdf.close()
    scanned = fitz.open()
    scanned.new_page(width=72, height=72).insert_image(
        fitz.Rect(0, 0, 72, 72), stream=image_bytes
    )
    scanned.save(tmp_path / "scan.pdf")
    scanned.close()
    doc = docx.Document()
    doc.add_heading("DOCX sentinel", level=1)
    doc.add_paragraph("Native document content")
    doc.add_picture(str(image))
    doc.add_picture(str(image))
    doc.save(tmp_path / "doc.docx")
    prs = pptx.Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.shapes.add_textbox(0, 0, 5000000, 1000000).text_frame.text = "PPTX sentinel"
    slide.shapes.add_picture(str(image), 0, 1000000)
    slide.notes_slide.notes_text_frame.text = "Notes sentinel"
    prs.save(tmp_path / "slides.pptx")
    wb = openpyxl.Workbook()
    wb.active.title = "Visible"
    wb.active.append(["sample", "value"])
    wb.active.append(["control", 3])
    wb.active.add_image(openpyxl.drawing.image.Image(str(image)), "D1")
    hidden = wb.create_sheet("Hidden")
    hidden.sheet_state = "hidden"
    hidden.append(["hidden sentinel"])
    wb.save(tmp_path / "book.xlsx")
    return tmp_path


@pytest.mark.parametrize(
    "name,sentinels",
    [
        ("Smith_2026_Sentinel.pdf", ["Synthetic PDF sentinel"]),
        ("doc.docx", ["# DOCX sentinel", "Native document content"]),
        ("slides.pptx", ["PPTX sentinel", "Notes sentinel"]),
        ("book.xlsx", ["## Visible", "control", "## Hidden", "hidden sentinel"]),
    ],
)
def test_local_document_semantics(corpus, name, sentinels):
    result = md.MarkItDown().convert_local(corpus / name)
    for text in sentinels:
        assert text in result.markdown
    assert str(result) == result.markdown


def test_csv_ragged_rows_and_cr_lines():
    result = md.MarkItDown().convert_stream(
        io.BytesIO(b"a,b\r1,2,extra\r"), stream_info=md.StreamInfo(extension=".csv")
    )
    assert "extra" in result.markdown and "| a | b |" in result.markdown


def test_uppercase_data_uri_and_binary_stream_contract():
    converter = md.MarkItDown()
    assert (
        "sentinel"
        in converter.convert_uri("DATA:text/plain;BASE64,c2VudGluZWw=").markdown
    )
    with pytest.raises(TypeError):
        converter.convert(io.StringIO("not binary"))


def test_validated_response_and_zip_duplicate_entries():
    import requests

    response = requests.Response()
    response.status_code = 200
    response.url = "https://example.invalid/synthetic.html"
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    response._content = b"<h1>Response sentinel</h1>"
    response._content_consumed = True
    assert "# Response sentinel" in md.MarkItDown().convert_response(response).markdown
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("same.txt", "first sentinel")
        with pytest.warns(UserWarning):
            z.writestr("same.txt", "second sentinel")
    archive.seek(0)
    text = (
        md.MarkItDown()
        .convert_stream(archive, stream_info=md.StreamInfo(extension=".zip"))
        .markdown
    )
    assert "first sentinel" in text and "second sentinel" in text


def test_cli_stdin_and_plugin_flag_contract(tmp_path):
    output = tmp_path / "out.md"
    call = subprocess.run(
        [
            sys.executable,
            "-m",
            "markitdown",
            "-x",
            ".csv",
            "-m",
            "text/csv",
            "-o",
            str(output),
        ],
        input=b"x,y\n1,2\n",
        capture_output=True,
    )
    assert call.returncode == 0, call.stderr.decode()
    assert "| x | y |" in output.read_text()
    unsupported = subprocess.run(
        [sys.executable, "-m", "markitdown", "--llm-model", "synthetic"],
        capture_output=True,
    )
    assert unsupported.returncode == 2


def test_batch_and_literature_clis(corpus, tmp_path):
    out = tmp_path / "batch"
    manifest = out / "manifest.json"
    command = [
        sys.executable,
        str(SKILL_ROOT / "scripts/batch_convert.py"),
        str(corpus),
        str(out),
        "--extensions",
        ".docx",
        ".pptx",
        ".xlsx",
        "--manifest",
        str(manifest),
    ]
    first = subprocess.run(command, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    assert all(
        r["status"] == "converted" for r in json.loads(manifest.read_text())["records"]
    )
    assert (out / "doc.docx.md").is_file()
    second = subprocess.run(command, capture_output=True, text=True)
    assert second.returncode == 0
    assert all(
        r["status"] == "skipped" for r in json.loads(manifest.read_text())["records"]
    )
    papers = tmp_path / "papers"
    papers.mkdir()
    (papers / "Smith_2026_Sentinel.pdf").write_bytes(
        (corpus / "Smith_2026_Sentinel.pdf").read_bytes()
    )
    literature = tmp_path / "literature"
    run = subprocess.run(
        [
            sys.executable,
            str(SKILL_ROOT / "scripts/convert_literature.py"),
            str(papers),
            str(literature),
            "--create-index",
            "--organize-by-year",
        ],
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stderr
    text = (literature / "2026/Smith_2026_Sentinel.md").read_text()
    assert "source_sha256:" in text and "Synthetic PDF sentinel" in text
    assert "2026/Smith_2026_Sentinel.md" in (literature / "INDEX.md").read_text()


def test_openai_image_request_uses_chat_completions(image_bytes):
    openai = pytest.importorskip("openai")
    httpx = pytest.importorskip("httpx2")
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "id": "synthetic",
                "object": "chat.completion",
                "created": 0,
                "model": "synthetic-vision",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "Caption sentinel"},
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    with openai.OpenAI(
        api_key="synthetic-no-network",
        base_url="https://example.invalid/v1",
        http_client=httpx.Client(transport=httpx.MockTransport(handle)),
    ) as client:
        converter = md.MarkItDown(
            llm_client=client, llm_model="synthetic-vision", llm_prompt="Read labels"
        )
        result = converter.convert_stream(
            io.BytesIO(image_bytes),
            stream_info=md.StreamInfo(extension=".png", mimetype="image/png"),
        )
    assert "Caption sentinel" in result.markdown
    assert len(requests) == 1 and requests[0].url.path == "/v1/chat/completions"
    payload = json.loads(requests[0].content)
    assert payload["model"] == "synthetic-vision"
    parts = payload["messages"][0]["content"]
    assert parts[0] == {"type": "text", "text": "Read labels"}
    assert base64.b64decode(parts[1]["image_url"]["url"].split(",")[1]) == image_bytes


@pytest.mark.parametrize("name", ["doc.docx", "book.xlsx", "scan.pdf"])
def test_ocr_plugin_preserves_native_text_and_calls_vision(corpus, name):
    pytest.importorskip("markitdown_ocr")
    create = Mock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="Recognized sentinel <unsafe>")
                )
            ]
        )
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    converter = md.MarkItDown(
        enable_plugins=True, llm_client=client, llm_model="synthetic-vision"
    )
    text = converter.convert_local(corpus / name).markdown
    assert "Recognized sentinel" in text
    if name == "doc.docx":
        assert (
            "Native document content" in text and text.count("Recognized sentinel") == 2
        )
        assert create.call_count == 1  # repeated image bytes share per-document OCR
    if name == "book.xlsx":
        assert "hidden sentinel" in text and text.index("control") < text.index(
            "Recognized sentinel"
        )
    assert create.call_count >= 1


def test_pptx_native_caption_precedes_plugin_ocr(corpus):
    pytest.importorskip("markitdown_ocr")
    create = Mock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(content="Caption sentinel"))
            ]
        )
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    text = (
        md.MarkItDown(
            enable_plugins=True, llm_client=client, llm_model="synthetic-vision"
        )
        .convert_local(corpus / "slides.pptx")
        .markdown
    )
    assert "Caption sentinel" in text and "[Image OCR]" not in text
    assert create.call_count == 1


def test_mcp_in_process_discovery_conversion_and_http_initialize():
    server = pytest.importorskip("markitdown_mcp.__main__")
    from starlette.testclient import TestClient

    text = asyncio.run(server.convert_to_markdown("data:text/plain,MCP%20sentinel"))
    assert "MCP sentinel" in text
    app = server.create_starlette_app(server.mcp)
    assert {"/mcp", "/sse"} <= {r.path for r in app.routes}
    with TestClient(app, base_url="http://127.0.0.1:3001") as client:
        response = client.post(
            "/mcp",
            headers={"Accept": "application/json, text/event-stream"},
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2026-07-28",
                    "capabilities": {},
                    "clientInfo": {"name": "synthetic-test", "version": "1"},
                },
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["result"]["serverInfo"]["name"] == "markitdown"
        tools = client.post(
            "/mcp",
            headers={"Accept": "application/json, text/event-stream"},
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        assert [t["name"] for t in tools.json()["result"]["tools"]] == [
            "convert_to_markdown"
        ]


def azure_transport():
    """Use real SDK serialization and polling against an in-memory transport."""
    pytest.importorskip("azure.core")
    from azure.core.pipeline.transport import HttpResponse, HttpTransport

    class Response(HttpResponse):
        def __init__(self, request, status, body, headers=None):
            super().__init__(request, None)
            self.status_code = status
            from requests.structures import CaseInsensitiveDict

            self.headers = CaseInsensitiveDict(
                {"content-type": "application/json", **(headers or {})}
            )
            self.content_type = "application/json"
            self.reason = "synthetic"
            self._payload = json.dumps(body).encode()

        def body(self):
            return self._payload

        def text(self, encoding=None):
            return self._payload.decode(encoding or "utf-8")

        def read(self):
            return self._payload

        def json(self):
            return json.loads(self._payload)

        def iter_bytes(self):
            yield self._payload

        def iter_raw(self):
            yield self._payload

        def close(self):
            pass

    class Transport(HttpTransport):
        def __init__(self):
            self.requests = []

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

        def open(self):
            pass

        def close(self):
            pass

        def send(self, request, **kwargs):
            self.requests.append(request)
            cu = "/contentunderstanding/" in request.url
            if request.method == "POST":
                location = (
                    "https://example.invalid/contentunderstanding/analyzerResults/synthetic"
                    if cu
                    else "https://example.invalid/documentintelligence/documentModels/prebuilt-layout/analyzeResults/synthetic"
                )
                location += (
                    "?api-version="
                    + parse_qs(urlparse(request.url).query)["api-version"][0]
                )
                return Response(
                    request,
                    202,
                    {},
                    {"Operation-Location": location, "Retry-After": "0"},
                )
            if "/analyzers/" in request.url:
                return Response(
                    request,
                    200,
                    {"analyzerId": "custom", "baseAnalyzerId": "prebuilt-document"},
                )
            result = (
                {
                    "analyzerId": "prebuilt-documentSearch",
                    "apiVersion": "2026-06-01-preview",
                    "contents": [
                        {
                            "kind": "document",
                            "mimeType": "application/pdf",
                            "markdown": "# CU sentinel",
                            "fields": {
                                "Title": {"type": "string", "valueString": "Test"}
                            },
                        }
                    ],
                }
                if cu
                else {
                    "apiVersion": "2024-11-30",
                    "modelId": "prebuilt-layout",
                    "content": "# DI sentinel <!-- PageNumber=1 -->",
                    "pages": [],
                }
            )
            return Response(
                request,
                200,
                {
                    "status": "Succeeded" if cu else "succeeded",
                    "result" if cu else "analyzeResult": result,
                },
            )

    return Transport()


def test_document_intelligence_current_wire_contract(monkeypatch):
    sdk = pytest.importorskip("azure.ai.documentintelligence")
    from azure.core.credentials import AzureKeyCredential
    from markitdown.converters import _doc_intel_converter as impl

    transport = azure_transport()
    real_client = sdk.DocumentIntelligenceClient

    def client(**kwargs):
        return real_client(**kwargs, transport=transport, polling_interval=0)

    monkeypatch.setattr(impl, "DocumentIntelligenceClient", client)
    converter = impl.DocumentIntelligenceConverter(
        endpoint="https://example.invalid", credential=AzureKeyCredential("synthetic")
    )
    result = converter.convert(
        io.BytesIO(b"fake PDF bytes"),
        md.StreamInfo(extension=".pdf", mimetype="application/pdf"),
    )
    assert "# DI sentinel" in result.markdown and "<!--" not in result.markdown
    post, poll = transport.requests
    assert post.method == "POST" and poll.method == "GET"
    assert urlparse(post.url).path.endswith("/documentModels/prebuilt-layout:analyze")
    query = parse_qs(urlparse(post.url).query)
    assert query["api-version"] == ["2024-11-30"]
    assert query["outputContentFormat"] == ["markdown"]
    assert set(query["features"][0].split(",")) == {
        "formulas",
        "ocrHighResolution",
        "styleFont",
    }
    assert base64.b64decode(json.loads(post.body)["base64Source"]) == b"fake PDF bytes"
    assert post.headers["Ocp-Apim-Subscription-Key"] == "synthetic"
    assert converter._analysis_features(md.StreamInfo(extension=".docx")) == []


def test_content_understanding_binary_custom_lookup_and_routing(monkeypatch):
    sdk = pytest.importorskip("azure.ai.contentunderstanding")
    from azure.core.credentials import AzureKeyCredential
    from markitdown.converters import _cu_converter as impl

    transport = azure_transport()
    real_client = sdk.ContentUnderstandingClient

    def client(**kwargs):
        return real_client(**kwargs, transport=transport, polling_interval=0)

    monkeypatch.setattr(impl, "ContentUnderstandingClient", client)
    converter = impl.ContentUnderstandingConverter(
        endpoint="https://example.invalid",
        credential=AzureKeyCredential("synthetic"),
        analyzer_id="custom",
    )
    assert transport.requests[0].method == "GET"  # constructor resolves custom modality
    text = converter.convert(
        io.BytesIO(b"synthetic audio"),
        md.StreamInfo(extension=".mp3", mimetype="audio/mpeg"),
    ).markdown
    assert "# CU sentinel" in text and "Title:" in text
    lookup, post, poll = transport.requests
    assert post.method == "POST" and poll.method == "GET"
    assert urlparse(post.url).path.endswith(
        "/analyzers/prebuilt-audioSearch:analyzeBinary"
    )
    assert parse_qs(urlparse(post.url).query)["api-version"] == ["2026-06-01-preview"]
    assert post.body == b"synthetic audio"
    assert post.headers["Content-Type"] == "audio/mpeg"
    assert post.headers["Ocp-Apim-Subscription-Key"] == "synthetic"


def test_audio_transcription_and_youtube_are_explicit_external_paths(monkeypatch):
    sr = pytest.importorskip("speech_recognition")
    from markitdown.converters._transcribe_audio import transcribe_audio
    import wave

    wav = io.BytesIO()
    with wave.open(wav, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(16000)
        writer.writeframes(b"\x00\x00" * 160)
    wav.seek(0)
    recognize = Mock(return_value="speech sentinel")
    monkeypatch.setattr(sr.Recognizer, "recognize_google", recognize)
    assert transcribe_audio(wav) == "speech sentinel"
    assert recognize.call_count == 1
    from markitdown.converters import _youtube_converter as youtube

    fake_api = Mock()
    fake_api.list.return_value = [SimpleNamespace(language_code="fr")]
    fake_api.fetch.return_value = [SimpleNamespace(text="transcript sentinel")]
    monkeypatch.setattr(youtube, "YouTubeTranscriptApi", Mock(return_value=fake_api))
    converter = youtube.YouTubeConverter()
    text = converter.convert(
        io.BytesIO(b'<html><meta property="og:title" content="Title"></html>'),
        md.StreamInfo(extension=".html", url="https://youtu.be/synthetic"),
        youtube_transcript_languages=["fr"],
    ).markdown
    assert "transcript sentinel" in text
    fake_api.fetch.assert_called_once_with("synthetic", languages=["fr"])
    assert (
        converter._get_video_id("https://www.youtube.com/shorts/synthetic")
        == "synthetic"
    )
    assert converter._get_video_id("https://www.youtube.com/live/synthetic") is None
