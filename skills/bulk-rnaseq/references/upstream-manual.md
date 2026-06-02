# Path B — Standalone tools (reads → quant)

Run each stage yourself when you want transparency, have only a few samples, or can't use Nextflow/containers. Results are equivalent to Path A when tools, versions, reference, and parameters match. Quantify **every sample identically**.

Install (bioconda): `conda create -n rnaseq -c bioconda -c conda-forge fastqc fastp trim-galore "star=2.7.11b" "salmon=1.10.3" subread multiqc rseqc`.

## 0. Reference data

You need, for your organism and a **pinned** annotation release:
- genome FASTA (`genome.fa`) and matching annotation GTF (`annotation.gtf`) — for STAR/featureCounts.
- transcriptome FASTA (`transcripts.fa`, cDNA) — for Salmon.

Fetch download links with the `gget` skill (`gget ref -w dna,gtf,cdna <species>`), or from Ensembl/GENCODE directly. Keep genome and GTF from the **same** release.

## 1. QC raw reads — FastQC

```bash
mkdir -p qc/raw
fastqc -t 8 -o qc/raw reads/*.fastq.gz
```

Inspect per-base quality, adapter content, duplication, and over-represented sequences. Interpretation/thresholds: `design-and-qc.md`.

## 2. Trim — fastp (recommended) or Trim Galore

`fastp` is fast and emits a JSON/HTML report MultiQC understands:

```bash
mkdir -p trimmed
fastp \
  -i reads/s1_R1.fastq.gz -I reads/s1_R2.fastq.gz \
  -o trimmed/s1_R1.fq.gz  -O trimmed/s1_R2.fq.gz \
  --detect_adapter_for_pe --qualified_quality_phred 20 --length_required 36 \
  --thread 4 --json qc/s1.fastp.json --html qc/s1.fastp.html
```

Trim Galore (wraps Cutadapt + FastQC; auto-detects adapters):

```bash
trim_galore --paired --cores 4 --fastqc -o trimmed reads/s1_R1.fastq.gz reads/s1_R2.fastq.gz
```

Aggressive quality trimming is usually unnecessary for modern data and for STAR (which soft-clips); adapter removal is the main goal. Re-run FastQC on trimmed reads to confirm.

## 3a. STAR — genome alignment + gene counts

Build the index once per genome+annotation+read-length. `--sjdbOverhang` = read length − 1 (100 is a safe default). Human needs ~30 GB RAM.

```bash
STAR --runMode genomeGenerate --runThreadN 12 \
  --genomeDir star_index \
  --genomeFastaFiles genome.fa \
  --sjdbGTFfile annotation.gtf \
  --sjdbOverhang 100
```

Align each sample, asking STAR to also count reads per gene:

```bash
STAR --runThreadN 12 --genomeDir star_index \
  --readFilesIn trimmed/s1_R1.fq.gz trimmed/s1_R2.fq.gz --readFilesCommand zcat \
  --outSAMtype BAM SortedByCoordinate \
  --quantMode GeneCounts \
  --outFileNamePrefix star/s1.
```

`--quantMode GeneCounts` writes `s1.ReadsPerGene.out.tab` (4 columns, see strandedness below). The sorted BAM is useful for QC (RSeQC, IGV) and for featureCounts.

## 3b. Salmon — decoy-aware quasi-mapping

Build a **decoy-aware** index (genome as decoy) so reads from unannotated/genomic regions don't get miscounted against transcripts:

```bash
# 1. Decoys = all genome sequence names; gentrome = transcriptome THEN genome (order matters)
grep '^>' genome.fa | sed 's/^>//; s/ .*//' > decoys.txt
cat transcripts.fa genome.fa | gzip > gentrome.fa.gz

# 2. Index (k=31 works for reads >=75 bp; use smaller k for shorter reads)
salmon index -t gentrome.fa.gz -d decoys.txt -i salmon_index -k 31 -p 12
```

Quantify each sample (`-l A` auto-detects library type/strandedness; enable bias correction):

```bash
salmon quant -i salmon_index -l A \
  -1 trimmed/s1_R1.fq.gz -2 trimmed/s1_R2.fq.gz \
  --gcBias --seqBias --validateMappings -p 8 \
  -o quant/s1
```

Each `quant/<sample>/quant.sf` is transcript-level; aggregate to gene level with `scripts/build_counts_matrix.py --from salmon` (needs a `tx2gene` map — see `counts-and-handoff.md`). Always check the reported mapping rate (`quant/<sample>/logs/salmon_quant.log`).

## 3c. featureCounts — counts from a STAR BAM (alternative to STAR GeneCounts)

```bash
featureCounts -T 8 -p --countReadPairs \
  -a annotation.gtf -g gene_id \
  -s 2 \                       # strandedness: 0 unstranded, 1 forward, 2 reverse
  -o counts/featurecounts.txt \
  star/s1.Aligned.sortedByCoord.out.bam star/s2.Aligned.sortedByCoord.out.bam ...
```

Pass all sample BAMs at once to get one matrix. Parse it with `scripts/build_counts_matrix.py --from featurecounts`.

## Strandedness — get this right

The wrong setting silently discards ~half the reads. Determine it once, then apply consistently:

- **Salmon** `-l A` auto-detects and reports the library type in `quant/<sample>/lib_format_counts.json` (`ISR` = reverse-stranded paired, `ISF` = forward, `IU`/`IS` = unstranded).
- Or run **RSeQC** `infer_experiment.py -r genes.bed -i s1.bam` on a STAR BAM.

Map the result to each tool:

| Library | Salmon `-l` | featureCounts `-s` | STAR column (in `ReadsPerGene.out.tab`) |
|---------|-------------|--------------------|------------------------------------------|
| Unstranded | `IU` (auto `A`) | `0` | col 2 |
| Forward (e.g. Ligation) | `ISF` (auto `A`) | `1` | col 3 |
| Reverse (e.g. dUTP/TruSeq stranded) | `ISR` (auto `A`) | `2` | col 4 |

Illumina TruSeq Stranded mRNA — the most common kit — is **reverse** (`-s 2`, STAR col 4). When in doubt, let Salmon auto-detect and match the others to it.

## 4. Aggregate QC — MultiQC

```bash
multiqc qc/ star/ quant/ counts/ -o qc/multiqc
```

MultiQC collates FastQC, fastp/Trim Galore, STAR, Salmon, and featureCounts logs into one report — your QC narrative for the methods section. Then build the counts matrix (`counts-and-handoff.md`) and hand off to `pydeseq2`.
