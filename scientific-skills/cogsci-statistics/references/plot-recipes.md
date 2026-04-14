# Visualization Recipes for Cognitive Science

Concrete code recipes for common cognitive science figures. Each recipe specifies: when to use, tool (Python/R), key parameters, APA formatting tips, and common mistakes.

---

## Recipe 1: RT Distribution -- Raincloud Plot

### When to Use
- Visualizing reaction time distributions across conditions
- Any continuous dependent variable where distribution shape matters
- Replacing bar charts in manuscripts (Allen et al., 2019; Weissgerber et al., 2015)

### R Code (ggrain)

```r
library(ggplot2)
library(ggrain)

p <- ggplot(d, aes(x = condition, y = RT, fill = condition, color = condition)) +
 geom_rain(
 rain.side = "l", # Density on left
 point.args = list(size = 1, alpha = 0.3),
 boxplot.args = list(width = 0.1, outlier.shape = NA),
 violin.args = list(alpha = 0.5)
 ) +
 scale_fill_manual(values = c("#E69F00", "#56B4E9", "#009E73")) + # Okabe-Ito
 scale_color_manual(values = c("#E69F00", "#56B4E9", "#009E73")) +
 labs(x = "Condition", y = "Reaction time (ms)") +
 theme_classic(base_size = 12) +
 theme(
 legend.position = "none",
 axis.text = element_text(size = 10),
 axis.title = element_text(size = 12)
 )

ggsave("rt_raincloud.tiff", p, width = 3.3, height = 3.3, dpi = 300, units = "in")
```

### Python Code (PtitPrince)

```python
import ptitprince as pt
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.family'] = 'Arial'
matplotlib.rcParams['font.size'] = 10

fig, ax = plt.subplots(figsize=(3.3, 3.3), dpi=300)

pt.RainCloud(
 x="condition", y="RT", data=d, ax=ax,
 palette=["#E69F00", "#56B4E9", "#009E73"], # Okabe-Ito (Okabe & Ito, 2002)
 bw=0.2, # Bandwidth for density estimation
 width_viol=0.6,
 point_size=2,
 alpha=0.5,
 orient="v",
 move=0.2
)

ax.set_xlabel("Condition")
ax.set_ylabel("Reaction time (ms)")
ax.spines[['top', 'right']].set_visible(False)

fig.tight_layout()
fig.savefig("rt_raincloud.tiff", dpi=300, format='tiff')
```

### Key Parameters
- **Bandwidth (bw)**: Controls smoothness of density. Too narrow = noisy; too wide = oversmoothed. Default (Silverman's rule) is usually acceptable.
- **Point alpha**: **0.2-0.4** for large N (> 50 per condition); **0.5-0.8** for small N (< 30)
- **Colors**: Use Okabe-Ito palette for colorblind safety (Okabe & Ito, 2002)

### APA Formatting Tips
- Width: **3.3 in** (single column) or **6.9 in** (double column)
- Font: Arial or Helvetica, **10-12 pt** in final printed size
- Caption: "Raincloud plot showing RT distributions by condition. Points represent individual trials/participants. Box plots show median and IQR. Density estimates show distribution shape."

### Common Mistakes
- Not jittering points sufficiently (creates a solid line instead of visible scatter)
- Using bar charts instead because "that's what my advisor always uses"
- Not specifying what individual points represent (trials? participant means?)

---

## Recipe 2: ERP Waveform Plot

### When to Use
- Comparing ERP waveforms across conditions at a specific electrode or ROI
- Showing temporal dynamics of brain responses

### Python Code (MNE-Python)

```python
import mne
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.family'] = 'Arial'
matplotlib.rcParams['font.size'] = 10

fig, ax = plt.subplots(figsize=(4.5, 3.0), dpi=300)

# Plot evoked responses for each condition
colors = {"congruent": "#0072B2", "incongruent": "#D55E00"} # Okabe-Ito subset
linestyles = {"congruent": "-", "incongruent": "--"}

for cond, evoked in evoked_dict.items():
 times = evoked.times * 1000 # Convert to ms
 data = evoked.data[channel_idx, :] * 1e6 # Convert to uV

 ax.plot(times, data,
 color=colors[cond], linestyle=linestyles[cond],
 linewidth=1.5, label=cond)

# Convention: negative up (traditional ERP; Luck, 2014)
ax.invert_yaxis()

# Mark stimulus onset
ax.axvline(x=0, color='black', linestyle=':', linewidth=0.5)
ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)

# Shade component window (e.g., N400: 300-500 ms; Kutas & Federmeier, 2011)
ax.axvspan(300, 500, alpha=0.1, color='gray', label='N400 window')

# Shade baseline
ax.axvspan(-200, 0, alpha=0.05, color='gray')

ax.set_xlabel("Time (ms)")
ax.set_ylabel("Amplitude (uV)")
ax.set_xlim([-200, 800])
ax.legend(loc='lower right', fontsize=8, frameon=False)
ax.spines[['top', 'right']].set_visible(False)

fig.tight_layout()
fig.savefig("erp_waveform.tiff", dpi=300, format='tiff')
```

### R Code (ggplot2)

```r
library(ggplot2)

p <- ggplot(erp_data, aes(x = time_ms, y = amplitude_uv, color = condition,
 linetype = condition)) +
 geom_line(linewidth = 0.8) +
 geom_vline(xintercept = 0, linetype = "dotted", linewidth = 0.5) +
 geom_hline(yintercept = 0, linewidth = 0.5) +
 annotate("rect", xmin = 300, xmax = 500, ymin = -Inf, ymax = Inf,
 alpha = 0.1, fill = "gray") +
 scale_y_reverse() + # Negative up (Luck, 2014)
 scale_color_manual(values = c("#0072B2", "#D55E00")) + # Okabe-Ito
 labs(x = "Time (ms)", y = expression(paste("Amplitude (", mu, "V)"))) +
 theme_classic(base_size = 10) +
 theme(legend.position = c(0.8, 0.2), legend.background = element_blank())

ggsave("erp_waveform.tiff", p, width = 4.5, height = 3.0, dpi = 300, units = "in")
```

### Key Parameters
- **Line width**: **1.0-1.5 pt** for waveforms (Luck, 2014)
- **Time range**: Typically **-200 to 800 ms** (adjust for paradigm)
- **Y-axis direction**: Invert for negative-up convention
- **Component shading**: Use named time windows from literature (e.g., N400: **300-500 ms**; Kutas & Federmeier, 2011)

### APA Formatting Tips
- Caption: "Grand-averaged ERP waveforms at electrode [Cz/Pz/etc.] for [condition names]. Negative is plotted upward. Shaded region indicates the [component] time window ([start]-[end] ms). N = [number]."
- Always state polarity convention, electrode, and number of participants

### Common Mistakes
- Not stating polarity convention (negative up vs. down)
- Using different y-axis scales across panels without noting it
- Not showing stimulus onset marker
- Plotting only group averages without any indication of variability

---

## Recipe 3: ERP Topographic Map

### When to Use
- Showing scalp distribution of ERP effect at a specific time window
- Validating that the observed effect has the expected topography for a given component

### Python Code (MNE-Python)

```python
import mne
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 3, figsize=(6.9, 2.5), dpi=300)

# Time windows for topographic maps
time_windows = {
 "N1 (80-120 ms)": (0.080, 0.120),
 "N400 (300-500 ms)": (0.300, 0.500),
 "P600 (500-800 ms)": (0.500, 0.800)
}

for ax, (label, (tmin, tmax)) in zip(axes, time_windows.items()):
 # Compute mean amplitude in time window
 evoked_diff = mne.combine_evoked(
 [evoked_cond_a, evoked_cond_b], weights=[1, -1]
 )

 evoked_diff.plot_topomap(
 times=[(tmin + tmax) / 2],
 average=(tmax - tmin),
 axes=ax,
 colorbar=False,
 cmap='RdBu_r', # Diverging colormap (Crameri et al., 2020)
 vlim=(-3, 3), # Symmetric limits in uV
 show=False
 )
 ax.set_title(label, fontsize=9)

# Add shared colorbar
sm = plt.cm.ScalarMappable(cmap='RdBu_r', norm=plt.Normalize(-3, 3))
sm.set_array([])
cbar = fig.colorbar(sm, ax=axes.tolist(), shrink=0.8)
cbar.set_label('Amplitude (uV)', fontsize=9)

fig.tight_layout()
fig.savefig("erp_topomap.tiff", dpi=300, format='tiff')
```

### Key Parameters
- **Colormap**: `RdBu_r` (diverging, blue-white-red, colorblind-safe; Crameri et al., 2020)
- **Limits (vlim)**: Symmetric around zero; set to capture the range of the data
- **Time windows**: Use established component windows from literature (see `../cogsci-statistics/references/common-analyses.md`)
- **Sensor positions**: Show electrode markers on the map

### APA Formatting Tips
- Caption: "Topographic distribution of the [effect name] (condition A minus condition B) at [time windows]. Scale in microvolts. Electrode positions marked as dots."
- Use consistent color scales across all topographic maps in the same figure

### Common Mistakes
- Using non-diverging colormap for difference data (obscures the zero-crossing)
- Different color scales across panels within the same figure
- Not specifying whether the map shows absolute values or condition differences
- Omitting the color bar

---

## Recipe 4: fMRI Activation Map

### When to Use
- Showing brain regions activated by a contrast of interest
- Whole-brain statistical results display

### Python Code (nilearn)

```python
from nilearn import plotting
import matplotlib.pyplot as plt

# Option 1: Glass brain (whole-brain overview)
fig = plt.figure(figsize=(6.9, 2.5), dpi=300)

display = plotting.plot_glass_brain(
 stat_map_img,
 threshold=3.1, # z = 3.1 ~ p < 0.001 (Eklund et al., 2016)
 colorbar=True,
 cmap='inferno', # Perceptually uniform (Crameri et al., 2020)
 plot_abs=False, # Show both positive and negative
 display_mode='lyrz', # Left, top, right, lateral views
 figure=fig,
 title='Contrast: Task > Rest'
)

fig.savefig("fmri_glass_brain.tiff", dpi=300, format='tiff')

# Option 2: Slice montage with anatomical underlay
fig, axes = plt.subplots(1, 1, figsize=(6.9, 2.0), dpi=300)

display = plotting.plot_stat_map(
 stat_map_img,
 bg_img=mni_template, # MNI152 T1 1mm template
 threshold=3.1, # z = 3.1 (Eklund et al., 2016)
 display_mode='z', # Axial slices
 cut_coords=[-20, -5, 10, 25, 40, 55], # Show multiple levels
 colorbar=True,
 cmap='cold_hot', # Diverging for activation/deactivation
 annotate=True, # Show coordinates
 figure=fig
)

fig.savefig("fmri_slices.tiff", dpi=300, format='tiff')

# Option 3: Surface projection
fig, axes = plt.subplots(2, 2, figsize=(6.9, 5.0), dpi=300,
 subplot_kw={'projection': '3d'})

for ax, hemi, view in zip(axes.flat,
 ['left', 'right', 'left', 'right'],
 ['lateral', 'lateral', 'medial', 'medial']):
 plotting.plot_surf_stat_map(
 surf_mesh=f'fsaverage5_{hemi}',
 stat_map=stat_map_surface,
 hemi=hemi,
 view=view,
 threshold=3.1,
 colorbar=True,
 cmap='inferno',
 axes=ax
 )

fig.savefig("fmri_surface.tiff", dpi=300, format='tiff')
```

### Key Parameters
- **Threshold**: z = **3.1** corresponds to approximately p < 0.001 uncorrected (Eklund et al., 2016 -- minimum for cluster-forming threshold)
- **Colormap**: `inferno` or `hot` for sequential; `cold_hot` or `RdBu_r` for diverging (Crameri et al., 2020)
- **Background**: MNI152 T1 **1 mm** template for anatomical detail
- **Display mode**: `'z'` for axial, `'x'` for sagittal, `'y'` for coronal, `'ortho'` for all three

### APA Formatting Tips
- Caption: "Statistical map showing regions with significantly greater activation for [contrast]. Voxel-level threshold: z > 3.1 (p < 0.001 uncorrected); cluster-level correction: p < 0.05 FWE. Coordinates in MNI space. Color bar indicates z-score."
- Always report: threshold, correction method, coordinate space, template

### Common Mistakes
- Using jet/rainbow colormap (Borland & Taylor, 2007)
- Not reporting the threshold in the figure or caption
- Showing only a single slice that happens to contain the peak voxel
- Using different thresholds in the figure vs. the statistics reported in the text

---

## Recipe 5: Behavioral Accuracy -- Dot Plot with Within-Subject CI

### When to Use
- Displaying condition means for accuracy or any proportion in a within-subjects design
- When standard (between-subject) CIs would be misleading for within-subject comparisons

### R Code

```r
library(ggplot2)
library(Rmisc) # for summarySEwithin

# Within-subject summary statistics (Morey, 2008)
d_summary <- summarySEwithin(d, measurevar = "accuracy",
 withinvars = "condition",
 idvar = "subject")

p <- ggplot() +
 # Individual subject data (connected for within-subjects)
 geom_line(data = d, aes(x = condition, y = accuracy, group = subject),
 alpha = 0.2, color = "gray60") +
 geom_point(data = d, aes(x = condition, y = accuracy),
 alpha = 0.3, size = 1, color = "gray40",
 position = position_jitter(width = 0.05)) +
 # Group means with within-subject CI (Morey, 2008)
 geom_pointrange(data = d_summary,
 aes(x = condition, y = accuracy,
 ymin = accuracy - ci, ymax = accuracy + ci),
 size = 0.8, linewidth = 1.0,
 color = "black") +
 labs(x = "Condition", y = "Accuracy (proportion correct)") +
 scale_y_continuous(limits = c(0, 1)) +
 theme_classic(base_size = 11) +
 theme(axis.text = element_text(size = 10))

ggsave("accuracy_dotplot.tiff", p, width = 3.3, height = 3.3, dpi = 300, units = "in")
```

### Python Code

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
matplotlib.rcParams['font.family'] = 'Arial'

# Within-subject CI (Cousineau, 2005; Morey, 2008 correction)
def within_subject_ci(data, dv, subject, condition, ci=0.95):
 """Compute within-subject confidence intervals with Morey (2008) correction."""
 # Remove between-subject variance
 subj_means = data.groupby(subject)[dv].transform('mean')
 grand_mean = data[dv].mean()
 data_norm = data.copy()
 data_norm[dv] = data[dv] - subj_means + grand_mean

 # Compute CI on normalized data
 k = data[condition].nunique()
 correction = np.sqrt(k / (k - 1)) # Morey (2008) correction factor

 summary = data_norm.groupby(condition)[dv].agg(['mean', 'sem']).reset_index()
 from scipy import stats
 t_crit = stats.t.ppf((1 + ci) / 2, df=data[subject].nunique() - 1)
 summary['ci'] = summary['sem'] * t_crit * correction
 summary['mean_orig'] = data.groupby(condition)[dv].mean().values
 return summary

summary = within_subject_ci(d, 'accuracy', 'subject', 'condition')

fig, ax = plt.subplots(figsize=(3.3, 3.3), dpi=300)

# Individual subjects
for subj in d['subject'].unique():
 subj_data = d[d['subject'] == subj]
 ax.plot(subj_data['condition'], subj_data['accuracy'],
 color='gray', alpha=0.15, linewidth=0.5)

# Group means with within-subject CI
ax.errorbar(summary['condition'], summary['mean_orig'],
 yerr=summary['ci'], fmt='ko', markersize=6,
 linewidth=1.5, capsize=4)

ax.set_xlabel("Condition")
ax.set_ylabel("Accuracy (proportion correct)")
ax.set_ylim([0, 1])
ax.spines[['top', 'right']].set_visible(False)

fig.tight_layout()
fig.savefig("accuracy_dotplot.tiff", dpi=300, format='tiff')
```

### Key Parameters
- **Morey (2008) correction**: Multiply SE by `sqrt(k / (k-1))` where k = number of conditions
- **Individual data alpha**: **0.15-0.3** (thin, semi-transparent lines connecting within-subject data)
- **Y-axis range**: [0, 1] for proportions

### APA Formatting Tips
- Caption: "Mean accuracy by condition. Error bars indicate within-subject 95% CI (Morey, 2008). Gray lines connect individual participants' data points. N = [number]."
- Always specify that CIs are within-subject corrected

### Common Mistakes
- Using between-subject CIs for within-subject comparisons (overestimates variability; Loftus & Masson, 1994)
- Not connecting individual data points in within-subject designs (connection shows paired structure)
- Starting y-axis at 0.5 when accuracy is near ceiling (may obscure meaningful variation -- but state the break)

---

## Recipe 6: Group Comparison -- Cumming Estimation Plot (DABEST)

### When to Use
- Comparing two or more groups or conditions
- Emphasizing effect size and uncertainty over p-values
- "Estimation statistics" approach (Cumming, 2014; Ho et al., 2019)

### Python Code (DABEST)

```python
import dabest

# Gardner-Altman estimation plot (Ho et al., 2019)
analysis = dabest.load(d, x="group", y="score",
 idx=("control", "treatment"))

fig = analysis.mean_diff.plot(
 color_col="group",
 custom_palette=["#56B4E9", "#E69F00"], # Okabe-Ito
 raw_marker_size=4,
 es_marker_size=8,
 swarm_label="Score",
 contrast_label="Mean difference",
 fig_size=(4.5, 4.0),
 dpi=300
)

fig.savefig("estimation_plot.tiff", dpi=300, format='tiff')
```

### R Code (dabestr)

```r
library(dabestr)

result <- dabest(d, x = group, y = score,
 idx = c("control", "treatment"),
 paired = FALSE) %>%
 mean_diff()

plot(result,
 color.column = group,
 palette = c("control" = "#56B4E9", "treatment" = "#E69F00"),
 rawplot.markersize = 2,
 effsize.markersize = 4) +
 theme_classic(base_size = 10)

ggsave("estimation_plot.tiff", width = 4.5, height = 4.0, dpi = 300, units = "in")
```

### Key Parameters
- **Bootstrap resamples**: **5000** (default in DABEST; Ho et al., 2019)
- **Effect size**: Mean difference with 95% CI (default) or Cohen's d
- **Individual data**: Shown as a swarm plot (left panel)

### APA Formatting Tips
- Caption: "Gardner-Altman estimation plot showing individual data points (left) and the mean difference with bootstrap 95% CI (right). N = [per group]. [Number] bootstrap resamples."
- The estimation plot naturally communicates effect size and uncertainty

### Common Mistakes
- Not reporting the numerical effect size and CI in the text (the plot supplements but does not replace statistical reporting)
- Using this for within-subject designs without the paired option

---

## Recipe 7: Time-Frequency Representation (TFR)

### When to Use
- Visualizing oscillatory power changes over time and frequency
- Showing event-related spectral perturbation (ERSP)

### Python Code (MNE-Python)

```python
import mne
import matplotlib.pyplot as plt

# Compute TFR using Morlet wavelets
freqs = np.logspace(np.log10(4), np.log10(40), num=30) # 4-40 Hz log-spaced
n_cycles = freqs / 2 # Frequency-dependent cycles (standard: freq / 2; Cohen, 2014)

power = mne.time_frequency.tfr_morlet(
 epochs, freqs=freqs, n_cycles=n_cycles,
 return_itc=False, average=True
)

# Apply baseline correction (dB; Cohen, 2014)
# Baseline: -500 to -200 ms (avoid edge artifacts)
power.apply_baseline(baseline=(-0.5, -0.2), mode='logratio')

fig, ax = plt.subplots(figsize=(4.5, 3.0), dpi=300)

power.plot(
 picks=[channel_idx],
 axes=ax,
 baseline=None, # Already applied
 cmap='RdBu_r', # Diverging for dB change (Crameri et al., 2020)
 vmin=-1.5, vmax=1.5, # Symmetric for diverging map
 show=False
)

ax.set_xlabel("Time (ms)")
ax.set_ylabel("Frequency (Hz)")
ax.set_title("") # Remove auto-title; use figure caption instead

fig.tight_layout()
fig.savefig("tfr.tiff", dpi=300, format='tiff')
```

### Key Parameters
- **Frequencies**: **4-40 Hz** (or task-specific range) on a log scale (Cohen, 2014)
- **Wavelet cycles**: `n_cycles = freq / 2` provides balanced time-frequency resolution (Cohen, 2014)
- **Baseline**: Apply before plotting; use **-500 to -200 ms** to avoid onset contamination (Cohen, 2014)
- **Baseline mode**: `'logratio'` (decibel, dB) is standard for TFR (Cohen, 2014)
- **Colormap**: `RdBu_r` (diverging, centered on zero; for baseline-corrected power)

### APA Formatting Tips
- Caption: "Time-frequency representation at electrode [name] showing event-related spectral power (dB relative to baseline [start]-[end] ms). Morlet wavelets with [n_cycles specification]. Warm colors indicate power increase; cool colors indicate power decrease."
- Always report: baseline period, baseline correction method, wavelet parameters, frequency range

### Common Mistakes
- Not applying baseline correction (raw power values are not interpretable across frequencies)
- Using a sequential colormap for baseline-corrected data (which has both positive and negative values)
- Using a linear frequency axis when a log axis would better represent the data (low frequencies are overrepresented)
- Using fixed n_cycles across all frequencies (poor time resolution at low frequencies or poor frequency resolution at high frequencies)

---

## Recipe 8: Correlation Matrix -- Hierarchically Clustered Heatmap

### When to Use
- Visualizing relationships among multiple variables (behavioral measures, neural measures, questionnaire subscales)
- Identifying clusters of related variables

### Python Code (seaborn)

```python
import seaborn as sns
import matplotlib.pyplot as plt
from scipy.cluster.hierarchy import linkage
from scipy.spatial.distance import squareform

# Compute correlation matrix
corr_matrix = d[variable_list].corr()

# Hierarchical clustering for ordering
linkage_matrix = linkage(squareform(1 - corr_matrix.abs()), method='ward')

fig, ax = plt.subplots(figsize=(5.0, 4.5), dpi=300)

g = sns.clustermap(
 corr_matrix,
 row_linkage=linkage_matrix,
 col_linkage=linkage_matrix,
 cmap='RdBu_r', # Diverging (Crameri et al., 2020)
 vmin=-1, vmax=1, # Full correlation range
 center=0,
 annot=True, # Show correlation values
 fmt='.2f', # Two decimal places
 linewidths=0.5,
 figsize=(5.0, 4.5),
 dendrogram_ratio=(0.15, 0.15),
 cbar_kws={'label': "Pearson's r", 'shrink': 0.8}
)

g.ax_heatmap.set_xticklabels(g.ax_heatmap.get_xticklabels(),
 fontsize=8, rotation=45, ha='right')
g.ax_heatmap.set_yticklabels(g.ax_heatmap.get_yticklabels(),
 fontsize=8, rotation=0)

g.savefig("correlation_heatmap.tiff", dpi=300, format='tiff')
```

### R Code (corrplot)

```r
library(corrplot)

# Compute correlation matrix
cor_mat <- cor(d[, variables], use = "pairwise.complete.obs")

# Hierarchically clustered heatmap
tiff("correlation_heatmap.tiff", width = 5, height = 4.5, units = "in", res = 300)

corrplot(cor_mat,
 method = "color",
 type = "lower",
 order = "hclust", # Hierarchical clustering order
 hclust.method = "ward.D2",
 col = colorRampPalette(c("#2166AC", "white", "#B2182B"))(200), # RdBu
 tl.col = "black",
 tl.cex = 0.7,
 number.cex = 0.6,
 addCoef.col = "black", # Show correlation values
 cl.cex = 0.7)

dev.off()
```

### Key Parameters
- **Colormap**: `RdBu_r` (diverging, centered on zero; Crameri et al., 2020)
- **Range**: [-1, 1] for correlation matrices
- **Clustering method**: Ward's method (`ward.D2`) for balanced clusters
- **Annotation format**: Two decimal places for correlation values

### APA Formatting Tips
- Caption: "Hierarchically clustered correlation matrix of [variable description]. Color indicates Pearson's r. Variables are ordered by Ward's hierarchical clustering. N = [number]."
- For many variables (> 15), consider showing only significant correlations or using a threshold

### Common Mistakes
- Not centering the colormap on zero (asymmetric colors misrepresent the sign of correlations)
- Using an unclustered default ordering (misses the modular structure)
- Annotating with too many decimal places (clutters the figure)
- Not specifying the correlation type (Pearson vs. Spearman) in the caption

---

## General Tips Across All Recipes

### Save Settings for Reproducibility

```python
# Python: Save figure parameters
FIGURE_PARAMS = {
 'single_col_width': 3.3, # inches (typical journal single column)
 'double_col_width': 6.9, # inches (typical journal double column)
 'dpi': 300, # Minimum for print (APA 7th, 2020)
 'font_family': 'Arial',
 'font_size': 10, # Base font size for final figure
 'line_width': 1.0, # Default line width
 'palette': ["#E69F00", "#56B4E9", "#009E73",
 "#F0E442", "#0072B2", "#D55E00",
 "#CC79A7", "#000000"] # Okabe-Ito (Okabe & Ito, 2002)
}
```

```r
# R: Theme for consistent formatting
theme_publication <- function(base_size = 10) {
 theme_classic(base_size = base_size) +
 theme(
 text = element_text(family = "Arial"),
 axis.text = element_text(size = base_size - 1),
 axis.title = element_text(size = base_size),
 legend.text = element_text(size = base_size - 1),
 strip.text = element_text(size = base_size),
 plot.title = element_text(size = base_size + 1, face = "bold")
 )
}
```

### Colorblind Testing Checklist

Before submitting any figure:
1. View in grayscale (does the information survive?)
2. Run through a CVD simulator (deuteranopia and protanopia at minimum)
3. Verify that color is not the ONLY encoding (use linetype, shape, labels as redundant cues)

---

## References

- Allen, M., et al. (2019). Raincloud plots. *Wellcome Open Research*, 4, 63.
- Borland, D., & Taylor, R. M. (2007). Rainbow color map (still) considered harmful. *IEEE CGA*, 27(2), 14-17.
- Cohen, M. X. (2014). *Analyzing Neural Time Series Data*. MIT Press.
- Cousineau, D. (2005). Confidence intervals in within-subject designs. *TQMP*, 1(1), 42-45.
- Crameri, F., et al. (2020). The misuse of colour in science communication. *Nature Communications*, 11, 5444.
- Cumming, G. (2014). The new statistics. *Psychological Science*, 25(1), 7-29.
- Eklund, A., et al. (2016). Cluster failure. *PNAS*, 113(28), 7900-7905.
- Ho, J., Tumkaya, T., Aryal, S., Choi, H., & Claridge-Chang, A. (2019). Moving beyond P values: Data analysis with estimation graphics. *Nature Methods*, 16, 565-566.
- Kutas, M., & Federmeier, K. D. (2011). Thirty years and counting. *Annual Review of Psychology*, 62, 621-647.
- Loftus, G. R., & Masson, M. E. J. (1994). Using confidence intervals in within-subject designs. *Psychonomic Bulletin & Review*, 1(4), 476-490.
- Luck, S. J. (2014). *An Introduction to the Event-Related Potential Technique* (2nd ed.). MIT Press.
- Morey, R. D. (2008). Confidence intervals from normalized data. *TQMP*, 4(2), 61-64.
- Okabe, M., & Ito, K. (2002). Color universal design (CUD). J*Fly*.
- Weissgerber, T. L., et al. (2015). Beyond bar and line graphs. *PLoS Biology*, 13(4), e1002128.
