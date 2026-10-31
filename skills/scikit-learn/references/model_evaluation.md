# Model Selection and Evaluation Reference

Targets scikit-learn 1.9.1. Snippets with caller-supplied data/columns are illustrative; fit all learned preprocessing inside the training folds when estimating predictive performance.

## Overview

Comprehensive guide for evaluating models, tuning hyperparameters, and selecting the best model using scikit-learn's model selection tools.

## Train-Test Split

### Basic Splitting

```python
from sklearn.model_selection import train_test_split

# Basic split (default 75/25)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)

# With stratification (preserves class distribution)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, stratify=y, random_state=42
)

# Three-way split (train/val/test)
X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, random_state=42)
X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42)
```

Split by the independent unit: patients/specimens/sites and related molecules must not cross partitions. Future prediction requires temporal boundaries and available-at-prediction features. Integer index examples below assume NumPy arrays; use `.iloc[index]` for pandas. CV fold SD is descriptive, not a confidence interval, because folds overlap in training data.

## Cross-Validation

#Split by the independent unit: patients/specimens/sites and related molecules must not cross partitions. Future prediction requires temporal boundaries and available-at-prediction features. Integer index examples below assume NumPy arrays; use `.iloc[index]` for pandas. CV fold SD is descriptive, not a confidence interval, because folds overlap in training data.

## Cross-Validation Strategies

**KFold**
- Standard k-fold cross-validation
- Splits data into k consecutive folds
```python
from sklearn.model_selection import KFold

kf = KFold(n_splits=5, shuffle=True, random_state=42)
for train_idx, val_idx in kf.split(X):
    X_train, X_val = X[train_idx], X[val_idx]
    y_train, y_val = y[train_idx], y[val_idx]
```

**StratifiedKFold**
- Preserves class distribution in each fold
- Use for imbalanced classification
```python
from sklearn.model_selection import StratifiedKFold

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
for train_idx, val_idx in skf.split(X, y):
    X_train, X_val = X[train_idx], X[val_idx]
    y_train, y_val = y[train_idx], y[val_idx]
```

**TimeSeriesSplit**
- For time series data
- Respects temporal order
```python
from sklearn.model_selection import TimeSeriesSplit

tscv = TimeSeriesSplit(n_splits=5)
for train_idx, val_idx in tscv.split(X):
    X_train, X_val = X[train_idx], X[val_idx]
    y_train, y_val = y[train_idx], y[val_idx]
```

**GroupKFold**
- Ensures samples from same group don't appear in both train and validation
- Use when samples are not independent
```python
from sklearn.model_selection import GroupKFold

gkf = GroupKFold(n_splits=5)
for train_idx, val_idx in gkf.split(X, y, groups=group_ids):
    X_train, X_val = X[train_idx], X[val_idx]
    y_train, y_val = y[train_idx], y[val_idx]
```

**LeaveOneOut (LOO)**
- Each sample used as validation set once
- Use for very small datasets
- Computationally expensive
```python
from sklearn.model_selection import LeaveOneOut

loo = LeaveOneOut()
for train_idx, val_idx in loo.split(X):
    X_train, X_val = X[train_idx], X[val_idx]
    y_train, y_val = y[train_idx], y[val_idx]
```

#Split by the independent unit: patients/specimens/sites and related molecules must not cross partitions. Future prediction requires temporal boundaries and available-at-prediction features. Integer index examples below assume NumPy arrays; use `.iloc[index]` for pandas. CV fold SD is descriptive, not a confidence interval, because folds overlap in training data.

## Cross-Validation Functions

**cross_val_score**
- Evaluate model using cross-validation
- Returns array of scores
```python
from sklearn.model_selection import cross_val_score
from sklearn.ensemble import RandomForestClassifier

model = RandomForestClassifier(n_estimators=100, random_state=42)
scores = cross_val_score(model, X, y, cv=5, scoring='accuracy')

print(f"Scores: {scores}")
print(f"Mean: {scores.mean():.3f} (fold SD {scores.std():.3f})")
```

**cross_validate**
- More comprehensive than cross_val_score
- Can return multiple metrics and fit times
```python
from sklearn.model_selection import cross_validate

model = RandomForestClassifier(n_estimators=100, random_state=42)
cv_results = cross_validate(
    model, X, y, cv=5,
    scoring=['accuracy', 'precision_macro', 'recall_macro', 'f1_macro'],
    return_train_score=True,
    return_estimator=True  # Returns fitted estimators
)

print(f"Test accuracy: {cv_results['test_accuracy'].mean():.3f}")
print(f"Test precision: {cv_results['test_precision_macro'].mean():.3f}")
print(f"Fit time: {cv_results['fit_time'].mean():.3f}s")
```

**cross_val_predict**
- Get predictions for each sample when it was in validation set
- Useful for analyzing errors; requires each sample to appear in exactly one test fold. Pooled prediction metrics need not equal average fold scores
```python
from sklearn.model_selection import cross_val_predict

model = RandomForestClassifier(n_estimators=100, random_state=42)
y_pred = cross_val_predict(model, X, y, cv=5)

# Now can analyze predictions vs actual
from sklearn.metrics import confusion_matrix
cm = confusion_matrix(y, y_pred)
```

## Hyperparameter Tuning

### Grid Search

**GridSearchCV**
- Exhaustive search over parameter grid
- Tests all combinations
```python
from sklearn.model_selection import GridSearchCV
from sklearn.ensemble import RandomForestClassifier

param_grid = {
    'n_estimators': [50, 100, 200],
    'max_depth': [5, 10, 15, None],
    'min_samples_split': [2, 5, 10],
    'min_samples_leaf': [1, 2, 4]
}

model = RandomForestClassifier(random_state=42)
grid_search = GridSearchCV(
    model, param_grid,
    cv=5,
    scoring='accuracy',
    n_jobs=-1,  # Use all CPU cores
    verbose=1
)

grid_search.fit(X_train, y_train)

print(f"Best parameters: {grid_search.best_params_}")
print(f"Best cross-validation score: {grid_search.best_score_:.3f}")
print(f"Test score: {grid_search.score(X_test, y_test):.3f}")

# Access best model
best_model = grid_search.best_estimator_

# View all results
import pandas as pd
results_df = pd.DataFrame(grid_search.cv_results_)
```

### Randomized Search

**RandomizedSearchCV**
- Samples random combinations from parameter distributions
- More efficient for large search spaces
```python
from sklearn.model_selection import RandomizedSearchCV
from scipy.stats import randint, uniform

param_distributions = {
    'n_estimators': randint(50, 300),
    'max_depth': [5, 10, 15, 20, None],
    'min_samples_split': randint(2, 20),
    'min_samples_leaf': randint(1, 10),
    'max_features': uniform(0.1, 0.9)  # Continuous distribution
}

model = RandomForestClassifier(random_state=42)
random_search = RandomizedSearchCV(
    model, param_distributions,
    n_iter=100,  # Number of parameter settings sampled
    cv=5,
    scoring='accuracy',
    n_jobs=-1,
    verbose=1,
    random_state=42
)

random_search.fit(X_train, y_train)

print(f"Best parameters: {random_search.best_params_}")
print(f"Best score: {random_search.best_score_:.3f}")
```

### Successive Halving

**HalvingGridSearchCV / HalvingRandomSearchCV**
- Iteratively selects best candidates using successive halving
- More efficient than exhaustive search
```python
from sklearn.experimental import enable_halving_search_cv
from sklearn.model_selection import HalvingGridSearchCV

param_grid = {
    'n_estimators': [50, 100, 200, 300],
    'max_depth': [5, 10, 15, 20, None],
    'min_samples_split': [2, 5, 10, 20]
}

model = RandomForestClassifier(random_state=42)
halving_search = HalvingGridSearchCV(
    model, param_grid,
    cv=5,
    factor=3,  # Roughly one third of candidates survive each iteration
    resource='n_samples',  # For n_estimators, remove it from the grid and set max_resources
    max_resources='auto',
    random_state=42
)

halving_search.fit(X_train, y_train)
print(f"Best parameters: {halving_search.best_params_}")
```

## Classification Metrics

### Basic Metrics

```python
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    balanced_accuracy_score, matthews_corrcoef
)

y_pred = model.predict(X_test)

accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred, average='weighted')  # For multiclass
recall = recall_score(y_test, y_pred, average='weighted')
f1 = f1_score(y_test, y_pred, average='weighted')
balanced_acc = balanced_accuracy_score(y_test, y_pred)  # Good for imbalanced data
mcc = matthews_corrcoef(y_test, y_pred)  # Matthews correlation coefficient

print(f"Accuracy: {accuracy:.3f}")
print(f"Precision: {precision:.3f}")
print(f"Recall: {recall:.3f}")
print(f"F1-score: {f1:.3f}")
print(f"Balanced Accuracy: {balanced_acc:.3f}")
print(f"MCC: {mcc:.3f}")
```

### Classification Report

```python
from sklearn.metrics import classification_report

print(classification_report(y_test, y_pred, target_names=class_names))
```

### Confusion Matrix

```python
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
import matplotlib.pyplot as plt

cm = confusion_matrix(y_test, y_pred)
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=class_names)
disp.plot(cmap='Blues')
plt.show()
```

### ROC and AUC

Binary `predict_proba[:, 1]` corresponds to `model.classes_[1]`; explicitly identify the scientific positive class. Multiclass probability columns must follow the class order. ROC AUC is threshold-free and does not establish calibrated probabilities or clinical utility.

```python
from sklearn.metrics import roc_auc_score, roc_curve, RocCurveDisplay

# Binary classification
y_proba = model.predict_proba(X_test)[:, 1]
auc = roc_auc_score(y_test, y_proba)
print(f"ROC AUC: {auc:.3f}")

# Plot ROC curve
fpr, tpr, thresholds = roc_curve(y_test, y_proba, pos_label=model.classes_[1])
RocCurveDisplay(fpr=fpr, tpr=tpr, roc_auc=auc).plot()

# Multiclass (one-vs-rest)
y_proba_multi = model.predict_proba(X_test)  # Use a multiclass fitted model here
auc_ovr = roc_auc_score(y_test, y_proba_multi, labels=model.classes_, multi_class='ovr')
```

### Precision-Recall Curve

```python
from sklearn.metrics import precision_recall_curve, PrecisionRecallDisplay
from sklearn.metrics import average_precision_score

precision, recall, thresholds = precision_recall_curve(y_test, y_proba, pos_label=model.classes_[1])
ap = average_precision_score(y_test, y_proba, pos_label=model.classes_[1])

disp = PrecisionRecallDisplay(precision=precision, recall=recall, average_precision=ap)
disp.plot()
```

### Log Loss

```python
from sklearn.metrics import log_loss

y_proba = model.predict_proba(X_test)
logloss = log_loss(y_test, y_proba)
print(f"Log Loss: {logloss:.3f}")
```

## Regression Metrics

MAPE is a relative value (0.1 means 10%) and becomes unstable near zero targets. R² may be negative on test data; constant targets require care with its default `force_finite=True` behavior.

```python
from sklearn.metrics import (
    mean_squared_error, root_mean_squared_error, mean_absolute_error, r2_score,
    mean_absolute_percentage_error, median_absolute_error
)

y_pred = model.predict(X_test)

mse = mean_squared_error(y_test, y_pred)
rmse = root_mean_squared_error(y_test, y_pred)
mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)
mape = mean_absolute_percentage_error(y_test, y_pred)
median_ae = median_absolute_error(y_test, y_pred)

print(f"MSE: {mse:.3f}")
print(f"RMSE: {rmse:.3f}")
print(f"MAE: {mae:.3f}")
print(f"R² Score: {r2:.3f}")
print(f"MAPE: {mape:.3f}")
print(f"Median AE: {median_ae:.3f}")
```

## Clustering Metrics

### With Ground Truth Labels

```python
from sklearn.metrics import (
    adjusted_rand_score, normalized_mutual_info_score,
    adjusted_mutual_info_score, fowlkes_mallows_score,
    homogeneity_score, completeness_score, v_measure_score
)

ari = adjusted_rand_score(y_true, y_pred)
nmi = normalized_mutual_info_score(y_true, y_pred)
ami = adjusted_mutual_info_score(y_true, y_pred)
fmi = fowlkes_mallows_score(y_true, y_pred)
homogeneity = homogeneity_score(y_true, y_pred)
completeness = completeness_score(y_true, y_pred)
v_measure = v_measure_score(y_true, y_pred)
```

### Without Ground Truth

Require `2 <= n_labels < n_samples`; do not let DBSCAN noise label -1 silently become a cluster. If excluding noise, report coverage and avoid comparing the resulting score directly with all-row scores. These internal indices favor compact/convex geometry and cannot confirm scientific validity.

```python
from sklearn.metrics import (
    silhouette_score, calinski_harabasz_score, davies_bouldin_score
)

silhouette = silhouette_score(X, labels)  # [-1, 1], higher better
ch_score = calinski_harabasz_score(X, labels)  # Higher better
db_score = davies_bouldin_score(X, labels)  # Lower better
```

## Custom Scoring

### Using make_scorer

```python
from sklearn.metrics import make_scorer

def custom_metric(y_true, y_pred):
    # Illustrative binary cost: a missed positive costs five false positives.
    import numpy as np
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    return np.mean(5 * ((y_true == 1) & (y_pred == 0)) +
                   ((y_true == 0) & (y_pred == 1)))

custom_scorer = make_scorer(custom_metric, greater_is_better=False)

# Use in cross-validation or grid search
scores = cross_val_score(model, X, y, cv=5, scoring=custom_scorer)
```

### Multiple Metrics in Grid Search

```python
from sklearn.model_selection import GridSearchCV

scoring = {
    'accuracy': 'accuracy',
    'precision': 'precision_weighted',
    'recall': 'recall_weighted',
    'f1': 'f1_weighted'
}

grid_search = GridSearchCV(
    model, param_grid,
    cv=5,
    scoring=scoring,
    refit='f1',  # Refit on best f1 score
    return_train_score=True
)

grid_search.fit(X_train, y_train)
```

## Validation Curves

### Learning Curve

```python
from sklearn.model_selection import learning_curve
import matplotlib.pyplot as plt
import numpy as np

train_sizes, train_scores, val_scores = learning_curve(
    model, X, y,
    cv=5,
    train_sizes=np.linspace(0.1, 1.0, 10),
    scoring='accuracy',
    n_jobs=-1
)

train_mean = train_scores.mean(axis=1)
train_std = train_scores.std(axis=1)
val_mean = val_scores.mean(axis=1)
val_std = val_scores.std(axis=1)

plt.figure(figsize=(10, 6))
plt.plot(train_sizes, train_mean, label='Training score')
plt.plot(train_sizes, val_mean, label='Validation score')
plt.fill_between(train_sizes, train_mean - train_std, train_mean + train_std, alpha=0.1)
plt.fill_between(train_sizes, val_mean - val_std, val_mean + val_std, alpha=0.1)
plt.xlabel('Training Set Size')
plt.ylabel('Score')
plt.title('Learning Curve')
plt.legend()
plt.grid(True)
```

### Validation Curve

```python
from sklearn.model_selection import validation_curve

param_range = [1, 10, 50, 100, 200, 500]
train_scores, val_scores = validation_curve(
    model, X, y,
    param_name='n_estimators',
    param_range=param_range,
    cv=5,
    scoring='accuracy',
    n_jobs=-1
)

train_mean = train_scores.mean(axis=1)
val_mean = val_scores.mean(axis=1)

plt.figure(figsize=(10, 6))
plt.plot(param_range, train_mean, label='Training score')
plt.plot(param_range, val_mean, label='Validation score')
plt.xlabel('n_estimators')
plt.ylabel('Score')
plt.title('Validation Curve')
plt.legend()
plt.grid(True)
```

## Model Persistence

Pickle/joblib loading can execute arbitrary code: load trusted artifacts only. Cross-version scikit-learn loading is unsupported. Save the fitted pipeline, exact package versions, feature schema, and validation provenance together.

### Save and Load Models

```python
import joblib

# Save model
joblib.dump(model, 'model.pkl')

# Load model
loaded_model = joblib.load('model.pkl')

# Also works with pipelines
joblib.dump(pipeline, 'pipeline.pkl')
```

### Using pickle

```python
import pickle

# Save
with open('model.pkl', 'wb') as f:
    pickle.dump(model, f)

# Load
with open('model.pkl', 'rb') as f:
    loaded_model = pickle.load(f)
```

## Imbalanced Data Strategies

### Class Weighting

```python
from sklearn.ensemble import RandomForestClassifier

# Automatically balance classes
model = RandomForestClassifier(class_weight='balanced', random_state=42)
model.fit(X_train, y_train)

# Custom weights
class_weights = {0: 1, 1: 10}  # Give class 1 more weight
model = RandomForestClassifier(class_weight=class_weights, random_state=42)
```

### Resampling (using imbalanced-learn)

```python
# Install: uv pip install imbalanced-learn
from imblearn.over_sampling import SMOTE
from imblearn.under_sampling import RandomUnderSampler
from imblearn.pipeline import Pipeline as ImbPipeline

# Resampling belongs inside each training fold; pass this pipeline to CV/search.
# Binary numeric features only here: float ratios are not multiclass strategies.
# For nominal columns consider SMOTENC; never interpolate arbitrary category codes.
# Combined approach
pipeline = ImbPipeline([
    ('over', SMOTE(sampling_strategy=0.5, random_state=42)),
    ('under', RandomUnderSampler(sampling_strategy=0.8, random_state=42)),
    ('model', RandomForestClassifier(random_state=42))
])
```

## Best Practices

### Stratified Splitting
Use stratified splitting for classification only when rows are independent and the deployment task permits random splitting; retain group or temporal boundaries when those apply:
```python
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)
```

### Appropriate Metrics
- **Balanced data**: Accuracy, F1-score
- **Imbalanced data**: Per-class Precision/Recall, Average Precision, macro F1, Balanced Accuracy; weighted averages can hide minority failures
- **Cost-sensitive**: Define custom scorer with costs
- **Ranking**: ROC AUC, Average Precision

#Split by the independent unit: patients/specimens/sites and related molecules must not cross partitions. Future prediction requires temporal boundaries and available-at-prediction features. Integer index examples below assume NumPy arrays; use `.iloc[index]` for pandas. CV fold SD is descriptive, not a confidence interval, because folds overlap in training data.

## Cross-Validation
- Use 5 or 10-fold CV for most cases
- Use StratifiedKFold for classification
- Use TimeSeriesSplit for time series
- Use GroupKFold when samples are grouped

### Nested Cross-Validation
Estimate the complete selection procedure on untouched outer folds; do not choose algorithms or preprocessing using the outer scores. Both levels must respect groups/time where applicable:
```python
from sklearn.model_selection import cross_val_score, GridSearchCV

# Inner loop: hyperparameter tuning
grid_search = GridSearchCV(model, param_grid, cv=5)

# Outer loop: performance estimation
scores = cross_val_score(grid_search, X, y, cv=5)
print(f"Nested CV score: {scores.mean():.3f} (fold SD {scores.std():.3f})")
```

## Upstream references

- https://scikit-learn.org/stable/modules/cross_validation.html
- https://scikit-learn.org/stable/modules/model_evaluation.html
- https://scikit-learn.org/stable/model_persistence.html
- https://imbalanced-learn.org/stable/common_pitfalls.html
