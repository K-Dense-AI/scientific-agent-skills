---
name: xlsx
description: "Creates, edits, analyzes, or converts Excel spreadsheets (.xlsx, .xlsm, .xltx) where the workbook file is the primary deliverable. Use for formulas, formatting, financial models, multi-sheet workbooks, and tabular cleanup exported to Excel. Also applies to .csv/.tsv when the user wants spreadsheet output. Do NOT use for Word documents, HTML reports, standalone Python scripts, database pipelines, or Google Sheets API work."
allowed-tools: Read Write Edit Bash Grep Glob
license: Proprietary. LICENSE.txt has complete terms
metadata:
  version: "2.5"
  last-reviewed: "2026-09-30"
  skill-author: Anthropic, PBC
  adapted-by: K-Dense Inc.
  source: https://github.com/anthropics/skills/tree/main/skills/xlsx
compatibility: Requires Python 3.10+ and openpyxl 3.1.5; LibreOffice (soffice on PATH) for recalculation. Optional pandas and markitdown[xlsx] for tabular extraction. The Linux restricted-socket shim needs gcc. Network access is needed only to install dependencies.
---

# XLSX creation, editing, and analysis

| Task | Approach |
|---|---|
| **Create** or **edit** with formulas/formatting | `openpyxl` — see gotchas below |
| **Bulk data** in or out | `pandas` (`read_excel`, `to_excel`) |
| **Quick look** at a sheet | `markitdown file.xlsx` — `## SheetName` per sheet, no cell coordinates. Use openpyxl for `.xlsm` and precise edits |
| **Read** a model (formulas *and* values) | two `load_workbook` passes — see gotchas |

> Do not assume packages are preinstalled. Reuse a suitable environment or use `uv run --with openpyxl==3.1.5 python your_script.py`. Install optional tabular readers only when needed; MarkItDown requires its `xlsx` extra. The bundled workflow was exercised with openpyxl 3.1.5 and LibreOffice 26.2.4.2; current online LibreOffice help describes 26.8.

> Script paths below are relative to this skill's directory.

## Requirements for every output

- **Professional font** (Arial, Times New Roman) throughout, unless the user says otherwise.
- **Zero formula errors.** Never ship while `recalc.py` reports `errors_found`. If you think an error predates you, prove it: load the *original* with `data_only=True` and look at that cell. An error you introduced looks exactly like one you inherited.
- **Use formulas, never hardcoded results.** Write `sheet['B10'] = '=SUM(B2:B9)'`, not the Python-computed total. The sheet must recalculate when its inputs change.
- **Follow the user's spec literally.** Exact tab names, exact column headers, and the formula they spelled out. A redesign that computes something else fails, however elegant.
- **Document every assumption and hardcoded number** where the reader will see it — a cell comment, or an adjacent cell at a table's end. Cite a real source when one exists (`Source: Company 10-K, FY2024, Page 45, Revenue Note, [SEC EDGAR URL]`); when the number came from the user, say so plainly.
- **A workbook *you create* for someone to fill in** needs a short legend naming which cells to edit, and one example row of realistic values showing the expected format. Never add such a row to a file you were asked to edit.
- **Editing an existing file: match its conventions exactly.** They override every guideline here. Find its designated input cells first — a distinct font color, fill, or shading marks them — preserve its formulas unless the user requests formula changes. Make requested changes on a working copy.

## Recalculate and verify

openpyxl does not evaluate formulas. Saving through it removes worksheet formula caches;
`load_workbook(data_only=True)` then returns `None` for those formula cells until a spreadsheet
engine computes them. Input constants remain present. Setting `fullCalcOnLoad` alone does
not generate cached values.

```bash
python scripts/recalc.py output.xlsx 30   # optional timeout in seconds; default 30
python scripts/recalc.py --help
```

The helper runs LibreOffice `calculateAll()` on a staged copy with a temporary profile,
document macros disabled, and linked-document updates disabled. It checks that the file was
rewritten, original formula anchors remain, and formulas have caches (empty string results
are valid). On a successful check it replaces the original path atomically. **Keep a backup:**
LibreOffice can change formatting, embedded objects, formulas, and external links during export.
It is a calculation compatibility check, not native Excel certification or a network sandbox.

Read the JSON, not just the exit code:

- `status: success`: no typed error cells found. `total_formulas` counts formula cells including
  array anchors, not every output cell of an array.
- `status: errors_found`: recalculation completed and the file **was replaced**, but it contains
  typed Excel errors. Both statuses exit 0. `total_errors` and `error_summary` report errors;
  each type lists at most 100 locations with an optional `locations_truncated` count.
- An `error` key with no `status`: conversion or verification failed; the original was not
  replaced and the command exits 1. Invalid CLI arguments exit 2. Retain the original and
  investigate instead of treating this as a successful recalculation.

**A clean error scan does not prove correct results or complete array output.** Independently
check expected values, units, totals, formula ranges, and every intended array output cell.
Compare relevant styling, charts, links, and macros before/after; open or render the workbook
in its intended application and inspect column widths, number formats, print areas, and charts.
`office/validate.py` explicitly performs no XLSX schema validation; its exit code is not an
XLSX validity certificate.

### External links and protected features

`='[1]Returns Analysis'!$B$2` references another file through the workbook's external-reference
list. `keep_links=True` (openpyxl's default) preserves external-link data where supported;
it does **not** preserve cached results of worksheet formulas when saving. An unavailable
source may turn a previously cached result into an error after recalculation.

The helper refuses direct, named, and array references it recognizes when their worksheet
caches are absent. This is a partial guard: transitive names, charts, conditional formatting,
and other links may escape detection. `--force` bypasses it and accepts possible loss; use
only on a disposable copy. It does not supply missing source files or refresh linked data.
For important external links, VBA/UDFs, dynamic spills, controls, or other Excel-only features,
use a compatible Excel workflow and verify the actual target engine. If static values are
requested, extract them from the original cached-value load and label that conversion clearly.

## Choosing formulas that survive verification

Use English function names and commas in formulas written by openpyxl, even if Calc's UI
uses semicolons. OOXML functions added after the original specification may require `_xlfn.`;
some additionally use `_xlws.`. A prefix is not a guarantee of engine support.

- `SUMIFS`, `INDEX`, `MATCH`, `IFERROR`, and `SUMPRODUCT` remain useful portable choices.
- Prefix newer functions as required, for example `=_xlfn.TEXTJOIN(",",TRUE,A1:A3)`.
  Verify the exact formula in the deployed engine; do not infer support from its spelling.
- **Scalar XLOOKUP and XMATCH work in current LibreOffice.** Both were added in 24.8;
  `_xlfn.XLOOKUP(2,A1:A3,B1:B3)` and `_xlfn.XMATCH(2,A1:A3)` were exercised in 26.2.4.2.
  XMATCH returns a position; it is not a spilling array function.
- `SORT`, `FILTER`, `UNIQUE`, and `SEQUENCE` also exist since LibreOffice 24.8, but array
  storage matters. A bare `=_xlfn.SEQUENCE(3,1,1,1)` produced **only its first value** in
  the tested round trip with no error. Do not equate an error-free cell with a complete spill.
- For a **fixed output range**, openpyxl supports `ArrayFormula`; assign it to the range's
  top-left cell and verify every output. This does not promise an automatically resizing
  Excel dynamic spill. Use native Excel when resizing/spill semantics are required.

```python
from openpyxl import Workbook
from openpyxl.worksheet.formula import ArrayFormula

wb = Workbook()
ws = wb.active
ws["A1"] = ArrayFormula("A1:A3", "=_xlfn.SEQUENCE(3,1,1,1)")
wb.save("sequence.xlsx")
wb.close()
# Run recalc.py sequence.xlsx, then verify A1:A3 == [1, 2, 3].
```

## openpyxl gotchas

- **Reading a model takes two loads.** `data_only=True` yields cached values with the formulas gone; the default yields formula strings with no values. One pass cannot give you both.
- **`data_only=True` is destructive if you save.** That workbook has no formulas left, so saving replaces every one with a literal — permanently.
- **`data_only=True` on a file openpyxl just wrote returns `None` for formula cells** — run `recalc.py` first. (A formula whose result is `""` also reads back as `None`.)
- **Merged cells: write the top-left anchor only.** Every other cell in the range is a `MergedCell` whose `.value` is read-only.
- **`.xlsm` loses its macros unless you pass `keep_vba=True`** to `load_workbook`. This preserves VBA data, not every Excel feature. Before editing a feature-rich workbook, inventory shapes, controls, drawings, and other embedded objects; openpyxl does not preserve all of them. Save a working copy and compare those objects after saving and recalculation. If required objects cannot survive the round trip, use a compatible Excel workflow instead of delivering a stripped workbook.
- **Quote sheet names** in cross-sheet references: `='Assumptions Inputs'!$B$5`. Use `openpyxl.utils.cell.quote_sheetname(name)` to also escape apostrophes.
- **Rich text** needs `rich_text=True` on load if its cell-level formatting must survive.
- **Templates** require `wb.template=True` and a matching `.xltx`/`.xltm` extension; renaming an ordinary workbook is insufficient. The helper loads templates for editing with `AsTemplate=False`.
- **Untrusted text beginning with `=`** must stay text: assign it, then set the cell's `data_type = "s"`. Keep identifiers with leading zeros as strings, and explicit units/dates separate from measurements.

## Financial models

Unless the user says otherwise, or the existing file already does something else.

**Color:** blue text (`0,0,255`) for hardcoded inputs and scenario levers · black for formulas ·
green (`0,128,0`) for links to another sheet · red (`255,0,0`) for links to another file ·
yellow fill (`255,255,0`) for key assumptions and cells the user should fill in.

**Numbers:** currency `$#,##0`, with the unit named in the header (`Revenue ($mm)`) · zeros
render as `-` (`$#,##0;($#,##0);"-"`) · negatives in parentheses ·
percentages `0.0%;(0.0%);"-"`, **stored as fractions** (`0.15` renders `15.0%`; storing `15` renders
`1500.0%`) · valuation multiples `0.0"x"` · years as text (`"2024"`, never `2,024`).

**Structure:** every assumption in its own labeled cell, referenced by the formulas that use it
(`=B5*(1+$B$6)`, never `=B5*1.05`) · formulas consistent across every projection period, since a
lone edited cell mid-row is the commonest silent error · guard denominators that can be zero.

## Worked verification example

This small synthetic example was recalculated with LibreOffice 26.2.4.2. The concentrations
are illustrative, not experimental measurements. Preserve the formula workbook after recalc;
do not save the `data_only=True` verification load.

```python
from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import Font

wb = Workbook()
ws = wb.active
ws.title = "Dilution"
ws.append(["Sample", "Stock (mM)", "Stock volume (uL)", "Final volume (uL)", "Final (mM)"])
ws.append(["Example A", 10, 20, 100, "=B2*C2/D2"])
ws["A4"] = "Edit A2:D2; E2 calculates concentration. Synthetic example inputs."
ws["B2"].comment = Comment("Illustrative stock concentration; replace with measured input.", "Source")
for row in ws.iter_rows():
    for cell in row:
        cell.font = Font(name="Arial", size=11)
for cell in ws[1]:
    cell.font = Font(name="Arial", size=11, bold=True)
for col in "ABCDE":
    ws.column_dimensions[col].width = 22
ws["E2"].number_format = '0.00'
ws.freeze_panes = "A2"
wb.save("dilution.xlsx")
wb.close()
# Run: python scripts/recalc.py dilution.xlsx
# Then in a separate verification step:
# cached = load_workbook("dilution.xlsx", data_only=True)
# assert cached["Dilution"]["E2"].value == 2
# cached.close()
```

For a new table-only export, pandas supports
`df.to_excel("table.xlsx", sheet_name="Data", index=False, engine="openpyxl")`.
`pd.read_excel(path, sheet_name=None, engine="openpyxl")` reads all sheets into a dictionary;
choose `dtype`/`converters` and missing-value handling deliberately. A DataFrame round trip
is not a preservation workflow for styled models, formulas, or embedded objects.

## Dependencies and reviewed documentation

Recalculation needs openpyxl and a separately installed LibreOffice (`soffice` on `PATH`).
The shared OOXML utilities also use defusedxml and lxml. Optional pandas handles tabular data;
MarkItDown needs `markitdown[xlsx]` for XLSX conversion. Do not assume `.xlsm` support from
MarkItDown's XLSX converter: its documented source dispatch recognizes `.xlsx`/XLSX MIME.
No API credentials or remote service calls are required for workbook processing.

- [openpyxl loading, preservation, and templates](https://openpyxl.readthedocs.io/en/stable/tutorial.html)
- [openpyxl formulas and ArrayFormula](https://openpyxl.readthedocs.io/en/stable/simple_formulae.html)
- [pandas read_excel](https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html) and [to_excel](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_excel.html)
- [MarkItDown XLSX converter](https://github.com/microsoft/markitdown/blob/main/packages/markitdown/src/markitdown/converters/_xlsx_converter.py)
- [LibreOffice XLOOKUP](https://help.libreoffice.org/latest/en-US/text/scalc/01/func_xlookup.html), [XMATCH](https://help.libreoffice.org/latest/en-US/text/scalc/01/func_xmatch.html), and [SEQUENCE](https://help.libreoffice.org/latest/en-US/text/scalc/01/func_sequence.html)
- [LibreOffice document loading properties](https://api.libreoffice.org/docs/idl/ref/servicecom_1_1sun_1_1star_1_1document_1_1MediaDescriptor.html) and [calculateAll](https://api.libreoffice.org/docs/idl/ref/interfacecom_1_1sun_1_1star_1_1sheet_1_1XCalculatable.html)

---

*This skill originates from [Anthropic](https://github.com/anthropics/skills/tree/main/skills/xlsx). Adapted here with repository metadata and additional preservation guidance; see LICENSE.txt for terms.*
