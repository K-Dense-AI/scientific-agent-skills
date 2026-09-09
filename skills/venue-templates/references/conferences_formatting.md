# Conference Formatting Requirements

Current-year conference rules change independently by track. Use this guide to find the authoritative source and to understand the scope of the rule; do not carry a page limit or style file into another year.

**Reviewed:** 2026-07-20

## How to Use This Guide

For every submission, record:

1. conference year and track;
2. initial, rebuttal, or camera-ready stage;
3. official author-instruction URL and date checked;
4. page-limit scope, including references and appendices;
5. anonymity and external-link policy; and
6. exact official template package.

Official instructions and files override every summary below.

## Verified 2026 ML and Vision Snapshots

### NeurIPS 2026 — Main Track

**Official sources**

- Call for Papers: https://neurips.cc/Conferences/2026/CallForPapers
- Main Track Handbook: https://neurips.cc/Conferences/2026/MainTrackHandbook
- Official formatting package: linked from the Call for Papers

**Initial submission**

- Up to **9 content pages**, including figures.
- Additional pages containing acknowledgments, references, the required paper checklist, and optional technical appendices do not count as content pages.
- Omit both the `final` and `preprint` style options; the official style then anonymizes the submission and adds line numbers.
- Do not include acknowledgments in the anonymized submission.
- The **NeurIPS Paper Checklist is required**; omitting it can cause desk rejection.
- Technical appendices may be included after the references. Reviewers are not required to rely on them.

**Template rule**

Use the exact NeurIPS 2026 package. The bundled `assets/journals/neurips_article.tex` is only a wrapper and requires the official `neurips_2026.sty` and checklist files.

### ICML 2026 — Main Track

**Official sources**

- Author Instructions: https://icml.cc/Conferences/2026/AuthorInstructions
- Call for Papers: https://icml.cc/Conferences/2026/CallForPapers
- Official style package: https://media.icml.cc/Conferences/ICML2026/Styles/icml2026.zip

**Initial submission**

- Main body: up to **8 pages**.
- References and appendices may use additional pages and remain in the same PDF.
- Submissions must use LaTeX, be anonymized, and follow the official style.
- The camera-ready version permits one extra main-body page.
- Material essential to evaluation belongs in the main body; reviewers may decline to read appendices or separate supplements.

### ICLR 2026

**Official source**

- Author Guide: https://iclr.cc/Conferences/2026/AuthorGuide

**Initial submission**

- Main text: up to **9 pages**.
- References do not count toward the limit.
- Appendices may use additional pages, but reviewers are not required to read them.
- Submissions are double blind; identifying information in the paper or supplement can cause desk rejection.
- Use the `iclr2026` package linked by the Author Guide.

**Later stages**

- The discussion/rebuttal and camera-ready limit increases to **10 main-text pages**.
- Do not apply that later-stage allowance to the initial submission.

### CVPR 2026

**Official source**

- Author Guidelines: https://cvpr.thecvf.com/Conferences/2026/AuthorGuidelines

**Initial submission**

- Main paper: up to **8 pages**, including figures and tables.
- Additional pages may contain cited references only.
- Use the official CVPR 2026 author kit linked by the Author Guidelines.
- Papers must be anonymized. Identifying acknowledgments, grant IDs, videos, attached papers, or external links can violate anonymity.
- External links that expand submitted content or bypass length restrictions are prohibited.

**Rebuttal**

- The rebuttal is a one-page PDF using the rebuttal template from the author kit.
- It must remain anonymous and may not add external material.

## Other Conference Families

The following links are discovery starting points, not cached requirements.

| Venue/family | Official starting point | Template rule |
|---|---|---|
| AAAI | https://aaai.org/conference/aaai/ | Use the target year's author kit |
| IJCAI | https://www.ijcai.org/ | Use the target year's call and style |
| ACL / ARR | https://aclrollingreview.org/ | Check ARR submission requirements and the committing venue |
| EMNLP | https://www.emnlp.org/ | Check the current call and ACL style package |
| ACM CHI | https://chi.acm.org/ | Check the current papers track and ACM workflow |
| ACM SIGKDD | https://kdd.org/ | Check the exact track; limits differ |
| ACM SIGIR | https://sigir.org/ | Check the target year's call |
| USENIX Security | https://www.usenix.org/conference/usenixsecurity26 | Check the current submission cycle and artifact rules |
| ISMB | https://www.iscb.org/ismb2026 | Check the proceedings track and journal instructions |
| RECOMB | https://www.recomb.org/ | Check the target year's Springer/author kit |
| PSB | https://psb.stanford.edu/ | Check the current author instructions |
| IEEE conferences | https://conferences.ieeeauthorcenter.ieee.org/ | Use the conference-selected IEEE template |
| ICRA | https://www.ieee-ras.org/conferences-workshops/fully-sponsored/icra | Check the current author kit and page charges |

Do not assume that last year's page limit, review model, supplement policy, or class options survived unchanged.

## Official Template Workflow

1. Download the package from the conference's official author page.
2. Keep all `.sty`, `.cls`, bibliography, and checklist files together.
3. Compile the sample before editing.
4. Copy the sample and replace content without changing layout commands.
5. Preserve submission mode for review; enable camera-ready options only after acceptance.
6. Re-download the package if the organizers announce a revision.

Avoid unofficial mirrors when an official package exists. Do not rename an old style file to a new year.

## Blind-Review Checklist

Check the manuscript, supplement, source archive, PDF metadata, figures, and linked resources.

- Remove names, affiliations, emails, acknowledgments, grant numbers, and institution-identifying text when required.
- Follow the venue's self-citation policy; do not automatically replace every self-citation with “Anonymous.”
- Remove identifying paths, usernames, comments, Git metadata, document properties, and image metadata.
- Use only external links permitted by the current policy.
- Ensure code and data packages are anonymized if submitted for review.
- Do not disclose the submission's venue status where the conference prohibits it.

## Page-Limit Interpretation

“Eight pages” is incomplete without scope. Record whether the limit applies to:

- main text only;
- figures and tables;
- acknowledgments;
- references;
- appendices;
- checklists or impact statements; and
- the combined PDF or a separate supplement.

When using `scripts/validate_format.py`, supply `--content-pages` after manually counting according to this scope. Total PDF pages alone cannot establish compliance.

## Supplementary Material

- Put claims essential to acceptance in the main paper.
- Treat appendices as optional reading unless the current instructions say otherwise.
- Apply the same anonymity rules to supplements.
- Check file count, type, and size limits.
- Do not use links or supplements to evade the main-paper limit.
- Confirm whether code/data uploads share the paper deadline.

## Camera-Ready Preparation

After acceptance:

1. switch to the official final/camera-ready mode;
2. add authors and permitted acknowledgments;
3. apply the camera-ready page allowance, if any;
4. complete rights, licensing, accessibility, and metadata forms;
5. include only accepted and permitted supplementary material; and
6. inspect the publisher or proceedings proof.

Submission and camera-ready rules are different contracts. Re-verify both.
