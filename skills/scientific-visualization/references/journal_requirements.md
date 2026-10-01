# Publisher and Journal Figure Snapshots

Reviewed 2026-10-01 against official pages, except the explicitly historical Science snapshot below. Requirements are date-sensitive and often depend on the journal, article type, figure type, and submission phase. Verify the live target-journal page before submission. Source IDs resolve in `sources.md`.

The machine-readable subset in `assets/publisher_profiles.json` is for planning and deterministic screening only. `scripts/export_plan.py` never claims compliance.

## Nature (flagship journal)

**Scope:** `Nature` final submission after acceptance in principle, not all Nature Portfolio journals [NATURE-FINAL] [NATURE-FIG].

- Standard widths: 89 mm single column, 183 mm double column; 120-136 mm is possible for one-and-a-half columns.
- Full page depth: 247 mm.
- Panels: lowercase bold upright `a`, `b`, `c`, 8 pt.
- Other text: 5-7 pt at final size; Helvetica or Arial preferred.
- Keep text and line art editable; do not outline or rasterize them.
- Preferred line/graph containers include AI, PostScript, vector EPS, and PDF.
- Preferred raster source: layered PSD or TIFF. The final-submission page states 300-600 dpi for photographs; minimum 300 dpi at maximum use size.
- The newer research-figure guide recommends export images at 450 dpi or above because online proofs top out at 450 dpi. This is a recommendation layered on the final-submission minimum, not a universal 450 dpi rule.
- RGB is recommended; final print conversion may use CMYK.
- Type 42 fonts are requested. The figure guide explicitly gives `matplotlib.rcParams["pdf.fonttype"] = 42`.
- High-quality JPEG can be accepted when it is the only option for a photograph. Therefore, “Nature never accepts JPEG” is false.
- Extended Data has different rules: RGB, maximum 300 ppi, maximum 10 MB, and JPEG preferred with TIFF/EPS alternatives.

Do not apply these flagship rules automatically to Nature Communications, Scientific Reports, npj journals, or Nature Reviews; each has its own page.

## Science (AAAS flagship journal)

**Scope:** historical `Science` snapshot accessed 2026-07-23, with separate initial and revised stages [SCIENCE-INITIAL] [SCIENCE-REVISED]. Both pages blocked direct and fresh extraction on 2026-10-01. The numbers below remain provisional until live instructions are checked.

### Initial submission

- A single manuscript file with embedded figures is preferred.
- Figures should be 300 dpi for review.
- Printed widths are usually 5.7 cm (one column), 12.1 cm (two columns), or 18.4 cm (three columns).
- Vector creation is preferred.
- Use sans serif, preferably Helvetica. Lettering should be about 7 pt after reduction and no smaller than 5 pt.
- Avoid red/green combinations and similar hues as sole identifiers; add shape/texture where needed.
- Scales should not extend beyond the plotted data merely as empty range.

### Revised manuscript

- Upload each figure separately.
- Preferred vector formats: PDF, EPS, or AI.
- Raster illustrations/diagrams and photographs/microscopy: TIFF.
- Vector/raster combinations: PDF or EPS.
- Line art without a vector original: at least 300 dpi at final size, preferably higher.
- Color and grayscale images: at least 300 dpi at final size.
- Upsampling is not permitted.
- PowerPoint and figures embedded in Word are not accepted at this stage.

The 2026-07-23 snapshot did **not** state the older blanket “1,000 dpi line art / 600 dpi combination” numbers that this skill previously claimed.

Science Advances and other AAAS journals publish separate figure guides; do not reuse the flagship profile without checking.

## Cell Press

**Scope:** general Cell Press figure page; exceptions are explicitly listed for STAR Protocols and `Cell` Leading Edge [CELL-FIG].

### Initial submission and review

- Cell Press accepts a wide range of formats, sizes, and resolutions.
- Figures may be embedded or uploaded separately.
- Individual 1-2 MB files are recommended for reviewer convenience.

### Final production

- Upload each main figure as one separate file containing all its panels; keep titles/legends in the manuscript.
- Recommended overall maximum: 16.5 × 20 cm. This is framed as a recommendation.
- Two-column article widths: 8.5 cm, 11.4 cm, and 17.4 cm.
- Three-column formats: 5.5 cm, 11.4 cm, and 17.4 cm.
- Maximum individual file size: 20 MB.
- TIFF and PDF are preferred for most journals/types. EPS, JPEG, and CDX are accepted. Special cases differ.
- Color/grayscale: at least 300 dpi; black-and-white: at least 500 dpi; line art: at least 1,000 dpi at final size.
- RGB, Arial, capital panel letters, 6-8 pt text, and 0.5-1.5 pt strokes.
- Embed fonts. General production guidance says flatten layers, except specified `Cell` Leading Edge material.
- Do not use red and green together as the only distinction.

Cell Press requires minimal image processing, original unprocessed data on request, and disclosure of processing/stitching. Its current policy prohibits generative AI/AI-assisted alteration of research/data images, including brightness, contrast, or color-balance adjustment performed by such tools.

## PLOS research journals

**Scope:** current PLOS Computational Biology page, consistent with the sampled PLOS research-journal figure pages [PLOS-FIG]. Verify the selected PLOS journal.

- Formatting requirements are waived until provisional Editorial Accept.
- Final figure format: TIFF or EPS.
- Width: 789-2250 px at 300 dpi, equivalent to 6.68-19.05 cm.
- Text-column alignment recommendation: no wider than 13.2 cm.
- Maximum height: 2625 px at 300 dpi, equivalent to 22.23 cm.
- Resolution: 300-600 dpi at final dimensions. The page warns that above 600 may trigger resizing and below 300 will degrade output.
- The summary table says less than 10 MB; the detailed section says 10 MB or less. The planner conservatively uses the stricter boundary and flags the inconsistency.
- Text: Arial, Times, or Symbol, 8-12 pt.
- Color mode: RGB 8-bit/channel or grayscale.
- Put all panels of one figure in one single-page file. TIFF must have no alpha channel and must use LZW compression.
- The pixel bounds are expressed at 300 dpi: a 600 dpi raster at the same physical size contains twice as many pixels per axis. The screen compares physical size via its 300 dpi equivalent, not an absolute 2250-pixel cap.
- Captions remain in the manuscript; filenames are `Fig1.tif`, `Fig2.eps`, and so on.
- Do not increase pixel count and present that as improved resolution.

For manuscripts submitted on or after 2026-04-01, original uncropped, minimally adjusted blot/gel images must be supplied before acceptance. Adjustments must not alter scientific information and must be applied consistently.

## Elsevier

**Scope:** publisher-general artwork instructions. Elsevier explicitly says journal-specific Guides for Authors can override them [ELSEVIER-FORMAT] [ELSEVIER-SIZE].

- Recommended containers: TIFF for halftones/bitmaps, EPS for vector-based images (including embedded images), and PDF for vector/text material.
- JPEG and Microsoft Office files are accepted in the general checklist; use the journal page to decide suitability.
- RGB is preferred unless the journal says otherwise.
- General target widths: 90 mm single, 140 mm one-and-a-half, 190 mm full; 30 mm is the listed minimal size.
- General raster targets at final size: 300 dpi halftone, 500 dpi combination, 1,000 dpi line art.
- General lettering rule of thumb: 7 pt normal text, not smaller than 6 pt for sub/superscripts.

These are publisher defaults, not universal Elsevier-journal hard limits.

## IEEE journals

**Scope:** IEEE Author Center journal graphics page, modified 2025-02-25 [IEEE-SIZE].

- Acceptable vector formats listed on the page: PS, EPS, PDF.
- Non-vector color/grayscale graphics: **greater than** 300 dpi.
- Black-and-white line art: **greater than** 600 dpi.
- One-column width: 3.5 in / 88.9 mm.
- Two-column width: 7.16 in / 182 mm.
- IEEE warns that increasing resolution after creation does not improve quality.

Conference and magazine instructions can differ; use their separate Author Center pages.

## BMC

**Scope:** BMC Bioinformatics, used as a current BMC-journal example rather than a guaranteed BMC-wide profile [BMC-BIOINFO].

- Web widths: 600 px standard, 1200 px high resolution.
- PDF widths: 85 mm half page, 170 mm full page.
- Maximum figure-plus-legend height: 225 mm.
- Approximately 300 dpi at final size.
- Fonts embedded; lines wider than 0.25 pt at final width.
- Accepted formats include EPS, PDF, Word, PowerPoint, TIFF, JPEG, PNG, BMP, and CDX; JPEG is described as less suitable for graphical images.
- One composite file per multi-panel figure; individual file maximum 10 MB.

BMC Bioinformatics now redirects to Springer Nature Link. The approximate DPI target has no numeric tolerance and the height includes the legend; the planner reports these as review items rather than unconditional passes.

## ACS Publications

**Scope:** legacy “Preparing Manuscript Graphics,” currently hosted on the official ACS Paragon Plus site with an explicit update date of 2006-01-21 [ACS-GRAPHICS]. It is not a current universal digital-export profile; use the selected journal’s Author Guidelines.

- Listed maximum dimensions: 3.25 in single column, 7 in double column, 9.5 in length.
- Lettering should be no smaller than 5 pt after reduction; Helvetica/Arial are suggested.
- Lines should be no thinner than 1 pt on that general page.
- The page mentions using the best available resolution and 600+ dpi printing, but it does not establish a universal per-figure digital file-format/DPI rule for all ACS journals.

Use the selected ACS journal’s current Author Guidelines for formats, color, resolution, and TOC/abstract graphics. The planner intentionally does not invent missing ACS-wide requirements.

## Rules that are not universal

Do not present these as cross-publisher laws:

- “JPEG is never accepted.” Several publishers accept it for photographs or specific workflows.
- “All line art must be 1,000/1,200 dpi.” Vector output is often preferred, and current Science revised guidance says at least 300 dpi when vector is unavailable.
- “All publishers require grayscale compatibility.” Accessibility guidance varies; use redundant encoding regardless.
- “All figures must be RGB.” RGB is often preferred, but Nature accepts RGB or CMYK for final print artwork and target-journal rules can differ.
- “All figures need error bars/significance stars.” The right display depends on the estimand, data, and analysis.
- “A matching DPI/width means compliant.” Technical metadata is only one part of submission review.

## Submission-stage workflow

1. Identify exact journal, article type, figure type, and current stage.
2. Save the live official page URL and access date.
3. Create a plan with `scripts/export_plan.py`.
4. Export with explicit dimensions and settings.
5. Inspect the delivered file with `scripts/image_metadata.py`.
6. Review fonts, embedded rasters, image integrity, accessibility, caption, and source data manually.
7. Re-check official instructions immediately before upload.
