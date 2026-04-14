# Opsin Catalog

Comprehensive reference for optogenetic opsins. All values represent typical measurements in cultured hippocampal neurons unless otherwise noted. Kinetic values are at room temperature (~22-25 deg C); in vivo values at 37 deg C are approximately 2x faster (Mattis et al., 2012).

## Excitatory Opsins (Cation Channels — Depolarizing)

### Blue-Light Activated

| Opsin | Lambda Peak | Tau-on | Tau-off | Peak Photocurrent | EPD50 | Max Spike Rate | Key Feature | Citation |
|---|---|---|---|---|---|---|---|---|
| ChR2 (wild-type) | 470 nm | <1 ms | 9-12 ms | ~200 pA | ~1.3 mW/mm2 | ~30-40 Hz | Gold standard, most characterized | Boyden et al., 2005; Nagel et al., 2005 |
| ChR2 (H134R) | 470 nm | <1 ms | ~18 ms | ~300 pA | ~1.3 mW/mm2 | ~25-35 Hz | Higher photocurrent, slightly slower | Nagel et al., 2005; Mattis et al., 2012 |
| ChETA (E123T) | 470 nm | <1 ms | ~3 ms | ~100 pA | ~2 mW/mm2 | 100-200 Hz | Ultrafast, reduced photocurrent | Gunaydin et al., 2010 |
| ChETA (E123A) | 470 nm | <1 ms | ~4 ms | ~120 pA | ~2 mW/mm2 | ~100 Hz | Fast, slightly more current than E123T | Mattis et al., 2012 |
| ChIEF | 450 nm | <1 ms | ~8 ms | ~400 pA | ~1 mW/mm2 | ~40-50 Hz | High current, low desensitization | Lin et al., 2009 |
| CheRiff | 460 nm | 0.5 ms | ~8 ms | ~1 nA | ~0.2 mW/mm2 | ~40 Hz | Highest photocurrent, 9x more sensitive than ChR2 | Hochbaum et al., 2014 |
| Chronos | 500 nm | <1 ms | ~3.5 ms | ~200 pA | ~0.5 mW/mm2 | ~100 Hz | Fastest excitatory opsin, good current | Klapoetke et al., 2014 |
| oChIEF | 450 nm | <1 ms | ~7 ms | ~500 pA | ~1 mW/mm2 | ~50 Hz | Optimized ChIEF, minimal desensitization | Lin et al., 2013 |
| ChroME | 510 nm | <1 ms | ~5 ms | ~600 pA | ~0.5 mW/mm2 | ~50 Hz | Engineered for two-photon holography | Mardinly et al., 2018 |

### Red-Shifted Excitatory Opsins

| Opsin | Lambda Peak | Tau-on | Tau-off | Peak Photocurrent | EPD50 | Max Spike Rate | Key Feature | Citation |
|---|---|---|---|---|---|---|---|---|
| C1V1(TT) | 540 nm | ~1 ms | ~50 ms | ~250 pA | ~1 mW/mm2 | ~15-20 Hz | First practical red-shifted opsin | Yizhar et al., 2011 |
| ReaChR | 590 nm | ~5 ms | ~20 ms | ~300 pA | ~0.5 mW/mm2 | ~20-30 Hz | Red-shifted, good current | Lin et al., 2013 |
| ChrimsonR | 630 nm | ~2 ms | ~15 ms | ~200 pA | ~1 mW/mm2 | ~20-30 Hz | Most red-shifted fast opsin | Klapoetke et al., 2014 |
| CsChrimson | 630 nm | ~3 ms | ~20 ms | ~250 pA | ~0.8 mW/mm2 | ~20 Hz | Higher expression than ChrimsonR | Klapoetke et al., 2014 |
| bReaChES | 570 nm | ~1 ms | ~10 ms | ~350 pA | ~0.5 mW/mm2 | ~30-40 Hz | Fast red-shifted, good for dual-color | Rajasethupathy et al., 2015 |
| ChRmine | 520-530 nm | ~5 ms | ~60 ms | >1 nA | <0.1 mW/mm2 | ~50 Hz | Ultra-high sensitivity, deep tissue | Marshel et al., 2019 |
| hsChRmine | 520-530 nm | ~3 ms | ~30 ms | ~800 pA | ~0.2 mW/mm2 | ~80 Hz | Faster ChRmine variant | Kishi et al., 2022 |
| frChRmine | 585 nm | ~4 ms | ~45 ms | ~700 pA | ~0.15 mW/mm2 | ~40 Hz | Further red-shifted ChRmine | Kishi et al., 2022 |

### Usage Notes for Excitatory Opsins

**ChR2 (H134R)** remains the most widely used and best-characterized excitatory opsin. Choose it as the default unless your experiment specifically demands:
- Higher frequency (>40 Hz) — use ChETA or Chronos
- Red-shifted activation — use ChrimsonR or ChRmine
- Maximum sensitivity — use CheRiff or ChRmine
- Dual-color experiments — use ChrimsonR paired with a blue-light inhibitory opsin

**ChR2 desensitization**: Under continuous illumination, ChR2 photocurrent decays ~80% from peak to steady-state. This means the first pulse in a train produces a larger response than subsequent pulses (Nagel et al., 2003; Mattis et al., 2012). Design experiments with an initial "warm-up" period of 5-10 pulses before the analysis epoch.

**ChRmine caution**: While ChRmine offers extraordinary sensitivity, its slow kinetics (~60 ms tau-off) mean it cannot produce individually timed spikes at high frequency. It is best suited for sustained activation paradigms or situations requiring minimal light delivery (e.g., deep brain, large volumes, or minimally invasive approaches) (Marshel et al., 2019).

## Inhibitory Opsins

### Ion Pumps (One Ion Per Photocycle)

| Opsin | Lambda Peak | Mechanism | Photocurrent | EPD50 | Key Feature | Limitation | Citation |
|---|---|---|---|---|---|---|---|
| eNpHR3.0 | 590 nm | Cl- pump (inward) | ~50-100 pA | 5-10 mW/mm2 | Established, yellow-light | Cl- loading, rebound, low sensitivity | Gradinaru et al., 2010 |
| eArch3.0 | 520-550 nm | H+ pump (outward) | ~100-150 pA | 3-5 mW/mm2 | Green-light, fast recovery | pH changes, paradoxical presynaptic release | Chow et al., 2010; Mattis et al., 2012 |
| ArchT | 566 nm | H+ pump (outward) | ~200 pA | ~2 mW/mm2 | Higher sensitivity than Arch | Same pH concerns as eArch3.0 | Han et al., 2011 |
| eMac3.0 | 550 nm | H+ pump (outward) | ~80-120 pA | ~5 mW/mm2 | Alternative proton pump | Lower photocurrent | Chow et al., 2010; Mattis et al., 2012 |

### Anion Channels (High Conductance)

| Opsin | Lambda Peak | Mechanism | Photocurrent | EPD50 | Key Feature | Limitation | Citation |
|---|---|---|---|---|---|---|---|
| GtACR1 | 515 nm | Anion channel | ~500-1000 pA | ~0.02 mW/mm2 | Highest photocurrent inhibitory opsin | Axonal excitation (not soma-targeted) | Govorunova et al., 2015 |
| GtACR2 | 470 nm | Anion channel | ~600 pA | ~0.05 mW/mm2 | Blue-activated, high current | Axonal excitation, blue light heating | Govorunova et al., 2015 |
| stGtACR2 | 480 nm | Anion channel (soma-targeted) | ~500 pA | ~0.05 mW/mm2 | Most potent somatic inhibition | Requires blue light | Mahn et al., 2018 |
| iC++ | 480 nm | Engineered anion channel | ~200 pA | ~0.5 mW/mm2 | Improved Cl- selectivity | Lower current than GtACRs | Berndt et al., 2016 |
| ZipACR | 520 nm | Anion channel | ~300 pA | ~0.1 mW/mm2 | Fast kinetics for inhibition | Less characterized | Govorunova et al., 2017 |

### Usage Notes for Inhibitory Opsins

**stGtACR2 vs. eNpHR3.0**: stGtACR2 is 100-200x more light-sensitive than eNpHR3.0 (EPD50: 0.05 vs. 5-10 mW/mm2), produces 5-10x larger photocurrents, does not cause chloride loading, and does not have the same rebound excitation problem (Mahn et al., 2018). For new experiments, **stGtACR2 should be the default inhibitory opsin** unless:
- You need yellow/green light activation — use eNpHR3.0 or eArch3.0
- You need spectral separation from a blue-activated excitatory opsin — use eNpHR3.0

**Pump vs. channel inhibition**: Ion pumps (NpHR, Arch) transport one ion per photocycle, limiting their inhibitory capacity. Anion channels (GtACR, stGtACR2) open a pore, allowing many ions per channel opening and producing much larger currents. However, pumps can operate against the electrochemical gradient, while channels cannot (Wiegert et al., 2017).

**Antidromic activation warning**: Non-soma-targeted anion channelrhodopsins (GtACR1, GtACR2) expressed in axons can cause paradoxical excitation due to the high chloride concentration in axons, which makes chloride channel opening depolarizing rather than hyperpolarizing at axon terminals (Mahn et al., 2018). Always use **soma-targeted** variants (stGtACR2) when somatic inhibition is the goal.

**eNpHR3.0 time limit**: Continuous eNpHR3.0 activation should be limited to **<15 seconds** to avoid pathological chloride accumulation and GABA-A reversal potential shifts (Raimondo et al., 2012). For longer inhibition, use pulsed protocols (e.g., 5 s on / 2 s off) or switch to stGtACR2.

**eArch3.0 presynaptic caveat**: Sustained eArch3.0 activation at presynaptic terminals paradoxically increases spontaneous neurotransmitter release through pH-mediated mechanisms. This pH change, not hyperpolarization, mediates the primary synaptic silencing effect (Bhatt et al., 2015; El-Gaby et al., 2016). Use eArch3.0 primarily for somatic inhibition, not presynaptic silencing.

## Step-Function and Bistable Opsins

| Opsin | Activate | Deactivate | Tau-off (dark) | Type | Key Feature | Citation |
|---|---|---|---|---|---|---|
| SFO (C128S) | 470 nm | 590 nm | ~30 s | Excitatory | First step-function opsin | Berndt et al., 2009 |
| SSFO (C128S/D156A) | 470 nm | 590 nm | ~29 min | Excitatory | Ultra-stable, subthreshold depolarization | Yizhar et al., 2011 |
| SOUL | 470 nm | 590 nm | ~29 min | Excitatory | Ultra-sensitive SSFO, transcranial capable | Gong et al., 2020 |
| SwiChR++ | 480 nm | 600 nm | ~115 s | Inhibitory | Bistable Cl- channel | Berndt et al., 2016 |

### Usage Notes for Step-Function Opsins

**SSFO does NOT drive action potentials directly.** It produces subthreshold depolarization that increases the cell's sensitivity to endogenous synaptic inputs (Yizhar et al., 2011). This is fundamentally different from ChR2-driven spiking and is better suited for modulating excitability than for driving precise spike patterns.

**Activation protocol for SSFO**: A brief pulse (1-2 s) of blue light activates the channel; it remains open in the dark for ~29 minutes. A pulse of yellow light (~590 nm) immediately closes it. This allows experiments with minimal total light delivery and virtually no heating concern.

**SwiChR++ for sustained inhibition**: SwiChR++ can be activated by a brief blue pulse and remains in the inhibitory (chloride-conducting) state for ~115 s in the dark. Red light (600 nm) deactivates it within ~150 ms (Berndt et al., 2016). This is ideal for experiments requiring sustained inhibition without continuous illumination.

## References

- Berndt, A. et al. (2009). Bi-stable neural state switches. *Nat. Neurosci.*, 12, 229-234.
- Berndt, A. et al. (2016). Structural foundations of optogenetics: determinants of channelrhodopsin ion selectivity. *PNAS*, 113(4), 822-829.
- Boyden, E. S. et al. (2005). Millisecond-timescale, genetically targeted optical control of neural activity. *Nat. Neurosci.*, 8(9), 1263-1268.
- Chow, B. Y. et al. (2010). High-performance genetically targetable optical neural silencing. *Nature*, 463, 98-102.
- Gong, X. et al. (2020). An ultra-sensitive step-function opsin for minimally invasive optogenetic stimulation. *Neuron*, 107(1), 38-51.
- Govorunova, E. G. et al. (2015). Natural light-gated anion channels. *Science*, 349(6248), 647-650.
- Govorunova, E. G. et al. (2017). Extending the time domain of neuronal silencing with cryptophyte anion channelrhodopsins. *eNeuro*, 5(1), e0174-17.
- Gradinaru, V. et al. (2010). Molecular and cellular approaches for diversifying and extending optogenetics. *Cell*, 141(1), 154-165.
- Gunaydin, L. A. et al. (2010). Ultrafast optogenetic control. *Nat. Neurosci.*, 13(3), 387-392.
- Han, X. et al. (2011). A high-light sensitivity optical neural silencer. *Front. Syst. Neurosci.*, 5, 18.
- Hochbaum, D. R. et al. (2014). All-optical electrophysiology in mammalian neurons. *Nat. Methods*, 11, 825-833.
- Kishi, K. E. et al. (2022). Structural basis for channel conduction in the pump-like channelrhodopsin ChRmine. *Cell*, 185, 672-689.
- Klapoetke, N. C. et al. (2014). Independent optical excitation of distinct neural populations. *Nat. Methods*, 11, 338-346.
- Lin, J. Y. et al. (2009). Characterization of engineered channelrhodopsin variants with improved properties and kinetics. *Biophys. J.*, 96(5), 1803-1814.
- Lin, J. Y. et al. (2013). ReaChR: a red-shifted variant of channelrhodopsin enables deep transcranial optogenetic excitation. *Nat. Neurosci.*, 16, 1499-1508.
- Mahn, M. et al. (2018). High-efficiency optogenetic silencing with soma-targeted anion-conducting channelrhodopsins. *Nat. Commun.*, 9, 4125.
- Mardinly, A. R. et al. (2018). Precise multimodal optical control of neural ensemble activity. *Nat. Neurosci.*, 21, 881-893.
- Marshel, J. H. et al. (2019). Cortical layer-specific critical dynamics triggering perception. *Science*, 365(6453), eaaw5202.
- Mattis, J. et al. (2012). Principles for applying optogenetic tools. *Nat. Methods*, 9, 159-172.
- Nagel, G. et al. (2003). Channelrhodopsin-2, a directly light-gated cation-selective membrane channel. *PNAS*, 100(24), 13940-13945.
- Nagel, G. et al. (2005). Light activation of channelrhodopsin-2 in excitable cells of Caenorhabditis elegans. *Curr. Biol.*, 15(24), 2279-2284.
- Raimondo, J. V. et al. (2012). Optogenetic silencing strategies differ in their effects on inhibitory synaptic transmission. *Nat. Neurosci.*, 15, 1102-1104.
- Rajasethupathy, P. et al. (2015). Projections from neocortex mediate top-down control of memory retrieval. *Nature*, 526, 653-659.
- Wiegert, J. S. et al. (2017). Silencing neurons: tools, applications, and experimental constraints. *Neuron*, 95(3), 504-529.
- Yizhar, O. et al. (2011). Optogenetics in neural systems. *Neuron*, 71(1), 9-34.
