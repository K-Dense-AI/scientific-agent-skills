# Praxis — Techniques Quick Reference

## XRD (X-ray Diffraction)

**Data format:** 2θ (degrees) vs intensity (counts or a.u.)
**Common file types:** .xy, .csv, .raw, .brml, .dat

**Analysis pipeline:**
1. Load data → auto-detect 2θ and intensity columns
2. Baseline correction (if needed)
3. Peak detection → positions, heights, FWHM
4. d-spacing calculation (Bragg's law)
5. Scherrer crystallite size from FWHM
6. Williamson-Hall plot (separate size/strain broadening)

**Key functions:**
```python
from techniques.xrd import analyse_xrd, calc_d_spacing, scherrer_size
results = analyse_xrd(two_theta, intensity, wavelength="Cu_Ka")
```

**Parameters:**
- Wavelength: Cu Kα (1.5406 Å), Co Kα (1.7889 Å), Mo Kα (1.7107 Å)
- Scherrer constant K: 0.89–0.94 (0.9 default)

---

## DSC (Differential Scanning Calorimetry)

**Data format:** Temperature (°C) vs heat flow (mW or W/g)
**Common analysis:** Tg (glass transition), Tm (melting), Tc (crystallisation), enthalpy (J/g), crystallinity %

**Pipeline:**
1. Load data
2. Identify transitions (endothermic down or up convention)
3. Tg: midpoint of step change
4. Tm/Tc: peak temperature
5. Enthalpy: integrate peak area
6. Crystallinity: ΔHm / ΔH°m × 100%

---

## TGA (Thermogravimetric Analysis)

**Data format:** Temperature (°C) vs mass (% or mg)
**Common analysis:** Onset/endset temperatures, DTG peaks, residue %, multi-step decomposition

**Pipeline:**
1. Load data
2. DTG (derivative) for decomposition steps
3. Onset temperature (tangent method)
4. Mass loss per step
5. Final residue %

---

## EIS (Electrochemical Impedance Spectroscopy)

**Data format:** Frequency (Hz), Z' (Ω), Z'' (Ω) — or |Z| and phase
**Common file types:** .csv, .dta (Gamry), .mpr (Bio-Logic)

**Analysis pipeline:**
1. Parse impedance data (real/imag or mod/phase)
2. Nyquist plot (Z' vs -Z'')
3. Bode plot (|Z| and phase vs frequency)
4. Equivalent circuit fitting (Randles, R-CPE, etc.)
5. Extract resistance values
6. Calculate conductivity (σ = L/RA)
7. Arrhenius analysis for temperature-dependent data

**Key functions:**
```python
from techniques.impedance import parse_impedance, fit_circuit, plot_nyquist
data = parse_impedance(freq, z_real=zr, z_imag=zi)
fit = fit_circuit(data, circuit="randles")
plot_nyquist(data, fit=fit)
```

**Available circuits:** randles, randles_cpe, rc, r_cpe

---

## Mechanical Testing

**Data format:** Extension/strain vs force/stress
**Common analysis:** Young's modulus, yield strength (0.2% offset), UTS, elongation at break, toughness

**Pipeline:**
1. Load data (force-displacement or stress-strain)
2. Convert if needed (force → stress, displacement → strain)
3. Linear region for Young's modulus
4. 0.2% offset yield
5. UTS and elongation at break
6. Toughness (area under curve)

---

## FTIR / Raman Spectroscopy

**Data format:** Wavenumber (cm⁻¹) vs absorbance/transmittance (FTIR) or intensity (Raman)
**Common file types:** .csv, .spe, .jdx, .dx

**Analysis pipeline:**
1. Load spectrum
2. Baseline correction
3. Peak identification
4. Functional group assignment
5. Spectral subtraction (if reference available)

---

## XPS (X-ray Photoelectron Spectroscopy)

**Data format:** Binding energy (eV) vs intensity (counts)
**Common analysis:** Survey scan, high-res peak fitting, chemical state ID, atomic %

**Pipeline:**
1. Survey scan overview
2. High-resolution region selection
3. Shirley or Tougaard background subtraction
4. Peak fitting (Gaussian-Lorentzian mixed)
5. Binding energy calibration (C 1s = 284.8 eV)
6. Atomic % calculation from peak areas and sensitivity factors

---

## SEM/EDS

**SEM analysis:** Grain size (line intercept, area method), porosity, particle size distribution
**EDS analysis:** Elemental composition tables, line scan profiles

---

## AFM (Atomic Force Microscopy)

**Data format:** Height maps (matrix), line profiles
**Common analysis:** Ra (arithmetic roughness), Rq (RMS roughness), Rz, grain analysis

---

## Piezoelectric Characterisation

**Data types:**
- d33/d31 coefficient measurements
- P-E hysteresis loops (polarisation vs electric field)
- S-E butterfly curves (strain vs electric field)
- Impedance resonance (for kp, kt, Qm)
- Temperature-dependent depolarisation

---

## Dielectric Properties

**Data format:** Frequency (Hz) vs permittivity (ε') and loss tangent (tan δ)
**Common analysis:** Cole-Cole plots, Curie-Weiss fitting, AC conductivity

---

## General Data Processing (all techniques)

**Curve fitting:** linear, polynomial, Gaussian, Lorentzian, Voigt, exponential, power law, sigmoidal, custom
**Peak analysis:** detection, FWHM, area integration, deconvolution
**Baseline correction:** polynomial, ALS, SNIP, rubberband, Shirley
**Smoothing:** Savitzky-Golay, moving average, Gaussian, median
**FFT:** power spectrum, low/high/band-pass filtering
**Statistics:** descriptive stats, t-test, ANOVA, error propagation
