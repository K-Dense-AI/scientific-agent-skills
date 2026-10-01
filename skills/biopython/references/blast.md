# BLAST Operations with Bio.Blast

## Overview

Bio.Blast provides tools for running BLAST searches (both locally and via NCBI web services) and parsing BLAST results in various formats. The module handles the complexity of submitting queries and parsing outputs.

## Running BLAST via NCBI Web Services

### Bio.Blast.NCBIWWW

The `qblast()` function submits to `https://blast.ncbi.nlm.nih.gov/Blast.cgi`
(`CMD=Put` then `CMD=Get` with the returned RID). The current URL API documents
`XML2_S` for one XML document; `XML2` can return a ZIP archive. The legacy
`NCBIWWW` API returns a text handle and `NCBIXML` supports XML1/XML2; keep that
object model separate from the newer binary-handle `Bio.Blast.qblast`/`Blast.read`.

Set `NCBIWWW.email` and `NCBIWWW.tool` before submission. Entrez settings and its
3/10 requests-per-second limits do not apply to BLAST: leave at least 10 seconds
between contacts and 60 seconds between polls of one RID. Coordinate across
workers; use local BLAST for volume. `qblast` polls internally without a hard
completion deadline. These remote examples were checked against docs/source and
mocked transport, not submitted to the public search queue.

```python
from Bio.Blast import NCBIWWW
NCBIWWW.email = "your.email@example.com"
NCBIWWW.tool = "your_tool_name"
```

Submit a single query:

```python
from Bio.Blast import NCBIWWW
from Bio import SeqIO

# Read sequence from file
record = SeqIO.read("sequence.fasta", "fasta")

# Run BLAST search
result_handle = NCBIWWW.qblast(
    program="blastn",           # BLAST program
    database="nt",              # Database to search
    sequence=str(record.seq),   # Query sequence
    format_type="XML2_S"        # Single XML document, not a ZIP archive
)

# Save results
with open("blast_results.xml", "w") as out_file:
    out_file.write(result_handle.read())
result_handle.close()
```

### BLAST Programs Available

- **blastn** - Nucleotide vs nucleotide
- **blastp** - Protein vs protein
- **blastx** - Translated nucleotide vs protein
- **tblastn** - Protein vs translated nucleotide
- **tblastx** - Translated nucleotide vs translated nucleotide

### Common Databases

**Nucleotide databases:**
- `nt` - NCBI nucleotide collection; the service can substitute `core_nt`
- `core_nt` - Core nucleotide database; record the actual database in results
- `refseq_rna` - RefSeq RNA sequences

**Protein databases:**
- `nr` - NCBI nonredundant protein collection (not every possible protein)
- `refseq_protein` - RefSeq protein sequences
- `pdb` - Protein Data Bank sequences
- `swissprot` - Curated UniProtKB/Swiss-Prot

### Advanced qblast Parameters

```python
result_handle = NCBIWWW.qblast(
    program="blastn",
    database="nt",
    sequence=str(record.seq),
    expect=0.001,              # E-value threshold
    hitlist_size=50,           # Number of hits to return
    word_size=11,              # Word size for initial match
    gapcosts="5 2",            # Gap costs (open extend)
    format_type="XML2_S"       # Single XML document
)
```

### Using Sequence Files or IDs

```python
# Use FASTA format string
with open("sequence.fasta") as handle:
    fasta_string = handle.read()
result_handle = NCBIWWW.qblast("blastn", "nt", fasta_string, format_type="XML2_S")

# Use GenBank ID
result_handle = NCBIWWW.qblast("blastn", "nt", "EU490707", format_type="XML2_S")

# Prefer accession.version identifiers over historical GI numbers.
```

## Parsing BLAST Results

### Bio.Blast.NCBIXML

NCBIXML provides parsers for BLAST XML output (the recommended format):

```python
from Bio.Blast import NCBIXML

# Parse single BLAST result
with open("blast_results.xml") as result_handle:
    blast_record = NCBIXML.read(result_handle)
```

### Accessing BLAST Record Data

```python
# Query information
print(f"Query: {blast_record.query}")
print(f"Query length: {blast_record.query_length}")
print(f"Database: {blast_record.database}")
print(f"Number of sequences in database: {blast_record.database_sequences}")

# Iterate through alignments (hits)
for alignment in blast_record.alignments:
    print(f"\nHit: {alignment.title}")
    print(f"Length: {alignment.length}")
    print(f"Accession: {alignment.accession}")

    # Each alignment can have multiple HSPs (high-scoring pairs)
    for hsp in alignment.hsps:
        print(f"  E-value: {hsp.expect}")
        print(f"  Score: {hsp.score}")
        print(f"  Bits: {hsp.bits}")
        print(f"  Identities: {hsp.identities}/{hsp.align_length}")
        print(f"  Gaps: {hsp.gaps}")
        print(f"  Query: {hsp.query}")
        print(f"  Match: {hsp.match}")
        print(f"  Subject: {hsp.sbjct}")
```

### Filtering Results

```python
# Only show hits with E-value < 0.001
E_VALUE_THRESH = 0.001

for alignment in blast_record.alignments:
    for hsp in alignment.hsps:
        if hsp.expect < E_VALUE_THRESH:
            print(f"Hit: {alignment.title}")
            print(f"E-value: {hsp.expect}")
            print(f"Identities: {hsp.identities}/{hsp.align_length}")
            print()
```

### Multiple BLAST Results

For files containing multiple BLAST results (e.g., from batch searches):

```python
from Bio.Blast import NCBIXML

with open("batch_blast_results.xml") as result_handle:
    blast_records = NCBIXML.parse(result_handle)

    for blast_record in blast_records:
        print(f"\nQuery: {blast_record.query}")
        print(f"Hits: {len(blast_record.alignments)}")

        if blast_record.alignments:
            # Get best hit
            best_alignment = blast_record.alignments[0]
            best_hsp = best_alignment.hsps[0]
            print(f"Best hit: {best_alignment.title}")
            print(f"E-value: {best_hsp.expect}")
```

## Running Local BLAST

### Prerequisites

Local BLAST requires:
1. BLAST+ command-line tools installed
2. BLAST databases downloaded locally

### Running BLAST+ via subprocess

Biopython 1.86 removed `Bio.Application` and the BLAST command-line wrappers in `Bio.Blast.Applications`. Use the standard library `subprocess` module with explicit argument lists. Keep command names and flags fixed, validate file paths before running, and do not interpolate unsanitized user input into shell commands.

```python
import subprocess
from Bio.Blast import NCBIXML

cmd = [
    "blastn",
    "-query", "input.fasta",
    "-db", "local_database",
    "-evalue", "0.001",
    "-outfmt", "5",  # XML format for NCBIXML
    "-out", "results.xml",
]
subprocess.run(cmd, check=True)

# Parse results
with open("results.xml") as result_handle:
    blast_record = NCBIXML.read(result_handle)
```

### Common BLAST+ commands

- `blastn` - nucleotide vs nucleotide
- `blastp` - protein vs protein
- `blastx` - translated nucleotide vs protein
- `tblastn` - protein vs translated nucleotide
- `tblastx` - translated nucleotide vs translated nucleotide
- `makeblastdb` - create local BLAST databases

### Creating BLAST Databases

```python
import subprocess

cmd = [
    "makeblastdb",
    "-in", "sequences.fasta",
    "-dbtype", "nucl",
    "-out", "my_database",
]
subprocess.run(cmd, check=True)
```

## Analyzing BLAST Results

### Extract Best Hits

```python
def get_best_hits(blast_record, num_hits=10, e_value_thresh=0.001):
    """Extract best hits from BLAST record."""
    hits = []
    for alignment in blast_record.alignments[:num_hits]:
        for hsp in alignment.hsps:
            if hsp.expect < e_value_thresh:
                hits.append({
                    'title': alignment.title,
                    'accession': alignment.accession,
                    'length': alignment.length,
                    'e_value': hsp.expect,
                    'score': hsp.score,
                    'identities': hsp.identities,
                    'align_length': hsp.align_length,
                    'query_start': hsp.query_start,
                    'query_end': hsp.query_end,
                    'sbjct_start': hsp.sbjct_start,
                    'sbjct_end': hsp.sbjct_end
                })
                break  # Only take best HSP per alignment
    return hits
```

### Calculate Percent Identity

```python
def calculate_percent_identity(hsp):
    """Calculate percent identity for an HSP."""
    return (hsp.identities / hsp.align_length) * 100

# Use it
for alignment in blast_record.alignments:
    for hsp in alignment.hsps:
        if hsp.expect < 0.001:
            identity = calculate_percent_identity(hsp)
            print(f"{alignment.title}: {identity:.2f}% identity")
```

### Extract Hit Sequences

```python
from Bio import Entrez, SeqIO

Entrez.email = "your.email@example.com"

def fetch_hit_sequences(blast_record, num_sequences=5, db="nucleotide"):
    """Fetch hits; choose protein for blastp/blastx targets, nucleotide otherwise."""
    sequences = []

    for alignment in blast_record.alignments[:num_sequences]:
        accession = alignment.accession

        # Fetch sequence from GenBank
        handle = Entrez.efetch(
            db=db,
            id=accession,
            rettype="fasta",
            retmode="text"
        )
        record = SeqIO.read(handle, "fasta")
        handle.close()

        sequences.append(record)

    return sequences
```

## Parsing Other BLAST Formats

### Tab-Delimited Output (outfmt 6/7)

```python
import subprocess

cmd = [
    "blastn",
    "-query", "input.fasta",
    "-db", "database",
    "-outfmt", "6",
    "-out", "results.txt",
]
subprocess.run(cmd, check=True)

# Parse tabular results
with open("results.txt") as f:
    for line in f:
        fields = line.strip().split('\t')
        query_id = fields[0]
        subject_id = fields[1]
        percent_identity = float(fields[2])
        align_length = int(fields[3])
        e_value = float(fields[10])
        bit_score = float(fields[11])

        print(f"{query_id} -> {subject_id}: {percent_identity}% identity, E={e_value}")
```

### Custom Output Formats

```python
import subprocess

# Specify custom columns (outfmt 6 with custom fields)
cmd = [
    "blastn",
    "-query", "input.fasta",
    "-db", "database",
    "-outfmt", "6 qseqid sseqid pident length evalue bitscore qseq sseq",
    "-out", "results.txt",
]
subprocess.run(cmd, check=True)
```

## Best Practices

1. **Use XML format** for parsing (outfmt 5) - most reliable and complete
2. **Save BLAST results** - Don't re-run searches unnecessarily
3. **Set appropriate E-value thresholds** - Default is 10, but 0.001-0.01 is often better
4. **Handle rate limits** - NCBI limits request frequency
5. **Use local BLAST** for large-scale searches or repeated queries
6. **Cache results** - Save parsed data to avoid re-parsing
7. **Check for empty results** - Handle cases with no hits gracefully
8. **Consider alternatives** - For large datasets, consider DIAMOND or other fast aligners
9. **Batch searches** - Submit multiple sequences together when possible
10. **Filter by identity** - E-value alone may not be sufficient

## Common Use Cases

### Basic BLAST Search and Parse

```python
from Bio.Blast import NCBIWWW, NCBIXML
from Bio import SeqIO

# Read query sequence
record = SeqIO.read("query.fasta", "fasta")

# Run BLAST
print("Running BLAST search...")
result_handle = NCBIWWW.qblast("blastn", "nt", str(record.seq), format_type="XML2_S")

# Parse results
blast_record = NCBIXML.read(result_handle)

# Display top 5 hits
print(f"\nTop 5 hits for {blast_record.query}:")
for i, alignment in enumerate(blast_record.alignments[:5], 1):
    hsp = alignment.hsps[0]
    identity = (hsp.identities / hsp.align_length) * 100
    print(f"{i}. {alignment.title}")
    print(f"   E-value: {hsp.expect}, Identity: {identity:.1f}%")
```

### Find Candidate Homologs

```python
from Bio.Blast import NCBIWWW, NCBIXML
from Bio import Entrez, SeqIO

Entrez.email = "your.email@example.com"

# Query gene sequence
query_record = SeqIO.read("gene.fasta", "fasta")

# BLAST against specific organism
result_handle = NCBIWWW.qblast(
    "blastn",
    "nt",
    str(query_record.seq),
    entrez_query="Mus musculus[Organism]",  # Restrict to mouse
    format_type="XML2_S"
)

blast_record = NCBIXML.read(result_handle)

# Find best hit
if blast_record.alignments:
    best_hit = blast_record.alignments[0]
    print(f"Candidate homolog: {best_hit.title}")
    print(f"Accession: {best_hit.accession}")
```

### Batch BLAST Multiple Sequences

```python
from Bio.Blast import NCBIWWW, NCBIXML
from Bio import SeqIO

# Read multiple sequences
sequences = list(SeqIO.parse("queries.fasta", "fasta"))

# Illustrative serial batch: save one complete XML2 document per query.
from pathlib import Path
from time import sleep
Path("blast_results").mkdir(exist_ok=True)
for index, seq_record in enumerate(sequences):
    if index:
        sleep(10)  # Coordinate all other callers separately.
    path = Path("blast_results") / f"query_{index}.xml"
    with NCBIWWW.qblast("blastn", "nt", str(seq_record.seq), format_type="XML2_S") as result_handle:
        path.write_text(result_handle.read(), encoding="utf-8")
    with path.open() as result_handle:
        for blast_record in NCBIXML.parse(result_handle):
            print(f"{seq_record.id}: {len(blast_record.alignments)} hits")
```

### Reciprocal Best Hits

For a real reciprocal-best-hit analysis, run local BLAST against each species'
proteome in turn. Exclude self hits, resolve tied scores explicitly, normalize
accession versions, and set alignment coverage requirements. Confirm that A's best
qualified hit in species B is B and B's best qualified hit in species A is A.
Unrestricted `nr` searches, including self matches, cannot implement this check;
even a reciprocal best hit is evidence for orthology, not proof.

## Error Handling

```python
from Bio.Blast import NCBIWWW, NCBIXML
from urllib.error import HTTPError

try:
    result_handle = NCBIWWW.qblast("blastn", "nt", "ATCGATCGATCG", format_type="XML2_S")
    blast_record = NCBIXML.read(result_handle)
    result_handle.close()
except HTTPError as e:
    print(f"HTTP Error: {e.code}")
except Exception as e:
    print(f"Error running BLAST: {e}")
```
