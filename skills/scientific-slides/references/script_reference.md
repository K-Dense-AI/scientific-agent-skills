# Bundled Script Reference

Arguments, options, and usage for `generate_slide_image.py`, `slides_to_pdf.py`,
`validate_presentation.py`, and `pdf_to_images.py`, plus the pptx-skill scripts and
external tools this skill relies on.

## Current runtime and API contracts

Reviewed 2026-09-30. Local tests use PyMuPDF 1.28.2, Pillow 12.3.0,
python-pptx 1.0.2 and pypdf 6.19.0. Install packages in a dedicated environment;
for a single command, for example:

```bash
uv run --isolated --with pymupdf==1.28.2 python scripts/pdf_to_images.py presentation.pdf review/slide --format png
```

Generation needs `requests` and `OPENROUTER_API_KEY`; it sends prompts and attached
images to OpenRouter and the selected model provider. Prefer the environment or
`.env` over putting a credential in shell history with `--api-key`.

- `POST https://openrouter.ai/api/v1/images`: Bearer authentication, JSON
  `model`, `prompt`, `n: 1`, `aspect_ratio: "16:9"`, optional `input_references`
  containing `image_url` data URLs. The model is `google/gemini-3.1-flash-image`
  (Nano Banana 2). Its current endpoints accept up to 14 references, PNG/JPEG/GIF/WebP
  inputs, and no `output_format` capability; the helper checks returned PNG MIME/signature.
- Response: `data[0].b64_json` with optional `media_type`, rather than a chat message.
  Output filenames must end in `.png`. This does not promise vector/editable output,
  transparency, exact typography, or unchanged attached figures.
- `POST https://openrouter.ai/api/v1/chat/completions`: the review uses
  `google/gemini-3.7-flash`, multipart text plus `image_url`, and reads
  `choices[0].message.content`. Its 6.5/10 threshold is a local heuristic,
  not validation of scientific accuracy or accessibility.
- `GET /api/v1/images/models` and `GET /api/v1/images/models/{model-id}/endpoints`
  discover image capabilities; `GET /api/v1/models` verifies the review model's image
  input and text output. These public catalog responses have no page loop here.
- The helper makes one generation call and one review per draft, at most two drafts.
  A generation failure stops without replay; a failed refinement keeps the earlier draft.
  `<stem>_review_log.json` separates `success` (image saved), `quality_met`,
  `final_reviewed`, model IDs, and `termination_reason`. Missing reviews never invent scores.

Official sources: [Image API](https://openrouter.ai/docs/guides/overview/multimodal/image-generation),
[model endpoints](https://openrouter.ai/api/v1/images/models/google/gemini-3.1-flash-image/endpoints),
[image inputs for review](https://openrouter.ai/docs/guides/overview/multimodal/image-understanding).
The current contracts were checked against documentation/public catalogs and offline
mock responses. No authenticated image/review request was made during this refresh.

## Nano Banana 2 Script Reference

### generate_slide_image.py

Generate presentation slides or visuals using Nano Banana 2 AI.

```bash
# Full slide (default) - generates complete slide as image
python scripts/generate_slide_image.py "slide description" -o output.png

# Visual only - generates just the image/figure for embedding in PPT
python scripts/generate_slide_image.py "visual description" -o output.png --visual-only

# With reference images attached (Nano Banana 2 will see these)
python scripts/generate_slide_image.py "Create a conceptual overview matching this style" -o slide.png --attach style_reference.png
python scripts/generate_slide_image.py "Draft a conceptual comparison of these designs" -o compare.png --attach concept_a.png --attach concept_b.png
```

**Options:**
- `-o, --output`: Output PNG path with `.png` suffix (required)
- `--attach IMAGE`: Attach image file(s) as context for generation (can use multiple times)
- `--visual-only`: Generate just the visual/figure, not a complete slide
- `--iterations`: Maximum drafts, 1 or 2 (default: 2)
- `--api-key`: OpenRouter API key (or set OPENROUTER_API_KEY env var)
- `-v, --verbose`: Verbose output

**Attaching Reference Images:**

Use `--attach` for conceptual context or style drafts. It may redraw every pixel,
including labels, logos, axes and measurements. For final quantitative results,
embed the original figure with native PowerPoint or Beamer geometry; do not ask
the image model to combine or preserve it. Verify conceptual diagrams against the
source before presenting them.

**Environment Setup:**
```bash
export OPENROUTER_API_KEY='your_api_key_here'
# Get key at: https://openrouter.ai/keys
```

### slides_to_pdf.py

Combine multiple slide images into a single PDF.

```bash
# Combine PNG files
python scripts/slides_to_pdf.py slides/*.png -o presentation.pdf

# Combine specific files in order
python scripts/slides_to_pdf.py title.png intro.png methods.png -o talk.pdf

# From directory (sorted by filename)
python scripts/slides_to_pdf.py slides/ -o presentation.pdf
```

**Options:**
- `-o, --output`: Output PDF path (required)
- `--dpi`: PDF resolution (default: 150)
- `-v, --verbose`: Verbose output

**Ordering:** Explicit file arguments retain their given order. Each directory/glob expands in filename order; duplicates are removed at their first occurrence.

**Tip:** Name slides with numbers for correct ordering: `01_title.png`, `02_intro.png`, etc.

---

## Tools and Scripts

### Nano Banana 2 Scripts

**generate_slide_image.py** - Generate slides or visuals with AI:
```bash
# Full slide (for PDF workflow)
python scripts/generate_slide_image.py "Title: Introduction\nContent: Key points" -o slide.png

# Visual only (for PPT workflow)
python scripts/generate_slide_image.py "Diagram description" -o figure.png --visual-only

# Options:
# -o, --output       Output PNG path with `.png` suffix (required)
# --visual-only      Generate just the visual, not complete slide
# --iterations N     Maximum drafts, 1 or 2 (default: 2)
# -v, --verbose      Verbose output
```

**slides_to_pdf.py** - Combine slide images into PDF:
```bash
# From glob pattern
python scripts/slides_to_pdf.py slides/*.png -o presentation.pdf

# From directory (sorted by filename)
python scripts/slides_to_pdf.py slides/ -o presentation.pdf

# Options:
# -o, --output    Output PDF path (required)
# --dpi N         PDF resolution (default: 150)
# -v, --verbose   Verbose output
```

### Validation Scripts

**validate_presentation.py**:
```bash
python scripts/validate_presentation.py presentation.pdf --duration 15

# Checks:
# - Slide count vs. recommended range
# - File size warnings
# - Slide dimensions
# - Font sizes (PowerPoint)
# - Compilation (Beamer)
```

**pdf_to_images.py**:
```bash
python scripts/pdf_to_images.py presentation.pdf output/slide --dpi 150

# Converts PDF to images for visual inspection
# Supports: JPG, PNG
# Adjustable DPI
# Page range selection
```

### Validation limits and external PowerPoint tools

`validate_presentation.py` supports PDF, PPTX and TEX. Convert legacy PPT to PPTX/PDF
first. It counts PDF pages (including Beamer overlays/appendices), not conceptual frames;
its timing guidance is only a rehearsal aid. Font checks inspect explicit text-run sizes,
not inherited theme sizes, tables, groups, reading order or text overflow. TEX validation
runs one `pdflatex -no-shell-escape` pass; resolve citations and navigation with `latexmk`
or the full bibliography build before delivery.

`pdf_to_images.py` uses the current `pymupdf` import and `get_pixmap(dpi=...)`;
`--first`/`--last` are inclusive and 1-based. Invalid ranges and nonpositive DPI fail.
`slides_to_pdf.py` uses Pillow's `save_all`/`append_images`; DPI controls page dimensions,
not new image detail. All input slides should share an aspect ratio and pixel size.

To review a PPTX deck, export it to PDF in PowerPoint or LibreOffice
(`soffice --headless --convert-to pdf deck.pptx`) and use the bundled PDF renderer.

Sources: [PyMuPDF rendering](https://pymupdf.readthedocs.io/en/latest/recipes-images.html),
[Pillow PDF](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#pdf),
[python-pptx presentations](https://python-pptx.readthedocs.io/en/latest/user/presentations.html),
[pypdf reader](https://pypdf.readthedocs.io/en/latest/modules/PdfReader.html).

### External Tools

**Recommended**:
- PDF viewer: For reviewing presentations
- Color contrast checker: WebAIM Contrast Checker
- Color blindness simulator: Coblis
- Timer app: For practice sessions
- Screen recorder: For self-review
