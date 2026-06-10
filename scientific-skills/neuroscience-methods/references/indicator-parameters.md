# Indicator Parameters: Calcium Indicator Properties and Analysis Implications

## Genetically Encoded Calcium Indicator (GECI) Kinetics

### GCaMP Family Overview

The GCaMP family of genetically encoded calcium indicators is the most widely used class of GECIs in neuroscience. Each generation has improved sensitivity and/or kinetics, with direct implications for analysis pipeline configuration.

**Key principle**: Faster indicators allow resolving higher firing rates but may have lower sensitivity (smaller dF/F per spike). Slower indicators integrate more spikes, producing larger signals but poorer temporal resolution. This tradeoff was largely resolved with the jGCaMP8 family (Zhang et al., 2023).

### Kinetics Table: In Vivo Measurements

All values are for single action potential responses unless otherwise noted. In vivo values are reported where available, as in vitro kinetics are typically faster.

#### GCaMP6 Family (Chen et al., 2013)

| Indicator | Half-Rise Time (ms) | Half-Decay Time (ms) | dF/F per 1 AP (%) | Kd (nM) | Source |
|-----------|---------------------|-----------------------|--------------------|---------|--------|
| GCaMP6s | ~180 | ~550-600 | ~24 | ~144 | Chen et al., 2013 |
| GCaMP6m | ~80 | ~270 | ~15 | ~167 | Chen et al., 2013 |
| GCaMP6f | ~45 | ~140-200 | ~12 | ~375 | Chen et al., 2013 |

**Deconvolution tau recommendations for GCaMP6**:
- GCaMP6s: **tau = 1.0-1.5 s** (Suite2P default uses 1.0 s)
- GCaMP6m: **tau = 0.5-0.7 s**
- GCaMP6f: **tau = 0.3-0.4 s**

Note: The half-decay time and the exponential decay constant (tau) used for deconvolution are related but not identical. The half-decay time is t_1/2 = tau * ln(2). Suite2P uses tau as the exponential time constant. The values above account for this conversion and empirical tuning.

#### jGCaMP7 Family (Dana et al., 2019)

| Indicator | Half-Rise Time (ms) | Half-Decay Time (ms) | dF/F per 1 AP (%) | Kd (nM) | Source |
|-----------|---------------------|-----------------------|--------------------|---------|--------|
| jGCaMP7s | ~200 | ~600 | ~42 | ~68 | Dana et al., 2019 |
| jGCaMP7f | ~25-30 | ~270-280 | ~18 | ~174 | Dana et al., 2019 |
| jGCaMP7b | ~20 | ~120 | ~7 | ~82 | Dana et al., 2019 |
| jGCaMP7c | ~25 | ~250 | ~12 | ~298 | Dana et al., 2019 |

**Deconvolution tau recommendations for jGCaMP7**:
- jGCaMP7s: **tau = 1.0-1.5 s**
- jGCaMP7f: **tau = 0.3-0.4 s**
- jGCaMP7b: **tau = 0.15-0.2 s**
- jGCaMP7c: **tau = 0.3-0.4 s**

#### jGCaMP8 Family (Zhang et al., 2023)

Measured in vivo in Drosophila L2 neurons:

| Indicator | Half-Rise Time (ms) | Half-Decay Time (ms) | dF/F per 1 AP (%) | Source |
|-----------|---------------------|-----------------------|--------------------|--------|
| jGCaMP8s | ~80 | ~198 | ~38 | Zhang et al., 2023 |
| jGCaMP8m | ~58 | ~137 | ~34 | Zhang et al., 2023 |
| jGCaMP8f | ~76 | ~192 | ~24 | Zhang et al., 2023 |

**Deconvolution tau recommendations for jGCaMP8**:
- jGCaMP8s: **tau = 0.2-0.3 s**
- jGCaMP8m: **tau = 0.14-0.2 s**
- jGCaMP8f: **tau = 0.2-0.3 s**

Note: jGCaMP8 kinetics measured in Drosophila may differ from mouse cortical neurons. Verify with pilot data when possible. In mouse V1, preliminary data suggest similar trends with slightly longer time constants due to calcium buffering differences.

### Cross-Generation Comparison: Speed vs. Sensitivity

| Indicator | Relative Speed | Relative Sensitivity (1 AP) | Best Use Case |
|-----------|---------------|------------------------------|---------------|
| GCaMP6s | Slowest | High | Low-firing populations, dendrites |
| GCaMP6f | Moderate | Moderate | General purpose 2P |
| jGCaMP7f | Moderate-Fast | High | General purpose, improved over 6f |
| jGCaMP7s | Slow | Highest (GCaMP7 family) | Maximum sensitivity needed |
| jGCaMP8s | Fast | Very high | High sensitivity + speed |
| jGCaMP8m | Fastest | Very high | Fast-spiking neurons, burst detection |
| jGCaMP8f | Fast | High | General purpose, best kinetics/sensitivity balance |

## Choosing an Indicator Based on Expected Firing Rate

The temporal resolution of calcium imaging is fundamentally limited by indicator kinetics. The maximum resolvable firing rate depends on the indicator's decay time.

### Firing Rate Resolution Limits

| Indicator | Approximate Max Resolvable Rate | Rationale | Source |
|-----------|---------------------------------|-----------|--------|
| GCaMP6s | **~2-3 Hz** | Consecutive transients merge above ~2 Hz | Chen et al., 2013 |
| GCaMP6f | **~5-10 Hz** | Resolution interval ~50-75 ms | Chen et al., 2013 |
| jGCaMP7f | **~5-10 Hz** | Similar decay to GCaMP6f but higher sensitivity | Dana et al., 2019 |
| jGCaMP8m | **~15-30 Hz** | Fastest decay in the family | Zhang et al., 2023 |
| jGCaMP8f | **~10-20 Hz** | Good balance for most applications | Zhang et al., 2023 |

**Domain judgment for indicator choice**:
- **Cortical pyramidal neurons** (typical firing rate 0.1-10 Hz): GCaMP6f, jGCaMP7f, or jGCaMP8f are all suitable
- **Fast-spiking interneurons** (10-100 Hz): jGCaMP8m preferred; GCaMP6s will severely underestimate activity due to saturation
- **Cerebellar Purkinje cells** (simple spikes ~50-100 Hz): Standard GECIs cannot resolve individual simple spikes; complex spikes (~1 Hz) are resolvable with GCaMP6f or faster
- **Hippocampal place cells** (burst firing, 5-20 Hz within field): jGCaMP7f or jGCaMP8f recommended
- **Dopamine neurons** (tonic ~5 Hz, burst ~20 Hz): jGCaMP8f for distinguishing burst from tonic
- **Dendrites and spines** (local calcium signals): GCaMP6s or jGCaMP7s preferred for maximum sensitivity at low amplitudes

### Saturation Effects

All GECIs have a finite dynamic range (F_max / F_min) that causes fluorescence to saturate at high calcium concentrations.

| Indicator | Dynamic Range (F_max/F_min) | Approximate Saturation Onset | Source |
|-----------|----------------------------|------------------------------|--------|
| GCaMP6s | ~63 | ~10-20 spikes in burst | Chen et al., 2013 |
| GCaMP6f | ~52 | ~20-30 spikes in burst | Chen et al., 2013 |
| jGCaMP7f | ~40 | ~15-25 spikes in burst | Dana et al., 2019 |
| jGCaMP8f | ~83 | ~30+ spikes in burst | Zhang et al., 2023 |

**Implication for analysis**: When fluorescence approaches saturation, the relationship between firing rate and dF/F becomes sublinear. Deconvolution algorithms that assume a linear model will underestimate spike counts during high-frequency bursts. This is a fundamental biophysical limit, not an algorithmic failure.

## Red Calcium Indicators

For experiments requiring a second color channel (e.g., dual-population imaging or co-expression with green optogenetic actuators):

| Indicator | Half-Decay (ms) | dF/F per 1 AP (%) | Excitation (nm) | Emission (nm) | Source |
|-----------|-----------------|--------------------|-----------------|--------------------|--------|
| jRGECO1a | ~350 | ~12 | 560 | 590 | Dana et al., 2016 |
| jRCaMP1a | ~500 | ~5 | 560 | 590 | Dana et al., 2016 |
| jRCaMP1b | ~350 | ~8 | 560 | 590 | Dana et al., 2016 |

**Warning**: Red indicators are generally dimmer and less sensitive than green GCaMPs. Analysis requires adjusted SNR thresholds and more conservative deconvolution.

## Expression Systems

### AAV Serotype Selection

The choice of AAV serotype determines which cell types and brain regions are effectively transduced.

| Serotype | Brain Tropism | Cell Preference | Notes | Source |
|----------|---------------|-----------------|-------|--------|
| AAV1 | Broad, cortex-preferred | Neurons (strong) | High transduction efficiency; first approved for gene therapy | Aschauer et al., 2013 |
| AAV2 | Moderate, localized | Neurons | Smaller spread from injection site; retrograde with AAV2-retro | Aschauer et al., 2013 |
| AAV5 | Broad | Astrocytes preferred, also neurons | Best for glial targeting | Aschauer et al., 2013 |
| AAV8 | Broad | Neurons and astrocytes | Good for deep structures | Aschauer et al., 2013 |
| AAV9 | Very broad, crosses BBB | Neurons, some glia | Can be delivered IV in neonates | Aschauer et al., 2013 |
| PHP.eB | CNS-wide (IV delivery) | Neurons (strong) | Engineered for systemic delivery in mice; tropism is strain-dependent (C57BL/6 best) | Chan et al., 2017 |
| AAV2-retro | Retrograde from terminals | Projection neurons | Inject at projection target to label cell bodies in source region | Tervo et al., 2016 |

**Critical notes**:
- Tropism varies between species and even mouse strains. PHP.eB works well in C57BL/6 but poorly in BALB/c mice (Hordeaux et al., 2018).
- Always validate expression pattern in your specific preparation before running experiments.
- Higher viral titers produce brighter expression but risk cytotoxicity and nuclear GCaMP accumulation (overexpression toxicity; see below).

### Promoter Selection

| Promoter | Expression Pattern | Strength | Use Case | Source |
|----------|-------------------|----------|----------|--------|
| CaMKIIa | Excitatory neurons | Moderate | Standard for cortical/hippocampal pyramidal cells | Dittgen et al., 2004 |
| Synapsin (hSyn) | Pan-neuronal | Strong | All neurons; most common for calcium imaging | Kugler et al., 2003 |
| CAG | Ubiquitous | Very strong | Maximum brightness; includes glia with non-neuronal AAVs | Niwa et al., 1991 |
| EF1a | Ubiquitous | Strong | Common alternative to CAG | Kim et al., 1990 |
| mDlx | GABAergic interneurons | Moderate | Inhibitory neuron-specific imaging | Dimidschstein et al., 2016 |
| GFAP | Astrocytes | Moderate | Astrocyte calcium imaging | Lee et al., 2008 |

### Cre-Dependent Expression Strategies

For cell-type-specific expression, Cre-dependent constructs are used in Cre driver lines:

- **DIO (Double-floxed Inverted Open reading frame)**: Inverted GCaMP is flipped into sense orientation only in Cre-expressing cells
- **FLEX**: Similar double-floxed strategy; most common
- **Advantage**: Sparse, cell-type-specific labeling reduces neuropil contamination and simplifies ROI detection
- **Disadvantage**: Expression level depends on Cre driver line activity and AAV titer

### Transgenic Mouse Lines

| Line | Indicator | Expression | Notes | Source |
|------|-----------|------------|-------|--------|
| Ai93 (TITL-GCaMP6f) | GCaMP6f | Cre-dependent, tTA-dependent | Requires both Cre and tTA drivers; widely used in Allen Brain Observatory | Madisen et al., 2015 |
| Ai94 (TITL-GCaMP6s) | GCaMP6s | Cre-dependent, tTA-dependent | Slower but more sensitive than Ai93 | Madisen et al., 2015 |
| Ai148 (TIT2L-GC6f-ICL-tTA2) | GCaMP6f | Cre-dependent, self-amplifying | Brighter than Ai93; standard for Allen Institute | Daigle et al., 2018 |
| Thy1-GCaMP6 | GCaMP6s/f | Sparse, layer 5 pyramidal | No Cre required; variable expression across founders | Dana et al., 2014 |
| CaMPARI | Photoconvertible | Activity-dependent, all-optical | Converts green-to-red upon simultaneous calcium and UV light | Fosque et al., 2015 |

**Domain judgment on expression method**:
- Viral expression (AAV) takes 2-4 weeks to reach stable levels. Imaging too early produces dim signals; too late risks overexpression toxicity.
- Transgenic lines provide more uniform expression but may have lower signal amplitude than high-titer AAV.
- Overexpression toxicity: chronically high GCaMP levels can cause nuclear filling (GCaMP enters the nucleus), altered calcium buffering, and abnormal neural activity. Signs include: bright fluorescence with no transients, nuclear fluorescence visible, and abnormally high baseline fluorescence (Chen et al., 2013; Daigle et al., 2018).

## Indicator-Specific Analysis Implications

### GCaMP6s
- **Deconvolution**: Tau = 1.0-1.5 s. Deconvolution strongly recommended because raw traces are very slow.
- **Baseline window**: Use longer sliding window (60-90 s) because transients are prolonged and a short window tracks them.
- **Neuropil correction**: Standard r = 0.7 works well. High sensitivity means transients are usually distinguishable from neuropil.
- **Spike inference quality**: Good for low-rate neurons (< 3 Hz). Above ~5 Hz, individual spikes merge into plateau.

### GCaMP6f
- **Deconvolution**: Tau = 0.3-0.4 s. Most common choice for general-purpose 2P.
- **Baseline window**: 30-60 s sliding window is appropriate.
- **Neuropil correction**: Standard r = 0.7. Lower SNR per spike than GCaMP6s means neuropil correction is more critical.
- **Spike inference quality**: Resolves spikes up to ~10 Hz. Standard workhorse indicator.

### jGCaMP7f
- **Deconvolution**: Tau = 0.3-0.4 s (similar to GCaMP6f decay but higher amplitude).
- **Baseline window**: 30-60 s.
- **Neuropil correction**: Brighter than GCaMP6f; over-subtraction risk is higher. Consider starting with r = 0.6 and adjusting.
- **Spike inference quality**: Better single-spike detection than GCaMP6f due to higher dF/F.

### jGCaMP8f
- **Deconvolution**: Tau = 0.2-0.3 s. Fastest widely available indicator.
- **Baseline window**: 20-40 s may be sufficient due to faster kinetics.
- **Neuropil correction**: Very bright; monitor for over-subtraction artifacts.
- **Spike inference quality**: Best temporal resolution in the family. Can resolve bursts up to ~20 Hz.
- **Note**: Ground truth data for jGCaMP8 deconvolution is still being accumulated (as of 2025). CASCADE has begun incorporating jGCaMP8 ground truth (Rupprecht et al., 2025 preprint).

### jGCaMP8m
- **Deconvolution**: Tau = 0.14-0.2 s. The fastest variant.
- **Frame rate requirement**: Benefits from higher frame rates (> 20 Hz) to capture fast dynamics.
- **Best for**: Fast-spiking interneurons, cerebellar granule cells, any application where temporal precision matters most.

### jGCaMP8s
- **Deconvolution**: Tau = 0.2-0.3 s.
- **Analysis advantage**: Combines good sensitivity with improved kinetics over GCaMP6s.
- **Best for**: Replacing GCaMP6s in experiments where both sensitivity and speed matter.

## Wavelength and Optical Parameters

| Parameter | Green GCaMP | Red jRGECO1a | Source |
|-----------|-------------|--------------|--------|
| Excitation peak (1P) | 488 nm | 560 nm | Manufacturer data |
| Excitation peak (2P) | 920-940 nm | 1000-1040 nm | Dana et al., 2016 |
| Isosbestic point | 405-415 nm | ~530 nm | Lerner et al., 2015 |
| Emission peak | 510 nm | 590 nm | Manufacturer data |
| Emission filter | 500-550 nm BP | 570-640 nm BP | Common configurations |

## References

- Aschauer, D. F., et al. (2013). Analysis of transduction efficiency, tropism and axonal transport of AAV serotypes 1, 2, 5, 6, 8 and 9 in the mouse brain. *PLoS ONE*, 8(9), e76310.
- Chan, K. Y., et al. (2017). Engineered AAVs for efficient noninvasive gene delivery to the central and peripheral nervous systems. *Nature Neuroscience*, 20(8), 1172-1179.
- Chen, T. W., et al. (2013). Ultrasensitive fluorescent proteins for imaging neuronal activity. *Nature*, 499, 295-300.
- Chen, X., et al. (2020). Soma-targeted imaging of neural circuits by ribosome tethering. *Neuron*, 107(3), 454-469.
- Daigle, T. L., et al. (2018). A suite of transgenic driver and reporter mouse lines with enhanced brain-cell-type targeting and functionality. *Cell*, 174(2), 465-480.
- Dana, H., et al. (2014). Thy1-GCaMP6 transgenic mice for neuronal population imaging in vivo. *PLoS ONE*, 9(9), e108697.
- Dana, H., et al. (2016). Sensitive red protein calcium indicators for imaging neural activity. *eLife*, 5, e12727.
- Dana, H., et al. (2019). High-performance calcium sensors for imaging activity in neuronal populations and microcompartments. *Nature Methods*, 16, 649-657.
- Dimidschstein, J., et al. (2016). A viral strategy for targeting and manipulating interneurons across vertebrate species. *Nature Neuroscience*, 19(12), 1743-1749.
- Dittgen, T., et al. (2004). Lentivirus-based genetic manipulations of cortical neurons and their optical and electrophysiological monitoring in vivo. *Proceedings of the National Academy of Sciences*, 101(52), 18206-18211.
- Fosque, B. F., et al. (2015). Neural circuits. Labeling of active neural circuits in vivo with designed calcium integrators. *Science*, 347(6223), 755-760.
- Hordeaux, J., et al. (2018). The neurotropic properties of AAV-PHP.B are limited to C57BL/6J mice. *Molecular Therapy*, 26(3), 664-668.
- Kugler, S., et al. (2003). Human synapsin 1 gene promoter confers highly neuron-specific long-term transgene expression from an adenoviral vector in the adult rat brain. *Gene Therapy*, 10(4), 337-347.
- Madisen, L., et al. (2015). Transgenic mice for intersectional targeting of neural sensors and effectors with high specificity and performance. *Neuron*, 85(5), 942-958.
- Rupprecht, P., et al. (2021). A database and deep learning toolbox for noise-optimized, generalized spike inference from calcium imaging. *Nature Neuroscience*, 24, 1324-1337.
- Tervo, D. G. R., et al. (2016). A designer AAV variant permits efficient retrograde access to projection neurons. *Neuron*, 92(2), 372-382.
- Zhang, Y., et al. (2023). Fast and sensitive GCaMP calcium indicators for imaging neural populations. *Nature*, 615, 884-891.
