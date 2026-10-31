# Datasets and Benchmarking

Targets aeon 1.6. Generic archive loaders may download data on first use; use an explicit writable `extract_path` to control caching. Bundled helpers such as `load_gunpoint`, `load_covid_3month`, and `load_airline` are convenient for offline checks. Archive download examples below are illustrative and were not executed in this review.

## Classification and regression

```python
from aeon.datasets import load_classification, load_regression

X_train, y_train = load_classification(
    "GunPoint", split="train", extract_path="data/aeon"
)
X_test, y_test = load_classification(
    "GunPoint", split="test", extract_path="data/aeon"
)
X_reg, y_reg, metadata = load_regression(
    "Covid3Month", split="train", extract_path="data/aeon", return_metadata=True
)
```

Equal-length collections normally have shape `(n_cases, n_channels, n_timepoints)`; unequal-length data use lists of 2D arrays. Check the returned metadata and estimator capabilities before padding, imputing, or normalizing. `Covid3Month` is a time-series **regression** benchmark with a target per case, not an API for rolling COVID forecasts.

```python
from aeon.datasets import load_gunpoint, load_covid_3month, load_airline

X_train, y_train = load_gunpoint(split="train")
X_test, y_test = load_gunpoint(split="test")
X_reg, y_reg = load_covid_3month(split="train")
y_airline = load_airline()
```

Aeon 1.6 classification/regression loaders resolve published TSML records on Zenodo. They inspect record metadata and download the record's files; a requested dataset can therefore entail more than a single small file. `download_all_regression(extract_path=...)` explicitly downloads the full archive and is unsuitable for a smoke test.

## Forecasting and anomaly archives

```python
from aeon.datasets import load_forecasting

# Returns a dataframe and metadata, not (y, exogenous_X).
frame, metadata = load_forecasting(
    "m1_yearly_dataset", extract_path="data/aeon", return_metadata=True
)
y = frame.iloc[0]["series_value"]
```

`load_forecasting` uses names from `aeon.datasets.tsf_datasets.tsf_all`, not arbitrary dataset nicknames; the `return_X_y` argument is unsupported. The default dataframe represents TSF records, with each series stored in its `series_value` field. Respect per-series forecast horizons/frequency from metadata.

```python
from aeon.datasets import load_anomaly_detection

X, labels = load_anomaly_detection(
    ("KDD-TSAD", "001_UCR_Anomaly_DISTORTED1sddb40"),
    split="test", extract_path="data/aeon",
)
```

The anomaly loader requires `(collection_name, dataset_name)`. It downloads a whole TimeEval collection ZIP when necessary; some datasets have no training split. Returned multivariate data are **timepoints by channels**, and labels are one binary indicator per timepoint. Pass `axis=0` to compatible series estimators. A test label file must not enter training or threshold calibration.

## Local file I/O

File examples are templates; supply your own paths. `.ts` writing and reading were tested with temporary synthetic data.

```python
from pathlib import Path
from aeon.datasets import (
    load_from_ts_file, load_from_tsf_file, load_from_arff_file,
    load_from_tsv_file, load_from_timeeval_csv_file, save_to_ts_file,
)

X, y = load_from_ts_file("data/example.ts")
frame, metadata = load_from_tsf_file("data/example.tsf")
X_arff, y_arff = load_from_arff_file("data/example.arff")
X_tsv, y_tsv = load_from_tsv_file("data/example.tsv")
X_time, anomaly_labels = load_from_timeeval_csv_file(Path("data/timeeval.csv"))

save_to_ts_file(
    X, y, label_type="classification", path="output", problem_name="MyDataset"
)
# Writes output/MyDataset.ts; use label_type="regression" for continuous targets.
```

`save_to_ts_file` requires `label_type` when labels are provided, and `path` is a directory. There is no public `write_to_ts_file` or `write_to_arff_file` in 1.6.

## Dataset metadata and discovery

The metadata service returns a dataframe, with case-sensitive column names:

```python
from aeon.datasets import get_dataset_meta_data

metadata = get_dataset_meta_data(data_names=["GunPoint"])
print(metadata[["Dataset", "TrainSize", "TestSize", "Length", "Channels"]])
all_metadata = get_dataset_meta_data()
univariate_names = all_metadata.loc[all_metadata["Channels"] == 1, "Dataset"].tolist()
```

This fetches `https://timeseriesclassification.com/aeon-toolkit/metadata.csv`. Use archive-specific public lists in `aeon.datasets.tsc_datasets`, `tser_datasets`, and `tsf_datasets`; `get_available_datasets("classification")` is not an aeon API. Metadata describes the published archive and is not a substitute for checking the loaded arrays.

## Published results

```python
from aeon.benchmarking.results_loaders import (
    get_available_estimators, get_estimator_results,
)

names = get_available_estimators(task="classification", as_list=True)
results = get_estimator_results(
    estimators="ROCKET", datasets=["GunPoint"], task="classification",
    measure="accuracy", num_resamples=1,
)
# Nested mapping: results[estimator][dataset] is a score for one resample,
# or an array when multiple resamples were requested.
```

The loader reads published CSVs under `https://timeseriesclassification.com/results/ReferenceResults`; task, metric, estimator alias and available resamples determine the file. These are public file downloads, without credentials or pagination. Missing dataset scores may be absent from the mapping. Match splits, resampling protocol, metric direction, hyperparameters, and compute budget before comparing your score to published results.

## Resampling and leakage

Preserve an archive's original split for a directly comparable benchmark. For a protocol explicitly requiring resamples, use:

```python
from aeon.benchmarking.resampling import stratified_resample_data

X_res_train, y_res_train, X_res_test, y_res_test = stratified_resample_data(
    X_train, y_train, X_test, y_test, random_state=42
)
```

This combines train and test, then makes a new split preserving original set sizes and class counts; it is not an ordinary training-only validation split. Never use it to tune against a test set that must remain untouched. Use sklearn validation tools inside training data instead, with group or temporal splitting for repeated subjects or overlapping windows. Keep supervised feature selection and augmentation inside each training fold.

## Metrics

```python
from aeon.benchmarking.metrics.anomaly_detection import (
    range_roc_auc_score,
)
from aeon.benchmarking.metrics.clustering import clustering_accuracy_score
from aeon.benchmarking.metrics.segmentation import count_error, hausdorff_error

auc = range_roc_auc_score(y_true, y_scores)  # continuous anomaly scores

# Arbitrary cluster IDs are optimally matched to class IDs.
accuracy = clustering_accuracy_score(class_labels, cluster_labels)

# Supply change-point locations, not dense state labels.
count_err = count_error(true_change_points, predicted_change_points)
hausdorff_err = hausdorff_error(true_change_points, predicted_change_points)
```

`range_precision`, `range_recall`, and `range_f_score` require `prts`; its current NumPy<2 requirement conflicts with aeon 1.6. Those APIs were source-checked but not executed; a standard resolver cannot install the combination. F-score uses `p_alpha`/`r_alpha`, whereas precision and recall use `alpha`.

Range metric tolerance/weighting can change conclusions: report buffer size and threshold-selection policy; report alpha, bias and cardinality if using range precision/recall in a separately validated environment. AUC requires both anomalous and normal targets for a meaningful evaluation. Handle empty change-point sets explicitly before Hausdorff evaluation.

## Statistical comparisons across datasets

Aeon's `wilcoxon_test` accepts a matrix `(n_datasets, n_estimators)` plus estimator names and returns an **upper-triangular matrix of one-sided p-values**, not `(statistic, p_value)`. Only entries above the diagonal are pairwise tests; lower-triangle zeros are placeholders. Nemenyi takes ordered average ranks and a dataset count; it does not take raw score arrays.

```python
import numpy as np
from scipy.stats import rankdata
from aeon.benchmarking.stats import check_friedman, nemenyi_test, wilcoxon_test

# Illustrative scores: rows are independent datasets, columns are estimators.
scores = np.array([[.81, .77, .75], [.72, .75, .68], [.92, .88, .85],
                   [.69, .66, .70], [.83, .81, .79], [.76, .73, .71]])
ranks = rankdata(-scores, axis=1)  # smaller rank = higher accuracy
friedman_p = check_friedman(ranks.T)
avg_ranks = ranks.mean(axis=0)
order = np.argsort(avg_ranks)
cliques = nemenyi_test(avg_ranks[order], n_datasets=len(scores), alpha=0.05)
p_values = wilcoxon_test(scores, ["A", "B", "C"], lower_better=False)
```

This code demonstrates API semantics, not evidence that any algorithm is superior. Check the omnibus test and pre-specified post-hoc protocol, account for multiplicity, and report effect sizes. Do not treat repeated resamples of the same dataset as independent datasets. Use `scipy.stats.wilcoxon(a, b, alternative="two-sided")` for a two-sided pairwise statistic and p-value.

Sources: [datasets API](https://www.aeon-toolkit.org/en/stable/api_reference/datasets.html), [dataset source](https://github.com/aeon-toolkit/aeon/blob/v1.6.0/aeon/datasets/_data_loaders.py), [results loaders](https://github.com/aeon-toolkit/aeon/blob/v1.6.0/aeon/benchmarking/results_loaders.py), [statistical tests](https://github.com/aeon-toolkit/aeon/blob/v1.6.0/aeon/benchmarking/stats.py). Archive data downloads were source-verified only; the metadata/results CSVs were also fetched read-only. Local I/O, resampling and metric examples were exercised with synthetic data.
