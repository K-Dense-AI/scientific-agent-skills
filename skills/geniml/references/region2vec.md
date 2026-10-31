# Region2Vec

Verified against `geniml==0.8.4` release source and the official BEDbase
documentation on 2026-10-01.

## What the method does

Region2Vec learns vectors for genomic regions from region co-occurrence within
interval sets. The primary paper describes randomizing regions within each set
to create word2vec-like contexts, then pooling region vectors to represent
sets. Treat learned proximity as a property of the training corpus and
universe, not as proof of a biological mechanism.

Primary method source: Gharavi et al. (2021), *Embeddings of genomic region sets
capture rich biological associations in low dimensions*,
doi:[10.1093/bioinformatics/btab439](https://doi.org/10.1093/bioinformatics/btab439).

## Stable 0.8.4 API reality

Use concrete module paths:

```python
from geniml.region2vec.main import Region2VecExModel
from geniml.region2vec.utils import Region2VecDataset
from gtars.tokenizers import Tokenizer
```

The release's `geniml.region2vec.__init__` does not export
`Region2VecExModel` or the legacy `region2vec` function. Consequently,
`from geniml.region2vec import region2vec` and the installed
`geniml region2vec ...` dispatch path are not reliable in 0.8.4. The old
function still exists at `geniml.region2vec.main_legacy.region2vec`, but use it
only to reproduce an existing workflow after a pinned smoke test.

## Universe and tokenizer contract

Create the tokenizer from a validated local BED universe:

```python
from gtars.tokenizers import Tokenizer

tokenizer = Tokenizer.from_bed("refs/universe.bed")
```

With verified `gtars==0.10.0`:

- universe regions receive stable IDs in file order;
- seven special tokens are added (`unk`, `pad`, `mask`, `cls`, `eos`, `bos`,
  and `sep`);
- `len(tokenizer)` is universe row count plus special tokens;
- `tokenizer(region_set)["input_ids"]` returns integer IDs.

Compatibility requires the exact universe bytes/order, assembly, contig policy,
Gtars version, special-token map/IDs, and tokenization behavior. Re-sorting a
universe changes IDs even when the interval set is mathematically identical.
Never infer compatibility from a shared filename such as `hg38.bed`.

Before tokenizing:

1. Validate BED as 0-based half-open intervals.
2. Confirm a single assembly with a checksummed chromosome-sizes file.
3. Resolve `chr1`/`1`, alt-contig, mitochondrial, and strand policies.
4. Split by patient/donor before learning or evaluating representations.
5. Record the universe SHA-256 and row count.

Run:

```bash
python skills/geniml/scripts/bed_validator.py \
  --input refs/universe.bed \
  --assembly GRCh38 \
  --chrom-sizes refs/GRCh38.chrom.sizes
```

## Prepare the token corpus

`Region2VecDataset` reads a Parquet file with one list-valued column named
`tokens`; each row is one BED document, sample, or cell. IDs must come from the
same tokenizer that initializes the model.

```python
import pyarrow as pa
import pyarrow.parquet as pq
from gtars.models import RegionSet

documents = []
for local_bed in validated_local_beds:
    ids = tokenizer(RegionSet(local_bed))["input_ids"]
    documents.append(ids)

table = pa.table({"tokens": pa.array(documents, type=pa.list_(pa.int32()))})
pq.write_table(table, "work/tokens.parquet")
```

This example assumes `validated_local_beds` came from a bounded, local
manifest. Do not discover arbitrary directory contents, follow symlinks, or
log sample filenames. Ensure every token is an integer in
`[0, len(tokenizer))`. Empty or unusually short documents need an explicit
policy; do not silently discard them after splitting.

`Region2VecDataset(path, shuffle=True, convert_to_str=False)` loads the full
Parquet `tokens` column into memory. Bound rows and total tokens before
construction. `shuffle=True` mutates each document order when accessed; record
the training seed, but do not assume every library/thread schedule is bitwise
deterministic.

## Train the modern model

```python
from geniml.region2vec.main import Region2VecExModel
from geniml.region2vec.utils import Region2VecDataset

dataset = Region2VecDataset("work/tokens.parquet", shuffle=True, convert_to_str=True)
model = Region2VecExModel(
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

The recipe was executed with a tiny synthetic corpus on the pinned CPU stack.
Seed Python's `random` before dataset iteration and Torch before model
construction as well as passing Gensim's `seed`: `shuffle=True` uses Python's
global RNG. `convert_to_str=True` makes vocabulary keys explicit strings.

Current source defaults are not fully consistent across legacy and modern
modules. Pass every material setting explicitly. `train` uses Gensim
Word2Vec, then copies learned weights into a Torch embedding matrix.
`load_from_checkpoint` and per-epoch Gensim `.model` files deserialize Gensim
artifacts; load only artifacts you created or independently trust.

Suggested run record:

- Geniml, Gtars, Python, Torch, Gensim, NumPy, and PyArrow versions;
- lockfile digest and platform;
- universe/checkpoint/config/token-corpus/manifest SHA-256;
- assembly, coordinate and contig contracts;
- vocabulary and special-token sizes;
- embedding dimension, window, epochs, `min_count`, workers, seed, shuffling,
  pooling, and device;
- train/validation/test grouping and excluded documents.

Generate a bounded plan first:

```bash
python skills/geniml/scripts/embedding_plan.py \
  --mode region2vec \
  --data work/tokens.parquet \
  --universe refs/universe.bed \
  --output-dir work/region2vec \
  --assembly GRCh38 \
  --embedding-dim 100 --epochs 10 --workers 4 --seed 42
```

## Export and inspect artifacts

The 0.8.4 constants are:

- `checkpoint.pt`
- `config.yaml`
- `universe.bed`

The config uses `vocab_size` and `embedding_dim`; `embedding_size` is accepted
only for backward compatibility and is marked for future deprecation.

Important release-source caveat: `model.export(path)` calls
`export_region2vec_model`, which writes the Torch checkpoint and YAML config
but does **not** write the tokenizer's universe or the pooling method, despite
the API docstring. A model initialized with max pooling reloads as mean pooling
unless `pooling_method` is added to `config.yaml`.
Copy the exact validated universe into the bundle yourself, without changing
row order, then create a checksum manifest.

```python
from pathlib import Path
import shutil
import yaml

bundle = Path("models/region2vec")
model.export(str(bundle))
shutil.copyfile("refs/universe.bed", bundle / "universe.bed")
config_path = bundle / "config.yaml"
config = yaml.safe_load(config_path.read_text())
config["pooling_method"] = model.pooling_method
config_path.write_text(yaml.safe_dump(config))
```

Do not overwrite an existing bundle without preserving its prior manifest.
Inspect without deserialization:

```bash
python skills/geniml/scripts/model_artifact_inspector.py \
  --model-dir models/region2vec

python skills/geniml/scripts/tokenizer_compatibility.py \
  --model-dir models/region2vec \
  --universe refs/universe.bed \
  --assembly GRCh38
```

The checkpoint is a `.pt` file. Geniml's local loader uses
`torch.load(..., weights_only=True)`, which reduces but does not eliminate
untrusted-artifact risks such as resource exhaustion, parser defects, or
native-library vulnerabilities. Never use `torch.load`, Gensim load, pickle,
or joblib merely to inspect metadata.

## Load only after verification

Local bundle:

```python
from geniml.region2vec.main import Region2VecExModel

model = Region2VecExModel.from_pretrained("models/region2vec")
```

Despite its name, this classmethod joins local filenames and makes no Hub
request. In contrast:

```python
model = Region2VecExModel(model_path="organization/model")
```

calls `huggingface_hub.hf_hub_download` for the checkpoint, universe, and
config, but **does not forward constructor kwargs** such as `revision`,
`cache_dir`, or `local_files_only`. For an authorized download, call
`hf_hub_download(repo_id=..., filename=..., revision=REVIEWED_COMMIT,
local_dir=...)` directly for each expected file, verify the resulting hashes,
then use the local classmethod. This download recipe is source-verified;
no public weights were fetched in this review.

The loader constructs the tokenizer from `universe.bed`, reads `config.yaml`
with YAML `safe_load`, creates a model of `vocab_size × embedding_dim`, and
loads checkpoint weights. A checksum match is necessary but not sufficient:
also compare assembly, special tokens, shape, pooling, and software versions.

## Encode intervals and sets

`Region2VecExModel.encode` accepts a local BED path, a Region, a sequence of
regions, `geniml.io.RegionSet`, or `gtars.models.RegionSet`.

```python
vectors = model.encode(
    "data/query.bed",
    pooling="mean",
    batch_size=64,
)
```

The method tokenizes each input region, projects its token IDs, and applies
mean or max pooling. It returns one vector per input region. It does not
validate assembly or repair malformed intervals. Validate first, and report
aggregate shapes/statistics rather than raw genomic coordinates. Empty input
raises rather than returning an empty matrix; unmatched regions get the `unk`
embedding, which is usually untrained. Reject or explicitly flag these cases.
The wrapper's `device` argument records a target but does not move its model
or inference tensors; the verified recipe is CPU-only.

## Evaluate without leakage

Geniml's `eval` module implements the paper's:

- CTT: cluster tendency;
- RCT: preservation of training-occurrence information;
- GDST: relation between genomic and embedding distance;
- NPT: preservation of genomic neighborhoods.

Source-backed CLI:

```text
geniml eval ctt --model-path MODEL --embed-type exmodel
geniml eval gdst --model-path MODEL --embed-type exmodel
geniml eval npt --model-path MODEL --embed-type exmodel --K 10
geniml eval rct --model-path MODEL --embed-type exmodel \
  --bin-path BINARY_EMBEDDINGS
```

For the modern directory bundle above, use `--embed-type exmodel`.
`region2vec` means a legacy Gensim model file, not a Geniml bundle directory.
The exmodel loader was executed and correctly excluded all seven special
vectors. It does not exclude low-frequency untrained region vectors; audit
those separately. These metric commands are parser-checked templates;
large-cohort metric estimation was not executed.

`rct` also requires binary embeddings from the same tokenized corpus. The
official tutorial and `eval bin-gen` write pickle; treat that format as trusted
local output only and never load a third-party pickle. Hold out independent
patients/donors before universe selection, hyperparameter tuning, training, and
metric selection. Report all metrics and baselines rather than selecting a
single favorable score.

Primary evaluation source: Zheng et al. (2024), *Methods for evaluating
unsupervised vector representations of genomic regions*,
doi:[10.1093/nargab/lqae086](https://doi.org/10.1093/nargab/lqae086).

## Official sources

- [PyPI geniml 0.8.4](https://pypi.org/project/geniml/0.8.4/) (released
  2026-01-14; accessed 2026-10-01)
- [v0.8.4 release source](https://github.com/databio/geniml/tree/v0.8.4)
  (commit `5e8dd14126c45d14917df74de4fb405f383afb61`; accessed 2026-10-01)
- [Official Region2Vec tutorial](https://docs.bedbase.org/geniml/tutorials/region2vec/)
  (undated; accessed 2026-10-01; contains legacy imports)
- [Official evaluation tutorial](https://docs.bedbase.org/geniml/tutorials/evaluation/)
  (undated; accessed 2026-10-01)
- [Gtars tokenizer documentation](https://docs.bedbase.org/gtars/tokenizers)
  (undated; accessed 2026-10-01)
