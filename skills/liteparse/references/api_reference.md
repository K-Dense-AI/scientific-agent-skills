# LiteParse API Reference

Targets **liteparse 2.0.0** (Python) and **@llamaindex/liteparse** (Node). Rust crate: `liteparse = "2"`.

## Python: `LiteParse`

```python
from liteparse import LiteParse, ParseResult, ParsedPage, TextItem, ScreenshotResult, search_items
```

### Constructor options

| Python parameter | Type | Default | Description |
|------------------|------|---------|-------------|
| `ocr_enabled` | bool | `True` | Run OCR on regions needing it |
| `ocr_language` | str | `"eng"` | Tesseract language code |
| `ocr_server_url` | str \| None | `None` | HTTP OCR server (see `ocr_and_formats.md`) |
| `tessdata_path` | str \| None | `None` | Path to tessdata directory |
| `max_pages` | int | `1000` | Maximum pages to parse |
| `target_pages` | str \| None | `None` | e.g. `"1-5,10,15-20"` |
| `dpi` | float | `150` | Render DPI (OCR / screenshots) |
| `output_format` | str | `"json"` | `"json"` or `"text"` (affects native output mode) |
| `preserve_very_small_text` | bool | `False` | Keep very small text runs |
| `password` | str \| None | `None` | Encrypted PDF password |
| `quiet` | bool | `False` | Suppress progress output |
| `num_workers` | int | CPU−1 | Concurrent OCR workers |

### `parse(file_data)`

**Input:** file path (`str` / `Path`) or **raw PDF bytes** (`bytes`).

**Returns:** `ParseResult`

```python
@dataclass
class ParseResult:
    pages: List[ParsedPage]
    text: str              # full document text (layout-preserved)

    @property
    def num_pages(self) -> int

    def get_page(self, page_num: int) -> Optional[ParsedPage]  # 1-indexed
```

```python
@dataclass
class ParsedPage:
    page_num: int
    width: float
    height: float
    text: str
    text_items: List[TextItem]
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

**Raises:** `FileNotFoundError`, `ParseError`

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

Non-PDF formats are converted when LibreOffice/ImageMagick are installed.

### `get_config()`

Returns resolved `LiteParseConfig` dataclass.

### `search_items(items, phrase, *, case_sensitive=False)`

Search a list of `TextItem` for a phrase that may span multiple items. Returns merged `TextItem` objects with combined bounding boxes.

```python
from liteparse import search_items

matches = search_items(page.text_items, "Figure 1", case_sensitive=False)
```

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

Install: `npm i @llamaindex/liteparse` (includes `lit` CLI).

Browser/edge: `@llamaindex/liteparse-wasm` — see upstream WASM README.

---

## Rust (library)

```rust
use liteparse::{LiteParse, LiteParseConfig};

let parser = LiteParse::new(LiteParseConfig::default());
let result = parser.parse("document.pdf").await?;
```

Custom OCR: implement `OcrEngine` trait and `.with_ocr_engine(Arc::new(engine))`.

CLI: `cargo install liteparse`
