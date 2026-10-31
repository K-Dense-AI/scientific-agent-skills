# OCR and Supported Input Formats (2.15.0)

## Built-in Tesseract

OCR is enabled by default and runs selectively on sparse pages and embedded
images. `--no-ocr` / `ocr_enabled=False` bypasses it. Tesseract itself is bundled,
but a missing language file triggers a download, even if `tessdata_path` or
`TESSDATA_PREFIX` names a directory. The client performs an unauthenticated GET
of `https://github.com/tesseract-ocr/tessdata_best/raw/main/<code>.traineddata`.

For offline operation, populate **every** requested file before parsing and use
an explicit directory; merely setting that directory does not disable downloads.
`ocr_language="eng+fra"` requires both files. Standard Tesseract codes include
`eng`, `fra`, `deu`, `spa`, `chi_sim`; common two-letter aliases are normalized
by the built-in engine. Language data and download permissions are separate
from installing the package.

```bash
lit parse scan.pdf --ocr-language eng --tessdata-path ./tessdata
lit parse document.pdf --no-ocr
```

Check that `./tessdata/eng.traineddata` exists before the first command. These
commands assume caller-supplied input files; local English OCR was exercised
with already-installed language data, not a network download.

## Optional HTTP OCR

Pass the **complete endpoint URL**, including its path. LiteParse POSTs to the
URL unchanged; it does **not** append `/ocr`:

```bash
lit parse scan.pdf --ocr-server-url http://localhost:8080/ocr --ocr-language en
```

This sends rendered document images to that server. There is no built-in cloud
account, fixed hosted endpoint, or universal auth scheme. A server requiring
credentials can be configured through Python without embedding a secret:

```python
import os
from liteparse import LiteParse

parser = LiteParse(
    ocr_server_url=os.environ["OCR_SERVER_URL"],
    ocr_server_headers={"Authorization": "Bearer " + os.environ["OCR_API_KEY"]},
    ocr_language="en",
    quiet=True,
)
result = parser.parse("scan.pdf")
```

This authentication example is illustrative; configure the header scheme your
server requires. CLI `--ocr-server-header "Name: Value"` is repeatable. Do not
log credentials; command arguments may be visible in process lists.

### Wire contract

- Method: **POST** to the exact configured URL (commonly `/ocr`). No pagination,
  jobs, polling, or separate upload endpoint: each call processes one raster.
- Request: `multipart/form-data`; `file` is PNG bytes named `image.png`, and
  `language` is a string.
- **Language is forwarded unchanged to HTTP OCR.** The standalone API spec
  suggests ISO 639-1 (`en`, `fr`), while LiteParse's default is `eng`. Set a code
  accepted by the server; the HTTP client does not perform the Tesseract alias mapping.
- Response: HTTP 200, `application/json`, with `results` entries containing
  `text`, `bbox` and `confidence`. Empty results are valid.

```json
{
  "results": [{
    "text": "recognized text",
    "bbox": [10, 20, 130, 40],
    "confidence": 0.95
  }]
}
```

Coordinates are top-left-origin image pixels; `[x1,y1,x2,y2]` must have positive
width/height. Optional `polygon` is four `[x,y]` points ordered TL, TR, BR, BL in
the glyphs' upright reading frame, to preserve rotation information.

The client also accepts a worker-style `result` array of `[polygon,text,confidence]`
tuples, but use the standard `results` contract for new servers. Non-2xx HTTP
responses fail. In 2.15.0, transient failures can trigger up to 10 attempts with
60-second per-request timeouts and backoff; 400/401/404 are not retried.
`ocr_failure_fatal=True` (default) fails the parse if all OCR tasks fail and at
least one sparse page depends on OCR. Partial OCR failures may still leave an
incomplete document: compare source pages and extracted content. Python
`pool_size` plus `parse_timeout` can enforce a whole-parse deadline. Request
hedging is opt-in and creates duplicate server work; leave it unset normally.

A loopback test verified exact URL, multipart PNG, language, auth header,
successful result decoding and non-retried 401 handling. This verifies client
transport, not any production OCR service or its recognition quality.

## File conversion

| Input | Examples | Requirement |
|---|---|---|
| PDF | `.pdf` | Native PDFium |
| Word | `.doc`, `.docx`, `.docm`, `.odt`, `.rtf`, `.pages` | LibreOffice |
| Presentations | `.ppt`, `.pptx`, `.pptm`, `.odp`, `.key` | LibreOffice |
| Spreadsheets | `.xls`, `.xlsx`, `.xlsm`, `.xlsb`, `.ods`, `.csv`, `.tsv`, `.numbers` | LibreOffice |
| Images | `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.tiff`, `.tif`, `.webp`, `.svg` | Built-in Rust image/resvg/usvg conversion |

Office and image inputs convert to PDF first. **ImageMagick is not required in
2.15.0**, despite stale internal enum names in source. Plain `.txt`/`.md` are not
supported page-layout inputs and cannot be screenshot-rendered. A supported
extension is not a promise that every file or animation/frame is preserved;
check page count and rendering, especially for multi-frame images and Office formats.

LibreOffice must be discoverable by the platform. Typical installation commands
(illustrative; not run as part of this review):

```bash
# macOS
brew install --cask libreoffice
# Ubuntu/Debian
sudo apt-get install libreoffice
# Windows / Chocolatey
choco install libreoffice-fresh
```

On Windows, put LibreOffice's `program` directory on PATH. Font availability,
print areas, pagination and formula caches affect converted output. Validate
scientific symbols and sheet coverage visually rather than equating a successful
conversion with complete extraction.

Sources reviewed 2026-10-01:

- [OCR API specification](https://github.com/run-llama/liteparse/blob/d3a79177b9e9e570f8c2d9878ace601445fdaf76/OCR_API_SPEC.md)
- [HTTP client](https://github.com/run-llama/liteparse/blob/d3a79177b9e9e570f8c2d9878ace601445fdaf76/crates/liteparse/src/ocr/http_simple.rs)
- [Language downloads](https://github.com/run-llama/liteparse/blob/d3a79177b9e9e570f8c2d9878ace601445fdaf76/crates/liteparse/src/ocr/tesseract.rs)
- [Conversion implementation](https://github.com/run-llama/liteparse/blob/d3a79177b9e9e570f8c2d9878ace601445fdaf76/crates/liteparse/src/conversion.rs)
