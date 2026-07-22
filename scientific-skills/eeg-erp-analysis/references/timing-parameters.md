# Timing Parameters for EEG Paradigm Design

Detailed reference for stimulus timing, epoch windows, baseline durations, jittering, block structure, and habituation management across ERP paradigm types. All numerical parameters include citations.

---

## 1. SOA and ISI Ranges by Paradigm Type

The stimulus onset asynchrony (SOA) is the time from the onset of one stimulus to the onset of the next. The inter-stimulus interval (ISI) is the time from the offset of one stimulus to the onset of the next (ISI = SOA - stimulus duration). In EEG, the SOA is the more critical parameter because ERPs are time-locked to stimulus onset.

### General Principles

- **Minimum SOA to avoid ERP overlap**: The SOA must exceed the duration of the slowest ERP component of interest. Since late components (P3b, N400, P600) can extend to **800--1000 ms**, SOAs under **~1200 ms** risk ERP overlap for these components (Luck, 2014, Ch. 6; Woldorff, 1993).
- **Maximum practical SOA**: SOAs above **~4000 ms** reduce trial throughput without proportional SNR benefit. For most paradigms, **1500--2500 ms** is the efficient range (Luck, 2014, Ch. 6).

### SOA/ISI by Paradigm Type

| Paradigm Type | Recommended SOA | ISI (with typical stim duration) | Source |
|---|---|---|---|
| **Auditory oddball (P3b)** | **1200--2000 ms** | 1000--1800 ms | Polich, 2007; Duncan et al., 2009 |
| **Auditory oddball (MMN)** | **300--600 ms** | 200--500 ms | Naatanen et al., 2007; shorter SOAs strengthen memory trace |
| **Visual oddball (P3b)** | **1200--2000 ms** | 900--1700 ms | Polich, 2007 |
| **Semantic sentence (N400/P600)** | **500--800 ms** (word-to-word in RSVP) | 200--500 ms | Kutas & Federmeier, 2011 |
| **Word-pair priming (N400)** | **800--1200 ms** (prime-to-target) | 500--900 ms | Kutas & Federmeier, 2011 |
| **Visual search (N2pc)** | **1000--1500 ms** (display-to-display) | 700--1200 ms | Luck, 2014, Ch. 3 |
| **Spatial attention (P1/N1)** | **1000--2000 ms** | 800--1800 ms | Luck, 2005; Hillyard et al., 1998 |
| **Face perception (N170)** | **1000--1500 ms** | 700--1200 ms | Rossion & Jacques, 2008 |
| **Flanker task (ERN)** | **1200--2000 ms** (trial-to-trial) | 800--1500 ms | Kappenman et al., 2021 |
| **Go/No-Go (N2, P3)** | **1000--2000 ms** | 700--1500 ms | Falkenstein et al., 1999; Wessel, 2018 |
| **S1-S2 foreperiod (CNV)** | **1000--4000 ms** (S1-to-S2) | N/A (defined by foreperiod) | Brunia et al., 2012; Walter et al., 1964 |
| **SSVEP (frequency tagging)** | Continuous (block-based) | N/A (steady-state) | Norcia et al., 2015 |

### Special Case: Fast Presentation Paradigms

Some paradigms require rapid presentation rates that cause ERP overlap:

| Paradigm | Presentation Rate | Overlap Management | Source |
|---|---|---|---|
| **RSVP (sentence reading)** | **300--700 ms** per word | Accept overlap; focus on N400/P600 in difference wave (which cancels shared overlap) | Kutas & Federmeier, 2011 |
| **MMN oddball** | **300--600 ms** SOA | N1 overlap is inherent; use difference wave (deviant - standard) to isolate MMN from sensory overlap | Naatanen et al., 2007 |
| **Rapid visual search** | **200--500 ms** per display | Use regression-based overlap correction (unfold toolbox; Ehinger & Dimigen, 2019) | Luck, 2014, Ch. 6 |
| **Attentional blink (RSVP)** | **~100 ms** per item | Overlap is the phenomenon of interest; analyze T2-locked ERPs conditioned on T1 accuracy | Raymond et al., 1992 |

---

## 2. Jittering Requirements

### Why Jitter Is Essential for EEG

1. **CNV contamination**: Fixed ISIs allow participants to predict stimulus onset, generating a CNV (slow negative wave) that contaminates the pre-stimulus baseline (Luck, 2014, Ch. 6).
2. **Overlap correction**: Regression-based deconvolution methods (e.g., unfold, LIMO) require variable SOAs to separate overlapping ERPs mathematically (Ehinger & Dimigen, 2019).
3. **Habituation mitigation**: Temporal predictability increases habituation of early sensory components (P1, N1), reducing sensitivity to experimental effects (Luck, 2005).

### Recommended Jitter Parameters

| Parameter | Recommendation | Source |
|---|---|---|
| **Jitter distribution** | Uniform or truncated exponential | Luck, 2014, Ch. 6 |
| **Jitter range (uniform)** | Mean ISI +/- **200--500 ms** | Luck, 2014, Ch. 6 |
| **Exponential distribution** | Mean = 500 ms, min = 200 ms, max = 1500 ms (prevents very long gaps) | Woldorff, 1993 |
| **Minimum ISI with jitter** | **>= 500 ms** even at the short end of the jitter range | Luck, 2014, Ch. 6 |

### Jitter Configuration by Paradigm

| Paradigm | Base ISI | Jitter | Resulting ISI Range | Source |
|---|---|---|---|---|
| Oddball (P3b) | 1500 ms | +/- 300 ms uniform | 1200--1800 ms | Polich, 2007 |
| Semantic (N400) | 700 ms word-to-word | +/- 100 ms | 600--800 ms | Kutas & Federmeier, 2011 |
| Visual search (N2pc) | 1200 ms | +/- 300 ms uniform | 900--1500 ms | Luck, 2014, Ch. 3 |
| Flanker (ERN) | 1500 ms | +/- 300 ms uniform | 1200--1800 ms | Kappenman et al., 2021 |
| Face perception (N170) | 1200 ms | +/- 200 ms uniform | 1000--1400 ms | Rossion & Jacques, 2008 |
| MMN | 500 ms | Typically fixed (jitter unnecessary for passive MMN due to short SOA) | ~500 ms | Naatanen et al., 2007 |

---

## 3. Epoch Windows

The epoch window defines the time segment extracted around each event for ERP analysis. It must include sufficient pre-stimulus time for baseline correction and sufficient post-stimulus time to capture the component of interest.

### Epoch Windows by Component

| Component | Epoch Window | Baseline Window | Rationale | Source |
|---|---|---|---|---|
| **P1 / N1** | **-200 to 500 ms** | -200 to 0 ms | Component resolves by ~250 ms; 500 ms captures any late effects | Luck, 2014, Ch. 5 |
| **N170** | **-200 to 500 ms** | -200 to 0 ms | Peak at 170 ms; include N250r if studying repetition effects | Rossion & Jacques, 2008 |
| **MMN** | **-100 to 400 ms** | -100 to 0 ms | Component peaks 100--250 ms; shorter baseline adequate for auditory paradigms with short SOA | Naatanen et al., 2007; Duncan et al., 2009 |
| **N2pc** | **-200 to 500 ms** | -200 to 0 ms | Component at 200--300 ms; include post-N2pc window for SPCN/CDA if studying VWM | Luck, 2014, Ch. 3 |
| **P3a** | **-200 to 800 ms** | -200 to 0 ms | Component at 250--350 ms; extend for late slow-wave analysis | Polich, 2007 |
| **P3b** | **-200 to 1000 ms** | -200 to 0 ms | P3b can extend to 600+ ms; 1000 ms captures the full component | Luck, 2014, Ch. 5; Polich, 2007 |
| **N400** | **-200 to 800 ms** | -200 to 0 ms | Component at 300--500 ms; extend to 800 ms to capture late positivities | Kutas & Federmeier, 2011 |
| **P600** | **-200 to 1200 ms** | -200 to 0 ms | Component extends to 800--1000 ms; extra buffer for late effects | Osterhout & Holcomb, 1992 |
| **ERN** | **-200 to 500 ms** (response-locked) | -200 to -50 ms pre-response | Response-locked; avoid including the response itself in baseline | Gehring et al., 1993; Kappenman et al., 2021 |
| **LRP (stimulus-locked)** | **-200 to 1000 ms** | -200 to 0 ms | Onset timing varies; extend to capture the full LRP and response | Coles et al., 1988 |
| **LRP (response-locked)** | **-600 to 200 ms** | -600 to -400 ms | Pre-response baseline; LRP onset typically 200--500 ms pre-response | Coles et al., 1988; Eimer, 1998 |
| **CNV** | **-200 to S2 + 500 ms** | Pre-S1: -200 to 0 ms | Must capture entire S1-S2 interval; use pre-S1 baseline | Brunia et al., 2012 |
| **SSVEP** | Block-based (10--60 s) | First 1--2 s of block (onset transient) | Frequency-domain analysis on steady-state portion | Norcia et al., 2015 |

### Baseline Duration Guidelines

| Baseline Duration | When to Use | Source |
|---|---|---|
| **-200 to 0 ms** | Default for most stimulus-locked ERPs | Luck, 2014, Ch. 5 |
| **-500 to -200 ms** | When early post-stimulus activity (P1) may be affected by pre-stimulus differences | Luck, 2014, Ch. 5 |
| **-100 to 0 ms** | Short epochs (MMN with rapid SOA) where -200 ms would overlap with the previous trial's ERP | Duncan et al., 2009 |
| **-200 to -50 ms** | Response-locked (ERN); avoids including the response in the baseline | Kappenman et al., 2021 |
| **Pre-cue baseline** | When a cue precedes the target and cue-related activity contaminates the standard baseline | Luck, 2014, Ch. 6 |

---

## 4. Block and Rest Structure

### Why Block Structure Matters for EEG

1. **Impedance drift**: Electrode impedances increase over time, degrading signal quality. Breaks allow repositioning and impedance checks.
2. **Alpha power increase**: Sustained recording increases drowsiness-related alpha, reducing ERPs to stimuli (Luck, 2014, Ch. 6).
3. **Muscle artifact accumulation**: Sustained posture increases neck and facial muscle tension.
4. **Blink suppression fatigue**: Participants instructed to minimize blinks eventually cannot comply; breaks reset this.

### Recommended Block Structure

| Parameter | Recommendation | Source |
|---|---|---|
| **Block duration** | **3--5 min** of active recording per block | Luck, 2014, Ch. 6 |
| **Rest breaks** | **1--2 min** between blocks; encourage blinking and relaxation | Luck, 2014, Ch. 6; Keil et al., 2014 |
| **Impedance check interval** | Every **15--20 min** (every 4--5 blocks) | Keil et al., 2014 |
| **Total session duration** | **60--90 min** maximum EEG recording (excluding cap setup) | Keil et al., 2014 |
| **Trials per block** | **30--60** trials depending on ISI | Calculated from block duration / SOA |
| **Number of blocks** | Depends on total trial count; typically **8--16** blocks | Varies by paradigm |

### Block Structure by Paradigm Type

| Paradigm | Trials/Block | Blocks | Total Duration | Source |
|---|---|---|---|---|
| Oddball (P3b, 20% targets) | ~60 total (~12 targets) | 12--16 | ~30--40 min | Polich, 2007 |
| MMN (10% deviants, 500 ms SOA) | ~200 total (~20 deviants) | 8--12 | ~15--25 min | Naatanen et al., 2007 |
| Visual search (N2pc) | ~50 | 12--16 | ~25--35 min | Luck, 2014, Ch. 3 |
| Sentence reading (N400) | ~20--30 sentences | 8--12 | ~25--35 min | Kutas & Federmeier, 2011 |
| Flanker (ERN) | ~50 | 8--12 | ~20--30 min | Kappenman et al., 2021 |
| Face perception (N170) | ~60 | 8--12 | ~20--30 min | Rossion & Jacques, 2008 |
| SSVEP (frequency tagging) | 5--10 blocks of 15--30 s | 5--10 per condition | ~15--20 min | Norcia et al., 2015 |

---

## 5. Habituation Management

### The Problem

Repeated stimulus presentation produces neural adaptation (habituation), which reduces the amplitude of sensory ERPs (P1, N1, N170) and the MMN over time. Habituation is stronger for:
- Shorter ISIs (< **500 ms**; Naatanen et al., 2007)
- Physically identical stimuli (vs. varied exemplars; Luck, 2005)
- Longer blocks without breaks (Luck, 2014, Ch. 6)

### Strategies to Manage Habituation

| Strategy | Implementation | Effect | Source |
|---|---|---|---|
| **Sufficient ISI** | Maintain ISI >= **1000 ms** for P1/N1 paradigms | Reduces sensory refractoriness | Luck, 2005; Coles & Rugg, 1995 |
| **Stimulus variety** | Use multiple exemplars within each category (>= **40** faces, >= **40** control objects for N170) | Reduces repetition suppression | Rossion & Jacques, 2008 |
| **Jittered ISI** | Vary ISI +/- **200--500 ms** | Prevents rhythmic entrainment and anticipatory adaptation | Luck, 2014, Ch. 6 |
| **Short blocks with breaks** | **3--5 min** blocks, **1--2 min** rest | Resets arousal and attention | Luck, 2014, Ch. 6 |
| **Randomized stimulus order** | Pseudorandomize with constraints (no > 3 same-condition trials in a row) | Prevents local adaptation effects | Luck, 2014, Ch. 6 |
| **Discard initial trials** | Exclude first **2--5 trials** of each block from analysis | Removes orienting response to block onset | Expert consensus |
| **Balanced stimulus ordering** | Ensure equal transition probabilities between conditions across the experiment | Prevents sequence-dependent habituation patterns | Luck, 2014, Ch. 6 |

### Habituation Sensitivity by Component

| Component | Habituation Sensitivity | ISI Requirement | Source |
|---|---|---|---|
| P1 | High | >= **1000 ms** | Luck, 2005 |
| N1 | High | >= **1000 ms** | Luck, 2005; Naatanen et al., 2007 |
| N170 | Moderate | >= **1000 ms**; use varied exemplars | Rossion & Jacques, 2008 |
| MMN | Low (memory-trace based) | **300--600 ms** SOA is fine; shorter strengthens trace | Naatanen et al., 2007 |
| P3a | High (to novelty) | Use unique stimuli; avoid repetition | Polich, 2007 |
| P3b | Low--Moderate | >= **1200 ms** | Polich, 2007 |
| N400 | Low | Standard RSVP rates (500--800 ms SOA) are fine | Kutas & Federmeier, 2011 |
| ERN | Low | Response-locked; ISI effect minimal | Gehring et al., 1993 |
| SSVEP | Low (sustained entrainment) | Block-based; discard first 1--2 s | Norcia et al., 2015 |

---

## 6. Timing Constraints for Special Populations

When designing EEG paradigms for populations other than healthy young adults, adjust timing parameters:

| Population | Timing Adjustments | Rationale | Source |
|---|---|---|---|
| **Children (< 12 yr)** | Increase ISI by **200--500 ms**; shorten blocks to **2--3 min**; increase rest breaks; reduce total trials by **30--40%** | Shorter attention spans; more movement artifacts; ERP latencies delayed ~**50--100 ms** | DeBoer et al., 2007 |
| **Older adults (> 65 yr)** | Increase ISI by **200--500 ms**; extend response deadlines by **200--500 ms**; increase break frequency | Slower processing speed; P3 latency delayed ~**50--100 ms** (Polich, 1997); higher artifact rates | Polich, 1997; Friedman, 2012 |
| **Clinical populations** | Shorten total session to **<= 45 min**; simplify task; increase ISI; consider passive paradigms (MMN) | Fatigue, medication effects, reduced compliance | Duncan et al., 2009 |
| **Infants** | ISI: **1000--2000 ms**; block duration: **1--2 min**; expect **50--70%** data loss from artifacts; need **>= 200%** more trials than adults | High artifact rates from movement; short usable windows | DeBoer et al., 2007 |

---

## 7. Summary Decision Table

Quick reference for timing parameters by target ERP component:

| Component | SOA (ms) | Jitter (ms) | Epoch (ms) | Baseline (ms) | Min Trials | Block (min) |
|---|---|---|---|---|---|---|
| P1 | 1000--2000 | +/-300 | -200 to 500 | -200 to 0 | 60--80 | 3--5 |
| N1 | 1000--2000 | +/-300 | -200 to 500 | -200 to 0 | 60--80 | 3--5 |
| N170 | 1000--1500 | +/-200 | -200 to 500 | -200 to 0 | 40--60 | 3--5 |
| MMN | 300--600 | Fixed | -100 to 400 | -100 to 0 | 150--200 dev | 3--5 |
| N2pc | 1000--1500 | +/-300 | -200 to 500 | -200 to 0 | 100--200 | 3--5 |
| P3a | 1500--2500 | +/-300 | -200 to 800 | -200 to 0 | 30--40 | 3--5 |
| P3b | 1200--2000 | +/-300 | -200 to 1000 | -200 to 0 | 30--50 | 3--5 |
| N400 | 500--800 (word) | +/-100 | -200 to 800 | -200 to 0 | 30--40 | 3--5 |
| P600 | 500--800 (word) | +/-100 | -200 to 1200 | -200 to 0 | 30--40 | 3--5 |
| ERN | 1200--2000 (trial) | +/-300 | -200 to 500 resp | -200 to -50 resp | 6--15 err | 3--5 |
| LRP | 1500--2000 | +/-300 | -200 to 1000 (S) | -200 to 0 (S) | 40--50/hand | 3--5 |
| CNV | 1000--4000 (S1-S2) | Varies | -200 to S2+500 | -200 to 0 (pre-S1) | 30--40 | 3--5 |
| SSVEP | Continuous | N/A | 10--60 s blocks | First 1--2 s | 10--20 blocks | 15--30 s |

---

## References

- Brunia, C. H. M., van Boxtel, G. J. M., & Bocker, K. B. E. (2012). Negative slow waves as indices of anticipation. In *The Oxford Handbook of ERP Components*.
- Coles, M. G. H., Gratton, G., & Donchin, E. (1988). Detecting early communication. *Biological Psychology*, 26, 69--89.
- Coles, M. G. H., & Rugg, M. D. (1995). Event-related brain potentials: An introduction. In *Electrophysiology of Mind*. Oxford University Press.
- DeBoer, T., Scott, L. S., & Nelson, C. A. (2007). Methods for acquiring and analyzing infant event-related potentials. In M. de Haan (Ed.), *Infant EEG and Event-Related Potentials*. Psychology Press.
- Duncan, C. C., et al. (2009). Event-related potentials in clinical research: Guidelines. *Clinical Neurophysiology*, 120(11), 1883--1908.
- Ehinger, B. V., & Dimigen, O. (2019). Unfold: An integrated toolbox for overlap correction. *PeerJ*, 7, e7838.
- Eimer, M. (1998). The lateralized readiness potential as an on-line measure. *Behavior Research Methods*, 30(1), 146--156.
- Falkenstein, M., Hoormann, J., & Hohnsbein, J. (1999). ERP components in Go/Nogo tasks and their relation to inhibition. *Acta Psychologica*, 101(2--3), 267--291.
- Friedman, D. (2012). The components of aging. In *The Oxford Handbook of ERP Components*. Oxford University Press.
- Gehring, W. J., et al. (1993). A neural system for error detection and compensation. *Psychological Science*, 4(6), 385--390.
- Hillyard, S. A., Vogel, E. K., & Luck, S. J. (1998). Sensory gain control. *Phil. Trans. R. Soc. B*, 353(1373), 1257--1270.
- Kappenman, E. S., et al. (2021). ERP CORE: An open resource. *NeuroImage*, 225, 117465.
- Keil, A., et al. (2014). Committee report: Publication guidelines for EEG and MEG. *Psychophysiology*, 51(1), 1--21.
- Kutas, M., & Federmeier, K. D. (2011). Thirty years and counting. *Annual Review of Psychology*, 62, 621--647.
- Luck, S. J. (2005). Ten simple rules for designing ERP experiments. In *Event-Related Potentials: A Methods Handbook*. MIT Press.
- Luck, S. J. (2014). *An Introduction to the Event-Related Potential Technique* (2nd ed.). MIT Press.
- Naatanen, R., et al. (2004). The mismatch negativity (MMN): Towards the optimal paradigm. *Clinical Neurophysiology*, 115(1), 140--144.
- Naatanen, R., et al. (2007). The mismatch negativity (MMN) in basic research. *Clinical Neurophysiology*, 118(12), 2544--2590.
- Norcia, A. M., et al. (2015). The steady-state visual evoked potential in vision research: A review. *Journal of Vision*, 15(6), 4.
- Osterhout, L., & Holcomb, P. J. (1992). Event-related brain potentials elicited by syntactic anomaly. *JMLV*, 31(6), 785--806.
- Polich, J. (1997). EEG and ERP assessment of normal aging. *EEG and Clinical Neurophysiology*, 104(3), 244--256.
- Polich, J. (2007). Updating P300. *Clinical Neurophysiology*, 118(10), 2128--2148.
- Raymond, J. E., Shapiro, K. L., & Arnell, K. M. (1992). Temporary suppression of visual processing in an RSVP task. *JEP: HPP*, 18(3), 849--860.
- Rossion, B., & Jacques, C. (2008). Does physical interstimulus variance account for early electrophysiological face sensitive responses? *NeuroImage*, 39(4), 1959--1966.
- Walter, W. G., et al. (1964). Contingent negative variation. *Nature*, 203(4943), 380--384.
- Wessel, J. R. (2018). Prepotent motor activity and inhibitory control demands in different variants of the go/no-go paradigm. *Psychophysiology*, 55(3), e12871.
- Woldorff, M. G. (1993). Distortion of ERP averages due to overlap from temporally adjacent ERPs. *Psychophysiology*, 30(1), 98--119.
