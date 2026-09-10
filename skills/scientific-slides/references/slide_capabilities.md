# Slide Capabilities

Presentation structure, design principles, data visualization for slides, talk-specific
guidance, implementation options, visual review and iteration, timing and pacing, and
validation and quality assurance.

## Core Capabilities

### 1. Presentation Structure and Organization

Build presentations with clear narrative flow and appropriate structure for different contexts. For detailed guidance, refer to `references/presentation_structure.md`.

**Universal Story Arc**:
1. **Hook**: Grab attention (30-60 seconds)
2. **Context**: Establish importance (5-10% of talk)
3. **Problem/Gap**: Identify what's unknown (5-10% of talk)
4. **Approach**: Explain your solution (15-25% of talk)
5. **Results**: Present key findings (40-50% of talk)
6. **Implications**: Discuss meaning (15-20% of talk)
7. **Closure**: Memorable conclusion (1-2 minutes)

**Talk-Specific Structures**:
- **Conference talks (15 min)**: Focused on 1-2 key findings, minimal methods
- **Academic seminars (45 min)**: Comprehensive coverage, detailed methods, multiple studies
- **Thesis defenses (60 min)**: Complete dissertation overview, all studies covered
- **Grant pitches (15 min)**: Emphasis on significance, feasibility, and impact
- **Journal clubs (30 min)**: Critical analysis of published work

### 2. Slide Design Principles

Create professional, readable, and accessible slides that enhance understanding. For complete design guidelines, refer to `references/slide_design_principles.md`.

**ANTI-PATTERN: Avoid Dry, Text-Heavy Presentations**

❌ **What Makes Presentations Dry and Forgettable:**
- Walls of text (more than 6 bullets per slide)
- Small fonts (<24pt body text)
- Black text on white background only (no visual interest)
- No images or graphics (bullet points only)
- Generic templates with no customization
- Dense, paragraph-like bullet points
- Missing research context (no citations)
- All slides look the same (repetitive)

✅ **What Makes Presentations Engaging and Memorable:**
- HIGH-QUALITY VISUALS dominate (figures, photos, diagrams, icons)
- Large, clear text as accent (not the main content)
- Modern, purposeful color schemes (not default themes)
- Generous white space (slides breathe)
- Research-backed context (proper citations from research-lookup)
- Variety in slide layouts (not all bullet lists)
- Story-driven flow with visual anchors
- Professional, polished appearance

**Core Design Principles**:

**Visual-First Approach** (CRITICAL):
- Start with visuals (figures, images, diagrams), add text as support
- Every slide should have STRONG visual element (figure, chart, photo, diagram)
- Text explains or complements visuals, not replaces them
- Think: "How can I show this, not just tell it?"
- Target: 60-70% visual content, 30-40% text

**Simplicity with Impact**:
- One main idea per slide
- MINIMAL text (3-4 bullets, 4-6 words each preferred)
- Generous white space (40-50% of slide)
- Clear visual focus
- Bold, confident design choices

**Typography for Engagement**:
- Sans-serif fonts (Arial, Calibri, Helvetica)
- LARGE fonts: 24-28pt for body text (not minimum 18pt)
- 36-44pt for slide titles (make bold)
- High contrast (minimum 4.5:1, prefer 7:1)
- Use size for hierarchy, not just weight

**Color for Impact**:
- MODERN color palettes (not default blue/gray)
- Consider your topic: biotech? vibrant colors. Physics? sleek darks. Health? warm tones.
- Limited palette (3-5 colors total)
- High contrast combinations
- Color-blind safe (avoid red-green combinations)
- Use color purposefully (not decoration)

**Layout for Visual Interest**:
- Vary layouts (not all bullet lists)
- Use two-column layouts (text + figure)
- Full-slide figures for key results
- Asymmetric compositions (more interesting than centered)
- Rule of thirds for focal points
- Consistent but not repetitive

### 3. Data Visualization for Slides

Adapt scientific figures for presentation context. For detailed guidance, refer to `references/data_visualization_slides.md`.

**Key Differences from Journal Figures**:
- Simplify, don't replicate
- Larger fonts (18-24pt minimum)
- Fewer panels (split across slides)
- Direct labeling (not legends)
- Emphasis through color and size
- Progressive disclosure for complex data

**Visualization Best Practices**:
- **Bar charts**: Comparing discrete categories
- **Line graphs**: Trends and trajectories
- **Scatter plots**: Relationships and correlations
- **Heatmaps**: Matrix data and patterns
- **Network diagrams**: Relationships and connections

**Common Mistakes to Avoid**:
- Tiny fonts (<18pt)
- Too many panels on one slide
- Complex legends
- Insufficient contrast
- Cluttered layouts

### 4. Talk-Specific Guidance

Different presentation contexts require different approaches. For comprehensive guidance on each type, refer to `references/talk_types_guide.md`.

**Conference Talks** (10-20 minutes):
- Structure: Brief intro → minimal methods → key results → quick conclusion
- Focus: 1-2 main findings only
- Style: Engaging, fast-paced, memorable
- Goal: Generate interest, network, get invited

**Academic Seminars** (45-60 minutes):
- Structure: Comprehensive coverage with detailed methods
- Focus: Multiple findings, depth of analysis
- Style: Scholarly, interactive, discussion-oriented
- Goal: Demonstrate expertise, get feedback, collaborate

**Thesis Defenses** (45-60 minutes):
- Structure: Complete dissertation overview, all studies
- Focus: Demonstrating mastery and independent thinking
- Style: Formal, comprehensive, prepared for interrogation
- Goal: Pass examination, defend research decisions

**Grant Pitches** (10-20 minutes):
- Structure: Problem → significance → approach → feasibility → impact
- Focus: Innovation, preliminary data, team qualifications
- Style: Persuasive, focused on outcomes and impact
- Goal: Secure funding, demonstrate viability

**Journal Clubs** (20-45 minutes):
- Structure: Context → methods → results → critical analysis
- Focus: Understanding and critiquing published work
- Style: Educational, critical, discussion-facilitating
- Goal: Learn, critique, discuss implications

### 5. Implementation Options

#### Nano Banana Pro PDF (Default - Recommended)

**Best for**: Visually stunning slides, fast creation, non-technical audiences

**This is the default and recommended approach.** Generate each slide as a complete image using AI.

**Workflow**:
1. Plan each slide (title, content, visual elements)
2. Generate each slide with `generate_slide_image.py`
3. Combine into PDF with `slides_to_pdf.py`

```bash
# Generate slides
python scripts/generate_slide_image.py "Title: Introduction..." -o slides/01.png
python scripts/generate_slide_image.py "Title: Methods..." -o slides/02.png

# Combine to PDF
python scripts/slides_to_pdf.py slides/*.png -o presentation.pdf
```

**Advantages**:
- Most visually impressive results
- Fast creation (describe and generate)
- No design skills required
- Consistent, professional appearance
- Perfect for general audiences

**Best for**:
- Conference talks
- Business presentations
- General scientific talks
- Pitch presentations

#### PowerPoint via PPTX Skill

**Best for**: Editable slides, custom designs, template-based workflows

**Reference**: See `skills/pptx/SKILL.md` for complete documentation

Use Nano Banana Pro with `--visual-only` to generate images, then build PPTX with text.

**Key Resources**:
- `assets/powerpoint_design_guide.md`: Complete PowerPoint design guide
- PPTX skill's `SKILL.md`: Programmatic creation with PptxGenJS, plus template editing
- PPTX skill's scripts: `thumbnail.py`, `add_slide.py`, `clean.py`, `office/validate.py`

**Workflow**:
1. Generate visuals with `generate_slide_image.py --visual-only`
2. Author slides with PptxGenJS (for programmatic) or use templates
3. Create presentation using PptxGenJS or template editing
4. Add generated images and text content
5. Generate thumbnails for visual validation
6. Iterate based on visual inspection

**Advantages**:
- Editable slides (can modify text later)
- Complex animations and transitions
- Interactive elements
- Company template compatibility

#### LaTeX Beamer

**Best for**: Mathematical content, consistent formatting, version control

**Reference**: See `references/beamer_guide.md` for complete documentation

**Templates Available**:
- `assets/beamer_template_conference.tex`: 15-minute conference talk
- `assets/beamer_template_seminar.tex`: 45-minute academic seminar
- `assets/beamer_template_defense.tex`: Dissertation defense

**Workflow**:
1. Choose appropriate template
2. Customize theme and colors
3. Add content (LaTeX native: equations, code, algorithms)
4. Compile to PDF
5. Convert to images for visual validation

**Advantages**:
- Beautiful mathematics and equations
- Consistent, professional appearance
- Version control friendly (plain text)
- Excellent for algorithms and code
- Reproducible and programmatic

### 6. Visual Review and Iteration

Implement iterative improvement through visual inspection. For complete workflow, refer to `references/visual_review_workflow.md`.

**Visual Validation Workflow**:

**Step 1: Generate PDF** (if not already PDF)
- PowerPoint: Export as PDF
- Beamer: Compile LaTeX source

**Step 2: Convert to Images**
```bash
# Using the pdf_to_images script
python scripts/pdf_to_images.py presentation.pdf review/slide --dpi 150

# Or use pptx skill's thumbnail tool
python skills/pptx/scripts/thumbnail.py presentation.pptx review/thumb
```

**Step 3: Systematic Inspection**

Check each slide for:
- **Text overflow**: Text cut off at edges
- **Element overlap**: Text overlapping images or other text
- **Font sizes**: Text too small (<18pt)
- **Contrast**: Insufficient contrast between text and background
- **Layout issues**: Misalignment, poor spacing
- **Visual quality**: Pixelated images, poor rendering

**Step 4: Document Issues**

Create issue log:
```
Slide # | Issue Type | Description | Priority
--------|-----------|-------------|----------
3       | Text overflow | Bullet 4 extends beyond box | High
7       | Overlap | Figure overlaps with caption | High
12      | Font size | Axis labels too small | Medium
```

**Step 5: Apply Fixes**

Make corrections to source files:
- PowerPoint: Edit text boxes, resize elements
- Beamer: Adjust LaTeX code, recompile

**Step 6: Re-Validate**

Repeat Steps 1-5 until no critical issues remain.

**Stopping Criteria**:
- No text overflow
- No inappropriate overlaps
- All text readable (≥18pt equivalent)
- Adequate contrast (≥4.5:1)
- Professional appearance

### 7. Timing and Pacing

Ensure presentations fit allocated time. For comprehensive timing guidance, refer to `assets/timing_guidelines.md`.

**The One-Slide-Per-Minute Rule**:
- General guideline: ~1 slide per minute
- Adjust for complex slides (2-3 minutes)
- Adjust for simple slides (15-30 seconds)

**Time Allocation**:
- Introduction: 15-20%
- Methods: 15-20%
- Results: 40-50% (MOST TIME)
- Discussion: 15-20%
- Conclusion: 5%

**Practice Requirements**:
- 5-minute talk: Practice 5-7 times
- 15-minute talk: Practice 3-5 times
- 45-minute talk: Practice 3-4 times
- Defense: Practice 4-6 times

**Timing Checkpoints**:

For 15-minute talk:
- 3-4 minutes: Finishing introduction
- 7-8 minutes: Halfway through results
- 12-13 minutes: Starting conclusions

**Emergency Strategies**:
- Running behind: Skip backup slides (prepare in advance)
- Running ahead: Expand examples, slow slightly
- Never skip conclusions

### 8. Validation and Quality Assurance

**Automated Validation**:
```bash
# Validate slide count, timing, file size
python scripts/validate_presentation.py presentation.pdf --duration 15

# Generates report on:
# - Slide count vs. recommended range
# - File size warnings
# - Slide dimensions
# - Font size issues (PowerPoint)
# - Compilation success (Beamer)
```

**Manual Validation Checklist**:
- [ ] Slide count appropriate for duration
- [ ] Title slide complete (name, affiliation, date)
- [ ] Clear narrative flow
- [ ] One main idea per slide
- [ ] Font sizes ≥18pt (preferably 24pt+)
- [ ] High contrast colors
- [ ] Figures large and readable
- [ ] No text overflow or element overlap
- [ ] Consistent design throughout
- [ ] Slide numbers present
- [ ] Contact info on final slide
- [ ] Backup slides prepared
- [ ] Tested on projector (if possible)
