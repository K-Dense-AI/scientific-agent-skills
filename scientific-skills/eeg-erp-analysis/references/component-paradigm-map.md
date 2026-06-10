# Component-Paradigm Map

Detailed reference mapping each major ERP component to its canonical paradigm(s), key manipulations, critical design parameters, typical effect sizes, and minimum trial requirements. Use this file alongside the SKILL.md decision logic when selecting a paradigm for a target ERP component.

---

## 1. Early Visual Components

### P1 (Visual P1)

| Property | Details |
|---|---|
| **Latency** | **80--130 ms** post-stimulus (Luck, 2014, Ch. 3) |
| **Polarity / Distribution** | Positive, lateral occipital (O1, O2, PO7, PO8) |
| **Canonical paradigm** | Spatial attention (Posner cueing) with visual stimuli |
| **Key manipulation** | Compare ERPs to stimuli at attended vs. unattended locations; P1 is larger for attended-location stimuli (Hillyard et al., 1998) |
| **Typical effect size** | P1 attention effect: **~0.5--1.5 uV** difference (Hillyard et al., 1998; Di Russo et al., 2002) |
| **Minimum trials/condition** | **60--80** per attention condition (Luck, 2005) |
| **Critical parameters** | Stimulus eccentricity: **4--8 degrees** from fixation; stimulus duration: **50--200 ms**; ISI: **>= 1000 ms** to avoid sensory refractoriness (Luck, 2005) |
| **Control condition** | Unattended-location stimuli (same physical stimulus, different attentional state) |
| **Common confound** | Luminance/contrast differences between conditions produce P1 differences unrelated to attention (Luck, 2014, Ch. 2) |

---

### N1 (Visual N1)

| Property | Details |
|---|---|
| **Latency** | **150--200 ms** (posterior); **100--150 ms** (anterior subcomponent) (Luck, 2005; Vogel & Luck, 2000) |
| **Polarity / Distribution** | Negative, posterior (PO7, PO8) and anterior (FCz) subcomponents |
| **Canonical paradigm** | Discrimination tasks; also enhanced by spatial attention |
| **Key manipulation** | N1 is enhanced when a discrimination is required vs. simple detection (Vogel & Luck, 2000) |
| **Typical effect size** | Attention effect: **~1--2 uV** difference (Hillyard et al., 1998) |
| **Minimum trials/condition** | **60--80** (Luck, 2005) |
| **Critical parameters** | Stimulus must require perceptual discrimination; ISI: **>= 1000 ms** to avoid refractoriness; avoid stimuli at fixation (no lateralized P1/N1 at midline) |
| **Control condition** | Physically identical stimuli in detection-only task (no discrimination required) |
| **Common confound** | Multiple N1 subcomponents from different generators -- specify which N1 you are measuring (Luck, 2005) |

---

### N170

| Property | Details |
|---|---|
| **Latency** | **140--200 ms**, peak ~**170 ms** (Bentin et al., 1996; Rossion & Jacques, 2008) |
| **Polarity / Distribution** | Negative, bilateral occipitotemporal (P7/P8, PO7/PO8), often right-lateralized for faces |
| **Canonical paradigm** | Face perception: upright faces vs. non-face control objects |
| **Key manipulation** | Compare faces to matched control stimuli (scrambled faces, houses, objects); N170 is larger and earlier for faces (Bentin et al., 1996) |
| **Typical effect size** | Face vs. object: **~2--4 uV** difference; Cohen's d ~ **0.8--1.5** (Rossion & Jacques, 2008) |
| **Minimum trials/condition** | **40--60** per category (Rossion & Jacques, 2008); **>= 80** for individual differences (Jensen & MacDonald, 2023) |
| **Critical parameters** | Match luminance, spatial frequency, size, and contrast between face and control stimuli; use multiple exemplars (>= **40** per category) to avoid item-specific effects; present centrally; stimulus duration **200--500 ms**; ISI: **>= 1000 ms** |
| **Control condition** | Phase-scrambled faces (matched low-level features); inverted faces (face-inversion effect); or non-face objects matched on visual complexity |
| **Common confound** | Low-level visual differences between faces and objects (contrast, spatial frequency) produce P1/N1 differences that contaminate the N170 comparison (Rossion & Jacques, 2008) |

---

## 2. Attention Components

### N2pc

| Property | Details |
|---|---|
| **Latency** | **200--300 ms** (Luck & Hillyard, 1994; Eimer, 1996) |
| **Polarity / Distribution** | Negative, posterior contralateral to attended item (PO7/PO8) |
| **Canonical paradigm** | Lateralized visual search with bilateral displays |
| **Key manipulation** | Target appears in left or right hemifield; compute contralateral-minus-ipsilateral difference at PO7/PO8 (Luck, 2014, Ch. 3) |
| **Typical effect size** | **~0.5--1.5 uV** contralateral--ipsilateral difference; Cohen's d ~ **0.5--0.8** (Kappenman et al., 2021) |
| **Minimum trials/condition** | **100** per target side; recommend **150--200** (Luck, 2014, Ch. 3; Kappenman et al., 2021) |
| **Critical parameters** | **Bilateral display** required -- items on both sides of fixation to cancel sensory asymmetries; target must be defined by a feature that allows pop-out or efficient search; balance target side (50% left, 50% right); stimulus duration: **100--200 ms** to prevent saccades; ISI: **>= 1000 ms** (Luck & Hillyard, 1994; Eimer, 1996) |
| **Control condition** | Ipsilateral activity from the same trials serves as the built-in control (lateralization logic) |
| **Common confound** | (1) Horizontal eye movements toward the target create HEOG artifacts mimicking N2pc; enforce strict fixation and reject trials with HEOG > **+/- 16 uV** (Woodman & Luck, 2003). (2) Singleton distractors also elicit contralateral activity (Pd component) that can overlap with N2pc |

---

### P3a (Novelty P300)

| Property | Details |
|---|---|
| **Latency** | **250--350 ms** (Polich, 2007) |
| **Polarity / Distribution** | Positive, frontocentral (Fz, FCz, Cz) |
| **Canonical paradigm** | Three-stimulus oddball with novel distractors (e.g., environmental sounds among tones) |
| **Key manipulation** | Compare ERPs to novel stimuli vs. frequent standards; P3a is elicited by task-irrelevant novel/deviant stimuli (Polich, 2007) |
| **Typical effect size** | **~3--8 uV** for novels vs. standards; large effect (Polich, 2007) |
| **Minimum trials/condition** | **30--40** novel trials (Polich, 2007) |
| **Critical parameters** | Novel stimuli must be unique or highly varied (non-repeating environmental sounds); standard probability: **~70--80%**; target probability: **~10--15%**; novel probability: **~10--15%**; ISI: **1500--2500 ms** (Polich, 2007) |
| **Control condition** | Frequent standards (same modality, repeated) |
| **Common confound** | If novels repeat, habituation eliminates P3a; use a large pool of unique sounds (Polich, 2007) |

---

### P3b (Target P300)

| Property | Details |
|---|---|
| **Latency** | **300--600 ms** (Polich, 2007; Luck, 2014, Ch. 3) |
| **Polarity / Distribution** | Positive, centroparietal (Pz maximal) |
| **Canonical paradigm** | Two-stimulus oddball: rare targets among frequent standards |
| **Key manipulation** | Target probability **~15--20%** vs. standard probability **~80--85%**; P3b is larger for less probable task-relevant stimuli (Polich, 2007; Donchin & Coles, 1988) |
| **Typical effect size** | **~5--15 uV** target vs. standard difference; Cohen's d ~ **1.5--3.0** (very large) (Kappenman et al., 2021) |
| **Minimum trials/condition** | **30** target trials retained after artifact rejection (Luck, 2014, Ch. 9; Boudewyn et al., 2018) |
| **Critical parameters** | Target probability: **15--20%** (lower = larger P3b but fewer trials); ISI: **1200--2000 ms** (Polich, 2007); use simple stimuli (tones, letters) for robust effects; ensure targets require a response to maintain task relevance |
| **Control condition** | Frequent standards; optionally add rare non-targets (equiprobable control) to separate probability from task relevance |
| **Common confound** | (1) P3a overlap from novelty processing when targets are physically distinctive; (2) P3b amplitude varies with ISI -- longer ISIs produce larger P3b (Polich, 2007); (3) target probability and task relevance are confounded in two-stimulus oddball |

---

## 3. Language Components

### N400

| Property | Details |
|---|---|
| **Latency** | **300--500 ms** (Kutas & Hillyard, 1980; Kutas & Federmeier, 2011) |
| **Polarity / Distribution** | Negative, centroparietal (Cz, CPz, Pz) with slight rightward lateralization |
| **Canonical paradigm** | Sentence reading with semantic violations; or word-pair semantic priming |
| **Key manipulation** | Semantically incongruent vs. congruent sentence completions; N400 amplitude is inversely proportional to cloze probability (Kutas & Federmeier, 2011) |
| **Typical effect size** | **~3--6 uV** for strong violations; Cohen's d ~ **1.0--2.0** (Kutas & Federmeier, 2011; Kappenman et al., 2021) |
| **Minimum trials/condition** | **30--40** per condition (Boudewyn et al., 2018; Kappenman et al., 2021) |
| **Critical parameters** | Word duration: **~200--500 ms** for visual; ISI (word-to-word): **300--700 ms** for RSVP; sentence SOA: **500--800 ms**; epoch: **-200 to 800 ms**; use high-cloze items (> **80%** cloze probability) for congruent condition; low-cloze items (< **10%** cloze probability) for incongruent condition (Kutas & Federmeier, 2011) |
| **Control condition** | High-cloze (expected) sentence completions |
| **Common confound** | (1) Word frequency, length, and orthographic neighborhood differ between congruent and incongruent completions -- match these lexical properties; (2) P600 overlap in the same trials; (3) sentence position effects -- critical word should be at a consistent position (Kutas & Federmeier, 2011) |

---

### P600 / Late Positive Complex

| Property | Details |
|---|---|
| **Latency** | **500--800 ms**, can extend to **1000 ms** (Osterhout & Holcomb, 1992; Kuperberg, 2007) |
| **Polarity / Distribution** | Positive, centroparietal (Pz, CPz) |
| **Canonical paradigm** | Sentence reading with syntactic violations (agreement errors, phrase structure violations) |
| **Key manipulation** | Syntactically anomalous vs. correct sentences; P600 is larger for violations (Osterhout & Holcomb, 1992) |
| **Typical effect size** | **~2--5 uV** for clear violations; Cohen's d ~ **0.8--1.5** (Osterhout & Holcomb, 1992) |
| **Minimum trials/condition** | **30--40** per condition |
| **Critical parameters** | Same as N400 paradigm for presentation; epoch window must extend to **>= 1000 ms** post-stimulus; use clear syntactic violations (agreement in person/number, tense) with matched correct controls; avoid semantic plausibility confounds (Kuperberg, 2007) |
| **Control condition** | Grammatically correct matched sentences |
| **Common confound** | (1) N400 and P600 often co-occur; report both; (2) the P600/LPC overlaps with the parietal old/new effect from memory -- if the paradigm involves repetition, memory-related positivity may contaminate the P600 (Brouwer et al., 2017) |

---

## 4. Auditory / Mismatch Components

### MMN (Mismatch Negativity)

| Property | Details |
|---|---|
| **Latency** | **100--250 ms** after deviance onset (Naatanen et al., 2007) |
| **Polarity / Distribution** | Negative, frontocentral (Fz, FCz) with polarity reversal at mastoids |
| **Canonical paradigm** | Passive auditory oddball: frequent standards with rare deviants, no task required |
| **Key manipulation** | Physically deviant tones (frequency, duration, intensity, location) presented among repetitive standards; MMN = deviant-minus-standard difference wave (Naatanen et al., 2007) |
| **Typical effect size** | **~1--3 uV** in the difference wave; Cohen's d ~ **0.5--1.0** (Duncan et al., 2009) |
| **Minimum trials/condition** | **150--200** deviant trials retained; **>= 600--800** standards (Naatanen et al., 2007; Duncan et al., 2009) |
| **Critical parameters** | Deviant probability: **10--20%** (lower = larger MMN but fewer deviant trials; **10--15%** optimal; Naatanen et al., 2004); SOA: **300--600 ms** (shorter SOAs strengthen the memory trace, producing larger MMN; Naatanen et al., 2007); stimulus duration: **50--200 ms** for tones; use mastoid or nose reference (polarity inverts at mastoids); subjects do not respond to sounds (passive listening, often watching a silent movie) |
| **Control condition** | Standard tones; additionally, use a "many-standards" or "flip-flop" control where the deviant physical stimulus serves as a standard in a separate block, to rule out differential N1 refractoriness (Jacobsen & Schroger, 2001; Naatanen et al., 2004) |
| **Common confound** | (1) The N1 component is larger for deviants than standards due to refractoriness (standards are more frequent, so N1 habituates more); this sensory difference is not MMN. Use many-standards control to isolate the true memory-comparison MMN (Jacobsen & Schroger, 2001). (2) Attention allocation to deviants produces an overlapping N2b/P3a complex; ensure passive paradigm with distraction task |

---

### Optimum-1 Multi-Feature MMN Paradigm

| Property | Details |
|---|---|
| **Purpose** | Efficiently assess MMN to multiple deviant types in a single session (Naatanen et al., 2004) |
| **Design** | Standard tones alternate with deviants; every other tone is a standard, and the intervening tones are deviants varying in one of 5 features (frequency, duration, intensity, location, gap) |
| **Deviant probability** | Each deviant type: **~10%** of total; standards: **~50%** (Naatanen et al., 2004) |
| **Advantage** | Acquires 5 MMN subtypes in the time needed for 1 traditional oddball (Naatanen et al., 2004; Pakarinen et al., 2007) |
| **Validation** | MMN amplitudes from Optimum-1 are comparable to those from single-deviant paradigms (Naatanen et al., 2004) |

---

## 5. Executive Control / Motor Components

### ERN (Error-Related Negativity)

| Property | Details |
|---|---|
| **Latency** | **0--100 ms** post-response, peak ~**50--80 ms** (Gehring et al., 1993; Falkenstein et al., 1991) |
| **Polarity / Distribution** | Negative, frontocentral (FCz, Cz) |
| **Canonical paradigm** | Speeded response tasks that generate errors: Eriksen flanker, Go/No-Go, Stroop |
| **Key manipulation** | Compare response-locked ERPs on error vs. correct trials; ERN is a sharp negativity on error trials (Gehring et al., 1993) |
| **Typical effect size** | **~5--10 uV** error vs. correct difference; Cohen's d ~ **1.5--3.0** (very large) (Kappenman et al., 2021; Olvet & Hajcak, 2009) |
| **Minimum trials/condition** | **6--8** error trials for detection of the component; **10--15** for stable individual-difference measures (Olvet & Hajcak, 2009; Boudewyn et al., 2018) |
| **Critical parameters** | **Response-locked** epoching (-200 to 500 ms around response); error rate must be sufficient (**10--25%**); use speed-emphasis instructions ("respond as quickly as possible, errors are expected"); ISI: **>= 1000 ms**; flanker task is the standard ERP CORE paradigm (Kappenman et al., 2021) |
| **Control condition** | Correct-response trials from the same task |
| **Common confound** | (1) Post-error slowing changes the timing of subsequent stimuli, affecting stimulus-locked ERPs; (2) if error rate is too low, insufficient trials; if too high, the ERN habituates (Gehring et al., 1993). (3) The Pe (error positivity, 200--400 ms post-response) follows the ERN -- report both |

---

### LRP (Lateralized Readiness Potential)

| Property | Details |
|---|---|
| **Latency** | Sustained, begins **~200--500 ms** before response (response-locked) or **~200--400 ms** post-stimulus (stimulus-locked) (Coles et al., 1988; Eimer, 1998) |
| **Polarity / Distribution** | Negative over motor cortex contralateral to responding hand (C3/C4) |
| **Canonical paradigm** | Choice-RT task with lateralized (left vs. right hand) responses |
| **Key manipulation** | Compute double subtraction: [(C3 - C4) for right-hand trials + (C4 - C3) for left-hand trials] / 2; this isolates lateralized motor preparation from non-lateralized activity (Coles et al., 1988) |
| **Typical effect size** | **~1--3 uV** lateralization; Cohen's d ~ **0.5--1.0** (Boudewyn et al., 2018; Kappenman et al., 2021) |
| **Minimum trials/condition** | **40--50** per response hand; recommend **80--100** (Boudewyn et al., 2018; Kappenman et al., 2021) |
| **Critical parameters** | Equal numbers of left- and right-hand response trials; counterbalance stimulus-response mapping across participants; ISI: **>= 1500 ms**; both stimulus-locked (S-LRP, onset reflects stimulus-processing duration) and response-locked (LRP-R, onset reflects motor-preparation duration) waveforms are informative (Eimer, 1998) |
| **Control condition** | Built-in via the lateralization computation; non-lateralized activity cancels out |
| **Common confound** | (1) Unequal trial counts for left vs. right responses bias the LRP; (2) eye movements or head turns produce lateralized artifacts; (3) stimulus-response compatibility effects modulate LRP onset |

---

### CNV (Contingent Negative Variation)

| Property | Details |
|---|---|
| **Latency** | Sustained, from S1 (warning) to S2 (imperative), typically **1000--4000 ms** (Walter et al., 1964; Brunia et al., 2012) |
| **Polarity / Distribution** | Negative, frontocentral (Cz, FCz); early CNV: frontal; late CNV: central |
| **Canonical paradigm** | S1-S2 foreperiod paradigm: warning cue followed by an imperative stimulus requiring a response |
| **Key manipulation** | Vary foreperiod duration, temporal predictability, or motivational significance; CNV amplitude reflects preparatory state (Brunia et al., 2012) |
| **Typical effect size** | **~5--20 uV** sustained negativity (Walter et al., 1964; Brunia et al., 2012) |
| **Minimum trials/condition** | **30--40** per foreperiod condition (Brunia et al., 2012) |
| **Critical parameters** | S1-S2 interval: **1000--4000 ms** (1500 ms is standard to separate early/late CNV; shorter than 500 ms suppresses CNV); **variable foreperiods** across conditions to study temporal expectation; motor response to S2 required for robust CNV; **low high-pass filter** (<= **0.05 Hz**, ideally **0.01 Hz**) essential -- standard **0.1 Hz** cutoff attenuates the CNV (Tanner et al., 2015; Brunia et al., 2012) |
| **Control condition** | S1-only trials (no S2) to assess orienting response without preparation; or passive-viewing trials |
| **Common confound** | (1) The CNV contaminates the baseline of subsequent stimulus-locked ERPs if the ISI is fixed; use jittered ISIs; (2) eye blinks during the foreperiod are common and disrupt the slow wave; instruct participants to blink after S2 |

---

## 6. Frequency-Domain Components

### SSVEP (Steady-State Visual Evoked Potential)

| Property | Details |
|---|---|
| **Latency** | Steady-state; response is ongoing at the stimulus frequency and harmonics (Norcia et al., 2015) |
| **Polarity / Distribution** | Oscillatory, maximal at occipital sites (Oz, O1, O2) |
| **Canonical paradigm** | Frequency tagging: a visual stimulus flickers at a fixed rate; the EEG response at that frequency indexes processing of the tagged stimulus |
| **Key manipulation** | Modulate attention to the flickering stimulus; attended stimuli show larger SSVEP amplitude at the tagged frequency (Muller et al., 1998) |
| **Typical effect size** | Attention modulation: **~20--50%** amplitude increase for attended vs. unattended (Muller et al., 1998) |
| **Minimum trials/condition** | **10--20 blocks** of **10--20 s** each; frequency-domain analysis requires sufficient total duration rather than trial counts (Norcia et al., 2015) |
| **Critical parameters** | Flicker frequency: **~5--30 Hz**; strongest responses at **~10 Hz** (alpha resonance) and **~15 Hz** (Norcia et al., 2015); avoid **15--25 Hz** for photosensitive individuals (seizure risk; Fisher et al., 2005); for multi-stimulus tagging, use non-harmonically-related frequencies (e.g., **7.5 Hz** and **12 Hz**, not **8 Hz** and **16 Hz**) to prevent harmonic overlap; monitor refresh rate must be an integer multiple of the flicker frequency; duty cycle: **50%** (square wave) is standard |
| **Control condition** | Unattended stimulus flickering at a different frequency |
| **Common confound** | (1) Harmonics of one frequency can overlap with the fundamental of another frequency; (2) intermodulation frequencies (f1 + f2, f1 - f2) appear when two stimuli interact nonlinearly; (3) muscle artifacts contaminate higher frequencies |

---

## References

- Bentin, S., Allison, T., Puce, A., Perez, E., & McCarthy, G. (1996). Electrophysiological studies of face perception in humans. *JOCN*, 8(6), 551--565.
- Boudewyn, M. A., Luck, S. J., Farrens, J. L., & Kappenman, E. S. (2018). How many trials does it take to get a significant ERP effect? *Psychophysiology*, 55(6), e13049.
- Brouwer, H., et al. (2017). A neurocomputational model of the N400 and the P600 in language processing. *Cognitive Science*, 41, 1318--1352.
- Brunia, C. H. M., van Boxtel, G. J. M., & Bocker, K. B. E. (2012). Negative slow waves as indices of anticipation. In *The Oxford Handbook of ERP Components*.
- Coles, M. G. H., Gratton, G., & Donchin, E. (1988). Detecting early communication. *Biological Psychology*, 26, 69--89.
- Di Russo, F., et al. (2002). Cortical sources of the early components of the visual evoked potential. *Human Brain Mapping*, 15(2), 95--111.
- Donchin, E., & Coles, M. G. H. (1988). Is the P300 component a manifestation of context updating? *BBS*, 11(3), 357--374.
- Duncan, C. C., et al. (2009). Event-related potentials in clinical research: Guidelines. *Clinical Neurophysiology*, 120(11), 1883--1908.
- Eimer, M. (1996). The N2pc component as an indicator of attentional selectivity. *EEG and Clinical Neurophysiology*, 99(3), 225--234.
- Eimer, M. (1998). The lateralized readiness potential as an on-line measure of central response activation processes. *Behavior Research Methods*, 30(1), 146--156.
- Falkenstein, M., et al. (1991). Effects of crossmodal divided attention on late ERP components. *EEG and Clinical Neurophysiology*, 78(6), 447--455.
- Fisher, R. S., et al. (2005). Photic- and pattern-induced seizures: A review for the Epilepsy Foundation of America Working Group. *Epilepsia*, 46(9), 1426--1441.
- Gehring, W. J., et al. (1993). A neural system for error detection and compensation. *Psychological Science*, 4(6), 385--390.
- Hillyard, S. A., Vogel, E. K., & Luck, S. J. (1998). Sensory gain control as a mechanism of selective attention. *Phil. Trans. R. Soc. B*, 353(1373), 1257--1270.
- Jacobsen, T., & Schroger, E. (2001). Is there pre-attentive memory-based comparison of pitch? *Psychophysiology*, 38(4), 723--727.
- Jensen, K. M., & MacDonald, J. A. (2023). Towards thoughtful planning of ERP studies. *Psychophysiology*, 60(7), e14245.
- Kappenman, E. S., et al. (2021). ERP CORE: An open resource for human event-related potential research. *NeuroImage*, 225, 117465.
- Kuperberg, G. R. (2007). Neural mechanisms of language comprehension. *Brain Research*, 1146, 23--49.
- Kutas, M., & Federmeier, K. D. (2011). Thirty years and counting. *Annual Review of Psychology*, 62, 621--647.
- Kutas, M., & Hillyard, S. A. (1980). Reading senseless sentences. *Science*, 207(4427), 203--205.
- Luck, S. J. (2005). Ten simple rules for designing ERP experiments. In *Event-Related Potentials: A Methods Handbook*. MIT Press.
- Luck, S. J. (2014). *An Introduction to the Event-Related Potential Technique* (2nd ed.). MIT Press.
- Luck, S. J., & Hillyard, S. A. (1994). Spatial filtering during visual search. *JEP: HPP*, 20(5), 1000--1014.
- Muller, M. M., et al. (1998). Sustained division of the attentional spotlight. *Nature*, 424, 309--312.
- Naatanen, R., Pakarinen, S., Rinne, T., & Takegata, R. (2004). The mismatch negativity (MMN): Towards the optimal paradigm. *Clinical Neurophysiology*, 115(1), 140--144.
- Naatanen, R., Paavilainen, P., Rinne, T., & Alho, K. (2007). The mismatch negativity (MMN) in basic research of central auditory processing. *Clinical Neurophysiology*, 118(12), 2544--2590.
- Norcia, A. M., et al. (2015). The steady-state visual evoked potential in vision research: A review. *Journal of Vision*, 15(6), 4.
- Olvet, D. M., & Hajcak, G. (2009). The stability of error-related brain activity with increasing number of trials. *Psychophysiology*, 46(5), 957--961.
- Osterhout, L., & Holcomb, P. J. (1992). Event-related brain potentials elicited by syntactic anomaly. *JMLV*, 31(6), 785--806.
- Pakarinen, S., et al. (2007). Measurement of extensive auditory discrimination profiles using the MMN. *Clinical Neurophysiology*, 118(1), 177--185.
- Polich, J. (2007). Updating P300: An integrative theory of P3a and P3b. *Clinical Neurophysiology*, 118(10), 2128--2148.
- Rossion, B., & Jacques, C. (2008). Does physical interstimulus variance account for early electrophysiological face sensitive responses? *NeuroImage*, 39(4), 1959--1966.
- Tanner, D., et al. (2015). How inappropriate high-pass filters can produce artifactual effects. *Psychophysiology*, 52(8), 997--1009.
- Vogel, E. K., & Luck, S. J. (2000). The visual N1 component as an index of a discrimination process. *Psychophysiology*, 37(2), 190--203.
- Walter, W. G., et al. (1964). Contingent negative variation. *Nature*, 203(4943), 380--384.
- Woodman, G. F., & Luck, S. J. (2003). Serial deployment of attention during visual search. *JEP: HPP*, 29(1), 121--138.
