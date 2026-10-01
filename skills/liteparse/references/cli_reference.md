# LiteParse CLI Reference (`lit`)

The **`lit`** command ships with `liteparse` (Python), `@llamaindex/liteparse` (npm), and `cargo install liteparse` (Rust). This reference covers the Python-provided 2.15.0 CLI (`lit ... --help` was executed). Node/Rust releases target the same commands, but inspect the installed CLI before copying version-specific flags.

```bash
lit --help
lit parse --help
lit batch-parse --help
lit screenshot --help
```

---

## `lit parse`

Parse a single file or stdin.

```
lit parse [OPTIONS] <file>
```

| Option | Description |
|--------|-------------|
| `-o, --output <file>` | Write output to file (default: stdout) |
| `--format <format>` | `json`, `text`, or `markdown` (default: `text`) |
| `--no-ocr` | Disable OCR |
| `--ocr-language <lang>` | Tesseract language (default: `eng`) |
| `--ocr-server-url <url>` | Complete HTTP OCR endpoint URL (no `/ocr` appended) |
| `--ocr-server-header <header>` | Repeatable `Name: Value` header for HTTP OCR |
| `--tessdata-path <path>` | Tessdata directory; missing files still download |
| `--max-pages <n>` | Max pages (default: 1000) |
| `--target-pages <pages>` | e.g. `1-5,10,15-20` |
| `--dpi <dpi>` | Rendering DPI (default: 150) |
| `--preserve-small-text` | Keep very small text |
| `--password <password>` | Encrypted document password |
| `--num-workers <n>` | Concurrent OCR workers |
| `-q, --quiet` | Suppress progress |
| `-h, --help` | Help |

### Examples

```bash
lit parse document.pdf
lit parse document.pdf --format json -o output.json
lit parse document.pdf --format markdown -o output.md
lit parse document.pdf --target-pages "1-5,10" --no-ocr
lit parse scan.pdf --ocr-language fra --dpi 200
lit parse protected.pdf --password secret
curl -sL https://example.com/paper.pdf | lit parse - -o paper.txt
```

---

Optional parse flags verified from 2.15.0 `--help`:

- `--continue-on-page-error`: report page extraction failures while retaining
  successful pages. Check JSON `page_errors`; text/Markdown errors go to stderr.
- `--image-mode off|placeholder|embed`: Markdown presentation; use
  `--extract-images --image-output-dir images` for actual image files.
- `--no-links`, `--keep-headers-footers`: control Markdown rendering.
- `--extract-blocks`, `--extract-annotations`, `--extract-form-fields`,
  `--extract-structure-tree`, `--extract-vector-graphics`,
  `--extract-text-metadata`, `--extract-xfa-packets`, `--extract-content-bounds`,
  `--complexity`: include optional structured fields in JSON.

These optional extraction flags were source/help-checked; representative block,
image and metadata behavior was smoke-tested, not every document feature.

## `lit batch-parse`

Parse every supported file in a directory.

```
lit batch-parse [OPTIONS] <input-dir> <output-dir>
```

| Option | Description |
|--------|-------------|
| `--format <format>` | `json`, `text`, or `markdown` (default: `text`) |
| `--no-ocr` | Disable OCR |
| `--ocr-language <lang>` | Tesseract language (default: `eng`) |
| `--ocr-server-url <url>` | Complete HTTP OCR endpoint URL |
| `--ocr-server-header <header>` | Repeatable `Name: Value` header for HTTP OCR |
| `--tessdata-path <path>` | Tessdata directory; missing files still download |
| `--max-pages <n>` | Max pages per file (default: 1000) |
| `--dpi <dpi>` | Rendering DPI (default: 150) |
| `--recursive` | Recurse into subdirectories |
| `--extension <ext>` | Only files with extension (e.g. `.pdf`) |
| `--password <password>` | Password for encrypted documents |
| `--num-workers <n>` | Concurrent OCR workers |
| `-q, --quiet` | Suppress progress |
| `-h, --help` | Help |

### Examples

```bash
lit batch-parse ./papers ./parsed
lit batch-parse ./papers ./parsed --format json --recursive
lit batch-parse ./pdfs ./out --extension .pdf --no-ocr
```

Output paths mirror relative input directories with `.txt`, `.json`, or `.md` replacing the input extension. Same-stem files in the same directory can overwrite each other; restrict `--extension .pdf` or use the bundled wrapper, which preserves source suffixes and refuses existing outputs.

---

## `lit screenshot`

Render pages to PNG files.

```
lit screenshot [OPTIONS] <file>
```

| Option | Description |
|--------|-------------|
| `-o, --output-dir <dir>` | Output directory (default: `./screenshots`) |
| `--target-pages <pages>` | Pages to render (e.g. `1,3,5` or `1-5`) |
| `--dpi <dpi>` | Rendering DPI (default: 150) |
| `--password <password>` | Encrypted document password |
| `-q, --quiet` | Suppress progress |
| `-h, --help` | Help |

### Examples

```bash
lit screenshot document.pdf -o ./screenshots
lit screenshot document.pdf --target-pages "1,3,5" --dpi 300
```

---

## Environment variables

| Variable | Description |
|----------|-------------|
| `TESSDATA_PREFIX` | Directory containing Tesseract `.traineddata` files (offline/air-gapped) |

Reviewed 2026-10-01 against [2.15.0 Python CLI source](https://github.com/run-llama/liteparse/blob/d3a79177b9e9e570f8c2d9878ace601445fdaf76/crates/liteparse-python/src/cli.rs) and installed help/output. Native CLI JSON uses `pages[].page` and has no top-level `text`; see `output_formats.md`.
