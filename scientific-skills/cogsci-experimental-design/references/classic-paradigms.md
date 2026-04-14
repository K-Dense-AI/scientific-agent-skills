# Classic Cognitive Paradigms Reference

This reference covers established experimental paradigms across six core domains of cognitive psychology. Each paradigm entry includes its purpose, standard procedure, key parameters with cited ranges, dependent variables, and common variants.

---

## 1. Attention

### 1.1 Stroop Task

- **Seminal reference**: Stroop (1935). Studies of interference in serial verbal reactions. *Journal of Experimental Psychology, 18*, 643-662.
- **Purpose**: Measures selective attention and cognitive control by assessing interference between automatic word reading and controlled color naming.
- **Procedure**: Participants name the ink color of color words. Conditions: congruent (word matches ink), incongruent (word differs from ink), neutral (non-color word or symbols).
- **Key parameters**:
 - **Number of colors/responses**: Minimum **4** color-response mappings to avoid first-order contingency confounds (Schmidt & Besner, 2008; Mordkoff, 2012)
 - **Congruency proportion**: Standard is **50% congruent / 50% incongruent**; mostly-congruent lists (75% congruent) inflate interference; mostly-incongruent lists (75% incongruent) reduce it via proactive control (Logan & Zbrodoff, 1979; Bugg & Crump, 2012)
 - **SOA** (for separated-format Stroop): **0 ms** (simultaneous) is standard; SOAs of **-400 to +400 ms** used for onset asynchrony manipulations (Glaser & Glaser, 1982)
 - **Stimulus duration**: Typically **until response** or a fixed **2000 ms** deadline
 - **Inter-trial interval**: **1000-2000 ms** (MacLeod, 1991)
 - **Typical effect size**: Stroop interference ~**100 ms** RT difference (MacLeod, 1991, meta-analysis)
 - **Trial count**: **48-96 trials per condition** recommended for stable individual differences (Hedge et al., 2018)
- **DV**: Reaction time (ms), error rate (%)
- **Variants**: Manual (button-press) vs. vocal (naming); single-item vs. blocked; picture-word interference version

### 1.2 Visual Search

- **Seminal reference**: Treisman & Gelade (1980). A feature-integration theory of attention. *Cognitive Psychology, 12*, 97-136.
- **Purpose**: Investigates how attention selects targets among distractors, distinguishing parallel (pop-out) from serial search.
- **Procedure**: Participants detect or identify a target among varying numbers of distractors. Present/absent response on each trial.
- **Key parameters**:
 - **Set size**: Typically **4, 8, 12, 16** items (or **1, 5, 15, 30** in the original Treisman & Gelade, 1980); minimum 4 levels recommended for reliable slope estimation
 - **Target-distractor similarity**: Low similarity yields flat search slopes (pop-out, ~**3 ms/item**); high similarity yields steep slopes (~**20-60 ms/item** for conjunction search) (Treisman & Gelade, 1980; Wolfe, 1998)
 - **Target prevalence**: Standard **50%** present trials; low prevalence (<10%) increases miss rates dramatically (Wolfe et al., 2005)
 - **Display duration**: **Until response** or fixed (e.g., **3000-5000 ms**)
 - **Absent-to-present slope ratio**: ~**2:1** for serial self-terminating search (Treisman & Gelade, 1980)
- **DV**: RT x set-size slope (ms/item), accuracy, target-absent vs. target-present slopes
- **Variants**: Feature search, conjunction search, guided search (Wolfe, 1994); spatial configuration search

### 1.3 Posner Cueing Task

- **Seminal reference**: Posner (1980). Orienting of attention. *Quarterly Journal of Experimental Psychology, 32*, 3-25.
- **Purpose**: Measures covert spatial attention shifts, distinguishing exogenous (reflexive) from endogenous (voluntary) orienting.
- **Procedure**: Central fixation, followed by a spatial cue, then a target at a cued (valid) or uncued (invalid) location.
- **Key parameters**:
 - **Cue validity**: Standard **80% valid / 20% invalid** for endogenous cues (Posner, 1980); 50% (uninformative) for exogenous cues
 - **SOA (cue-target interval)**: **100-1000 ms**; exogenous facilitation peaks at ~**100-300 ms**, inhibition of return (IOR) appears at **>300-500 ms** (Posner & Cohen, 1984; Klein, 2000)
 - **Facilitation effect**: ~**20-50 ms** faster for valid vs. neutral trials (Posner, 1980)
 - **IOR**: ~**15-30 ms** slowing at long SOAs for peripheral cues (Klein, 2000)
 - **Inter-trial interval**: **1500-3000 ms** (Posner, 1980)
 - **Catch trial proportion**: **~20%** (no-target trials to prevent anticipatory responses)
- **DV**: RT (ms), accuracy, validity effect (invalid RT - valid RT)
- **Variants**: Peripheral vs. central cues; detection vs. discrimination task; double-cue paradigm

### 1.4 Attentional Blink

- **Seminal reference**: Raymond, Shapiro, & Arnell (1992). Temporary suppression of visual processing in an RSVP task: An attentional blink? *Journal of Experimental Psychology: Human Perception and Performance, 18*, 849-860.
- **Purpose**: Reveals temporal limits of attention by showing impaired detection of a second target (T2) shortly after a first target (T1) in a rapid serial visual presentation (RSVP) stream.
- **Procedure**: Items presented sequentially at fixation. Participants identify T1 (e.g., a white letter among black) and detect/identify T2 at varying lags.
- **Key parameters**:
 - **RSVP rate**: ~**10 items/sec** (each item ~**100 ms**) (Raymond et al., 1992; Chun & Potter, 1995)
 - **T1-T2 lag**: Typically **1-8 items** (100-800 ms); AB window spans **lags 2-5** (~200-500 ms) (Raymond et al., 1992)
 - **Lag-1 sparing**: T2 accuracy relatively preserved when T2 immediately follows T1 (lag 1) (Raymond et al., 1992; Visser et al., 1999)
 - **T2 presence**: T2 present on **50%** of trials (Raymond et al., 1992)
 - **T1 masking**: Removing T1+1 mask eliminates the AB (Raymond et al., 1992)
 - **Stream length**: Typically **15-24 items** per trial
 - **AB magnitude**: T2 accuracy drops **~20-50%** at worst lag compared to long-lag baseline (Martens & Wyble, 2010)
- **DV**: T2 accuracy conditioned on correct T1 report, across lag positions
- **Variants**: Skeletal AB (two-target, no distractors); emotional AB; cross-modal AB

### 1.5 Flanker Task (Eriksen)

- **Seminal reference**: Eriksen & Eriksen (1974). Effects of noise letters upon the identification of a target letter in a nonsearch task. *Perception & Psychophysics, 16*, 143-149.
- **Purpose**: Measures selective attention and response conflict by presenting task-irrelevant flanking stimuli alongside a central target.
- **Procedure**: Participants respond to a central target letter (or arrow) flanked by congruent, incongruent, or neutral stimuli.
- **Key parameters**:
 - **Target-flanker spacing**: **0.06-1.0 degrees** of visual angle; closer spacing produces stronger congruency effects (Eriksen & Eriksen, 1974; Miller, 1991)
 - **Flanker congruency effect**: ~**50-100 ms** RT difference (incongruent - congruent) (Eriksen & Eriksen, 1974)
 - **Number of flankers**: Standard is **2 flankers per side** (total display: 5 items, e.g., HHSHH) or **3 per side** (7 items) (Eriksen & Eriksen, 1974)
 - **Congruency proportion**: **50% congruent / 50% incongruent** is standard; proportion manipulations modulate the Gratton effect (Gratton et al., 1992)
 - **Stimulus duration**: Typically **until response** or **200 ms** with mask
 - **Response deadline**: **1000-1500 ms**
- **DV**: RT (ms), accuracy, congruency effect, delta plots (for distributional analysis)
- **Variants**: Arrow flanker (ANT version; Fan et al., 2002); color flanker; bimodal flanker

---

## 2. Memory

### 2.1 Sternberg Memory Scanning Task

- **Seminal reference**: Sternberg (1966). High-speed scanning in human memory. *Science, 153*, 652-654.
- **Purpose**: Investigates short-term memory retrieval processes by measuring how RT varies with the number of items held in memory.
- **Procedure**: Memorize a set of items (digits or letters), then judge whether a probe item was in the set (yes/no).
- **Key parameters**:
 - **Set size**: **1-6 items** (Sternberg, 1966); most commonly **1, 2, 4, 6**
 - **Scanning rate (slope)**: ~**38-40 ms per item** (Sternberg, 1966, 1969)
 - **Intercept**: ~**400 ms** baseline RT for set size 1 (Sternberg, 1966)
 - **Positive/negative slope equality**: Equal slopes support serial exhaustive search model (Sternberg, 1966)
 - **Probe duration**: Typically **until response** or **2000 ms** deadline
 - **Retention interval**: ~**2000 ms** between set presentation and probe
 - **Positive probe proportion**: **50%** (half in-set, half out-of-set)
- **DV**: RT as a function of set size; slope (scanning speed); intercept (baseline processing)
- **Variants**: Varied-set vs. fixed-set procedure; articulatory suppression version

### 2.2 DRM (Deese-Roediger-McDermott) Paradigm

- **Seminal reference**: Roediger & McDermott (1995). Creating false memories: Remembering words not presented in lists. *Journal of Experimental Psychology: Learning, Memory, and Cognition, 21*, 803-814.
- **Purpose**: Studies false memory formation by presenting lists of semantically associated words and testing recall/recognition of non-presented critical lures.
- **Procedure**: Study lists of **12-15 words** that are strong associates of a non-presented critical lure (e.g., "bed, rest, awake..." for the lure "SLEEP"). Test via free recall and/or recognition.
- **Key parameters**:
 - **List length**: **12-15 words** per list (Roediger & McDermott, 1995; Stadler et al., 1999)
 - **Number of lists**: **8-24 lists** per experiment (Roediger & McDermott, 1995 used 24 lists)
 - **Backward Associative Strength (BAS)**: Primary predictor of false recall; high-BAS lists (e.g., "sleep": mean BAS ~**0.20**) produce ~**60%** false recall; low-BAS lists (e.g., "king": mean BAS ~**0.06**) produce ~**10%** false recall (Deese, 1959; Roediger et al., 2001)
 - **Presentation rate**: **~2 sec per word** (1.5 sec display + 0.5 sec ISI) (Roediger & McDermott, 1995)
 - **Word ordering**: Descending associative strength (strongest associate first) (Roediger & McDermott, 1995)
 - **False recognition rate for critical lures**: ~**72-84%** for high-BAS lists (Roediger & McDermott, 1995)
- **DV**: Proportion of critical lure recall/recognition; Remember/Know judgments; hit and false alarm rates
- **Variants**: Pictorial DRM; categorical DRM; warning manipulation; divided attention at encoding

### 2.3 Remember-Know Paradigm

- **Seminal reference**: Tulving (1985). Memory and consciousness. *Canadian Psychology, 26*, 1-12. Extended by Gardiner (1988).
- **Purpose**: Dissociates conscious recollection ("Remember") from familiarity-based recognition ("Know") during memory retrieval.
- **Procedure**: Standard recognition test; for each "old" response, participants further judge whether they "Remember" (recollect specific contextual details) or "Know" (familiar but no specific recollection).
- **Key parameters**:
 - **Study-test delay**: **Immediate** to **48 hours**; Remember responses decline more steeply than Know over time (Gardiner & Java, 1991)
 - **Encoding manipulation**: Levels of processing — deep encoding increases Remember but not Know judgments (Gardiner, 1988)
 - **Typical R/K proportions**: ~**40-60%** Remember, ~**20-40%** Know for studied items at immediate test (Gardiner, 1988; Rajaram, 1993)
 - **Guess option**: Some designs add a third "Guess" response to improve the purity of Know judgments (Gardiner et al., 1998)
 - **Independence correction**: Familiarity = Know / (1 - Remember) to correct for redundancy (Yonelinas & Jacoby, 1995)
- **DV**: Proportion Remember, proportion Know, corrected familiarity estimates
- **Variants**: Source memory R/K; confidence-based R/K; perceptual vs. conceptual encoding manipulations

### 2.4 Change Detection (Visual Working Memory)

- **Seminal reference**: Luck & Vogel (1997). The capacity of visual working memory for features and conjunctions. *Nature, 390*, 279-281.
- **Purpose**: Measures visual working memory (VWM) capacity by requiring detection of changes in brief visual arrays.
- **Procedure**: Briefly display an array of colored squares (sample), blank retention interval, then a test array. Participants judge whether one item changed.
- **Key parameters**:
 - **Set size**: **1-8 items**; typically **2, 4, 6, 8** (Luck & Vogel, 1997)
 - **Sample display duration**: **100-500 ms** (typically **100-150 ms** to prevent verbal recoding) (Luck & Vogel, 1997; Vogel et al., 2001)
 - **Retention interval**: **900-1000 ms** (must be long enough to eliminate iconic memory trace, ~**1 s**) (Luck & Vogel, 1997; Vogel et al., 2001)
 - **Change probability**: **50%** of trials contain a change (Luck & Vogel, 1997)
 - **Capacity estimate (Cowan's K)**: **K = N x (hit rate - false alarm rate)**; typical K ~**3-4 items** (Cowan, 2001; Luck & Vogel, 1997)
 - **Test array**: Whole-display probe or single-probe (single-probe preferred to avoid decisional noise) (Rouder et al., 2011)
- **DV**: Accuracy, Cowan's K, hit rate, false alarm rate
- **Variants**: Whole-report vs. single-probe; bilateral (lateralized for CDA/ERP measurement); continuous-report (for precision estimation)

### 2.5 Serial Position Curve

- **Seminal reference**: Murdock (1962). The serial position effect of free recall. *Journal of Experimental Psychology, 64*, 482-488.
- **Purpose**: Demonstrates primacy (better recall of early items) and recency (better recall of late items) in list memory.
- **Procedure**: Present a list of items sequentially; test via free recall.
- **Key parameters**:
 - **List length**: **10-40 items**; 15-20 is common (Murdock, 1962; Glanzer & Cunitz, 1966)
 - **Presentation rate**: **1-2 sec per item** (Murdock, 1962)
 - **Delay before recall**: **0 sec** (immediate) preserves recency; **15-30 sec** filled delay eliminates recency but not primacy (Glanzer & Cunitz, 1966; Postman & Phillips, 1965)
 - **Distractor task**: Counting backward by 3s during delay period (Peterson & Peterson, 1959)
 - **Primacy span**: First **3-4 items** show enhanced recall (Murdock, 1962)
 - **Recency span**: Last **3-4 items** show enhanced recall in immediate test (Murdock, 1962)
- **DV**: Proportion correct recall as a function of serial position
- **Variants**: Probed recall; continual distractor paradigm (eliminates recency-primacy dissociation for short-term vs. long-term memory distinction; Bjork & Whitten, 1974)

---

## 3. Decision Making

### 3.1 Iowa Gambling Task (IGT)

- **Seminal reference**: Bechara, Damasio, Damasio, & Anderson (1994). Insensitivity to future consequences following damage to human prefrontal cortex. *Cognition, 50*, 7-15.
- **Purpose**: Assesses decision making under ambiguity and risk, particularly the ability to learn from reward/punishment contingencies.
- **Procedure**: Choose cards from 4 decks (A, B, C, D) across 100 trials. Each selection yields a gain and, on some trials, a loss.
- **Key parameters**:
 - **Number of trials**: **100 selections** (Bechara et al., 1994)
 - **Starting loan**: **$2,000** (play money) (Bechara et al., 1994)
 - **Deck contingencies** (Bechara et al., 1994):
 - Decks A & B ("bad"): **$100 gain/card**, net loss of **-$250 per 10 cards**
 - Decks C & D ("good"): **$50 gain/card**, net gain of **+$250 per 10 cards**
 - **Loss frequency**: Decks A & C: frequent, small losses; Decks B & D: infrequent, large losses (Bechara et al., 1994)
 - **Learning phase**: Participants typically begin advantageous selections around trial **40-50** (Bechara et al., 1997)
 - **Performance score**: **(C + D) - (A + B)** across all 100 trials (Bechara et al., 1994)
- **DV**: Net score, deck selections per block of 20 trials, learning curve
- **Variants**: Computerized versions; modified IGT with reversed reward/loss frequency; Soochow Gambling Task

### 3.2 Delay Discounting

- **Seminal reference**: Mazur (1987). An adjusting procedure for studying delayed reinforcement. In *Quantitative Analyses of Behavior*, Vol. 5.
- **Purpose**: Measures how subjective value of rewards decreases as a function of delay, quantifying impulsivity in intertemporal choice.
- **Procedure**: Participants choose between a smaller-sooner reward and a larger-later reward across multiple delay conditions.
- **Key parameters**:
 - **Delays**: Commonly **1 day, 1 week, 1 month, 6 months, 1 year, 5 years** (Richards et al., 1999)
 - **Reward magnitudes**: $100 (or $1000) standard amount; smaller amount adjusted (Rachlin et al., 1991)
 - **Hyperbolic model**: **V = A / (1 + kD)**, where V = subjective value, A = amount, D = delay, k = discounting rate (Mazur, 1987)
 - **Discounting rate (k)**: Higher k indicates steeper discounting (more impulsive); typical log(k) ranges from **-4 to 0** in human studies (Johnson & Bickel, 2002)
 - **Area Under the Curve (AUC)**: Model-free alternative to k; ranges from **0** (complete discounting) to **1** (no discounting) (Myerson et al., 2001)
 - **Number of choice trials**: Minimum **~60-100 trials** across delays for stable k estimation; adjusting-amount procedures use ~**5-6 trials per delay** (Du et al., 2002)
- **DV**: Indifference points, k parameter, AUC, proportion of larger-later choices
- **Variants**: Adjusting-amount procedure; adjusting-delay procedure; experiential discounting task; probabilistic discounting

### 3.3 Signal Detection Theory (SDT) Framework

- **Seminal reference**: Green & Swets (1966). *Signal Detection Theory and Psychophysics*. New York: Wiley.
- **Purpose**: Separates perceptual sensitivity from response bias in detection/recognition tasks.
- **Procedure**: Present signal+noise or noise-alone trials. Participants respond "yes" (signal present) or "no". Record hits, misses, false alarms, correct rejections.
- **Key parameters**:
 - **d' (sensitivity)**: **d' = z(hit rate) - z(false alarm rate)** (Green & Swets, 1966); d' = 0 means chance; d' = 1 is moderate; d' > 2 is high sensitivity
 - **Criterion (c)**: **c = -0.5 * [z(hit rate) + z(false alarm rate)]** (Macmillan & Creelman, 2005); c = 0 is unbiased; c > 0 is conservative; c < 0 is liberal
 - **Beta (likelihood ratio)**: **beta = f_s(c) / f_n(c)**; beta = 1 is unbiased (Green & Swets, 1966)
 - **Signal proportion**: **50%** is standard; unequal base rates shift criterion (Macmillan & Creelman, 2005)
 - **Trial count**: Minimum **~100 trials** (50 signal, 50 noise) for stable d' estimation; **200+ trials** preferred (Macmillan & Creelman, 2005)
 - **ROC analysis**: Minimum **4-6 confidence levels** for ROC curve construction (Macmillan & Creelman, 2005)
- **DV**: d', criterion c, beta, hit rate, false alarm rate, ROC curves, AUC
- **Variants**: Yes/No; forced-choice (2AFC, mAFC); rating-scale procedure; confidence ratings

### 3.4 Two-Alternative Forced Choice (2AFC)

- **Seminal reference**: Fechner (1860/1966). *Elements of Psychophysics*. Formalized in SDT framework by Green & Swets (1966).
- **Purpose**: Bias-free method for measuring perceptual/cognitive sensitivity by requiring a choice between two intervals or locations.
- **Procedure**: Two stimuli (or intervals) presented; one contains the signal/target. Participant indicates which.
- **Key parameters**:
 - **Sensitivity advantage over Yes/No**: d'(2AFC) = d'(Yes/No) x sqrt(2) (Green & Swets, 1966)
 - **Chance performance**: **50%** correct (compared to variable rates in Yes/No)
 - **Inter-stimulus interval**: **500-1000 ms** between the two intervals (Kingdom & Prins, 2016)
 - **Trial count**: **~80-200 trials** per condition for stable threshold estimates (Kingdom & Prins, 2016)
 - **Interval bias**: Tracked and controlled; some observers show a bias toward the first or second interval
- **DV**: Proportion correct, d', psychometric function parameters
- **Variants**: 2IFC (two-interval), 2AFC spatial (left/right), mAFC (m > 2)

---

## 4. Perception

### 4.1 Psychophysical Staircase Methods

- **Seminal reference**: Cornsweet (1962). The staircase method in psychophysics. *American Journal of Psychology, 75*, 485-491.
- **Purpose**: Efficiently estimates perceptual thresholds by adaptively adjusting stimulus intensity based on the observer's responses.
- **Procedure**: Stimulus intensity increases after incorrect responses and decreases after correct responses. Threshold estimated from reversal points.

#### 4.1.1 Transformed Up-Down Methods

- **Reference**: Levitt (1971). Transformed up-down methods in psychoacoustics. *Journal of the Acoustical Society of America, 49*, 467-477.
- **Key parameters**:
 - **1-up/1-down**: Converges on **50%** correct point (Cornsweet, 1962)
 - **1-up/2-down**: Converges on **70.7%** correct point (Levitt, 1971)
 - **1-up/3-down**: Converges on **79.4%** correct point (Levitt, 1971)
 - **Initial step size**: Typically **large** (e.g., **4-8 dB** or **20-50%** of range) then halved after first 2-4 reversals (Garcia-Perez, 1998)
 - **Number of reversals**: **6-12 reversals** for threshold estimation; average last **6-8** reversals (Levitt, 1971)
 - **Total trials**: Typically **40-80 trials** per staircase (Garcia-Perez, 1998)
 - **Starting level**: Suprathreshold (~**10-20 dB** above expected threshold) (Garcia-Perez, 1998)

#### 4.1.2 QUEST (Bayesian Adaptive)

- **Reference**: Watson & Pelli (1983). QUEST: A Bayesian adaptive psychometric method. *Perception & Psychophysics, 33*, 113-120.
- **Key parameters**:
 - **Prior**: Assumes threshold is uniformly distributed (or Gaussian) over a specified range (Watson & Pelli, 1983)
 - **Psychometric function**: Typically Weibull; **slope (beta)** parameter must be specified (default ~**3.5** for 2AFC) (Watson & Pelli, 1983)
 - **Target performance level**: **82%** correct for Weibull in 2AFC (Watson & Pelli, 1983)
 - **Lapse rate**: **0.01-0.04** (Watson & Pelli, 1983; Wichmann & Hill, 2001)
 - **Convergence speed**: ~**20-40 trials** for reasonable estimates; ~**50 trials** for good precision (Watson & Pelli, 1983)
 - **QUEST+**: Extended version allowing multi-parameter estimation (Watson, 2017)
- **DV**: Threshold estimate, confidence interval
- **Variants**: QUEST+ (Watson, 2017); Psi method (Kontsevich & Tyler, 1999); Bayesian adaptive estimation

### 4.2 Masking Paradigms

- **Seminal references**: Breitmeyer (1984). *Visual Masking: An Integrative Approach*. Oxford University Press. Breitmeyer & Ogmen (2006). *Visual Masking: Time Slices Through Conscious and Unconscious Vision*. Oxford University Press.
- **Purpose**: Controls conscious visibility of a target stimulus by presenting a mask at varying temporal offsets. Used to study subliminal processing and temporal dynamics of visual processing.

#### 4.2.1 Forward Masking (Paracontrast)

- **Key parameters**:
 - **Mask-to-target SOA**: **-500 to 0 ms** (mask precedes target) (Breitmeyer & Ogmen, 2006)
 - **Peak masking**: At SOA of approximately **-50 to -100 ms** for pattern masks (Breitmeyer, 1984)
 - **Mask duration**: **20-100 ms** (Breitmeyer, 1984)
 - **Recovery**: Forward masking typically weaker than backward masking (Breitmeyer & Ogmen, 2006)

#### 4.2.2 Backward Masking (Metacontrast)

- **Key parameters**:
 - **Target-to-mask SOA**: **0-200 ms**; strongest masking at **~50-100 ms** SOA for metacontrast (Breitmeyer, 1984; Breitmeyer & Ogmen, 2006)
 - **Type-A masking**: Monotonic decrease in masking with increasing SOA (pattern masking; high mask/target energy ratio) (Kahneman, 1968)
 - **Type-B masking**: U-shaped function with peak masking at intermediate SOAs (~**50-150 ms**) (metacontrast/paracontrast) (Breitmeyer, 1984)
 - **Target duration**: **10-50 ms** (brief, to allow masking to be effective) (Breitmeyer & Ogmen, 2006)
 - **Mask duration**: **50-200 ms** typically (Breitmeyer, 1984)
 - **Mask type**: Pattern mask (spatially overlapping) or metacontrast mask (spatially adjacent, non-overlapping) (Breitmeyer & Ogmen, 2006)
 - **Criterion content**: d' can be high even when subjective visibility is near zero, distinguishing detection from identification (Breitmeyer et al., 2004)
- **DV**: Accuracy, d', subjective visibility ratings (PAS or confidence), RT
- **Variants**: Pattern masking, metacontrast/paracontrast, object substitution masking (Enns & Di Lollo, 2000), sandwich masking

---

## 5. Language

### 5.1 Lexical Decision Task

- **Seminal reference**: Meyer & Schvaneveldt (1971). Facilitation in recognizing pairs of words: Evidence of a dependence between retrieval operations. *Journal of Experimental Psychology, 90*, 227-234.
- **Purpose**: Measures lexical access speed by requiring participants to classify letter strings as words vs. nonwords.
- **Procedure**: Display a letter string; participant presses "word" or "nonword" button as quickly and accurately as possible.
- **Key parameters**:
 - **Word frequency effect**: High-frequency words are recognized ~**50-100 ms** faster than low-frequency words (Balota & Chumbley, 1984; Brysbaert & New, 2009)
 - **Neighborhood density (Coltheart's N)**: High-N words (many orthographic neighbors) show ~**10-30 ms** inhibition compared to low-N words (Coltheart et al., 1977; Andrews, 1997)
 - **Nonword construction**: Pseudowords (pronounceable, e.g., "trud") are harder to reject than random letter strings; matched to words on length and bigram frequency (Keuleers & Brysbaert, 2010)
 - **Word-nonword ratio**: **50:50** (equal numbers of words and nonwords) (Balota & Chumbley, 1984)
 - **Stimulus duration**: Typically **until response** or **2000 ms** deadline
 - **Trial count**: **~200-400 trials** total for stable effects (Keuleers et al., 2012)
- **DV**: RT (ms), accuracy (%), lexical processing time
- **Variants**: Go/No-Go lexical decision; masked priming lexical decision; progressive demasking

### 5.2 Sentence Processing

#### 5.2.1 Self-Paced Reading

- **Seminal reference**: Just, Carpenter, & Woolley (1982). Paradigms and processes in reading comprehension. *Journal of Experimental Psychology: General, 111*, 228-238.
- **Purpose**: Measures incremental processing difficulty during reading by recording reading times for successive regions of a sentence.
- **Procedure**: Sentence segments presented one at a time (word-by-word or phrase-by-phrase); participant presses a key to advance. Each segment is either revealed cumulatively or replaces the previous one.
- **Key parameters**:
 - **Presentation mode**: Moving-window (non-cumulative) preferred for reducing parafoveal preview and re-reading (Just et al., 1982)
 - **Segmentation**: Word-by-word (most common) or phrase-by-phrase (Just et al., 1982)
 - **Comprehension questions**: After **~30-50%** of sentences to ensure attention (Just et al., 1982)
 - **Critical region**: Target word + **1-2 words** spillover region (Just et al., 1982; Rayner, 1998)
 - **Typical effect sizes**: Garden-path effects ~**50-150 ms** per word at the disambiguating region (Frazier & Rayner, 1982)
 - **Number of items per condition**: **24-48 sentences** per condition (Keating & Jegerski, 2015)

#### 5.2.2 Eye-Tracking During Reading

- **Seminal reference**: Rayner (1998). Eye movements in reading and information processing: 20 years of research. *Psychological Bulletin, 124*, 372-422.
- **Key eye-tracking measures** (Rayner, 1998):
 - **First-fixation duration**: Duration of the first fixation on a word (~**200-250 ms** for typical words)
 - **Gaze duration**: Sum of all first-pass fixations on a word (~**200-300 ms** for typical words)
 - **Total reading time**: All fixations on a word, including regressions
 - **Regression probability**: Proportion of trials with regressions to/from a region (~**10-15%** for normal text)
 - **Typical fixation duration**: ~**200-250 ms** for skilled readers (Rayner, 1998)
 - **Average saccade length**: ~**7-9 characters** (Rayner, 1998)
- **DV**: First-fixation duration, gaze duration, total time, regression probability, go-past time

### 5.3 Priming (Semantic/Associative)

- **Seminal reference**: Meyer & Schvaneveldt (1971); Neely (1977). Semantic priming and retrieval from lexical memory. *Journal of Experimental Psychology: General, 106*, 226-254.
- **Purpose**: Measures automatic and controlled spreading activation in semantic memory by presenting a related or unrelated prime before a target.
- **Procedure**: Prime word displayed, followed by target word. Participant makes lexical decision or names the target.
- **Key parameters**:
 - **SOA (prime-target)**: Short SOA (**<300 ms**): automatic priming predominates; Long SOA (**>500 ms**): strategic/expectancy-based priming predominates (Neely, 1977; Hutchison, 2003)
 - **Priming effect magnitude**: ~**20-40 ms** at short SOA; ~**40-80 ms** at long SOA for related vs. unrelated pairs (Neely, 1977; Lucas, 2000)
 - **Prime duration**: **150-500 ms** for visible priming; **30-60 ms** with mask for masked priming (Forster & Davis, 1984)
 - **Proportion of related pairs (relatedness proportion, RP)**: Standard **50%** related; higher RP inflates priming via strategic expectancy (Neely et al., 1989; Hutchison, 2007)
 - **Nonword ratio**: **50%** of targets are nonwords (when using lexical decision) (Neely, 1977)
 - **Number of items**: **~40-80 prime-target pairs** per condition (McNamara, 2005)
- **DV**: Priming effect (unrelated RT - related RT), accuracy
- **Variants**: Masked priming; repetition priming; cross-modal priming; mediated priming; negative priming

---

## 6. Executive Function

### 6.1 Go/No-Go Task

- **Seminal reference**: Donders (1868/1969). On the speed of mental processes. Translated in *Acta Psychologica, 30*, 412-431.
- **Purpose**: Measures response inhibition by requiring participants to respond to "Go" stimuli and withhold responses to "No-Go" stimuli.
- **Procedure**: Stimuli appear one at a time. Press button for Go stimuli (e.g., letter "X"), withhold for No-Go stimuli (e.g., letter "Y").
- **Key parameters**:
 - **Go/No-Go ratio**: **70-80% Go / 20-30% No-Go** to create prepotent Go response (Wessel, 2018)
 - **Commission error rate**: Healthy adults ~**5-15%** false alarms to No-Go stimuli (Bezdjian et al., 2009)
 - **Stimulus duration**: **200-500 ms** (Wessel, 2018)
 - **ISI**: **1000-2000 ms** (Wessel, 2018)
 - **No-Go N2/P3 ERP components**: N2 peaks at ~**200-300 ms**; P3 at ~**300-500 ms** at frontocentral sites (Falkenstein et al., 1999)
 - **Trial count**: **~200-400 total trials** (minimum **50 No-Go trials**) (Wessel, 2018)
- **DV**: Commission error rate, omission error rate, Go RT, No-Go N2/P3 amplitude
- **Variants**: Emotional Go/No-Go; cued Go/No-Go; sustained-attention-to-response task (SART)

### 6.2 Stop-Signal Task

- **Seminal reference**: Logan & Cowan (1984). On the ability to inhibit thought and action: A theory of an act of control. *Psychological Review, 91*, 295-327.
- **Purpose**: Measures the ability to cancel an already-initiated response (outright stopping), yielding an estimate of stop-signal reaction time (SSRT).
- **Procedure**: Primarily Go trials (respond to a stimulus); on a subset of trials, a stop signal (usually auditory) appears after the go stimulus, instructing participants to withhold their response.
- **Key parameters**:
 - **Stop-signal proportion**: **25%** of trials are stop trials (Logan et al., 1984; Verbruggen et al., 2019)
 - **Stop-signal delay (SSD)**: Adaptive staircase tracking procedure: SSD increases by **50 ms** after successful stops, decreases by **50 ms** after failed stops; targets **50%** inhibition probability (Levitt, 1971 transformed rule; Verbruggen et al., 2008)
 - **SSRT estimation**: **Integration method** preferred: SSRT = nth RT - mean SSD, where n = number of RTs x p(respond|signal) (Verbruggen et al., 2019, consensus guide)
 - **Typical SSRT**: **~200-250 ms** in healthy adults (Logan et al., 1984; Verbruggen et al., 2019)
 - **Go RT**: ~**450-600 ms** for choice RT tasks (Logan et al., 1984)
 - **Minimum trial count**: **~160-200 total trials** (~40-50 stop trials) for reliable SSRT (Verbruggen et al., 2019)
 - **Independence assumption**: Go and stop processes race independently; checked by verifying that failed-stop RTs < Go RTs (Logan & Cowan, 1984)
- **DV**: SSRT, Go RT, p(respond|signal), SSD, Go accuracy
- **Variants**: Stop-change task; selective stopping; anticipated-response version

### 6.3 Task Switching

- **Seminal reference**: Rogers & Monsell (1995). Costs of a predictable switch between simple cognitive tasks. *Journal of Experimental Psychology: General, 124*, 207-231. Review: Monsell (2003). Task switching. *Trends in Cognitive Sciences, 7*, 134-140.
- **Purpose**: Measures cognitive flexibility and task-set reconfiguration costs when alternating between two or more tasks.
- **Procedure**: Alternating-runs paradigm (AABB...) or cued task-switching. Two tasks share the same stimuli but require different responses.
- **Key parameters**:
 - **Switch cost**: RT difference between switch trials and repeat trials; typically ~**100-300 ms** for short preparation intervals (Rogers & Monsell, 1995; Monsell, 2003)
 - **Mixing cost**: RT difference between repeat trials in mixed blocks and trials in pure (single-task) blocks; typically **~100-200 ms** (Rubin & Meiran, 2005; Los, 1996)
 - **Preparation interval (cue-stimulus interval, CSI)**: Switch cost reduces with longer CSI up to ~**600 ms**, then asymptotes (residual cost ~**50-100 ms**) (Rogers & Monsell, 1995; Monsell, 2003)
 - **Residual switch cost**: Persists even with **>5 sec** preparation; ~**50-150 ms** (Monsell, 2003)
 - **Response-stimulus interval (RSI)**: Typically **100-1500 ms**; confounded with CSI in alternating-runs designs (Monsell, 2003)
 - **Number of tasks**: Most commonly **2 tasks**; 3+ tasks used for mixing cost studies
 - **Trial count**: **~100-200 trials per cell** (switch vs. repeat x task) (Monsell, 2003)
- **DV**: Switch cost (RT, errors), mixing cost, preparation effect, error switch cost
- **Variants**: Alternating-runs (Rogers & Monsell, 1995); cued task-switching (Meiran, 1996); voluntary task-switching (Arrington & Logan, 2004)

### 6.4 N-Back Task

- **Seminal reference**: Kirchner (1958). Age differences in short-term retention of rapidly changing information. *Journal of Experimental Psychology, 55*, 352-358. Meta-analysis: Owen, McMillan, Laird, & Bullmore (2005). *Human Brain Mapping, 25*, 46-59.
- **Purpose**: Assesses working memory updating by requiring participants to match current stimuli to those presented n items earlier.
- **Procedure**: Continuous stream of stimuli. Respond "match" when current stimulus equals the one presented n positions back.
- **Key parameters**:
 - **Load levels**: **0-back** (control), **1-back**, **2-back**, **3-back** (standard range; >3-back often produces floor-level accuracy) (Owen et al., 2005)
 - **Target proportion**: **~20-33%** of trials are targets (matches) (Owen et al., 2005; Jaeggi et al., 2010)
 - **Stimulus duration**: **500 ms** (typical) (Owen et al., 2005)
 - **ISI**: **1500-2500 ms** (Owen et al., 2005)
 - **Typical d' by load level** (Haatveit et al., 2010):
 - 0-back: ~**3.1**
 - 1-back: ~**2.5**
 - 2-back: ~**1.6**
 - 3-back: ~**0.7**
 - **Stimulus type**: Letters, digits, spatial locations, shapes, faces (Owen et al., 2005)
 - **Trial count**: **~40-60 trials per load level**; minimum **~20 targets per level** for stable d' (Jaeggi et al., 2010)
 - **Lure trials**: Stimuli matching at n-1 or n+1 positions to test interference resistance (Gray et al., 2003)
- **DV**: d' (sensitivity), accuracy (hits, false alarms, omissions), RT for hits
- **Variants**: Dual n-back (Jaeggi et al., 2008); emotional n-back; spatial vs. verbal n-back

---

## Quick Reference: Domain Coverage Summary

| Domain | Paradigms Covered | Count |
|---|---|---|
| Attention | Stroop, Visual Search, Posner Cueing, Attentional Blink, Flanker | 5 |
| Memory | Sternberg, DRM, Remember-Know, Change Detection, Serial Position | 5 |
| Decision Making | Iowa Gambling Task, Delay Discounting, SDT, 2AFC | 4 |
| Perception | Psychophysical Staircase (Up-Down, QUEST), Masking (Forward, Backward) | 3+ |
| Language | Lexical Decision, Sentence Processing (SPR, Eye-tracking), Priming | 4 |
| Executive Function | Go/No-Go, Stop-Signal, Task Switching, N-Back | 4 |
| **Total** | | **25+** |
