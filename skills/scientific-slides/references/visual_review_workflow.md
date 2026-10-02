# Visual Review Workflow for Presentations

## Overview

Visual review is a critical quality assurance step for presentations, allowing you to identify and fix layout issues, text overflow, element overlap, and design problems before presenting. This guide covers converting presentations to images, systematic visual inspection, common issues, and iterative improvement strategies.

## Render for layout; extract text for content checks

Render every slide with `pdf_to_images.py` to inspect layout, cropping, and labels.
Use PDF text extraction separately to check citations and wording; it cannot detect
visual overlap. Work in page batches if tool/image limits require it. A past tool buffer
failure is not a property of all PDFs and does not prohibit direct PDF inspection.

1. Export PDF from PowerPoint/Beamer.
2. Render pages and review them visually.
3. Check the source text, citations, original figures and reading order separately.
4. Correct source files, export again and recheck affected pages.

## Why Visual Review Matters

### Common Problems Invisible in Source

**LaTeX Beamer Issues**:
- Text overflow from text boxes
- Overlapping elements (equations over images)
- Poor line breaking
- Figures extending beyond slide boundaries
- Font size issues at actual resolution

**PowerPoint Issues**:
- Text cut off by shapes or slide edges
- Images overlapping with text
- Inconsistent spacing between slides
- Color rendering differences
- Font substitution problems

**Projection Issues**:
- Content visible on laptop but cut off when projected
- Colors looking different on projector
- Low contrast elements becoming invisible
- Small details disappearing

### Benefits of Visual Review

- **Catch layout errors early**: Fix before printing or presenting
- **Verify readability**: Ensure text is large enough and high contrast
- **Check consistency**: Spot inconsistencies across slides
- **Test accessibility**: Verify color contrast and clarity
- **Validate design**: Ensure professional appearance

## Conversion: PDF to Images

### Method 1: Using pdf_to_images.py Script (Recommended)

**No External Dependencies Required**:
The script uses PyMuPDF, a self-contained Python library - no poppler or other system software needed.

**Installation**:
```bash
# Install in your task environment (the repository environment omits scientific dependencies)
uv pip install pymupdf
```

**Basic Conversion**:
```bash
# Convert all slides to JPEG images
python skills/scientific-slides/scripts/pdf_to_images.py presentation.pdf slide --dpi 150

# Creates: slide-001.jpg, slide-002.jpg, slide-003.jpg, ...
```

**High-Resolution Conversion**:
```bash
# Higher quality for detailed inspection (300 DPI)
python skills/scientific-slides/scripts/pdf_to_images.py presentation.pdf slide --dpi 300

# PNG format (lossless, larger files)
python skills/scientific-slides/scripts/pdf_to_images.py presentation.pdf slide --dpi 150 --format png
```

**Convert Specific Slides**:
```bash
# Slides 5-10 only
python skills/scientific-slides/scripts/pdf_to_images.py presentation.pdf slide --dpi 150 --first 5 --last 10

# Single slide
python skills/scientific-slides/scripts/pdf_to_images.py presentation.pdf slide --dpi 150 --first 3 --last 3
```

**Output Options**:
```bash
# Different output directory
python skills/scientific-slides/scripts/pdf_to_images.py presentation.pdf review/slide --dpi 150

# Custom naming
python skills/scientific-slides/scripts/pdf_to_images.py presentation.pdf output/presentation --dpi 150
```

### Method 2: Exporting PowerPoint Through LibreOffice

For PowerPoint presentations, export to PDF with LibreOffice, then render as in Method 1:

```bash
soffice --headless --convert-to pdf --outdir review presentation.pptx
python skills/scientific-slides/scripts/pdf_to_images.py review/presentation.pdf review/slide --dpi 150
```

LibreOffice substitutes fonts that are not installed, so confirm final text fit in PowerPoint.

**Advantages**:
- Optimized for PowerPoint files
- Can create overview grids
- Handles .pptx format directly
- Customizable layout

### Method 3: Using ImageMagick 7 (Optional)

**Installation**:
```bash
# Ubuntu/Debian
sudo apt-get install imagemagick

# macOS
brew install imagemagick
```

**Conversion** (PDF reading also requires Ghostscript and an enabled PDF security policy; prefer PyMuPDF if unavailable):
```bash
# Convert PDF to images
magick -density 150 presentation.pdf slide.jpg

# Higher quality
magick -density 300 presentation.pdf slide.jpg

# Specific format
magick -density 150 presentation.pdf slide.png
```

### Method 4: Using Python (Programmatic)

```python
import pymupdf as fitz  # PyMuPDF

# Open PDF
doc = fitz.open('presentation.pdf')

# Convert each page to image
for i, page in enumerate(doc, start=1):
    pixmap = page.get_pixmap(dpi=200)
    pixmap.save(f'slide-{i:03d}.jpg', output='jpeg')

doc.close()
```

**Install PyMuPDF**:
```bash
uv pip install pymupdf
# No external dependencies needed!
```

## Systematic Visual Inspection

### Inspection Workflow

**Step 1: Overview Pass**
- View all slides quickly
- Note overall consistency
- Identify obviously problematic slides
- Create list of slides needing detailed review

**Step 2: Detailed Inspection**
- Review each flagged slide carefully
- Check against issue checklist (below)
- Document specific problems with slide numbers
- Take notes on required fixes

**Step 3: Cross-Slide Comparison**
- Check consistency across similar slides
- Verify uniform spacing and alignment
- Ensure consistent font sizes
- Check color scheme consistency

**Step 4: Distance Test**
- View images at reduced size (simulates projection)
- Check readability from ~6 feet
- Verify key elements are visible
- Test if main message is clear

### Issue Checklist

Review each slide for these common problems:

#### Text Issues

**Overflow and Truncation**:
- [ ] Text cut off at slide edges
- [ ] Text extending beyond text boxes
- [ ] Equations running into margins
- [ ] Captions cut off at bottom
- [ ] Bullet points extending beyond boundary

**Readability**:
- [ ] Font size too small (minimum 18pt visible)
- [ ] Poor contrast (text vs background)
- [ ] Inadequate line spacing
- [ ] Text too close to slide edge
- [ ] Overlapping lines of text

#### Element Overlap

**Text Overlaps**:
- [ ] Text overlapping with images
- [ ] Text overlapping with shapes
- [ ] Multiple text boxes overlapping
- [ ] Labels overlapping with data points
- [ ] Title overlapping with content

**Visual Element Overlaps**:
- [ ] Images overlapping
- [ ] Shapes overlapping inappropriately
- [ ] Figures extending into margins
- [ ] Legend overlapping with plot
- [ ] Watermark obscuring content

#### Layout and Spacing

**Alignment Issues**:
- [ ] Misaligned text boxes
- [ ] Uneven margins
- [ ] Inconsistent element positioning
- [ ] Off-center titles
- [ ] Unaligned bullet points

**Spacing Problems**:
- [ ] Cramped content (insufficient white space)
- [ ] Too much empty space (poor use of slide area)
- [ ] Inconsistent spacing between elements
- [ ] Uneven gaps in multi-column layouts
- [ ] Poor distribution of content

#### Color and Contrast

**Visibility**:
- [ ] Insufficient contrast (text vs background)
- [ ] Colors too similar (hard to distinguish)
- [ ] Text on busy backgrounds
- [ ] Light text on light background
- [ ] Dark text on dark background

**Consistency**:
- [ ] Inconsistent color schemes between slides
- [ ] Unexpected color changes
- [ ] Clashing color combinations
- [ ] Poor color choices for data visualization

#### Figures and Graphics

**Quality**:
- [ ] Pixelated or blurry images
- [ ] Low-resolution figures
- [ ] Distorted aspect ratios
- [ ] Poor quality screenshots
- [ ] Jagged edges on graphics

**Layout**:
- [ ] Figures too small to read
- [ ] Axis labels too small
- [ ] Legend text illegible
- [ ] Complex figures without explanation
- [ ] Figures not centered or aligned

#### Technical Issues

**Rendering**:
- [ ] Missing fonts (substituted)
- [ ] Special characters not displaying
- [ ] Equations rendering incorrectly
- [ ] Broken images or missing files
- [ ] Incorrect colors (RGB vs CMYK)

**Consistency**:
- [ ] Slide numbers incorrect or missing
- [ ] Inconsistent footer/header
- [ ] Navigation elements broken
- [ ] Hyperlinks not working (if testing interactively)

## Documentation Template

### Issue Log Format

Create a spreadsheet or document tracking all issues:

```
Slide # | Issue Category | Description | Severity | Status
--------|---------------|-------------|----------|--------
3       | Text Overflow | Bullet point 4 extends beyond box | High | Fixed
7       | Element Overlap | Figure overlaps with caption | High | Fixed
12      | Font Size | Axis labels too small | Medium | Fixed
15      | Alignment | Title not centered | Low | Fixed
22      | Contrast | Yellow text on white background | High | Fixed
```

**Severity Levels**:
- **Critical**: Makes slide unusable or unprofessional
- **High**: Significantly impacts readability or appearance
- **Medium**: Noticeable but doesn't prevent comprehension
- **Low**: Minor cosmetic issues

### Example Issue Documentation

**Good Documentation**:
```
Slide 8: Text Overflow Issue
- Description: Last bullet point "...implementation details" 
  extends ~0.5 inches beyond right margin of text box
- Cause: Bullet text too long for available width
- Fix: Reduce text to "...implementation" or increase box width
- Verification: Check neighboring slides for similar issue
```

**Poor Documentation**:
```
Slide 8: text problem
- Fix: make smaller
```

## Common Issues and Solutions

### Issue 1: Text Overflow

**Problem**: Text extends beyond boundaries

**Identification**:
- Visible text cut off at edge
- Text running into margins
- Partial characters visible

**Solutions**:

**LaTeX Beamer**:
```latex
% Reduce text
\begin{frame}{Title}
  \begin{itemize}
    \item Shorten this long bullet point
    % or
    \item Use abbreviations or acronyms
    % or
    \item<alert@1> Split into multiple bullets
  \end{itemize}
\end{frame}

% Set Beamer margins in the preamble
\setbeamersize{text margin left=8mm,text margin right=8mm}
\begin{frame}
  Content with wider margins
\end{frame}
% Recompile and inspect the resulting frame

% Smaller font for specific element
{\small
  Long text that needs to fit
}
```

**PowerPoint**:
- Reduce font size for that element
- Shorten text content
- Increase text box size
- Use text box auto-fit options (cautiously)
- Split into multiple slides

### Issue 2: Element Overlap

**Problem**: Elements overlapping inappropriately

**Identification**:
- Text obscured by images
- Shapes covering text
- Figures overlapping

**Solutions**:

**LaTeX Beamer**:
```latex
% Use columns for better separation
\begin{columns}
  \begin{column}{0.5\textwidth}
    Text content
  \end{column}
  \begin{column}{0.5\textwidth}
    \includegraphics[width=\textwidth]{figure.pdf}
  \end{column}
\end{columns}

% Add spacing
\vspace{0.5cm}

% Adjust figure size
\includegraphics[width=0.7\textwidth]{figure.pdf}
```

**PowerPoint**:
- Use alignment guides to reposition
- Reduce element sizes
- Use two-column layout
- Send elements backward/forward (layering)
- Increase spacing between elements

### Issue 3: Poor Contrast

**Problem**: Text difficult to read due to color choices

**Identification**:
- Squinting required to read text
- Text fades into background
- Colors too similar

**Solutions**:

**LaTeX Beamer**:
```latex
% Increase contrast
\setbeamercolor{frametitle}{fg=black,bg=white}
\setbeamercolor{normal text}{fg=black,bg=white}

% Use darker colors
\definecolor{darkblue}{RGB}{0,50,100}
\setbeamercolor{structure}{fg=darkblue}

% Test in grayscale
\usepackage{xcolor}
\selectcolormodel{gray}  % Temporarily for testing
```

**PowerPoint**:
- Choose high-contrast color combinations
- Use dark text on light background or vice versa
- Avoid pastels for text
- Test with WebAIM contrast checker
- Add text background box if needed

### Issue 4: Tiny Fonts

**Problem**: Text too small to read from distance

**Identification**:
- Can't read text from 3 feet away
- Axis labels disappear when viewing normally
- Captions illegible

**Solutions**:

**LaTeX Beamer**:
```latex
% Increase base font size
\documentclass[14pt]{beamer}  % Instead of 11pt default

% Recreate figures with larger fonts
% In matplotlib:
plt.rcParams['font.size'] = 18
plt.rcParams['axes.labelsize'] = 20

% In R/ggplot2:
theme_set(theme_minimal(base_size = 16))
```

**PowerPoint**:
- Minimum 18pt for body text, 24pt preferred
- Recreate figures with larger labels
- Use direct labeling instead of legends
- Simplify complex figures
- Split dense content across multiple slides

### Issue 5: Misalignment

**Problem**: Elements not properly aligned

**Identification**:
- Uneven margins
- Titles at different positions
- Irregular spacing

**Solutions**:

**LaTeX Beamer**:
```latex
% Use consistent templates
\setbeamertemplate{frametitle}[default][center]

% Align columns at top
\begin{columns}[T]  % T = top alignment
  \begin{column}{0.5\textwidth}
    Content
  \end{column}
  \begin{column}{0.5\textwidth}
    Content
  \end{column}
\end{columns}

% Center figures
\begin{center}
  \includegraphics[width=0.8\textwidth]{figure.pdf}
\end{center}
```

**PowerPoint**:
- Use alignment tools (Align Left/Center/Right)
- Enable gridlines and guides
- Use snap to grid
- Distribute objects evenly
- Create master slides with consistent layouts

## Iterative Improvement Process

### Workflow Cycle

```
1. Generate PDF
    ↓
2. Convert to images
    ↓
3. Systematic visual inspection
    ↓
4. Document issues
    ↓
5. Prioritize fixes
    ↓
6. Apply corrections to source
    ↓
7. Regenerate PDF
    ↓
8. Re-inspect (go to step 2)
    ↓
9. Complete when no critical issues remain
```

### Prioritization Strategy

**Fix Immediately** (Block presentation):
- Text overflow making content unreadable
- Critical element overlaps obscuring data
- Broken figures or missing content
- Severely poor contrast

**Fix Before Presenting**:
- Font sizes too small
- Moderate alignment issues
- Inconsistent spacing
- Moderate contrast problems

**Fix If Time Permits**:
- Minor misalignments
- Small spacing inconsistencies
- Cosmetic improvements
- Non-critical color adjustments

### Stopping Criteria

**Minimum Standards**:
- [ ] No text overflow or truncation
- [ ] No element overlaps obscuring content
- [ ] All text readable at minimum 18pt equivalent
- [ ] Adequate contrast (4.5:1 ratio minimum)
- [ ] Figures and images display correctly
- [ ] Consistent slide structure

**Ideal Standards**:
- [ ] Professional appearance throughout
- [ ] Consistent alignment and spacing
- [ ] High contrast (7:1 ratio)
- [ ] Optimal font sizes (24pt+)
- [ ] Polished visual design
- [ ] Zero layout issues

## Automated Detection Strategies

### Python Script for Text Overflow Detection

```python
from PIL import Image
import numpy as np

def detect_edge_content(image_path, threshold=10):
    """
    Detect if content extends too close to slide edges.
    Returns True if potential overflow detected.
    """
    img = Image.open(image_path).convert('L')  # Grayscale
    arr = np.array(img)
    
    # Check edges (10 pixel border)
    left_edge = arr[:, :threshold]
    right_edge = arr[:, -threshold:]
    top_edge = arr[:threshold, :]
    bottom_edge = arr[-threshold:, :]
    
    # Look for non-white pixels (content)
    white_threshold = 240
    
    issues = []
    if np.any(left_edge < white_threshold):
        issues.append("Left edge")
    if np.any(right_edge < white_threshold):
        issues.append("Right edge")
    if np.any(top_edge < white_threshold):
        issues.append("Top edge")
    if np.any(bottom_edge < white_threshold):
        issues.append("Bottom edge")
    
    return issues

# Usage
for slide_num in range(1, 26):
    issues = detect_edge_content(f'slide-{slide_num:03d}.jpg')
    if issues:
        print(f"Slide {slide_num}: Content near {', '.join(issues)}")
```

### Contrast Checking

Check each actual foreground/background color pair. Whole-slide bright/dark percentiles
cannot determine text contrast. For sRGB hex colors, use the WCAG relative luminance
formula (normal text >=4.5:1; large text >=3:1). Projection may warrant greater contrast.

```python
def contrast_ratio(foreground, background):
    def luminance(hex_color):
        values = [int(hex_color.lstrip("#")[i:i+2], 16) / 255 for i in (0, 2, 4)]
        linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in values]
        return sum(v * w for v, w in zip(linear, (0.2126, 0.7152, 0.0722)))
    light, dark = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (light + 0.05) / (dark + 0.05)

assert contrast_ratio("#000000", "#FFFFFF") == 21.0
assert contrast_ratio("#FFFFFF", "#FFFFFF") == 1.0
print(contrast_ratio("#003366", "#FFFFFF"))
```

Source: [WCAG 2.2 contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html).
The edge-content example above is an illustrative white-background heuristic;
it flags dark backgrounds and intentional full-bleed images and cannot certify overflow.
Its filenames must match the renderer's zero padding (for example `slide-001.jpg`).

## Manual Review Best Practices

### Review Environment

**Setup**:
- Large monitor or dual monitors
- Good lighting (not too bright, not dark)
- Distraction-free environment
- Image viewer with zoom capability
- Notepad or spreadsheet for tracking issues

**Viewing Options**:
- View at 100% for detail inspection
- View at 50% to simulate distance
- View in sequence to check consistency
- Compare similar slides side-by-side

### Review Tips

**Fresh Eyes**:
- Take breaks every 15-20 slides
- Review at different times of day
- Get colleague to review
- Come back next day for final check

**Systematic Approach**:
- Review in order (slide 1 → end)
- Focus on one issue type at a time
- Use checklist to ensure thoroughness
- Document as you go, not from memory

**Common Oversights**:
- Backup slides (review these too!)
- Title slide (first impression matters)
- Acknowledgments slide (often forgotten)
- Last slide (visible during Q&A)

## Tools and Resources

### Recommended Software

**PDF to Image Conversion**:
- **PyMuPDF** (Python): Fast, no external dependencies (recommended)
- **pdf_to_images.py script**: Wrapper for easy CLI usage
- **ImageMagick**: Flexible, many options (optional)

**Image Viewing**:
- **IrfanView** (Windows): Fast, many formats
- **Preview** (macOS): Built-in, simple
- **Eye of GNOME** (Linux): Lightweight
- **XnView**: Cross-platform, batch operations

**Issue Tracking**:
- **Spreadsheet** (Excel, Google Sheets): Simple, flexible
- **Markdown file**: Version control friendly
- **Issue tracker** (GitHub, Jira): If team collaboration
- **Checklist app**: For mobile review

### Contrast Checkers

- **WebAIM Contrast Checker**: https://webaim.org/resources/contrastchecker/
- **Colour Contrast Analyser**: Desktop application
- **Chrome DevTools**: Built-in contrast checking

### Color Blindness Simulators

- **Coblis**: https://www.color-blindness.com/coblis-color-blindness-simulator/
- **Color Oracle**: Free desktop application
- **Photoshop/GIMP**: Built-in color blindness filters

## Summary Checklist

Before finalizing your presentation:

**Conversion**:
- [ ] PDF converted to images at adequate resolution (150-300 DPI)
- [ ] All slides converted (including backup slides)
- [ ] Images saved in organized directory

**Visual Inspection**:
- [ ] All slides reviewed systematically
- [ ] Issue checklist completed for each slide
- [ ] Problems documented with slide numbers
- [ ] Severity assigned to each issue

**Issue Resolution**:
- [ ] Critical issues fixed
- [ ] High-priority issues addressed
- [ ] Source files updated (not just PDF)
- [ ] Regenerated and re-inspected

**Final Verification**:
- [ ] No text overflow or truncation
- [ ] No inappropriate element overlaps
- [ ] Adequate contrast throughout
- [ ] Consistent layout and spacing
- [ ] Professional appearance
- [ ] Ready for projection or distribution

**Testing**:
- [ ] Tested on projector if possible
- [ ] Viewed from back of room distance
- [ ] Checked in various lighting conditions
- [ ] Backup copy saved
