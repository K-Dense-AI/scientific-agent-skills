# Praxis Cookbook

A technique-by-technique reference showing data formats, loading, analysis, plotting, and expected results. Every example uses the actual Praxis API.

---

## Structural Techniques

### XRD (X-ray Diffraction)

**Data:** 2theta (deg) vs intensity (counts). File formats: .csv, .xy, .brml, .dat

**Load:**
```python
df = load_data("scan.xy")
# .brml files from Bruker instruments are auto-detected
```

**Analyse:**
```python
from techniques.xrd import analyse_xrd
results = analyse_xrd(df["x"], df["y"], wavelength="Cu_Ka")
# Returns: XRDResults with peaks (position, d-spacing, FWHM, crystallite size)
# Also runs Williamson-Hall if >= 3 peaks found
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["x"], df["y"], kind="line",
                    xlabel="2theta (deg)", ylabel="Intensity (a.u.)")
export_figure(fig, "xrd_pattern.svg", dpi=300)
```

**Key results:** d-spacing (A), crystallite size via Scherrer (nm), lattice strain via Williamson-Hall, FWHM (deg)

---

### Neutron / Electron Diffraction

**Data:** 2theta or d-spacing vs intensity. Same column formats as XRD.

**Load:**
```python
df = load_data("neutron_diffraction.dat")
```

**Analyse:**
```python
from techniques.xrd import analyse_xrd
# Use the appropriate wavelength for your source
results = analyse_xrd(df["x"], df["y"], wavelength=1.5401)
# Custom wavelength in Angstrom for neutron/electron source
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["x"], df["y"], kind="line",
                    xlabel="2theta (deg)", ylabel="Intensity (a.u.)")
export_figure(fig, "neutron_diffraction.svg")
```

**Key results:** Same as XRD -- d-spacings, crystallite sizes, strain. Adjust wavelength for your source.

---

### SAXS / SANS / WAXS (Small-Angle Scattering)

**Data:** q (1/A or 1/nm) vs I(q) (a.u.). File formats: .csv, .dat, .txt

**Load:**
```python
df = load_data("saxs_data.csv")
```

**Analyse:**
```python
from techniques.saxs import analyse_saxs, guinier_analysis, porod_analysis, kratky_plot
results = analyse_saxs(df["q"], df["I"])
# Returns: SAXSResults with Guinier (Rg, I(0)), Porod (constant, exponent), invariant Q

# Individual analyses:
guinier = guinier_analysis(df["q"], df["I"], q_range=(0.01, 0.05))
porod = porod_analysis(df["q"], df["I"])
q_kratky, iq2 = kratky_plot(df["q"], df["I"])
```

**Plot:**
```python
apply_style("nature")
# Log-log I(q) vs q
fig, ax = plot_data(df["q"], df["I"], kind="line", log_x=True, log_y=True,
                    xlabel="q (1/A)", ylabel="I(q) (a.u.)")
export_figure(fig, "saxs_loglog.svg")

# Kratky plot
fig2, ax2 = plot_data(q_kratky, iq2, kind="line",
                      xlabel="q (1/A)", ylabel="I(q) * q^2")
export_figure(fig2, "kratky_plot.svg")
```

**Key results:** Radius of gyration Rg, forward scattering I(0), Porod exponent (~4 for sharp interfaces), scattering invariant Q

---

## Microscopy

### SEM (Grain Size, Porosity)

**Data:** Grain intercept lengths or grain areas (from image analysis). File formats: .csv, .xlsx

**Load:**
```python
df = load_data("grain_measurements.csv")
```

**Analyse:**
```python
from techniques.sem_eds import grain_size_line_intercept, grain_size_area_method, estimate_porosity

# Line intercept method
gs = grain_size_line_intercept(df["intercept_length"], scale_factor=0.5, unit="um")
# Returns: GrainSizeResults with mean, std, median, D10, D50, D90

# Area method (equivalent circular diameter)
gs2 = grain_size_area_method(df["grain_area"], scale_factor=0.25, unit="um")

# Porosity from greyscale image (2D numpy array)
import numpy as np
image = np.loadtxt("sem_greyscale.csv", delimiter=",")
porosity = estimate_porosity(image, dark_is_pore=True)
# Returns: dict with porosity_pct, threshold
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(None, df["intercept_length"].values, kind="histogram",
                    xlabel="Grain size (um)", ylabel="Count", bins=20)
export_figure(fig, "grain_size_distribution.svg")
```

**Key results:** Mean grain size, standard deviation, D10/D50/D90 percentiles, porosity %

---

### EDS / EDX (Energy Dispersive Spectroscopy)

**Data:** Element list with wt% or at%. Or energy (keV) vs counts for raw spectrum.

**Load:**
```python
df = load_data("eds_composition.csv")
```

**Analyse:**
```python
from techniques.sem_eds import parse_eds_composition, analyse_eds_line_scan

# Composition table
eds = parse_eds_composition(
    elements=["O", "Si", "Al", "Fe"],
    weight_pct=[45.2, 30.1, 15.3, 9.4]
)
# Returns: EDSResults with elements, weight_pct, atomic_pct

# Line scan
normalised = analyse_eds_line_scan(
    position=df["position"],
    intensities={"Si": df["Si"], "O": df["O"], "Fe": df["Fe"]}
)
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["energy"], df["counts"], kind="line",
                    xlabel="Energy (keV)", ylabel="Counts")
export_figure(fig, "eds_spectrum.svg")
```

**Key results:** Elemental composition in wt% and at%, normalised line scan profiles

---

### AFM (Atomic Force Microscopy)

**Data:** 1D height profile or 2D height map (nm). File formats: .csv, .txt, .dat

**Load:**
```python
df = load_data("afm_profile.csv")
# Or for 2D maps:
import numpy as np
height_map = np.loadtxt("afm_map.csv", delimiter=",")
```

**Analyse:**
```python
from techniques.afm import profile_roughness, surface_roughness, extract_profile

# 1D profile roughness
rough = profile_roughness(df["height"], unit="nm", detrend=True)
# Returns: RoughnessResults with Ra, Rq, Rz, Rmax, Rsk, Rku

# 2D surface roughness
rough2d = surface_roughness(height_map, pixel_size=5.0, unit="nm")
# Also returns Sa, Sq (areal parameters)

# Extract a profile from a 2D map
pos, heights = extract_profile(height_map, row=128, pixel_size=5.0)
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["x"], df["height"], kind="line",
                    xlabel="Position (um)", ylabel="Height (nm)")
export_figure(fig, "afm_profile.svg")

# 3D surface
fig2, ax2 = plot_contour(x_grid, y_grid, height_map, kind="heatmap",
                         xlabel="x (um)", ylabel="y (um)", clabel="Height (nm)")
export_figure(fig2, "afm_surface.svg")
```

**Key results:** Ra, Rq, Rz, Rmax (nm), skewness, kurtosis, Sa/Sq for areal analysis

---

## Spectroscopy

### FTIR (Fourier Transform Infrared)

**Data:** Wavenumber (cm-1) vs absorbance or transmittance. File formats: .csv, .jdx, .dx, .spe

**Load:**
```python
df = load_data("ftir_spectrum.csv")
# JCAMP-DX files auto-detected:
df = load_data("spectrum.jdx")
```

**Analyse:**
```python
from techniques.spectroscopy import analyse_ftir, atr_correction, transmittance_to_absorbance

# Convert transmittance to absorbance if needed
absorbance = transmittance_to_absorbance(df["transmittance"])

# Full FTIR analysis with automatic peak assignment
results = analyse_ftir(df["wavenumber"], absorbance,
                       baseline_method="als", assign_peaks=True)
# Returns: SpectroscopyResults with peaks (position, assignment, functional group)

# ATR correction
wn_corr, abs_corr = atr_correction(df["wavenumber"], absorbance,
                                     n_crystal=2.4)  # diamond ATR
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["wavenumber"], absorbance, kind="line", invert_x=True,
                    xlabel="Wavenumber (cm-1)", ylabel="Absorbance")
export_figure(fig, "ftir_spectrum.svg")
```

**Key results:** Peak positions (cm-1), functional group assignments, FWHM

---

### Raman Spectroscopy

**Data:** Raman shift (cm-1) vs intensity (counts). File formats: .csv, .txt, .spe

**Load:**
```python
df = load_data("raman_spectrum.csv")
```

**Analyse:**
```python
from techniques.spectroscopy import analyse_raman

results = analyse_raman(df["raman_shift"], df["intensity"],
                        baseline_method="als", min_peak_height_pct=5.0)
# Returns: SpectroscopyResults with peaks (position, intensity, FWHM, area)
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["raman_shift"], df["intensity"], kind="line",
                    xlabel="Raman Shift (cm-1)", ylabel="Intensity (a.u.)")
export_figure(fig, "raman_spectrum.svg")
```

**Key results:** Peak positions (cm-1), peak intensities, FWHM, peak areas

---

### UV-Vis (Beer-Lambert, Tauc)

**Data:** Wavelength (nm) vs absorbance or transmittance. File formats: .csv, .txt

**Load:**
```python
df = load_data("uv_vis.csv")
```

**Analyse:**
```python
from techniques.spectroscopy import beer_lambert, tauc_plot, transmittance_to_absorbance

# Beer-Lambert: calculate concentration from absorbance
bl = beer_lambert(absorbance=0.85, molar_absorptivity=1500, path_length=1.0)
# Returns: dict with absorbance, molar_absorptivity, path_length, concentration

# Tauc plot for band gap
energy, tauc_y, band_gap = tauc_plot(
    df["wavelength"], df["absorbance"],
    n=0.5,  # 0.5 = direct allowed, 2 = indirect allowed
    thickness=0.01  # cm, optional
)
```

**Plot:**
```python
apply_style("nature")
# Absorbance spectrum
fig, ax = plot_data(df["wavelength"], df["absorbance"], kind="line",
                    xlabel="Wavelength (nm)", ylabel="Absorbance")
export_figure(fig, "uv_vis.svg")

# Tauc plot
fig2, ax2 = plot_data(energy, tauc_y, kind="line",
                      xlabel="Energy (eV)", ylabel="(alpha*hv)^(1/n)")
export_figure(fig2, "tauc_plot.svg")
```

**Key results:** Concentration (mol/L), molar absorptivity, band gap (eV)

---

### XPS (X-ray Photoelectron Spectroscopy)

**Data:** Binding energy (eV) vs intensity (CPS or counts). File formats: .csv, .txt, .dat

**Load:**
```python
df = load_data("xps_survey.csv")
```

**Analyse:**
```python
from techniques.xps import analyse_survey, fit_highres, calibrate_be

# Calibrate binding energy to adventitious carbon
be_cal, shift = calibrate_be(df["binding_energy"], c1s_measured=285.3)

# Survey scan analysis (auto-detects elements)
survey = analyse_survey(be_cal, df["intensity"])
# Returns: XPSResults with peaks, composition (atomic %)

# High-resolution peak fitting (e.g. C 1s)
hr = fit_highres(df_c1s["binding_energy"], df_c1s["intensity"],
                 n_peaks=3, background="shirley", element="C 1s")
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(be_cal, df["intensity"], kind="line", invert_x=True,
                    xlabel="Binding Energy (eV)", ylabel="Intensity (CPS)")
export_figure(fig, "xps_survey.svg")
```

**Key results:** Elemental composition (at%), peak positions, chemical states, FWHM

---

### Photoluminescence (PL)

**Data:** Wavelength (nm) or energy (eV) vs intensity (a.u.). File formats: .csv, .txt

**Load:**
```python
df = load_data("pl_spectrum.csv")
```

**Analyse:**
```python
from analysis.peaks import find_peaks_auto
from analysis.fitting import fit_curve

# Peak detection
peaks = find_peaks_auto(df["wavelength"], df["intensity"], min_height_pct=5.0)

# Gaussian fit to emission peak
fit = fit_curve(df["wavelength"], df["intensity"], model="gaussian")
# Returns: FitResult with center, amplitude, sigma, FWHM
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["wavelength"], df["intensity"], kind="line",
                    xlabel="Wavelength (nm)", ylabel="PL Intensity (a.u.)")
export_figure(fig, "pl_spectrum.svg")
```

**Key results:** Emission peak wavelength (nm), FWHM (nm), peak intensity, Stokes shift

---

### NMR (Nuclear Magnetic Resonance)

**Data:** Chemical shift (ppm) vs intensity. File formats: .csv, .jdx, .txt

**Load:**
```python
df = load_data("nmr_1h.csv")
```

**Analyse:**
```python
from techniques.nmr import analyse_nmr, integrate_peaks, reference_spectrum

# Reference to TMS
cs_ref, intens = reference_spectrum(df["ppm"], df["intensity"],
                                     reference_peak_ppm=0.05, target_ppm=0.0)

# Full analysis: peaks, integration, multiplicity
results = analyse_nmr(cs_ref, intens, nucleus="1H", solvent="CDCl3")
# Returns: NMRResults with peaks (shift, integral, multiplicity, J-coupling)

# Manual region integration
integrals = integrate_peaks(cs_ref, intens,
                            regions=[(0.5, 1.5), (3.0, 4.0), (6.5, 8.0)])
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(cs_ref, intens, kind="line", invert_x=True,
                    xlabel="Chemical Shift (ppm)", ylabel="Intensity")
export_figure(fig, "nmr_1h.svg")
```

**Key results:** Chemical shifts (ppm), integrals (normalised), multiplicity (s/d/t/q/m), J-coupling (Hz)

---

### EPR / ESR (Electron Paramagnetic Resonance)

**Data:** Magnetic field (mT or G) vs signal intensity (derivative). File formats: .csv, .dat

**Load:**
```python
df = load_data("epr_spectrum.csv")
```

**Analyse:**
```python
from analysis.peaks import find_peaks_auto
from analysis.fitting import fit_curve

# EPR spectra are typically first-derivative -- find zero crossings for g-factor
peaks = find_peaks_auto(df["field_mT"], df["signal"], min_height_pct=5.0)

# g-factor calculation: g = h*v / (mu_B * B)
# h = 6.626e-34 J.s, mu_B = 9.274e-24 J/T, v = microwave frequency
v_hz = 9.5e9  # 9.5 GHz X-band
for p in peaks.peaks:
    B_tesla = p.position * 1e-3  # mT to T
    g = (6.626e-34 * v_hz) / (9.274e-24 * B_tesla)
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["field_mT"], df["signal"], kind="line",
                    xlabel="Magnetic Field (mT)", ylabel="dX''/dB (a.u.)")
export_figure(fig, "epr_spectrum.svg")
```

**Key results:** g-factor, linewidth (mT), peak-to-peak amplitude, hyperfine splitting

---

### AES (Auger Electron Spectroscopy)

**Data:** Kinetic energy (eV) vs dN/dE (derivative spectrum). File formats: .csv, .dat

**Load:**
```python
df = load_data("aes_spectrum.csv")
```

**Analyse:**
```python
from analysis.peaks import find_peaks_auto

# Auger spectra are typically plotted as dN(E)/dE
peaks = find_peaks_auto(df["kinetic_energy"], df["dNdE"], min_height_pct=5.0)
# Peak positions correspond to Auger transition energies
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["kinetic_energy"], df["dNdE"], kind="line",
                    xlabel="Kinetic Energy (eV)", ylabel="dN(E)/dE (a.u.)")
export_figure(fig, "aes_spectrum.svg")
```

**Key results:** Auger peak energies (eV), peak-to-peak heights, elemental identification

---

### EELS (Electron Energy Loss Spectroscopy)

**Data:** Energy loss (eV) vs intensity (counts). File formats: .csv, .dat

**Load:**
```python
df = load_data("eels_spectrum.csv")
```

**Analyse:**
```python
from analysis.peaks import find_peaks_auto
from analysis.baseline import correct_baseline

# Background subtraction (power-law common for EELS)
corrected, bg, _ = correct_baseline(df["energy_loss"], df["intensity"],
                                     method="polynomial", degree=3)

# Edge detection
peaks = find_peaks_auto(df["energy_loss"], corrected, min_height_pct=3.0)
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["energy_loss"], df["intensity"], kind="line",
                    xlabel="Energy Loss (eV)", ylabel="Intensity (counts)")
export_figure(fig, "eels_spectrum.svg")
```

**Key results:** Core-loss edge positions (eV), near-edge fine structure, elemental identification

---

## Chemical Composition

### WDS (Wavelength Dispersive Spectroscopy)

**Data:** Same format as EDS -- element list with wt% or at%.

**Analyse:**
```python
from techniques.sem_eds import parse_eds_composition

# WDS gives higher accuracy than EDS; same analysis pipeline
wds = parse_eds_composition(
    elements=["Ba", "Ti", "O"],
    weight_pct=[58.9, 20.5, 20.6]
)
```

**Key results:** Elemental composition in wt% and at% (higher precision than EDS)

---

### ICP-MS / ICP-OES

**Data:** Element vs concentration (ppb, ppm, mg/L). File formats: .csv, .xlsx

**Load:**
```python
df = load_data("icp_results.xlsx")
```

**Analyse:**
```python
from analysis.statistics import descriptive
from analysis.fitting import fit_curve

# Descriptive stats on repeat measurements
for element in df.columns[1:]:
    stats = descriptive(df[element].values)

# Calibration curve
fit = fit_curve(df["concentration"], df["signal"], model="linear")
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["concentration"], df["signal"], kind="scatter",
                    xlabel="Concentration (ppb)", ylabel="Signal (CPS)",
                    label="Calibration")
export_figure(fig, "icp_calibration.svg")
```

**Key results:** Elemental concentrations (ppb/ppm), calibration R2, detection limits

---

### XRF (X-ray Fluorescence)

**Data:** Energy (keV) vs intensity (counts) or element vs wt%. File formats: .csv, .xlsx

**Load:**
```python
df = load_data("xrf_spectrum.csv")
```

**Analyse:**
```python
from analysis.peaks import find_peaks_auto
from techniques.sem_eds import parse_eds_composition

# Spectrum peak detection
peaks = find_peaks_auto(df["energy_keV"], df["counts"], min_height_pct=3.0)

# Composition table (if already quantified)
comp = parse_eds_composition(
    elements=["Fe", "Si", "Al", "Ca"],
    weight_pct=[35.2, 25.1, 18.3, 12.4]
)
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["energy_keV"], df["counts"], kind="line",
                    xlabel="Energy (keV)", ylabel="Counts")
export_figure(fig, "xrf_spectrum.svg")
```

**Key results:** Elemental composition (wt%), characteristic X-ray energies (keV)

---

## Surface Techniques

### Contact Angle

**Data:** Time (s) vs contact angle (deg), or left/right angle measurements. File formats: .csv, .xlsx

**Load:**
```python
df = load_data("contact_angle.csv")
```

**Analyse:**
```python
from analysis.statistics import descriptive

# Static contact angle
stats = descriptive(df["angle"])
# Returns: DescriptiveStats with mean, std, CI

# Dynamic (advancing/receding)
adv = descriptive(df["advancing"])
rec = descriptive(df["receding"])
hysteresis = adv.mean - rec.mean
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(None, [df["advancing"].values, df["receding"].values],
                    kind="box", labels=["Advancing", "Receding"],
                    ylabel="Contact Angle (deg)")
export_figure(fig, "contact_angle.svg")
```

**Key results:** Static angle (deg), advancing/receding angles, contact angle hysteresis

---

### Ellipsometry

**Data:** Wavelength (nm) or angle (deg) vs psi and delta. File formats: .csv, .dat

**Load:**
```python
df = load_data("ellipsometry.csv")
```

**Analyse:**
```python
from analysis.fitting import fit_curve

# Fit Cauchy model for transparent films
# n(lambda) = A + B/lambda^2 + C/lambda^4
fit = fit_curve(df["wavelength"], df["psi"], model="polynomial", degree=4)

# Film thickness from interference fringes
from analysis.peaks import find_peaks_auto
peaks = find_peaks_auto(df["wavelength"], df["psi"])
```

**Plot:**
```python
apply_style("nature")
fig, axes = create_subplots(2, 1, sharex=True)
axes[0].plot(df["wavelength"], df["psi"])
axes[0].set_ylabel("Psi (deg)")
axes[1].plot(df["wavelength"], df["delta"])
axes[1].set_ylabel("Delta (deg)")
axes[1].set_xlabel("Wavelength (nm)")
export_figure(fig, "ellipsometry.svg")
```

**Key results:** Film thickness (nm), refractive index n, extinction coefficient k

---

### Profilometry

**Data:** Position (um) vs height (um or nm). File formats: .csv, .txt

**Load:**
```python
df = load_data("profilometry.csv")
```

**Analyse:**
```python
from techniques.afm import profile_roughness

# Same roughness analysis as AFM profiles
rough = profile_roughness(df["height"], unit="um", detrend=True)
# Returns: Ra, Rq, Rz, Rmax, Rsk, Rku

# Step height measurement
step = df["height"].max() - df["height"].min()
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["position"], df["height"], kind="line",
                    xlabel="Position (um)", ylabel="Height (um)")
export_figure(fig, "profilometry.svg")
```

**Key results:** Ra, Rq (um or nm), step height, film thickness

---

## Thermal Techniques

### DSC (Differential Scanning Calorimetry)

**Data:** Temperature (C) vs heat flow (mW or W/g). File formats: .csv, .txt, .xlsx

**Load:**
```python
df = load_data("dsc_scan.csv")
```

**Analyse:**
```python
from techniques.dsc_tga import analyse_dsc

results = analyse_dsc(df["temperature"], df["heat_flow"],
                      endotherm_down=True,    # TA Instruments convention
                      dh_reference=293.0,     # J/g for 100% crystalline PE
                      smoothing_window=11)
# Returns: DSCResults with Tg, Tm, Tc, crystallinity %, transitions list
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["temperature"], df["heat_flow"], kind="line",
                    xlabel="Temperature (C)", ylabel="Heat Flow (W/g)")
export_figure(fig, "dsc_curve.svg")
```

**Key results:** Tg (C), Tm (C), Tc (C), enthalpy of fusion (J/g), crystallinity (%)

---

### TGA (Thermogravimetric Analysis)

**Data:** Temperature (C) vs mass (% or mg). File formats: .csv, .txt, .xlsx

**Load:**
```python
df = load_data("tga_scan.csv")
```

**Analyse:**
```python
from techniques.dsc_tga import analyse_tga

results = analyse_tga(df["temperature"], df["mass"],
                      mass_unit="percent", smoothing_window=11)
# Returns: TGAResults with steps (onset, endset, DTG peak, mass loss %), residue %
```

**Plot:**
```python
apply_style("nature")
fig, axes = create_subplots(2, 1, sharex=True)
axes[0].plot(df["temperature"], df["mass"])
axes[0].set_ylabel("Mass (%)")
# DTG (derivative)
import numpy as np
dtg = np.gradient(df["mass"], df["temperature"])
axes[1].plot(df["temperature"], dtg)
axes[1].set_ylabel("DTG (%/C)")
axes[1].set_xlabel("Temperature (C)")
export_figure(fig, "tga_dtg.svg")
```

**Key results:** Onset/endset temperatures (C), DTG peak temperatures, mass loss per step (%), final residue (%)

---

### DTA (Differential Thermal Analysis)

**Data:** Temperature (C) vs delta-T (C). File formats: .csv, .txt

**Load:**
```python
df = load_data("dta_scan.csv")
```

**Analyse:**
```python
# DTA is analysed the same way as DSC (different signal, same transitions)
from techniques.dsc_tga import analyse_dsc

results = analyse_dsc(df["temperature"], df["delta_T"],
                      endotherm_down=True, smoothing_window=11)
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["temperature"], df["delta_T"], kind="line",
                    xlabel="Temperature (C)", ylabel="Delta T (C)")
export_figure(fig, "dta_curve.svg")
```

**Key results:** Transition temperatures (C), endothermic/exothermic peaks

---

### TMA (Thermomechanical Analysis)

**Data:** Temperature (C) vs dimensional change (um or %). File formats: .csv, .txt

**Load:**
```python
df = load_data("tma_scan.csv")
```

**Analyse:**
```python
from analysis.fitting import fit_curve

# CTE from linear region slope
fit = fit_curve(df["temperature"], df["displacement"], model="linear")
# CTE = slope / original_length

# Tg from change in slope
from analysis.peaks import find_peaks_auto
deriv = np.gradient(df["displacement"], df["temperature"])
peaks = find_peaks_auto(df["temperature"], np.abs(np.gradient(deriv, df["temperature"])))
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["temperature"], df["displacement"], kind="line",
                    xlabel="Temperature (C)", ylabel="Displacement (um)")
export_figure(fig, "tma_curve.svg")
```

**Key results:** Tg (C), coefficient of thermal expansion (CTE), softening point

---

### DMA (Dynamic Mechanical Analysis)

**Data:** Temperature (C) vs storage modulus (MPa), loss modulus (MPa), tan delta. File formats: .csv, .xlsx

**Load:**
```python
df = load_data("dma_scan.csv")
```

**Analyse:**
```python
from techniques.mechanical import analyse_dma

results = analyse_dma(df["temperature"], df["storage_modulus"],
                      df["loss_modulus"], tan_delta=df["tan_delta"])
# Returns: DMAResults with Tg (from tan delta peak and loss modulus peak),
# storage modulus onset
```

**Plot:**
```python
apply_style("nature")
fig, ax1 = plt.subplots()
ax1.semilogy(df["temperature"], df["storage_modulus"], label="E'")
ax1.semilogy(df["temperature"], df["loss_modulus"], label="E''")
ax1.set_xlabel("Temperature (C)")
ax1.set_ylabel("Modulus (MPa)")
ax2 = ax1.twinx()
ax2.plot(df["temperature"], df["tan_delta"], "r--", label="tan delta")
ax2.set_ylabel("tan delta")
export_figure(fig, "dma_curve.svg")
```

**Key results:** Tg from tan delta peak (C), Tg from loss modulus peak (C), glassy plateau modulus (MPa), peak tan delta value

---

## Mechanical Techniques

### Tensile Testing

**Data:** Strain (% or fraction) vs stress (MPa). File formats: .csv, .xlsx, .txt

**Load:**
```python
df = load_data("tensile_test.csv")
```

**Analyse:**
```python
from techniques.mechanical import analyse_tensile, force_to_stress, displacement_to_strain

# Convert raw force/displacement if needed
stress = force_to_stress(df["force_N"], area=12.57)  # mm2
strain = displacement_to_strain(df["displacement_mm"], gauge_length=50.0)

results = analyse_tensile(strain, stress, strain_unit="percent")
# Returns: TensileResults with Young's modulus, yield strength (0.2% offset),
# UTS, elongation at break, toughness
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(strain, stress, kind="line",
                    xlabel="Strain (%)", ylabel="Stress (MPa)")
export_figure(fig, "stress_strain.svg")
```

**Key results:** Young's modulus (MPa), yield strength (MPa), UTS (MPa), elongation at break (%), toughness (MJ/m3)

---

### Compression Testing

**Data:** Same format as tensile -- strain (%) vs stress (MPa).

**Analyse:**
```python
from techniques.mechanical import analyse_tensile

# Same analysis function works for compression
results = analyse_tensile(df["strain"], df["stress"], strain_unit="percent")
# UTS becomes compressive strength, yield is compressive yield
```

**Key results:** Compressive modulus (MPa), compressive strength (MPa), yield stress (MPa)

---

### Hardness (Vickers / Rockwell / Brinell)

**Data:** Load (N or kgf), diagonal/indentation measurements. File formats: .csv, .xlsx

**Load:**
```python
df = load_data("hardness_measurements.csv")
```

**Analyse:**
```python
from analysis.statistics import descriptive

# Vickers hardness from diagonal measurements
# HV = 1.8544 * F / d^2 (F in kgf, d in mm)
df["HV"] = 1.8544 * df["load_kgf"] / (df["diagonal_mm"] ** 2)
stats = descriptive(df["HV"].values)
# Returns: mean, std, 95% CI
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(None, df["HV"].values, kind="box",
                    ylabel="Vickers Hardness (HV)")
export_figure(fig, "hardness.svg")
```

**Key results:** Mean hardness (HV, HRC, or HB), standard deviation, 95% confidence interval

---

### Nanoindentation

**Data:** Depth (nm) vs load (mN). File formats: .csv, .txt, .xlsx

**Load:**
```python
df = load_data("nanoindent.csv")
```

**Analyse:**
```python
from techniques.nanoindentation import analyse_indent, batch_indents, creep_analysis

# Single indent (Oliver-Pharr method)
result = analyse_indent(df["depth_nm"], df["load_mN"],
                        tip="berkovich", poisson_sample=0.3)
# Returns: IndentResult with hardness (GPa), modulus (GPa), contact depth

# Batch analysis (multiple indents)
indent_pairs = [(df1["depth"], df1["load"]), (df2["depth"], df2["load"]), ...]
batch = batch_indents(indent_pairs, tip="berkovich")
# Returns: BatchIndentResult with mean/std hardness and modulus

# Creep analysis during hold segment
creep = creep_analysis(df_hold["time"], df_hold["depth"], model="log")
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["depth_nm"], df["load_mN"], kind="line",
                    xlabel="Depth (nm)", ylabel="Load (mN)")
export_figure(fig, "load_displacement.svg")
```

**Key results:** Hardness (GPa), reduced modulus (GPa), elastic modulus (GPa), contact stiffness, creep displacement

---

### Fatigue Testing

**Data:** Cycles (N) vs stress amplitude (MPa) or strain amplitude. File formats: .csv, .xlsx

**Load:**
```python
df = load_data("fatigue_data.csv")
```

**Analyse:**
```python
from analysis.fitting import fit_curve

# S-N curve (Basquin's law): S = A * N^b
fit = fit_curve(df["cycles"], df["stress_amplitude"], model="power")
# Returns: FitResult with A (coefficient) and b (exponent)
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["cycles"], df["stress_amplitude"],
                    kind="scatter", log_x=True,
                    xlabel="Cycles to Failure (N)", ylabel="Stress Amplitude (MPa)")
export_figure(fig, "sn_curve.svg")
```

**Key results:** Fatigue life (cycles), endurance limit (MPa), Basquin exponent

---

### Creep Testing

**Data:** Time (s or h) vs strain (%) at constant stress. File formats: .csv, .xlsx

**Load:**
```python
df = load_data("creep_data.csv")
```

**Analyse:**
```python
from techniques.nanoindentation import creep_analysis

# Logarithmic or power-law creep model
result = creep_analysis(df["time_s"], df["strain"],
                        load=100.0, model="log")
# Returns: dict with model parameters, R2, total creep
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["time_s"], df["strain"], kind="line",
                    xlabel="Time (s)", ylabel="Strain (%)")
export_figure(fig, "creep_curve.svg")
```

**Key results:** Creep rate, total creep displacement, model parameters

---

### Fracture Toughness

**Data:** Crack length (mm) vs load (kN), or J-integral data. File formats: .csv, .xlsx

**Load:**
```python
df = load_data("fracture_toughness.csv")
```

**Analyse:**
```python
from analysis.fitting import fit_curve
from analysis.statistics import descriptive

# KIc from SENB or compact tension
# KIc = (P * S) / (B * W^(3/2)) * f(a/W)  -- geometry-dependent
stats = descriptive(df["KIc"].values)
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["displacement"], df["load"], kind="line",
                    xlabel="Displacement (mm)", ylabel="Load (kN)")
export_figure(fig, "fracture_toughness.svg")
```

**Key results:** KIc (MPa.m^0.5), critical load (kN), crack length (mm)

---

## Electrical Techniques

### Four-Point Probe

**Data:** Voltage (V) vs current (A) measurements. File formats: .csv, .xlsx

**Load:**
```python
df = load_data("four_point_probe.csv")
```

**Analyse:**
```python
from techniques.iv_curves import four_point_probe

result = four_point_probe(
    df["voltage"], df["current"],
    spacing=1e-3,        # probe spacing in metres
    thickness=500e-6     # sample thickness in metres
)
# Returns: FourPointResult with sheet_resistance (Ohm/sq), resistivity (Ohm.m)
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["current"], df["voltage"], kind="scatter",
                    xlabel="Current (A)", ylabel="Voltage (V)")
export_figure(fig, "four_point_probe.svg")
```

**Key results:** Sheet resistance (Ohm/sq), resistivity (Ohm.m), correction factor

---

### Hall Effect

**Data:** Magnetic field (T) vs Hall voltage (V) at fixed current. File formats: .csv, .xlsx

**Load:**
```python
df = load_data("hall_effect.csv")
```

**Analyse:**
```python
from analysis.fitting import fit_curve

# Hall coefficient: RH = VH * t / (I * B)
fit = fit_curve(df["field_T"], df["hall_voltage_V"], model="linear")
# slope = VH/B; RH = slope * thickness / current
RH = fit.params["slope"] * thickness / current
carrier_conc = 1.0 / (1.602e-19 * abs(RH))  # cm-3
mobility = abs(RH) / resistivity  # cm2/(V.s)
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["field_T"], df["hall_voltage_V"], kind="scatter",
                    xlabel="Magnetic Field (T)", ylabel="Hall Voltage (V)")
export_figure(fig, "hall_effect.svg")
```

**Key results:** Hall coefficient (m3/C), carrier concentration (cm-3), mobility (cm2/V.s), carrier type (n/p)

---

### Impedance Spectroscopy (EIS)

**Data:** Frequency (Hz), Z' (Ohm), Z'' (Ohm) or |Z|, phase (deg). File formats: .csv, .dta (Gamry), .txt

**Load:**
```python
df = load_data("eis_data.csv")
# Gamry .dta files auto-detected:
df = load_data("impedance.dta")
```

**Analyse:**
```python
from techniques.impedance import parse_impedance, fit_circuit, plot_nyquist, plot_bode
from techniques.impedance import calc_conductivity, arrhenius_conductivity

data = parse_impedance(df["freq"], z_real=df["Zreal"], z_imag=df["Zimag"])
# Or from modulus/phase: parse_impedance(freq, z_mod=|Z|, z_phase=phase)

# Circuit fitting
fit = fit_circuit(data, circuit="randles")
# Available circuits: "randles", "randles_cpe", "rc", "r_cpe"

# Conductivity
sigma = calc_conductivity(resistance=fit.params["Rct"],
                          thickness=0.1, area=1.0)  # cm, cm2

# Arrhenius analysis
arr = arrhenius_conductivity(
    temperatures_c=[25, 50, 75, 100, 125],
    conductivities=[1e-5, 3e-5, 8e-5, 2e-4, 5e-4]
)
# Returns: dict with Ea_eV, sigma_0, r_squared
```

**Plot:**
```python
apply_style("nature")
fig_ny, ax_ny = plot_nyquist(data, fit=fit)
export_figure(fig_ny, "nyquist.svg")

fig_bo, axes_bo = plot_bode(data, fit=fit)
export_figure(fig_bo, "bode.svg")
```

**Key results:** Circuit parameters (Rs, Rct, Cdl, CPE), conductivity (S/cm), activation energy (eV)

---

### I-V Curves

**Data:** Voltage (V) vs current (A or mA). File formats: .csv, .txt

**Load:**
```python
df = load_data("iv_curve.csv")
```

**Analyse:**
```python
from techniques.iv_curves import analyse_iv, analyse_diode

# General I-V analysis
result = analyse_iv(df["voltage"], df["current"])
# Returns: dict with resistance, r_squared, is_diode

# Diode fitting (Shockley equation)
diode = analyse_diode(df["voltage"], df["current"], temperature=300.0)
# Returns: DiodeResult with ideality factor, saturation current, series resistance
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["voltage"], df["current"], kind="line",
                    xlabel="Voltage (V)", ylabel="Current (mA)")
export_figure(fig, "iv_curve.svg")
```

**Key results:** Resistance (Ohm), ideality factor n, saturation current I0, series resistance Rs

---

### C-V Measurement

**Data:** Voltage (V) vs capacitance (F or pF). File formats: .csv, .txt

**Load:**
```python
df = load_data("cv_measurement.csv")
```

**Analyse:**
```python
from techniques.cv_measurement import analyse_cv, mott_schottky, doping_profile

# General C-V analysis
cv = analyse_cv(df["voltage"], df["capacitance"])
# Returns: CVResult with flat_band_voltage, max/min capacitance

# Mott-Schottky analysis
ms = mott_schottky(df["voltage"], df["capacitance"],
                   area=0.01, permittivity=11.7)
# Returns: MottSchottkyResult with doping concentration, flat_band voltage, carrier type

# Doping profile
W, N = doping_profile(df["voltage"], df["capacitance"],
                      area=0.01, permittivity=11.7)
```

**Plot:**
```python
apply_style("nature")
# C-V curve
fig, ax = plot_data(df["voltage"], df["capacitance"] * 1e12, kind="line",
                    xlabel="Voltage (V)", ylabel="Capacitance (pF)")
export_figure(fig, "cv_curve.svg")

# Mott-Schottky plot (1/C^2 vs V)
inv_c2 = 1.0 / (df["capacitance"] ** 2)
fig2, ax2 = plot_data(df["voltage"], inv_c2, kind="scatter",
                      xlabel="Voltage (V)", ylabel="1/C^2 (F^-2)")
export_figure(fig2, "mott_schottky.svg")
```

**Key results:** Flat-band voltage (V), doping concentration (cm-3), carrier type (n/p), built-in potential

---

### Solar Cell J-V

**Data:** Voltage (V) vs current density (mA/cm2). File formats: .csv, .txt

**Load:**
```python
df = load_data("solar_cell_jv.csv")
```

**Analyse:**
```python
from techniques.iv_curves import analyse_solar_cell

result = analyse_solar_cell(df["voltage"], df["current_density"],
                            illumination=100.0)  # mW/cm2 for 1-sun AM1.5
# Returns: SolarCellResult with Voc, Jsc, fill_factor, efficiency (PCE)
```

**Plot:**
```python
apply_style("nature")
fig, ax1 = plt.subplots()
ax1.plot(df["voltage"], df["current_density"], "b-", label="J-V")
ax1.set_xlabel("Voltage (V)")
ax1.set_ylabel("Current Density (mA/cm2)")
ax2 = ax1.twinx()
power = df["voltage"] * df["current_density"]
ax2.plot(df["voltage"], power, "r--", label="Power")
ax2.set_ylabel("Power Density (mW/cm2)")
export_figure(fig, "solar_cell_jv.svg")
```

**Key results:** Voc (V), Jsc (mA/cm2), fill factor, PCE (%), Pmax, V_mpp, J_mpp

---

## Magnetic Techniques

### VSM / SQUID (M-H Loops)

**Data:** Magnetic field (Oe or T) vs magnetisation (emu/g or A/m). File formats: .csv, .dat

**Load:**
```python
df = load_data("vsm_data.csv")
```

**Analyse:**
```python
from techniques.magnetometry import analyse_mh_loop, langevin_fit

# M-H loop analysis
loop = analyse_mh_loop(df["field_Oe"], df["magnetisation_emu_g"])
# Returns: MHLoopResult with Ms, Mr, Hc, squareness, loop area

# Langevin fit for superparamagnetic particles
lang = langevin_fit(df["field_T"], df["magnetisation"], temperature=300.0)
# Returns: LangevinResult with Ms, magnetic moment (J/T and Bohr magnetons)
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["field_Oe"], df["magnetisation_emu_g"], kind="line",
                    xlabel="Magnetic Field (Oe)",
                    ylabel="Magnetisation (emu/g)")
export_figure(fig, "mh_loop.svg")
```

**Key results:** Ms (emu/g), Mr (emu/g), Hc (Oe), squareness Mr/Ms, loop area

---

### Curie Temperature

**Data:** Temperature (K or C) vs magnetisation (emu/g). File formats: .csv, .dat

**Load:**
```python
df = load_data("mt_data.csv")
```

**Analyse:**
```python
from techniques.magnetometry import curie_temperature

tc = curie_temperature(df["temperature_K"], df["magnetisation"],
                       method="inflection")
# Returns: CurieResult with Tc (from dM/dT inflection point)
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["temperature_K"], df["magnetisation"], kind="line",
                    xlabel="Temperature (K)", ylabel="Magnetisation (emu/g)")
export_figure(fig, "mt_curie.svg")
```

**Key results:** Curie temperature Tc (K or C)

---

## Porosity Techniques

### BET (Surface Area)

**Data:** Relative pressure P/P0 vs quantity adsorbed (cm3/g STP). File formats: .csv, .txt, .xlsx

**Load:**
```python
df = load_data("bet_isotherm.csv")
```

**Analyse:**
```python
from techniques.bet import analyse_bet, bjh_pore_distribution, classify_isotherm, total_pore_volume

# BET surface area
bet = analyse_bet(df["p_p0"], df["quantity_adsorbed"], adsorbate="N2")
# Returns: BETResult with surface_area_m2g, bet_constant_c, monolayer_capacity, R2

# Pore size distribution (BJH)
pores = bjh_pore_distribution(df["p_p0"], df["quantity_adsorbed"],
                               branch="desorption")
# Returns: PoreDistribution with diameters, dV/dD, mean pore diameter, total pore volume

# Isotherm classification
iso_type = classify_isotherm(df["p_p0"], df["quantity_adsorbed"])
# Returns: string e.g. "Type IV"

# Total pore volume
v_pore = total_pore_volume(df["p_p0"], df["quantity_adsorbed"])
```

**Plot:**
```python
apply_style("nature")
# Isotherm
fig, ax = plot_data(df["p_p0"], df["quantity_adsorbed"], kind="line",
                    xlabel="Relative Pressure (P/P0)",
                    ylabel="Quantity Adsorbed (cm3/g STP)")
export_figure(fig, "bet_isotherm.svg")

# Pore size distribution
fig2, ax2 = plot_data(pores.diameters, pores.dv_dd, kind="line",
                      xlabel="Pore Diameter (nm)", ylabel="dV/dD (cm3/g/nm)")
export_figure(fig2, "pore_distribution.svg")
```

**Key results:** BET surface area (m2/g), BET constant C, mean pore diameter (nm), total pore volume (cm3/g), isotherm type

---

### Mercury Porosimetry

**Data:** Pressure (MPa or psia) vs cumulative intrusion volume (mL/g). File formats: .csv, .xlsx

**Load:**
```python
df = load_data("mercury_porosimetry.csv")
```

**Analyse:**
```python
# Washburn equation: D = -4 * gamma * cos(theta) / P
# gamma = 0.485 N/m, theta = 130 deg for mercury
import numpy as np
gamma = 0.485
theta = np.radians(130)
df["diameter_nm"] = -4 * gamma * np.cos(theta) / (df["pressure_MPa"] * 1e6) * 1e9

# Pore size distribution from derivative
dv = np.gradient(df["intrusion_mL_g"], df["diameter_nm"])

from analysis.statistics import descriptive
stats = descriptive(df["diameter_nm"].values)
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["diameter_nm"], dv, kind="line",
                    log_x=True,
                    xlabel="Pore Diameter (nm)",
                    ylabel="dV/dD (mL/g/nm)")
export_figure(fig, "mercury_psd.svg")
```

**Key results:** Porosity (%), median pore diameter (nm), total intrusion volume (mL/g), bulk/skeletal density

---

### Gas Adsorption (General)

**Data:** Same as BET -- P/P0 vs quantity adsorbed.

**Analyse:**
```python
from techniques.bet import analyse_bet, bjh_pore_distribution

# Works with N2, Ar, Kr -- specify the adsorbate
bet = analyse_bet(df["p_p0"], df["quantity_adsorbed"], adsorbate="Ar")
pores = bjh_pore_distribution(df["p_p0"], df["quantity_adsorbed"])
```

**Key results:** Same as BET section above. Ar gives better resolution for micropores.

---

## Chromatography

### GC / HPLC / IC / SEC

**Data:** Retention time (min) vs detector signal (mAU, counts, etc.). File formats: .csv, .txt

**Load:**
```python
df = load_data("chromatogram.csv")
```

**Analyse:**
```python
from techniques.chromatography import analyse_chromatogram, calibration_curve

# Peak detection and characterisation
results = analyse_chromatogram(df["time_min"], df["signal"],
                               technique="HPLC", min_peak_height_pct=3.0)
# Returns: ChromResults with peaks (retention time, area, height, width,
# plate count, asymmetry, resolution)

# Calibration curve for quantification
cal = calibration_curve(
    concentrations=[1, 5, 10, 25, 50, 100],
    areas_or_heights=[120, 580, 1150, 2900, 5800, 11500],
    unknown_area=3500
)
# Returns: CalibrationResult with slope, intercept, R2, unknown_concentration
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["time_min"], df["signal"], kind="line",
                    xlabel="Retention Time (min)", ylabel="Signal (mAU)")
export_figure(fig, "chromatogram.svg")
```

**Key results:** Retention times (min), peak areas and area%, plate count N, resolution Rs, asymmetry factor

---

## Mass Spectrometry

### MS / MALDI / TOF-MS

**Data:** m/z vs intensity (counts or relative). File formats: .csv, .txt, .jdx

**Load:**
```python
df = load_data("mass_spectrum.csv")
```

**Analyse:**
```python
from techniques.mass_spec import analyse_spectrum, find_molecular_ion, isotope_pattern, mass_accuracy

# Peak detection
results = analyse_spectrum(df["mz"], df["intensity"], charge=1)
# Returns: MSResults with peaks (m/z, intensity, neutral mass), base peak, TIC

# Molecular ion identification (checks for [M+H]+, [M+Na]+, etc.)
ions = find_molecular_ion(df["mz"], df["intensity"])

# Predicted isotope pattern from formula
pattern = isotope_pattern("C12H22O11")
# Returns: dict with M, M+1, M+2 relative intensities and monoisotopic mass

# Mass accuracy
ppm = mass_accuracy(measured=342.1165, theoretical=342.1162)
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["mz"], df["intensity"], kind="step",
                    xlabel="m/z", ylabel="Relative Intensity (%)")
export_figure(fig, "mass_spectrum.svg")
```

**Key results:** Molecular ion m/z, neutral mass (Da), mass accuracy (ppm), isotope pattern, adduct assignments

---

## Dielectric and Piezoelectric

### Permittivity and Loss Tangent

**Data:** Frequency (Hz) vs permittivity (epsilon_r) and loss tangent (tan delta). File formats: .csv, .txt

**Load:**
```python
df = load_data("dielectric_data.csv")
```

**Analyse:**
```python
from techniques.dielectric import parse_dielectric, analyse_dielectric

data = parse_dielectric(df["frequency"], df["epsilon_r"],
                        tan_delta=df["tan_delta"])
# Or calculate from capacitance:
data = parse_dielectric(df["frequency"], df["epsilon_r"],
                        capacitance=df["capacitance_F"],
                        area=1e-4, thickness=1e-3)  # m2, m

results = analyse_dielectric(data)
# Returns: DielectricResults with peak permittivity, frequency at peak, peak tan delta
```

**Plot:**
```python
apply_style("nature")
fig, ax1 = plt.subplots()
ax1.semilogx(data.frequency, data.epsilon_r, "b-", label="epsilon_r")
ax1.set_xlabel("Frequency (Hz)")
ax1.set_ylabel("Relative Permittivity")
ax2 = ax1.twinx()
ax2.semilogx(data.frequency, data.tan_delta, "r--", label="tan delta")
ax2.set_ylabel("Loss Tangent")
export_figure(fig, "dielectric_frequency.svg")
```

**Key results:** Peak permittivity, frequency at peak, peak loss tangent, AC conductivity

---

### Cole-Cole Plot

**Data:** Real permittivity (epsilon') vs imaginary permittivity (epsilon'').

**Analyse:**
```python
from techniques.dielectric import cole_cole_data

er, ei = cole_cole_data(df["epsilon_r"], df["epsilon_i"])
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(er, ei, kind="scatter",
                    xlabel="epsilon'", ylabel="epsilon''")
ax.set_aspect("equal")
export_figure(fig, "cole_cole.svg")
```

**Key results:** Relaxation time, distribution of relaxation times, static and high-frequency permittivity

---

### Curie-Weiss Fitting

**Data:** Temperature (C or K) vs permittivity. File formats: .csv, .txt

**Analyse:**
```python
from techniques.dielectric import curie_weiss_fit

cw = curie_weiss_fit(df["temperature"], df["permittivity"],
                     temp_range=(200, 400))  # fit above Tc only
# Returns: dict with Tc (Curie temperature), C (Curie constant), r_squared
```

**Key results:** Curie temperature Tc, Curie-Weiss constant C, R2

---

### P-E Hysteresis Loops

**Data:** Electric field (kV/cm) vs polarisation (uC/cm2). File formats: .csv, .txt

**Load:**
```python
df = load_data("pe_loop.csv")
```

**Analyse:**
```python
from techniques.piezoelectric import analyse_pe_loop

results = analyse_pe_loop(df["electric_field"], df["polarisation"])
# Returns: PELoopResults with Pr (remanent), Ec (coercive), Ps (saturation),
# loop area (energy loss)
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["electric_field"], df["polarisation"], kind="line",
                    xlabel="Electric Field (kV/cm)",
                    ylabel="Polarisation (uC/cm2)")
export_figure(fig, "pe_loop.svg")
```

**Key results:** Pr (uC/cm2), Ec (kV/cm), Ps (uC/cm2), loop area

---

### S-E Butterfly Curves

**Data:** Electric field (kV/cm) vs strain (%). File formats: .csv, .txt

**Load:**
```python
df = load_data("se_curve.csv")
```

**Analyse:**
```python
from techniques.piezoelectric import analyse_se_curve

results = analyse_se_curve(df["electric_field"], df["strain"],
                           thickness=1.0)  # mm
# Returns: SECurveResults with d33_eff (pm/V), S_max (%), asymmetry
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["electric_field"], df["strain"], kind="line",
                    xlabel="Electric Field (kV/cm)", ylabel="Strain (%)")
export_figure(fig, "se_butterfly.svg")
```

**Key results:** Effective d33 (pm/V), maximum strain (%), negative strain, strain asymmetry

---

### Impedance Resonance (Piezoelectric)

**Data:** Frequency (Hz) vs |Z| (Ohm) and phase (deg). File formats: .csv, .txt

**Load:**
```python
df = load_data("resonance.csv")
```

**Analyse:**
```python
from techniques.piezoelectric import analyse_resonance

results = analyse_resonance(df["frequency"], df["impedance"],
                            capacitance_free=1e-9)
# Returns: ResonanceResults with fr, fa, kp, kt, Qm
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["frequency"], df["impedance"],
                    kind="line", log_y=True,
                    xlabel="Frequency (Hz)", ylabel="|Z| (Ohm)")
export_figure(fig, "impedance_resonance.svg")
```

**Key results:** Resonance fr (Hz), anti-resonance fa (Hz), coupling factor kp/kt, mechanical quality factor Qm

---

## Thermal Conductivity

### Laser Flash

**Data:** Time (s) vs normalised temperature rise (0-1) on rear face. File formats: .csv, .txt

**Load:**
```python
df = load_data("laser_flash.csv")
```

**Analyse:**
```python
from techniques.thermal_conductivity import laser_flash_diffusivity, calc_conductivity

# Thermal diffusivity from half-rise time (Parker method)
alpha = laser_flash_diffusivity(df["time_s"], df["temperature_rise"],
                                 thickness=2e-3, method="parker")
# Returns: diffusivity in m2/s

# Calculate thermal conductivity: k = alpha * Cp * rho
result = calc_conductivity(diffusivity=alpha,
                           specific_heat=500,  # J/(kg.K)
                           density=7800)       # kg/m3
# Returns: ThermalConductivityResult with k in W/(m.K)
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(df["time_s"] * 1000, df["temperature_rise"], kind="line",
                    xlabel="Time (ms)", ylabel="Normalised Temperature Rise")
export_figure(fig, "laser_flash.svg")
```

**Key results:** Thermal diffusivity (m2/s), thermal conductivity (W/m.K)

---

### Steady-State Methods

**Data:** Heat flux (W), temperature difference (K), geometry. File formats: .csv or manual entry.

**Analyse:**
```python
from techniques.thermal_conductivity import steady_state_conductivity, conductivity_vs_temperature

# Single measurement (Fourier's law)
k = steady_state_conductivity(heat_flux=5.0, thickness=0.01,
                               delta_T=10.0, area=0.001)
# Returns: k in W/(m.K)

# Temperature-dependent conductivity
result = conductivity_vs_temperature(
    temperatures=[25, 100, 200, 300, 400],
    conductivities=[1.5, 1.8, 2.1, 2.3, 2.4]
)
# Returns: dict with polynomial fit parameters and R2
```

**Plot:**
```python
apply_style("nature")
fig, ax = plot_data(result["temperatures"], result["conductivities"],
                    kind="scatter",
                    xlabel="Temperature (C)", ylabel="k (W/m.K)")
export_figure(fig, "k_vs_temperature.svg")
```

**Key results:** Thermal conductivity (W/m.K), temperature dependence coefficients
