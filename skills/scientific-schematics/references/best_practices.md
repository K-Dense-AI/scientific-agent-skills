# Best Practices for Scientific Diagrams

## Overview

This guide supports prompt writing and manual figure review. Numeric design suggestions below are starting points; the target journal and article type determine submission requirements. AI-generated artwork also needs the venue's current permissions/disclosure policy checked before use.

### How this relates to the generator

These are the standards a figure is judged against — not a description of what
`scripts/generate_schematic.py` does for you. The generator produces a **PNG** and nothing else.
Read this file for two purposes:

- **To write the prompt.** Typography, colour, contrast, layout, labelling, and accessibility are
  all things the image model will attempt if you ask for them specifically. The sections below are
  the vocabulary for asking.
- **To judge the result, and to plan post-processing.** File format, resolution, colour space, and
  physical dimensions are fixed once the PNG exists. Where a journal's requirement differs from what
  came out, that is a conversion step you perform afterwards — the skill has no vector path, no DPI
  control, and no CMYK output.

## Publication Standards

### 1. File Format Requirements

**Vector Formats (Preferred)**
- **PDF**: Common for vector artwork and LaTeX; acceptance is venue-specific
  - Use for: Line drawings, flowcharts, block diagrams, circuit diagrams
  - Advantages: Scalable, small file size, embeds fonts
  - Standard for LaTeX workflows

- **EPS (Encapsulated PostScript)**: Legacy format, still accepted
  - Use for: Older publishing systems
  - Compatible with most journals
  - Can be converted from PDF

- **SVG (Scalable Vector Graphics)**: Web-friendly, increasingly accepted
  - Use for: Online publications, interactive figures
  - Can be edited in vector graphics software
  - Not all journals accept SVG

**Raster Formats (When Necessary)**
- **TIFF**: Professional standard for raster graphics
  - Use for: Microscopy images, photographs combined with diagrams
  - Minimum 300 DPI at final print size
  - Lossless compression (LZW)

- **PNG**: Web-friendly, lossless compression
  - Use for: Online supplementary materials, presentations
  - Minimum 300 DPI for print
  - Supports transparency

**Avoid for new diagram masters**
- **JPEG**: Lossy compression can damage text and lines; some venues accept high-quality JPEG for photographs
- **GIF**: Limited colors, inappropriate for scientific figures
- **BMP**: Uncompressed, unnecessarily large files

### 2. Resolution Requirements

**Vector Graphics**
- Infinite resolution (scalable)
- **Recommended**: Always use vector when possible

**Raster graphics**
- Calculate effective pixels per inch at the final physical size.
- Photographic submission targets commonly start at 300 ppi; line art may require more.
- Screen quality depends on pixel dimensions and display size, not DPI metadata.
- Check the venue-specific requirement before exporting; changing DPI metadata or upsampling cannot recover missing detail.

**Calculating DPI**
```
DPI = pixels / (inches at final size)

Example:
Image size: 2400 × 1800 pixels
Final print size: 8 × 6 inches
DPI = 2400 / 8 = 300 ✓ (acceptable)
```

### 3. Size and Dimensions

**Choose the venue and article type first**
- Nature's main-figure guide lists 89 mm and 183 mm widths; Extended Data has separate rules.
- Other publishers have different width ranges and file requirements. Do not reuse Nature dimensions for Science, Cell, PLOS, or IEEE without checking that venue's current instructions.
- See the source links under Journal-Specific Guidelines below.

**Best Practices**
- Design at final print size (avoid scaling)
- Use journal templates when available
- Allow margins for cropping
- Test appearance at final size before submission

### 4. Typography Standards

**Font Selection**
- **Recommended**: Arial, Helvetica, Calibri (sans-serif)
- **Acceptable**: Times New Roman (serif) for mathematics-heavy
- **Avoid**: Decorative fonts, script fonts, system fonts that may not embed

**Font Sizes (at final print size)**
- **Minimum**: 6-7 pt (journal dependent)
- **Axis labels**: 8-9 pt
- **Figure labels**: 10-12 pt
- **Panel labels (A, B, C)**: 10-14 pt, bold
- **Main text**: Should match manuscript body text

**Text Clarity**
- Use sentence case: "Time (seconds)" not "TIME (SECONDS)"
- Include units in parentheses: "Temperature (°C)"
- Spell out abbreviations in figure caption
- Avoid rotated text when possible (exception: y-axis labels)
- **No figure numbers in diagram** - do not include "Figure 1:", "Fig. 1", etc. (these are added by LaTeX/document)

### 5. Line Weights and Strokes

**Recommended Line Widths**
- **Diagram outlines**: 0.5-1.0 pt
- **Connection lines/arrows**: 1.0-2.0 pt
- **Emphasis elements**: 2.0-3.0 pt
- **Minimum visible**: 0.25 pt at final size

**Consistency**
- Use same line weight for similar elements
- Vary line weight to show hierarchy
- Avoid hairline rules (too thin to print reliably)

## Accessibility and Colorblindness

### 1. Colorblind-Safe Palettes

**Okabe-Ito Palette (Recommended)**
A useful starting palette from [Color Universal Design](https://jfly.uni-koeln.de/color/); no palette guarantees accessibility for every viewer, background, or adjacent pair:

```latex
% RGB values
Orange:     #E69F00 (230, 159,   0)
Sky Blue:   #56B4E9 ( 86, 180, 233)
Green:      #009E73 (  0, 158, 115)
Yellow:     #F0E442 (240, 228,  66)
Blue:       #0072B2 (  0, 114, 178)
Vermillion: #D55E00 (213,  94,   0)
Purple:     #CC79A7 (204, 121, 167)
Black:      #000000 (  0,   0,   0)
```

**Alternative: ColorBrewer Palettes**
- **Qualitative**: consider Set2, Paired, Dark2 after enabling ColorBrewer's colorblind-safe filter for the chosen number of categories
- **Sequential**: Blues, Greens, Oranges (avoid Reds/Greens together)
- **Diverging**: RdBu (Red-Blue), PuOr (Purple-Orange)

**Colors to Avoid Together**
- Red-Green combinations without redundant labels or shapes
- Blue-Purple combinations
- Yellow-Light green combinations

### 2. Redundant Encoding

Don't rely on color alone. Use multiple visual channels:

**Shape + Color**
```
Circle + Blue   = Condition A
Square + Orange = Condition B
Triangle + Green = Condition C
```

**Line Style + Color**
```
Solid + Blue = Treatment 1
Dashed + Orange = Treatment 2
Dotted + Green = Control
```

**Pattern Fill + Color**
```
Solid fill + Blue = Group A
Diagonal stripes + Orange = Group B
Cross-hatch + Green = Group C
```

### 3. Grayscale Compatibility

**Test Requirement**: All diagrams must be interpretable in grayscale

**Strategies**
- Use different shades (light, medium, dark)
- Add patterns or textures to filled areas
- Vary line styles (solid, dashed, dotted)
- Use labels directly on elements
- Include text annotations

**Grayscale Test**
```bash
# Convert to grayscale to test
magick diagram.png -colorspace Gray diagram_gray.png
```

### 4. Contrast Requirements

**WCAG 2.2 web accessibility targets** (useful checks, not a blanket journal certification)
- **Normal text**: 4.5:1
- **Large text** (at least 18 pt regular or 14 pt bold): 3:1
- **Necessary graphical objects**: 3:1 against adjacent colors, subject to the criterion's exceptions

See [text contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) and [non-text contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html). Raster labels still need to be legible at their final displayed size.

**High Contrast Practices**
- Dark text on light background (or vice versa)
- Avoid low-contrast color pairs (yellow on white, light gray on white)
- Use black or dark gray for critical text
- White text on dark backgrounds needs larger font size

### 5. Alternative Text and Descriptions

**Figure Captions Must Include**
- Description of diagram type
- All abbreviations spelled out
- Explanation of symbols and colors
- Sample sizes (n) where relevant
- Statistical annotations explained
- Reference to detailed methods if applicable

**Example Caption**
"Participant flow diagram following CONSORT guidelines. Rectangles represent study stages, with participant numbers (n) shown. Exclusion criteria are listed beside each screening stage. In this illustrative complete-case example, primary-outcome analysis included n=325 participants (160 and 165); 25 lacked primary-outcome measurements. Reconcile this with the statistical analysis plan rather than equating every follow-up loss with exclusion from intention-to-treat analysis."

## Design Principles

### 1. Simplicity and Clarity

**Occam's Razor for Diagrams**
- Remove every element that doesn't add information
- Simplify complex relationships
- Break complex diagrams into multiple panels
- Use consistent layouts across related figures

**Visual Hierarchy**
- Most important elements: Largest, darkest, central
- Supporting elements: Smaller, lighter, peripheral
- Annotations: Minimal, clear labels only

### 2. Consistency

**Within a Figure**
- Same shape/color represents same concept
- Consistent arrow styles for same relationships
- Uniform spacing and alignment
- Matching font sizes for similar elements

**Across Figures in a Paper**
- Reuse color schemes
- Maintain consistent node styles
- Use same notation system
- Apply same layout principles

### 3. Professional Appearance

**Alignment**
- Use grids for node placement
- Align nodes horizontally or vertically
- Evenly space elements
- Center labels within shapes

**White Space**
- Don't overcrowd diagrams
- Leave breathing room around elements
- Use white space to group related items
- Margins around entire diagram

**Polish**
- No jagged lines or misaligned elements
- Smooth curves and precise angles
- Clean connection points
- No overlapping text

## Common Pitfalls and Solutions

### Pitfall 1: Overcomplicated Diagrams

**Problem**: Too much information in one diagram
**Solution**: 
- Split into multiple panels (A, B, C)
- Create overview + detailed diagrams
- Move details to supplementary figures
- Use hierarchical presentation

### Pitfall 2: Inconsistent Styling

**Problem**: Different styles for same elements across figures
**Solution**:
- Create and use style templates
- Use the same color palette throughout
- Document your style choices

### Pitfall 3: Poor Label Placement

**Problem**: Labels overlap elements or are hard to read
**Solution**:
- Place labels outside shapes when possible
- Use leader lines for distant labels
- Rotate text only when necessary
- Ensure adequate contrast with background

### Pitfall 4: Tiny Text

**Problem**: Text too small to read at final print size
**Solution**:
- Design at final size from the start
- Test print at final size
- Minimum 7-8 pt font
- Simplify labels if space is limited

### Pitfall 5: Ambiguous Arrows

**Problem**: Unclear what arrows represent or where they point
**Solution**:
- Use different arrow styles for different meanings
- Add labels to arrows
- Include legend for arrow types
- Use anchor points for precise connections

### Pitfall 6: Color Overuse

**Problem**: Too many colors, confusing or inaccessible
**Solution**:
- Limit to 3-5 colors maximum
- Use color purposefully (categories, emphasis)
- Stick to colorblind-safe palette
- Provide redundant encoding

## Quality Control Checklist

### Before Submission

**Technical Requirements**
- [ ] Correct file format (PDF/EPS preferred for diagrams)
- [ ] Sufficient resolution (vector or 300+ DPI)
- [ ] Appropriate size (matches journal column width)
- [ ] Fonts embedded in PDF
- [ ] No compression artifacts

**Accessibility**
- [ ] Colorblind-safe palette used
- [ ] Works in grayscale (tested)
- [ ] Text minimum 7-8 pt at final size
- [ ] High contrast between elements
- [ ] Redundant encoding (not color alone)

**Design Quality**
- [ ] Elements aligned properly
- [ ] Consistent spacing and layout
- [ ] No overlapping text or elements
- [ ] Clear visual hierarchy
- [ ] Professional appearance

**Content**
- [ ] All elements labeled
- [ ] Abbreviations defined
- [ ] Units included where relevant
- [ ] Legend provided if needed
- [ ] Caption comprehensive

**Consistency**
- [ ] Matches other figures in style
- [ ] Same notation as text
- [ ] Consistent with journal guidelines
- [ ] Cross-references work

## Journal-Specific Guidelines

Consult the current instructions for the exact journal and figure category. Avoid treating a local reviewer score or a single resolution value as a publication standard.

- [Nature final submission](https://www.nature.com/nature/for-authors/final-submission): main figures use 89/183 mm widths and editable vector artwork for line drawings where possible. Photographs need at least 300 dpi at use size. Extended Data has separate format/size rules. The [figure guide](https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications/) recommends RGB and stresses that upsampling cannot improve detail.
- [PLOS ONE figures](https://journals.plos.org/plosone/s/figures): TIFF/EPS, 300–600 dpi, and explicit width/height limits; inspect the current table rather than assuming generic single/double column widths.
- [IEEE graphics](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-graphics-for-your-article/): use the current graphics guide for dimensions, format, resolution, fonts, and color handling. Do not assume all print editions are grayscale.
- [Science instructions](https://www.science.org/content/page/instructions-preparing-initial-manuscript) and [Cell author resources](https://www.cell.com/cell/authors): exact dimensions and submission-stage rules must be checked for the manuscript. Science's and Cell's pages blocked automated access during this review; no numeric requirements are asserted here.

## Scientific integrity before styling

Use source material for every entity, count, and relationship. For [CONSORT 2025](https://www.consort-spirit.org/item-22a-randomized), distinguish allocation, receipt of intervention, discontinuation, follow-up, and the primary-outcome analysis set. For [PRISMA 2020](https://www.prisma-statement.org/prisma-2020-flow-diagram), reconcile records, reports, and studies using the appropriate template. A diagram should not invent omitted numbers or turn a missing outcome into an automatic analysis exclusion.

## Software-Specific Export Settings

### AI-Generated Images

AI-generated diagrams are exported as PNG images and can be included in LaTeX documents using:

```latex
\includegraphics[width=\textwidth]{diagram.png}
```

### Python (Matplotlib) Export

Runnable local example, checked with Matplotlib 3.11.2. Install in a separate environment (`uv run --no-project --isolated --with matplotlib==3.11.2 python example.py`). This produces a schematic from explicit code; it does not vectorize a generated PNG.

```python
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Set publication quality
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
plt.rcParams['font.size'] = 8
plt.rcParams['pdf.fonttype'] = 42  # TrueType fonts in PDF

fig, ax = plt.subplots(figsize=(3.5, 2.0))
ax.annotate('Input', (0.2, 0.5), ha='center', bbox={'boxstyle': 'round', 'fc': 'white'})
ax.annotate('Output', (0.8, 0.5), ha='center', bbox={'boxstyle': 'round', 'fc': 'white'})
ax.annotate('', (0.65, 0.5), (0.35, 0.5), arrowprops={'arrowstyle': '->'})
ax.set_axis_off()

# Save with proper DPI and cropping
fig.savefig('diagram.pdf', dpi=300, bbox_inches='tight', 
            pad_inches=0.1, transparent=False)
fig.savefig('diagram.png', dpi=300, bbox_inches='tight')
plt.close(fig)
```

### Schemdraw Export

Checked with Schemdraw 0.23 and Matplotlib 3.11.2. Install `schemdraw[matplotlib]` in an isolated environment. The SVG backend alone cannot save PDF/PNG; choose the Matplotlib backend for this example. See [the drawing API](https://schemdraw.readthedocs.io/en/latest/classes/drawing.html).

```python
import matplotlib
matplotlib.use('Agg')
import schemdraw
import schemdraw.elements as elm

d = schemdraw.Drawing(canvas='matplotlib', show=False)
d += elm.Resistor().label('1 kΩ')
d += elm.Capacitor().down().label('10 µF')
d += elm.Ground()

# Export
d.save('circuit.svg')  # Vector
d.save('circuit.pdf')  # Vector
d.save('circuit.png', dpi=300)  # Raster
```

### Inkscape Command Line

Current flags follow the [Inkscape manual](https://inkscape.org/doc/inkscape-man.html); the old `--export-png` and `--export-pdf` forms should not be used. These optional commands require Inkscape and were documentation-checked only.

```bash
# SVG to PNG (illustrative: Inkscape is not installed in the validation environment)
inkscape diagram.svg --export-type=png --export-filename=diagram.png --export-dpi=300

# SVG to PDF (preserves vector elements from the SVG)
inkscape diagram.svg --export-type=pdf --export-filename=diagram.pdf
```

## Version Control Best Practices

**Keep Source Files**
- Save original .tex, .py, or .svg files
- Use descriptive filenames with versions
- Document color palette and style choices
- Include README with regeneration instructions

**Directory Structure**
```
figures/
├── source/          # Editable source files
│   ├── diagram1.tex
│   ├── circuit.py
│   └── pathway.svg
├── generated/       # Auto-generated outputs
│   ├── diagram1.pdf
│   ├── circuit.pdf
│   └── pathway.pdf
└── final/          # Final submission versions
    ├── figure1.pdf
    └── figure2.pdf
```

**Git Tracking**
- Track source files (.tex, .py)
- Consider .gitignore for generated PDFs (large files)
- Use releases/tags for submission versions
- Document generation process in README

## Testing and Validation

### Pre-Submission Tests

**Visual Tests**
1. **Print test**: Print at final size, check readability
2. **Grayscale test**: Convert to grayscale, verify interpretability
3. **Zoom test**: View at 400% and 25% to check scalability
4. **Screen test**: View on different devices (phone, tablet, desktop)

**Technical Tests**
1. **Font embedding**: Check PDF properties
2. **Resolution check**: Verify DPI meets requirements
3. **File size**: Ensure under journal limits
4. **Format compliance**: Verify accepted format

**Accessibility Tests**
1. **Colorblind simulation**: Use tools like Color Oracle
2. **Contrast checker**: WCAG contrast ratio tools
3. **Screen reader**: Test alt text (for web figures)

### Tools for Testing

**Colorblind Simulation**
- Color Oracle (free, cross-platform)
- Coblis (Color Blindness Simulator)
- Photoshop/GIMP colorblind preview modes

**PDF Inspection**

Requires Poppler (`pdfinfo`, `pdffonts`, `pdfimages`) and ImageMagick 7 (`magick`). Embedded-image ppi from `pdfimages -list` differs from a PNG's density metadata; it reflects placement in that PDF.
```bash
# Check PDF properties
pdfinfo diagram.pdf

# Check fonts
pdffonts diagram.pdf

# Inspect embedded raster resolution in a PDF (Poppler)
pdfimages -list diagram.pdf

# Inspect pixel dimensions and density metadata of the generated PNG (ImageMagick 7)
magick identify -verbose diagram.png
```

**Contrast Checking**
- WebAIM Contrast Checker: https://webaim.org/resources/contrastchecker/
- Colorable: https://colorable.jxnblk.com/

## Summary: Golden Rules

1. **Vector first**: Always use vector formats when possible
2. **Design at final size**: Avoid scaling after creation
3. **Colorblind-safe palette**: Use Okabe-Ito or similar
4. **Test in grayscale**: Diagrams must work without color
5. **Minimum 7-8 pt text**: At final print size
6. **Consistent styling**: Across all figures in paper
7. **Keep it simple**: Remove unnecessary elements
8. **High contrast**: Ensure readability
9. **Align elements**: Professional appearance matters
10. **Comprehensive caption**: Explain everything

## Further Resources

- **Nature Figure Preparation**: https://www.nature.com/nature/for-authors/final-submission
- **Science Figure Guidelines**: https://www.science.org/content/page/instructions-preparing-initial-manuscript
- **WCAG Accessibility Standards**: https://www.w3.org/WAI/WCAG22/quickref/
- **Color Universal Design (CUD)**: https://jfly.uni-koeln.de/color/
- **ColorBrewer**: https://colorbrewer2.org/

Check the final artifact in its real manuscript layout; these checks support review but do not guarantee scientific correctness, accessibility, or publisher acceptance.

