# Compilation and Quality Control

Reviewed 2026-09-30 with pdfLaTeX (TeX Live 2025), beamerposter 1.13,
tikzposter 2.0, archived baposter v2.0, and Poppler 26.09.0. The three asset
templates were compiled, rendered, and visually inspected. Examples involving
custom figures, fonts, bibliography, or conversion are illustrative and need
project-specific verification.

## Compile from the project directory

```bash
pdflatex -interaction=nonstopmode -halt-on-error poster.tex
pdflatex -interaction=nonstopmode -halt-on-error poster.tex
```

The second run resolves QR caching and cross-references. If the project uses a
BibTeX bibliography, run `bibtex poster` between LaTeX runs; for biblatex/Biber,
follow that project's backend configuration. LuaLaTeX/XeLaTeX support `fontspec`
with installed fonts but require their own compilation and visual checks.

Do not add `-shell-escape` merely to compile a poster. Convert SVG artwork to PDF
separately or use a known project workflow if external processing is required.

## Class-specific layout controls

- **beamerposter:** set paper dimensions with the package's `size` and `orientation`,
  or `size=custom,width=...,height=...` in centimetres. Beamer already loads geometry;
  use `\geometry{...}` for adjustments instead of loading it again with new options.
  `\setbeamersize{text margin left=...,text margin right=...}` controls content margins.
- **tikzposter:** choose the class's paper size and margins. A full-width block outside
  `columns` is simply `\block{Title}{Content}`. Use `titlewidthscale` and `bodywidthscale`
  for scaling; `width`, `x`, and `y` are not block option keys in version 2.0. `\vfill`
  between TikZ blocks does not distribute the poster's positioned blocks like ordinary
  vertical LaTeX text; use `blockverticalspace` and inspect the rendered layout.
- **baposter:** named boxes can reference only boxes already declared. Define a footer
  before a box referencing it. `above=footer` sets the bottom edge and may create an
  unexpectedly tall box unless its top is also positioned. Avoid blank paragraphs
  inside the option list. Existing class forks can differ; record the revision.

Keep margins appropriate for the printer's safe area. Increasing a margin decreases
usable space and can worsen overflow; first reduce content or correct the offending
box dimensions. Treat `0.85\linewidth` as a starting figure width, not a package rule.

## Read-only automated preflight

```bash
bash /path/to/latex-posters/scripts/review_poster.sh poster.pdf
```

The helper requires Bash, standard `awk`/`wc`, and Poppler. Exit 0 means its automated
checks passed; 1 means a detected failure, and 2 means a required Poppler inspector
is missing. It continues through independent checks and always prints the manual
checklist. It does not alter or compress the PDF.

The script inspects PDF readability, one-page output, approximate recognized sizes,
all font rows, and effective raster PPI. It does not enforce a venue-specific size,
parse all LaTeX warnings, certify PDF/X/accessibility, detect all overlap, or verify
scientific content. Low raster PPI is advisory because final requirements vary.

### Dimensions and page count

```bash
pdfinfo poster.pdf
```

PDF dimensions are in points (72 points/inch), which differ from TeX's 72.27 pt/inch.
Approximate portrait sizes:

| Paper | PDF width × height (points) | Physical size |
| --- | --- | --- |
| A0 | 2383.94 × 3370.39 | 841 × 1189 mm |
| A1 | 1683.78 × 2383.94 | 594 × 841 mm |
| 36 × 48 inches | 2592 × 3456 | 914.4 × 1219.2 mm |

Landscape swaps width and height. Compare the actual output to the venue's exact
specification; a recognized name is not evidence of compliance. Confirm `Pages: 1`.

### Font embedding

```bash
pdffonts poster.pdf
```

Inspect the `emb` column for every font, not just the first page of terminal output.
Font type names can contain spaces, so fixed whitespace column numbers are unreliable.
The bundled script locates the stable trailing fields. If no fonts are listed, the
PDF may contain outlines or rasterized text; that is not evidence of accessibility.

If `emb` is `no`, locate whether the font came from LaTeX or an imported figure and
rebuild that source with an embeddable font. `-dEmbedAllFonts=true` belongs to
Ghostscript, not `pdflatex`. It does not recover a missing font by itself.

### Raster resolution

```bash
pdfimages -list poster.pdf
```

`x-ppi` and `y-ppi` report resolution at the placed size. A raster image 3000 pixels
wide placed at 10 inches has 300 PPI. A small image does not need enough pixels to
cover the entire A0 sheet. Vector artwork has no raster resolution; check its labels
and line widths at final size. Soft masks are separate records, not extra photographs.
Use the printer's requirements; 300 PPI is a starting target for close inspection.

## Log and visual review

```bash
rg -n 'Overfull|Underfull|Warning|undefined' poster.log
pdftoppm -scale-to 2000 -singlefile -png poster.pdf poster-preview
```

Open `poster-preview.png`, then inspect the PDF or higher-resolution crops as needed.
A scaled preview detects layout defects but cannot prove print sharpness.

- Inspect title, all four edges, each column boundary, footer, and QR area.
- Overfull hboxes/vboxes mean material exceeded its intended box. Investigate and
  fix unintended overflow; the warning alone does not prove it was clipped by the page.
- Underfull boxes indicate spacing quality. A clean log does not detect overlapping
  TikZ/baposter boxes, missing scientific context, or unreadable text baked into a raster.
- Resolve missing figures, fonts, citations, and references. Draft figure-box warnings
  in the supplied templates are intentional until real artwork is supplied.
- Verify every number, statistical annotation, unit, legend, and caption against the
  analysis. Keep method details needed to interpret results and acknowledge limitations.

## Proof at physical size

A0 to A4 is approximately 25% linear scale. A 36×48-inch poster becomes 9×12 inches
at 25%, so Letter needs a smaller factor (about 23%, before printer margins).
A1 to A5 is approximately 25%.

For a proof scaled by factor `s`, use a viewing distance `s` times the intended
full-size distance: a 25% proof viewed at 1 foot approximates a full poster at 4 feet.
“25% zoom” on an unknown display is not calibrated. Print an actual-size crop to
check figure sharpness, captions, QR code size, and line weights. Test QR codes with
a device and verify their destination, not merely their visible pattern.

Use [WCAG contrast criteria](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
as digital palette guidance (4.5:1 normal text, 3:1 large text). Print conditions and
paper still need proofing. Caption text does not automatically create PDF tags or
screen-reader reading order; provide an accessible text alternative when necessary.

## Derived PDFs and printer requirements

Confirm the exact PDF/X variant, output profile, safe margins, bleed, and crop-mark
requirements with the printer. Plain pdfLaTeX output is not automatically PDF/X.
Do not assume every printer requires a CMYK conversion or PDF/X-1a.

Optional digital-sharing conversion, illustrative and not needed for the tested
small template PDFs:

```bash
gs -sDEVICE=pdfwrite -dPDFSETTINGS=/printer \
   -dNOPAUSE -dQUIET -dBATCH \
   -sOutputFile=poster-sharing.pdf poster.pdf
```

[Ghostscript creates a new PDF](https://ghostscript.readthedocs.io/en/latest/VectorDevices.html)
and can change content such as links, annotations, transparency, colors, and images.
Preserve the original, measure the resulting size, rerun preflight, and visually
compare the output. A small file can be a perfectly good vector poster; size alone
is not a quality metric.

## Primary documentation

- [beamerposter documentation and source](https://ctan.org/pkg/beamerposter)
- [tikzposter manual](https://mirrors.ctan.org/graphics/pgf/contrib/tikzposter/tikzposter.pdf)
- [Poppler project and current releases](https://poppler.freedesktop.org/); installed
  `man pdfinfo`, `man pdffonts`, and `man pdfimages` document the local command contracts.
- [Ghostscript PDF conversion](https://ghostscript.readthedocs.io/en/latest/VectorDevices.html)
