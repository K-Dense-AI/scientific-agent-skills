# Research Poster Design Principles

Reviewed 2026-09-30. Design numbers are starting points, not measured guarantees.
Code fragments are illustrative; use the bundled tested templates as the executable
starting point. Replace example names, statistics, citations, URLs, and assets with
verified project content.

## Overview

Effective poster design balances visual appeal, readability, and scientific content. This guide covers typography, color theory, visual hierarchy, accessibility, and practical design starting points for research posters.

## Core Design Principles

### 1. Visual Hierarchy

Guide viewers through content in logical order using size, color, position, and contrast.

**Hierarchy Levels**:

1. **Primary (Title)**: Largest, most prominent
   - Size: 72-120pt
   - Position: Top center or top spanning
   - Weight: Bold
   - Purpose: Capture attention from 20+ feet

2. **Secondary (Section Headers)**: Organize content
   - Size: 48-72pt
   - Weight: Bold or semi-bold
   - Purpose: Section navigation, readable from 10 feet

3. **Tertiary (Body Text)**: Main content
   - Size: 24-36pt minimum
   - Weight: Regular
   - Purpose: Detailed information, readable from 4-6 feet

4. **Quaternary (Captions, References)**: Supporting info
   - Size: 18-24pt
   - Weight: Regular or light
   - Purpose: Context and attribution

**Implementation**:
```latex
% Illustrative Beamer font settings; sizes depend on class and poster scale.
\setbeamerfont{title}{size=\VeryHuge,series=\bfseries}
\setbeamerfont{block title}{size=\Huge,series=\bfseries}
\setbeamerfont{block body}{size=\LARGE}
\setbeamerfont{caption}{size=\large}
```

### 2. White Space (Negative Space)

Empty space is not wasted space—it enhances readability and guides attention.

**White Space Functions**:
- **Breathing room**: Prevents overwhelming viewers
- **Grouping**: Shows which elements belong together
- **Focus**: Draws attention to important elements
- **Flow**: Creates visual pathways through content

**Guidelines**:
- Keep a safe margin required by the printer, then choose padding for readability
- Consistent spacing between blocks (1-2cm)
- Space around figures equal to or greater than border width
- Group related items closely, separate unrelated items
- Don't fill every inch—aim for 40-60% text coverage

**LaTeX Implementation**:
```latex
% beamerposter spacing
\setbeamertemplate{block begin}{
  \vskip2ex  % Space before block
  ...
}

% tikzposter spacing
\documentclass[..., blockverticalspace=15mm, colspace=15mm]{tikzposter}

% Manual spacing
\vspace{2cm}  % Vertical space
\hspace{1cm}  % Horizontal space
```

### 3. Alignment and Grid Systems

Proper alignment creates professional, organized appearance.

**Alignment Types**:
- **Left-aligned text**: Most readable for body text (Western audiences)
- **Center-aligned**: Headers, titles, symmetric layouts
- **Right-aligned**: Rarely used, special cases only
- **Justified**: Avoid (creates uneven spacing)

**Grid Systems**:
- **2-column**: Simple, traditional, good for narrative flow
- **3-column**: Most common, balanced, versatile
- **4-column**: Complex, information-dense, requires careful design
- **Asymmetric**: Creative, modern, requires expertise

**Best Practices**:
- Align block edges to invisible grid lines
- Keep consistent column widths (unless intentionally asymmetric)
- Align similar elements (all figures, all text blocks)
- Use consistent margins throughout

### 4. Visual Flow and Reading Patterns

Design for natural eye movement and logical content progression.

**Common Reading Patterns**:

**Z-Pattern (Landscape posters)**:
```
Start → → → Top Right
  ↓
Middle Left → → Middle
  ↓
Bottom Left → → → End
```

**F-Pattern (Portrait posters)**:
```
Title → → → →
↓
Section 1 → →
↓
Section 2 → →
↓
Section 3 → →
↓
Conclusion → →
```

**Gutenberg Diagram**:
```
Primary Area     Strong Fallow
(top-left)       (top-right)
        ↓              ↓
Weak Fallow      Terminal Area
(bottom-left)    (bottom-right)
```

**Implementation Strategy**:
1. Place most important content in "hot zones" (top-left, center)
2. Create visual paths with arrows, lines, or color
3. Use numbering for sequential information (Methods steps)
4. Design left-to-right, top-to-bottom flow (Western audiences)
5. Position conclusions prominently (bottom-right is natural endpoint)

## Typography

### Font Selection

**Recommended Fonts**:

**Sans-Serif (Recommended for posters)**:
- **Helvetica**: Clean, professional, widely available
- **Arial**: Similar to Helvetica, universal compatibility
- **Calibri**: Modern, friendly, good readability
- **Open Sans**: Contemporary, excellent web and print
- **Roboto**: Modern, Google design, highly readable
- **Lato**: Warm, professional, works at all sizes

**Serif (Use sparingly)**:
- **Times New Roman**: Traditional, formal
- **Garamond**: Elegant, good for humanities
- **Georgia**: Designed for screens, readable

**Avoid**:
- ❌ Comic Sans (unprofessional)
- ❌ Decorative or script fonts (illegible from distance)
- ❌ Mixing more than 2-3 font families

**LaTeX Implementation**:
```latex
% Helvetica (sans-serif)
\usepackage{helvet}
\renewcommand{\familydefault}{\sfdefault}

% Avant Garde (not Arial)
\usepackage{avant}
\renewcommand{\familydefault}{\sfdefault}

% Modern fonts with fontspec (requires LuaLaTeX/XeLaTeX)
\usepackage{fontspec}
\setmainfont{Helvetica Neue}
\setsansfont{Open Sans}
```

### Font Sizing

**Absolute Minimum Sizes** (readable from 4-6 feet):
- Title: 72pt+ (85-120pt recommended)
- Section headers: 48-72pt
- Body text: 24-36pt (30pt+ recommended)
- Captions/small text: 18-24pt
- References: 16-20pt minimum

**Testing Readability**:
- Print at 25% scale
- Read from 2-3 feet distance
- If legible, full-scale poster will be readable from 8-12 feet

**Font commands are class-dependent.** `\Large`, `\Huge`, and related commands
change with the document class and poster scale; there is no universal point-size
conversion table. `\VeryHuge` is provided by beamerposter, not ordinary LaTeX.
For explicit control, use `\fontsize{30}{36}\selectfont` in the appropriate scope
and verify the rendered PDF at final size.

### Text Formatting Best Practices

**Use**:
- ✅ **Bold** for emphasis and headers
- ✅ Short paragraphs (3-5 lines maximum)
- ✅ Bullet points for lists
- ✅ Adequate line spacing (1.2-1.5)
- ✅ High contrast (dark text on light background)

**Avoid**:
- ❌ Italics from distance (hard to read)
- ❌ ALL CAPS FOR LONG TEXT (SLOW TO READ)
- ❌ Underlines (old-fashioned, interferes with descenders)
- ❌ Long paragraphs (> 6 lines)
- ❌ Light text on light backgrounds

**Line Spacing**:
```latex
% Increase line spacing for readability
\usepackage{setspace}
\setstretch{1.3}  % 1.3x normal spacing

% Or in specific blocks
\begin{spacing}{1.5}
  Your text here with extra spacing
\end{spacing}
```

## Color Theory for Posters

### Color Psychology and Meaning

Colors convey meaning and affect viewer perception:

| Color | Associations | Use Cases |
|-------|--------------|-----------|
| **Blue** | Trust, professionalism, science | Academic, medical, technology |
| **Green** | Nature, health, growth | Environmental, biology, health |
| **Red** | Energy, urgency, passion | Attention, warnings, bold statements |
| **Orange** | Creativity, enthusiasm | Innovative research, friendly approach |
| **Purple** | Wisdom, creativity, luxury | Humanities, arts, premium research |
| **Gray** | Neutral, professional, modern | Technology, minimal designs |
| **Yellow** | Optimism, attention, caution | Highlights, energy, caution areas |

### Color Scheme Types

**1. Monochromatic**: Variations of single hue
- **Pros**: Harmonious, professional, easy to execute
- **Cons**: Can be boring, less visual interest
- **Use**: Conservative conferences, institutional branding

```latex
% Monochromatic blue scheme
\definecolor{darkblue}{RGB}{0,51,102}
\definecolor{medblue}{RGB}{51,102,153}
\definecolor{lightblue}{RGB}{204,229,255}
```

**2. Analogous**: Adjacent colors on color wheel
- **Pros**: Harmonious, visually comfortable
- **Cons**: Low contrast, may lack excitement
- **Use**: Nature/biology topics, smooth gradients

```latex
% Analogous blue-green scheme
\definecolor{blue}{RGB}{0,102,204}
\definecolor{teal}{RGB}{0,153,153}
\definecolor{green}{RGB}{51,153,102}
```

**3. Complementary**: Opposite colors on wheel
- **Pros**: High contrast, vibrant, energetic
- **Cons**: Can be overwhelming if intense
- **Use**: Drawing attention, modern designs

```latex
% Complementary blue-orange scheme
\definecolor{primary}{RGB}{0,71,171}     % Blue
\definecolor{accent}{RGB}{255,127,0}     % Orange
```

**4. Triadic**: Three evenly spaced colors
- **Pros**: Balanced, vibrant, visually rich
- **Cons**: Can appear busy if not balanced
- **Use**: Multi-topic posters, creative fields

```latex
% Triadic scheme
\definecolor{blue}{RGB}{0,102,204}
\definecolor{red}{RGB}{204,0,51}
\definecolor{yellow}{RGB}{255,204,0}
```

**5. Split-Complementary**: Base + two adjacent to complement
- **Pros**: High contrast but less tense than complementary
- **Cons**: Complex to balance
- **Use**: Sophisticated designs, experienced designers

### High-Contrast Combinations

Ensure readability with sufficient contrast:

**Excellent Contrast (Use these)**:
- Dark blue on white
- Black on white
- White on dark blue/green/purple
- Dark gray on light yellow
- Black on light cyan

**Poor Contrast (Avoid)**:
- ❌ Red on green (color-blind issue)
- ❌ Yellow on white
- ❌ Light gray on white
- ❌ Blue on black (hard to read)
- ❌ Any pure colors on each other

**Conservative Contrast Targets**:
- Aim for at least 4.5:1 for text, with 7:1 where practical
- WCAG AA permits 3:1 for large text; print conditions also need evaluation
- Test at: https://webaim.org/resources/contrastchecker/

**LaTeX Color Contrast**:
```latex
% High contrast header
\setbeamercolor{block title}{bg=black, fg=white}

% Medium contrast body
\setbeamercolor{block body}{bg=gray!10, fg=black}

% Check contrast manually or use online tools
```

### Color-Blind Friendly Palettes

Color-vision differences vary across people and populations; test distinctions with redundant encoding.

**Safe Color Combinations**:
- Blue + Orange (most universally distinguishable)
- Blue + Yellow
- Blue + Red
- Purple + Green (use with caution)

**Avoid**:
- ❌ Red + Green (indistinguishable to most common color blindness)
- ❌ Green + Brown
- ❌ Blue + Purple (can be problematic)
- ❌ Light green + Yellow

**Recommended Palettes**:

**Okabe-Ito Palette** (use redundant shapes/labels as well):
```latex
\definecolor{okorange}{RGB}{230,159,0}
\definecolor{okskyblue}{RGB}{86,180,233}
\definecolor{okgreen}{RGB}{0,158,115}
\definecolor{okyellow}{RGB}{240,228,66}
\definecolor{okblue}{RGB}{0,114,178}
\definecolor{okvermillion}{RGB}{213,94,0}
\definecolor{okpurple}{RGB}{204,121,167}
```

**Paul Tol's Bright Palette**:
```latex
\definecolor{tolblue}{RGB}{68,119,170}
\definecolor{tolred}{RGB}{204,102,119}
\definecolor{tolgreen}{RGB}{34,136,51}
\definecolor{tolyellow}{RGB}{238,221,136}
\definecolor{tolcyan}{RGB}{102,204,238}
```

### Institutional Branding

Obtain current colors and logo assets from the institution's official brand guide.
Do not infer official identity from an example palette or regenerate a logo with AI.
Use xcolor RGB/HTML/CMYK values as specified by that guide and the printer.

## Accessibility Considerations

### Universal Design Principles

Design posters usable by the widest range of people:

**1. Visual Accessibility**:
- High contrast text (minimum 4.5:1 ratio)
- Large font sizes (24pt+ body text)
- Color-blind safe palettes
- Clear visual hierarchy
- Avoid relying solely on color to convey information

**2. Cognitive Accessibility**:
- Clear, simple language
- Logical organization
- Consistent layout
- Visual cues for navigation (arrows, numbers)
- Avoid clutter and information overload

**3. Physical Accessibility**:
- Position critical content at wheelchair-accessible height (3-5 feet)
- Include QR codes to digital versions
- Provide printed handouts for detail viewing
- Consider lighting and reflection in poster material choice

### Alternative Text and Descriptions

A visible caption is useful but does not create a tagged PDF or figure alternative
text. [CTAN currently marks beamerposter tagging unsupported](https://ctan.org/pkg/beamerposter).
Do not claim accessible PDF conformance from successful compilation or a comment
beside `\includegraphics`. Inspect reading order/tags using appropriate validators;
provide a separate accessible text/HTML summary when the chosen class cannot meet
the accessibility requirement.

### Multi-Modal Information

Don't rely on single sensory channel:

**Use Redundant Encoding**:
- Color + Shape (not just color for categories)
- Color + Pattern (hatching, stippling)
- Color + Label (text labels on graph elements)
- Text + Icons (visual + verbal)

**Example**:
```latex
% Good: Color + shape + label
\begin{tikzpicture}
  \draw[fill=blue, circle] (0,0) circle (0.3) node[right] {Male: 45\%};
  \draw[fill=red, rectangle] (0,-1) rectangle (0.6,-0.4) node[right] {Female: 55\%};
\end{tikzpicture}
```

## Layout Composition

### Rule of Thirds

Divide poster into 3×3 grid; place key elements at intersections:

```
+-----+-----+-----+
|  ×  |     |  ×  |  ← Top third (title, logos)
+-----+-----+-----+
|     |  ×  |     |  ← Middle third (main content)
+-----+-----+-----+
|  ×  |     |  ×  |  ← Bottom third (conclusions)
+-----+-----+-----+
  ↑           ↑
Left        Right
```

**Power Points** (intersections):
- Top-left: Primary section start
- Top-right: Logos, QR codes
- Center: Key figure or main result
- Bottom-right: Conclusions, contact

### Balance and Symmetry

**Symmetric Layouts**:
- Formal, traditional, stable
- Easy to design
- Can appear static or boring
- Good for conservative audiences

**Asymmetric Layouts**:
- Dynamic, modern, interesting
- Harder to execute well
- More visually engaging
- Good for creative fields

**Visual Weight Balance**:
- Large elements = heavy weight
- Dark colors = heavy weight
- Dense text = heavy weight
- Distribute weight evenly across poster

### Proximity and Grouping

**Gestalt Principles**:

**Proximity**: Items close together are perceived as related
```
[Introduction]  [Methods]

[Results]       [Discussion]
```

**Similarity**: Similar items are perceived as grouped
- Use consistent colors for related sections
- Same border styles for similar content types

**Continuity**: Eyes follow lines and paths
- Use arrows to guide through methods
- Align elements to create invisible lines

**Closure**: Mind completes incomplete shapes
- Use partial borders to group without boxing in

## Visual Elements

### Icons and Graphics

Strategic use of icons enhances comprehension:

**Benefits**:
- Universal language (crosses linguistic barriers)
- Faster processing than text
- Adds visual interest
- Clarifies concepts

**Best Practices**:
- Use consistent style (all line, all filled, all flat)
- Appropriate size (1-3cm typical)
- Label ambiguous icons
- Source: Font Awesome, Noun Project, academic icon sets

**LaTeX Implementation**:
```latex
% Font Awesome icons
\usepackage{fontawesome5}
\faFlask{} Methods \quad \faChartBar{} Results

% Custom icons with TikZ
\begin{tikzpicture}
  \node[circle, draw, thick, minimum size=1cm] {\Huge \faAtom};
\end{tikzpicture}
```

### Borders and Dividers

**Use Borders To**:
- Define sections
- Group related content
- Add visual interest
- Match institutional branding

**Border Styles**:
- Solid lines: Traditional, formal
- Dashed lines: Informal, secondary info
- Rounded corners: Friendly, modern
- Drop shadows: Depth, modern (use sparingly)

**Guidelines**:
- Keep consistent width (2-5pt typical)
- Use sparingly (not every element needs a border)
- Match border color to content or theme
- Ensure sufficient padding inside borders

```latex
% tikzposter borders
\usecolorstyle{Denmark}
\tikzposterlatexaffectionproofoff  % Remove bottom-right logo

% Custom border style
\defineblockstyle{CustomBlock}{
  titlewidthscale=1, bodywidthscale=1, titleleft,
  titleoffsetx=0pt, titleoffsety=0pt, bodyoffsetx=0pt, bodyoffsety=0pt,
  bodyverticalshift=0pt, roundedcorners=10, linewidth=2pt,
  titleinnersep=8mm, bodyinnersep=8mm
}{
  \draw[draw=blocktitlebgcolor, fill=blockbodybgcolor, 
        rounded corners=\blockroundedcorners, line width=\blocklinewidth]
       (blockbody.south west) rectangle (blocktitle.north east);
}
```

### Background and Texture

**Background Options**:

**Plain (Recommended)**:
- White or very light color
- Maximum readability
- Professional
- Print-friendly

**Gradient**:
- Subtle gradients acceptable
- Top-to-bottom or radial
- Avoid strong contrasts that interfere with text

**Textured**:
- Very subtle textures only
- Watermarks of logos/molecules (5-10% opacity)
- Avoid patterns that create visual noise

**Avoid**:
- ❌ Busy backgrounds
- ❌ Images behind text
- ❌ High contrast backgrounds
- ❌ Repeating patterns that cause visual artifacts

```latex
% Gradient background in tikzposter
\documentclass{tikzposter}
\definecolorstyle{GradientStyle}{
  % ...color definitions...
}{
  \colorlet{backgroundcolor}{white!90!blue}
  \colorlet{framecolor}{white!70!blue}
}

% Watermark
\usepackage{tikz}
\usepackage{eso-pic}
\AddToShipoutPictureBG{%
  \begin{tikzpicture}[remember picture,overlay]
    \node[opacity=0.05] at (current page.center)
      {\includegraphics[width=0.5\paperwidth]{university-seal.pdf}};
  \end{tikzpicture}%
}
```

## Common Design Mistakes

### Critical Errors

**1. Too Much Text** (Most common mistake)
- ❌ More than 1000 words
- ❌ Long paragraphs (>5 lines)
- ❌ Small font sizes to fit more content
- ✅ Solution: Cut ruthlessly, use bullet points, focus on key messages

**2. Poor Contrast**
- ❌ Light text on light background
- ❌ Colored text on colored background
- ✅ Solution: Dark on light or light on dark, test contrast ratio

**3. Font Size Too Small**
- ❌ Body text under 24pt
- ❌ Trying to fit full paper content
- ✅ Solution: 30pt+ body text, prioritize key findings

**4. Cluttered Layout**
- ❌ No white space
- ❌ Elements touching edges
- ❌ Random placement
- ✅ Solution: Generous margins, grid alignment, intentional white space

**5. Inconsistent Styling**
- ❌ Multiple font families
- ❌ Varying header styles
- ❌ Misaligned elements
- ✅ Solution: Define style guide, use templates, align to grid

### Moderate Issues

**6. Poor Figure Quality**
- ❌ Pixelated images (<300 DPI)
- ❌ Tiny axis labels
- ❌ Unreadable legends
- ✅ Solution: Vector graphics (PDF (convert SVG first)), large labels, clear legends

**7. Color Overload**
- ❌ Too many colors (>5 distinct hues)
- ❌ Neon or overly saturated colors
- ✅ Solution: Limit to 2-3 main colors, use tints/shades for variation

**8. Ignoring Visual Hierarchy**
- ❌ All text same size
- ❌ No clear entry point
- ✅ Solution: Vary sizes significantly, clear title, visual flow

**9. Information Overload**
- ❌ Trying to show everything
- ❌ Too many figures
- ✅ Solution: Show 3-5 key results, link to full paper via QR code

**10. Poor Typography**
- ❌ Justified text (uneven spacing)
- ❌ All caps body text
- ❌ Mixing serif and sans-serif randomly
- ✅ Solution: Left-align body, sentence case, consistent fonts

## Design Checklist

### Before Printing

- [ ] Title visible and readable from 20+ feet
- [ ] Body text minimum 24pt, ideally 30pt+
- [ ] High contrast (4.5:1 minimum) throughout
- [ ] Color-blind friendly palette
- [ ] Less than 800 words total
- [ ] White space around all elements
- [ ] Consistent alignment and spacing
- [ ] All figures high resolution (300+ DPI)
- [ ] Figure labels readable (18pt+ minimum)
- [ ] No orphaned text or awkward breaks
- [ ] Contact information included
- [ ] QR codes tested and functional
- [ ] Consistent font usage (2-3 families max)
- [ ] All acronyms defined
- [ ] Proper institutional branding/logos
- [ ] Print test at 25% scale for readability check

### Content Review

- [ ] Clear narrative arc (problem → approach → findings → impact)
- [ ] 1-3 main messages clearly communicated
- [ ] Methods concise but reproducible
- [ ] Results visually presented (not just text)
- [ ] Conclusions actionable and clear
- [ ] References cited appropriately
- [ ] No typos or grammatical errors
- [ ] Figures have descriptive captions
- [ ] Data visualizations are clear and honest
- [ ] Statistical significance properly indicated

## Validate design with readers

Treat word budgets, column counts, and viewing distances as starting assumptions.
Test the actual poster with representative readers: can they identify the question,
main result, uncertainty, and limitations? Do not attach numerical claims about
processing speed, recall, comprehension, or engagement without primary evidence.

For digital contrast targets, [WCAG 2.2 SC 1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
sets 4.5:1 for ordinary text and 3:1 for large text. These web criteria inform the
palette; a printed proof is still required for lighting, paper, and color shifts.
Meeting contrast alone does not establish WCAG or PDF accessibility conformance.

## Resources and Tools

### Color Tools
- **Coolors.co**: Generate color palettes
- **Adobe Color**: Color wheel and accessibility checker
- **ColorBrewer**: Scientific visualization palettes
- **WebAIM Contrast Checker**: Test contrast ratios

### Design Resources
- **Canva**: Poster mockups and inspiration
- **Figma**: Design prototypes before LaTeX
- **Noun Project**: Icons and graphics
- **Font Awesome**: Icon fonts for LaTeX

### Testing Tools
- **Coblis**: Color blindness simulator
- **Vischeck**: Another color blindness checker
- **Accessibility Checker**: WCAG compliance

### LaTeX Packages
- `xcolor`: Extended color support
- `tcolorbox`: Colored boxes and frames
- `fontawesome5`: Icon fonts
- `qrcode`: QR code generation
- `tikz`: Custom graphics

## Conclusion

Effective poster design requires balancing aesthetics, readability, and scientific content. Follow these core principles:

1. **Less is more**: Prioritize key messages over comprehensive detail
2. **Size matters**: Make text large enough to read from distance
3. **Contrast is critical**: Ensure all text is highly readable
4. **Accessibility first**: Design for diverse audiences
5. **Visual hierarchy**: Guide viewers through content logically
6. **Test early**: Print at reduced scale and gather feedback

Remember: A poster is an advertisement for your research and a conversation starter—not a substitute for reading the full paper.

