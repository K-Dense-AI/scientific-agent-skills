#!/usr/bin/env python3
"""Read or search bundled programmer book PDFs.

Book-specific guidance lives in references/*.md. Raw book PDFs live directly in
assets/. This helper extracts PDF text on demand so agents do not need to
recreate PDF extraction logic.
"""
from __future__ import print_function

import argparse
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zlib

SKILL_DIR = Path(__file__).resolve().parents[1]
ASSETS_DIR = SKILL_DIR / "assets"


def _book_stems():
    if not ASSETS_DIR.exists():
        return []
    return sorted(path.stem for path in ASSETS_DIR.iterdir() if path.suffix == ".pdf")


def list_books():
    for stem in _book_stems():
        print(stem)


def resolve_book(name):
    raw = Path(name)
    if raw.exists():
        if raw.suffix != ".pdf":
            raise SystemExit("Expected a PDF path: %s" % raw)
        return raw
    candidates = []
    if name.endswith(".pdf"):
        candidates.append(ASSETS_DIR / name)
    else:
        candidates.append(ASSETS_DIR / (name + ".pdf"))
    lower = name.lower().replace(".pdf", "")
    for stem in _book_stems():
        if lower in stem.lower():
            candidates.append(ASSETS_DIR / (stem + ".pdf"))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    available = _book_stems()
    hint = ("\nPDFs are not shipped with this skill. Obtain a copy you are entitled to "
            "of the edition listed in SKILL.md (Additional Resources) and save it to "
            "assets/%s.pdf, then re-run." % name)
    raise SystemExit("Book PDF not found: %s\nAvailable books:\n%s%s"
                     % (name, "\n".join(available) if available else "  (none yet)", hint))


def extract_with_pdftotext(path):
    exe = shutil.which("pdftotext")
    if not exe:
        return None
    proc = subprocess.Popen([exe, "-layout", str(path), "-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    if proc.returncode != 0:
        return None
    return out.decode("utf-8", "replace")


def extract_with_python_pdf(path):
    for module_name in ("pypdf", "PyPDF2"):
        try:
            module = __import__(module_name)
        except Exception:
            continue
        try:
            reader_cls = getattr(module, "PdfReader")
            reader = reader_cls(str(path))
            chunks = []
            for page in reader.pages:
                chunks.append(page.extract_text() or "")
            return "\n\n".join(chunks)
        except Exception:
            continue
    return None


def _decode_pdf_literal(value):
    out = []
    i = 0
    while i < len(value):
        ch = value[i]
        if ch != "\\":
            out.append(ch)
            i += 1
            continue
        i += 1
        if i >= len(value):
            break
        esc = value[i]
        mapping = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f", "(": "(", ")": ")", "\\": "\\"}
        if esc in mapping:
            out.append(mapping[esc])
            i += 1
        elif esc in "01234567":
            digits = esc
            i += 1
            for _ in range(2):
                if i < len(value) and value[i] in "01234567":
                    digits += value[i]
                    i += 1
            try:
                out.append(chr(int(digits, 8)))
            except Exception:
                pass
        else:
            out.append(esc)
            i += 1
    return "".join(out)


def _extract_literals(text):
    chunks = []
    for match in re.finditer(r"\((?:\\.|[^\\)])*\)", text, re.S):
        literal = match.group(0)[1:-1]
        decoded = _decode_pdf_literal(literal)
        if decoded.strip():
            chunks.append(decoded)
    return chunks


def _ascii_spans(text):
    return re.findall(r"[A-Za-z][A-Za-z0-9 ,.;:'\"!?/()\[\]_-]{5,}", text)


def extract_with_pdf_streams(path):
    data = Path(path).read_bytes()
    chunks = []
    pos = 0
    while True:
        stream_pos = data.find(b"stream", pos)
        if stream_pos < 0:
            break
        line_start = data.find(b"\n", stream_pos)
        if line_start < 0:
            break
        stream_start = line_start + 1
        stream_end = data.find(b"endstream", stream_start)
        if stream_end < 0:
            break
        header = data[max(0, stream_pos - 3000):stream_pos]
        payload = data[stream_start:stream_end].strip(b"\r\n")
        decoded = None
        if b"/FlateDecode" in header:
            try:
                decoded = zlib.decompress(payload)
            except Exception:
                decoded = None
        if decoded is None:
            decoded = payload
        text = decoded.decode("latin-1", "ignore")
        chunks.extend(_extract_literals(text))
        chunks.extend(_ascii_spans(text))
        pos = stream_end + len(b"endstream")
    if not chunks:
        raw = data.decode("latin-1", "ignore")
        chunks.extend(_extract_literals(raw))
        chunks.extend(_ascii_spans(raw))
    if not chunks:
        return None
    return "\n".join(chunks)


def read_pdf(path):
    text = extract_with_pdftotext(path)
    if text is None:
        text = extract_with_python_pdf(path)
    if text is None:
        text = extract_with_pdf_streams(path)
    if text is None:
        raise SystemExit("Could not extract PDF text. Install pdftotext, pypdf, or PyPDF2: %s" % path)
    return text


def print_excerpt(text, max_chars):
    text = text.rstrip()
    if len(text) > max_chars:
        print(text[:max_chars].rstrip())
        print("\n--- truncated at %d characters ---" % max_chars)
    else:
        print(text)


def search_text(text, pattern, context_lines, max_chars):
    rx = re.compile(pattern, re.IGNORECASE)
    lines = text.splitlines()
    chunks = []
    total = 0
    for idx, line in enumerate(lines):
        if not rx.search(line):
            continue
        start = max(0, idx - context_lines)
        end = min(len(lines), idx + context_lines + 1)
        chunk = "\n".join("%d:%s" % (i + 1, lines[i]) for i in range(start, end))
        if total + len(chunk) > max_chars:
            break
        chunks.append(chunk)
        total += len(chunk)
    if not chunks:
        raise SystemExit("No matches for pattern: %s" % pattern)
    print("\n\n---\n\n".join(chunks))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read/search programmer skill book PDFs.")
    parser.add_argument("book", nargs="?", help="Book slug, partial slug, PDF filename, or PDF path. Use --list to see slugs.")
    parser.add_argument("--list", action="store_true", help="List available book PDF slugs.")
    parser.add_argument("--query", help="Case-insensitive regex to search in the selected PDF.")
    parser.add_argument("--context", type=int, default=4, help="Context lines around --query matches.")
    parser.add_argument("--max-chars", type=int, default=12000, help="Maximum characters to print.")
    args = parser.parse_args(argv)

    if args.list:
        list_books()
        return 0
    if not args.book:
        parser.error("book is required unless --list is used")
    path = resolve_book(args.book)
    text = read_pdf(path)
    if args.query:
        search_text(text, args.query, args.context, args.max_chars)
    else:
        print_excerpt(text, args.max_chars)
    return 0


if __name__ == "__main__":
    sys.exit(main())
