# PDF Processing Advanced Reference

This document contains advanced PDF processing features, detailed examples, and additional libraries not covered in the main skill instructions.

## pypdfium2 Library (Apache/BSD License)

### Overview
pypdfium2 is a Python binding for PDFium (Chromium's PDF library). It's excellent for fast PDF rendering, image generation, and serves as a PyMuPDF replacement.

### Render PDF to Images

This example targets pypdfium2 5.13.0. The PIL image may share the bitmap's
buffer: save or copy it before closing the bitmap. Close pages promptly and use
processes, not concurrent threads, for PDFium work.

```python
import pypdfium2 as pdfium

with pdfium.PdfDocument("document.pdf") as pdf:
    pdf.init_forms()  # Needed for interactive form rendering when present
    for i in range(len(pdf)):
        page = pdf[i]
        try:
            bitmap = page.render(scale=2.0, rotation=0)
            try:
                image = bitmap.to_pil()
                image.save(f"page_{i+1}.png")
                image.close()
            finally:
                bitmap.close()
        finally:
            page.close()
```

### Extract Text with pypdfium2
```python
import pypdfium2 as pdfium

with pdfium.PdfDocument("document.pdf") as pdf:
    for i in range(len(pdf)):
        page = pdf[i]
        textpage = page.get_textpage()
        try:
            text = textpage.get_text_bounded()
            print(f"Page {i+1} text length: {len(text)} chars")
        finally:
            textpage.close()
            page.close()
```

Official [API and resource lifetime documentation](https://pypdfium2.readthedocs.io/en/stable/python_api.html).

## JavaScript Libraries

### pdf-lib (MIT License)

The following examples were exercised with pdf-lib 1.17.1. It creates and modifies
PDFs in JavaScript. These `.mjs` examples
use Node.js and `npm install pdf-lib`; they operate on local fixture files.
Page indices are zero-based. Copying pages is not a promise to preserve forms,
bookmarks, or signatures; validate document-level structures separately.

#### Load and Manipulate Existing PDF
```javascript
import { PDFDocument } from 'pdf-lib';
import fs from 'fs';

async function manipulatePDF() {
    // Load existing PDF
    const existingPdfBytes = fs.readFileSync('input.pdf');
    const pdfDoc = await PDFDocument.load(existingPdfBytes);

    // Get page count
    const pageCount = pdfDoc.getPageCount();
    console.log(`Document has ${pageCount} pages`);

    // Add new page
    const newPage = pdfDoc.addPage([600, 400]);
    newPage.drawText('Added by pdf-lib', {
        x: 100,
        y: 300,
        size: 16
    });

    // Save modified PDF
    const pdfBytes = await pdfDoc.save();
    fs.writeFileSync('modified.pdf', pdfBytes);
}
await manipulatePDF();
```

#### Create Complex PDFs from Scratch
```javascript
import { PDFDocument, rgb, StandardFonts } from 'pdf-lib';
import fs from 'fs';

async function createPDF() {
    const pdfDoc = await PDFDocument.create();

    // Add fonts
    const helveticaFont = await pdfDoc.embedFont(StandardFonts.Helvetica);
    const helveticaBold = await pdfDoc.embedFont(StandardFonts.HelveticaBold);

    // Add page
    const page = pdfDoc.addPage([595, 842]); // A4 size
    const { width, height } = page.getSize();

    // Add text with styling
    page.drawText('Invoice #12345', {
        x: 50,
        y: height - 50,
        size: 18,
        font: helveticaBold,
        color: rgb(0.2, 0.2, 0.8)
    });

    // Add rectangle (header background)
    page.drawRectangle({
        x: 40,
        y: height - 100,
        width: width - 80,
        height: 30,
        color: rgb(0.9, 0.9, 0.9)
    });

    // Add table-like content
    const items = [
        ['Item', 'Qty', 'Price', 'Total'],
        ['Widget', '2', '$50', '$100'],
        ['Gadget', '1', '$75', '$75']
    ];

    let yPos = height - 150;
    items.forEach(row => {
        let xPos = 50;
        row.forEach(cell => {
            page.drawText(cell, {
                x: xPos,
                y: yPos,
                size: 12,
                font: helveticaFont
            });
            xPos += 120;
        });
        yPos -= 25;
    });

    const pdfBytes = await pdfDoc.save();
    fs.writeFileSync('created.pdf', pdfBytes);
}
await createPDF();
```

#### Advanced Merge and Split Operations
```javascript
import { PDFDocument } from 'pdf-lib';
import fs from 'fs';

async function mergePDFs() {
    // Create new document
    const mergedPdf = await PDFDocument.create();

    // Load source PDFs
    const pdf1Bytes = fs.readFileSync('doc1.pdf');
    const pdf2Bytes = fs.readFileSync('doc2.pdf');

    const pdf1 = await PDFDocument.load(pdf1Bytes);
    const pdf2 = await PDFDocument.load(pdf2Bytes);

    // Copy pages from first PDF
    const pdf1Pages = await mergedPdf.copyPages(pdf1, pdf1.getPageIndices());
    pdf1Pages.forEach(page => mergedPdf.addPage(page));

    // Copy specific pages from second PDF (pages 0, 2, 4)
    const pdf2Pages = await mergedPdf.copyPages(pdf2, [0, 2, 4]);
    pdf2Pages.forEach(page => mergedPdf.addPage(page));

    const mergedPdfBytes = await mergedPdf.save();
    fs.writeFileSync('merged.pdf', mergedPdfBytes);
}
await mergePDFs();
```

### pdfjs-dist (Apache License)

PDF.js renders PDFs in the browser. These browser examples are illustrative
(documentation-checked; the browser DOM path was not executed). Serve them over
HTTP with the PDF on the same origin or correctly configured CORS. Copy
`pdf.mjs` and `pdf.worker.mjs` from the **same installed version** of
`pdfjs-dist/build/` beside the module. Also serve that package's `cmaps/`,
`standard_fonts/`, and `wasm/` directories at the URLs below. API calls were
exercised with pdfjs-dist 6.3.289 under Node.js; deployment of the browser worker
and these assets still needs a browser check. PDF.js is not a general PDF editor.
See the [examples](https://mozilla.github.io/pdf.js/examples/) and
[current rendering contract](https://mozilla.github.io/pdf.js/api/draft/module-pdfjsLib.html).

#### Basic PDF Loading and Rendering
```javascript
import * as pdfjsLib from './pdf.mjs';

// Configure worker (important for performance)
pdfjsLib.GlobalWorkerOptions.workerSrc = new URL('./pdf.worker.mjs', import.meta.url).href;

async function renderPDF() {
    // Load PDF
    const loadingTask = pdfjsLib.getDocument({url: 'document.pdf', cMapUrl: './cmaps/', cMapPacked: true,
        standardFontDataUrl: './standard_fonts/', wasmUrl: './wasm/'});
    const pdf = await loadingTask.promise;

    console.log(`Loaded PDF with ${pdf.numPages} pages`);

    // Get first page
    const page = await pdf.getPage(1);
    const viewport = page.getViewport({ scale: 1.5 });

    // Render to canvas
    const canvas = document.createElement('canvas');
    canvas.height = viewport.height;
    canvas.width = viewport.width;

    const renderContext = {
        canvas: canvas,
        viewport: viewport
    };

    await page.render(renderContext).promise;
    document.body.appendChild(canvas);
    await loadingTask.destroy();
}
await renderPDF();
```

#### Extract Text with Coordinates
```javascript
import * as pdfjsLib from './pdf.mjs';

pdfjsLib.GlobalWorkerOptions.workerSrc = new URL('./pdf.worker.mjs', import.meta.url).href;

async function extractText() {
    const loadingTask = pdfjsLib.getDocument({url: 'document.pdf', cMapUrl: './cmaps/', cMapPacked: true,
        standardFontDataUrl: './standard_fonts/', wasmUrl: './wasm/'});
    const pdf = await loadingTask.promise;

    let fullText = '';

    // Extract text from all pages
    for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const textContent = await page.getTextContent();

        const items = textContent.items.filter(item => 'str' in item);
        const pageText = items
            .map(item => item.str)
            .join(' ');

        fullText += `\n--- Page ${i} ---\n${pageText}`;

        // Get text with coordinates for advanced processing
        const textWithCoords = items.map(item => ({
            text: item.str,
            x: item.transform[4],
            y: item.transform[5],
            width: item.width,
            height: item.height
        }));
    }

    console.log(fullText);
    await loadingTask.destroy();
    return fullText;
}
await extractText();
```

#### Extract Annotations and Forms
```javascript
import * as pdfjsLib from './pdf.mjs';

pdfjsLib.GlobalWorkerOptions.workerSrc = new URL('./pdf.worker.mjs', import.meta.url).href;

async function extractAnnotations() {
    const loadingTask = pdfjsLib.getDocument({url: 'annotated.pdf', cMapUrl: './cmaps/', cMapPacked: true,
        standardFontDataUrl: './standard_fonts/', wasmUrl: './wasm/'});
    const pdf = await loadingTask.promise;

    for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const annotations = await page.getAnnotations();

        annotations.forEach(annotation => {
            console.log(`Annotation type: ${annotation.subtype}`);
            console.log(`Content: ${annotation.contentsObj?.str ?? ''}`);
            console.log(`Coordinates: ${JSON.stringify(annotation.rect)}`);
        });
    }
    await loadingTask.destroy();
}
await extractAnnotations();
```

## Advanced Command-Line Operations

Poppler commands were exercised locally. qpdf commands below are illustrative,
checked against its 12.4.2 manual; the native qpdf executable was unavailable.

### poppler-utils Advanced Features

#### Extract Text with Bounding Box Coordinates
```bash
# Extract words with bounding boxes and layout blocks as XHTML
pdftotext -bbox-layout document.pdf output.xml

# The XML output contains precise coordinates for each text element
```

#### Advanced Image Conversion
```bash
# Convert to PNG images with specific resolution
pdftoppm -png -r 300 document.pdf output_prefix

# Convert specific page range with high resolution
pdftoppm -png -r 600 -f 1 -l 3 document.pdf high_res_pages

# Convert to JPEG with quality setting
pdftoppm -jpeg -jpegopt quality=85 -r 200 document.pdf jpeg_output
```

#### Extract Embedded Images
```bash
# Extract images with page numbers in names (not metadata sidecars)
pdfimages -j -p document.pdf page_images

# List image info without extracting
pdfimages -list document.pdf

# Extract images in their original format
mkdir -p images
pdfimages -all document.pdf images/img
```

### qpdf Advanced Features

#### Complex Page Manipulation
```bash
# Split PDF into groups of pages
qpdf --split-pages=3 input.pdf output_group.pdf

# Extract specific pages with complex ranges
qpdf input.pdf --pages input.pdf 1,3-5,8,10-end -- extracted.pdf

# Merge specific pages from multiple PDFs
qpdf --empty --pages doc1.pdf 1-3 doc2.pdf 5-7 doc3.pdf 2,4 -- combined.pdf
```

#### PDF Optimization and Repair
```bash
# Optimize PDF for web (linearize for streaming)
qpdf --linearize input.pdf optimized.pdf

# Lossless stream/object compression; may not shrink an already optimized PDF
qpdf --object-streams=generate --recompress-flate --compression-level=9 input.pdf compressed.pdf

# Attempt to repair corrupted PDF structure
qpdf --check input.pdf
qpdf damaged.pdf repaired.pdf  # Best-effort structural recovery during rewrite

# Show detailed PDF structure for debugging
qpdf --show-pages input.pdf > structure.txt
```

#### Advanced Encryption
```bash
# Add password protection with specific permissions
qpdf --encrypt user_pass owner_pass 256 --print=none --modify=none -- input.pdf encrypted.pdf

# Check encryption status
qpdf --show-encryption encrypted.pdf

# Remove password protection (requires password)
qpdf --password=secret123 --decrypt encrypted.pdf decrypted.pdf
```

## Advanced Python Techniques

### pdfplumber Advanced Features

#### Extract Text with Precise Coordinates
```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    page = pdf.pages[0]
    
    # Extract all text with coordinates
    chars = page.chars
    for char in chars[:10]:  # First 10 characters
        print(f"Char: '{char['text']}' at x:{char['x0']:.1f} y:{char['y0']:.1f}")
    
    # Extract text by bounding box (left, top, right, bottom)
    bbox_text = page.within_bbox((100, 100, 400, 200)).extract_text()
```

#### Advanced Table Extraction with Custom Settings
```python
import pdfplumber
import pandas as pd

with pdfplumber.open("complex_table.pdf") as pdf:
    page = pdf.pages[0]
    
    # Extract tables with custom settings for complex layouts
    table_settings = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 3,
        "intersection_tolerance": 15
    }
    tables = page.extract_tables(table_settings)
    
    # Visual debugging for table extraction
    img = page.to_image(resolution=150)
    img.debug_tablefinder(table_settings)
    img.save("debug_layout.png")
```

### reportlab Advanced Features

#### Create Professional Reports with Tables
```python
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# Sample data
data = [
    ['Product', 'Q1', 'Q2', 'Q3', 'Q4'],
    ['Widgets', '120', '135', '142', '158'],
    ['Gadgets', '85', '92', '98', '105']
]

# Create PDF with table
doc = SimpleDocTemplate("report.pdf")
elements = []

# Add title
styles = getSampleStyleSheet()
title = Paragraph("Quarterly Sales Report", styles['Title'])
elements.append(title)

# Add table with advanced styling
table = Table(data)
table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 14),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
    ('GRID', (0, 0), (-1, -1), 1, colors.black)
]))
elements.append(table)

doc.build(elements)
```

## Complex Workflows

### Extract Figures/Images from PDF

#### Method 1: Using pdfimages (fastest)
```bash
# Extract all images with original quality
mkdir -p images
pdfimages -all document.pdf images/img
```

#### Method 2: Render and crop a known region

Use the pypdfium2 renderer above, then crop a region whose boundaries you have
visually checked. A non-white pixel mask also selects text, rules, and backgrounds;
it is not a validated figure detector. Rendering produces pixels at the chosen
scale and does not recover original vector figures. Preserve the page number,
rendering scale, and crop coordinates with the exported image.

### Batch PDF Processing with Error Handling

This example logs failures and produces partial results; inspect the log before
using the merged PDF. Keep output outside the input directory.
```python
import os
import glob
from pypdf import PdfReader, PdfWriter
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def batch_process_pdfs(input_dir, operation='merge'):
    pdf_files = sorted(glob.glob(os.path.join(input_dir, "*.pdf")))
    
    if operation == 'merge':
        writer = PdfWriter()
        for pdf_file in pdf_files:
            try:
                writer.append(pdf_file)
                logger.info(f"Processed: {pdf_file}")
            except Exception as e:
                logger.error(f"Failed to process {pdf_file}: {e}")
                continue
        
        with open("batch_merged.pdf", "wb") as output:
            writer.write(output)
    
    elif operation == 'extract_text':
        for pdf_file in pdf_files:
            try:
                reader = PdfReader(pdf_file)
                text = ""
                for page in reader.pages:
                    text += (page.extract_text() or "") + "\n"
                
                output_file = pdf_file.replace('.pdf', '.txt')
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(text)
                logger.info(f"Extracted text from: {pdf_file}")
                
            except Exception as e:
                logger.error(f"Failed to extract text from {pdf_file}: {e}")
                continue
```

### Advanced PDF Cropping

Cropping changes the visible area. It does not delete hidden content and must
never be treated as redaction. Coordinates below assume an unrotated page large
enough to contain the requested rectangle.
```python
from pypdf import PdfWriter, PdfReader

reader = PdfReader("input.pdf")
writer = PdfWriter()

# Crop page (left, bottom, right, top in points)
page = reader.pages[0]
page.cropbox.left = 50
page.cropbox.bottom = 50
page.cropbox.right = 550
page.cropbox.top = 750

writer.add_page(page)
with open("cropped.pdf", "wb") as output:
    writer.write(output)
```

## Performance Optimization Tips

### 1. For Large PDFs
- Render bounded page ranges; one high-DPI raster alone may be large
- Use `qpdf --split-pages` for splitting large files
- Process pages individually with pypdfium2

### 2. For Text Extraction
- Use `pdftotext` for plain text and `-bbox-layout` when coordinates are needed
- Use pdfplumber for structured data and tables
- Benchmark `page.extract_text()` on representative content; scanned images need OCR

### 3. For Image Extraction
- `pdfimages` extracts embedded raster objects without rendering page contents
- Use low resolution for previews, high resolution for final output

### 4. For Form Filling
- Use the AcroForm workflow in [forms.md](forms.md); XFA and signatures need specialized handling
- Pre-validate form fields before processing

### 5. Memory Management
```python
# Bounds each output writer, not all reader memory.
from pypdf import PdfReader, PdfWriter

def process_large_pdf(pdf_path, chunk_size=10):
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    
    for start_idx in range(0, total_pages, chunk_size):
        end_idx = min(start_idx + chunk_size, total_pages)
        writer = PdfWriter()
        
        writer.append(reader, pages=list(range(start_idx, end_idx)))
        
        # Process chunk
        with open(f"chunk_{start_idx//chunk_size}.pdf", "wb") as output:
            writer.write(output)
```

## Troubleshooting Common Issues

### Encrypted PDFs
```python
# Handle password-protected PDFs
from pypdf import PdfReader

try:
    reader = PdfReader("encrypted.pdf")
    if reader.is_encrypted:
        if not reader.decrypt("password"):
            raise ValueError("Incorrect password")
except Exception as e:
    print(f"Failed to decrypt: {e}")
```

### Corrupted PDFs
```bash
# Use qpdf to repair
qpdf --check corrupted.pdf
qpdf corrupted.pdf recovered.pdf
qpdf --check recovered.pdf
```

### Text Extraction Issues

Use the bounded OCR loop in [SKILL.md](SKILL.md). It needs Poppler, Tesseract,
and installed language data, in addition to Python packages. Incorrect Unicode
maps can require OCR even when a PDF contains text. Compare numeric and symbolic
content against the rendered page; OCR alone does not validate research data.

## License Information

- **pypdf**: BSD License
- **pdfplumber**: MIT License
- **pypdfium2**: Apache/BSD License
- **reportlab**: BSD License
- **poppler-utils**: GPL-2 License
- **qpdf**: Apache License
- **pdf-lib**: MIT License
- **pdfjs-dist**: Apache License

License summaries describe upstream dependencies, not the license of this skill.
Preserve LICENSE.txt. See [pdf-lib API](https://pdf-lib.js.org/docs/api/classes/pdfdocument),
[ReportLab tables](https://docs.reportlab.com/reportlab/userguide/ch7_tables/),
[pdf2image API](https://pdf2image.readthedocs.io/en/latest/reference.html), and
[qpdf CLI](https://qpdf.readthedocs.io/en/stable/cli.html) for the contracts reviewed.
