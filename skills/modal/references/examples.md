# Modal Common Examples

Reviewed against Modal 1.6.0. These are **illustrative cloud workload templates**:
SDK registration and selected local handlers were checked, but container builds,
GPU jobs, weights and database writes were not executed. Package pins are examples,
not a validated combined environment. Resolve a lockfile per workload and record the
model revision, hardware, seeds and input provenance before a scientific run.
External helpers such as `transform()` are application-defined.

## LLM Inference Service (vLLM)

```python
import modal

app = modal.App("vllm-service")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .uv_pip_install("vllm==0.21.0", "fastapi[standard]==0.136.3")
)

@app.cls(gpu="H100", image=image, max_containers=1)
class LLMService:
    @modal.enter()
    def load(self):
        from vllm import LLM
        self.llm = LLM(model="Qwen/Qwen3-8B", max_model_len=4096)

    @modal.method()
    def generate(self, prompt: str, max_tokens: int = 512) -> str:
        from vllm import SamplingParams
        params = SamplingParams(max_tokens=max_tokens, temperature=0.7)
        outputs = self.llm.generate([prompt], sampling_params=params)
        return outputs[0].outputs[0].text

    @modal.fastapi_endpoint(method="POST", requires_proxy_auth=True)
    def api(self, request: dict):
        text = self.generate.local(request["prompt"], request.get("max_tokens", 512))
        return {"text": text}
```

[vLLM `LLM.generate`](https://docs.vllm.ai/en/latest/serving/offline_inference/) uses
`SamplingParams`; `max_tokens` is not a `generate()` keyword. This template accepts
a preformatted completion prompt. Apply the model's chat template for chat messages.
Use your Proxy Token to call the endpoint. A 70B BF16 model does not fit one H100;
GPU capacity must include weights and KV cache, not just parameter count.

## Image Generation (Flux)

```python
import modal

app = modal.App("image-gen")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .uv_pip_install(
        "diffusers==0.38.0",
        "torch==2.12.0",
        "transformers==5.9.0",
        "accelerate==1.13.0",
    )
)

vol = modal.Volume.from_name("flux-weights", create_if_missing=True)

@app.cls(gpu="L40S", image=image, volumes={"/models": vol})
class ImageGenerator:
    @modal.enter()
    def load(self):
        import torch
        from diffusers import FluxPipeline
        self.pipe = FluxPipeline.from_pretrained(
            "black-forest-labs/FLUX.1-schnell",
            torch_dtype=torch.bfloat16,
            cache_dir="/models",
        ).to("cuda")
        vol.commit()

    @modal.method()
    def generate(self, prompt: str) -> bytes:
        image = self.pipe(prompt, num_inference_steps=4, guidance_scale=0.0).images[0]
        import io
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return buf.getvalue()
```

## Speech Transcription (Whisper)

The audio path must exist inside the container. Upload it to the named Volume
first; passing a local laptop path does not transfer audio.

```python
import modal

app = modal.App("transcription")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg")
    .uv_pip_install("openai-whisper==20250625", "torch==2.12.0")
)

audio_vol = modal.Volume.from_name("audio-data", create_if_missing=True)

@app.cls(gpu="T4", image=image, volumes={"/audio": audio_vol})
class Transcriber:
    @modal.enter()
    def load(self):
        import whisper
        self.model = whisper.load_model("large-v3")

    @modal.method()
    def transcribe(self, audio_path: str) -> dict:
        audio_vol.reload()
        return self.model.transcribe(audio_path)
```

## Batch Data Processing

```python
import modal

app = modal.App("batch-processor")

image = modal.Image.debian_slim().uv_pip_install("pandas", "pyarrow")
vol = modal.Volume.from_name("batch-data", create_if_missing=True)

@app.function(image=image, volumes={"/data": vol}, cpu=4.0, memory=8192)
def process_chunk(chunk_id: int) -> dict:
    import pandas as pd
    from pathlib import Path
    from uuid import uuid4
    vol.reload()
    df = pd.read_parquet(f"/data/input/chunk_{chunk_id:04d}.parquet")
    result = df.groupby("category").agg({"value": ["sum", "mean", "count"]})
    output_dir = Path("/data/output") / uuid4().hex
    output_dir.mkdir(parents=True)
    output = output_dir / f"result_{chunk_id:04d}.parquet"
    result.to_parquet(output)
    vol.commit()
    return {"chunk_id": chunk_id, "rows": len(df), "output": str(output)}

@app.local_entrypoint()
def main():
    chunk_ids = list(range(500))
    results = list(process_chunk.map(chunk_ids))
    total = sum(r["rows"] for r in results)
    print(f"Processed {total} total rows across {len(results)} chunks")
```

## Web Scraping at Scale

```python
import modal

app = modal.App("scraper")

image = modal.Image.debian_slim().uv_pip_install("httpx", "beautifulsoup4")

@app.function(image=image, retries=3, timeout=60)
def scrape_url(url: str) -> dict:
    import httpx
    from bs4 import BeautifulSoup
    response = httpx.get(url, follow_redirects=True, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    return {
        "url": url,
        "title": soup.title.string if soup.title else None,
        "text": soup.get_text()[:5000],
    }

@app.local_entrypoint()
def main():
    urls = ["https://example.com", "https://example.org"]  # Your URL list
    results = list(scrape_url.map(urls))
    for r in results:
        print(f"{r['url']}: {r['title']}")
```

## Protein Structure Prediction

```python
import modal

app = modal.App("protein-folding")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .uv_pip_install("chai-lab")
)

vol = modal.Volume.from_name("protein-data", create_if_missing=True)

@app.function(gpu="A100-80GB", image=image, volumes={"/data": vol}, timeout=3600)
def fold_protein(sequence: str) -> list[str]:
    from pathlib import Path
    from uuid import uuid4
    from chai_lab.chai1 import run_inference
    if not sequence or any(c not in "ACDEFGHIKLMNPQRSTVWY" for c in sequence):
        raise ValueError("Provide one non-empty canonical protein sequence")
    run_dir = Path("/data/runs") / uuid4().hex
    run_dir.mkdir(parents=True)
    fasta = run_dir / "input.fasta"
    fasta.write_text(f">protein|name=target\n{sequence}\n")
    candidates = run_inference(
        fasta_file=fasta,
        output_dir=run_dir / "predictions",
        use_msa_server=False,
        use_templates_server=False,
        seed=42,
        device="cuda:0",
    )
    vol.commit()
    return [str(path) for path in candidates.cif_paths]
```

The [Chai API](https://github.com/chaidiscovery/chai-lab/blob/main/chai_lab/chai1.py)
accepts `Path` objects and returns `StructureCandidates`, not an output filename.
Server-based MSA/template search is disabled here; enabling it sends sequence data
to another service. Predicted structures and confidence scores require scientific
validation; they are not experimental evidence.

## Scheduled ETL Pipeline

```python
import modal

app = modal.App("etl")

image = modal.Image.debian_slim().uv_pip_install("pandas", "sqlalchemy", "psycopg2-binary")

@app.function(
    image=image,
    schedule=modal.Cron("0 3 * * *"),  # 3 AM UTC daily
    secrets=[modal.Secret.from_name("database-creds")],
    timeout=7200,
)
def daily_etl():
    import os
    import pandas as pd
    from sqlalchemy import create_engine

    source = create_engine(os.environ["SOURCE_DB"])
    dest = create_engine(os.environ["DEST_DB"])

    df = pd.read_sql("SELECT * FROM events WHERE date = CURRENT_DATE - 1", source)
    df = transform(df)
    # Illustrative append: add a date/run key and transactional upsert in production
    # so redeploys, retries or manual reruns cannot duplicate observations.
    df.to_sql("daily_summary", dest, if_exists="append", index=False)
    print(f"Loaded {len(df)} rows")
```

## FastAPI with GPU Model

```python
import modal

app = modal.App("api-with-gpu")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .uv_pip_install("fastapi[standard]==0.136.3", "sentence-transformers==5.5.1", "torch==2.12.0")
)

@app.cls(gpu="L40S", image=image, min_containers=1)
class EmbeddingService:
    @modal.enter()
    def load(self):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer("all-MiniLM-L6-v2", device="cuda")

    @modal.asgi_app(requires_proxy_auth=True)
    def serve(self):
        from fastapi import FastAPI
        api = FastAPI()

        @api.post("/embed")
        def embed(request: dict):
            embeddings = self.model.encode(request["texts"])
            return {"embeddings": embeddings.tolist()}

        @api.get("/health")
        async def health():
            return {"status": "ok"}

        return api
```

## Document OCR Job Queue

```python
import modal

app = modal.App("ocr-queue")

image = modal.Image.debian_slim().uv_pip_install("pytesseract", "Pillow").apt_install("tesseract-ocr")
vol = modal.Volume.from_name("ocr-data", create_if_missing=True)

@app.function(image=image, volumes={"/data": vol})
def ocr_page(image_path: str) -> str:
    import pytesseract
    from PIL import Image
    vol.reload()
    with Image.open(image_path) as img:
        return pytesseract.image_to_string(img)

@app.function(volumes={"/data": vol})
def process_document(doc_id: str):
    import os
    from uuid import uuid4
    if not doc_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in doc_id):
        raise ValueError("Invalid document ID")
    vol.reload()
    pages = sorted(os.listdir(f"/data/docs/{doc_id}/"))
    paths = [f"/data/docs/{doc_id}/{p}" for p in pages]
    texts = list(ocr_page.map(paths))
    full_text = "\n\n".join(texts)
    os.makedirs("/data/results", exist_ok=True)
    output = f"/data/results/{doc_id}-{uuid4().hex}.txt"
    with open(output, "w") as f:
        f.write(full_text)
    vol.commit()
    return {"doc_id": doc_id, "pages": len(texts), "output": output}
```

Additional upstream contracts reviewed: [FLUX](https://huggingface.co/docs/diffusers/api/pipelines/flux),
[Whisper](https://github.com/openai/whisper), [Sentence Transformers](https://sbert.net/docs/quickstart.html).
For pretrained weights, verify licensing/access and pin revisions; the GPU examples
remain unexecuted and do not establish numerical reproducibility or performance.
