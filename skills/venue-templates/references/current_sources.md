# Source and execution ledger

Reviewed **2026-10-01**. These are dated snapshots, not a promise that the next
submission cycle has identical rules. This skill has no remote API client:
its Python helpers only read local templates/PDFs and invoke Poppler. Publisher
and conference links are human-facing documentation or template downloads, not
submission endpoints.

## Journal sources

| Primary source | Verified scope and correction |
|---|---|
| [Nature initial submissions](https://www.nature.com/nature/for-authors/initial-submission), [formatting guide](https://www.nature.com/nature/for-authors/formatting-guide) | Format-flexible initial review within reason; referenced Article summary ideally at most 200 words; Methods in the main file after legends; separate funding statement. Published print lengths are not one universal submission cap. |
| [PLOS ONE submission guidelines](https://journals.plos.org/plosone/s/submission-guidelines), [LaTeX instructions](https://journals.plos.org/plosone/s/latex) | Abstract at most 300 words, no citations; double-spaced single-column manuscript with continuous line/page numbering. The official package controls actual LaTeX submission. |
| [Cell revision instructions](https://www.cell.com/cell/information-for-authors/revise-manuscript), [final instructions](https://www.cell.com/cell/information-for-authors/final-submission), [linked final-file checklist](https://www.cell.com/pb-assets/journals/EM/MasterFFCs/CELLFFC-1790092533770.pdf) | Summary at most 150 words; up to four Highlights of at most 85 characters each; eTOC/In Brief at most 50 words, two sentences, third person. References use numbered superscripts. Resource Availability, STAR Methods, and the Key Resources Table have distinct roles. Final graphical abstract: 1200 × 1200 pixels at 300 dpi, TIFF/PDF/JPG. These are Cell rules, not all Cell Press journals. |
| [STAR Methods resources](https://star-methods.com/) | Current author tool and resources for the Key Resources Table; no automated submission integration tested. |
| [Elsevier LaTeX instructions](https://www.elsevier.com/researcher/author/policies-and-guidelines/latex-instructions), [CTAN elsarticle](https://ctan.org/pkg/elsarticle) | Official elsarticle 3.5 (2026-01-09). All three bundled `.tex` samples and three `.bst` files match this release; LPPL notices retained. Editorial Manager source files need a single folder level. Journal instructions select class and citation mode. |
| [JAMA author instructions](https://jamanetwork.com/journals/jama/pages/instructions-for-authors) | Original-data abstract maximum 350 words, prescribed headings; article-type rules differ. AI drafting restrictions for Opinion, Letters, and Online Comments and the advice against AI-generated/formatted references are venue-specific. |
| [The BMJ article types](https://www.bmj.com/about-bmj/resources-authors/article-types) | No fixed research main-text word cap; abstract normally 250–300 words, up to 400 for CONSORT/PRISMA reporting. |
| [The Lancet author hub](https://www.thelancet.com/lancet/information-for-authors), [August 2026 instructions](https://www.thelancet.com/pb-assets/Lancet/authors/tl-info-for-authors-1787150940677.pdf) | Original research has a five-paragraph summary of at most 300 words and a Research in Context panel; apply the exact article category rather than publisher-wide limits. |

Discovery hubs were reviewed for their role, not treated as uniform formatting
rules: [IEEE templates](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/authoring-tools-and-templates/tools-for-ieee-authors/ieee-article-templates/),
[BMC](https://link.springer.com/brands/bmc/why-publish-with-bmc),
[Frontiers](https://www.frontiersin.org/guidelines/author-guidelines),
[PNAS](https://www.pnas.org/author-center), and [APS](https://journals.aps.org/authors).

## Conference sources

| Primary source | Verified scope |
|---|---|
| [NeurIPS 2026 CFP](https://neurips.cc/Conferences/2026/CallForPapers), [Main Track Handbook](https://neurips.cc/Conferences/2026/MainTrackHandbook) | Initial main content 9 pages, camera-ready 10; references, technical appendices, and checklist excluded. Review omits acknowledgments. The official author ZIP provides `neurips_2026.sty` and `checklist.tex`; default submission mode is anonymous. No universal separately titled Broader Impacts section. |
| [ICML 2026 author instructions](https://icml.cc/Conferences/2026/AuthorInstructions), [CFP](https://icml.cc/Conferences/2026/CallForPapers) | Initial 8 pages, final 9; references/appendices additional in the same PDF. Anonymous code branch freezes at deadline. No revised manuscript during author feedback. |
| [ICLR 2026 author guide](https://iclr.cc/Conferences/2026/AuthorGuide) | Initial 9 pages, discussion/camera-ready 10; references/appendices excluded. This is a 2026 snapshot, not a verified 2027 rule. |
| [CVPR 2026 author guidelines](https://cvpr.thecvf.com/Conferences/2026/AuthorGuidelines) | Initial 8 pages plus cited references; anonymous one-page rebuttal, no external links, new contributions/unrequested experimental results discouraged. |
| [ARR current CFP](https://aclrollingreview.org/cfp) | 8/4-page long/short content; required Limitations after the conclusion and outside that count. Reviews are not public simply because ARR uses OpenReview. Check current October 2026 service/capacity policy. |
| [CHI 2026 papers](https://chi2026.acm.org/authors/papers/), [publication formats](https://chi2026.acm.org/chi-publication-formats/), [review process](https://chi2026.acm.org/papers-review-process/) | Single-column anonymous `acmart` manuscript for review; current TAPS production. Do not use the old `sigchi` option. |
| [KDD 2026 research CFP](https://kdd2026.kdd.org/research-track-call-for-papers/) | Research track uses `sigconf,anonymous,review`; other tracks have their own instructions. Theory need not claim empirical state of the art. |

Other families remain discovery links with no cached limits. The broken USENIX
and ISMB generic URLs were replaced with [USENIX conferences](https://www.usenix.org/conferences/security)
and [ISMB series](https://www.iscb.org/conferences-events/about-ismb); EMNLP resolves
through [SIGDAT](https://sigdat.org/). AAAI, IJCAI, KDD, SIGIR, RECOMB, PSB, and IEEE
conference/ICRA hubs were checked; select the actual year's call before drafting.

## Grants and reporting

- [NSF PAPPG](https://www.nsf.gov/policies/pappg) and [Chapter II](https://www.nsf.gov/policies/pappg/24-1/ch-2-proposal-preparation): 24-1 remains the effective base, with [26-200](https://www.nsf.gov/policies/document/pappg24-1-supplement-1) and [26-202](https://www.nsf.gov/policies/document/pappg24-1-supplement-2). The Research.gov DMSP tool supersedes the old two-page PDF process from 2026-04-27. Common-form/SciENcv workflows replace obsolete biosketch layouts. Prior-support publication lists are not capped at five publications.
- NIH [page limits](https://grants.nih.gov/grants-process/write-application/how-to-apply-application-guide/page-limits) and [attachment formatting](https://grants.nih.gov/grants-process/write-application/how-to-apply-application-guide/format-attachments): generally one-page Aims, R01 Strategy 12 pages, R21 Strategy 6; body text at least 11 points, margins at least half an inch, density limits apply. Actual PDF and NOFO remain controlling.
- NIH [Common Form](https://www.grants.nih.gov/grants-process/write-application/forms-directory/biographical-sketch-common-form) and [26-079](https://grants.nih.gov/grants/guide/notice-files/NOT-OD-26-079.html): implementation for 2026-01-25 due dates, system enforcement from 2026-05-08, research-security-training certification for 2026-05-25 due dates. These are separate dates.
- [DOE Office of Science guidance](https://science.osti.gov/grants/Policy-and-Guidance) and [DARPA Heilmeier questions](https://www.darpa.mil/about/heilmeier-catechism) are starting points; the active office-specific call determines submission system and limits.
- [CONSORT/SPIRIT](https://www.consort-spirit.org/): current core guidelines are 2025, not CONSORT 2010/SPIRIT 2013. [STROBE](https://www.strobe-statement.org/), [PRISMA](https://www.prisma-statement.org/), and [STARD](https://www.equator-network.org/reporting-guidelines/stard/) require design-appropriate checklists/extensions, not a universal medical-paper structure.

## Tool and template execution

The maintained helpers require only Python's standard library. Poppler's
`pdffonts` table includes **all** font rows and an `emb` flag; a listed name alone
is not proof of embedding. Local `pdfinfo`/`pdffonts` execution checked both
embedded-font PDFs and an intentionally nonembedded Helvetica fixture.
The inspector still cannot certify point sizes, margins, reading order,
anonymity, or the manually supplied content-page boundary.

Native pdfLaTeX (TeX Live 2025), with shell escape disabled, compiled all nine
bundled `.tex` files. The NeurIPS wrapper used the actual 2026 author kit and a
synthetic bibliography fixture; it is not a paper ready to submit. Elsevier used
the current 3.5 class generated from upstream source. BibTeX separately exercised
all three bundled styles. Plain `elsarticle-num` does not supply author names
for `\citet`; the numeric-with-names and author-year styles do.

The Elsevier samples are unmodified upstream copies and repeat `fig1` on a table
and figure, producing a duplicate-label warning. Assign unique labels in the
working manuscript. Their empty graphical-abstract/highlight placeholders are
also examples, not completed content. Nonfatal epstopdf shell-escape warnings
are expected with no external conversion enabled; PLOS's microtype/footnote
patch warning and tikzposter's nullfont diagnostic were recorded during review.

[beamerposter](https://ctan.org/pkg/beamerposter),
[tikzposter](https://ctan.org/pkg/tikzposter), and
[qrcode](https://ctan.org/pkg/qrcode) package documentation informed the poster
workflow. The beamerposter/tikzposter preambles and local QR generation compiled. A separate baposter preamble compatibility check also compiled using a cached archival v2.0 class dated 2011-11-26 from the [mloesch mirror](https://github.com/mloesch/baposter/tree/eabd151901a0f005faf0ff06e1f3ab88773a287f); this is not evidence of a current maintained upstream release.
The NIH Aims placeholder is one page; the poster is one A0 portrait page with a
visible title. Actual authored content must be recompiled and visually checked.
Poster layout/type-size advice is heuristic. [WCAG contrast guidance](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
is a web accessibility criterion, not certification that a printed poster or PDF
is accessible. Color simulations and asset-library links are optional author
resources, not tested integrations or permission to redistribute their artwork.

## Verification boundaries

- Fresh [Science instructions](https://www.science.org/content/page/instructions-authors) could not be retrieved. [NEJM](https://www.nejm.org/author-center/new-manuscripts) and [Annals](https://www.acpjournals.org/journal/aim/authors) returned navigation without complete article-type instructions. Unverified fixed numerical limits were removed; retrieve current full instructions before submitting.
- The generic ACM/CHI hubs blocked automated access; official CHI and KDD 2026 instructions supplied the current `acmart` workflow evidence.
- `baposter.cls` is absent from the installed TeX distribution and its current package page could not be retrieved. The short preamble has only the archival compatibility check described above; no baposter class/template is bundled.
- Browser-based design services, submission portals, authenticated SciENcv/Research.gov workflows, print-shop output, and real submission acceptance were not exercised. Source verification and local compilation are different evidence.
- All prose examples contain placeholders. They neither report executed experiments nor establish scientific validity, journal fit, or acceptance.
