# Divergent Thinking Scoring Rubric and Training Materials

## Subjective Originality Rating Rubric

### 5-Point Scale (Silvia et al., 2008)

| Score | Label | Description | Anchor Example (Object: Brick) |
|-------|-------|-------------|-------------------------------|
| 1 | Not at all creative | Common, conventional use; first thing most people would think of | "Build a wall" |
| 2 | Slightly creative | Somewhat unusual but still a plausible common use | "Use as a doorstop" |
| 3 | Moderately creative | Uncommon use that requires some imaginative thinking | "Grind into powder for pigment" |
| 4 | Very creative | Novel and unexpected use; clever repurposing | "Carve into a stamp for printing" |
| 5 | Exceptionally creative | Highly original, surprising, and well-articulated | "Heat and use as a therapeutic warmer for sore muscles" |

### Rater Training Procedure

1. **Provide the rubric** with 5-10 anchor examples per score level
2. **Practice round**: Raters independently score 20-30 responses
3. **Calibration meeting**: Discuss discrepancies, resolve disagreements, refine understanding
4. **Second practice round**: Score another 20-30 responses
5. **Reliability check**: Compute ICC; proceed if ICC ≥ 0.70 (Shrout & Fleiss, 1979)
6. **If ICC < 0.70**: Additional training and calibration until criterion is met
7. **Production scoring**: Score all responses independently; do NOT discuss scores during production

### Reliability Computation

**Recommended ICC model** (Shrout & Fleiss, 1979):

- **ICC(2,k)** — Two-way random effects, average measures: Use when raters are a random sample from a larger population of possible raters, and you will average scores across raters
- **ICC(3,k)** — Two-way mixed effects, average measures: Use when raters are the specific raters of interest (most common in practice)

**Benchmarks** (Cicchetti, 1994):
| ICC | Interpretation |
|-----|----------------|
| < 0.40 | Poor |
| 0.40 - 0.59 | Fair |
| 0.60 - 0.74 | Good |
| 0.75 - 1.00 | Excellent |

Lee & Chung (2024) achieved:
- Fluency ICC = 0.89
- Flexibility ICC = 0.85
- Originality ICC = 0.72

## Statistical Rarity Scoring Procedure

### Step-by-Step

1. **Collect all responses** across all participants
2. **Normalize text**:
 - Lowercase all responses
 - Remove leading/trailing whitespace
 - Correct obvious typos
 - Merge synonyms (e.g., "door stop" = "doorstop")
 - Lemmatize when appropriate (e.g., "building" = "build")
3. **Compute frequency** of each unique (normalized) response
4. **Apply threshold**: Mark as original if frequency < 5% of total participants
5. **Compute per-participant score**:
 - Sum: total number of original responses
 - Proportion: original responses / total responses (controls for fluency)

### Example

Sample size N = 100, Object = Brick

| Response (normalized) | Frequency | % | Original? |
|----------------------|-----------|---|-----------|
| build a wall | 45 | 45% | No |
| doorstop | 22 | 22% | No |
| paperweight | 18 | 18% | No |
| weapon/throw | 15 | 15% | No |
| grinding surface | 3 | 3% | **Yes** |
| heated massage stone | 1 | 1% | **Yes** |
| aquarium decoration | 2 | 2% | **Yes** |

## Semantic Distance Computation Guide

### Using SemDis Platform (Beaty & Johnson, 2021)

1. Go to https://semdis.wlu.psu.edu/
2. Upload a CSV with columns: `participant_id`, `prompt_word`, `response`
3. Select model: **GloVe Common Crawl 300d** (recommended default)
4. Download results: each response gets a cosine distance score

### Manual Computation (Python)

```python
# Pseudocode for semantic distance computation
# Requires: gensim or custom GloVe loader

import numpy as np

def cosine_distance(vec1, vec2):
 """1 - cosine similarity = cosine distance"""
 sim = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
 return 1 - sim

def response_vector(response, model):
 """Average word vectors for multi-word response"""
 words = response.lower().split()
 vectors = [model[w] for w in words if w in model]
 if not vectors:
 return None # OOV response
 return np.mean(vectors, axis=0)

def semantic_distance(prompt, response, model):
 """Compute semantic distance between prompt and response"""
 prompt_vec = model[prompt.lower()]
 resp_vec = response_vector(response, model)
 if resp_vec is None:
 return None # Flag for manual review
 return cosine_distance(prompt_vec, resp_vec)
```

### Handling Edge Cases

| Edge Case | Solution |
|-----------|----------|
| Response word not in vocabulary | Flag for manual scoring; do not impute |
| Multi-word response | Average word vectors (Beaty & Johnson, 2021) |
| Very short response (1 word) | Use the single word vector directly |
| Ambiguous response | Keep as-is; semantic distance handles ambiguity implicitly |
| Non-English response | Use language-appropriate embedding model |

## Composite Scoring Approaches

### Option 1: Report All Dimensions Separately (Recommended)

Report fluency, flexibility, originality, and semantic distance as separate DVs. This is the most transparent approach and allows readers to assess which dimensions drive effects.

### Option 2: Creativity Quotient (Snyder et al., 2004)

CQ = (Originality sum × Flexibility) / Fluency

Penalizes high fluency without corresponding quality. Less commonly used but addresses the fluency confound.

### Option 3: Top-N Scoring (Silvia et al., 2008)

Average the subjective creativity ratings of only the top 2 (or 3) most creative responses per participant. This:
- Controls for fluency differences
- Captures peak creative ability
- Has good psychometric properties
- Is the **recommended method** when creative quality is the primary outcome
