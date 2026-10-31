# Choosing a Document Parser

LiteParse **2.15.0** supports text, JSON and Markdown locally. Do not route away
from it solely because the consumer wants Markdown.

| Need | Suitable path |
|---|---|
| Text boxes, page PNGs, local PDF/Office/image parsing | LiteParse |
| Heuristic Markdown from PDFs or converted Office files | LiteParse; visually inspect complex layouts |
| HTML, EPUB, audio or other formats outside LiteParse's supported inputs | Review the `markitdown` skill and its converter dependencies |
| Merge/split/rotate, watermark or fill PDF forms | A PDF manipulation library such as `pypdf` |
| Local extraction fails on dense tables, handwriting or hard scans | Review LlamaParse cloud capabilities, document-sharing authorization and pricing separately |

LiteParse's HTTP OCR is optional and may send rasterized pages to a remote
server. Its bundled Tesseract can download missing language files. A local
parser therefore does not imply a network-free first run.

For layout-aware RAG, store page number, page dimensions and bounding boxes
alongside text; pair the same pages/settings with screenshots. For Markdown,
use `output_format="markdown"` directly and inspect headings, tables, equations,
units and references. No local heuristic parser guarantees faithful scientific
transcription or chart-data recovery.

The general comparison does not certify another parser's current format matrix
or output fidelity. See its own skill/docs before execution. LlamaParse is a
separate cloud service, not an endpoint or drop-in credential for LiteParse's
HTTP OCR contract.

Reviewed 2026-10-01:
[LiteParse overview](https://developers.llamaindex.ai/liteparse/),
[released LiteParse README](https://github.com/run-llama/liteparse/blob/d3a79177b9e9e570f8c2d9878ace601445fdaf76/README.md),
[LlamaParse overview](https://developers.llamaindex.ai/llamaparse/parse/).
