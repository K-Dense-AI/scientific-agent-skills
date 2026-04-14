# Pipeline Details: Tool Comparison and Modality-Specific Processing

## Tool Comparison Matrix

### Overview

Four major open-source pipelines exist for calcium imaging analysis. Each has distinct strengths depending on your imaging modality, data scale, and computational resources.

### Suite2P (Pachitariu et al., 2017)

- **Language**: Python
- **Modality**: Primarily 2P; 1P support via preprocessing
- **Repository**: [MouseLand/suite2p](https://github.com/MouseLand/suite2p)
- **Key features**:
 - Fastest processing: runs faster than real time on standard workstations
 - Clustering-based ROI detection via PCA and spatial smoothing
 - Integrated Cellpose support for anatomical detection
 - Built-in GUI for manual curation with classifier retraining
 - Neuropil coefficient estimated iteratively with deconvolution
- **Best for**: Large 2P datasets (>10,000 neurons), rapid processing, labs with limited computational infrastructure
- **Limitations**: Less flexible background modeling than CaImAn; 1P support is secondary

### CaImAn (Giovannucci et al., 2019)

- **Language**: Python (MATLAB version also available)
- **Modality**: 2P and 1P (via CNMF-E mode)
- **Repository**: [flatironinstitute/CaImAn](https://github.com/flatironinstitute/CaImAn)
- **Key features**:
 - CNMF-based source extraction with principled statistical model
 - NoRMCorre for non-rigid motion correction (Pnevmatikakis & Giovannucci, 2017)
 - CNMF-E background model for 1P data (Zhou et al., 2018)
 - OnACID for online processing during acquisition (Giovannucci et al., 2017)
 - CNN-based component evaluation
 - MapReduce framework for datasets larger than RAM
- **Best for**: 1P miniscope data (CNMF-E mode), principled statistical source separation, online processing, very large datasets
- **Limitations**: More parameters to tune; slower than Suite2P for standard 2P processing

### CNMF-E (Zhou et al., 2018)

- **Language**: MATLAB (standalone) or Python (via CaImAn)
- **Modality**: 1P / miniscope only
- **Key features**:
 - Extended background model explicitly captures large, structured 1P background
 - Models background as low-rank spatiotemporal component rather than per-ROI annulus
 - Best background subtraction performance compared to alternatives (Zhou et al., 2018)
- **Best for**: 1P miniscope data where background subtraction is critical
- **Limitations**:
 - Computationally demanding (memory and CPU)
 - Can over-segment: tends to split single neurons into multiple components
 - Offline batch processing only (OnACID-E provides online variant)
 - Requires careful merge parameter tuning

### MIN1PIPE (Lu et al., 2018)

- **Language**: MATLAB
- **Modality**: 1P / miniscope only
- **Repository**: [JinghaoLu/MIN1PIPE](https://github.com/JinghaoLu/MIN1PIPE)
- **Key features**:
 - Fully automatic with minimal parameter tuning
 - Neural enhancing module for background removal via morphological operations
 - Hierarchical movement correction handles deformations with minimal error propagation
 - Seeds-cleansed extraction avoids setting unknown initialization parameters
 - RNN-LSTM classifier for calcium transient validation
- **Best for**: Labs new to 1P analysis wanting a turnkey solution; data with severe movement artifacts
- **Limitations**: MATLAB only; less community support than CaImAn; no online processing mode

### Summary Comparison Table

| Feature | Suite2P | CaImAn | CNMF-E | MIN1PIPE |
|---------|---------|--------|--------|----------|
| 2P support | Excellent | Excellent | No | No |
| 1P support | Limited | Excellent (CNMF-E mode) | Excellent | Excellent |
| Speed | Fastest | Moderate | Slow | Moderate |
| Background model | Per-ROI annulus | CNMF / CNMF-E low-rank | Low-rank spatio-temporal | Morphological |
| Online processing | No | Yes (OnACID) | No (OnACID-E) | No |
| GUI | Yes | Jupyter notebooks | No | No |
| Auto-classification | Naive Bayes | CNN | Manual | RNN-LSTM |
| Language | Python | Python/MATLAB | MATLAB/Python | MATLAB |
| Scalability (>10k neurons) | Excellent | Excellent | Moderate | Moderate |

## Preprocessing Differences: 2P vs. 1P

### Two-Photon (2P) Microscopy

**Characteristics**:
- Optical sectioning: minimal out-of-focus fluorescence
- Sparse, punctate background (neuropil only)
- Higher SNR for individual neurons
- Typical frame rates: 15-30 Hz (resonant scanning), 1-5 Hz (galvo scanning)
- FOV: 500 um x 500 um typical at 16x-25x magnification

**Preprocessing pipeline**:
1. Motion correction (rigid or non-rigid)
2. ROI detection (standard CNMF, Suite2P clustering, or Cellpose)
3. Neuropil correction (annulus-based, r ~ 0.7; Chen et al., 2013)
4. dF/F computation
5. Deconvolution

**2P-specific parameters**:
- Registration max shift: **10% of FOV** (Suite2P default; Pachitariu et al., 2017)
- Spatial scale for cell detection: auto-detect or set to match cell diameter in pixels
- Neuropil inner radius: **2 pixels** gap between ROI and neuropil annulus (Suite2P default)

### One-Photon (1P) / Miniscope

**Characteristics**:
- No optical sectioning: large, fluctuating background from out-of-focus fluorescence
- Background can be 5-10x brighter than individual cell signals
- Lower SNR per neuron than 2P
- Typical frame rates: 10-30 Hz
- FOV: depends on GRIN lens; typically 500-1000 um diameter
- Imaging through GRIN lens adds optical aberrations

**Preprocessing pipeline**:
1. Spatial high-pass filtering or morphological opening (remove large-scale background before registration)
2. Motion correction (on high-pass filtered data; Giovannucci et al., 2019)
3. Apply motion correction vectors to original (unfiltered) data
4. Source extraction with explicit background model (CNMF-E or MIN1PIPE)
5. dF/F computation (background already subtracted by CNMF-E)
6. Deconvolution

**1P-specific parameters**:
- Background model rank in CNMF-E: **1-3** (number of background components per patch; Zhou et al., 2018)
- Ring model radius for CNMF-E: **~1.5x expected cell radius** (CaImAn documentation)
- Spatial high-pass filter kernel: **~2-3x cell diameter** for preprocessing (expert consensus)
- MIN1PIPE neural enhancing: morphological disk radius ~ cell diameter

**Critical difference**: Do NOT use standard neuropil subtraction (F - r*Fneu) for 1P data. The neuropil annulus approach assumes sparse background, which is violated in 1P imaging. CNMF-E's low-rank background model is required (Zhou et al., 2018).

### Fiber Photometry

**Characteristics**:
- Population-level signal (no single-cell resolution)
- Uses fiber optic implant, not a microscope
- Measures bulk fluorescence changes from indicator-expressing population
- Typical sampling rates: 100-1000 Hz (photomultiplier/photodiode) or 20-40 Hz (camera-based)
- Often uses isosbestic control channel (405-415 nm excitation)

**Preprocessing pipeline**:
1. Deinterleave signal and control channels (if time-division multiplexed)
2. Smooth both channels (low-pass Butterworth filter, **< 10 Hz** cutoff for neural signals)
3. Fit isosbestic channel to signal channel via regression
4. Subtract fitted isosbestic from signal (motion + bleaching correction)
5. Divide by fitted isosbestic to get dF/F
6. Z-score for cross-subject comparison

**Fiber photometry-specific parameters**:
- Isosbestic excitation wavelength: **405-415 nm** (calcium-independent GCaMP excitation; Lerner et al., 2015)
- Signal excitation wavelength: **470 nm** (calcium-dependent GCaMP excitation)
- Regression method: IRLS preferred over OLS; OLS over-fits to neural dynamics and under-corrects artifacts
- Event detection: use z-score threshold (typically **z > 2.58**, p < 0.01) or MAD-based threshold

## Cell Classification Criteria

### Automated Classification Features

Suite2P's built-in classifier uses the following features (Pachitariu et al., 2017):

| Feature | Description | Good Cell | Bad ROI |
|---------|-------------|-----------|---------|
| Skewness | Skewness of neuropil-subtracted trace | > 0.5 | ~ 0 or negative |
| Compactness | Mean pixel distance from ROI center | Low (compact soma) | High (diffuse) |
| Footprint | Spatial extent of trace-image correlation | Moderate (soma-sized) | Very large or very small |
| Aspect ratio | Elongation of spatial footprint | ~ 1 (round) | >> 1 (elongated, likely dendrite) |

CaImAn uses a CNN trained on spatial footprints plus temporal SNR:
- **CNN probability > 0.5**: accept as cell (Giovannucci et al., 2019)
- **Peak SNR > 3**: minimum transient amplitude relative to noise (Giovannucci et al., 2019)
- **Spatial correlation > 0.8**: correlation between raw data and model prediction within ROI

### Manual Curation Guidelines

For any dataset included in a publication, manual curation should verify:

1. **Spatial footprint**: Should resemble a filled circle (soma) of expected diameter for the brain region and cell type
2. **Temporal trace**: Should contain clearly identifiable calcium transients (fast rise, slow decay) above the noise floor
3. **Neuropil-corrected trace**: Transients should persist after neuropil subtraction (if they disappear, the signal was likely neuropil, not somatic)
4. **No motion correlation**: Activity should not be correlated with registration shift metrics. Check scatter plot of neural activity vs. motion magnitude
5. **No duplicate detection**: Ensure the same neuron is not detected as multiple ROIs. Check for ROI pairs with high temporal correlation (> 0.8) and spatial proximity (< 1 cell diameter)

## Motion Metric Thresholds

| Metric | Acceptable Range | Action if Exceeded | Source |
|--------|-----------------|-------------------|--------|
| Mean frame-to-reference correlation | > **0.8** | Check preparation stability, increase reference frame count | Expert consensus |
| Max single-frame displacement | < **10% of FOV** | Flag frames, consider excluding session | Suite2P default |
| Frame displacement SD | < **2 um** for 2P, < **5 um** for 1P | Apply non-rigid if using rigid only | Expert consensus |
| Fraction of bad frames (outlier shifts) | < **5%** of total frames | Consider excluding session | Expert consensus |
| Post-correction residual motion | < **0.5 um** RMS | Acceptable for most analyses | Dombeck et al., 2007 |

**Assessment protocol**:
1. Run registration and save displacement traces (x-shift, y-shift per frame)
2. Compute correlation of each frame to the reference image
3. Plot displacement and correlation over time; look for sudden jumps (animal movement) and slow drift (mechanical instability)
4. If non-rigid correction does not adequately reduce motion artifacts, the imaging session may need to be excluded
5. For awake behaving data, examine whether residual motion correlates with behavioral variables (running speed, licking). If so, neural-behavioral correlations may be confounded by motion

## References

- Chen, T. W., et al. (2013). Ultrasensitive fluorescent proteins for imaging neuronal activity. *Nature*, 499, 295-300.
- Chen, X., et al. (2020). Soma-targeted imaging of neural circuits by ribosome tethering. *Neuron*, 107(3), 454-469.
- Dombeck, D. A., et al. (2007). Imaging large-scale neural activity with cellular resolution in awake, mobile mice. *Neuron*, 56(1), 43-57.
- Giovannucci, A., et al. (2017). OnACID: Online analysis of calcium imaging data in real time. In *Advances in Neural Information Processing Systems*.
- Giovannucci, A., et al. (2019). CaImAn: An open source tool for scalable calcium imaging data analysis. *eLife*, 8, e38173.
- Lerner, T. N., et al. (2015). Intact-brain analyses reveal distinct information carried by SNc dopamine subcircuits. *Cell*, 162(3), 635-647.
- Lu, J., et al. (2018). MIN1PIPE: A miniscope 1-photon-based calcium imaging signal extraction pipeline. *Cell Reports*, 23(12), 3673-3684.
- Mukamel, E. A., et al. (2009). Automated analysis of cellular signals from large-scale calcium imaging data. *Neuron*, 63(6), 747-760.
- Pachitariu, M., et al. (2017). Suite2p: beyond 10,000 neurons with standard two-photon microscopy. *bioRxiv*, 061507.
- Pnevmatikakis, E. A., et al. (2016). Simultaneous denoising, deconvolution, and demixing of calcium imaging data. *Neuron*, 89(2), 285-299.
- Pnevmatikakis, E. A., & Giovannucci, A. (2017). NoRMCorre: An online algorithm for piecewise rigid motion correction. *Journal of Neuroscience Methods*, 291, 83-94.
- Zhou, P., et al. (2018). Efficient and accurate extraction of in vivo calcium signals from microendoscopic video data. *eLife*, 7, e28728.
