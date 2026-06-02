# OCR and Supported Input Formats

## Built-in OCR (Tesseract)

- **Default:** OCR enabled on parse.
- **Engine:** Tesseract bundled with the library (zero extra setup for typical English PDFs).
- **Disable** when PDFs have selectable text: `--no-ocr` or `ocr_enabled=False`.

```bash
lit parse document.pdf
lit parse document.pdf --ocr-language fra
lit parse document.pdf --no-ocr
```

```python
parser = LiteParse(ocr_enabled=True, ocr_language="eng", num_workers=4)
```

### Language codes

Use **Tesseract** codes (not ISO alone): `eng`, `fra`, `deu`, `spa`, `chi_sim`, etc. Map HTTP OCR `language=en` separately (see below).

### Offline / air-gapped environments

Pre-download `.traineddata` files, then either:

```bash
export TESSDATA_PREFIX=/path/to/tessdata
lit parse document.pdf --ocr-language eng
```

or:

```bash
lit parse document.pdf --tessdata-path /path/to/tessdata
```

---

## HTTP OCR servers (optional)

For higher accuracy or GPU-backed OCR, run a server implementing the LiteParse OCR API and point LiteParse at it:

```bash
lit parse document.pdf --ocr-server-url http://localhost:8080/ocr
```

```python
parser = LiteParse(ocr_server_url="http://localhost:8080/ocr")
```

### API contract (summary)

- **POST** `{base_url}/ocr` (typically `http://host:8080/ocr`)
- **Content-Type:** `multipart/form-data`
- **Fields:** `file` (image bytes, required), `language` (optional, ISO 639-1, default `en`)
- **Response JSON:**

```json
{
  "results": [
    {
      "text": "recognized text",
      "bbox": [x1, y1, x2, y2],
      "confidence": 0.95
    }
  ]
}
```

- Origin top-left; bbox axis-aligned in pixels.
- Full spec: https://github.com/run-llama/liteparse/blob/main/OCR_API_SPEC.md

### Reference server implementations (upstream repo)

- `ocr/easyocr/` — EasyOCR wrapper
- `ocr/paddleocr/` — PaddleOCR wrapper

You only need a server if you choose HTTP OCR; Tesseract is sufficient for many workflows.

---

## Supported input formats

### PDF (native)

`.pdf` — no conversion step.

### Office documents (LibreOffice)

Requires LibreOffice installed and on PATH.

| Type | Extensions |
|------|------------|
| Word | `.doc`, `.docx`, `.docm`, `.odt`, `.rtf`, `.pages` |
| PowerPoint | `.ppt`, `.pptx`, `.pptm`, `.odp`, `.key` |
| Spreadsheets | `.xls`, `.xlsx`, `.xlsm`, `.ods`, `.csv`, `.tsv`, `.numbers` |

**Install LibreOffice:**

```bash
# macOS
brew install --cask libreoffice

# Ubuntu/Debian
sudo apt-get install libreoffice

# Windows (Chocolatey)
choco install libreoffice-fresh
```

On Windows, add LibreOffice `program` directory to PATH (often `C:\Program Files\LibreOffice\program`).

### Images (ImageMagick)

Requires ImageMagick.

| Formats |
|---------|
| `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.tiff`, `.webp`, `.svg` |

**Install ImageMagick:**

```bash
# macOS
brew install imagemagick

# Ubuntu/Debian
sudo apt-get install imagemagick

# Windows
choco install imagemagick.app
```

---

## Conversion pipeline

```text
Office / image → (LibreOffice or ImageMagick) → PDF → PDFium extract → optional OCR → grid projection → text + JSON
```

If conversion fails, install the missing tool and retry. Plain-text-only paths cannot be screenshot-rendered.
