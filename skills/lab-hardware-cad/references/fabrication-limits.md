# Fabrication limits, tolerances, and materials

Read this before finalising any geometry. Process determines what geometry is possible; material
determines whether the part survives the lab.

## Process tolerances

Achievable tolerance and minimum feature size, as planning figures. **Every number here depends on
the specific machine, material, and operator.** Use them to choose a process and to size a first
article, then verify with a test coupon.

| Process | Typical tolerance | Min wall | Min feature | Notes |
| --- | --- | --- | --- | --- |
| FDM | ±0.3 mm (often worse over 100 mm) | 1.2 mm (3 x 0.4 mm nozzle) | ~0.8 mm | Anisotropic: much weaker across layers. Porous. |
| SLA / DLP | ±0.1 mm | 0.8 mm | ~0.3 mm | Better surface and detail. Resin choice dominates properties. |
| SLS (nylon) | ±0.2 mm | 0.8 mm | ~0.5 mm | Often less anisotropic than FDM; no supports; porous surface. |
| CNC milling | ±0.05 mm or better | 0.8 mm in metal | Set by tool diameter | Internal corners carry the tool radius — you cannot mill a sharp internal corner. |
| Laser cutting | ±0.1 mm | n/a | Kerf ~0.1-0.3 mm | 2D only. Edge taper on thick stock. Kerf offset must be applied. |

Two consequences that catch people:

- **Holes print undersize** on both FDM and SLA. A 6.0 mm modelled hole typically measures under
  6.0 mm. Oversize functional bores, or plan to ream them.
- **Internal corners cannot be sharp in milling.** If a milled pocket must accept a square part,
  add corner relief cuts. (For a part with *rounded* corners the tool radius is harmless as long
  as it stays at or below the part's minimum corner radius — see the corner-radius rule in
  `references/labware-adapters.md`.)

### Laser cutting

- **Kerf direction is fixed by the physics, so get it right in the handover.** The beam removes a
  strip of width k (~0.1–0.3 mm) centred on the drawn line. Cutting on the line therefore makes
  **holes and internal cutouts come out oversize by ~k, and the part's outer outline undersize by
  ~k**. Say which convention the DXF uses (on-the-line is the default assumption) and let the shop
  offset, or offset the geometry yourself and say so — never both.
- **Put cut geometry on a named layer** (one layer per operation: `CUT`, `ENGRAVE`). Shops key
  power and speed to layer or colour; geometry on layer 0 forces them to guess.
- **Cut order matters:** internal features before the outer outline, or the part shifts once it is
  freed from the sheet.
- **Sheet stock is not its nominal thickness.** "3 mm" acrylic commonly runs ~2.8–3.2 mm; slots
  sized for nominal will be loose or tight. For solvent-welded joints prefer **cast** acrylic over
  extruded — cleaner cut edge, less vapour crazing — and remember alcohols craze acrylic either
  way (see Chemical, below).
- Laser-cut edges are sharp and slightly tapered; call out deburring or flame-polishing for
  anything handled or animal-facing.

## Fits and clearances

Nominal dimensions do not produce fits. Choose a clearance deliberately, per side:

| Fit | FDM | SLA | CNC |
| --- | --- | --- | --- |
| Free-sliding (a plate dropping into a pocket) | 0.40 mm | 0.20 mm | 0.10 mm |
| Located but removable by hand | 0.25 mm | 0.10 mm | 0.05 mm |
| Press / interference | Coupon-specific | Coupon-specific | Use a toleranced shaft/hole fit |

For a guaranteed free fit, receiving-feature CAD size minus its undersize tolerance
must exceed the mating part's maximum size plus the required functional gap.
A nominal allowance is not the guaranteed assembled clearance.

Then remember the **other** part has tolerance too. When mating to a standardised component,
design the receiving feature against the component's **maximum material condition**, not its
nominal — a pocket sized from nominal does not guarantee clearance for conforming parts. This is what
`intent: "envelope"` enforces. Declare it in the model and check the manifest:

```bash
python scripts/check.py interfaces out/part.manifest.json
```

Or check a single number by hand:

```bash
python scripts/check.py fit --standard slas-microplate-footprint \
  --intent envelope --clearance 0.8 --value footprint_length=129.06
```

## Threads and inserts

**Printed threads are usually a mistake.** Layer resolution is comparable to the thread pitch, so
printed threads are weak, dimensionally unreliable, and shed particles.

In descending order of preference:

1. **Heat-set threaded inserts** — the standard solution for printed parts. Model a straight bore
   to the insert manufacturer's specified diameter (it varies by insert; get the datasheet) and
   provide enough surrounding wall, typically at least 2 mm.
2. **Clearance hole plus a captive nut** in a hex pocket. Reliable and cheap.
3. **Tapping the printed material directly** — acceptable for light, infrequently-assembled joints.
4. **Printing the thread** — only for coarse threads (roughly M6 and above), never for fine
   threads like the 0.635 mm pitch SM1 (see `references/optomechanics.md`).

## Orientation and anisotropy

For FDM especially, orientation is a design decision, not a printing detail:

- Parts are substantially weaker **across** layers than along them. Orient so that load runs
  along layers, and state the intended orientation in the model docstring.
- Overhangs beyond roughly 45 degrees need support, and supported surfaces come out rough and
  dimensionally poor. If a surface is a sealing or mating face, orient it so it is not supported.
- Holes printed with their axis vertical are usually more circular; printed horizontally they come out with a
  drooped top. Teardrop or chamfer horizontal holes that must stay round.
- **Every enclosed cavity needs a drain path** in resin printing. See
  `references/microfluidics.md`.

## Materials

### Thermal

| Material | Approximate service limit | Autoclave (121 °C)? |
| --- | --- | --- |
| PLA | ~50-60 °C | **No** — distorts well below autoclave temperature |
| PETG | ~70-80 °C | No |
| ABS / ASA | ~90-100 °C | Marginal, generally no |
| Polypropylene | Grade/application dependent | Some molded labware is rated for 121 °C; printed parts need validation |
| Nylon (SLS) | ~120-160 °C | Sometimes; verify per grade |
| PEEK | Grade/load dependent | Often compatible; verify grade and cycles |
| Stainless steel, aluminium, glass | Grade/coating dependent | Often compatible; verify corrosion and thermal-shock limits |

**Assume a printed part is not autoclavable unless it is a verified high-temperature material.**
Offer chemical or gas sterilisation as the alternative, and check that against the solvent notes
below.

### Chemical

- **Acrylic (PMMA)** crazes on contact with alcohols, including 70% ethanol — a serious problem in
  a lab that disinfects everything with ethanol.
- **Polycarbonate** is attacked by many solvents and by some alkaline cleaners.
- **PLA** hydrolyses; it degrades in warm, wet, or repeatedly-cleaned service.
- **PP, PTFE, PEEK** have broad chemical resistance, but require compatibility checks for the exact
  chemical, concentration, temperature and exposure time; none is universally safe.

Always ask what the part will be cleaned with, not just what it will contain. Cleaning agent
compatibility is more often the failure than the sample.

### Biocompatibility

- **Uncured SLA resin is cytotoxic.** Even nominally biocompatible resins require the
  manufacturer's full post-cure and wash protocol, and leachables can still affect sensitive cell
  assays.
- For anything contacting cells, tissue, or animals: prefer glass, medical-grade polymer, or PTFE
  for the contact surface, and use the printed part as a holder that does not touch the sample.
- "Biocompatible" on a resin datasheet refers to a specific certified process and application. It
  does not transfer to your printer, your cure schedule, or your assay. Say this rather than
  implying a printed part is cell-safe.

### Optical

- Printed and milled surfaces scatter; they are not optical surfaces.
- Most printed resins **autofluoresce**, often strongly, which contaminates fluorescence readouts.
- Black is not automatically non-reflective.
- Where an optical surface is needed, use glass or a bonded film and model the holder around it.

## Cost and lead-time reality

Mention these when recommending a process: FDM is hours and pennies; SLA is hours and modest cost;
SLS and CNC are typically outsourced with days of lead time and much higher cost. For ±0.05 mm requirements, ask the supplier to confirm process capability and inspection
method; CNC or post-machining may be needed.

## Before fabrication

Work through `references/validation.md`.

## Review sources

The dimensional tables are illustrative planning values, not supplier acceptance criteria.

- Resin cure and biocompatibility are process-specific: <https://formlabs.com/support/Best-practices-for-post-curing-prints/>
- Polypropylene labware sterilisation: <https://www.thermofisher.com/de/de/home/life-science/lab-plasticware-supplies/plastic-material-selection/polypropylene-pp-labware.html>
- Grade/chemical/temperature compatibility: <https://documents.thermofisher.com/TFS-Assets/LCD/posters/LCD-Chemical-Resistance-Guide-GALSPCHEMRESPOSTER-EN.pdf>
