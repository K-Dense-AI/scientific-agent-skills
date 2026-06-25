# Praxis Workflows

Complete multi-step analysis pipelines from raw data to publication figure. Each workflow shows the full sequence of function calls with comments.

---

## 1. XRD Full Pipeline

Load raw XRD data, correct baseline, detect and index peaks, calculate crystallite sizes, run Williamson-Hall analysis, and produce a Nature-style figure.

```python
import sys
sys.path.insert(0, "path/to/praxis/scripts")

from core.loader import load_data
from core.plotter import plot_data, plot_with_inset
from core.exporter import export_figure
from core.utils import apply_style
from analysis.baseline import correct_baseline
from analysis.smoothing import smooth
from techniques.xrd import analyse_xrd, williamson_hall

# Step 1: Load data
df = load_data("sample_xrd.xy")
two_theta = df["x"].values
intensity = df["y"].values

# Step 2: Optional baseline correction
corrected, baseline, _ = correct_baseline(two_theta, intensity, method="als")

# Step 3: Optional smoothing (only if noisy)
# corrected = smooth(corrected, method="savgol", window=7, polyorder=3)

# Step 4: Full XRD analysis (peaks, d-spacings, Scherrer, Williamson-Hall)
results = analyse_xrd(two_theta, corrected, wavelength="Cu_Ka",
                       min_height_pct=5.0, instrument_broadening=0.05)
# Results printed automatically as a table

# Step 5: Publication plot
apply_style("nature")
fig, ax = plot_data(two_theta, corrected, kind="line",
                    xlabel="2theta (deg)", ylabel="Intensity (a.u.)")
# Annotate major peaks
for peak in results.peaks[:5]:
    ax.annotate(f"{peak.d_spacing:.2f} A",
                xy=(peak.two_theta, peak.intensity),
                xytext=(0, 10), textcoords="offset points",
                fontsize=7, ha="center")

# Step 6: Inset zoom on a region of interest
fig2, ax2 = plot_with_inset(two_theta, corrected,
                             inset_xlim=(25, 35), inset_ylim=(0, 500),
                             xlabel="2theta (deg)", ylabel="Intensity (a.u.)")

# Step 7: Williamson-Hall plot (if results contain W-H data)
if results.wh_slope is not None:
    wh = williamson_hall(results.peaks, results.wavelength)
    fig3, ax3 = plot_data(wh["x"], wh["y"], kind="scatter",
                          xlabel="4 sin(theta)", ylabel="beta cos(theta)")
    import numpy as np
    x_fit = np.linspace(wh["x"].min(), wh["x"].max(), 100)
    ax3.plot(x_fit, results.wh_slope * x_fit + np.polyval(
        [results.wh_slope, wh["y"].mean() - results.wh_slope * wh["x"].mean()], x_fit
    ), "r--", label=f"R2={results.wh_r_squared:.4f}")

# Step 8: Export
export_figure(fig, "xrd_pattern.svg", dpi=300)
export_figure(fig, "xrd_pattern.png", dpi=600)
```

---

## 2. Impedance Analysis (EIS)

Load impedance data, parse into complex impedance, plot Nyquist and Bode, fit equivalent circuit, calculate conductivity, and run Arrhenius analysis across temperatures.

```python
from core.loader import load_data
from core.exporter import export_figure
from core.utils import apply_style
from techniques.impedance import (
    parse_impedance, fit_circuit, plot_nyquist, plot_bode,
    calc_conductivity, arrhenius_conductivity,
)

# Step 1: Load impedance data
df = load_data("eis_data.csv")
data = parse_impedance(df["freq"], z_real=df["Zreal"], z_imag=df["Zimag"])

# Step 2: Nyquist plot (quick look)
apply_style("nature")
fig_ny, ax_ny = plot_nyquist(data, title="Nyquist Plot")

# Step 3: Bode plot (quick look)
fig_bo, axes_bo = plot_bode(data, title="Bode Plot")

# Step 4: Fit equivalent circuit
fit = fit_circuit(data, circuit="randles_cpe",
                  params={"Rs": 50, "Rct": 5000, "Q": 1e-7, "n": 0.85, "Aw": 200})
# fit.report() printed automatically

# Step 5: Overlay fit on Nyquist
fig_ny2, ax_ny2 = plot_nyquist(data, fit=fit, title="Nyquist + Fit")
export_figure(fig_ny2, "nyquist_fit.svg")

# Step 6: Overlay fit on Bode
fig_bo2, axes_bo2 = plot_bode(data, fit=fit, title="Bode + Fit")
export_figure(fig_bo2, "bode_fit.svg")

# Step 7: Calculate conductivity from bulk resistance
sigma = calc_conductivity(
    resistance=fit.params["Rct"],
    thickness=0.1,   # cm
    area=1.0,        # cm2
)

# Step 8: Arrhenius analysis (from multiple temperatures)
temperatures = [25, 50, 75, 100, 125, 150]
conductivities = []

for temp, file in zip(temperatures, [f"eis_{t}C.csv" for t in temperatures]):
    df_t = load_data(file)
    data_t = parse_impedance(df_t["freq"], z_real=df_t["Zreal"], z_imag=df_t["Zimag"])
    fit_t = fit_circuit(data_t, circuit="randles_cpe")
    sigma_t = calc_conductivity(fit_t.params["Rct"], thickness=0.1, area=1.0)
    conductivities.append(sigma_t)

arr = arrhenius_conductivity(temperatures, conductivities)
# arr["Ea_eV"] = activation energy

# Step 9: Arrhenius plot
from core.plotter import plot_data
fig_arr, ax_arr = plot_data(arr["x"], arr["y"], kind="scatter",
                            xlabel="1000/T (1/K)", ylabel="ln(sigma*T)")
import numpy as np
x_line = np.linspace(arr["x"].min(), arr["x"].max(), 100)
coeffs = np.polyfit(arr["x"], arr["y"], 1)
ax_arr.plot(x_line, np.polyval(coeffs, x_line), "r--",
            label=f"Ea = {arr['Ea_eV']:.3f} eV")
ax_arr.legend(frameon=False)
export_figure(fig_arr, "arrhenius_conductivity.svg")
```

---

## 3. Tensile Testing

Load raw force-displacement data, convert to engineering stress-strain, extract all mechanical properties, and produce an annotated stress-strain curve.

```python
from core.loader import load_data
from core.plotter import plot_data
from core.exporter import export_figure
from core.utils import apply_style
from techniques.mechanical import (
    analyse_tensile, force_to_stress, displacement_to_strain,
)
import numpy as np

# Step 1: Load raw data
df = load_data("tensile_raw.csv")

# Step 2: Convert force/displacement to stress/strain
cross_section_area = 12.57  # mm2 (e.g. 4 mm diameter)
gauge_length = 50.0         # mm

stress = force_to_stress(df["force_N"], area=cross_section_area)  # MPa
strain = displacement_to_strain(df["displacement_mm"],
                                 gauge_length=gauge_length, unit="percent")

# Step 3: Full tensile analysis
results = analyse_tensile(strain, stress, strain_unit="percent",
                          smoothing_window=5)
# Prints: Young's modulus, yield strength, UTS, elongation, toughness

# Step 4: Publication plot with annotations
apply_style("nature")
fig, ax = plot_data(strain, stress, kind="line",
                    xlabel="Strain (%)", ylabel="Stress (MPa)")

# Annotate yield point
if results.yield_strength is not None:
    # Draw 0.2% offset line
    E = results.youngs_modulus
    strain_line = np.linspace(0.2, strain.max(), 100)
    stress_line = E * (strain_line / 100 - 0.002)
    ax.plot(strain_line, stress_line, "k--", linewidth=0.8, alpha=0.5)
    ax.annotate(f"sigma_y = {results.yield_strength:.0f} MPa",
                xy=(0.2, results.yield_strength),
                xytext=(2, results.yield_strength * 0.8),
                arrowprops=dict(arrowstyle="->", lw=0.8), fontsize=8)

# Annotate UTS
uts_idx = np.argmax(stress)
ax.annotate(f"UTS = {results.uts:.0f} MPa",
            xy=(strain[uts_idx], results.uts),
            xytext=(strain[uts_idx] + 2, results.uts - 20),
            arrowprops=dict(arrowstyle="->", lw=0.8), fontsize=8)

# Annotate modulus
ax.text(0.05, 0.95, f"E = {results.youngs_modulus:.0f} MPa",
        transform=ax.transAxes, fontsize=8, va="top")

# Step 5: Export
export_figure(fig, "stress_strain_annotated.svg", dpi=300)
```

---

## 4. DSC Analysis

Load DSC data, detect glass transition, melting, and crystallisation, integrate enthalpy, calculate crystallinity, and produce a publication figure.

```python
from core.loader import load_data
from core.plotter import plot_data, create_subplots
from core.exporter import export_figure
from core.utils import apply_style
from techniques.dsc_tga import analyse_dsc
import numpy as np

# Step 1: Load DSC data
df = load_data("dsc_scan.csv")
temp = df["temperature"].values
hf = df["heat_flow"].values

# Step 2: Full DSC analysis
results = analyse_dsc(temp, hf,
                      endotherm_down=True,       # TA Instruments convention
                      dh_reference=293.0,        # J/g for 100% crystalline (e.g. PET)
                      smoothing_window=15,
                      min_peak_height_pct=8.0)

# Step 3: Print key results
print(f"Tg = {results.tg} C") if results.tg else None
print(f"Tm = {results.tm} C") if results.tm else None
print(f"Tc = {results.tc} C") if results.tc else None
print(f"Crystallinity = {results.crystallinity:.1f}%") if results.crystallinity else None

# Step 4: Publication plot
apply_style("nature")
fig, ax = plot_data(temp, hf, kind="line",
                    xlabel="Temperature (C)",
                    ylabel="Heat Flow (W/g)")

# Annotate transitions
if results.tg:
    ax.axvline(results.tg, color="grey", linestyle=":", linewidth=0.8)
    ax.annotate(f"Tg = {results.tg:.1f} C", xy=(results.tg, hf.min()),
                xytext=(results.tg + 10, hf.min() * 0.9), fontsize=8)
if results.tm:
    ax.annotate(f"Tm = {results.tm:.1f} C",
                xy=(results.tm, hf[np.argmin(np.abs(temp - results.tm))]),
                xytext=(results.tm + 15, hf.mean()), fontsize=8,
                arrowprops=dict(arrowstyle="->", lw=0.8))

# Arrow indicating endo direction
ax.annotate("", xy=(temp.max() - 20, hf.max()),
            xytext=(temp.max() - 20, hf.min()),
            arrowprops=dict(arrowstyle="->", lw=1.0))
ax.text(temp.max() - 15, hf.mean(), "endo", fontsize=7, rotation=90)

# Step 5: Export
export_figure(fig, "dsc_analysis.svg", dpi=300)
```

---

## 5. FTIR Comparison

Batch-load multiple FTIR spectra, baseline-correct, normalise, overlay on a single plot with automatic peak labels.

```python
from core.loader import load_data
from core.plotter import overlay_plots
from core.exporter import export_figure
from core.utils import apply_style
from analysis.baseline import correct_baseline
from analysis.normalisation import normalise
from techniques.spectroscopy import analyse_ftir

# Step 1: Load multiple spectra
files = ["sample_A.csv", "sample_B.csv", "sample_C.csv"]
labels = ["Sample A", "Sample B", "Sample C"]
spectra = {}
for f in files:
    spectra[f] = load_data(f)

# Step 2: Baseline correct and normalise each spectrum
processed = {}
for name, df in spectra.items():
    wn = df.iloc[:, 0].values
    absorb = df.iloc[:, 1].values
    # Baseline correction
    corrected, _, _ = correct_baseline(wn, absorb, method="als")
    # Normalise to max = 1
    corrected = normalise(corrected, method="max")
    processed[name] = {"wn": wn, "absorb": corrected}

# Step 3: Analyse each for peaks
for name, data in processed.items():
    results = analyse_ftir(data["wn"], data["absorb"],
                           min_peak_height_pct=5.0, assign_peaks=True)
    processed[name]["peaks"] = results.peaks

# Step 4: Overlay plot
apply_style("nature")
datasets = []
for name, label in zip(files, labels):
    data = processed[name]
    datasets.append({
        "x": data["wn"], "y": data["absorb"],
        "label": label, "kind": "line",
    })

fig, ax = overlay_plots(datasets,
                        xlabel="Wavenumber (cm-1)",
                        ylabel="Absorbance (normalised)")
ax.invert_xaxis()  # IR convention: high wavenumber on left

# Step 5: Annotate key peaks from first spectrum
for peak in processed[files[0]]["peaks"][:6]:
    if peak.assignment:
        ax.annotate(peak.assignment,
                    xy=(peak.position, peak.intensity),
                    xytext=(0, 8), textcoords="offset points",
                    fontsize=6, ha="center", rotation=45)

# Step 6: Export
export_figure(fig, "ftir_comparison.svg", dpi=300)
```

---

## 6. XPS Quantification

Load survey scan, calibrate binding energy, identify elements, quantify atomic percentages, then fit high-resolution C 1s region.

```python
from core.loader import load_data
from core.plotter import plot_data, create_subplots
from core.exporter import export_figure
from core.utils import apply_style
from techniques.xps import analyse_survey, fit_highres, calibrate_be
import numpy as np

# Step 1: Load survey scan
df = load_data("xps_survey.csv")
be = df["binding_energy"].values
intens = df["intensity"].values

# Step 2: Calibrate binding energy (adventitious C at 284.8 eV)
be_cal, shift = calibrate_be(be, c1s_measured=285.3)
print(f"BE shift applied: {shift:+.2f} eV")

# Step 3: Survey scan analysis
survey = analyse_survey(be_cal, intens, min_peak_height_pct=3.0)
# Prints: elemental composition in at%

# Step 4: Publication survey plot
apply_style("nature")
fig, ax = plot_data(be_cal, intens, kind="line", invert_x=True,
                    xlabel="Binding Energy (eV)", ylabel="Intensity (CPS)")
# Label identified elements
for peak in survey.peaks:
    if peak.element:
        ax.annotate(peak.element,
                    xy=(peak.binding_energy, peak.intensity),
                    xytext=(0, 10), textcoords="offset points",
                    fontsize=7, ha="center")
export_figure(fig, "xps_survey.svg")

# Step 5: High-resolution C 1s fitting
df_c1s = load_data("xps_c1s.csv")
hr = fit_highres(df_c1s["binding_energy"].values + shift,
                 df_c1s["intensity"].values,
                 n_peaks=3, background="shirley",
                 peak_model="pseudo_voigt", element="C 1s")

# Step 6: High-res plot with deconvolution
fig2, ax2 = plot_data(df_c1s["binding_energy"] + shift, df_c1s["intensity"],
                      kind="line", invert_x=True,
                      xlabel="Binding Energy (eV)", ylabel="Intensity (CPS)",
                      label="Data")
# hr.peaks contains the fitted components
export_figure(fig2, "xps_c1s_fit.svg")

# Step 7: Composition bar chart
elements = list(survey.composition.keys())
percentages = list(survey.composition.values())
fig3, ax3 = plot_data(np.arange(len(elements)), percentages, kind="bar",
                      xlabel="Element", ylabel="Atomic %")
ax3.set_xticks(np.arange(len(elements)))
ax3.set_xticklabels(elements)
export_figure(fig3, "xps_composition.svg")
```

---

## 7. Solar Cell J-V Analysis

Load J-V curve, extract all figures of merit, plot with power curve overlay.

```python
from core.loader import load_data
from core.plotter import create_subplots
from core.exporter import export_figure
from core.utils import apply_style
from techniques.iv_curves import analyse_solar_cell
import numpy as np

# Step 1: Load J-V data
df = load_data("solar_cell.csv")
voltage = df["voltage"].values
j = df["current_density"].values  # mA/cm2

# Step 2: Extract solar cell parameters
result = analyse_solar_cell(voltage, j, illumination=100.0)
# Prints: Voc, Jsc, fill factor, PCE

# Step 3: Publication plot (J-V + power curve)
apply_style("nature")
import matplotlib.pyplot as plt
fig, ax1 = plt.subplots(figsize=(6, 4.5))

# J-V curve
ax1.plot(voltage, j, "b-", linewidth=1.5, label="J-V")
ax1.set_xlabel("Voltage (V)")
ax1.set_ylabel("Current Density (mA/cm2)")
ax1.axhline(0, color="grey", linewidth=0.5, linestyle=":")
ax1.axvline(0, color="grey", linewidth=0.5, linestyle=":")

# Power density on twin axis
ax2 = ax1.twinx()
power = voltage * np.abs(j)
ax2.plot(voltage, power, "r--", linewidth=1.2, label="Power")
ax2.set_ylabel("Power Density (mW/cm2)")

# Mark MPP
ax1.plot(result.v_mpp, result.j_mpp, "ko", markersize=6)
ax1.annotate(f"MPP\n{result.pmax:.1f} mW/cm2",
             xy=(result.v_mpp, result.j_mpp),
             xytext=(result.v_mpp + 0.1, result.j_mpp * 0.5),
             arrowprops=dict(arrowstyle="->", lw=0.8), fontsize=8)

# Text box with parameters
textstr = (f"Voc = {result.voc:.3f} V\n"
           f"Jsc = {result.jsc:.2f} mA/cm2\n"
           f"FF = {result.fill_factor:.3f}\n"
           f"PCE = {result.efficiency:.2f}%")
ax1.text(0.02, 0.02, textstr, transform=ax1.transAxes,
         fontsize=8, verticalalignment="bottom",
         bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))

# Step 4: Combined legend
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, frameon=False, loc="upper right")

fig.tight_layout()
export_figure(fig, "solar_cell_jv.svg", dpi=300)
```

---

## 8. BET Surface Area

Load nitrogen adsorption isotherm, classify isotherm type, perform BET analysis, calculate pore size distribution (BJH), and produce a two-panel figure.

```python
from core.loader import load_data
from core.plotter import create_subplots
from core.exporter import export_figure
from core.utils import apply_style
from techniques.bet import (
    analyse_bet, bjh_pore_distribution,
    classify_isotherm, total_pore_volume,
)

# Step 1: Load isotherm data
df = load_data("n2_isotherm.csv")
p_p0 = df["relative_pressure"].values
quantity = df["quantity_adsorbed"].values

# Step 2: Classify isotherm type
iso_type = classify_isotherm(p_p0, quantity)
print(f"Isotherm type: {iso_type}")

# Step 3: BET surface area
bet = analyse_bet(p_p0, quantity, adsorbate="N2")
print(f"Surface area: {bet.surface_area_m2g:.2f} m2/g")
print(f"BET constant C: {bet.bet_constant_c:.1f}")

# Step 4: Total pore volume
v_pore = total_pore_volume(p_p0, quantity)
print(f"Total pore volume: {v_pore:.4f} cm3/g")

# Step 5: BJH pore size distribution
pores = bjh_pore_distribution(p_p0, quantity, branch="desorption")
print(f"Mean pore diameter: {pores.mean_pore_diameter:.2f} nm")

# Step 6: Two-panel publication figure
apply_style("nature")
fig, axes = create_subplots(1, 2, figsize=(10, 4.5))

# Panel (a): Isotherm
axes[0].plot(p_p0, quantity, "o-", markersize=3, linewidth=1.2)
axes[0].set_xlabel("Relative Pressure (P/P0)")
axes[0].set_ylabel("Quantity Adsorbed (cm3/g STP)")
axes[0].text(0.05, 0.95, f"{iso_type}\nS = {bet.surface_area_m2g:.1f} m2/g",
             transform=axes[0].transAxes, fontsize=8, va="top")
axes[0].text(-0.12, 1.06, "(a)", transform=axes[0].transAxes,
             fontsize=12, fontweight="bold", va="top")

# Panel (b): Pore size distribution
axes[1].plot(pores.diameters, pores.dv_dd, "b-", linewidth=1.2)
axes[1].set_xlabel("Pore Diameter (nm)")
axes[1].set_ylabel("dV/dD (cm3/g/nm)")
axes[1].text(0.95, 0.95, f"d_mean = {pores.mean_pore_diameter:.1f} nm",
             transform=axes[1].transAxes, fontsize=8, va="top", ha="right")
axes[1].text(-0.12, 1.06, "(b)", transform=axes[1].transAxes,
             fontsize=12, fontweight="bold", va="top")

fig.tight_layout()
export_figure(fig, "bet_analysis.svg", dpi=300)
```

---

## 9. Multi-Technique Report

Combine XRD, SEM grain size, and EDS composition into a single markdown report with embedded figures.

```python
from core.loader import load_data
from core.plotter import plot_data
from core.exporter import export_figure
from core.utils import apply_style
from techniques.xrd import analyse_xrd
from techniques.sem_eds import grain_size_line_intercept, parse_eds_composition
from analysis.report import AnalysisReport

# Step 1: XRD analysis
df_xrd = load_data("sample_xrd.xy")
xrd_results = analyse_xrd(df_xrd["x"], df_xrd["y"], wavelength="Cu_Ka")

apply_style("nature")
fig_xrd, ax_xrd = plot_data(df_xrd["x"], df_xrd["y"], kind="line",
                             xlabel="2theta (deg)", ylabel="Intensity (a.u.)")
xrd_path = export_figure(fig_xrd, "xrd_for_report.png")

# Step 2: SEM grain size
df_gs = load_data("grain_sizes.csv")
gs = grain_size_line_intercept(df_gs["intercept_length"], scale_factor=1.0, unit="um")

fig_gs, ax_gs = plot_data(None, df_gs["intercept_length"].values, kind="histogram",
                          xlabel="Grain Size (um)", ylabel="Count", bins=15)
gs_path = export_figure(fig_gs, "grainsize_for_report.png")

# Step 3: EDS composition
eds = parse_eds_composition(
    elements=["Ba", "Ti", "O", "Zr"],
    weight_pct=[54.3, 18.2, 21.5, 6.0]
)

# Step 4: Build report
report = AnalysisReport("BaTiO3 Ceramic Characterisation")

# Add XRD section
report.add_xrd_results(xrd_results, section_title="XRD Phase Analysis")
report.add_figure(str(xrd_path), caption="XRD pattern of sintered BaTiO3")

# Add SEM section
report.add_section(
    "Microstructure",
    f"Grain size analysis by line intercept method on SEM images.\n\n"
    f"Mean grain size: {gs.mean_size:.2f} {gs.unit}\n"
    f"Standard deviation: {gs.std_size:.2f} {gs.unit}\n"
    f"D10/D50/D90: {gs.d10:.2f}/{gs.d50:.2f}/{gs.d90:.2f} {gs.unit}",
    figures=[str(gs_path)],
)

# Add EDS section
report.add_section(
    "Chemical Composition (EDS)",
    "Energy dispersive spectroscopy composition analysis.",
    tables=[{
        "data": {
            "Element": eds.elements,
            "wt%": [f"{w:.2f}" for w in eds.weight_pct],
            "at%": [f"{a:.2f}" for a in eds.atomic_pct],
        },
        "caption": "EDS elemental composition",
    }],
)

# Step 5: Generate report
md = report.generate("output/characterisation_report.md")
print(f"Report length: {len(md)} characters")
```

---

## 10. Batch Processing

Process 20 XRD files with the same pipeline, extract a parameter table, and create an overlay plot.

```python
from core.loader import load_data
from core.exporter import export_figure
from core.utils import apply_style
from batch.batch import load_batch, batch_analyse, batch_overlay, extract_parameters
from techniques.xrd import analyse_xrd
import numpy as np

# Step 1: Batch load all .xy files from a directory
datasets = load_batch(pattern="*.xy", directory="xrd_data/")
# Returns: dict of filename -> DataFrame

# Step 2: Batch analyse with XRD function
results_table = batch_analyse(
    datasets,
    analysis_func=analyse_xrd,
    x_col=0, y_col=1,
    wavelength="Cu_Ka"
)
# Returns: DataFrame with one row per file, columns for extracted parameters
print(results_table.to_string())

# Step 3: Custom parameter extraction
extractors = {
    "max_intensity": lambda x, y: float(np.max(y)),
    "peak_2theta": lambda x, y: float(x[np.argmax(y)]),
    "integrated_area": lambda x, y: float(np.trapz(y, x)),
}
params = extract_parameters(datasets, extractors)
print(params.to_string())

# Step 4: Save parameter table
params.to_csv("output/xrd_batch_parameters.csv", index=False)

# Step 5: Overlay plot
apply_style("nature")
fig, ax = batch_overlay(
    datasets,
    xlabel="2theta (deg)",
    ylabel="Intensity (a.u.)",
    title="XRD Batch Comparison",
)
export_figure(fig, "xrd_batch_overlay.svg", dpi=300)

# Step 6: Waterfall plot (offset stacked)
from core.plotter import plot_data
apply_style("nature")
y_datasets = [df.iloc[:, 1].values for df in datasets.values()]
x_common = list(datasets.values())[0].iloc[:, 0].values
fig2, ax2 = plot_data(
    x_common, y_datasets, kind="waterfall",
    labels=list(datasets.keys()),
    xlabel="2theta (deg)", ylabel="Intensity (offset, a.u.)",
)
export_figure(fig2, "xrd_waterfall.svg", dpi=300)
```

---

## 11. Statistical Comparison

Load repeat measurements from multiple samples, compute descriptive statistics, test for normality, run ANOVA, and produce a box plot with statistical annotations.

```python
from core.loader import load_data
from core.plotter import plot_data
from core.exporter import export_figure
from core.utils import apply_style
from analysis.statistics import descriptive, normality_test, anova, t_test
import numpy as np

# Step 1: Load data (e.g. hardness measurements from 3 sample groups)
df = load_data("hardness_data.xlsx")
group_a = df["Sample_A"].dropna().values
group_b = df["Sample_B"].dropna().values
group_c = df["Sample_C"].dropna().values

# Step 2: Descriptive statistics for each group
print("=== Sample A ===")
stats_a = descriptive(group_a)
print("\n=== Sample B ===")
stats_b = descriptive(group_b)
print("\n=== Sample C ===")
stats_c = descriptive(group_c)

# Step 3: Normality test
norm_a = normality_test(group_a, method="shapiro")
norm_b = normality_test(group_b, method="shapiro")
norm_c = normality_test(group_c, method="shapiro")

# Step 4: One-way ANOVA
anova_result = anova(group_a, group_b, group_c, alpha=0.05)
# Prints: F-statistic, p-value, eta-squared effect size

# Step 5: Post-hoc pairwise t-tests (if ANOVA is significant)
if anova_result.p_value < 0.05:
    print("\n--- Post-hoc pairwise comparisons ---")
    t_ab = t_test(group_a, group_b, alpha=0.05)
    t_ac = t_test(group_a, group_c, alpha=0.05)
    t_bc = t_test(group_b, group_c, alpha=0.05)

# Step 6: Box plot
apply_style("nature")
fig, ax = plot_data(
    None,
    [group_a, group_b, group_c],
    kind="box",
    labels=["Sample A", "Sample B", "Sample C"],
    ylabel="Vickers Hardness (HV)",
)

# Add individual data points (swarm/jitter)
for i, group in enumerate([group_a, group_b, group_c], 1):
    jitter = np.random.normal(0, 0.04, len(group))
    ax.scatter(np.full(len(group), i) + jitter, group,
               c="black", s=10, alpha=0.5, zorder=3)

# Annotate ANOVA result
sig_text = f"ANOVA: F={anova_result.statistic:.2f}, p={anova_result.p_value:.3e}"
ax.text(0.5, 1.02, sig_text, transform=ax.transAxes,
        fontsize=8, ha="center")

# Step 7: Export
export_figure(fig, "statistical_comparison.svg", dpi=300)
```

---

## 12. Signal Processing

Load raw sensor data (e.g. piezoelectric accelerometer), compute FFT, identify frequency components, apply filtering, and produce time-domain and frequency-domain plots.

```python
from core.loader import load_data
from core.plotter import plot_data, create_subplots
from core.exporter import export_figure
from core.utils import apply_style
from analysis.fft import compute_fft, power_spectrum, filter_signal
from analysis.smoothing import smooth
import numpy as np

# Step 1: Load raw sensor data
df = load_data("sensor_output.csv")
time = df["time_s"].values
signal = df["voltage_V"].values

# Step 2: Compute FFT
fft_result = compute_fft(signal, x=time, window="hann", remove_dc=True)
# Prints: dominant frequency, amplitude, sample rate

# Step 3: Power spectral density
freq_psd, psd = power_spectrum(signal, x=time, window="hann")

# Step 4: Apply lowpass filter to remove high-frequency noise
filtered_lp = filter_signal(signal, "lowpass", cutoff=500.0, x=time, order=4)

# Step 5: Apply notch filter to remove 50 Hz mains interference
filtered_notch = filter_signal(signal, "notch", cutoff=50.0, x=time,
                                quality_factor=30)

# Step 6: Combined filter chain
clean = filter_signal(signal, "bandpass", cutoff=(10, 1000), x=time, order=4)

# Step 7: Smoothing (Savitzky-Golay)
smoothed = smooth(clean, method="savgol", window=21, polyorder=3)

# Step 8: Four-panel publication figure
apply_style("nature")
fig, axes = create_subplots(2, 2, figsize=(10, 8))

# (a) Raw signal
axes[0, 0].plot(time * 1000, signal, linewidth=0.5)
axes[0, 0].set_xlabel("Time (ms)")
axes[0, 0].set_ylabel("Voltage (V)")
axes[0, 0].set_title("Raw Signal")
axes[0, 0].text(-0.12, 1.06, "(a)", transform=axes[0, 0].transAxes,
                fontsize=12, fontweight="bold", va="top")

# (b) FFT amplitude spectrum
axes[0, 1].plot(fft_result.freq, fft_result.amplitude, linewidth=0.8)
axes[0, 1].set_xlabel("Frequency (Hz)")
axes[0, 1].set_ylabel("Amplitude")
axes[0, 1].set_xlim(0, 2000)
axes[0, 1].set_title("Frequency Spectrum")
axes[0, 1].annotate(f"Dominant: {fft_result.dominant_freq:.1f} Hz",
                    xy=(fft_result.dominant_freq, fft_result.dominant_amplitude),
                    xytext=(fft_result.dominant_freq + 100,
                            fft_result.dominant_amplitude * 0.8),
                    arrowprops=dict(arrowstyle="->", lw=0.8), fontsize=8)
axes[0, 1].text(-0.12, 1.06, "(b)", transform=axes[0, 1].transAxes,
                fontsize=12, fontweight="bold", va="top")

# (c) Filtered signal
axes[1, 0].plot(time * 1000, signal, linewidth=0.3, alpha=0.3, label="Raw")
axes[1, 0].plot(time * 1000, clean, linewidth=0.8, label="Filtered")
axes[1, 0].set_xlabel("Time (ms)")
axes[1, 0].set_ylabel("Voltage (V)")
axes[1, 0].set_title("Bandpass Filtered")
axes[1, 0].legend(frameon=False, fontsize=7)
axes[1, 0].text(-0.12, 1.06, "(c)", transform=axes[1, 0].transAxes,
                fontsize=12, fontweight="bold", va="top")

# (d) Power spectral density (log scale)
axes[1, 1].semilogy(freq_psd, psd, linewidth=0.8)
axes[1, 1].set_xlabel("Frequency (Hz)")
axes[1, 1].set_ylabel("PSD (normalised)")
axes[1, 1].set_xlim(0, 2000)
axes[1, 1].set_title("Power Spectral Density")
axes[1, 1].text(-0.12, 1.06, "(d)", transform=axes[1, 1].transAxes,
                fontsize=12, fontweight="bold", va="top")

fig.tight_layout()
export_figure(fig, "signal_processing.svg", dpi=300)
```
