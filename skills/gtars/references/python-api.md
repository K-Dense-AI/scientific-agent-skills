# Python API (`gtars==0.10.0`)

Research and runtime verification date: **2026-10-01**. The PyPI package requires
Python 3.10+ and contains a native PyO3 extension.

## Import surface

Public functionality is grouped into submodules:

```python
import gtars
from gtars.models import Region, RegionSet
from gtars.genomic_distributions import consensus
from gtars.tokenizers import Tokenizer, tokenize_fragment_file
from gtars.refget import RefgetStore, digest_fasta, digest_sequence
```

`gtars.__version__` is `0.10.0`. `Region`, `RegionSet`, `Tokenizer`, and
`RefgetStore` are not documented as top-level classes. Python 0.10.0 does not
export Python `uniwig`, `igd`, `scoring`, `fragsplit`, or `bbcache` submodules.

## Verified signatures

The installed 0.10.0 wheel reported:

```text
Region(chr, start, end, rest)
RegionSet(path)
RegionSet.from_regions(regions, strands=None)
RegionSet.from_vectors(chrs, starts, ends, strands=None)
RegionSet.count_overlaps(self, other)
RegionSet.coverage(self, other)
Tokenizer(path)
Tokenizer.from_bed(path)
Tokenizer.from_pretrained(path)
tokenize_fragment_file(file, tokenizer)
consensus(region_sets)
RefgetStore.open_local(path)
RefgetStore.open_remote(cache_path, remote_url)
RefgetStore.get_substring(self, seq_digest, start, end)
```

The shipped `.pyi` stubs omit some runtime methods (`from_vectors`, `disjoin`,
`strands`, and several refget load methods). The tagged PyO3 source and the
installed runtime are authoritative for those omissions.

## `Region`

```python
from gtars.models import Region

region = Region(
    chr="chr1",
    start=100,
    end=200,
    rest="peak_001\t500\t+",
)
assert len(region) == 100
assert (region.chr, region.start, region.end) == ("chr1", 100, 200)
```

`start` and `end` are Rust `u32`. Validate `0 <= start < end <= contig_length`
before construction. The constructor does not itself prove assembly or contig
compatibility. Equality compares only chromosome/start/end; trailing `rest`
content is not part of equality.

## `RegionSet` constructors

### Local file

```python
from pathlib import Path
from gtars.models import RegionSet

path = Path("reviewed-input.bed.gz")
if not path.is_file() or path.is_symlink():
    raise ValueError("expected a reviewed local regular file")
regions = RegionSet(str(path))
```

The Python build enables `gtars-core`'s HTTP feature. If the supplied string is
not an existing local file, core code attempts to open it as a URL. Therefore,
checking `is_file()` before construction is a security boundary, not just an
error-message improvement.

File parsing:

- accepts tab-separated BED-like input and `.gz`;
- skips `browser`, `track`, and `#` lines;
- treats a first row with a nonnumeric second field as a column header;
- requires at least three columns;
- stores columns 4+ as one tab-joined `Region.rest` string;
- rejects an empty region set;
- sorts in memory by lexicographic chromosome then numeric start.

The original file is not rewritten, but input row order is not preserved in the
object.

### In-memory regions

```python
from gtars.models import Region, RegionSet

regions = RegionSet.from_regions(
    [
        Region("chr1", 100, 200, None),
        Region("chr2", 300, 450, None),
    ],
    strands=["+", "-"],
)

same = RegionSet.from_vectors(
    ["chr1", "chr2"],
    [100, 300],
    [200, 450],
    strands=["+", "-"],
)
```

All coordinate vectors, and the optional strand vector, must have equal length.
When strands are omitted, the separate strand vector contains `"*"`.

## Properties and mutability

```python
n = len(regions)
first = regions[0]       # negative indices are supported
identifier = regions.identifier
file_digest = regions.file_digest
header = regions.header
strands = regions.strands

regions.sort()           # in-place; returns None; see strand caveat below
regions.to_bed("out.bed")
regions.to_bed_gz("out.bed.gz")
regions.to_bigbed("out.bb", "assembly.chrom.sizes")
```

- `identifier` is an MD5-like identifier over sorted first-three-column content.
- `file_digest` includes retained trailing columns. Neither value substitutes for
  an independently recorded SHA-256 provenance hash.
- `path` raises `ValueError` for a set created from regions/vectors.
- `sort()` reorders regions but does not reorder the separate `strands` vector
  in 0.10.0. Sort `(region, strand)` pairs before construction, or maintain the
  association externally; otherwise strand-dependent annotations can be silently
  reassigned. File loading already sets this vector to `"*"`.
- Writers overwrite/create the specified output; check output policy first.
- `to_bigbed` needs chromosome sizes matching every contig and bound.

## Interval statistics and structural operations

The following methods are current:

```python
widths = regions.widths()                 # list[int]
same_widths = regions.region_widths()     # alias
mean_width = regions.mean_region_width()  # runtime returns float
length = regions.get_nucleotide_length()
max_ends = regions.get_max_end_per_chr()
stats = regions.chromosome_statistics()

reduced = regions.reduce()
disjoint = regions.disjoin()
trimmed = regions.trim({"chr1": 248956422})
gaps = regions.gaps({"chr1": 248956422})
clusters = regions.cluster(max_gap=100)
```

`reduce()` merges overlapping **and adjacent** ranges. `trim()` drops unknown
contigs and clamps bounds. These transformations do not perform liftover and can
drop the separate strand vector.

`promoters(upstream, downstream)` is relative to each region's start in the
current implementation; it is not a safe substitute for a strand-aware TSS
workflow. Establish strand and TSS semantics independently.

`neighbor_distances()` and `nearest_neighbors()` can return fewer values than
input regions because singletons on a chromosome are skipped; results are not
row-aligned.

`distribution(n_bins=250, chrom_sizes=None)` uses observed maximum ends when
chromosome sizes are absent, making results non-comparable across files. Supply
the exact assembly dictionary. Unknown/out-of-bounds regions are skipped when
sizes are supplied, so summed counts may be lower than input count.

## Pairwise and all-vs-all operations

```python
a = RegionSet("a.bed")
b = RegionSet("b.bed")

concatenated = a.concat(b)          # no merge
union = a.union(b)                  # minimal merged set
difference = a.setdiff(b)           # subtract b bases from a
pairwise = a.pintersect(b)          # pair by index, not genomic all-vs-all
all_pieces = a.intersect_all(b)     # every genomic overlap fragment

jaccard = a.jaccard(b)
coverage = a.coverage(b)
coefficient = a.overlap_coefficient(b)
closest = a.closest(b)
```

`coverage` is `covered base pairs in a / merged base pairs in a`, in `[0,1]`.
Overlaps internal to either input are reduced for these set metrics.
It is not signal coverage and does not produce WIG/bigWig. `pintersect` depends
on index position after constructors may have sorted the inputs. It silently
truncates to the shorter input and emits zero-width intervals for nonoverlapping
or different-contig pairs. Require equal lengths and explicit row pairing first;
filter or label misses before applying the strict nonempty-BED contract.

Overlap query methods are directional:

```python
counts = a.count_overlaps(b)        # one integer for each region in a
flags = a.any_overlaps(b)           # one bool for each region in a
indices = a.find_overlaps(b)        # indices into b for each region in a
subset = a.subset_by_overlaps(b)    # regions from a having at least one hit
```

## Consensus

```python
from gtars.genomic_distributions import consensus

result = consensus([a, b])
# [{"chr": "chr1", "start": 100, "end": 500, "count": 2}, ...]
```

The implementation concatenates all sets, reduces them into merged union
intervals (including adjacency), then counts how many input sets have at least
one overlap with each union interval. It does **not** segment a merged interval
at every support-change boundary. Use this exact meaning when interpreting
`count`.

## Tokenizer and fragment boundary

`Tokenizer.tokenize()` accepts a `RegionSet` or region objects accepted by the
native extractor. Despite older prose examples, the verified wheel rejected a
list of region strings. Use:

```python
from gtars.tokenizers import Tokenizer

tokenizer = Tokenizer.from_bed("local-universe.bed")
tokens = tokenizer.tokenize(a)
ids = tokenizer(a)["input_ids"]
```

See `tokenizers.md` for special-token, universe-order, remote download, and
fragment-file behavior.

## Error handling

The package does not export the invented `gtars.FileNotFoundError`,
`InvalidFormatError`, or `ParseError` classes from the old skill. Validate before
the call, then catch only the narrow built-in/native errors relevant to the
operation:

```python
try:
    regions = RegionSet("reviewed-local.bed")
except (OSError, RuntimeError, ValueError) as exc:
    raise RuntimeError("Gtars could not load the validated BED") from exc
```

Do not use a broad catch to continue past corrupted rows.

## APIs that are not present

The 0.10.0 Python surface does not provide:

- `gtars.RegionSet` or `RegionSet.from_bed`;
- `total_coverage`, `filter_by_size`, `filter_by_chromosome`, `intersect`,
  `subtract`, or `symmetric_difference` under the old names;
- `to_json`, `from_json`, NumPy array getters, `from_arrays`;
- `stream_bed`, `mmap=True`, `parallel=True`, or `parallel_apply`;
- global `set_option`, `option_context`, or `set_log_level`;
- a Python `uniwig` coverage object.

## Official sources (accessed 2026-10-01)

- [PyPI gtars 0.10.0](https://pypi.org/project/gtars/)
- [Python 0.10.0 model stubs](https://github.com/databio/gtars/blob/gtars-python-v0.10.0/gtars-python/py_src/gtars/models/__init__.pyi)
- [Python 0.10.0 Region binding](https://github.com/databio/gtars/blob/gtars-python-v0.10.0/gtars-python/src/models/region.rs)
- [Python 0.10.0 RegionSet binding](https://github.com/databio/gtars/blob/gtars-python-v0.10.0/gtars-python/src/models/region_set.rs)
- [Python 0.10.0 genomic-distribution stubs](https://github.com/databio/gtars/blob/gtars-python-v0.10.0/gtars-python/py_src/gtars/genomic_distributions/__init__.pyi)
- [Gtars model guide](https://docs.bedbase.org/gtars/regionSet/)
