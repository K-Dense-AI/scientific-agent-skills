# Effect Size Lookup Tables for Neuroimaging

## Overview

This reference provides empirically derived effect size benchmarks for common neuroimaging paradigms, organized by analysis type. These values can be used as starting points for power analysis when pilot data are unavailable.

**Important caveat**: Published effect sizes are likely inflated due to publication bias and the "winner's curse" (Button et al., 2013). When using these values for power analysis, consider using 50-75% of the reported effect as a more realistic estimate.

## fMRI Task Activation Effect Sizes

### Sensory and Motor Paradigms

| Paradigm | Region | Typical d | Typical % Signal Change | Source |
|---|---|---|---|---|
| Visual checkerboard | V1 | 1.5-3.0 | 2-5% | Poldrack et al., 2017 |
| Finger tapping | M1 | 1.0-2.5 | 1-3% | Poldrack et al., 2017 |
| Auditory tone | A1 | 0.8-2.0 | 0.5-2% | Poldrack et al., 2017 |
| Face viewing | FFA | 0.8-1.5 | 0.5-1.5% | Kanwisher et al., 1997 |

### Cognitive Paradigms

| Paradigm | Typical Region | Typical d | Source |
|---|---|---|---|
| Working memory (n-back) | dlPFC, parietal | 0.5-1.0 | Owen et al., 2005 |
| Stroop interference | ACC, dlPFC | 0.4-0.8 | Nee et al., 2007 |
| Episodic memory encoding | MTL, PFC | 0.3-0.8 | Kim, 2011 |
| Language (semantic) | Left temporal, IFG | 0.5-1.0 | Binder et al., 2009 |
| Emotion (faces > shapes) | Amygdala | 0.3-0.7 | Hariri et al., 2002 |

### Between-Group Differences

| Comparison | Typical d | Sample Needed (80% power, corrected) | Source |
|---|---|---|---|
| Patient vs. control (task activation) | 0.5-0.8 | 25-50 per group | Poldrack et al., 2017 |
| Patient vs. control (resting connectivity) | 0.3-0.6 | 40-80 per group | Marek et al., 2022 |
| Age group differences | 0.3-0.7 | 30-60 per group | Grady, 2012 |
| Sex differences (task) | 0.2-0.5 | 50-100+ per group | Poldrack et al., 2017 |

## ERP Effect Sizes

### Classic ERP Components

| Component | Paradigm | Typical d (within-subject) | Typical Amplitude | Minimum Trials | Source |
|---|---|---|---|---|---|
| P300 (P3b) | Oddball | 0.8-1.5 | 5-15 uV | 20 | Luck, 2014 |
| N400 | Semantic violation | 0.5-1.0 | 2-5 uV | 30 | Kutas & Federmeier, 2011 |
| N170 | Face vs. object | 0.5-1.0 | 3-8 uV | 30 | Rossion & Jacques, 2008 |
| MMN | Auditory deviant | 0.4-0.8 | 1-3 uV | 100+ deviants | Naatanen et al., 2007 |
| ERN | Error vs. correct | 0.5-1.0 | 3-10 uV | 6+ errors minimum | Olvet & Hajcak, 2009 |
| LPP | Emotional vs. neutral | 0.3-0.7 | 2-5 uV | 30 | Hajcak et al., 2010 |
| N2pc | Attention lateralization | 0.4-0.8 | 1-3 uV | 200+ | Luck, 2012 |

### Between-Group ERP Effects

| Comparison | Component | Typical d | N Needed (80% power) | Source |
|---|---|---|---|---|
| Anxiety vs. control | ERN | 0.4-0.6 | 35-50 per group | Olvet & Hajcak, 2009 |
| Depression vs. control | P300 | 0.3-0.5 | 50-80 per group | Luck, 2014 |
| Young vs. elderly | N400 | 0.4-0.7 | 30-50 per group | Kutas & Federmeier, 2011 |

## EEG Oscillatory Effect Sizes

| Measure | Typical d | Typical N | Source |
|---|---|---|---|
| Alpha power (eyes closed vs. open) | 1.0-2.0 | 10-15 | Cohen, 2014 |
| Alpha lateralization (attention task) | 0.3-0.6 | 25-40 | Cohen, 2014 |
| Theta power (WM load) | 0.4-0.8 | 20-35 | Cohen, 2014 |
| Gamma power (perceptual binding) | 0.2-0.5 | 30-60 | Cohen, 2014 |
| Phase-amplitude coupling | 0.3-0.6 | 25-40 | Cohen, 2014 |

## Correction for Publication Bias

Published effect sizes are inflated because:
1. Studies with larger effects are more likely to be published
2. Small studies that find significant effects necessarily have inflated effect sizes ("winner's curse")
3. Analytic flexibility (researcher degrees of freedom) inflates reported effects

**Correction heuristic** (Button et al., 2013):
- For well-replicated effects (meta-analyses with many studies): use **75%** of the meta-analytic estimate
- For single-study effects: use **50%** of the reported effect
- For very small studies (N < 20): use **40%** of the reported effect

## References

- Binder, J. R., Desai, R. H., Graves, W. W., & Conant, L. L. (2009). Where is the semantic system? *Cerebral Cortex*, 19(12), 2767-2796.
- Button, K. S., Ioannidis, J. P. A., Mokrysz, C., et al. (2013). Power failure. *Nature Reviews Neuroscience*, 14(5), 365-376.
- Cohen, M. X. (2014). *Analyzing Neural Time Series Data*. MIT Press.
- Grady, C. (2012). The cognitive neuroscience of ageing. *Nature Reviews Neuroscience*, 13, 491-505.
- Hajcak, G., MacNamara, A., & Olvet, D. M. (2010). Event-related potentials, emotion, and emotion regulation. *Journal of Abnormal Psychology*, 119(1), 126-135.
- Hariri, A. R., Tessitore, A., Mattay, V. S., et al. (2002). The amygdala response to emotional stimuli. *NeuroImage*, 17(1), 317-323.
- Kanwisher, N., McDermott, J., & Chun, M. M. (1997). The fusiform face area. *Journal of Neuroscience*, 17(11), 4302-4311.
- Kim, H. (2011). Neural activity that predicts subsequent memory and forgetting. *NeuroImage*, 54(3), 2446-2461.
- Kutas, M., & Federmeier, K. D. (2011). Thirty years and counting: Finding meaning in the N400 component. *Annual Review of Psychology*, 62, 621-647.
- Luck, S. J. (2012). Electrophysiological correlates of the focusing of attention within complex visual scenes. In *Cognitive Electrophysiology of Attention*, 329-346.
- Luck, S. J. (2014). *An Introduction to the Event-Related Potential Technique* (2nd ed.). MIT Press.
- Marek, S., Tervo-Clemmens, B., Calabro, F. J., et al. (2022). Reproducible brain-wide association studies require thousands of individuals. *Nature*, 603(7902), 654-660.
- Naatanen, R., Paavilainen, P., Rinne, T., & Alho, K. (2007). The mismatch negativity (MMN) in basic research of central auditory processing. *Clinical Neurophysiology*, 118(12), 2544-2590.
- Nee, D. E., Wager, T. D., & Jonides, J. (2007). Interference resolution: Insights from a meta-analysis of neuroimaging tasks. *Cognitive, Affective, & Behavioral Neuroscience*, 7(1), 1-17.
- Olvet, D. M., & Hajcak, G. (2009). The stability of error-related brain activity with increasing number of trials. *Psychophysiology*, 46(5), 957-961.
- Owen, A. M., McMillan, K. M., Laird, A. R., & Bullmore, E. (2005). N-back working memory paradigm: A meta-analysis. *Human Brain Mapping*, 25(1), 46-59.
- Poldrack, R. A., Baker, C. I., Durnez, J., et al. (2017). Scanning the horizon. *Nature Reviews Neuroscience*, 18(2), 115-126.
- Rossion, B., & Jacques, C. (2008). Does physical interstimulus variance account for early electrophysiological face sensitive responses? *NeuroImage*, 39(3), 1694-1703.
