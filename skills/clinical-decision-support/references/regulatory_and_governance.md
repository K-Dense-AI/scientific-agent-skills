# Regulatory and Governance Context

Checked 2026-09-30. This is orientation for research documentation, not legal advice or a regulatory determination.

## FDA Clinical Decision Support

FDA issued the current **Clinical Decision Support Software** final guidance in January 2026 and reissued it on January 29, 2026. It explains how FDA interprets the statutory criteria for certain CDS software functions excluded from the device definition under section 520(o)(1)(E) of the FD&C Act and distinguishes those functions from device software functions.

Do not turn the guidance into a self-certification score. Regulatory status depends on the complete function and intended use, including:

- who uses the function;
- what information it acquires, processes, or analyzes;
- the output and its role in prevention, diagnosis, or treatment;
- whether the healthcare professional can independently review the basis;
- time criticality, automation, and reliance;
- patient/caregiver use and other applicable digital-health policies.

This skill intentionally stays outside patient-specific and live clinical functions. An artifact title, disclaimer, or “human in the loop” statement does not by itself make software non-device.

Source: [FDA Clinical Decision Support Software, final guidance (January 2026)](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software).

## FDA AI-Enabled Device Lifecycle

Use these sources only to identify documentation themes for research governance:

- [Predetermined Change Control Plan for AI-Enabled Device Software Functions](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/marketing-submission-recommendations-predetermined-change-control-plan-artificial-intelligence) — final guidance, August 2025. A PCCP describes planned modifications, methods to develop/validate/implement them, and impact assessment; FDA reviews it within a marketing submission.
- [AI-Enabled Device Software Functions: Lifecycle Management and Marketing Submission Recommendations](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/artificial-intelligence-enabled-device-software-functions-lifecycle-management-and-marketing) — draft guidance, January 2025; **not for implementation** as of the check date.
- [Good Machine Learning Practice for Medical Device Development](https://www.fda.gov/medical-devices/artificial-intelligence-enabled-medical-devices/good-machine-learning-practice-medical-device-development-guiding-principles) — FDA page points to the January 2025 IMDRF final principles.
- [Transparency for Machine Learning-Enabled Medical Devices](https://www.fda.gov/medical-devices/artificial-intelligence-enabled-medical-devices/transparency-machine-learning-enabled-medical-devices-guiding-principles) — joint guiding principles, June 2024.

Recurring lifecycle themes:

- representative data and independent test sets;
- performance of the human-AI team;
- clinically relevant testing across intended conditions;
- known limitations, confidence intervals, gaps, and failure modes;
- monitoring, issue investigation, change notification, and version traceability;
- training/test data characterization and subgroup performance.

These sources do not authorize this skill to create a medical device or a submission.

## ONC HTI-1 Transparency

The HTI-1 final rule added the Decision Support Interventions certification criterion at 45 CFR 170.315(b)(11). Its scope is certified health IT and the configurations defined in the rule; it is not a universal certification checklist for every research model.

For predictive DSIs in scope, the rule and ONC materials emphasize source attributes covering:

- developer and funding;
- output type, purpose, intended population, users, and decision role;
- cautioned out-of-scope uses and known limitations;
- development data and input features;
- fairness process;
- external validation;
- quantitative performance;
- ongoing maintenance;
- update, continued-validation, and fairness-assessment schedules.

They also describe intervention risk management for predictive DSIs supplied by certified health IT developers. At review, the [current 45 CFR 170.315(b)(11)](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-D/part-170/subpart-C/section-170.315) still contains these provisions. The [HTI-5 proposed rule](https://healthit.gov/resources/health-data-technology-and-interoperability-astp-onc-deregulatory-actions-to-unleash-prosperity-hti-5-proposed-rule/) proposes removing AI model-card requirements; do not treat that proposal as an enacted change. Recheck the effective regulation before using this crosswalk. Use these categories as a useful transparency crosswalk only when relevant; do not claim ONC certification.

Sources:

- [HTI-1 final rule](https://www.federalregister.gov/citation/89-FR-1391)
- [ONC HTI-1 DSI fact sheet](https://www.healthit.gov/wp-content/uploads/2023/12/HTI-1_DSI_fact-sheet_508.pdf)
- [ONC DSI final-rule presentation](https://healthit.gov/wp-content/uploads/2024/01/DSI_HTI1-Final-Rule-Presentation_508.pdf)

## ICH E6(R3), E9, and E9(R1)

Use ICH only when the artifact concerns clinical-trial planning, conduct, analysis, or evidence interpretation.

The current consolidated E6(R3) Step 4 guideline combines the principles, Annex 1, and Annex 2. It was adopted June 16, 2026 after Annex 2 reached Step 4 on June 3, 2026. Relevant governance themes include:

- quality by design and proportionate risk management;
- clear roles, oversight, and documented decisions;
- fit-for-purpose data and computerized systems;
- data integrity, metadata, auditability, and traceability;
- privacy and confidentiality;
- protocol and statistical-analysis-plan alignment;
- management of deviations, incidents, and important changes;
- fitness-for-purpose considerations for real-world data.

ICH E9 provides statistical principles for clinical trials. E9(R1), adopted November 20, 2019, requires alignment of the clinical question, estimand, design, conduct, analysis, and interpretation. Its estimand attributes and intercurrent-event strategies should be pre-specified; sensitivity analyses assess robustness to assumptions.

Sources:

- [ICH E6(R3) consolidated Step 4 guideline (June 2026)](https://database.ich.org/sites/default/files/ICH%20E6(R3)_Step4_FinalConsolidatedGuideline_2026_0616_.pdf)
- [ICH E9(R1) estimands and sensitivity analysis](https://database.ich.org/sites/default/files/E9-R1_Step4_Guideline_2019_1203.pdf)
- [ICH efficacy guideline index](https://www.ich.org/page/efficacy-guidelines)

ICH alignment must be assessed by the sponsor and relevant authorities. A script cannot establish GCP conformity.

## Governance Crosswalk

| Documentation field | FDA/AI theme | ONC HTI-1 theme | ICH theme |
|---|---|---|---|
| Intended use/users/population | Function and intended use | Purpose/source attributes | Trial objective/population |
| Limitations/out-of-scope use | Labeling/transparency | Cautioned use | Protocol constraints |
| Data provenance | Dataset characterization | Development details | Data origin/fitness |
| External validation | Clinically relevant testing | External-validation process | Evidence reliability |
| Subgroup/fairness | Representative performance | Fairness process | Population relevance |
| Human factors | Human-AI team | Intended decision role | Feasibility/quality |
| Monitoring/change control | TPLC/PCCP | Maintenance schedule | Quality management |
| Audit trail | Submission/version evidence | Source attributes | Essential records/metadata |

Treat the crosswalk as a documentation aid, never a conformity assessment.
