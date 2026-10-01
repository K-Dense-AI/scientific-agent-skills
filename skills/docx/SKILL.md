---
name: docx
description: "Creates, reads, edits, and manipulates Word documents (.docx files) or Word templates (.dotx files). Triggers include: any mention of 'Word doc', 'word document', '.docx', '.dotx', or requests to produce professional documents with formatting like tables of contents, headings, page numbers, or letterheads. Also use when extracting or reorganizing content from .docx or .dotx files, inserting or replacing images in documents, performing find-and-replace in Word files, working with tracked changes or comments, or converting content into a polished Word document. If the user asks for a 'report', 'memo', 'letter', 'template', or similar deliverable as a Word or .docx file, use this skill. Do NOT use for PDFs, spreadsheets, Google Docs, or general coding tasks unrelated to document generation."
compatibility: Requires Node.js with docx, Python 3.11+ with defusedxml and lxml, and LibreOffice, Pandoc, and Poppler for conversion and visual checks. Network access is only needed for installation.
license: Proprietary. LICENSE.txt has complete terms
metadata:
  version: "2.4"
  last-reviewed: "2026-09-30"
  tested-docx-js: "9.8.1"
  skill-author: Anthropic, PBC
  source: https://github.com/anthropics/skills/tree/main/skills/docx
---

# DOCX creation, editing, and analysis

A `.docx` is a ZIP archive of XML files. Choose your approach by task:

| Task | Approach |
|---|---|
| **Create** a new document | Write a `docx` (npm) script — see gotchas below |
| **Fill** placeholders in a template | `patchDocument({ data, outputType, patches })` from `docx` |
| **Edit** arbitrary existing content | Safely unpack → edit the relevant OOXML parts → repackage |
| **Read** content | `pandoc -f docx -t markdown --track-changes=all file.docx` for review; `accept` for the accepted text view |

> Script paths below are relative to this skill's directory.

## Creating with docx-js — gotchas

Examples target **docx 9.8.1**. Check `node -p "require.resolve('docx')"` in the
script's project first. If absent, install it there with `npm install docx@9.8.1`;
preinstallation is environment-specific. These are the main layout constraints:

- **Page size defaults to A4.** For US Letter set `page: { size: { width: 12240, height: 15840 } }` (DXA; 1440 = 1″).
- **Landscape:** pass portrait dimensions and `orientation: PageOrientation.LANDSCAPE` — docx-js swaps width/height internally.
- **Tables:** for predictable fixed geometry, use `layout: TableLayoutType.FIXED`, table `width: { size, type: WidthType.DXA }`, numeric `columnWidths` in DXA, and matching widths on cells. With spans, sum the spanned columns. Percentage widths are supported, but cross-editor layout needs visual verification.
- **Table shading:** use `ShadingType.CLEAR` with `fill` for a plain background; `SOLID` uses the foreground pattern color, not just `fill`.
- **Lists:** never insert `•` literally; use a `numbering` config with `LevelFormat.BULLET`.
- **`ImageRun` requires `type:`** (`"png"`, `"jpg"`, …).
- **`PageBreak` must be inside a `Paragraph`.**
- **Paragraphs and line breaks:** use separate `Paragraph` elements for paragraphs; `new TextRun({ break: 1, text: "Next line" })` gives a line break within a paragraph. Do not expect `\n` in a plain text string to create paragraphs.
- **TOC:** built-in `HeadingLevel.*` works with `headingStyleRange`. For custom styles use `stylesWithLevels`, or `outlineLevel` with `useAppliedParagraphOutlineLevel: true`. Update the TOC field in Word/LibreOffice before checking page numbers; creating a field does not calculate pagination.
- **Don't use a table as a horizontal rule** — use a paragraph bottom border instead.
- **Dot-leader / right-aligned-on-same-line:** use `PositionalTab` (`alignment: PositionalTabAlignment.RIGHT`, `relativeTo: PositionalTabRelativeTo.MARGIN`, `leader: PositionalTabLeader.DOT`) inside a `TextRun`, not literal `.` or space padding. LibreOffice 26.2.4.2 did not render that positional leader/alignment in the smoke test; use paragraph `tabStops` plus a `Tab` run when that renderer must reproduce it.

### Small creation and template example

Run this CommonJS script with `node example.cjs`. `patchDocument` replaces
`{{name}}` without requiring a complete document rebuild; it is a placeholder
patcher, not a general Word document editing object model.

```javascript
const fs = require("node:fs/promises");
const { Document, Packer, Paragraph, TextRun, HeadingLevel,
        patchDocument, PatchType } = require("docx");

async function main() {
  const document = new Document({ sections: [{
    properties: { page: { size: { width: 12240, height: 15840 } } },
    children: [
      new Paragraph({ text: "Research memo", heading: HeadingLevel.HEADING_1 }),
      new Paragraph("Prepared for {{name}}"),
    ],
  }] });
  const template = await Packer.toBuffer(document);
  const output = await patchDocument({
    data: template, outputType: "nodebuffer",
    patches: { name: { type: PatchType.PARAGRAPH,
      children: [new TextRun({ text: "Research team", bold: true })] } },
  });
  await fs.writeFile("output.docx", output);
}
main().catch(error => { console.error(error); process.exitCode = 1; });
```

## Verify the output

After writing a `.docx`, render it and look at it:

```bash
mkdir -p preview
python scripts/office/soffice.py --headless --convert-to pdf --outdir preview output.docx
test -s preview/output.pdf
pdftoppm -jpeg -r 100 preview/output.pdf preview/page
ls preview/page-*.jpg   # then Read the images
```

Use a fresh preview directory or remove its old PDF first: converter exit status alone
does not prove that a new file was written. Inspect every rendered page for overflow,
headers, tables, and missing images; conversion can substitute unavailable fonts.

`pdftoppm` zero-pads page numbers to the width of the page count (`page-01.jpg`…`page-12.jpg`).

## Editing existing documents

Legacy `.doc` files must be converted first: `python scripts/office/soffice.py --headless --convert-to docx file.doc`.

```bash
python - <<'PY'
import sys, zipfile
from pathlib import Path
sys.path.insert(0, "scripts")
from office.helpers import safe_extract
with zipfile.ZipFile("doc.docx") as archive:
    safe_extract(archive, Path("unpacked"))  # rejects symlinks and traversal
PY
python scripts/merge_runs.py unpacked/   # coalesce fragmented runs so text is findable
# edit unpacked/word/document.xml in place — do NOT reformat or pretty-print
(cd unpacked && rm -f ../out.docx && zip -Xr ../out.docx .)
python scripts/office/validate.py out.docx --original doc.docx   # bundled schema and package checks
# redlining? add --author "<the name you redlined under>" to check every edit is tracked
```

Word splits text across many `<w:r>` runs (revision ids, spell-check markers), so a phrase you can see in the document often doesn't exist as a contiguous string in the XML. `merge_runs.py` merges adjacent identically-formatted runs in `word/document.xml` while retaining text and formatting boundaries; render-check the result, especially fields and complex content; it also accepts a `.docx` directly (`python scripts/merge_runs.py doc.docx -o merged.docx`).

**Tracked changes:** preserve author/date/IDs and revisions that already exist. When redlining, validate with `--author "<the name you redlined under>"` (needs `--original`) — it compares body text after undoing new `<w:ins>`/`<w:del>` revisions, to expose untracked text edits that an accepted view can hide. Wrap runs in `<w:ins>`/`<w:del>` with `w:id`, `w:author`, `w:date` attributes. Inside `<w:del>`, the text element is `<w:delText>`, not `<w:t>`. A deleted paragraph mark (`<w:pPr><w:rPr><w:del w:id=".." w:author=".." w:date=".."/></w:rPr></w:pPr>`) means "merge this paragraph into the next" — so deleting a paragraph outright is that plus a `<w:del>` around every run. Within paragraph-mark `w:rPr`, place revision markers before the other run properties as required by that content model.

To produce a clean copy with all tracked changes accepted: `python scripts/accept_changes.py in.docx out.docx`.

The helper uses a temporary copy and isolated LibreOffice profile. Its own application
macro opens the input with `MacroExecutionMode=NEVER_EXECUTE`, so document-supplied
macros are disabled; it does not lower profile macro security. A timeout, conversion
failure, or remaining revision elements in any Word XML part leaves the destination
unchanged. `--timeout 120` raises the limit per LibreOffice operation. A document
without revision elements is copied without a LibreOffice round trip.

Accepting a deleted paragraph mark should join that paragraph to the next. Do not
assume a Pandoc accepted-text view or LibreOffice conversion exactly reproduces
Word's paragraph, list, or formatting semantics. Inspect deleted paragraph marks in
the XML and render the clean copy, particularly deleted numbered paragraphs beside
empty spacers. An unexpected empty bullet needs investigation, not automatic dismissal.

The bundled validator is a practical check against the shipped 2016 schemas plus
selected Microsoft extensions, not a complete current Word compatibility verdict.
`--original` suppresses inherited schema errors. `--auto-repair` rewrites the input
and may change significant whitespace; inspect its changes. The redlining check
covers body text only, not formatting, tables' structural revisions, or other stories.

### Document-wide edit coverage

`word/document.xml` contains the main story, not all document text. Before a
whole-document replacement, inventory the relevant header, footer, footnote,
endnote, comment, and text-box stories through the package relationships.
`merge_runs.py` processes only `word/document.xml`; it does not normalize those
other parts. Apply the requested edit wherever its scope requires, preserve
relationships, and check the rendered first-page and odd/even headers and
footers as well as the body. See Microsoft's [WordprocessingML structure](https://learn.microsoft.com/en-us/office/open-xml/word/structure-of-a-wordprocessingml-document).

## Comments

Basic comments need a comments part, its relationship/content type, and a matching
`commentReference`; range start/end markers optionally identify the text span.
The helper additionally writes Microsoft extension parts for reply threading. Use it — directory mode when you'll also be editing `document.xml` (saves an unzip/rezip cycle), `.docx`-direct mode otherwise:

```bash
# Against an already-unpacked directory (preferred when also placing markers)
python scripts/comment.py unpacked/ "Fees & expenses cap is too low"
python scripts/comment.py unpacked/ "Agreed" --parent 0

# Against a .docx directly
python scripts/comment.py contract.docx "This cap is too low" -o annotated.docx
```

The script writes `comments.xml`, `commentsExtended.xml`, `commentsIds.xml`, `commentsExtensible.xml`, the relationships, and the content-type overrides. Comment IDs are auto-assigned; duplicate explicit IDs are rejected. Replies reference the last paragraph ID of the parent comment. Existing parts using alternate filenames require editing those relationship targets directly; the helper rejects them instead of creating competing comment parts. It then prints the `<w:commentRangeStart>`/`<w:commentRangeEnd>`/`<w:commentReference>` snippet to add to `word/document.xml` so the comment anchors to specific text — until you place those markers, the comment exists but is not visible.

## Dependencies

`docx` (npm) · Python `defusedxml` and `lxml` · `pandoc` · LibreOffice (`soffice`) · `pdftoppm` (Poppler).
Python package installation: `python -m pip install defusedxml lxml` in a dedicated
environment. No credentials or service API calls are needed.

Reviewed against the current [docx API](https://docx.js.org/api/),
[patchDocument](https://docx.js.org/api/functions/index.patchDocument.html),
[LibreOffice command line](https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html),
[Microsoft comments](https://learn.microsoft.com/en-us/office/open-xml/word/how-to-retrieve-comments-from-a-word-processing-document),
[reply paragraph IDs](https://learn.microsoft.com/en-us/openspecs/office_standards/ms-docx/9660dacc-2ceb-4352-87d2-42ba1184f522),
and [Pandoc options](https://pandoc.org/MANUAL.html#option--track-changes).
Creation, placeholder patching, PDF rendering, comments, and revision acceptance
were smoke-tested with docx 9.8.1, LibreOffice 26.2.4.2, Pandoc 3.11, and Poppler
26.09.0. Microsoft Word and Google Docs rendering were not tested.

---

*This skill is created and maintained by [Anthropic](https://github.com/anthropics/skills/tree/main/skills/docx). Adapted here with frontmatter metadata and editing-scope guidance; see LICENSE.txt for terms.*
