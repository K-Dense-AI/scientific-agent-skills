---
name: pinecone
description: Managed vector database for persistent semantic retrieval in scientific RAG pipelines. Use when working with embeddings from scientific literature, multi-omics records, multimodal medical data, or proprietary research corpora that require sub-second similarity search at scale. This is the retrieval persistence skill—for embedding generation use voyage-ai/openai/ESM/MolBERT; for upstream data access use database-lookup, paper-lookup, or biopython.
allowed-tools: Read Write Edit Bash
license: MIT license
metadata:
  skill-author: Muhammad Furqan
---

# Pinecone

## Overview

Pinecone is a managed vector database that provides persistent storage and millisecond-latency similarity search over embeddings. In scientific workflows, it serves as the retrieval layer between embedding models and downstream LLM reasoning — enabling RAG over PubMed/bioRxiv corpora, semantic search over proprietary clinical notes, molecular similarity lookup, and multimodal retrieval over radiology + report pairs.

The repository already provides direct API access to 100+ scientific databases via `database-lookup`, `paper-lookup`, and friends. Pinecone is **not** a replacement for those — it is the persistence layer you reach for when:

- Repeated API queries are too slow or rate-limited for production retrieval
- You need to embed and search proprietary or derived data not in any public database
- Multimodal retrieval (text + image) requires a unified vector store
- A RAG pipeline needs sub-second top-k retrieval over millions of vectors

## When to Use This Skill

Use this skill when:

- Building RAG pipelines grounded in literature, clinical notes, or proprietary research data
- Persisting embeddings from voyage-ai, OpenAI, ESM, MolBERT, BioMedBERT, or other domain models
- Performing semantic similarity search at scale (>100k vectors)
- Combining dense semantic search with sparse keyword search (hybrid) for scientific terminology
- Building multi-tenant scientific platforms requiring namespace isolation per study/organism
- Indexing multimodal scientific data (text + medical images, SMILES + structure images)

**Tested with:** `pinecone>=6.0.0`. Earlier versions (`pinecone-client` v2/v3) had different APIs — pin the version explicitly in production.

## Installation

```bash
# Core SDK
uv pip install "pinecone>=6.0.0"

# For sparse/hybrid search support
uv pip install "pinecone[grpc]>=6.0.0" pinecone-text

# Embedding model companions (choose what you need)
uv pip install voyageai openai sentence-transformers
```

## Quick Start

### Initialize client and create an index

```python
import os
from pinecone import Pinecone, ServerlessSpec

pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])

# Create serverless index (recommended default)
if "scientific-literature" not in [idx.name for idx in pc.list_indexes()]:
    pc.create_index(
        name="scientific-literature",
        dimension=1024,             # Match your embedding model's output
        metric="cosine",            # cosine | dotproduct | euclidean
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )

index = pc.Index("scientific-literature")
```

> **Security:** Always load API keys from environment variables or a secrets manager. The Cisco AI skill scanner will flag hardcoded keys.

### Upsert vectors with scientific metadata

```python
vectors = [
    {
        "id": "pmid_38291847",
        "values": embedding_1024d,  # list[float] of dimension 1024
        "metadata": {
            "title": "CRISPR-based gene editing in oncology",
            "source": "PubMed",
            "year": 2024,
            "disease": "cancer",
            "mesh_terms": ["CRISPR-Cas Systems", "Neoplasms"]
        }
    }
]

index.upsert(vectors=vectors, namespace="oncology")
```

### Query with metadata filtering

```python
results = index.query(
    vector=query_embedding,
    top_k=10,
    namespace="oncology",
    include_metadata=True,
    filter={
        "year": {"$gte": 2022},
        "disease": {"$eq": "cancer"}
    }
)

for match in results["matches"]:
    print(f"{match['score']:.4f}  {match['metadata']['title']}")
```

## Core Capabilities

### 1. Index Management

Choose between serverless (default, scales automatically) and pod-based (predictable throughput) indexes. Match the metric to your embedding type.

| Metric | Best for |
|---|---|
| `cosine` | Normalized text/protein/molecular embeddings (most common) |
| `dotproduct` | **Required** for hybrid (dense + sparse) search |
| `euclidean` | Geometric similarity (image features, coordinates) |

**See:** `references/index_types.md` for serverless vs pod tradeoffs and dimension selection by embedding model.

### 2. Batch Upserting at Scale

Pinecone enforces ≤100 vectors per upsert request and ≤2MB payload. Always batch:

```python
def batch_upsert(index, vectors, namespace="", batch_size=100):
    """Upsert vectors in batches with progress reporting."""
    total_batches = (len(vectors) + batch_size - 1) // batch_size
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i + batch_size]
        index.upsert(vectors=batch, namespace=namespace)
        print(f"Batch {i // batch_size + 1}/{total_batches} upserted")
```

For very large corpora (>1M vectors), use the gRPC client for ~3x faster upsert throughput:

```python
from pinecone.grpc import PineconeGRPC

pc = PineconeGRPC(api_key=os.environ["PINECONE_API_KEY"])
index = pc.Index("my-index")  # Same query API, faster ingest
```

### 3. Namespaces for Scientific Data Isolation

Namespaces are the recommended way to separate logically distinct data within one index:

```python
index.upsert(vectors=human_data,    namespace="homo-sapiens")
index.upsert(vectors=mouse_data,    namespace="mus-musculus")
index.upsert(vectors=compound_data, namespace="drug-compounds")

# Query a specific namespace
results = index.query(vector=q, top_k=5, namespace="homo-sapiens")
```

Common namespace strategies in scientific projects:

- **By organism:** `homo-sapiens`, `mus-musculus`, `e-coli`
- **By data type:** `literature`, `compounds`, `proteins`, `ehr`
- **By study/cohort:** `tcga-brca`, `proton-emas-2024`
- **By environment:** `dev`, `staging`, `production`

### 4. Metadata Filtering

Pinecone supports a MongoDB-style filter syntax: `$eq`, `$ne`, `$gt`, `$gte`, `$lt`, `$lte`, `$in`, `$nin`.

```python
# Recent oncology papers from PubMed
filter = {
    "source":  {"$eq": "PubMed"},
    "year":    {"$gte": 2022},
    "disease": {"$in": ["breast cancer", "lung cancer"]}
}

results = index.query(vector=q, top_k=20, filter=filter, include_metadata=True)
```

**Metadata best practices:**

- Index only filterable fields here — store full text/large blobs in S3 or a relational DB
- Use string, number, boolean, or string-array values (no nested dicts)
- Keep keys consistent across upserts for reliable filtering

### 5. Hybrid Search (Dense + Sparse BM25)

Critical for scientific terminology where exact gene names, compound IDs, or assay types must match. Requires `metric="dotproduct"`.

```python
from pinecone_text.sparse import BM25Encoder

bm25 = BM25Encoder()
bm25.fit(corpus_texts)  # Fit once on your corpus
bm25.dump("bm25_model.json")
```

**See:** `references/hybrid_search.md` for full setup including the alpha-blending query pattern.

### 6. Multimodal Retrieval

For workflows combining text and images — radiology reports + DICOM slices, SMILES + 2D structures, microscopy + experimental notes. Pinecone is embedding-model-agnostic; pair it with `voyage-multimodal-3` or similar:

```python
import voyageai
voyage = voyageai.Client(api_key=os.environ["VOYAGE_API_KEY"])

# voyage-multimodal-3 accepts mixed text + PIL.Image inputs
result = voyage.multimodal_embed(
    inputs=[[report_text, pil_image]],
    model="voyage-multimodal-3",
    input_type="document"
)
embedding = result.embeddings[0]  # 1024-dim, ready to upsert
```

**See:** `references/scientific_embedding_models.md` for a mapping of scientific domains → recommended embedding models with dimensions.

## Common Scientific Workflows

### Workflow 1: PubMed Literature RAG

Index PubMed abstracts and answer scientific questions with grounded citations. Full implementation in `scripts/index_pubmed.py`.

```python
# After indexing (see scripts/index_pubmed.py for ingestion)
def scientific_rag(question: str, namespace: str = "pubmed", top_k: int = 5):
    query_emb = voyage.embed(
        [question], model="voyage-large-2", input_type="query"
    ).embeddings[0]

    results = index.query(
        vector=query_emb, top_k=top_k, namespace=namespace, include_metadata=True
    )

    context = "\n\n---\n\n".join(
        f"[Score: {m['score']:.3f}] {m['metadata']['title']}\n{m['metadata']['abstract']}"
        for m in results["matches"]
    )

    response = oai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content":
                "Answer based only on the provided abstracts. Cite each claim by paper title."},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
        ]
    )
    return response.choices[0].message.content
```

### Workflow 2: Multimodal Radiology + Report Retrieval

Index radiology reports paired with imaging thumbnails for fast case-similarity lookup. Full implementation in `scripts/multimodal_radiology.py`.

```python
# Embed a (report_text, image) pair
inputs = [[report_text, dicom_thumbnail_pil] for report_text, dicom_thumbnail_pil in pairs]
embeddings = voyage.multimodal_embed(
    inputs=inputs, model="voyage-multimodal-3", input_type="document"
).embeddings

vectors = [
    {
        "id": case["id"],
        "values": emb,
        "metadata": {
            "modality":   case["modality"],         # "CT", "MRI", "Xray"
            "body_part":  case["body_part"],
            "finding":    case["finding"],
            "study_uid":  case["study_uid"]
        }
    }
    for case, emb in zip(cases, embeddings)
]

batch_upsert(index, vectors, namespace="radiology")
```

### Workflow 3: Clinical Note Similarity (Bio_ClinicalBERT)

Index EHR notes for patient-similarity retrieval and guideline lookup.

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("emilyalsentzer/Bio_ClinicalBERT")  # 768-dim
embeddings = model.encode(
    [note["text"] for note in notes], batch_size=32, show_progress_bar=True
).tolist()

vectors = [
    {
        "id": note["id"],
        "values": emb,
        "metadata": {
            "patient_id": note["patient_id"],
            "note_type":  note["type"],         # "discharge", "progress", "consult"
            "icd_codes":  note["icd_codes"],
            "department": note["department"]
        }
    }
    for note, emb in zip(notes, embeddings)
]

batch_upsert(index, vectors, namespace="ehr")
```

### Workflow 4: Molecular Similarity Search

Index a compound library and find structurally similar molecules. Pinecone computes cosine similarity over the vector representation — for binary Morgan fingerprints, this approximates but is **not equivalent to** Tanimoto coefficient. If true Tanimoto is required, retrieve top-N candidates via Pinecone then recompute Tanimoto with RDKit downstream.

```python
from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit.DataStructs import TanimotoSimilarity

def smiles_to_morgan(smiles: str, radius: int = 2, n_bits: int = 1024):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)

def find_similar_compounds(query_smiles: str, top_k: int = 50, rerank_top: int = 10):
    """Two-stage: Pinecone for fast recall, RDKit Tanimoto for precise rerank."""
    query_fp = smiles_to_morgan(query_smiles)
    if query_fp is None:
        raise ValueError(f"Invalid SMILES: {query_smiles}")

    # Stage 1: fast vector recall
    candidates = index.query(
        vector=list(query_fp), top_k=top_k,
        namespace="compounds", include_metadata=True
    )

    # Stage 2: precise Tanimoto rerank
    reranked = []
    for match in candidates["matches"]:
        cand_fp = smiles_to_morgan(match["metadata"]["smiles"])
        if cand_fp is not None:
            tanimoto = TanimotoSimilarity(query_fp, cand_fp)
            reranked.append((tanimoto, match["metadata"]))

    return sorted(reranked, reverse=True)[:rerank_top]
```

## Index Operations Reference

```python
# Fetch by ID
fetched = index.fetch(ids=["pmid_38291847"], namespace="pubmed")

# Update metadata
index.update(id="pmid_38291847", set_metadata={"reviewed": True}, namespace="pubmed")

# Delete vectors
index.delete(ids=["pmid_001", "pmid_002"], namespace="pubmed")
index.delete(delete_all=True, namespace="staging")  # Clear a namespace

# Stats
stats = index.describe_index_stats()
print(f"Total: {stats['total_vector_count']}")
for ns, info in stats["namespaces"].items():
    print(f"  {ns}: {info['vector_count']}")
```

## Integration with Other Skills

- **paper-lookup** — retrieve abstracts → embed → upsert to Pinecone for persistent literature RAG
- **database-lookup** — pull records from any of 78 public databases → embed → index for offline retrieval
- **biopython / pysam** — extract sequences/variants → embed with domain models → similarity search
- **scanpy** — embed cell representations → retrieve similar cell populations across datasets
- **paper-lookup + scientific-writing** — RAG-grounded literature review and writing pipeline
- **pyhealth** — patient feature vectors → similarity-based outcome prediction

## Troubleshooting

**Dimension mismatch on upsert** — Verify embedding dimension matches index dimension. Common cause: switching embedding models without recreating the index.

```python
emb = model.embed("test")
print(f"Embedding dim: {len(emb)}, Index dim: {pc.describe_index('my-index').dimension}")
```

**Low retrieval quality** —
- Confirm `input_type="query"` when embedding queries vs `"document"` for corpus (voyage, cohere)
- Verify metadata filters aren't over-restrictive
- Try hybrid search if exact terminology (gene names, compound IDs) is being missed
- Consider re-ranking top-50 candidates with a cross-encoder downstream

**Slow upsert for large corpora** — Switch to `PineconeGRPC` client; parallelize across namespaces; ensure batches are ≤100 vectors.

**Rate limits hit during ingestion** — Pinecone serverless has generous limits but voyage-ai/OpenAI embedding APIs may rate-limit first. Use exponential backoff or batch embedding requests.

## Resources

- **Pinecone Docs**: https://docs.pinecone.io
- **Python SDK**: https://github.com/pinecone-io/pinecone-python-client
- **Voyage AI (multimodal embeddings)**: https://docs.voyageai.com
- **pinecone-text (sparse/BM25)**: https://github.com/pinecone-io/pinecone-text
- **Agent Skills Standard**: https://agentskills.io
