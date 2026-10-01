# Clinical-Trial Reporting

## Keep the artifacts distinct

- **Protocol**: planned design and conduct. Route randomized-trial protocols to SPIRIT 2025.
- **Results manuscript**: completed trial reporting for publication. Route randomized-trial results to CONSORT 2025.
- **Clinical Study Report (CSR)**: integrated clinical and statistical report of an individual study. Route to ICH E3 and its Q&A.
- **Safety report**: individual or aggregate safety communication. Route separately; see `safety_reporting.md`.

One checklist does not substitute for another.

## CONSORT 2025

The official SPIRIT–CONSORT site describes CONSORT 2025 as a **30-item** minimum checklist plus a participant flow diagram for results of randomized trials. The primary statement was published 14 April 2025.

Use the statement, expanded checklist, and explanation/elaboration together. Check the current extension catalogue for every applicable design, data, intervention, and population extension. In particular, consider the current harms extension for adverse-event reporting.

The local template stores item IDs `C01`–`C30`; it does not reproduce, reinterpret, or score the checklist. A qualified methodologist must map each item to the official wording and resolve interactions with extensions.

Do not:

- fabricate a flow count or reason;
- infer analysis populations, endpoints, estimands, missing-data methods, or harms;
- add a figure when no verified data support it;
- treat a reporting checklist as proof of valid conduct or analysis.

## SPIRIT 2025

SPIRIT 2025 is the current reporting guideline for randomized-trial protocols. It was published 28 April 2025, contains **34 minimum items** plus a participant timeline figure, and supersedes SPIRIT 2013.

Notable updated areas include open science, harms assessment, intervention/comparator description, and patient/public involvement. Use the statement, expanded checklist, explanation/elaboration, and applicable extensions together.

The local template stores item IDs `S01`–`S34`. It checks item coverage only. It does not create a protocol, design a trial, select endpoints, specify interventions or doses, perform ethics review, or authorize conduct.

## ICH E3 Clinical Study Reports

ICH E3 reached Step 4 on 30 November 1995. The current E3 Q&A (R1), dated 6 July 2012, states that E3 is guidance rather than a rigid required template and may be adapted with justified additions, deletions, renaming, or reordering.

The structural validator expects these canonical sections:

1. Title Page
2. Synopsis
3. Table of Contents for the Individual Clinical Study Report
4. List of Abbreviations and Definitions of Terms
5. Ethics
6. Investigators and Study Administrative Structure
7. Introduction
8. Study Objectives
9. Investigational Plan
10. Study Patients
11. Efficacy Evaluation
12. Safety Evaluation
13. Discussion and Overall Conclusions
14. Tables, Figures, and Graphs Referred to but Not Included in the Text
15. Reference List
16. Appendices

Use `not_applicable_with_rationale` only when the study design and a qualified regulatory reviewer support the adaptation. The validator does not assess scientific content, appendices, eCTD placement, regional acceptability, or submission readiness.

## ICH E6(R3)

ICH adopted E6(R3) Principles and Annex 1 on 6 January 2025, Annex 2 on 3 June 2026, and a consolidated final guideline on 16 June 2026.

The guideline:

- applies to interventional trials of investigational products intended for regulatory submission, while principles may be applicable more broadly under local requirements;
- uses flexible, fit-for-purpose, proportionate, risk-based approaches;
- emphasizes participant rights, safety, and well-being and reliable results;
- requires attention to data governance, records, security, quality management, provenance, and traceability;
- expects the sponsor to describe the trial quality-management approach in the CSR.

Step 4 adoption does not prove regional implementation. FDA’s dedicated E6(R3) page lists final guidance from September 2025, while its general ICH index still describes E6(R2). Use the dedicated current regional document and verify Annex 2 status separately; do not infer that the June 2026 ICH consolidated text automatically replaced a regional version. A qualified regulatory professional must verify the applicable adopted version and transition rules.

## Data integrity and provenance

For every populated field:

- retain the protocol/SAP-defined population and endpoint language;
- identify the verified source and field path;
- preserve prespecified versus post hoc status;
- preserve database-cut and coding-dictionary versions;
- report denominators and missingness explicitly;
- record transformations and reconciliation decisions made by accountable humans;
- expose unresolved discrepancies.

Do not copy subject-level listings into local examples or tests. Use aggregate manifests and hashes.

## Review owners

- accountable clinical author: clinical interpretation;
- trial statistician: analysis populations, estimands, methods, outputs, and denominators;
- safety physician/professional: safety interpretation and individual-case decisions;
- data management/quality: source lineage and reconciliation;
- privacy/legal/ethics: authorization and disclosure;
- regulatory professional: CSR structure, regional rules, and submission package.

No script result replaces any of these reviews.
