# ProteinGym Schemas, Metrics, and Cross-Validation Reference

## 1. Dataset Configurations and Column Contracts

Official ProteinGym v1 benchmarks (`OATML-Markslab/ProteinGym` on GitHub and `OATML-Markslab/ProteinGym_v1` on Hugging Face) organize variant assays into four configurations:

| Configuration | Variant Type | Target Column | Binary Label Column | Key Identifier Columns |
| --- | --- | --- | --- | --- |
| `DMS_substitutions` | Single & multi-point amino acid substitutions | `DMS_score` (float, higher = fitter) | `DMS_score_bin` (`1` = fit, `0` = not fit) | `DMS_id`, `mutant`, `mutated_sequence`, `target_seq` |
| `DMS_indels` | Insertions and deletions | `DMS_score` (float, higher = fitter) | `DMS_score_bin` (`1` = fit, `0` = not fit) | `DMS_id`, `mutated_sequence`, `target_seq` |
| `clinical_substitutions` | Human missense clinical variants | None (categorical only) | `annotation` / binary pathogenic label | `protein_id`, `mutant`, `mutated_sequence` |
| `clinical_indels` | Human clinical indels | None (categorical only) | `annotation` / binary pathogenic label | `protein_id`, `mutated_sequence` |

### Colon-Delimited Substitution Syntax (`mutant`)
- Single substitution: `<WT_AA><1_based_pos><MUT_AA>` (e.g., `A1P` replaces Alanine at residue 1 with Proline).
- Multiple substitutions: Colon-joined tokens sorted by position, e.g., `A1P:D2N:K114R`.
- Wild-type reference row (when present in combinatorial libraries): `WT`.

## 2. Mathematical Definitions of the Five Standard Metrics

Let $y = (y_1, \dots, y_N)$ denote experimental `DMS_score`, $b \in \{0, 1\}^N$ denote `DMS_score_bin`, and $\hat{y} = (\hat{y}_1, \dots, \hat{y}_N)$ denote model fitness scores oriented such that higher $\hat{y}_i$ predicts higher fitness.

1. **Spearman Rank Correlation ($\rho$)**:
   Assign midranks $R(y)$ and $R(\hat{y})$ (averaging ranks across tied values) and compute Pearson correlation on the midranks.
2. **Area Under the ROC Curve (`AUC`)**:
   Computed between continuous $\hat{y}$ and binary $b \in \{0, 1\}$ via the tie-aware Mann-Whitney U statistic.
3. **Matthews Correlation Coefficient (`MCC`)**:
   Thresholding the top $N_+$ predictions (matching assay positive prevalence $N_+ / N$) to evaluate balanced binary classification.
4. **Normalized Discounted Cumulative Gain at Top Quantile (`NDCG@q`, default $q = 0.10$)**:
   Shift experimental scores to $[0, 1]$ relevance gains $g_i = (y_i - y_{\min}) / (y_{\max} - y_{\min})$, take $K = \max(1, \lfloor q N \rfloor)$, compute $\text{DCG}@K = \sum_{r=1}^K g_{\pi(r)} / \log_2(r + 1)$, and normalize by ideal $\text{IDCG}@K$.
5. **Top-Quantile Recall (`Top_recall@q`, default $q = 0.10$)**:
   Fraction of true top-$K$ experimental variants captured within the predicted top-$K$ set ($K = \max(1, \lfloor q N \rfloor)$).

## 3. Pairwise Epistasis Classification

For a double mutant $AB$ carrying substitutions $A$ and $B$ with wild-type score $y_{\text{WT}}$:
- Single-mutant effects: $\Delta y_A = y_A - y_{\text{WT}}$, $\Delta y_B = y_B - y_{\text{WT}}$
- Double-mutant effect: $\Delta y_{AB} = y_{AB} - y_{\text{WT}}$
- Pairwise epistasis: $\varepsilon_{AB} = \Delta y_{AB} - (\Delta y_A + \Delta y_B) = y_{AB} - y_A - y_B + y_{\text{WT}}$

Regime classification (with tolerance $\delta \ge 0$):
- **Reciprocal sign epistasis**: Conditional fitness effect of *both* mutations flips sign in the partner background.
- **Sign epistasis**: Conditional fitness effect of *one* mutation flips sign in the partner background.
- **Positive / Negative magnitude epistasis**: Conditional effects keep their signs with $\varepsilon_{AB} > \delta$ or $\varepsilon_{AB} < -\delta$.

## 4. Supervised Cross-Validation Folding Rules

- `random`: Deterministic hash assignment across rows (measures interpolation across observed positions).
- `modulo`: Mutated position $p$ assigned to $p \bmod F$; cross-fold multi-mutants receive `cv_fold = -1`.
- `contiguous`: Observed mutated positions partitioned into $F$ contiguous segments; cross-segment multi-mutants receive `cv_fold = -1`.
