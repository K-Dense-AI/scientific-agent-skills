# GRN Inference Algorithms

Arboreto provides two high-level algorithms for gene regulatory network (GRN) inference, both based on the multiple regression approach.

## Algorithm Overview

Both algorithms follow the same inference strategy:
1. For each target gene in the dataset, train a regression model
2. Identify the most important features (potential regulators) from the model
3. Emit these features as candidate regulators with importance scores

The key difference is **computational efficiency** and the underlying regression method.

## GRNBoost2 (Recommended)

**Purpose**: Fast GRN inference for large-scale datasets using gradient boosting.

### When to Use
- **Large datasets**: Tens of thousands of observations (e.g., single-cell RNA-seq)
- **Time-constrained analysis**: Need faster results than GENIE3
- **Default choice**: GRNBoost2 is the flagship algorithm and recommended for most use cases

### Technical Details
- **Method**: Stochastic gradient boosting with early-stopping regularization
- **Performance**: Significantly faster than GENIE3 on large datasets
- **Output**: Same format as GENIE3 (TF-target-importance triplets)

### Usage
```python
from arboreto.algo import grnboost2

network = grnboost2(
    expression_data=expression_matrix,
    tf_names=tf_names,
    seed=42,
    limit=5000,
)
```

### Parameters (`grnboost2`)
```python
grnboost2(
    expression_data,              # DataFrame, ndarray, or scipy.sparse.csc_matrix
    gene_names=None,              # Required for ndarray/sparse inputs
    tf_names='all',                 # TF list, None/'all' → all genes as regulators
    client_or_address='local',      # 'local', scheduler address, or Dask Client
    early_stop_window_length=25,    # Early-stopping window (GRNBoost2 only)
    limit=None,                     # Return top N links globally
    seed=None,                      # Random seed; None = non-deterministic
    verbose=False,
)
```

## GENIE3

**Purpose**: Classic Random Forest-based GRN inference, serving as the conceptual blueprint.

### When to Use
- **Smaller datasets**: When dataset size allows for longer computation
- **Comparison studies**: When comparing with published GENIE3 results
- **Validation**: To validate GRNBoost2 results

### Technical Details
- **Method**: Random Forest regression (ExtraTrees available via `diy`)
- **Foundation**: Original multiple regression GRN inference strategy
- **Trade-off**: More computationally expensive but well-established

### Usage
```python
from arboreto.algo import genie3

network = genie3(
    expression_data=expression_matrix,
    tf_names=tf_names,
    seed=42,
)
```

### Parameters (`genie3`)
```python
genie3(
    expression_data,
    gene_names=None,
    tf_names='all',
    client_or_address='local',
    limit=None,
    seed=None,
    verbose=False,
)
```

## Algorithm Comparison

| Feature | GRNBoost2 | GENIE3 |
|---------|-----------|--------|
| **Speed** | Fast (optimized for large data) | Slower |
| **Method** | Gradient boosting (GBM) | Random Forest |
| **Best for** | Large-scale data (10k+ observations) | Small-medium datasets |
| **Output format** | Same | Same |
| **Inference strategy** | Multiple regression | Multiple regression |
| **Recommended** | Yes (default choice) | For comparison/validation |
| **Early stopping** | Yes (`early_stop_window_length`) | No |

## Advanced: Custom Regressors with `diy`

For custom scikit-learn regressor settings, use `diy()` (not `grnboost2`/`genie3` kwargs):

```python
from arboreto.algo import diy
from arboreto.core import SGBM_KWARGS, RF_KWARGS

# Custom GRNBoost2-style run
custom_gbm = diy(
    expression_data=expression_matrix,
    regressor_type='GBM',  # 'RF', 'GBM', or 'ET'
    regressor_kwargs={
        **SGBM_KWARGS,
        'n_estimators': 100,
        'max_depth': 5,
        'learning_rate': 0.1,
    },
    tf_names=tf_names,
    seed=42,
)

# Custom GENIE3-style run
custom_rf = diy(
    expression_data=expression_matrix,
    regressor_type='RF',
    regressor_kwargs={
        **RF_KWARGS,
        'n_estimators': 1000,
        'max_features': 'sqrt',
    },
    tf_names=tf_names,
)
```

Import default kwargs from `arboreto.core` and override only the keys you need.

## Choosing the Right Algorithm

**Decision guide**:

1. **Start with GRNBoost2** — faster and better suited to large single-cell datasets
2. **Use GENIE3 if**:
   - Comparing with existing GENIE3 publications
   - Dataset is small-medium sized
   - Validating GRNBoost2 results
3. **Use `diy()` if** you need non-default regressor hyperparameters

Both algorithms produce comparable regulatory networks with the same output format.
