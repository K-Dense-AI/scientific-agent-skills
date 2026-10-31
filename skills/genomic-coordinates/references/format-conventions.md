# Coordinate conventions, format by format

Two independent choices define a convention, and formats mix them freely:

- **Base**: is the first base of a contig called 0 or 1?
- **Closure**: is the end coordinate part of the interval (inclusive) or one past
  it (half-open)?

There is no correlation between a format's age, its authorship, or its purpose and
which pair it picked. UCSC alone ships both.

## The table

| Format | Convention | Length | Notes |
| --- | --- | --- | --- |
| BED (3/6/12) | 0-based half-open | `end - start` | `chromStart` may be 0 |
| bedGraph | 0-based half-open | `end - start` | despite sitting next to WIG |
| bigWig / bigBed | 0-based half-open | `end - start` | binary; matches BED |
| narrowPeak / broadPeak | 0-based half-open | `end - start` | BED6+4 and BED6+3 |
| WIG (fixedStep, variableStep) | 1-based inclusive | `end - start + 1` | the trap next to bedGraph |
| GFF3 | 1-based inclusive | `end - start + 1` | `start <= end` always |
| GTF / GFF2 | 1-based inclusive | `end - start + 1` | GENCODE, Ensembl |
| VCF text | 1-based POS | `len(REF)` for literal REF span | event span can differ; BCF binary POS is 0-based |
| SAM (text) | 1-based inclusive | from CIGAR | `POS` is the leftmost mapped base |
| BAM (binary) | 0-based | from CIGAR | encoded alignment start |
| CRAM | 1-based absolute alignment start | from alignment | AP can be delta encoded; do not treat it as BAM |
| genePred / refFlat | 0-based half-open | `end - start` | `exonEnds` are exclusive |
| PSL (BLAT) | 0-based half-open | `end - start` | see the minus-strand note below |
| Picard interval_list | 1-based inclusive | `end - start + 1` | GATK targets, bait sets |
| MAF — Mutation Annotation | 1-based inclusive | `End - Start + 1` | TCGA somatic calls |
| MAF — Multiple Alignment | 0-based half-open | `size` field | UCSC whole-genome alignments |
| samtools / tabix region string | 1-based inclusive | `end - start + 1` | `chr3:1000-2000` is 1001 bp |
| UCSC browser position box | 1-based inclusive | `end - start + 1` | 1-based UI over 0-based files |
| Ensembl REST region string | 1-based inclusive | `end - start + 1` | `chr:start..end:strand` |
| IGV locus box | 1-based inclusive | `end - start + 1` | matches the UCSC box |
| Bioconductor GRanges / IRanges | 1-based inclusive | `width()` | R ecosystem default |
| PyRanges / pybedtools | 0-based half-open | `End - Start` | Python ecosystem default |

`scripts/convert_coords.py --list` prints its supported convention names. It
converts explicit interval triples; its limited file readers are listed in
`../SKILL.md`. It is not a native parser for every format in this table.

## The conversions worth memorising

For ordinary nonempty spans, these two transformations cover the base/closure change:

```
1-based inclusive  ->  0-based half-open :  start - 1,  end
0-based half-open  ->  1-based inclusive :  start + 1,  end
```

For these nonempty spans on one reference, only the start changes. This rule
does not describe strand reversal, insertions, circular features, or liftover.

## Per-format detail

### BED

`chromStart` is 0-based, `chromEnd` is exclusive. The first base of a chromosome
is `0 1`. A single base at 1-based position 100 is `99 100`.

`chromStart == chromEnd` is a **legal zero-length feature** — an insertion point
between two bases, used by some variant tracks. Converting it requires feature
semantics. GFF3 represents an insertion after base N with start=end=N; the same
numbers can also denote a one-base feature. The generic converter reports
`unrepresentable` for inclusive targets instead of guessing the feature meaning.

BED12 block fields have exact rules that hand-written files routinely break:

- `blockStarts` are offsets **from `chromStart`**, not absolute coordinates.
- `blockStarts[0]` must be `0`.
- `chromStart + blockStarts[-1] + blockSizes[-1]` must equal `chromEnd`.
- `blockCount` must equal the length of both lists.

`thickStart`/`thickEnd` delimit the CDS and must lie within `chromStart`/`chromEnd`;
`thickStart == thickEnd` marks a non-coding transcript.

narrowPeak's tenth column, `peak`, is an offset **from `chromStart`**, or `-1` when
no summit was called. Adding it to `chromStart` gives the summit; treating it as an
absolute coordinate puts the summit on the wrong chromosome arm.

### GFF3 and GTF

Both are 1-based inclusive across nine tab-separated columns. `start <= end` is
required **regardless of strand** — a minus-strand exon is still written with the
smaller coordinate first, and orientation lives only in column 7. A GFF file with
`start > end` is corrupt, not reverse-stranded.

`start == 0` violates the format; inspect provenance before deciding that an
entire file needs a shift. GFF3 circular features may have end larger than the
landmark length to encode crossing its origin. The `##FASTA` directive terminates
feature rows and introduces an optional sequence section.

Column 8 is **phase** in GFF3 and **frame** in GTF, and they mean the same thing:
the bases to skip from the transcriptional start of this segment to find the
next complete codon. Retain those bases when concatenating CDS segments: they
complete the codon begun in the preceding exon. Values are `0`, `1`, `2`, or `.`. It is not the reading
frame of the feature's start position, and it is not `start % 3`. Every CDS
feature should declare it; a missing phase requires annotation-specific review.

Attribute syntax differs and parsers key on it:

```
GFF3   ID=exon1;Parent=transcript1;gene_name=TP53
GTF    gene_id "ENSG00000141510"; transcript_id "ENST00000269305";
```

A `.gtf` file containing GFF3 attributes may fail or lose attributes in readers
that choose a parser from the extension.

`exon_number` in GTF counts in **transcription order**, so on the minus strand
exon 1 has the largest genomic coordinate. Sorting exons by coordinate and
numbering them reproduces the right answer only on the plus strand.

### VCF

`POS` is 1-based and refers to the first base of `REF`. The interval a record
occupies is `POS` to `POS + len(REF) - 1`.

For a simple indel, the unchanged padding base normally precedes the event;
at the beginning of a contig, it follows it. Complex substitutions need not have
an unchanged padding base.

```
reference   ...  A  C  G  T  T  T  A  ...
positions        4  5  6  7  8  9 10

deletion of TT at 8-9    POS=7  REF=TTT   ALT=T
insertion of AA after 7  POS=7  REF=T     ALT=TAA
SNV at 7                POS=7  REF=T     ALT=G
```

This illustrates padding before normalization; the deletion shifts left in its
T repeat. `-` is not a VCF allele. `POS=0` and `POS=N+1` can occur in telomeric
breakend records, whose REF/ALT need structural interpretation. `*` is a spanning
deletion allele. Symbolic alleles and gVCF reference blocks cannot be reduced to
`len(REF)`: VCF 4.5 uses allele-specific `SVLEN` and reference-block `FORMAT/LEN`,
with legacy `INFO/END` retained for compatibility. Read the declared version.

Allele representation has its own reference: `variant-representation.md`.

### SAM, BAM, CRAM

SAM text `POS` is 1-based; BAM stores a 0-based position. CRAM absolute
alignment starts are 1-based and may be delta encoded. The library interface
is a separate contract from the physical format:

- `pysam`'s `AlignedSegment.reference_start` is **0-based**.
- `pysam`'s `.pos` is the same 0-based number.
- The `POS` you see in `samtools view` output is **1-based**.

`reference_end` in pysam is 0-based exclusive, and is `None` for unmapped reads.
`pysam.AlignmentFile.fetch(contig, start, end)` takes **0-based half-open**
coordinates, but `fetch(region="chr1:100-200")` takes a **1-based inclusive**
region string. The same method, two conventions, chosen by which argument you pass.

### Region strings

`RNAME[:STARTPOS[-ENDPOS]]`, 1-based, both endpoints included, so `chr3:1000-2000`
spans 1001 bases.

Omitting the end does **not** mean a single base. `chr2:1000000` means position
1,000,000 to the end of the chromosome. `scripts/convert_coords.py` refuses a
region string without an explicit end rather than guessing which reading was meant.

GRCh38 contig names can contain colons — `HLA-DRB1*12:17` is a real contig — so a
region string is ambiguous without escaping. htslib resolves this with braces:

```
{HLA-DRB1*12:17}          the whole contig
{HLA-DRB1*12:17}:100-200  a region on it
```

Commas as thousands separators are accepted by htslib with
`HTS_PARSE_THOUSANDS_SEP` and by the UCSC and IGV boxes, so `chr1:1,000,000-2,000,000`
is valid input in most places and invalid in most file formats.

### The UCSC split

The UCSC Genome Browser displays and accepts 1-based inclusive coordinates in its
position box, while the BED files it serves and consumes are 0-based half-open.
Both are correct; they are different interfaces to the same data. A coordinate
copied out of the browser window into a BED file is one base too far right.

The UCSC Table Browser applies the same split per output format: BED output is
0-based, "all fields from selected table" output of a genePred table is 0-based,
and the position column shown in the browser is 1-based.

### PSL

PSL uses 0-based half-open coordinates. For DNA query alignments, `qStart` and
`qEnd` remain on the **forward query**, even when the query strand is minus.
The per-block `qStarts` list instead uses reverse-complement coordinates on a
minus query. Convert a reverse-coordinate block `[q, q + size)` to the forward
query as `[qSize - q - size, qSize - q)`. Translated PSL may carry a second strand
character for the target and uses different block-size units; use a PSL parser.

## Tool behaviour

`bedtools` interprets recognized BED, GFF, and VCF inputs in their own
conventions. Do not shift GFF columns and still label the result GFF. Output
depends on the subcommand and options: `intersect -wa/-wb` preserves original
records, and BAM input can produce BAM output. Do not assume all output is BED.
Sorting is required for `-sorted` and indexing, not every bedtools operation.

`bedtools slop` and `flank` require `-g` with chromosome sizes and clip to those
bounds; omitting it is a usage error, not permission to emit negative starts.

`rtracklayer::import()` converts BED coordinates to GRanges on read and export
converts back. When manually constructing GRanges from BED numbers, adjust the
start explicitly. Library accessors should be checked independently of file
encodings (for example pysam `VariantRecord.pos` versus `.start`).

## Official sources reviewed 2026-10-01

- [UCSC format specifications](https://genome.ucsc.edu/FAQ/FAQformat.html): BED,
  PSL, genePred, WIG, MAF and BED-derived formats.
- [GENCODE GTF format](https://www.gencodegenes.org/pages/data_format.html).
- [GFF3 specification](https://github.com/The-Sequence-Ontology/Specifications/blob/master/gff3.md):
  insertion sites, circular landmarks, phase and embedded FASTA.
- [VCF 4.5 and BCF](https://samtools.github.io/hts-specs/VCFv4.5.pdf),
  [SAM/BAM](https://samtools.github.io/hts-specs/SAMv1.pdf),
  [CRAM 3](https://samtools.github.io/hts-specs/CRAMv3.pdf).
- [pysam API](https://pysam.readthedocs.io/en/latest/api.html).
- [Ensembl sequence-region endpoint](https://rest.ensembl.org/documentation/info/sequence_region):
  use `X:1000000..1000100:1` or `:-1`, not a `+`/`-` REST strand. The converter
  accepts those signs as input convenience and emits numeric Ensembl strands.
  Public GET, no key; at most 10 Mb per request, no pagination. A 101-base
  plus/minus pair was fetched and reverse-complement checked during this review.
- [bedtools intersect](https://bedtools.readthedocs.io/en/latest/content/tools/intersect.html),
  [slop](https://bedtools.readthedocs.io/en/latest/content/tools/slop.html),
  [flank](https://bedtools.readthedocs.io/en/latest/content/tools/flank.html).

- [GenomicRanges introduction](https://bioconductor.org/packages/release/bioc/vignettes/GenomicRanges/inst/doc/GenomicRangesIntroduction.html),
  [pybedtools interval accessors](https://daler.github.io/pybedtools/intervals.html),
  [PyRanges coordinate operations](https://pyranges1.readthedocs.io/en/latest/how_to_genomic_ops.html).
  These library conventions were documentation-checked, not separately installed
  for this standard-library helper suite.
