# Privacy and De-identification

This reference documents a review process. It is not legal advice, a technical de-identification service, or evidence of HIPAA compliance.

## HHS framework

HHS guidance under 45 CFR 164.514(b) describes two methods:

1. **Expert Determination** — a person with appropriate knowledge and experience applies generally accepted statistical and scientific principles and documents that re-identification risk is very small under the anticipated conditions.
2. **Safe Harbor** — specified identifiers are removed and the covered entity has no actual knowledge that remaining information could identify an individual.

A local script cannot perform Expert Determination, establish “no actual knowledge,” or decide whether an organization is a covered entity or business associate.

## Safe Harbor identifier categories

The responsible privacy professional must review the exact regulation and HHS guidance. The categories include:

1. names;
2. geographic subdivisions smaller than a state, subject to the specific ZIP-code rule;
3. date elements more specific than year directly related to an individual, plus the age rule for persons over 89;
4. telephone numbers;
5. fax numbers;
6. email addresses;
7. Social Security numbers;
8. medical record numbers;
9. health-plan beneficiary numbers;
10. account numbers;
11. certificate or license numbers;
12. vehicle identifiers and serial numbers;
13. device identifiers and serial numbers;
14. URLs;
15. IP addresses;
16. biometric identifiers;
17. full-face photographs and comparable images;
18. other unique identifying numbers, characteristics, or codes.

Removal of obvious patterns is insufficient. Initials, partial identifiers, metadata, free text, rare events, small cells, unusual dates, images, and combined quasi-identifiers may still identify a person.

## Minimum necessary

HHS states that covered entities generally take reasonable steps to limit uses, disclosures, and requests for PHI to the minimum necessary for the purpose. HHS also lists exceptions, including certain treatment disclosures, disclosures to the individual, authorized uses/disclosures, uses/disclosures required for HIPAA administration, HHS enforcement, and uses/disclosures required by law.

Do not apply the phrase mechanically. The responsible privacy/legal reviewer determines scope, exceptions, authorization, waiver, limited-data-set rules, and any more protective law or policy.

## Local process

1. Define purpose, recipient, authority, jurisdiction, and data class.
2. Exclude fields not needed for the purpose.
3. Keep source records in the authorized system; use authorized opaque locators and integrity hashes in the draft workspace. A locator, value hash, or aggregate can still disclose information: hashing an identifier is not a Safe Harbor substitute, and predictable values can be guessed. Include the manifest itself in privacy review.
4. Select Safe Harbor, Expert Determination, or a documented synthetic/aggregate-data rationale through the responsible reviewer.
5. Review structured fields, free text, attachments, images, headers, filenames, metadata, and linked data.
6. Review combinations and small-cell/rare-case risk.
7. Record actual-knowledge review or Expert Determination documentation as applicable.
8. Verify access controls, storage, transmission, retention, and deletion under organizational policy.
9. Obtain privacy/legal/institutional approval for the intended disclosure.
10. Re-review after every content, recipient, or purpose change.

## What the checklist does

`assets/deidentification_process_checklist.json` and `scripts/check_deidentification.py` verify that required process fields are documented. They deliberately:

- do not scan patient free text;
- do not output detected identifiers;
- do not label a document `COMPLIANT`, `SAFE`, or `DEIDENTIFIED`;
- do not substitute for Expert Determination or legal review;
- block missing process declarations and retain a review-required status even when the declarations are complete.

The strongest successful result is `PROCESS_DOCUMENTED_REVIEW_REQUIRED`.

## Consent and authorization

Publication consent, research consent, HIPAA authorization, IRB/Privacy Board waiver, and permission to use an image are distinct. Do not infer one from another or generate a stock assertion.

Record only the status and local documentation reference verified by the responsible human. Never store a signed consent form or direct identifier in this skill’s assets, tests, or example manifests.

## Incident handling

If real PHI is unexpectedly present:

1. stop processing;
2. do not echo, copy, transform, or upload it;
3. preserve only the minimum operational information needed under policy;
4. notify the authorized privacy/security contact through the institution’s process;
5. do not independently determine breach status or notification duties.
