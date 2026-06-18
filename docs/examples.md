# Real-World Scientific Examples

This document provides comprehensive, practical examples demonstrating how to combine Scientific Agent Skills to solve real scientific problems across multiple domains.

---

## 📋 Table of Contents

1. [Drug Discovery & Medicinal Chemistry](#drug-discovery--medicinal-chemistry)
2. [Cancer Genomics & Precision Medicine](#cancer-genomics--precision-medicine)
3. [Single-Cell Transcriptomics](#single-cell-transcriptomics)
4. [Protein Structure & Function](#protein-structure--function)
5. [Chemical Safety & Toxicology](#chemical-safety--toxicology)
6. [Clinical Trial Analysis](#clinical-trial-analysis)
7. [Metabolomics & Systems Biology](#metabolomics--systems-biology)
8. [Materials Science & Chemistry](#materials-science--chemistry)
9. [Digital Pathology](#digital-pathology)
10. [Lab Automation & Protocol Design](#lab-automation--protocol-design)
11. [Agricultural Genomics](#agricultural-genomics)
12. [Neuroscience & Brain Imaging](#neuroscience--brain-imaging)
13. [Environmental Microbiology](#environmental-microbiology)
14. [Infectious Disease Research](#infectious-disease-research)
15. [Multi-Omics Integration](#multi-omics-integration)
16. [Computational Chemistry & Synthesis](#computational-chemistry--synthesis)
17. [Clinical Research & Real-World Evidence](#clinical-research--real-world-evidence)
18. [Experimental Physics & Data Analysis](#experimental-physics--data-analysis)
19. [Chemical Engineering & Process Optimization](#chemical-engineering--process-optimization)
20. [Scientific Illustration & Visual Communication](#scientific-illustration--visual-communication)
21. [Quantum Computing for Chemistry](#quantum-computing-for-chemistry)
22. [Research Grant Writing](#research-grant-writing)
23. [Flow Cytometry & Immunophenotyping](#flow-cytometry--immunophenotyping)
24. [Geospatial & Earth Observation](#geospatial--earth-observation)
25. [Time-Series Forecasting & Sensor Analytics](#time-series-forecasting--sensor-analytics)
26. [Cloud-Scale Bioinformatics](#cloud-scale-bioinformatics)
27. [Functional Genomics & Knowledge Graphs](#functional-genomics--knowledge-graphs)
28. [Molecular Modeling & Simulation](#molecular-modeling--simulation)
29. [Protein Engineering & Cloud Wet-Lab](#protein-engineering--cloud-wet-lab)
30. [Medical Imaging & Clinical AI](#medical-imaging--clinical-ai)
31. [Research Ideation & Study Planning](#research-ideation--study-planning)
32. [Literature & Knowledge Management](#literature--knowledge-management)
33. [Regulatory & Quality Management](#regulatory--quality-management)
34. [Scientific Communication & Tooling](#scientific-communication--tooling)

---

## Drug Discovery & Medicinal Chemistry

### Example 1: Discovery of Novel EGFR Inhibitors for Lung Cancer

**Objective**: Identify novel small molecule inhibitors of EGFR with improved properties compared to existing drugs.

**Skills Used**:
- `database-lookup` - Query ChEMBL, PubChem, COSMIC, AlphaFold DB
- `paper-lookup` - Search PubMed for literature
- `rdkit` - Analyze molecular properties
- `datamol` - Generate analogs
- `medchem` - Medicinal chemistry filters
- `molfeat` - Molecular featurization
- `diffdock` - Molecular docking
- `deepchem` - Property prediction
- `torchdrug` - Graph neural networks for molecules
- `scientific-visualization` - Create figures
- `clinical-reports` - Generate PDF reports

**Workflow**:

```bash
# Always use available 'skills' when possible. Keep the output organized.

Step 1: Query ChEMBL for known EGFR inhibitors with high potency
- Search for compounds targeting EGFR (CHEMBL203)
- Filter: IC50 < 50 nM, pChEMBL value > 7
- Extract SMILES strings and activity data
- Export to DataFrame for analysis

Step 2: Analyze structure-activity relationships
- Load compounds into RDKit
- Calculate molecular descriptors (MW, LogP, TPSA, HBD, HBA)
- Generate Morgan fingerprints (radius=2, 2048 bits)
- Perform hierarchical clustering to identify scaffolds
- Visualize top scaffolds with activity annotations

Step 3: Identify resistance mutations from COSMIC
- Query COSMIC for EGFR mutations in lung cancer
- Focus on gatekeeper mutations (T790M, C797S)
- Extract mutation frequencies and clinical significance
- Cross-reference with literature in PubMed

Step 4: Retrieve EGFR structure from AlphaFold
- Download AlphaFold prediction for EGFR kinase domain
- Alternatively, use experimental structure from PDB (if available)
- Prepare structure for docking (add hydrogens, optimize)

Step 5: Generate novel analogs using datamol
- Select top 5 scaffolds from ChEMBL analysis
- Use scaffold decoration to generate 100 analogs per scaffold
- Apply Lipinski's Rule of Five filtering
- Ensure synthetic accessibility (SA score < 4)
- Check for PAINS and unwanted substructures

Step 6: Predict properties with DeepChem
- Train graph convolutional model on ChEMBL EGFR data
- Predict pIC50 for generated analogs
- Predict ADMET properties (solubility, permeability, hERG)
- Rank candidates by predicted potency and drug-likeness

Step 7: Virtual screening with DiffDock
- Perform molecular docking on top 50 candidates
- Dock into wild-type EGFR and T790M mutant
- Rank generated poses by DiffDock confidence, then rescore with GNINA/MM-GBSA for affinity-oriented prioritization
- Identify compounds with favorable binding to both forms

Step 8: Search PubChem for commercial availability
- Query PubChem for top 10 candidates by InChI key
- Check supplier information and purchasing options
- Identify close analogs if exact matches unavailable

Step 9: Literature validation with PubMed
- Search for any prior art on top scaffolds
- Query: "[scaffold_name] AND EGFR AND inhibitor"
- Summarize relevant findings and potential liabilities

Step 10: Create comprehensive report
- Generate 2D structure visualizations of top hits
- Create scatter plots: MW vs LogP, TPSA vs potency
- Produce binding pose figures for top 3 compounds
- Generate table comparing properties to approved drugs (gefitinib, erlotinib)
- Write scientific summary with methodology, results, and recommendations
- Export to PDF with proper citations

Expected Output: 
- Ranked list of 10-20 novel EGFR inhibitor candidates
- Predicted activity and ADMET properties
- Docking poses and binding analysis
- Comprehensive scientific report with publication-quality figures
```

---

### Example 2: Drug Repurposing for Rare Diseases

**Objective**: Identify FDA-approved drugs that could be repurposed for treating a rare metabolic disorder.

**Skills Used**:
- `database-lookup` - Query DrugBank, Open Targets, STRING, KEGG, Reactome, ClinicalTrials.gov, FDA
- `paper-lookup` - Search OpenAlex, bioRxiv, PubMed
- `networkx` - Network analysis
- `bioservices` - Biological database queries
- `literature-review` - Systematic review

**Workflow**:

```bash
Step 1: Define disease pathway
- Query KEGG and Reactome for disease-associated pathways
- Identify key proteins and enzymes involved
- Map upstream and downstream pathway components

Step 2: Find protein-protein interactions
- Query STRING database for interaction partners
- Build protein interaction network around key disease proteins
- Identify hub proteins and bottlenecks using NetworkX
- Calculate centrality metrics (betweenness, closeness)

Step 3: Query Open Targets for druggable targets
- Search for targets associated with disease phenotype
- Filter by clinical precedence and tractability
- Prioritize targets with existing approved drugs

Step 4: Search DrugBank for drugs targeting identified proteins
- Query for approved drugs and their targets
- Filter by mechanism of action relevant to disease
- Retrieve drug properties and safety information

Step 5: Query FDA databases for safety profiles
- Check FDA adverse event database (FAERS)
- Review drug labels and black box warnings
- Assess risk-benefit for rare disease population

Step 6: Search ClinicalTrials.gov for prior repurposing attempts
- Query for disease name + drug names
- Check for failed trials (and reasons for failure)
- Identify ongoing trials that may compete

Step 7: Perform pathway enrichment analysis
- Map drug targets to disease pathways
- Calculate enrichment scores with Reactome
- Identify drugs affecting multiple pathway nodes

Step 8: Conduct systematic literature review
- Search PubMed for drug name + disease associations
- Include bioRxiv for recent unpublished findings
- Document any case reports or off-label use
- Use literature-review skill to generate comprehensive review

Step 9: Prioritize candidates
- Rank by: pathway relevance, safety profile, existing evidence
- Consider factors: oral availability, blood-brain barrier penetration
- Assess commercial viability and patent status

Step 10: Generate repurposing report
- Create network visualization of drug-target-pathway relationships
- Generate comparison table of top 5 candidates
- Write detailed rationale for each candidate
- Include mechanism of action diagrams
- Provide recommendations for preclinical validation
- Format as professional PDF with citations

Expected Output:
- Ranked list of 5-10 repurposing candidates
- Network analysis of drug-target-disease relationships
- Safety and efficacy evidence summary
- Repurposing strategy report with next steps
```

---

## Cancer Genomics & Precision Medicine

### Example 3: Clinical Variant Interpretation Pipeline

**Objective**: Analyze a patient's tumor sequencing data to identify actionable mutations and therapeutic recommendations.

**Skills Used**:
- `database-lookup` - Query Ensembl, ClinVar, COSMIC, NCBI Gene, UniProt, ClinPGx, DrugBank, ClinicalTrials.gov, Open Targets
- `paper-lookup` - Search PubMed for literature evidence
- `pysam` - Parse VCF files
- `gget` - Unified gene/protein data retrieval
- `clinical-reports` - Generate clinical report PDF

**Workflow**:

```bash
Step 1: Parse and filter VCF file
- Use pysam to read tumor VCF
- Filter for high-quality variants (QUAL > 30, DP > 20)
- Extract variant positions, alleles, and VAF (variant allele frequency)
- Separate SNVs, indels, and structural variants

Step 2: Annotate variants with Ensembl
- Query Ensembl VEP API for functional consequences
- Classify variants: missense, nonsense, frameshift, splice site
- Extract transcript information and protein changes
- Identify canonical transcripts for each gene

Step 3: Query ClinVar for known pathogenic variants
- Search ClinVar by genomic coordinates
- Extract clinical significance classifications
- Note conflicting interpretations and review status
- Prioritize variants with "Pathogenic" or "Likely Pathogenic" labels

Step 4: Query COSMIC for somatic cancer mutations
- Search COSMIC for each variant
- Extract mutation frequency across cancer types
- Identify hotspot mutations (high recurrence)
- Note drug resistance mutations

Step 5: Retrieve gene information from NCBI Gene
- Get detailed gene descriptions
- Extract associated phenotypes and diseases
- Identify oncogene vs tumor suppressor classification
- Note gene function and biological pathways

Step 6: Assess protein-level impact with UniProt
- Query UniProt for protein domain information
- Map variants to functional domains (kinase domain, binding site)
- Check if variant affects active sites or protein stability
- Retrieve post-translational modification sites

Step 7: Search DrugBank for targetable alterations
- Query for drugs targeting mutated genes
- Filter for FDA-approved and investigational drugs
- Extract mechanism of action and indications
- Prioritize variants with approved targeted therapies

Step 8: Query Open Targets for target-disease associations
- Validate therapeutic hypotheses
- Assess target tractability scores
- Review clinical precedence for each gene-disease pair

Step 9: Search ClinicalTrials.gov for matching trials
- Build query with: cancer type + gene names + variants
- Filter for: recruiting status, phase II/III trials
- Extract trial eligibility criteria
- Note geographic locations and contact information

Step 10: Literature search for clinical evidence
- PubMed query: "[gene] AND [variant] AND [cancer type]"
- Focus on: case reports, clinical outcomes, resistance mechanisms
- Extract relevant prognostic or predictive information

Step 11: Classify variants by actionability
Tier 1: FDA-approved therapy for this variant
Tier 2: Clinical trial available for this variant
Tier 3: Therapy approved for variant in different cancer
Tier 4: Biological evidence but no approved therapy

Step 12: Generate clinical genomics report
- Executive summary of key findings
- Table of actionable variants with evidence levels
- Therapeutic recommendations with supporting evidence
- Clinical trial options with eligibility information
- Prognostic implications based on mutation profile
- References to guidelines (NCCN, ESMO, AMP/ASCO/CAP)
- Generate professional PDF using clinical-reports skill

Expected Output:
- Annotated variant list with clinical significance
- Tiered list of actionable mutations
- Therapeutic recommendations with evidence levels
- Matching clinical trials
- Comprehensive clinical genomics report (PDF)
```

---

### Example 4: Cancer Subtype Classification from Gene Expression

**Objective**: Classify breast cancer subtypes using RNA-seq data and identify subtype-specific therapeutic vulnerabilities.

**Skills Used**:
- `database-lookup` - Query NCBI Gene, Reactome, Open Targets
- `paper-lookup` - Search PubMed for literature validation
- `pydeseq2` - Differential expression
- `scanpy` - Clustering and visualization
- `scikit-learn` - Machine learning classification
- `gget` - Gene data retrieval
- `matplotlib` - Visualization
- `seaborn` - Heatmaps
- `scientific-visualization` - Publication-quality & interactive visualization
- `scikit-survival` - Survival analysis
- `pathway-enrichment` - Gene-set and pathway enrichment analysis

**Workflow**:

```bash
Step 1: Load and preprocess RNA-seq data
- Load count matrix (genes × samples)
- Filter low-expression genes (mean counts < 10)
- Normalize with DESeq2 size factors
- Apply variance-stabilizing transformation (VST)

Step 2: Classify samples using PAM50 genes
- Query NCBI Gene for PAM50 classifier gene list
- Extract expression values for PAM50 genes
- Train Random Forest classifier on labeled training data
- Predict subtypes: Luminal A, Luminal B, HER2+, Basal, Normal-like
- Validate with published markers (ESR1, PGR, ERBB2, MKI67)

Step 3: Perform differential expression for each subtype
- Use PyDESeq2 to compare each subtype vs all others
- Apply multiple testing correction (FDR < 0.05)
- Filter by log2 fold change (|LFC| > 1.5)
- Identify subtype-specific signature genes

Step 4: Annotate differentially expressed genes
- Query NCBI Gene for detailed annotations
- Classify as oncogene, tumor suppressor, or other
- Extract biological process and molecular function terms

Step 5: Pathway enrichment analysis
- Submit gene lists to Reactome API
- Identify enriched pathways for each subtype (p < 0.01)
- Focus on druggable pathways (kinase signaling, metabolism)
- Compare pathway profiles across subtypes

Step 6: Identify therapeutic targets with Open Targets
- Query Open Targets for each upregulated gene
- Filter by tractability score > 5
- Prioritize targets with clinical precedence
- Extract associated drugs and development phase

Step 7: Create comprehensive visualization
- Generate UMAP projection of all samples colored by subtype
- Create heatmap of PAM50 genes across subtypes
- Produce volcano plots for each subtype comparison
- Generate pathway enrichment dot plots
- Create drug target-pathway network diagrams

Step 8: Literature validation
- Search PubMed for each predicted therapeutic target
- Query: "[gene] AND [subtype] AND breast cancer AND therapy"
- Summarize clinical evidence and ongoing trials
- Note any resistance mechanisms reported

Step 9: Generate subtype-specific recommendations
For each subtype:
- List top 5 differentially expressed genes
- Identify enriched biological pathways
- Recommend therapeutic strategies based on vulnerabilities
- Cite supporting evidence from literature

Step 10: Create comprehensive report
- Classification results with confidence scores
- Differential expression tables for each subtype
- Pathway enrichment summaries
- Therapeutic target recommendations
- Publication-quality figures
- Export to PDF with citations

Expected Output:
- Sample classification into molecular subtypes
- Subtype-specific gene signatures
- Pathway enrichment profiles
- Prioritized therapeutic targets for each subtype
- Scientific report with visualizations and recommendations
```

---

## Single-Cell Transcriptomics

### Example 5: Single-Cell Atlas of Tumor Microenvironment

**Objective**: Characterize immune cell populations in tumor microenvironment and identify immunotherapy biomarkers.

**Skills Used**:
- `database-lookup` - Query NCBI Gene for cell type markers
- `scanpy` - Single-cell analysis
- `scvi-tools` - Batch correction and integration
- `scvelo` - RNA velocity and cell-state transitions
- `cellxgene-census` - Reference data
- `lamindb` - Dataset registration and lineage tracking
- `gget` - Gene data retrieval
- `anndata` - Data structure
- `arboreto` - Gene regulatory networks
- `pytorch-lightning` - Deep learning
- `matplotlib` - Visualization
- `scientific-visualization` - Publication-quality & interactive visualization
- `statistical-analysis` - Hypothesis testing
- `geniml` - Genomic ML embeddings

**Workflow**:

```bash
Step 1: Load and QC 10X Genomics data
- Use Scanpy to read 10X h5 files
- Calculate QC metrics: n_genes, n_counts, pct_mitochondrial
- Identify mitochondrial genes (MT- prefix)
- Filter cells: 200 < n_genes < 5000, pct_mt < 20%
- Filter genes: expressed in at least 10 cells
- Document filtering criteria and cell retention rate

Step 2: Normalize and identify highly variable genes
- Normalize to 10,000 counts per cell
- Log-transform data (log1p)
- Store raw counts in adata.raw
- Identify 3,000 highly variable genes
- Regress out technical variation (n_counts, pct_mt)
- Scale to unit variance, clip at 10 standard deviations

Step 3: Integrate with reference atlas using scVI
- Download reference tumor microenvironment data from Cellxgene Census
- Train scVI model on combined dataset for batch correction
- Use scVI latent representation for downstream analysis
- Generate batch-corrected expression matrix

Step 4: Dimensionality reduction and clustering
- Compute neighborhood graph (n_neighbors=15, n_pcs=50)
- Calculate UMAP embedding for visualization
- Perform Leiden clustering at multiple resolutions (0.3, 0.5, 0.8)
- Select optimal resolution based on silhouette score

Step 5: Identify cell type markers
- Run differential expression for each cluster (Wilcoxon test)
- Calculate marker scores (log fold change, p-value, pct expressed)
- Query NCBI Gene for canonical immune cell markers:
  * T cells: CD3D, CD3E, CD4, CD8A
  * B cells: CD19, MS4A1 (CD20), CD79A
  * Myeloid: CD14, CD68, CD163
  * NK cells: NKG7, GNLY, NCAM1
  * Dendritic: CD1C, CLEC9A, LILRA4

Step 6: Annotate cell types
- Assign cell type labels based on marker expression
- Refine annotations with CellTypist or manual curation
- Identify T cell subtypes: CD4+, CD8+, Tregs, exhausted T cells
- Characterize myeloid cells: M1/M2 macrophages, dendritic cells
- Create cell type proportion tables by sample/condition

Step 7: Identify tumor-specific features
- Compare tumor samples vs normal tissue (if available)
- Identify expanded T cell clones (high proliferation markers)
- Detect exhausted T cells (PDCD1, CTLA4, LAG3, HAVCR2)
- Characterize immunosuppressive populations (Tregs, M2 macrophages)

Step 8: Gene regulatory network inference
- Use Arboreto/GRNBoost2 on each major cell type
- Identify transcription factors driving cell states
- Focus on exhaustion TFs: TOX, TCF7, EOMES
- Build regulatory networks for visualization

Step 9: Statistical analysis of cell proportions
- Calculate cell type frequencies per sample
- Test for significant differences between groups (responders vs non-responders)
- Use statistical-analysis skill for appropriate tests (t-test, Mann-Whitney)
- Calculate effect sizes and confidence intervals

Step 10: Biomarker discovery for immunotherapy response
- Correlate cell type abundances with clinical response
- Identify gene signatures associated with response
- Test signatures: T cell exhaustion, antigen presentation, inflammation
- Validate with published immunotherapy response signatures

Step 11: Create comprehensive visualizations
- UMAP plots colored by: cell type, sample, treatment, key genes
- Dot plots of canonical markers across cell types
- Cell type proportion bar plots by condition
- Heatmap of top differentially expressed genes per cell type
- Gene regulatory network diagrams
- Volcano plots for differentially abundant cell types

Step 12: Generate scientific report
- Methods: QC, normalization, batch correction, clustering
- Results: Cell type composition, differential abundance, markers
- Biomarker analysis: Predictive signatures and validation
- High-quality figures suitable for publication
- Export processed h5ad file and PDF report

Expected Output:
- Annotated single-cell atlas with cell type labels
- Cell type composition analysis
- Biomarker signatures for immunotherapy response
- Gene regulatory networks for key cell states
- Comprehensive report with publication-quality figures
```

---

## Protein Structure & Function

### Example 6: Structure-Based Design of Protein-Protein Interaction Inhibitors

**Objective**: Design small molecules to disrupt a therapeutically relevant protein-protein interaction.

**Skills Used**:
- `database-lookup` - Query AlphaFold DB, PDB, UniProt, ZINC
- `biopython` - Structure analysis
- `esm` - Protein language models and embeddings
- `rdkit` - Chemical library generation
- `datamol` - Molecule manipulation
- `diffdock` - Molecular docking
- `deepchem` - Property prediction
- `scientific-visualization` - Structure visualization
- `medchem` - Medicinal chemistry filters

**Workflow**:

```bash
Step 1: Retrieve protein structures
- Query AlphaFold Database for both proteins in the interaction
- Download PDB files and confidence scores
- If available, get experimental structures from PDB database
- Compare AlphaFold predictions with experimental structures (if any)

Step 2: Analyze protein interaction interface
- Load structures with BioPython
- Identify interface residues (distance < 5Å between proteins)
- Calculate interface area and binding energy contribution
- Identify hot spot residues (key for binding)
- Map to UniProt to get functional annotations

Step 3: Characterize binding pocket
- Identify cavities at the protein-protein interface
- Calculate pocket volume and surface area
- Assess druggability: depth, hydrophobicity, shape
- Identify hydrogen bond donors/acceptors
- Note any known allosteric sites

Step 4: Query UniProt for known modulators
- Search UniProt for both proteins
- Extract information on known inhibitors or modulators
- Review PTMs that affect interaction
- Check disease-associated mutations in interface

Step 5: Search ZINC15 for fragment library
- Query ZINC for fragments matching pocket criteria:
  * Molecular weight: 150-300 Da
  * LogP: 0-3 (appropriate for PPI inhibitors)
  * Exclude PAINS and aggregators
- Download 1,000-5,000 fragment SMILES

Step 6: Virtual screening with fragment library
- Use DiffDock to dock fragments into interface pocket
- Rank by pose confidence, then rescore promising poses with an affinity-oriented method
- Identify fragments binding to hot spot residues
- Select top 50 fragments for elaboration

Step 7: Fragment elaboration with RDKit
- For each fragment hit, generate elaborated molecules:
  * Add substituents to core scaffold
  * Merge fragments binding to adjacent pockets
  * Apply medicinal chemistry filters
- Generate 20-50 analogs per fragment
- Filter by Lipinski's Ro5 and PPI-specific rules (MW 400-700)

Step 8: Second round of virtual screening
- Dock elaborated molecules with DiffDock
- Analyze interaction patterns and rescore poses with GNINA/MM-GBSA or another affinity-oriented method
- Prioritize molecules with:
  * Strong binding to hot spot residues
  * Multiple H-bonds and hydrophobic contacts
  * Favorable predicted ΔG

Step 9: Predict ADMET properties with DeepChem
- Train models on ChEMBL data
- Predict: solubility, permeability, hERG liability
- Filter for drug-like properties
- Rank by overall score (affinity + ADMET)

Step 10: Literature and patent search
- PubMed: "[protein A] AND [protein B] AND inhibitor"
- USPTO: Check for prior art on top scaffolds
- Assess freedom to operate
- Identify any reported PPI inhibitors for this target

Step 11: Prepare molecules for synthesis
- Assess synthetic accessibility (SA score < 4)
- Identify commercial building blocks
- Propose synthetic routes for top 10 candidates
- Calculate estimated synthesis cost

Step 12: Generate comprehensive design report
- Interface analysis with hot spot identification
- Fragment screening results
- Top 10 designed molecules with predicted properties
- Docking poses and interaction diagrams
- Synthetic accessibility assessment
- Comparison to known PPI inhibitors
- Recommendations for experimental validation
- Publication-quality figures and PDF report

Expected Output:
- Interface characterization and hot spot analysis
- Ranked library of designed PPI inhibitors
- Predicted binding modes and affinities
- ADMET property predictions
- Synthetic accessibility assessment
- Comprehensive drug design report
```

---

## Chemical Safety & Toxicology

### Example 7: Predictive Toxicology Assessment

**Objective**: Assess potential toxicity and safety liabilities of drug candidates before synthesis.

**Skills Used**:
- `database-lookup` - Query ChEMBL, PubChem, DrugBank, FDA, HMDB
- `rdkit` - Molecular descriptors
- `medchem` - Toxicophore detection
- `deepchem` - Toxicity prediction
- `pytdc` - Therapeutics data commons
- `scikit-learn` - Classification models
- `shap` - Model interpretability
- `clinical-reports` - Safety assessment reports

**Workflow**:

```bash
Step 1: Calculate molecular descriptors
- Load candidate molecules with RDKit
- Calculate physicochemical properties:
  * MW, LogP, TPSA, rotatable bonds, H-bond donors/acceptors
  * Aromatic rings, sp3 fraction, formal charge
- Calculate structural alerts:
  * PAINS patterns
  * Toxic functional groups (nitroaromatics, epoxides, etc.)
  * Genotoxic alerts (Ames mutagenicity)

Step 2: Screen for known toxicophores
- Search for structural alerts using SMARTS patterns:
  * Michael acceptors
  * Aldehyde/ketone reactivity
  * Quinones and quinone-like structures
  * Thioureas and isocyanates
- Flag molecules with high-risk substructures

Step 3: Query ChEMBL for similar compounds with toxicity data
- Perform similarity search (Tanimoto > 0.7)
- Extract toxicity assay results:
  * Cytotoxicity (IC50 values)
  * Hepatotoxicity markers
  * Cardiotoxicity (hERG inhibition)
  * Genotoxicity (Ames test results)
- Analyze structure-toxicity relationships

Step 4: Search PubChem BioAssays for toxicity screening
- Query relevant assays:
  * Tox21 panel (cell viability, stress response, genotoxicity)
  * Liver toxicity assays
  * hERG channel inhibition
- Extract activity data for similar compounds
- Calculate hit rates for concerning assays

Step 5: Train toxicity prediction models with DeepChem
- Load Tox21 dataset from DeepChem
- Train graph convolutional models for:
  * Nuclear receptor signaling
  * Stress response pathways
  * Genotoxicity endpoints
- Validate models with cross-validation
- Predict toxicity for candidate molecules

Step 6: Predict hERG cardiotoxicity liability
- Train DeepChem model on hERG inhibition data from ChEMBL
- Predict IC50 for hERG channel
- Flag compounds with predicted IC50 < 10 μM
- Identify structural features associated with hERG liability

Step 7: Predict hepatotoxicity risk
- Train models on DILI (drug-induced liver injury) datasets
- Extract features: reactive metabolites, mitochondrial toxicity
- Predict hepatotoxicity risk class (low/medium/high)
- Use SHAP values to explain predictions

Step 8: Predict metabolic stability and metabolites
- Identify sites of metabolism using RDKit SMARTS patterns
- Predict CYP450 interactions
- Query HMDB for potential metabolite structures
- Assess if metabolites contain toxic substructures
- Predict metabolic stability (half-life)

Step 9: Check FDA adverse event database
- Query FAERS for approved drugs similar to candidates
- Extract common adverse events
- Identify target organ toxicities
- Calculate reporting odds ratios for serious events

Step 10: Literature review of toxicity mechanisms
- PubMed search: "[scaffold] AND (toxicity OR hepatotoxicity OR cardiotoxicity)"
- Identify mechanistic studies on similar compounds
- Note any case reports of adverse events
- Review preclinical and clinical safety data

Step 11: Assess ADME liabilities
- Predict solubility, permeability, plasma protein binding
- Identify potential drug-drug interaction risks
- Assess blood-brain barrier penetration (for CNS or non-CNS drugs)
- Evaluate metabolic stability

Step 12: Generate safety assessment report
- Executive summary of safety profile for each candidate
- Red flags: structural alerts, predicted toxicities
- Yellow flags: moderate concerns requiring testing
- Green light: acceptable predicted safety profile
- Comparison table of all candidates
- Recommendations for risk mitigation:
  * Structural modifications to reduce toxicity
  * Priority in vitro assays to run
  * Preclinical study design recommendations
- Comprehensive PDF report with:
  * Toxicophore analysis
  * Prediction model results with confidence
  * SHAP interpretation plots
  * Literature evidence
  * Risk assessment matrix

Expected Output:
- Toxicity predictions for all candidates
- Structural alert analysis
- hERG, hepatotoxicity, and genotoxicity risk scores
- Metabolite predictions
- Prioritized list with safety rankings
- Comprehensive toxicology assessment report
```

---

## Clinical Trial Analysis

### Example 8: Competitive Landscape Analysis for New Indication

**Objective**: Analyze the clinical trial landscape for a specific indication to inform development strategy.

**Skills Used**:
- `database-lookup` - Query ClinicalTrials.gov, FDA, DrugBank, Open Targets
- `paper-lookup` - Search PubMed, OpenAlex for published results
- `polars` - Data manipulation
- `matplotlib` - Visualization
- `seaborn` - Statistical plots
- `scientific-visualization` - Publication-quality & interactive visualization
- `clinical-reports` - Report generation
- `market-research-reports` - Competitive intelligence
- `usfiscaldata` - U.S. federal R&D and economic context data

**Workflow**:

```bash
Step 1: Search ClinicalTrials.gov for all trials in indication
- Query: "[disease/indication]"
- Filter: All phases, all statuses
- Extract fields:
  * NCT ID, title, phase, status
  * Start date, completion date, enrollment
  * Intervention/drug names
  * Primary/secondary outcomes
  * Sponsor and collaborators
- Export to structured JSON/CSV

Step 2: Categorize trials by mechanism of action
- Extract drug names and intervention types
- Query DrugBank for mechanism of action
- Query Open Targets for target information
- Classify into categories:
  * Small molecules vs biologics
  * Target class (kinase inhibitor, antibody, etc.)
  * Novel vs repurposing

Step 3: Analyze trial phase progression
- Calculate success rates by phase (I → II, II → III)
- Identify terminated trials and reasons for termination
- Track time from phase I start to NDA submission
- Calculate median development timelines

Step 4: Search FDA database for recent approvals
- Query FDA drug approvals in the indication (last 10 years)
- Extract approval dates, indications, priority review status
- Note any accelerated approvals or breakthroughs
- Review FDA drug labels for safety information

Step 5: Extract outcome measures
- Compile all primary endpoints used
- Identify most common endpoints:
  * Survival (OS, PFS, DFS)
  * Response rates (ORR, CR, PR)
  * Biomarker endpoints
  * Patient-reported outcomes
- Note emerging or novel endpoints

Step 6: Analyze competitive dynamics
- Identify leading companies and their pipelines
- Map trials by phase for each major competitor
- Note partnership and licensing deals
- Assess crowded vs underserved patient segments

Step 7: Search PubMed for published trial results
- Query: "[NCT ID]" for each completed trial
- Extract published outcomes and conclusions
- Identify trends in efficacy and safety
- Note any unmet needs highlighted in discussions

Step 8: Analyze target validation evidence
- Query Open Targets for target-disease associations
- Extract genetic evidence scores
- Review tractability assessments
- Compare targets being pursued across trials

Step 9: Identify unmet needs and opportunities
- Analyze trial failures for common patterns
- Identify patient populations excluded from trials
- Note resistance mechanisms or limitations mentioned
- Assess gaps in current therapeutic approaches

Step 10: Perform temporal trend analysis
- Plot trial starts over time (by phase, mechanism)
- Identify increasing or decreasing interest in targets
- Correlate with publication trends and scientific advances
- Predict future trends in the space

Step 11: Create comprehensive visualizations
- Timeline of all trials (Gantt chart style)
- Phase distribution pie chart
- Mechanism of action breakdown
- Geographic distribution of trials
- Enrollment trends over time
- Success rate funnels (Phase I → II → III → Approval)
- Sponsor/company market share

Step 12: Generate competitive intelligence report
- Executive summary of competitive landscape
- Total number of active programs by phase
- Key players and their development stage
- Standard of care and approved therapies
- Emerging approaches and novel targets
- Identified opportunities and white space
- Risk analysis (crowded targets, high failure rates)
- Strategic recommendations:
  * Patient population to target
  * Differentiation strategies
  * Partnership opportunities
  * Regulatory pathway considerations
- Export as professional PDF with citations and data tables using clinical-reports skill

Expected Output:
- Comprehensive trial database for indication
- Success rate and timeline statistics
- Competitive landscape mapping
- Unmet need analysis
- Strategic recommendations
- Publication-ready report with visualizations
```

---

## Metabolomics & Systems Biology

### Example 9: Multi-Omics Integration for Metabolic Disease

**Objective**: Integrate transcriptomics, proteomics, and metabolomics to identify dysregulated pathways in metabolic disease.

**Skills Used**:
- `database-lookup` - Query HMDB, Metabolomics Workbench, KEGG, Reactome, STRING
- `pydeseq2` - RNA-seq analysis
- `pyopenms` - Mass spectrometry
- `matchms` - Mass spectra matching
- `cobrapy` - Constraint-based metabolic modeling
- `pathway-enrichment` - Multi-omics pathway/gene-set enrichment
- `statsmodels` - Multi-omics correlation
- `networkx` - Network analysis
- `pymc` - Bayesian modeling
- `scientific-visualization` - Publication-quality & interactive visualization

**Workflow**:

```bash
Step 1: Process RNA-seq data
- Load gene count matrix
- Run differential expression with PyDESeq2
- Compare disease vs control (adjusted p < 0.05, |LFC| > 1)
- Extract gene symbols and fold changes
- Map to KEGG gene IDs

Step 2: Process proteomics data
- Load LC-MS/MS results with PyOpenMS
- Perform peptide identification and quantification
- Normalize protein abundances
- Run statistical testing (t-test or limma)
- Extract significant proteins (p < 0.05, |FC| > 1.5)

Step 3: Process metabolomics data
- Load untargeted metabolomics data (mzML format) with PyOpenMS
- Perform peak detection and alignment
- Match features to HMDB database by accurate mass
- Annotate metabolites with MS/MS fragmentation
- Extract putative identifications (Level 2/3)
- Perform statistical analysis (FDR < 0.05, |FC| > 2)

Step 4: Search Metabolomics Workbench for public data
- Query for same disease or tissue type
- Download relevant studies
- Reprocess for consistency with own data
- Use as validation cohort

Step 5: Map all features to KEGG pathways
- Map genes to KEGG orthology (KO) terms
- Map proteins to KEGG identifiers
- Map metabolites to KEGG compound IDs
- Identify pathways with multi-omics coverage

Step 6: Perform pathway enrichment analysis
- Test for enrichment in KEGG pathways
- Test for enrichment in Reactome pathways
- Apply Fisher's exact test with multiple testing correction
- Focus on pathways with hits in ≥2 omics layers

Step 7: Build protein-metabolite networks
- Query STRING for protein-protein interactions
- Map proteins to KEGG reactions
- Connect enzymes to their substrates/products
- Build integrated network with genes → proteins → metabolites

Step 8: Network topology analysis with NetworkX
- Calculate node centrality (degree, betweenness)
- Identify hub metabolites and key enzymes
- Find bottleneck reactions
- Detect network modules with community detection
- Identify dysregulated subnetworks

Step 9: Correlation analysis across omics layers
- Calculate Spearman correlations between:
  * Gene expression and protein abundance
  * Protein abundance and metabolite levels
  * Gene expression and metabolites (for enzyme-product pairs)
- Use statsmodels for significance testing
- Focus on enzyme-metabolite pairs with expected relationships

Step 10: Bayesian network modeling with PyMC
- Build probabilistic graphical model of pathway
- Model causal relationships: gene → protein → metabolite
- Incorporate prior knowledge from KEGG/Reactome
- Perform inference to identify key regulatory nodes
- Estimate effect sizes and uncertainties

Step 11: Identify therapeutic targets
- Prioritize enzymes with:
  * Significant changes in all three omics layers
  * High network centrality
  * Druggable target class (kinases, transporters, etc.)
- Query DrugBank for existing inhibitors
- Search PubMed for validation in disease models

Step 12: Create comprehensive multi-omics report
- Summary statistics for each omics layer
- Venn diagram of overlapping pathway hits
- Pathway enrichment dot plots
- Integrated network visualization (color by fold change)
- Correlation heatmaps (enzyme-metabolite pairs)
- Bayesian network structure
- Table of prioritized therapeutic targets
- Biological interpretation and mechanistic insights
- Generate publication-quality figures
- Export PDF report with all results

Expected Output:
- Integrated multi-omics dataset
- Dysregulated pathway identification
- Multi-omics network model
- Prioritized list of therapeutic targets
- Comprehensive systems biology report
```

---

## Materials Science & Chemistry

### Example 10: High-Throughput Materials Discovery for Battery Applications

**Objective**: Discover novel solid electrolyte materials for lithium-ion batteries using computational screening.

**Skills Used**:
- `pymatgen` - Materials analysis and feature engineering
- `scikit-learn` - Machine learning
- `pymoo` - Multi-objective optimization
- `sympy` - Symbolic math
- `vaex` - Large dataset handling
- `dask` - Parallel computing
- `matplotlib` - Visualization
- `scientific-writing` - Report generation
- `scientific-visualization` - Publication figures

**Workflow**:

```bash
Step 1: Generate candidate materials library
- Use Pymatgen to enumerate compositions:
  * Li-containing compounds (Li₁₋ₓM₁₊ₓX₂)
  * M = transition metals (Zr, Ti, Ta, Nb)
  * X = O, S, Se
- Generate ~10,000 candidate compositions
- Apply charge neutrality constraints

Step 2: Filter by thermodynamic stability
- Query Materials Project database via Pymatgen
- Calculate formation energy from elements
- Calculate energy above convex hull (E_hull)
- Filter: E_hull < 50 meV/atom (likely stable)
- Retain ~2,000 thermodynamically plausible compounds

Step 3: Predict crystal structures
- Use Pymatgen structure predictor
- Generate most likely crystal structures for each composition
- Consider common structure types: LISICON, NASICON, garnet, perovskite
- Calculate structural descriptors

Step 4: Calculate material properties with Pymatgen
- Lattice parameters and volume
- Density
- Packing fraction
- Ionic radii and bond lengths
- Coordination environments

Step 5: Feature engineering with Pymatgen
- Calculate compositional features using Pymatgen's featurizers:
  * Elemental property statistics (electronegativity, ionic radius)
  * Valence electron concentrations
  * Stoichiometric attributes
- Calculate structural features:
  * Pore size distribution
  * Site disorder parameters
  * Partial radial distribution functions

Step 6: Build ML models for Li⁺ conductivity prediction
- Collect training data from literature (experimental conductivities)
- Train ensemble models with scikit-learn:
  * Random Forest
  * Gradient Boosting
  * Neural Network
- Use 5-fold cross-validation
- Predict ionic conductivity for all candidates

Step 7: Predict additional properties
- Electrochemical stability window (ML model)
- Mechanical properties (bulk modulus, shear modulus)
- Interfacial resistance (estimate from structure)
- Synthesis temperature (ML prediction from similar compounds)

Step 8: Multi-objective optimization with PyMOO
Define optimization objectives:
- Maximize: ionic conductivity (>10⁻³ S/cm target)
- Maximize: electrochemical window (>4.5V target)
- Minimize: synthesis temperature (<800°C preferred)
- Minimize: cost (based on elemental abundance)

Run NSGA-II to find Pareto optimal solutions
Extract top 50 candidates from Pareto front

Step 9: Analyze Pareto optimal materials
- Identify composition trends (which elements appear frequently)
- Analyze structure-property relationships
- Calculate trade-offs between objectives
- Identify "sweet spot" compositions

Step 10: Validate predictions with DFT calculations
- Select top 10 candidates for detailed study
- Set up DFT calculations using Pymatgen's interface
- Calculate:
  * Accurate formation energies
  * Li⁺ migration barriers (NEB calculations)
  * Electronic band gap
  * Elastic constants
- Compare DFT results with ML predictions

Step 11: Literature and patent search
- Search for prior art on top candidates
- PubMed and Google Scholar: "[composition] AND electrolyte"
- USPTO: Check for existing patents on similar compositions
- Identify any experimental reports on related materials

Step 12: Generate materials discovery report
- Summary of screening workflow and statistics
- Pareto front visualization (conductivity vs stability vs cost)
- Structure visualization of top candidates
- Property comparison table
- Composition-property trend analysis
- DFT validation results
- Predicted performance vs state-of-art materials
- Synthesis recommendations
- IP landscape summary
- Prioritized list of 5-10 materials for experimental validation
- Export as publication-ready PDF

Expected Output:
- Screened library of 10,000+ materials
- ML models for property prediction
- Pareto-optimal set of 50 candidates
- Detailed analysis of top 10 materials
- DFT validation results
- Comprehensive materials discovery report
```

---

## Digital Pathology

### Example 11: Automated Tumor Detection in Whole Slide Images

**Objective**: Develop and validate a deep learning model for automated tumor detection in histopathology images.

**Skills Used**:
- `histolab` - Whole slide image processing
- `pathml` - Computational pathology
- `pytorch-lightning` - Deep learning and image models
- `scikit-learn` - Model evaluation
- `pydicom` - DICOM handling
- `omero-integration` - Image management
- `matplotlib` - Visualization
- `scientific-visualization` - Publication-quality & interactive visualization
- `shap` - Model interpretability
- `clinical-reports` - Clinical validation reports

**Workflow**:

```bash
Step 1: Load whole slide images with HistoLab
- Load WSI files (SVS, TIFF formats)
- Extract slide metadata and magnification levels
- Visualize slide thumbnails
- Inspect tissue area vs background

Step 2: Tile extraction and preprocessing
- Use HistoLab to extract tiles (256×256 pixels at 20× magnification)
- Filter tiles:
  * Remove background (tissue percentage > 80%)
  * Apply color normalization (Macenko or Reinhard method)
  * Filter out artifacts and bubbles
- Extract ~100,000 tiles per slide across all slides

Step 3: Create annotations (if training from scratch)
- Load pathologist annotations (if available via OMERO)
- Convert annotations to tile-level labels
- Categories: tumor, stroma, necrosis, normal
- Balance classes through stratified sampling

Step 4: Set up PathML pipeline
- Create PathML SlideData objects
- Define preprocessing pipeline:
  * Stain normalization
  * Color augmentation (HSV jitter)
  * Rotation and flipping
- Split data: 70% train, 15% validation, 15% test

Step 5: Build deep learning model with PyTorch Lightning
- Architecture: ResNet50 or EfficientNet backbone
- Add custom classification head for tissue types
- Define training pipeline:
  * Loss function: Cross-entropy or Focal loss
  * Optimizer: Adam with learning rate scheduling
  * Augmentations: rotation, flip, color jitter, elastic deformation
  * Batch size: 32
  * Mixed precision training

Step 6: Train model
- Train on tile-level labels
- Monitor metrics: accuracy, F1 score, AUC
- Use early stopping on validation loss
- Save best model checkpoint
- Training time: ~6-12 hours on GPU

Step 7: Evaluate model performance
- Test on held-out test set
- Calculate metrics with scikit-learn:
  * Accuracy, precision, recall, F1 per class
  * Confusion matrix
  * ROC curves and AUC
- Compute confidence intervals with bootstrapping

Step 8: Slide-level aggregation
- Apply model to all tiles in each test slide
- Aggregate predictions:
  * Majority voting
  * Weighted average by confidence
  * Spatial smoothing with convolution
- Generate probability heatmaps overlaid on WSI

Step 9: Model interpretability with SHAP
- Apply GradCAM or SHAP to explain predictions
- Visualize which regions contribute to tumor classification
- Generate attention maps showing model focus
- Validate that model attends to relevant histological features

Step 10: Clinical validation
- Compare model predictions with pathologist diagnosis
- Calculate inter-rater agreement (kappa score)
- Identify discordant cases for review
- Analyze error types: false positives, false negatives

Step 11: Integration with OMERO
- Upload processed slides and heatmaps to OMERO server
- Attach model predictions as slide metadata
- Enable pathologist review interface
- Store annotations and corrections for model retraining

Step 12: Generate clinical validation report
- Model architecture and training details
- Performance metrics with confidence intervals
- Slide-level accuracy vs pathologist ground truth
- Heatmap visualizations for representative cases
- Analysis of failure modes
- Comparison with published methods
- Discussion of clinical applicability
- Recommendations for deployment and monitoring
- Export PDF report for regulatory submission (if needed)

Expected Output:
- Trained deep learning model for tumor detection
- Tile-level and slide-level predictions
- Probability heatmaps for visualization
- Performance metrics and validation results
- Model interpretation visualizations
- Clinical validation report
```

---

## Lab Automation & Protocol Design

### Example 12: Automated High-Throughput Screening Protocol

**Objective**: Design and execute an automated compound screening workflow using liquid handling robots.

**Skills Used**:
- `pylabrobot` - Lab automation
- `opentrons-integration` - Opentrons protocol
- `benchling-integration` - Sample tracking
- `labarchive-integration` - Electronic lab notebook
- `protocolsio-integration` - Protocol documentation
- `simpy` - Process simulation
- `polars` - Data processing
- `matplotlib` - Plate visualization
- `scientific-visualization` - Publication-quality & interactive visualization
- `rdkit` - PAINS filtering for hits
- `clinical-reports` - Screening report generation

**Workflow**:

```bash
Step 1: Define screening campaign in Benchling
- Create compound library in Benchling registry
- Register all compounds with structure, concentration, location
- Define plate layouts (384-well format)
- Track compound source plates in inventory
- Set up ELN entry for campaign documentation

Step 2: Design assay protocol
- Define assay steps:
  * Dispense cells (5000 cells/well)
  * Add compounds (dose-response curve, 10 concentrations)
  * Incubate 48 hours at 37°C
  * Add detection reagent (cell viability assay)
  * Read luminescence signal
- Calculate required reagent volumes
- Document protocol in Protocols.io
- Share with team for review

Step 3: Simulate workflow with SimPy
- Model liquid handler, incubator, plate reader as resources
- Simulate timing for 20 plates (7,680 wells)
- Identify bottlenecks (plate reader reads take 5 min/plate)
- Optimize scheduling: stagger plate processing
- Validate that throughput goal is achievable (20 plates/day)

Step 4: Design plate layout
- Use PyLabRobot to generate plate maps:
  * Columns 1-2: positive controls (DMSO)
  * Columns 3-22: compound titrations (10 concentrations in duplicate)
  * Columns 23-24: negative controls (cytotoxic control)
- Randomize compound positions across plates
- Account for edge effects (avoid outer wells for samples)
- Export plate maps to CSV

Step 5: Create Opentrons protocol for cell seeding
- Write Python protocol using Opentrons API 2.0
- Steps:
  * Aspirate cells from reservoir
  * Dispense 40 μL cell suspension per well
  * Tips: use P300 multi-channel for speed
  * Include mixing steps to prevent settling
- Simulate protocol in Opentrons app
- Test on one plate before full run

Step 6: Create Opentrons protocol for compound addition
- Acoustic liquid handler (Echo) or pin tool for nanoliter transfers
- If using Opentrons:
  * Source: 384-well compound plates
  * Transfer 100 nL compound (in DMSO) to assay plates
  * Use P20 for precision
  * Prepare serial dilutions on deck if needed
- Account for DMSO normalization (1% final)

Step 7: Integrate with Benchling for sample tracking
- Use Benchling API to:
  * Retrieve compound information (structure, batch, concentration)
  * Log plate creation in inventory
  * Create transfer records for audit trail
  * Link assay plates to ELN entry

Step 8: Execute automated workflow
- Day 1: Seed cells with Opentrons
- Day 1 (4h later): Add compounds with Opentrons
- Day 3: Add detection reagent (manual or automated)
- Day 3 (2h later): Read plates on plate reader
- Store plates at 4°C between steps

Step 9: Collect and process data
- Export raw luminescence data from plate reader
- Load data with Polars for fast processing
- Normalize data:
  * Subtract background (media-only wells)
  * Calculate % viability relative to DMSO control
  * Apply plate-wise normalization to correct systematic effects
- Quality control:
  * Z' factor calculation (> 0.5 for acceptable assay)
  * Coefficient of variation for controls (< 10%)
  * Flag plates with poor QC metrics

Step 10: Dose-response curve fitting
- Fit 4-parameter logistic curves for each compound
- Calculate IC50, Hill slope, max/min response
- Use scikit-learn or scipy for curve fitting
- Compute 95% confidence intervals
- Flag compounds with poor curve fits (R² < 0.8)

Step 11: Hit identification and triage
- Define hit criteria:
  * IC50 < 10 μM
  * Max inhibition > 50%
  * Curve quality: R² > 0.8
- Prioritize hits by potency
- Check for PAINS patterns with RDKit
- Cross-reference with known aggregators/frequent hitters

Step 12: Visualize results and generate report
- Create plate heatmaps showing % viability
- Dose-response curve plots for hits
- Scatter plot: potency vs max effect
- QC metric summary across plates
- Structure visualization of top 20 hits
- Generate campaign summary report:
  * Screening statistics (compounds tested, hit rate)
  * QC metrics and data quality assessment
  * Hit list with structures and IC50 values
  * Protocol documentation from Protocols.io
  * Raw data files and analysis code
  * Recommendations for confirmation assays
- Update Benchling ELN with results
- Export PDF report for stakeholders

Expected Output:
- Automated screening protocols (Opentrons Python files)
- Executed screen of 384-well plates
- Quality-controlled dose-response data
- Hit list with IC50 values
- Comprehensive screening report
```

---

## Agricultural Genomics

### Example 13: GWAS for Crop Yield Improvement

**Objective**: Identify genetic markers associated with drought tolerance and yield in a crop species.

**Skills Used**:
- `database-lookup` - Query GWAS Catalog, Ensembl, NCBI Gene
- `biopython` - Sequence analysis
- `pysam` - VCF processing
- `gget` - Gene data retrieval
- `scanpy` - Population structure analysis
- `scikit-learn` - PCA and clustering
- `statsmodels` - Association testing
- `statistical-analysis` - Hypothesis testing
- `matplotlib` - Manhattan plots
- `seaborn` - Visualization
- `scientific-visualization` - Publication-quality & interactive visualization

**Workflow**:

```bash
Step 1: Load and QC genotype data
- Load VCF file with pysam
- Filter variants:
  * Call rate > 95%
  * Minor allele frequency (MAF) > 5%
  * Hardy-Weinberg equilibrium p > 1e-6
- Convert to numeric genotype matrix (0, 1, 2)
- Retain ~500,000 SNPs after QC

Step 2: Assess population structure
- Calculate genetic relationship matrix
- Perform PCA with scikit-learn (use top 10 PCs)
- Visualize population structure (PC1 vs PC2)
- Identify distinct subpopulations or admixture
- Note: will use PCs as covariates in GWAS

Step 3: Load and process phenotype data
- Drought tolerance score (1-10 scale, measured under stress)
- Grain yield (kg/hectare)
- Days to flowering
- Plant height
- Quality control:
  * Remove outliers (> 3 SD from mean)
  * Transform if needed (log or rank-based for skewed traits)
  * Adjust for environmental covariates (field, year)

Step 4: Calculate kinship matrix
- Compute genetic relatedness matrix
- Account for population structure and relatedness
- Will use in mixed linear model to control for confounding

Step 5: Run genome-wide association study
- For each phenotype, test association with each SNP
- Use mixed linear model (MLM) in statsmodels:
  * Fixed effects: SNP genotype, PCs (top 10)
  * Random effects: kinship matrix
  * Bonferroni threshold: p < 5e-8 (genome-wide significance)
- Multiple testing correction: Bonferroni or FDR
- Calculate genomic inflation factor (λ) to check for inflation

Step 6: Identify significant associations
- Extract SNPs passing significance threshold
- Determine lead SNPs (most significant in each locus)
- Define loci: extend ±500 kb around lead SNP
- Identify independent associations via conditional analysis

Step 7: Annotate significant loci
- Map SNPs to genes using Ensembl Plants API
- Identify genic vs intergenic SNPs
- For genic SNPs:
  * Determine consequence (missense, synonymous, intronic, UTR)
  * Extract gene names and descriptions
- Query NCBI Gene for gene function
- Prioritize genes with known roles in stress response or development

Step 8: Search GWAS Catalog for prior reports
- Query GWAS Catalog for similar traits in same or related species
- Check for replication of known loci
- Identify novel vs known associations

Step 9: Functional enrichment analysis
- Extract all genes within significant loci
- Perform GO enrichment analysis
- Test for enrichment in KEGG pathways
- Focus on pathways related to:
  * Drought stress response (ABA signaling, osmotic adjustment)
  * Photosynthesis and carbon fixation
  * Root development

Step 10: Estimate SNP heritability and genetic architecture
- Calculate variance explained by significant SNPs
- Estimate SNP-based heritability (proportion of variance explained)
- Assess genetic architecture: few large-effect vs many small-effect loci

Step 11: Build genomic prediction model
- Train genomic selection model with scikit-learn:
  * Ridge regression (GBLUP equivalent)
  * Elastic net
  * Random Forest
- Use all SNPs (not just significant ones)
- Cross-validate to predict breeding values
- Assess prediction accuracy

Step 12: Generate GWAS report
- Manhattan plots for each trait
- QQ plots to assess test calibration
- Regional association plots for significant loci
- Gene models overlaid on loci
- Table of significant SNPs with annotations
- Functional enrichment results
- Genomic prediction accuracy
- Biological interpretation:
  * Candidate genes for drought tolerance
  * Potential molecular mechanisms
  * Implications for breeding programs
- Recommendations:
  * SNPs to use for marker-assisted selection
  * Genes for functional validation
  * Crosses to generate mapping populations
- Export publication-quality PDF with all results

Expected Output:
- Significant SNP-trait associations
- Annotated candidate genes
- Functional enrichment analysis
- Genomic prediction models
- Comprehensive GWAS report
- Recommendations for breeding programs
```

---

## Neuroscience & Brain Imaging

### Example 14: Brain Connectivity Analysis from fMRI Data

**Objective**: Analyze resting-state fMRI data to identify altered brain connectivity patterns in disease.

**Skills Used**:
- `bids` - Organize/validate neuroimaging data in BIDS format
- `neurokit2` - Neurophysiological signal processing
- `neuropixels-analysis` - Neural data analysis
- `scikit-learn` - Classification and clustering
- `networkx` - Graph theory analysis
- `statsmodels` - Statistical testing
- `statistical-analysis` - Hypothesis testing
- `torch-geometric` - Graph neural networks
- `pymc` - Bayesian modeling
- `matplotlib` - Brain visualization
- `seaborn` - Connectivity matrices
- `scientific-visualization` - Publication-quality & interactive visualization

**Workflow**:

```bash
Step 1: Load and preprocess fMRI data
# Note: Use nilearn or similar for fMRI-specific preprocessing
- Organize and validate the dataset in BIDS layout using the bids skill
  (standardized sub-*/func/ structure, JSON sidecars, participants.tsv)
- Load 4D fMRI images (BOLD signal)
- Preprocessing:
  * Motion correction (realignment)
  * Slice timing correction
  * Spatial normalization to MNI space
  * Smoothing (6mm FWHM Gaussian kernel)
  * Temporal filtering (0.01-0.1 Hz bandpass)
  * Nuisance regression (motion, CSF, white matter)

Step 2: Define brain regions (parcellation)
- Apply brain atlas (e.g., AAL, Schaefer 200-region atlas)
- Extract average time series for each region
- Result: 200 time series per subject (one per brain region)

Step 3: Signal cleaning with NeuroKit2
- Denoise time series
- Remove physiological artifacts
- Apply additional bandpass filtering if needed
- Identify and handle outlier time points

Step 4: Calculate functional connectivity
- Compute pairwise Pearson correlations between all regions
- Result: 200×200 connectivity matrix per subject
- Fisher z-transform correlations for group statistics
- Threshold weak connections (|r| < 0.2)

Step 5: Graph theory analysis with NetworkX
- Convert connectivity matrices to graphs
- Calculate global network metrics:
  * Clustering coefficient (local connectivity)
  * Path length (integration)
  * Small-worldness (balance of segregation and integration)
  * Modularity (community structure)
- Calculate node-level metrics:
  * Degree centrality
  * Betweenness centrality
  * Eigenvector centrality
  * Participation coefficient (inter-module connectivity)

Step 6: Statistical comparison between groups
- Compare patients vs healthy controls
- Use statsmodels for group comparisons:
  * Paired or unpaired t-tests for connectivity edges
  * FDR correction for multiple comparisons across all edges
  * Identify edges with significantly different connectivity
- Compare global and node-level network metrics
- Calculate effect sizes (Cohen's d)

Step 7: Identify altered subnetworks
- Threshold statistical maps (FDR < 0.05)
- Identify clusters of altered connectivity
- Map to functional brain networks:
  * Default mode network (DMN)
  * Salience network (SN)
  * Central executive network (CEN)
  * Sensorimotor network
- Visualize altered connections on brain surfaces

Step 8: Machine learning classification
- Train classifier to distinguish patients from controls
- Use scikit-learn Random Forest or SVM
- Features: connectivity values or network metrics
- Cross-validation (10-fold)
- Calculate accuracy, sensitivity, specificity, AUC
- Identify most discriminative features (connectivity edges)

Step 9: Graph neural network analysis with Torch Geometric
- Build graph neural network (GCN or GAT)
- Input: connectivity matrices as adjacency matrices
- Train to predict diagnosis
- Extract learned representations
- Visualize latent space (UMAP)
- Interpret which brain regions are most important

Step 10: Bayesian network modeling with PyMC
- Build directed graphical model of brain networks
- Estimate effective connectivity (directional influence)
- Incorporate prior knowledge about anatomical connections
- Perform posterior inference
- Identify key driver regions in disease

Step 11: Clinical correlation analysis
- Correlate network metrics with clinical scores:
  * Symptom severity
  * Cognitive performance
  * Treatment response
- Use Spearman or Pearson correlation
- Identify brain-behavior relationships

Step 12: Generate comprehensive neuroimaging report
- Brain connectivity matrices (patients vs controls)
- Statistical comparison maps on brain surface
- Network metric comparison bar plots
- Graph visualizations (circular or force-directed layout)
- Machine learning ROC curves
- Brain-behavior correlation plots
- Clinical interpretation:
  * Which networks are disrupted?
  * Relationship to symptoms
  * Potential biomarker utility
- Recommendations:
  * Brain regions for therapeutic targeting (TMS, DBS)
  * Network metrics as treatment response predictors
- Export publication-ready PDF with brain visualizations

Expected Output:
- Functional connectivity matrices for all subjects
- Statistical maps of altered connectivity
- Graph theory metrics
- Machine learning classification model
- Brain-behavior correlations
- Comprehensive neuroimaging report
```

---

## Environmental Microbiology

### Example 15: Metagenomic Analysis of Environmental Samples

**Objective**: Characterize microbial community composition and functional potential from environmental DNA samples.

**Skills Used**:
- `database-lookup` - Query ENA, GEO, UniProt, KEGG
- `biopython` - Sequence processing
- `pysam` - BAM file handling
- `phylogenetics` - MAFFT/IQ-TREE/FastTree tree building
- `etetoolkit` - Phylogenetic trees
- `scikit-bio` - Microbial ecology
- `networkx` - Co-occurrence networks
- `statsmodels` - Diversity statistics
- `statistical-analysis` - Hypothesis testing
- `matplotlib` - Visualization
- `scientific-visualization` - Publication-quality & interactive visualization

**Workflow**:

```bash
Step 1: Load and QC metagenomic reads
- Load FASTQ files with BioPython
- Quality control with FastQC-equivalent:
  * Remove adapters and low-quality bases (Q < 20)
  * Filter short reads (< 50 bp)
  * Remove host contamination (if applicable)
- Subsample to even depth if comparing samples

Step 2: Taxonomic classification
- Use Kraken2-like approach or query ENA database
- Classify reads to taxonomic lineages
- Generate abundance table:
  * Rows: taxa (species or OTUs)
  * Columns: samples
  * Values: read counts or relative abundance
- Summarize at different levels: phylum, class, order, family, genus, species

Step 3: Calculate diversity metrics with scikit-bio
- Alpha diversity (within-sample):
  * Richness (number of species)
  * Shannon entropy
  * Simpson diversity
  * Chao1 estimated richness
- Beta diversity (between-sample):
  * Bray-Curtis dissimilarity
  * Weighted/unweighted UniFrac distance
  * Jaccard distance
- Rarefaction curves to assess sampling completeness

Step 4: Statistical comparison of communities
- Compare diversity between groups (e.g., polluted vs pristine)
- Use statsmodels for:
  * Mann-Whitney or Kruskal-Wallis tests (alpha diversity)
  * PERMANOVA for beta diversity (adonis test)
  * LEfSe for differential abundance testing
- Identify taxa enriched or depleted in each condition

Step 5: Build phylogenetic tree with ETE Toolkit
- Extract 16S rRNA sequences (or marker genes)
- Align sequences (MUSCLE/MAFFT equivalent)
- Build phylogenetic tree (neighbor-joining or maximum likelihood)
- Visualize tree colored by sample or environment
- Root tree with outgroup

Step 6: Co-occurrence network analysis
- Calculate pairwise correlations between taxa
- Use Spearman correlation to identify co-occurrence patterns
- Filter significant correlations (p < 0.01, |r| > 0.6)
- Build co-occurrence network with NetworkX
- Identify modules (communities of co-occurring taxa)
- Calculate network topology metrics
- Visualize network (nodes = taxa, edges = correlations)

Step 7: Functional annotation
- Assemble contigs from reads (if performing assembly)
- Predict genes with Prodigal-like tools
- Annotate genes using UniProt and KEGG
- Map proteins to KEGG pathways
- Generate functional profile:
  * Abundance of metabolic pathways
  * Key enzymes (nitrification, denitrification, methanogenesis)
  * Antibiotic resistance genes
  * Virulence factors

Step 8: Functional diversity analysis
- Compare functional profiles between samples
- Calculate pathway richness and evenness
- Identify enriched pathways with statistical testing
- Link taxonomy to function:
  * Which taxa contribute to which functions?
  * Use shotgun data to assign functions to taxa

Step 9: Search ENA for related environmental samples
- Query ENA for metagenomic studies from similar environments
- Download and compare to own samples
- Place samples in context of global microbiome diversity
- Identify unique vs ubiquitous taxa

Step 10: Environmental parameter correlation
- Correlate community composition with metadata:
  * Temperature, pH, salinity
  * Nutrient concentrations (N, P)
  * Pollutant levels (heavy metals, hydrocarbons)
- Use Mantel test to correlate distance matrices
- Identify environmental drivers of community structure

Step 11: Biomarker discovery
- Identify taxa or pathways that correlate with environmental condition
- Use Random Forest to find predictive features
- Validate biomarkers:
  * Sensitivity and specificity
  * Cross-validation across samples
- Propose taxa as bioindicators of environmental health

Step 12: Generate environmental microbiome report
- Taxonomic composition bar charts (stacked by phylum/class)
- Alpha and beta diversity plots (boxplots, PCoA)
- Phylogenetic tree with environmental context
- Co-occurrence network visualization
- Functional pathway heatmaps
- Environmental correlation plots
- Statistical comparison tables
- Biological interpretation:
  * Dominant taxa and their ecological roles
  * Functional potential of the community
  * Environmental factors shaping the microbiome
  * Biomarker taxa for monitoring
- Recommendations:
  * Biomarkers for environmental monitoring
  * Functional guilds for restoration
  * Further sampling or sequencing strategies
- Export comprehensive PDF report

Expected Output:
- Taxonomic profiles for all samples
- Diversity metrics and statistical comparisons
- Phylogenetic tree
- Co-occurrence network
- Functional annotation and pathway analysis
- Comprehensive microbiome report
```

---

## Infectious Disease Research

### Example 16: Antimicrobial Resistance Surveillance and Prediction

**Objective**: Track antimicrobial resistance trends and predict resistance phenotypes from genomic data.

**Skills Used**:
- `database-lookup` - Query ENA, UniProt, NCBI Gene
- `biopython` - Sequence analysis
- `pysam` - Genome assembly analysis
- `phylogenetics` - Core-genome alignment and ML phylogenies
- `etetoolkit` - Phylogenetic analysis
- `polars-bio` - Fast genomic interval operations on assemblies
- `scikit-learn` - Resistance prediction
- `networkx` - Transmission networks
- `statsmodels` - Trend analysis
- `statistical-analysis` - Hypothesis testing
- `matplotlib` - Epidemiological plots
- `scientific-visualization` - Publication-quality & interactive visualization
- `clinical-reports` - Surveillance reports

**Workflow**:

```bash
Step 1: Collect bacterial genome sequences
- Isolates from hospital surveillance program
- Load FASTA assemblies with BioPython
- Basic QC:
  * Assess assembly quality (N50, completeness)
  * Estimate genome size and coverage
  * Remove contaminated assemblies

Step 2: Species identification and MLST typing
- Perform in silico MLST (multi-locus sequence typing)
- Extract housekeeping gene sequences
- Assign sequence types (ST)
- Classify isolates into clonal complexes
- Identify high-risk clones (e.g., ST131 E. coli, ST258 K. pneumoniae)

Step 3: Antimicrobial resistance (AMR) gene detection
- Query NCBI Gene and UniProt for AMR gene databases
- Screen assemblies for resistance genes:
  * Beta-lactamases (blaTEM, blaCTX-M, blaKPC, blaNDM)
  * Aminoglycoside resistance (aac, aph, ant)
  * Fluoroquinolone resistance (gyrA, parC mutations)
  * Colistin resistance (mcr-1 to mcr-10)
  * Efflux pumps
- Calculate gene presence/absence matrix

Step 4: Resistance mechanism annotation
- Map detected genes to resistance classes:
  * Enzymatic modification (e.g., beta-lactamases)
  * Target modification (e.g., ribosomal methylation)
  * Target mutation (e.g., fluoroquinolone resistance)
  * Efflux pumps
- Query UniProt for detailed mechanism descriptions
- Link genes to antibiotic classes affected

Step 5: Build phylogenetic tree with ETE Toolkit
- Extract core genome SNPs
- Concatenate SNP alignments
- Build maximum likelihood tree
- Root with outgroup or midpoint rooting
- Annotate tree with:
  * Resistance profiles
  * Sequence types
  * Collection date and location

Step 6: Genotype-phenotype correlation
- Match genomic data with phenotypic susceptibility testing
- For each antibiotic, correlate:
  * Presence of resistance genes with MIC values
  * Target mutations with resistance phenotype
- Calculate sensitivity/specificity of genetic markers
- Identify discordant cases (false positives/negatives)

Step 7: Machine learning resistance prediction
- Train classification models with scikit-learn:
  * Features: presence/absence of resistance genes + mutations
  * Target: resistance phenotype (susceptible/intermediate/resistant)
  * Models: Logistic Regression, Random Forest, Gradient Boosting
- Train separate models for each antibiotic
- Cross-validate (stratified 5-fold)
- Calculate accuracy, precision, recall, F1 score
- Feature importance: which genes are most predictive?

Step 8: Temporal trend analysis
- Track resistance rates over time
- Use statsmodels for:
  * Mann-Kendall trend test
  * Joinpoint regression (identify change points)
  * Forecast future resistance rates (ARIMA)
- Analyze trends for each antibiotic class
- Identify emerging resistance mechanisms

Step 9: Transmission network inference
- Identify closely related isolates (< 10 SNPs difference)
- Build transmission network with NetworkX:
  * Nodes: isolates
  * Edges: putative transmission links
- Incorporate temporal and spatial data
- Identify outbreak clusters
- Detect super-spreaders (high degree nodes)
- Analyze network topology

Step 10: Search ENA for global context
- Query ENA for same species from other regions/countries
- Download representative genomes
- Integrate into phylogenetic analysis
- Assess whether local isolates are globally distributed clones
- Identify region-specific vs international resistance genes

Step 11: Plasmid and mobile element analysis
- Identify plasmid contigs
- Detect insertion sequences and transposons
- Track mobile genetic elements carrying resistance genes
- Identify conjugative plasmids facilitating horizontal gene transfer
- Build plasmid similarity networks

Step 12: Generate AMR surveillance report
- Summary statistics:
  * Number of isolates by species, ST, location
  * Resistance rates for each antibiotic
- Phylogenetic tree annotated with resistance profiles
- Temporal trend plots (resistance % over time)
- Transmission network visualizations
- Prediction model performance metrics
- Heatmap: resistance genes by isolate
- Geographic distribution map (if spatial data available)
- Interpretation:
  * Predominant resistance mechanisms
  * High-risk clones circulating
  * Temporal trends and emerging threats
  * Transmission clusters and outbreaks
- Recommendations:
  * Infection control measures for clusters
  * Antibiotic stewardship priorities
  * Resistance genes to monitor
  * Laboratories to perform confirmatory testing
- Export comprehensive PDF for public health reporting

Expected Output:
- AMR gene profiles for all isolates
- Phylogenetic tree with resistance annotations
- Temporal trends in resistance rates
- ML models for resistance prediction from genomes
- Transmission networks
- Comprehensive AMR surveillance report for public health
```

---

## Multi-Omics Integration

### Example 17: Integrative Analysis of Cancer Multi-Omics Data

**Objective**: Integrate genomics, transcriptomics, proteomics, and clinical data to identify cancer subtypes and therapeutic strategies.

**Skills Used**:
- `database-lookup` - Query Ensembl, COSMIC, STRING, Reactome, Open Targets
- `pydeseq2` - RNA-seq DE analysis
- `pysam` - Variant calling
- `gget` - Gene data retrieval
- `scikit-learn` - Clustering and classification
- `torch-geometric` - Graph neural networks
- `umap-learn` - Dimensionality reduction
- `scikit-survival` - Survival analysis
- `statsmodels` - Statistical modeling
- `pymoo` - Multi-objective optimization
- `pyhealth` - Healthcare ML models
- `clinical-reports` - Integrative genomics report

**Workflow**:

```bash
Step 1: Load and preprocess genomic data (WES/WGS)
- Parse VCF files with pysam
- Filter high-quality variants (QUAL > 30, DP > 20)
- Annotate with Ensembl VEP (missense, nonsense, frameshift)
- Query COSMIC for known cancer mutations
- Create mutation matrix: samples × genes (binary: mutated or not)
- Focus on cancer genes from COSMIC Cancer Gene Census

Step 2: Process transcriptomic data (RNA-seq)
- Load gene count matrix
- Run differential expression with PyDESeq2
- Compare tumor vs normal (if paired samples available)
- Normalize counts (TPM or FPKM)
- Identify highly variable genes
- Create expression matrix: samples × genes (log2 TPM)

Step 3: Load proteomic data (Mass spec)
- Protein abundance matrix from LC-MS/MS
- Normalize protein abundances (median normalization)
- Log2-transform
- Filter proteins detected in < 50% of samples
- Create protein matrix: samples × proteins

Step 4: Load clinical data
- Demographics: age, sex, race
- Tumor characteristics: stage, grade, histology
- Treatment: surgery, chemo, radiation, targeted therapy
- Outcome: overall survival (OS), progression-free survival (PFS)
- Response: complete/partial response, stable/progressive disease

Step 5: Data integration and harmonization
- Match sample IDs across omics layers
- Ensure consistent gene/protein identifiers
- Handle missing data:
  * Impute with KNN or median (for moderate missingness)
  * Remove features with > 50% missing
- Create multi-omics data structure (dictionary of matrices)

Step 6: Multi-omics dimensionality reduction
- Concatenate all omics features (genes + proteins + mutations)
- Apply UMAP with umap-learn for visualization
- Alternative: PCA or t-SNE
- Visualize samples in 2D space colored by:
  * Histological subtype
  * Stage
  * Survival (high vs low)
- Identify patterns or clusters

Step 7: Unsupervised clustering to identify subtypes
- Perform consensus clustering with scikit-learn
- Test k = 2 to 10 clusters
- Evaluate cluster stability and optimal k
- Assign samples to clusters (subtypes)
- Visualize clustering in UMAP space

Step 8: Characterize molecular subtypes
For each subtype:
- Differential expression analysis:
  * Compare subtype vs all others with PyDESeq2
  * Extract top differentially expressed genes and proteins
- Mutation enrichment:
  * Fisher's exact test for each gene
  * Identify subtype-specific mutations
- Pathway enrichment:
  * Query Reactome for enriched pathways
  * Query KEGG for metabolic pathway differences
  * Identify hallmark biological processes

Step 9: Build protein-protein interaction networks
- Query STRING database for interactions among:
  * Differentially expressed proteins
  * Products of mutated genes
- Construct PPI network with NetworkX
- Identify network modules (community detection)
- Calculate centrality metrics to find hub proteins
- Overlay fold changes on network for visualization

Step 10: Survival analysis by subtype
- Use statsmodels or lifelines for survival analysis
- Kaplan-Meier curves for each subtype
- Log-rank test for significance
- Cox proportional hazards model:
  * Covariates: subtype, stage, age, treatment
  * Estimate hazard ratios
- Identify prognostic subtypes

Step 11: Predict therapeutic response
- Train machine learning models with scikit-learn:
  * Features: multi-omics data
  * Target: response to specific therapy (responder/non-responder)
  * Models: Random Forest, XGBoost, SVM
- Cross-validation to assess performance
- Identify features predictive of response
- Calculate AUC and feature importance

Step 12: Graph neural network for integrated prediction
- Build heterogeneous graph with Torch Geometric:
  * Nodes: samples, genes, proteins, pathways
  * Edges: gene-protein, protein-protein, gene-pathway
  * Node features: expression, mutation status
- Train GNN to predict:
  * Subtype classification
  * Survival risk
  * Treatment response
- Extract learned embeddings for interpretation

Step 13: Identify therapeutic targets with Open Targets
- For each subtype, query Open Targets:
  * Input: upregulated genes/proteins
  * Extract target-disease associations
  * Prioritize by tractability score
- Search for FDA-approved drugs targeting identified proteins
- Identify clinical trials for relevant targets
- Propose subtype-specific therapeutic strategies

Step 14: Multi-objective optimization of treatment strategies
- Use PyMOO to optimize treatment selection:
  * Objectives:
    1. Maximize predicted response probability
    2. Minimize predicted toxicity
    3. Minimize cost
  * Constraints: patient eligibility, drug availability
- Generate Pareto-optimal treatment strategies
- Personalized treatment recommendations per patient

Step 15: Generate comprehensive multi-omics report
- Sample clustering and subtype assignments
- UMAP visualization colored by subtype, survival, mutations
- Subtype characterization:
  * Molecular signatures (genes, proteins, mutations)
  * Enriched pathways
  * PPI networks
- Kaplan-Meier survival curves by subtype
- ML model performance (AUC, confusion matrices)
- Feature importance plots
- Therapeutic target tables with supporting evidence
- Personalized treatment recommendations
- Clinical implications:
  * Prognostic biomarkers
  * Predictive biomarkers for therapy selection
  * Novel drug targets
- Export publication-quality PDF with all figures and tables

Expected Output:
- Integrated multi-omics dataset
- Cancer subtype classification
- Molecular characterization of subtypes
- Survival analysis and prognostic markers
- Predictive models for treatment response
- Therapeutic target identification
- Personalized treatment strategies
- Comprehensive integrative genomics report
```

---

## Experimental Physics & Data Analysis

### Example 18: Analysis of Particle Physics Detector Data

**Objective**: Analyze experimental data from particle detector to identify signal events and measure physical constants.

**Skills Used**:
- `astropy` - Units and constants
- `sympy` - Symbolic mathematics
- `matlab` - Matrix/numerical computing and signal processing
- `statistical-analysis` - Statistical analysis
- `scikit-learn` - Classification
- `stable-baselines3` - Reinforcement learning for optimization
- `matplotlib` - Visualization
- `seaborn` - Statistical plots
- `statsmodels` - Hypothesis testing
- `dask` - Large-scale data processing
- `vaex` - Out-of-core dataframes
- `scientific-visualization` - Publication-quality & interactive visualization

**Workflow**:

```bash
Step 1: Load and inspect detector data
- Load ROOT files or HDF5 with raw detector signals
- Use Vaex for out-of-core processing (TBs of data)
- Inspect data structure: event IDs, timestamps, detector channels
- Extract key observables:
  * Energy deposits in calorimeters
  * Particle trajectories from tracking detectors
  * Time-of-flight measurements
  * Trigger information

Step 2: Apply detector calibration and corrections
- Load calibration constants
- Apply energy calibrations to convert ADC to physical units
- Correct for detector efficiency variations
- Apply geometric corrections (alignment)
- Use Astropy units for unit conversions (eV, GeV, MeV)
- Account for dead time and detector acceptance

Step 3: Event reconstruction
- Cluster energy deposits to form particle candidates
- Reconstruct particle trajectories (tracks)
- Match tracks to calorimeter clusters
- Calculate invariant masses for particle identification
- Compute momentum and energy for each particle
- Use Dask for parallel processing across events

Step 4: Event selection and filtering
- Define signal region based on physics hypothesis
- Apply quality cuts:
  * Track quality (chi-squared, number of hits)
  * Fiducial volume cuts
  * Timing cuts (beam window)
  * Particle identification cuts
- Estimate trigger efficiency
- Calculate event weights for corrections

Step 5: Background estimation
- Identify background sources:
  * Cosmic rays
  * Beam-related backgrounds
  * Detector noise
  * Physics backgrounds (non-signal processes)
- Simulate backgrounds using Monte Carlo (if available)
- Estimate background from data in control regions
- Use sideband subtraction method

Step 6: Signal extraction
- Fit invariant mass distributions to extract signal
- Use scipy for likelihood fitting:
  * Signal model: Gaussian or Breit-Wigner
  * Background model: polynomial or exponential
  * Combined fit with maximum likelihood
- Calculate signal significance (S/√B or Z-score)
- Estimate systematic uncertainties

Step 7: Machine learning event classification
- Train classifier with scikit-learn to separate signal from background
- Features: kinematic variables, topology, detector response
- Models: Boosted Decision Trees (XGBoost), Neural Networks
- Cross-validate with k-fold CV
- Optimize selection criteria using ROC curves
- Calculate signal efficiency and background rejection

Step 8: Reinforcement learning for trigger optimization
- Use Stable-Baselines3 to optimize trigger thresholds
- Environment: detector simulator
- Action: adjust trigger thresholds
- Reward: maximize signal efficiency while controlling rate
- Train PPO or SAC agent
- Validate on real data

Step 9: Calculate physical observables
- Measure cross-sections:
  * σ = N_signal / (ε × L × BR)
  * N_signal: number of signal events
  * ε: detection efficiency
  * L: integrated luminosity
  * BR: branching ratio
- Use Sympy for symbolic error propagation
- Calculate with Astropy for proper unit handling

Step 10: Statistical analysis and hypothesis testing
- Perform hypothesis tests with statsmodels:
  * Likelihood ratio test for signal vs background-only
  * Calculate p-values and significance levels
  * Set confidence limits (CLs method)
- Bayesian analysis for parameter estimation
- Calculate confidence intervals and error bands

Step 11: Systematic uncertainty evaluation
- Identify sources of systematic uncertainty:
  * Detector calibration uncertainties
  * Background estimation uncertainties
  * Theoretical uncertainties (cross-sections, PDFs)
  * Monte Carlo modeling uncertainties
- Propagate uncertainties through analysis chain
- Combine statistical and systematic uncertainties
- Present as error budget

Step 12: Create comprehensive physics report
- Event displays showing candidate signal events
- Kinematic distributions (momentum, energy, angles)
- Invariant mass plots with fitted signal
- ROC curves for ML classifiers
- Cross-section measurements with error bars
- Comparison with theoretical predictions
- Systematic uncertainty breakdown
- Statistical significance calculations
- Interpretation:
  * Consistency with Standard Model
  * Constraints on new physics parameters
  * Discovery potential or exclusion limits
- Recommendations:
  * Detector improvements
  * Additional data needed
  * Future analysis strategies
- Export publication-ready PDF formatted for physics journal

Expected Output:
- Reconstructed physics events
- Signal vs background classification
- Measured cross-sections and branching ratios
- Statistical significance of observations
- Systematic uncertainty analysis
- Comprehensive experimental physics paper
```

---

## Chemical Engineering & Process Optimization

### Example 19: Optimization of Chemical Reactor Design and Operation

**Objective**: Design and optimize a continuous chemical reactor for maximum yield and efficiency while meeting safety and economic constraints.

**Skills Used**:
- `sympy` - Symbolic equations and reaction kinetics
- `statistical-analysis` - Numerical analysis
- `pymoo` - Multi-objective optimization
- `simpy` - Process simulation
- `pymc` - Bayesian parameter estimation
- `scikit-learn` - Process modeling
- `stable-baselines3` - Real-time control optimization
- `pufferlib` - High-throughput vectorized RL training for control policies
- `matplotlib` - Process diagrams
- `scientific-visualization` - Publication-quality & interactive visualization
- `fluidsim` - Fluid dynamics simulation
- `scientific-writing` - Engineering reports
- `pdf` - Technical documentation

**Workflow**:

```bash
Step 1: Define reaction system and kinetics
- Chemical reaction: A + B → C + D
- Use Sympy to define symbolic rate equations:
  * Arrhenius equation: k = A × exp(-Ea/RT)
  * Rate law: r = k × [A]^α × [B]^β
- Define material and energy balances symbolically
- Include equilibrium constants and thermodynamics
- Account for side reactions and byproducts

Step 2: Develop reactor model
- Select reactor type: CSTR, PFR, batch, or semi-batch
- Write conservation equations:
  * Mass balance: dC/dt = (F_in × C_in - F_out × C)/V + r
  * Energy balance: ρCp × dT/dt = Q - ΔH_rxn × r × V
  * Momentum balance (pressure drop)
- Include heat transfer correlations
- Model mixing and mass transfer limitations

Step 3: Parameter estimation with PyMC
- Load experimental data from pilot reactor
- Bayesian inference to estimate kinetic parameters:
  * Pre-exponential factor (A)
  * Activation energy (Ea)
  * Reaction orders (α, β)
- Use MCMC sampling with PyMC
- Incorporate prior knowledge from literature
- Calculate posterior distributions and credible intervals
- Assess parameter uncertainty and correlation

Step 4: Model validation
- Simulate reactor with estimated parameters using scipy.integrate
- Compare predictions with experimental data
- Calculate goodness of fit (R², RMSE)
- Perform sensitivity analysis:
  * Which parameters most affect yield?
  * Identify critical operating conditions
- Refine model if needed

Step 5: Machine learning surrogate model
- Train fast surrogate model with scikit-learn
- Generate training data from detailed model (1000+ runs)
- Features: T, P, residence time, feed composition, catalyst loading
- Target: yield, selectivity, conversion
- Models: Gaussian Process Regression, Random Forest
- Validate surrogate accuracy (R² > 0.95)
- Use for rapid optimization

Step 6: Single-objective optimization
- Maximize yield with scipy.optimize:
  * Decision variables: T, P, feed ratio, residence time
  * Objective: maximize Y = (moles C produced) / (moles A fed)
  * Constraints:
    - Temperature: 300 K ≤ T ≤ 500 K (safety)
    - Pressure: 1 bar ≤ P ≤ 50 bar (equipment limits)
    - Residence time: 1 min ≤ τ ≤ 60 min
    - Conversion: X_A ≥ 90%
- Use Sequential Least Squares Programming (SLSQP)
- Identify optimal operating point

Step 7: Multi-objective optimization with PyMOO
- Competing objectives:
  1. Maximize product yield
  2. Minimize energy consumption (heating/cooling)
  3. Minimize operating cost (raw materials, utilities)
  4. Maximize reactor productivity (throughput)
- Constraints:
  - Safety: temperature and pressure limits
  - Environmental: waste production limits
  - Economic: minimum profitability
- Run NSGA-II or NSGA-III
- Generate Pareto front of optimal solutions
- Select operating point based on preferences

Step 8: Dynamic process simulation with SimPy
- Model complete plant:
  * Reactors, separators, heat exchangers
  * Pumps, compressors, valves
  * Storage tanks and buffers
- Simulate startup, steady-state, and shutdown
- Include disturbances:
  * Feed composition variations
  * Equipment failures
  * Demand fluctuations
- Evaluate dynamic stability
- Calculate time to steady state

Step 9: Control system design
- Design feedback control loops:
  * Temperature control (PID controller)
  * Pressure control
  * Flow control
  * Level control
- Tune PID parameters using Ziegler-Nichols or optimization
- Implement cascade control for improved performance
- Add feedforward control for disturbance rejection

Step 10: Reinforcement learning for advanced control
- Use Stable-Baselines3 to train RL agent:
  * Environment: reactor simulation (SimPy-based)
  * State: T, P, concentrations, flow rates
  * Actions: adjust setpoints, flow rates, heating/cooling
  * Reward: +yield -energy cost -deviation from setpoint
- Train PPO or TD3 agent
- Compare with conventional PID control
- Evaluate performance under disturbances
- Implement model-free adaptive control

Step 11: Economic analysis
- Calculate capital costs (CAPEX):
  * Reactor vessel cost (function of size, pressure rating)
  * Heat exchanger costs
  * Pumps and instrumentation
  * Installation costs
- Calculate operating costs (OPEX):
  * Raw materials (A, B, catalyst)
  * Utilities (steam, cooling water, electricity)
  * Labor and maintenance
- Revenue from product sales
- Calculate economic metrics:
  * Net present value (NPV)
  * Internal rate of return (IRR)
  * Payback period
  * Levelized cost of production

Step 12: Safety analysis
- Identify hazards:
  * Exothermic runaway reactions
  * Pressure buildup
  * Toxic or flammable materials
- Perform HAZOP-style analysis
- Calculate safe operating limits:
  * Maximum temperature of synthesis reaction (MTSR)
  * Adiabatic temperature rise
  * Relief valve sizing
- Design emergency shutdown systems
- Implement safety interlocks

Step 13: Uncertainty quantification
- Propagate parameter uncertainties from PyMC:
  * How does kinetic parameter uncertainty affect yield?
  * Monte Carlo simulation with parameter distributions
- Evaluate robustness of optimal design
- Calculate confidence intervals on economic metrics
- Identify critical uncertainties for further study

Step 14: Generate comprehensive engineering report
- Executive summary of project objectives and results
- Process flow diagram (PFD) with material and energy streams
- Reaction kinetics and model equations
- Parameter estimation results with uncertainties
- Optimization results:
  * Pareto front for multi-objective optimization
  * Recommended operating conditions
  * Trade-off analysis
- Dynamic simulation results (startup curves, response to disturbances)
- Control system design and tuning
- Economic analysis with sensitivity to key assumptions
- Safety analysis and hazard mitigation
- Scale-up considerations:
  * Pilot to commercial scale
  * Heat and mass transfer limitations
  * Equipment sizing
- Recommendations:
  * Optimal reactor design (size, type, materials of construction)
  * Operating conditions for maximum profitability
  * Control strategy
  * Further experimental studies needed
- Technical drawings and P&ID (piping and instrumentation diagram)
- Export as professional engineering report (PDF)

Expected Output:
- Validated reactor model with parameter uncertainties
- Optimal reactor design and operating conditions
- Pareto-optimal solutions for multi-objective optimization
- Dynamic process simulation results
- Advanced control strategies (RL-based)
- Economic feasibility analysis
- Safety assessment
- Comprehensive chemical engineering design report
```

---

## Scientific Illustration & Visual Communication

### Example 20: Creating Publication-Ready Scientific Figures

**Objective**: Generate and refine scientific illustrations, diagrams, and graphical abstracts for publications and presentations.

**Skills Used**:
- `generate-image` - AI image generation and editing
- `matplotlib` - Data visualization
- `scientific-visualization` - Best practices
- `scientific-schematics` - Scientific diagrams
- `scientific-writing` - Figure caption creation
- `scientific-slides` - Presentation materials
- `latex-posters` - Conference posters
- `pptx-posters` - PowerPoint posters
- `pdf` - PDF report generation

**Workflow**:

```bash
Step 1: Plan visual communication strategy
- Identify key concepts that need visual representation:
  * Experimental workflow diagrams
  * Molecular structures and interactions
  * Data visualization (handled by matplotlib)
  * Conceptual illustrations for mechanisms
  * Graphical abstract for paper summary
- Determine appropriate style for target journal/audience
- Sketch rough layouts for each figure

Step 2: Generate experimental workflow diagram
- Use generate-image skill with detailed prompt:
  "Scientific illustration showing a step-by-step experimental 
  workflow for CRISPR gene editing: (1) guide RNA design at computer,
  (2) cell culture in petri dish, (3) electroporation device,
  (4) selection with antibiotics, (5) sequencing validation.
  Clean, professional style with numbered steps, white background,
  suitable for scientific publication."
- Save as workflow_diagram.png
- Review and iterate on prompt if needed

Step 3: Create molecular interaction schematic
- Generate detailed molecular visualization:
  "Scientific diagram of protein-ligand binding mechanism:
  show receptor protein (blue ribbon structure) with binding pocket,
  small molecule ligand (ball-and-stick, orange) approaching,
  key hydrogen bonds indicated with dashed lines, water molecules
  in binding site. Professional biochemistry illustration style,
  clean white background, publication quality."
- Generate multiple versions with different angles/styles
- Select best representation

Step 4: Edit existing figures for consistency
- Load existing figure that needs modification:
  python scripts/generate_image.py "Change the background to white
  and make the protein blue instead of green" --input figure1.png
- Standardize color schemes across all figures
- Edit to match journal style guidelines:
  python scripts/generate_image.py "Remove the title text and
  increase contrast for print publication" --input diagram.png

Step 5: Generate graphical abstract
- Create comprehensive visual summary:
  "Graphical abstract for cancer immunotherapy paper: left side
  shows tumor cells (irregular shapes, red) being attacked by
  T cells (round, blue). Center shows the drug molecule structure.
  Right side shows healthy tissue (green). Arrow flow from left
  to right indicating treatment progression. Modern, clean style
  with minimal text, high contrast, suitable for journal TOC."
- Ensure dimensions meet journal requirements
- Iterate to highlight key findings

Step 6: Create conceptual mechanism illustrations
- Generate mechanism diagrams:
  "Scientific illustration of enzyme catalysis mechanism:
  Show substrate entering active site (step 1), transition state
  formation with electron movement arrows (step 2), product
  release (step 3). Use standard biochemistry notation,
  curved arrows for electron movement, clear labeling."
- Generate alternative representations for supplementary materials

Step 7: Produce presentation-ready figures
- Create high-impact visuals for talks:
  "Eye-catching scientific illustration of DNA double helix
  unwinding during replication, with DNA polymerase (large
  green structure) adding nucleotides. Dynamic composition,
  vibrant but professional colors, dark background for
  presentation slides."
- Adjust style for poster vs slide format
- Create versions at different resolutions

Step 8: Generate figure panels for multi-part figures
- Create consistent series of related images:
  "Panel A: Normal cell with intact membrane (green outline)
  Panel B: Cell under oxidative stress with damaged membrane
  Panel C: Cell treated with antioxidant, membrane recovering
  Consistent style across all panels, same scale, white background,
  scientific illustration style suitable for publication."
- Ensure visual consistency across panels
- Annotate with panel labels

Step 9: Edit for accessibility
- Modify figures for colorblind accessibility:
  python scripts/generate_image.py "Change the red and green
  elements to blue and orange for colorblind accessibility,
  maintain all other aspects" --input figure_v1.png
- Add patterns or textures for additional differentiation
- Verify contrast meets accessibility standards

Step 10: Create supplementary visual materials
- Generate additional context figures:
  "Anatomical diagram showing location of pancreatic islets
  within the pancreas, cross-section view with labeled structures:
  alpha cells, beta cells, blood vessels. Medical illustration
  style, educational, suitable for supplementary materials."
- Create protocol flowcharts and decision trees
- Generate equipment setup diagrams

Step 11: Compile figure legends and captions
- Use scientific-writing skill to create descriptions:
  * Figure number and title
  * Detailed description of what is shown
  * Explanation of symbols, colors, and abbreviations
  * Scale bars and measurement units
  * Statistical information if applicable
- Format according to journal guidelines

Step 12: Assemble final publication package
- Organize all figures in publication order
- Create high-resolution exports (300+ DPI for print)
- Generate both RGB (web) and CMYK (print) versions
- Compile into PDF using pdf skill:
  * Title page with graphical abstract
  * All figures with captions
  * Supplementary figures section
- Create separate folder with individual figure files
- Document all generation prompts for reproducibility

Expected Output:
- Complete set of publication-ready scientific illustrations
- Graphical abstract for table of contents
- Mechanism diagrams and workflow figures
- Edited versions meeting journal style guidelines
- Accessibility-compliant figure versions
- Figure package with captions and metadata
- Documentation of prompts used for reproducibility
```

---

## Quantum Computing for Chemistry

### Example 21: Variational Quantum Eigensolver for Molecular Ground States

**Objective**: Use quantum computing to calculate molecular electronic structure and ground state energies for drug design applications.

**Skills Used**:
- `qiskit` - IBM quantum computing framework
- `pennylane` - Quantum machine learning
- `cirq` - Google quantum circuits
- `qutip` - Quantum dynamics simulation
- `rdkit` - Molecular structure input
- `sympy` - Symbolic Hamiltonian construction
- `matplotlib` - Energy landscape visualization
- `scientific-visualization` - Publication figures
- `scientific-writing` - Quantum chemistry reports

**Workflow**:

```bash
Step 1: Define molecular system
- Load molecular structure with RDKit (small drug molecule)
- Extract atomic coordinates and nuclear charges
- Define basis set (STO-3G, 6-31G for small molecules)
- Calculate number of qubits needed (2 qubits per orbital)

Step 2: Construct molecular Hamiltonian
- Use Qiskit Nature to generate fermionic Hamiltonian
- Apply Jordan-Wigner transformation to qubit Hamiltonian
- Use SymPy to symbolically verify Hamiltonian terms
- Calculate number of Pauli terms

Step 3: Design variational ansatz with Qiskit
- Choose ansatz type: UCCSD, hardware-efficient, or custom
- Define circuit depth and entanglement structure
- Calculate circuit parameters (variational angles)
- Estimate circuit resources (gates, depth)

Step 4: Implement VQE algorithm
- Initialize variational parameters randomly
- Define cost function: <ψ(θ)|H|ψ(θ)>
- Choose classical optimizer (COBYLA, SPSA, L-BFGS-B)
- Set convergence criteria

Step 5: Run quantum simulation with PennyLane
- Configure quantum device (simulator or real hardware)
- Execute variational circuits
- Measure expectation values of Hamiltonian terms
- Update parameters iteratively

Step 6: Error mitigation
- Implement readout error mitigation
- Apply zero-noise extrapolation
- Use measurement error correction
- Estimate uncertainty in energy values

Step 7: Quantum dynamics with QuTiP
- Simulate molecular dynamics on quantum computer
- Calculate time evolution of molecular system
- Study non-adiabatic transitions
- Visualize wavefunction dynamics

Step 8: Compare with classical methods
- Run classical HF and DFT calculations for reference
- Compare VQE results with CCSD(T) (gold standard)
- Analyze quantum advantage for this system
- Quantify accuracy vs computational cost

Step 9: Scale to larger molecules
- Design circuits for larger drug candidates
- Estimate resources for pharmaceutical applications
- Identify molecules where quantum advantage is expected
- Plan for near-term quantum hardware capabilities

Step 10: Generate quantum chemistry report
- Energy convergence plots
- Circuit diagrams and ansatz visualizations
- Comparison with classical methods
- Resource estimates for target molecules
- Discussion of quantum advantage timeline
- Publication-quality figures
- Export comprehensive report

Expected Output:
- Molecular ground state energies from VQE
- Optimized variational circuits
- Comparison with classical chemistry methods
- Resource estimates for drug molecules
- Quantum chemistry analysis report
```

---

## Research Grant Writing

### Example 22: NIH R01 Grant Proposal Development

**Objective**: Develop a comprehensive research grant proposal with literature review, specific aims, and budget justification.

**Skills Used**:
- `database-lookup` - Query ClinicalTrials.gov for preliminary data context
- `paper-lookup` - Search PubMed, OpenAlex for literature and citations
- `research-grants` - Grant writing templates and guidelines
- `literature-review` - Systematic literature analysis
- `hypothesis-generation` - Scientific hypothesis development
- `scientific-writing` - Technical writing
- `scientific-critical-thinking` - Research design
- `citation-management` - Reference formatting
- `pdf` - PDF generation

**Workflow**:

```bash
Step 1: Define research question and significance
- Use hypothesis-generation skill to refine research questions
- Identify knowledge gaps in the field
- Articulate significance and innovation
- Define measurable outcomes

Step 2: Comprehensive literature review
- Search PubMed for relevant publications (last 10 years)
- Query OpenAlex for citation networks
- Identify key papers and review articles
- Use literature-review skill to synthesize findings
- Identify gaps that proposal will address

Step 3: Develop specific aims
- Aim 1: Mechanistic studies (hypothesis-driven)
- Aim 2: Translational applications
- Aim 3: Validation and clinical relevance
- Ensure aims are interdependent but not contingent
- Define success criteria for each aim

Step 4: Design research approach
- Use scientific-critical-thinking for experimental design
- Define methods for each specific aim
- Include positive and negative controls
- Plan statistical analysis approach
- Identify potential pitfalls and alternatives

Step 5: Preliminary data compilation
- Gather existing data supporting hypothesis
- Search ClinicalTrials.gov for relevant prior work
- Create figures showing preliminary results
- Quantify feasibility evidence

Step 6: Innovation and significance sections
- Articulate what is novel about approach
- Compare to existing methods/knowledge
- Explain expected impact on field
- Address NIH mission alignment

Step 7: Timeline and milestones
- Create Gantt chart for 5-year project
- Define quarterly milestones
- Identify go/no-go decision points
- Plan for personnel and resource allocation

Step 8: Budget development
- Calculate personnel costs (PI, postdocs, students)
- Equipment and supplies estimates
- Core facility usage costs
- Travel and publication costs
- Indirect cost calculation

Step 9: Rigor and reproducibility
- Address biological variables (sex, age, strain)
- Statistical power calculations
- Data management and sharing plan
- Authentication of key resources

Step 10: Format and compile
- Use research-grants templates for NIH format
- Apply citation-management for references
- Create biosketch and facilities sections
- Generate PDF with proper formatting
- Check page limits and formatting requirements

Step 11: Review and revision
- Use peer-review skill principles for self-assessment
- Check for logical flow and clarity
- Verify alignment with FOA requirements
- Ensure responsive to review criteria

Step 12: Final deliverables
- Specific Aims page (1 page)
- Research Strategy (12 pages)
- Bibliography
- Budget and justification
- Biosketches
- Letters of support
- Data management plan
- Human subjects/vertebrate animals sections (if applicable)

Expected Output:
- Complete NIH R01 grant proposal
- Literature review summary
- Budget spreadsheet with justification
- Timeline and milestone chart
- All required supplementary documents
- Properly formatted PDF ready for submission
```

---

## Flow Cytometry & Immunophenotyping

### Example 23: Multi-Parameter Flow Cytometry Analysis Pipeline

**Objective**: Analyze high-dimensional flow cytometry data to characterize immune cell populations in clinical samples.

**Skills Used**:
- `flowio` - FCS file parsing
- `scanpy` - High-dimensional analysis
- `scikit-learn` - Clustering and classification
- `umap-learn` - Dimensionality reduction
- `statistical-analysis` - Population statistics
- `matplotlib` - Flow cytometry plots
- `scientific-visualization` - Publication-quality & interactive visualization
- `clinical-reports` - Clinical flow reports
- `exploratory-data-analysis` - Data exploration

**Workflow**:

```bash
Step 1: Load and parse FCS files
- Use flowio to read FCS 3.0/3.1 files
- Extract channel names and metadata
- Load compensation matrix from file
- Parse keywords (patient ID, tube, date)

Step 2: Quality control
- Check for acquisition anomalies (time vs events)
- Identify clogging or fluidics issues
- Remove doublets (FSC-A vs FSC-H)
- Gate viable cells (exclude debris)
- Document QC metrics per sample

Step 3: Compensation and transformation
- Apply compensation matrix
- Transform data (biexponential/logicle)
- Verify compensation with single-stain controls
- Visualize spillover reduction

Step 4: Traditional gating strategy
- Sequential manual gating approach:
  * Lymphocytes (FSC vs SSC)
  * Single cells (FSC-A vs FSC-H)
  * Live cells (viability dye negative)
  * CD3+ T cells, CD19+ B cells, etc.
- Calculate population frequencies
- Export gated populations

Step 5: High-dimensional analysis with Scanpy
- Convert flow data to AnnData format
- Apply variance-stabilizing transformation
- Calculate highly variable markers
- Build neighbor graph

Step 6: Dimensionality reduction
- Run UMAP with umap-learn for visualization
- Optimize UMAP parameters (n_neighbors, min_dist)
- Create 2D embeddings colored by:
  * Marker expression
  * Sample/patient
  * Clinical group

Step 7: Automated clustering
- Apply Leiden or FlowSOM clustering
- Determine optimal cluster resolution
- Assign cell type labels based on marker profiles
- Validate clusters against manual gating

Step 8: Differential abundance analysis
- Compare population frequencies between groups
- Use statistical-analysis for hypothesis testing
- Calculate fold changes and p-values
- Apply multiple testing correction
- Identify significantly altered populations

Step 9: Biomarker discovery
- Train classifiers to predict clinical outcome
- Use scikit-learn Random Forest or SVM
- Calculate feature importance (which populations matter)
- Cross-validate prediction accuracy
- Identify candidate biomarkers

Step 10: Quality metrics and batch effects
- Calculate CV for control samples
- Detect batch effects across acquisition dates
- Apply batch correction if needed
- Generate Levey-Jennings plots for QC

Step 11: Visualization suite
- Traditional flow plots:
  * Bivariate dot plots with quadrant gates
  * Histogram overlays
  * Contour plots
- High-dimensional plots:
  * UMAP colored by population
  * Heatmaps of marker expression
  * Violin plots for marker distributions
- Interactive plots with Plotly

Step 12: Generate clinical flow cytometry report
- Sample information and QC summary
- Gating strategy diagrams
- Population frequency tables
- Reference range comparisons
- Statistical comparisons between groups
- Interpretation and clinical significance
- Export as PDF for clinical review

Expected Output:
- Parsed and compensated flow cytometry data
- Traditional and automated gating results
- High-dimensional clustering and UMAP
- Differential abundance statistics
- Biomarker candidates for clinical outcome
- Publication-quality flow plots
- Clinical flow cytometry report
```

---

## Geospatial & Earth Observation

### Example 24: Remote Sensing for Environmental Monitoring

**Objective**: Combine satellite imagery and vector data to map land-cover change and quantify environmental drivers across a watershed.

**Skills Used**:
- `geomaster` - Remote sensing, GIS, and earth-observation workflows
- `geopandas` - Vector data (shapefiles, GeoJSON) and spatial joins
- `zarr-python` - Chunked N-D arrays for large raster/time stacks
- `dask` - Parallel/out-of-core processing of image cubes
- `scikit-learn` - Land-cover classification
- `statistical-analysis` - Trend and correlation testing
- `matplotlib` - Mapping and charts
- `scientific-visualization` - Publication-quality & interactive visualization

**Workflow**:

```bash
Step 1: Acquire and stack imagery
- Use geomaster to pull Sentinel-2/Landsat scenes for the area and time range
- Compute spectral indices (NDVI, NDWI, NBR) per scene
- Store the multi-date raster cube as a chunked Zarr array (zarr-python)

Step 2: Prepare vector layers with GeoPandas
- Load watershed boundaries, land parcels, and road networks
- Reproject all layers to a common CRS
- Clip rasters to the area of interest and rasterize key vector masks

Step 3: Scale processing with Dask
- Lazily load the Zarr cube as Dask arrays
- Map index calculations and cloud masking across chunks in parallel

Step 4: Land-cover classification
- Sample labeled training pixels (forest, cropland, water, urban)
- Train a Random Forest classifier with scikit-learn on spectral + index features
- Produce per-date land-cover maps and accuracy metrics (confusion matrix, kappa)

Step 5: Change detection and zonal statistics
- Compute land-cover transitions between years
- Use GeoPandas zonal stats to summarize change per sub-catchment
- Correlate change with covariates (slope, precipitation) via statistical-analysis

Step 6: Generate report
- Time-series maps, change matrices, and trend plots
- Per-zone summary tables and interpretation
- Export publication-quality figures and a PDF report

Expected Output:
- Analysis-ready Zarr raster cube and classified land-cover maps
- Quantified land-cover change with per-zone statistics
- Environmental driver analysis and geospatial report
```

---

## Time-Series Forecasting & Sensor Analytics

### Example 25: Forecasting Clinical Vitals and Wearable Sensor Streams

**Objective**: Forecast physiological time series and detect anomalies from wearable/ICU sensor data to support early-warning systems.

**Skills Used**:
- `timesfm-forecasting` - Zero-shot foundation-model forecasting
- `aeon` - Time-series classification, clustering, and anomaly detection
- `neurokit2` - Physiological signal processing (ECG, PPG, EDA)
- `pyhealth` - Healthcare ML models and clinical pipelines
- `statistical-analysis` - Evaluation and hypothesis testing
- `matplotlib` - Visualization

**Workflow**:

```bash
Step 1: Ingest and clean signals
- Load multi-channel sensor streams (heart rate, SpO2, ECG, activity)
- Use NeuroKit2 to clean ECG/PPG, detect R-peaks, and derive HRV features
- Resample to a common cadence and handle gaps/outliers

Step 2: Feature extraction and segmentation with aeon
- Extract time-series features and segment into windows
- Cluster typical vs atypical patterns
- Flag anomalous windows with aeon anomaly detectors

Step 3: Zero-shot forecasting with TimesFM
- Forecast each vital sign ahead (e.g., next 30-60 min) with timesfm-forecasting
- Produce point forecasts and quantile/uncertainty bands
- No per-series training required (foundation model)

Step 4: Clinical risk modeling with PyHealth
- Build a deterioration/early-warning model from forecasts + EHR features
- Evaluate with appropriate clinical metrics (AUROC, AUPRC, calibration)

Step 5: Statistical evaluation
- Backtest forecasts (MAE, MASE, coverage) with statistical-analysis
- Compare TimesFM vs aeon baselines and test for significant differences

Step 6: Generate monitoring report
- Forecast vs actual overlays with uncertainty bands
- Anomaly timelines and alert thresholds
- Model performance summary and deployment recommendations

Expected Output:
- Cleaned, feature-rich physiological time series
- Multi-horizon forecasts with uncertainty
- Anomaly detection and early-warning model with validation
```

---

## Cloud-Scale Bioinformatics

### Example 26: Reproducible, Cloud-Scale Genomics Pipelines

**Objective**: Run a reproducible tumor-normal and bulk RNA-seq analysis at population scale across cloud platforms, with lineage tracking and efficient variant storage.

**Skills Used**:
- `get-available-resources` - Detect CPU/GPU/memory and plan execution
- `bulk-rnaseq` - End-to-end bulk RNA-seq orchestration
- `nextflow` - Build/run Nextflow & nf-core pipelines
- `pacsomatic` - nf-core/pacsomatic matched tumor-normal workflow
- `dnanexus-integration` - DNAnexus cloud execution and data management
- `latchbio-integration` - LatchBio SDK workflows and deployment
- `modal` - Serverless GPU/CPU compute for custom steps
- `optimize-for-gpu` - GPU-accelerate alignment/quantification steps
- `tiledbvcf` - Scalable VCF ingestion and querying
- `polars-bio` - Fast genomic interval operations
- `gtars` - High-performance genomic interval/BED analysis
- `lamindb` - Dataset registration and lineage tracking
- `pydeseq2` - Differential expression
- `pathway-enrichment` - Downstream gene-set enrichment

**Workflow**:

```bash
Step 1: Plan resources
- Run get-available-resources to detect cores/GPUs/RAM/disk
- Choose local vs cloud execution and parallelism strategy

Step 2: RNA-seq quantification
- Use the bulk-rnaseq skill to take FASTQ -> QC (FastQC/fastp) -> STAR/Salmon -> counts
- Register raw inputs and outputs in LaminDB for lineage

Step 3: Somatic variant calling at scale
- Prepare a pacsomatic-compliant samplesheet for matched tumor-normal BAMs
- Launch the nf-core/pacsomatic Nextflow workflow
- Offload heavy steps to DNAnexus or LatchBio; use Modal for custom GPU steps
- Apply optimize-for-gpu to accelerate alignment/variant steps where supported

Step 4: Variant storage and interval analysis
- Ingest resulting VCFs into a TileDB-VCF store for incremental, queryable storage
- Use polars-bio and gtars for overlaps, coverage, and region annotation

Step 5: Differential expression and enrichment
- Run PyDESeq2 on the counts matrix (tumor vs normal / subtype contrasts)
- Pass ranked/DE gene lists to the pathway-enrichment skill

Step 6: Track lineage and report
- Record every artifact, transform, and parameter set in LaminDB
- Export a reproducible pipeline report with provenance graph

Expected Output:
- Reproducible, cloud-portable RNA-seq + somatic pipelines
- Queryable TileDB-VCF variant store
- DE + pathway results with full data lineage
```

---

## Functional Genomics & Knowledge Graphs

### Example 27: Cancer Dependency Mapping and Knowledge-Graph Target Discovery

**Objective**: Identify cancer-specific vulnerabilities and synthetic-lethal targets by combining dependency screens with biomedical knowledge graphs.

**Skills Used**:
- `depmap` - DepMap CRISPR dependency, drug sensitivity, gene-effect data
- `primekg` - Precision Medicine Knowledge Graph queries
- `database-lookup` - Cross-reference Open Targets, DrugBank, COSMIC
- `networkx` - Graph analysis over knowledge subnetworks
- `pathway-enrichment` - Enrichment of dependency hit sets
- `what-if-oracle` - Structured scenario analysis of target hypotheses
- `scikit-learn` - Predictive modeling of dependency
- `scientific-visualization` - Publication-quality & interactive visualization

**Workflow**:

```bash
Step 1: Pull dependency profiles
- Query DepMap for gene-effect (CRISPR Chronos) scores across cell lines
- Filter for strong, selective dependencies in the lineage of interest
- Retrieve drug-sensitivity profiles for candidate vulnerabilities

Step 2: Define context and synthetic lethality
- Stratify cell lines by mutation/expression context
- Identify genes essential only in a given context (synthetic-lethal candidates)

Step 3: Knowledge-graph expansion with PrimeKG
- For each candidate, query PrimeKG for connected genes, drugs, diseases, phenotypes
- Extract relevant subgraphs and analyze with NetworkX (centrality, shortest paths)
- Cross-reference with Open Targets/DrugBank via database-lookup

Step 4: Enrichment and mechanism
- Run pathway-enrichment on the dependency hit set
- Map hits to pathways and protein complexes for mechanistic hypotheses

Step 5: Predictive modeling
- Train scikit-learn models predicting dependency from omics features
- Identify biomarkers of vulnerability and validate via cross-validation

Step 6: Scenario analysis and prioritization
- Use what-if-oracle to explore best/likely/worst-case target hypotheses
  (resistance, toxicity, tractability, competition)
- Rank targets by selectivity, druggability, and KG support

Step 7: Report
- Dependency heatmaps, KG subnetwork diagrams, enrichment plots
- Prioritized target list with supporting evidence and risks

Expected Output:
- Context-specific dependency and synthetic-lethal candidates
- Knowledge-graph-supported mechanisms and drug links
- Prioritized, de-risked target list with visualizations
```

---

## Molecular Modeling & Simulation

### Example 28: Molecular Dynamics and Binding Free Energy for Lead Optimization

**Objective**: Refine a protein-ligand complex with molecular dynamics and estimate binding affinity to guide lead optimization.

**Skills Used**:
- `molecular-dynamics` - OpenMM/MDAnalysis simulation and trajectory analysis
- `rowan` - Cloud molecular modeling (pKa, conformers, docking, cofolding)
- `rdkit` - Ligand preparation and cheminformatics
- `biopython` - Protein structure handling
- `optimize-for-gpu` - GPU acceleration of MD and analysis
- `matplotlib` - Plots
- `scientific-visualization` - Publication-quality & interactive visualization

**Workflow**:

```bash
Step 1: Prepare structures
- Load the protein with BioPython; clean, protonate, and assign chains
- Prepare ligand 3D conformers/tautomers and protonation states with RDKit
- Use rowan for pKa/macropKa and conformer/tautomer ensembles, and to refine
  docked or cofolded protein-ligand poses

Step 2: System setup (molecular-dynamics skill)
- Define force field, solvate, add ions, and parameterize the ligand
- Energy minimize, then equilibrate (NVT, NPT)

Step 3: Production MD
- Run production simulations on GPU (optimize-for-gpu)
- Save trajectories for multiple replicas

Step 4: Trajectory analysis
- Compute RMSD/RMSF, contact maps, H-bond occupancy, and pocket stability
- Identify key interactions and conformational changes

Step 5: Binding free energy
- Estimate relative/absolute binding free energies (MM-GBSA / alchemical methods)
- Rank analogs by predicted affinity and stability

Step 6: Report
- Trajectory plots, interaction fingerprints, and free-energy rankings
- Recommendations for the next round of analogs

Expected Output:
- Equilibrated protein-ligand MD trajectories
- Interaction and stability analysis
- Binding free-energy rankings to guide optimization
```

---

## Protein Engineering & Cloud Wet-Lab

### Example 29: Designing and Validating an Engineered Binder

**Objective**: Design a protein binder, engineer its glycosylation and stability, and validate candidates through cloud wet-lab assays.

**Skills Used**:
- `esm` - Protein language model embeddings and variant scoring
- `hugging-science` - Scientific ML models for design/screening
- `phylogenetics` - Homolog alignment and evolutionary context
- `glycoengineering` - N/O-glycosylation analysis and engineering
- `biopython` - Sequence/structure manipulation
- `adaptyv` - Adaptyv Bio Foundry protein binding assays
- `ginkgo-cloud-lab` - Ginkgo Cloud Lab protocol execution

**Workflow**:

```bash
Step 1: Establish evolutionary context
- Collect homologs and build an alignment/tree with the phylogenetics skill
- Identify conserved and variable positions to guide design

Step 2: Generate and score variants
- Use ESM embeddings and variant effect scores to propose stabilizing/affinity mutations
- Screen designs with hugging-science models (structure/function predictors)
- Manipulate sequences and models with BioPython

Step 3: Glycoengineering
- Scan for N-glycosylation sequons (N-X-S/T) and predict O-glyco hotspots
- Add/remove sequons to tune stability, half-life, or immunogenicity (glycoengineering)

Step 4: Submit binding assays to Adaptyv
- Design a protein binding experiment and submit via the Adaptyv Foundry API
- Retrieve and parse measured affinities/binding results

Step 5: Cloud wet-lab expression with Ginkgo
- Submit cell-free expression / validation protocols to Ginkgo Cloud Lab
- Track RAC execution and collect results

Step 6: Iterate and report
- Correlate predicted vs measured performance; pick the next design round
- Report designs, glyco profiles, and assay results

Expected Output:
- Ranked, evolution- and ML-informed binder designs
- Engineered glycosylation profiles
- Experimental binding/expression results from Adaptyv and Ginkgo
```

---

## Medical Imaging & Clinical AI

### Example 30: AI-Assisted Radiology on Public Imaging Cohorts

**Objective**: Train and interpret a deep learning model on public cancer imaging data and generate a clinically oriented summary.

**Skills Used**:
- `imaging-data-commons` - Query/download NCI Imaging Data Commons (CT/MR/PET)
- `pydicom` - DICOM parsing and handling
- `hugging-science` - Pretrained medical imaging models
- `pytorch-lightning` - Model training
- `optimize-for-gpu` - GPU acceleration
- `shap` - Interpretability
- `clinical-decision-support` - Evidence-based decision support
- `treatment-plans` - Generate structured treatment plan documents

**Workflow**:

```bash
Step 1: Acquire imaging cohort
- Use idc-index via the imaging-data-commons skill to query CT/MR/PET by modality,
  collection, and metadata (no authentication required)
- Download and organize series for the task

Step 2: Load and preprocess DICOM
- Parse pixel data and metadata with pydicom
- Resample, window, and normalize; build train/val/test splits

Step 3: Model training
- Start from a hugging-science pretrained medical imaging backbone
- Fine-tune with PyTorch Lightning; accelerate with optimize-for-gpu
- Track metrics (AUC, Dice/IoU for segmentation)

Step 4: Evaluation and interpretability
- Evaluate on the held-out set with confidence intervals
- Use SHAP/saliency to explain predictions and verify clinically relevant focus

Step 5: Clinical synthesis
- Map model findings to guidance with clinical-decision-support
- Generate a concise treatment plan document with the treatment-plans skill

Step 6: Report
- Performance metrics, example predictions with heatmaps
- Interpretability summary and clinical caveats

Expected Output:
- Trained, interpreted imaging model on IDC data
- Decision-support mapping and a structured treatment plan
- Validation report with explainability
```

---

## Research Ideation & Study Planning

### Example 31: From Idea to a Powered, Well-Designed Study

**Objective**: Move from open-ended ideation to concrete, testable hypotheses and a statistically powered, well-designed study.

**Skills Used**:
- `scientific-brainstorming` - Open-ended ideation and gap-finding
- `consciousness-council` - Multi-perspective deliberation on directions
- `what-if-oracle` - Structured scenario/branch analysis
- `hypothesis-generation` - Formalize testable hypotheses
- `hypogenic` - Data-driven hypothesis generation on tabular data
- `experimental-design` - Choose design, randomization, and blocking
- `statistical-power` - Sample size, MDE, and power curves

**Workflow**:

```bash
Step 1: Diverge — generate ideas
- Use scientific-brainstorming to explore the problem space and interdisciplinary links
- Run a consciousness-council deliberation to weigh competing research directions

Step 2: Stress-test directions
- Use what-if-oracle to explore best/likely/worst/contrarian scenarios for top ideas
- Eliminate fragile or untestable directions

Step 3: Formalize hypotheses
- Convert the chosen direction into testable hypotheses with hypothesis-generation
- If pilot/tabular data exist, use hypogenic to mine and rank candidate hypotheses

Step 4: Design the study
- Use experimental-design to select a design (factorial, RCT, block, crossover),
  define randomization, blocking, and treatment combinations

Step 5: Power and sample size
- Use statistical-power for a priori power analysis, minimum detectable effect,
  and power curves across plausible effect sizes

Step 6: Deliverable
- A pre-registration-ready plan: hypotheses, design diagram, analysis plan, and
  justified sample size

Expected Output:
- A prioritized set of testable hypotheses
- A concrete experimental design with randomization/blocking
- Power analysis and sample-size justification
```

---

## Literature & Knowledge Management

### Example 32: Systematic Literature Review and Research Knowledge Base

**Objective**: Run a multi-source literature search, ingest and organize sources, and synthesize a cited, well-managed review.

**Skills Used**:
- `research-lookup` - Routed current-research search (web/deep/academic)
- `exa-search` - Semantic web search tuned for technical content
- `parallel-web` - Academic-focused web search/fetch and enrichment
- `bgpt-paper-search` - Structured experimental data extracted from papers
- `paperzilla` - Canonical papers and project recommendations
- `liteparse` - Local PDF/Office parsing with layout/bounding boxes
- `markitdown` - Convert documents to Markdown
- `open-notebook` - Organize sources into AI research notebooks
- `pyzotero` - Manage a Zotero reference library
- `scholar-evaluation` - ScholarEval structured quality assessment
- `dhdna-profiler` - Profile authors'/reviewers' thinking patterns
- `citation-management` - Reference formatting
- `literature-review` - Systematic synthesis

**Workflow**:

```bash
Step 1: Multi-source search
- Use research-lookup to route queries; broaden with exa-search and parallel-web
- Pull structured study fields (sample sizes, methods, outcomes) via bgpt-paper-search
- Surface canonical references and recommendations with paperzilla

Step 2: Ingest and normalize sources
- Parse local PDFs/Office files with liteparse (layout + bounding boxes)
- Convert mixed documents to clean Markdown with markitdown
- Organize everything into an open-notebook research notebook

Step 3: Reference management
- Store and de-duplicate references in Zotero via pyzotero
- Tag by theme, method, and evidence level

Step 4: Critical appraisal
- Use scholar-evaluation (ScholarEval) to score methodology, analysis, and writing
- Optionally profile argumentation/thinking style with dhdna-profiler

Step 5: Synthesize
- Use the literature-review skill to synthesize themes, gaps, and consensus/conflicts
- Format citations with citation-management

Step 6: Deliverable
- A cited systematic review with evidence tables and a managed reference library

Expected Output:
- Comprehensive multi-source search results
- Organized, parsed, and reference-managed corpus
- Appraised, synthesized, fully cited literature review
```

---

## Regulatory & Quality Management

### Example 33: ISO 13485 Documentation for an AI Diagnostic Device

**Objective**: Prepare a Quality Management System documentation package for a medical-device software product.

**Skills Used**:
- `iso-13485-certification` - Gap analysis and QMS documentation
- `clinical-decision-support` - Clinical evidence and intended-use framing
- `treatment-plans` - Care-pathway documentation where applicable
- `markdown-mermaid-writing` - Process diagrams and SOP flowcharts
- `docx` - Formatted Word deliverables
- `pdf` - Final controlled documents

**Workflow**:

```bash
Step 1: Gap analysis
- Use the iso-13485-certification skill to assess existing documentation vs the standard
- Identify missing procedures, records, and controls

Step 2: Define scope and intended use
- Frame intended use and clinical claims with clinical-decision-support inputs
- Document care pathways/treatment context with treatment-plans where relevant

Step 3: Author QMS documents
- Draft required SOPs, work instructions, and quality manual sections
- Diagram processes (design controls, CAPA, risk management) with markdown-mermaid-writing

Step 4: Produce controlled deliverables
- Export procedures and the quality manual to DOCX
- Generate signed, version-controlled PDFs

Step 5: Traceability
- Build a requirements/records traceability matrix
- Map each clause to its evidence

Expected Output:
- Gap-analysis report against ISO 13485
- Complete QMS document set (SOPs, manual, diagrams)
- Controlled DOCX/PDF deliverables with traceability
```

---

## Scientific Communication & Tooling

### Example 34: Publication Packaging — Diagrams, Infographics, and Venue Formatting

**Objective**: Turn results into a venue-ready manuscript package with diagrams, an infographic summary, and correct formatting.

**Skills Used**:
- `markdown-mermaid-writing` - Text-based diagrams and structured docs
- `scientific-schematics` - Scientific diagrams
- `infographics` - AI-generated infographics with data accuracy checks
- `venue-templates` - LaTeX templates and submission guidelines
- `markitdown` - Convert drafts/sources to Markdown
- `docx` - Word manuscript output
- `latex-posters` - Conference poster
- `pdf` - Final compiled outputs

**Workflow**:

```bash
Step 1: Structure the manuscript
- Draft the document in Markdown; add Mermaid flowcharts/diagrams (markdown-mermaid-writing)
- Convert existing source materials to Markdown with markitdown

Step 2: Build figures and schematics
- Create mechanism/workflow schematics with scientific-schematics
- Produce a one-page infographic summary with the infographics skill (verified data)

Step 3: Apply venue formatting
- Use venue-templates to select the correct LaTeX template and follow submission rules
  (Nature/Science/PLOS/IEEE/ACM or a target conference)

Step 4: Generate outputs
- Compile the manuscript to PDF and a DOCX version for collaborators
- Build a conference poster with latex-posters

Step 5: Final check
- Verify formatting, figure resolution, and reference style against venue requirements

Expected Output:
- Venue-formatted manuscript (PDF + DOCX)
- Diagrams, schematics, and an infographic summary
- A matching conference poster
```

---

### Example 35: Building and Automating Custom Scientific Tools

**Objective**: Detect repeated research workflows, draft new automation, and deploy compute-heavy steps to the cloud.

**Skills Used**:
- `autoskill` - Detect repeated workflows and draft new skills/recipes
- `pi-agent` - Build/use the Pi terminal coding harness and skills/extensions
- `get-available-resources` - Detect local CPU/GPU/memory
- `optimize-for-gpu` - GPU-accelerate Python (CuPy/Numba/cuDF/cuML, etc.)
- `modal` - Serverless on-demand GPU/CPU deployment
- `hugging-science` - Scientific ML models to wrap as tools

**Workflow**:

```bash
Step 1: Discover repeated workflows
- Use autoskill to observe recurring research steps and match them to existing skills
- Draft new skills or composition recipes for gaps

Step 2: Prototype a custom tool
- Build the tool/harness with pi-agent (Pi skills, extensions, or SDK embedding)
- Wrap a relevant hugging-science model as a callable component

Step 3: Profile and accelerate
- Run get-available-resources to size the job
- Apply optimize-for-gpu to accelerate the hot numerical paths

Step 4: Deploy to the cloud
- Package the workload on Modal for on-demand GPU/CPU execution
- Expose it as a scheduled job or web endpoint

Step 5: Document
- Document the new skill/recipe and usage for the team

Expected Output:
- New drafted skills/composition recipes for recurring work
- A deployed, GPU-accelerated custom tool on Modal
- Documentation for reuse

---

## Summary

These examples demonstrate:

1. **Cross-domain applicability**: Skills are useful across many scientific fields
2. **Skill integration**: Complex workflows combine multiple databases, packages, and analysis methods
3. **Real-world relevance**: Examples address actual research questions and clinical needs
4. **End-to-end workflows**: From data acquisition to publication-ready reports
5. **Best practices**: QC, statistical rigor, visualization, interpretation, and documentation

### Skills Coverage Summary

The examples in this document cover the following skill categories:

**Databases & Data Sources:**
- `database-lookup` — unified access to 78+ databases including ChEMBL, PubChem, DrugBank, UniProt, NCBI Gene, Ensembl, ClinVar, COSMIC, STRING, KEGG, Reactome, HMDB, PDB, AlphaFold DB, ZINC, GWAS Catalog, GEO, ENA, ClinicalTrials.gov, FDA, Open Targets, ClinPGx, Metabolomics Workbench, and more
- `paper-lookup` — unified access to 10 academic paper databases including PubMed, PMC, bioRxiv, medRxiv, arXiv, OpenAlex, Crossref, Semantic Scholar, CORE, Unpaywall
- `cellxgene-census` — CZ CELLxGENE single-cell reference data
- `depmap` — Cancer Dependency Map (CRISPR/drug sensitivity)
- `primekg` — Precision Medicine Knowledge Graph
- `imaging-data-commons` — NCI Imaging Data Commons (CT/MR/PET)
- `usfiscaldata` — U.S. Treasury Fiscal Data API

**Analysis Packages:**
- Chemistry & Modeling: `rdkit`, `datamol`, `medchem`, `molfeat`, `deepchem`, `torchdrug`, `pytdc`, `diffdock`, `pyopenms`, `matchms`, `cobrapy`, `rowan`, `molecular-dynamics`
- Genomics: `biopython`, `pysam`, `pydeseq2`, `bulk-rnaseq`, `scanpy`, `scvelo`, `scvi-tools`, `anndata`, `gget`, `geniml`, `deeptools`, `etetoolkit`, `phylogenetics`, `scikit-bio`, `gtars`, `polars-bio`, `tiledbvcf`, `pathway-enrichment`, `lamindb`
- Proteins & Engineering: `esm`, `bioservices`, `glycoengineering`, `adaptyv`
- Machine Learning: `scikit-learn`, `pytorch-lightning`, `torch-geometric`, `transformers`, `stable-baselines3`, `pufferlib`, `shap`, `hugging-science`, `hypogenic`
- Statistics & Design: `statsmodels`, `statistical-analysis`, `pymc`, `scikit-survival`, `statistical-power`, `experimental-design`
- Time Series: `aeon`, `timesfm-forecasting`
- Visualization: `matplotlib`, `seaborn`, `scientific-visualization`
- Data Processing: `polars`, `dask`, `vaex`, `networkx`, `zarr-python`
- Geospatial: `geomaster`, `geopandas`
- Materials: `pymatgen`
- Physics & Math: `astropy`, `sympy`, `fluidsim`, `matlab`
- Quantum: `qiskit`, `pennylane`, `cirq`, `qutip`
- Neuroscience: `neurokit2`, `neuropixels-analysis`, `bids`
- Pathology & Imaging: `histolab`, `pathml`, `pydicom`
- Flow Cytometry: `flowio`
- Dimensionality Reduction: `umap-learn`, `arboreto`
- Lab Automation & Cloud Labs: `pylabrobot`, `opentrons-integration`, `benchling-integration`, `labarchive-integration`, `protocolsio-integration`, `ginkgo-cloud-lab`
- Simulation & Optimization: `simpy`, `pymoo`
- Compute & Pipelines: `get-available-resources`, `optimize-for-gpu`, `modal`, `nextflow`, `pacsomatic`, `dnanexus-integration`, `latchbio-integration`

**Ideation, Search & Knowledge:**
- `scientific-brainstorming`, `consciousness-council`, `hypothesis-generation`, `what-if-oracle`
- `research-lookup`, `exa-search`, `parallel-web`, `bgpt-paper-search`, `paperzilla`
- `liteparse`, `markitdown`, `open-notebook`, `pyzotero`, `scholar-evaluation`, `dhdna-profiler`

**Writing & Reporting:**
- `scientific-writing`, `scientific-visualization`, `scientific-schematics`, `scientific-slides`, `markdown-mermaid-writing`, `infographics`
- `clinical-reports`, `clinical-decision-support`, `treatment-plans`
- `literature-review`, `scientific-critical-thinking`
- `research-grants`, `peer-review`, `venue-templates`, `iso-13485-certification`
- `pdf`, `docx`, `pptx`, `xlsx`, `latex-posters`, `pptx-posters`
- `citation-management`, `market-research-reports`

**Image, Media & Tooling:**
- `generate-image`, `omero-integration`
- `autoskill`, `pi-agent`

### How to Use These Examples

1. **Adapt to your needs**: Modify parameters, datasets, and objectives for your specific research question
2. **Combine skills creatively**: Mix and match skills from different categories
3. **Follow the structure**: Each example provides a clear step-by-step workflow
4. **Generate comprehensive output**: Aim for publication-quality figures and professional reports
5. **Cite your sources**: Always verify data and provide proper citations

### Additional Notes

- Always start with: "Always use available 'skills' when possible. Keep the output organized."
- For complex projects, break into manageable steps and validate intermediate results
- Save checkpoints and intermediate data files
- Document parameters and decisions for reproducibility
- Generate README files explaining methodology
- Create PDFs for stakeholder communication

These examples showcase the power of combining the skills in this repository to tackle complex, real-world scientific challenges across multiple domains.

