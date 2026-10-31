# Ethics, Safety, Feasibility, and Responsible AI

## This is a routing guide

This reference helps identify gates. It is not legal, medical, regulatory, biosafety, biosecurity, export-control, ethics, or institutional advice. Requirements vary by jurisdiction, sponsor, institution, organism, material, and intended use.

When applicability is uncertain, mark the gate `undetermined`, stop operational planning, and obtain a determination from the qualified local authority.

## Universal intake

Record:

- accountable owner and institution;
- intended purpose and foreseeable misuse;
- affected people, animals, communities, ecosystems, infrastructure, or security interests;
- data and material sensitivity;
- funding, jurisdiction, and collaborating sites;
- required expertise;
- conflicts and incentives;
- approvals, determinations, and unresolved blocks;
- less risky ways to answer the question.

Feasibility never overrides ethics or safety.

## Human-participant gate

Potential triggers include:

- intervention or interaction with living people;
- identifiable private information or biospecimens;
- secondary use, linkage, re-identification, recruitment, or contact;
- vulnerable populations or sensitive topics;
- international or community-governed data.

Required action:

- obtain an IRB/REC or other authorized determination before research starts;
- do not self-declare exemption;
- address consent or authorized waiver, privacy, security, equitable selection, risk/benefit, compensation, return of results, and community governance as applicable;
- use additional protections required by law or policy.

In the United States, HHS 45 CFR 46 includes the Common Rule and additional subparts. Local and non-U.S. rules can differ. The 2024 revision of the World Medical Association Declaration of Helsinki is a relevant international ethical statement for medical research involving human participants.

This skill does not provide clinical advice or authorize an intervention.

## Animal-research gate

Potential triggers include live vertebrate animals, field capture, breeding, procedures, tissues tied to ongoing animal activities, or covered training/testing.

Required action:

- obtain the applicable IACUC or equivalent approval before work;
- establish institutional assurance and veterinary oversight where required;
- apply replacement, reduction, and refinement;
- justify species/model, numbers, endpoints, welfare monitoring, analgesia/anesthesia, and humane endpoints through the authorized process;
- use current reporting guidance such as ARRIVE when applicable.

The bundled tools do not calculate animal numbers or approve protocols.

## Biosafety and biosecurity gate

Potential triggers include:

- recombinant or synthetic nucleic acids;
- infectious agents, toxins, biological materials, gene transfer, or modified organisms;
- environmental release;
- select agents or regulated materials;
- procedures that could alter hazard, host range, pathogenicity, transmissibility, resistance, or detection;
- work beyond established institutional containment and training.

Required action:

- stop before operational detail;
- route to the biosafety officer, Institutional Biosafety Committee, and other required authority;
- use the current NIH Guidelines, CDC/NIH *Biosafety in Microbiological and Biomedical Laboratories*, local biosafety manual, and applicable regulations;
- document containment and occupational-health decisions only after authorized review.

Do not infer a containment level or operating procedure from this skill.

## Dual-use and harmful-use gate

Potential triggers include research, data, models, or protocols that could reasonably enable:

- increased biological harm or spread;
- evasion of detection, treatment, control, or safeguards;
- scalable production or dissemination of harmful agents;
- weaponization;
- exploitation of critical vulnerabilities;
- transfer of restricted technical information.

Required action:

1. Do not provide optimization, stepwise procedures, parameter choices, sequences, acquisition pathways, or troubleshooting that increase harmful capability.
2. Preserve only a high-level scientific question, benefit rationale, and risk statement.
3. Route to institutional dual-use/biosecurity review, funder, legal/export-control, and other required authorities.
4. Follow current policy, award terms, and jurisdiction-specific controls.

### U.S. policy status checked 2026-10-01

- The July 2026 [USG Policy for Stopping High-Risk Life Sciences Research](https://www.whitehouse.gov/wp-content/uploads/2026/07/USG-Policy-for-Stopping-High-Risk-Life-Sciences-Research_July-2026.pdf) has been issued; it is no longer an awaited replacement for the 2024 DURC/PEPP framework.
- NIH [NOT-OD-26-101](https://grants.nih.gov/grants/guide/notice-files/NOT-OD-26-101.html), issued July 28, 2026, describes federal funding prohibitions and oversight for dangerous gain-of-function research and international research of concern. It states that activities previously identified as potential dangerous gain-of-function research remain paused until NIH-specific implementation requirements are established. Do not infer that policy publication authorizes resumption.
- The [NIH biosafety/biosecurity portal](https://osp.od.nih.gov/policies/biosafety-and-biosecurity-policy/) still directs researchers to the April 2024 NIH Guidelines. Its separately proposed [Draft NIH Biosafety Policy](https://grants.nih.gov/grants/guide/notice-files/NOT-OD-26-112.html), released August 19 with comments due October 19, 2026, would replace those Guidelines only when finalized. The draft is not an effective replacement.

Check the current agency implementation notices, award terms, and institutional determination for every project; neither a historical policy nor a pending proposal is clearance.

WHO’s *Global Guidance Framework for the Responsible Use of the Life Sciences* provides an international risk-governance framework; it does not replace national or local rules.

## Data-governance gate

Before using data:

- confirm authority, consent, license, data-use agreement, and purpose limitation;
- classify sensitivity and re-identification risk;
- minimize fields and access;
- use approved storage, retention, deletion, audit, and sharing controls;
- address community and Indigenous governance;
- separate public, controlled, confidential, proprietary, and export-controlled materials.

Passing a local schema check is not de-identification, anonymization, HIPAA compliance, GDPR compliance, or authorization to share.

## Regulatory gate

Potential triggers include:

- human interventions or clinical investigations;
- drugs, biologics, devices, diagnostics, or software intended for clinical use;
- environmental release;
- genetically modified organisms;
- regulated laboratory, animal, agricultural, or chemical activities;
- claims intended for product labeling, approval, or public-health action.

Record:

- intended use;
- jurisdiction;
- product/activity classification;
- sponsor and responsible regulatory owner;
- applicable quality system or submission route;
- current determination and source/date.

Do not infer regulatory status from a research label, reporting checklist, or generated artifact.

## Feasibility gate

Assess:

- scientific and technical capability;
- validated measurement;
- statistical information/precision;
- qualified personnel and facilities;
- time and resources;
- access to population/system;
- approvals and material/data access;
- foreseeable failure and stopping criteria.

If infeasible, revise the question or conduct a bounded feasibility study. Do not weaken protections or invent optimistic assumptions.

## Responsible AI policy

### Local-first rule

Default to local processing. Do not send sensitive, unpublished, confidential, personal, proprietary, controlled, or security-relevant information to an external AI system without:

- explicit authorization;
- a named approved service and account;
- a defined minimum data scope;
- contract, retention, training-use, location, and access review;
- applicable publisher, funder, institutional, and participant permission.

The bundled scripts make no network, model, image, or external-service calls and read no environment credentials.

### Human accountability

An accountable human must:

- own the question, candidate set, and final scientific decisions;
- verify every citation, identifier, quotation, and source-to-claim link;
- verify calculations and scientific plausibility;
- inspect omitted rivals and boundary conditions;
- review ethics, safety, privacy, dual-use, and regulatory implications;
- disclose AI assistance where policy requires;
- retain or delete records under the controlling policy.

AI output is not evidence and cannot grant approval.

### Known AI risks

NIST AI 600-1 identifies generative-AI risks including confabulation, data privacy, harmful bias/homogenization, information integrity, human–AI configuration, and dangerous recommendations. Mitigate by:

- independent human ideation before AI expansion;
- generating rivals from different disciplinary perspectives;
- separating source retrieval from claim synthesis;
- checking primary sources directly;
- recording prompts/tool versions when authorized and scientifically relevant;
- challenging convergent, polished, or overly confident output;
- using multiple human reviewers for high-consequence work.

Doshi and Hauser’s 2024 experiment found AI-assisted stories were more similar to one another even while some individual creativity measures improved. Do not generalize that one study to all scientific ideation; treat homogenization as a plausible risk and preserve independent candidate generation.

UNESCO’s AI ethics recommendation emphasizes human rights, privacy/data protection, responsibility/accountability, transparency, and human oversight. Ultimate responsibility remains human.

## Stop conditions

Stop and escalate when:

- authorization is absent or ambiguous;
- a required review is missing;
- data or material classification is unknown;
- harmful-use potential cannot be bounded;
- a request seeks operational harmful detail;
- patient-specific advice is requested;
- a regulatory or legal determination is needed;
- the proposed measurement cannot validly bear on the construct;
- qualified expertise is unavailable.

Record the block without copying sensitive details into a general-purpose artifact.
