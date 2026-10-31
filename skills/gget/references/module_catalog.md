# gget Module Catalog

Every module by category, with selected parameters and CLI/Python examples for gget 0.30.8. Examples are illustrative unless identified as executed in [workflows.md](workflows.md); optional setup, input files, and network access are required. See [database contracts](database_info.md) for authentication, return fields, and pagination limits.
This is the usage-oriented cut; see `module_reference.md` for the fuller per-parameter
reference and `database_info.md` for the underlying data sources.

## Module Categories

### 1. Reference & Gene Information

#### gget ref - Reference Genome Downloads

Retrieve download links and metadata for Ensembl reference genomes.

**Parameters**:
- `species`: Genus_species format (e.g., 'homo_sapiens', 'mus_musculus'). Shortcuts: 'human', 'mouse'
- `-w/--which`: Specify return types as comma-separated CLI values or Python list (gtf, cdna, dna, cds, cdrna, pep). Default: all
- `-r/--release`: Ensembl release number (default: latest)
- `-od/--out_dir`: Directory for downloaded files
- `-l/--list_species`: List available vertebrate species
- `-liv/--list_iv_species`: List available invertebrate species
- `-ftp`: Return only FTP links
- `-d/--download`: CLI-only download (requires curl; Python returns links)

**Examples**:
```bash
# List available species
gget ref --list_species

# Get all reference files for human
gget ref homo_sapiens

# Download GTF and cDNA files for mouse
gget ref -w gtf,cdna -d mouse
```

```python
# Python
gget.ref("homo_sapiens")
gget.ref("mus_musculus", which=["gtf", "cdna"])  # metadata/links; CLI -d downloads
```

#### gget search - Gene Search

Locate genes by name, description, and Ensembl synonyms across species.

**Parameters**:
- `searchwords`: One or more search terms (case-insensitive)
- `-s/--species`: Target species (e.g., 'homo_sapiens', 'mouse')
- `-r/--release`: Ensembl release number
- `-t/--id_type`: Return 'gene' (default) or 'transcript'
- `-ao/--andor`: 'or' (default) finds ANY searchword; 'and' requires ALL
- `-l/--limit`: Maximum results to return
- `wrap_text`: Python-only display helper for wide DataFrames

**Returns**: ensembl_id, gene_name, ensembl_description, ext_ref_description, biotype, synonym, url

**Examples**:
```bash
# Search for GABA-related genes in human
gget search -s human gaba gamma-aminobutyric

# Find specific gene, require all terms
gget search -s mouse -ao and pax7 transcription
```

```python
# Python
gget.search(["gaba", "gamma-aminobutyric"], species="homo_sapiens")
```

#### gget info - Gene/Transcript Information

Retrieve comprehensive gene and transcript metadata from Ensembl, UniProt, and NCBI.

**Parameters**:
- `ens_ids`: One or more Ensembl IDs (also supports WormBase, Flybase IDs). Limit: ~1000 IDs
- `-n/--ncbi`: Disable NCBI data retrieval
- `-u/--uniprot`: Disable UniProt data retrieval
- `-pdb`: Include PDB identifiers (increases runtime)

**Returns**: UniProt ID, NCBI gene ID, primary gene name, synonyms, protein names, descriptions, biotype, canonical transcript

**Examples**:
```bash
# Get info for multiple genes
gget info ENSG00000034713 ENSG00000104853 ENSG00000170296

# Include PDB IDs
gget info ENSG00000034713 -pdb
```

```python
# Python
gget.info(["ENSG00000034713", "ENSG00000104853"], pdb=True)
```

#### gget seq - Sequence Retrieval

Fetch nucleotide or amino acid sequences for genes and transcripts.

**Parameters**:
- `ens_ids`: One or more Ensembl identifiers
- `-t/--translate`: Fetch amino acid sequences instead of nucleotide
- `-iso/--isoforms`: Return all transcript variants (gene IDs only)

**Returns**: Python list of FASTA lines (header, sequence, ...), or None on failure; CLI prints FASTA

**Examples**:
```bash
# Get nucleotide sequences
gget seq ENSG00000034713 ENSG00000104853

# Get all protein isoforms
gget seq -t -iso ENSG00000034713
```

```python
# Python
gget.seq(["ENSG00000034713"], translate=True, isoforms=True)
```

### 2. Sequence Analysis & Alignment

#### gget blast - BLAST Searches

BLAST nucleotide or amino acid sequences against standard databases.

**Parameters**:
- `sequence`: Sequence string or path to FASTA/.txt file
- `-p/--program`: blastn, blastp, blastx, tblastn, tblastx (auto-detected)
- `-db/--database`:
  - Nucleotide: nt, refseq_rna, pdbnt
  - Protein: nr, swissprot, pdbaa, refseq_protein
- `-l/--limit`: Max hits (default: 50)
- `-e/--expect`: E-value cutoff (default: 10.0)
- `-lcf/--low_comp_filt`: Enable low complexity filtering
- `-mbo/--megablast_off`: Disable MegaBLAST (blastn only)

**Examples**:
```bash
# BLAST protein sequence
gget blast MKWMFKEDHSLEHRCVESAKIRAKYPDRVPVIVEKVSGSQIVDIDKRKYLVPSDITVAQFMWIIRKRIQLPSEKAIFLFVDKTVPQSR

# BLAST from file with specific database
gget blast sequence.fasta -db swissprot -l 10
```

```python
# Python
gget.blast("MKWMFK...", database="swissprot", limit=10)
```

#### gget blat - BLAT Searches

Locate genomic positions of sequences using UCSC BLAT.

**Parameters**:
- `sequence`: Sequence string or path to FASTA/.txt file
- `-st/--seqtype`: 'DNA', 'protein', 'translated%20RNA', 'translated%20DNA' (auto-detected)
- `-a/--assembly`: Target assembly (default: 'human'/hg38; options: 'mouse'/mm39, 'zebrafinch'/taeGut2, etc.)

**Returns**: genome, query size, alignment positions, matches, mismatches, alignment percentage

**Examples**:
```bash
# Find genomic location in human
gget blat ATCGATCGATCGATCG

# Search in different assembly
gget blat -a mm39 ATCGATCGATCGATCG
```

```python
# Python
gget.blat("ATCGATCGATCGATCG", assembly="mouse")
```

#### gget muscle - Multiple Sequence Alignment

Align multiple nucleotide or amino acid sequences using Muscle5.

**Parameters**:
- `fasta`: Sequences or path to FASTA/.txt file
- `-s5/--super5`: Use Super5 algorithm for faster processing (large datasets)

**Returns**: Aligned sequences in ClustalW format or aligned FASTA (.afa)

**Examples**:
```bash
# Align sequences from file
gget muscle sequences.fasta -o aligned.afa

# Use Super5 for large dataset
gget muscle large_dataset.fasta -s5
```

```python
# Python
gget.muscle("sequences.fasta", out="aligned.afa")
```

#### gget diamond - Local Sequence Alignment

Perform fast local protein alignment or translated nucleotide-to-protein alignment using DIAMOND.

**Parameters**:
- Query: Sequences (string/list) or FASTA file path
- `-ref/--reference`: Reference sequences (string/list) or FASTA file path (required)
- `-s/--sensitivity`: fast, mid-sensitive, sensitive, more-sensitive, very-sensitive (default), ultra-sensitive
- `-t/--threads`: CPU threads (default: 1)
- `-db/--diamond_db`: Database output path (reference still required)
- `-x/--translated`: Enable nucleotide query to amino acid reference alignment

**Returns**: Identity percentage, sequence lengths, match positions, gap openings, E-values, bit scores

**Examples**:
```bash
# Align against reference
gget diamond GGETISAWESQME -ref reference.fasta -t 4

# Translate nucleotide query against amino acid reference
gget diamond query_nt.fasta -ref proteins.fasta --translated
```

```python
# Python
gget.diamond("GGETISAWESQME", reference="reference.fasta", threads=4)
gget.diamond("ATGGGC...", reference="proteins.fasta", translated=True)
```

### 3. Structural & Protein Analysis

#### gget pdb - Protein Structures

Query RCSB Protein Data Bank for structure and metadata.

**Parameters**:
- `pdb_id`: PDB identifier (e.g., '7S7U')
- `-r/--resource`: Data type (pdb, mmcif, entry, pubmed, assembly, entity types)
- `-i/--identifier`: Assembly, entity, or chain ID

**Returns**: PDB/mmCIF text (structures) or dictionary (metadata); `resource="pdb"` falls back to mmCIF if PDB is unavailable

**Examples**:
```bash
# Download PDB structure
gget pdb 7S7U -o 7S7U.pdb

# Get metadata
gget pdb 7S7U -r entry
```

```python
# Python
gget.pdb("7S7U", save=True)
```

#### gget g2p - Residue Annotations and Isoform Maps

Public G2P lookups, added in 0.30.7 and updated in 0.30.8. At least one of `gene`
or `uniprot_id` is required. Gene-only lookup chooses a reviewed human UniProt
match; specify the pair when identity matters. `resource` is `features`, `map`,
or `alignment`. Alignment requires explicit canonical `uniprot_id` and alternative
`isoform`. `residues` filters positions locally for features/alignment, not map.
Python returns DataFrame or None on request failure; invalid inputs can raise.
There is no Python `json` argument. `out` writes CSV and overrides `save`.

```bash
gget g2p TP53 -u P04637 -r map --csv
```

```python
mapping = gget.g2p("TP53", uniprot_id="P04637", resource="map")
features = gget.g2p("TP53", uniprot_id="P04637", residues=[175, 248, 273])
```

Results include `gene_name`/`uniprot_id`; maps add `PDB Ids List`. The public API
does not expose the portal's ClinVar/gnomAD/HGMD variant overlays. Per-residue
scores and predictions require their own calibration; they do not establish
pathogenicity. [Official manual](https://scverse.org/gget/en/g2p.html).

#### gget alphafold - Protein Structure Prediction

Legacy AlphaFold2 wrapper, deprecated and no longer actively maintained since 0.30.7. Retained for existing environments; prefer a maintained predictor for new work.

**Setup Required**:
```bash
# Legacy setup; installs third-party dependencies and downloads model parameters
gget setup alphafold
```

**Parameters**:
- `sequence`: Amino acid sequence (string), multiple sequences (list), or FASTA file. Multiple sequences trigger multimer modeling
- `-mr/--multimer_recycles`: Recycling iterations (default: 3; higher values increase compute without guaranteeing accuracy)
- `-mfm/--multimer_for_monomer`: Apply multimer model to single proteins
- `-r/--relax`: AMBER relaxation for top-ranked model
- `-jhd/--jackhmmer_savedir`: Directory for temporary jackhmmer files
- `plot`: Python-only; generate interactive 3D visualization (default: True)
- `show_sidechains`: Python-only; include side chains (default: True)

**Returns**: PDB structure file, JSON alignment error data, optional 3D visualization

**Examples**:
```bash
# Predict single protein structure
gget alphafold MKWMFKEDHSLEHRCVESAKIRAKYPDRVPVIVEKVSGSQIVDIDKRKYLVPSDITVAQFMWIIRKRIQLPSEKAIFLFVDKTVPQSR

# Legacy multimer example; increased recycles are not an accuracy guarantee
gget alphafold sequence1.fasta -mr 20 -r
```

```python
# Python with visualization
gget.alphafold("MKWMFK...", plot=True, show_sidechains=True)

# Multimer prediction
gget.alphafold(["sequence1", "sequence2"], multimer_recycles=20)
```

#### gget elm - Eukaryotic Linear Motifs

Predict Eukaryotic Linear Motifs in protein sequences.

**Setup Required**:
```bash
gget setup elm
```

**Parameters**:
- `sequence`: Amino acid sequence or UniProt Acc
- `-u/--uniprot`: Indicates sequence is UniProt Acc
- `-e/--expand`: Include protein names, organisms, references
- `-s/--sensitivity`: DIAMOND alignment sensitivity (default: "very-sensitive")
- `-t/--threads`: Number of threads (default: 1)

**Returns**: Two outputs:
1. **ortholog_df**: Linear motifs from orthologous proteins
2. **regex_df**: Motifs directly matched in input sequence

**Examples**:
```bash
# Predict motifs from sequence
gget elm LIAQSIGQASFV -o results

# Use UniProt accession with expanded info
gget elm --uniprot Q02410 -e
```

```python
# Python
ortholog_df, regex_df = gget.elm("LIAQSIGQASFV")
```

### 4. Expression & Disease Data

#### gget archs4 - Gene Correlation & Tissue Expression

Query ARCHS4 database for correlated genes or tissue expression data.

**Parameters**:
- `gene`: Gene symbol or Ensembl ID (with `--ensembl` flag)
- `-w/--which`: 'correlation' (default, returns 100 most correlated genes) or 'tissue' (expression atlas)
- `-s/--species`: 'human' (default) or 'mouse' (tissue data only)
- `-e/--ensembl`: Input is Ensembl ID

**Returns**:
- **Correlation mode**: `gene_symbol`, `pearson_correlation` (human only; Python `gene_count` controls count)
- **Tissue mode**: `id`, `min`, `q1`, `median`, `q3`, `max`

**Examples**:
```bash
# Get correlated genes
gget archs4 ACE2

# Get tissue expression
gget archs4 -w tissue ACE2
```

```python
# Python
gget.archs4("ACE2", which="tissue")
```

#### gget cellxgene - Single-Cell RNA-seq Data

Query CZ CELLxGENE Discover Census for single-cell data.

**Setup Required**:
```bash
gget setup cellxgene
```

**Parameters**:
- `--gene` (-g): Gene names or Ensembl IDs (case-sensitive! 'PAX7' for human, 'Pax7' for mouse)
- `--tissue`: Tissue type(s)
- `--cell_type`: Specific cell type(s)
- `--species` (-s): 'homo_sapiens' (default), 'mus_musculus', 'macaca_mulatta', 'callithrix_jacchus', or 'pan_troglodytes' (primates require Census 2025-11-08 or newer)
- `--census_version` (-cv): Version ("stable", "latest", or dated)
- `--ensembl` (-e): Use Ensembl IDs
- `--meta_only` (-mo): Return metadata only
- Additional filters: disease, development_stage, sex, assay, dataset_id, donor_id, self_reported_ethnicity, suspension_type

**Returns**: AnnData with raw counts; metadata-only DataFrame rows are cells, and the gene filter is ignored in that mode. Pin a dated release and scope observations.

**Examples**:
```bash
# Get single-cell data for specific genes and cell types
gget cellxgene --gene ACE2 ABCA1 --tissue lung --cell_type "mucus secreting cell" -o lung_data.h5ad

# Metadata only
gget cellxgene --gene PAX7 --tissue muscle --meta_only -o metadata.csv
```

```python
# Python
adata = gget.cellxgene(gene=["ACE2", "ABCA1"], tissue="lung", cell_type="mucus secreting cell")
```

#### gget enrichr - Enrichment Analysis

Perform ontology enrichment analysis on gene lists using Enrichr.

**Parameters**:
- `genes`: Gene symbols, or Ensembl IDs with `ensembl=True` / CLI `--ensembl`
- `-db/--database`: Reference database (supports shortcuts: 'pathway', 'transcription', 'ontology', 'diseases_drugs', 'celltypes')
- `-s/--species`: human (default), mouse, fly, yeast, worm, fish
- `-bkg_l/--background_list`: Background genes for comparison
- `-ko/--kegg_out`: Save KEGG pathway images with highlighted genes
- `plot`: Python-only; generate graphical results

**Database Shortcuts**:
- 'pathway' → KEGG_2021_Human
- 'transcription' → ChEA_2016
- 'ontology' → GO_Biological_Process_2021
- 'diseases_drugs' → GWAS_Catalog_2019
- 'celltypes' → PanglaoDB_Augmented_2021
- 'kinase_interactions' → KEA_2015

Shortcuts apply to human/mouse only. Other species need their full library names; custom backgrounds are human/mouse only. Ensembl background IDs also require `ensembl_bkg=True`.

**Examples**:
```bash
# Enrichment analysis for ontology
gget enrichr -db ontology ACE2 AGT AGTR1

# Save KEGG pathways
gget enrichr -db pathway ACE2 AGT AGTR1 -ko ./kegg_images/
```

```python
# Python with plot
gget.enrichr(["ACE2", "AGT", "AGTR1"], database="ontology", plot=True)
```

#### gget bgee - Orthology & Expression

Retrieve orthology and gene expression data from Bgee database.

**Parameters**:
- `ens_id`: Ensembl gene ID or NCBI gene ID (for non-Ensembl species). Multiple IDs supported when `type=expression`
- `-t/--type`: 'orthologs' (default) or 'expression'

**Returns**:
- **Orthologs mode**: Matching genes across species with IDs, names, taxonomic info
- **Expression mode**: Anatomical entities, confidence scores, expression status

**Examples**:
```bash
# Get orthologs
gget bgee ENSG00000169194

# Get expression data
gget bgee ENSG00000169194 -t expression

# Multiple genes
gget bgee ENSBTAG00000047356 ENSBTAG00000018317 -t expression
```

```python
# Python
gget.bgee("ENSG00000169194", type="orthologs")
```

#### gget opentargets - Disease & Drug Associations

Retrieve disease and drug associations from OpenTargets.

**Parameters**:
- Ensembl gene ID (required)
- `-r/--resource`: diseases (default), drugs, tractability, pharmacogenetics, expression, depmap, interactions
- `-l/--limit`: Cap results count
- `--filter`: Exact-match filters using returned OpenTargets column names; repeat on the CLI or pass a Python dict
- Filters use AND logic; there is no `--or` option in the released 0.30.8 CLI

**Current notes**:
- gget 0.30.8 returns dot-separated columns, including `disease.name`, `score`, `drug.name`, and `drug.maximumClinicalStage`.
- Expression is `baselineExpression`: `median/min/q1/q3/max/unit` and `tissueBiosample.*`/`celltypeBiosample.*`.
- Filters apply locally after limit. Expression fetches one page (max 3000); diseases/drugs/interactions use server default pages. `limit=None` does not make a complete export.
- The older `--filter_mode` argument was removed upstream.

**Examples**:
```bash
# Get associated diseases
gget opentargets ENSG00000169194 -r diseases -l 5

# Get associated drugs
gget opentargets ENSG00000169194 -r drugs -l 10

# Filter interactions by returned column names
gget opentargets ENSG00000169194 -r interactions --filter intA=P35225 --filter targetB.id=ENSG00000077238
```

```python
# Python
gget.opentargets("ENSG00000169194", resource="diseases", limit=5)
gget.opentargets(
    "ENSG00000169194",
    resource="interactions",
    filters={"intA": "P35225", "targetB.id": "ENSG00000077238"},
)
```

#### gget cbio - cBioPortal Cancer Genomics

Plot cancer genomics heatmaps using cBioPortal data.

**Setup:** `gget setup cbio` installs optional dependencies.

**Two subcommands**:

**search** - Find study IDs:
```bash
gget cbio search breast lung
```

**plot** - Generate heatmaps:

**Parameters**:
- `-s/--study_ids`: Space-separated cBioPortal study IDs (required)
- `-g/--genes`: Space-separated gene names or Ensembl IDs (required)
- `-st/--stratification`: Column to organize data (tissue, cancer_type, cancer_type_detailed, study_id, sample)
- `-vt/--variation_type`: Data type (mutation_occurrences, cna_nonbinary, sv_occurrences, cna_occurrences, Consequence)
- `-f/--filter`: Filter by column value (e.g., 'study_id:msk_impact_2017')
- `-dd/--data_dir`: Cache directory (default: ./gget_cbio_cache)
- `-fd/--figure_dir`: Output directory (default: ./gget_cbio_figures)
- `-dpi`: Resolution (default: 100)
- `-sh/--show`: Display plot in window
- `-nc/--no_confirm`: Skip download confirmations

**Examples**:
```bash
# Search for studies
gget cbio search esophag ovary

# Create heatmap
gget cbio plot -s msk_impact_2017 -g AKT1 ALK BRAF -st tissue -vt mutation_occurrences
```

```python
# Python
gget.cbio_search(["esophag", "ovary"])
gget.cbio_plot(["msk_impact_2017"], ["AKT1", "ALK"], stratification="tissue")
```

#### gget cosmic - COSMIC Database

Search COSMIC (Catalogue Of Somatic Mutations In Cancer) database.

**Important**: License fees apply for commercial use. Requires COSMIC account credentials.
Avoid passing COSMIC credentials directly as CLI arguments on shared systems because command-line arguments can be exposed in shell history, process listings, and logs. Prefer the interactive prompt (`gget cosmic --download_cosmic ...`) or named environment variables read inside Python.

**Parameters**:
- `searchterm`: Gene name, Ensembl ID, mutation notation, or sample ID
- `-ctp/--cosmic_tsv_path`: Path to downloaded COSMIC TSV file (required for querying)
- `-l/--limit`: Maximum results (default: 100)

**Database download flags**:
- `-d/--download_cosmic`: Activate download mode
- `-gm/--gget_mutate`: Create version for gget mutate
- `-cp/--cosmic_project`: Database type (cancer, cancer_example, census, cell_line, resistance, genome_screen, targeted_screen)
- `-cv/--cosmic_version`: COSMIC version
- `-gv/--grch_version`: Human reference genome (37 or 38)
- `--email`, `--password`: COSMIC credentials for non-interactive downloads; prefer prompt or Python env vars

**Examples**:
```bash
# First download database; gget prompts for COSMIC email/password
gget cosmic --download_cosmic --cosmic_project cancer

# Then query
gget cosmic EGFR --cosmic_tsv_path "CancerMutationCensus_AllData_Tsv_v101_GRCh37/CancerMutationCensus_AllData_v101_GRCh37.tsv" -l 10
```

```python
# Python
import os

gget.cosmic(
    searchterm=None,
    download_cosmic=True,
    cosmic_project="cancer",
    email=os.environ["COSMIC_EMAIL"],
    password=os.environ["COSMIC_PASSWORD"],
)
gget.cosmic("EGFR", cosmic_tsv_path="cosmic_data.tsv", limit=10)
```

### 5. Viral & Mouse Specificity Data

#### gget virus - Viral Sequence Downloads

Download viral nucleotide sequences plus linked metadata from INSDC sources via NCBI Virus, with optional GenBank metadata enrichment. Results are saved to an output folder as FASTA, CSV, JSONL, and a command summary file.

**Parameters**:
- `virus`: Virus taxon name, taxon ID, accession, space-separated accessions, or path to a text file of accessions
- `-a/--is_accession`: Treat `virus` as accession input
- `--is_sars_cov2`, `--is_alphainfluenza`: Use optimized cached NCBI datasets paths for SARS-CoV-2 or Influenza A
- `--host`: Host organism name or NCBI taxonomy ID
- `--nuc_completeness`: complete or partial
- `--min_seq_length`, `--max_seq_length`: Sequence length filters
- `-g/--genbank_metadata`: Fetch detailed GenBank metadata; auto-enabled by some annotation filters
- `--segment`, `--vaccine_strain`, `--annotated`, `--lab_passaged`, `--source_database`: Common viral metadata filters
- `--download_all_accessions`: Apply filters across all viral accessions
- `--baseline`, `--merge-results`: Resume or merge with prior metadata from partial/previous runs

**Important**: Do not use `--download_all_accessions` without restrictive filters; it can attempt to download the entire Viruses taxonomy and consume substantial time, bandwidth, and disk.

**Examples**:
```bash
# Complete Zika genomes from human hosts
gget virus "Zika virus" --nuc_completeness complete --host human --out zika_data

# SARS-CoV-2 reference genome by accession
gget virus NC_045512.2 --is_accession --is_sars_cov2
```

```python
# Python
gget.virus(
    "SARS-CoV-2",
    host="human",
    nuc_completeness="complete",
    min_seq_length=29000,
    genbank_metadata=True,
    is_sars_cov2=True,
    outfolder="covid_data",
)
```

#### gget 8cube - Mouse Specificity & Expression

Query 8cubeDB for snRNA-seq gene specificity metrics and normalized expression values across mouse strains, tissues, sexes, and individuals.

**Subcommands**:
- `gget 8cube specificity <genes...>`: Return gene-level psi/zeta specificity statistics
- `gget 8cube psi_block <genes...> --analysis_level <level> --analysis_type <type>`: Return block-level specificity
- `gget 8cube expression <genes...> --analysis_level <level> --analysis_type <type>`: Return mean/variance normalized expression

**Examples**:
```bash
gget 8cube specificity Acsm2 ENSMUSG00000046623.9
gget 8cube psi_block Acsm2 --analysis_level Kidney --analysis_type "Sex:Celltype"
gget 8cube expression Gjb4 --analysis_level Across_tissues --analysis_type Strain
```

```python
# Python
from gget import specificity, psi_block, gene_expression

specificity(["Acsm2", "ENSMUSG00000046623.9"])
psi_block(["Acsm2"], analysis_level="Kidney", analysis_type="Sex:Celltype")
gene_expression(["Gjb4"], analysis_level="Across_tissues", analysis_type="Strain")
```

### 6. Additional Tools

#### gget mutate - Generate Mutated Sequences

Generate mutated nucleotide sequences from mutation annotations.

**Scope**: Applies mutation annotations to supplied nucleotide sequences. Python returns raw mutated sequence strings when `out` is omitted; `out` writes FASTA. Verify the exact transcript/CDS and reference bases before applying `c.` coordinates; this does not assess functional impact. Broader variant-screening workflows are maintained in the upstream `kvar` project.

**Parameters**:
- `sequences`: FASTA file path or direct nucleotide sequence input (string/list)
- `-m/--mutations`: Mutation string/list, CSV/TSV path, or DataFrame with mutation data (required)
- `-mc/--mut_column`: Mutation column name (default: 'mutation')
- `-sic/--seq_id_column`: Sequence ID column (default: 'seq_ID')
- `-mic/--mut_id_column`: Mutation ID column (default: same as mut_column)
- `-k/--k`: Length of flanking sequences (default: 30 nucleotides)
- `-o/--out`: Output FASTA path; without it Python returns a list of mutated sequences

**Returns**: List of mutated sequence strings in Python; `out` writes FASTA

**Examples**:
```bash
# Single mutation
gget mutate ATCGCTAAGCT -m "c.4G>T"

# Multiple sequences with one mutation per sequence
gget mutate ATCGCTAAGCT TAGCTA -m "c.4G>T" "c.1_3inv" -o mutated.fasta
```

```python
# Python
gget.mutate("ATCGCTAAGCT", "c.4G>T")
gget.mutate(["ATCGCTAAGCT", "TAGCTA"], ["c.4G>T", "c.1_3inv"], out="mutated.fasta")
```

#### gget gpt - OpenAI Text Generation

Legacy OpenAI wrapper; deprecated and no longer actively maintained since 0.30.7. Examples below are illustrative and require an account-compatible model.

**Setup Required**:
```bash
gget setup gpt
```

**Important**: Requires an OpenAI API key. Do not hard-code the key in notebooks, scripts, shell history, or committed files. Prefer a named environment variable such as `OPENAI_API_KEY`, and inspect the account and model requirements before use.

**Parameters**:
- `prompt`: Text input for generation (required)
- `api_key`: OpenAI authentication (required by the upstream API)
- Model configuration: model, temperature, top_p, stop, max_tokens, frequency_penalty, presence_penalty, logit_bias
- Default model: gpt-3.5-turbo (upstream default; verify available models in your OpenAI account)

**Examples**:
For CLI usage, `gget gpt` expects the API key as an argument. Avoid this on shared systems because process arguments can be visible to other users.

```python
# Python
import os

# Legacy wrapper uses openai.ChatCompletion.create, removed by modern SDKs.
# Do not execute it in a modern SDK environment or assume the default model exists.
```

#### gget setup - Install Dependencies

Install/download third-party dependencies for specific modules.

As of gget 0.29.2, `gget setup` tries `uv pip install` first for Python dependencies and falls back to plain `pip install` if uv is unavailable or fails.

**Parameters**:
- `module`: Module name requiring dependency installation
- `-o/--out`: Output folder path (elm module only)

**Modules requiring setup**:
- `alphafold` - Downloads ~4GB of model parameters
- `cbio` - Installs optional cBioPortal dependencies (bravado)
- `cellxgene` - Installs cellxgene-census (may require Python 3.12/3.13 if the latest Python is unsupported)
- `elm` - Downloads local ELM database
- `gpt` - Installs/configures OpenAI integration dependencies

**Examples**:
```bash
# Setup AlphaFold
gget setup alphafold

# Setup ELM with custom directory
gget setup elm -o /path/to/elm_data
```

```python
# Python
gget.setup("alphafold")
```
