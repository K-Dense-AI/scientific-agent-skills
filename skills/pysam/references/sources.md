# Authoritative Sources

Last researched: **2026-07-23**

Skill baseline: **pysam 0.24.0**, released **2026-04-27**, wrapping
**HTSlib/samtools/bcftools 1.23.1**.

Use these sources in priority order when refreshing this skill. Do not assume
that the newest standalone HTSlib release is the version embedded in the
current pysam wheel.

## Pysam Release and Package Metadata

- [pysam on PyPI](https://pypi.org/project/pysam/) — current published version,
  release date, wheels, release history, and provenance attestations
- [Pysam release notes](https://pysam.readthedocs.io/en/latest/release.html) —
  0.24 CRAM changes, Python support, bundled component versions, bug fixes, and
  deprecations
- [pysam-developers/pysam](https://github.com/pysam-developers/pysam) —
  upstream source and current development state
- [pysam 0.24.0 source tag](https://github.com/pysam-developers/pysam/tree/v0.24.0)
  — version-specific implementation and tests

As of the research date, PyPI identifies 0.24.0 as latest. The 0.24 release
notes state:

- tested Python versions: 3.8 through 3.14
- wheels: macOS and Linux, ARM and x86-64
- bundled HTSlib/samtools/bcftools: 1.23.1
- default newly written CRAM: 3.1
- implicit EBI CRAM reference fetching: removed
- `format_options`: Python `str` values work as documented
- top-level CIGAR constants remain compatibility aliases; prefer
  `pysam.CIGAR_OPS`

Re-check all of these before changing the version pin.

## Official Pysam Documentation

- [Documentation index](https://pysam.readthedocs.io/en/latest/index.html)
- [Installation](https://pysam.readthedocs.io/en/latest/installation.html)
- [Usage guide](https://pysam.readthedocs.io/en/latest/usage.html)
- [API reference](https://pysam.readthedocs.io/en/latest/api.html)
- [FAQ](https://pysam.readthedocs.io/en/latest/faq.html)
- [Release notes](https://pysam.readthedocs.io/en/latest/release.html)
- [Glossary](https://pysam.readthedocs.io/en/latest/glossary.html)

Use the API reference for signatures and documented defaults. Use the FAQ for
iterator lifetime, threading, coordinate, pileup, and quality-editing
behavior. Where prose in the older usage guide conflicts with the current API,
verify against the 0.24 source/tests and installed runtime.

One known example: a real Python file object exposing `fileno()` works with
`AlignmentFile`, while `io.BytesIO` does not. The API constructor documents
file-object support; the usage guide's broad statement about "true python file
objects" is too general.

## Bundled Tool Manuals

Pysam 0.24 wraps the 1.23.1 tool line. Consult manuals matching that line when
using dispatchers:

- [samtools 1.23 manual](https://www.htslib.org/doc/1.23/samtools.html)
- [bcftools 1.23 manual](https://www.htslib.org/doc/1.23/bcftools.html)
- [tabix 1.23 manual](https://www.htslib.org/doc/1.23/tabix.html)
- [bgzip 1.23 manual](https://www.htslib.org/doc/1.23/bgzip.html)
- [faidx 1.23 format/manual](https://www.htslib.org/doc/1.23/faidx.html)
- [HTSlib documentation index](https://www.htslib.org/doc/)

Pysam dispatchers emulate command-line subcommands but capture stdout/stderr.
The pysam usage guide, not only the tool manual, defines `catch_stdout`,
`save_stdout`, `split_lines`, `get_messages()`, and `SamtoolsError`.

## CRAM References

- [Pysam 0.24 release notes](https://pysam.readthedocs.io/en/latest/release.html#release-0-24-0)
  — CRAM 3.1 default and removal of implicit EBI lookup
- [Samtools reference-sequence guidance](https://www.htslib.org/doc/1.23/samtools.html)
  — CRAM reference search order and `REF_PATH`/`REF_CACHE`
- [Using CRAM within Samtools](https://www.htslib.org/workflow/cram.html) —
  reference-based compression, M5 tags, local caches, and workflow concepts

The older CRAM workflow page describes historical fallback to EBI. For pysam
0.24/HTSlib 1.23 behavior, the 0.24 release notes and matching samtools manual
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

## Research Queries Used for This Refresh

Parallel web search/extract was used for:

- current stable pysam version, date, Python range, and wheel platforms
- recent 0.22–0.24 release changes and deprecations
- current AlignmentFile, pileup, VariantFile, FASTA/FASTQ, and Tabix APIs
- current coordinate, iterator, thread-safety, and pileup FAQ guidance
- HTSlib CRAM reference behavior and canonical format specifications

Context7 cross-checked the upstream source documentation for:

- pysam 0.24 release/CRAM behavior
- AlignmentFile signatures and defaults
- VariantFile, FastaFile, FastxFile, and TabixFile APIs

No generated research JSON is part of this skill.

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
