# Journal Formatting Requirements

Journal requirements vary by journal, article type, and submission stage. Publisher-wide conventions are useful for discovery but do not replace the target journal's current Guide for Authors.

**Reviewed:** 2026-10-01

## Verification Workflow

Before formatting:

1. identify the exact journal and article type;
2. open the journal's official author instructions;
3. determine whether the initial submission is format-flexible;
4. distinguish initial-submission rules from revised/final-production rules;
5. record length, abstract, display-item, data/code, reporting, and disclosure requirements; and
6. use the official template only when the journal requires or recommends it.

Do not apply rules from a flagship journal to every journal in the same publisher family.

## Nature Portfolio

### Nature

**Official resources**

- Author hub: https://www.nature.com/nature/for-authors
- Initial submission: https://www.nature.com/nature/for-authors/initial-submission
- Formatting guide: https://www.nature.com/nature/for-authors/formatting-guide

Nature states that initial submissions are flexible in format within reason. Authors are encouraged to combine text and figures in one Word file or PDF for review. The formatting guide describes article formats and typical final print lengths; these are not a generic “five-page submission limit.”

For Articles, the formatting guide describes:

- a fully referenced summary paragraph, ideally no more than 200 words;
- typical final print lengths that differ for physical-science and biological/clinical/social-science papers; and
- detailed figure, reference, methods, and reporting requirements.

Use `assets/journals/nature_article.tex` only as a writing scaffold. It is not an official Nature class or a guarantee of compliance.

### Other Nature Portfolio journals

Open the exact journal's **Submission Guidelines**. Some Nature Portfolio journals explicitly accept PDF, Word, or compiled TeX/LaTeX for a format-flexible initial submission, while others provide journal-specific structure and final-format instructions.

Do not assume that Nature, Nature Communications, Scientific Reports, and subject journals share one word limit or template.

## Science Family

**Official starting point**

- Science author instructions: https://www.science.org/content/page/instructions-authors

Resolve the exact journal and contribution type before applying length, abstract, reference, or supplementary-material rules. Fresh Science author-page retrieval was blocked in this audit; this skill therefore does not assert a current Science word or reference limit. Science, Science Advances, and specialist journals have different workflows.

No Science template is bundled in this skill. Use the official instructions and files provided by the target journal.

## PLOS

**Official resources**

- PLOS ONE submission guidelines: https://journals.plos.org/plosone/s/submission-guidelines
- PLOS ONE LaTeX package: https://journals.plos.org/plosone/s/latex

PLOS supplies an official LaTeX package and BibTeX style for LaTeX submissions. Follow the target PLOS journal's package and upload instructions; manuscript and figure-file handling can be specific to the journal and submission stage.

`assets/journals/plos_one.tex` is a drafting scaffold, not a substitute for the current PLOS package.

## Cell Press

**Official starting point**

- Cell author resources: https://www.cell.com/cell/authors

Check the exact journal and article type for:

- Summary and Highlights limits;
- graphical abstract or eTOC requirements;
- STAR Methods or other methods structure;
- Resource Availability and Lead Contact sections;
- Limitations of the Study;
- data/code availability declarations; and
- generative-AI or AI-assisted-technology declarations.

No Cell Press LaTeX template is bundled. Use `references/cell_press_style.md` for writing guidance and the official author resources for submission requirements. Current Cell reference citations are numbered superscripts, not the older author-year style.

## IEEE

**Official resources**

- IEEE journal templates: https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/authoring-tools-and-templates/tools-for-ieee-authors/ieee-article-templates
- IEEE Template Selector: https://template-selector.ieee.org/

Use the Template Selector to resolve the publication-specific Word or LaTeX package. Page limits, review layout, biographies, open-access declarations, and overlength charges vary by journal.

No IEEE template is bundled in this skill.

## ACM

**Official resources**

- ACM LaTeX preparation: https://authors.acm.org/proceedings/production-information/preparing-your-article-with-latex
- ACM journals submission process: https://authors.acm.org/journals/submission-process

ACM uses the `acmart` class with publication-specific options and the TAPS production workflow. The review format selected by a conference or journal may differ from the final TAPS output.

No ACM template is bundled. Use the official ACM Master Article Template and the target publication's instructions.

## Elsevier

**Official resource**

- LaTeX instructions: https://www.elsevier.com/researcher/author/policies-and-guidelines/latex-instructions

Elsevier documents the `elsarticle` class and provides separate CAS single- and double-column templates. The exact journal's Guide for Authors determines word limits, article structure, reference style, highlights, graphical abstracts, and whether PDF-only initial submission is accepted.

Bundled examples:

| File | Citation mode | Matching bibliography style |
|---|---|---|
| `assets/journals/elsarticle-template-num.tex` | numeric | `elsarticle-num.bst` |
| `assets/journals/elsarticle-template-num-names.tex` | numeric with author names | `elsarticle-num-names.bst` |
| `assets/journals/elsarticle-template-harv.tex` | author-year | `elsarticle-harv.bst` |

The six bundled Elsevier files match the official CTAN `elsarticle` 3.5 bundle (2026-01-09); their LPPL notices are preserved. `elsarticle-num-names.bst` supports author names with numeric citations; sorting and compression are separate natbib options. The plain numeric style does not provide author metadata for `\citet`; use the numeric-with-names style when textual author citations are required. The current upstream sample repeats the label `fig1` for a table and figure: assign unique labels in your working copy. The class itself is not bundled. Compile with the current class and target journal settings. Elsevier Editorial Manager requires source files at one folder level; confirm journal upload item types, and include a compiled PDF when permitted.

Official package: https://ctan.org/pkg/elsarticle

## Other Publisher and Society Starting Points

| Publisher or journal | Official starting point | Key caution |
|---|---|---|
| Springer Nature journals | Target journal's “Submission Guidelines” | Template and reference style vary by journal |
| BMC | https://link.springer.com/brands/bmc/why-publish-with-bmc | Article type and declaration sections vary |
| Frontiers | https://www.frontiersin.org/guidelines/author-guidelines | Check article-type limits and required statements |
| PNAS | https://www.pnas.org/author-center | Check article type and current significance-statement rules |
| APS / PRL | https://journals.aps.org/authors | Use current REVTeX and journal-specific length rules |
| NEJM | https://www.nejm.org/author-center | Use article-type instructions and reporting guidelines |
| The Lancet | https://www.thelancet.com/what-we-publish | Use journal and article-type author guidance |

## What to Extract From Author Instructions

### Manuscript structure

- article type and section order;
- structured or unstructured abstract;
- word, character, display-item, and reference limits;
- required methods, limitations, reporting, and availability sections; and
- title-page and contributor information.

### Files and formatting

- accepted initial manuscript format;
- whether figures are embedded or uploaded separately;
- official Word/LaTeX package;
- line numbering, page numbering, and spacing;
- figure dimensions, color mode, and resolution;
- editable table requirements; and
- source archive requirements after acceptance.

### Policy and declarations

- authorship and contributor roles;
- competing interests and funding;
- ethics approval, consent, and trial registration;
- data, code, and materials availability;
- preprint and related-manuscript policy;
- reporting guideline/checklist; and
- use of generative AI or AI-assisted tools.

## Initial Submission Versus Production

Many journals accept a readable, format-flexible initial PDF and impose detailed house style only after revision or acceptance. Formatting a first submission to mimic the published two-column layout may add work without improving compliance.

Use this order:

1. satisfy the current initial-submission requirements;
2. preserve editable source and high-quality figures;
3. wait for journal-specific revision or production instructions; and
4. reformat only when requested or required.

## Bundled Asset Inventory

Only these journal-oriented assets are present:

- `assets/journals/nature_article.tex`
- `assets/journals/plos_one.tex`
- `assets/journals/neurips_article.tex`
- three Elsevier `elsarticle` examples and their `.bst` files

If a template is not in this list, obtain it from the official source. Do not invent a relative asset path.

## Final Journal Checklist

- [ ] Exact journal and article type confirmed
- [ ] Official instructions checked and dated
- [ ] Initial versus revised/final rules distinguished
- [ ] Official template used if required
- [ ] Length and display-item limits checked
- [ ] Required reporting guideline and checklist included
- [ ] Ethics, consent, trial registration, and disclosures complete
- [ ] Data/code/materials statements complete
- [ ] Figures and tables meet current technical requirements
- [ ] Source archive and PDF reviewed in the submission portal
