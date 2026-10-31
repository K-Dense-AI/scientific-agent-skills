# PowerPoint poster dimensions, layout, and output

## Keep six concepts separate

1. **Physical trim size** — finished width and height after cutting.
2. **Bleed** — artwork extending beyond each trim edge when the printer requires it.
3. **Physical artboard** — trim plus bleed on both sides:
   `artboard = trim + 2 × bleed`.
4. **Safe margin** — inset inside the trim edge for non-bleed content.
5. **PowerPoint canvas** — the slide width and height stored in the PPTX.
6. **Print/export scale** — uniform conversion from canvas to physical artboard.

Raster effective DPI and final font size depend on physical placement, not merely the
canvas.

## Current PowerPoint size limits

[Microsoft's current slide-size guidance](https://support.microsoft.com/en-us/office/change-the-size-of-your-powerpoint-slides-040a811c-be43-40b9-8d04-0de5ed79987e)
states that each custom dimension is from 1 to 56 inches (2.54–142.24 cm). It also
states that all slides in a presentation have the same size.

Do not bypass this limit by supplying pixel values; PowerPoint converts entered units.
This skill accepts inches and enforces the 1–56 inch range.

If a required physical artboard exceeds 56 inches on an edge:

- choose a smaller proportional canvas;
- preserve the exact artboard aspect ratio;
- record the uniform output scale;
- confirm that the printer permits scaling;
- scale design fonts so their final point sizes remain correct;
- calculate image DPI at final physical placement.

Do not scale width and height independently.

## Scale equations

For a proportional design:

```text
scale_x = physical_artboard_width / canvas_width
scale_y = physical_artboard_height / canvas_height
scale_x must equal scale_y

final_font_pt = design_font_pt × scale
final_placed_width_in = design_width_in × scale
effective_dpi_x = image_width_px / final_placed_width_in
```

The manifest validator allows only a small numerical tolerance between `scale_x` and
`scale_y`.

## Bleed and safe area

Bleed and safe margin are printer-specific. A conference board dimension does not
establish either.

The manifest treats the physical artboard, including bleed, as the area mapped to the
PowerPoint canvas. It computes the safe inset on the canvas as:

`(bleed + safe margin) / print scale`

Native text must remain inside that boundary. Only intentional imagery may set
`allow_in_bleed: true`.

PowerPoint generation is not a press-ready preflight. The printer must confirm crop,
trim, bleed, substrate, and proofing behavior.

## Conference examples show variation

These are dated examples, not presets:

- [CSCW 2026](https://cscw.acm.org/2026/posters.html) allocated a 48 × 48 inch
  space, recommended no more than 45 inches on either side, allowed up to 47 inches,
  and said A0 or A1 could be acceptable.
- [IEEE DSC 2025](https://attend.ieee.org/dsc-2025/call-for-posters/) required
  posters to fit an A1 space (84.1 × 59.4 cm).

The differences are the point: check the current instruction for the actual event.
Board size, maximum poster size, submission-document format, and physical print size
can be different rules.

## Choosing a layout

Choose a grid after content, orientation, language direction, and required dimensions
are known.

- A single narrative path can use one broad column or a sequence of panels.
- Two columns can work for comparisons or smaller formats.
- Three or more columns can shorten lines on wide canvases but increase navigation
  complexity.
- An asymmetric grid can emphasize one key result if the reading order remains clear.

No column count is inherently standard or accessible. Use consistent alignment and
spacing, and leave enough room for the actual approved content without shrinking type.

The strict manifest places every text or image element in an explicit rectangle.
Elements are listed in contiguous reading order and are generated in that order.

## Bounds and overlap

The layout checker reads PresentationML transforms directly. It reports:

- shapes outside the slide;
- direct bounding-box intersections;
- text without explicit size;
- text below the manifest's final-output minimum;
- direct shape order and, when a manifest is supplied, exact object-name/order
  comparison against approved `reading_order`.

Bounding boxes are conservative. A report can include an intentional overlay, while
a clean report can still hide text overflow, rotation, group-transform, chart, SmartArt,
or font-substitution problems. The generator avoids groups, charts, SmartArt, and
overlays so that a clean direct-box check is meaningful.

Always inspect in PowerPoint and in the exported PDF.

## Images

Image placement uses `contain` fitting:

- preserve the source aspect ratio;
- center the image inside its approved element box;
- do not crop or stretch;
- use final placed dimensions for effective DPI.

If the scientific message depends on a crop, create and approve a new local asset,
hash it, and update its source/alt text. Do not apply a silent crop during generation.

QR placement boxes must be square. Test the final physical QR code; pixel count and
box geometry do not guarantee scan reliability.

## Color mode

Treat PowerPoint as an RGB authoring workflow. Its documented automation color
property is RGB, and the generated package uses opaque sRGB hex colors.

If the printer accepts RGB, record that requirement and approve a proof. If the
printer manages conversion, obtain its profile/process and approve a proof. If the
printer requires CMYK, the export plan blocks a claim of readiness until a
printer-approved conversion and proof are complete. Do not label a native PowerPoint
PDF as CMYK-compliant without verifying the actual output.

Transparency, gradients, photographs, and institutional colors can change during
conversion. Contrast calculations on source sRGB values do not predict the printed
result.

## PDF export

[Microsoft's export guidance](https://support.microsoft.com/en-us/powerpoint/export-a-presentation)
distinguishes Standard quality for publishing/printing from Minimum size. Use the
current PowerPoint interface and Standard/high print quality when PDF is required.

The export plan reports both canvas dimensions and final-artboard dimensions in
PDF points (72 points per inch), but creates no PDF. A reduced canvas does not make
the exported page automatically full-size. Measure the actual PDF page; arrange
printer scaling or an approved full-size PDF conversion as required, then verify
the transformed file again. Never confuse full-size print placement with PDF page
size.

On macOS, [Microsoft's accessible PDF export route](https://support.microsoft.com/en-us/accessibility/office-accessibility/create-accessible-pdfs)
uses an online conversion service. Record the route and settings; choose a local
route when document transmission is not authorized and inspect its actual tags and
links. Standard/high quality is a print setting, not a privacy or tagging guarantee.

After export, independently verify:

- PDF page/artboard dimensions and orientation;
- one-page output when the organizer expects one page;
- trim/bleed handling;
- fonts, glyphs, equations, clipping, and substitutions;
- image quality and resampling;
- color and printer proof;
- tags, reading order, alt text, links, and language;
- conference naming, file-size, and upload requirements.

[Microsoft's PowerPoint PDF accessibility documentation](https://learn.microsoft.com/en-us/office/pdf/powerpoint/powerpointpdfaccessibility)
describes modern tagged-PDF behavior, but availability varies by PowerPoint version
and channel. Verify the installed version and the actual PDF; do not infer PDF
accessibility from the PPTX.

## Resizing existing content

Microsoft presents **Maximize** and **Ensure Fit** when changing slide size. Maximize
can move content outside the slide; Ensure Fit can make content smaller.

This workflow sets dimensions before adding content and does not repurpose an existing
slide. If a human later changes the size, treat that as a layout change:

1. re-check physical/canvas aspect and print scale;
2. re-check every final font size and effective DPI;
3. re-run bounds and overlap checks;
4. renew author approval because layout and possibly content hash changed;
5. re-export and re-proof.

## Final physical review

Inspect a reduced-scale proof and the printer's full-size or contract proof. Confirm
readability at expected distances, trim, bleed, margins, color, raster quality, QR
function, mounting constraints, and accessibility. No XML or geometry checker can
simulate the final venue.
