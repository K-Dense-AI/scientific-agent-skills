# Ethical and Confidential Peer Review

Reviewed on **2026-10-01** against COPE, ICMJE, and illustrative publisher policies listed in `assets/source_ledger.csv`. Source-specific access limits and dates are recorded there.

COPE’s current membership framework is its [Code of Conduct](https://publicationethics.org/membership/code-of-conduct), published 21 July 2026 with a 12-month implementation transition. It replaces the 2017 Core Practices, which were [retired in 2024](https://publicationethics.org/about/what-we-do/our-story/history-code-conduct). This membership framework is distinct from the still-current reviewer-specific **Ethical Guidelines for Peer Reviewers, version 2 (2017)** used below. The target journal’s published process controls the individual assignment.

## Role boundary

This skill supports an accountable human preparing a review draft or structured assessment. It must not:

- Claim to be the assigned reviewer, editor, journal, funder, or decision-maker
- Submit a review or contact authors, editors, institutions, or third parties without authorization
- Invent manuscript content, experiments, analyses, citations, reviewer identity, or editorial outcomes
- Present generated text as an independently completed review
- Investigate authors or search unpublished content outside the authorized process

The editor decides the editorial outcome. The reviewer provides evidence-bounded advice within the requested scope.

## Before accepting or starting

COPE’s Ethical Guidelines for Peer Reviewers and ICMJE recommendations require reviewers to consider:

### Competence

- Accept only work for which the reviewer can provide a useful assessment.
- State material subject-matter, methods, statistics, ethics, language, or domain limits.
- Ask the editor for a specialist reviewer when a central issue exceeds competence.
- Do not conceal limits by producing confident generic criticism.

### Conflicts

Disclose actual, potential, or perceived conflicts before proceeding. They can be:

- Financial or commercial
- Personal or family
- Institutional
- Recent collaboration, supervision, mentorship, or competition
- Intellectual commitments or directly competing work
- Political, religious, advocacy, or legal interests

The journal decides whether a disclosed conflict permits review. If unresolved, stop. In the intake, `disclosed_to_editor` remains blocked; record `editor_cleared` only after clearance. Do not accept merely to gain access to unpublished work.

### Capacity and timeliness

Accept only if the review can be completed within the agreed time. Tell the editor promptly if scope or timing changes.

### Journal policy

Record:

- Review model and anonymity expectations
- Whether co-review is allowed and how contributors are named
- Confidentiality and retention requirements
- Required author-facing and editor-only fields
- AI and tool policy
- Citation, image-integrity, data, ethics, and reporting expectations

Journal practices differ. A policy from another publisher is an example, not authority for the target venue.

Use `scripts/validate_review_intake.py` before substantive review.

## Confidentiality and data handling

An unpublished manuscript, its supplements, review comments, and editorial correspondence are privileged confidential material.

### Default rule

Keep processing local. Do not send, paste, upload, transcribe, summarize, or expose unpublished manuscript or review text to:

- Public or external generative-AI systems
- Search engines or web research tools
- Citation, plagiarism, grammar, translation, or image services
- Unapproved collaborators
- Cloud storage or telemetry outside the authorized environment

unless the publisher or author has authorized that specific use, the target venue permits it, and applicable privacy, contract, intellectual-property, and data-governance requirements are satisfied.

Authorization to review is not automatically authorization to disclose material to a service. A tool’s promise not to train on data is not, by itself, authorization.

A hosted assistant reading a file is external processing even when its shell or bundled validator executes locally. Do not confuse the CLI's local-only behavior with the assistant platform's handling of content.

The bundled CLIs:

- Use only Python’s standard library
- Read bounded local JSON, CSV, or Markdown
- Make no network, model, image, subprocess, environment-variable, or dynamic-code calls
- Emit identifiers, counts, rule codes, and line numbers rather than raw manuscript or review text
- Refuse symlink inputs and implicit output overwrite

They do not make an external service safe and do not authorize its use.

### Assistance and co-review

Obtain journal permission before sharing with a trainee or colleague. Record the contributor and acknowledge the contribution to the editor as required. The invited reviewer remains responsible for confidentiality and the submitted report.

### No reuse

Do not:

- Appropriate ideas, methods, code, data, or language before publication
- Use the material for model training, benchmarking, product improvement, or unrelated research
- Build a private corpus of manuscripts or reviews
- Retain content for convenience beyond policy

### Retention and deletion

After submitting or ending the review:

1. Follow the target venue’s retention rule.
2. Delete local manuscript and review copies when required.
3. Empty derivative exports and temporary files within the authorized workspace.
4. Retain only what policy requires.
5. Record deletion or authorized retention without copying confidential content into the record.

ICMJE recommends that reviewers not retain manuscripts for personal use and delete copies after review. Local law, publisher policy, or a documented investigation may impose a different rule; follow the controlling requirement.

## AI and automated assistance

ICMJE says reviewers must follow the journal’s AI policy or request permission before using AI, maintain confidentiality, disclose use, and remain responsible for output that may be incorrect, incomplete, or biased.

For any permitted assistance:

- Identify the tool, version, purpose, and material exposed
- Use only the minimum necessary content
- Keep an accountable human in control
- Verify every statement, citation, calculation, and proposed comment
- Disclose use exactly as the journal requires
- Do not let a model create an autonomous review or editorial outcome

If permission is absent, the policy is unclear, or confidentiality cannot be assured, do not use AI on the material. Local deterministic checks may still be possible if policy and authorization permit local file processing.

Illustrative policies, not universal rules:

- [Nature Portfolio's current AI policy](https://www.nature.com/nature-portfolio/editorial-policies/ai) permits support under human accountability and disclosure, prohibits sharing manuscript content with unsecured/public AI tools, and prohibits delegating critique or judgment. Some [reviewer instructions](https://www.nature.com/nature/for-referees/policies-and-processes) still state a broader no-upload rule. Check the instructions for the actual journal and assignment; seek editor clarification when policies conflict.
- [BMJ](https://authors.bmj.com/policies/ai-use) requires declaration of AI used for review-language assistance and prohibits placing unpublished material into publicly available tools when confidentiality cannot be guaranteed.
- [JAMA Network's 2023 published guidance](https://jamanetwork.com/journals/jama/fullarticle/2807956) states that entering manuscript, abstract, or review text into a chatbot or language model violates its confidentiality agreement and requires disclosure of other AI resource use. This dated article is an example; verify the current invitation and reviewer instructions.

Always check the current target-venue policy.

## Preparing the report

COPE and ICMJE emphasize constructive, honest, polite, fair, and timely comments.

### Evidence and proportionality

- Anchor every consequential criticism to a location and reason.
- Distinguish missing reporting from demonstrated methodological error.
- Explain why the issue changes validity, interpretation, reproducibility, ethics, or reader understanding.
- Request the least burdensome adequate remedy.
- Label optional suggestions as optional.
- Do not expand the study beyond its stated scope merely to satisfy reviewer preference.
- Do not request citations to benefit the reviewer or associates.

### Tone

Critique the work, not the people. Avoid:

- Insults, sarcasm, ridicule, threats, or speculation about competence or motives
- Language policing unrelated to scientific clarity
- Bias based on identity, institution, location, seniority, language, or reputation
- Accusations when the evidence supports only a question or discrepancy
- Vague commands such as “redo the statistics” or “needs more work”

Use direct language without hostility:

> “The analysis appears to treat three observations per participant as independent. Please define the analysis unit and account for within-participant dependence, or explain why independence is justified.”

### Requests for additional work

Request a new experiment or analysis only when it is necessary and proportionate to evaluate or support a central claim. State:

- Which claim depends on it
- Why existing evidence is insufficient
- Whether a narrower claim, correction, sensitivity analysis, or limitation would be an adequate alternative

Do not turn review into an opportunity to redesign the authors’ research program.

## Separate communication channels

### Comments to authors

Include:

- Neutral summary of the work actually reviewed
- Specific strengths
- Major comments affecting validity, interpretation, reproducibility, ethics, or central claims
- Minor comments affecting clarity, consistency, figures, tables, citations, or reporting
- Review limitations and unavailable materials when useful

Do not include:

- Reviewer identity when policy requires anonymity
- Unnecessary personal information
- Editor-only conflict details
- Accusations or investigative instructions
- An editorial outcome presented as decided

### Confidential comments to editor

Use only for matters that require a separate channel:

- Reviewer conflicts or competence limits
- Permission, confidentiality, or AI-use disclosures
- Credible ethics, integrity, duplicate-publication, image, or security concerns
- Reasons an issue cannot safely be raised directly with authors
- Requests for specialist review

Ordinary scientific criticism should not appear only in the editor channel. Do not write a harsher private review that contradicts the author-facing report. The bundled scaffold keeps these channels visibly separate.

## Suspected integrity problems

Reviewers identify concerns; they do not adjudicate misconduct.

1. Preserve confidentiality.
2. Record the exact location and observable discrepancy.
3. Describe uncertainty and plausible benign explanations.
4. Notify the editor through the designated confidential route.
5. Do not contact authors, institutions, journals, funders, or media independently.
6. Do not run external similarity, face-recognition, image, or data-search services on confidential material without authorization.
7. Follow editor instructions and retain or delete evidence according to policy.

Use “Figure 3 appears similar to Figure 5 after rotation; please assess under the journal’s image-integrity process,” not “the authors fabricated the data.”

## Final ethical check

- Authorization and role are documented.
- Conflicts are resolved or disclosed.
- Competence limits and specialist needs are stated.
- Target-venue policy and review model are known.
- No unauthorized person or service received confidential material.
- AI or other assistance is permitted and disclosed.
- Author and editor channels are separate.
- Every criticism is specific, evidence-backed, proportionate, and professional.
- No invented citation, analysis, experiment, or editorial outcome appears.
- Deletion or authorized retention is planned.
