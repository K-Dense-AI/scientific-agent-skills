# LiteParse 2.15.0 Output Formats

## Text and Markdown

`lit parse document.pdf --format text` produces layout-preserved plain text;
`--format markdown` reconstructs headings, lists, tables and links heuristically.
Python `result.text` contains the selected document output, while each page has
`text` and `markdown` fields. Text items remain available in every output mode.

Markdown's default `image_mode="placeholder"` emits image references, not image
files. Use `extract_images=True, image_output_dir="images"` (CLI
`--extract-images --image-output-dir images`) to save bytes; `image_mode="off"`
removes Markdown references. JSON carries image metadata, never image bytes.

## Native CLI JSON is not the Python object schema

```bash
lit parse document.pdf --format json --no-ocr -o document.json
```

A minimal 2.15.0 native-text result has this shape (illustrative values):

```json
{
  "total_pages": 1,
  "pages": [{
    "page": 1,
    "width": 612.0,
    "height": 792.0,
    "text": "Materials and Methods",
    "text_items": [{
      "text": "Materials and Methods",
      "x": 72.0,
      "y": 120.28,
      "width": 242.76,
      "height": 26.78,
      "font_name": "Helvetica",
      "font_size": 24.0,
      "confidence": 1.0
    }]
  }]
}
```

There is **no top-level `text`** and the page-number key is **`page`**, not
`page_num`. Optional fields may be absent. `total_pages` counts source pages
before selection/capping, not `len(pages)`. When present, CLI `page_errors`
entries use `page` and `message`. Python uses `PageError.page_number`.

`--extract-blocks`, `--extract-annotations`, `--extract-form-fields`,
`--extract-structure-tree`, `--extract-vector-graphics`, and `--complexity` add
opt-in page fields. These can enlarge output substantially. `--extract-text-metadata`
adds rotation and richer glyph/font metadata. Read the
[released serializer](https://github.com/run-llama/liteparse/blob/d3a79177b9e9e570f8c2d9878ace601445fdaf76/crates/liteparse/src/output/json.rs)
for the full schema. npm's CLI also uses snake_case; Node library objects use camelCase.

## Python and the bundled batch wrapper

Python exposes `result.text`, `result.total_pages`, `result.pages`,
`result.page_errors`; page objects expose `page_num`, `text_items`, `text`,
`markdown`, dimensions and optional metadata. `result.num_pages == len(result.pages)`.
`result.get_page(1)` returns `None` if page 1 was not parsed.

The bundled `scripts/batch_parse_dir.py` deliberately emits a compact custom
JSON subset: `text`, `total_pages`, `page_errors`, and pages with `page_num`,
`width`, `height`, `text`, `markdown`, `page_label`, and basic `text_items`.
It excludes image bytes and optional rich metadata. Use native CLI JSON when
that schema or advanced extraction fields are required. The wrapper rejects
partial-page results, page-count truncation and existing output files, reports failures
and exits nonzero. For more than the default 1000 pages, use the native CLI/API
with an explicit `max_pages` and reconcile the returned pages.
It mirrors input subdirectories and appends the output extension to the whole
source name, e.g. `supplement/paper.pdf.json`.

## Boxes, confidence, and validation

- Text-item boxes are `(x, y, width, height)` in top-left page viewport coordinates,
  at 72 units per inch; right/down are positive. Store each page's dimensions.
- For a screenshot of width `Wpx` and height `Hpx`, scale x/width by
  `Wpx / page.width` and y/height by `Hpx / page.height`. Rotations/crops must use
  the same parser settings. Never overlay raw PDF coordinates onto a 150-DPI image.
- HTTP OCR returns `[x1, y1, x2, y2]` in uploaded-image pixels. LiteParse maps
  these into page coordinates and merges native/OCR text.
- A text item may be a multiword span; Python `emit_word_boxes=True` opts into
  `item.words`. The default does not promise per-token boxes.
- Python native-text `confidence` may be `None`; **CLI JSON substitutes 1.0**.
  OCR scores are normalized to 0–1, but are not calibrated probabilities or a
  guarantee of a correct scientific transcription. Confidence alone cannot
  identify OCR provenance.
- Compare requested page numbers with returned pages and inspect `page_errors`.
  Review tables, units, equations and multi-column reading order against PNGs.
  Keep low-confidence source evidence available for review rather than silently
  discarding it from an allegedly complete corpus.

```python
from liteparse import search_items

page = result.get_page(1)
hits = search_items(page.text_items, "Supplementary Table 1") if page else []
for hit in hits:
    print(hit.text, hit.x, hit.y, hit.width, hit.height)
```

Reviewed 2026-10-01 against 2.15.0 source and synthetic PDF/PNG runtime fixtures.
