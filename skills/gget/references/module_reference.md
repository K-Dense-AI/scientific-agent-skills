# gget Module Reference

Comprehensive parameter reference for all gget modules.

## Reference & Gene Information Modules

### gget ref
Retrieve Ensembl reference genome FTPs and metadata.

**Parameters:**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `species` | str | Species in Genus_species format or shortcuts ('human', 'mouse') | Required |
| `-w/--which` | str/list | File types to return: gtf, cdna, dna, cds, cdrna, pep | All |
| `-r/--release` | int | Ensembl release number | Latest |
| `-od/--out_dir` | str | Output directory path | None |
| `-o/--out` | str | JSON file path for results | None |
| `-l/--list_species` | flag | List available vertebrate species | False |
| `-liv/--list_iv_species` | flag | List available invertebrate species | False |
| `-ftp` | flag | Return only FTP links | False |
| `-d/--download` | flag | Download files (requires curl) | False |
| `-q/--quiet` | flag | Suppress progress information | False |

**Returns:** JSON containing FTP links, Ensembl release numbers, release dates, file sizes

---

### gget search
Search for genes by name or description in Ensembl.
Search includes Ensembl synonyms in current gget versions.

**Parameters:**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `searchwords` | str/list | Search terms (case-insensitive) | Required |
| `-s/--species` | str | Target species or core database name | Required |
| `-r/--release` | int | Ensembl release number | Latest |
| `-t/--id_type` | str | Return 'gene' or 'transcript' | 'gene' |
| `-ao/--andor` | str | 'or' (ANY term) or 'and' (ALL terms) | 'or' |
| `-l/--limit` | int | Maximum results to return | None |
| `-o/--out` | str | Output file path (CSV/JSON) | None |
| `wrap_text` | bool | Python-only wrapped text display for wide results | False |

**Returns:** ensembl_id, gene_name, ensembl_description, ext_ref_description, biotype, URL

---

### gget info
Get comprehensive gene/transcript metadata from Ensembl, UniProt, and NCBI.

**Parameters:**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `ens_ids` | str/list | Ensembl IDs (WormBase, Flybase also supported) | Required |
| `-o/--out` | str | Output file path (CSV/JSON) | None |
| `-n/--ncbi` | bool | Disable NCBI data retrieval | False |
| `-u/--uniprot` | bool | Disable UniProt data retrieval | False |
| `-pdb` | bool | Include PDB identifiers | False |
| `-csv` | flag | Return CSV format (CLI) | False |
| `-q/--quiet` | flag | Suppress progress display | False |

**Python-specific:**
- `save=True`: Save output to current directory
- `wrap_text=True`: Format dataframe with wrapped text

**Note:** Processing >1000 IDs simultaneously may cause server errors.

**Returns:** UniProt ID, NCBI gene ID, gene name, synonyms, protein names, descriptions, biotype, canonical transcript

---

### gget seq
Retrieve nucleotide or amino acid sequences in FASTA format.

**Parameters:**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `ens_ids` | str/list | Ensembl identifiers | Required |
| `-o/--out` | str | Output file path | stdout |
| `-t/--translate` | flag | Fetch amino acid sequences | False |
| `-iso/--isoforms` | flag | Return all transcript variants | False |
| `-q/--quiet` | flag | Suppress progress information | False |

**Data sources:** Ensembl (nucleotide), UniProt (amino acid)

**Returns:** FASTA format sequences

---

## Sequence Analysis & Alignment Modules

### gget blast
BLAST sequences against standard databases.

**Parameters:**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `sequence` | str | Sequence or path to FASTA/.txt | Required |
| `-p/--program` | str | blastn, blastp, blastx, tblastn, tblastx | Auto-detect |
| `-db/--database` | str | nt, refseq_rna, pdbnt, nr, swissprot, pdbaa, refseq_protein | nt or nr |
| `-l/--limit` | int | Max hits returned | 50 |
| `-e/--expect` | float | E-value cutoff | 10.0 |
| `-lcf/--low_comp_filt` | flag | Enable low complexity filtering | False |
| `-mbo/--megablast_off` | flag | Disable MegaBLAST (blastn only) | False |
| `-o/--out` | str | Output file path | None |
| `-q/--quiet` | flag | Suppress progress | False |

**Returns:** Description, Scientific Name, Common Name, Taxid, Max Score, Total Score, Query Coverage

---

### gget blat
Find genomic positions using UCSC BLAT.

**Parameters:**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `sequence` | str | Sequence or path to FASTA/.txt | Required |
| `-st/--seqtype` | str | 'DNA', 'protein', 'translated%20RNA', 'translated%20DNA' | Auto-detect |
| `-a/--assembly` | str | Target assembly (hg38, mm39, taeGut2, etc.) | 'human'/hg38 |
| `-o/--out` | str | Output file path | None |
| `-csv` | flag | Return CSV format (CLI) | False |
| `-q/--quiet` | flag | Suppress progress | False |

**Returns:** genome, query size, alignment start/end, matches, mismatches, alignment percentage

---

### gget muscle
Align multiple sequences using Muscle5.

**Parameters:**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `fasta` | str/list | Sequences or FASTA file path | Required |
| `-o/--out` | str | Output file path | stdout |
| `-s5/--super5` | flag | Use Super5 algorithm (faster, large datasets) | False |
| `-q/--quiet` | flag | Suppress progress | False |

**Returns:** ClustalW format alignment or aligned FASTA (.afa)

---

### gget diamond
Fast local protein alignment and translated nucleotide-to-protein alignment.

**Parameters:**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `query` | str/list | Query sequences or FASTA file | Required |
| `-ref/--reference` | str/list | Reference sequences or FASTA file | Required |
| `-s/--sensitivity` | str | fast, mid-sensitive, sensitive, more-sensitive, very-sensitive, ultra-sensitive | very-sensitive |
| `-t/--threads` | int | CPU threads | 1 |
| `--diamond_binary` | str | Path to DIAMOND installation | Auto-detect |
| `-db/--diamond_db` | str | Save database for reuse | None |
| `-x/--translated` | flag | Enable nucleotide query to amino acid reference alignment | False |
| `-o/--out` | str | Output file path | None |
| `-csv` | flag | CSV format (CLI) | False |
| `-q/--quiet` | flag | Suppress progress | False |

**Returns:** Identity %, sequence lengths, match positions, gap openings, E-values, bit scores

---

## Structural & Protein Analysis Modules

### gget pdb
Query RCSB Protein Data Bank.

**Parameters:**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `pdb_id` | str | PDB identifier (e.g., '7S7U') | Required |
| `-r/--resource` | str | pdb, entry, pubmed, assembly, entity types | 'pdb' |
| `-i/--identifier` | str | Assembly, entity, or chain ID | None |
| `-o/--out` | str | Output file path | stdout |

**Returns:** PDB format (structures) or JSON (metadata)

---

### gget alphafold
Predict 3D protein structures using AlphaFold2.

**Setup:** Requires OpenMM and `gget setup alphafold` (~4GB download)

**Parameters:**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `sequence` | str/list | Amino acid sequence(s) or FASTA file | Required |
| `-mr/--multimer_recycles` | int | Recycling iterations for multimers | 3 |
| `-o/--out` | str | Output folder path | timestamped |
| `-mfm/--multimer_for_monomer` | flag | Apply multimer model to monomers | False |
| `-r/--relax` | flag | AMBER relaxation for top model | False |
| `-q/--quiet` | flag | Suppress progress | False |

**Python-only:**
- `plot` (bool): Generate 3D visualization (default: True)
- `show_sidechains` (bool): Include side chains (default: True)

**Note:** Multiple sequences automatically trigger multimer modeling

**Returns:** PDB structure file, JSON alignment error data, optional 3D plot

---

### gget elm
Predict Eukaryotic Linear Motifs.

**Setup:** Requires `gget setup elm`

**Parameters:**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `sequence` | str | Amino acid sequence or UniProt Acc | Required |
| `-s/--sensitivity` | str | DIAMOND alignment sensitivity | very-sensitive |
| `-t/--threads` | int | Number of threads | 1 |
| `-bin/--diamond_binary` | str | Path to DIAMOND binary | Auto-detect |
| `-o/--out` | str | Output directory path | None |
| `-u/--uniprot` | flag | Input is UniProt Acc | False |
| `-e/--expand` | flag | Include protein names, organisms, references | False |
| `-csv` | flag | CSV format (CLI) | False |
| `-q/--quiet` | flag | Suppress progress | False |

**Returns:** Two outputs:
1. **ortholog_df**: Motifs from orthologous proteins
2. **regex_df**: Motifs matched in input sequence

---

## Expression & Disease Data Modules

### gget archs4
Query ARCHS4 for gene correlation or tissue expression.

**Parameters:**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `gene` | str | Gene symbol or Ensembl ID | Required |
| `-w/--which` | str | 'correlation' or 'tissue' | 'correlation' |
| `-s/--species` | str | 'human' or 'mouse' (tissue only) | 'human' |
| `-o/--out` | str | Output file path | None |
| `-e/--ensembl` | flag | Input is Ensembl ID | False |
| `-csv` | flag | CSV format (CLI) | False |
| `-q/--quiet` | flag | Suppress progress | False |

**Returns:**
- **correlation**: Gene symbols, Pearson correlation coefficients (top 100)
- **tissue**: Tissue IDs, min/Q1/median/Q3/max expression

---

### gget cellxgene
Query CZ CELLxGENE Discover Census for single-cell data.

**Setup:** Requires `gget setup cellxgene`

**Parameters:**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `--gene` (-g) | list | Gene names or Ensembl IDs (case-sensitive!) | Required |
| `--tissue` | list | Tissue type(s) | None |
| `--cell_type` | list | Cell type(s) | None |
| `--species` (-s) | str | 'homo_sapiens' or 'mus_musculus' | 'homo_sapiens' |
| `--census_version` (-cv) | str | "stable", "latest", or dated version | "stable" |
| `-o/--out` | str | Output file path (required for CLI) | Required |
| `--ensembl` (-e) | flag | Use Ensembl IDs | False |
| `--meta_only` (-mo) | flag | Return metadata only | False |
| `-q/--quiet` | flag | Suppress progress | False |

**Additional filters:** disease, development_stage, sex, assay, dataset_id, donor_id, ethnicity, suspension_type

**Important:** Gene symbols are case-sensitive ('PAX7' for human, 'Pax7' for mouse)

**Returns:** AnnData object with count matrices and metadata

---

### gget enrichr
Perform enrichment analysis using Enrichr/modEnrichr.

**Parameters:**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `genes` | list | Gene symbols or Ensembl IDs | Required |
| `-db/--database` | str | Reference database or shortcut | Required |
| `-s/--species` | str | human, mouse, fly, yeast, worm, fish | 'human' |
| `-bkg_l/--background_list` | list | Background genes | None |
| `-o/--out` | str | Output file path | None |
| `-ko/--kegg_out` | str | KEGG pathway images directory | None |

**Python-only:**
- `plot` (bool): Generate graphical results

**Database shortcuts:**
- 'pathway' → KEGG_2021_Human
- 'transcription' → ChEA_2016
- 'ontology' → GO_Biological_Process_2021
- 'diseases_drugs' → GWAS_Catalog_2019
- 'celltypes' → PanglaoDB_Augmented_2021

**Returns:** Pathway/function associations with adjusted p-values, overlapping gene counts

---

### gget bgee
Retrieve orthology and expression from Bgee.

**Parameters:**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `ens_id` | str/list | Ensembl or NCBI gene ID | Required |
| `-t/--type` | str | 'orthologs' or 'expression' | 'orthologs' |
| `-o/--out` | str | Output file path | None |
| `-csv` | flag | CSV format (CLI) | False |
| `-q/--quiet` | flag | Suppress progress | False |

**Note:** Multiple IDs supported when `type='expression'`

**Returns:**
- **orthologs**: Genes across species with IDs, names, taxonomic info
- **expression**: Anatomical entities, confidence scores, expression status

---

### gget opentargets
Retrieve disease/drug associations from OpenTargets.

**Parameters:**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `ens_id` | str | Ensembl gene ID | Required |
| `-r/--resource` | str | diseases, drugs, tractability, pharmacogenetics, expression, depmap, interactions | 'diseases' |
| `-l/--limit` | int | Maximum results | None |
| `-o/--out` | str | Output file path | None |
| `--filters` | repeated key=value / dict | Exact-match filters using returned column names | None |
| `-or/--or` | flag | Combine CLI filters with OR instead of AND | False |
| `-csv` | flag | CSV format (CLI) | False |
| `-q/--quiet` | flag | Suppress progress | False |

**Current notes:**
- gget 0.30.5 rewrote this module for the newer OpenTargets API; output column/key names may differ from older releases.
- The older `--filter_mode` argument was removed upstream. Use CLI `--or` or Python filter logic documented by the current API.
- Prefer inspecting returned column names before writing filters, then filter with exact column names such as `protein_a_id` or `gene_b_id`.

**Returns:** Disease/drug associations, tractability, pharmacogenetics, expression, DepMap, interactions

---

### gget cbio
Plot cancer genomics heatmaps from cBioPortal.

**Subcommands:** search, plot

**search parameters:**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `keywords` | list | Search terms | Required |

**plot parameters:**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `-s/--study_ids` | list | cBioPortal study IDs | Required |
| `-g/--genes` | list | Gene names or Ensembl IDs | Required |
| `-st/--stratification` | str | tissue, cancer_type, cancer_type_detailed, study_id, sample | None |
| `-vt/--variation_type` | str | mutation_occurrences, cna_nonbinary, sv_occurrences, cna_occurrences, Consequence | None |
| `-f/--filter` | str | Filter by column value (e.g., 'study_id:msk_impact_2017') | None |
| `-dd/--data_dir` | str | Cache directory | ./gget_cbio_cache |
| `-fd/--figure_dir` | str | Output directory | ./gget_cbio_figures |
| `-t/--title` | str | Custom figure title | None |
| `-dpi` | int | Resolution | 100 |
| `-q/--quiet` | flag | Suppress progress | False |
| `-nc/--no_confirm` | flag | Skip download confirmations | False |
| `-sh/--show` | flag | Display plot in window | False |

**Returns:** PNG heatmap figure

---

### gget cosmic
Search COSMIC database for cancer mutations.

**Important:** License fees for commercial use. Requires COSMIC account. Avoid passing credentials directly on the command line on shared systems; prefer the interactive prompt or Python code that reads named environment variables.

**Query parameters:**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `searchterm` | str | Gene name, Ensembl ID, mutation, sample ID | Required |
| `-ctp/--cosmic_tsv_path` | str | Path to COSMIC TSV file | Required |
| `-l/--limit` | int | Maximum results | 100 |
| `-csv` | flag | CSV format (CLI) | False |

**Download parameters:**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `-d/--download_cosmic` | flag | Activate download mode | False |
| `-gm/--gget_mutate` | flag | Create version for gget mutate | False |
| `-cp/--cosmic_project` | str | cancer, cancer_example, census, cell_line, resistance, genome_screen, targeted_screen | cancer |
| `-cv/--cosmic_version` | str | COSMIC version | Latest |
| `-gv/--grch_version` | int | Human reference genome (37 or 38) | None |
| `--email` | str | COSMIC account email for non-interactive download | Prompt/env preferred |
| `--password` | str | COSMIC account password for non-interactive download | Prompt/env preferred |

**Note:** First-time users must download database

**Returns:** Mutation data from COSMIC

---

### gget virus
Download viral nucleotide sequences and metadata from INSDC sources via NCBI Virus.

**Parameters:**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `virus` | str | Virus taxon name, taxon ID, accession(s), or accession text file | Required unless `--download_all_accessions` |
| `-a/--is_accession` | flag | Treat `virus` as accession input | False |
| `--is_sars_cov2` | flag | Use optimized SARS-CoV-2 cached data path | False |
| `--is_alphainfluenza` | flag | Use optimized Influenza A cached data path | False |
| `--host` | str | Host organism name or NCBI Taxonomy ID | None |
| `--nuc_completeness` | str | complete or partial | None |
| `--min_seq_length` / `--max_seq_length` | int | Sequence length filters | None |
| `--segment` | str | Segment filter for segmented viruses | None |
| `--source_database` | str | genbank or refseq | None |
| `--annotated` | bool | Include/exclude annotated sequences | None |
| `--vaccine_strain` | bool | Include/exclude vaccine strain sequences | None |
| `-g/--genbank_metadata` | flag | Fetch detailed GenBank metadata | False |
| `--download_all_accessions` | flag | Apply filters across all viral accessions | False |
| `--baseline` / `--merge-results` | path/flag | Resume or merge with previous metadata | None/False |
| `-q/--quiet` | flag | Suppress progress | False |

**Warning:** `--download_all_accessions` without restrictive filters can request the entire Viruses taxonomy and require many hours and substantial disk.

**Returns:** FASTA, CSV, JSONL, optional GenBank metadata, and `command_summary.txt` in an output folder.

---

### gget 8cube
Query 8cubeDB mouse snRNA-seq specificity and expression metrics.

**Subcommands:**
| Subcommand | Description | Required arguments |
|------------|-------------|--------------------|
| `specificity` | Gene-level psi/zeta specificity values | `genes` |
| `psi_block` | Block-level specificity values | `genes`, `--analysis_level`, `--analysis_type` |
| `expression` | Mean/variance normalized expression values | `genes`, `--analysis_level`, `--analysis_type` |

**Common parameters:**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `genes` | str/list | Gene symbols or Ensembl gene IDs | Required |
| `-al/--analysis_level` | str | Biological grouping such as Kidney or Across_tissues | Required for psi_block/expression |
| `-at/--analysis_type` | str | Partition type such as Sex:Celltype or Strain | Required for psi_block/expression |
| `-csv/--csv` | flag | Return CSV instead of JSON (CLI) | False |
| `-o/--out` | str | Output file path | None |
| `-q/--quiet` | flag | Suppress progress | False |

**Returns:** JSON/CSV on the CLI or DataFrame/JSON in Python.

---

## Additional Tools

### gget mutate
Generate mutated nucleotide sequences.

**Parameters:**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `sequences` | str/list | FASTA file or nucleotide sequence(s) | Required |
| `-m/--mutations` | str/list/df | Mutation string/list, CSV/TSV file, or DataFrame | Required |
| `-mc/--mut_column` | str | Mutation column name | 'mutation' |
| `-sic/--seq_id_column` | str | Sequence ID column | 'seq_ID' |
| `-mic/--mut_id_column` | str | Mutation ID column | Same as mut_column |
| `-k/--k` | int | Length of flanking sequences | 30 |
| `-o/--out` | str | Output FASTA file path | None (return list/stdout) |
| `-q/--quiet` | flag | Suppress progress | False |

**Returns:** Mutated sequences in FASTA format

**Note:** More complex variant-screening functionality moved upstream to the `kvar` project.

---

### gget gpt
Generate text using OpenAI's API.

**Setup:** Requires `gget setup gpt` and OpenAI API key

**Parameters:**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `prompt` | str | Text input for generation | Required |
| `api_key` | str | OpenAI API key; prefer reading from `OPENAI_API_KEY` | Required |
| `model` | str | OpenAI model name | gpt-3.5-turbo |
| `temperature` | float | Sampling temperature (0-2) | 1.0 |
| `top_p` | float | Nucleus sampling | 1.0 |
| `max_tokens` | int | Maximum tokens to generate | None |
| `frequency_penalty` | float | Frequency penalty (0-2) | 0 |
| `presence_penalty` | float | Presence penalty (0-2) | 0 |
| `stop` | str | Stop sequence | None |
| `logit_bias` | dict | Token bias map | None |

**Important:** Do not hard-code API keys or pass real keys in examples. The upstream CLI accepts a key argument; Python code that reads `OPENAI_API_KEY` is safer for notebooks and scripts.

**Returns:** Generated text string

---

### gget setup
Install/download dependencies for modules.

**Parameters:**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `module` | str | Module name | Required |
| `-o/--out` | str | Output folder (elm only) | Package install folder |
| `-q/--quiet` | flag | Suppress progress | False |

**Modules requiring setup:**
- `alphafold` - Downloads ~4GB model parameters
- `cellxgene` - Installs cellxgene-census
- `elm` - Downloads local ELM database
- `gpt` - Configures OpenAI integration

**Returns:** None (installs dependencies)
