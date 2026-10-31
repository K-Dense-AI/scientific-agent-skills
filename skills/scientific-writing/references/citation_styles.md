# Citation Integrity and Reference Formatting

## Verification before style

Formatting cannot repair an unverified reference. For every cited source:

1. Open the source or authoritative bibliographic record.
2. Confirm the cited proposition at a precise locator.
3. Confirm authors or organization, title, publication state, venue, year, and version.
4. Copy identifiers exactly from the verified record.
5. Record corrections, retractions, expressions of concern, updates, and preprint status.
6. Assign an evidence ID and human verification record.

Do not cite a source that was not read for the proposition. Do not copy a DOI, PMID,
quotation, or reference from generated text, a search snippet, or another article
without verification. ICMJE assigns authors responsibility for reference accuracy and
rejects AI-generated material as a primary source [SW-S01].

## Quotations and paraphrases

- Verify every quotation character-for-character and record a stable locator.
- Preserve context, qualifications, and negation.
- Mark changes, omissions, or translations according to venue policy.
- Paraphrase from understanding, not by superficial word substitution.
- Obtain permissions where copyright or license terms require them.
- For personal communications or unpublished information, obtain required permission
  and follow current journal policy [SW-S01].

## Source choice

Prefer the original source for a reported method, dataset, result, policy, or guideline.
Use a review for synthesis when it actually supports the synthesized claim. Clearly
identify preprints and other non-peer-reviewed versions. Check that a later correction
or published version does not supersede the cited record.

Do not use citation counts, venue prestige, recency, or a target percentage of recent
references as a substitute for relevance and evidentiary fit.

## Identifiers

The local checker validates syntax and duplicates only. It does not resolve identifiers
and cannot establish that an identifier belongs to the recorded work.

Supported local checks include:

- DOI;
- PMID;
- PMCID;
- ISBN checksum;
- HTTP or HTTPS URL shape;
- duplicate normalized titles and identifiers.

After the local check, a human must compare each identifier with the opened source.

## NLM and journal styles

For biomedical references, use *Citing Medicine* and NLM's sample references for the
relevant source type [SW-S20, SW-S21]. These cover articles, books, datasets, software,
and online material. The current target journal's instructions override generic style
examples. JAMA currently advises against using AI/LLMs to generate or format
references; use a standard reference manager and manually verify its output for that
venue [SW-S25].

For APA, AMA, Chicago, IEEE, ACS, Vancouver-derived, or publisher-specific styles:

- use the current official manual or journal style;
- render from verified structured metadata;
- check author truncation, title case, journal abbreviation, version, date, locator,
  and identifier rules;
- inspect the rendered list manually after conversion.

Do not invent a complete-looking example reference. Templates should use explicit
fields or evidence IDs until verified metadata exists.

## Citation audit

Before submission:

- every factual or numeric claim maps to verified evidence IDs;
- each in-text citation maps to a source-manifest record;
- every reference-list entry is cited unless the venue explicitly permits a
  bibliography;
- citation ordering and repeated citation behavior match the target style;
- reused figures, tables, datasets, software, protocols, and standards are attributed;
- direct quotations have locators and permissions where needed;
- duplicate and malformed identifiers are resolved;
- no retracted or corrected status is concealed.

Run:

```bash
python3 scripts/audit_claims.py manuscript.md claims.csv source_manifest.json
python3 scripts/check_references.py source_manifest.json
```
