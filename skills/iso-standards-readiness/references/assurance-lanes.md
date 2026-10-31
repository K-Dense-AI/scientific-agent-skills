# Assurance Lanes: What Each One Actually Decides

Research basis: **2026-10-01**. Read this before preparing evidence for any standard in
this skill. Most substantive errors in readiness work are lane confusion, not missing
documents: an output that is correct for one lane is wrong, and sometimes a false claim,
in another.

Every lane below is decided by a different body, against a different basis, producing a
different artifact with a different scope. None of them is a substitute for another, and
this skill produces none of them.

## Six assurance lanes and the risk-evidence role

| Lane | Who decides | Basis | Artifact | Applies to |
| --- | --- | --- | --- | --- |
| Management-system certification | Certification body under ISO/IEC 17021-1 | Authorized standard + certification scheme | Certificate, scoped | ISO 13485 |
| Laboratory accreditation | Accreditation body under ISO/IEC 17011 | Authorized standard + scheme rules | Accreditation + scope schedule | ISO/IEC 17025, ISO 15189 |
| Regulator inspection | National regulator | That jurisdiction's law | Inspection outcome, enforcement | FDA QMSR, CLIA, national regimes |
| Mandatory certification/licensure | Government or its agent | Statute | Certificate/licence to operate | CLIA |
| Regulatory audit programme | Recognized Auditing Organization | Programme audit model | Audit report used by participating regulators | MDSAP |
| Conformity assessment | Notified body / manufacturer per route | Product regulation | Product certificate, declaration of conformity | EU MDR/IVDR |
| Risk evidence within a declared lane | Whoever runs the declared lane | The standard, as evidence | Supporting evidence; no assurance result from this skill | ISO 14971 |

## Certification and accreditation are not synonyms

This is the most frequent wording error in readiness documents.

- Organizations and management systems are **certified** by a certification body.
  ISO 13485 is a certification lane.
- Laboratories, inspection bodies, proficiency-testing providers, and reference-material
  producers are **accredited** by an accreditation body, for a defined technical scope.
  ISO/IEC 17025 and ISO 15189 are accreditation lanes.
- Accreditation bodies themselves are peer-evaluated through the international
  recognition arrangement; they are not certified.

"ISO 17025 certified" and "ISO 15189 certified" are category errors. So is treating an
accreditation schedule as if it covered the whole organization: an accreditation scope
is per location and per activity or examination, and work outside it must carry no
accreditation claim.

Since **2026-01-01**, Global Accreditation Cooperation Incorporated has replaced the
former ILAC and IAF and operates a single Multilateral Recognition Arrangement.
Certificates and accredited results issued under the former IAF MLA / ILAC MRA remain
recognized during the transition. Before reproducing any recognition claim, logo, or
document designation, verify the current wording — legacy phrasing may be transitional
rather than current.

## A certificate never displaces a regulator

Hold these apart in every output:

- **ISO 13485 certification does not exempt a manufacturer from FDA inspection, and
  FDA does not issue ISO 13485 certificates.** FDA assesses applicable FDA
  requirements; QMSR has been effective and enforced since 2026-02-02, and FDA uses
  Compliance Program 7382.850 rather than the retired QSIT.
- **ISO 15189 accreditation does not satisfy CLIA.** CLIA certification by CMS is
  required for applicable clinical testing, subject to the exceptions and exemptions
  in 42 CFR 493.3. Research-only testing without patient-specific clinical reporting
  is an explicit exception. The authorized owner must resolve applicability. Deemed
  status comes from an approved CLIA program, not ISO 15189 by itself.
- **An MDSAP audit is not generic ISO certification, and an FDA inspection does not
  follow the MDSAP audit plan.**
- **Accreditation or certification alone is not notified-body designation.** Verify a
  notified body's current legislation, task, and designation-code scope in NANDO.
- **EU conformity assessment covers product, technical documentation, post-market,
  vigilance, and economic-operator requirements** well beyond generic
  management-system documentation.

## What a scope statement limits

Whatever the lane, the artifact is bounded. Record the boundaries explicitly, because a
claim that quietly exceeds them is the failure mode:

- named legal organization and the specific sites or locations;
- activities, and for laboratories the specific methods, measurands, or examinations
  with ranges and uncertainty basis;
- the product or technical areas covered;
- the standard edition and any amendment basis, and the scheme applied;
- validity dates and current status, including suspension or withdrawal; and
- the issuing body and its own accreditation or designation status.

## Product- and jurisdiction-specific controls sit outside all of this

Classification, intended purpose and claims, software and cybersecurity, clinical or
performance evidence, biocompatibility, electrical safety, sterilization, UDI,
registration, personnel qualification, reporting, and payer conditions each require
separate authorized analysis. A management-system or laboratory-competence readiness
output says nothing about any of them.

## Lane declaration is a required input, not an inference

Before evidence work starts, name the lane or lanes in the intake, with an owner for
each applicability decision. The bundled checks record what humans declared; they never
infer a lane from a document set. Where a lane is undetermined, the intake check raises
`HUMAN_DECISION_REQUIRED` as a blocker — leave it as a blocker.

Manifest `audit_context.purpose` accepts one declared purpose per manifest:
`internal-audit`, `iso-certification-readiness`,
`accreditation-assessment-readiness`, `fda-inspection-readiness`,
`national-regulatory-inspection-readiness`, `mdsap-audit-readiness`, or
`eu-conformity-assessment-readiness`. Preparing for two lanes means two manifests with
two scopes and two sets of limitations, not one manifest with a blended purpose.

## Titling rule

Never title an output "certificate," "accreditation," "compliance report," "audit
pass," "deemed status," or "ready for inspection." Use **Draft evidence review for
authorized human assessment**, and state which lane the evidence was prepared for.

## Sources

- `references/source-ledger.md` — dated official sources for every claim above
- [GLOBAC launch](https://iaf.nu/en/news/global-accreditation-cooperation-incorporated-launch-unifies-international-accreditation-organisations-and-strengthens-worldwide-trust/)
- [Specifying use of GLOBAC accreditation](https://ilac.org/latest_ilac_news/iaf-and-ilac-release-information-on-specifying-use-of-globac-accreditation/)
- [FDA QMSR](https://www.fda.gov/medical-devices/postmarket-requirements-devices/quality-management-system-regulation-qmsr)
- [CMS CLIA](https://www.cms.gov/medicare/quality/clinical-laboratory-improvement-amendments)
- [MDSAP Audit Approach](https://www.mdsap.global/documents/library/audit-approach)
- [NANDO](https://webgate.ec.europa.eu/single-market-compliance-space/notified-bodies)
