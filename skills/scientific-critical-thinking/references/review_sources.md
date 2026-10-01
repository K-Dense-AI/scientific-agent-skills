# Primary guidance and review limits

Reviewed 2026-10-01. This is an evidence-appraisal workflow, not an implementation of
formal scoring algorithms, a statistical package, or a clinical decision system. Use the
complete current tool documents for a formal assessment and retain version/date, result
identity, source locations, signalling answers, and judgment rationale.

## Risk of bias, reporting, and certainty

| Source | Verified scope and consequence |
| --- | --- |
| [Cochrane Handbook, chapter 8](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-08) | RoB 2 is result-specific; assignment versus adherence and trial variant matter. Overall judgments use domain rules, not an average score. |
| [ROBINS-I V2 developers](https://www.riskofbias.info/welcome/robins-i-v2) | November 2025 V2 is still labelled draft, for follow-up/cohort intervention studies. It differs from ROBINS-I 2016; name the version. |
| [QUADAS-3 developers](https://www.bristol.ac.uk/population-health-sciences/projects/quadas/quadas-3/) | Current recommended diagnostic accuracy tool, published February 2026; listed download v1.2. Assessment is per accuracy estimate, with synthesis questions and an ideal test accuracy trial. |
| [AMSTAR 2 developers](https://amstar.ca/Amstar-2.php) | Appraises systematic reviews of healthcare interventions; critical domains determine confidence, not a summed score. |
| [PEDro scale](https://pedro.org.au/english/resources/pedro-scale/) | Physiotherapy-trial appraisal scale; eligibility item is not part of the total. Not equivalent to RoB 2 or a GRADE certainty rating. |
| [Newcastle-Ottawa Scale developers](https://ohri.ca/en/who-we-are/core-facilities-and-platforms/ottawa-methods-centre/newcastle-ottawa-scale) | Cohort/case-control forms address selection, comparability, and outcome/exposure ascertainment. Do not invent universal star thresholds. |
| [CASP checklists](https://casp-uk.net/casp-tools-checklists/) | Separate appraisal checklists by design; use the matching current form. |
| [CONSORT/SPIRIT developers](https://www.consort-spirit.org/) and [extensions](https://www.consort-spirit.org/extensions) | Core trial-results and protocol guidance is CONSORT 2025/SPIRIT 2025. Some applicable extensions still reference older cores. Reporting standards do not certify conduct. |
| [STROBE developers](https://www.strobe-statement.org/) | Cohort, case-control, and cross-sectional reporting; explicitly not a study-quality assessment instrument. |
| [PRISMA 2020 developers](https://www.prisma-statement.org/prisma-2020) | Systematic-review reporting checklist, expanded checklist, and flow diagrams; not a bias or certainty score. |
| [STARD guidance](https://www.equator-network.org/reporting-guidelines/stard/) | STARD 2015 for diagnostic accuracy reports; STARD-AI is a 2025 extension for AI studies. |
| [COREQ guidance](https://www.equator-network.org/reporting-guidelines/coreq/) | Qualitative interviews and focus groups; not all qualitative designs indiscriminately. |
| [CARE developers](https://www.care-statement.org/) | Case-report guidance developed in 2013 with 2017 explanation; reporting does not identify a comparative treatment effect. |
| [GRADE Book principles](https://book.gradepro.org/guideline/principles-for-assessing-the-certainty-of-interventions) | Current chapter dated August 2025: outcome-level certainty relative to explicit thresholds/ranges, absolute effects, alternative NRSI starting approaches, and no double counting. |
| [GRADE Book overview](https://book.gradepro.org/guideline/overview-of-the-grade-approach) | Updated May 2026; intervention, diagnostic, prognosis, exposure, and values applications differ. The intervention design hierarchy is not universal. |
| [GRADE recommendations](https://book.gradepro.org/guideline/grade-recommendations) | Updated March 2026: recommendation direction/strength requires a separate evidence-to-decision rationale and context. |
| [Cochrane Handbook, chapter 14](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-14) | Practical Summary of Findings and ROBINS-I/GRADE integration; preserve outcome/comparison scope and explicit domain explanations. |

The GRADE Book is replacing the older handbook progressively. Its three chapters above
were read through rendered-page extraction because ordinary HTTP/browser text returned a
JavaScript shell. The newer threshold/range framing should not be replaced with the older
shortcut that certainty only means closeness to a point estimate.

## Statistical and causal appraisal

- [ASA p-value statement](https://www.amstat.org/asa/files/pdfs/p-valuestatement.pdf):
  p-values do not give hypothesis probabilities, effect importance, or a complete basis
  for decisions. Interpretation requires the analysis context and full reporting.
- [Greenland et al., statistical misinterpretations](https://link.springer.com/article/10.1007/s10654-016-0149-3):
  test statistics and confidence intervals depend on the full model and sampling/selection
  assumptions; avoid observed-power, threshold, and interval-overlap shortcuts.
- [Hernán and Robins, Causal Inference: What If](https://miguelhernan.org/whatifbook):
  define the causal estimand and defend consistency, exchangeability, positivity, and
  selection assumptions. The authors' current book link is dated August 19, 2026.
- [Cochrane Handbook, chapter 13](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-13):
  missing-evidence appraisal cannot be reduced to a funnel plot. Asymmetry has alternative
  explanations; tests usually require at least ten studies and appropriate effect measures.
- [ARRIVE 2.0 experimental-unit explanation](https://arriveguidelines.org/arrive-guidelines/study-design/1b/explanation):
  state the independent unit and avoid treating subsamples or repeated measurements as
  additional independent experimental units.
- [FDA multiple-endpoints guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/multiple-endpoints-clinical-trials):
  supports specifying endpoint families and multiplicity strategies in human drug/biologic
  trials; its regulatory scope is not a universal rule for all exploratory science.
- [WMA Declaration of Helsinki](https://www.wma.net/policies-post/wma-declaration-of-helsinki/):
  current 2024 revision concerns medical research involving human participants. Institutional
  review and applicable local requirements must be checked; this skill certifies no compliance.

## Executed checks and limits

- The skill contains no scripts, SDK calls, scientific API endpoints, or statistical
  computation engine. References to REDCap, Qualtrics, registries, and statistical software
  identify possible workflow tools; they are not integrations or tested instructions.
- Tiny known-answer arithmetic checks verify the illustrative predictive values and
  independent multiple-testing probability; they do not establish diagnostic performance
  in a real population or validate a formal risk-of-bias/GRADE assessment.
- The optional scientific-schematics command was checked at the local CLI/help boundary.
  No paid generation of that example or private-data transmission was performed. Its
  provider contract and dependencies belong to that skill, not this appraisal workflow.
- No patient data, clinical study, registry submission, or authenticated scientific service
  was accessed. Human clinical/policy decisions require the applicable professional process.
