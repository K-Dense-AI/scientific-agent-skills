# Refget, sequence digests, stores, and BEDbase

Local synthetic FASTA/store tests on **2026-10-01** used Python `gtars==0.10.0`,
with bundled refget 0.10.0. CLI 0.10.0 and direct Rust refget 0.11.0
were source reviewed, not compiled or executed.

## Digest terminology

Current Python functions:

```python
from gtars.refget import (
    compute_fai,
    digest_fasta,
    digest_sequence,
    load_fasta,
    md5_digest,
    sha512t24u_digest,
)

digest = sha512t24u_digest("ACGT")
assert digest == "aKF498dAxcJAqme6QYQ7EZ07-fiw8Kw2"
assert md5_digest("ACGT") == "f1f8f4bf413b16ad135722aa4591043e"
```

Gtars returns the 32-character unprefixed `sha512t24u` value. The preferred
GA4GH refget sequence identifier adds `SQ.`:

```text
SQ.aKF498dAxcJAqme6QYQ7EZ07-fiw8Kw2
```

MD5 is retained for legacy lookup and is not a collision-resistant provenance
hash. Keep an independent SHA-256 for artifact integrity.

`digest_sequence(data: bytes, name=None, description=None)` uppercases sequence
bytes and returns a `SequenceRecord` containing metadata and data.
`digest_fasta(path)` computes a `SequenceCollection`; `load_fasta(path)` loads
sequence data into memory. `compute_fai(path)` is for uncompressed FASTA.

GA4GH refget normalizes sequence content before computing its sequence
identifier. Do not hash raw FASTA bytes and call that a sequence digest: headers,
line wrapping, compression, and sequence normalization are different layers.

## Current Python store class

The runtime class is `RefgetStore`, not the older tutorial name
`GlobalRefgetStore`:

```python
from gtars.refget import RefgetStore
```

Verified constructors:

```text
RefgetStore.in_memory()
RefgetStore.on_disk(cache_path)
RefgetStore.open_local(path)
RefgetStore.open_remote(cache_path, remote_url)
RefgetStore.store_exists(path)
```

### Local and in-memory modes

```python
from gtars.refget import RefgetStore

store = RefgetStore.in_memory()
metadata, was_new = store.add_sequence_collection_from_fasta(
    "reviewed-reference.fa",
    force=False,
    namespaces=["refseq"],
    collection_alias="local:reference",
)

store.write_store_to_dir("approved-store")
reopened = RefgetStore.open_local("approved-store")
```

Side effects:

- `in_memory()` does not write.
- `on_disk(path)` opens an existing store or creates a new disk-backed store.
- `open_local(path)` reads store metadata/indexes and lazy-loads local sequence
  data.
- `write_store_to_dir` and `enable_persistence` create/write files.
- `force=True` can replace existing collection/sequence entries.

Use `store_exists(path)` before choosing create versus open. Refuse symlinks,
unexpected files, output collisions, and unapproved stores.

Batch import:

```python
report = store.add_sequence_collections_from_fastas(
    ["ref-a.fa.gz", "ref-b.fa.gz"],
    file_list=None,
    jobs=1,
    force=False,
    namespaces=["refseq"],
)
```

In 0.10.0 the return is `ImportReport`: iterate `report.collections` for
`(metadata, was_new)` results. `report.n_collections_new`,
`report.n_sequences_written`, and `report.n_sequences_deduped` describe this
import run. `len(report)` is the number of file results. The report itself is
not a list or iterator. A skipped existing collection may contribute no sequence
counters if the import short-circuits before reading it.

`store.stats()` instead describes totals and current RAM residency. Its Python
values are strings: convert counts with `int(...)`. The keys now include
`n_sequences_in_memory`, `n_collections_in_memory`, and `logical_sequence_bytes`;
old `*_loaded` names are removed. Logical sequence bytes are encoded data volume,
not a measured cache-directory size.

`collection_alias="namespace:alias"` applies to the single-FASTA method. An
invalid syntax raises `ValueError`; alias conflicts require explicit resolution.
Do not silently overwrite a reference assembly alias.

`fastas` can also accept globs or directories and `jobs=0` means automatic
concurrency. For controlled runs, enumerate reviewed files explicitly and set a
positive bounded job count.

## Metadata-only and sequence access

Metadata methods avoid loading full sequence content:

```python
collections_page = store.list_collections(page=0, page_size=100)
sequence_metadata = store.list_sequences()
one_metadata = store.get_sequence_metadata(sequence_digest)
collection_metadata = store.get_collection_metadata(collection_digest)
```

`list_collections` returns a dictionary with `results` and `pagination`
(`page`, `page_size`, `total`); pages are zero-based. Advance the page until the
collected count reaches `total`. `list_sequences()` returns the full metadata
list without pagination, so it can still be large.

Data methods (the loop's `consume_bounded` is an application-specific callback):

```python
record = store.get_sequence(sequence_digest)
by_name = store.get_sequence_by_name(collection_digest, "chr1")
piece = store.get_substring(sequence_digest, 100, 200)
pieces = store.get_substrings(sequence_digest, [(100, 200), (500, 550)])

for chunk in store.stream_sequence(
    sequence_digest,
    start=0,
    end=1_000_000,
    chunk_size=65_536,
):
    consume_bounded(chunk)
```

Substring ranges are 0-based half-open. Validate `0 <= start <= end <= length`.
`stream_sequence` bounds peak result memory, but downstream accumulation can
still defeat streaming.

The 0.10.0 runtime also exposes `load_sequence`, `load_collection`,
`load_all_sequences`, and `load_all_collections`. These materialize more data;
do not call an all-load method without an explicit byte/RAM budget.

## Remote stores require an approval gate

```python
# Network + cache side effects: do not call before approval.
remote = RefgetStore.open_remote(
    approved_cache_path,
    approved_https_base_url,
)
```

`open_remote` takes only a cache path and base URL. It fetches remote metadata,
creates/uses local cache state, and enables persistence by default. In 0.10.0:

- `get_substring` can issue remote byte-range reads without downloading the
  whole sequence;
- `stream_sequence` can stream remote ranges;
- `load_sequence` is the whole-sequence path and can persist it.

This URL is the base of a **Gtars static store**, not an arbitrary GA4GH
`/sequence` REST endpoint. Source reads `rgstore.json`, referenced index files,
`collections/<digest>.rgsi`, and sequence files specified by the store manifest.
Substring requests use HTTP `Range` over encoded storage bytes, not genomic
coordinates in the URL; a range response must be HTTP 206. These methods expose
no auth-header argument. Source review covered this request contract; no public
remote store was exercised in this audit.

Calling `disable_persistence()` after opening does not undo metadata/cache work
already performed. There is no constructor parameter for revision, endpoint
allowlist, checksum manifest, byte quota, or offline mode.

Before `open_remote`:

1. obtain explicit approval for exact HTTPS host/path and cache directory;
2. reject credentials in URLs and unreviewed redirects;
3. pin an immutable server/store revision or content-addressed identifier;
4. record expected collection/sequence digests and independent SHA-256 where
   applicable;
5. cap metadata, per-range, total transfer, sequence length, cache, retries,
   concurrency, and time;
6. disclose that request coordinates/digests and network metadata leave the
   environment;
7. validate returned lengths and digests before scientific use.

Custom/patient-specific assemblies and requested ranges can be sensitive even
when a public reference genome is not.

## Read-only concurrent stores

`into_readonly()` converts a mutable store into `ReadonlyRefgetStore` for
concurrent reads. It consumes/replaces the mutable store and cannot lazy-load
collections that were not prepared. Load only the bounded data required before
conversion; do not use `load_all_*` reflexively.

## CLI store build

CLI 0.10.0 supports local store construction, export, and writer-lock status.
The following templates were checked against source, not executed:

```bash
gtars refget build reference.fa reference-alt.fa.gz \
  --output approved-store \
  --jobs 1
```

Options:

- `--file-list/-f PATH`: file of paths/globs/directories;
- `--output/-o DIR`: required;
- `--jobs/-j N`: concurrent FASTA files, default `0` (auto);
- `--raw`: raw instead of default alphabet-dependent encoded storage;
- `--force`: overwrite existing entries;
- `--collection-alias NAMESPACE:ALIAS`: name one input FASTA's collection;
- `--lock-timeout SECONDS`: bounded wait for writer contention (default 1800).

```bash
gtars refget lock-status approved-store
gtars refget export --store approved-store --collection local:reference \
  --names chr1 --output chr1.fa.gz --line-width 80
```

Export defaults to the sole collection when `--collection` is omitted and
otherwise accepts a digest or alias. It loads selected sequences into RAM;
restrict `--names`, account for sequence bytes, and refuse an existing output.
The output extension `.gz` enables gzip. `--force-unlock` can break an active
writer's protection; inspect lock status and confirm the holder is gone before
using the recovery operation. `--force-alias` replaces conflicting aliases.

There is no current `gtars refget digest` or `verify` CLI matching the old skill.
Use the Python digest functions, direct Rust API, or a local store build after
preflight.

## Offline metadata/digest plan

The bundled helper accepts a conservative local policy manifest:

```json
{
  "schema_version": "1.0",
  "assembly": "GRCh38.p14",
  "coordinate_system": "0-based-half-open",
  "collection_digest": "<32-char sha512t24u-like value>",
  "sequences": [
    {
      "name": "chr1",
      "length": 248956422,
      "sha512t24u": "<32-char digest>",
      "md5": "<32 lowercase hex>"
    }
  ]
}
```

This is a **skill policy manifest**, not an upstream refget wire schema. Validate
it and optionally recompute sequence-level digests from local FASTA:

```bash
python3 -B scripts/refget_digest_plan.py \
  --metadata refget-metadata.json \
  --fasta reference.fa.gz \
  --assembly GRCh38.p14
```

The helper does not recompute the sequence-collection digest; it validates its
shape and verifies each listed local sequence's length, sha512t24u, and MD5.
Use Gtars' pinned collection implementation for final seqcol verification.

## BEDbase and `bbcache`

BEDbase caching is separate from refget. In CLI 0.10.0:

```text
gtars bbcache cache-bed
gtars bbcache cache-bedset
gtars bbcache seek
gtars bbcache inspect-bedfiles
gtars bbcache inspect-bedsets
gtars bbcache rm
```

Defaults from tagged source:

- API: `BEDBASE_API`, otherwise `https://api.bedbase.org`;
- cache: `BBCLIENT_CACHE`, otherwise `$HOME/.bbcache/` (or `/tmp/.bbcache/`);
- cached BEDs: `bedfiles/<first>/<second>/<id>.bed.gz`;
- BED sets: `bedsets/<first>/<second>/<id>.txt`;
- cache metadata includes SQLite state through the cache dependency.

Constructing `BBClient` creates the root and BED/BED-set subdirectories, even for
inspection/seek. `cache-bed` accepts a local file/directory, URL, or intended
BEDbase identifier; `cache-bedset` accepts a local directory/list or intended
BEDbase ID. `rm` deletes files and cache records and can remove member BEDs for a
BED set.

Important source finding: the 0.10.0 release's `BBClient.load_bed(id)` delegates a bare ID
to `RegionSet::try_from`, while the core source has the bare-BEDbase-ID fallback
commented out. Therefore, ID-only `cache-bed`/BED-set downloads may fail in this
release even though the public docs claim support. Do not work around this with
guessed URLs. Verify the installed help/behavior on a non-sensitive approved
test, or resolve an explicit official file URL through reviewed BEDbase metadata.

The `gtars-bbcache 0.5.4` source requests
`GET /v1/bedset/{bedset_id}/bedfiles`, without authentication headers, query
parameters, or a request body; it extracts string IDs from JSON `results[].id`.
It neither checks pagination nor follows another page, and malformed member
records are filtered out. Thus a returned list must not be assumed complete.
The live OpenAPI probe was blocked (HTTP 403); current server pagination and
response compatibility were not independently exercised. Consult the
[official API guide](https://docs.bedbase.org/bedbase/user/bedbase-api-user-guide/)
for record/object distinctions and resolve explicit file URLs before local use.

The bbcache source does not expose an expected SHA-256/revision parameter. Treat
downloads as untrusted:

- approve and allowlist `api.bedbase.org` and any exact data host separately;
- record BEDbase record ID, API response revision/time, explicit file URL,
  expected identifier/digest, and SHA-256;
- use an explicit quota-limited cache folder;
- validate BED assembly/bounds/content before indexing;
- never rely on a successful cache write as integrity proof.

## Rust pin

For the newer direct Rust component (source-reviewed; not compiled here):

```toml
[dependencies]
gtars-refget = "=0.11.0"
```

For the 0.10.0 wrapper release set:

```toml
[dependencies]
gtars = { version = "=0.10.0", default-features = false, features = ["refget"] }
```

These are different minor versions. In direct refget 0.11.0,
`list_sequences()` returns `Result<Vec<_>>`; handle its error. It also adds Zstd
storage and changes loading behavior. Do not substitute the direct 0.11 API for
the Python 0.10 wheel contract. The wrapper uses compatible dependency ranges;
retain Cargo.lock to record actual component versions.

## Official sources (accessed 2026-10-01)

- [Direct refget 0.11.0 release](https://github.com/databio/gtars/releases/tag/gtars-refget-v0.11.0)
- [Python refget 0.10.0 stubs](https://github.com/databio/gtars/blob/gtars-python-v0.10.0/gtars-python/py_src/gtars/refget/__init__.pyi)
- [Python 0.10.0 release](https://github.com/databio/gtars/releases/tag/gtars-python-v0.10.0)
- [gtars-refget 0.11.0 crate](https://crates.io/crates/gtars-refget)
- [Gtars refget module guide](https://docs.bedbase.org/gtars/refget/)
- [Gtars Python refget API](https://docs.bedbase.org/gtars/python/refget-api/)
- [CLI refget parser](https://github.com/databio/gtars/blob/gtars-v0.10.0/gtars-cli/src/refget/cli.rs)
- [BEDbase cache source](https://github.com/databio/gtars/tree/gtars-v0.10.0/gtars-bbcache)
- [BEDbase caching guide](https://docs.bedbase.org/gtars/bbcache/)
- [GA4GH refget sequences v2](https://ga4gh.github.io/refget/sequences)
- [GA4GH refget sequence collections](https://ga4gh.github.io/refget/seqcols/)
