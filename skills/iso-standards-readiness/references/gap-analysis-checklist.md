# Fail-Closed Evidence Review

Research basis: **2026-10-01**; current-source details are in `references/source-ledger.md`. This
checklist organizes evidence questions; it is not ISO or IEC text, an audit, an
assessment, a legal determination, or a compliance score.

Sections up to "Training, competence, and change control" apply to the device QMS lanes
(`iso-13485`, `iso-14971`). The laboratory sections near the end apply to `iso-17025`
and `iso-15189`. Use the sections your declared profile covers; do not report on a
domain you did not sample.

## Status vocabulary

Use only:

- `not-assessed` — no authorized decision was recorded;
- `evidence-missing` — applicable/expected evidence was not supplied;
- `evidence-incomplete` — evidence is draft, unapproved, unsourced, stale, or
  insufficiently linked;
- `evidence-present-for-human-review` — controlled evidence is available for
  substantive review; no adequacy claim;
- `not-applicable-approved` — an authorized person approved a documented rationale.

Never convert these states into a “compliance percentage.” Unequal, conditional,
product-specific, and jurisdiction-specific evidence cannot be responsibly reduced
to keyword counts.

## Required fields for every review item

| Field | Required content |
|---|---|
| Item ID | Stable unique identifier |
| Scope | Products, sites, processes, suppliers, systems, and period |
| Owner | Accountable role |
| Status | One value from the vocabulary above |
| Evidence | Controlled IDs, revisions/dates, and locations |
| Source/version | Official source, exact edition/version/date, access/currency review |
| Rationale | Evidence-based conclusion or approved not-applicable rationale |
| Action | Gap/change/CAPA ID, owner, due date, and status |
| Approval | Named authorized approver, decision, date, and record ID |

Blank, placeholder, inaccessible, stale, or unapproved fields fail closed.

## Workflow

1. Freeze the review purpose and boundaries: internal audit, ISO certification
   preparation, laboratory accreditation assessment preparation, FDA inspection
   preparation, national regulatory inspection preparation, MDSAP, or EU conformity
   assessment. One purpose per review.
2. Obtain authorized standards and current official regulatory sources.
3. Record product/site/market/activity scope; route applicability decisions to
   authorized management, RA/QA, and legal roles.
4. Build a controlled evidence manifest. Do not classify files from names alone.
5. Sample implementation records across time, products, sites, shifts, suppliers,
   and risk as justified.
6. Trace findings to risk, correction, CAPA, change, validation, training, and
   management review.
7. Preserve limitations and unresolved decisions in the report.
8. Obtain human approval. Do not issue a certification/readiness/compliance claim.

## Scope, roles, and source basis

- [ ] Legal entities, sites, products/families, lifecycle activities, outsourced
      processes, and markets considered are explicit.
- [ ] Authorized management representative, RA/QA owner, process owners, document/
      record owners, delegates, and escalation are documented.
- [ ] Independence and authority for audit, release, complaint/reportability,
      nonconformity disposition, CAPA closure, and change approval are defined.
- [ ] Each applicability or not-applicable decision cites current official
      source/version evidence and authorized approval.
- [ ] ISO, FDA, MDSAP, EU, and product-specific criteria are separately identified.
- [ ] External-source currency reviews and change-impact records are current.

## Document and record control

- [ ] Every controlled document has ID, title, revision, owner, status, approval,
      effective date, change rationale, controlled location, and training impact.
- [ ] Point-of-use control prevents unintended use of draft or obsolete documents.
- [ ] External standards, regulations, guidance, specifications, and customer/
      supplier documents have exact versions and currency-review ownership.
- [ ] Record creation, attribution, correction, integrity, security, audit trail,
      backup/recovery, retrieval, retention, legal hold, and disposition are controlled.
- [ ] Each retention period has an approved source/version and start-event rationale.
- [ ] Electronic systems and migrations preserve integrity and retrievability.
- [ ] Document changes link to affected risk, design, supplier, production,
      validation/software, postmarket, and training evidence.

## Risk management

- [ ] Product and process risk scope, responsibilities, methods, criteria, reviews,
      and records are approved.
- [ ] Intended use, reasonably foreseeable use, hazards/signals, evaluations,
      controls, verification, residual-risk decisions, and production/postmarket
      feedback are traceable.
- [ ] Risk controls link to design inputs/outputs, verification/validation,
      production controls, labeling/information, and acceptance evidence.
- [ ] Supplier, software, process, usability, cybersecurity, clinical/performance,
      and postmarket risks are considered where applicable.
- [ ] Complaints, trends, vigilance, CAPA, and changes update risk evidence.
- [ ] ISO 14971 and any EN A11 source are identified by exact edition and role.

## Design and development

- [ ] Authorized applicability decision covers the actual legal/lifecycle role.
- [ ] Plans define stages, responsibilities, interfaces, reviews, resources,
      verification, validation, transfer, and change controls.
- [ ] Inputs are approved, testable, traceable, and linked to risk and
      product/regulatory requirements.
- [ ] Outputs support production, suppliers, acceptance, service, labeling, and safe
      use as applicable.
- [ ] Reviews preserve participants, independence/competence, issues, decisions, and
      follow-up evidence.
- [ ] Verification and validation have approved protocols, objective criteria,
      representative configurations/samples, deviations, results, and approvals.
- [ ] Transfer and design changes include risk, validation, production, supplier,
      software, training, product-file, and postmarket impact evidence.

## Supplier and outsourced-process controls

- [ ] Supplier/product/process criticality has an approved risk basis.
- [ ] Selection, qualification, approval, and scope are evidenced.
- [ ] Purchasing information defines requirements, acceptance, records, change
      notification, and sub-tier flow-down as applicable.
- [ ] Incoming/acceptance verification is risk-based and linked to supplier
      performance.
- [ ] Quality agreements assign responsibilities for critical/outsourced processes.
- [ ] Monitoring, re-evaluation, audits, nonconformity, SCAR/CAPA, effectiveness,
      escalation, and disqualification are controlled.
- [ ] Supplier changes route through product/process risk, validation, and change
      control before acceptance.

## Production, service, validation, and software

- [ ] Infrastructure, maintenance, environment, contamination/cleanliness,
      personnel, instructions, and process parameters are controlled as applicable.
- [ ] Materials/components, equipment, software, methods, labeling/packaging,
      acceptance, release, preservation, distribution, installation, and service
      records are traceable.
- [ ] Processes whose output needs validation have approved protocols, acceptance
      criteria, qualified resources, deviations, results, revalidation triggers, and
      change approval.
- [ ] Monitoring/measurement equipment has identification, status, traceability,
      calibration/verification, maintenance, out-of-tolerance impact, and records.
- [ ] QMS and production software has intended use, risk, requirements,
      configuration, access/data-integrity controls, validation, release, incident,
      backup/recovery, supplier, and change/revalidation evidence.
- [ ] Product release is performed by authorized personnel against approved criteria.

## Identification and traceability

- [ ] Approved scope defines the needed extent for each product and jurisdiction.
- [ ] Material/component, lot/serial/UDI, process, acceptance/release, distribution,
      installation, and service evidence is linked as applicable.
- [ ] Traceability supports complaint, investigation, correction/removal, vigilance,
      field action, and CAPA decisions.
- [ ] Record retention and retrieval preserve traceability for the approved period.

## Complaints, feedback, postmarket, and vigilance

- [ ] Intake captures source, device, event, dates, reporter, and potential safety/
      performance issue without losing original information.
- [ ] Evaluation and investigation have owners, rationale, evidence, product/risk
      impact, and approved conclusions.
- [ ] Authorized roles make jurisdiction-specific reportability/vigilance and field-
      action decisions within controlled workflows.
- [ ] Trends and postmarket plans/reports use defined data sources, methods, review
      intervals, thresholds, limitations, and actions.
- [ ] Feedback links to risk, design, suppliers, production, labeling, validation,
      CAPA, and management review.
- [ ] MDR/IVDR work considers current MDCG PMS/vigilance guidance as nonbinding
      guidance with exact document/revision/date.

## Nonconformity and CAPA

- [ ] Nonconforming outputs are identified, controlled, evaluated, segregated where
      appropriate, dispositioned by authorized roles, and reverified after rework.
- [ ] Correction/containment, concession, post-delivery action, regulatory review,
      and affected-party communication are evidenced.
- [ ] CAPA intake defines source, factual problem, scope, risk/reportability review,
      and decision rationale.
- [ ] Investigation evidence supports the root cause or justified conclusion and
      systemic-extent review.
- [ ] Actions address the supported cause/risk and link to change, validation,
      training, supplier, product, and postmarket controls.
- [ ] Effectiveness plans define objective criteria, baseline, sample/window, timing,
      independent reviewer, evidence, and approval.
- [ ] Pending, insufficient, or ineffective evidence blocks closure.

## Internal audit and management review

- [ ] Audit program is risk-based and covers applicable processes, sites, products,
      shifts/time, prior findings, and changes over a justified cycle.
- [ ] Audit plans define criteria, scope, sampling, methods, competence, and
      independence.
- [ ] Reports separate evidence, findings, corrections, CAPA decisions, owners,
      dates, and effectiveness follow-up.
- [ ] Management review inputs are controlled and complete for the approved agenda.
- [ ] Outputs record decisions, resources, changes, actions, owners, due dates, and
      follow-up.
- [ ] FDA inspection preparation accounts for current access to management, internal-
      audit, and supplier-audit records under QMSR.

## Training, competence, and change control

- [ ] Roles have competence criteria and objective evidence of education, training,
      skills, experience, and authorization.
- [ ] Training is completed and effectiveness assessed before independent work or
      document effective use, as risk justifies.
- [ ] Changes identify source/version, reason, affected scope, risk, product,
      validation/software, supplier, production, document/record, training,
      postmarket, and regulatory/certification impacts.
- [ ] Changes have implementation plans, approvals, rollback/contingency where
      needed, verification, and closure evidence.

## Current QMSR transition evidence

As of this research date, QMSR is effective and FDA uses Compliance Program
7382.850. Review:

- [ ] current eCFR and incorporated-edition source basis;
- [ ] FDA supplemental provisions and linked current regulations;
- [ ] disposition of obsolete QSR/QSIT references;
- [ ] pre-2026-02-02 QMS record evidence;
- [ ] inspection-accessible management, quality-audit, and supplier-audit records;
- [ ] complaint/servicing records and labeling/packaging controls;
- [ ] updated inspection-process training;
- [ ] supplier, software-validation, and change-control evidence; and
- [ ] removal of claims that ISO certification establishes FDA compliance or an
      inspection exemption.

Use `scripts/check_qmsr_transition.py`; do not create a legacy-QSR clause map as the
current control framework.

## Laboratory scope, impartiality, and competence (`iso-17025`, `iso-15189`)

- [ ] Declared scope of laboratory activities is recorded per location, per method or
      examination, with the measurand or property and the range or sample type.
- [ ] Declared scope is reconciled against the current accredited scope schedule, and
      any work outside it is identified with its claim controls.
- [ ] Accreditation symbols, endorsement wording, and recognition-arrangement phrasing
      are current, authorized, and used only within scope.
- [ ] Impartiality risks are identified with controls, review evidence, and an owner —
      not a bare policy statement.
- [ ] Authorized signatories are listed with the scope each covers and the competence
      evidence behind the authorization.
- [ ] Personnel competence is evidenced per activity: training, authorization,
      ongoing monitoring, and reauthorization after change.
- [ ] Facilities and environmental conditions that affect results are monitored, with
      records and action on excursions.
- [ ] Equipment records cover calibration status, intermediate checks, out-of-service
      handling, and the effect of any failure on previously reported results.

## Metrological traceability, uncertainty, and decision rules (`iso-17025`, `iso-15189`)

- [ ] Traceability is documented as a chain per measurement: stated reference, provider
      and its accreditation scope, certificate identity, uncertainty carried forward,
      interval justification, and intermediate checks.
- [ ] Where no reference system exists for a measurand, that fact and the alternative
      comparability approach are recorded and authorized.
- [ ] Measurement uncertainty is evaluated for the measurands that require it, with a
      stated basis, contributions, and controlled revision.
- [ ] Reported uncertainty and its relationship to the decision rule are consistent
      with the report wording.
- [ ] Where conformity is stated, the decision rule is documented, agreed where
      required, and applied consistently at the specification limit.
- [ ] The policy basis for traceability and decision rules is cited by current
      designation and issue, confirmed rather than assumed.

## Methods, validity of results, and reporting (`iso-17025`, `iso-15189`)

- [ ] Each scope item is classified: standard method used as published, modified or
      out-of-scope standard method, non-standard method, or laboratory-developed
      method. An unmodified standard method still needs laboratory performance
      verification; record validation for the intended use where applicable.
- [ ] Verification or validation records show performance characteristics evaluated,
      acceptance criteria, data, and authorized approval to put into service.
- [ ] Methods are revisited after instrument, reagent, personnel, or issue changes.
- [ ] Proficiency-testing or external-quality-assessment enrolment covers the scope
      items it should, with a documented plan and frequency.
- [ ] Every questionable or unsatisfactory PT/EQA result has an investigation, an
      action, and effectiveness evidence. **Treat an uninvestigated unsatisfactory
      result as a blocker.**
- [ ] Where no scheme exists, the alternative comparison approach is recorded and
      authorized.
- [ ] Technical records are sufficient to reproduce the reported result, with
      identifiable personnel, dates, and revisions.
- [ ] Report and certificate content, amendment and retraction handling, and
      authorized signature are controlled.
- [ ] Nonconforming work has documented evaluation, action, customer notification where
      required, and recall or amendment of affected results.

## Medical laboratory pre- and post-examination (`iso-15189`)

- [ ] Request content, patient identification, and primary sample identification
      controls are evidenced by records, including identification-error events and their
      investigations.
- [ ] Collection, transport, stability, acceptance, and rejection criteria are recorded,
      with rejection and transport-excursion records sampled.
- [ ] Result review and authorization before release is evidenced per examination.
- [ ] Biological reference intervals and clinical decision limits have a documented
      basis for the population served, not only a package-insert citation.
- [ ] Critical-result notification records exist, with recipient, time, read-back, and
      timeliness against the defined requirement.
- [ ] Interpretive comments are made only by authorized persons, per a controlled basis.
- [ ] Point-of-care testing under the laboratory's responsibility has governance,
      operator authorization, QC, connectivity, and reconciliation evidence.
- [ ] Laboratory information management covers data integrity, access control, change
      control, validation of the system and of interfaces, and downtime handling.
- [ ] Continuity and emergency arrangements have been exercised, with records — not a
      plan nobody has tested.
- [ ] CLIA, licensure, and payer evidence is kept in a separate register, with no
      implication that ISO 15189 accreditation satisfies any of them.

## Regime handoff

Before final review, state which authorized party owns the next decision:

- ISO certification body for certification audit/certificate decisions;
- the accreditation body and its assessors for accreditation and scope decisions;
- CMS, the CMS-approved accreditation organization, or the state agency for CLIA
  certification, deemed status, and licensure decisions;
- FDA for inspection and enforcement decisions;
- MDSAP-recognized Auditing Organization and participating authorities for MDSAP;
- designated MDR/IVDR notified body and competent authorities for applicable EU
  conformity-assessment/regulatory decisions;
- authorized management, RA/QA, legal, and product specialists for organizational
  decisions.

## Deterministic tooling

- `validate_scope_intake.py` — accountable scope/applicability decisions (`--standard`)
- `audit_document_records.py` — document, record, retention, and source register
- `check_capa.py` — CAPA/effectiveness closure gates
- `check_traceability.py` — risk/design/production/postmarket links; device lanes only,
  and **not** metrological traceability
- `check_qmsr_transition.py` — current post-effective-date QMSR evidence; US device lane
- `validate_evidence_manifest.py` — bounded local readiness manifest (`--standard`)
- `check_supplier_controls.py` — risk-based supplier and external-provider evidence
- `gap_analyzer.py` — domain coverage without keyword or percentage scoring
  (`--standard`)

Pass `--standard iso-13485|iso-14971|iso-17025|iso-15189` to the three profile-aware
checks so the domain vocabulary matches the standard under review. An unlisted value is
refused rather than defaulted.

All tools are local JSON/Markdown structural checks. Exit 0 means only that no
structural finding was generated for the supplied data.
