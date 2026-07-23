# Migration to Pysam 0.24

Use this checklist when moving an existing environment or pipeline to
pysam 0.24.0.

## Runtime Baseline

- Pysam 0.24.0 was released 27 April 2026.
- It was tested with Python 3.8–3.14.
- It wraps HTSlib/samtools/bcftools 1.23.1.
- It requires Cython 3 when building/extending from source.
- The release notes expect 0.24 to be the final line supporting Python 3.8.

For a reproducible environment:

```bash
uv pip install "pysam==0.24.0"
```

If maintaining Python/Cython extensions that cimport pysam declarations,
rebuild them against 0.24. Do not reuse binaries built against a different
pysam ABI without verification.

## CRAM Behavior

### Output version

New CRAM output defaults to CRAM 3.1. If downstream software only supports
3.0:

```python
pysam.AlignmentFile(
    "output.cram",
    "wc",
    header=header,
    reference_filename="reference.fa",
    format_options=["version=3.0"],
)
```

Upgrade downstream tooling instead of forcing 3.0 when possible.

### Reference lookup

Implicit EBI reference fetching is no longer enabled by default. Existing
pipelines that relied on hidden network retrieval can now fail.

Preferred fix:

```python
pysam.AlignmentFile(
    "input.cram",
    "rc",
    reference_filename="reference.fa",
)
```

Only configure `REF_PATH` and `REF_CACHE` when managed checksum-based lookup is
intentional. Do not restore remote fetching without documenting network,
cache, and provenance behavior.

## `format_options`

Pysam 0.24 fixes Python 3 handling so `AlignmentFile(format_options=...)` and
`HTSFile.add_hts_options()` accept documented `str` values rather than
requiring bytes:

```python
format_options=["version=3.0"]
```

Remove workarounds that encode these strings to bytes.

## CIGAR Constants

Pysam 0.23.2 restored top-level aliases such as `pysam.CMATCH` after a Cython
behavior change, but the release notes warn that a future release will remove
them.

Migrate new and maintained code:

```python
# Compatibility alias
pysam.CMATCH

# Preferred
pysam.CIGAR_OPS.CMATCH
```

Audit all CIGAR operators, not only `CMATCH`.

## Modified Bases

Pysam 0.24:

- removes the prior five-modification-type limit in
  `AlignedSegment.modified_bases`
- fixes a crash for degenerate MM fields that describe no modified bases

Retest MM/ML parsing with:

- multiple modification codes
- empty/degenerate MM tags
- missing ML tags
- forward and reverse alignments
- `modified_bases_forward`

## Quality Conversion

`pysam.array_to_qualitystring()` was optimized substantially in 0.24. Remove
custom micro-optimizations only after confirming identical handling of missing
or invalid values.

## Coverage and Python 3.13+

The 0.24 release fixes coverage functionality for Python 3.13 and later.
Re-run `count_coverage()` regression cases when upgrading both Python and
pysam:

- zero-depth positions
- base-quality threshold boundaries
- duplicate/secondary/supplementary filtering
- ambiguous query bases
- contig boundaries

## Variant Documentation and Errors

Pysam 0.24 adds documentation for many `VariantHeader` and `VariantRecord`
internal field wrappers. Prefer documented public mappings and methods over
introspection into Cython implementation details.

Recent 0.23.x releases also improved `AlignmentFile` and `VariantFile` I/O
exception handling. Catch specific `OSError`/`ValueError` conditions and do
not depend on old message text.

## Avoid Pysam 0.23.1 for Cython Extensions

Pysam 0.23.1 was yanked because it broke binary compatibility for Cython
projects by changing `AlignedSegment` size. Pysam 0.23.2 restored
compatibility. Pure Python users were not affected in the same way.

When migrating from 0.23:

- skip 0.23.1
- rebuild extension modules
- test Cython cimports against the 0.24 declarations

## Dispatcher Output

Keep wrapped command output out of memory for bulk or binary operations:

```python
import pysam.samtools

pysam.samtools.sort(
    "-o",
    "sorted.bam",
    "input.bam",
    catch_stdout=False,
)
```

This is not new to 0.24, but it is important when updating older examples that
omit `catch_stdout=False`.

## Regression Checklist

1. Print and record `pysam.__version__` and `pysam.__samtools_version__`.
2. Open representative BAM, CRAM, VCF.gz, BCF, FASTA, FASTQ, and tabix files.
3. Compare numeric queries with equivalent region strings.
4. Decode CRAM with no network and an explicit reference.
5. Write/read CRAM 3.1; test 3.0 only if required.
6. Rebuild all Cython extensions.
7. Exercise pileup and `count_coverage()` thresholds.
8. Test modified-base MM/ML edge cases.
9. Run sort/index/normalization dispatchers with file output.
10. Recreate indexes and compare known regions and aggregate counts.
