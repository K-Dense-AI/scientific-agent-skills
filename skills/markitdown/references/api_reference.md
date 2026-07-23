# MarkItDown 0.1.6 API Reference

Verified against the `v0.1.6` source tag and installed package on July 23, 2026.

## Public Imports

```python
from markitdown import (
    DocumentConverter,
    DocumentConverterResult,
    FileConversionException,
    MarkItDown,
    MissingDependencyException,
    PRIORITY_GENERIC_FILE_FORMAT,
    PRIORITY_SPECIFIC_FILE_FORMAT,
    StreamInfo,
    UnsupportedFormatException,
)
```

Azure file-type enums are exported from `markitdown.converters`:

```python
from markitdown.converters import (
    ContentUnderstandingFileType,
    DocumentIntelligenceFileType,
)
```

## `MarkItDown`

### Constructor

```python
MarkItDown(
    *,
    enable_builtins: bool | None = None,
    enable_plugins: bool | None = None,
    **kwargs,
)
```

Built-in converters are enabled by default. Third-party plugins are disabled by default.

Recognized constructor keywords include:

| Keyword | Purpose |
|---|---|
| `requests_session` | Custom `requests.Session` used by HTTP(S) URI conversion |
| `llm_client` | OpenAI-compatible client for image descriptions and compatible plugins |
| `llm_model` | Provider-specific model identifier |
| `llm_prompt` | Prompt for image description/OCR |
| `exiftool_path` | Explicit trusted ExifTool executable |
| `style_map` | Mammoth style map for DOCX conversion |
| `docintel_endpoint` | Enable Azure Document Intelligence |
| `docintel_credential` | Explicit `AzureKeyCredential` or token credential |
| `docintel_file_types` | Restrict Document Intelligence routing |
| `docintel_api_version` | Azure Document Intelligence API version |
| `cu_endpoint` | Enable Azure Content Understanding |
| `cu_credential` | Explicit `AzureKeyCredential` or token credential |
| `cu_analyzer_id` | Custom Content Understanding analyzer |
| `cu_file_types` | Restrict Content Understanding routing |

The public signature uses `**kwargs`; spell these names exactly.

### Conversion methods

#### `convert()`

```python
convert(
    source: str | Path | requests.Response | BinaryIO,
    *,
    stream_info: StreamInfo | None = None,
    **kwargs,
) -> DocumentConverterResult
```

Dispatch rules:

- `str` beginning with `http:`, `https:`, `file:`, or `data:` → `convert_uri()`
- other `str` or `Path` → `convert_local()`
- `requests.Response` → `convert_response()`
- binary file-like object → `convert_stream()`
- text stream → `TypeError`

This convenience method is broad. Prefer a narrower method for untrusted or application-facing inputs.

#### `convert_local()`

```python
convert_local(
    path: str | Path,
    *,
    stream_info: StreamInfo | None = None,
    file_extension: str | None = None,
    url: str | None = None,
    **kwargs,
) -> DocumentConverterResult
```

`file_extension` and `url` are legacy parameters; put overrides in `StreamInfo`.

```python
from pathlib import Path

from markitdown import MarkItDown

source = Path("experiment.xlsx")
result = MarkItDown().convert_local(source)
Path("experiment.md").write_text(result.markdown, encoding="utf-8")
```

#### `convert_stream()`

```python
convert_stream(
    stream: BinaryIO,
    *,
    stream_info: StreamInfo | None = None,
    file_extension: str | None = None,
    url: str | None = None,
    **kwargs,
) -> DocumentConverterResult
```

Requirements and behavior:

- The stream must be binary.
- A seekable stream is preferred.
- A non-seekable stream is copied completely into an in-memory `BytesIO`.
- `file_extension` and `url` are legacy hints; prefer `StreamInfo`.

```python
from io import BytesIO

from markitdown import MarkItDown, StreamInfo

payload = b"sample,value\ncontrol,1\ntreated,2\n"
result = MarkItDown().convert_stream(
    BytesIO(payload),
    stream_info=StreamInfo(
        extension=".csv",
        mimetype="text/csv",
        charset="utf-8",
        filename="results.csv",
    ),
)
print(result.markdown)
```

#### `convert_uri()`

```python
convert_uri(
    uri: str,
    *,
    stream_info: StreamInfo | None = None,
    file_extension: str | None = None,
    mock_url: str | None = None,
    **kwargs,
) -> DocumentConverterResult
```

Supported schemes:

- `file:` with an empty authority or `localhost`
- `data:`
- `http:`
- `https:`

HTTP(S) conversion uses the configured `requests.Session`, follows Requests defaults, and then buffers the complete response in memory. It does not provide an application-level SSRF policy, download-size limit, or redirect allowlist. Validate and fetch remote resources yourself before calling `convert_response()`.

`convert_url()` remains a backward-compatible alias, but new code should use `convert_uri()`.

#### `convert_response()`

```python
convert_response(
    response: requests.Response,
    *,
    stream_info: StreamInfo | None = None,
    file_extension: str | None = None,
    url: str | None = None,
    **kwargs,
) -> DocumentConverterResult
```

The method derives hints from `Content-Type`, `Content-Disposition`, and the response URL, then buffers every response chunk into memory. The caller is responsible for destination validation, redirect handling, timeout, maximum size, authentication, and TLS policy.

## `StreamInfo`

```python
StreamInfo(
    *,
    mimetype: str | None = None,
    extension: str | None = None,
    charset: str | None = None,
    filename: str | None = None,
    local_path: str | None = None,
    url: str | None = None,
)
```

Examples:

```python
pdf_info = StreamInfo(
    mimetype="application/pdf",
    extension=".pdf",
    filename="paper.pdf",
)

html_info = StreamInfo(
    mimetype="text/html",
    extension=".html",
    charset="utf-8",
    filename="article.html",
)
```

Hints are merged with extension, HTTP header, and Magika content-detection guesses. If a caller-supplied hint conflicts with content detection, MarkItDown may try both guesses.

## `DocumentConverterResult`

```python
DocumentConverterResult(
    markdown: str,
    *,
    title: str | None = None,
)
```

Attributes and conversions:

| Interface | Status |
|---|---|
| `result.markdown` | Canonical converted Markdown |
| `result.title` | Optional source-derived title |
| `result.text_content` | Soft-deprecated alias for `markdown` |
| `str(result)` | Returns `markdown` |

```python
result = MarkItDown().convert_local("paper.pdf")
markdown = result.markdown
title = result.title
```

## Per-conversion Options

Converter-specific values can be forwarded through a conversion call:

```python
result = converter.convert_local(
    "page.html",
    keep_data_uris=False,
)
```

Common options:

| Option | Used by |
|---|---|
| `keep_data_uris` | HTML/Markdown conversion; preserve rather than truncate data URIs |
| `youtube_transcript_languages` | YouTube transcript language preference |
| `llm_client`, `llm_model`, `llm_prompt` | Image/PPTX description and compatible plugins |
| `style_map` | DOCX conversion |
| `exiftool_path` | Image/audio metadata |

## Exceptions

```python
from markitdown import (
    FileConversionException,
    MissingDependencyException,
    UnsupportedFormatException,
)
```

| Exception | Meaning |
|---|---|
| `MissingDependencyException` | The converter matched, but its optional dependency is unavailable |
| `UnsupportedFormatException` | No registered converter accepted the source |
| `FileConversionException` | One or more matching converters attempted and failed |
| `TypeError` | `convert()` received an unsupported source type, such as a text stream |

```python
from markitdown import (
    FileConversionException,
    MarkItDown,
    MissingDependencyException,
    UnsupportedFormatException,
)

try:
    result = MarkItDown().convert_local("input.pdf")
except MissingDependencyException:
    print("Install markitdown[pdf]==0.1.6")
except UnsupportedFormatException:
    print("No converter accepted this input")
except FileConversionException as exc:
    print(f"A matching converter failed: {exc}")
```

## Converter Registration

```python
register_converter(
    converter: DocumentConverter,
    *,
    priority: float = PRIORITY_SPECIFIC_FILE_FORMAT,
) -> None
```

Lower numeric priorities run first. The built-in specific-format priority is `0.0`; generic converters use `10.0`. For registrations with equal priority, the most recently registered converter is attempted first.

`register_page_converter()` is deprecated.

## Custom Converter

Version 0.1.x converters operate on binary streams and implement both `accepts()` and `convert()`:

```python
from typing import Any, BinaryIO

from markitdown import (
    DocumentConverter,
    DocumentConverterResult,
    StreamInfo,
)


class RtfConverter(DocumentConverter):
    def accepts(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,
    ) -> bool:
        return (stream_info.extension or "").lower() == ".rtf"

    def convert(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,
    ) -> DocumentConverterResult:
        raw = file_stream.read()
        # Replace this placeholder with a real, bounded RTF parser.
        return DocumentConverterResult(
            markdown=f"```text\n{raw.decode('utf-8', errors='replace')}\n```"
        )
```

Do not advance the stream in `accepts()`. If inspection is necessary, save the position with `tell()` and restore it with `seek()`.

## Plugin Package Contract

The plugin module exports interface version 1 and a registration function:

```python
from markitdown import MarkItDown

__plugin_interface_version__ = 1


def register_converters(markitdown: MarkItDown, **kwargs) -> None:
    markitdown.register_converter(RtfConverter())
```

Register the module through `pyproject.toml`:

```toml
[project.entry-points."markitdown.plugin"]
example = "example_markitdown_plugin"
```

Inspect and install a trusted, pinned plugin, then verify discovery:

```bash
markitdown --list-plugins
markitdown --use-plugins input.rtf -o output.md
```

## CLI Reference

```text
markitdown [options] [filename]
```

If `filename` is omitted, MarkItDown reads binary input from stdin.

| Option | Meaning |
|---|---|
| `-v`, `--version` | Print package version |
| `-o`, `--output PATH` | Write UTF-8 Markdown to a file |
| `-x`, `--extension EXT` | File-extension hint |
| `-m`, `--mime-type TYPE` | MIME-type hint |
| `-c`, `--charset NAME` | Charset hint |
| `-d`, `--use-docintel` | Use Azure Document Intelligence |
| `-e`, `--endpoint URL` | Document Intelligence endpoint |
| `--use-cu`, `--use-content-understanding` | Use Azure Content Understanding |
| `--cu-endpoint URL` | Content Understanding endpoint |
| `--cu-analyzer ID` | Custom analyzer ID |
| `--cu-file-types LIST` | Comma-separated CU file types |
| `-p`, `--use-plugins` | Enable installed third-party plugins |
| `--list-plugins` | List discovered plugins and exit |
| `--keep-data-uris` | Preserve full data URIs |

Document Intelligence and Content Understanding are mutually exclusive in one CLI invocation.

The core 0.1.6 parser does **not** expose `--llm-client` or `--llm-model`. Configure image descriptions or the OCR plugin through Python.

## Source Basis

- v0.1.6 package API: https://github.com/microsoft/markitdown/tree/v0.1.6/packages/markitdown/src/markitdown
- v0.1.6 CLI: https://github.com/microsoft/markitdown/blob/v0.1.6/packages/markitdown/src/markitdown/__main__.py
- v0.1.6 sample plugin: https://github.com/microsoft/markitdown/tree/v0.1.6/packages/markitdown-sample-plugin
