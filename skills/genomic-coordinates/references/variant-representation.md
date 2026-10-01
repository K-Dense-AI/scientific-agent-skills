# Variant representation and normalisation

The same change to a genome can be written many ways. Two records that share no
field values can describe one variant, and two records with identical `POS` can
describe different ones. Comparisons, joins, deduplication, or annotation lookups can lose real matches
when equivalent alleles are represented differently. Normalizing literal alleles
reduces that problem; it does not solve every form of haplotype equivalence.

## Why one variant has many spellings

Take this reference:

```
position    1  2  3  4  5  6  7  8  9 10
base        G  G  C  A  C  A  C  A  C  T
```

Deleting `AC` from the `CACACAC` run yields `GGCACACT` no matter which adjacent
`AC` you remove. All of these are the same variant:

```
POS=7  REF=CAC  ALT=C
POS=5  REF=CAC  ALT=C
POS=3  REF=CAC  ALT=C
POS=2  REF=GCA  ALT=G
```

Any caller may emit any of them. Repeat regions, which is where indels
concentrate, are exactly where the ambiguity is worst.

Redundant flanking bases add a second axis. `POS=3 REF=CA ALT=CT` and
`POS=4 REF=A ALT=T` are the same SNV; the first just carries a base that does not
change.

## The normalisation rule

A variant is normalised when it is **parsimonious** (as few bases as possible,
while keeping at least one) and **left-aligned** (shifted as far towards the
start of the contig as it can go without changing the sequence it describes).
This is the definition from Tan, Abecasis & Kang, *Unified representation of
genetic variants*, Bioinformatics 31(13):2202–2204, 2015, and it is what
`bcftools norm` and `vt normalize` implement.

The procedure:

1. While the alleles all end with the same base: if any allele is down to one
   base, extend every allele one base to the left using the reference and
   decrement `POS`; then drop the last base of every allele.
2. While every allele has at least two bases and they all start with the same
   base: drop the first base of every allele and increment `POS`.

Step 1 walks the variant left through a repeat. Step 2 strips redundant padding.
At the contig start, do not extend past base 1. The helper bounds left-extension
with `--window` and reports `incomplete` if that limit stops normalization:

```bash
python3 normalize_variant.py --fasta ref.fa chr1 7 CAC C
# chr1:7:CAC:C  ->  chr1:2:GCA:G   pos_shift 5
```

`pos_shift` is positive when left-alignment moved the anchor left through a
repeat, negative when trimming moved it right onto a shorter, equivalent record.

## Checking equivalence

Normalise both and compare the four fields:

```bash
python3 normalize_variant.py --fasta ref.fa \
    --compare chr1:7:CAC:C chr1:3:CAC:C chr1:2:GCA:G
# verdict: identical -- all 3 records normalise to chr1:2:GCA:G
```

The verdict goes to stderr so the per-record table on stdout stays parseable.

## Normalisation needs the right reference

Left-alignment reads reference bases. Handed the wrong assembly it will produce a
confident, wrong answer, so the `REF` field is checked against the FASTA first and
a mismatch stops that record:

```
ref_check  MISMATCH   REF says A but the reference has C at chr1:3
```

A `REF` mismatch is evidence of inconsistent inputs, not a diagnosis of the
cause. Check assembly, exact contig names, strand, sequence versions, and
coordinates. Sequence masking and reference errors can also matter. A matching
REF at a few sites does not prove that the whole assembly matches.

## Multi-allelic records

`ALT=G,GG` contains two alternatives sharing a record. Normalization can operate
on a multiallelic site jointly; its shared representation is not necessarily the
same as the independently normalized biallelic keys. Choose the representation
needed for comparison. This helper only normalizes one literal ALT at a time
and rejects unsplit lists:

```bash
python3 normalize_variant.py --fasta ref.fa --split --input cohort.vcf
```

This produces allele-key TSV/JSON and **does not preserve INFO, FORMAT, GT, or
sample identity**. For a VCF workflow use the native tool, for example:

```bash
bcftools norm -m -any -f ref.fa -c e --old-rec-tag ORIG cohort.vcf -Ov -o normalized.vcf
```

`bcftools norm` handles splitting and reference-based normalization in one
command. Field handling depends on declared `Number=A/R/G`, ploidy and options;
it is not a blanket duplication of non-A fields. Review genotype projection
(`--multi-overlaps 0|.`), allele depths (`--keep-sum AD`), and provenance before
using the split output for frequency or dosage calculations. Tested with a tiny
multiallelic GT/AD/PL fixture under bcftools 1.24.

## The other direction: HGVS shifts right

VCF normalization conventionally left-aligns on the genome. HGVS instead uses
the 3'-most position on the described reference: *"in the case of ambiguity, the most 3'
position possible of the reference sequence is arbitrarily assigned to have been
changed."* The shift can differ between genomic and transcript descriptions of one
variant; it is not always opposite in genomic direction.

Worse, HGVS's "3'" is relative to **the reference sequence being described**:

| Description | Shifted towards | On a plus-strand gene | On a minus-strand gene |
| --- | --- | --- | --- |
| VCF `POS` | contig start | leftmost genomic | leftmost genomic |
| HGVS `g.` | contig end | rightmost genomic | rightmost genomic |
| HGVS `c.` / `n.` / `p.` | transcript 3' end | rightmost genomic | **leftmost** genomic |

So for a minus-strand gene, an HGVS `c.` description and a left-aligned VCF
record can coincide. On the plus strand, they can differ in repeats.
Never convert between the two by adjusting coordinates; round-trip through a
tool that knows the transcript model (VEP, Mutalyzer, `hgvs` in Python).
The HGVS exon-junction exceptions also apply; a blind transcript shift is unsafe.
`bcftools norm --gff-annot` supports transcript-aware right-alignment on forward
transcripts, but does not create a general HGVS description.

## Symbolic and structural alleles

Symbolic alleles (`<DEL>`, `<DUP>`, etc.), breakend replacement strings, missing
ALT `.`, and spanning-deletion ALT `*` are outside this helper's literal-allele
normalization. Breakends can include local inserted sequence, and their REF
need not always be a single base. They pass through unchanged with `ref_check =
skipped`; this does not validate their REF, structural syntax, or event extent.

In VCF 4.5, symbolic structural alleles use per-ALT positive `SVLEN`; legacy
`END` and negative deletion lengths have backward-compatibility rules. gVCF
reference blocks use `FORMAT/LEN` in the current specification. Follow the file's
declared version and use a native structural-variant validator/comparator.

`*` represents sequence absent due to an overlapping deletion. It may occur in
sample genotypes, but should not be counted as a separate newly discovered
sequence-change event at that position. Frequency handling is analysis-specific.

## What to run before comparing two variant sets

```bash
# 1. same assembly, same contig naming?
python3 check_contigs.py setA.vcf setB.vcf --genome ref.fa.fai

# 2. structural conventions intact?
python3 audit_intervals.py setA.vcf --genome ref.fa.fai

# 3. split, check REF, trim, left-align -- both sets, same reference
python3 normalize_variant.py --fasta ref.fa --split --input setA.vcf -o A.norm.tsv
python3 normalize_variant.py --fasta ref.fa --split --input setB.vcf -o B.norm.tsv
```

Join only successful literal-allele keys. Stop on mismatches, errors, or
`incomplete` normalization; skipped rows need a different comparison. Even fully
normalized alleles do not establish equivalence of phased haplotypes represented
as multiple SNVs versus one MNV, complex variants, or structural events.

## Official sources reviewed 2026-10-01

- [bcftools norm manual](https://samtools.github.io/bcftools/bcftools.html#norm).
- [VCF 4.5 specification](https://samtools.github.io/hts-specs/VCFv4.5.pdf).
- [HGVS general recommendations](https://hgvs-nomenclature.org/stable/recommendations/general/)
  and [numbering](https://hgvs-nomenclature.org/stable/background/numbering/).
