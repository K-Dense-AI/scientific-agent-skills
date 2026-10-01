# Vision, OCR, and Azure Extraction

This guide distinguishes four different features that are often conflated:

1. Built-in image metadata/description
2. Official `markitdown-ocr` vision plugin
3. Azure Document Intelligence
4. Azure Content Understanding

All examples target MarkItDown 0.1.8. Hosted examples are illustrative: October 1, 2026 verification used installed SDKs, official source, and synthetic mocked requests, not authenticated service calls.

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
uv pip install "markitdown[pptx]==0.1.8" "openai==3.22.1"
```

```python
import os

from markitdown import MarkItDown
from openai import OpenAI

# The SDK obtains only its named provider credential through its normal
# configuration. The image and prompt are sent to that provider.
client = OpenAI()

converter = MarkItDown(
    llm_client=client,
    llm_model=os.environ["MARKITDOWN_VISION_MODEL"],
    llm_prompt=(
        "Describe the scientific figure. Transcribe visible labels, identify "
        "axes and units, and report trends without inventing missing values."
    ),
)

result = converter.convert_local("figure.png")
print(result.markdown)
```

Set `MARKITDOWN_VISION_MODEL` to an approved model supporting image input on Chat Completions. This variable belongs to the example, not MarkItDown itself. Client/model availability is provider-specific. With `OpenAI()`, the SDK reads `OPENAI_API_KEY` and sends `POST https://api.openai.com/v1/chat/completions` using bearer authentication. The body contains `model` and one user message with `text` plus `image_url.url="data:image/png;base64,..."`; MarkItDown reads `choices[0].message.content`. It does not use the image-generation or Responses endpoints. Empty/refused responses require explicit quality checks.

### Limitations

- Built-in image conversion accepts JPEG and PNG.
- Without ExifTool or an LLM client, output can be empty.
- A description is not guaranteed OCR or quantitative chart extraction.
- Generated descriptions can hallucinate labels, values, or relationships.
- Always compare critical claims with the original image.

## Official `markitdown-ocr` Plugin

Core 0.1.6 introduced the official monorepo plugin. The current plugin is 0.1.1 and requires `markitdown>=0.1.8,<0.2.0`; it reuses the core Office image-rendering hooks.

Install exact versions:

```bash
uv pip install \
  "markitdown==0.1.8" \
  "markitdown-ocr==0.1.1" \
  "openai==3.22.1"
```

Review discovery before activation:

```bash
markitdown --list-plugins
```

Configure through Python:

```python
import os

from markitdown import MarkItDown
from openai import OpenAI

converter = MarkItDown(
    enable_plugins=True,
    llm_client=OpenAI(),
    llm_model=os.environ["MARKITDOWN_VISION_MODEL"],
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
- PPTX image shapes, placeholders, and grouped images: native LLM captions run first; OCR is the fallback when no caption is returned
- XLSX worksheet images after each sheet's table, not interleaved with cell rows; legacy XLS has no image OCR

OCR blocks are inserted using markers similar to:

```text
*[Image OCR]
<extracted text>
[End OCR]*
```

### Operational behavior

- The plugin registers enhanced converters at priority `-1.0`, ahead of built-ins.
- Selected images/pages can become provider calls. Office OCR caches repeated image bytes per conversion; native PPTX caption calls precede that OCR cache. Do not assume one call per document.
- If a provider call fails, conversion can continue without that image's OCR.
- If no `llm_client` is supplied, the plugin loads but silently falls back to standard conversion.
- Large scanned documents can be expensive and slow because pages are rendered at 300 DPI.

### CLI discrepancy in 0.1.8

The plugin README shows `--llm-client` and `--llm-model`, but MarkItDown 0.1.8's core CLI parser does not define those options. Use the Python API above rather than copying that CLI example.

## Azure Document Intelligence

Install:

```bash
uv pip install "markitdown[az-doc-intel]==0.1.8"
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

MarkItDown 0.1.8 sets `docintel_api_version=None` by default and lets the installed SDK choose. Tested `azure-ai-documentintelligence==1.0.2` uses `2024-11-30`; set `docintel_api_version="2024-11-30"` for an explicit service pin. The CLI has no API-version flag. Its endpoint also accepts `MARKITDOWN_DOCINTEL_ENDPOINT` as a fallback.

The SDK submits `POST {endpoint}/documentintelligence/documentModels/prebuilt-layout:analyze?api-version=2024-11-30` with a JSON `base64Source` (serialized from `AnalyzeDocumentRequest(bytes_source=...)`), `outputContentFormat=markdown`, and applicable `features`. It polls the response's `Operation-Location` after HTTP 202 and returns `AnalyzeResult.content`. The converter removes HTML comments, including page comments: keep separate page provenance when required. API-key authentication uses `Ocp-Apim-Subscription-Key`; token credentials use the Azure Cognitive Services scope.

## Azure Content Understanding

Install:

```bash
uv pip install "markitdown[az-content-understanding]==0.1.8" "azure-ai-contentunderstanding==1.2.0b3"
```

This core release requires `azure-ai-contentunderstanding>=1.2.0b1` for the
`to_llm_input()` helper. The tested 1.2.0b3 SDK defaults to service API
`2026-06-01-preview`. MarkItDown exposes **no `cu_api_version` option** and
constructs the SDK client itself; passing that unknown keyword does not pin the
API. If GA-only service API `2025-11-01` is required, use the Azure SDK directly
with an explicit API version and `to_llm_input()` instead of claiming this
MarkItDown wrapper is pinned to GA.

Use the exact Foundry resource endpoint from Azure (typically
`https://RESOURCE.services.ai.azure.com/`). Provision model deployments and the
required prebuilt-analyzer model aliases on that resource before conversion;
MarkItDown does not configure deployments or default model mappings.

Content Understanding provides:

- Document/image/audio/video analyzers
- Prebuilt analyzer auto-routing
- Optional custom analyzers
- Structured fields serialized as YAML front matter
- One endpoint across supported modalities

Every routed `convert()`/`convert_local()` call is an Azure API call and may be billable. An unknown/custom analyzer also triggers `get_analyzer()` during construction to resolve modality; known prebuilt IDs use the local routing table. Credentials follow the same explicit credential / `AZURE_API_KEY` / `DefaultAzureCredential` order as Document Intelligence.

### CLI

```bash
markitdown interview.mp4 \
  --use-cu \
  --cu-endpoint "https://RESOURCE.services.ai.azure.com/" \
  --cu-file-types mp4 \
  -o interview.md
```

With a custom analyzer:

```bash
markitdown invoice.pdf \
  --use-cu \
  --cu-endpoint "https://RESOURCE.services.ai.azure.com/" \
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
    cu_endpoint="https://RESOURCE.services.ai.azure.com/",
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
    cu_endpoint="https://RESOURCE.services.ai.azure.com/",
    cu_credential=DefaultAzureCredential(),
    cu_analyzer_id="my-contract-analyzer",
    cu_file_types=[ContentUnderstandingFileType.PDF],
)
```

When the custom analyzer's modality is incompatible with an input, the converter falls back to the matching prebuilt analyzer.

### SDK request contract

For the tested SDK, `begin_analyze_binary(analyzer_id=..., binary_input=bytes,
content_type=...)` submits `POST {endpoint}/contentunderstanding/analyzers/{id}:analyzeBinary?api-version=2026-06-01-preview` with the actual file bytes and a matching media type. An HTTP 202 result is polled using `Operation-Location`; the result is formatted with `to_llm_input(result)`, including available fields, warnings, and page/time metadata. Unknown analyzer lookup is `GET {endpoint}/contentunderstanding/analyzers/{id}` with the same API version. These are single operations/polling, not paginated list calls. The SDK controls retries and polling; the wrapper does not expose response objects or per-call polling settings.

The CLI accepts `MARKITDOWN_CU_ENDPOINT` as its endpoint fallback and supports binary stdin with format hints. It does not expose an LLM/model/API-version flag.

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

- MarkItDown 0.1.8 guide: https://github.com/microsoft/markitdown/blob/v0.1.8/README.md
- OCR plugin 0.1.1: https://github.com/microsoft/markitdown/tree/v0.1.8/packages/markitdown-ocr
- Document Intelligence converter: https://github.com/microsoft/markitdown/blob/v0.1.8/packages/markitdown/src/markitdown/converters/_doc_intel_converter.py
- Content Understanding converter: https://github.com/microsoft/markitdown/blob/v0.1.8/packages/markitdown/src/markitdown/converters/_cu_converter.py

- OpenAI Chat Completions contract: https://developers.openai.com/api/reference/resources/chat
- Azure Document Intelligence analyze: https://learn.microsoft.com/en-us/rest/api/aiservices/document-models/analyze-document?view=rest-aiservices-v4.0+(2024-11-30)
- Azure CU SDK versions/setup: https://learn.microsoft.com/en-us/python/api/overview/azure/ai-contentunderstanding-readme?view=azure-python-preview
- Azure CU SDK source (preview contract): https://github.com/Azure/azure-sdk-for-python/tree/azure-ai-contentunderstanding_1.2.0b3/sdk/contentunderstanding/azure-ai-contentunderstanding
