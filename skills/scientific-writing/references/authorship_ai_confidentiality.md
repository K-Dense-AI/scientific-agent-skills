# Authorship, CRediT, AI, and Confidentiality

## Human authorship and accountability

Use the current target-journal authorship policy. For biomedical work, ICMJE's four
criteria require substantial contribution, drafting or critical revision, final
approval, and accountability for all aspects of the work [SW-S01].

AI systems and other nonhuman tools are not authors. They cannot approve the work,
accept accountability, disclose conflicts, or manage copyright and license agreements
[SW-S01, SW-S03].

Do not:

- add or remove an author without all required human approvals;
- infer contributions from author order, affiliations, or email;
- generate an author-contribution statement from incomplete records;
- use CRediT roles as a substitute for the venue's authorship criteria.

## CRediT

CRediT is the ANSI/NISO Z39.104-2022 taxonomy of 14 contributor roles. The standard
explicitly describes contributions and does not define authorship [SW-S19].

Record only roles confirmed by the contributor and accountable author team:

- Conceptualization
- Data curation
- Formal analysis
- Funding acquisition
- Investigation
- Methodology
- Project administration
- Resources
- Software
- Supervision
- Validation
- Visualization
- Writing – original draft
- Writing – review & editing

One person may have multiple roles; a project need not use every role. Non-author
contributors may also receive appropriate credit and acknowledgment subject to consent
and journal policy.

## AI-use disclosure

The January 2026 ICMJE Recommendations call for disclosure of the AI tool and purpose
in the cover letter and appropriate manuscript section. Writing assistance belongs
in acknowledgments; use for data collection, analysis, or figure generation belongs
in Methods as applicable
[SW-S01, SW-S02]. COPE's formal position likewise requires disclosure and keeps full
responsibility with human authors [SW-S03].

Journal and publisher rules differ and evolve. Check them at the time of use and again
before submission. Record:

- tool, provider, and version or access date;
- purpose and affected stage;
- whether output entered text, code, analysis, tables, or figures;
- human verification performed;
- disclosure locations required by the venue;
- what material, if any, was sent outside the approved environment;
- authorization and policy review for any restricted transfer.

Do not fabricate an AI-use statement or claim that no AI was used. Obtain confirmation
from the human authors.

## Confidentiality boundary

Do not send any of the following to an external service without explicit authorization
and a documented policy review:

- unpublished manuscripts or drafts;
- peer-review or editorial material;
- sensitive or restricted data;
- protected health information or other personal data;
- proprietary or contract-restricted content;
- source documents, including full articles, reports, protocols, and datasets.

Authorization must come from a person or body empowered to grant it and must be
consistent with journal policy, consent, ethics approval, contracts, law, institutional
policy, and data-use terms. Removing obvious names does not by itself make content safe.

When authorization is absent or unclear, keep processing local and use only minimal
metadata. This skill's bundled tools make no network calls and do not read environment
variables or `.env` files.

ICMJE treats submitted manuscripts as privileged communications and warns editors and
reviewers not to upload them to AI systems where confidentiality cannot be assured
without author permission [SW-S01]. JAMA provides a journal-policy example with the same
confidentiality concern [SW-S24].

## COPE status as of the research date

COPE's 2017 Core Practices were retired in 2024. The Code of Conduct for COPE
Members was published on 21 July 2026, with 12 months from first publication for
implementation. It sits alongside the 2026 Core Principles [SW-S04, SW-S05]. Use
current topic-specific guidance; distinguish formal positions from discussion
documents, webinars, comments, and case advice.

## Validation

Populate `authorship.json`, then run:

```bash
python3 scripts/validate_authorship.py authorship.json
```

The validator checks human authorship gates, exact CRediT role names, guarantors, final
approval, declaration-hash syntax, AI disclosure, and restricted external-transfer
gates. It does not compare declaration hashes against manuscript statements.
These are ICMJE-style local gates, not a universal authorship standard. For example,
Nature Portfolio uses a different contribution criterion [SW-S23]. The guarantor
record is a local accountability convention, not a claim that all journals require
one. Do not falsely attest to a gate to pass the tool; document the actual venue
criteria and any local-validator limitation. The tool cannot adjudicate contribution
disputes or determine who deserves authorship.
