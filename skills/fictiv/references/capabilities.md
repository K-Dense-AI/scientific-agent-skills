# Fictiv capabilities reference

Material lists marked **(live)** were read from the app's configurator in Sep 2026. Everything else comes from Fictiv's Help Center, spec pages and marketing pages, which sometimes disagree with each other. **The live configurator wins.** Re-check with `scripts/list_dropdown_options.js` if a choice matters.

## Contents
1. Processes at a glance
2. File formats
3. CNC machining: materials (live), finishes (live), tolerances, surface, threads, design rules
4. 3D printing: technologies, materials (live), tolerances, build sizes, design rules
5. Sheet metal
6. Urethane casting
7. Injection molding
8. Compression molding, die casting
9. Inspection and certificates
10. Lead-time mechanics and holidays
11. Compliance: export control, ITAR, IP, NDA
12. Tools: Materials.AI, Atlas, Punchout; there is no public API

---

## 1. Processes at a glance

| Process (card name) | Quote | "As fast as" | Account needed | Notes |
|---|---|---|---|---|
| **CNC Machining**: mill, lathe, EDM, gear hobbing, 3/5-axis | Instant; complex or drawing parts go to a human (under 2 h) | 1 day | any | 70+ materials. Tolerances to ±0.001" reliably with a drawing; marketing claims ±0.0001". Finishing, assembly, welding, inserts. |
| **3D Printing**: FDM, SLS, SLA, PolyJet, MJF, Carbon DLS | Instant | 1 day | any | 45+ materials, 11 finishes. No DMLS/metal printing listed. |
| **Urethane Casting** | Instant for simple parts, else manual | 7–10 days | company email | 12 materials. About 20 castings per silicone mold. |
| **Sheet Metal**: cutting, forming, welding, inserts | Instant | 2 days | any | 11 materials, 11 finishes |
| **Injection Molding**: production, family, multi-cavity, overmolding | Instant IM for simple straight-pull parts (<8×8×4 in), else "within 48 hours" | 10 days (T1) | company email | 30+ standard / 100+ custom resins |
| **Compression Molding** | Manual (48 h) | 10 days | company email | 9 elastomers |
| **Die Casting**: high and low pressure | Manual (48 h) | 10–15 days | company email | 8 alloys, post-machining |

Fictiv doesn't design parts. It needs a 3D CAD file. Extrusion isn't a self-serve process.

## 2. File formats (live "Supported File Types" modal)

"Files must contain a singular, solid body."

- **Parametric CAD (all processes):**
  - Dassault: `.sldprt .3dxml .catpart .catshape .cgr .dlv .exp .model .session`
  - Siemens: `.jt .par .prt .x_t .x_b`
  - STEP: `.stp .step`
  - Autodesk: `.ipt`
  - PTC: `.prt`
  - Other: `.3dm .vda .x3dv .ifc .xpr .xas .mf1 .neu .prc .sab .sat .u3d`
  - The uploader's accept list also includes `.3mf .arc .gts .ifczip .pkg .psm .pwd .unv .xmt .xmt_txt .wrl`.
- **Mesh (3D printing only):** `.stl .3ds .collada .dae .obj .off .ply .v3d .pts .tri .acs .x3d .wrl`
- **PDF drawings:** must accompany a CAD file and can't be quoted alone.
- **Assemblies (BOM only, not quotable):** `.sldasm .asm .iam .catproduct`
- **Not supported:** IGES, `.f3d`, `.slddrw`, `.dxf`, `.catdrawing`
- **SolidWorks:** save a single configuration, because multi-config files are rejected.
- **File size limit:** not documented.

**Best choice:** STEP (AP214 or AP242), one part per file, modeled at true size.

## 3. CNC machining

### 3.1 Materials (live list)

- **Aluminum:** 2024 (T3/T351/T4), 5052 (H32), 6061 (T6/T651/T6511), 6063 (T5/T52), 7050 (T7451), 7075 (T6/T651/T6511/T7351), MIC-6
- **Stainless steel:** 15-5 PH, 17-4 PH (Annealed / H1150 / H900), 303, 304/304L, 316/316L, 410, 416, 420, 440C, A286, Nitronic 60
- **Steel:** 1045, 1215, 12L14, 4130, 4140, 4340, 8620, A2 tool, A36, A514, Cast Iron, D2 tool, Inconel 625, Inconel 718, O1 tool, 1018, Zinc-Galvanized Low-Carbon Steel, Galvannealed Steel
- **Copper, brass, bronze:** 101 Cu, 110 Cu, 260 Brass, 360 Brass, 544 / 932 / 954 Bearing Bronze
- **Plastic:** ABS, Acrylic, Chemical-Resistant PVC, Delrin (20% GF), Delrin 150, Delrin AF (13% PTFE), Garolite G-10, HDPE, Nylon (30% GF), Nylon 6/6, PEEK, PEEK (30% GF), Polycarbonate, Polypropylene, PPS, PTFE (Teflon), Torlon PAI 4301, UHMW, ULTEM 1000
- **Titanium:** Grade 2, Grade 5
- **Exotic:** AZ31B / AZ61B / AZ91D Magnesium, Invar 36, Kovar, Zamak 3
- **Custom Materials, Other:** these force a manual quote

Machinability affects price. Aluminum and brass are fastest and cheapest. Stainless, titanium, Inconel and tool steels cost more and take longer.

### 3.2 Finishes

Live menu for 6061:
- Anodize per MIL-PRF-8625 **Type II**
- **Type III** (hardcoat)
- **Type III w/ PTFE**
- **Chem Film (Alodine™)**
- **ENP** (electroless nickel)
- **Media Blasting** (Fictiv's name for bead blast)
- **Nickel Plating**
- **Powder Coating**
- **Vibratory Tumble**

Type II colors (live): Natural, Black, Blue, Gold, Red, all sealed. Type II adds about 2 days.

Other finishes by material (Help Center):
- **Steel and stainless:** Black Oxide, Passivation, Electropolish, Zinc Plating, ENP, Powder coat, Media blast, Tumble
- **Acrylic:** Hand polish
- **Polycarbonate:** Vapor polish

The default is **As machined: ISO Grade N7, Ra 1.6 µm / 63 µin**.
- Custom Ra, cosmetic specs, masking, Type I anodize and custom colors all need a drawing and/or manual review.
- Powder coat supports Pantone and RAL matching (ask).

### 3.3 Tolerances and surface

- **Default without a drawing:** ISO 2768-medium. Standard inspection is by hand metrology.
- **Tighter:** call it out on a PDF drawing.
  - The Help Center's reliable ceiling is **±0.025 mm (±0.001")**.
  - Marketing claims down to ±0.0001" for metals.
  - Plastics: Fictiv flags anything under ±0.1 mm and can't hold under ±0.05 mm. Use PEEK for stability.
- **Roughness:**
  - 6.3–12.5 µm: coarse
  - 1.6–3.2: standard
  - 0.4–0.8: fine
  - 0.1–0.2: fine polish
  - 0.025–0.05: super-fine
  - The best "machined" finish is Ra 0.4.

### 3.4 Threads

- The Threads tab offers standard UNC/UNF, metric coarse and fine, ACME, trapezoidal and BSP threads that fit each modeled hole, each with a max tap depth.
- **Model tapped holes at tap-drill size.**
- Keep tap depth ≤ 3× diameter. 1–1.5× diameter of engagement is enough.
- Non-standard threads are "produced at risk" and need a drawing.
- Inserts, helicoils, dowel pins and hardware go through a drawing plus "Contact us".

### 3.5 Size limits

- **Help Center:** mill 1828 × 500 × 152 mm (72 × 20 × 6 in); lathe Ø152 × 394 mm (6 × 12 in).
- **Marketing:** up to 48 in length. A large-parts program reaches up to 10.5 m × 3.7 m × 1.2 m through sales.
- Oversize parts go to manual review or sales.

### 3.6 Design rules (DFM)

These are what trigger Fictiv's warnings:
- **Walls:** at least 0.5 mm metal and 1.0 mm plastic is safe. Fictiv's DFM flagged "below our minimum thickness (0.5mm for metals)" live. The glossary's hard floor is 0.25 mm metal / 0.5 mm plastic.
- **Internal vertical corners** are always radiused ("Fillets: Added"). Model radii at or above 0.8 mm, and slightly larger than a standard tool (e.g. R3.2 instead of R3.175). Sharp internal corners otherwise mean EDM, which costs more and takes longer.
- **Pocket depth:** keep it to 5× tool diameter or less; up to 10× is possible. Rough limits by material: plastics 15×, aluminum 10×, steel 5×.
- **Drill depth:** keep it to 6× diameter or less; up to 12× is possible. Make blind holes 25% deeper than the thread.
- **Turning:** L:D of 8:1 or less.
- **Text:** at least 0.020" deep and 0.030" wide.
- **Setups:** aim for 1–2. Parallel, flat outer faces are easiest to hold.
- **Undercuts, unreachable volumes and gear hobbing** mean manual review, EDM or overseas-only production.

## 4. 3D printing

### 4.1 Technologies and materials (live list)

- **SLS:** Nylon 12, Nylon 12 Fire Retardant, Nylon 12 Glass-Filled, TPU 88A
- **MJF:** PA 12, PA 12 Glass Beads
- **SLA:** Accura 25, Accura 60, Accura AMX Rigid Black, Accura ClearVue, Accura Xtreme Gray, Accura Xtreme White 200, Somos Evolve, Somos PerFORM, Somos WaterClear, Somos WaterShed
- **FDM:** ABS, ABS ESD, ABS M30i, ASA, Nylon 6 CF, PC + ABS, PC-ISO, PETG, Polycarbonate, Ultem 1010, Ultem 9085
- **PolyJet:** ABS-like, Rubber-Like, VeroBlack, VeroClear, VeroWhite
- **Carbon DLS:** EPU 40/41, EPX 82, EPX 86FR, FPU 50, Loctite 3D 3843, IND147, IND405 Clear, MPU 100, RPU 70, UMA 90
- **Custom Materials, Other**

### 4.2 Which technology to use (Fictiv's guidance)

- **FDM:** cheapest early prototypes. Visible layers. Infill 10–25% by default and adjustable.
- **SLA:** high detail and smooth surfaces. Clear parts with ClearVue or WaterClear.
- **SLS / MJF:** functional nylon parts, low-to-mid volume, no supports. MJF is grey by default and can be dyed black.
- **PolyJet:** visual models, rubber-like overmold mock-ups. Avoid internal cavities.
- **Carbon DLS:** production-grade elastomers and rigid parts. Repeatable.

### 4.3 Tolerances

Fictiv says 3DP tolerances "cannot be guaranteed". Typical values:
- PolyJet ±0.2 mm
- SLS and MJF ±0.3 mm
- SLA ±(0.13 mm + 0.05 mm/mm)
- FDM ±0.5 mm (PLA ±1.0 mm)

Use CNC for critical fits.

### 4.4 Max build size (mm)

- FDM ABS: 406×355×406 (Help Center); large-format FDM up to 914×610×914
- MJF: 380×284×380
- SLS: 700×380×580
- PolyJet: 490×390×200
- SLA: 254³ for Accura 25 (Help Center); up to 635×736×533 (capability page)
- Carbon: 189×118×326

### 4.5 Design rules

- **Minimum walls:** FDM >1 mm, PolyJet >1 mm (rubber-like 2 mm). Spec page: SLA 0.4, SLS 0.7, MJF 0.5 mm.
- Avoid trapped internal cavities in SLS (powder) and PolyJet (support).
- Heat-set threaded inserts are available and go to engineering review in under 2 h.
- DFM for 3DP is limited to wall-thickness checks.
- Multiple bodies in one file are only acceptable for interlinked moving assemblies such as chains or hinges.

## 5. Sheet metal

- **Processes:** laser, punch, waterjet; brake forming, rolling; MIG, TIG, spot welding; PEM hardware.
- **Materials:** Al 5052-H32, 6061, 7075; SS 301, 303, 304, 316, 430; steel 1018, 1020, CRS, HRS, galvanized; brass, copper, bronze, titanium.
- **Rules:**
  - Thickness 0.015–0.375". Welding needs at least 0.030".
  - Hole diameter at least 1× thickness.
  - Hole-to-edge at least 2t. Hole-to-bend at least 2.5t plus bend radius.
  - Flange at least 4t (3t minimum).
  - Bend radius 0.5–1t for Al 5052 and 1–2t for SS 304.
  - Flat tolerance ±0.005". Bend angle ±0.5–1°.
- **Files:** upload the 3D part as STEP or native CAD. DXF is not supported.

## 6. Urethane casting

- **Materials** (Shore D):
  - ABS-like (75–85D), ABS-like FR V0, ABS-like HT, Acrylic-like, Nylon-like, POM-like, PP-like
  - Opaque elastomers 20A–90A
  - Water-clear elastomers 30A–80A
- **Colors:** Natural, Black, White, Gray, Red, Yellow, Blue, Green, Orange, Purple, Color Match.
- **Textures:** matte, glossy, MT-11010, MT-11020, MT-11030.
- **Volume:** 10–200 units typical. Max 2200×1200×1000 mm. Mesh files are not accepted.

## 7. Injection molding

- **Tooling:**
  - GlobalFlex (inserts in shared frames, CN, US or MX)
  - Traditional aluminum or steel (US)
  - Mantle printed-steel inserts (US)
  - Production Import
  - China steel
  - Class 101 or 103; multi-cavity and family molds
- **Lead times:** T1 samples as fast as 10 days, typically 2–5 weeks. Production runs 4–7 business days after T1 approval.
- **Resins:** ABS, POM, ASA, HDPE, LDPE, HIPS, PA66 (±GF), PBT, PC (±GF), PC/ABS, PEEK, PEI, PET, PMMA, PP, PPA, PPO, PPS, PPSU, PVC, SAN, TPE, TPU, TPV, EPDM, silicone (LSR). Custom resins are available.
- **Surface and extras:** SPI A-1 to D-3, Mold-Tech and Yick Sang textures; overmolding, insert molding, 2K/3K, gas-assist; pad printing, plating, laser marking, ultrasonic welding, heat staking; PPAP, FAI, Cpk.
- **Design:**
  - Nominal wall 2–3 mm, uniform within ±10%.
  - Draft 0.5–2°.
  - Ribs 50–65% of the wall.
  - Standard tolerance ±0.030".
- **DFM report:**
  - Slides are marked Warning, Approval required or Revision required.
  - Annotate slides, then "Notify Fictiv".
  - Customer owns the cavity and core. Storage is free for 2 years, then $500/yr.
- **Tooling payment:** 100% upfront, or 50/50 with PO terms.

## 8. Compression molding and die casting

- **Compression molding:** silicone, SBR, natural rubber, neoprene, NBR, FKM/Viton, HNBR, PU, EPDM. Max 1000×600 mm. SPI and Mold-Tech finishes, pad print, color match.
- **Die casting:**
  - Alloys: Al ADC12, A380, ADC10, A383, A390; Zn Zamak 3/5; Mg AZ91D.
  - Tolerances: ±0.1 mm per 25 mm as-cast, ±0.05 mm post-machined.
  - Finishes: powder coat (black or white), others.
- Both are manually quoted. Allow 24–48 h.

## 9. Inspection and certificates

| Option | Where | Cost / time | Needs |
|---|---|---|---|
| Standard Inspection Report | Included automatically | free | — |
| Advanced Inspection Report (CMM, laser, optical) | Config → Inspections → Add | per part; +3–5 business days | Bubbled drawing |
| Certificate of Conformity | Config → Certificates → Add | about $100 | Drawing callout recommended |
| Material Certification | Config → Certificates → Add | varies; not available for every material | — |
| FAI, custom reports, PPAP | "Contact us" / chat / account manager | quoted | Drawing; discuss with AE *before* ordering |

## 10. Lead-time mechanics

- Production days are **business days**. Orders placed after the daily cutoff start the next business day.
  - The live checkout banner showed an **8 PM** cutoff. The Help Center says 3 pm PT. Trust the banner.
- The quote's ship date is driven by the **slowest part**. Finishes, inspections and EDM add days.
- **Six tiers per quote:** North America (USA or Mexico) Fastest / Standard / Cost-effective, and Overseas Fastest / Standard / Cost-effective. "USA only" restricts production to US suppliers.
- **Holidays excluded:**
  - US: Dec 24–25, Jan 1, MLK, Presidents', Memorial, Jul 4, Labor, Thanksgiving (2 days).
  - Overseas: Chinese New Year (about a week), May 1–5, Oct 1–3, Mid-Autumn.
  - The checkout banner links "holiday schedule".
- Quotes are valid for **30 days**.

## 11. Compliance

- **Export control:** EAR99 and 9E991 are self-serve. Other ECCNs go through Fictiv's off-platform request form.
- **ITAR:** not supported. Files and quotes with ITAR language are auto-deleted. Uploading controlled data violates the Terms.
- **If a user's part is defense, space or aerospace hardware, ask about its classification before uploading.**
- **IP:** Fictiv strips identifying info before sharing with partners. Partners are under NDA. Fictiv may not train AI on customer data. A mutual NDA is available through the contact form (1–2 business days).
- **End-use declaration:** Prototype or Commercial, on every quote.

## 12. Tools and integrations

- **Materials.AI:** an in-app ("Ask Materials.AI") and web (fictiv.com/ai/materials) chat for choosing materials. Informational only; needs a company email.
- **Atlas** (atlas.fictiv.com): an AI CNC complexity score and manufacturability analysis. Early access / waitlist.
- **Punchout:** cXML to SAP Ariba, Coupa and Dynamics 365 (Teams only).
- **No public API, SDK or CAD plugin exists.** Everything is done through the web app. The app talks to an internal GraphQL endpoint (`prod-graphql.fictiv.com`). It's undocumented, unsupported and subject to change, so drive the UI rather than calling it.
