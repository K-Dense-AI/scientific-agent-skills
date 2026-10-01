# Poster manifest 2.0

## Purpose

The manifest is the only content input to the generator. It binds:

- approved text and images;
- exact source IDs;
- local asset hashes and licenses;
- PowerPoint canvas and physical output geometry;
- conference and printer rules;
- accessibility/quality thresholds and their basis;
- reading order;
- author approval to a canonical content hash.

Unknown keys, duplicate JSON keys, non-finite numbers, remote asset paths, path escape,
unapproved fields, unresolved sources, unused records, and common placeholders are
rejected.

## Template

`assets/poster_manifest_template.json` is intentionally invalid. It contains
replacement tokens, false confirmations, and draft approval so it cannot produce a
poster accidentally.

Copy it into a project directory, then replace every field with reviewed values.
Asset paths are relative to that manifest's directory.

## Top-level object

Manifest version 2.0 requires exactly these keys:

- `schema_version`
- `document`
- `canvas`
- `physical_output`
- `requirements`
- `quality`
- `palette`
- `sources`
- `assets`
- `elements`
- `approval`

The validator rejects extensions to the schema rather than silently ignoring them.

## `document`

- `id`: stable identifier beginning with a letter.
- `title`: exact approved title, at most 255 characters.
- `subject`: exact approved description for core document metadata, at most 255 characters.
- `language`: BCP 47-style language tag.
- `authors`: exact ordered author names; joined by `; ` they must fit the 255-character
  core-property limit. No author is silently dropped or shortened.
- `source_ids`: exact records supporting title, subject, language, and author metadata.

Exactly one text element with role `title` must match `document.title` verbatim.
It must have `reading_order: 1`; generation uses it as the native PowerPoint slide
title placeholder rather than as an undifferentiated text box.

## `canvas`

- `width_in`, `height_in`: PowerPoint slide dimensions, each 1–56 inches.
- `background_color`: opaque six-digit sRGB hex.

These are design dimensions, not automatically the physical trim size.

## `physical_output`

- `trim_width_in`, `trim_height_in`: finished physical dimensions.
- `bleed_in`: physical bleed on each edge.
- `safe_margin_in`: inset inside the trim edge for non-bleed content.
- `orientation`: `portrait`, `landscape`, or `square`, matching trim dimensions.

The physical artboard is trim plus twice the bleed. It must share the canvas aspect
ratio.

## `requirements`

### `conference`

The organizer record must be confirmed and provide:

- exact `source_id`;
- maximum width and height;
- orientation (`portrait`, `landscape`, `square`, or `either`);
- required delivery format (`PDF`, `PPTX`, `PDF_AND_PPTX`, or `OTHER`);
- notes copied or summarized from the verified rule.

The physical trim dimensions must fit.
The referenced source record must have kind `conference_rule`.

### `printer`

The printer record must be confirmed and provide:

- exact `source_id`;
- trim width/height, bleed, and safe margin matching `physical_output`;
- accepted color mode (`RGB`, `CMYK`, or `PRINTER_MANAGED`);
- whether uniform scaling is allowed;
- notes describing the confirmed workflow.

If scaling is forbidden, canvas and physical artboard must be 1:1. A CMYK requirement
does not prevent creation of an editable RGB PPTX, but the export plan blocks a claim
of print readiness pending printer-approved conversion/proof.
The referenced source record must have kind `printer_rule`.

## `quality`

- `minimum_font_pt_final`
- `font_guidance_basis`
- `font_guidance_source_id`
- `minimum_raster_dpi_final`
- `raster_dpi_basis`
- `raster_dpi_source_id`

Basis values are:

- `heuristic`
- `source_specific`
- `conference_requirement`
- `printer_requirement`

A heuristic must have a null source ID. Every other basis requires an exact source
ID. Values apply at final physical output, after uniform scaling.

## `palette`

`colors` maps stable IDs to opaque `#RRGGBB` sRGB values.

Each `contrast_pairs` record contains:

- `id`
- `foreground_color_id`
- `background_color_id`
- `usage`: `normal_text`, `large_text`, or `non_text`

The validator applies 4.5:1 to normal text and 3:1 to large text/non-text. A text
element using `large_text` must be at least 18 pt final, or at least 14 pt final and
bold.

`data_series_redundant_encoding` must be true. This is an author confirmation that
color is supplemented by labels, shapes, markers, patterns, or line styles. It is not
an automated certification.

## `sources`

Each source has:

- `id`
- `kind`
- `citation`
- `locator`
- `author_verified: true`

Kinds include author content, publication, dataset, asset license, conference rule,
printer rule, institutional rule, and other.

Every source must be used, and every referenced ID must exist. The scripts do not
resolve URLs, DOIs, or local records.

## `assets`

The array may be empty: figures, logos, and QR codes are optional. Only local
PNG/JPEG assets are accepted when an asset is present. Each record has:

- `id`
- manifest-relative `path`
- `role`: `figure`, `logo`, or `qr_code`
- lowercase SHA-256
- exact `source_id`
- `license`: exact license or permission statement
- `provenance`: exact author-verified origin or generation record
- concise `alt_text`
- `author_approved: true`
- `qr_target`

`qr_target` is null except for QR assets, where it is an exact `https://` URL. Files
are bounded, final symlinks are rejected, paths cannot escape the manifest directory,
and hashes must match.

All asset records must be placed in the poster.
Use one asset record for repeated placement of the same file; duplicate asset paths
are rejected.

The image inventory rejects EXIF, XMP, comments, and embedded text/application
metadata to avoid publishing hidden or location-identifying information. Flatten and
strip such metadata in an author-reviewed offline workflow, then hash and approve the
resulting pixels as a new asset. ICC profiles and basic technical image fields are
reported but not silently removed.

## `elements`

Elements are listed in ascending, contiguous `reading_order` from 1. The list order is
not silently changed.

Every element has:

- `id`, `type`, and `reading_order`
- design coordinates `x_in`, `y_in`, `width_in`, `height_in`
- one or more exact `source_ids`
- `author_approved: true`
- `allow_in_bleed`

All boxes must stay on the canvas. Non-bleed elements must remain inside the physical
safe area mapped to the canvas. Text can never be allowed in bleed.

### Text elements

Text elements also specify:

- `role`
- exact `text`
- `font_size_pt_design`
- `font_face`
- `bold`
- horizontal and vertical alignment
- `contrast_pair_id`
- optional `line_color_id`
- `line_width_pt`
- `margin_in`

Roles include title, authors, affiliation, heading, body, caption, reference,
acknowledgement, contact, QR fallback, and other.

Font size is checked after physical scaling. Text auto-shrink is disabled during
generation.

### Image elements

Image elements also specify:

- `asset_id`
- `fit: "contain"`
- `fallback_text_element_id`
- `long_description_element_id`

Contain fitting preserves aspect ratio and centers the image. A QR asset requires a
square box and a fallback text element whose role is `qr_fallback` and whose text
contains the exact `qr_target`. Other assets use null fallback IDs.

`long_description_element_id` is null when approved alt text and adjacent native text
are sufficient. For a complex figure that needs a longer explanation, it references
an approved native text element with role `body`, `caption`, or `other`. That element
must follow the image in reading order and include every source ID used by the image.
QR assets use the required visible fallback text and therefore set this field to null.
The reference is structural; a human must decide whether the description is complete.

## Approval

Draft form:

```json
{
  "status": "draft",
  "approved_by": null,
  "approved_at": null,
  "content_sha256": null
}
```

After all non-approval fields validate:

```bash
python -B scripts/validate_manifest.py poster.json \
  --print-content-hash
```

Give the exact manifest and reported hash to the author. Approved form requires:

- `status: "approved"`
- nonempty `approved_by`
- ISO 8601 `approved_at` with UTC offset
- exact lowercase `content_sha256`

The hash covers every top-level field except `approval`, using canonical sorted
UTF-8 JSON. Any content, source, requirement, palette, coordinate, or asset-metadata
change invalidates approval. The generator preserves the approval timestamp in its
report and converts it to UTC for the PPTX created/modified core properties, as
required by python-pptx; the original UTC offset is not stored in those properties.

## Validation modes and exit codes

Normal validation reads and hashes assets and requires approval:

```bash
python -B scripts/validate_manifest.py poster.json
```

`--structure-only` skips file reads/hashes but still validates path syntax. Use it for
planning/audit only, never generation.

`--print-content-hash` permits draft approval but does not permit placeholders,
unverified sources, unapproved elements, or false requirements.

CLIs use:

- exit 0: pass;
- exit 1: completed audit found a release-blocking issue;
- exit 2: invalid input, unsafe input, missing dependency, or command error.
