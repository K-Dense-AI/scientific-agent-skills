# scEmbed

Verified against `geniml==0.8.4` release source, current Gtars
`0.10.0`, and official BEDbase documentation on 2026-10-01.

## Scope and evidence

scEmbed learns region embeddings from scATAC-seq accessibility and pools them
to represent cells. The primary paper reports that pre-trained region
embeddings can support clustering and transfer to unseen datasets. Do not turn
that result into a universal accuracy claim; performance depends on assay,
reference corpus, universe, filtering, cell types, and split design.

Primary source: LeRoy et al. (2024), *Fast clustering and cell-type annotation
of scATAC data with pre-trained embeddings*,
doi:[10.1093/nargab/lqae073](https://doi.org/10.1093/nargab/lqae073).

## Stable API and known drift

Use:

```python
from geniml.scembed.main import ScEmbed
from geniml.region2vec.utils import Region2VecDataset
from gtars.tokenizers import Tokenizer
```

Do not use `from geniml.scembed import ScEmbed`: the 0.8.4 package
`__init__` does not export it. The installed `geniml scembed` command parses
legacy MatrixMarket options but its 0.8.4 command body does no training or
encoding.

With Geniml 0.8.4 / Gtars 0.10.0, both `tokenize_anndata` and
`ScEmbed.encode` fail: Geniml omits the required fourth `Region(..., rest)`
argument. Even after that is fixed, `ScEmbed.encode` assumes an extra nesting
level that the tokenizer does not return. Use the explicit recipe below; it
was tested on small synthetic cells, including cell-order and pooling checks.
The environment must keep AnnData 0.12.19 and Zarr 2.18.7; AnnData 0.13's
Zarr >=3 requirement conflicts with Geniml.

## AnnData contract

The AnnData object must satisfy:

- rows (`obs`) are cells;
- columns (`var`) are accessible regions/features;
- `var["chr"]`, `var["start"]`, and `var["end"]` describe each feature;
- coordinates are validated 0-based half-open BED coordinates;
- all features use one declared assembly and contig convention;
- `X` is sparse CSR for bounded tokenization performance;
- duplicate feature coordinates and duplicate barcodes have an explicit policy.

Confirm matrix orientation. A 10x peak-by-barcode MatrixMarket file is often
transposed when constructing AnnData; inspect dimensions instead of copying a
blind `.T`.

Do not expose barcodes, patient IDs, phenotypes, rare cell labels, or raw
intervals in logs. An `.h5ad` may contain identifying metadata in `obs`,
`uns`, embeddings, and file provenance. Output only bounded aggregate counts
unless the user explicitly approves disclosure.

## Leakage-safe split order

Split before fitting or selecting anything:

1. Group cells by patient/donor and biological replicate.
2. Assign complete groups to train/validation/test.
3. Fit QC thresholds, feature/universe selection, token vocabulary, model,
   annotation references, and hyperparameters on training data only.
4. Apply the frozen universe/tokenizer/model to validation and test.
5. Keep technical replicates and multiple samples from one patient together.

Randomly splitting cells from the same donor leaks donor- and batch-specific
accessibility. Building a consensus universe from all patients can also leak
test-set feature prevalence even when labels are hidden.

Audit a local manifest without printing metadata values:

```bash
python skills/geniml/scripts/corpus_auditor.py \
  --manifest data/cells.tsv \
  --group-column patient_id \
  --split-column split \
  --assembly-column assembly
```

## Build and validate the tokenizer

Use a local, checksummed universe from the training partition:

```python
from gtars.tokenizers import Tokenizer

tokenizer = Tokenizer.from_bed("refs/training_universe.bed")
```

Record:

- source cohort and split;
- assembly, chromosome sizes, coordinate/contig/strand policy;
- universe SHA-256, row order, and row count;
- Gtars version and special-token map/IDs;
- `len(tokenizer)`.

Gtars 0.10.0 `Tokenizer.from_pretrained(path)` accepts only a path argument;
it provides no revision/cache kwargs. For an authorized Hub download, fetch
the exact universe through the Hub client at a reviewed revision and build
`Tokenizer.from_bed` from those verified local bytes. A model and tokenizer
are compatible only when the exact universe,
special-token IDs, and model vocabulary size agree.

## Pre-tokenize to one bounded Parquet file

```python
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import scanpy as sc
from scipy.sparse import csr_matrix
from gtars.models import Region

adata = sc.read_h5ad("data/train.h5ad")
# Validate coordinates/assembly first; do not truncate noninteger coordinates.
adata.X = csr_matrix(adata.X)
adata.X.sum_duplicates()
adata.X.eliminate_zeros()
if not np.isfinite(adata.X.data).all() or (adata.X.data < 0).any():
    raise ValueError("accessibility must be finite and nonnegative")
features = [
    Region(chrom, int(start), int(end), None)
    for chrom, start, end in zip(adata.var["chr"], adata.var["start"], adata.var["end"])
]
cells = []
for row in range(adata.n_obs):
    indices = adata.X.indices[adata.X.indptr[row]:adata.X.indptr[row + 1]]
    ids = tokenizer([features[i] for i in indices])["input_ids"] if len(indices) else []
    cells.append(ids)
special_ids = {getattr(tokenizer, key + "_id") for key in tokenizer.special_tokens_map}
if any(not ids or special_ids.intersection(ids) for ids in cells):
    raise ValueError("empty or unmatched cells require an explicit QC policy")

table = pa.table({"tokens": pa.array(cells, type=pa.list_(pa.int32()))})
pq.write_table(table, "work/train_tokens.parquet")
```

Before writing:

- verify `len(cells) == adata.n_obs`;
- check each token list is bounded and contains IDs in
  `[0, len(tokenizer))`;
- quantify empty cells and out-of-vocabulary/unmatched features;
- preserve row correspondence in a separate protected manifest;
- do not include barcodes or labels in the training Parquet unless required.

The upstream issue
[`databio/geniml#14`](https://github.com/databio/geniml/issues/14)
(opened 2025-09-05) proposes moving away from one `.gtok` file per cell.
Prefer the single Parquet corpus for current work; treat `.gtok` as legacy.

## Train

```python
from geniml.region2vec.utils import Region2VecDataset
from geniml.scembed.main import ScEmbed

dataset = Region2VecDataset(
    "work/train_tokens.parquet",
    shuffle=True,
    convert_to_str=True,
)
model = ScEmbed(
    tokenizer=tokenizer,
    embedding_dim=100,
    pooling_method="mean",
    device="cpu",
)
model.train(
    dataset,
    window_size=5,
    epochs=10,
    min_count=10,
    num_cpus=4,
    seed=42,
)
```

Seed Python `random` before token shuffling and Torch before construction;
Gensim's `seed` alone does not set those RNGs. Derive and retain trained-token
IDs from the training corpus counts and the actual `min_count`; untouched
Torch rows remain random even after `model.trained` becomes true.

Bound cells, nonzeros, tokens per cell, workers, epochs, checkpoint frequency,
RAM, and disk. `Region2VecDataset` loads the full Parquet token column into
memory. Training uses Gensim and Torch; Gensim checkpoint loading is unsafe for
untrusted `.model` files.

Generate a run plan first:

```bash
python skills/geniml/scripts/embedding_plan.py \
  --mode scembed \
  --data work/train_tokens.parquet \
  --universe refs/training_universe.bed \
  --output-dir work/scembed \
  --assembly GRCh38 \
  --embedding-dim 100 --epochs 10 --workers 4 --seed 42
```

## Export and local loading

```python
from pathlib import Path
import shutil
import yaml

bundle = Path("models/scembed")
model.export(str(bundle))
shutil.copyfile(
    "refs/training_universe.bed",
    bundle / "universe.bed",
)
config_path = bundle / "config.yaml"
config = yaml.safe_load(config_path.read_text())
config["pooling_method"] = model.pooling_method
config_path.write_text(yaml.safe_dump(config))
```

As in Region2Vec, the 0.8.4 export utility writes `checkpoint.pt` and
`config.yaml` but does not write the tokenizer universe or preserve
`pooling_method`. Add the exact validated `universe.bed` and record pooling
before generating checksums.

Inspect before loading:

```bash
python skills/geniml/scripts/model_artifact_inspector.py \
  --model-dir models/scembed

python skills/geniml/scripts/tokenizer_compatibility.py \
  --model-dir models/scembed \
  --universe refs/training_universe.bed \
  --assembly GRCh38
```

Then, for a trusted local bundle:

```python
from geniml.scembed.main import ScEmbed

model = ScEmbed.from_pretrained("models/scembed")
```

This classmethod is local. In contrast,
`ScEmbed(model_path="organization/model")` downloads three files through
Hugging Face Hub. Constructor kwargs for revision/cache/offline behavior are
silently discarded in 0.8.4. For authorized downloads, call `hf_hub_download`
directly at a reviewed immutable revision, verify each file, then load the
local bundle. No public weights were downloaded in this review.

`checkpoint.pt` is loaded with Torch `weights_only=True`. Continue to treat it
as untrusted until verified and load in an isolated, resource-bounded
environment. Never inspect it using pickle.

## Generate and attach cell embeddings

Use the token lists above, in exactly the AnnData cell order. This explicit
mean pooling rejects unsupported cells rather than assigning random unknown
or untrained vectors. For held-out data, tokenize its own features with the
same frozen tokenizer; keep `trained_ids` from the training corpus.

```python
from collections import Counter
import numpy as np
import torch

# Set to the actual min_count passed to model.train, using training cells only.
min_count = 10
counts = Counter(token for ids in cells for token in ids)
trained_ids = {token for token, count in counts.items() if count >= min_count}

def pool_cells(model, cell_tokens, trained_ids):
    projection = model.model.projection
    rows = []
    with torch.inference_mode():
        for ids in cell_tokens:
            if not ids or any(token not in trained_ids for token in ids):
                raise ValueError("cell has empty or untrained token set")
            tensor = torch.tensor(ids, dtype=torch.long, device=projection.weight.device)
            rows.append(projection(tensor).mean(dim=0).cpu().numpy())
    if not rows:
        raise ValueError("no cells to embed")
    return np.vstack(rows)

embeddings = pool_cells(model, cells, trained_ids)
assert embeddings.shape == (adata.n_obs, model.model.embedding_dim)
assert np.isfinite(embeddings).all()
adata.obsm["X_scembed"] = embeddings
```

This recipe explicitly chooses mean pooling. Record a different pooling policy
if needed and test its effect. Passing `device="cuda"` to the wrapper alone
does not move its model; CPU training/projection is the tested configuration.

Illustrative downstream analysis (requires the Scanpy Leiden/igraph extras):

```python
import scanpy as sc

sc.pp.neighbors(adata, use_rep="X_scembed")
sc.tl.leiden(adata, resolution=0.5, random_state=42)
sc.tl.umap(adata, random_state=42)
```

UMAP and Leiden are exploratory unless validated on held-out donors. Store
software versions, seeds, neighborhood parameters, and the embedding checksum.

## Cell-type annotation

The release contains `geniml.scembed.annotation.Annotator`, but it is not a
working current-client recipe: it calls removed `QdrantClient.search`, and
internally hard-codes `obsm["embedding"]` and `obs["leiden"]` despite exposing
custom key arguments. Its public constructor also does not accept an API key.
A modern Qdrant integration must use `query_points(...).points`, preserve the
requested keys, and handle authentication explicitly; this is source/runtime
API verification, not a validated annotation workflow. That is a separate
network/data-disclosure decision: embeddings and metadata can be sensitive.
Do not create or contact an annotation server without explicit approval.

For any KNN annotation:

- reference and query embeddings must use the same model/tokenizer/universe;
- fit the reference index using training donors only;
- tune `k` and score thresholds on validation donors;
- include unknown/reject behavior;
- report per-class metrics and calibration on held-out donors;
- avoid claiming labels for absent reference cell types.

Never send raw barcodes, patient metadata, or interval lists to a hosted vector
store by default.

## Evaluation

Report:

- donor-grouped clustering metrics with confidence intervals;
- annotation macro/micro F1 and per-class support;
- unknown/reject rate;
- batch/donor association;
- runtime and peak memory;
- baselines fitted on the same training split.

Do not select clusters, labels, or universe parameters by inspecting the test
UMAP. If pre-trained public models were trained on overlapping donors or
datasets, document that possible leakage.

## Official sources

- [scEmbed training tutorial](https://docs.bedbase.org/geniml/tutorials/train-scembed-model)
  (undated; accessed 2026-10-01)
- [scEmbed API page](https://docs.bedbase.org/geniml/api-reference/scembed/)
  (undated; accessed 2026-10-01)
- [Geniml v0.8.4 source](https://github.com/databio/geniml/tree/v0.8.4/geniml/scembed)
  (released 2026-01-14; accessed 2026-10-01)
- [Gtars tokenizer documentation](https://docs.bedbase.org/gtars/tokenizers)
  (undated; accessed 2026-10-01)
- [Primary scEmbed paper](https://doi.org/10.1093/nargab/lqae073)
  (2024)
