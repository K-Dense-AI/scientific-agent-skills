# LaTeX Poster Reference Index

Reviewed 2026-09-30. Start with `SKILL.md` at the skill root for the complete workflow
and tested version limits. Paths below are relative to the skill root. Supporting
snippets are illustrative; the three asset templates were compiled and rendered
with pdfLaTeX (TeX Live 2025) and Poppler 26.09.0.

## Choose a template

- `assets/beamerposter_template.tex`: Beamer blocks and configurable colors.
- `assets/tikzposter_template.tex`: TikZ-based columns and theme styling.
- `assets/baposter_template.tex`: named boxes and a spanning results area; requires
  a separately supplied class. The original upstream site was unavailable at review;
  the tested archival v2.0 source is documented in `latex_poster_packages.md`.

Missing figures appear as explicit draft placeholders so the templates can compile.
Replace all example content, citations, contact details, QR targets, and logo boxes
before delivery. Real figure dimensions change layout, so compile and inspect again.

## Reference map

| File | Consult for |
| --- | --- |
| `latex_poster_packages.md` | Package versions, valid option keys, themes, installation limitations |
| `latex_poster_reference.md` | Poster sizes, figure inclusion, typography, QR codes |
| `poster_layout_design.md` | Grids, column layouts, whitespace, reading-order heuristics |
| `poster_design_principles.md` | Contrast, font sizing, redundant color encoding, accessibility limits |
| `poster_content_guide.md` | Scientific content, statistics, section drafts, manuscript adaptation |
| `ai_graphics_for_posters.md` | Optional conceptual art, exact helper API contract, visual review |
| `compilation_and_quality_control.md` | Compilation, log triage, dimensions, all-font checks, placed PPI, proofs |
| `poster_patterns_and_presentation.md` | Section patterns, accessible presentation, discussion preparation |

## Compile and check

From the project directory after copying a template:

```bash
pdflatex -interaction=nonstopmode -halt-on-error poster.tex
pdflatex -interaction=nonstopmode -halt-on-error poster.tex
pdfinfo poster.pdf
pdffonts poster.pdf
pdfimages -list poster.pdf
pdftoppm -scale-to 2000 -singlefile -png poster.pdf poster-preview
```

Run `bash /path/to/latex-posters/scripts/review_poster.sh poster.pdf` for read-only
preflight. Exit 0 means automated checks passed, 1 means a failure, and 2 means a
required inspector is absent. Manual visual and scientific review remains required.
Use `assets/poster_quality_checklist.md` for the remaining checks.

Scientific results should come from verified analysis outputs. The optional image
helper creates conceptual diagrams; it does not establish values, statistical
findings, physical font sizes, or accessibility. There is no required AI-image quota.

For proofing, A0-to-A4 is about 25% linear scale. A 36×48-inch poster requires
9×12-inch paper at 25%; use a smaller factor to fit Letter. Judge a reduced proof
from the same scale factor times the intended full-size viewing distance.
