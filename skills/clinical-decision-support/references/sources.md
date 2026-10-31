# Authoritative Source Ledger

Documentation review: **2026-09-30**.

Reviewed official agencies, standards/guideline hosts, and primary publications using web search/read and fresh `parallel-cli extract` fallbacks. This skill has no runtime service endpoints, authentication, pagination, or external SDK dependencies: its seven CLIs consume local JSON. The optional collection-citation lookup is separate from artifact processing.

Status labels below reflect this review date. Some publisher/Bookshelf pages blocked direct reads; their indexed primary records, official guideline catalogues, or fresh extracts supplied the cited scope. A link is not an endorsement or a substitute for checking a living source before use. Tests use synthetic aggregates and establish helper behavior only, not clinical validity or compliance.

## FDA: CDS and AI-Enabled Devices

- **Clinical Decision Support Software** — FDA final guidance, January 2026; page reissued/content current January 29, 2026. Defines FDA's current interpretation of non-device CDS criteria and device-software boundaries.
  https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software
- **Marketing Submission Recommendations for a Predetermined Change Control Plan for AI-Enabled Device Software Functions** — FDA final guidance, August 2025. Used for planned modifications, validation methodology, impact assessment, and change-control concepts.
  https://www.fda.gov/regulatory-information/search-fda-guidance-documents/marketing-submission-recommendations-predetermined-change-control-plan-artificial-intelligence
- **AI-Enabled Device Software Functions: Lifecycle Management and Marketing Submission Recommendations** — FDA draft guidance, January 2025; explicitly draft/not for implementation on the cutoff date. Used only as clearly labeled draft lifecycle context.
  https://www.fda.gov/regulatory-information/search-fda-guidance-documents/artificial-intelligence-enabled-device-software-functions-lifecycle-management-and-marketing
- **Good Machine Learning Practice for Medical Device Development: Guiding Principles** — FDA page linking the January 2025 IMDRF final principles. Used for lifecycle, representative data, human-AI team, and independent testing themes.
  https://www.fda.gov/medical-devices/artificial-intelligence-enabled-medical-devices/good-machine-learning-practice-medical-device-development-guiding-principles
- **Transparency for Machine Learning-Enabled Medical Devices: Guiding Principles** — FDA/Health Canada/MHRA, June 13, 2024. Used for intended users, limitations, data characterization, uncertainty, human factors, monitoring, and update communication.
  https://www.fda.gov/medical-devices/artificial-intelligence-enabled-medical-devices/transparency-machine-learning-enabled-medical-devices-guiding-principles
- **Artificial Intelligence-Enabled Medical Devices** — current FDA topic page (redirect from the former software-as-a-medical-device route). Used to cross-check the guidance sequence.
  https://www.fda.gov/medical-devices/digital-health-center-excellence/artificial-intelligence-enabled-medical-devices

## ONC / HTI-1

- **HTI-1 Final Rule** — official Federal Register text, January 2024. Used for the legal scope of predictive DSI/source-attribute and intervention-risk-management requirements.
  https://www.federalregister.gov/citation/89-FR-1391
- **HTI-1 Decision Support Interventions Fact Sheet** — ONC, December 2023. Used for the section 170.315(b)(11) overview and predictive-DSI transparency categories.
  https://www.healthit.gov/wp-content/uploads/2023/12/HTI-1_DSI_fact-sheet_508.pdf
- **Requirements for Decision Support Interventions and Predictive Models** — ONC final-rule presentation, January 18, 2024. Used for intended use, population, user, decision role, out-of-scope use, fairness, validation, performance, and maintenance source attributes.
  https://healthit.gov/wp-content/uploads/2024/01/DSI_HTI1-Final-Rule-Presentation_508.pdf
- **HTI-1 Final Rule landing page** — ONC. Used to verify official supporting materials and current resource location.
  https://healthit.gov/regulations/hti-rules/hti-1-final-rule

- **Current DSI certification text** — 45 CFR 170.315(b)(11); predictive DSI source-attribute and risk-management provisions remain in the current text.
  https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-D/part-170/subpart-C/section-170.315
- **HTI-5 proposed rule** — proposal to remove AI model-card requirements; not treated as effective law.
  https://healthit.gov/resources/health-data-technology-and-interoperability-astp-onc-deregulatory-actions-to-unleash-prosperity-hti-5-proposed-rule/

## GRADE

- **GRADE Working Group** — official overview and minimum requirements. Used for outcome-specific certainty, explicit domain judgments, evidence profiles, and Evidence-to-Decision separation.
  https://www.gradeworkinggroup.org/
- **GRADE Book** — official current resource, progressively replacing the prior handbook by 2026. Used as the preferred methodology entry point.
  https://book.gradepro.org/
- **GRADE Handbook** — legacy/current transition resource. Retained for comparison where a GRADE Book chapter is not yet available; verify against the GRADE Book.
  https://gradepro.org/handbook

- **GRADE Book: Imprecision** — current chapter permits human judgments of serious, very serious, and extremely serious imprecision; supports explicit thresholds and uncertainty, not automatic grading.
  https://book.gradepro.org/guideline/imprecision
- **GRADE Book: Dissemination bias** — current terminology broadens the legacy publication-bias assessment to selective availability. The local schema retains `publication_bias` as its field name.
  https://book.gradepro.org/guideline/dissemination-bias

## AI and Clinical-Study Reporting

- **TRIPOD+AI** — Collins et al., BMJ 2024;385:e078378, published April 16, 2024. Reporting of prediction-model development/evaluation using regression or machine learning.
  https://www.bmj.com/content/385/bmj-2023-078378
- **TRIPOD+AI EQUATOR record** — scope, checklist, and related materials.
  https://www.equator-network.org/reporting-guidelines/tripod-statement
- **TRIPOD-LLM** — Gallifant et al., Nature Medicine 2025;31:60-69, published January 8, 2025. Modular reporting guidance for LLM development, tuning, and evaluation; not a quality appraisal tool.
  https://www.nature.com/articles/s41591-024-03425-5
- **CONSORT-AI** — Liu et al., Nature Medicine 2020;26:1364-1374, published September 9, 2020. AI-intervention randomized-trial reports.
  https://www.nature.com/articles/s41591-020-1034-x
- **CONSORT 2025** — Hopewell et al., BMJ 2025;389:e081123, published April 14, 2025. Current generic base statement used with CONSORT-AI.
  https://www.bmj.com/content/389/bmj-2024-081123
- **SPIRIT-AI** — Rivera et al., Nature Medicine 2020;26:1351-1363, published September 9, 2020. AI-intervention trial protocols.
  https://www.nature.com/articles/s41591-020-1037-7
- **SPIRIT 2025** — current generic base statement used with SPIRIT-AI.
  https://pubmed.ncbi.nlm.nih.gov/40295741
- **DECIDE-AI** — Vasey et al., Nature Medicine 2022;28:924-933, published May 18, 2022. Early-stage live clinical evaluation of AI-based decision-support systems. Included for reporting context; live evaluation is outside this skill.
  https://www.nature.com/articles/s41591-022-01772-9
- **DECIDE-AI EQUATOR record** — scope and publication links.
  https://www.equator-network.org/reporting-guidelines/reporting-guideline-for-the-early-stage-clinical-evaluation-of-decision-support-systems-driven-by-artificial-intelligence-decide-ai/
- **STARD-AI** — Sounderajah et al., Nature Medicine, published September 15, 2025, DOI 10.1038/s41591-025-03953-8. Final reporting guideline for AI diagnostic-accuracy studies.
  https://www.nature.com/articles/s41591-025-03953-8
- **STARD-AI author correction** — July 13, 2026; adds an omitted steering-committee author, with no checklist revision stated.
  https://www.nature.com/articles/s41591-026-04570-9
- **SPIRIT-CONSORT official site and extension catalogue** — confirms current 2025 bases; AI extensions remain listed under the 2013/2010 bases, requiring an item-content crosswalk.
  https://www.consort-spirit.org/
  https://www.consort-spirit.org/extensions
- **STARD-AI EQUATOR record** — final status, scope, citation, and checklist location.
  https://www.equator-network.org/reporting-guidelines/the-stard-ai-reporting-guideline-for-diagnostic-accuracy-studies-using-artificial-intelligence/

## Prediction-Model Risk of Bias

- **PROBAST+AI** — Moons et al., BMJ 2025;388:e082505, published March 24, 2025. Current quality/risk-of-bias/applicability tool for regression and AI prediction models; separates development from evaluation and uses participants/data sources, predictors, outcome, and analysis domains.
  https://pubmed.ncbi.nlm.nih.gov/40127903
- **PROBAST+AI project site** — tool resources and updates.
  https://www.probast.org/probast_ai

## Privacy and De-identification

- **HHS Guidance Regarding Methods for De-identification of PHI** — official OCR guidance, checked with current 45 CFR 164.514. Used for Expert Determination, Safe Harbor, actual knowledge, derivatives, and free-text cautions.
  https://www.hhs.gov/hipaa/for-professionals/special-topics/de-identification/index.html
- **45 CFR 164.514** — current eCFR text for de-identification and related requirements.
  https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-E/section-164.514

## ICH

- **ICH E6(R3) consolidated Step 4 guideline** — final version adopted June 16, 2026, consolidating principles, Annex 1, and Annex 2. Used for quality by design, fit-for-purpose data, oversight, privacy, auditability, and modern trial settings.
  https://database.ich.org/sites/default/files/ICH%20E6(R3)_Step4_FinalConsolidatedGuideline_2026_0616_.pdf
- **ICH E9(R1) Addendum on Estimands and Sensitivity Analysis** — final, adopted November 20, 2019. Used for estimand-led planning and sensitivity analysis.
  https://database.ich.org/sites/default/files/E9-R1_Step4_Guideline_2019_1203.pdf
- **ICH efficacy-guideline index** — official status/version cross-check.
  https://www.ich.org/page/efficacy-guidelines

## Cohort, Survival, and Biomarker Methods

- **STROBE** — official reporting guidance for observational studies.
  https://www.strobe-statement.org/
- **RECORD** — reporting extension for routinely collected health data.
  https://www.record-statement.org/
- **REMARK** — reporting recommendations for tumor-marker prognostic studies.
  https://www.equator-network.org/reporting-guidelines/reporting-recommendations-for-tumour-marker-prognostic-studies-remark
- **FDA-NIH BEST Resource** — living biomarker and endpoint terminology resource, 2016 onward.
  https://www.ncbi.nlm.nih.gov/books/NBK326791/
- **BEST Glossary** — revision January 16, 2025; includes multicomponent and response terminology. Direct Bookshelf reads returned a browser challenge; the indexed official glossary and FDA companion resource were used.
  https://www.ncbi.nlm.nih.gov/books/NBK338448/
  https://www.fda.gov/drugs/biomarker-qualification-program/about-biomarkers-and-qualification
- **Evaluation of clinical prediction models (part 2): how to undertake an external validation study** — Riley et al., BMJ 2024;384:e074820, published January 15, 2024. Used for locked-model evaluation, calibration, discrimination, utility, and transparent reporting.
  https://www.bmj.com/content/384/bmj-2023-074820
- **External validation of clinical prediction models: simulation-based sample size calculations were more reliable than rules-of-thumb** — Snell et al., Journal of Clinical Epidemiology 2021;135:79-89. Used to reject blanket event-count rules and emphasize precision targets.
  https://pmc.ncbi.nlm.nih.gov/articles/PMC8352630
- **Calibration: the Achilles heel of predictive analytics** — Van Calster et al., BMC Medicine 2019. Used for calibration assessment and interpretation.
  https://pubmed.ncbi.nlm.nih.gov/31842878
- **Restricted mean survival time** — Royston and Parmar, BMC Medical Research Methodology 2013;13:152. Used as an alternative population-level summary when proportional hazards is doubtful.
  https://pubmed.ncbi.nlm.nih.gov/24314264/
- **Competing risks introduction** — Austin, Lee, and Fine, Circulation 2016;133:601-609. Used to distinguish cause-specific hazards, subdistribution hazards, and cumulative incidence.
  https://pmc.ncbi.nlm.nih.gov/articles/PMC4741409/
- **Fine-Gray reporting recommendations** — Austin and Fine, Statistics in Medicine 2017;36:4391-4400. Used for careful interpretation of subdistribution hazard models.
  https://pmc.ncbi.nlm.nih.gov/articles/PMC5698744

## Deliberately Out of Scope

HL7 CDS Hooks, SMART on FHIR, and FHIR implementation guidance were not
added because the version 2.0 safety redesign deliberately removes
recommendation-oriented and live CDS behavior. It produces offline
research/governance artifacts only; implementation guidance would conflict
with the hard boundary.

No source requiring an API key, external model, image generator, or network call is used at runtime.
