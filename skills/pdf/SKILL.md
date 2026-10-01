---
name: pdf
description: Processes PDF files by extracting text and tables, merging, splitting, rotating, watermarking, creating documents, filling forms, encrypting or decrypting, extracting images, and running OCR. Used when a task involves reading, editing, creating, or validating a .pdf file.
license: Proprietary. LICENSE.txt has complete terms
compatibility: Requires Python 3.12+ and task-specific PDF packages. Poppler is needed for pdf2image; Tesseract and language data for OCR. Optional Node.js for JavaScript examples, qpdf/PDFtk/ImageMagick for their CLI examples. No API credentials required.
metadata:
  version: "1.4"
  last-reviewed: "2026-09-30"
  skill-author: Anthropic, PBC
  source: https://github.com/anthropics/skills/tree/main/skills/pdf
---

# PDF Processing Guide

## Overview

This guide covers essential PDF processing operations using Python libraries and command-line tools. For advanced features, JavaScript libraries, and detailed examples, see [reference.md](reference.md). If you need to fill out a PDF form, read [forms.md](forms.md) and follow its instructions.

## Environment and validation

The Python examples were exercised with pypdf 6.19.0, pdfplumber 0.11.10,
pypdfium2 5.13.0, ReportLab 5.0.1, and pdf2image 1.17.0 on synthetic PDFs.
Install only what the task needs; for example:

```bash
uv pip install 'pypdf[crypto]==6.19.0' pdfplumber==0.11.10 reportlab==5.0.1 pdf2image==1.17.0 pillow
# Optional table-to-Excel and OCR examples:
uv pip install pandas openpyxl pytesseract
```

Preserve the source PDF and write a separate result. Reopen results, check page
counts and extracted values, then render every changed page to inspect clipping,
fonts, form values, and placement. Text extraction is not visual validation.
For research tables, retain page provenance and check units, decimal separators,
minus signs, and merged cells against the page before analyzing the data.

## Quick Start

```python
from pypdf import PdfReader, PdfWriter

# Read a PDF
reader = PdfReader("document.pdf")
print(f"Pages: {len(reader.pages)}")

# Extract text
text = ""
for page in reader.pages:
    text += (page.extract_text() or "") + "\n"
```

## Python Libraries

### pypdf - Basic Operations

#### Merge PDFs
```python
from pypdf import PdfWriter, PdfReader

writer = PdfWriter()
for pdf_file in ["doc1.pdf", "doc2.pdf", "doc3.pdf"]:
    writer.append(pdf_file)

with open("merged.pdf", "wb") as output:
    writer.write(output)
```

Use `append` to preserve document/form structure. When merging forms with
colliding field names, first namespace each reader with `reader.add_form_topname("source1")`.

#### Split PDF
```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("input.pdf")
for i, page in enumerate(reader.pages):
    writer = PdfWriter()
    writer.append(reader, pages=[i])
    with open(f"page_{i+1}.pdf", "wb") as output:
        writer.write(output)
```

#### Extract Metadata
```python
from pypdf import PdfReader

reader = PdfReader("document.pdf")
meta = reader.metadata
if meta is not None:
    print(meta.title, meta.author, meta.subject, meta.creator)
```

#### Rotate Pages
```python
from pypdf import PdfReader, PdfWriter

writer = PdfWriter(clone_from="input.pdf")
writer.pages[0].rotate(90)  # Rotate 90 degrees clockwise

with open("rotated.pdf", "wb") as output:
    writer.write(output)
```

### pdfplumber - Text and Table Extraction

#### Extract Text with Layout
```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    for page in pdf.pages:
        text = page.extract_text(layout=True)
        print(text)
```

#### Extract Tables
```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    for i, page in enumerate(pdf.pages):
        tables = page.extract_tables()
        for j, table in enumerate(tables):
            print(f"Table {j+1} on page {i+1}:")
            for row in table:
                print(row)
```

#### Advanced Table Extraction
```python
import pdfplumber
import pandas as pd

with pdfplumber.open("document.pdf") as pdf:
    all_tables = []
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            if table:  # Check if table is not empty
                df = pd.DataFrame(table[1:], columns=table[0])
                all_tables.append(df)

# Combine only tables verified to have the same schema and units
if all_tables:
    combined_df = pd.concat(all_tables, ignore_index=True)
    combined_df.to_excel("extracted_tables.xlsx", index=False, engine="openpyxl")
```

### reportlab - Create PDFs

#### Basic PDF Creation
```python
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

c = canvas.Canvas("hello.pdf", pagesize=letter)
width, height = letter

# Add text
c.drawString(100, height - 100, "Hello World!")
c.drawString(100, height - 120, "This is a PDF created with reportlab")

# Add a line
c.line(100, height - 140, 400, height - 140)

# Save
c.save()
```

#### Create PDF with Multiple Pages
```python
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet

doc = SimpleDocTemplate("report.pdf", pagesize=letter)
styles = getSampleStyleSheet()
story = []

# Add content
title = Paragraph("Report Title", styles['Title'])
story.append(title)
story.append(Spacer(1, 12))

body = Paragraph("This is the body of the report. " * 20, styles['Normal'])
story.append(body)
story.append(PageBreak())

# Page 2
story.append(Paragraph("Page 2", styles['Heading1']))
story.append(Paragraph("Content for page 2", styles['Normal']))

# Build PDF
doc.build(story)
```

#### Subscripts and Superscripts

The built-in fonts do not cover all Unicode subscript/superscript glyphs. Use Paragraph markup below, or embed a font with verified glyph coverage and inspect the rendered result.

Instead, use ReportLab's XML markup tags in Paragraph objects:
```python
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet

styles = getSampleStyleSheet()

# Subscripts: use <sub> tag
chemical = Paragraph("H<sub>2</sub>O", styles['Normal'])

# Superscripts: use <super> tag
squared = Paragraph("x<super>2</super> + y<super>2</super>", styles['Normal'])
```

For canvas-drawn text (not Paragraph objects), manually adjust the font size and position rather than using Unicode subscripts/superscripts.

## Command-Line Tools

### pdftotext (poppler-utils)
```bash
# Extract text
pdftotext input.pdf output.txt

# Extract text preserving layout
pdftotext -layout input.pdf output.txt

# Extract specific pages
pdftotext -f 1 -l 5 input.pdf output.txt  # Pages 1-5
```

### qpdf

These qpdf and PDFtk commands were checked against official manuals; their native
executables were unavailable for this review, so these are illustrative commands.
```bash
# Merge PDFs
qpdf --empty --pages file1.pdf file2.pdf -- merged.pdf

# Split pages
qpdf input.pdf --pages . 1-5 -- pages1-5.pdf
qpdf input.pdf --pages . 6-10 -- pages6-10.pdf

# Rotate pages
qpdf input.pdf output.pdf --rotate=+90:1  # Rotate page 1 by 90 degrees

# Remove password
qpdf --password=mypassword --decrypt encrypted.pdf decrypted.pdf
```

### pdftk (if available)
```bash
# Merge
pdftk file1.pdf file2.pdf cat output merged.pdf

# Split
pdftk input.pdf burst

# Rotate
pdftk input.pdf cat 1east 2-end output rotated.pdf  # Requires at least 2 pages
```

## Common Tasks

### Extract Text from Scanned PDFs

Install the native tools as well as the Python packages: `pdf2image` requires
Poppler (`pdftoppm`/`pdftocairo`), and `pytesseract` requires the Tesseract
executable plus language data for the document. Python package installation alone
does not provide these dependencies. For long PDFs, render bounded page ranges
or use an output directory to avoid holding every page image in RAM. Check a
representative page for reading order, symbols, and numeric accuracy before
using OCR text as research data. See the [pdf2image installation guide](https://pdf2image.readthedocs.io/en/latest/installation.html)
and [pytesseract prerequisites](https://github.com/madmaze/pytesseract).
```python
# Requires: uv pip install pytesseract pdf2image
import pytesseract
from pdf2image import convert_from_path, pdfinfo_from_path

text = ""
count = pdfinfo_from_path('scanned.pdf', timeout=60)['Pages']
for number in range(1, count + 1):
    image = convert_from_path('scanned.pdf', first_page=number, last_page=number,
                              dpi=200, timeout=120)[0]
    try:
        text += f"Page {number}:\n" + pytesseract.image_to_string(image, lang='eng', timeout=60) + "\n\n"
    finally:
        image.close()

print(text)
```

The OCR example returns text. To create a searchable PDF, Tesseract also exposes
`pytesseract.image_to_pdf_or_hocr(image, extension="pdf")`; inspect OCR quality and
merge the resulting page PDFs with pypdf. Rendering loses original vector/form structure.

### Add Watermark
```python
from pypdf import PdfReader, PdfWriter

# Create watermark (or load existing)
watermark = PdfReader("watermark.pdf").pages[0]

# Apply to all pages
writer = PdfWriter(clone_from="document.pdf")
for page in writer.pages:
    page.transfer_rotation_to_content()
    page.merge_page(watermark)  # Assumes watermark coordinates match the page size

with open("watermarked.pdf", "wb") as output:
    writer.write(output)
```

### Extract Images
```bash
# Using pdfimages (poppler-utils)
pdfimages -j input.pdf output_prefix

# JPEG images stay JPEG; other image types may be emitted as PBM/PPM.
# Use -all to preserve supported native image encodings, not for vector figures.
```

### Password Protection
```python
from pypdf import PdfReader, PdfWriter

writer = PdfWriter(clone_from="input.pdf")

# Use task-provided passwords; requires pypdf[crypto]. Omitting algorithm uses RC4.
writer.encrypt("userpassword", "ownerpassword", algorithm="AES-256")

with open("encrypted.pdf", "wb") as output:
    writer.write(output)
```

## Form routing

Follow [forms.md](forms.md): inspect for AcroForms first, extract field IDs and
all widget locations, validate values, fill, then reopen and render affected pages.
XFA, signatures, and pushbuttons require specialized handling. Static forms use
structure-derived or visually measured boxes followed by coordinate checks.
The FreeText helper supports unrotated zero-origin pages with matching page boxes;
its annotations depend on viewer support and are not flattened content. Use a
ReportLab overlay when fixed page content is required, and visually verify it.

## Quick Reference

| Task | Best Tool | Command/Code |
|------|-----------|--------------|
| Merge PDFs | pypdf | `writer.append(path)` |
| Split PDFs | pypdf | One page per file |
| Extract text | pdfplumber | `page.extract_text()` |
| Extract tables | pdfplumber | `page.extract_tables()` |
| Create PDFs | reportlab | Canvas or Platypus |
| Command line merge | qpdf | `qpdf --empty --pages ...` |
| OCR scanned PDFs | pytesseract | Convert to image first |
| Fill PDF forms | pdf-lib or pypdf (see forms.md) | See forms.md |

## Upstream references

Reviewed official [pypdf forms](https://pypdf.readthedocs.io/en/stable/user/forms.html),
[encryption](https://pypdf.readthedocs.io/en/stable/user/encryption-decryption.html),
[pdfplumber](https://github.com/jsvine/pdfplumber),
[ReportLab](https://docs.reportlab.com/reportlab/userguide/ch2_graphics/),
[qpdf](https://qpdf.readthedocs.io/en/stable/cli.html), and
[PDFtk](https://www.pdflabs.com/docs/pdftk-man-page/).

## Next Steps

- For advanced pypdfium2 usage, see reference.md
- For JavaScript libraries (pdf-lib), see reference.md
- If you need to fill out a PDF form, follow the instructions in forms.md
- For troubleshooting guides, see reference.md

---

*This skill is created and maintained by [Anthropic](https://github.com/anthropics/skills/tree/main/skills/pdf). Adapted here with frontmatter metadata, lowercase `reference.md`/`forms.md` links, and local workflow clarifications; see LICENSE.txt for terms.*
