# Compendial, CLSI, and ISO Sources (No Standard Text)

Research basis: **2026-09-30**. This reference identifies documents, their scope, and where to obtain
them. **It does not reproduce their requirements, thresholds, or study designs**, because they are
copyrighted and paywalled.

## Copyright boundary

USP–NF general chapters, CLSI documents, and ISO/IEC standards are copyrighted works sold by their
publishers. Do not ask an agent to retrieve, transcribe, summarise clause-by-clause, reconstruct, or
store their text. Vendor application notes and training decks that quote them are equally
constrained, and a paraphrase that carries the same numbers is still a reproduction of the
substantive content.

The practical consequence: **when a numeric criterion or a study design lives in one of these
documents, read it from the authorised copy.** An agent asked for "the USP <621> tailing factor
limit" or "the CLSI EP15 number of days" will produce a plausible number. Plausible is not the same
as correct, and the difference is discovered at audit.

Record publisher, title, designation, edition, amendments, authorised location, access date, and
review date in the laboratory's controlled source register.

## USP–NF general chapters

| Chapter | Title | Scope |
| --- | --- | --- |
| `<1220>` | Analytical Procedure Life Cycle | Three-stage lifecycle: procedure design (Stage 1), performance qualification (Stage 2), ongoing performance verification (Stage 3), organised around an analytical target profile. Official 1 May 2022, confirmed by the USP Council of Experts report. Integrates the concepts previously spread across `<1224>`, `<1225>`, and `<1226>`. |
| `<1225>` | Validation of Compendial Procedures | Compendial validation. The linked 2025 preview is a **proposal** extending and aligning the chapter with Q2(R2); confirm the effective controlled text before relying on proposed Stage 2 changes. |
| `<1226>` | Verification of Compendial Procedures | Assessment of selected performance characteristics showing a compendial procedure works under actual conditions of use. **Verification is not revalidation** and does not repeat the full validation. |
| `<1224>` | Transfer of Analytical Procedures | Transfer between laboratories. |
| `<1010>` | Analytical Data — Interpretation and Treatment | Statistical treatment of analytical data. |
| `<621>` | Chromatography | System suitability and chromatographic operating parameters, including the extent to which a compendial procedure may be adjusted without triggering revalidation. |
| `<711>` / `<1092>` | Dissolution / The Dissolution Procedure | Dissolution testing and development/validation of the procedure. |

Obtain from the USP–NF (<https://www.uspnf.com/>). Regional pharmacopoeias — Ph. Eur., JP, ChP —
carry their own general chapters; check which pharmacopoeia the specification cites, because
adjustment allowances and system suitability requirements differ between them.

**The `<1226>` decision.** Verification applies when using a compendial procedure as written and
within its scope. Two situations push you back to `<1225>` validation: using the procedure outside
its stated scope (a different matrix, a different dosage form, a concentration range it does not
cover), or modifying it beyond the adjustments the relevant chapter permits. Getting this wrong in
either direction is expensive — unnecessary full validation, or an unsupported claim of verification.

## CLSI EP series

Publisher catalogue metadata checked **2026-09-30**; full standards were not accessed.
These edition numbers identify the reviewed baseline, not a guarantee of the next revision.

| Designation | Subject | Publisher edition baseline |
| --- | --- | --- |
| [EP05](https://clsi.org/shop/standards/ep05-plus/) | Precision establishment | **4th edition**, 11 Dec 2025; Plus includes a Quick Guide |
| [EP06](https://clsi.org/shop/standards/ep06/) | Linearity | 2nd edition, 24 Nov 2020; publisher also lists separate establishment/implementation guides |
| [EP07](https://clsi.org/shop/standards/ep07-plus/) | Interference | 3rd edition, 30 Apr 2018; Plus guide published 17 Mar 2026 is not a new edition |
| [EP09](https://clsi.org/shop/standards/ep09/) | Patient-sample comparison and bias | 3rd edition, corrected 20 Jun 2018 |
| [EP15](https://clsi.org/shop/standards/ep15/) | User precision verification and bias estimation | 3rd edition, 11 Sep 2014 |
| [EP17](https://clsi.org/shop/standards/ep17/) | Detection capability | 2nd edition |
| [EP25](https://clsi.org/shop/standards/ep25/) | Stability of in vitro medical laboratory test reagents | 2nd edition |
| [EP28](https://clsi.org/shop/standards/ep28/) | Reference intervals | 3rd edition; EP28IG companion listed |

The [May 2026 publisher update](https://clsi.org/resources/insights-blog/purpose-driven-content-for-ep-documents-a-strategic-update/)
describes modular EP documents and a revision in progress for EP09. A development announcement or
companion guide is not proof that a new technical edition superseded the listed standard.

**Vocabulary.** CLSI distinguishes *limit of blank*, *limit of detection*, and *limit of quantitation*
as three separate quantities with separate protocols. This is not the same taxonomy as ICH Q2(R2)'s
detection limit and quantitation limit, and the two should not be translated into each other
casually — the underlying definitions and the experiments differ.

**Verification versus establishment.** For an unmodified FDA-cleared or approved nonwaived test under CLIA, a
laboratory *verifies* the manufacturer's performance claims — a bounded study. For a
laboratory-developed test, or an assay used off-label, the laboratory *establishes* performance,
which is a much larger exercise. Under CLIA the distinction has direct regulatory consequences and
also depends on test complexity. CE marking alone does not establish this US distinction; apply
the governing regional requirements. See the [CMS CLIA regulation entrypoint](https://www.cms.gov/medicare/health-safety-standards/clinical-laboratory-improvement-amendments-clia/clia-regulations-compliance).

## ISO standards

| Standard | Relevance |
| --- | --- |
| ISO/IEC 17025:2017 (edition 3; ISO catalogue status: confirmed) | Clause 7.2 selection, verification and validation of methods; clause 7.6 measurement uncertainty. Validation "to the extent necessary" for the intended application — no universal fixed checklist or numeric acceptance limits. |
| ISO 15189 | Medical laboratories: quality and competence. The clinical-laboratory counterpart to 17025. |
| ISO 21748 / ISO 5725 series | Using repeatability, reproducibility and trueness estimates in measurement uncertainty; accuracy of measurement methods. |

Obtain from ISO (<https://www.iso.org/>) or a national member body. A laboratory is **accredited** to
ISO/IEC 17025 by an accreditation body — it is not "17025 certified", and writing "certified" is a
substantive error assessors notice.

For accreditation readiness, the quality manual, and the surrounding management system, use this
repository's `iso-standards-readiness` skill. This skill stays at the level of the individual
procedure.

## Environmental, food, and forensic method systems

Where a prescribed method system governs — a published EPA method, an AOAC Official Method, a
standard method for water or food analysis — the validation and quality-control requirements are
written into the method or the programme, and they take precedence. Do not substitute a
pharmaceutical framework. Common differences: matrix spike and duplicate requirements per batch,
prescribed calibration-verification frequencies, method detection limit procedures that differ from
both ICH and CLSI, and mandatory participation in proficiency testing schemes.
