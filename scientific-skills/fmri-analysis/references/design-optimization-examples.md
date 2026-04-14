# Design Optimization Examples

## Overview

This reference provides worked examples of fMRI design optimization, expanding on the design efficiency concepts in `../SKILL.md`.

## Example 1: Block Design for Visual Localizer

**Goal**: Localize face-selective regions (fusiform face area).

**Design specification**:
- Conditions: Faces, Objects, Scrambled, Fixation
- Block duration: **16 seconds** (Kanwisher et al., 1997)
- Blocks per condition per run: **6**
- Rest between blocks: **12 seconds** (fixation cross)
- Run duration: 6 blocks x 4 conditions x (16 + 12) s = **672 seconds** (~11.2 minutes)
- Number of runs: **2** for replication

**Contrast**: Faces > Objects (isolates face-selective response while controlling for visual stimulation)

**Why this works**: Block design maximizes detection power for the categorical contrast. The 16-second block duration is near the optimal range of 15-20 seconds (Maus et al., 2010). Six blocks per condition provide sufficient repetitions for stable parameter estimates.

## Example 2: Rapid Event-Related Design for Memory Encoding

**Goal**: Identify neural correlates of successful memory encoding (subsequent memory paradigm).

**Design specification**:
- Conditions: Subsequently Remembered, Subsequently Forgotten (determined post-hoc)
- Stimulus duration: **2 seconds** (word presentation)
- ISI: Jittered **2-8 seconds**, exponential distribution with mean **4 seconds** (Dale, 1999)
- Null trials: **25%** of total events (fixation only)
- Trials per run: **60** target items + **20** null trials
- Run duration: 80 events x ~6 s mean = **480 seconds** (~8 minutes)
- Number of runs: **3** (total 180 target items)

**Optimization**: Sequences generated using optseq2 (Dale, 1999), selecting the top 5 sequences from 10,000 iterations based on maximum detection efficiency for the Remembered vs. Forgotten contrast.

**Why jitter matters**: With fixed 4-second ISI, the overlapping HRFs from consecutive trials create a nearly flat predicted response. Jittering introduces variability that allows the GLM to separate individual trial responses (Dale, 1999).

## Example 3: Mixed Design for Task-Switching

**Goal**: Separate sustained task-set maintenance from transient switch costs (Petersen & Dubis, 2012).

**Design specification**:
- Task blocks: 30 seconds each (Petersen & Dubis, 2012)
- Conditions: Task A blocks, Task B blocks, Rest blocks
- Within each block: 10 trials with 2-second stimulus + 1-second ISI
- Switch trials: First trial of each new block
- Repeat trials: Remaining trials within a block
- Rest between blocks: **20 seconds**
- Runs: **4** runs of 6 blocks each

**Model specification**:
- Sustained regressors: Boxcar for each task block type (onset = block start, duration = 30 s)
- Transient regressors: Individual trial onsets for switch vs. repeat trials
- Both convolved with canonical HRF + temporal derivative

## Design Efficiency Comparison Table

| Design | Contrast | Relative Detection Efficiency | Relative Estimation Efficiency |
|---|---|---|---|
| Block (20 s on, 20 s off) | A > rest | **1.00** (reference) | 0.15 |
| Slow ER (ISI = 16 s) | A > rest | 0.25 | **1.00** (reference) |
| Rapid ER (jittered 2-8 s) | A > rest | 0.65 | 0.55 |
| Rapid ER (jittered 2-8 s) | A > B | 0.70 | 0.50 |
| Mixed | Sustained A > rest | 0.85 | 0.10 |
| Mixed | Transient switch > repeat | 0.50 | 0.45 |

Values are approximate and depend on specific timing parameters. Based on simulations from Liu et al. (2001) and Dale (1999).

## ISI Distribution Examples

### Truncated Exponential Distribution

Parameters for a typical rapid event-related design:
- Minimum ISI: **2 seconds** (Glover, 1999)
- Mean ISI: **4 seconds** (Dale, 1999)
- Maximum ISI: **12 seconds** (truncation point)
- Lambda (rate parameter): 1 / (mean - minimum) = 1 / (4 - 2) = **0.5**

This produces approximately:
- 37% of ISIs between 2-3 s
- 23% between 3-4 s
- 14% between 4-5 s
- 26% between 5-12 s

### Uniform Distribution

- Minimum: **2 seconds**
- Maximum: **8 seconds**
- Mean: **5 seconds**
- All ISI values equally likely within range

The exponential distribution is preferred because it provides more short ISIs (higher event rate, more power) while still including enough long ISIs for HRF estimation (Hagberg et al., 2001).

## Counterbalancing Checklist

For a well-counterbalanced fMRI experiment:

1. **Condition order**: Use m-sequences (Buracas & Boynton, 2002) or optimized sequences (Dale, 1999) to ensure each condition follows every other condition equally often
2. **Response mapping**: Half of subjects use left-hand = "yes", right-hand = "no"; the other half use the reverse
3. **Stimulus assignment**: If stimuli are assigned to conditions (e.g., which words are targets vs. distractors), counterbalance assignments across subjects
4. **Run order**: If runs contain different conditions, counterbalance run order across subjects
5. **Scanner field**: For lateralized effects, consider head orientation relative to the main magnetic field

## References

- Buracas, G. T., & Boynton, G. M. (2002). Efficient design of event-related fMRI experiments using m-sequences. *NeuroImage*, 16(3), 801-813.
- Dale, A. M. (1999). Optimal experimental design for event-related fMRI. *Human Brain Mapping*, 8(2-3), 109-114.
- Hagberg, G. E., Zito, G., Patria, F., & Sanes, J. N. (2001). Improved detection of event-related functional MRI signals using probability functions. *NeuroImage*, 14(5), 1193-1205.
- Kanwisher, N., McDermott, J., & Chun, M. M. (1997). The fusiform face area: A module in human extrastriate cortex specialized for face perception. *Journal of Neuroscience*, 17(11), 4302-4311.
- Liu, T. T., Frank, L. R., Wong, E. C., & Buxton, R. B. (2001). Detection power, estimation efficiency, and predictability in event-related fMRI. *NeuroImage*, 13(4), 759-773.
- Maus, B., van Breukelen, G. J. P., Goebel, R., & Berger, M. P. F. (2010). Optimal design of multi-subject blocked fMRI experiments. *NeuroImage*, 51(3), 1338-1348.
- Petersen, S. E., & Dubis, J. W. (2012). The mixed block/event-related design. *NeuroImage*, 62(2), 1177-1184.
