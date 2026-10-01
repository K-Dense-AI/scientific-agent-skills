# Privacy and Data Governance

Last reviewed: **2026-10-01**

## No compliance claim

Passing a template or script does not establish de-identification, HIPAA compliance, authorization, lawful disclosure, security, or appropriate retention. Those determinations belong to qualified local privacy, security, legal, and records personnel.

## Data classes

Use exactly one package-wide classification:

- `synthetic` — invented records with no relationship to a real person.
- `deidentified_qualified_review` — patient-derived information that a qualified reviewer has approved under the applicable method and context.
- `real_patient_minimum_necessary` — identifiable or potentially identifiable data handled only in an authorized local environment.

Never relabel real data as synthetic. Hashing, pseudonymization, redaction of obvious fields, using a patient code, or removing direct identifiers does not by itself make data de-identified.

## HHS de-identification boundary

HHS describes two HIPAA Privacy Rule methods:

1. **Expert Determination** — a qualified expert determines that re-identification risk is very small and documents methods and results.
2. **Safe Harbor** — specified identifiers are removed and the covered entity lacks actual knowledge that remaining information could identify an individual.

This skill performs neither method. Free text, dates, geography, rare combinations, longitudinal patterns, and other contextual information can retain identification risk. HHS specifically notes that clinical narratives are information-rich and may allow identification.

For patient-derived material:

- document which method and policy were applied;
- record the qualified reviewer's role, review date, scope, assumptions, and expiration or re-review condition;
- keep the determination and supporting analysis in the authorized local system;
- re-review after material data, recipient, linkage, technology, or purpose changes;
- treat uncertainty as a release blocker.

Do not place a de-identification analysis or patient-derived examples in this repository.

## Minimum-necessary handling

HHS states that the HIPAA minimum necessary standard generally requires reasonable steps to limit uses, disclosures, and requests for protected health information, while identifying exceptions including disclosures to or requests by a healthcare provider for treatment.

This skill does not decide whether an exception applies. As a conservative process safeguard, always minimize what enters the package and follow the institution's current role-based access and disclosure policies.

Record:

- the specific documentation purpose;
- authorized users and recipient;
- required data categories;
- excluded data categories;
- local authorization and environment references;
- retention and disposition requirements;
- who approved any exception or broader access.

## Real-patient gate

Before any real-patient package is opened:

1. Confirm local authorization and an approved environment.
2. Confirm the accountable clinical and privacy owners.
3. Confirm the minimum-necessary field set and intended recipient.
4. Confirm no external service, model, API, search, telemetry, image, or cloud-processing step will receive content.
5. Confirm content will not be copied into prompts, logs, examples, tests, screenshots, issue reports, or commit messages.
6. Confirm retention, deletion, access, and incident-response rules.
7. Run only local standard-library scripts against file paths.

If any confirmation is absent, use synthetic templates and stop before reading values.

## Structured-data preference

Prefer discrete identifiers, enums, dates, booleans, role labels, and source references. Use bounded clinician-authored text only where exact transcription is necessary.

Avoid:

- copied progress notes, discharge narratives, portal messages, or full record exports;
- names, addresses, contact information, dates of birth, medical-record numbers, account numbers, images, biometrics, or device identifiers;
- exact free-text descriptions when a structured status or local record locator is sufficient;
- patient details in filenames or directory names.

The generic `subject_ref` must be a locally controlled pseudonymous reference. It is not proof of de-identification.

## Report minimization

Bundled scripts must not echo clinical values. Reports are limited to:

- rule codes;
- pass/fail status;
- document types;
- field paths;
- counts;
- explicit dates in the separate schedule output, which can be identifying when derived from patient records;
- local filenames without parent-directory expansion.

Do not run scripts with shell tracing. Do not redirect reports to shared logs. Review local command history policies before working with sensitive paths.

## Local path controls

The scripts:

- reject URL-like input paths and network-share syntax;
- reject leaf symlink inputs and outputs (ancestor directories and mounted volumes require local verification);
- accept only bounded regular UTF-8 JSON files;
- reject duplicate keys, excessive nesting, oversized text, excessive records, and unknown fields;
- create private outputs without implicit overwrite;
- do not inspect environment variables or credential files.

These are defense-in-depth controls, not privacy determinations. A local-looking path can still be network-mounted or cloud-synchronized. Verify the resolved storage, access controls, backups, and telemetry in the authorized environment; these helpers do not create a sandbox. POSIX file modes do not establish Windows ACL protections.

The schedule is not de-identified merely because names and clinical text are omitted. Under HIPAA Safe Harbor, dates directly related to an individual generally require removal of all elements except year. This schema requires full calendar dates for checkpoints and some review fields, so it cannot represent every Safe Harbor-derived record. Do not invent dates or relabel the data to satisfy the schema: keep incompatible records in the approved source workflow and have qualified reviewers determine any permitted method and context.

## Incident routing

If accidental disclosure, unauthorized access, or suspected mishandling occurs:

- stop processing;
- preserve only what local policy requires;
- use the institution's current privacy/security incident route;
- do not investigate by copying content into another tool;
- do not decide whether an event is reportable;
- record the responsible role and local case/reference number only after authorization.

HHS OCR breach reporting sources are listed in `source_ledger.md`. The skill does not file reports.
