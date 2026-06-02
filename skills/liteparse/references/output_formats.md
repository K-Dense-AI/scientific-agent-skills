# LiteParse Output Formats

## Text output (`--format text`)

- **CLI:** layout-preserved plain text written to stdout or `-o` file.
- **Python:** `ParseResult.text` — full document; each `ParsedPage.text` — page-level text.
- Reading order follows reconstructed spatial layout (grid projection), not raw PDF content stream order.

Use text output when feeding chunkers, summarizers, or keyword search that do not need coordinates.

---

## JSON output (`--format json`)

### CLI

```bash
lit parse document.pdf --format json -o document.json
```

The CLI serializes the native parse result. Structure aligns with the Python object model below.

### Python object model

After `parser.parse(path)`, use `result.pages` and `result.text`. To emit JSON manually:

```python
import json
from dataclasses import asdict

# Simple serialization pattern (adapt fields as needed)
def page_to_dict(page):
    return {
        "page_num": page.page_num,
        "width": page.width,
        "height": page.height,
        "text": page.text,
        "text_items": [
            {
                "text": item.text,
                "x": item.x,
                "y": item.y,
                "width": item.width,
                "height": item.height,
                "font_name": item.font_name,
                "font_size": item.font_size,
                "confidence": item.confidence,
            }
            for item in page.text_items
        ],
    }

payload = {
    "text": result.text,
    "pages": [page_to_dict(p) for p in result.pages],
}
json.dump(payload, open("out.json", "w"), indent=2)
```

### Example JSON shape

```json
{
  "text": "Full document text...\n",
  "pages": [
    {
      "page_num": 1,
      "width": 612.0,
      "height": 792.0,
      "text": "Page 1 text...",
      "text_items": [
        {
          "text": "Introduction",
          "x": 72.0,
          "y": 100.0,
          "width": 120.0,
          "height": 14.0,
          "font_name": "Times-Bold",
          "font_size": 12.0,
          "confidence": null
        },
        {
          "text": "scanned phrase",
          "x": 80.0,
          "y": 400.0,
          "width": 200.0,
          "height": 12.0,
          "font_name": null,
          "font_size": null,
          "confidence": 0.94
        }
      ]
    }
  ]
}
```

Exact CLI JSON keys may match upstream serialization; treat `text_items` geometry as authoritative for grounding.

---

## Bounding box coordinate system

- Origin **(0, 0)** is **top-left** of the page.
- **x** increases right; **y** increases down.
- Each `TextItem` uses **(x, y, width, height)** — top-left corner plus size in page units (typically PDF points).
- HTTP OCR servers return `[x1, y1, x2, y2]`; LiteParse normalizes into `x, y, width, height` internally.

### Convert corner box to width/height

```python
x1, y1, x2, y2 = bbox
x, y, width, height = x1, y1, x2 - x1, y2 - y1
```

---

## Confidence scores

- Present on OCR-derived `text_items` (since upstream v1.4.0).
- Range **0.0–1.0** when set; `null` for native PDF text extraction.
- Filter low-confidence items in downstream pipelines if needed.

---

## Phrase search across items

Use `search_items()` when a query spans multiple `text_items`:

```python
from liteparse import search_items

hits = search_items(page.text_items, "Supplementary Table 1")
for hit in hits:
    # hit.text — matched phrase
    # hit.x, hit.y, hit.width, hit.height — merged bbox
```

---

## Layout-aware RAG patterns

1. **Chunk by page** — `page.text` or group `text_items` by vertical bands.
2. **Ground citations** — store `(page_num, x, y, width, height)` with each chunk.
3. **Multimodal** — pair JSON chunks with `screenshot()` PNGs for the same `page_num`.
4. **Quality gate** — drop items with `confidence` below threshold on OCR-heavy pages.
