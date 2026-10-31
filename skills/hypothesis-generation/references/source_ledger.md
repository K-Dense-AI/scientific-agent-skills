# Dated Source Ledger

Latest targeted refresh: **2026-10-01**. The original source review was **2026-07-23**; `verified_on` in the machine-readable ledger records which sources were rechecked. Historical rows keep their original dates rather than implying every full text was reopened.

Machine-readable ledger: `assets/source_ledger.csv`.

## Search boundary

The original review used `parallel-cli`; the October refresh used live official/primary web documentation and indexed primary-source text, focusing on policy replacements, current reporting and preregistration guidance, and Python input semantics. The combined search scope covers:

- NIH rigor, reproducibility, and the 2026 replication initiative;
- Cochrane PICO and the original well-built clinical-question article;
- FINER’s attributed historical source and current interpretation;
- Platt’s original strong-inference essay;
- COS/OSF preregistration and Registered Reports;
- SPIRIT 2025 and CONSORT 2025;
- causal questions, counterfactuals, estimands, and bias;
- negative controls, HARKing, multiplicity, reproducibility, and replication;
- NIST/UNESCO responsible AI and primary evidence on output homogenization;
- human, animal, biosafety, biosecurity, dual-use, data, and regulatory gates.

Searches prioritized official domains and primary publications. Full-text extraction or search excerpts were used to verify titles, dates, versions, and relevant passages. Some publisher/PMC pages returned bot challenges; SPIRIT/CONSORT checklist scope and negative-control guidance were checked against indexed primary-source content. This was a targeted skill refresh, not a systematic review, patent search, or proof of scientific novelty. Source review does not authenticate or submit a registration.

## Core methodology sources

### Question formulation

- `SRC-COCHRANE-PICO` — current Cochrane Handbook Chapter 2. PICO is used for intervention-effect review questions, with objectives defined in advance and stakeholder input where appropriate.
- `SRC-PICO-ORIGINAL` — Richardson et al., 1995, *The well-built clinical question*. Foundational four-part clinical-question article.
- `SRC-FINER-1988` — Hulley and Cummings, *Designing Clinical Research*, first edition metadata (1988). It is the earliest FINER-attributed source located in this refresh.
- `SRC-FINER-CURRENT` — Werner and Willis, 2023, current FINER interpretation.

**Historical limitation:** the available targeted search confirmed the 1988 book’s bibliographic metadata and later attribution but did not establish the exact first printed use or coinage of the FINER mnemonic. The skill therefore does not claim that provenance as proven.

### Multiple hypotheses and falsification

- `SRC-PLATT-1964` — John R. Platt, “Strong Inference,” *Science* 146:347–353, DOI `10.1126/science.146.3642.347`.
- `SRC-NEG-CONTROL` — Lipsitch, Tchetgen Tchetgen, and Cohen, 2010, negative controls for confounding and bias, DOI `10.1097/EDE.0b013e3181d61eeb`.
- `SRC-HARKING` — Kerr, 1998, HARKing, DOI `10.1207/s15327957pspr0203_4`.
- `SRC-ASA-PVALUE` — ASA statement: thresholds alone do not support scientific conclusions; p-values do not measure hypothesis truth or effect importance; full reporting is required.

### Rigor, reproducibility, and replication

- `SRC-NIH-RIGOR` — NIH guidance on scientific premise, rigorous design, relevant biological variables, authentication, and transparency.
- `SRC-NIH-REPLICATION` — NIH’s agency-wide replication and reproducibility initiative, current official page at the NIH beta site; the central hub can change as implementation continues.
- `SRC-NASEM-RR` — National Academies 2019 consensus report defining computational reproducibility and replicability with new data.
- `SRC-TOP` — original 2015 Transparency and Openness Promotion article, retained as historical background.
- `SRC-TOP-2025` — current COS TOP 2025 framework: distinct research practices, implementation levels, and independent verification; apply the adopting journal/funder's policy.
- `SRC-NIH-DMS` — NIH Data Management and Sharing Policy.

Open practices remain subject to consent, privacy, community governance, intellectual property, export control, and security restrictions.

## Preregistration and intervention trials

- `SRC-COS-PREREG` — preregistration separates planned from unplanned work; transparent exploration remains valuable.
- `SRC-OSF-REG` — current OSF registration/preregistration implementation guidance, including justified registration updates; attached files cannot be added or removed during an update. The local scaffold is not an OSF submission.
- `SRC-COS-RR` — Registered Reports and results-blind protocol review.
- `SRC-SPIRIT-2025` — current 34-item randomized-trial protocol guideline; supersedes SPIRIT 2013.
- `SRC-CONSORT-2025` — current 30-item randomized-trial result-reporting guideline, including open science, harms, outcomes, intervention details, and important changes.

SPIRIT and CONSORT are reporting guidelines, not design-quality, ethics, regulatory, or efficacy certifications.

## Causal inference and estimands

- `SRC-WHATIF` — Hernán and Robins, *Causal Inference: What If*. Use the author page's latest-version link; the authors state that online revisions may not be individually documented, so do not infer a fixed current revision from an older filename.
- `SRC-ICH-E9R1` — ICH E9(R1), defining the estimand as the precise treatment-effect target and aligning planning, design, analysis, sensitivity analysis, and interpretation.

These sources ground the distinctions among target causal contrast, estimator, and estimate, and the explicit treatment of confounding, selection, collider, measurement, and intervention-definition assumptions.

## Responsible AI

- `SRC-NIST-GENAI` — NIST AI 600-1, covering confabulation, privacy, harmful bias/homogenization, information integrity, dangerous recommendations, and human–AI configuration.
- `SRC-UNESCO-AI` — human rights, privacy, accountability, transparency, diversity, and human oversight.
- `SRC-DOSHI-HAUSER` — Doshi and Hauser, 2024, DOI `10.1126/sciadv.adn5290`. In the studied story-writing task, AI-assisted outputs were more similar to one another while some individual creativity measures improved.

The primary homogenization result is task-specific. The skill treats idea homogenization as a plausible risk, not a universal measured effect across scientific domains.

## Ethics and oversight

### Humans

- `SRC-HHS-COMMON-RULE` — U.S. Common Rule/45 CFR 46 portal.
- `SRC-BELMONT` — respect for persons, beneficence, and justice.
- `SRC-HELSINKI` — World Medical Association Declaration of Helsinki, revised October 2024.

An authorized IRB/REC or equivalent must determine applicability; the skill does not self-declare exemption.

### Animals

- `SRC-OLAW-PHS` — PHS Policy and IACUC/Assurance requirements for covered work.
- `SRC-ARRIVE` — ARRIVE 2.0 reporting guidance.

### Biosafety and dual use

- `SRC-NIH-RSNA` — NIH Guidelines for research involving recombinant or synthetic nucleic acid molecules.
- `SRC-NIH-BIOSEC` — current NIH biosafety/biosecurity portal.
- `SRC-BMBL` — CDC/NIH BMBL sixth edition.
- `SRC-WHO-LIFE` — WHO Global Guidance Framework for the Responsible Use of the Life Sciences.

### U.S. high-risk research and biosafety transition status

As checked on **2026-10-01**:

- `SRC-EO-14292` and `SRC-NIH-NOT-25-112` provide the 2025 historical transition and rescission of NIH's 2024 implementation.
- `SRC-USG-HIGH-RISK-2026` is the issued July 2026 USG policy. `SRC-NIH-NOT-26-101` (July 28) describes funding prohibitions and oversight for dangerous gain-of-function research and international research of concern. It states that previously flagged potential dangerous gain-of-function work remains paused pending NIH-specific implementation requirements. Publication is not permission to resume.
- `SRC-ASPR-HIGH-RISK` is the current ASPR oversight portal; the old DURC transition URL returned 404.
- `SRC-NIH-BIOSAFETY-DRAFT` (August 19) is a proposal with comments due October 19, 2026. It would replace the April 2024 NIH Guidelines when finalized; the NIH portal still lists those Guidelines as current. Do not treat the draft as effective policy.

This status is time-sensitive. Recheck current federal, funder, award, institutional, and jurisdiction-specific rules before any related work. Do not use this ledger as clearance.

## Local tools and endpoint scope

`SRC-PYTHON-JSON` confirms that Python's default JSON decoder accepts nonstandard numeric constants; the bundled reader explicitly rejects them and converts excessive nesting into a controlled input error. `SRC-PYTHON-DATE` documents the broader ISO formats accepted since Python 3.11; the schema explicitly requires `YYYY-MM-DD`.

All seven bundled CLIs remain local-only and have no network API, authentication, pagination, or model contract. The collection citation's optional arXiv `/api/query?id_list=2609.00065` lookup is separate documentation: the [official API manual](https://info.arxiv.org/help/api/user-manual.html) confirms an unversioned ID retrieves the latest version in Atom XML. It requires no credentials and needs no pagination for this single-record lookup. The live record and shared parent probe confirmed the cited authors/title and v2; no citation correction was needed.

## Source-use rules

1. Verify each citation and identifier against the live primary source before publication or registration.
2. Recheck time-sensitive policy after the cutoff date.
3. Link every scientific claim to evidence in `assets/evidence_ledger_template.csv`.
4. Include challenging, null, and limitation evidence, not only support.
5. Do not infer novelty from this source ledger; it documents the skill refresh, not a user’s research topic.
6. Do not expose a sensitive research question in an external search query without authorization.
