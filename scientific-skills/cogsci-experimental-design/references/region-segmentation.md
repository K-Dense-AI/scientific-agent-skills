# Region Segmentation for Self-Paced Reading

This reference provides detailed guidance on how to segment sentences into reading regions for self-paced reading (SPR) experiments. Region boundaries are the most consequential design decision in SPR because they determine what can be measured and what will be confounded.

---

## Fundamental Principles

### 1. Regions Must Respect Syntactic Constituency

Never split a region in the middle of a syntactic constituent. A region boundary within a noun phrase (e.g., splitting "the tall" from "man") forces participants to process an incomplete constituent, introducing processing difficulty that is an artifact of segmentation rather than a reflection of the intended manipulation (Jegerski, 2014).

**Good segmentation** (respects constituency):

```
The maid | of the actress | who was | on the balcony | shouted | to the crowd.
```

**Bad segmentation** (splits constituents):

```
The maid of | the actress who | was on | the balcony shouted | to the | crowd.
```

### 2. Critical Regions Must Be Controlled

The critical region -- where you expect to observe a reading time difference between conditions -- must be matched across conditions on:

| Property | How to Match | Source for Norms |
|---|---|---|
| **Word length (characters)** | Within +/- 1 character across conditions | Count characters |
| **Lexical frequency** | Within 0.5 log10 units (SUBTLEX-US) | Brysbaert & New (2009); SUBTLEX-US database |
| **Number of syllables** | Same syllable count preferred | Standard dictionaries |
| **Morphological complexity** | Same number of morphemes preferred | Linguistic analysis |
| **Part of speech** | Identical across conditions | Linguistic analysis |
| **Orthographic neighborhood size** | Match if feasible | English Lexicon Project (Balota et al., 2007) |

If the same word appears in the critical region across all conditions (e.g., an ambiguity resolves on a word that is identical but disambiguates due to prior context), length and frequency matching is automatic. This is the ideal design.

### 3. Pre-Critical and Post-Critical (Spillover) Regions Must Be Identical

The words immediately before and after the critical region should be character-for-character identical across conditions. This is essential because:

- **Pre-critical region**: Any difference here creates a baseline shift that propagates into the critical region via spillover (Mitchell, 2004)
- **Post-critical (spillover) region**: Effects from the critical word reliably appear 1-3 words downstream in SPR (Just et al., 1982; Rayner, 1998). If spillover regions differ across conditions, you cannot attribute reading time differences to the critical manipulation

### 4. Avoid Clause and Sentence Boundaries in Critical Regions

Wrap-up effects inflate reading times at clause-final and sentence-final words by **50-100+ ms** (Just & Carpenter, 1980; Warren, White, & Reichle, 2009). This inflation is independent of experimental condition and adds noise that reduces statistical power. Additionally, clause-final words often co-occur with punctuation (commas, periods), which introduces visual complexity unrelated to your manipulation.

**Rule**: Place the critical region at least 2 words before any clause or sentence boundary.

---

## Segmentation Strategies by Construction Type

### Garden-Path Sentences

Garden-path sentences temporarily mislead the parser. The critical region is typically the disambiguation point.

**Example**: Main verb / reduced relative ambiguity

Condition A (ambiguous):
```
The horse | raced | past the barn | fell | down | the hill.
 pre-crit CRIT spill1 spill2 spill3
```

Condition B (unambiguous control):
```
The horse | that was raced | past the barn | fell | down | the hill.
 pre-crit CRIT spill1 spill2
```

**Key considerations**:
- The critical word "fell" is identical across conditions -- this is ideal
- Spillover regions ("down the hill") are identical
- In condition B, the relative clause marker "that was raced" makes the structure unambiguous before the critical region
- The garden-path effect (longer RT in condition A at "fell") may spill over to "down" and even "the hill"

### Relative Clause Attachment

Relative clause attachment ambiguity (high vs. low attachment) typically manipulates the plausibility or gender match of the relative clause with one of two potential hosts.

**Example**: High vs. low attachment

```
The maid | of the actress | who was | sitting | on the | balcony | spoke loudly.
 R1 R2 R3 CRIT spill1 spill2 wrap-up
```

**Key considerations**:
- The critical region is the verb inside the relative clause ("sitting") where semantic fit disambiguates attachment
- "on the balcony" serves as spillover
- "spoke loudly" is the wrap-up region -- do NOT analyze this as spillover because it includes sentence-final wrap-up effects
- The two host nouns ("maid" and "actress") must be matched for length and frequency
- If the disambiguation depends on semantic fit (e.g., "who was knitting" fits better with "actress"), the critical verbs across conditions must be matched for length and frequency

### Filler-Gap Dependencies

In filler-gap constructions, a moved element (the filler) is interpreted at a later position (the gap). The critical region is the gap site.

**Example**: Object relative with gap

```
The book | that the author | wrote _ | in the | library | was | a bestseller.
 filler intervener GAP spill1 spill2 spill3 wrap-up
```

Control: Subject relative (no object gap)

```
The author | that _ wrote | the book | in the | library | was | quite famous.
 GAP post-gap spill1 spill2 spill3 wrap-up
```

**Key considerations**:
- Compare reading times at the verb ("wrote") and spillover regions across the two structures
- The gap site is implicit (no overt marker), so the parser must posit a gap based on syntactic expectations
- Spillover regions must be identical or closely matched because gap-filling effects propagate downstream (Stowe, 1986)

### Verb Argument Structure

When manipulating subcategorization or argument structure expectations, the critical region is typically the post-verbal material where the argument structure becomes clear.

**Example**: Transitive vs. intransitive bias

```
The doctor | hoped | the patient | would recover | quickly | from | the illness.
 verb CRIT spill1 spill2 spill3 wrap-up
```

```
The doctor | examined | the patient | would recover | quickly | from | the illness.
 verb CRIT spill1 spill2 spill3 wrap-up
```

**Key considerations**:
- "hoped" is intransitive-biased: "the patient" is unexpected as a direct object
- "examined" is transitive-biased: "the patient" is expected as a direct object
- The critical region ("the patient") is identical across conditions
- The verbs differ across conditions -- they must be matched for length and frequency
- The pre-critical verb is the only word that differs, so any RT difference at "the patient" or spillover must be due to the verb's argument structure bias

### Agreement and Morphosyntactic Violations

For studies of grammatical agreement or morphosyntactic processing, the critical region is the word where the violation becomes apparent.

**Example**: Subject-verb number agreement

Grammatical:
```
The key | to the cabinets | was | rusty | and | old.
 subj intervener CRIT spill1 spill2 spill3
```

Ungrammatical:
```
The key | to the cabinets | were | rusty | and | old.
 subj intervener CRIT spill1 spill2 spill3
```

**Key considerations**:
- "was" vs. "were" differ by one character -- this is an acceptable minimal difference
- The intervening noun ("cabinets") creates an attraction environment that is part of the manipulation
- Spillover regions must be identical across conditions
- With agreement violations, effects are often largest in the spillover region (Pearlmutter, Garnsey, & Bock, 1999), not the critical word itself

---

## Word-by-Word vs. Phrase-by-Phrase: When to Choose Each

### Word-by-Word

Use word-by-word presentation (the default and most common method) when:

- You need maximal temporal resolution
- The critical manipulation is localized to a single word
- You want to track spillover word-by-word
- You need comparability with the existing SPR literature

### Phrase-by-Phrase

Use phrase-by-phrase presentation when:

- The critical manipulation spans a multi-word constituent (e.g., an entire PP or relative clause)
- Word-by-word presentation would break up a tightly bound phrase unnaturally
- You are studying phrase-level prosodic or structural effects

When using phrase-by-phrase, follow these rules:

1. **Segment at constituent boundaries.** Every region must be a complete syntactic constituent (NP, VP, PP, clause)
2. **Match region length (in words and characters) across conditions.** If condition A has a 4-word critical region and condition B has a 3-word critical region, the length difference confounds the comparison
3. **Report your segmentation criteria explicitly.** Phrase-by-phrase segmentation is more subjective than word-by-word. Readers of your paper need to evaluate whether your boundaries are defensible

---

## Controlling for Confounds Within Regions

### Word Length

Reading time in SPR increases approximately **30-40 ms per additional character** (Ferreira & Clifton, 1986; Trueswell, Tanenhaus, & Garnsey, 1994). This means a 2-character difference between conditions at the critical word creates a **60-80 ms confound** -- often larger than the effect of interest.

**Solutions** (in order of preference):
1. Use identical words in the critical region across conditions (best)
2. Match word length exactly (within +/- 1 character)
3. Include word length as a covariate in the statistical model
4. Use residual reading times (Ferreira & Clifton, 1986)

### Word Frequency

Low-frequency words take longer to read than high-frequency words. The frequency effect in SPR is approximately **20-40 ms per log unit** of frequency difference (Rayner, 1998; Inhoff & Rayner, 1986).

**Solutions**:
1. Use identical words in the critical region across conditions (best)
2. Match on log-transformed word frequency (SUBTLEX-US; Brysbaert & New, 2009)
3. Include log frequency as a covariate in the statistical model

### Word Position in Sentence

Reading times are typically slower for the first 2-3 words of a sentence (start-up cost) and inflated at the final 1-2 words (wrap-up; Just & Carpenter, 1980). Avoid placing critical regions in these positions.

**Safe zone**: Words 3 through (sentence_length - 3) are least affected by positional artifacts.

---

## Example: Complete Segmentation with Region Labels

**Study**: Effect of verb bias on complement clause processing

Condition A (SC-biased verb):
```
Position: R1 R2 R3-CRIT R4-spill1 R5-spill2 R6-wrap
Sentence: The coach | knew | the team | would travel | to the game | on Friday.
```

Condition B (DO-biased verb):
```
Position: R1 R2 R3-CRIT R4-spill1 R5-spill2 R6-wrap
Sentence: The coach | told | the team | would travel | to the game | on Friday.
```

- **R1** (pre-verb context): Identical across conditions
- **R2** (verb): Differs across conditions -- "knew" (4 chars) vs. "told" (4 chars) -- matched for length. Must also match frequency.
- **R3** (critical region): "the team" is identical -- this is where the sentence-complement interpretation becomes clear for DO-biased "told" but not SC-biased "knew"
- **R4-R5** (spillover): Identical across conditions
- **R6** (wrap-up): Do not analyze as spillover due to sentence-final wrap-up effects

---

## References

- Balota, D. A., et al. (2007). The English Lexicon Project. *Behavior Research Methods, 39*, 445-459.
- Brysbaert, M., & New, B. (2009). Moving beyond Kucera and Francis. *Behavior Research Methods, 41*, 977-990.
- Ferreira, F., & Clifton, C. (1986). The independence of syntactic processing. *Journal of Memory and Language, 25*, 348-368.
- Inhoff, A. W., & Rayner, K. (1986). Parafoveal word processing during eye fixations in reading. *Perception & Psychophysics, 40*, 431-439.
- Jegerski, J. (2014). Self-paced reading. In J. Jegerski & B. VanPatten (Eds.), *Research methods in second language psycholinguistics*. Routledge.
- Just, M. A., & Carpenter, P. A. (1980). A theory of reading: From eye fixations to comprehension. *Psychological Review, 87*, 329-354.
- Just, M. A., Carpenter, P. A., & Woolley, J. D. (1982). Paradigms and processes in reading comprehension. *Journal of Experimental Psychology: General, 111*, 228-238.
- Keating, G. D., & Jegerski, J. (2015). Experimental designs in sentence processing research. *Studies in Second Language Acquisition, 37*, 1-32.
- Mitchell, D. C. (2004). On-line methods in language processing. In M. Carreiras & C. Clifton (Eds.), *The on-line study of sentence comprehension*. Psychology Press.
- Pearlmutter, N. J., Garnsey, S. M., & Bock, K. (1999). Agreement processes in sentence comprehension. *Journal of Memory and Language, 41*, 427-456.
- Rayner, K. (1998). Eye movements in reading and information processing. *Psychological Bulletin, 124*, 372-422.
- Stowe, L. A. (1986). Parsing WH-constructions: Evidence for on-line gap location. *Language and Cognitive Processes, 1*, 227-245.
- Trueswell, J. C., Tanenhaus, M. K., & Garnsey, S. M. (1994). Semantic influences on parsing. *Journal of Memory and Language, 33*, 285-318.
- Warren, T., White, S. J., & Reichle, E. D. (2009). Investigating the causes of wrap-up effects. *Cognition, 111*, 132-137.
