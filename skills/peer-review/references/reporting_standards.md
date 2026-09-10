# Reporting Guidelines and Domain Metadata Standards

Verified against primary or official sources on **2026-07-23**. The dated evidence record is `assets/source_ledger.csv`; the machine-readable selector catalog is `assets/reporting_guidelines.json`.

## What reporting guidelines do—and do not do

A reporting guideline identifies information that should be reported so readers can understand and appraise a study. It is not, by itself:

- A method for designing or conducting the study
- A risk-of-bias tool
- A statistical reanalysis
- A measure of truth, importance, novelty, or manuscript merit
- A publication recommendation

Checklist completion must never be converted automatically into a quality score. A fully reported study can have serious design problems; an incompletely reported study may be impossible to assess. Record missing information as a reporting gap, then separately assess any design, conduct, analysis, reproducibility, or ethics concern using appropriate evidence and expertise.

Use the guideline’s current statement together with its explanation and elaboration. Check applicable extensions and the target venue’s instructions. Do not copy checklist wording into a review when a specific, contextual comment is more useful.

## Selection workflow

1. Identify the **report kind**: results, protocol, abstract, or data release.
2. Identify the **study design**, not merely the topic or journal section.
3. Add cross-cutting features: AI intervention, diagnostic AI, routinely collected data, clustered design, qualitative interviews, and so on.
4. Select the current base guideline and applicable extensions.
5. Use the official checklist to record `reported`, `partly_reported`, `not_reported`, `not_applicable`, or `not_assessed`.
6. Explain `not_applicable`; do not treat it as a defect.
7. Keep reporting coverage separate from methodological appraisal.

Run:

```bash
python3 scripts/select_reporting_guidelines.py \
  assets/study_profile_template.json \
  --coverage assets/reporting_checklist_template.csv
```

The bundled catalog is a dated aid, not a live registry. Consult the [EQUATOR Network](https://www.equator-network.org/) and official guideline site when the study type is unclear or a newer extension may apply.

## Major current health-research guidelines

### Randomized trial results — CONSORT 2025

- Current statement: **CONSORT 2025**, published 14 April 2025
- Structure: 30 main checklist items and a participant flow diagram
- Supersedes: CONSORT 2010
- Use for: reports of randomized trials
- Review with: explanation and elaboration plus design/intervention extensions
- Important boundary: the statement explicitly says it is not a quality assessment instrument

Check registration, protocol and statistical analysis plan consistency, allocation, participant flow, outcomes and harms, effect estimates and uncertainty, protocol changes, data sharing, conflicts, and patient/public involvement where applicable.

Official sources: [CONSORT–SPIRIT](https://www.consort-spirit.org/) and the [CONSORT 2025 statement](https://www.bmj.com/content/389/bmj-2024-081123).

### Randomized trial protocols — SPIRIT 2025

- Current statement: **SPIRIT 2025**, published 28 April 2025
- Structure: 34 main checklist items and a participant timeline
- Supersedes: SPIRIT 2013
- Use for: randomized trial protocols

Compare the protocol with registration, statistical analysis plan, ethics records, amendments, and any completed-trial report. Explicitly stated non-applicability with rationale is not missing reporting.

Official sources: [CONSORT–SPIRIT](https://www.consort-spirit.org/) and the [SPIRIT 2025 statement](https://www.bmj.com/content/389/bmj-2024-081477).

### Systematic reviews — PRISMA 2020

- Current statement: **PRISMA 2020** (named 2020; published 2021)
- Structure: 27 main items, expanded checklist, abstract checklist, and flow diagrams
- Use for: completed systematic reviews, primarily reviews of intervention effects
- Protocols: use PRISMA-P
- Extensions: use the appropriate extension for scoping, diagnostic, individual-participant-data, network, equity, harms, or other specialized reviews

PRISMA explicitly does not assess review conduct or methodological quality. Use appropriate methods and risk-of-bias tools separately.

Official sources: [PRISMA 2020 resources](https://www.prisma-statement.org/prisma-2020) and the [primary statement](https://www.bmj.com/content/372/bmj.n71).

### Observational studies — STROBE

- Current base statement: **STROBE 2007**
- Structure: 22 main items with cohort, case-control, cross-sectional, and combined checklists
- Use for: reports of observational epidemiologic studies
- Extensions: examples include RECORD for routinely collected health data, STREGA for genetic association studies, STROBE-MR, and domain-specific extensions

STROBE helps identify whether selection, measurement, bias, confounding, missing data, sensitivity analyses, and generalizability are reported. It does not establish that those methods were adequate.

Official source: [STROBE](https://www.strobe-statement.org/).

### Diagnostic accuracy — STARD 2015

- Current base statement: **STARD 2015**
- Structure: 30 main items and a flow diagram
- Use for: studies estimating diagnostic accuracy against a reference standard

Separately assess risk of bias and applicability with a suitable tool such as the current QUADAS family when relevant. STARD’s official implementation guidance explicitly says not to use the reporting checklist as a design-quality tool.

Official source: [STARD 2015](https://www.equator-network.org/reporting-guidelines/stard/).

### AI-centered diagnostic accuracy — STARD-AI

- Current statement: **STARD-AI 2025**
- Published: 15 September 2025; an author correction was published 13 July 2026
- Structure: 40 items, including 18 new or modified items relative to STARD 2015
- Use for: AI-centered diagnostic accuracy studies, including suitable diagnostic classification tasks

Check dataset practices, index-test specification, evaluation, algorithmic bias and fairness, applicability, and generalizability. If the primary aim is development or evaluation of a multivariable prediction model, use TRIPOD+AI instead.

Official source: [STARD-AI](https://www.nature.com/articles/s41591-025-03953-8).

### Clinical prediction models — TRIPOD+AI

- Current statement: **TRIPOD+AI 2024**
- Structure: 27 main items plus a 13-item abstract checklist
- Replaces: TRIPOD 2015
- Use for: development, evaluation, or updating of diagnostic or prognostic prediction models using regression or machine-learning methods

Do not select it solely because software called “AI” appears in a paper. Select it when the study’s primary object is a prediction model. Relevant extensions include TRIPOD-Cluster, TRIPOD-SRMA, and TRIPOD-LLM.

Official sources: [TRIPOD](https://www.tripod-statement.org/) and the [TRIPOD+AI statement](https://www.bmj.com/content/385/bmj-2023-078378).

### Case reports — CARE

- Current base checklist: **CARE 2013**
- Explanation and elaboration/manual: 2017
- Structure: 13 main items
- Use for: clinical case reports

Check timeline, diagnostic reasoning, interventions, outcomes, adverse events, patient perspective where available, informed consent, privacy, and venue requirements.

Official source: [CARE checklist](https://www.care-statement.org/checklist).

### In vivo animal research — ARRIVE 2.0

- Current statement: **ARRIVE 2.0**, published July 2020
- Structure: Essential 10 plus 11 Recommended Set items
- Use for: research involving live animals across bioscience disciplines

The Essential 10 are a minimum reporting set, not a ranking. Review study design, sample size, inclusion/exclusion, randomization, blinding, outcome measures, statistics, animal details, procedures, and results; also assess ethics, welfare, humane endpoints, adverse events, protocol registration, data access, and interests.

Official source: [ARRIVE 2.0](https://arriveguidelines.org/arrive-guidelines).

### Quality improvement — SQUIRE 2.0

- Current statement: **SQUIRE 2.0**, published 2015
- Structure: 18 main items
- Use for: system-level work intended to improve healthcare quality, safety, value, or equity where methods seek to relate outcomes to the intervention

SQUIRE states that every item should be considered, but not every element belongs in every manuscript. Attend to local context, rationale, intervention evolution, measures, analysis, ethics, unintended consequences, and sustainability.

Official source: [SQUIRE 2.0](https://www.equator-network.org/reporting-guidelines/squire/).

### Health economic evaluations — CHEERS 2022

- Current statement: **CHEERS 2022**
- Structure: 28 main items
- Replaces: CHEERS 2013
- Use for: economic evaluations of health interventions

Assess perspective, comparators, time horizon, discounting, outcome and cost measurement, model assumptions, heterogeneity, distributional effects where applicable, uncertainty, engagement, funding, and conflicts. Use a separate critical-appraisal framework for methodological quality.

Official source: [ISPOR CHEERS](https://www.ispor.org/heor-resources/good-practices/cheers).

### Qualitative research — SRQR and COREQ

- **SRQR**: broad qualitative research reporting standard
- **COREQ**: 32-item checklist specifically for interviews and focus groups

Select by methods, not by the presence of quotations. Review researcher reflexivity, sampling, context, data collection, analytic process, credibility, participant voice, ethics, and limitations without imposing one epistemology on all qualitative traditions.

Official registry records: [SRQR](https://www.equator-network.org/reporting-guidelines/srqr) and [COREQ](https://www.equator-network.org/reporting-guidelines/coreq/).

## AI extensions and overlap

Use the guideline that matches the study’s primary design and claim:

- Randomized trial of an AI intervention: CONSORT 2025 plus current CONSORT-AI guidance
- Protocol for such a trial: SPIRIT 2025 plus current SPIRIT-AI guidance
- AI diagnostic accuracy: STARD-AI
- Prediction model development or performance evaluation: TRIPOD+AI
- Biomedical large-language-model prediction or evaluation: check TRIPOD-LLM and design-specific guidance
- Medical imaging AI: consider current modality guidance in addition to the design-specific base

Multiple guidelines can apply, but do not create redundant demands. State which base and extension address each concern.

## Domain metadata standards: verified legacy status

These standards describe minimum experiment or repository metadata. They complement, rather than replace, study-design reporting and methodological appraisal.

### MIAME and MINSEQE

**Retain with qualification.** NCBI GEO’s page was last modified 8 July 2026 and still states that GEO submission procedures implement:

- MIAME for microarray experiments
- MINSEQE for next-generation/high-throughput sequencing experiments

ArrayExpress/Annotare also continues to reference these standards. Verify the current repository’s fields, file formats, raw/processed data expectations, and accession requirements; do not rely on an old static project page alone.

Official implementation source: [GEO and MIAME/MINSEQE](https://www.ncbi.nlm.nih.gov/geo/info/MIAME.html).

### MIAPE

**Retain as a modular current-qualified standard.** The HUPO Proteomics Standards Initiative lists released components with separate versions, including mass spectrometry, mass-spectrometry informatics, quantification, gel electrophoresis, gel informatics, chromatography, and capillary electrophoresis.

Select only components relevant to the actual workflow and verify current repository expectations. Do not present “MIAPE” as one unversioned universal checklist.

Official source: [HUPO-PSI MIAPE](https://www.psidev.info/miape).

### MIFlowCyt

**Retain with qualification.** ISAC continues to identify MIFlowCyt 1.0 as an ISAC recommendation for experiment overview, samples, instrumentation, and data analysis. Also check current FCS, gating, panel, controls, and FlowRepository requirements.

Official source: [ISAC MIFlowCyt](https://isac-net.org/miflowcyt-2/).

### MIAPPE

**Use MIAPPE 1.2**, released October 2024, for plant phenotyping metadata. It remains compatible with 1.1; version 2.0 was still in early development on the verification date.

Official source: [MIAPPE releases](https://www.miappe.org/releases).

### MIGS and MIMS

**Do not present standalone MIGS/MIMS as the current umbrella.** The Genomic Standards Consortium now organizes these legacy checklists within **MIxS** (Minimum Information about any Sequence), alongside newer checklists and environmental packages. Select the current MIxS release and applicable checklist/package.

Official source: [GSC standards](https://www.gensc.org/pages/standards-intro.html).

## Other study types

The EQUATOR database contains hundreds of guidelines. Common additional choices include:

- Protocols: design-specific protocol guidance
- Routinely collected health data: RECORD
- Clinical practice guidelines: RIGHT and AGREE reporting guidance
- Surveys: design-appropriate survey reporting guidance
- Implementation studies: current implementation-reporting guidance
- Mixed methods: current mixed-methods guidance
- Laboratory and omics studies: study-design reporting plus current repository metadata standards

If no suitable guideline exists, say so. Do not force the nearest checklist or invent one.

## Coverage language for reviews

Use:

> “Item 12 is not reported clearly enough to determine the analysis population. Please identify the included participants and reconcile this denominator with Figure 1.”

Avoid:

> “The manuscript scores 18/30 on CONSORT and is therefore low quality.”

Report counts or item identifiers only as navigation aids. The local selector deliberately emits no percentage or merit score.
