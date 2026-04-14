# Lexical Databases Guide

This reference file supplements the main `SKILL.md` with detailed instructions for accessing and querying the lexical control databases needed for stimulus norming.

## 1. Word Frequency Databases

### 1.1 SUBTLEX-US (Recommended)

**Source**: Brysbaert & New (2009)
**URL**: https://www.ugent.be/pp/experimentele-psychologie/en/research/documents/subtlexus
**Corpus**: American English subtitles (~51 million words from 8,388 films/TV episodes)

**Key columns**:
| Column | Description | Use |
|--------|-------------|-----|
| `FREQcount` | Raw frequency count | For computing custom metrics |
| `CDcount` | Contextual diversity (number of films/episodes containing the word) | Better predictor than raw frequency for some tasks (Adelman et al., 2006) |
| `Lg10WF` | Log10(frequency per million + 1) | **Primary frequency measure** -- use this for matching |
| `Lg10CD` | Log10(contextual diversity per million + 1) | Alternative to Lg10WF |
| `SUBTLWF` | Frequency per million words | For reporting and interpretability |

**How to use**:
1. Download the Excel file from the URL above
2. Look up each critical word
3. Extract `Lg10WF` for each word
4. Compare condition means; ensure no significant difference (p > 0.20)

**Typical values**:
- Very high frequency (the, is, and): Lg10WF > **4.0**
- High frequency (house, water, know): Lg10WF ~ **3.0-4.0**
- Medium frequency (sword, puzzle, brave): Lg10WF ~ **2.0-3.0**
- Low frequency (abacus, fjord, plinth): Lg10WF < **2.0**
- Very low frequency / unknown: Lg10WF < **1.0** or absent from database

### 1.2 SUBTLEX-UK

**Source**: van Heuven et al. (2014)
**URL**: http://crr.ugent.be/archives/1423
**Use**: For British English materials; same structure as SUBTLEX-US

### 1.3 Other Language Versions

SUBTLEX databases exist for: Dutch, Chinese, German, Spanish, French, Greek, and others. Use the version matching your experimental language.

## 2. Concreteness Ratings

### Brysbaert et al. (2014)

**Source**: Brysbaert, Warriner, & Kuperman (2014)
**URL**: http://crr.ugent.be/archives/1330
**Coverage**: ~40,000 English word lemmas
**Scale**: 1 (abstract) to 5 (concrete), collected via crowdsourcing (N ~ 30 raters per word)

**Key columns**:
| Column | Description |
|--------|-------------|
| `Conc.M` | Mean concreteness rating (1-5) |
| `Conc.SD` | Standard deviation of ratings |

**Typical values**:
- Very concrete (table, dog, hammer): > **4.5**
- Concrete (forest, music, bread): **3.5-4.5**
- Medium (justice, freedom, idea): **2.5-3.5**
- Abstract (truth, hope, theory): **1.5-2.5**
- Very abstract (essence, entropy): < **1.5**

## 3. Age of Acquisition (AoA) Ratings

### Kuperman et al. (2012)

**Source**: Kuperman, Stadthagen-Gonzalez, & Brysbaert (2012)
**URL**: http://crr.ugent.be/archives/806
**Coverage**: ~30,000 English words
**Scale**: Estimated age (in years) at which the word was learned

**Key columns**:
| Column | Description |
|--------|-------------|
| `Rating.Mean` | Mean estimated AoA in years |
| `Rating.SD` | Standard deviation |

**Typical values**:
- Early acquired (dog, water, happy): **2-4 years**
- Medium acquisition (bicycle, important, discover): **5-8 years**
- Late acquired (mortgage, rhetoric, hypothesis): **10+ years**

## 4. Emotional Valence and Arousal

### Warriner et al. (2013)

**Source**: Warriner, Kuperman, & Brysbaert (2013)
**URL**: http://crr.ugent.be/archives/1003
**Coverage**: ~14,000 English words
**Scale**: 1-9 for valence (unhappy-happy), arousal (calm-excited), and dominance (controlled-in control)

**Key columns**:
| Column | Description |
|--------|-------------|
| `V.Mean.Sum` | Mean valence rating (1-9) |
| `A.Mean.Sum` | Mean arousal rating (1-9) |
| `D.Mean.Sum` | Mean dominance rating (1-9) |

**When to control**: Control valence and arousal when your manipulation is not emotional, to ensure emotional content does not confound the critical comparison.

## 5. Orthographic Neighborhood Density

### Definition

Orthographic neighborhood density (Coltheart's N) = the number of words that can be created by changing one letter of the target word while preserving word length (Coltheart et al., 1977).

### Sources

| Tool | URL | Features |
|------|-----|----------|
| **N-Watch** | https://www.pc.rhul.ac.uk/staff/c.davis/Utilities/N-Watch/ | N, frequency-weighted N, bigram frequency |
| **CLEARPOND** | http://clearpond.northwestern.edu/ | Cross-linguistic; N for English, Dutch, French, German, Spanish |
| **English Lexicon Project** | https://elexicon.wustl.edu/ | N, OLD20, phonological N, and many other metrics |

### Key Metrics

| Metric | Description | When to Control |
|--------|-------------|-----------------|
| **Coltheart's N** | Count of orthographic neighbors | Always, for single-word reading tasks |
| **OLD20** | Mean Levenshtein distance to 20 nearest orthographic neighbors | More sensitive than N; recommended (Yarkoni et al., 2008) |
| **Frequency-weighted N** | N weighted by neighbor frequency | When high-frequency neighbors might prime/inhibit the target |

## 6. Multi-Variable Lookup Tools

### English Lexicon Project (ELP)

**URL**: https://elexicon.wustl.edu/
**Features**: One-stop lookup for frequency (HAL, SUBTLEX), length, N, OLD20, morphological information, plus behavioral data (lexical decision RT, naming RT) for ~40,000 words (Balota et al., 2007).

**Behavioral benchmarks from ELP** (Balota et al., 2007):
- Average lexical decision RT: ~**620 ms** (correct responses)
- High frequency words: ~**550-580 ms**
- Low frequency words: ~**680-750 ms**
- Very low frequency words: ~**800+ ms**

### Other Multi-Variable Tools

| Tool | URL | Coverage |
|------|-----|----------|
| **WordSmith** | Various | Corpus analysis toolkit |
| **ARC Nonword Database** | https://www.cogsci.mq.edu.au/research/resources/nwdb/ | Nonword generation with controlled properties |
| **Wuggy** | http://crr.ugent.be/programs-data/wuggy | Pseudoword generation matching real-word properties |

## 7. Practical Workflow for Lexical Matching

### Step-by-Step Protocol

1. **List all critical words** per condition
2. **Query SUBTLEX-US** for `Lg10WF` (frequency)
3. **Query Kuperman et al.** for AoA
4. **Query Brysbaert et al.** for concreteness
5. **Query ELP** for word length, N, OLD20
6. **Create a comparison table** with condition means and SDs for each variable
7. **Run independent-samples t-tests** (2 conditions) or one-way ANOVAs (3+ conditions) on each variable
8. **Criterion**: All p-values > 0.20 (conservative) or > 0.10 (minimum acceptable)
9. If any variable differs: replace problematic items or add as covariate

### Example Comparison Table

| Variable | Condition A (M +/- SD) | Condition B (M +/- SD) | t | p |
|----------|----------------------|----------------------|---|---|
| SUBTLEX Lg10WF | 2.85 +/- 0.62 | 2.78 +/- 0.71 | 0.42 | 0.68 |
| Length (chars) | 5.2 +/- 1.1 | 5.4 +/- 1.3 | -0.67 | 0.51 |
| Concreteness | 3.82 +/- 0.94 | 3.71 +/- 0.88 | 0.48 | 0.63 |
| AoA (years) | 6.3 +/- 2.1 | 6.8 +/- 2.4 | -0.89 | 0.38 |
| Coltheart's N | 4.1 +/- 3.2 | 3.8 +/- 2.9 | 0.39 | 0.70 |

All p > 0.20: conditions are adequately matched.

## References

- Adelman, J. S., Brown, G. D. A., & Quesada, J. F. (2006). Contextual diversity, not word frequency, determines word-naming and lexical decision times. *Psychological Science*, 17, 814-823.
- Balota, D. A., Yap, M. J., Cortese, M. J., et al. (2007). The English Lexicon Project. *Behavior Research Methods*, 39, 445-459.
- Brysbaert, M., & New, B. (2009). Moving beyond Kucera and Francis: A critical evaluation of current word frequency norms. *Behavior Research Methods*, 41, 977-990.
- Brysbaert, M., Warriner, A. B., & Kuperman, V. (2014). Concreteness ratings for 40 thousand generally known English word lemmas. *Behavior Research Methods*, 46, 904-911.
- Coltheart, M., Davelaar, E., Jonasson, J. T., & Besner, D. (1977). Access to the internal lexicon. In S. Dornic (Ed.), *Attention and performance VI*. Erlbaum.
- Kuperman, V., Stadthagen-Gonzalez, H., & Brysbaert, M. (2012). Age-of-acquisition ratings for 30,000 English words. *Behavior Research Methods*, 44, 978-990.
- van Heuven, W. J. B., Mandera, P., Keuleers, E., & Brysbaert, M. (2014). SUBTLEX-UK: A new and improved word frequency database for British English. *Quarterly Journal of Experimental Psychology*, 67, 1176-1190.
- Warriner, A. B., Kuperman, V., & Brysbaert, M. (2013). Norms of valence, arousal, and dominance for 13,915 English lemmas. *Behavior Research Methods*, 45, 1191-1207.
- Yarkoni, T., Balota, D., & Yap, M. (2008). Moving beyond Coltheart's N: A new measure of orthographic similarity. *Psychonomic Bulletin & Review*, 15, 971-979.
