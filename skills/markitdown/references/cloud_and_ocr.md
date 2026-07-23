# Vision, OCR, and Azure Extraction

This guide distinguishes four different features that are often conflated:

1. Built-in image metadata/description
2. Official `markitdown-ocr` vision plugin
3. Azure Document Intelligence
4. Azure Content Understanding

All examples target MarkItDown 0.1.6.

## Decision Guide

| Requirement | Best fit |
|---|---|
| Describe a standalone JPEG/PNG or images on PPTX slides | Built-in `llm_client` path |
| Read text from PDF/DOCX/PPTX/XLSX embedded images | `markitdown-ocr` |
| OCR scanned PDFs with Azure layout extraction | Document Intelligence |
| Custom fields, YAML front matter, video, or richer multimodal analysis | Content Understanding |
| Data must remain local | Use a separate local OCR/layout parser |

None of the first four options is a local Tesseract workflow.

## Data-Handling Rule

Before using an external service:

- Identify the exact provider, endpoint, region, account, and model/analyzer.
- Tell the user which source bytes, images, audio, video, and prompts will leave the machine.
- Confirm that the provider is approved for the source's classification and regulatory requirements.
- Estimate cost and retention implications.
- Send only the required files/pages.
- Never log API keys, bearer tokens, source bytes, or full base64 payloads.

## Built-in Image Descriptions

The built-in JPEG/PNG and PPTX paths can call an OpenAI-compatible client. MarkItDown encodes image bytes as a data URI and calls:

```text
client.chat.completions.create(model=..., messages=...)
```

Install a reviewed client version:

```bash
uv pip install "markitdown[pptx]==0.1.6" "openai==2.41.1"
```

```python
from markitdown import MarkItDown
from openai import OpenAI

# The SDK obtains only its named provider credential through its normal
# configuration. The image and prompt are sent to that provider.
client = OpenAI()

converter = MarkItDown(
    llm_client=client,
    llm_model="gpt-4o",
    llm_prompt=(
        "Describe the scientific figure. Transcribe visible labels, identify "
        "axes and units, and report trends without inventing missing values."
    ),
)

result = converter.convert_local("figure.png")
print(result.markdown)
```

Use a provider/model approved by the user; model identifiers and availability are provider-specific.

### Limitations

- Built-in image conversion accepts JPEG and PNG.
- Without ExifTool or an LLM client, output can be empty.
- A description is not guaranteed OCR or quantitative chart extraction.
- Generated descriptions can hallucinate labels, values, or relationships.
- Always compare critical claims with the original image.

## Official `markitdown-ocr` Plugin

Version 0.1.6 introduced the official monorepo plugin. The published plugin version is 0.1.0.

Install exact versions:

```bash
uv pip install \
  "markitdown==0.1.6" \
  "markitdown-ocr==0.1.0" \
  "openai==2.41.1"
```

Review discovery before activation:

```bash
markitdown --list-plugins
```

Configure through Python:

```python
from markitdown import MarkItDown
from openai import OpenAI

converter = MarkItDown(
    enable_plugins=True,
    llm_client=OpenAI(),
    llm_model="gpt-4o",
    llm_prompt=(
        "Extract all visible text exactly. Preserve table rows, columns, "
        "symbols, signs, decimal points, and units. Do not summarize."
    ),
)

result = converter.convert_local("scanned-paper.pdf")
print(result.markdown)
```

### Supported plugin paths

- PDF embedded images, interleaved by page position
- Full-page rendering fallback for scanned PDF pages without extractable text
- PyMuPDF rendering fallback for some malformed PDFs
- DOCX embedded images
- PPTX image shapes, placeholders, and grouped images
- XLSX worksheet images

OCR blocks are inserted using markers similar to:

```text
*[Image OCR]
<extracted text>
[End OCR]*
```

### Operational behavior

- The plugin registers enhanced converters at priority `-1.0`, ahead of built-ins.
- Every selected image/page can become a separate provider call.
- If a provider call fails, conversion can continue without that image's OCR.
- If no `llm_client` is supplied, the plugin loads but silently falls back to standard conversion.
- Large scanned documents can be expensive and slow because pages are rendered at 300 DPI.

### CLI discrepancy in 0.1.6

The plugin README shows `--llm-client` and `--llm-model`, but MarkItDown 0.1.6's core CLI parser does not define those options. Use the Python API above rather than copying that CLI example.

## Azure Document Intelligence

Install:

```bash
uv pip install "markitdown[az-doc-intel]==0.1.6"
```

The converter sends the complete file to Azure's `prebuilt-layout` analyzer and requests Markdown output. For PDF/images it enables formula extraction, high-resolution OCR, and font-style analysis.

### Authentication

If no explicit credential is supplied, MarkItDown:

1. Uses the named `AZURE_API_KEY` value with `AzureKeyCredential` when present.
2. Otherwise uses `DefaultAzureCredential`.

Prefer workload identity, managed identity, or another `DefaultAzureCredential` source over long-lived keys.

### CLI

```bash
markitdown report.pdf \
  --use-docintel \
  --endpoint "https://RESOURCE.cognitiveservices.azure.com/" \
  -o report.md
```

The CLI requires a filename; stdin is not accepted with this mode.

### Python

```python
from azure.identity import DefaultAzureCredential
from markitdown import MarkItDown

converter = MarkItDown(
    docintel_endpoint="https://RESOURCE.cognitiveservices.azure.com/",
    docintel_credential=DefaultAzureCredential(),
)

result = converter.convert_local("report.pdf")
print(result.markdown)
```

Restrict routing:

```python
from markitdown import MarkItDown
from markitdown.converters import DocumentIntelligenceFileType

converter = MarkItDown(
    docintel_endpoint="https://RESOURCE.cognitiveservices.azure.com/",
    docintel_file_types=[
        DocumentIntelligenceFileType.PDF,
        DocumentIntelligenceFileType.PNG,
    ],
)
```

Supported enum values include DOCX, PPTX, XLSX, HTML, PDF, JPEG, PNG, BMP, and TIFF. The default list excludes HTML.

The 0.1.6 default Document Intelligence API version is `2024-07-31-preview`; override it with `docintel_api_version` only after checking Azure compatibility.

## Azure Content Understanding

Install:

```bash
uv pip install "markitdown[az-content-understanding]==0.1.6"
```

Content Understanding provides:

- Document/image/audio/video analyzers
- Prebuilt analyzer auto-routing
- Optional custom analyzers
- Structured fields serialized as YAML front matter
- One endpoint across supported modalities

Every routed `convert()`/`convert_local()` call is an Azure API call and may be billable.

### CLI

```bash
markitdown interview.mp4 \
  --use-cu \
  --cu-endpoint "https://RESOURCE.cognitiveservices.azure.com/" \
  --cu-file-types mp4 \
  -o interview.md
```

With a custom analyzer:

```bash
markitdown invoice.pdf \
  --use-cu \
  --cu-endpoint "https://RESOURCE.cognitiveservices.azure.com/" \
  --cu-analyzer "my-invoice-analyzer" \
  --cu-file-types pdf \
  -o invoice.md
```

### Python

```python
from azure.identity import DefaultAzureCredential
from markitdown import MarkItDown
from markitdown.converters import ContentUnderstandingFileType

converter = MarkItDown(
    cu_endpoint="https://RESOURCE.cognitiveservices.azure.com/",
    cu_credential=DefaultAzureCredential(),
    cu_file_types=[
        ContentUnderstandingFileType.PDF,
        ContentUnderstandingFileType.PNG,
    ],
)

result = converter.convert_local("report.pdf")
print(result.markdown)
```

Custom analyzer:

```python
converter = MarkItDown(
    cu_endpoint="https://RESOURCE.cognitiveservices.azure.com/",
    cu_credential=DefaultAzureCredential(),
    cu_analyzer_id="my-contract-analyzer",
    cu_file_types=[ContentUnderstandingFileType.PDF],
)
```

When the custom analyzer's modality is incompatible with an input, the converter falls back to the matching prebuilt analyzer.

### Default prebuilt routing

| Modality | Analyzer |
|---|---|
| Document | `prebuilt-documentSearch` |
| Image | `prebuilt-documentSearch` |
| Audio | `prebuilt-audioSearch` |
| Video | `prebuilt-videoSearch` |

## Choosing Between Azure Services

| Capability | Built-in | Document Intelligence | Content Understanding |
|---|---|---|---|
| Local text extraction | Yes | No | No |
| Scanned PDF OCR | No | Yes | Yes |
| Office conversion | Yes | Yes | Yes |
| Structured custom fields | No | Not exposed by this integration | Yes |
| Video | No | No | Yes |
| Custom analyzer | No | Not exposed by this integration | Yes |
| YAML field front matter | No | No | Yes |
| External cost | No for local-only paths | Yes | Yes |

## Validation for OCR/Cloud Output

1. Record the package/plugin version, provider, model/analyzer, endpoint region, and date.
2. Compare a sample of pages against the source.
3. Check minus signs, decimal points, Greek letters, superscripts, units, and table boundaries.
4. Flag uncertain or illegible spans instead of silently normalizing them.
5. Reconcile page counts and section headings.
6. Keep the original artifact and provider response provenance.

## Sources

- MarkItDown 0.1.6 guide: https://github.com/microsoft/markitdown/blob/v0.1.6/README.md
- OCR plugin 0.1.0: https://github.com/microsoft/markitdown/tree/v0.1.6/packages/markitdown-ocr
- Document Intelligence converter: https://github.com/microsoft/markitdown/blob/v0.1.6/packages/markitdown/src/markitdown/converters/_doc_intel_converter.py
- Content Understanding converter: https://github.com/microsoft/markitdown/blob/v0.1.6/packages/markitdown/src/markitdown/converters/_cu_converter.py
