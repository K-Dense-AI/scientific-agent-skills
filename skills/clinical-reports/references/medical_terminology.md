# Versioned Terminology and Schema Checks

Terminology selection and coding are clinical/regulatory tasks. The local checker validates manifest shape and code syntax; it does not confirm that a code exists, is current, matches a display, or is clinically appropriate.

## Required manifest fields

For every coded item record:

- `system`: controlled system name;
- `system_uri`: canonical identifier supplied by the implementing organization;
- `code`;
- `display`;
- `version`;
- `language`;
- `source_fact_id`;
- `coding_status`: `verified_by_qualified_reviewer` or `unverified`;
- `verified_by_role` and `verified_at` when verified.

Do not infer a code from narrative text.

## MedDRA

- ICH developed MedDRA for regulatory information about human medical products.
- The current released English guide is MedDRA 29.1, September 2026; a release date is not a universal study or regulatory implementation date.
- MedDRA uses a multiaxial hierarchy and version-specific currency/relationships.
- State exact version and language.
- Use the study/sponsor-authorized version, official licensed files, and current Points to Consider.
- Do not assume the newest release is the required release.

The aggregate adverse-event formatter accepts SOC and PT labels as supplied and does not validate hierarchy, codes, or coding quality.

## LOINC

LOINC identifies health observations, measurements, and documents. LOINC 2.83 was released 19 August 2026 and is the current release at this review. Planned monthly releases are a future cadence change; verify actual release files before selecting a version.

- A valid-looking `number-checkdigit` string is only syntactic evidence.
- The method, property, timing, system/specimen, scale, and version can affect meaning.
- Verify against the official release or authorized terminology service.
- Review the LOINC license and third-party content terms.

## SNOMED CT

SNOMED CT concept identifiers are not clinically validated by their numeric shape.

- Use the applicable international edition, national extension, and effective date.
- Verify concept activity, module, description, and reference-set membership.
- Comply with SNOMED International and national licensing/distribution requirements.
- Do not embed or redistribute licensed terminology content through these assets.

## ICD-10-CM

ICD-10-CM changes by fiscal-year release and may require encounter, laterality, or placeholder characters.

- Record the exact release, applicable jurisdiction, and service-date range. CDC lists FY27 files for services from 1 October 2026; on this review date (30 September 2026), the FY26 April update still applies to services in its stated date window. File availability does not make a future effective version applicable early.
- Verify with official CDC/CMS files and coding guidance.
- A regex match cannot establish billability, specificity, sequencing, or clinical correctness.
- This skill does not support billing or reimbursement decisions.

## UCUM and units

Record the original unit exactly and, when an organization uses UCUM, record the verified UCUM expression separately. Do not automatically convert units in a report draft.

Any conversion must have:

- an authorized rule and version;
- original value/unit;
- converted value/unit;
- precision/rounding rule;
- source-fact and reviewer traceability.

The consistency checker flags missing or inconsistent unit labels but performs no clinical conversion. The terminology checker uses a restricted character screen for UCUM, not the complete UCUM grammar or semantic parser. Do not change a verified expression merely to satisfy that screen; record the limitation for qualified review.

## Optional local dictionary

`terminology_validator.py --dictionary <file.json>` can compare code/display/version tuples with a caller-supplied local dictionary. The dictionary must be an authorized bounded JSON file.

A match means only “matched this supplied dictionary.” It does not prove:

- the dictionary is official, complete, current, or licensed for the use;
- the chosen code is appropriate;
- the clinical statement is true;
- the report is compliant or ready for release.

Without a dictionary, the strongest result is `SCHEMA_VALID_SYNTAX_ONLY_REVIEW_REQUIRED`.
