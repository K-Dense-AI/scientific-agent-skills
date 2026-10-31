# Documentation and Evidence Architecture

Research basis: **2026-10-01**; current-source details are in `references/source-ledger.md`. This is a
process-oriented planning reference, not a list of copyrighted ISO or IEC requirements.

The five-layer hierarchy below applies to every standard this skill covers. Where the
wording is device-specific, the laboratory equivalent is noted; for depth read
`references/iso-17025.md` or `references/iso-15189.md`.

## Do not use a fixed “31 procedures” claim

ISO 13485 does not require one universal package of a fixed number of separately
titled procedures for every organization. Document architecture depends on QMS
scope, products, lifecycle activities, sites, outsourced processes, applicable
regulatory requirements, and how controlled processes are combined or split.

Avoid:

- declaring a QMS complete because a named-document count was reached;
- equating a filename or keyword hit with implementation;
- treating an example document name as mandatory;
- labeling every conditional process “not applicable” without an authorized decision;
- assuming one regime's records satisfy another regime; or
- claiming certification/readiness from document presence.

Use an authorized copy of ISO 13485 and current jurisdiction/product sources to
identify the documentation and records that actually apply. ISO publications are
copyrighted; see [ISO copyright](https://www.iso.org/copyright.html).

## Controlled evidence hierarchy

### 1. Source and applicability layer

Maintain:

- dated official-source ledger with exact edition/version;
- product/site/market/lifecycle scope intake;
- authorized applicability and not-applicable decisions;
- regulatory/product-requirements matrix;
- certification, MDSAP, FDA, and EU assurance-route distinctions;
- source-change monitoring and impact assessments.

Minimum fields: source ID, publisher, title, edition/version/date, authorized
location, access date, owner, status, currency-review date, impact record, and
approval.

### 2. Governance and policy layer

Typical controlled documents and records:

- QMS scope and quality manual or equivalent policy architecture;
- quality policy/objectives and measures;
- organization chart, role authorities, delegates, independence, and escalation;
- authorized management representative appointment;
- process-interaction map;
- management review plan, records, decisions, and follow-up.

The quality manual is not evidence that the processes operate. Link it to approved
procedures and sampled implementation records.

### 3. Process-control layer

An organization may combine or separate controlled procedures. Use titles that match
actual work. At minimum, assess whether controlled documentation is needed for:

- document, record, and external-source control;
- risk management;
- design and development, transfer, and design change;
- customer/product requirements and communications;
- suppliers, purchasing, outsourced processes, and acceptance;
- production, service, infrastructure, environment, and maintenance;
- process, equipment, test-method, and software validation;
- monitoring/measurement equipment;
- identification, traceability, preservation, installation, and servicing;
- feedback, complaints, postmarket surveillance, and vigilance/reporting;
- nonconforming outputs, corrections, removals/advisory actions, and CAPA;
- internal audit, data/trend analysis, and management review;
- competence, training, authorization, and awareness; and
- QMS/product/process/source/software change control.

Each controlled process should identify purpose, scope, roles, inputs, outputs,
methods, decision criteria, records, interfaces, measures, change controls,
source/version basis, approval, and effective date.

### 4. Product and technical evidence layer

Maintain a controlled file architecture for each applicable product/type/family.
Depending on product and jurisdiction, evidence may include:

- product description, intended purpose/use, claims, variants, accessories;
- classifications and authorized decision records;
- requirements/specifications and acceptance criteria;
- risk management and benefit-risk evidence;
- design planning, inputs, outputs, reviews, verification, validation, transfer,
  and changes;
- production, supplier, packaging, labeling, installation, and service information;
- software lifecycle, cybersecurity, usability, biocompatibility, electrical safety,
  sterilization, clinical/performance, and other product-specific evidence;
- acceptance/release and distribution/traceability records;
- postmarket plans, reports, complaints, vigilance, field actions, and updates.

Do not claim that an ISO 13485 “medical device file” automatically replaces every
FDA, EU, or other jurisdiction-specific file or record concept. Build a cross-reference
that preserves each required record and its source/version.

**Laboratory equivalent.** For ISO/IEC 17025 and ISO 15189 the technical evidence layer
is organized per scope item — per method, measurand, or examination — rather than per
product family. Depending on the activity it may include:

- the controlled method or examination procedure and its issue, with the authorization
  to put it into service;
- verification or validation evidence: performance characteristics evaluated,
  acceptance criteria, data, and approval;
- the measurement-uncertainty evaluation and its stated basis;
- metrological traceability evidence: stated reference, provider and its accreditation
  scope, certificate identity, uncertainty carried forward, interval justification, and
  intermediate checks;
- the documented decision rule and customer-agreement record where conformity is
  stated;
- proficiency-testing or external-quality-assessment enrolment, results, evaluation
  against criteria, and investigation of unsatisfactory outcomes;
- equipment, reagent, consumable, and reference-material records;
- technical records sufficient to reproduce the reported result; and
- report and certificate templates, amendment/retraction handling, and authorized
  signatories.

An accredited scope schedule is not this layer — it is the output of the accreditation
body. Keep the two apart in the register.

### 5. Implementation-record layer

Procedures describe controls; records show what happened. Sample actual records for:

- approvals, revision/effective status, training, and point-of-use control;
- competence and role authorization;
- management review inputs, decisions, resources, actions, and follow-up;
- internal audits, findings, corrections/CAPA, and effectiveness;
- risk reviews and links to design/production/postmarket changes;
- design reviews, verification, validation, transfer, and changes;
- supplier qualification, agreements, monitoring, change notices, re-evaluation,
  nonconformity, and CAPA;
- production/service work, process parameters, acceptance, release, validation,
  revalidation, maintenance, and calibration;
- software intended use, risk, validation, release, incidents, and changes;
- identification, traceability, distribution, installation, and service;
- complaints, investigations, reportability/vigilance decisions, and communications;
- nonconformity, disposition, corrections, CAPA, and effectiveness; and
- data analysis, trends, objectives, escalation, and change decisions.

## Fail-closed document register

For every controlled document, capture:

- unique ID, title, type, owner, revision, and status;
- source/version references and change rationale;
- reviewers/approvers and approval evidence;
- effective date and training impact;
- linked documents, forms, records, systems, products, suppliers, and processes;
- obsolete/superseded disposition; and
- controlled location and access classification.

For every record series, capture:

- owner, record type, creation/attribution method, and status;
- integrity, security, audit trail, backup/recovery, retrieval, and correction controls;
- exact retention period and approved basis;
- disposition method and authorization;
- applicable products/sites/jurisdictions;
- evidence samples and approval.

Unknown, placeholder, unapproved, uncontrolled, or inaccessible entries are gaps—not
assumed evidence.

## Regime-specific supplements

### ISO certification

Maintain the authorized standard edition, certification scope, sites/activities,
certification-body and accreditation-scope evidence, audit program, findings, and
certificate status. A certificate is limited to its scope and is not a product or
regulatory authorization.

### Laboratory accreditation (ISO/IEC 17025, ISO 15189)

Maintain the authorized standard edition, the scope of laboratory activities as
declared and as accredited, per-location coverage, the accreditation body and its own
recognition status, assessment history and findings with their closure evidence, and
current accreditation status including any suspension or scope reduction.

Additional controls specific to this lane:

- **Claim control.** Record where accreditation symbols and endorsement wording may and
  may not be used, and who authorizes each use. Work outside the accredited scope must
  carry no accreditation claim. Since 2026-01-01 the recognition arrangement sits with
  Global Accreditation Cooperation Incorporated — verify current wording rather than
  reusing legacy ILAC MRA / IAF MLA phrasing.
- **Scope-change control.** New methods, extended ranges, new locations, and new
  authorized signatories are scope questions for the accreditation body, not only
  internal change control. Keep the notification and approval records.
- **Authorized signatories.** Maintain the current list, the scope each is authorized
  for, and the competence evidence behind each authorization.
- **Subcontracting and referral.** Record the provider, its own accreditation or
  licensure status, the customer-notification basis, and how results are reported.

For ISO 15189 specifically, keep CLIA, licensure, and payer evidence in a **separate**
register. ISO 15189 accreditation does not satisfy CLIA, and blending the two produces
a register that implies an equivalence that does not exist. See
`references/iso-15189.md`.

### FDA QMSR

Since **2026-02-02**, use current
[21 CFR Part 820](https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-820),
the incorporated ISO edition, current FDA supplemental provisions, and other
applicable FDA regulations. FDA now uses
[Compliance Program 7382.850](https://www.fda.gov/media/80195/download?attachment),
not QSIT. Keep evidence for current complaint, servicing, labeling/packaging, and
other FDA-specific requirements. Do not retain old QSR section numbers as the
current control model.

FDA's
[QMSR FAQ](https://www.fda.gov/medical-devices/quality-management-system-regulation-qmsr/quality-management-system-regulation-frequently-asked-questions)
states that investigators may review pre-effective-date QMS records and management,
quality-audit, and supplier-audit reports. Prepare controlled retrieval without
rewriting history or backdating records.

### MDSAP

Use the current
[MDSAP AU P0002.011 Audit Approach](https://www.mdsap.global/documents/library/audit-approach),
dated 2026-08-03, and the current MDSAP document library. Record participating
jurisdictions, products, sites, recognized Auditing Organization, audit cycle,
jurisdiction-specific evidence, findings, and action status. Do not substitute an
ISO-only certificate or FDA inspection checklist.

### EU MDR/IVDR

Keep the current consolidated regulation, conformity-assessment route, device
classification, technical documentation, QMS, clinical/performance, postmarket,
vigilance, registration/UDI, economic-operator, and notified-body evidence as
applicable. Verify notified-body designation and codes in
[NANDO](https://webgate.ec.europa.eu/single-market-compliance-space/notified-bodies).
MDCG guidance is useful but nonbinding; record document number, revision, date, and
impact.

For European standards, distinguish ISO publications from EN adoptions,
corrigenda, and European A11 amendments. Verify current OJEU citations on the
Commission's
[harmonised standards page](https://health.ec.europa.eu/medical-devices-topics-interest/harmonised-standards_en).

## Retention: no universal period

Do not use generic “5–10 year” statements or “device lifetime” as a complete
retention schedule. For each record type, authorized reviewers should reconcile:

- current standard and regulatory sources;
- product/device lifetime and market-specific periods;
- complaint, vigilance, traceability, clinical/performance, technical-documentation,
  and certificate obligations;
- legal hold, privacy, contract, and business requirements; and
- system migration and durable retrieval.

Record the chosen period, start event, source/version, rationale, owner, approval,
disposition method, and hold override.

## Evidence-quality gate

A document or record is ready for substantive human review only when:

- scope and applicability are resolved or explicitly blocked;
- owner and status are clear;
- referenced controlled revision exists;
- approval and effective dates are recorded;
- implementation evidence is sampled;
- source versions are current and traceable;
- open findings and change/CAPA links are visible; and
- the artifact makes no unsupported compliance, conformity, certification, or
  readiness claim.

Use `scripts/audit_document_records.py` for structural checks and
`scripts/validate_evidence_manifest.py` for a bounded local manifest. Passing either
means only that the supplied fields passed deterministic checks.
