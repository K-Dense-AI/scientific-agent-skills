# Quick-reference property data

Design estimates mirroring the tables baked into `scripts/_common.py`; every
value is a typical literature number with provenance in
`references/source-ledger.md`. Local measurements override all of them.

## Fluids (viscosity µ, density ρ)

| Fluid | T (°C) | µ (mPa·s) | ρ (kg/m³) | Notes |
| --- | --- | --- | --- | --- |
| Water | 20 | 1.002 | 998.2 | IAPWS/CRC |
| Water | 25 | 0.890 | 997.0 | |
| Water | 37 | 0.6913 | 993.3 | |
| PBS (1×) | 25 | 0.91 | 1004 | σ ≈ 1.6 S/m |
| Culture medium | 37 | ~0.75 | ~1000 | serum adds 10–20% |
| Plasma | 37 | 1.3–1.7 | 1025 | ~Newtonian |
| Whole blood | 37 | 3–4 (high shear) | 1060 | **shear-thinning** |
| Glycerol 50% w/w | 25 | 5.0 | 1124 | viscosity standard |
| Mineral oil (light) | 25 | 10–70 | 850 | lot-dependent; swells PDMS |
| HFE-7500 | 25 | 1.24 | 1614 | droplet oil; no PDMS swelling |
| FC-40 | 25 | 4.1 | 1855 | droplet oil; no PDMS swelling |
| Air | 25 | 0.0185 | 1.184 | mean free path 68 nm |

## Diffusivities in water (25 °C unless noted)

| Species | D (m²/s) |
| --- | --- |
| Generic small molecule (<1 kDa) | 5×10⁻¹⁰ |
| Fluorescein | 4.25×10⁻¹⁰ |
| Glucose | 6.7×10⁻¹⁰ |
| O₂ (25 °C / 37 °C) | 2.1×10⁻⁹ / 3.0×10⁻⁹ |
| BSA (66 kDa) | 6.1×10⁻¹¹ |
| IgG (150 kDa) | 4.4×10⁻¹¹ |
| Sphere radius r | k_BT / (6πµr) |

## Water contact angles (static, typical)

| Surface | θ (°) | Caveat |
| --- | --- | --- |
| PDMS native | ~110 | |
| PDMS plasma-treated, fresh | ~10 | recovers toward ~70–110 in hours–days |
| Glass (clean) | ~30 | contamination raises it fast |
| SU-8 | ~80 | |
| PMMA | ~70 | |
| COC | ~92 | |
| Polystyrene | ~87 | tissue-culture treatment lowers it |
| PTFE / fluoropolymer | ~115 | |

## Zeta potentials (~pH 7, ~1 mM, order-of-magnitude)

| Surface | ζ (mV) |
| --- | --- |
| Glass / fused silica | −90 to −100 |
| PDMS (native / plasma) | −68 / −80 |
| PMMA | −40 |
| COC | −35 |

Strongly pH-, buffer-, and history-dependent (Kirby 2010) — measure for
quantitative EOF work.

## Acoustic properties (density, sound speed)

| Material | ρ (kg/m³) | c (m/s) |
| --- | --- | --- |
| Water (25 °C) | 997 | 1497 |
| Polystyrene bead | 1050 | 2350 |
| Silica bead | 2200 | 5900 |
| Generic cell | ~1080 | ~1535 |
| Red blood cell | ~1100 | ~1650 |

Compressibility κ = 1/(ρc²). Contrast factor Φ = f₁/3 + f₂/2 with
f₁ = 1 − κ_p/κ_m, f₂ = 2(ρ̃−1)/(2ρ̃+1).

## Thermal properties

| Material | k (W/m·K) | ρ (kg/m³) | c_p (J/kg·K) |
| --- | --- | --- | --- |
| PDMS | 0.16 | 970 | 1460 |
| Glass (borosilicate) | 1.1 | 2230 | 830 |
| Silicon | 149 | 2329 | 700 |
| PMMA | 0.19 | 1180 | 1470 |
| COC | 0.13 | 1020 | 1200 |
| Water | 0.61 | 997 | 4181 |

## Oxygen numbers for cell culture (37 °C)

- Air-saturated medium: ~0.2 mol/m³ dissolved O₂ (p_O₂ ≈ 19.9 kPa)
- PDMS O₂ permeability: ~2.7×10⁻¹³ mol/(m·s·Pa) (~800 Barrer)
- OCR: 1–400 amol/cell/s across cell types; primary hepatocytes 300–900.
  **Measure for your cells** — this is the least certain design input.
