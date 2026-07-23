# Pysam 0.24 API Quick Reference

This is a compact navigation aid, not a replacement for the official API
documentation. Signatures and defaults below are for pysam 0.24.0.

## Alignment Files

### Constructor

```python
pysam.AlignmentFile(
    filepath_or_object,
    mode=None,
    template=None,
    reference_names=None,
    reference_lengths=None,
    text=None,
    header=None,
    add_sq_text=True,
    add_sam_header=True,
    check_header=True,
    check_sq=True,
    reference_filename=None,
    filename=None,
    index_filename=None,
    filepath_index=None,
    require_index=False,
    duplicate_filehandle=True,
    ignore_truncation=False,
    format_options=None,
    threads=1,
)
```

Core methods:

```python
AlignmentFile.fetch(
    contig=None,
    start=None,
    stop=None,
    region=None,
    tid=None,
    until_eof=False,
    multiple_iterators=False,
    reference=None,  # compatibility alias
    end=None,        # compatibility alias
)

AlignmentFile.count(
    contig=None,
    start=None,
    stop=None,
    region=None,
    until_eof=False,
    read_callback="nofilter",
    reference=None,
    end=None,
)

AlignmentFile.count_coverage(
    contig,
    start=None,
    stop=None,
    region=None,
    quality_threshold=15,
    read_callback="all",
    reference=None,
    end=None,
)

AlignmentFile.pileup(
    contig=None,
    start=None,
    stop=None,
    region=None,
    reference=None,
    end=None,
    **kwargs,
)
```

Important pileup kwargs/defaults:

| Option | Default | Meaning |
|---|---:|---|
| `truncate` | `False` | limit columns to exact query interval |
| `max_depth` | `8000` | maximum depth |
| `stepper` | `"samtools"` in current implementation/docs context | read filtering/processing mode |
| `fastafile` | `None` | reference for BAQ/samtools behavior |
| `ignore_overlaps` | `True` | collapse overlapping paired bases |
| `ignore_orphans` | `True` | exclude improper paired orphans |
| `flag_filter` | unmapped, secondary, QC-fail, duplicate | excluded flags |
| `flag_require` | `0` | required flags |
| `min_base_quality` | `13` | base-quality threshold |
| `min_mapping_quality` | `0` | mapping-quality threshold |
| `compute_baq` | `True` | compute BAQ when reference is available |
| `redo_baq` | `False` | recompute existing BAQ |

Always pass important pileup semantics explicitly rather than depending on
defaults.

Other useful methods/properties:

- `write(read)`
- `has_index()` / `check_index()`
- `get_index_statistics()`
- `get_reference_name(tid)` / `get_tid(name)`
- `get_reference_length(name)`
- `find_introns(read_iterator)`
- `head(n, multiple_iterators=True)`
- `references`, `lengths`, `nreferences`
- `mapped`, `unmapped`, `nocoordinate` when index statistics support them

## `AlignedSegment`

Construction:

```python
read = pysam.AlignedSegment(header=None)
```

Prefer passing the destination `AlignmentHeader`.

Frequently used attributes:

- identity: `query_name`, `query_sequence`, `query_qualities`
- query spans: `query_length`, `query_alignment_start`,
  `query_alignment_end`, `query_alignment_length`
- reference: `reference_id`, `reference_name`, `reference_start`,
  `reference_end`, `reference_length`
- mapping: `mapping_quality`, `cigarstring`, `cigartuples`
- mate: `next_reference_id`, `next_reference_name`,
  `next_reference_start`, `template_length`
- flags: `flag` and `is_*` boolean properties

Methods:

- `get_tag(tag, with_value_type=False)`
- `set_tag(tag, value, value_type=None, replace=True)`
- `has_tag(tag)`
- `get_tags(with_value_type=False)`
- `set_tags(tags)`
- `get_aligned_pairs(matches_only=False, with_seq=False, with_cigar=False)`
- `get_blocks()`
- `get_reference_positions(full_length=False)`
- `get_reference_sequence()` (requires MD)
- `get_forward_sequence()` / `get_forward_qualities()`
- `infer_query_length()` / `infer_read_length()`

Modified-base properties:

- `modified_bases`
- `modified_bases_forward`

They return mappings from `(canonical_base, strand, modification)` to
`(query_position, quality)` calls.

## Pileup Objects

`PileupColumn`:

- `reference_id`, `reference_name`, `reference_pos`
- `nsegments`
- `pileups`
- `get_num_aligned()`
- `get_query_sequences(...)`
- `get_query_qualities()`
- `get_mapping_qualities()`

`PileupRead`:

- `alignment`
- `query_position`
- `query_position_or_next`
- `is_del`
- `is_refskip`
- `indel`
- `level`

Proxy objects are valid only while their iterator remains alive.

## Variant Files

### Constructor

```python
pysam.VariantFile(
    filename,
    mode=None,
    index_filename=None,
    header=None,
    drop_samples=False,
    duplicate_filehandle=True,
    ignore_truncation=False,
    threads=1,
)
```

Core methods:

```python
VariantFile.fetch(
    contig=None,
    start=None,
    stop=None,
    region=None,
    reopen=False,
    end=None,
    reference=None,
)

VariantFile.subset_samples(include_samples)
VariantFile.new_record(*args, **kwargs)
VariantFile.write(record)
```

Numeric fetch coordinates are 0-based, half-open. `reopen=True` supports
multiple simultaneous iterators.

`VariantHeader`:

```python
header.copy()
header.add_meta(key, value=None, items=None)
header.add_line(line)
header.add_sample(sample)
header.new_record(
    contig=None,
    start=0,
    stop=0,
    alleles=None,
    id=None,
    qual=None,
    filter=None,
    info=None,
    samples=None,
    **kwargs,
)
```

Metadata collections:

- `contigs`
- `samples`
- `filters`
- `info`
- `formats`
- `records`

`VariantRecord`:

- location: `contig`, `chrom`, `pos`, `start`, `stop`, `rlen`
- alleles: `ref`, `alts`, `alleles`, `alleles_variant_types`
- metadata: `id`, `qual`, `filter`, `info`
- samples: `samples`
- methods: `copy()`, `translate(destination_header)`

## FASTA and FASTX

```python
pysam.FastaFile(
    filename,
    filepath_index=None,
    filepath_index_compressed=None,
)

FastaFile.fetch(
    reference=None,
    start=None,
    end=None,
    region=None,
)

FastaFile.get_reference_length(reference)
```

Properties: `references`, `lengths`, `nreferences`.

```python
pysam.FastxFile(filename, persist=True)
```

Yielded records expose:

- `name`
- `comment`
- `sequence`
- `quality`
- `get_quality_array()`

`persist=False` is faster but returns temporary read-only proxies.

## Tabix

```python
pysam.TabixFile(
    filename,
    index=None,
    mode="r",
    parser=None,
    encoding="ascii",
    threads=1,
)

TabixFile.fetch(
    reference=None,
    start=None,
    end=None,
    region=None,
    parser=None,
    multiple_iterators=False,
)
```

Properties: `contigs`, `header`, `filename`, `index_filename`.

Compression and indexing:

```python
pysam.tabix_compress(
    filename_in,
    filename_out,
    force=False,
)

pysam.tabix_index(
    filename,
    force=False,
    seq_col=None,
    start_col=None,
    end_col=None,
    preset=None,
    meta_char="#",
    line_skip=0,
    zerobased=False,
    min_shift=-1,
    index=None,
    keep_original=False,
    csi=False,
)
```

Parsers:

- `pysam.asTuple()`
- `pysam.asBed()`
- `pysam.asGTF()`
- `pysam.asVCF()`

## Wrapped Commands

Explicit imports:

```python
import pysam.samtools
import pysam.bcftools
```

Each dispatcher has:

```python
command(
    *args: str,
    catch_stdout=True,
    save_stdout=None,
    split_lines=False,
)

command.get_messages()
command.usage()
```

- command-line tokens are separate strings
- stdout is returned by default
- `save_stdout=path` writes captured stdout to a file
- `catch_stdout=False` discards stdout and avoids overriding a command's `-o`
- stderr is captured and available from `get_messages()`
- a nonzero exit raises `pysam.SamtoolsError`

Top-level samtools aliases such as `pysam.sort` exist, but explicit module
imports make provenance clearer. Bcftools should be explicitly imported as
`pysam.bcftools`.

## Convenience Functions

- `pysam.qualitystring_to_array(text)`
- `pysam.array_to_qualitystring(values)`
- `pysam.index(*samtools_args, **dispatcher_kwargs)`
- `pysam.faidx(*samtools_args, **dispatcher_kwargs)`
- `pysam.tabix_compress(...)`
- `pysam.tabix_index(...)`
- `pysam.set_verbosity(level)`

Pysam 0.24 substantially optimized `array_to_qualitystring()`.

## Exceptions

Expect and handle narrowly:

- `ValueError`: invalid coordinates, header/record errors, unusable index
- `OSError` / `IOError`: file, compression, and HTSlib I/O problems
- `IndexError`: out-of-range FASTA coordinates and sequence access
- `KeyError`: missing headers, samples, tags, or fields when accessed directly
- `pysam.SamtoolsError`: wrapped command failure

Do not use `ignore_truncation=True` as general error suppression.

## Compatibility Names to Avoid in New Code

Prefer:

- `AlignmentFile`, not `Samfile`
- `AlignedSegment`, not `AlignedRead`
- `FastxFile`, not `FastqFile`
- `get_tag()` / `set_tag()`, not `opt()` / `setTag()`
- `get_reference_name()` / `get_tid()`, not old PEP8-incompatible names
- `pysam.CIGAR_OPS.CMATCH` and related enum members, not top-level aliases

Compatibility aliases can remain in 0.24 but are poor foundations for new
work.
