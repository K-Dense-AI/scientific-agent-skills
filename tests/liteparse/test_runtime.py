"""Small real LiteParse fixtures; the HTTP service is a loopback contract stub."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

liteparse = pytest.importorskip("liteparse")
SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "liteparse"


def make_pdf(*texts: str) -> bytes:
    """Generate an uncompressed PDF with one Helvetica line per page, no dependencies."""
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    kids = []
    for text in texts:
        page_id = len(objects) + 1
        kids.append(f"{page_id} 0 R")
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {page_id + 1} 0 R >>".encode())
        escaped = text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        content = f"BT /F1 24 Tf 72 650 Td ({escaped}) Tj ET".encode()
        objects.append(f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream")
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(texts)} >>".encode()
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf.extend(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(pdf)


@pytest.fixture
def paper(tmp_path):
    path = tmp_path / "paper.pdf"
    path.write_bytes(make_pdf("Materials and Methods", "Second page"))
    return path


def cli(*args, data=None):
    return subprocess.run([sys.executable, "-m", "liteparse.cli", *map(str, args)],
                          input=data, capture_output=True, timeout=30)


def test_real_pdf_path_bytes_subset_and_search(paper):
    parser = liteparse.LiteParse(ocr_enabled=False, quiet=True)
    result = parser.parse(paper.read_bytes())
    assert result.total_pages == result.num_pages == 2
    assert result.page_errors == []
    page = result.get_page(1)
    assert page.width == 612 and page.height == 792
    hits = liteparse.search_items(page.text_items, "Materials and Methods")
    assert hits and hits[0].width > 0 and hits[0].y >= 0
    assert result.get_page(8) is None
    subset = liteparse.LiteParse(ocr_enabled=False, target_pages="2", quiet=True).parse(paper)
    assert subset.total_pages == 2 and subset.num_pages == 1
    assert subset.pages[0].page_num == 2 and "Second page" in subset.text


def test_real_markdown_screenshots_and_native_image_conversion(paper, tmp_path):
    result = liteparse.LiteParse(ocr_enabled=False, output_format="markdown", quiet=True).parse(paper)
    assert "Materials and Methods" in result.text
    assert result.pages[0].markdown
    shots = liteparse.LiteParse(dpi=72, quiet=True).screenshot(paper, page_numbers=[1])
    assert (shots[0].width, shots[0].height) == (612, 792)
    assert shots[0].image_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    image_path = tmp_path / "scan.png"
    image_path.write_bytes(shots[0].image_bytes)
    # No OCR, no ImageMagick process: verifies built-in image-to-PDF conversion.
    image_result = liteparse.LiteParse(ocr_enabled=False, quiet=True).parse(image_path)
    assert image_result.num_pages == 1 and image_result.pages[0].width > 0


def test_cli_json_markdown_and_stdin(paper):
    result = cli("parse", "-", "--format", "json", "--no-ocr", "--quiet", data=paper.read_bytes())
    assert result.returncode == 0, result.stderr.decode()
    payload = json.loads(result.stdout)
    assert payload["pages"][0]["page"] == 1
    assert payload["pages"][0]["text_items"]
    result = cli("parse", paper, "--format", "markdown", "--no-ocr", "--quiet")
    assert result.returncode == 0 and b"Materials and Methods" in result.stdout


def test_batch_recursive_names_and_repeat_failure(paper, tmp_path):
    source = tmp_path / "in"
    for name in ("a/paper.pdf", "b/paper.pdf"):
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(paper.read_bytes())
    dest = tmp_path / "out"
    command = [sys.executable, str(SKILL_ROOT / "scripts" / "batch_parse_dir.py"),
               str(source), str(dest), "--recursive", "--format", "json", "--no-ocr", "--quiet"]
    first = subprocess.run(command, capture_output=True, timeout=30)
    assert first.returncode == 0, first.stderr.decode()
    a = dest / "a" / "paper.pdf.json"
    b = dest / "b" / "paper.pdf.json"
    assert a.exists() and b.exists()
    payload = json.loads(a.read_text())
    assert payload["total_pages"] == 2 and payload["page_errors"] == []
    previous = a.read_bytes()
    second = subprocess.run(command, capture_output=True, timeout=30)
    assert second.returncode == 1 and a.read_bytes() == previous


@pytest.mark.parametrize("status", [200, 401])
def test_http_ocr_exact_url_headers_language_and_errors(paper, tmp_path, status):
    # Render text to a raster so OCR is the primary text source. Native client
    # runs in a child process so the Python handler cannot be blocked by its GIL.
    png = liteparse.LiteParse(dpi=150, quiet=True).screenshot(paper, page_numbers=[1])[0].image_bytes
    scan = tmp_path / "scan.png"
    scan.write_bytes(png)
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            seen.append((self.path, dict(self.headers), body))
            payload = {"results": [{"text": "Loopback OCR", "bbox": [150, 250, 500, 300], "confidence": 0.95}]} if status == 200 else {"error": "unauthorized fixture"}
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode())

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/custom-ocr"
        result = cli("parse", scan, "--format", "json", "--ocr-server-url", url,
                     "--ocr-server-header", "Authorization: Bearer fixture-only",
                     "--ocr-language", "fr", "--quiet")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    assert seen and all(path == "/custom-ocr" for path, _, _ in seen)
    headers = {k.lower(): v for k, v in seen[0][1].items()}
    assert headers["authorization"] == "Bearer fixture-only"
    assert "multipart/form-data" in headers["content-type"]
    assert b'name="file"' in seen[0][2] and b'image/png' in seen[0][2]
    assert b'name="language"\r\n\r\nfr\r\n' in seen[0][2]
    if status == 200:
        assert result.returncode == 0, result.stderr.decode()
        payload = json.loads(result.stdout)
        assert "Loopback OCR" in payload["pages"][0]["text"]
        assert any(item.get("confidence") for item in payload["pages"][0]["text_items"])
    else:
        assert result.returncode != 0
        assert len(seen) == 1  # Deterministic auth errors are not retried.


def test_opt_in_metadata_blocks_and_pool(paper):
    parser = liteparse.LiteParse(
        ocr_enabled=False, quiet=True, extract_blocks=True, extract_text_metadata=True,
        extract_document_metadata=True, include_complexity=True,
    )
    result = parser.parse(paper)
    assert result.doc_meta is not None
    assert result.pages[0].blocks
    assert result.pages[0].complexity is not None
    assert result.pages[0].text_items[0].confidence is None
    with liteparse.LiteParse(ocr_enabled=False, quiet=True, pool_size=1, parse_timeout=30) as pool:
        pooled = pool.parse(paper)
    assert pooled.text == result.text
