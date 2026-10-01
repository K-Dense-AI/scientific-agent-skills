---
name: pptx
description: Creates, reads, edits, and validates PowerPoint presentations and templates (.pptx and .potx). Uses PptxGenJS for new decks and package-aware XML editing for existing slides, layouts, notes, charts, and media. Applies when creating a slide deck, adapting a presentation template, extracting slide content, or checking presentation structure and rendering.
license: Proprietary. LICENSE.txt has complete terms
compatibility: Requires Python 3.10+, Node.js, and the packages listed below. Visual rendering requires LibreOffice and Poppler; installation may require network access.
metadata:
  version: "2.4"
  last-reviewed: "2026-09-30"
  skill-author: Anthropic, PBC
  source: https://github.com/anthropics/skills/tree/main/skills/pptx
---

# PPTX creation, editing, and analysis

A `.pptx` is a ZIP archive of XML files. Choose your approach by task:

| Task | Approach |
|---|---|
| **Create** a new deck | Write a `pptxgenjs` script — see gotchas below |
| **Edit** an existing deck, or build from a template | unzip → edit `ppt/slides/slideN.xml` → zip |
| **Read** content | `markitdown deck.pptx` (one block per slide under `<!-- Slide number: N -->` markers); visual grid: `python scripts/thumbnail.py deck.pptx` |

## Scripts

Paths are relative to this skill's directory. Everything else is plain Python, `node`, or shell.

| Script | What it does |
|---|---|
| `scripts/thumbnail.py deck.pptx [prefix]` | Labeled grid of every slide, for picking template layouts. Accepts `.pptx` and `.potx`. Pass `prefix` — it defaults to `thumbnails`, which overwrites the grids of any other deck done in the same directory |
| `scripts/add_slide.py unpacked/ slide2.xml [--after slideN.xml]` | Duplicate a slide (or a `slideLayoutN.xml`) with all the package bookkeeping. Also takes a `.pptx` directly with `-o out.pptx` |
| `scripts/clean.py unpacked/` | Delete slides, media, and rels no longer referenced. Run **after** `<p:sldIdLst>` is final |
| `scripts/office/validate.py deck.pptx [--original src.pptx]` | Schema, relationship, content-type, chart and slide checks; each failure names its fix. Pass `--original` for any template-derived deck — it baselines the schema checks against the template, so the template's own XSD errors don't read as yours |
| `scripts/office/soffice.py --headless --convert-to pdf deck.pptx` | LibreOffice wrapper with a temporary user profile and an optional Linux socket shim |

## Creating with pptxgenjs — gotchas

This guide targets **PptxGenJS 4.0.1**, checked against its current release source and local generation. Check the active environment with `node -e 'const P = require("pptxgenjs"); console.log(new P().version)'`. If absent, install it in your working project with `npm install pptxgenjs@4.0.1`; availability is environment-specific. Use current [API documentation](https://gitbrent.github.io/PptxGenJS/docs/usage-pres-options/) and the release's TypeScript declarations rather than guessing option names.

- **Set `pres.layout` before adding slides.** The default canvas is `LAYOUT_16x9` = **10" × 5.625"**, not 13.3" wide. Coordinates past the edge are written, not clamped — the shape just isn't on the slide. (`LAYOUT_WIDE` is 13.3" × 7.5".)
- **Use six-digit RGB colors**, such as `color: "FF0000"`, or supported `pres.SchemeColor` values. Do not encode alpha in the hex string. Version 4.0.1 strips `#` and replaces invalid colors in some paths, but other paths emit raw values; normalization is not universal. Use `transparency: 0-100` for fills/images and `opacity: 0.0-1.0` for shadows.
- **pptxgenjs mutates option objects in place** (including shadow units during serialization). Never share one `shadow`/options object across two `add*` calls — build a fresh object each time.
- **Shadow `offset` must be ≥ 0** — a negative offset corrupts the file. To cast a shadow upward, use `angle: 270` with a positive offset.
- **`letterSpacing` is silently ignored** — the real option is `charSpacing`.
- **Lists:** `bullet: true` on each item, never a literal `•` (renders double bullets). Set `breakLine: true` on every array item except the last. Space bulleted paragraphs with `paraSpaceAfter`, not `lineSpacing` (huge gaps).
- **One `new pptxgen()` per output file** — never reuse an instance.
- **Rounded rectangles:** use `pres.ShapeType.roundRect` with `rectRadius`; `pres.ShapeType.rect` has square corners. Uppercase names from old examples are not current `ShapeType` keys.
- **Gradient fills aren't supported** — use a gradient image as the background instead.
- **Text boxes have built-in internal padding** — set `margin: 0` whenever text must align with a shape, line, or icon at the same x.
- **Speaker notes go in `slide.addNotes("...")`** (plain text, once per slide), never in a text box on the slide. Notes are part of the delivered file, so review them for leftover template content too.
- **Prefer editable native charts** using `addChart()` (an array of `{type, data, options}` for combos). For unsupported scientific features, use validated OOXML or a clearly identified rendered figure. Extra data series are not automatically equivalent to error bars or trendlines: preserve the intended statistics, units, uncertainty, and source data.
- **Default charts render bare** — no title, no data labels, dated palette. Set `showTitle` + `title`, `showValue: true` + `dataLabelPosition`, `chartColors: [...]` from your palette, and quiet the frame (`catAxisLabelColor`/`valAxisLabelColor`, `valGridLine: { color, size }`, `catGridLine: { style: "none" }`, `showLegend: false` for a single series).
- **On stacked bar/column charts, use `dataLabelPosition: "ctr"`, `"inEnd"`, or `"inBase"`.** The bundled compatibility check rejects `outEnd`; native PowerPoint behavior still needs an application check.
- **For a combo with both secondary axes**, set `secondaryValAxis: true` and `secondaryCatAxis: true` on that series and supply two entries each in `valAxes` and `catAxes`. Version 4.0.1 otherwise can emit undeclared axis IDs. A secondary value axis alone does not imply a secondary category axis; inspect the actual references.
- **Await `pres.writeFile({ fileName: "deck.pptx" })` before using the file**, then run `python scripts/office/validate.py deck.pptx`. It reports targeted chart and slide defects. Fix them in your generator and rebuild.
- **Preserve the generator's presentation child order during editing.** PptxGenJS 4.0.1 deliberately writes `<p:notesMasterIdLst>` after `<p:sldIdLst>` as a PowerPoint compatibility workaround. The bundled validator accounts for that order; it is not a general rule for every OOXML producer.
- **Icons:** render `react-icons` to SVG (`ReactDOMServer.renderToStaticMarkup`), rasterize with `sharp` at ≥256px, and insert via `addImage({ data: "image/png;base64," + buf.toString("base64") })` — the `image/png;base64,` prefix is required (install the optional `react-icons`, `react`, `react-dom`, and `sharp` packages in the working project if needed).

### Minimal runnable example

Save as `make-deck.cjs`, supply a PNG named `figure.png`, then run `node make-deck.cjs`. This example was generated and rendered with a synthetic 2:1 figure during review. `image-size` reads the actual dimensions; install `image-size@1.2.1` in the working project if needed.

```javascript
const fs = require("node:fs");
const PptxGenJS = require("pptxgenjs");
const { imageSize } = require("image-size");
const pres = new PptxGenJS();
pres.layout = "LAYOUT_16x9";
pres.theme = { headFontFace: "Arial", bodyFontFace: "Arial", lang: "en-US" };
function fitImage(widthPx, heightPx, x, y, w, h) {
  if (![widthPx, heightPx, w, h].every(v => Number.isFinite(v) && v > 0)) {
    throw new Error("Image and target dimensions must be positive");
  }
  const scale = Math.min(w / widthPx, h / heightPx);
  const width = widthPx * scale, height = heightPx * scale;
  return { x: x + (w - width) / 2, y: y + (h - height) / 2, w: width, h: height };
}
async function main() {
  const slide = pres.addSlide();
  slide.addText("Synthetic figure: aspect-ratio check", {
    x: 0.5, y: 0.3, w: 9, h: 0.6, fontSize: 26, margin: 0, color: "16324F"
  });
  const { width, height } = imageSize(fs.readFileSync("figure.png"));
  slide.addImage({ path: "figure.png", ...fitImage(width, height, 0.5, 1.2, 9, 3.6),
    altText: "Synthetic test fixture, not research data" });
  slide.addNotes("Synthetic rendering smoke test.");
  await pres.writeFile({ fileName: "output.pptx" });
}
main().catch(error => { console.error(error); process.exitCode = 1; });
```

PptxGenJS 4.0.1 has no `pres.imageSizingContain()` method. Its native `sizing` option does not discover source aspect ratio when top-level dimensions are omitted. Explicit geometry above avoids stretching; always check displayed proportions in the render.

## Editing existing decks and templates

Pick layouts first: `python scripts/thumbnail.py template.pptx template-thumbs` writes a labeled grid of every slide and prints the file(s) it created — `template-thumbs.jpg`, split into `template-thumbs-N.jpg` past 12 slides. **Always pass that second argument, named after the deck.** It defaults to `thumbnails`, so two decks thumbnailed in one directory silently overwrite each other's grids — the first deck's are simply gone (template analysis only — visual QA needs the full-resolution renders from [Converting to Images](#converting-to-images); it accepts `.pptx` and `.potx` directly). Use it with `markitdown` to map each content section onto a template slide, and vary the layouts — don't put every section on the same title-and-bullets slide.

```bash
PYTHONPATH=scripts python -c "import zipfile; from pathlib import Path; from office.helpers import safe_extract; safe_extract(zipfile.ZipFile('deck.pptx'), Path('unpacked'))"
python scripts/add_slide.py unpacked/ slide2.xml --after slide2.xml   # duplicate a slide (or slideLayoutN.xml); prints the new slide's path
# reorder / delete slides = edit <p:sldIdLst> in ppt/presentation.xml
python scripts/clean.py unpacked/                                     # after deletions: removes orphaned slides, media, rels
# edit slide content in ppt/slides/slideN.xml
PYTHONPATH=scripts python -c "from pathlib import Path; from office.helpers import rezip; rezip(Path('unpacked'), Path('out.pptx'))"
python scripts/office/validate.py out.pptx --original deck.pptx
```

- Work on a fresh extracted copy. `clean.py` deletes files in place; malformed or missing registration metadata is a reason to stop, not evidence that every slide is unused. The editors target Transitional OOXML and refuse unsupported presentation namespaces.
- A `slideLayoutN.xml` source creates a blank slide linked to the layout; it does not clone editable placeholders. Duplicate a populated slide when you need those slots.
- **Do all structural work — add, delete, reorder — before editing any slide's content.** `add_slide.py` copies a slide file verbatim, so duplicating after you edit clones the edited content; and `clean.py` deletes any slide missing from `<p:sldIdLst>`, including one you just wrote.
- **Never copy a slide file by hand** — `add_slide.py` does every registration a new slide needs and reports what it made (`Created ppt/slides/slide17.xml from slide2.xml`). It also works directly on a file: `add_slide.py deck.pptx slide2.xml -o out.pptx` — **pass `-o`, or it rewrites the input deck in place.** A duplicated slide still *references* its source's chart/SmartArt/embedded-object parts rather than cloning them, so editing one slide's chart changes the other's.
- **If you use `python-pptx`**, three things it won't do: duplicate a slide (its only entry point is `add_slide(layout)`), preserve formatting through `text_frame.text = "..."` (that collapses the paragraph to a single unstyled run — assign `run.text` instead), or insert every vector format via `add_picture` (its image inspection depends on Pillow; rasterize unsupported SVG/EMF inputs). It can preserve existing parts without decoding them.
- Legacy `.ppt` must be converted first: `python scripts/office/soffice.py --headless --convert-to pptx file.ppt`. `.potx` templates use a different main content type from `.pptx`; preserve both content type and extension when editing a template. To deliver a normal presentation from a template, save/convert as `.pptx` in an Office application instead of merely renaming the file.
- To reuse a template icon or image, duplicate a slide or layout that already contains it.

When filling in a template:

- If you script an XML transform, parse with `defusedxml.minidom` — preserve namespace bindings, especially prefixes named inside `mc:Ignorable` attributes. Changing a prefix alone is legal XML, but losing the binding used by an attribute value can break compatibility. Match elements by namespace URI rather than literal `p:`/`a:` prefixes.
- **Template slots ≠ source items.** If the template shows 4 team members and you have 3, delete the 4th member's entire group (image + text boxes), not just its text — then check for orphaned visuals in QA.
- One `<a:p>` per list item — never concatenate items into a single paragraph. Copy the sibling `<a:pPr>` to preserve spacing, and put `b="1"` on the `<a:rPr>` of titles, section headers, and inline labels (`Status:`, `Owner:`).
- Let bullets inherit from the layout; only add `<a:buChar>`, `<a:buAutoNum>` (numbered), or `<a:buNone>` to override — never a literal `•` in the text.
- Preserve the exact text node, including leading/trailing spaces. DrawingML `<a:t>` is an XML Schema string; do not copy Word's `w:t` whitespace-repair rule into slide XML or add unsupported attributes automatically.

## Design Ideas

**Don't create boring slides.** Plain bullets on a white background won't impress anyone. Consider ideas from this list for each slide.

### Before Starting

- **Pick a bold, content-informed color palette**: The palette should feel designed for THIS topic. If swapping your colors into a completely different presentation would still "work," you haven't made specific enough choices.
- **Dominance over equality**: One color should dominate (60-70% visual weight), with 1-2 supporting tones and one sharp accent. Never give all colors equal weight.
- **Dark/light contrast**: Dark backgrounds for title + conclusion slides, light for content ("sandwich" structure). Or commit to dark throughout for a premium feel.
- **Commit to a visual motif**: Pick ONE distinctive element and repeat it — rounded image frames, icons in colored circles. Carry it across every slide. **Do not use a color bar or accent stripe as your motif** (see Avoid list).

### Color Palettes

Choose colors that match your topic — don't default to generic blue. Use these palettes as inspiration:

| Theme | Primary | Secondary | Accent |
|-------|---------|-----------|--------|
| **Midnight Executive** | `1E2761` (navy) | `CADCFC` (ice blue) | `FFFFFF` (white) |
| **Forest & Moss** | `2C5F2D` (forest) | `97BC62` (moss) | `F5F5F5` (cream) |
| **Coral Energy** | `F96167` (coral) | `F9E795` (gold) | `2F3C7E` (navy) |
| **Warm Terracotta** | `B85042` (terracotta) | `E7E8D1` (sand) | `A7BEAE` (sage) |
| **Ocean Gradient** | `065A82` (deep blue) | `1C7293` (teal) | `21295C` (midnight) |
| **Charcoal Minimal** | `36454F` (charcoal) | `F2F2F2` (off-white) | `212121` (black) |
| **Teal Trust** | `028090` (teal) | `00A896` (seafoam) | `02C39A` (mint) |
| **Berry & Cream** | `6D2E46` (berry) | `A26769` (dusty rose) | `ECE2D0` (cream) |
| **Sage Calm** | `84B59F` (sage) | `69A297` (eucalyptus) | `50808E` (slate) |
| **Cherry Bold** | `990011` (cherry) | `FCF6F5` (off-white) | `2F3C7E` (navy) |

### For Each Slide

**Every slide needs a visual element** — image, chart, icon, or shape. Text-only slides are forgettable.

**Layout options:**
- Two-column (text left, illustration on right)
- Icon + text rows (icon in colored circle, bold header, description below)
- 2x2 or 2x3 grid (image on one side, grid of content blocks on other)
- Half-bleed image (full left or right side) with content overlay

**Data display:**
- Large stat callouts (big numbers 60-72pt with small labels below)
- Comparison columns (before/after, pros/cons, side-by-side options)
- Timeline or process flow (numbered steps, arrows)

**Visual polish:**
- Icons in small colored circles next to section headers
- Italic accent text for key stats or taglines

### Typography

Font availability depends on the rendering machine and the recipient's Office installation. No font list guarantees identical metrics in both. Microsoft 365 [cloud fonts](https://support.microsoft.com/en-us/office/fonts/cloud-fonts-in-office) can depend on connectivity and Office settings, and LibreOffice can substitute missing faces.

- Inspect installed fonts before choosing them; with Fontconfig, `fc-match Arial` shows the actual matched font, not proof that Arial is installed.
- Prefer fonts available in both environments, and keep the user's requested typography. Use Aptos when it is available and appropriate; do not assume it exists on older/offline installations.
- Render with the chosen fonts installed. If substitution occurs, record the substituted family and treat line wrapping as approximate. Extra space helps but is not validation.
- For critical delivery, reopen in the target PowerPoint environment and check text fit. Embedding fonts, when available and permitted by their license, may help portability.

| Element | Size |
|---------|------|
| Slide title | 36-44pt bold |
| Section header | 20-24pt bold |
| Body text | 14-16pt |
| Captions | 10-12pt muted |

### Spacing

- 0.5" minimum margins
- 0.3-0.5" between content blocks
- Leave breathing room—don't fill every inch

### Avoid (Common Mistakes)

- **Don't repeat the same layout** — vary columns, cards, and callouts across slides
- **Don't center body text** — left-align paragraphs and lists; center only titles
- **Don't skimp on size contrast** — titles need 36pt+ to stand out from 14-16pt body
- **Don't default to blue** — pick colors that reflect the specific topic
- **Don't mix spacing randomly** — choose 0.3" or 0.5" gaps and use consistently
- **Don't style one slide and leave the rest plain** — commit fully or keep it simple throughout
- **Don't create text-only slides** — add images, icons, charts, or visual elements; avoid plain title + bullets
- **Don't forget text box padding** — when aligning lines or shapes with text edges, set `margin: 0` on the text box or offset the shape to account for padding
- **Don't use low-contrast elements** — icons AND text need strong contrast against the background; avoid light text on light backgrounds or dark text on dark backgrounds
- **NEVER use accent lines under titles** — these are a hallmark of AI-generated slides; use whitespace or background color instead
- **NEVER add decorative color bars or accent stripes** — this includes: header/footer bars spanning the slide width, vertical sidebar stripes down one edge of the slide, thin accent stripes along one edge of a card or content block, and "single-side borders" on rectangles. These read as AI-generated filler. If you want to set a card apart, use a subtle background tint, a drop shadow, or an icon — not an edge stripe.
- **Don't default to cream/beige backgrounds** — when no background is specified, use white (`FFFFFF`) or the user's brand palette; avoid warm-neutral defaults like `F5F5DC`, `FAF0E6`, `FAEBD7`, `FFF8E1`
- **Don't ship text that overflows its shape** — if text doesn't fit, reduce font size, split across slides, or enlarge the container; never leave content cut off or spilling past bounds

## QA (Required)

Render every slide, fix visible issues, and rerender affected slides. Repeat until they pass; changes to themes or fonts require checking the whole deck again.

### Content QA

```bash
markitdown output.pptx
```

Check for missing content, typos, wrong order.

**When using templates, check for leftover placeholder text:**

```bash
markitdown output.pptx | rg -i "\bx{3,}\b|lorem|ipsum|\bTODO|\[insert|this.*(page|slide).*layout"
```

If the search returns results, fix them before declaring success.

### Accessibility QA

Check the deck in PowerPoint with Accessibility Checker and inspect the [Reading Order pane](https://support.microsoft.com/en-us/powerpoint/make-slides-easier-to-read-by-using-the-reading-order-pane). Arrange objects in the intended spoken sequence, add meaningful alt text to informative visuals, and exclude purely decorative objects from reading order. A correctly rendered slide can still be read in the wrong order by a screen reader. If native accessibility checks are unavailable, state that gap instead of treating image inspection as accessibility validation.

### File QA (required)

```bash
python scripts/office/validate.py output.pptx                      # built from scratch
python scripts/office/validate.py output.pptx --original src.pptx  # built from a template
```

**If the deck came from a template, always pass `--original`.** A template may itself
contain parts the XSD rejects, so a bare run can report failures you never caused — and
a genuine regression can hide among them. `--original` baselines
the schema and slide checks against the template, suppressing errors it already had.
The structural checks — relationships, content types, charts — ignore `--original` and
report template-inherited problems either way, so read those on their own merits.

This validator combines bundled 2016 XSDs with targeted compatibility checks; it does not prove every chart or modern Office extension is valid. Some chart/theme heuristics assume conventional XML prefixes. `--original` can suppress inherited errors, so inspect warnings as well as the exit code. Keep the original and perform native PowerPoint QA when available; successful LibreOffice rendering alone does not prove PowerPoint compatibility.

### Visual QA

Convert the slides to images (see [Converting to Images](#converting-to-images)) and inspect every one. After staring at the generating code you tend to see what you expect rather than what rendered, so look at the images fresh (a subagent works well for this if you have one). User-visible defects to look for:

- **Text overflow or text cut off at a box or slide boundary — check this first.** It is the most common defect and always user-visible. (For substituted fonts, record the limitation and confirm in the target application.)
- Overlapping elements (text through shapes, lines through words, stacked elements)
- Source citations or footers colliding with content above
- Elements too close (< 0.3" gaps) or cards/sections nearly touching
- Uneven gaps (large empty area in one place, cramped in another)
- Insufficient margin from slide edges (< 0.5")
- Columns or similar elements not aligned consistently
- Low-contrast text (e.g., light gray text on cream-colored background)
- Template decoration mispositioned after text replacement — e.g., a title underline positioned for one line, but the replaced title wrapped to two
- Low-contrast icons (e.g., dark icons on dark backgrounds without a contrasting circle)
- Text boxes too narrow causing excessive wrapping
- Leftover placeholder content

## Converting to Images

Convert presentations to individual slide images for visual inspection:

```bash
mkdir -p qa-output
python scripts/office/soffice.py --headless --convert-to pdf --outdir qa-output output.pptx
pdftoppm -jpeg -r 150 qa-output/output.pdf qa-output/slide
ls -1 "$PWD"/qa-output/slide-*.jpg
```

Use a fresh `qa-output` directory for each run so stale PDFs or slide images cannot be mistaken for the latest result. Confirm that conversion created a new PDF, then inspect the full-resolution images. `pdftoppm` pads page numbers according to the total page count.

After edits, regenerate the PDF before rasterizing again. LibreOffice excludes hidden slides from PDF by default; review the labeled hidden placeholders in the thumbnail grid, and export hidden slides explicitly when they are part of the review scope:

```bash
python scripts/office/soffice.py --headless --convert-to 'pdf:impress_pdf_Export:{"ExportHiddenSlides":{"type":"boolean","value":"true"}}' --outdir qa-output output.pptx
```

## Dependencies

`pptxgenjs@4.0.1` (npm; generation) · `image-size@1.2.1` (npm; example dimension inspection) · `markitdown[pptx]`, `Pillow`, `defusedxml`, `lxml` (Python; text extraction, thumbnail, clean, validate) · optional `python-pptx` (Python editing) · LibreOffice (`soffice` on PATH) · `pdftoppm` (Poppler). No credentials or remote service are needed for local editing. Package installation and linked media may need network access.

Review evidence: generated PptxGenJS 4.0.1 files, package edits, notes, images, and chart-axis references were checked locally; rendered with LibreOffice 26.2.4.2 and Poppler 26.09.0. Native PowerPoint, screen-reader order, animations, and user-specific templates remain application-level checks.

Current references: [PptxGenJS text](https://gitbrent.github.io/PptxGenJS/docs/api-text/), [images](https://gitbrent.github.io/PptxGenJS/docs/api-images/), [charts](https://gitbrent.github.io/PptxGenJS/docs/api-charts/), [saving](https://gitbrent.github.io/PptxGenJS/docs/usage-saving/), [python-pptx text](https://python-pptx.readthedocs.io/en/latest/api/text.html), [LibreOffice CLI](https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html), [PDF export options](https://help.libreoffice.org/latest/en-US/text/shared/guide/pdf_params.html), and [MarkItDown](https://github.com/microsoft/markitdown).

---

*This skill is created and maintained by [Anthropic](https://github.com/anthropics/skills/tree/main/skills/pptx). Locally maintained with versioned API guidance, package-editing fixes, and QA instructions; see LICENSE.txt for terms.*
