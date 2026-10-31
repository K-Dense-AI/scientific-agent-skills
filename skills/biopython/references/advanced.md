# Advanced Biopython Features

## Sequence Motifs with Bio.motifs

### Creating Motifs

```python
from Bio import motifs
from Bio.Seq import Seq

# Create motif from instances
instances = [
    Seq("TACAA"),
    Seq("TACGC"),
    Seq("TACAC"),
    Seq("TACCC"),
    Seq("AACCC"),
    Seq("AATGC"),
    Seq("AATGC"),
]

motif = motifs.create(instances)
```

### Motif Consensus and Degenerate Sequences

```python
# Get consensus sequence
print(motif.counts.consensus)

# Get degenerate consensus (IUPAC ambiguity codes)
print(motif.counts.degenerate_consensus)

# Access counts matrix
print(motif.counts)
```

### Position Weight Matrix (PWM)

```python
# Create position weight matrix
motif.pseudocounts = 0.5
pwm = motif.pwm  # Keep the PWM and relative_entropy on the same pseudocount model
print(pwm)

# Calculate information content
ic = sum(motif.relative_entropy)
print(f"Information content: {ic:.2f} bits")
```

### Searching for Motifs

```python
from Bio.Seq import Seq

# Search sequence for motif
test_seq = Seq("ATACAGGACAGACATACGCATACAACATTACAC")

# Get Position Specific Scoring Matrix (PSSM)
pssm = pwm.log_odds()

# Search sequence
for position, score in pssm.search(test_seq, threshold=5.0):
    print(f"Position {position}: score = {score:.2f}")
```

### Reading Motifs from Files

```python
# Read motif from JASPAR format
with open("motif.jaspar") as handle:
    motif = motifs.read(handle, "jaspar")

# Read multiple motifs
with open("motifs.jaspar") as handle:
    for m in motifs.parse(handle, "jaspar"):
        print(m.name)

# Supported formats: jaspar, meme, transfac, pfm
```

### Writing Motifs

```python
# Write motif in JASPAR format
with open("output.jaspar", "w") as handle:
    handle.write(motif.format("jaspar"))
```

## Population Genetics with Bio.PopGen

### Working with GenePop Files

```python
from Bio.PopGen import GenePop

# Read GenePop file
with open("data.gen") as handle:
    record = GenePop.read(handle)

# Access populations
print(f"Number of populations: {len(record.populations)}")
print(f"Loci: {record.loci_list}")

# Iterate through populations
for pop_idx, pop in enumerate(record.populations):
    print(f"\nPopulation {pop_idx + 1}:")
    for individual in pop:
        print(f"  {individual[0]}: {individual[1]}")
```

### Population Statistics Require Separate Software

Biopython 1.88 retains GenePop file parsers, but does not ship
`Bio.PopGen.GenePop.Controller` or `GenePopController`. Do not call the former
`calc_fst_all`/`test_hw_pop` wrappers. Export validated GenePop data and run the
chosen population-statistics software separately; its estimates and test settings
need independent validation. No external GenePop executable was tested here.

## Sequence Utilities with Bio.SeqUtils

### GC Content

```python
from Bio.SeqUtils import gc_fraction
from Bio.Seq import Seq

seq = Seq("ATCGATCGATCG")
gc = gc_fraction(seq)
print(f"GC content: {gc:.2%}")
```

### Molecular Weight

```python
from Bio.SeqUtils import molecular_weight

# DNA molecular weight
dna_seq = Seq("ATCG")
mw = molecular_weight(dna_seq, seq_type="DNA")
print(f"DNA MW: {mw:.2f} g/mol")

# Protein molecular weight
protein_seq = Seq("ACDEFGHIKLMNPQRSTVWY")
mw = molecular_weight(protein_seq, seq_type="protein")
print(f"Protein MW: {mw:.2f} Da")
```

### Melting Temperature

```python
from Bio.SeqUtils import MeltingTemp as mt

# Calculate Tm using nearest-neighbor method
seq = Seq("ATCGATCGATCG")
tm = mt.Tm_NN(seq)
print(f"Tm: {tm:.1f}°C")

# Use different salt concentration
tm = mt.Tm_NN(seq, Na=50, Mg=1.5)  # 50 mM Na+, 1.5 mM Mg2+

# Wallace rule (for primers)
tm_wallace = mt.Tm_Wallace(seq)
```

### GC Skew

```python
from Bio.SeqUtils import GC_skew

# Calculate GC skew
seq = Seq("ATCGATCGGGCCCAAATTT")
skew = GC_skew(seq, window=100)
print(f"GC skew: {skew}")
```

### ProtParam - Protein Analysis

```python
from Bio.SeqUtils.ProtParam import ProteinAnalysis

protein_seq = "ACDEFGHIKLMNPQRSTVWY"
analyzed_seq = ProteinAnalysis(protein_seq)

# Molecular weight
print(f"MW: {analyzed_seq.molecular_weight():.2f} Da")

# Isoelectric point
print(f"pI: {analyzed_seq.isoelectric_point():.2f}")

# Amino acid composition in percent (0-100), not fractions
print(f"Composition: {analyzed_seq.amino_acids_percent}")

# Instability index
print(f"Instability: {analyzed_seq.instability_index():.2f}")

# Aromaticity
print(f"Aromaticity: {analyzed_seq.aromaticity():.2f}")

# Secondary structure fraction
ss = analyzed_seq.secondary_structure_fraction()
print(f"Helix: {ss[0]:.2%}, Turn: {ss[1]:.2%}, Sheet: {ss[2]:.2%}")

# Extinction coefficients: tuple for reduced cysteines and cystines, respectively
print(f"Extinction coefficient: {analyzed_seq.molar_extinction_coefficient()}")

# Gravy (grand average of hydropathy)
print(f"GRAVY: {analyzed_seq.gravy():.3f}")
```

## Restriction Analysis with Bio.Restriction

```python
from Bio import Restriction
from Bio.Seq import Seq

# Analyze sequence for restriction sites
seq = Seq("GAATTCATCGATCGATGAATTC")

# Use specific enzyme
ecori = Restriction.EcoRI
sites = ecori.search(seq)
print(f"EcoRI sites at: {sites}")

# Use multiple enzymes
rb = Restriction.RestrictionBatch(["EcoRI", "BamHI", "PstI"])
results = rb.search(seq)
for enzyme, sites in results.items():
    if sites:
        print(f"{enzyme}: {sites}")

# Get all enzymes that cut sequence
all_enzymes = Restriction.Analysis(rb, seq)
print(f"Cutting enzymes: {all_enzymes.with_sites()}")
```

## Sequence Translation Tables

```python
from Bio.Data import CodonTable

# Standard genetic code
standard_table = CodonTable.unambiguous_dna_by_id[1]
print(standard_table)

# Mitochondrial code
mito_table = CodonTable.unambiguous_dna_by_id[2]

# Get specific codon
print(f"ATG codes for: {standard_table.forward_table['ATG']}")

# Get stop codons
print(f"Stop codons: {standard_table.stop_codons}")

# Get start codons
print(f"Start codons: {standard_table.start_codons}")
```

## Cluster Analysis with Bio.Cluster

```python
from Bio.Cluster import kcluster
import numpy as np

# Sample data matrix (genes x conditions)
data = np.array([
    [1.2, 0.8, 0.5, 1.5],
    [0.9, 1.1, 0.7, 1.3],
    [0.2, 0.3, 2.1, 2.5],
    [0.1, 0.4, 2.3, 2.2],
])

# Perform k-means clustering
clusterid, error, nfound = kcluster(data, nclusters=2)
print(f"Cluster assignments: {clusterid}")
print(f"Error: {error}")
```

## Genome Diagrams with GenomeDiagram

```python
from Bio.Graphics import GenomeDiagram
from Bio.SeqFeature import SeqFeature, FeatureLocation
from Bio import SeqIO
from reportlab.lib import colors

# Read GenBank file
record = SeqIO.read("sequence.gb", "genbank")

# Create diagram
gd_diagram = GenomeDiagram.Diagram("Genome Diagram")
gd_track = gd_diagram.new_track(1, greytrack=True)
gd_feature_set = gd_track.new_set()

# Add features
for feature in record.features:
    if feature.type == "CDS":
        color = colors.blue
    elif feature.type == "gene":
        color = colors.lightblue
    else:
        color = colors.grey

    gd_feature_set.add_feature(
        feature,
        color=color,
        label=True,
        label_size=6,
        label_angle=45
    )

# Draw and save
gd_diagram.draw(format="linear", pagesize="A4", fragments=1)
gd_diagram.write("genome_diagram.pdf", "PDF")
```

## Sequence Comparison with PairwiseAligner

`Bio.pairwise2` is deprecated (since Biopython 1.80). Use `Bio.Align.PairwiseAligner` for new pairwise alignment code (see `alignment.md`). For HMM workflows, `Bio.HMM` and `Bio.MarkovModel` were removed in Biopython 1.86; use [hmmlearn](https://pypi.org/project/hmmlearn/) instead.

```python
from Bio.Align import PairwiseAligner

aligner = PairwiseAligner()
aligner.mode = "global"
aligner.match_score = 1
aligner.mismatch_score = 0
aligner.gap_score = 0  # Optional: mimic the old globalxx scoring style

alignments = aligner.align("ACCGT", "ACGT")

from itertools import islice
for alignment in islice(alignments, 3):
    print(alignment)
    print(f"Score: {alignment.score}")
```

Avoid importing `Bio.pairwise2` in new code. It remains a legacy migration concern only.

## Working with PubChem

```python
from Bio import Entrez

Entrez.email = "your.email@example.com"

# Search PubChem
handle = Entrez.esearch(db="pccompound", term="aspirin")
result = Entrez.read(handle)
handle.close()

if not result["IdList"]:
    raise ValueError("No compound matched the query")
compound_id = result["IdList"][0]

# Get an Entrez compound summary (not a chemical structure download)
handle = Entrez.esummary(db="pccompound", id=compound_id, retmode="xml")
compound_data = Entrez.read(handle)
handle.close()
```

## Sequence Features with Bio.SeqFeature

```python
from Bio.SeqFeature import SeqFeature, FeatureLocation
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

# Create a feature
feature = SeqFeature(
    location=FeatureLocation(start=10, end=50, strand=1),
    type="CDS",
    qualifiers={"gene": ["ABC1"], "product": ["ABC protein"]}
)

# Add feature to record
record = SeqRecord(Seq("ATCG" * 20), id="seq1")
record.features.append(feature)

# Extract feature sequence
feature_seq = feature.extract(record.seq)
print(feature_seq)
```

## Sequence Ambiguity

```python
from Bio.Data import IUPACData

# DNA ambiguity codes
print(IUPACData.ambiguous_dna_letters)

# Protein ambiguity codes
print(IUPACData.ambiguous_protein_letters)

# Resolve ambiguous bases
print(IUPACData.ambiguous_dna_values["N"])  # Any base
print(IUPACData.ambiguous_dna_values["R"])  # A or G
```

## Quality Scores (FASTQ)

```python
from Bio import SeqIO

# Read FASTQ with quality scores
for record in SeqIO.parse("reads.fastq", "fastq"):
    print(f"ID: {record.id}")
    print(f"Sequence: {record.seq}")
    print(f"Quality: {record.letter_annotations['phred_quality']}")

    # Calculate average quality
    avg_quality = sum(record.letter_annotations['phred_quality']) / len(record)
    print(f"Average quality: {avg_quality:.2f}")

    # Filter by quality
    min_quality = min(record.letter_annotations['phred_quality'])
    if min_quality >= 20:
        print("High quality read")
```

## Best Practices

1. **Use appropriate modules** - Choose the right tool for your analysis
2. **Handle pseudocounts** - Important for motif analysis
3. **Validate input data** - Check file formats and data quality
4. **Consider performance** - Some operations can be computationally intensive
5. **Cache results** - Store intermediate results for large analyses
6. **Use proper genetic codes** - Select appropriate translation tables
7. **Document parameters** - Record thresholds and settings used
8. **Validate statistical results** - Understand limitations of tests
9. **Handle edge cases** - Check for empty results or invalid input
10. **Combine modules** - Leverage multiple Biopython tools together

## Common Use Cases

### Find Stop-Free Translated Segments

```python
from Bio import SeqIO
from Bio.SeqUtils import gc_fraction

def find_orfs(seq, min_length=100, table=1):
    """Return stop-free segments; min_length is nt, coordinates are on input.

    These candidates do not require a start codon and are not validated CDSs.
    Coordinates are zero-based, half-open; terminal stop codons are excluded.
    """
    if min_length < 1:
        raise ValueError("min_length must be positive")
    orfs = []

    for strand, nuc in [(+1, seq), (-1, seq.reverse_complement())]:
        for frame in range(3):
            usable = max(0, len(nuc) - frame) // 3 * 3
            trans = nuc[frame:frame + usable].translate(table=table)
            trans_len = len(trans)

            aa_start = 0
            while aa_start < trans_len:
                aa_end = trans.find("*", aa_start)
                if aa_end == -1:
                    aa_end = trans_len

                if (aa_end - aa_start) * 3 >= min_length:
                    start = frame + aa_start * 3
                    end = frame + aa_end * 3
                    genomic_start, genomic_end = (
                        (start, end) if strand == 1 else (len(seq) - end, len(seq) - start)
                    )
                    orfs.append({
                        'start': genomic_start,
                        'end': genomic_end,
                        'strand': strand,
                        'frame': frame,
                        'length': end - start,
                        'sequence': nuc[start:end]
                    })

                aa_start = aa_end + 1

    return orfs

# Use it
record = SeqIO.read("sequence.fasta", "fasta")
orfs = find_orfs(record.seq, min_length=300)
for orf in orfs:
    print(f"ORF: {orf['start']}-{orf['end']}, strand={orf['strand']}, length={orf['length']}")
```

### Analyze Codon Usage

```python
from Bio import SeqIO

def analyze_codon_usage(fasta_file):
    """Analyze codon usage in coding sequences."""
    codon_counts = {}

    for record in SeqIO.parse(fasta_file, "fasta"):
        # Input must already be an oriented, in-frame coding sequence.
        seq = record.seq.upper()
        if len(seq) % 3 or set(str(seq)) - set("ACGT"):
            raise ValueError(f"Invalid complete DNA codons in {record.id}")

        # Count codons
        for i in range(0, len(seq), 3):
            codon = str(seq[i:i+3])
            codon_counts[codon] = codon_counts.get(codon, 0) + 1

    # Calculate frequencies
    total = sum(codon_counts.values())
    codon_freq = {k: v/total for k, v in codon_counts.items()}

    return codon_freq
```

### Calculate Sequence Complexity

```python
def sequence_complexity(seq, k=2):
    """Calculate k-mer complexity (Shannon entropy)."""
    import math
    from collections import Counter

    if k < 1 or len(seq) < k or set(str(seq).upper()) - set("ACGT"):
        raise ValueError("Requires k >= 1 and at least k unambiguous DNA bases")
    seq = str(seq).upper()

    # Generate k-mers
    kmers = [str(seq[i:i+k]) for i in range(len(seq) - k + 1)]

    # Count k-mers
    counts = Counter(kmers)
    total = len(kmers)

    # Calculate entropy
    entropy = 0
    for count in counts.values():
        freq = count / total
        entropy -= freq * math.log2(freq)

    # Normalize by maximum possible entropy
    max_entropy = math.log2(4 ** k)  # For DNA

    return entropy / max_entropy if max_entropy > 0 else 0

# Use it
from Bio.Seq import Seq
seq = Seq("ATCGATCGATCGATCG")
complexity = sequence_complexity(seq, k=2)
print(f"Sequence complexity: {complexity:.3f}")
```

### Extract Promoter Regions

```python
def extract_promoters(genbank_file, upstream=500):
    """Extract upstream candidates on a linear record, not proven promoters."""
    from Bio import SeqIO

    record = SeqIO.read(genbank_file, "genbank")
    promoters = []
    if upstream < 1 or record.annotations.get("topology") == "circular":
        raise ValueError("Requires positive upstream length and a linear record")

    for feature in record.features:
        if feature.type == "gene":
            from Bio.SeqFeature import ExactPosition, SimpleLocation
            loc = feature.location
            if (not isinstance(loc, SimpleLocation) or loc.strand not in (-1, 1)
                    or not isinstance(loc.start, ExactPosition)
                    or not isinstance(loc.end, ExactPosition)):
                raise ValueError("Requires exact, simple, stranded gene coordinates")
            if feature.location.strand == 1:
                # Forward strand
                start = max(0, feature.location.start - upstream)
                end = feature.location.start
            else:
                # Reverse strand
                start = feature.location.end
                end = min(len(record.seq), feature.location.end + upstream)

            promoter_seq = record.seq[start:end]
            if feature.location.strand == -1:
                promoter_seq = promoter_seq.reverse_complement()

            promoters.append({
                'gene': feature.qualifiers.get('gene', ['Unknown'])[0],
                'sequence': promoter_seq,
                'start': start,
                'end': end
            })

    return promoters
```
