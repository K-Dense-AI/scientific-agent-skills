---
name: liteparse
description: Local document and PDF parsing with spatial text and bounding boxes. Use for extracting text from PDFs, DOCX, Office files, and images; OCR on scans; layout-preserved JSON for RAG; batch-ingesting paper folders; or page screenshots for multimodal agents — even when the user does not name liteparse. Prefer over MarkItDown when you need bboxes, fast local parsing, or PNG page renders; prefer over the pdf skill for merge/split/forms.
license: Apache-2.0
allowed-tools: Read Write Edit Bash
compatibility: Python 3.10+. Optional LibreOffice (Office formats) and ImageMagick (images). Bundled Tesseract for OCR. All processing is local — no cloud API required.
metadata:
  version: "1.0"
  skill-author: K-Dense Inc.
---

# LiteParse — Local Document Parsing

## Overview

LiteParse is a fast, open-source document parser (Rust core, Python/Node bindings) focused on **local, layout-aware text extraction** with bounding boxes. It does not produce Markdown and does not call cloud LLMs. Outputs are **plain text** (layout-preserved) or **structured JSON** with per-page `text_items` (position, font metadata, optional confidence).

**Version note:** Examples target **liteparse 2.0.0** (PyPI, May 2026). The upstream V1 branch is legacy; this skill documents **V2 / main** only.

For parser selection vs MarkItDown, the `pdf` skill, or LlamaParse, see `references/choosing_a_parser.md`.

## When to Use This Skill

Use LiteParse when you need:

- **Fast local parsing** of PDFs or converted Office/image files without cloud dependencies
- **Spatial text** with bounding boxes for layout-aware RAG, citation grounding, or figure/table region logic
- **OCR** on scanned PDFs or images (bundled Tesseract, or a user-run HTTP OCR server)
- **Page screenshots** (PNG) for multimodal agents that must see charts, figures, or handwriting
- **Batch ingestion** of literature folders, supplementary PDFs, or protocol libraries
- **Page subsets** or **password-protected** PDFs

## When Not to Use

| Task | Use instead |
|------|-------------|
| Markdown for LLM ingestion (EPUB, audio, YouTube, HTML) | `markitdown` skill |
| Merge/split PDFs, forms, watermarks, rotation | `pdf` skill |
| Dense tables, handwriting, production cloud pipelines | [LlamaParse](https://docs.cloud.llamaindex.ai/llamaparse/overview) (cloud; sign up separately) |

## Installation

```bash
uv pip install "liteparse==2.0.0"
```

This installs the Python bindings and the **`lit`** CLI. Verify:

```bash
lit --help
python -c "import liteparse; print(liteparse.__version__)"
```

**Optional system tools** (for non-PDF inputs):

- **LibreOffice** — Word, Excel, PowerPoint, OpenDocument, CSV/TSV
- **ImageMagick** — PNG, JPEG, TIFF, WebP, SVG, etc.

Install commands are in `references/ocr_and_formats.md`.

**Node.js / TypeScript** (optional): `npm i @llamaindex/liteparse` — see `references/api_reference.md`.

---

## Quick Start

### Python

```python
from liteparse import LiteParse

parser = LiteParse(quiet=True)
result = parser.parse("paper.pdf")
print(result.text)

for page in result.pages:
    print(f"Page {page.page_num}: {len(page.text_items)} items")
```

### CLI

```bash
# Layout-preserved text (default)
lit parse paper.pdf

# Structured JSON with bounding boxes
lit parse paper.pdf --format json -o paper.json

# Disable OCR on text-native PDFs (faster)
lit parse paper.pdf --no-ocr
```

---

## Core Workflows

### 1. Parse to layout-preserved text

Best for quick full-document text or feeding chunkers that do not need coordinates.

```python
parser = LiteParse(ocr_enabled=True, quiet=True)
result = parser.parse("document.pdf")
full_text = result.text
```

```bash
lit parse document.pdf -o output.txt
```

### 2. Parse to structured JSON (bounding boxes)

Use when building layout-aware RAG, highlighting source regions, or joining text with screenshots.

```python
import json
from liteparse import LiteParse

parser = LiteParse(output_format="json", quiet=True)
result = parser.parse("document.pdf")

# Programmatic access
for page in result.pages:
    for item in page.text_items:
        bbox = (item.x, item.y, item.width, item.height)
        # item.text, item.confidence, item.font_name, item.font_size
```

```bash
lit parse document.pdf --format json -o document.json
```

JSON field layout: `references/output_formats.md`.

### 3. Parse specific pages

```python
parser = LiteParse(target_pages="1-5,10,15-20", quiet=True)
result = parser.parse("long_paper.pdf")
```

```bash
lit parse long_paper.pdf --target-pages "1-5,10"
```

### 4. Parse from bytes or stdin

Useful for uploads, S3 downloads, or piping remote PDFs.

```python
with open("document.pdf", "rb") as f:
    result = parser.parse(f.read())
```

```bash
curl -sL https://example.com/report.pdf | lit parse -
```

### 5. Page screenshots for multimodal agents

Screenshots capture visual content that text extraction alone misses (figures, complex tables, handwriting).

```python
from pathlib import Path

parser = LiteParse(dpi=150, quiet=True)
shots = parser.screenshot("document.pdf", page_numbers=[1, 2, 3])
out = Path("screenshots")
out.mkdir(exist_ok=True)
for s in shots:
    (out / f"page_{s.page_num}.png").write_bytes(s.image_bytes)
```

```bash
lit screenshot document.pdf --target-pages "1,3,5" -o ./screenshots
lit screenshot document.pdf --dpi 300 -o ./screenshots
```

Combine **JSON parse + screenshots** when an agent needs both coordinates and pixels for the same pages.

### 6. Batch-parse a directory

For large corpora, prefer the CLI (parallel OCR workers) or the bundled script.

```bash
lit batch-parse ./papers ./parsed --format json --recursive
lit batch-parse ./papers ./parsed --extension .pdf --no-ocr
```

```bash
python scripts/batch_parse_dir.py ./papers ./parsed --format json --recursive
```

See `scripts/batch_parse_dir.py` for a Python batch wrapper without network calls.

### 7. OCR configuration

OCR is **on by default**. Tesseract is bundled; no extra install for basic English OCR.

```python
parser = LiteParse(
    ocr_enabled=True,
    ocr_language="eng",       # Tesseract codes: fra, deu, etc.
    num_workers=4,            # parallel OCR (default: CPU cores - 1)
    dpi=150,                  # higher DPI → better OCR, slower
)
```

```bash
lit parse scan.pdf --ocr-language fra
lit parse scan.pdf --no-ocr
lit parse scan.pdf --ocr-server-url http://localhost:8080/ocr
```

**Offline / air-gapped:** set `TESSDATA_PREFIX` to a directory of `.traineddata` files, or pass `--tessdata-path`. Details: `references/ocr_and_formats.md`.

### 8. Encrypted PDFs

```python
parser = LiteParse(password="secret", quiet=True)
result = parser.parse("protected.pdf")
```

```bash
lit parse protected.pdf --password secret
```

### 9. Search text items by phrase

Merge adjacent items and return combined bounding boxes for a phrase (e.g. section titles).

```python
from liteparse import search_items

page = result.get_page(1)
matches = search_items(page.text_items, "Materials and Methods", case_sensitive=False)
```

---

## Multi-Format Inputs

| Category | Extensions (examples) | Requirement |
|----------|----------------------|-------------|
| PDF | `.pdf` | Native |
| Office | `.docx`, `.xlsx`, `.pptx`, `.doc`, `.odt`, … | LibreOffice |
| Images | `.png`, `.jpg`, `.tiff`, `.webp`, `.svg`, … | ImageMagick |

Files are converted to PDF internally, then parsed. If conversion tools are missing, parsing fails with an actionable error — install the dependency and retry.

---

## Performance Tips

- **`--no-ocr`** on born-digital PDFs — largest speedup
- **`target_pages`** — parse only methods/supplement sections
- **`num_workers`** — scale OCR across CPU cores
- **`max_pages`** — cap very large files (default 1000)
- **`lit batch-parse`** — directory-scale jobs with `--recursive` and `--extension`
- Lower **`dpi`** (e.g. 100) when OCR quality is already sufficient

---

## Reference Files

| File | Read when |
|------|-----------|
| `references/choosing_a_parser.md` | Unsure whether to use LiteParse, MarkItDown, pdf, or LlamaParse |
| `references/api_reference.md` | Python/TypeScript API, types, `search_items` |
| `references/cli_reference.md` | Full `lit` command flags |
| `references/output_formats.md` | JSON schema, bboxes, confidence scores |
| `references/ocr_and_formats.md` | Tesseract, HTTP OCR, LibreOffice, ImageMagick |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Office file fails | Install LibreOffice; ensure `soffice` is on PATH (Windows: add LibreOffice `program` dir) |
| Image fails | Install ImageMagick; verify `convert` or `magick` works |
| OCR poor quality | Increase `--dpi`; try `--ocr-language`; or HTTP OCR server |
| OCR slow | `--no-ocr` if not needed; reduce pages; increase `num_workers` |
| Air-gapped OCR | `export TESSDATA_PREFIX=/path/to/tessdata` or `--tessdata-path` |
| `ParseError` on bytes | Ensure input is valid PDF bytes (Office bytes need a file path + conversion) |

---

## Resources

- **GitHub**: https://github.com/run-llama/liteparse
- **Docs**: https://developers.llamaindex.ai/liteparse/
- **PyPI**: https://pypi.org/project/liteparse/2.0.0/
- **npm**: https://www.npmjs.com/package/@llamaindex/liteparse
- **OCR API spec**: https://github.com/run-llama/liteparse/blob/main/OCR_API_SPEC.md
