# File Formats and Conversion Behavior

This reference targets Microsoft MarkItDown 0.1.6. "Built-in" means the converter ships in the `markitdown` package; some built-ins still require an optional dependency extra.

## Installation by Format

```bash
# Full built-in feature set
uv pip install "markitdown[all]==0.1.6"

# Common document subset
uv pip install "markitdown[pdf,docx,pptx,xlsx]==0.1.6"

# Minimal package; suitable for core text/HTML/CSV/ZIP/EPUB/IPYNB paths
uv pip install "markitdown==0.1.6"
```

## Built-in Converter Matrix

| Input | Typical extensions/source | Extra | Main behavior | Important limitations/network |
|---|---|---|---|---|
| Plain text | `.txt`, `.md`, recognized text, JSON/XML text | Core | Decodes text while preserving content | JSON/XML are not guaranteed to be normalized or pretty-printed |
| CSV | `.csv`, `text/csv` | Core | Dedicated CSV-to-Markdown table conversion | Very wide/large tables can create large Markdown |
| HTML | `.html`, `.htm` | Core | Headings, links, lists, tables, and readable text | CSS layout, client-side rendering, and visual fidelity are not preserved |
| RSS/Atom-like XML | feed content/URLs | Core | Feed-focused Markdown | Remote retrieval uses network if a URI is supplied |
| Wikipedia page | Wikipedia URL | Core | Page-oriented Markdown | Network; URL-specific converter |
| Bing result page | Bing search-result URL | Core | Search-result-oriented Markdown | Network; HTML and service behavior can change |
| YouTube | `https://www.youtube.com/watch?...` | `youtube-transcription` for transcript | Metadata, description, and available transcript | Fetches YouTube page/transcript; captions may be absent or restricted |
| ZIP | `.zip` | Core | Iterates members and invokes nested converters | Treat untrusted archives as hostile; output can expand substantially |
| EPUB | `.epub` | Core | Book metadata and structured text | Complex styling, fixed layout, DRM, and interactive content are not preserved |
| Jupyter Notebook | `.ipynb` | Core | Notebook cells and content to Markdown | Runtime state is not reproduced; cells remain inert text during conversion |
| PDF | `.pdf` | `pdf` | Extracts existing text and tables | No built-in local OCR for scanned pages; multi-column order and complex tables require validation |
| Word | `.docx` | `docx` | Headings, lists, links, tables, images/alt text, and OMML math | Track changes, floating layout, and visual pagination are not faithfully reproduced |
| PowerPoint | `.pptx` | `pptx` | Slide text, tables, notes, and shape ordering | Animations and layout fidelity are lost; image description requires an LLM client |
| Excel | `.xlsx` | `xlsx` | Worksheets rendered as Markdown tables | Formulas, charts, merged cells, and formatting require source-level validation |
| Legacy Excel | `.xls` | `xls` | Worksheets rendered as Markdown tables | Legacy parser limitations; no visual workbook fidelity |
| Outlook message | `.msg` | `outlook` | Message headers and body | Attachments and rich formatting may need separate handling |
| Image | `.jpg`, `.jpeg`, `.png` | Core | Selected ExifTool metadata; optional LLM description | Built-in converter does not locally OCR text; image may be sent to an external LLM |
| Audio/video-audio | `.wav`, `.mp3`, `.m4a`, `.mp4` | `audio-transcription` | Metadata plus speech transcript | Transcription uses Google Web Speech through `SpeechRecognition`; content leaves the machine |

### Formats commonly overstated

- The 0.1.6 built-in `ImageConverter` accepts JPEG and PNG, not GIF or WebP.
- Built-in PDF conversion extracts a text layer; Tesseract is not part of MarkItDown's PDF path.
- The package does not promise page ranges, bounding boxes, coordinates, or pixel-faithful output.
- JSON and XML are text-based inputs, not schema-aware transformations.
- A successful conversion does not imply complete figure, equation, table, or reading-order recovery.

## PDF

### Built-in extraction

```python
from markitdown import MarkItDown

result = MarkItDown().convert_local("paper.pdf")
print(result.markdown)
```

Use for born-digital PDFs where text is selectable. MarkItDown 0.1.5 improved aligned/wide table output and partially numbered lists; 0.1.6 fixed linear memory growth across PDF pages.

### Scanned PDFs

Choose one:

1. `markitdown-ocr==0.1.0` with an approved vision provider
2. Azure Document Intelligence
3. Azure Content Understanding
4. A local OCR/layout parser when content cannot leave the environment

Do not claim OCR was performed unless the selected path actually supplied it.

### Validate

- Reading order in multi-column papers
- Equations, superscripts, and symbols
- Table headers and row alignment
- Figure captions and footnotes
- References and hyperlinks
- Missing pages or empty scanned sections

## DOCX

Install:

```bash
uv pip install "markitdown[docx]==0.1.6"
```

Version 0.1.2 added DOCX math-equation rendering. Conversion is semantic, not page-layout preserving.

Validate:

- Heading levels and list nesting
- Tables and merged cells
- OMML equations
- Hyperlinks and image alt text
- Footnotes/endnotes
- Tracked changes and comments

For custom Mammoth mapping:

```python
from markitdown import MarkItDown

converter = MarkItDown(style_map="p[style-name='Abstract'] => blockquote.abstract")
result = converter.convert_local("manuscript.docx")
```

## PPTX

Install:

```bash
uv pip install "markitdown[pptx]==0.1.6"
```

The converter orders shapes to approximate reading order and extracts textual slide content. Optional `llm_client`, `llm_model`, and `llm_prompt` values can describe image content.

Validate:

- Slide order and boundaries
- Speaker notes
- Grouped/overlapping shapes
- Tables and chart labels
- Images containing essential text
- Content conveyed only by position, color, or animation

## XLSX and XLS

Install:

```bash
uv pip install "markitdown[xlsx,xls]==0.1.6"
```

The result is useful for textual review and LLM ingestion, but it is not a workbook round trip.

Validate:

- Sheet names and order
- Hidden rows, columns, and sheets
- Merged cells
- Formula text versus cached/displayed values
- Date/number interpretation
- Charts, images, comments, and conditional formatting

For numeric analysis, read the workbook directly with a dataframe or spreadsheet library after using MarkItDown for orientation.

## Images

The built-in converter supports `.jpg`, `.jpeg`, and `.png`.

Without an LLM client, output may contain only selected metadata and can be empty when ExifTool is unavailable or the file has no relevant metadata.

```python
from markitdown import MarkItDown

result = MarkItDown(exiftool_path="/opt/homebrew/bin/exiftool").convert_local(
    "figure.png"
)
```

Use only a trusted ExifTool executable. MarkItDown 0.1.3 added a safety requirement for ExifTool 12.24 or later.

Vision descriptions and OCR are external-processing paths; see `cloud_and_ocr.md`.

## Audio

Accepted extensions are `.wav`, `.mp3`, `.m4a`, and `.mp4`.

```bash
uv pip install "markitdown[audio-transcription]==0.1.6"
```

The implementation converts supported audio to a `SpeechRecognition` input and calls `recognize_google()`. This is not offline transcription. Obtain approval before converting confidential recordings.

The converter does not provide speaker diarization, timestamps, confidence values, or domain adaptation.

## YouTube

```bash
uv pip install "markitdown[youtube-transcription]==0.1.6"
markitdown "https://www.youtube.com/watch?v=VIDEO_ID" -o transcript.md
```

Behavior:

- Downloads the page
- Extracts title, description, and selected metadata
- Requests an available transcript
- Prefers English, then an available language, with translation fallback

Availability depends on YouTube, the video, geography, cookies/network policy, and transcript permissions.

## CSV, JSON, and XML

CSV has a dedicated table converter:

```python
result = MarkItDown().convert_local("measurements.csv")
```

JSON and XML are generally handled as text-like formats. If downstream work needs validated records, parse with `json`, `defusedxml`, or a schema-aware library rather than parsing the generated Markdown.

## ZIP and EPUB

ZIP conversion invokes MarkItDown recursively for archive members. Apply:

- Maximum archive size
- Maximum member count
- Maximum nested depth
- Compression-ratio limits
- Per-member type allowlists

Do not use conversion as an archive-security boundary.

EPUB conversion targets textual book structure. DRM-protected or fixed-layout publications may fail or lose essential visual information.

## Remote and Special Sources

`convert_uri()` accepts:

- `file:`
- `data:`
- `http:`
- `https:`

`file:` and `data:` are still potentially dangerous when user-controlled. `http:` and `https:` require SSRF, redirect, size, and timeout controls. See `security.md`.

## Azure Document Intelligence Format Set

The 0.1.6 integration supports:

- Documents: DOCX, PPTX, XLSX
- OCR/layout: PDF, JPEG, PNG, BMP, TIFF
- HTML is represented in the enum but is not in the converter's default file-type list

The default API version is `2024-07-31-preview`. Document bytes are sent to Azure.

## Azure Content Understanding Format Set

The 0.1.6 integration can route:

- Documents: PDF, DOCX, PPTX, XLSX, HTML, TXT, Markdown, RTF, XML
- Email: EML, MSG
- Images: JPEG, PNG, BMP, TIFF, HEIF/HEIC
- Video: MP4, M4V, MOV, AVI, MKV, WebM, FLV, WMV
- Audio: WAV, MP3, M4A, FLAC, OGG, AAC, WMA

Support here means Azure Content Understanding routing, not local built-in parsing. Each routed conversion is an external, potentially billable operation.

## Format Hints

When bytes lack a meaningful filename:

```python
from markitdown import MarkItDown, StreamInfo

with open("upload.bin", "rb") as stream:
    result = MarkItDown().convert_stream(
        stream,
        stream_info=StreamInfo(
            extension=".pdf",
            mimetype="application/pdf",
            filename="upload.pdf",
        ),
    )
```

CLI equivalents:

```bash
markitdown < upload.bin -x .pdf -m application/pdf -o output.md
```

## Source Basis

- Official 0.1.6 README: https://github.com/microsoft/markitdown/blob/v0.1.6/README.md
- Built-in converter registry: https://github.com/microsoft/markitdown/blob/v0.1.6/packages/markitdown/src/markitdown/_markitdown.py
- Release history: https://github.com/microsoft/markitdown/releases
