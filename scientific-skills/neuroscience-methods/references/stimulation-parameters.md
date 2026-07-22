# Stimulation Parameters Reference

Detailed pulse protocols, fiber optic specifications, viral vector selection, and light delivery parameters for optogenetic experiments.

## Pulse Protocol Recipes

### Recipe 1: Standard Excitatory Activation (ChR2)

**Use case**: Drive spiking in excitatory neurons during a behavioral epoch.

| Parameter | Value | Rationale |
|---|---|---|
| Opsin | ChR2 (H134R) | Standard, well-characterized (Boyden et al., 2005) |
| Wavelength | 473 nm | Matches ChR2 absorption peak (Mattis et al., 2012) |
| Power at fiber tip | 5-10 mW | Yields ~1-5 mW/mm2 for 200 um fiber |
| Pulse width | 5 ms | Sufficient for single spike per pulse (Mattis et al., 2012) |
| Frequency | 20 Hz | Within ChR2 reliable range; matches many physiological rhythms |
| Duty cycle | 10% | 5 ms pulse at 20 Hz = safe thermal margin |
| Epoch duration | 1-30 s | Adjust to behavioral paradigm |
| Inter-epoch interval | >30 s | Allow full ChR2 recovery from desensitization |

**Warm-up protocol**: Deliver 10 pulses before the analysis epoch begins to allow ChR2 photocurrent to reach steady-state (Mattis et al., 2012).

### Recipe 2: High-Frequency Activation (ChETA or Chronos)

**Use case**: Drive neurons at gamma frequency (40-100 Hz) or higher.

| Parameter | Value | Rationale |
|---|---|---|
| Opsin | ChETA (E123T) or Chronos | Fast kinetics required (Gunaydin et al., 2010; Klapoetke et al., 2014) |
| Wavelength | 473 nm (ChETA) or 500 nm (Chronos) | Match respective absorption peaks |
| Power at fiber tip | 10-15 mW | Higher power compensates for lower ChETA photocurrent |
| Pulse width | 1-2 ms | Short pulses for fast kinetics |
| Frequency | 40-100 Hz | Achievable with ChETA/Chronos (Gunaydin et al., 2010) |
| Duty cycle | 4-20% | 1 ms at 40 Hz = 4%; 2 ms at 100 Hz = 20% |
| Max continuous train | 10 s | Longer trains risk spike failure even with fast opsins |

**Critical note**: Even with fast opsins, verify spike fidelity with electrophysiology for the first few animals. Spike failure increases over time in extended trains (Mattis et al., 2012).

### Recipe 3: Red-Shifted Excitation (ChrimsonR)

**Use case**: Deep tissue activation, dual-color experiments, or reduced phototoxicity.

| Parameter | Value | Rationale |
|---|---|---|
| Opsin | ChrimsonR | Most red-shifted fast opsin (Klapoetke et al., 2014) |
| Wavelength | 638 nm | Matches ChrimsonR peak |
| Power at fiber tip | 10-20 mW | Red light penetrates deeper; may need more power at surface |
| Pulse width | 5-10 ms | Slightly slower kinetics than ChR2 |
| Frequency | 10-20 Hz | Conservative for reliable spiking |
| Duty cycle | 5-20% | Low heating risk with red light |

**Dual-color pairing**: ChrimsonR (638 nm excitation) can be combined with stGtACR2 (473 nm inhibition) for bidirectional control in the same animal. Verify minimal spectral crosstalk at your specific power levels (Klapoetke et al., 2014).

### Recipe 4: Ultra-Sensitive Large-Volume Activation (ChRmine)

**Use case**: Activate large cortical volumes, deep brain structures, or minimally invasive stimulation.

| Parameter | Value | Rationale |
|---|---|---|
| Opsin | ChRmine or hsChRmine | Ultra-high sensitivity (Marshel et al., 2019) |
| Wavelength | 532 nm or 561 nm | Broad activation spectrum centered ~520-530 nm |
| Power at fiber tip | 0.5-5 mW | Much lower power sufficient due to high sensitivity |
| Pulse width | 2-5 ms | Short pulses to compensate for slow tau-off (~60 ms) |
| Frequency | 10-20 Hz (ChRmine) or up to 50 Hz (hsChRmine) | Limited by slow kinetics (Kishi et al., 2022) |
| Duty cycle | 2-10% | Low power + low duty cycle = minimal heating |

**Important**: ChRmine's slow tau-off means each pulse may evoke multiple spikes at high expression levels. If single-spike precision is needed, use ChR2 or Chronos instead.

### Recipe 5: Sustained Somatic Inhibition (stGtACR2)

**Use case**: Silence a population of neurons during a behavioral task.

| Parameter | Value | Rationale |
|---|---|---|
| Opsin | stGtACR2 | Most potent somatic inhibition (Mahn et al., 2018) |
| Wavelength | 473 nm | Matches stGtACR2 peak (~480 nm) |
| Power at fiber tip | 1-5 mW | High sensitivity (EPD50 ~0.05 mW/mm2) allows low power |
| Protocol | Continuous or 1 s on / 0.5 s off | Pulsed to manage heating |
| Ramp-down | 500 ms linear ramp at offset | Prevents rebound excitation |
| Max epoch | 60 s continuous at low power (<2 mW) | Monitor for heating at longer durations |

**Heating management**: Despite stGtACR2's high sensitivity, blue light for sustained inhibition can still heat tissue. At 5 mW continuous 473 nm, expect ~0.5-1.25 deg C increase (Stujenske et al., 2015). Reduce power or use pulsed protocol for epochs >10 s.

### Recipe 6: Yellow-Light Inhibition (eNpHR3.0)

**Use case**: Inhibit neurons when blue light is already used for excitation (dual-opsin experiments).

| Parameter | Value | Rationale |
|---|---|---|
| Opsin | eNpHR3.0 | Yellow-activated inhibition (Gradinaru et al., 2010) |
| Wavelength | 594 nm | Matches NpHR excitation peak |
| Power at fiber tip | 10-15 mW | Higher power needed due to low pump sensitivity (EPD50: 5-10 mW/mm2) |
| Protocol | Continuous for <15 s; pulsed (5 s on / 2 s off) for longer | Cl- loading limit (Raimondo et al., 2012) |
| Ramp-down | 1 s linear ramp at offset | Prevents rebound from Cl- loading |
| Max continuous epoch | 15 s | Beyond this, GABA-A reversal potential shifts become significant |

**Rebound warning**: Always include a ramp-down period. Abrupt NpHR offset after >5 s illumination produces rebound spiking in ~30% of neurons (Raimondo et al., 2012).

### Recipe 7: Bistable Excitability Modulation (SSFO)

**Use case**: Increase neural excitability over minutes without continuous light delivery.

| Parameter | Value | Rationale |
|---|---|---|
| Opsin | SSFO (C128S/D156A) | Bistable, ~29 min tau-off (Yizhar et al., 2011) |
| Activation wavelength | 473 nm | Blue light opens channel |
| Deactivation wavelength | 594 nm | Yellow light closes channel |
| Activation pulse | 1-2 s continuous | Brief pulse sufficient for full activation |
| Activation power | 1-5 mW | Minimal light needed due to long open state |
| Deactivation pulse | 5-10 s continuous | Longer pulse ensures complete closure |

**Key insight**: SSFO modulates excitability (subthreshold depolarization), it does NOT drive spikes. It makes neurons more responsive to endogenous synaptic inputs. This is conceptually different from ChR2-driven activation and is appropriate for different experimental questions (Yizhar et al., 2011).

### Recipe 8: Place Cell Tagging / Optogenetic Identification

**Use case**: Identify opsin-expressing neurons during extracellular recording ("optotagging").

| Parameter | Value | Rationale |
|---|---|---|
| Opsin | ChR2 (H134R) | Reliable, short-latency spikes |
| Wavelength | 473 nm | Standard |
| Power at fiber tip | 1-5 mW (start low, ramp up) | Titrate to find minimal effective power |
| Pulse width | 1-2 ms | Brief to ensure single spike |
| Frequency | 1-2 Hz for identification; 10-50 Hz for waveform matching | Low rate for clean identification |
| Train structure | 10-50 pulses at each power level | Statistical reliability |
| Identification criteria | Latency <5 ms, jitter <2 ms, waveform correlation r > 0.95 | Lima et al., 2009; Cohen et al., 2012 |

**Critical requirements**: The optotagging pulse train must be delivered during a behavioral period where the cell's natural firing can be compared to light-evoked firing. Report both the false-positive rate (spontaneous spikes in the latency window) and the reliability (fraction of pulses evoking a spike) (Cohen et al., 2012).

## Fiber Optic Specifications

### Standard Configurations

| Application | Core Diameter | NA | Total OD (with cladding) | Recommended | Citation |
|---|---|---|---|---|---|
| Mouse cortex/hippocampus | 200 um | 0.22 | ~230 um | Standard for most experiments | Sparta et al., 2012 |
| Mouse deep brain (VTA, SN) | 200 um | 0.39 | ~230 um | Wider cone for deep structures | Sparta et al., 2012 |
| Mouse, minimal damage | 100 um | 0.22 | ~125 um | Reduced tissue displacement | |
| Rat brain | 200-400 um | 0.39 | 230-430 um | Larger target volumes in rat | Sparta et al., 2012 |
| Primate cortex | 200 um | 0.22 | ~230 um | Multiple fibers for coverage | Diester et al., 2011 |
| Bilateral implant | 200 um x 2 | 0.22 | ~230 um each | Separate fibers per hemisphere | |

### Illumination Volume Estimates

For a 200 um core, 0.22 NA fiber delivering 473 nm light in brain tissue:

| Distance from Fiber Tip | Estimated Irradiance (% of tip) | Approximate Diameter of Illuminated Cone | Source |
|---|---|---|---|
| 0 um (fiber face) | 100% | 200 um | Geometry |
| 100 um | ~50% | ~250 um | Yizhar et al., 2011 |
| 200 um | ~20% | ~300 um | Aravanis et al., 2007 |
| 500 um | ~3.2% | ~450 um | Aravanis et al., 2007 |
| 1000 um | ~0.56% | ~600 um | Aravanis et al., 2007 |

**Practical implication**: For a target at 500 um below the fiber tip, only ~3% of the tip irradiance reaches the target. If you need **1 mW/mm2** at the target and the fiber tip produces **30 mW/mm2**, the effective irradiance at 500 um is ~1 mW/mm2 (Aravanis et al., 2007).

### Fiber Placement Guidelines

1. **Target the fiber 200-500 um above the region of interest** (Yizhar et al., 2011)
2. **Never place the fiber within the target region** — mechanical damage at the fiber tip destroys the very neurons you are trying to manipulate
3. **For dorsal hippocampus (CA1)**: Place fiber tip at the boundary of overlying cortex and hippocampus (~-1.2 to -1.4 mm DV from brain surface in C57BL/6 mice; Paxinos & Franklin, 2012)
4. **For ventral structures (VTA, NAc)**: Use a higher NA fiber (0.39) to spread light more widely and compensate for the longer light path
5. **Verify placement post-hoc**: Always confirm fiber tip location in histological sections. Report the distance between fiber tip and the nearest expressing neurons

### Thermal Safety Calculations

Estimated steady-state temperature increase at 100 um from fiber tip for 473 nm continuous illumination (Stujenske et al., 2015):

| Power at Fiber Tip | Duty Cycle 10% | Duty Cycle 25% | Duty Cycle 50% | Duty Cycle 100% |
|---|---|---|---|---|
| 1 mW | 0.025 deg C | 0.06 deg C | 0.12 deg C | 0.25 deg C |
| 5 mW | 0.12 deg C | 0.31 deg C | 0.62 deg C | 1.25 deg C |
| 10 mW | 0.25 deg C | 0.62 deg C | 1.25 deg C | 2.5 deg C |
| 20 mW | 0.50 deg C | 1.25 deg C | 2.5 deg C | 5.0 deg C |

**Safety threshold**: Keep temperature increase **below 1 deg C** (Owen et al., 2019). Cells shaded above 1 deg C (10 mW at 50%, 5 mW at 100%, 20 mW at 25%) should be avoided or validated with opsin-negative controls.

**Red-shifted light heating**: 638 nm light produces approximately 30-50% less heating than 473 nm at the same power, due to lower absorption by brain tissue (Stujenske et al., 2015). This is an additional advantage of red-shifted opsins.

## Viral Vector Selection Guide

### AAV Serotype Comparison for Brain Injection

| Serotype | Neuronal Tropism | Expression Onset | Spread from Injection | Special Properties | Key Citation |
|---|---|---|---|---|---|
| AAV1 | High | 1-2 weeks | Large (~1 mm) | Anterograde transsynaptic at high titer | Aschauer et al., 2013; Zingg et al., 2017 |
| AAV2 | Moderate (neuronal-preferring) | 2-4 weeks | Small (~0.5 mm) | Confined expression, good for precise targeting | Burger et al., 2004 |
| AAV5 | Moderate (favors glia with ubiquitous promoters) | 2-4 weeks | Moderate (~0.7 mm) | Best with neuron-specific promoters | Aschauer et al., 2013 |
| AAV8 | High | 1-2 weeks | Large (~1 mm) | Good for deep structures | Aschauer et al., 2013 |
| AAV9 | High (broad) | 1-2 weeks | Large (>1 mm), crosses BBB | Systemic delivery possible; transduces glia without specific promoter | Foust et al., 2009 |
| AAV-DJ | High | 1-2 weeks | Small-moderate (~0.5-0.7 mm) | Engineered for high transduction in vitro and in vivo | Grimm et al., 2008 |
| AAVrg (AAV2-retro) | High (retrograde) | 2-4 weeks | Projection-specific | Retrograde labeling from axon terminals | Tervo et al., 2016 |

### Recommended Serotypes by Application

| Application | First Choice | Alternative | Notes |
|---|---|---|---|
| Local excitation in cortex | AAV1 or AAV5 | AAV8 | Use CaMKII or hSyn promoter |
| Local inhibition in hippocampus | AAV1 or AAV8 | AAV-DJ | Broad neuronal tropism needed |
| Projection-specific (retrograde) | AAVrg | AAV6 (partial retrograde) | Inject at axon terminal field |
| Projection-specific (anterograde) | AAV1 (high titer, >1e13 vg/mL) | AAV9 | Transsynaptic spread (Zingg et al., 2017) |
| Precise local targeting | AAV2 or AAV-DJ | | Minimal spread from injection site |
| Cre-dependent expression | Any + DIO/FLEX construct | | Serotype determines spread, Cre determines specificity |
| Interneuron targeting | AAV + Dlx enhancer | | Dimidschstein et al., 2016 |

### Titer and Volume Guidelines

| Parameter | Mouse | Rat | Primate |
|---|---|---|---|
| Standard titer | 1e12 - 5e12 vg/mL | 1e12 - 5e12 vg/mL | 1e12 - 1e13 vg/mL |
| Volume per site | 200-500 nL | 500 nL - 2 uL | 1-5 uL |
| Injection rate | 50-100 nL/min | 100-200 nL/min | 200-500 nL/min |
| Wait after injection (before withdrawal) | 5-10 min | 5-10 min | 10-15 min |
| Min expression time | 2-3 weeks | 2-3 weeks | 4-6 weeks |
| Optimal expression time | 3-6 weeks | 3-6 weeks | 6-8 weeks |
| Toxicity risk increases | >8 weeks at high titer | >8 weeks at high titer | >12 weeks |

**Titer warning**: Titers above **1e13 vg/mL** significantly increase the risk of cytotoxicity, particularly with strong promoters (CaMKII, hSyn). Signs include: nuclear inclusion bodies, cell loss at injection center, reactive gliosis. Always examine injection sites histologically (Miyashita et al., 2013).

**Injection rate matters**: Injecting too fast causes tissue damage and backflow up the needle track. Use a micropump or calibrated pressure system. Manual injection with a Hamilton syringe is acceptable if performed slowly with monitoring (Cetin et al., 2006).

### Promoter Selection

| Promoter | Expression Pattern | Strength | Time to Peak | Citation |
|---|---|---|---|---|
| hSyn (human Synapsin-1) | Pan-neuronal | Moderate-high | 2-3 weeks | Kugler et al., 2003 |
| CaMKIIa | Excitatory neurons (forebrain) | High | 2-4 weeks | Dittgen et al., 2004 |
| mDlx | GABAergic interneurons | Moderate | 3-4 weeks | Dimidschstein et al., 2016 |
| Ef1a | Ubiquitous (all cell types) | Very high | 1-2 weeks | |
| CAG | Ubiquitous (all cell types) | Very high | 1-2 weeks | |
| CMV | Ubiquitous, silences over time in neurons | Variable | 1-2 weeks | Paterna et al., 2000 |

**Promoter rule**: For optogenetics, **always use a cell-type-specific promoter** (hSyn, CaMKII, mDlx) unless you have a specific reason to use a ubiquitous promoter. CMV in particular silences over weeks in neurons and should be avoided for chronic experiments (Paterna et al., 2000; Aschauer et al., 2013).

### Cre-Dependent Strategies

For experiments using Cre-driver transgenic lines:

| Strategy | Construct | Advantage | Consideration |
|---|---|---|---|
| DIO (Double-floxed Inverted Open reading frame) | Ef1a-DIO-ChR2-eYFP | Strong, specific expression | Requires Cre mouse line |
| FLEX (Flip-excision) | Ef1a-FLEX-ChR2-eYFP | Equivalent to DIO | Same mechanism, different nomenclature |
| CreON/FlpON (intersectional) | Ef1a-CreON/FlpON-ChR2 | Dual-recombinase specificity | Requires Cre AND Flp (Fenno et al., 2014) |

**Expression level note**: Cre-dependent constructs typically produce lower expression than direct promoter-driven constructs because the inverted transgene must be flipped by Cre before transcription can begin. Allow an additional 1-2 weeks of expression time compared to non-Cre constructs (Atasoy et al., 2008).

## Common Equipment Specifications

### Laser Systems

| Wavelength | Common Source | Typical Max Power | Used For |
|---|---|---|---|
| 473 nm | DPSS laser | 50-200 mW | ChR2, CheRiff, stGtACR2, Chronos |
| 532 nm | DPSS laser | 50-200 mW | C1V1, ChRmine, eArch3.0 |
| 561 nm | DPSS laser | 50-150 mW | ChRmine, ReaChR, eNpHR3.0 |
| 594 nm | DPSS laser | 20-50 mW | eNpHR3.0, SSFO deactivation |
| 638 nm | Diode laser | 50-300 mW | ChrimsonR, CsChrimson |

**LED alternative**: For experiments not requiring precise temporal control (<10 ms resolution), fiber-coupled LEDs are cheaper and sufficient. LEDs have broader spectra (~20-30 nm FWHM) but adequate for most opsins (Warden et al., 2012).

### Patch Cable and Commutator

| Component | Specification | Notes |
|---|---|---|
| Patch cable core | Match implant fiber (typically 200 um) | Mismatch causes coupling loss |
| Patch cable NA | Match or exceed implant NA | Lower NA patch cable loses light |
| Rotary joint | Single-channel or dual-channel | Required for freely moving behavior |
| Ferrule sleeve | Zirconia, 1.25 mm ID | Standard mating connector |

## References

- Aravanis, A. M. et al. (2007). An optical neural interface. *J. Neural Eng.*, 4(3), S143-S156.
- Aschauer, D. F. et al. (2013). Analysis of transduction efficiency, tropism and axonal transport of AAV serotypes 1, 2, 5, 6, 8 and 9 in the mouse brain. *PLoS ONE*, 8(9), e76310.
- Atasoy, D. et al. (2008). A FLEX switch targets Channelrhodopsin-2 to multiple cell types for imaging and long-range circuit mapping. *J. Neurosci.*, 28(28), 7025-7030.
- Boyden, E. S. et al. (2005). Millisecond-timescale, genetically targeted optical control of neural activity. *Nat. Neurosci.*, 8(9), 1263-1268.
- Burger, C. et al. (2004). Recombinant AAV viral vectors pseudotyped with viral capsids from serotypes 1, 2, and 5 display differential efficiency and cell tropism. *Mol. Ther.*, 10(2), 302-317.
- Cetin, A. et al. (2006). Stereotaxic gene delivery in the rodent brain. *Nat. Protoc.*, 1, 3166-3173.
- Cohen, J. Y. et al. (2012). Neuron-type-specific signals for reward and punishment in the ventral tegmental area. *Nature*, 482, 85-88.
- Diester, I. et al. (2011). An optogenetic toolbox designed for primates. *Nat. Neurosci.*, 14, 387-397.
- Dimidschstein, J. et al. (2016). A viral strategy for targeting and manipulating interneurons across vertebrate species. *Nat. Neurosci.*, 19, 1743-1749.
- Dittgen, T. et al. (2004). Lentivirus-based genetic manipulations of cortical neurons and their optical and electrophysiological monitoring in vivo. *PNAS*, 101(52), 18206-18211.
- Fenno, L. E. et al. (2014). Targeting cells with single vectors using multiple-feature Boolean logic. *Nat. Methods*, 11, 763-772.
- Foust, K. D. et al. (2009). Intravascular AAV9 preferentially targets neonatal neurons and adult astrocytes. *Nat. Biotechnol.*, 27, 59-65.
- Gradinaru, V. et al. (2010). Molecular and cellular approaches for diversifying and extending optogenetics. *Cell*, 141(1), 154-165.
- Grimm, D. et al. (2008). In vitro and in vivo gene therapy vector evolution via multispecies interbreeding and retargeting of adeno-associated viruses. *J. Virol.*, 82(12), 5887-5911.
- Gunaydin, L. A. et al. (2010). Ultrafast optogenetic control. *Nat. Neurosci.*, 13(3), 387-392.
- Kishi, K. E. et al. (2022). Structural basis for channel conduction in the pump-like channelrhodopsin ChRmine. *Cell*, 185, 672-689.
- Klapoetke, N. C. et al. (2014). Independent optical excitation of distinct neural populations. *Nat. Methods*, 11, 338-346.
- Kugler, S. et al. (2003). Neuron-specific expression of therapeutic proteins. *Mol. Cell. Neurosci.*, 23(4), 618-633.
- Lima, S. Q. et al. (2009). PINP: a new method of tagging neuronal populations for identification during in vivo electrophysiological recording. *PLoS ONE*, 4(7), e6099.
- Mahn, M. et al. (2018). High-efficiency optogenetic silencing with soma-targeted anion-conducting channelrhodopsins. *Nat. Commun.*, 9, 4125.
- Marshel, J. H. et al. (2019). Cortical layer-specific critical dynamics triggering perception. *Science*, 365(6453), eaaw5202.
- Mattis, J. et al. (2012). Principles for applying optogenetic tools. *Nat. Methods*, 9, 159-172.
- Miyashita, T. et al. (2013). Long-term channelrhodopsin-2 expression can induce abnormal axonal morphology and targeting in cerebral cortex. *Front. Neural Circuits*, 7, 8.
- Owen, S. F. et al. (2019). Thermal constraints on in vivo optogenetic manipulations. *Nat. Neurosci.*, 22, 1061-1065.
- Paterna, J. C. et al. (2000). Influence of promoter and WHV post-transcriptional regulatory element on AAV-mediated transgene expression in the rat brain. *Gene Ther.*, 7, 1304-1311.
- Raimondo, J. V. et al. (2012). Optogenetic silencing strategies differ in their effects on inhibitory synaptic transmission. *Nat. Neurosci.*, 15, 1102-1104.
- Sparta, D. R. et al. (2012). Construction of implantable optical fibers for long-term optogenetic manipulation of neural circuits. *Nat. Protoc.*, 7, 12-23.
- Stujenske, J. M. et al. (2015). Modeling the spatiotemporal dynamics of light and heat propagation for in vivo optogenetics. *Cell Rep.*, 12(3), 525-534.
- Tervo, D. G. R. et al. (2016). A designer AAV variant permits efficient retrograde access to projection neurons. *Neuron*, 92(2), 372-382.
- Warden, M. R. et al. (2012). Optical neural interfaces. *Annu. Rev. Biomed. Eng.*, 14, 389-417.
- Yizhar, O. et al. (2011). Optogenetics in neural systems. *Neuron*, 71(1), 9-34.
- Zingg, B. et al. (2017). AAV-mediated anterograde transsynaptic tagging. *Neuron*, 93(1), 92-105.
