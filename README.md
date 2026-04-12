# Scientific Agent Skills

> **🔔 Claude Scientific Skills is now Scientific Agent Skills.** Same skills, broader compatibility — now works with any AI agent that supports the open [Agent Skills](https://agentskills.io/) standard, not just Claude.

> **New: [K-Dense BYOK](https://github.com/K-Dense-AI/k-dense-byok)** — A free, open-source AI co-scientist that runs on your desktop, powered by Scientific Agent Skills. Bring your own API keys, pick from 40+ models, and get a full research workspace with web search, file handling, 100+ scientific databases, and access to all 133 skills in this repo. Your data stays on your computer, and you can optionally scale to cloud compute via [Modal](https://modal.com/) for heavy workloads. [Get started here.](https://github.com/K-Dense-AI/k-dense-byok)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.md)
[![Skills](https://img.shields.io/badge/Skills-133-brightgreen.svg)](#whats-included)
[![Databases](https://img.shields.io/badge/Databases-100%2B-orange.svg)](#whats-included)
[![Agent Skills](https://img.shields.io/badge/Standard-Agent_Skills-blueviolet.svg)](https://agentskills.io/)
[![Works with](https://img.shields.io/badge/Works_with-Cursor_|_Claude_Code_|_Codex-blue.svg)](#getting-started)
[![X](https://img.shields.io/badge/Follow_on_X-%40k__dense__ai-000000?logo=x)](https://x.com/k_dense_ai)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-K--Dense_Inc.-0A66C2?logo=linkedin)](https://www.linkedin.com/company/k-dense-inc)
[![YouTube](https://img.shields.io/badge/YouTube-K--Dense_Inc.-FF0000?logo=youtube)](https://www.youtube.com/@K-Dense-Inc)

A comprehensive collection of **133 ready-to-use scientific and research skills** (covering cancer genomics, drug-target binding, molecular dynamics, RNA velocity, geospatial science, time series forecasting, 78+ scientific databases, and more) for any AI agent that supports the open [Agent Skills](https://agentskills.io/) standard, created by [K-Dense](https://k-dense.ai). Works with **Cursor, Claude Code, Codex, and more**. Transform your AI agent into a research assistant capable of executing complex multi-step scientific workflows across biology, chemistry, medicine, and beyond.

---

These skills enable your AI agent to seamlessly work with specialized scientific libraries, databases, and tools across multiple scientific domains. While the agent can use any Python package or API on its own, these explicitly defined skills provide curated documentation and examples that make it significantly stronger and more reliable for the workflows below:
- 🧬 Bioinformatics & Genomics - Sequence analysis, single-cell RNA-seq, gene regulatory networks, variant annotation, phylogenetic analysis
- 🧪 Cheminformatics & Drug Discovery - Molecular property prediction, virtual screening, ADMET analysis, molecular docking, lead optimization
- 🔬 Proteomics & Mass Spectrometry - LC-MS/MS processing, peptide identification, spectral matching, protein quantification
- 🏥 Clinical Research & Precision Medicine - Clinical trials, pharmacogenomics, variant interpretation, drug safety, clinical decision support, treatment planning
- 🧠 Healthcare AI & Clinical ML - EHR analysis, physiological signal processing, medical imaging, clinical prediction models
- 🖼️ Medical Imaging & Digital Pathology - DICOM processing, whole slide image analysis, computational pathology, radiology workflows
- 🤖 Machine Learning & AI - Deep learning, reinforcement learning, time series analysis, model interpretability, Bayesian methods
- 🔮 Materials Science & Chemistry - Crystal structure analysis, phase diagrams, metabolic modeling, computational chemistry
- 🌌 Physics & Astronomy - Astronomical data analysis, coordinate transformations, cosmological calculations, symbolic mathematics, physics computations
- ⚙️ Engineering & Simulation - Discrete-event simulation, multi-objective optimization, metabolic engineering, systems modeling, process optimization
- 📊 Data Analysis & Visualization - Statistical analysis, network analysis, time series, publication-quality figures, large-scale data processing, EDA
- 🌍 Geospatial Science & Remote Sensing - Satellite imagery processing, GIS analysis, spatial statistics, terrain analysis, machine learning for Earth observation
- 🧪 Laboratory Automation - Liquid handling protocols, lab equipment control, workflow automation, LIMS integration
- 📚 Scientific Communication - Literature review, peer review, scientific writing, document processing, posters, slides, schematics, citation management
- 🔬 Multi-omics & Systems Biology - Multi-modal data integration, pathway analysis, network biology, systems-level insights
- 🧬 Protein Engineering & Design - Protein language models, structure prediction, sequence design, function annotation
- 🎓 Research Methodology - Hypothesis generation, scientific brainstorming, critical thinking, grant writing, scholar evaluation

**Transform your AI coding agent into an 'AI Scientist' on your desktop!**

> ⭐ **If you find this repository useful**, please consider giving it a star! It helps others discover these tools and encourages us to continue maintaining and expanding this collection.

> 🎬 **New to Scientific Agent Skills?** Watch our [Getting Started with Scientific Agent Skills](https://youtu.be/ZxbnDaD_FVg) video for a quick walkthrough.

---

## 📦 What's Included

This repository provides **133 scientific and research skills** organized into the following categories:

- **100+ Scientific & Financial Databases** - A unified database-lookup skill provides direct access to 78 public databases (PubChem, ChEMBL, UniProt, COSMIC, ClinicalTrials.gov, FRED, USPTO, and more), plus dedicated skills for DepMap, Imaging Data Commons, PrimeKG, and U.S. Treasury Fiscal Data. Multi-database packages like BioServices (~40 bioinformatics services), BioPython (38 NCBI sub-databases via Entrez), and gget (20+ genomics databases) add further coverage
- **70+ Optimized Python Package Skills** - Explicitly defined skills for RDKit, Scanpy, PyTorch Lightning, scikit-learn, BioPython, pyzotero, BioServices, PennyLane, Qiskit, OpenMM, MDAnalysis, scVelo, TimesFM, and others — with curated documentation, examples, and best practices. Note: the agent can write code using *any* Python package, not just these; these skills simply provide stronger, more reliable performance for the packages listed
- **9 Scientific Integration Skills** - Explicitly defined skills for Benchling, DNAnexus, LatchBio, OMERO, Protocols.io, Open Notebook, and more. Again, the agent is not limited to these — any API or platform reachable from Python is fair game; these skills are the optimized, pre-documented paths
- **30+ Analysis & Communication Tools** - Literature review, scientific writing, peer review, document processing, posters, slides, schematics, infographics, Mermaid diagrams, and more
- **10+ Research & Clinical Tools** - Hypothesis generation, grant writing, clinical decision support, treatment plans, regulatory compliance, scenario analysis

Each skill includes:
- ✅ Comprehensive documentation (`SKILL.md`)
- ✅ Practical code examples
- ✅ Use cases and best practices
- ✅ Integration guides
- ✅ Reference materials

---

## 📋 Table of Contents

- [What's Included](#whats-included)
- [Why Use This?](#why-use-this)
- [Getting Started](#getting-started)
- [Security Disclaimer](#-security-disclaimer)
- [Support Open Source](#-support-the-open-source-community)
- [Prerequisites](#prerequisites)
- [Quick Examples](#quick-examples)
- [Use Cases](#use-cases)
- [Available Skills](#available-skills)
- [Contributing](#contributing)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Support](#support)
- [Join Our Community](#join-our-community)
- [Use with Other AI Agents](#-use-with-other-ai-agents-via-skillkit)
- [Citation](#citation)
- [License](#license)

---

## 🚀 Why Use This?

### ⚡ **Accelerate Your Research**
- **Save Days of Work** - Skip API documentation research and integration setup
- **Production-Ready Code** - Tested, validated examples following scientific best practices
- **Multi-Step Workflows** - Execute complex pipelines with a single prompt

### 🎯 **Comprehensive Coverage**
- **133 Skills** - Extensive coverage across all major scientific domains
- **100+ Databases** - Unified access to 78+ databases via database-lookup, plus dedicated data access skills and multi-database packages like BioServices, BioPython, and gget
- **70+ Optimized Python Package Skills** - RDKit, Scanpy, PyTorch Lightning, scikit-learn, BioServices, PennyLane, Qiskit, OpenMM, scVelo, TimesFM, and others (the agent can use any Python package; these are the pre-documented, higher-performing paths)

### 🔧 **Easy Integration**
- **Simple Setup** - Copy skills to your skills directory and start working
- **Automatic Discovery** - Your agent automatically finds and uses relevant skills
- **Well Documented** - Each skill includes examples, use cases, and best practices

### 🌟 **Maintained & Supported**
- **Regular Updates** - Continuously maintained and expanded by K-Dense team
- **Community Driven** - Open source with active community contributions
- **Enterprise Ready** - Commercial support available for advanced needs

---

## 🎯 Getting Started

Install Scientific Agent Skills with a single command:

```bash
npx skills add K-Dense-AI/scientific-agent-skills
```

This is the official standard approach for installing Agent Skills across **all platforms**, including **Claude Code**, **Claude Cowork**, **Codex**, **Gemini CLI**, **Cursor**, and any other agent that supports the open [Agent Skills](https://agentskills.io/) standard.

**That's it!** Your AI agent will automatically discover the skills and use them when relevant to your scientific tasks. You can also invoke any skill manually by mentioning the skill name in your prompt.

---

## ⚠️ Security Disclaimer

> **Skills can execute code and influence your coding agent's behavior. Review what you install.**

Agent Skills are powerful — they can instruct your AI agent to run arbitrary code, install packages, make network requests, and modify files on your system. A malicious or poorly written skill has the potential to steer your coding agent into harmful behavior.

We take security seriously. All contributions go through a review process, and we run LLM-based security scans (via [Cisco AI Defense Skill Scanner](https://github.com/cisco-ai-defense/skill-scanner)) on every skill in this repository. However, as a small team with a growing number of community contributions, we cannot guarantee that every skill has been exhaustively reviewed for all possible risks.

**It is ultimately your responsibility to review the skills you install and decide which ones to trust.**

We recommend the following:

- **Do not install everything at once.** Only install the skills you actually need for your work. While installing the full collection was reasonable when K-Dense created and maintained every skill, the repository now includes many community contributions that we may not have reviewed as thoroughly.
- **Read the `SKILL.md` before installing.** Each skill's documentation describes what it does, what packages it uses, and what external services it connects to. If something looks suspicious, don't install it.
- **Check the contribution history.** Skills authored by K-Dense (`K-Dense-AI`) have been through our internal review process. Community-contributed skills have been reviewed to the best of our ability, but with limited resources.
- **Run the security scanner yourself.** Before installing third-party skills, scan them locally:
  ```bash
  uv pip install cisco-ai-skill-scanner
  skill-scanner scan /path/to/skill --use-behavioral
  ```
- **Report anything suspicious.** If you find a skill that looks malicious or behaves unexpectedly, please [open an issue](https://github.com/K-Dense-AI/scientific-agent-skills/issues) immediately so we can investigate.

All skills are scanned on an approximately weekly basis, and [SECURITY.md](SECURITY.md) is updated with the latest results. We try to address security gaps as they arise.

---

## ❤️ Support the Open Source Community

Scientific Agent Skills is powered by **50+ incredible open source projects** maintained by dedicated developers and research communities worldwide. Projects like Biopython, Scanpy, RDKit, scikit-learn, PyTorch Lightning, and many others form the foundation of these skills.

**If you find value in this repository, please consider supporting the projects that make it possible:**

- ⭐ **Star their repositories** on GitHub
- 💰 **Sponsor maintainers** via GitHub Sponsors or NumFOCUS
- 📝 **Cite projects** in your publications
- 💻 **Contribute** code, docs, or bug reports

👉 **[View the full list of projects to support](docs/open-source-sponsors.md)**

---

## ⚙️ Prerequisites

- **Python**: 3.11+ (3.12+ recommended for best compatibility)
- **uv**: Python package manager (required for installing skill dependencies)
- **Git LFS**: Required for cloning large skill assets (models, datasets) — install before cloning
- **Client**: Any agent that supports the [Agent Skills](https://agentskills.io/) standard (Cursor, Claude Code, Gemini CLI, Codex, etc.)
- **System**: macOS, Linux, or Windows with WSL2
- **Dependencies**: Automatically handled by individual skills (check `SKILL.md` files for specific requirements)

### Installing Git LFS

Some skills include large binary assets (model weights, reference datasets) tracked with Git LFS. Without Git LFS, these files will appear as small pointer stubs rather than the actual content, causing checkout failures.

**macOS:**
```bash
brew install git-lfs && git lfs install
```

**Linux:**
```bash
sudo apt-get install git-lfs && git lfs install   # Debian/Ubuntu
# or
sudo yum install git-lfs && git lfs install       # RHEL/CentOS
```

**Windows:**
Download the installer from [git-lfs.github.com](https://git-lfs.github.com), then run:
```powershell
git lfs install
```

After installing, re-clone or run `git lfs pull` in an existing clone to fetch the full file contents.

### Installing uv

The skills use `uv` as the package manager for installing Python dependencies. Install it using the instructions for your operating system:

**macOS and Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Alternative (via pip):**
```bash
pip install uv
```

After installation, verify it works by running:
```bash
uv --version
```

For more installation options and details, visit the [official uv documentation](https://docs.astral.sh/uv/).

---

## 💡 Quick Examples

Once you've installed the skills, you can ask your AI agent to execute complex multi-step scientific workflows. Here are some example prompts:

### 🧪 Drug Discovery Pipeline
**Goal**: Find novel EGFR inhibitors for lung cancer treatment

**Prompt**:
```
Use available skills you have access to whenever possible. Query ChEMBL for EGFR inhibitors (IC50 < 50nM), analyze structure-activity relationships 
with RDKit, generate improved analogs with datamol, perform virtual screening with DiffDock 
against AlphaFold EGFR structure, search PubMed for resistance mechanisms, check COSMIC for 
mutations, and create visualizations and a comprehensive report.
```

**Skills Used**: ChEMBL, RDKit, datamol, DiffDock, AlphaFold DB, PubMed, COSMIC, scientific visualization

*Need cloud GPUs and a publication-ready report at the end? [Run this on K-Dense Web free.](https://k-dense.ai)*

---

### 🔬 Single-Cell RNA-seq Analysis
**Goal**: Comprehensive analysis of 10X Genomics data with public data integration

**Prompt**:
```
Use available skills you have access to whenever possible. Load 10X dataset with Scanpy, perform QC and doublet removal, integrate with Cellxgene 
Census data, identify cell types using NCBI Gene markers, run differential expression with 
PyDESeq2, infer gene regulatory networks with Arboreto, enrich pathways via Reactome/KEGG, 
and identify therapeutic targets with Open Targets.
```

**Skills Used**: Scanpy, Cellxgene Census, NCBI Gene, PyDESeq2, Arboreto, Reactome, KEGG, Open Targets

*Want zero-setup cloud execution and shareable outputs? [Try K-Dense Web free.](https://k-dense.ai)*

---

### 🧬 Multi-Omics Biomarker Discovery
**Goal**: Integrate RNA-seq, proteomics, and metabolomics to predict patient outcomes

**Prompt**:
```
Use available skills you have access to whenever possible. Analyze RNA-seq with PyDESeq2, process mass spec with pyOpenMS, integrate metabolites from 
HMDB/Metabolomics Workbench, map proteins to pathways (UniProt/KEGG), find interactions via 
STRING, correlate omics layers with statsmodels, build predictive model with scikit-learn, 
and search ClinicalTrials.gov for relevant trials.
```

**Skills Used**: PyDESeq2, pyOpenMS, HMDB, Metabolomics Workbench, UniProt, KEGG, STRING, statsmodels, scikit-learn, ClinicalTrials.gov

*This pipeline is heavy on compute. [Run it on K-Dense Web with cloud GPUs, free to start.](https://k-dense.ai)*

---

### 🎯 Virtual Screening Campaign
**Goal**: Discover allosteric modulators for protein-protein interactions

**Prompt**:
```
Use available skills you have access to whenever possible. Retrieve AlphaFold structures, identify interaction interface with BioPython, search ZINC 
for allosteric candidates (MW 300-500, logP 2-4), filter with RDKit, dock with DiffDock, 
rank with DeepChem, check PubChem suppliers, search USPTO patents, and optimize leads with 
MedChem/molfeat.
```

**Skills Used**: AlphaFold DB, BioPython, ZINC, RDKit, DiffDock, DeepChem, PubChem, USPTO, MedChem, molfeat

*Skip the local GPU bottleneck. [Run virtual screening on K-Dense Web free.](https://k-dense.ai)*

---

### 🏥 Clinical Variant Interpretation
**Goal**: Analyze VCF file for hereditary cancer risk assessment

**Prompt**:
```
Use available skills you have access to whenever possible. Parse VCF with pysam, annotate variants with Ensembl VEP, query ClinVar for pathogenicity, 
check COSMIC for cancer mutations, retrieve gene info from NCBI Gene, analyze protein impact 
with UniProt, search PubMed for case reports, check ClinPGx for pharmacogenomics, generate 
clinical report with document processing tools, and find matching trials on ClinicalTrials.gov.
```

**Skills Used**: pysam, Ensembl, ClinVar, COSMIC, NCBI Gene, UniProt, PubMed, ClinPGx, Document Skills, ClinicalTrials.gov

*Need a polished clinical report at the end, not just code? [K-Dense Web delivers publication-ready outputs. Try it free.](https://k-dense.ai)*

---

### 🌐 Systems Biology Network Analysis
**Goal**: Analyze gene regulatory networks from RNA-seq data

**Prompt**:
```
Use available skills you have access to whenever possible. Query NCBI Gene for annotations, retrieve sequences from UniProt, identify interactions via 
STRING, map to Reactome/KEGG pathways, analyze topology with Torch Geometric, reconstruct 
GRNs with Arboreto, assess druggability with Open Targets, model with PyMC, visualize 
networks, and search GEO for similar patterns.
```

**Skills Used**: NCBI Gene, UniProt, STRING, Reactome, KEGG, Torch Geometric, Arboreto, Open Targets, PyMC, GEO

*Want end-to-end pipelines with shareable outputs and no setup? [Try K-Dense Web free.](https://k-dense.ai)*

> 📖 **Want more examples?** Check out [docs/examples.md](docs/examples.md) for comprehensive workflow examples and detailed use cases across all scientific domains.

---

## 🚀 Want to Skip the Setup and Just Do the Science?

**Recognize any of these?**

- You spent more time configuring environments than running analyses
- Your workflow needs a GPU your local machine does not have
- You need a shareable, publication-ready figure or report, not just a script
- You want to run a complex multi-step pipeline right now, without reading package docs first

If so, **[K-Dense Web](https://k-dense.ai)** was built for you. It is the full AI co-scientist platform: everything in this repo plus cloud GPUs, 200+ skills, and outputs you can drop directly into a paper or presentation. Zero setup required.

| Feature | This Repo | K-Dense Web |
|---------|-----------|-------------|
| Scientific Skills | 133 skills | **200+ skills** (exclusive access) |
| Setup | Manual installation | **Zero setup, works instantly** |
| Compute | Your machine | **Cloud GPUs and HPC included** |
| Workflows | Prompt and code | **End-to-end research pipelines** |
| Outputs | Code and analysis | **Publication-ready figures, reports, and papers** |
| Integrations | Local tools | **Lab systems, ELNs, and cloud storage** |

> *"K-Dense Web took me from raw sequencing data to a draft figure in one afternoon. What used to take three days of environment setup and scripting now just works."*
> **Computational biologist, drug discovery**

> ### 💰 $50 in free credits, no credit card required
> Start running real scientific workflows in minutes.
>
> **[Try K-Dense Web free](https://k-dense.ai)**

*[k-dense.ai](https://k-dense.ai) | [Read the full comparison](https://k-dense.ai/blog/k-dense-web-vs-scientific-agent-skills)*

---

## 🔬 Use Cases

### 🧪 Drug Discovery & Medicinal Chemistry
- **Virtual Screening**: Screen millions of compounds from PubChem/ZINC against protein targets
- **Lead Optimization**: Analyze structure-activity relationships with RDKit, generate analogs with datamol
- **ADMET Prediction**: Predict absorption, distribution, metabolism, excretion, and toxicity with DeepChem
- **Molecular Docking**: Predict binding poses and affinities with DiffDock
- **Bioactivity Mining**: Query ChEMBL for known inhibitors and analyze SAR patterns

### 🧬 Bioinformatics & Genomics
- **Sequence Analysis**: Process DNA/RNA/protein sequences with BioPython and pysam
- **Single-Cell Analysis**: Analyze 10X Genomics data with Scanpy, identify cell types, infer GRNs with Arboreto
- **Variant Annotation**: Annotate VCF files with Ensembl VEP, query ClinVar for pathogenicity
- **Variant Database Management**: Build scalable VCF databases with TileDB-VCF for incremental sample addition, efficient population-scale queries, and compressed storage of genomic variant data
- **Gene Discovery**: Query NCBI Gene, UniProt, and Ensembl for comprehensive gene information
- **Network Analysis**: Identify protein-protein interactions via STRING, map to pathways (KEGG, Reactome)

### 🏥 Clinical Research & Precision Medicine
- **Clinical Trials**: Search ClinicalTrials.gov for relevant studies, analyze eligibility criteria
- **Variant Interpretation**: Annotate variants with ClinVar, COSMIC, and ClinPGx for pharmacogenomics
- **Drug Safety**: Query FDA databases for adverse events, drug interactions, and recalls
- **Precision Therapeutics**: Match patient variants to targeted therapies and clinical trials

### 🔬 Multi-Omics & Systems Biology
- **Multi-Omics Integration**: Combine RNA-seq, proteomics, and metabolomics data
- **Pathway Analysis**: Enrich differentially expressed genes in KEGG/Reactome pathways
- **Network Biology**: Reconstruct gene regulatory networks, identify hub genes
- **Biomarker Discovery**: Integrate multi-omics layers to predict patient outcomes

### 📊 Data Analysis & Visualization
- **Statistical Analysis**: Perform hypothesis testing, power analysis, and experimental design
- **Publication Figures**: Create publication-quality visualizations with matplotlib and seaborn
- **Network Visualization**: Visualize biological networks with NetworkX
- **Report Generation**: Generate comprehensive PDF reports with Document Skills

### 🧪 Laboratory Automation
- **Protocol Design**: Create Opentrons protocols for automated liquid handling
- **LIMS Integration**: Integrate with Benchling and LabArchives for data management
- **Workflow Automation**: Automate multi-step laboratory workflows

---

## 📚 Available Skills

This repository contains **133 scientific and research skills** organized across multiple domains. Each skill provides comprehensive documentation, code examples, and best practices for working with scientific libraries, databases, and tools.

### Skill Categories

> **Note:** The Python package and integration skills listed below are *explicitly defined* skills — curated with documentation, examples, and best practices for stronger, more reliable performance. They are not a ceiling: the agent can install and use *any* Python package or call *any* API, even without a dedicated skill. The skills listed simply make common workflows faster and more dependable.

#### 🧬 **Bioinformatics & Genomics** (21+ skills)
- Sequence analysis: BioPython, pysam, scikit-bio, BioServices
- Single-cell analysis: Scanpy, AnnData, scvi-tools, scVelo (RNA velocity), Arboreto, Cellxgene Census
- Genomic tools: gget, geniml, gtars, deepTools, FlowIO, Polars-Bio, Zarr, TileDB-VCF
- Differential expression: PyDESeq2
- Phylogenetics: ETE Toolkit, Phylogenetics (MAFFT, IQ-TREE 2, FastTree)

#### 🧪 **Cheminformatics & Drug Discovery** (10+ skills)
- Molecular manipulation: RDKit, Datamol, Molfeat
- Deep learning: DeepChem, TorchDrug
- Docking & screening: DiffDock
- Molecular dynamics: OpenMM + MDAnalysis (MD simulation & trajectory analysis)
- Cloud quantum chemistry: Rowan (pKa, docking, cofolding)
- Drug-likeness: MedChem
- Benchmarks: PyTDC

#### 🔬 **Proteomics & Mass Spectrometry** (2 skills)
- Spectral processing: matchms, pyOpenMS

#### 🏥 **Clinical Research & Precision Medicine** (8+ skills)
- Clinical databases: via Database Lookup (ClinicalTrials.gov, ClinVar, ClinPGx, COSMIC, FDA, cBioPortal, Monarch, and more)
- Cancer genomics: DepMap (cancer dependency scores, drug sensitivity)
- Cancer imaging: Imaging Data Commons (NCI radiology & pathology datasets via idc-index)
- Healthcare AI: PyHealth, NeuroKit2, Clinical Decision Support
- Clinical documentation: Clinical Reports, Treatment Plans

#### 🖼️ **Medical Imaging & Digital Pathology** (3 skills)
- DICOM processing: pydicom
- Whole slide imaging: histolab, PathML

#### 🧠 **Neuroscience & Electrophysiology** (1 skill)
- Neural recordings: Neuropixels-Analysis (extracellular spikes, silicon probes, spike sorting)

#### 🤖 **Machine Learning & AI** (16+ skills)
- Deep learning: PyTorch Lightning, Transformers, Stable Baselines3, PufferLib
- Classical ML: scikit-learn, scikit-survival, SHAP
- Time series: aeon, TimesFM (Google's zero-shot foundation model for univariate forecasting)
- Bayesian methods: PyMC
- Optimization: PyMOO
- Graph ML: Torch Geometric
- Dimensionality reduction: UMAP-learn
- Statistical modeling: statsmodels

#### 🔮 **Materials Science, Chemistry & Physics** (7 skills)
- Materials: Pymatgen
- Metabolic modeling: COBRApy
- Astronomy: Astropy
- Quantum computing: Cirq, PennyLane, Qiskit, QuTiP

#### ⚙️ **Engineering & Simulation** (4 skills)
- Numerical computing: MATLAB/Octave
- Computational fluid dynamics: FluidSim
- Discrete-event simulation: SimPy
- Symbolic math: SymPy

#### 📊 **Data Analysis & Visualization** (16+ skills)
- Visualization: Matplotlib, Seaborn, Scientific Visualization
- Geospatial analysis: GeoPandas, GeoMaster (remote sensing, GIS, satellite imagery, spatial ML, 500+ examples)
- Data processing: Dask, Polars, Vaex
- Network analysis: NetworkX
- Document processing: Document Skills (PDF, DOCX, PPTX, XLSX)
- Infographics: Infographics (AI-powered professional infographic creation)
- Diagrams: Markdown & Mermaid Writing (text-based diagrams as default documentation standard)
- Exploratory data analysis: EDA workflows
- Statistical analysis: Statistical Analysis workflows

#### 🧪 **Laboratory Automation** (4 skills)
- Liquid handling: PyLabRobot
- Cloud lab: Ginkgo Cloud Lab (cell-free protein expression, fluorescent pixel art via autonomous RAC infrastructure)
- Protocol management: Protocols.io
- LIMS integration: Benchling, LabArchives

#### 🔬 **Multi-omics & Systems Biology** (4+ skills)
- Pathway analysis: via Database Lookup (KEGG, Reactome, STRING) and PrimeKG
- Multi-omics: HypoGeniC
- Data management: LaminDB

#### 🧬 **Protein Engineering & Design** (3 skills)
- Protein language models: ESM
- Glycoengineering: Glycoengineering (N/O-glycosylation prediction, therapeutic antibody optimization)
- Cloud laboratory platform: Adaptyv (automated protein testing and validation)

#### 📚 **Scientific Communication** (20+ skills)
- Literature: Paper Lookup (PubMed, PMC, bioRxiv, medRxiv, arXiv, OpenAlex, Crossref, Semantic Scholar, CORE, Unpaywall), Literature Review
- Advanced paper search: BGPT Paper Search (25+ structured fields per paper — methods, results, sample sizes, quality scores — from full text, not just abstracts)
- Web search: Parallel Web (synthesized summaries with citations)
- Research notebooks: Open Notebook (self-hosted NotebookLM alternative — PDFs, videos, audio, web pages; 16+ AI providers; multi-speaker podcast generation)
- Writing: Scientific Writing, Peer Review
- Document processing: XLSX, MarkItDown, Document Skills
- Publishing: Venue Templates
- Presentations: Scientific Slides, LaTeX Posters, PPTX Posters
- Diagrams: Scientific Schematics, Markdown & Mermaid Writing
- Infographics: Infographics (10 types, 8 styles, colorblind-safe palettes)
- Citations: Citation Management
- Illustration: Generate Image (AI image generation with FLUX.2 Pro and Gemini 3 Pro (Nano Banana Pro))

#### 🔬 **Scientific Databases & Data Access** (5 skills → 100+ databases total)
> A unified database-lookup skill provides direct REST API access to 78 public databases across all domains. Dedicated skills cover specialized data platforms. Multi-database packages like BioServices (~40 bioinformatics services), BioPython (38 NCBI sub-databases via Entrez), and gget (20+ genomics databases) add further coverage.
- Unified access: Database Lookup (78 databases spanning chemistry, genomics, clinical, pathways, patents, economics, and more — PubChem, ChEMBL, UniProt, PDB, AlphaFold, KEGG, Reactome, STRING, ClinVar, COSMIC, ClinicalTrials.gov, FDA, FRED, USPTO, SEC EDGAR, and dozens more)
- Cancer genomics: DepMap (cancer cell line dependencies, drug sensitivity, gene effect profiles)
- Cancer imaging: Imaging Data Commons (NCI radiology & pathology datasets via idc-index)
- Knowledge graph: PrimeKG (precision medicine knowledge graph — genes, drugs, diseases, phenotypes)
- Fiscal data: U.S. Treasury Fiscal Data (national debt, Treasury statements, auctions, exchange rates)

#### 🔧 **Infrastructure & Platforms** (7+ skills)
- Cloud compute: Modal
- GPU acceleration: Optimize for GPU (CuPy, Numba CUDA, Warp, cuDF, cuML, cuGraph, KvikIO, cuCIM, cuxfilter, cuVS, cuSpatial, RAFT)
- Genomics platforms: DNAnexus, LatchBio
- Microscopy: OMERO
- Automation: Opentrons
- Resource detection: Get Available Resources

#### 🎓 **Research Methodology & Planning** (12+ skills)
- Ideation: Scientific Brainstorming, Hypothesis Generation
- Critical analysis: Scientific Critical Thinking, Scholar Evaluation
- Scenario analysis: What-If Oracle (multi-branch possibility exploration, risk analysis, strategic options)
- Multi-perspective deliberation: Consciousness Council (diverse expert viewpoints, devil's advocate analysis)
- Cognitive profiling: DHDNA Profiler (extract thinking patterns and cognitive signatures from any text)
- Funding: Research Grants
- Discovery: Research Lookup, Paper Lookup (10 academic databases)
- Market analysis: Market Research Reports

#### ⚖️ **Regulatory & Standards** (1 skill)
- Medical device standards: ISO 13485 Certification

> 📖 **For complete details on all skills**, see [docs/scientific-skills.md](docs/scientific-skills.md)

> 💡 **Looking for practical examples?** Check out [docs/examples.md](docs/examples.md) for comprehensive workflow examples across all scientific domains.

---

## 🤝 Contributing

We welcome contributions to expand and improve this scientific skills repository!

### Ways to Contribute

✨ **Add New Skills**
- Create skills for additional scientific packages or databases
- Add integrations for scientific platforms and tools

📚 **Improve Existing Skills**
- Enhance documentation with more examples and use cases
- Add new workflows and reference materials
- Improve code examples and scripts
- Fix bugs or update outdated information

🐛 **Report Issues**
- Submit bug reports with detailed reproduction steps
- Suggest improvements or new features

### How to Contribute

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-skill`)
3. **Follow** the existing directory structure and documentation patterns
4. **Ensure** all new skills include comprehensive `SKILL.md` files
5. **Test** your examples and workflows thoroughly
6. **Commit** your changes (`git commit -m 'Add amazing skill'`)
7. **Push** to your branch (`git push origin feature/amazing-skill`)
8. **Submit** a pull request with a clear description of your changes

### Contribution Guidelines

✅ **Adhere to the [Agent Skills Specification](https://agentskills.io/specification)** — Every skill must follow the official spec (valid `SKILL.md` frontmatter, naming conventions, directory structure)  
✅ Maintain consistency with existing skill documentation format  
✅ Ensure all code examples are tested and functional  
✅ Follow scientific best practices in examples and workflows  
✅ Update relevant documentation when adding new capabilities  
✅ Provide clear comments and docstrings in code  
✅ Include references to official documentation

### Security Scanning

All skills in this repository are security-scanned using [Cisco AI Defense Skill Scanner](https://github.com/cisco-ai-defense/skill-scanner), an open-source tool that detects prompt injection, data exfiltration, and malicious code patterns in Agent Skills.

If you are contributing a new skill, we recommend running the scanner locally before submitting a pull request:

```bash
uv pip install cisco-ai-skill-scanner
skill-scanner scan /path/to/your/skill --use-behavioral
```

> **Note:** A clean scan result reduces noise in review, but does not guarantee a skill is free of all risk. Contributed skills are also reviewed manually before merging.

### Recognition

Contributors are recognized in our community and may be featured in:
- Repository contributors list
- Special mentions in release notes
- K-Dense community highlights

Your contributions help make scientific computing more accessible and enable researchers to leverage AI tools more effectively!

### Support Open Source

This project builds on 50+ amazing open source projects. If you find value in these skills, please consider [supporting the projects we depend on](docs/open-source-sponsors.md).

---

## 🔧 Troubleshooting

### Common Issues

**Problem: Skills not loading**
- Verify skill folders are in the correct directory (see [Getting Started](#getting-started))
- Each skill folder must contain a `SKILL.md` file
- Restart your agent/IDE after copying skills
- In Cursor, check Settings → Rules to confirm skills are discovered

**Problem: Missing Python dependencies**
- Solution: Check the specific `SKILL.md` file for required packages
- Install dependencies: `uv pip install package-name`

**Problem: API rate limits**
- Solution: Many databases have rate limits. Review the specific database documentation
- Consider implementing caching or batch requests

**Problem: Authentication errors**
- Solution: Some services require API keys. Check the `SKILL.md` for authentication setup
- Verify your credentials and permissions

**Problem: Outdated examples**
- Solution: Report the issue via GitHub Issues
- Check the official package documentation for updated syntax

---

## ❓ FAQ

### General Questions

**Q: Is this free to use?**  
A: Yes! This repository is MIT licensed. However, each individual skill has its own license specified in the `license` metadata field within its `SKILL.md` file—be sure to review and comply with those terms.

**Q: Why are all skills grouped together instead of separate packages?**  
A: We believe good science in the age of AI is inherently interdisciplinary. Bundling all skills together makes it trivial for you (and your agent) to bridge across fields—e.g., combining genomics, cheminformatics, clinical data, and machine learning in one workflow—without worrying about which individual skills to install or wire together.

**Q: Can I use this for commercial projects?**  
A: The repository itself is MIT licensed, which allows commercial use. However, individual skills may have different licenses—check the `license` field in each skill's `SKILL.md` file to ensure compliance with your intended use.

**Q: Do all skills have the same license?**  
A: No. Each skill has its own license specified in the `license` metadata field within its `SKILL.md` file. These licenses may differ from the repository's MIT License. Users are responsible for reviewing and adhering to the license terms of each individual skill they use.

**Q: How often is this updated?**  
A: We regularly update skills to reflect the latest versions of packages and APIs. Major updates are announced in release notes.

**Q: Can I use this with other AI models?**  
A: The skills follow the open [Agent Skills](https://agentskills.io/) standard and work with any compatible agent, including Cursor, Claude Code, and Codex.

### Installation & Setup

**Q: Do I need all the Python packages installed?**  
A: No! Only install the packages you need. Each skill specifies its requirements in its `SKILL.md` file.

**Q: What if a skill doesn't work?**  
A: First check the [Troubleshooting](#troubleshooting) section. If the issue persists, file an issue on GitHub with detailed reproduction steps.

**Q: Do the skills work offline?**  
A: Database skills require internet access to query APIs. Package skills work offline once Python dependencies are installed.

### Contributing

**Q: Can I contribute my own skills?**  
A: Absolutely! We welcome contributions. See the [Contributing](#contributing) section for guidelines and best practices.

**Q: How do I report bugs or suggest features?**  
A: Open an issue on GitHub with a clear description. For bugs, include reproduction steps and expected vs actual behavior.

---

## 💬 Support

Need help? Here's how to get support:

- 📖 **Documentation**: Check the relevant `SKILL.md` and `references/` folders
- 🐛 **Bug Reports**: [Open an issue](https://github.com/K-Dense-AI/scientific-agent-skills/issues)
- 💡 **Feature Requests**: [Submit a feature request](https://github.com/K-Dense-AI/scientific-agent-skills/issues/new)
- 💼 **Enterprise Support**: Contact [K-Dense](https://k-dense.ai/) for commercial support
- 🌐 **Community**: [Join our Slack](https://join.slack.com/t/k-densecommunity/shared_invite/zt-3iajtyls1-EwmkwIZk0g_o74311Tkf5g)

---

## 🎉 Join Our Community!

**We'd love to have you join us!** 🚀

Connect with other scientists, researchers, and AI enthusiasts using AI agents for scientific computing. Share your discoveries, ask questions, get help with your projects, and collaborate with the community!

🌟 **[Join our Slack Community](https://join.slack.com/t/k-densecommunity/shared_invite/zt-3iajtyls1-EwmkwIZk0g_o74311Tkf5g)** 🌟

Whether you're just getting started or you're a power user, our community is here to support you. We share tips, troubleshoot issues together, showcase cool projects, and discuss the latest developments in AI-powered scientific research.

**See you there!** 💬

---

## 🤝 Use with Other AI Agents (via SkillKit)

[SkillKit](https://skillkit.dev) is a cross-agent package manager that lets you search, install, and translate Agent Skills for use with Cursor, Codex, Gemini CLI, Windsurf, and other tools — without manually copying folders.

### Quick Start

```bash
npm install -g skillkit
```

**Search for skills:**
```bash
skillkit search "scientific"
```

**Install this skill collection:**
```bash
skillkit install claude-scientific-skills
```

**Translate skills for a specific agent** (e.g., Cursor):
```bash
skillkit translate claude-scientific-skills --agent cursor
```

SkillKit automatically places skills in the correct directory for your target agent and handles any format differences between tools. See the [SkillKit documentation](https://skillkit.dev) for the full list of supported agents.

---

## 📖 Citation

If you use Scientific Agent Skills in your research or project, please cite it as:

### BibTeX
```bibtex
@software{scientific_agent_skills_2026,
  author = {{K-Dense Inc.}},
  title = {Scientific Agent Skills: A Comprehensive Collection of Scientific Tools for AI Agents},
  year = {2026},
  url = {https://github.com/K-Dense-AI/scientific-agent-skills},
  note = {133 skills covering databases, packages, integrations, and analysis tools}
}
```

### APA
```
K-Dense Inc. (2026). Scientific Agent Skills: A comprehensive collection of scientific tools for AI agents [Computer software]. https://github.com/K-Dense-AI/scientific-agent-skills
```

### MLA
```
K-Dense Inc. Scientific Agent Skills: A Comprehensive Collection of Scientific Tools for AI Agents. 2026, github.com/K-Dense-AI/scientific-agent-skills.
```

### Plain Text
```
Scientific Agent Skills by K-Dense Inc. (2026)
Available at: https://github.com/K-Dense-AI/scientific-agent-skills
```

We appreciate acknowledgment in publications, presentations, or projects that benefit from these skills!

---

## 📄 License

This project is licensed under the **MIT License**.

**Copyright © 2026 K-Dense Inc.** ([k-dense.ai](https://k-dense.ai/))

### Key Points:
- ✅ **Free for any use** (commercial and noncommercial)
- ✅ **Open source** - modify, distribute, and use freely
- ✅ **Permissive** - minimal restrictions on reuse
- ⚠️ **No warranty** - provided "as is" without warranty of any kind

See [LICENSE.md](LICENSE.md) for full terms.

### Individual Skill Licenses

> ⚠️ **Important**: Each skill has its own license specified in the `license` metadata field within its `SKILL.md` file. These licenses may differ from the repository's MIT License and may include additional terms or restrictions. **Users are responsible for reviewing and adhering to the license terms of each individual skill they use.**

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=K-Dense-AI/scientific-agent-skills&type=date&legend=top-left)](https://www.star-history.com/#K-Dense-AI/scientific-agent-skills&type=date&legend=top-left)
