# Authoritative Source Ledger

Review date: **2026-10-01**. Scope: all six JSON assets, eight standard-library
helpers, and documentation references. These sources support documentation design;
this is not a clinical evidence review, treatment recommendation, or deployment approval.

Method: current official page/PDF content read with web browsing. NICE NG197 and
AHRQ PSO returned access errors in that reader, so their official content was
retrieved with `parallel-cli extract --max-age-seconds 600 --disable-cache-fallback`.
Historical publication dates below are distinct from this review date. No patient
content, clinical queries, authenticated scientific API calls, or submissions were used.

## Privacy and data governance

- [HHS OCR de-identification guidance](https://www.hhs.gov/hipaa/for-professionals/special-topics/de-identification/index.html):
  Expert Determination and Safe Harbor are distinct methods. Removing obvious
  identifiers or using pseudonyms does not itself establish either method. Full dates
  related to a person can prevent Safe Harbor qualification; the schedule is still
  patient-derived data. Qualified review, recipient context, and free-text risk remain
  outside the helpers' capabilities. The schema cannot represent every date-suppressed
  record; never invent a full date to pass validation.
- [HHS Minimum Necessary Requirement](https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/minimum-necessary-requirement/index.html):
  confirms the general limitation principle and exceptions, including disclosures to
  or requests by a provider for treatment. This skill's minimization rule is an
  operational safeguard, not a claim that the legal standard applies to every use.
- [HHS Breach Notification Rule](https://www.hhs.gov/hipaa/for-professionals/breach-notification/index.html):
  route potential incidents to qualified local reviewers; the skill determines no duty,
  breach status, deadline, or required content.
- [OCR breach portal](https://ocrportal.hhs.gov/ocr/breach/breach_frontpage.jsf):
  the old `breach_report.jsf` entry redirects to this front page. It now presents
  HIPAA and 42 CFR Part 2 routes. The local owner must determine applicability;
  no portal form was opened or submitted. This is a human interface, not an API.

## FDA labeling and medication-risk programs

- [FDA human prescription-drug labeling resources](https://www.fda.gov/drugs/laws-acts-and-rules/fdas-labeling-resources-human-prescription-drugs):
  distinguishes Drugs@FDA's CDER-approved labeling from current/in-use labeling
  that can include company-submitted changes under review. Confirm exact product
  and source scope through an authorized professional; these helpers interpret no label.
- [FDA patient labeling resources](https://www.fda.gov/drugs/fdas-labeling-resources-human-prescription-drugs/patient-labeling-resources):
  distinguishes Medication Guides, Patient Package Inserts, Instructions for Use,
  and consumer medication information. Not every prescription drug requires
  FDA-approved patient labeling; generic consumer information is not FDA-reviewed.
- [FDA: What's in a REMS?](https://www.fda.gov/drugs/risk-evaluation-and-mitigation-strategies-rems/whats-rems):
  describes product-specific roles and activities. Its overview cannot establish
  current requirements for an individual product or person.
- [REMS@FDA](https://www.accessdata.fda.gov/scripts/cder/rems/index.cfm):
  current public table separates approved current programs from historical/released
  data files, with program-specific update dates and linked materials. Public content
  was read; no eligibility, enrollment, certification, prescribing, or dispensing was tested.

## Medication safety and care transitions

- [WHO: Transitions of Care](https://www.who.int/docs/default-source/patient-safety/9789241511599-eng.pdf?sfvrsn=a577528_2):
  **2016** Technical Series on Safer Primary Care. The prior ledger's September 19
  date was a references-access date, not an established publication date. Supports
  information transfer, reconciliation process, involvement, ownership and local
  adaptation. It is older process guidance, not a current specialty treatment guideline.
- [Joint Commission National Performance Goals](https://www.jointcommission.org/en-us/standards/national-performance-goals):
  the NPG chapter replaced NPSGs for Hospital and Critical Access Hospital programs
  effective **2026-01-01**. This is program-specific, not a universal care-plan mandate.
- [Joint Commission NPG 1 brief](https://digitalassets.jointcommission.org/api/public/content/2361b813982a420cb9590bd363d9c3f1?v=994360b5):
  the linked brief still labels itself 2025. Its identification, hand-off communication,
  and continuity concepts are used as process context only; the current program page
  controls the chapter's effective date. No proprietary standards are reproduced or
  accreditation conformity asserted.

## Shared decisions and person-centered planning

- [AHRQ SHARE Approach](https://www.ahrq.gov/sdm/share-approach/index.html):
  current canonical address redirects from the prior health-literacy path. Page
  reviewed **February 2026**; describes the clinician-led model and revised training.
  This skill records supplied documentation of the conversation, not options or risks.
- [AHRQ Shared Decisionmaking strategy](https://www.ahrq.gov/cahps/quality-improvement/improvement-guide/6-strategies-for-improving/communication/strategy6i-shared-decisionmaking.html):
  page reviewed **April 2023**. Supports balanced decision aids and expressed
  preferences as process context; it is not a current disease-specific evidence review.
- [NICE NG197](https://www.nice.org.uk/guidance/ng197):
  published and last reviewed **2021-06-17**, verified in the current official page.
  Adult scope excludes unexpected emergencies requiring immediate life-saving care
  and decisions when an adult lacks relevant capacity. Professional judgment and
  local applicability remain necessary; the skill assesses neither capacity nor consent.
- [CMS Person-Centered Care](https://www.cms.gov/priorities/innovation/key-concepts/person-centered-care):
  originally posted **2023-08-14**. Describes goals, values, preferences,
  communication, coordination and patient-reported outcomes. This concept page is
  not a universal documentation, coding, billing or reimbursement requirement.

## Reporting and safety governance

- [FDA MedWatch reporting overview](https://www.fda.gov/safety/medwatch-fda-safety-information-and-adverse-event-reporting-program/reporting-serious-problems-fda):
  distinguishes voluntary and mandatory reporting contexts. This package stores
  a local route only; it does not determine reportability or submit a form.
- [AHRQ PSO Common Formats / Data](https://pso.ahrq.gov/common-formats):
  page reviewed **January 2026**, now headed Data with links to Common Formats
  and NPSD. Supports a locator for standardized reporting under authorized processes;
  using a template does not establish PSQIA privilege or confidentiality.

## Local tool contracts

- [Python JSON](https://docs.python.org/3/library/json.html): duplicate keys are
  accepted by default and parse limits require explicit handling. The helpers use
  `object_pairs_hook`, reject nonfinite constants, bound reads, and convert excessive
  nesting and integer conversion failures into minimized errors. Schema validation
  rejects unsupported value types; JSON decoding alone is not schema validation.
- [Python datetime](https://docs.python.org/3/library/datetime.html): `fromisoformat`
  accepts forms broader than this schema, including week dates and alternate separators.
  Helpers explicitly require extended calendar dates and timestamps before conversion.
  Date filters have the same full-date contract; scheduling keeps the supplied local date.
- [Python filesystem APIs](https://docs.python.org/3/library/os.html#os.link):
  `os.replace` can overwrite an existing destination. Publication now uses a completed
  private temporary file plus `os.link`, failing if a destination appears concurrently.
  Hard-link support is required; there is no clobbering fallback. This is per-file
  publication, not a package transaction, filesystem sandbox, Windows ACL guarantee,
  or protection against untrusted ancestor directories and mounts.

## Verification limits

No external scientific API endpoint, authentication, pagination, response schema, or
network client is owned by this skill. FDA/REMS/OCR links are human source locators,
not undocumented API contracts. Clinical content, licensure, authority, applicability,
signature authenticity, patient privacy, clinical safety, and legal requirements are
human determinations, even if every structural check passes. Synthetic tests exercise
local behavior only. See `security_validation.md` for historical and current checks.
