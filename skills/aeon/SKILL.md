---
name: aeon
description: This skill should be used for time series machine learning tasks including classification, regression, clustering, forecasting, anomaly detection, segmentation, and similarity search. Use when working with temporal data, sequential patterns, or time-indexed observations requiring specialized algorithms beyond standard ML approaches. Particularly suited for univariate and multivariate time series analysis with scikit-learn compatible APIs.
license: BSD-3-Clause license
allowed-tools: Read Write Edit Bash
compatibility: Requires Python 3.10+ and the aeon package (uv pip install). Optional aeon[all_extras] for deep learning and extended dependencies.
metadata:
  version: "1.0"
  skill-author: K-Dense Inc.
---

# Aeon Time Series Machine Learning

## Overview

Aeon is a scikit-learn compatible Python toolkit for time series machine learning ([aeon-toolkit.org](https://www.aeon-toolkit.org/)). It provides algorithms across classification, regression, clustering, forecasting, anomaly detection, segmentation, similarity search, distances, transformations, benchmarking, and visualization — with a consistent estimator API.

**Version note:** Examples target **aeon 1.x** (stable docs: v1.4.0, March 2026). The v1.0 release reworked forecasting and transformations; import paths differ from aeon 0.x/sktime-era code.

## When to Use This Skill

Apply this skill when:
- Classifying or predicting from time series data
- Detecting anomalies or change points in temporal sequences
- Clustering similar time series patterns
- Forecasting future values
- Finding repeated patterns (motifs) or unusual subsequences (discords)
- Comparing time series with specialized distance metrics
- Extracting features from temporal data

## Installation

Requires **Python 3.10+** (3.11+ recommended). Pin a 1.x release for reproducibility:

```bash
uv pip install "aeon>=1.4,<2"
```

For deep learning forecasters/classifiers and other optional estimators:

```bash
uv pip install "aeon[all_extras]>=1.4,<2"
```

On zsh, quote the extras: `uv pip install "aeon[all_extras]>=1.4,<2"`.

### Experimental modules

Upstream treats **forecasting**, **anomaly_detection**, **segmentation**, **similarity_search**, and **visualisation** as experimental — interfaces may change between minor releases. Prefer stable modules (classification, regression, clustering, distances, transformations) for production pipelines unless you need these tasks.

## Core Capabilities

### 1. Time Series Classification

Categorize time series into predefined classes. See `references/classification.md` for complete algorithm catalog.

**Quick Start:**
```python
from aeon.classification.convolution_based import RocketClassifier
from aeon.datasets import load_classification

# Load data
X_train, y_train = load_classification("GunPoint", split="train")
X_test, y_test = load_classification("GunPoint", split="test")

# Train classifier
clf = RocketClassifier(n_kernels=10000)
clf.fit(X_train, y_train)
accuracy = clf.score(X_test, y_test)
```

**Algorithm Selection:**
- **Speed + Performance**: `MiniRocketClassifier`, `Arsenal`
- **Maximum Accuracy**: `HIVECOTEV2`, `InceptionTimeClassifier`
- **Interpretability**: `ShapeletTransformClassifier`, `Catch22Classifier`
- **Small Datasets**: `KNeighborsTimeSeriesClassifier` with DTW distance

### 2. Time Series Regression

Predict continuous values from time series. See `references/regression.md` for algorithms.

**Quick Start:**
```python
from aeon.regression.convolution_based import RocketRegressor
from aeon.datasets import load_regression

X_train, y_train = load_regression("Covid3Month", split="train")
X_test, y_test = load_regression("Covid3Month", split="test")

reg = RocketRegressor()
reg.fit(X_train, y_train)
predictions = reg.predict(X_test)
```

### 3. Time Series Clustering

Group similar time series without labels. See `references/clustering.md` for methods.

**Quick Start:**
```python
from aeon.clustering import TimeSeriesKMeans

clusterer = TimeSeriesKMeans(
    n_clusters=3,
    distance="dtw",
    averaging_method="ba"
)
labels = clusterer.fit_predict(X_train)
centers = clusterer.cluster_centers_
```

### 4. Forecasting

Predict future time series values (experimental module in aeon 1.x). See `references/forecasting.md` for forecasters.

**Quick Start:**
```python
import numpy as np
from aeon.forecasting import NaiveForecaster
from aeon.forecasting.stats import ARIMA

y_train = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])

# Set horizon in the constructor; predict passes the series to forecast from
naive = NaiveForecaster(strategy="last", horizon=5)
naive.fit(y_train)
y_pred = naive.predict(y_train)

# ARIMA uses p/d/q (not order=); multi-step via iterative_forecast
arima = ARIMA(p=1, d=1, q=1)
arima.fit(y_train)
y_pred = arima.iterative_forecast(y_train, prediction_horizon=5)
```

### 5. Anomaly Detection

Identify unusual patterns or outliers. See `references/anomaly_detection.md` for detectors.

**Quick Start:**
```python
from aeon.anomaly_detection import STOMP

detector = STOMP(window_size=50)
anomaly_scores = detector.fit_predict(y)

# Higher scores indicate anomalies
threshold = np.percentile(anomaly_scores, 95)
anomalies = anomaly_scores > threshold
```

### 6. Segmentation

Partition time series into regions with change points. See `references/segmentation.md`.

**Quick Start:**
```python
from aeon.segmentation import ClaSPSegmenter

segmenter = ClaSPSegmenter()
change_points = segmenter.fit_predict(y)
```

### 7. Similarity Search

Find similar patterns within or across time series. See `references/similarity_search.md`.

**Quick Start:**
```python
from aeon.similarity_search import StompMotif

# Find recurring patterns
motif_finder = StompMotif(window_size=50, k=3)
motifs = motif_finder.fit_predict(y)
```

## Feature Extraction and Transformations

Transform time series for feature engineering. See `references/transformations.md`.

**ROCKET Features:**
```python
from aeon.transformations.collection.convolution_based import RocketTransformer

rocket = RocketTransformer()
X_features = rocket.fit_transform(X_train)

# Use features with any sklearn classifier
from sklearn.ensemble import RandomForestClassifier
clf = RandomForestClassifier()
clf.fit(X_features, y_train)
```

**Statistical Features:**
```python
from aeon.transformations.collection.feature_based import Catch22

catch22 = Catch22()
X_features = catch22.fit_transform(X_train)
```

**Preprocessing:**
```python
from aeon.transformations.collection import MinMaxScaler, Normalizer

scaler = Normalizer()  # Z-normalization
X_normalized = scaler.fit_transform(X_train)
```

## Distance Metrics

Specialized temporal distance measures. See `references/distances.md` for complete catalog.

**Usage:**
```python
from aeon.distances import dtw_distance, dtw_pairwise_distance

# Single distance
distance = dtw_distance(x, y, window=0.1)

# Pairwise distances
distance_matrix = dtw_pairwise_distance(X_train)

# Use with classifiers
from aeon.classification.distance_based import KNeighborsTimeSeriesClassifier

clf = KNeighborsTimeSeriesClassifier(
    n_neighbors=5,
    distance="dtw",
    distance_params={"window": 0.2}
)
```

**Available Distances:**
- **Elastic**: DTW, DDTW, WDTW, ERP, EDR, LCSS, TWE, MSM
- **Lock-step**: Euclidean, Manhattan, Minkowski
- **Shape-based**: Shape DTW, SBD

## Deep Learning Networks

Neural architectures for time series. See `references/networks.md`.

**Architectures:**
- Convolutional: `FCNClassifier`, `ResNetClassifier`, `InceptionTimeClassifier`
- Recurrent: `RecurrentNetwork`, `TCNNetwork`
- Autoencoders: `AEFCNClusterer`, `AEResNetClusterer`

**Usage:**
```python
from aeon.classification.deep_learning import InceptionTimeClassifier

clf = InceptionTimeClassifier(n_epochs=100, batch_size=32)
clf.fit(X_train, y_train)
predictions = clf.predict(X_test)
```

## Datasets and Benchmarking

Load standard benchmarks and evaluate performance. See `references/datasets_benchmarking.md`.

**Load Datasets:**
```python
from aeon.datasets import load_classification, load_gunpoint, load_regression

# Classification (generic loader or dataset-specific helper)
X_train, y_train = load_classification("GunPoint", split="train")
X_train, y_train = load_gunpoint(split="train")  # same UCR dataset

# Regression
X_train, y_train = load_regression("Covid3Month", split="train")
```

**Benchmarking:**
```python
from aeon.benchmarking import get_estimator_results

# Compare with published results
published = get_estimator_results("ROCKET", "GunPoint")
```

## Common Workflows

### Classification Pipeline

```python
from aeon.transformations.collection import Normalizer
from aeon.classification.convolution_based import RocketClassifier
from sklearn.pipeline import Pipeline

pipeline = Pipeline([
    ('normalize', Normalizer()),
    ('classify', RocketClassifier())
])

pipeline.fit(X_train, y_train)
accuracy = pipeline.score(X_test, y_test)
```

### Feature Extraction + Traditional ML

```python
from aeon.transformations.collection import RocketTransformer
from sklearn.ensemble import GradientBoostingClassifier

# Extract features
rocket = RocketTransformer()
X_train_features = rocket.fit_transform(X_train)
X_test_features = rocket.transform(X_test)

# Train traditional ML
clf = GradientBoostingClassifier()
clf.fit(X_train_features, y_train)
predictions = clf.predict(X_test_features)
```

### Anomaly Detection with Visualization

```python
from aeon.anomaly_detection import STOMP
import matplotlib.pyplot as plt

detector = STOMP(window_size=50)
scores = detector.fit_predict(y)

plt.figure(figsize=(15, 5))
plt.subplot(2, 1, 1)
plt.plot(y, label='Time Series')
plt.subplot(2, 1, 2)
plt.plot(scores, label='Anomaly Scores', color='red')
plt.axhline(np.percentile(scores, 95), color='k', linestyle='--')
plt.show()
```

## Best Practices

### Data Preparation

1. **Normalize**: Most algorithms benefit from z-normalization
   ```python
   from aeon.transformations.collection import Normalizer
   normalizer = Normalizer()
   X_train = normalizer.fit_transform(X_train)
   X_test = normalizer.transform(X_test)
   ```

2. **Handle Missing Values**: Impute before analysis
   ```python
   from aeon.transformations.collection import SimpleImputer
   imputer = SimpleImputer(strategy='mean')
   X_train = imputer.fit_transform(X_train)
   ```

3. **Check Data Format**: Collections use `(n_cases, n_channels, n_timepoints)`; single series use `(n_channels, n_timepoints)` (see [data format](https://www.aeon-toolkit.org/en/stable/api_reference/data_format.html))

### Model Selection

1. **Start Simple**: Begin with ROCKET variants before deep learning
2. **Use Validation**: Split training data for hyperparameter tuning
3. **Compare Baselines**: Test against simple methods (1-NN Euclidean, Naive)
4. **Consider Resources**: ROCKET for speed, deep learning if GPU available

### Algorithm Selection Guide

**For Fast Prototyping:**
- Classification: `MiniRocketClassifier`
- Regression: `MiniRocketRegressor`
- Clustering: `TimeSeriesKMeans` with Euclidean

**For Maximum Accuracy:**
- Classification: `HIVECOTEV2`, `InceptionTimeClassifier`
- Regression: `InceptionTimeRegressor`
- Forecasting: `AutoARIMA`, `AutoETS`, `TCNForecaster` (requires `[all_extras]` for deep learning)

**For Interpretability:**
- Classification: `ShapeletTransformClassifier`, `Catch22Classifier`
- Features: `Catch22`, `TSFresh`

**For Small Datasets:**
- Distance-based: `KNeighborsTimeSeriesClassifier` with DTW
- Avoid: Deep learning (requires large data)

## Reference Documentation

Detailed information available in `references/`:
- `classification.md` - All classification algorithms
- `regression.md` - Regression methods
- `clustering.md` - Clustering algorithms
- `forecasting.md` - Forecasting approaches
- `anomaly_detection.md` - Anomaly detection methods
- `segmentation.md` - Segmentation algorithms
- `similarity_search.md` - Pattern matching and motif discovery
- `transformations.md` - Feature extraction and preprocessing
- `distances.md` - Time series distance metrics
- `networks.md` - Deep learning architectures
- `datasets_benchmarking.md` - Data loading and evaluation tools

## Additional Resources

- Documentation: https://www.aeon-toolkit.org/
- GitHub: https://github.com/aeon-toolkit/aeon
- Examples: https://www.aeon-toolkit.org/en/stable/examples.html
- API Reference: https://www.aeon-toolkit.org/en/stable/api_reference.html

