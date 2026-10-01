# Diagnostic-Report Scaffolds

These assets are structured field maps for authorized clinical services. They do not interpret data or produce a report suitable for patient care.

## Radiology

The ACR **Practice Parameter for Communication of Diagnostic Imaging Findings**, revised 2025 (Resolution 9), addresses diagnostic imaging reports, final-report principles, preliminary reports, nonroutine communication, informal communication, and organizational communication policies.

Use `assets/radiology_report_template.json` only to map verified facts such as:

- examination identity and status;
- clinical indication as supplied;
- technique and documented limitations;
- comparison-source references;
- findings and impression authored by the qualified interpreting professional;
- nonroutine-communication record references;
- amendments/corrections and report version.

Do not:

- inspect or interpret images;
- generate normal findings, pertinent negatives, differential diagnoses, urgency, follow-up, or management recommendations;
- select BI-RADS, LI-RADS, Lung-RADS, PI-RADS, or another category;
- infer that a preliminary report is final;
- initiate, simulate, or document a communication that did not occur.

The responsible radiologist and organization control report content, communication, correction, and signature.

## Pathology

CAP publishes and updates organ- and specimen-specific Cancer Protocols. The current CAP page lists 16 September 2026 updates across 14 protocols, including retirement of the Vaginal Biopsy protocol. Verify the selected protocol’s current scope and implementation requirements rather than reusing the earlier June snapshot. Protocol versions and required/core or conditional elements can change.

Use `assets/pathology_report_template.json` only after a qualified pathologist selects:

- exact organ/site and specimen/procedure;
- current CAP protocol title and version, if applicable;
- applicable biomarker protocol and staging edition;
- local laboratory/reporting requirements.

For CAP synoptic reporting within its scope, core and conditionally required data elements are represented as data-element/response pairs; applicability depends on the exact current protocol. CAP states that Biomarker Reporting Protocols provide reporting guidance and are not required for accreditation; do not extend a cancer-protocol accreditation requirement to every biomarker template.

Do not:

- generate a gross or microscopic observation;
- determine diagnosis, grade, stage, margin status, biomarker interpretation, or adequacy;
- apply a generic cancer checklist in place of the current exact protocol;
- convert `cannot be determined` or `not applicable` into a definitive value;
- create a signature or final diagnosis.

## Laboratory

For applicable US nonwaived testing, 42 CFR 493.1291 addresses accurate and timely transmission, required report information, referral-laboratory handling, accessibility, and corrected reports. The exact regulation and laboratory policy control.

Use `assets/lab_report_template.json` only to map results already released by the performing laboratory or verified source system. Preserve:

- report status and version;
- performing laboratory/source-system reference;
- specimen and test identifiers held in the authorized system, not copied into examples;
- result, units, reference interval, flags, method, and comments exactly as released;
- correction link to both original and corrected reports;
- documented notification reference when one exists.

Do not:

- calculate, normalize, convert, interpret, flag, or suppress a patient result;
- supply a reference interval or “critical” threshold;
- infer specimen adequacy;
- recommend follow-up or treatment;
- alter a referral laboratory’s result or interpretation;
- release or sign a report.

## Privacy and record integrity

Operational diagnostic reports often require identifiers for positive patient matching. This skill does not process those production records. It accepts only synthetic, de-identified, or aggregate manifests. Use institution-controlled systems for real clinical records and follow applicable access, retention, correction, audit, and disclosure procedures.

Every draft scaffold must remain `DRAFT_NOT_FOR_CLINICAL_USE` until the responsible licensed service reviews and completes it in its authorized system.
