# Genomic tokenizers and fragment tokenization

Local synthetic examples tested with Python `gtars==0.10.0`, wrapper crate `gtars==0.10.0`, and
component `gtars-tokenizers==0.5.3` on **2026-10-01**.

## Current class and constructors

The class is `Tokenizer`, not `TreeTokenizer`:

```python
from gtars.tokenizers import Tokenizer

tokenizer = Tokenizer.from_bed("reviewed-universe.bed")
```

Verified Python signatures:

```text
Tokenizer(path)
Tokenizer.from_config(path)
Tokenizer.from_bed(path)
Tokenizer.from_pretrained(path)
Tokenizer.tokenize(regions)
Tokenizer.encode(tokens)
Tokenizer.decode(ids)
Tokenizer.convert_ids_to_tokens(ids)
Tokenizer.convert_tokens_to_ids(tokens)
Tokenizer.get_vocab()
```

`Tokenizer(path)` auto-detects only `.toml`, `.bed`, and `.bed.gz`. The local
constructors read local files and build an in-memory overlap index.

## Local config

`from_config` expects TOML, not YAML:

```toml
universe = "universe.bed.gz"
tokenizer_type = "bits"
```

The universe path is relative to the config file. `tokenizer_type` is optional
and accepts `bits` or `ailist`; omitted means `bits`. A `special_tokens` array can
override defaults, but its values must be valid region-token strings and all
seven roles must remain compatible with the model. Prefer defaults unless a
pinned model manifest explicitly defines every role.

Default roles are:

```text
unk, pad, mask, cls, bos, eos, sep
```

For a unique N-row universe, the tested implementation has `N + 7` vocabulary
entries. Do not hardcode IDs from another universe.

## Tokenization semantics

```python
from gtars.models import Region, RegionSet
from gtars.tokenizers import Tokenizer

universe_path = "training-universe.bed"
tokenizer = Tokenizer.from_bed(universe_path)

query = RegionSet.from_regions(
    [Region("chr1", 100, 200, None)],
)
tokens = tokenizer.tokenize(query)
batch = tokenizer(query)
input_ids = batch["input_ids"]
attention_mask = batch["attention_mask"]
```

The overlap index returns every universe region overlapping each query region.
A query can therefore produce zero, one, or multiple region tokens; if the
entire call yields no overlap, it returns the unknown token. Unknown contigs also
fall through to unknown behavior. In a mixed call, unmatched regions disappear:
there is no one-ID-per-input-row alignment and no unknown placeholder for each
miss. The returned batch does not automatically add BOS/EOS/CLS tokens; record
any model-specific insertion separately.

The verified 0.10.0 wheel rejected a list of strings such as
`["chr1:100-200"]` because the native extractor expected region objects.
Older documentation showing string-list input is not reliable for this pin.
Pass a `RegionSet` or `Region` objects.

Conversion methods:

```python
ids = tokenizer.convert_tokens_to_ids(tokens)
round_trip = tokenizer.convert_ids_to_tokens(ids)
vocabulary = tokenizer.get_vocab()
vocab_size = tokenizer.vocab_size
specials = tokenizer.special_tokens_map
special_ids = {role: getattr(tokenizer, f"{role}_token_id")
               for role in ("unk", "pad", "mask", "cls", "bos", "eos", "sep")}
```

`encode()` maps token strings to IDs. Calling the tokenizer on regions performs
region overlap tokenization plus encoding. These are different stages.

## Universe compatibility is byte/order sensitive

Token IDs depend on the exact universe rows, their order, duplicate policy,
special-token assignment, and backend/config. Assembly labels alone are
insufficient.

Record this manifest before training or inference:

```json
{
  "schema_version": "1.0",
  "assembly": "GRCh38.p14",
  "coordinate_system": "0-based-half-open",
  "gtars_python_version": "0.10.0",
  "universe": {
    "sha256": "<64 lowercase hex>",
    "records": 100000,
    "chrom_sizes_sha256": "<64 lowercase hex>"
  },
  "tokenizer": {
    "backend": "bits",
    "vocab_size": 100007,
    "special_token_ids": {
      "unk": 100000,
      "pad": 100001,
      "mask": 100002,
      "cls": 100003,
      "bos": 100004,
      "eos": 100005,
      "sep": 100006
    }
  }
}
```

The numbers above illustrate the schema, not guaranteed default ID order.
Generate the values from the reviewed local tokenizer.

Validate without importing gtars:

```bash
python3 -B scripts/tokenizer_manifest.py \
  --manifest tokenizer-manifest.json \
  --universe universe.bed \
  --assembly GRCh38.p14 \
  --chrom-sizes GRCh38.p14.chrom.sizes
```

The helper checks manifest structure and declared compatibility without importing
Gtars; it does not prove that declared IDs equal the instantiated tokenizer.
Compare `special_ids`, vocabulary, and a fixed query corpus at runtime.
It requires exact SHA-256 and record count, seven distinct in-range
special IDs, compatible assembly/coordinates/version, and a unique valid BED.

## `from_pretrained` is network-capable

Tagged source implements:

1. if `path` exists locally, append `universe.bed.gz`;
2. otherwise construct a synchronous Hugging Face Hub client;
3. fetch `universe.bed.gz` from the named model repository into the Hub cache.

The Python signature exposes no `revision`, `cache_dir`, `local_files_only`, or
expected checksum. Therefore:

- do not call `Tokenizer.from_pretrained("owner/model")` by default;
- obtain approval for `huggingface.co`, repository, exact commit/revision,
  transfer size, cache path, and metadata disclosure;
- fetch through a reviewed revision-pinning mechanism;
- verify SHA-256 and manifest;
- present an existing local directory containing the reviewed
  `universe.bed.gz`.

No remote model code is needed for a universe file; never enable remote code.

## Fragment tokenization

Current Python binding:

```python
from gtars.tokenizers import Tokenizer, tokenize_fragment_file

tokenizer = Tokenizer.from_bed("training-universe.bed")
by_barcode = tokenize_fragment_file("fragments.tsv.gz", tokenizer)
# dict[str, list[int]]
```

Tagged implementation requires at least five whitespace-separated fields:

```text
chrom  start  end  barcode  count
```

It uses chromosome/start/end/barcode, but does **not** use the fifth count field.
Each input row contributes its overlapping token IDs once, and duplicate IDs are
retained in each barcode list. This can differ from expanding a fragment-support
count. Validate that this is the intended weighting.

The function accumulates all barcodes and token lists in memory. Set caps on
compressed and expanded bytes, rows, distinct barcodes, tokens per row, total
tokens, and process RSS before using it on single-cell data. Never print raw
barcodes.

For count matrices, the CLI's `fscoring --barcode` path uses a separate sparse
count implementation and writes Matrix Market outputs; see `cli.md`.

## Split leakage

Fit universes and tokenizers only from training patients/donors. All technical
and biological replicates from one patient must stay in one split. A universe
derived from all peaks leaks held-out locus support even if the model weights are
trained later.

Freeze and hash:

- patient/replicate split manifest;
- training-only BED inputs;
- consensus/universe BED and chromosome sizes;
- tokenizer manifest and special IDs;
- tokenized corpus schema and checksum;
- package/artifact versions.

Do not tune unknown handling, universe support threshold, backend, or special
tokens on validation/test outcomes more than the declared selection protocol
allows.

## Rust API

```toml
[dependencies]
gtars = { version = "=0.10.0", default-features = false, features = ["tokenizers"] }
```

The wrapper exposes this source-reviewed, uncompiled Rust template:

```rust
use gtars::tokenizers::Tokenizer;

let tokenizer = Tokenizer::from_bed("universe.bed")?;
let tokens = tokenizer.tokenize(&regions)?;
let ids = tokenizer.encode(&regions)?;
```

Rust also supports `from_config`, `from_auto`, and—because the wrapper enables
the `huggingface` feature—`from_pretrained`. Apply the same local-first and
revision/checksum gate.

## Removed stale claims

The current API does not provide `TreeTokenizer.from_bed_file`,
`from_region_string`, YAML tokenizer config, token objects with `.metadata`, or
the old CLI `tokenize` command in `gtars-cli 0.10.0`.

## Official sources (accessed 2026-10-01)

- [Gtars tokenizer guide](https://docs.bedbase.org/gtars/tokenizers/)
- [Python 0.10.0 tokenizer stubs](https://github.com/databio/gtars/blob/gtars-python-v0.10.0/gtars-python/py_src/gtars/tokenizers/__init__.pyi)
- [Python 0.10.0 tokenizer binding](https://github.com/databio/gtars/blob/gtars-python-v0.10.0/gtars-python/src/tokenizers/py_tokenizers/mod.rs)
- [Tokenizer implementation at v0.10.0](https://github.com/databio/gtars/blob/gtars-v0.10.0/gtars-tokenizers/src/tokenizer.rs)
- [Tokenizer TOML schema at v0.10.0](https://github.com/databio/gtars/blob/gtars-v0.10.0/gtars-tokenizers/src/config.rs)
- [Fragment tokenizer source at v0.10.0](https://github.com/databio/gtars/blob/gtars-v0.10.0/gtars-tokenizers/src/utils/fragments.rs)
