# I/O, tokenization, caches, evaluation, and security

Research snapshot: 2026-10-01. API claims below use official documentation,
PyPI metadata, and the `geniml` v0.8.4 release source. Where current docs and
release code disagree, the discrepancy is stated explicitly.

## Release and dependency facts

`geniml==0.8.4` was released on 2026-01-14. PyPI metadata:

- does not set `Requires-Python`;
- classifies Python 3.10, 3.11, 3.12, 3.13, and 3.14;
- provides `ml` and `test` extras;
- ships a pure-Python wheel, but dependencies include native packages;
- uses Trusted Publishing with a Sigstore provenance link to tag `v0.8.4`.

Release files:

```text
geniml-0.8.4-py3-none-any.whl
sha256 ac0fc520cde6f6461120aee6b40d3cbf20e1e3d8bdb95a3a45345724eee545b5

geniml-0.8.4.tar.gz
sha256 6f429c7c89d06a4c2c378e349d14b3a2d984dc441440ada38473772fce6addb1
```

The stable release requires `gtars>=0.2.5` without an upper bound. The
2026-10-01 synthetic CPU checks used `gtars==0.10.0`, Python 3.12,
AnnData 0.12.19, Scanpy 1.12.4, Zarr 2.18.7, Gensim 4.4.0, Torch 2.14.1,
PyArrow 25.0.1, NumPy 2.5.3, pandas 2.3.3, and Hugging Face Hub 2.0.0.
They exercised Region2Vec/scEmbed training, explicit token/cell pooling,
local bundles, CC construction, and local BED/token caches. Gtars 0.10.0 was released 2026-09-05 and requires
Python >=3.10.

Pin the tested stack and retain `uv.lock`; upstream transitive requirements
are mostly lower bounds. Geniml's Zarr <3 constraint is incompatible with
AnnData 0.13 (Zarr >=3). AnnData 0.12.19 works with the tested Zarr 2.18.7.
The full ml extra resolves but brings additional old pinned components;
it was resolver-checked only, unlike the selective stack above.

## BED coordinates and validation

BED is normally 0-based, half-open `[start, end)`. A valid BED3 row requires:

- nonempty contig;
- integer `start >= 0`;
- integer `end > start`;
- `end` no greater than the declared contig length;
- values within bounded integer limits.

Do not confuse BED with 1-based closed VCF/GFF coordinates. BED columns beyond
BED3 have their own constraints; preserve them rather than guessing.
BED3 carries no strand. When BED6 strand exists, preserve `+`, `-`, or `.`
unless a documented assay conversion says otherwise.

Assembly compatibility requires more than matching `chr` prefixes. BEDbase
describes chromosome-name sensitivity (XS), out-of-bounds regions (OOBR), and
sequence fit (SF) as separate criteria. Record a concrete assembly/accession
and chromosome-sizes digest. Reject unknown alt/decoy contigs rather than
dropping them silently.

Run:

```bash
python skills/geniml/scripts/bed_validator.py \
  --input data/peaks.bed \
  --assembly GRCh38 \
  --chrom-sizes refs/GRCh38.chrom.sizes
```

The script emits aggregate errors and a normalization plan. It never rewrites
coordinates or performs liftover.

## Region and RegionSet APIs

### Gtars API for new workflows

```python
from gtars.models import Region, RegionSet

region = Region("chr1", 100, 200, None)
regions = RegionSet("data/peaks.bed")
print(len(regions))
regions.to_bed("work/peaks.copy.bed")
```

Gtars 0.10.0 requires the fourth `Region` constructor argument (`rest`),
including `None` for BED3. It exposes operations including `sort`, `reduce`, `coverage`,
`count_overlaps`, `jaccard`, `nearest_neighbors`, `to_bed`, `to_bed_gz`, and
`to_bigbed`. Do not assume these operations validate assembly or coordinate
semantics. Validate before constructing the object and after writing output.

Official Gtars constructors can accept URLs. This skill restricts them to
validated local regular files by default.

### Legacy Geniml I/O

```python
from geniml.io import BedSet, Region, RegionSet

region = Region("chr1", 100, 200)  # third field is named stop
regions = RegionSet("data/peaks.bed", backed=False)
```

`geniml.io.RegionSet(regions, backed=False)` accepts a path/URL or a list of
legacy Regions. With `backed=True`, it streams the BED, supports iteration and
length, and does not support indexing. Other release classes include `BedSet`,
`Maf`, `SNP`, `TokenizedRegionSet`, and `RegionSetCollection`, though only
`Region`, `RegionSet`, and `BedSet` are exported from `geniml.io`.

The 0.7.0 changelog says RegionSet use switched toward Gtars. Avoid mixing
legacy and Gtars Region objects accidentally: field names and accepted types
differ.

## Tokenization

### Current Gtars tokenizer

```python
from gtars.models import RegionSet
from gtars.tokenizers import Tokenizer

tokenizer = Tokenizer.from_bed("refs/universe.bed")
encoded = tokenizer(RegionSet("data/peaks.bed"))
input_ids = encoded["input_ids"]
```

Gtars exposes `Tokenizer.from_config(cfg)` and
`Tokenizer.from_pretrained(path)`. The latter can access Hugging Face and has
no revision/cache kwargs. For authorized downloads, use the Hub client with
an immutable revision, then `Tokenizer.from_bed` on verified local bytes.

With Gtars 0.10.0, a two-region universe produced `len(tokenizer) == 9` because
seven special tokens are included. Preserve:

- universe bytes, row order, and assembly;
- Gtars version;
- `special_tokens_map` and every special-token ID;
- tokenizer length;
- token-corpus schema and checksum.

Run the local compatibility planner:

```bash
python skills/geniml/scripts/tokenizer_compatibility.py \
  --model-dir models/region2vec \
  --universe refs/universe.bed \
  --assembly GRCh38
```

### Legacy hard tokenization

The stable file `geniml.tokenization.main` defines:

```python
hard_tokenization_main(
    src_folder,
    dst_folder,
    universe_file,
    fraction=1e-9,
    file_list=None,
    num_workers=10,
    bedtools_path="bedtools",
)
```

It invokes an external Bedtools executable and multiprocessing. The
`fraction` is passed to interval intersection logic; it is **not a statistical
p-value**. The package `geniml.tokenization.__init__` comments out its public
exports, so `from geniml.tokenization import hard_tokenization` and the
installed `geniml tokenize` dispatcher are unreliable in 0.8.4.

Do not use an arbitrary `bedtools` found on `PATH`. If reproducing the legacy
path, pin and checksum the binary, pass an explicit absolute path, validate
argv, bound workers, use a fresh output directory, and compare synthetic
results with the Gtars tokenizer.

The current preferred token corpus is a bounded Parquet file with one
list-valued `tokens` column. Upstream issue #14 proposes deprecating one
`.gtok` file per cell.

## BBClient and cache behavior

```python
from geniml.bbclient import BBClient

client = BBClient(cache_folder="/absolute/project/.bbcache")
```

Release defaults:

- endpoint: `BEDBASE_API` or `https://api.bedbase.org`;
- cache root: `BBCLIENT_CACHE` or `~/.bbcache`;
- BEDs under `bedfiles/`;
- BED sets under `bedsets/`;
- token cache in `tokens.zarr`.

`load_bed`, `load_bedset`, `load_bed_tokens`, `add_bed_tokens_to_cache`,
and corresponding `cache-*` CLI commands may use the network on a cache miss.
`cache_tokens` itself writes local data. The S3 convenience methods
`add_bed_to_s3` and `get_bed_from_s3` are deprecated; use a separately
reviewed boto3/s3fs workflow for an explicitly requested cloud transfer.

The released client and current BEDhost source agree on these read routes:

| Operation | Request | Response contract |
| --- | --- | --- |
| BED file | `GET /v1/objects/bed.{bed_id}.bed_file/access/http/bytes` | File bytes; server may redirect to its object store. |
| BEDset members | `GET /v1/bedset/{bedset_id}/bedfiles` | JSON `results`, with each member's `id`; this route declares no pagination arguments. |
| Token cache location | `GET /v1/bed/{bed_id}/tokens/{universe_id}/info` | JSON `file_path` and `endpoint_url` for a separate S3/Zarr read; missing tokens return 404. |

These methods send no request body or API-authentication header. Public route
source declares no authentication dependency. No invented bearer-token setup
or pagination loop is needed. A deployment can impose its own access policy.
Live `openapi.json` retrieval returned HTTP 403 in this review, so this table
is source-verified and request-mocked, not a successful production download.

Important release behavior:

- BED and BEDset routes use `self.bedbase_api`; token-location requests use
  `DEFAULT_BEDBASE_API` captured at import time, ignoring the instance setting.
  Passing a private endpoint to the constructor does not contain token requests.
- Calls have no timeout, stream bound, or general retry handling. BEDset
  loading reads one complete response and downloads every listed BED; bound
  the requested collection before invoking it. Tokens can contact the separate
  `endpoint_url` returned by metadata.
- `BEDBASE_API` and `BBCLIENT_CACHE` defaults are read at module import time;
  changing them afterward does not update existing defaults. Explicit cache
  paths are preferable.
- BEDbase identifiers are content identifiers, not automatically SHA-256
  checksums of the compressed file. Record your own digest and validate
  assembly/coordinates after retrieval.

Local-oriented CLI:

```text
geniml bbclient seek ID --cache-folder CACHE
geniml bbclient inspect-bedfiles --cache-folder CACHE
geniml bbclient inspect-bedsets --cache-folder CACHE
geniml bbclient rm ID --cache-folder CACHE
```

`rm` mutates cache state; confirm the exact resolved target first. Inspection
can still expose BED IDs and local paths, so redact output in shared logs.

Before an approved download:

1. approve endpoint and exact IDs;
2. set a project-scoped cache and byte quota;
3. reject redirects to unapproved hosts where tooling permits;
4. verify compressed and expanded size;
5. checksum downloaded bytes;
6. validate BED and assembly;
7. record provenance and retrieval time.

No bundled skill script performs BBClient or Hub downloads.

## Model loading and artifact safety

Modern local classes:

```python
from geniml.region2vec.main import Region2VecExModel
from geniml.scembed.main import ScEmbed

r2v = Region2VecExModel.from_pretrained("models/region2vec")
sce = ScEmbed.from_pretrained("models/scembed")
```

These classmethods use local bundle paths. Constructors with
`model_path="organization/model"` call Hugging Face Hub and download
`checkpoint.pt`, `universe.bed`, and `config.yaml`. Their constructors silently
discard revision/cache/offline kwargs; call the Hub download API directly at a
reviewed commit for authorized downloads, then use the local classmethod.

Geniml's loader uses `torch.load(..., weights_only=True)` and YAML
`safe_load`. This is safer than unrestricted pickle, but artifacts can still
cause resource exhaustion or exploit parser/native-library vulnerabilities.
Gensim `.model`, pickle, joblib, TorchScript, shared libraries, and external
binaries require even stronger distrust.

Inspect without importing Torch or deserializing:

```bash
python skills/geniml/scripts/model_artifact_inspector.py \
  --model-dir models/region2vec \
  --verify-manifest models/region2vec/SHA256SUMS
```

The inspector reads bounded metadata formats, hashes bytes, flags risky
extensions, rejects URLs/symlinks/traversal, and never loads model objects.

## Embedding evaluation

The `geniml eval` release CLI has:

```text
gdst     Genome distance scaling test
npt      Neighborhood preserving test
ctt      Cluster tendency test
rct      Reconstruction test
bin-gen  Generate binary embeddings
```

Examples:

```bash
geniml eval gdst \
  --model-path /absolute/project/model \
  --embed-type exmodel \
  --num-samples 10000 \
  --seed 42

geniml eval npt \
  --model-path /absolute/project/model \
  --embed-type exmodel \
  --K 10 \
  --num-samples 1000 \
  --seed 42 \
  --num-workers 4
```

`exmodel` selects a modern local bundle; `region2vec` selects a legacy
Gensim model file. The modern loader and its special-token filtering were
executed. Full CTT/RCT/GDST/NPT calculations are illustrative templates here.
Check that every retained region vector was actually trained before a metric
calculation; removing special vectors alone does not establish that.

The official tutorial's `BaseEmbeddings` and `bin-gen` workflows use pickle
for binary embedding objects. Generate them locally and never load an
untrusted pickle. Bound samples/workers and record random seeds. Evaluate on
patients/donors excluded from universe selection and training.

Primary source: Zheng et al. (2024), *Methods for evaluating unsupervised
vector representations of genomic regions*,
doi:[10.1093/nargab/lqae086](https://doi.org/10.1093/nargab/lqae086).

## BEDshift

The integrated Bedshift CLI is:

```text
geniml bedshift --help
```

It can use a local chromosome-length file or resolve a Refgenie genome through
`refgenconf`. Prefer an explicit, checksummed local chromosome-sizes file to
avoid implicit lookup/network behavior. Set a seed, output bound, and
perturbation policy matching the null hypothesis. Validate randomized
coordinates exactly like originals.

Primary source: Gu et al. (2021), *Bedshift: perturbation of genomic interval
sets*, doi:[10.1186/s13059-021-02440-w](https://doi.org/10.1186/s13059-021-02440-w).

## Privacy and bounded reporting

Potentially sensitive:

- BED coordinates and filenames;
- sample, donor, patient, treatment, diagnosis, and tissue metadata;
- cell barcodes and rare labels;
- embeddings that permit membership or nearest-neighbor inference;
- local cache paths and BEDbase identifiers.

Default reports should contain only aggregate counts, schema names, checksums,
software versions, and redacted file IDs. Cap error examples; never dump
entire malformed rows or metadata values. Store full provenance manifests in
the protected project, not chat output.

## Migration and deprecation ledger

- 0.4.0: tokenizers renamed to `TreeTokenizer` and `AnnDataTokenizer`.
- 0.7.0: RegionSet use moved toward Gtars and encoding changed.
- 0.8.0: Atacformer added.
- 0.8.1: BEDspace fixed according to the changelog.
- 0.8.4: latest stable; release notes contain only the version bump.
- Current Gtars API: use the unified `gtars.tokenizers.Tokenizer`.
- `.gtok`: proposed for deprecation in upstream issue #14; prefer Parquet.
- `embedding_size`: backward-compatible config key; use `embedding_dim`.
- Top-level Region2Vec/scEmbed/tokenization exports shown by old docs are
  absent/commented in the 0.8.4 wheel.
- Official `geniml assess` examples are stale; use
  `geniml assess-universe`.

## Dated authoritative sources

Package and source:

- [PyPI: geniml 0.8.4](https://pypi.org/project/geniml/0.8.4/) — released
  2026-01-14; accessed 2026-10-01.
- [PyPI JSON: geniml 0.8.4](https://pypi.org/pypi/geniml/0.8.4/json) —
  artifact hashes, dependencies, extras, and null `Requires-Python`; accessed
  2026-10-01.
- [GitHub release v0.8.4](https://github.com/databio/geniml/releases/tag/v0.8.4)
  — commit `5e8dd14126c45d14917df74de4fb405f383afb61`; released
  2026-01-14; accessed 2026-10-01.
- [Geniml changelog](https://docs.bedbase.org/geniml/changelog/) — through
  0.8.1 on the rendered page; accessed 2026-10-01.
- [PyPI: gtars 0.10.0](https://pypi.org/project/gtars/0.10.0/) — released
  2026-09-05; accessed 2026-10-01.

Official API/ecosystem documentation:

- [Geniml documentation](https://docs.bedbase.org/geniml/) — accessed
  2026-10-01.
- [Geniml I/O API](https://docs.bedbase.org/geniml/api-reference/io/) —
  accessed 2026-10-01.
- [Gtars RegionSet](https://docs.bedbase.org/gtars/regionSet) — accessed
  2026-10-01.
- [Gtars tokenizers](https://docs.bedbase.org/gtars/tokenizers) — accessed
  2026-10-01.
- [BEDbase reference-genome compatibility](https://docs.bedbase.org/bedbase/user/reference-genome-compatibility/)
  — accessed 2026-10-01.
- [BEDbase BBClient and caching](https://docs.bedbase.org/bedbase/user/bbclient/)
  — accessed 2026-10-01.
- [Geniml evaluation tutorial](https://docs.bedbase.org/geniml/tutorials/evaluation/)
  — accessed 2026-10-01.
- [Official citation map](https://docs.bedbase.org/citations) — accessed
  2026-10-01.

Primary papers:

- [Gharavi et al. 2021, Region2Vec](https://doi.org/10.1093/bioinformatics/btab439)
- [Gu et al. 2021, BEDshift](https://doi.org/10.1186/s13059-021-02440-w)
- [Gharavi et al. 2024, BEDspace](https://doi.org/10.3390/bioengineering11030263)
- [LeRoy et al. 2024, scEmbed](https://doi.org/10.1093/nargab/lqae073)
- [Rymuza et al. 2024, consensus universes](https://doi.org/10.1093/nar/gkae685)
- [Zheng et al. 2024, embedding evaluation](https://doi.org/10.1093/nargab/lqae086)

## Current source and execution boundaries

- [Released Region2Vec implementation](https://github.com/databio/geniml/blob/v0.8.4/geniml/region2vec/main.py),
  [export/load utilities](https://github.com/databio/geniml/blob/v0.8.4/geniml/region2vec/utils.py),
  [scEmbed implementation](https://github.com/databio/geniml/blob/v0.8.4/geniml/scembed/main.py),
  and [tokenization](https://github.com/databio/geniml/blob/v0.8.4/geniml/tokenization/utils.py)
  were checked against the SHA-256-verified released wheel, not master.
- [Released BBClient](https://github.com/databio/geniml/blob/v0.8.4/geniml/bbclient/bbclient.py)
  and [route constants](https://github.com/databio/geniml/blob/v0.8.4/geniml/bbclient/const.py)
  were checked with mocked requests and a local Zarr cache.
- Current server source at commit `864eeddab6900249e05f4fc84a171890ac997877`:
  [objects](https://github.com/databio/bedhost/blob/864eeddab6900249e05f4fc84a171890ac997877/bedhost/routers/objects_api.py),
  [BEDsets](https://github.com/databio/bedhost/blob/864eeddab6900249e05f4fc84a171890ac997877/bedhost/routers/bedset_api.py),
  [token metadata](https://github.com/databio/bedhost/blob/864eeddab6900249e05f4fc84a171890ac997877/bedhost/routers/bed_api.py).
  This does not prove that production runs that commit.
- [AnnData release notes](https://anndata.readthedocs.io/en/stable/release-notes/)
  and [0.13.4 metadata](https://pypi.org/pypi/anndata/0.13.4/json) establish the
  separate Zarr 3 environment boundary.
- [Released Annotator](https://github.com/databio/geniml/blob/v0.8.4/geniml/scembed/annotation.py)
  still uses the removed search API; [Qdrant query documentation](https://python-client.qdrant.tech/qdrant_client.qdrant_client)
  documents `query_points`. Qdrant 1.19.1 client API was inspected locally;
  no hosted annotation or credentialed call was executed.
- No model weights, human cohort data, or large genomes were downloaded. No
  StarSpace native build, HMM/ML/CCF end-to-end run, or external annotation
  service was executed. Their source contracts are illustrative until a
  project-specific synthetic smoke passes.
