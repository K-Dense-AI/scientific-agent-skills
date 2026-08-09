# Fabrication methods and design rules

The numbers here are the **single source of truth** for
`fabrication_check.py`; each is a typical published value (ledgered in
[source-ledger.md](source-ledger.md)) and *local process limits override
them*. Citations: Duffy 1998; Xia & Whitesides 1998; McDonald & Whitesides
2002; Eddings 2008; Berthier 2012.

## PDMS soft lithography (the prototyping default)

Process chain: CAD → photomask (chrome ≥ ~1–2 µm features; transparency film
≥ ~10 µm) → SU-8 spin/expose/develop on Si (the master) → silanise master →
cast PDMS 10:1 base:crosslinker → cure 65–80 °C → peel, punch ports → O₂
plasma bond to glass/PDMS → bake to strengthen. Design-relevant realities:

- **Height comes from the SU-8 recipe**, one spin = one height; multi-height
  needs multi-layer lithography with alignment. Across-wafer uniformity
  ±5–10% — the h³ resistance sensitivity makes this the dominant tolerance.
- Rounded profiles for Quake valves need reflowed positive resist instead of
  SU-8 (see [valves-pumps-flow-control.md](valves-pumps-flow-control.md)).
- Master lifetime: silanised masters survive dozens of casts; the mask is the
  real archive — version it like source code.

### PDMS design-rule table (mirrored by `fabrication_check.py`)

| Rule | WARN | FAIL | Basis |
| --- | --- | --- | --- |
| Min feature (chrome mask) | < 2× | < 2 µm | lithography + casting fidelity |
| Min feature (transparency) | < 2× | < 10 µm | printer resolution |
| Roof sag (wide shallow) | w/h > ~7 | w/h > 20 | Delamarche 1998 collapse studies |
| Lateral collapse (tall thin) | — | h/w > 5 | pairing of high-aspect walls |
| Operating pressure | ≥ 200 kPa | ≥ 350 kPa | plasma-bond burst range (Eddings 2008) |

Support posts (~10% area, pitch ≲ 10× height) rescue wide shallow chambers.

## Thermoplastics (COC, PMMA, PS, PC)

- **Hot embossing**: min features ~10 µm (better with Si/Ni tools), aspect
  0.05–2, needs demolding draft ~2–5°. Bonding: thermal (near Tg — channel
  deformation is the risk), solvent-assisted (crazing risk: PMMA+ethanol),
  or UV/ozone-assisted low-temperature.
- **Injection molding**: the manufacturing endpoint — per-part cost cents,
  tooling cost 10⁴–10⁵ €; min features ~20 µm on standard tooling, uniform
  wall thickness, draft mandatory. Prototype in the *final material* before
  tooling: surface chemistry differences (vs PDMS) change assays.
- COC is the assay favourite: low autofluorescence, solvent-resistant, low
  water uptake, 134 °C-autoclavable grades exist.

## Glass

Wet HF etch is **isotropic**: profile is semi-elliptical, final width = mask
width + 2×depth (the checker emits this correction), so deep narrow channels
are impossible — pair a shallow etch with a bonded lid, or go DRIE-on-glass/
laser for vertical walls. Bonding: fusion (>500 °C, strongest), anodic
(glass–Si), or HF/adhesive at low temperature. Glass wins for: solvents,
high pressure (MPa-class), EOF stability, optics, zero absorption.

## Resin 3D printing (SLA/DLP)

Monolithic devices, no bonding, overnight turnaround. Enclosed-channel floor:
~100–200 µm reliably cleared of uncured resin on commercial printers
(exit-hole/drain design mandatory); published sub-100 µm results use custom
printers/resins. Watch: resin cytotoxicity (leachates kill cultures — post-
cure, solvent-wash, and cell-test any culture device), optical clarity, and
Z-stair-stepping on angled channels. FDM is not channel-tight below ~mm.

## Materials comparison

| Property | PDMS | COC | PMMA | PS | Glass | SLA resin |
| --- | --- | --- | --- | --- | --- | --- |
| E (stiffness) | ~1–3 MPa | 2.6–3.2 GPa | 3 GPa | 3–3.5 GPa | 64 GPa | 1–3 GPa |
| Small-molecule absorption | **high** | low | low | low | none | low–med |
| Gas permeable | **yes** | no | no | no | no | no |
| Autofluorescence | low–med | low | high (UV) | med | very low | med–high |
| Solvent resistance | poor (swells) | good | poor | poor | excellent | fair |
| Valves/stretch | **yes** | no | no | no | no | no |
| Autoclave | yes | grade-dep. | no | no | yes | usually no |
| Prototype turnaround | 1–2 days | days (emboss) | days | days | days–weeks | hours |

The Berthier/Young/Beebe (2012) argument: prototype in PDMS for speed, but
port maturing cell-based assays to thermoplastic before the biology
conclusions harden — absorption and leaching (details in
[cell-culture-organ-on-chip.md](cell-culture-organ-on-chip.md)) are not
footnotes.

## Surface treatments

- O₂ plasma: bonding + transient hydrophilicity (PDMS recovers in hours–days;
  storage under water slows it).
- PVA deposition on plasma-treated PDMS: stable hydrophilic; PEG-silane on
  glass: antifouling; BSA/pluronic: cheap dynamic antifouling for a run.
- Fluorosilane on masters: release layer. Collagen/fibronectin: cell adhesion
  (see the culture reference).

## World-to-chip interconnects and standards

- PDMS: biopsy-punched ports (0.5–4 mm; punch ≈ 0.8× tubing OD for
  interference fit) taking PTFE/Tygon tubing or steel pins. Leak-free to
  ~200 kPa when punched clean.
- Rigid chips: threaded fittings (10-32/6-40 into PMMA/COC manifolds),
  o-ring-clamped manifolds, or luer adapters. PEEK/FEP tubing (1/32", 1/16"
  OD) with flanged/ferrule fittings is the HPLC-grade standard.
- **ISO 22916:2022** standardises port pitch (1.5 mm grid), chip footprints,
  and fluidic interface positions — adopting it keeps chips compatible with
  commercial manifolds and instruments. `fabrication_check.py
  --port-diameter` sanity-checks port sizes against punch/tubing norms.
- Dead volume lives in the interconnect, not the chip: a 10 cm 1/16"-ID line
  holds ~20 µL — often 100× the chip volume. Budget it in the checklist.
