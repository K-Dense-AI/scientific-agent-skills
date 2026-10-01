# PPTX poster release checklist

Use this checklist for the final generated package and every exported/printed
derivative. A script pass is necessary but not sufficient.

## 1. Requirements and approval

- [ ] The organizer's current poster rule is recorded with an exact source ID.
- [ ] The printer's current trim, bleed, safe-margin, scaling, file-format, and
      color requirements are recorded with an exact source ID.
- [ ] The selected physical trim size and orientation comply with those records.
- [ ] No generic "standard poster size" was substituted for organizer/printer rules.
- [ ] Every claim, number, citation, author name, affiliation, logo, figure, and
      asset license has an exact source ID.
- [ ] Every source record is marked author-verified.
- [ ] Every element and asset is marked author-approved.
- [ ] No placeholder, sample claim, invented citation, or inferred result remains.
- [ ] The approving author reviewed the canonical content hash after the final edit.

Run:

```bash
python -B scripts/validate_manifest.py poster.json
```

## 2. Safe local generation

- [ ] Generation used the exact versions in `generation_dependencies.json`.
- [ ] All optional image paths are manifest-relative local PNG/JPEG files.
- [ ] Every asset hash matches.
- [ ] Every asset has exact provenance and a license/permission statement.
- [ ] No template file, remote image, URL download, API key, environment file,
      image-generation service, or network service was used.
- [ ] The output path was new; no existing file was replaced.
- [ ] The generated file is `.pptx`, never `.pptm`.

Run:

```bash
uv run --no-project --with "python-pptx==1.0.2" --with "Pillow==12.3.0" \
  --with "lxml==6.1.3" \
  python -B scripts/generate_poster.py poster.json --output poster.pptx
```

## 3. PPTX package security

- [ ] ZIP member names have no traversal, absolute paths, symlinks, duplicates,
      encryption, oversized entries, or excessive expansion ratios.
- [ ] The package has the standard macro-free PresentationML content type.
- [ ] The package matches the strict generated one-slide part profile.
- [ ] No VBA, ActiveX, OLE, embedded package, executable/binary payload, external
      link part, or custom UI is present.
- [ ] No relationship has `TargetMode="External"`.
- [ ] No remotely linked image is present.
- [ ] Internal relationship targets resolve to existing package parts.
- [ ] The presentation was inspected as ZIP/XML and was not opened or executed by
      the inspection script.

Run:

```bash
python -B scripts/inspect_pptx.py poster.pptx
```

Treat any package finding as a release blocker. Do not "fix" an untrusted package
by opening it in PowerPoint.

## 4. Dimensions, scale, bleed, and margins

- [ ] PowerPoint canvas width and height are each in the current 1–56 inch range.
- [ ] Final physical trim dimensions are recorded separately from canvas dimensions.
- [ ] Final artboard dimensions include twice the confirmed bleed on each axis.
- [ ] Canvas and final artboard have the same aspect ratio.
- [ ] Uniform print scale is explicit; no nonuniform stretching is allowed.
- [ ] Printer permission is recorded if final output is scaled from the PPTX canvas.
- [ ] All non-bleed content stays inside the confirmed safe margin from the trim edge.
- [ ] Full-bleed imagery reaches the artboard edge and does not move text into bleed.
- [ ] A physical or contract proof confirms trim and bleed behavior.

Run:

```bash
python -B scripts/plan_export.py poster.json
```

## 5. Layout and typography

- [ ] No shape is out of bounds.
- [ ] Every reported bounding-box overlap is either removed or documented as
      intentional after visual inspection.
- [ ] No text box visibly overflows, clips, wraps unexpectedly, or uses silent
      auto-shrink.
- [ ] Font sizes were assessed at final physical output, not only on the PPTX canvas.
- [ ] The manifest labels its minimum-font value as a project heuristic or ties it
      to an exact organizer/printer/source requirement.
- [ ] Required fonts are available on the export workstation and printer workflow.
- [ ] Font embedding rights and the chosen embed/not-embed workflow were reviewed;
      the generator itself did not embed fonts.
- [ ] Font substitution, equations, symbols, and scientific glyphs were checked.
- [ ] Visual hierarchy and reading path remain clear at reduced-scale proof size.

Run:

```bash
python -B scripts/check_layout.py poster.pptx --manifest poster.json
```

The checker cannot determine rendered overflow or font substitution; inspect those
in PowerPoint and in the exported PDF.

## 6. Raster images and assets

- [ ] Effective DPI is calculated from pixel dimensions divided by final placed
      inches, not from file metadata.
- [ ] Every placement meets the manifest's source-labeled or heuristic DPI threshold.
- [ ] No image is stretched out of aspect ratio.
- [ ] The final PDF and printer proof show no resampling artifacts.
- [ ] Asset IDs, hashes, source IDs, provenance, permissions/licenses, and alt text are
      in the inventory.
- [ ] EXIF, XMP, comments, and embedded text/application metadata were stripped in
      an author-reviewed offline workflow before hashing and approval.
- [ ] Logos and images are authorized for this use.

Run:

```bash
python -B scripts/inventory_images.py poster.json \
  --output poster.assets.json
```

## 7. Color and graphical accessibility

- [ ] Normal text pairs meet WCAG 2.2 SC 1.4.3 at 4.5:1.
- [ ] Large text pairs meet 3:1 only when final text is at least 18 pt, or at least
      14 pt and bold.
- [ ] Essential graphical objects meet the 3:1 non-text contrast screen where
      WCAG 2.2 SC 1.4.11 is being used as the design target.
- [ ] Information is never encoded by color alone.
- [ ] Categories also use direct labels, shapes, markers, patterns, or line styles.
- [ ] Palette selection is appropriate to data type: qualitative, sequential, or
      diverging.
- [ ] A grayscale/color-vision simulation is reviewed as a screen, not treated as
      proof of accessibility.
- [ ] A color proof confirms the printer's conversion and substrate behavior.

Run:

```bash
python -B scripts/check_palette.py poster.json
```

## 8. PowerPoint accessibility

- [ ] Every picture has concise, accurate alt text that conveys purpose.
- [ ] Complex figures have an approved source-bound native long description when alt
      text and adjacent prose are insufficient.
- [ ] Important text is native text, not only pixels inside an image.
- [ ] The visible title is the native slide-title placeholder and text language is
      correct.
- [ ] The Reading Order pane matches the intended logical sequence.
- [ ] The PowerPoint Accessibility Checker has no unresolved errors.
- [ ] A keyboard and screen-reader pass confirms the actual reading order.
- [ ] Text links have meaningful visible labels.
- [ ] Every QR code has the exact destination URL in visible fallback text.
- [ ] Each final printed QR code was tested with multiple devices.
- [ ] Language, author names, acronyms, captions, and table alternatives are correct.

Automated XML inspection cannot certify these manual checks.

## 9. Export and print

- [ ] Export uses PowerPoint's Standard/high print quality, not Minimum size.
- [ ] No audio, video, linked media, OLE, ActiveX, embedded file, or external
      relationship was introduced after generation.
- [ ] Exporter/settings and any online conversion route are recorded and permitted.
- [ ] Actual PDF page size is measured against canvas and final artboard separately;
      printer scaling or a full-size PDF derivative is confirmed when they differ.
- [ ] Exported PDF is checked independently for tags, reading order, alt text,
      links, fonts, clipping, image quality, and page dimensions.
- [ ] RGB is distinguished from any printer-required CMYK conversion.
- [ ] If CMYK is required, the printer-approved conversion/profile and proof are
      complete; the native PowerPoint export is not represented as CMYK-compliant.
- [ ] Conference file format, naming, file-size, and submission rules are met.
- [ ] Printer deadline, substrate, mounting, delivery, and backup requirements are met.

## 10. Final sign-off

- [ ] Presenting/corresponding author approved all scientific content and citations.
- [ ] Accessibility reviewer completed manual checks.
- [ ] Printer or production contact approved dimensions, bleed, scale, and color.
- [ ] The exact approved manifest, PPTX hash, asset inventory, audit reports, exported
      PDF, and proof are retained together.
- [ ] A final change triggers a new content hash, new author approval, regeneration,
      re-export, and all checks again.
