# Using scientific datasets from the catalog

A dataset entry points to a Hub repository, which may contain CSV/Parquet,
FASTA, HDF5, Zarr, or an author's custom layout. `load_dataset` does not make all
of these formats interchangeable. Inspect the card and file manifest before any
large download. Record repository commit, selected files, config and split.

## Install and authenticate

Use an active virtual environment or separate project; the combined tested stack
is in [using-models.md](using-models.md). Datasets 5.0.1 requires Hub below 2.0.

```bash
uv pip install 'datasets==5.0.1' 'huggingface-hub<2' python-dotenv
```

Load `.env` before Hub-dependent imports if the project uses `HF_TOKEN`; keep
`.env` gitignored. Public metadata/data often needs no token. Gated access still
requires the repository's terms/access approval; setting a token does not grant it.

## Discover metadata before rows

```python
from dotenv import load_dotenv
load_dotenv()
from datasets import get_dataset_config_names, get_dataset_split_names
from huggingface_hub import HfApi

repo = "opig/OAS"
revision = HfApi().dataset_info(repo).sha
configs = get_dataset_config_names(repo, revision=revision)
print(configs)
print(get_dataset_split_names(repo, config_name="paired", revision=revision))
```

The OAS card currently declares `default` and `paired` configs. Its `paired`
config points to `paired/*.csv`; species is `meta_Species`, not `species`.
The generic code `ex.get("species") == "human"` silently discards every row.

Illustrative remote streaming (card/source verified; no large OAS shard fetched):

```python
from datasets import Dataset, load_dataset

ds = load_dataset(repo, name="paired", revision=revision, split="train", streaming=True)
sample = next(iter(ds))
print(sample.keys())
if "meta_Species" not in sample:
    raise ValueError("OAS schema changed; inspect the selected configuration")
human_only = ds.filter(lambda ex: ex["meta_Species"] == "human")
subset = Dataset.from_list(list(human_only.take(100)))
if not len(subset):
    raise ValueError("No matching records in the selected data")
```

`streaming=True` with `split` returns an `IterableDataset`; without `split` it
returns a split mapping. `filter` is lazy and does not imply server-side filtering:
reading 100 matches may scan many rows. Only call `Dataset.from_list` on a bounded
subset. Local synthetic CSV tests exercise this loading/filtering/materialization
pattern. They do not establish remote shard performance or scientific suitability.

## OpenGenome2 is not a safe default full download

[OpenGenome2](https://huggingface.co/datasets/arcinstitute/opengenome2) contains
8.8 trillion base pairs, with raw FASTA and preprocessed JSONL that can include
special tokens and phylogenetic tags. Its manifest includes multipart compressed
FASTA files such as `.fasta.gz.aa`. Its JSONL directory also includes complete `.jsonl.gz` shards; select those explicitly when using the JSON loader. The multipart FASTA files are pieces of a compressed
stream, not individually decodable shards. Do not pass a broad wildcard over all
parts to `load_dataset` or assume `streaming=True` reassembles them.

Choose a documented, complete file or explicitly reconstruct the selected ordered
parts after budgeting disk/network. Use the JSON loader for complete JSONL,
sequence tools for FASTA, and verify the actual JSON field names before tokenizing.
No whole-repository `load_dataset("arcinstitute/opengenome2")` shortcut is
validated here. Keep assembly/accession provenance for downstream contamination checks.

## Schema and split checks

- DNA/protein alphabets, ambiguity codes and special tokens must match the model.
  Evo2 uses its native tokenizer; do not assume an `AutoTokenizer` exists.
- `Merck/TEDDY` is a **model/code repository**, not a dataset config named
  `single_cell`. Follow its documented AnnData preprocessing.
- Materials rows may serialize structures/CIFs; scientific imaging may use FITS,
  DICOM or NIfTI. The Hub `mmu_legacysurvey_dr10_south_21` release is HATS/Parquet
  with image-array fields; it is not a directory of FITS images.
- Inspect shapes, dtypes, units, coordinate systems and missingness before batching.
  A generic image decoder is not a scientific format validator.
- Names such as `train` may describe storage layout only. Preserve donor, patient,
  species, scaffold, chromosome or time groups as the scientific evaluation needs;
  prevent near-duplicate and pretraining overlap from inflating reported performance.
- Current Datasets does not execute dataset loading scripts. Adding
  `trust_remote_code=True` cannot revive a legacy scripted loader; use maintained
  standard files or the author's separately reviewed reader.
- Pin licenses, preprocessing and tokenizer revisions alongside the data. Scientific
  catalog inclusion does not establish consent, clinical suitability or commercial rights.

Sources: [loading](https://huggingface.co/docs/datasets/loading),
[streaming](https://huggingface.co/docs/datasets/stream),
[OAS card](https://huggingface.co/datasets/opig/OAS),
[Datasets 5.0.1 loader](https://github.com/huggingface/datasets/blob/5.0.1/src/datasets/load.py).
