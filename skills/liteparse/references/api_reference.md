# LiteParse API Reference

Targets **liteparse 2.15.0** (Python), **@llamaindex/liteparse 2.15.0** (Node 18+), and Rust crate `liteparse = "2.15.0"`. Reviewed 2026-10-01. Python examples were exercised with synthetic PDF/PNG fixtures; Node/Rust snippets are illustrative and source-checked, not executed.

## Python: `LiteParse`

```python
from liteparse import LiteParse, ParseResult, ParsedPage, TextItem, ScreenshotResult, search_items
```

### Constructor options

| Python parameter | Type | Default | Description |
|------------------|------|---------|-------------|
| `ocr_enabled` | bool | `True` | Run OCR on regions needing it |
| `ocr_language` | str | `"eng"` | Tesseract language code |
| `ocr_server_url` | str \| None | `None` | Complete HTTP OCR endpoint; no suffix appended |
| `ocr_server_headers` | dict[str, str] \| None | `None` | Server-specific headers, including authentication |
| `tessdata_path` | str \| None | `None` | Path to tessdata directory |
| `max_pages` | int | `1000` | Maximum pages to parse |
| `target_pages` | str \| None | `None` | e.g. `"1-5,10,15-20"` |
| `dpi` | float | `150` | Render DPI (OCR / screenshots) |
| `output_format` | str | `"json"` | `"json"`, `"text"` or `"markdown"`; Markdown is returned in `result.text` |
| `preserve_very_small_text` | bool | `False` | Keep very small text runs |
| `password` | str \| None | `None` | Encrypted PDF password |
| `quiet` | bool | `False` | Suppress progress output |
| `num_workers` | int | CPU−1 | Concurrent OCR workers |

Other useful constructor options:

| Parameter | Default | Meaning |
|---|---|---|
| `image_mode` | `"placeholder"` | Markdown image presentation: `placeholder`, `off`, `embed` |
| `extract_images` | `False` | Extract embedded image bytes/metadata |
| `image_output_dir` | `None` | Save extracted images; requires `extract_images=True` |
| `extract_links` | `True` | Markdown hyperlink syntax |
| `keep_headers_footers` | `False` | Retain repeated headers/footers in Markdown |
| `extract_screenshots` | `False` | Return PNG bytes for parsed pages |
| `continue_on_page_error` | `False` | Return partial pages and `page_errors` after page-level errors |
| `extract_blocks` | `False` | Reading-order layout blocks with boxes |
| `emit_word_boxes` | `False` | Populate `TextItem.words` with word boxes |
| `ocr_failure_fatal` | `True` | Fail when all OCR fails and a sparse page depends on it |
| `pool_size` | `None` | Persistent subprocess count for whole-document parsing |
| `parse_timeout` | `None` | Hard deadline in seconds; requires `pool_size` |

`extract_annotations`, `extract_form_fields`, `extract_structure_tree`,
`extract_vector_graphics`, `extract_text_metadata`, and `include_complexity`
are opt-in booleans, all false by default. Use the
[released constructor](https://github.com/run-llama/liteparse/blob/d3a79177b9e9e570f8c2d9878ace601445fdaf76/packages/python/liteparse/parser.py)
for advanced crop/orientation/document metadata options; do not assume every
API option has a CLI flag.

### `parse(file_data)`

**Input:** file path (`str` / `Path`) or raw document bytes (`bytes`). PDF bytes are the simplest path; supported binary formats are detected for conversion. Named files are preferable when a format is ambiguous.

**Returns:** `ParseResult`

```python
@dataclass
class ParseResult:
    pages: List[ParsedPage]
    text: str              # document text, or Markdown in markdown mode
    total_pages: int       # source count before page selection/cap
    page_errors: List[PageError]  # page_number, message; inspect for partial output

    @property
    def num_pages(self) -> int: ...  # len(pages), not source total

    def get_page(self, page_num: int) -> Optional[ParsedPage]: ...  # 1-indexed
```

```python
@dataclass
class ParsedPage:
    page_num: int
    width: float
    height: float
    text: str
    text_items: List[TextItem]
    markdown: str
    page_label: Optional[str]
```

```python
@dataclass
class TextItem:
    text: str
    x: float
    y: float
    width: float
    height: float
    font_name: Optional[str]
    font_size: Optional[float]
    confidence: Optional[float]   # 0.0–1.0 when from OCR
```

The type sketches show commonly used fields, not complete constructors.

**Raises:** `FileNotFoundError`, `ParseError`, and `ParseTimeoutError` in pool mode.

### `screenshot(file_path, *, page_numbers=None)`

**Input:** path to document (PDF or convertible format).

**Returns:** `List[ScreenshotResult]` with PNG bytes.

```python
@dataclass
class ScreenshotResult:
    page_num: int
    width: int
    height: int
    image_bytes: bytes
```

Non-PDF formats convert through LibreOffice (Office) or bundled image converters. Screenshots return pixel dimensions; text boxes use page coordinates. See `output_formats.md` before overlaying them.

### `get_config()`

Returns resolved `LiteParseConfig` dataclass.

### `search_items(items, phrase, *, case_sensitive=False)`

Search a list of `TextItem` for a phrase that may span multiple items. Returns merged `TextItem` objects with combined bounding boxes.

```python
from liteparse import search_items

matches = search_items(page.text_items, "Figure 1", case_sensitive=False)
```

---

## Process pools and page integrity

In-process PDFium parsing serializes under a process-global lock. `num_workers`
controls OCR concurrency, not parallel PDF parses. A pool provides separate
processes and `parse_timeout` kills/replaces a timed-out worker:

```python
from liteparse import LiteParse

with LiteParse(ocr_enabled=False, pool_size=2, parse_timeout=30, quiet=True) as parser:
    result = parser.parse("document.pdf")
    if result.page_errors:
        raise RuntimeError(f"Partial document: {result.page_errors}")
```

A page cap or explicit `target_pages` is an intentional subset: compare actual
page numbers with the requested range and `result.total_pages`. A nonempty
result is not proof every page was ingested. `is_complex(path_or_bytes)` returns
per-page `needs_ocr`/`reasons` heuristics; it does not certify transcription quality.

---

## TypeScript / Node.js

```typescript
import { LiteParse } from '@llamaindex/liteparse';

const parser = new LiteParse();
const result = await parser.parse('document.pdf');
console.log(result.text);

for (const page of result.pages) {
  console.log(`Page ${page.pageNum}: ${page.textItems.length} items`);
}
```

### Constructor options (camelCase)

| TypeScript | Python equivalent |
|------------|-------------------|
| `ocrEnabled` | `ocr_enabled` |
| `ocrLanguage` | `ocr_language` |
| `ocrServerUrl` | `ocr_server_url` |
| `ocrServerHeaders` | `ocr_server_headers` |
| `outputFormat` | `output_format` |
| `extractImages` / `imageOutputDir` | `extract_images` / `image_output_dir` |
| `poolSize` | `pool_size` |
| `parseTimeoutMs` | `parse_timeout` (Node milliseconds, Python seconds) |
| `tessdataPath` | `tessdata_path` |
| `maxPages` | `max_pages` |
| `targetPages` | `target_pages` |
| `dpi` | `dpi` |
| `preserveVerySmallText` | `preserve_very_small_text` |
| `password` | `password` |
| `quiet` | `quiet` |
| `numWorkers` | `num_workers` |

### Parse from bytes

```typescript
import { readFile } from 'fs/promises';

const pdfBytes = await readFile('document.pdf');
const result = await parser.parse(pdfBytes);
```

### Screenshots

```typescript
const screenshots = parser.screenshot('document.pdf', [1, 2, 3]);
for (const s of screenshots) {
  // s.pageNum, s.width, s.height, s.imageBuffer (PNG)
}
```

Install: `npm i @llamaindex/liteparse@2.15.0` (includes `lit` CLI).

Browser/edge uses the separate `@llamaindex/liteparse-wasm` package; native examples are not browser APIs. Consult its [WASM README](https://github.com/run-llama/liteparse/tree/main/packages/wasm) for runtime-specific requirements (not exercised here).

---

## Rust (library)

```rust
use liteparse::{LiteParse, LiteParseConfig};

let parser = LiteParse::new(LiteParseConfig::default());
let result = parser.parse("document.pdf").await?;
```

Custom OCR: implement `OcrEngine` trait and `.with_ocr_engine(Arc::new(engine))`.

CLI: `cargo install liteparse`

Sources: [Python API](https://github.com/run-llama/liteparse/blob/d3a79177b9e9e570f8c2d9878ace601445fdaf76/packages/python/README.md), [Node API](https://github.com/run-llama/liteparse/blob/d3a79177b9e9e570f8c2d9878ace601445fdaf76/packages/node/README.md), [Rust API](https://github.com/run-llama/liteparse/blob/d3a79177b9e9e570f8c2d9878ace601445fdaf76/crates/liteparse/README.md).
