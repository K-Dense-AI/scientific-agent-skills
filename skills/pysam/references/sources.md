# Authoritative Sources

Last researched: **2026-10-01**

Skill baseline: **pysam 0.24.1**, released **2026-09-07**, wrapping
**HTSlib/samtools/bcftools 1.24**.

Use these sources in priority order when refreshing this skill. Do not assume
that the newest standalone HTSlib release is the version embedded in the
current pysam wheel.

## Pysam Release and Package Metadata

- [pysam on PyPI](https://pypi.org/project/pysam/) — current published version,
  release date, wheels, release history, and provenance attestations
- [Pysam release notes](https://pysam.readthedocs.io/en/stable/release.html) —
  0.24 CRAM changes, Python support, bundled component versions, bug fixes, and
  deprecations
- [pysam-developers/pysam](https://github.com/pysam-developers/pysam) —
  upstream source and current development state
- [pysam 0.24.1 source tag](https://github.com/pysam-developers/pysam/tree/v0.24.1)
  — version-specific implementation and tests

As of the research date, PyPI identifies 0.24.1 as latest. The 0.24 release
notes state:

- tested Python versions: 3.9 through 3.15 (RC2)
- wheels: macOS and Linux, ARM and x86-64
- bundled HTSlib/samtools/bcftools: 1.24
- default newly written CRAM: 3.1
- implicit EBI CRAM reference fetching: removed
- `format_options`: Python `str` values work as documented
- top-level CIGAR constants remain compatibility aliases; prefer
  `pysam.CIGAR_OPS`

Re-check all of these before changing the version pin.

## Official Pysam Documentation

- [Documentation index](https://pysam.readthedocs.io/en/stable/index.html)
- [Installation](https://pysam.readthedocs.io/en/stable/installation.html)
- [Usage guide](https://pysam.readthedocs.io/en/stable/usage.html)
- [API reference](https://pysam.readthedocs.io/en/stable/api.html)
- [FAQ](https://pysam.readthedocs.io/en/stable/faq.html)
- [Release notes](https://pysam.readthedocs.io/en/stable/release.html)
- [Glossary](https://pysam.readthedocs.io/en/stable/glossary.html)

Use the API reference for signatures and documented defaults. Use the FAQ for
iterator lifetime, threading, coordinate, pileup, and quality-editing
behavior. Where prose in the older usage guide conflicts with the current API,
verify against the 0.24 source/tests and installed runtime.

One known example: a real Python file object exposing `fileno()` works with
`AlignmentFile`, while `io.BytesIO` does not. The API constructor documents
file-object support; the usage guide's broad statement about "true python file
objects" is too general.

## Bundled Tool Manuals

Pysam 0.24 wraps the 1.24 tool line. Consult manuals matching that line when
using dispatchers:

- [samtools 1.24 manual](https://www.htslib.org/doc/1.24/samtools.html)
- [bcftools 1.24 manual](https://www.htslib.org/doc/1.24/bcftools.html)
- [tabix 1.24 manual](https://www.htslib.org/doc/1.24/tabix.html)
- [bgzip 1.24 manual](https://www.htslib.org/doc/1.24/bgzip.html)
- [faidx 1.24 format/manual](https://www.htslib.org/doc/1.24/faidx.html)
- [HTSlib documentation index](https://www.htslib.org/doc/)

Pysam dispatchers emulate command-line subcommands but capture stdout/stderr.
The pysam usage guide, not only the tool manual, defines `catch_stdout`,
`save_stdout`, `split_lines`, `get_messages()`, and `SamtoolsError`.

## CRAM References

- [Pysam 0.24 release notes](https://pysam.readthedocs.io/en/stable/release.html#release-0-24-0)
  — CRAM 3.1 default and removal of implicit EBI lookup
- [Samtools reference-sequence guidance](https://www.htslib.org/doc/1.24/samtools.html)
  — CRAM reference search order and `REF_PATH`/`REF_CACHE`
- [Using CRAM within Samtools](https://www.htslib.org/workflow/cram.html) —
  reference-based compression, M5 tags, local caches, and workflow concepts

The older CRAM workflow page describes historical fallback to EBI. For pysam
0.24/HTSlib 1.24 behavior, the 0.24 release notes and matching samtools manual
take precedence: implicit EBI lookup is no longer the default.

## Canonical Format Specifications

- [HTS format specifications index](https://samtools.github.io/hts-specs/)
- [SAM/BAM and BAI specification](https://samtools.github.io/hts-specs/SAMv1.pdf)
- [SAM optional tags specification](https://samtools.github.io/hts-specs/SAMtags.pdf)
- [CRAM 3 specification](https://samtools.github.io/hts-specs/CRAMv3.pdf)
- [VCF 4.5 specification](https://samtools.github.io/hts-specs/VCFv4.5.pdf)
- [BCF 2 quick reference](https://samtools.github.io/hts-specs/BCFv2_qref.pdf)
- [Tabix index specification](https://samtools.github.io/hts-specs/tabix.pdf)
- [CSI specification](https://samtools.github.io/hts-specs/CSIv1.pdf)
- [BED 1 specification](https://samtools.github.io/hts-specs/BEDv1.pdf)

Use format specifications for coordinate fields, flags, tags, header
semantics, binary encodings, and index limits. Use pysam documentation for how
those concepts are translated into Python properties.

## Source and Runtime Discrepancies Verified in 0.24.1

The current release notes, API, installation guide, usage guide, FAQ, 1.24
manuals, and the tagged Cython implementation were reviewed. Key source files:

- [Alignment iteration, coverage, CRAM and pileup](https://github.com/pysam-developers/pysam/blob/v0.24.1/pysam/libcalignmentfile.pyx)
- [CIGAR, sequence orientation and pileup columns](https://github.com/pysam-developers/pysam/blob/v0.24.1/pysam/libcalignedsegment.pyx)
- [Variants, headers, fetch and write modes](https://github.com/pysam-developers/pysam/blob/v0.24.1/pysam/libcbcf.pyx)
- [FASTA/FASTQ index and bounds behavior](https://github.com/pysam-developers/pysam/blob/v0.24.1/pysam/libcfaidx.pyx)
- [Tabix constructor, indexes and parsers](https://github.com/pysam-developers/pysam/blob/v0.24.1/pysam/libctabix.pyx)
- [Dispatcher error and message handling](https://github.com/pysam-developers/pysam/blob/v0.24.1/pysam/utils.py)

Native synthetic tests on macOS/Python 3.13.3 confirmed:

- Alignment fetch can return placed unmapped records; no-region variant fetch
  rewinds and streams without an index.
- `get_num_aligned()` includes D/N entries; actual base depth needs exclusions.
- `count_coverage` sizes arrays from numeric start/stop, clips at the contig,
  and does not derive array bounds from region/end aliases.
- CRAI index counters are unavailable, not observed zero-read counts.
- `FastaFile` can create an implicit index; explicit index paths prevent it.
  End overruns clip rather than reliably raising.
- Tabix CSI requires `index=`; the loaded path is `filename_index`, and the
  0.24.1 implementation resets `threads` to 1.
- `wbu` raises; `wb0` is level-zero BGZF BCF. Appending a `fileformat` meta-line
  to a fresh `VariantHeader` duplicates the version line.
- `get_messages()` may be stale after a dispatcher exception; use the exception.

The per-skill tests generate tiny SAM/BAM/CRAM, VCF/BCF, FASTA/FASTQ and
BGZF/tabix fixtures. No clinical or other biological result is validated.
Linux networking-library loading, authenticated remote storage, institutional
reference caches, and Cython extension ABI builds were not executed. The
`example.org` remote-I/O URLs are explicitly illustrative, not service APIs.

## Refresh Checklist

When updating:

1. Check PyPI for the newest published pysam.
2. Read all release notes since the pinned version.
3. Record the embedded HTSlib/samtools/bcftools version.
4. Verify supported Python versions and wheel platforms.
5. Re-check CRAM defaults and reference lookup.
6. Compare API signatures in `api.html` and the tagged source.
7. Run bundled scripts against the new version.
8. Re-run Agent Skills validation and the security scanner.
