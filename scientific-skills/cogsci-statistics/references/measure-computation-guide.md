# Reading Time Measure Computation Guide

This reference file supplements the main `SKILL.md` with step-by-step procedures for computing eye-tracking reading measures and handling edge cases.

## 1. Measure Computation Procedures

### 1.1 First Fixation Duration (FFD)

**Definition**: Duration of the first fixation landing on the word/region during first-pass reading.

**Computation**:
1. Identify all fixations on the region during the first pass (first entry from the left until the eyes leave the region in either direction)
2. Take the duration of the **first** of these fixations
3. If the region was skipped during first pass: **missing data** (not zero)

**Edge cases**:
- If the reader enters the region via a regression from the right: this is **not** first pass. First pass requires entry from the left (i.e., progressive reading direction)
- If there is only one first-pass fixation, FFD = SFD = GD

### 1.2 Single Fixation Duration (SFD)

**Definition**: Duration of the fixation on a word, only for trials where the word received exactly one first-pass fixation.

**Computation**:
1. Identify first-pass fixations on the region
2. If exactly **one** fixation occurred: SFD = that fixation's duration
3. If zero fixations (skip) or multiple fixations: SFD is **missing** for that trial

**When to use**: SFD provides a cleaner measure of early lexical access than FFD because it excludes cases where refixation planning may have shortened the initial fixation (Rayner, 2009). However, conditioning on single-fixation trials introduces selection bias -- participants with longer words or more difficult conditions may have fewer single-fixation trials.

### 1.3 Gaze Duration (GD)

**Definition**: Sum of all first-pass fixation durations on the word/region.

**Computation**:
1. Identify all fixations on the region during first pass
2. Sum their durations
3. If skipped: **missing data**

**This is the default first-pass reading time measure** and should be reported in virtually all eye-tracking reading studies (Rayner, 1998, 2009).

### 1.4 Go-Past Time (GPT) / Regression Path Duration

**Definition**: Time from first fixating the region until first fixating any region to the right of the current region. Includes any time spent regressing to earlier parts of the sentence.

**Computation**:
1. Record the timestamp of the first fixation on the region (first pass)
2. Record the timestamp of the first fixation on any region to the **right** of the current region
3. GPT = timestamp_right - timestamp_region_entry
4. This includes:
 - Time fixating the current region
 - Time fixating any regions to the left (regressions)
 - Time fixating the current region again (if the reader returned)

**Edge cases**:
- If the reader never progresses past the region (e.g., trial ends with regressions): GPT is typically coded as **missing** or the total remaining reading time
- If the region is skipped: GPT = 0 from the perspective of that region (but typically treated as missing)

**Critical difference from GD**: GPT includes regression time. If GPT >> GD, the reader experienced difficulty and regressed to earlier material before continuing.

### 1.5 Total Reading Time (TRT)

**Definition**: Sum of all fixation durations on the word/region across the entire trial.

**Computation**:
1. Sum the durations of every fixation that lands on the region, regardless of pass
2. If the word was never fixated (skipped on first pass and never revisited): **missing data** or **zero**, depending on convention

**Note**: Some researchers include zero for never-fixated words in TRT analyses. The convention should be stated explicitly. The more common approach is to treat never-fixated words as missing.

### 1.6 Second-Pass Reading Time

**Definition**: TRT minus first-pass gaze duration. Captures only re-reading.

**Computation**:
1. Second-pass RT = TRT - GD
2. If the word was only fixated during first pass: second-pass RT = **0**
3. If the word was skipped on first pass but fixated later: second-pass RT = sum of all (non-first-pass) fixations

### 1.7 Regression Probability (Reg-out)

**Definition**: Binary variable -- did the reader make at least one regression from the current region during first-pass reading?

**Computation**:
1. During first-pass reading of the region, did any saccade leave the region going **leftward** (toward earlier text)?
2. Yes = 1, No = 0
3. If region was skipped: **missing**

**Statistical note**: Because this is a binary outcome, analyze with **logistic mixed-effects models** (GLMM with binomial family), not linear models (Jaeger, 2008).

### 1.8 Regression-In Probability

**Definition**: Binary variable -- did the reader regress back to this region from a downstream region at any point?

**Computation**:
1. After first-pass reading of the region, was there any subsequent fixation on this region?
2. Yes = 1, No = 0

## 2. Handling Multi-Word Regions

When the region of interest spans multiple words (e.g., a relative clause, a prepositional phrase):

### First-Pass Measures for Multi-Word Regions

- **First-pass reading time (region-level)**: Sum of all fixation durations from first entering the region until leaving it (in either direction). This is the region-level analog of gaze duration (Rayner, 1998).
- Entry and exit are defined by the region boundaries, not word boundaries.

### Regression Path Duration for Multi-Word Regions

- GPT for a multi-word region = time from first fixation in the region until the eyes first land on any word **to the right** of the region.

### Reporting Convention

When using multi-word regions, always also report word-level analyses for individual words within the region, especially the first and last words, to assess where within the region effects arise.

## 3. Data Cleaning Pipeline

### Step 1: Track Loss Removal

Remove trials where the eye-tracker lost the eye signal for substantial periods. Most eye-tracking software flags these automatically. Criterion: if > **20%** of the trial duration is track-loss, exclude the trial.

### Step 2: Fixation Merging

Merge short fixations that are likely parts of a single fixation broken by brief track loss or microsaccades:

- If a fixation is < **80 ms** and the next fixation is within **1 character position** (or **0.5 degrees**): merge by adding the short fixation's duration to the adjacent fixation (Rayner & Pollatsek, 1989)
- Some researchers use **40 ms** as the merge threshold; report the value used

### Step 3: Fixation Duration Filtering

After merging:
- Exclude fixations < **80 ms** (Rayner & Pollatsek, 1989; Inhoff & Radach, 1998)
- Exclude fixations > **800 ms** (Rayner & Pollatsek, 1989) or > **1000 ms** (alternative convention)
- Report the percentage of fixations excluded at each threshold

### Step 4: Trial-Level Exclusions

- Exclude trials with blinks on the critical region
- Exclude trials where the critical word was the first or last fixation in the trial (contaminated by initial positioning and wrap-up effects)
- Exclude trials where comprehension question was answered incorrectly (optional; depends on theory)

### Step 5: Participant Exclusions

- Exclude participants with < **80%** comprehension accuracy (Rayner et al., 2006)
- Exclude participants with > **30%** track-loss rate
- Exclude participants whose average fixation duration is more than **2.5 SD** from the group mean

### Reporting Template

```
Data from N participants were analyzed. X participants were excluded
for low comprehension accuracy (<80%; n = X), excessive track loss
(>30%; n = X), or outlier fixation patterns (>2.5 SD from mean; n = X).
Fixations shorter than 80 ms within one character of the next fixation
were merged; remaining fixations shorter than 80 ms (X% of data) and
longer than 800 ms (X% of data) were excluded. Trials with track
loss on the critical region were removed (X% of trials).
```

## 4. Typical Effect Sizes

These values provide calibration for what magnitudes of effects are expected (Rayner, 2009; Clifton et al., 2007):

| Effect | Measure | Typical Magnitude | Citation |
|--------|---------|-------------------|----------|
| Word frequency (high vs. low) | GD | **30-60 ms** | Rayner, 1998; Inhoff & Rayner, 1986 |
| Predictability (high vs. low cloze) | GD | **20-40 ms** | Rayner & Well, 1996 |
| Garden-path effect | GPT | **50-200 ms** | Frazier & Rayner, 1982 |
| Plausibility violation | GD | **20-50 ms** (early); GPT **40-100 ms** (late) | Rayner et al., 2004 |
| Spillover effects | GD on n+1 | **10-30 ms** | Rayner & Pollatsek, 1989 |

## 5. Software for Computing Reading Measures

| Software | Language | Features | Reference |
|----------|----------|----------|-----------|
| **EyeDoctor / EyeTrack** | Java | Classic Rayner lab tools for sentence reading | Stracuzzi & Kinsey, 2009 |
| **eyetrackingR** | R | General eye-tracking analysis | Dink & Ferguson, 2015 |
| **Robodoc** | Python/R | Automated reading measure computation | (various implementations) |
| **SR Research Data Viewer** | Standalone | EyeLink-specific analysis | SR Research, 2017 |
| **popEye** | R | Automated computation of all standard reading measures | Risse, 2015 |
| **em2** | R | Eye movement measures for reading | Logacev & Vasishth, 2006 |

## References

- Clifton, C., Staub, A., & Rayner, K. (2007). Eye movements in reading words and sentences. In R. P. G. van Gompel et al. (Eds.), *Eye movements: A window on mind and brain*. Elsevier.
- Frazier, L., & Rayner, K. (1982). Making and correcting errors during sentence comprehension: Eye movements in the analysis of structurally ambiguous sentences. *Cognitive Psychology*, 14, 178-210.
- Inhoff, A. W., & Radach, R. (1998). Definition and computation of oculomotor measures in the study of cognitive processes. In G. Underwood (Ed.), *Eye guidance in reading and scene perception*. Elsevier.
- Inhoff, A. W., & Rayner, K. (1986). Parafoveal word processing during eye fixations in reading: Effects of word frequency. *Perception & Psychophysics*, 40, 431-439.
- Jaeger, T. F. (2008). Categorical data analysis: Away from ANOVAs (transformation or not) and towards logit mixed models. *Journal of Memory and Language*, 59, 434-446.
- Rayner, K. (1998). Eye movements in reading and information processing: 20 years of research. *Psychological Bulletin*, 124, 372-422.
- Rayner, K. (2009). The 35th Sir Frederick Bartlett Lecture: Eye movements and attention in reading, scene perception, and visual search. *Quarterly Journal of Experimental Psychology*, 62, 1457-1506.
- Rayner, K., & Pollatsek, A. (1989). *The psychology of reading*. Englewood Cliffs, NJ: Prentice Hall.
- Rayner, K., & Well, A. D. (1996). Effects of contextual constraint on eye movements in reading: A further examination. *Psychonomic Bulletin & Review*, 3, 504-509.
- Rayner, K., Warren, T., Juhasz, B. J., & Liversedge, S. P. (2004). The effect of plausibility on eye movements in reading. *Journal of Experimental Psychology: Learning, Memory, and Cognition*, 30, 1290-1301.
- Rayner, K., Chace, K. H., Slattery, T. J., & Ashby, J. (2006). Eye movements as reflections of comprehension processes in reading. *Scientific Studies of Reading*, 10, 241-255.
