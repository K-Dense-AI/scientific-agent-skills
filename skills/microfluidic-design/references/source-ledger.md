# Source ledger

Provenance for every formula, threshold, and property value in this skill.
Only formulas and derived numbers are encoded — never source text. Entries
marked **[paywalled]** require an authorised copy for anything beyond what is
cited here; open-access or publisher-open items are marked [open]. Reviewed
2026-08-09.

## Textbooks and reviews (foundations)

- **Bruus, *Theoretical Microfluidics*, Oxford University Press, 2008**
  [paywalled] — exact rectangular-channel resistance series (eq. 3.53) and
  the square-channel coefficient ≈ 28.45 (readable in the 28.4 form at 3 sig
  figs); velocity-profile series; hydraulic-resistance framework;
  dimensionless groups. Used by `_common.rect_resistance`,
  `channel_resistance.py`, `governing-equations.md`.
- **Squires & Quake, "Microfluidics: fluid physics at the nanoliter scale",
  Rev. Mod. Phys. 77:977, 2005** [open preprint] — dimensionless-number
  design framing; low-Re physics. `dimensionless_numbers.py` readings.
- **Stone, Stroock & Ajdari, Annu. Rev. Fluid Mech. 36:381, 2004**
  [paywalled] — mixing and transport scalings.
- **Kirby, *Micro- and Nanoscale Fluid Mechanics*, Cambridge, 2010**
  [paywalled; author draft open] — Debye-length formula λ_D ≈ 0.304 nm/√I for
  1:1 electrolytes; zeta-potential magnitudes for glass/polymers.
  `electrokinetics.py debye`, zeta table.
- **Probstein, *Physicochemical Hydrodynamics*, Wiley, 2nd ed.** [paywalled]
  — Smoluchowski EOF relation; electrokinetic fundamentals.
- **Morgan & Green, *AC Electrokinetics: colloids and nanoparticles*, 2003**
  [paywalled]; **Pethig, Biomicrofluidics 4:022811, 2010** [open] —
  Clausius–Mossotti factor, DEP force expression, crossover behaviour,
  AC-electrokinetic artifacts. `electrokinetics.py dep`.
- **Bruus, "Acoustofluidics" tutorial series, Lab Chip 2011–2012 (parts 1,
  2, 7)** [paywalled] — Gor'kov coefficients f₁, f₂, contrast factor
  Φ = f₁/3 + f₂/2, radiation force 4πΦka³E_ac, energy-density calibration by
  particle tracking. `particle_separation.py acoustic`.
- **Taylor, Proc. R. Soc. A 219:186, 1953; Aris, Proc. R. Soc. A 235:67,
  1956** [open archives] — Taylor–Aris dispersion D_eff = D(1+Pe²/210).

## Fabrication

- **Duffy, McDonald, Schueller & Whitesides, Anal. Chem. 70:4974, 1998**
  [paywalled] — rapid prototyping of PDMS devices; process chain.
- **Xia & Whitesides, Annu. Rev. Mater. Sci. 28:153, 1998** [paywalled] —
  soft lithography feature limits.
- **McDonald & Whitesides, Acc. Chem. Res. 35:491, 2002** [paywalled] —
  PDMS device fabrication practice, port punching.
- **Delamarche et al., Adv. Mater. 9:741, 1997 / JACS 120:500, 1998**
  [paywalled] — PDMS stamp/channel deformation: sag and collapse aspect
  bands (w/h ≳ 20 collapse; pairing of tall features). Thresholds in
  `fabrication_check.py` (WARN w/h > 7, FAIL w/h > 20; FAIL h/w > 5).
- **Eddings, Johnson & Gale, J. Micromech. Microeng. 18:067001, 2008**
  [paywalled] — PDMS–PDMS bond strengths by method (~200–600 kPa range
  underlying the 200/350 kPa WARN/FAIL gates).
- **Lee, Park & Whitesides, Anal. Chem. 75:6544, 2003** [paywalled] —
  solvent swelling ranking of PDMS (fluorinated oils negligible; mineral/
  silicone oils swell). Droplet-oil caveats.
- **Berthier, Young & Beebe, Lab Chip 12:1224, 2012** [paywalled] — the
  PDMS-to-thermoplastic translation argument.
- **ISO 22916:2022, Microfluidic devices — interoperability requirements**
  [paywalled standard] — port pitch/footprint standardisation (cited by
  designation only).

## Mixing, gradients, extraction

- **Stroock et al., Science 295:647, 2002** [paywalled] — staggered
  herringbone mixer: groove geometry (~0.23–0.3× height, ~45°, ~6-groove
  half-cycles), ln(Pe) mixing-length scaling, ~1.5 cm at Pe 9×10⁵.
- **Dertinger, Chiu, Jeon & Whitesides, Anal. Chem. 73:1240, 2001**
  [paywalled] — Christmas-tree gradient generator design rules.
  `mixing_length.py gradient`.
- **Brody & Yager, Sens. Actuators A 58:13, 1997** [paywalled] — H-filter
  diffusive extraction. `mixing_length.py h-filter` (mode-series solution
  derived in `mixing-and-mass-transport.md`).

## Droplets

- **Garstecki, Fuerstman, Stone & Whitesides, Lab Chip 6:437, 2006**
  [paywalled] — T-junction squeezing law L/w = 1 + α·Q_d/Q_c, α ≈ 1–1.5.
- **De Menech, Garstecki, Jousse & Stone, J. Fluid Mech. 595:141, 2008**
  [paywalled] — squeezing→dripping transition near Ca ≈ 0.015.
- **Anna, Bontoux & Stone, Appl. Phys. Lett. 82:364, 2003** [paywalled] —
  flow-focusing regimes and size trends (basis of the ±30% estimate).
- **Christopher & Anna, J. Phys. D 40:R319, 2007** [paywalled] — droplet
  generation review; regime taxonomy.
- **Baret, Lab Chip 12:422, 2012** [paywalled] — surfactant choice and
  kinetics (PEG–PFPE 1–2% in HFE; Span 80 2–5% in mineral oil).
- **Collins et al., Lab Chip 15:3439, 2015** [paywalled] — Poisson
  encapsulation statistics and λ ≈ 0.05–0.3 practice.
- **3M Novec 7500 / Fluorinert FC-40 data sheets** [open] — µ, ρ of
  fluorinated oils in `_common.FLUIDS`.

## Particle and cell manipulation

- **Huang, Cox, Austin & Sturm, Science 304:987, 2004** [paywalled] — DLD
  principle. **Inglis, Davis, Sturm & Austin, Lab Chip 6:655, 2006**
  [paywalled] — DLD design geometry. **Davis et al., PNAS 103:14779, 2006**
  [open] — empirical D_c = 1.4·g·ε^0.48 (ε 0.01–0.1).
  **Loutherback et al., Microfluid. Nanofluid. 9:1143, 2010** [open] —
  triangular-post D_c reduction.
- **Di Carlo, Irimia, Tompkins & Toner, PNAS 104:18892, 2007** [open] —
  inertial focusing; a/D_h ≥ 0.07 gate. **Di Carlo, Lab Chip 9:3038, 2009**
  [paywalled] — F_L = f_L·ρU_m²a⁴/H², L_f = πµH²/(ρU_m a² f_L), f_L ≈ 0.05
  near-wall / 0.5 near-centre; Dean velocity fit U_D ≈ 1.8×10⁻⁴·De^1.63.
- **Tan & Takeuchi, PNAS 104:1146, 2007** [open] — bypass-resistance-ratio
  trap design rule.
- **Pamme, Lab Chip 6:24, 2006** [paywalled] — magnetophoresis force
  balance.
- **Laurell, Petersson & Nilsson, Chem. Soc. Rev. 36:492, 2007** [paywalled]
  — half-wave BAW separator design practice. **Settnes & Bruus, Phys. Rev. E
  85:016327, 2012** [open] — radiation force on a particle with viscosity
  corrections. **Ding et al., PNAS 109:11105, 2012** [open] — SSAW with PDMS.

## Platforms

- **Unger, Chou, Thorsen, Scherer & Quake, Science 288:113, 2000**
  [paywalled] — monolithic PDMS membrane valves; rounded-profile
  requirement. **Thorsen, Maerkl & Quake, Science 298:580, 2002**
  [paywalled] — 2·log₂N multiplexing. **Studer et al., J. Appl. Phys.
  95:393, 2004** [paywalled] — valve closing-pressure scaling. (The plate-
  bending coefficient 0.00406 is the standard clamped-square-plate value from
  Timoshenko plate theory, applied here as an estimate.)
- **Madou et al., Annu. Rev. Biomed. Eng. 8:601, 2006** [paywalled];
  **Ducrée et al., J. Micromech. Microeng. 17:S103, 2007** [open] —
  centrifugal pressure ρω²r̄Δr, burst valves, siphons, sequencing margins.
- **Cho, Moon & Fair (as Cho & Fair), J. MEMS 12:70, 2003** [paywalled] —
  EWOD transport/split/dispense; gap-to-pitch ≤ ~0.1 rule.
  **Mugele & Baret, J. Phys.: Condens. Matter 17:R705, 2005** [paywalled] —
  Lippmann–Young, saturation. Dielectric constants/breakdown fields from
  vendor data (Parylene C: SCS data sheet [open]).
- **Washburn, Phys. Rev. 17:273, 1921** [open] — filling dynamics.
  **Zimmermann, Schmid, Hunziker & Delamarche, Lab Chip 7:119, 2007**
  [paywalled] — capillary pumps and autonomous circuits.
  **Hosokawa, Sato, Ichikawa & Maeda, Lab Chip 4:181, 2004** [paywalled] —
  degas-driven flow. **Martinez, Phillips, Butte & Whitesides, Angew. Chem.
  46:1318, 2007** [open] — paper microfluidics. **Yetisen, Akram & Lowe,
  Lab Chip 13:2210, 2013** [paywalled] — lateral-flow design review.
- **Kopp, de Mello & Manz, Science 280:1046, 1998** [paywalled] —
  continuous-flow PCR zone architecture.

## Cell culture and sensing

- **Huh et al., Science 328:1662, 2010** [open PMC] — lung-on-chip membrane
  co-culture and stretch parameters. — **Toepke & Beebe, Lab Chip 6:1484,
  2006** [paywalled] — PDMS small-molecule absorption. **Regehr et al., Lab
  Chip 9:2132, 2009** [open PMC] — oligomer leaching and culture caveats.
- Physiological shear ranges: standard vascular-biology consensus values
  (arterial 1–2 Pa, venous 0.1–0.6 Pa) as reviewed in organ-on-chip
  literature; treat as planning bands, not specs.
- OCR range 1–400 amol/cell/s (hepatocytes to ~900): compiled from
  **Wagner, Venkataraman & Buettner, Free Radic. Biol. Med. 51:700, 2011**
  [open PMC] and organ-on-chip oxygen modelling papers; the skill flags OCR
  as the least certain input, to be measured per cell line.
- O₂ solubility ~0.2 mol/m³ (air-saturated, 37 °C) and D_O₂: CRC Handbook
  [paywalled]; PDMS O₂ permeability ~800 Barrer: polymer-membrane data
  compilations [open vendor data].
- **Gawad, Schild & Renaud, Lab Chip 1:76, 2001** [paywalled];
  **Sun & Morgan, Microfluid. Nanofluid. 8:423, 2010** [open] — impedance
  cytometry design rules (aperture ratio, coincidence).

## Property data

- **IAPWS / CRC Handbook of Chemistry and Physics** [paywalled] — water
  viscosity (1.002/0.890/0.6913 mPa·s at 20/25/37 °C), density, sound speed;
  air properties and mean free path (~68 nm, 1 atm).
- Diffusivities (fluorescein 4.25×10⁻¹⁰ m²/s at 25 °C, glucose, BSA, IgG,
  O₂): standard literature compilations; generic small-molecule 5×10⁻¹⁰ is a
  planning value.
- Contact angles, zeta potentials, acoustic and thermal properties: typical
  values compiled from the sources above and vendor data; all flagged in the
  tools as measurement-preferred.

## What is deliberately not encoded

Numeric content of paywalled standards beyond their designations (ISO 22916);
proprietary resin/printer limits; any claim that a specific commercial
device meets a spec. Where a threshold matters and its source is paywalled,
the tools present it as "typical" and instruct calibration.
