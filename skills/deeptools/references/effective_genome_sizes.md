# Effective genome size

RPGC requires a positive integer `--effectiveGenomeSize`. There are two distinct
approaches: counting non-N reference bases, or estimating uniquely mappable space
for the actual read length, mapper and filtering policy. Neither is an invariant
of an assembly nickname: primary-only, alternate, decoy and organellar contigs alter
both the numerator's read universe and the denominator.

## Verified source discrepancy

The current rolling upstream table differs from the **4.0.0 tagged source**. For
example, GRCh38 is 3,130,250,755 in the rolling table and 2,913,022,398 in the tag.
The tables do not identify enough reference-file provenance to resolve this for a
particular experiment. Do not silently substitute either number into an existing
analysis; derive/record the value for its actual FASTA and selection policy.

The examples in this skill use these values from the released tag as **illustrative**:

| Reference label | 4.0.0 tagged non-N value |
| --- | ---: |
| GRCh37 | 2864785220 |
| GRCh38 | 2913022398 |
| T2T/CHM13CAT_v2 | 3117292070 |
| GRCm38/mm10 | 2652783500 |
| GRCm39/mm39 | 2654621783 |
| GRCz11 | 1368780147 |
| dm6 | 142573017 |
| WBcel235/ce11 | 100286401 |
| TAIR10 | 119482012 |

These are not suitable by default when multimappers are excluded or MAPQ filtering
changes the accessible sequence space. Use an explicitly sourced mappability estimate
for the reference and read length. Do not round a read-length-specific table to
billions and present that as a measured denominator. `ce10` is not `ce11`.
No `hs`, `mm`, `GRCh38` or other string shorthand is accepted by these CLI integer
arguments.

## Commands

```bash
bamCoverage -b input.bam -o output.bw --normalizeUsing RPGC \
    --effectiveGenomeSize 2913022398

# GC bias requires a matching 2bit genome and an output frequencies file.
# Illustrative: GC correction was not executed in the tiny runtime smoke.
computeGCBias --bamfile input.bam --effectiveGenomeSize 2913022398 \
    --genome genome.2bit --fragmentLength 200 \
    --GCbiasFrequenciesFile freq.txt --biasPlot bias.png
```

`bamCompare --scaleFactorsMethod RPGC` is invalid. The 4.0.0 Rust command accepts
`--normalizeUsing RPGC` despite a contradictory rolling documentation note; its
ratio scaling was checked against bamCoverage on a tiny fixture. Separate normalized
tracks followed by bigwigCompare remain easier to inspect.

## Count non-N bases for the actual FASTA

This standard-library streaming example counts all symbols other than N/n across
selected FASTA records. Other ambiguity symbols are therefore included. If the
scientific definition is A/C/G/T only, change the rule explicitly and record it.
Filter the FASTA to the same contig set as the normalization universe first.

```python
from pathlib import Path

non_n = 0
with Path("genome.fa").open() as handle:
    for line in handle:
        if line.startswith(">"):
            continue
        sequence = "".join(line.split()).upper()
        non_n += len(sequence) - sequence.count("N")
print(non_n)
```

This yields 5 for `ACGTNN` plus `nR` (R is non-N). Record the FASTA checksum,
contig list, method, read length and exclusion policy with the resulting integer.
The former `seqtk comp ... $2` recipe counted total length, including N bases.

Sources: [rolling table](https://deeptools.readthedocs.io/en/latest/content/feature/effectiveGenomeSize.html),
[4.0.0 table](https://github.com/deeptools/deepTools/blob/4.0.0/docs/content/feature/effectiveGenomeSize.rst),
[bamCoverage](https://deeptools.readthedocs.io/en/latest/content/tools/bamCoverage.html).
