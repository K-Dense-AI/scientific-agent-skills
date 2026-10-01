# Report-Type Routing

Select one route before opening a template. Do not merge routes merely because artifacts share clinical data.

## Decision sequence

1. Is the artifact a patient-care record?
   Stop. This skill does not create SOAP notes, H&Ps, consultation notes, discharge summaries, prescriptions, orders, triage instructions, or signed diagnostic reports.
2. Is it a single clinical case intended for publication?
   Use CARE.
3. Is it a diagnostic-report scaffold controlled by a clinical service?
   Use ACR, the current specimen-specific CAP protocol, or CLIA as applicable.
4. Is it a randomized-trial protocol?
   Use SPIRIT 2025 and applicable extensions.
5. Is it a randomized-trial results manuscript?
   Use CONSORT 2025 and applicable extensions.
6. Is it an integrated report of one clinical study for regulatory review?
   Use ICH E3 plus E3 Q&A, with ICH E6(R3) and regional requirements as applicable.
7. Is it individual pre-approval safety information?
   Route to ICH E2A, E2B(R3), protocol/sponsor procedures, and regional requirements. Do not automate the reportability decision.
8. Is it individual post-approval safety information?
   Route to ICH E2D(R1), E2B(R3), marketing-authorisation-holder procedures, and regional requirements. Do not automate.
9. Is it an aggregate safety table?
   Use the protocol/SAP, ICH E3, CONSORT Harms when applicable, and the relevant regional aggregate-analysis guidance.
10. Is it an aggregate research summary?
    Use the reporting guideline for the actual design and the verified protocol/SAP. Do not imply clinical applicability.

## Route matrix

| Artifact | Base source | Add-ons | Do not substitute |
|---|---|---|---|
| Case report | CARE 2013 | CARE 2017 explanation; target journal | CONSORT, CSR, or diagnostic-report rules |
| Radiology scaffold | ACR 2025 communication parameter | Current modality/program standard and local policy | A generic impression generator |
| Cancer pathology scaffold | Current CAP protocol for exact organ/specimen | Current biomarker protocol and local policy | A static generic TNM checklist |
| Laboratory scaffold | 42 CFR 493.1291 for applicable US nonwaived testing | Method, specialty, state, accreditor, and laboratory policy | Hardcoded reference or critical ranges |
| Trial protocol | SPIRIT 2025 | Current design/data/intervention extensions | CONSORT results checklist |
| Randomized results | CONSORT 2025 | Current design/data/intervention extensions; CONSORT Harms | SPIRIT protocol checklist |
| CSR | ICH E3 and E3 Q&A | E6(R3), protocol, SAP, regional submission rules | CONSORT alone |
| Pre-approval ICSR | ICH E2A and E2B(R3) | Regional law/guidance and sponsor procedure | Aggregate formatter |
| Post-approval ICSR | ICH E2D(R1) and E2B(R3) | Regional law/guidance and MAH procedure | Pre-approval timing rules |
| Periodic aggregate safety | ICH E2C(R2), where applicable | Regional periodic-report rules | E2B message schema |

## CONSORT/SPIRIT extension selection

The base statements address standard randomized trials. Check the live official extension catalogue for:

- design: adaptive, cluster, cluster-crossover, crossover, dose-finding, factorial, multi-arm, non-inferiority/equivalence, N-of-1, pilot/feasibility, pragmatic, stepped-wedge, routine-data, or within-person;
- data: abstracts, harms, outcomes, patient-reported outcomes, surrogate outcomes, equity, and pathology;
- intervention/population: non-pharmacological, AI, social/psychological, children/adolescents, or other specialty extensions.

The catalogue now distinguishes SPIRIT-C/CONSORT-C children-and-adolescents extensions based on the 2025 statements from extensions based on CONSORT 2010 or SPIRIT 2013. Check each extension’s actual base rather than assuming the old item numbering still matches. Use the current extension with the 2025 base statement, document any conflict, and have a qualified methodologist resolve it. Do not silently renumber or reinterpret extension items.

## Jurisdiction and role gate

ICH Step 4 adoption does not itself prove implementation in a jurisdiction. FDA guidance is generally nonbinding but regulations are legally operative within scope. Institutional policy, protocol, contracts, ethics determinations, and sponsor procedures may add or change duties.

Record the jurisdiction, regulated-product category, responsible role, source version/date, and reviewer before drafting. If any is unknown, mark the route `BLOCKED_UNRESOLVED`.
