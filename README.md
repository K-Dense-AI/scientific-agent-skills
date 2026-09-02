# Scientific Agent Skills

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.md)
[![Version](https://img.shields.io/badge/Version-2.65.0-blue.svg)](pyproject.toml)
[![Skills](https://img.shields.io/badge/Skills-164-brightgreen.svg)](#-whats-included)
[![Databases](https://img.shields.io/badge/Databases-100%2B-orange.svg)](#-whats-included)
[![Agent Skills](https://img.shields.io/badge/Standard-Agent_Skills-blueviolet.svg)](https://agentskills.io/)
[![Agent Plugins](https://img.shields.io/badge/Standard-Agent_Plugins-0A7A72.svg)](https://agent-plugins.org/)
[![Security Scan](https://github.com/K-Dense-AI/scientific-agent-skills/actions/workflows/security-scan.yml/badge.svg)](https://github.com/K-Dense-AI/scientific-agent-skills/actions/workflows/security-scan.yml)
[![Skill Tests](https://github.com/K-Dense-AI/scientific-agent-skills/actions/workflows/skill-tests.yml/badge.svg)](https://github.com/K-Dense-AI/scientific-agent-skills/actions/workflows/skill-tests.yml)
[![Works with](https://img.shields.io/badge/Works_with-Cursor_|_Claude_Code_|_Codex_|_Google_Antigravity-blue.svg)](#-getting-started)
[![X](https://img.shields.io/badge/Follow_on_X-%40k__dense__ai-000000?logo=x)](https://x.com/k_dense_ai)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-K--Dense_Inc.-0A66C2?logo=linkedin)](https://www.linkedin.com/company/k-dense-inc)
[![YouTube](https://img.shields.io/badge/YouTube-K--Dense_Inc.-FF0000?logo=youtube)](https://www.youtube.com/@K-Dense-Inc)
[![Reddit](https://img.shields.io/badge/Reddit-u%2F--k--dense---FF4500?logo=reddit&logoColor=white)](https://www.reddit.com/user/-k-dense-/)

> **🔔 Claude Scientific Skills is now Scientific Agent Skills.** Same skills, broader compatibility — now works with any AI agent that supports the open [Agent Skills](https://agentskills.io/) standard, not just Claude.

> **New: [K-Dense BYOK](https://github.com/K-Dense-AI/k-dense-byok)** — A free, open-source AI co-scientist that runs on your desktop, powered by Scientific Agent Skills. Bring your own API keys, pick from 40+ models, and get a full research workspace with web search, file handling, 100+ scientific databases, and access to all 164 skills in this repo. Your data stays on your computer, and you can optionally scale to cloud compute via [Modal](https://modal.com/) for heavy workloads. [Get started here.](https://github.com/K-Dense-AI/k-dense-byok)

> **🎥 Webinar recording — [Getting Started with K-Dense BYOK](https://youtu.be/Du3BIE48DKc?si=9dPpETKSc2PeQbvU)**
> A hands-on walkthrough of [K-Dense BYOK](https://github.com/K-Dense-AI/k-dense-byok), our free, open-source AI co-scientist that runs locally on your own machine and is powered by Scientific Agent Skills. We cover how to set it up, bring your own API keys, and run real research workflows with these skills. No prior technical experience needed. **[Watch the recording →](https://youtu.be/Du3BIE48DKc?si=9dPpETKSc2PeQbvU)**

> **Stay up to date:** Follow K-Dense on [X](https://x.com/k_dense_ai), [LinkedIn](https://www.linkedin.com/company/k-dense-inc), [YouTube](https://www.youtube.com/@K-Dense-Inc), and [Reddit](https://www.reddit.com/user/-k-dense-/) for new skills, release announcements, walkthroughs, research workflow demos, and examples you can use with your own AI agent.

A comprehensive collection of **164 ready-to-use scientific and research skills** (covering cancer genomics, individual-level 1000 Genomes queries, hosted regulatory-sequence prediction, live pathogen-variant surveillance, analytical method validation, PK/PD modelling and dose selection, full-text biomedical and regulatory literature retrieval, drug-target binding, bounded biomedical knowledge graph search, molecular dynamics, RNA velocity, microbiome foundation models, geospatial science, time series forecasting, scientific ML resource discovery via Hugging Science, 78+ scientific databases, and more) for any AI agent that supports the open [Agent Skills](https://agentskills.io/) standard, created by [K-Dense](https://k-dense.ai). The repository is also a portable [Agent Plugins](https://agent-plugins.org/) package (`plugin.json` + `skills/`), so plugin-capable clients can load the whole collection as one plugin. Works with **Cursor, Claude Code, Codex, Google Antigravity, and more**. Transform your AI agent into a research assistant capable of executing complex multi-step scientific workflows across biology, chemistry, medicine, and beyond.

> ⭐ **Help make AI for science easier to discover:** If Scientific Agent Skills saves you time, teaches your agent a workflow, or helps your lab move faster, please [star this repository](https://github.com/K-Dense-AI/scientific-agent-skills). A star is a public signal that these open, reusable research skills are worth maintaining: it helps scientists, engineers, and open-source contributors find the project, shows which agent-skill standards are gaining real adoption, and gives us a clear reason to keep expanding the collection for the community.

---

These skills enable your AI agent to seamlessly work with specialized scientific libraries, databases, and tools across multiple scientific domains. While the agent can use any Python package or API on its own, these explicitly defined skills provide curated documentation and examples that make it significantly stronger and more reliable for the workflows below:
- 🧬 Bioinformatics & Genomics - Sequence analysis, single-cell RNA-seq, gene regulatory networks, variant annotation, phylogenetic analysis
- 🧪 Cheminformatics & Drug Discovery - Molecular property prediction, virtual screening, ADMET analysis, molecular docking, lead optimization
- 🔬 Proteomics & Mass Spectrometry - LC-MS/MS processing, peptide identification, spectral matching, protein quantification
- 🏥 Clinical Research & Evidence Workflows - Clinical trials, pharmacogenomics, variant evidence review, pharmacokinetic/pharmacodynamic modelling and dose-regimen evaluation, aggregate decision-support evaluation, source-bound draft report structures, and formatting of clinician-authored treatment decisions
- 🧠 Healthcare AI & Biosignal Research - EHR and model research, physiological signal analysis, and retrospective validation—not patient-specific diagnosis, treatment, alarms, or deployment decisions
- 🐭 Preclinical Research & Animal Welfare - Multivariate severity scoring and humane-endpoint forecasting for laboratory animal studies, for 3Rs/refinement analysis and EU Directive 2010/63/EU reporting—an aid to severity assessment, never a decision rule
- 🖼️ Medical Imaging & Digital Pathology - Privacy-aware DICOM processing and research-only whole-slide image analysis, computational pathology, and radiology data workflows
- 🤖 Machine Learning & AI - Deep learning, reinforcement learning, time series analysis, model interpretability, Bayesian methods
- 🔮 Materials Science & Chemistry - Crystal structure analysis, phase diagrams, metabolic modeling, computational chemistry
- 🌌 Physics & Astronomy - Astronomical data analysis, coordinate transformations, cosmological calculations, symbolic mathematics, physics computations
- ⚙️ Engineering & Simulation - Discrete-event simulation, multi-objective optimization, metabolic engineering, systems modeling, process optimization
- 📊 Data Analysis & Visualization - Statistical analysis, network analysis, time series, publication-quality figures, large-scale data processing, EDA
- 🌍 Geospatial Science & Remote Sensing - Satellite imagery processing, GIS analysis, spatial statistics, terrain analysis, machine learning for Earth observation
- 🧪 Laboratory Automation - Liquid handling protocols, lab equipment control, workflow automation, LIMS integration
- 📚 Scientific Communication - Evidence-traceable writing, confidential authorized peer review, literature synthesis, document processing, macro-free PPTX posters, slides, schematics, and citation management
- 🔬 Multi-omics & Systems Biology - Multi-modal data integration, pathway analysis, network biology, systems-level insights
- 🧬 Protein Engineering & Design - Protein language models, structure prediction, sequence design, function annotation
- 🧰 Agent Platforms & Infrastructure - Build on Pi with SDK, RPC, extensions, custom providers/models, packages, TUI components, and session tooling
- 🎓 Research Methodology - Evidence-bounded candidate hypotheses, scientific brainstorming, critical thinking, grant writing, and qualitative low-stakes evaluation of scholarly works
- ⚖️ Regulatory & Standards - Draft evidence-preparation artifacts for ISO management-system and laboratory standards, plus analytical method validation, verification, and transfer under ICH/USP/CLSI frameworks—prepared for qualified review, never a certification, accreditation, or method-release decision

**Transform your AI coding agent into an 'AI Scientist' on your desktop!**

> 🎬 **New to Scientific Agent Skills?** Watch our [Getting Started with Scientific Agent Skills](https://youtu.be/ZxbnDaD_FVg) video for a quick walkthrough.

### 🎥 More tutorials

Recorded walkthroughs of these skills on real research tasks, from the [K-Dense YouTube channel](https://www.youtube.com/@K-Dense-Inc):

| Video | What it covers |
|-------|----------------|
| [Skills 101: Build Your Own Scientific Agent Skill](https://youtu.be/lVZbHiwzMEg) | Writing, testing, and packaging a new skill from scratch |
| [Literature Review and Hypothesis Generation](https://youtu.be/wKJp8y4ZyiM) | Searching the literature and generating grounded hypotheses |
| [Draft and Budget an Experimental Protocol](https://youtu.be/Yz2L5s_M_34) | Turning a planned experiment into a costed, written protocol |
| [Draft Responses to Reviewer Comments](https://youtu.be/0MmU-Pmtg1o) | Building a point-by-point rebuttal from reviewer feedback |
| [Can AI Reproduce a Nature Medicine Paper?](https://youtu.be/4WTCK9kSfdk) | An end-to-end reproduction attempt on a published analysis |

---

## 📦 What's Included

This repository provides **164 scientific and research skills** organized into the following categories:

- **100+ Scientific & Financial Databases** - A unified database-lookup skill provides deterministic, provenance-rich access to 78 public databases (PubChem, ChEMBL, UniProt, COSMIC, ClinicalTrials.gov, FRED, USPTO, and more), plus dedicated skills for DepMap, Imaging Data Commons, PrimeKG, NCATS ARAX, U.S. Treasury Fiscal Data, Hugging Science, OneKGPd, and Genomic Intelligence. Multi-database packages like BioServices (~40 bioinformatics services), BioPython (39 NCBI sub-databases via Entrez), and gget (20+ genomics databases) add further coverage
- **70+ Optimized Python Package Skills** - Explicitly defined, version-aware workflows for RDKit, Scanpy, PyTorch Lightning, scikit-learn, PyTDC, PathML, pydicom, NeuroKit2, PufferLib, QuTiP, GeoPandas, pymatgen, BioPython, Qiskit, Molecular Dynamics (OpenMM/MDAnalysis), and others. The agent can still use *any* Python package; these skills provide stronger, safer guidance for the packages listed
- **9 Scientific Integration Skills** - Explicitly defined skills for Benchling, DNAnexus, LatchBio, OMERO, Protocols.io, Open Notebook, Ginkgo Cloud Lab, LabArchives, and Opentrons. Again, the agent is not limited to these — any API or platform reachable from Python is fair game; these skills are the optimized, pre-documented paths
- **30+ Analysis & Communication Tools** - Literature review, evidence-traceable scientific writing, confidential peer review, document processing, Paperclip (full-text papers, FDA/PMDA/EMA filings, and trial registries with line-pinned citations), Paperzilla, Exa Search, macro-free PPTX posters, slides, schematics, infographics, Mermaid diagrams, and more
- **10+ Research & Clinical Tools** - Evidence-bounded hypothesis generation, grant writing, aggregate clinical decision-support research, clinician-authored treatment-plan formatting, PK/PD modelling and simulation (NCA, population PK, exposure-response, bioequivalence, first-in-human dose), BIDS, ISO standards-readiness evidence preparation (ISO 13485, ISO 14971, ISO/IEC 17025, ISO 15189), analytical method validation and transfer (ICH Q2(R2)/Q14, ICH M10, USP, CLSI EP), scenario analysis, and workflow-derived skill drafting with Autoskill

Each skill includes:
- ✅ Comprehensive documentation (`SKILL.md`)
- ✅ Practical code examples
- ✅ Use cases and best practices
- ✅ Integration guides
- ✅ Reference materials
- ✅ A test suite for every skill that ships `scripts/` — CI blocks a pull request that adds bundled tooling without one

---

## 📋 Table of Contents

- [What's Included](#-whats-included)
- [Why Use This?](#-why-use-this)
- [Getting Started](#-getting-started)
- [Security Disclaimer](#%EF%B8%8F-security-disclaimer)
- [Support Open Source](#%EF%B8%8F-support-the-open-source-community)
- [Prerequisites](#%EF%B8%8F-prerequisites)
- [Quick Examples](#-quick-examples)
- [Use Cases](#-use-cases)
- [Available Skills](#-available-skills)
- [From the Blog](#-from-the-blog)
- [Contributing](#-contributing)
- [Troubleshooting](#-troubleshooting)
- [FAQ](#-faq)
- [Support](#-support)
- [Citation](#-citation)
- [License](#-license)

---

## 🚀 Why Use This?

### ⚡ **Accelerate Your Research**
- **Save Days of Work** - Skip API documentation research and integration setup
- **Reviewed Starting Points** - Tested examples with explicit validation, provenance, and safety boundaries; verify them in the target environment
- **Multi-Step Workflows** - Execute complex pipelines with a single prompt

### 🎯 **Comprehensive Coverage**
- **164 Skills** - Extensive coverage across all major scientific domains
- **100+ Databases** - Unified access to 78+ databases via database-lookup, plus dedicated data access skills and multi-database packages like BioServices, BioPython, and gget
- **70+ Optimized Python Package Skills** - Current, version-scoped guidance for packages including RDKit, Scanpy, PyTorch Lightning, scikit-learn, PyTDC, pydicom, PufferLib, QuTiP, GeoPandas, pymatgen, Qiskit, Molecular Dynamics (OpenMM/MDAnalysis), scVelo, and TimesFM (the agent can use any Python package; these are the pre-documented paths)

### 🔧 **Easy Integration**
- **Simple Setup** - Copy skills to your skills directory and start working
- **Configured Discovery** - Compatible hosts can find and use relevant skills from their configured skill paths
- **Well Documented** - Each skill includes examples, use cases, and best practices

### 🌟 **Maintained & Supported**
- **Regular Updates** - Continuously maintained and expanded by K-Dense team
- **Tested in CI** - Every skill that ships `scripts/` has a suite under `tests/`, plus a repo-wide structural contract (frontmatter, link resolution, script parsing, `--help` behavior) that runs on every pull request
- **Community Driven** - Open source with active community contributions
- **Enterprise Ready** - Commercial support available for advanced needs

---

## 🎯 Getting Started

### Option 1: npx (supported hosts)

Install Scientific Agent Skills with a single command:

```bash
npx skills add K-Dense-AI/scientific-agent-skills
```

This is a common standards-based installer for supported Agent Skills hosts, including current versions of **Claude Code**, **Claude Cowork**, **Codex**, **Gemini CLI**, **Google Antigravity**, and **Cursor**. Confirm installation paths and optional metadata behavior in your host's current documentation.

### Option 2: GitHub CLI (`gh skill`)

If you use the [GitHub CLI](https://cli.github.com/) (v2.90.0+), you can install skills with [`gh skill`](https://github.blog/changelog/2026-04-16-manage-agent-skills-with-github-cli/):

```bash
# Browse and install interactively
gh skill install K-Dense-AI/scientific-agent-skills

# Install a specific skill directly
gh skill install K-Dense-AI/scientific-agent-skills scanpy

# Target a specific agent host
gh skill install K-Dense-AI/scientific-agent-skills --agent cursor
gh skill install K-Dense-AI/scientific-agent-skills --agent claude-code
gh skill install K-Dense-AI/scientific-agent-skills --agent codex
gh skill install K-Dense-AI/scientific-agent-skills --agent gemini
```

`gh skill` automatically installs to the correct directory for your agent host and records provenance metadata for supply chain integrity.

#### Version pinning

Pin to a specific release tag or commit SHA for reproducible installs:

```bash
# Pin to a release tag
gh skill install K-Dense-AI/scientific-agent-skills --pin v2.65.0

# Pin to a commit SHA
gh skill install K-Dense-AI/scientific-agent-skills --pin abc123def
```

#### Keeping skills up to date

```bash
# Check for updates interactively
gh skill update

# Update all installed skills
gh skill update --all
```

### Option 3: Agent Plugins (Cursor, Codex, and other plugin clients)

This repository is a valid [Agent Plugins](https://agent-plugins.org/) 1.0.0 package: root [`plugin.json`](plugin.json) plus Agent Skills under `skills/`. Clients that support the standard discover every immediate child of `skills/` that contains a `SKILL.md`.

**Cursor** — symlink or copy the repo into the local plugins directory, then reload:

```bash
mkdir -p ~/.cursor/plugins/local
ln -s "$(pwd)" ~/.cursor/plugins/local/scientific-agent-skills
```

Restart Cursor or run **Developer: Reload Window**, then confirm the plugin and its skills appear under **Customize**. See [Cursor plugins](https://cursor.com/docs/plugins).

**Codex** — install from a local checkout (confirm the current CLI flag names in Codex docs):

```bash
codex plugins install .
```

Compatible clients (Cursor, Codex, GitHub Copilot, VS Code, Kiro, and others listed at [agent-plugins.org](https://agent-plugins.org/compatible-clients)) share the same package layout; installation UX stays client-specific.

### Other Agent Skills hosts (OpenClaw, NemoClaw, Pi, Hermes, …)

Agent hosts differ in install paths, discovery settings, and support for optional frontmatter fields. `npx skills add` (Option 1) commonly installs into the `~/.agents/skills/` convention, with project-scoped installs under `.agents/skills/`; confirm both paths against your host's current documentation. To install manually on a host configured to scan one of those locations:

```bash
git clone https://github.com/K-Dense-AI/scientific-agent-skills.git ~/.agents/skills/scientific-agent-skills   # user-level
git clone https://github.com/K-Dense-AI/scientific-agent-skills.git .agents/skills/scientific-agent-skills      # project-level
```

For Hermes versions that support skill taps, add the repository as a tap:

```bash
hermes skills tap add K-Dense-AI/scientific-agent-skills
```

Every `SKILL.md` has YAML frontmatter, but legacy and community skills vary in `metadata` formatting (block or flow style) and optional extension fields. Repository updates must keep `metadata.version` as a quoted numeric string and pass canonical `skills-ref validate ./skills/<skill-name>` checks. Hosts may interpret optional metadata and credential prompts differently, so verify behavior on the target host. Because 164 skills add up to a lot of standing context, consider installing a topical subset rather than the whole collection.

> **NemoClaw note:** NemoClaw runs agents inside NVIDIA OpenShell with default-deny outbound networking. Skills are discovered and loaded normally, but any skill that needs the network — package installs via `uv`, or API calls (Exa, Parallel, Benchling, NCBI, Materials Project, …) — only works once the operator pre-approves the relevant domains in the OpenShell TUI.

**That's it!** A compatible host can discover the skills from its configured paths and use them when relevant. You can also invoke any skill manually by mentioning the skill name in your prompt.

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

Skills are scanned weekly — incrementally, so unchanged skills carry their previous findings forward, with a full rescan of everything at least every 30 days and whenever the scanner or model changes — and the results are published to [docs/security-report.md](docs/security-report.md). See [SECURITY.md](SECURITY.md) for our security policy, what is in scope, how to report a vulnerability privately, and how to contest a scan finding. We try to address security gaps as they arise.

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

## 🙏 Skill Credits

The **[docx](skills/docx/)**, **[pdf](skills/pdf/)**, **[pptx](skills/pptx/)**, and **[xlsx](skills/xlsx/)** document skills are created and maintained by **Anthropic** and vendored here from [anthropics/skills](https://github.com/anthropics/skills/tree/main/skills). They are used under Anthropic's terms — see each skill's `LICENSE.txt` — and we track upstream so you get their latest improvements. All credit for those four skills goes to Anthropic.

---

## ⚙️ Prerequisites

- **Python**: 3.13+ for repository tooling; individual skill dependencies may support broader Python ranges
- **uv**: Python package manager (required for installing skill dependencies)
- **Client**: Any agent that supports the [Agent Skills](https://agentskills.io/) standard (Cursor, Claude Code, Gemini CLI, Codex, Google Antigravity, etc.)
- **System**: macOS, Linux, or Windows with WSL2
- **Dependencies**: Automatically handled by individual skills (check `SKILL.md` files for specific requirements)

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
**Goal**: Prioritize EGFR inhibitor candidates for preclinical lung-cancer research

**Prompt**:
```
Use available skills you have access to whenever possible. Query ChEMBL for EGFR inhibitors (IC50 < 50nM), analyze structure-activity relationships 
with RDKit, generate improved analogs with datamol, perform virtual screening with DiffDock 
against AlphaFold EGFR structure, search PubMed for resistance mechanisms, check COSMIC for 
mutations, and create visualizations and a comprehensive report.
```

**Skills Used**: database-lookup, rdkit, datamol, diffdock, paper-lookup, scientific-visualization

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

**Skills Used**: scanpy, cellxgene-census, database-lookup, pydeseq2, arboreto

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

**Skills Used**: pydeseq2, pyopenms, database-lookup, statsmodels, scikit-learn

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

**Skills Used**: database-lookup, biopython, rdkit, diffdock, deepchem, medchem, molfeat

---

### 🏥 Research Variant Evidence Review
**Goal**: Annotate a synthetic or properly de-identified VCF for hereditary-cancer research and qualified review

**Prompt**:
```
Use available skills you have access to whenever possible. Work only with authorized synthetic
or de-identified data. Parse the VCF with pysam, annotate variants with Ensembl VEP, retrieve
ClinVar/COSMIC/NCBI Gene/UniProt evidence, and verify literature sources. Build an evidence-
traceable research summary with scientific-writing. If clinical-reports is used, create only a
visibly marked draft structure from a verified source-fact manifest for qualified review; do not
diagnose, assess individual risk, recommend treatment, or determine trial eligibility.
```

**Skills Used**: pysam, database-lookup, paper-lookup, scientific-writing, clinical-reports

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

**Skills Used**: database-lookup, torch-geometric, arboreto, pymc, networkx, scientific-visualization

> 📖 **Want more examples?** Check out [docs/examples.md](docs/examples.md) for comprehensive workflow examples and detailed use cases across all scientific domains.

---

## 🔬 Use Cases

### 🧪 Drug Discovery & Medicinal Chemistry
- **Virtual Screening**: Screen millions of compounds from PubChem/ZINC against protein targets
- **Lead Optimization**: Analyze structure-activity relationships with RDKit, generate analogs with datamol
- **ADMET Prediction**: Predict absorption, distribution, metabolism, excretion, and toxicity with DeepChem
- **Molecular Docking**: Predict binding poses with DiffDock and rescore poses with affinity-oriented tools
- **Bioactivity Mining**: Query ChEMBL for known inhibitors and analyze SAR patterns

### 🧬 Bioinformatics & Genomics
- **Sequence Analysis**: Process DNA/RNA/protein sequences with BioPython and pysam
- **Single-Cell Analysis**: Analyze 10X Genomics data with Scanpy, identify cell types, infer GRNs with Arboreto
- **Variant Annotation**: Annotate research VCF files with Ensembl VEP and retrieve ClinVar evidence for qualified interpretation
- **Variant Database Management**: Build scalable VCF databases with TileDB-VCF for incremental sample addition, efficient population-scale queries, and compressed storage of genomic variant data
- **Population Genomics**: Query variants, cohort sample IDs, and relatedness in the 3,202-person GRCh38 1000 Genomes cohort with OneKGPd
- **Regulatory Sequence Models**: Run hosted Genomic Intelligence promoter, splice, enhancer, chromatin, expression, and gene-annotation predictions for research—not clinical or diagnostic decisions
- **Pathogen Surveillance**: Track which viral lineages are circulating now and how fast they are growing (SARS-CoV-2, influenza including H5N1, RSV, mpox, measles, dengue) through the GenSpectrum LAPIS API, with reporting lag measured rather than assumed
- **Gene Discovery**: Query NCBI Gene, UniProt, and Ensembl for comprehensive gene information
- **Network Analysis**: Identify protein-protein interactions via STRING, map to pathways (KEGG, Reactome)

### 🏥 Clinical Research & Evidence Workflows
- **Clinical Trials**: Analyze aggregate trial landscapes and protocol criteria without deciding individual eligibility
- **Variant Evidence Review**: Annotate authorized research data with ClinVar, COSMIC, and ClinPGx; qualified professionals retain interpretation responsibility
- **Drug Safety Research**: Query FDA databases for aggregate adverse-event, interaction, and recall evidence
- **Clinical Pharmacology**: Derive exposure metrics from concentration-time data, fit compartmental and population PK models, relate exposure to effect, and evaluate dosing regimens, bioequivalence, and first-in-human dose
- **Full-Text Evidence Retrieval**: Search and read papers, regulatory filings, and trial records end to end with Paperclip, returning citations pinned to line numbers rather than to abstracts
- **Decision-Support Evaluation**: Prepare synthetic or aggregate evaluation, evidence-profile, privacy, and governance artifacts—not live clinical decisions
- **Clinician-Authored Documentation**: Structure verified source-bound report drafts and format treatment decisions already made by authorized licensed professionals

### 🔬 Multi-Omics & Systems Biology
- **Multi-Omics Integration**: Combine RNA-seq, proteomics, and metabolomics data
- **Pathway Analysis**: Enrich differentially expressed genes in KEGG/Reactome pathways
- **Network Biology**: Reconstruct gene regulatory networks, identify hub genes
- **Biomarker Discovery**: Integrate multi-omics layers to predict patient outcomes

### 📊 Data Analysis & Visualization
- **Statistical Analysis**: Perform hypothesis testing, power analysis, and experimental design
- **Publication Figures**: Create publication-quality visualizations with matplotlib and seaborn
- **Network Visualization**: Visualize biological networks with NetworkX
- **Report Generation**: Produce evidence-traceable research reports with Scientific Writing and document tools; Clinical Reports outputs remain visibly marked drafts built only from verified synthetic, de-identified, or aggregate source facts

### 🧪 Laboratory Automation
- **Protocol Design**: Author and simulate Opentrons or PyLabRobot protocols before trained-operator review
- **LIMS/ELN Integration**: Prepare scoped Benchling and LabArchives operations with explicit authorization for remote writes
- **Workflow Automation**: Validate and simulate multi-step laboratory workflows offline; physical execution stays behind equipment-specific operator safety gates

---

## 📚 Available Skills

This repository contains **164 scientific and research skills** organized across multiple domains. Each skill provides comprehensive documentation, code examples, and best practices for working with scientific libraries, databases, and tools.

### Skill Categories

> **Note:** The Python package and integration skills listed below are *explicitly defined* skills — curated with documentation, examples, and best practices for stronger, more reliable performance. They are not a ceiling: the agent can install and use *any* Python package or call *any* API, even without a dedicated skill. The skills listed simply make common workflows faster and more dependable.

#### 🧬 **Bioinformatics & Genomics** (27 skills)
- RNA-seq pipelines: Bulk RNA-seq (end-to-end FASTQ -> counts -> DE -> enrichment orchestrator)
- Sequence analysis: BioPython, pysam, scikit-bio, BioServices
- Single-cell analysis: Scanpy, AnnData, scvi-tools, scVelo (RNA velocity), Arboreto, Cellxgene Census
- Genomic tools: gget, current geniml/Gtars interval workflows, deepTools, FlowIO, Polars-Bio, Zarr, TileDB-VCF
- Coordinate hygiene: Genomic Coordinates (convert intervals across BED/GFF/GTF/VCF/SAM/WIG conventions, normalise variant representations, and catch 0-based vs 1-based and assembly/contig-naming mismatches before they corrupt an analysis)
- Population and sequence intelligence: OneKGPd (individual-level 1000 Genomes cohort queries) and Genomic Intelligence (hosted regulatory/gene-expression predictions; research only)
- Differential expression: PyDESeq2
- Functional enrichment: Pathway Enrichment (ORA, GSEA/preranked, ssGSEA via gseapy + g:Profiler; GO, KEGG, Reactome, WikiPathways, MSigDB)
- Phylogenetics: ETE Toolkit, Phylogenetics (MAFFT, IQ-TREE 2, FastTree)
- Microbiome foundation models: Waypoint (Outpost Bio's open Waypoint-6m/45m/170m checkpoints, the Atlas 539k-sample MGnify pretraining corpus, and the eight-task Compass benchmark — embedding, fine-tuning, benchmarking, and pretraining on taxonomic abundance profiles, with MetaPhlAn/Kraken2/QIIME 2 conversion)

#### 🧪 **Cheminformatics & Drug Discovery** (10 skills)
- Molecular manipulation: RDKit, Datamol, Molfeat
- Deep learning: DeepChem, TorchDrug
- Docking & screening: DiffDock
- Molecular dynamics: OpenMM + MDAnalysis (MD simulation & trajectory analysis)
- Cloud quantum chemistry: Rowan (pKa, docking, cofolding)
- Drug-likeness: MedChem
- Benchmarks: PyTDC 1.1.15 on its verified CPython 3.11 compatibility stack

#### 🔬 **Proteomics & Mass Spectrometry** (2 skills)
- Spectral processing: matchms, pyOpenMS

#### 🏥 **Clinical Research & Evidence Workflows** (8 skills)
- Clinical databases: via Database Lookup (ClinicalTrials.gov, ClinVar, ClinPGx, COSMIC, FDA, cBioPortal, Monarch, and more)
- Clinical pharmacology: PK/PD Modeling (non-compartmental analysis, compartmental and population PK, exposure-response and Emax, TMDD, PBPK orientation, bioequivalence including RSABE/ABEL, allometric scaling and first-in-human dose, DDI prediction under ICH M12, concentration-QTc, and Bayesian therapeutic drug monitoring — stdlib + numpy/scipy, no proprietary estimation software invoked)
- Cancer genomics: DepMap (cancer dependency scores, drug sensitivity)
- Cancer imaging: Imaging Data Commons (NCI radiology & pathology datasets via idc-index)
- Healthcare AI research: PyHealth
- Decision-support research: local, aggregate or synthetic Clinical Decision Support evaluation and governance artifacts only
- Clinical documentation: source-bound Clinical Reports drafts and formatting of verified clinician-authored decisions with Treatment Plans; neither skill diagnoses or recommends care

#### 🐭 **Preclinical Research & Animal Welfare** (1 skill)
- Severity assessment: RELSA Severity Assessment (multivariate RELSA scores from body weight, temperature, clinical/nesting scores, biomarkers, activity, heart rate, burrowing and wheel running; ARIMA humane-endpoint forecasting with 95% prediction intervals; KDE-derived attention and danger zones for 3Rs/refinement and EU Directive 2010/63/EU severity reporting) — an aid to severity assessment, never a decision rule

#### 🖼️ **Medical Imaging & Digital Pathology** (4 skills)
- DICOM processing: pydicom 3.0.2 with privacy-first local preflight and no diagnostic or de-identification-compliance claims
- Whole slide imaging: histolab and research-only PathML 3.0.5
- Virtual spatial transcriptomics: noncommercial DeepSpot-M for transcriptome-wide spatial gene expression from 224x224 H&E tiles

#### 🧠 **Neuroscience & Electrophysiology** (3 skills)
- Data standards: BIDS (Brain Imaging Data Structure for neuroscience and biomedical datasets)
- Neural recordings: Neuropixels-Analysis (extracellular spikes, silicon probes, spike sorting)
- Physiological signals: NeuroKit2 0.2.13 for reproducible research workflows—not diagnosis, monitoring decisions, or medical-device validation

#### 🤖 **Machine Learning & AI** (14 core skills)
- Deep learning: PyTorch Lightning, Transformers, Stable Baselines3, and version-separated PufferLib 3.0/4.0 workflows
- Classical ML: scikit-learn, scikit-survival 0.28, and SHAP
- Time series: aeon, TimesFM (Google's zero-shot foundation model for univariate forecasting)
- Bayesian methods: PyMC
- Optimization: PyMOO
- Graph ML: Torch Geometric
- Dimensionality reduction: UMAP-learn
- Statistical modeling: statsmodels

#### 🔮 **Materials Science, Chemistry & Physics** (7 skills)
- Materials: current split pymatgen wrapper/core plus explicitly bounded Materials Project queries
- Metabolic modeling: COBRApy
- Astronomy: Astropy
- Quantum computing: Cirq, PennyLane, Qiskit, QuTiP 5.3

#### ⚙️ **Engineering & Simulation** (6 skills)
- Lab hardware CAD: parametric build123d 0.11.1 models for microfluidic chips and molds, optomechanical mounts, microplate and cuvette adapters, and behavior rigs, checked against ANSI/SLAS and optical-table dimensional standards and reviewed with mandatory multi-view renders
- Numerical computing: proprietary MATLAB R2026a and distinct GNU Octave 11.3 planning/review workflows
- Computational fluid dynamics: bounded FluidSim 0.9 simulations with numerical-validity and HPC checks
- Experimental flow measurement: OpenPIV (velocity fields from PIV image pairs, interrogation-window cross-correlation, spurious-vector validation, vorticity/strain-rate/turbulence statistics)
- Discrete-event simulation: SimPy 4.1.2 with replication, warm-up, and output-analysis guidance
- Symbolic math: SymPy

#### 📊 **Data Analysis & Visualization** (22 skills)
- Visualization: Matplotlib, Seaborn, Scientific Visualization
- Geospatial analysis: GeoPandas 1.1.4 and GeoMaster (remote sensing, GIS, satellite imagery, spatial ML, 500+ examples)
- Data processing: Dask, Polars, Vaex
- Network analysis: NetworkX
- Document processing: LiteParse (local PDF/document parsing with bounding boxes and OCR), MarkItDown, PDF, DOCX, PPTX, and XLSX
- Infographics: Infographics (AI-powered professional infographic creation)
- Diagrams: Markdown & Mermaid Writing (text-based diagrams as default documentation standard)
- Exploratory data analysis: bounded local EDA for explicitly supported formats, with unknown formats failing closed
- Statistical analysis: Statistical Analysis workflows
- Units and measurement uncertainty: Uncertainty & Units (pint dimensional checking, GUM uncertainty budgets, Type A/B evaluation, coverage factors and expanded uncertainty, Monte Carlo propagation, CODATA constants)
- Experimental design: Experimental Design (randomization, blocking, factorial/fractional-factorial DOE, crossover, cluster, sequential designs; pyDOE3)
- Statistical power: Statistical Power (sample-size & power for t-tests, ANOVA, proportions, correlation, regression — closed-form plus simulation-based for GLMs, mixed models, and cluster designs)

#### 🧪 **Laboratory Automation** (6 skills)
- Liquid handling: offline-first PyLabRobot planning/simulation and Opentrons authoring, with physical execution behind explicit operator safety gates
- Cloud lab: Ginkgo Cloud Lab (protein expression & purification across cell-free/E. coli/Pichia, IVT RNA synthesis, thermal shift and Echo-MS assays, SPR onboarding, fluorescent pixel art via autonomous RAC infrastructure)
- Protocol management: bounded protocols.io reads across documented v3/v4 endpoints and non-executing write plans
- LIMS/ELN integration: Benchling and the separate LabArchives legacy ELN and Inventory v1 APIs

#### 🔬 **Multi-omics & Systems Biology** (3 skills)
- Pathway analysis: via Database Lookup (KEGG, Reactome, STRING) and PrimeKG
- Data management: LaminDB

#### 🧬 **Protein Engineering & Design** (4 skills)
- Protein language models: ESM
- Glycoengineering: Glycoengineering (N/O-glycosylation prediction, therapeutic antibody optimization)
- Cloud laboratory platform: Adaptyv (automated protein testing and validation)
- Cloud structure & design platform: Tamarind (managed-GPU access to AlphaFold, Boltz, Chai, ESMFold, RFdiffusion, ProteinMPNN, BoltzGen, antibody/nanobody design, DiffDock/Vina docking, binding affinity, and MSA generation via REST API or MCP)

#### 📚 **Scientific Communication** (28 skills)
- Literature: Paper Lookup (PubMed, PMC, bioRxiv, medRxiv, arXiv, OpenAlex, Crossref, Semantic Scholar, CORE, Unpaywall), Literature Review, Paperzilla
- Full-text corpus access: Paperclip (read-only virtual filesystem over ~11M full-text papers, 217K+ FDA/PMDA/EMA regulatory documents, clinical trial registries, and UniProt/PDB/ChEMBL entries — source-scoped semantic search, corpus-wide grep, SQL metadata queries, map/reduce reading across many papers, figure vision analysis, and line-pinned citations)
- Advanced paper search: BGPT Paper Search (25+ structured fields per paper — methods, results, sample sizes, quality scores — from full text, not just abstracts) and Firecrawl Research (semantic paper search plus question-directed retrieval of the passages inside a paper, related-work expansion by co-citation/citers/references, and GitHub history search for implementation prior art)
- Web intelligence: Parallel Web (web search, URL/PDF extraction, deep research, structured enrichment, entity discovery, and recurring monitoring), Exa Search, and Research Lookup
- Research notebooks: Open Notebook (self-hosted NotebookLM alternative — PDFs, videos, audio, web pages; 16+ AI providers; multi-speaker podcast generation)
- Writing: evidence-traceable Scientific Writing and local, confidential, authorized Peer Review
- Document processing: LiteParse, PDF, DOCX, PPTX, XLSX, and MarkItDown
- Publishing and paper workflows: Venue Templates
- Presentations: Scientific Slides, LaTeX Posters, and macro-free PPTX Posters generated from author-approved local manifests
- Diagrams: Scientific Schematics, Markdown & Mermaid Writing
- Infographics: Infographics (10 types, 8 styles, colorblind-safe palettes)
- Citations: Citation Management, pyzotero
- Illustration: Generate Image (AI image generation with FLUX.2 Pro and Gemini 3.1 Flash Image / Nano Banana 2)

#### 🔬 **Scientific Databases & Data Access** (11 skills → 100+ databases total)
> A unified database-lookup skill provides deterministic REST API access to 78 public databases across all domains, with retrieval contracts, pagination/count reconciliation, and endpoint provenance. Dedicated skills cover specialized data platforms. Multi-database packages like BioServices (~40 bioinformatics services), BioPython (39 NCBI sub-databases via Entrez), and gget (20+ genomics databases) add further coverage.
- Unified access: Database Lookup (78 databases spanning chemistry, genomics, clinical, pathways, patents, economics, and more — PubChem, ChEMBL, UniProt, PDB, AlphaFold, KEGG, Reactome, STRING, ClinVar, COSMIC, ClinicalTrials.gov, FDA, FRED, USPTO, SEC EDGAR, and dozens more — with auditable filters and provenance)
- Cancer genomics: DepMap (cancer cell line dependencies, drug sensitivity, gene effect profiles)
- Cancer imaging: Imaging Data Commons (NCI radiology & pathology datasets via idc-index)
- Knowledge graph: PrimeKG (precision medicine knowledge graph — genes, drugs, diseases, phenotypes)
- Biomedical knowledge graph search: [NCATS ARAX](skills/ncats-arax/) (bounded, Biolink-constrained one-hop and endpoint-pinned two-hop queries over knowledge graphs with up to five explicitly selected NCATS Translator providers, with provenance preservation)
- Fiscal data: U.S. Treasury Fiscal Data (national debt, Treasury statements, auctions, exchange rates)
- Scientific ML resource catalog: Hugging Science (curated index of datasets, models, blog posts, and interactive Spaces across 17 scientific domains — astronomy, biology, chemistry, climate, genomics, materials science, medicine, physics, scientific reasoning, and more — with usage patterns for `datasets`, `transformers`, and `gradio_client`)
- Individual-level population genomics: OneKGPd (3,202-person high-coverage 1000 Genomes cohort queries)
- Hosted regulatory genomics: Genomic Intelligence (promoter, splice, enhancer, chromatin, expression, and gene-annotation predictions for research use)
- Ontology identifiers: Ontology Term Resolution (resolve free-text tissue, cell-type, disease, phenotype, assay, chemical, organism, and developmental-stage labels to term IDs and validate CURIEs against EBI OLS4, for GEO/ENA/BioSamples/CELLxGENE/HCA/ISA-Tab metadata)
- Live pathogen surveillance: Pathogen Variant Surveillance (which viral lineages are circulating now, how fast they are growing, and what mutations they carry — SARS-CoV-2, influenza including H5N1, RSV, mpox, measles, dengue and more through the GenSpectrum LAPIS API, with lineage names resolved against the live pango-designation nomenclature and reporting lag measured rather than assumed)

#### 🔧 **Infrastructure & Platforms** (11 skills)
- Cloud compute: Modal
- GPU acceleration: Optimize for GPU (CuPy, Numba CUDA, Warp, cuDF, cuML, cuGraph, KvikIO, cuCIM, cuxfilter, cuVS, cuSpatial, RAFT)
- Genomics platforms: DNAnexus, LatchBio
- Workflow engines: Nextflow (build/run/debug Nextflow & nf-core pipelines — DSL2 modules, executors/containers, HPC/cloud scaling) and pacsomatic (operator toolkit for the nf-core/pacsomatic tumor-normal somatic variant-calling workflow)
- Microscopy: OMERO
- Automation: Opentrons
- Resource detection: Get Available Resources on request or before a clearly resource-sensitive local workload; redacted and without stress tests
- Workflow mining: Autoskill (local screenpipe-based repeated workflow detection and skill drafting)
- Agent platform development: Pi Agent (using Pi as a terminal coding harness and building on it with SDK, RPC/JSONL, extensions, custom providers/models, packages, TUI components, and session tooling)

#### 🎓 **Research Methodology & Planning** (13 skills)
- Ideation: evidence-aware Scientific Brainstorming and non-scoring Hypothesis Generation that keeps hypotheses labeled as candidates
- Text-dataset hypothesis software: HypoGeniC/HypoRefine produces candidate textual patterns and task-prediction statistics, not validated scientific hypotheses
- Autonomous optimization: Arbor (Hypothesis Tree Refinement — iteratively improve a code/model/agent-harness/data artifact against a dev evaluator while a held-out test gate guards against overfitting)
- Critical analysis: Scientific Critical Thinking and qualitative, low-stakes Scholar Evaluation of works—never ranking people or supporting consequential decisions
- Scenario analysis: What-If Oracle (4–6 branch possibility exploration, contingency planning, decision stress-testing)
- Multi-perspective deliberation: Consciousness Council (diverse expert viewpoints, devil's advocate analysis)
- Cognitive profiling: DHDNA Profiler (extract thinking patterns and cognitive signatures from any text)
- Funding: Research Grants
- Discovery: Research Lookup, Paper Lookup (10 academic databases)
- Market analysis: evidence-traceable Market Research Reports with assumption-led sizing and forecast sensitivity

#### ⚖️ **Regulatory & Standards** (2 skills)
- Standards readiness: draft evidence-preparation artifacts for ISO 13485 (medical device QMS), ISO 14971 (device risk management), ISO/IEC 17025 (testing and calibration laboratories), and ISO 15189 (medical laboratories), with per-standard process domains selected by a `--standard` profile
- Analytical method validation: plan, evaluate, and document validation, verification, and transfer of analytical procedures (HPLC, LC-MS/MS, GC, CE, ICP-MS, dissolution, qNMR, qPCR, NIR, ligand-binding and cell-based assays) under whichever framework governs — ICH Q2(R2)/Q14 and ICH M10 encoded from their openly licensed text, with USP `<1220>`/`<1225>`/`<1226>`, the CLSI EP series, and ISO/IEC 17025 cited by designation and scope only; stdlib-only statistics, no network access
- Assurance-lane separation: keeps ISO certification, laboratory accreditation, FDA QMSR inspection, CLIA certification, MDSAP, and EU MDR/IVDR evidence boundaries distinct—laboratories are accredited rather than certified, and ISO 15189 accreditation does not satisfy CLIA
- Never a compliance, audit, assessment, certification, accreditation, or method-release decision; qualified RA/QA, legal, laboratory-director, assessor, and certification-body review is required

> 📖 **For complete details on all skills**, see [docs/skills.md](docs/skills.md)

> 💡 **Looking for practical examples?** Check out [docs/examples.md](docs/examples.md) for comprehensive workflow examples across all scientific domains.

---

## 📝 From the Blog

Deep dives, benchmarks, and guides from the [K-Dense blog](https://www.k-dense.ai/blog) that are directly relevant to using the skills in this repository.

### Start here

- **[Agent Skills: The Final Piece for AI-Powered Scientific Research](https://www.k-dense.ai/blog/agent-skills-final-piece-for-ai-powered-research)** — What Agent Skills are, why curated domain guidance beats raw model capability, and an introduction to this repository.
- **[K-Dense Web vs Scientific Agent Skills: Why We Built Both (And Which One You Should Use)](https://www.k-dense.ai/blog/k-dense-web-vs-scientific-agent-skills)** — When the open-source skills are the right tool, and when a hosted platform with managed compute makes more sense.
- **[AI Co-Scientists, Answered: 20 Questions from a Live Session with a University Research Center](https://www.k-dense.ai/blog/ai-co-scientists-answered-20-questions)** — Practical questions from a research center evaluating AI co-scientists: what stays open source and MIT-licensed, how local and desktop deployments work, how data is handled, and how to choose between the hosted platform and the BYOK setup that runs these skills.
- **[How to Use Multica for Scientific Research](https://www.k-dense.ai/blog/multica-scientific-research)** — A self-hosted Multica workspace plus a curated subset of these skills: clinical-trial and variant analyses, literature review, weekly autopilots, and a second-model audit, with each skill imported from `skills/<name>/`.

### Skill benchmarks and deep dives

- **[The Silent 97%: Introducing the waypoint-bio Agent Skill](https://www.k-dense.ai/blog/introducing-waypoint-agent-skill)** — [waypoint-bio](skills/waypoint-bio/) against silent data loss: an unconverted MetaPhlAn table keeps 3% of abundance mass and still returns a valid embedding; skill-equipped agents won 16 to 0 on matched pairs.
- **[The Millimetre Problem: Introducing the lab-hardware-cad Agent Skill](https://www.k-dense.ai/blog/lab-hardware-cad-skill)** — [lab-hardware-cad](skills/lab-hardware-cad/) over 98 geometry-scored runs: the skill arm produced parametric, regenerable models in 49 of 49 cases (baseline 0 of 49) and named the missing Y-maze standard instead of inventing one.
- **[One Skill, 78 Databases: Why We Didn't Build 78 Skills](https://www.k-dense.ai/blog/database-lookup-one-skill-78-databases)** — The design rationale behind [database-lookup](skills/database-lookup/): consolidation cut always-on context cost by 13.9x while holding routing accuracy across five models.
- **[Can an AI Agent Run Your Mass Spec Pipeline? Benchmarking the PyOpenMS Skill](https://www.k-dense.ai/blog/benchmarking-pyopenms-skill-mass-spectrometry)** — A 250-run study of [pyopenms](skills/pyopenms/): 100% task success with the skill versus 96% without, 92% fewer pyOpenMS API errors, and 10% lower cost.
- **[Beyond RDKit: Benchmarking the Rowan Agent Skill Against Experiment](https://www.k-dense.ai/blog/benchmarking-rowan-skill-chemistry)** — [rowan](skills/rowan/) compared against RDKit and experimental data: pKa MAE 0.23 (R² 0.986), logD₇.₄ MAE 1.15, and 0.19 Å RMSD docking pose recovery for roughly $0.52 of compute.
- **[GPU-Accelerate Your Science: 58x Average Speedup with a Single Skill](https://www.k-dense.ai/blog/optimize-for-gpu-skill)** — [optimize-for-gpu](skills/optimize-for-gpu/) rewriting CPU-bound Python across 12 libraries, with speedups ranging from 1.7x to 492x.
- **[Towards Smarter Scientific Search: Exa Joins the Scientific Agent Skills Library](https://www.k-dense.ai/blog/towards-smarter-scientific-search-exa-scientific-agent-skills)** — What [exa-search](skills/exa-search/) adds: neural semantic search and URL extraction tuned for scholarly discovery instead of keyword matching.
- **[Benchmarking Nano Banana 2 Lite for Scientific Image Generation](https://www.k-dense.ai/blog/benchmarking-nano-banana-2-lite-scientific-image-model)** — A 240-image comparison of scientific-diagram models, useful when choosing a backend for [generate-image](skills/generate-image/): 3.8 s median latency for Nano Banana 2 Lite against 49 s for GPT Image 2, with a quality tradeoff.
- **[Benchmarking NVIDIA BioNeMo Agent Toolkit Skills for NIM microservices](https://www.k-dense.ai/blog/benchmarking-nvidia-bionemo-nim-skill)** — A separate NVIDIA skill set rather than one of these, but the findings generalize: skills help most with routing to non-obvious endpoints and with weak-model reliability, and do not improve the underlying scientific model's accuracy.

### Why the workflow layer matters

- **[The Model Is No Longer the Bottleneck](https://www.k-dense.ai/blog/the-model-is-no-longer-the-bottleneck)** — The case for why a repository like this one exists: frontier models now match specialized scientific software on raw capability (±0.079 ppm on NMR hydrogen shift prediction), so the limiting factor has moved to the workflow around the model — data access, code execution, verification, and auditable output.
- **[The AI Co-Scientist Is Here. The Bottleneck Is Verification.](https://www.k-dense.ai/blog/ai-co-scientist-verification-bottleneck)** — A 10-point checklist for evaluating a research agent, built around exposing sources, code, data provenance, and intermediate work rather than a polished final answer — the same reasoning behind the provenance and retrieval-contract requirements in skills like [database-lookup](skills/database-lookup/) and [scientific-writing](skills/scientific-writing/).
- **[Reproduction, Not Generation, Is AI's Killer App for Science](https://www.k-dense.ai/blog/reproduction-not-generation-ai-for-science)** — Why re-running published analyses is the highest-value use of an agent: 78% of papers and 93% of individual analysis tasks reproduced across a 221-study benchmark, because a reproduction can be checked against known numbers while a generated claim cannot.
- **[Introducing K-Bench 01: Nine Frontier Models, 178 Real Scientific Tasks, and a Lot of Confident Wrong Answers](https://www.k-dense.ai/blog/introducing-k-bench-01-internal-benchmark)** — Nine frontier models on 178 real user tasks, with overclaiming in 40% of runs. Useful calibration for what to check when an agent reports success, and context for the verification boundaries written into the clinical, regulatory, and research-methodology skills above.

### Security and safe deployment

- **[Security in the Science Agent Era: What Every Lab Needs to Know Before Installing Skills](https://www.k-dense.ai/blog/skill-security-before-you-install)** — The practical review checklist behind this repo's [Security Disclaimer](#%EF%B8%8F-security-disclaimer): read the full `SKILL.md` and `scripts/`, scan before installing, and pin versions instead of tracking a branch.
- **[The Sandboxed AI Scientist: Pairing NVIDIA OpenShell with Scientific Agent Skills](https://www.k-dense.ai/blog/sandboxed-ai-scientist-openshell-skills)** — Running these skills inside a policy-governed sandbox; see also the NemoClaw note in [Getting Started](#-getting-started).

### Complementary open-source projects

- **[Introducing Science Superpowers: Scientific Discipline for Your Research Agent](https://www.k-dense.ai/blog/introducing-science-superpowers)** — Hypothesis pre-registration, reproducible workflows, and verification-before-claims that wrap around these skills to guard against p-hacking and HARKing.
- **[Your AI Assistant Reasons Like a Generalist. Science Needs a Specialist.](https://www.k-dense.ai/blog/introducing-scientific-agents)** — 503 open-source `AGENTS.md` profiles supplying the "how to think" layer alongside the "what to do" procedures in these skills.
- **[Introducing mimeo and 80+ Mimeographs](https://www.k-dense.ai/blog/introducing-mimeo-and-mimeographs)** — Generate your own `SKILL.md` / `AGENTS.md` expert profiles by distilling how a given practitioner reasons.
- **[Agentic Data Scientist: An Open Source AI That Actually Does the Analysis](https://www.k-dense.ai/blog/agentic-data-scientist-open-source)** — A multi-agent planning, execution, and validation harness that loads these skills for end-to-end data-science workflows.
- **[Karpathy: An Open Source Agentic Machine Learning Engineer](https://www.k-dense.ai/blog/karpathy-agentic-ml-engineer)** — An autonomous ML-training agent built to consume Scientific Agent Skills for preprocessing through hyperparameter search.

---

## 🤝 Contributing

We welcome contributions to expand and improve this scientific skills repository!

For detailed instructions on adding or updating a skill, see [CONTRIBUTING.md](CONTRIBUTING.md). The guide covers repository structure, required `SKILL.md` frontmatter, Agent Skills specification requirements, versioning, validation, security scanning, and pull request expectations.

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
3. **Follow** [CONTRIBUTING.md](CONTRIBUTING.md) and the existing directory structure
4. **Ensure** all new skills include valid `SKILL.md` files with required frontmatter and `metadata.version`
5. **Test** your examples and workflows thoroughly, and add a suite under `tests/<skill-name>/` if your skill ships `scripts/`
6. **Commit** your changes (`git commit -m 'Add amazing skill'`)
7. **Push** to your branch (`git push origin feature/amazing-skill`)
8. **Submit** a pull request with a clear description of your changes

### Contribution Guidelines

✅ **Adhere to the [Agent Skills Specification](https://agentskills.io/specification)** — Every skill must follow the official spec (valid `SKILL.md` frontmatter, naming conventions, directory structure)  
✅ Include a quoted `metadata.version` value in every `SKILL.md`  
✅ Increment `metadata.version` when updating an existing skill  
✅ Maintain consistency with existing skill documentation format  
✅ Ensure all code examples are tested and functional  
✅ Follow scientific best practices in examples and workflows  
✅ Update relevant documentation when adding new capabilities  
✅ Provide clear comments and docstrings in code  
✅ Include references to official documentation

### Testing

Every skill that ships `scripts/` must have a test suite under `tests/<skill-name>/` and an entry in `tests/skill-requirements.toml`. This is enforced — `tests/_meta` fails a pull request that adds bundled tooling without one, and it also runs a repo-wide structural contract over all skills (frontmatter conformance, `SKILL.md` length, local links resolving, scripts parsing, no shipped bytecode, no hardcoded local paths, `--help` behavior).

```bash
# Structural contract and coverage guard — seconds, no scientific packages needed
uv run python -m pytest tests/_meta -q

# One skill's suite
uv run --with pytest python -m pytest tests/<skill-name> -q

# Every suite, each in its own throwaway environment
uv run python tests/run_all.py --isolated
```

The [Skill Tests](https://github.com/K-Dense-AI/scientific-agent-skills/actions/workflows/skill-tests.yml) workflow runs the contract plus the standard-library-only suites on every pull request; the full `--isolated` sweep builds ~100 environments and is run locally or on a schedule.

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
- Verify skill folders are in the correct directory (see [Getting Started](#-getting-started))
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

**Problem: `gh skill install` or docs link to `scientific-skills/` fails (v2.43.0+)**
- As of v2.43.0, skills live under `skills/` (not `scientific-skills/`) to match the Agent Skills layout expected by GitHub CLI
- Update manual copy paths, bookmarks, and citations from `scientific-skills/<name>` to `skills/<name>`
- Re-run `gh skill install K-Dense-AI/scientific-agent-skills` after pulling the latest release

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
A: The core `SKILL.md` format follows the open [Agent Skills](https://agentskills.io/) standard. Installation paths, discovery, and optional metadata support vary by host and version, so confirm your target host's current documentation.

### Installation & Setup

**Q: Do I need all the Python packages installed?**  
A: No! Only install the packages you need. Each skill specifies its requirements in its `SKILL.md` file.

**Q: What if a skill doesn't work?**  
A: First check the [Troubleshooting](#-troubleshooting) section. If the issue persists, file an issue on GitHub with detailed reproduction steps.

**Q: Do the skills work offline?**  
A: Database skills require internet access to query APIs. Package skills work offline once Python dependencies are installed.

### Contributing

**Q: Can I contribute my own skills?**  
A: Absolutely! We welcome contributions. See the [Contributing](#-contributing) section for guidelines and best practices.

**Q: How do I report bugs or suggest features?**  
A: Open an issue on GitHub with a clear description. For bugs, include reproduction steps and expected vs actual behavior.

---

## 💬 Support

Need help? Here's how to get support:

- 📖 **Documentation**: Check the relevant `SKILL.md` and `references/` folders
- 🐛 **Bug Reports**: [Open an issue](https://github.com/K-Dense-AI/scientific-agent-skills/issues)
- 💡 **Feature Requests**: [Submit a feature request](https://github.com/K-Dense-AI/scientific-agent-skills/issues/new)
- 📣 **Updates and demos**: Follow [X](https://x.com/k_dense_ai), [LinkedIn](https://www.linkedin.com/company/k-dense-inc), [YouTube](https://www.youtube.com/@K-Dense-Inc), and [Reddit](https://www.reddit.com/user/-k-dense-/) to keep up with new skills, tutorials, and Scientific Agent Skills releases
- 💼 **Enterprise Support**: Contact [K-Dense](https://k-dense.ai/) for commercial support

---

## 📖 Citation

If you use Scientific Agent Skills in your research or project, please cite the overall collection and, when relevant, the individual skill or skills that materially supported your work.

The collection citation helps others find the repository, understand the broader skill ecosystem used in your workflow, and credit the maintenance effort behind Scientific Agent Skills. Individual skill citations give more precise credit for the specific package, database, or workflow guidance your agent used.

Recommended practice:
- Always cite **Scientific Agent Skills** using one of the formats below.
- Also cite each individual skill that directly contributed to your analysis, code, figures, reports, or research workflow.
- If a skill wraps or documents an external package, database, or platform, cite that upstream project too when your field's norms require it.

### Collection Citation

#### BibTeX
```bibtex
@software{scientific_agent_skills_2026,
  author = {{K-Dense Inc.}},
  title = {Scientific Agent Skills: A Comprehensive Collection of Scientific Tools for AI Agents},
  year = {2026},
  url = {https://github.com/K-Dense-AI/scientific-agent-skills},
  note = {164 skills covering databases, packages, integrations, and analysis tools}
}
```

#### APA
```
K-Dense Inc. (2026). Scientific Agent Skills: A comprehensive collection of scientific tools for AI agents [Computer software]. https://github.com/K-Dense-AI/scientific-agent-skills
```

#### MLA
```
K-Dense Inc. Scientific Agent Skills: A Comprehensive Collection of Scientific Tools for AI Agents. 2026, github.com/K-Dense-AI/scientific-agent-skills.
```

#### Plain Text
```
Scientific Agent Skills by K-Dense Inc. (2026)
Available at: https://github.com/K-Dense-AI/scientific-agent-skills
```

### Individual Skill Citation

When citing a specific skill, include the skill name, version from `metadata.version` in that skill's `SKILL.md`, and the direct skill URL. For example:

```bibtex
@software{scientific_agent_skills_astropy_2026,
  author = {{K-Dense Inc.}},
  title = {Astropy Skill for Scientific Agent Skills},
  year = {2026},
  url = {https://github.com/K-Dense-AI/scientific-agent-skills/tree/main/skills/astropy},
  note = {Version 1.0, part of Scientific Agent Skills}
}
```

Plain text format:

```text
Astropy skill for Scientific Agent Skills, version 1.0.
K-Dense Inc. (2026).
https://github.com/K-Dense-AI/scientific-agent-skills/tree/main/skills/astropy
```

We appreciate acknowledgment in publications, presentations, or projects that benefit from these skills.

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
