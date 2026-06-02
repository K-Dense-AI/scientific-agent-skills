# LiteParse CLI Reference (`lit`)

The **`lit`** command ships with `liteparse` (Python), `@llamaindex/liteparse` (npm), and `cargo install liteparse` (Rust). Behavior is the same across installs.

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
| `--format <format>` | `json` or `text` (default: `text`) |
| `--no-ocr` | Disable OCR |
| `--ocr-language <lang>` | Tesseract language (default: `eng`) |
| `--ocr-server-url <url>` | HTTP OCR server base URL |
| `--tessdata-path <path>` | Tessdata directory |
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
lit parse document.pdf --target-pages "1-5,10" --no-ocr
lit parse scan.pdf --ocr-language fra --dpi 200
lit parse protected.pdf --password secret
curl -sL https://example.com/paper.pdf | lit parse - -o paper.txt
```

---

## `lit batch-parse`

Parse every supported file in a directory.

```
lit batch-parse [OPTIONS] <input-dir> <output-dir>
```

| Option | Description |
|--------|-------------|
| `--format <format>` | `json` or `text` (default: `text`) |
| `--no-ocr` | Disable OCR |
| `--ocr-language <lang>` | Tesseract language (default: `eng`) |
| `--ocr-server-url <url>` | HTTP OCR server |
| `--tessdata-path <path>` | Tessdata directory |
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

Output files mirror input basenames with `.txt` or `.json` extension.

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
