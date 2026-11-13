---
name: proteingym
description: Evaluates protein fitness prediction and deep mutational scanning (DMS) benchmarks following ProteinGym conventions. Computes zero-shot and supervised variant-effect metrics (Spearman rho, ROC-AUC, MCC, NDCG, Top-K recall), parses colon-delimited multi-mutant strings, stratifies performance by mutation depth or active-site distance, generates position-disjoint cross-validation splits (random, modulo, contiguous), and quantifies pairwise mutational epistasis. Use when benchmarking protein language models, inverse folding models, stability predictors, or enzyme engineering variant rankings on DMS or clinical variant datasets.
license: MIT
compatibility: Bundled evaluation, epistasis, and split-generation CLI scripts use Python 3.10+ standard library only and run offline without external packages.
allowed-tools: Read Write Edit Bash
metadata:
  version: "1.0"
  skill-author: Xing Jiang
---

# ProteinGym Fitness & Epistasis Benchmarking

## When to Use

Use this skill when working with deep mutational scanning (DMS) assays, clinical variant benchmarks, or computational enzyme/protein engineering variant rankings:

- Evaluating zero-shot or supervised fitness predictions using the five standard ProteinGym metrics (`Spearman`, `AUC`, `MCC`, `NDCG`, `Top_recall`).
- Parsing and validating ProteinGym substitution strings (`A12P:D45N`, `WT`, 1-indexed positions) against wild-type target sequences.
- Stratifying variant prediction accuracy across mutation depths (single vs double vs higher-order mutants) or structural shells around catalytic active sites (`< 5 A`, `5-10 A`, `> 10 A`).
- Generating position-disjoint supervised cross-validation folds (`contiguous` and `modulo` vs `random`) to prevent additive residue-level data leakage.
- Quantifying pairwise mutational epistasis ($\varepsilon_{ij} = \Delta y_{ij} - \Delta y_i - \Delta y_j$), magnitude vs sign epistasis, and epistasis rank recovery.

For detailed metric equations, dataset column schemas, and split rules, see [references/metrics_and_splits.md](references/metrics_and_splits.md).

## Bundled Command-Line Tooling

The bundled script [scripts/evaluate_dms.py](scripts/evaluate_dms.py) uses only the Python standard library and runs offline on any ProteinGym-formatted CSV file.

| Flag | Purpose |
| --- | --- |
| `--input PATH` | Path to DMS CSV containing `mutant`, `DMS_score`, optional `DMS_score_bin`, and model score column |
| `--pred-col COL` | Column name of model fitness predictions (higher must mean fitter; negate raw ddG first) |
| `--negate-pred` | Multiply `--pred-col` by `-1` before scoring (use for $\Delta\Delta G$ or energy-based predictors) |
| `--dms-col COL` | Experimental continuous fitness column (default: `DMS_score`) |
| `--bin-col COL` | Binary fitness label column `0`/`1` (default: `DMS_score_bin` if present) |
| `--wt-seq SEQ` | Optional 1-indexed wild-type amino acid sequence for strict mutant validation |
| `--epistasis` | Compute pairwise epistasis $\varepsilon_{ij}$ across all double mutants with measured singles |
| `--wt-score FLOAT` | Wild-type experimental score baseline $y_{\text{WT}}$ for epistasis (default: `0.0` or `WT` row) |
| `--wt-pred FLOAT` | Wild-type predicted score baseline $\hat{y}_{\text{WT}}$ for predicted epistasis comparison |
| `--residue-distances PATH` | Optional CSV (`position,distance_angstrom`) to stratify metrics by active-site shell |
| `--split-out PATH` | Write deterministic CV fold assignments (`random`, `modulo`, `contiguous`) to CSV |
| `--split-scheme SCHEME` | Cross-validation split scheme: `random`, `modulo`, or `contiguous` (default: `modulo`) |
| `--json-out PATH` | Save structured metrics, depth breakdown, and epistasis report to JSON |

## Standard Workflow

### 1. Verify Input Schema and Sign Orientation

1. Inspect the assay CSV headers (`mutant`, `mutated_sequence`, `DMS_score`, `DMS_score_bin`, plus model score columns).
2. Confirm sign orientation before computing rank or top-quantile metrics:
   - In ProteinGym, **higher `DMS_score` always indicates higher experimental fitness** (catalytic activity, kcat/Km, growth enrichment, or stability).
   - Protein language model log-likelihood ratios ($\log P(x_{\text{mut}}) - \log P(x_{\text{WT}})$) are already positively oriented.
   - Physics or stability folding energies ($\Delta\Delta G$ in kcal/mol, where negative values stabilize) MUST be negated (`--negate-pred`) before computing `NDCG` or `Top_recall`; otherwise top-quantile metrics evaluate the most destabilizing variants instead of the fittest variants.
3. Pass `--wt-seq` whenever the wild-type target sequence is available so off-by-one indexing errors (0-based vs 1-based residue numbering) fail immediately with `[FAIL]` instead of silently corrupting site stratification.

### 2. Run Zero-Shot or Supervised Metric Evaluation

Execute [scripts/evaluate_dms.py](scripts/evaluate_dms.py) on an assay CSV:

```bash
python skills/proteingym/scripts/evaluate_dms.py \
  --input assay_scores.csv \
  --pred-col esm2_llr \
  --dms-col DMS_score \
  --bin-col DMS_score_bin \
  --epistasis \
  --wt-score 0.0 \
  --wt-pred 0.0 \
  --json-out evaluation_summary.json
```

Console diagnostics use portable ASCII markers (`[OK]`, `[FAIL]`, `->`):

```text
[OK] Loaded 1240 valid variants (single=980, double=260)
-> Spearman rho: 0.5842 | NDCG@10%: 0.7915 | Top-10% Recall: 0.4677
-> Binary metrics: ROC-AUC: 0.8124 | MCC: 0.4910
[OK] Pairwise epistasis evaluated on 245 complete double-mutant cycles
```

### 3. Stratify Enzyme DMS Assays by Active-Site Shell

In enzyme engineering benchmarks, whole-protein Spearman $\rho$ is frequently dominated by trivial core-destabilizing mutations far from the catalytic pocket. Separate stability filtering from catalytic tuning by supplying minimum heavy-atom or $C_\alpha$ distances to the catalytic residues / cofactor (`position,distance_angstrom`):

```bash
python skills/proteingym/scripts/evaluate_dms.py \
  --input tpl_dms.csv \
  --pred-col model_score \
  --residue-distances active_site_distances.csv
```

This reports metrics separately across three structural regimes:
- **First shell (`< 5.0 A`)**: Direct substrate/cofactor contact and catalytic residues (highest epistasis, lowest zero-shot PLM conservation accuracy).
- **Second shell (`5.0 - 10.0 A`)**: Pocket-shaping and loop-positioning residues (prime targets for activity/selectivity tuning).
- **Distal shell (`> 10.0 A`)**: Global folding stability and surface solubility mutations.

### 4. Generate Leakage-Free Supervised Splits

When training ridge regression, GP heads, or ProteinNPT/LoRA models on DMS embeddings, never evaluate generalization solely on random splits:

```bash
python skills/proteingym/scripts/evaluate_dms.py \
  --input assay_scores.csv \
  --pred-col esm2_llr \
  --split-scheme contiguous \
  --n-folds 5 \
  --split-out assay_with_folds.csv
```

- `random`: Variants assigned across folds regardless of position (measures interpolation across known positions).
- `modulo`: Mutated residue positions assigned via `position % n_folds` (zero shared single-mutant positions across folds).
- `contiguous`: Protein sequence partitioned into `n_folds` contiguous structural segments (tests extrapolation to unseen regions). Multi-mutants spanning two folds are tagged `cross_fold` (`cv_fold = -1`) so they are excluded from training when testing strict position-disjoint generalization.

## Scientific Caveats & Validation Rules

1. **Hierarchical Aggregation Across Assays**: ProteinGym contains multiple DMS assays for certain heavily studied proteins. When benchmarking across multiple CSVs, average metrics **per UniProt ID first**, then compute macro-averages across functional categories (Activity, Binding, Expression, Organismal Fitness, Stability) so multi-assay proteins do not overweight the benchmark mean.
2. **NDCG Gain Shifting**: Experimental `DMS_score` values often include negative log-enrichment ratios. Standard NDCG requires non-negative relevance gains; following ProteinGym conventions, shift gains per assay via $g_i = (y_i - y_{\min}) / (y_{\max} - y_{\min})$ before discounting by $\log_2(\text{rank}_i + 1)$ over the top predicted quantile.
3. **Specific vs Global Epistasis**: Non-zero $\varepsilon_{ij} = (y_{ij} - y_{\text{WT}}) - (y_i - y_{\text{WT}}) - (y_j - y_{\text{WT}})$ can arise from either biophysical residue coupling (specific epistasis) or a nonlinear sigmoid mapping between folding free energy and experimental readout (global/nonspecific epistasis). Prioritize **sign epistasis** and **reciprocal sign epistasis** counts when identifying genuine active-site conformational coupling.

## Demo Verification

Run the built-in self-check demo without external data files:

```bash
python skills/proteingym/scripts/evaluate_dms.py
```
