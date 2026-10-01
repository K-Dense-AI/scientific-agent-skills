# Common Workflows

Targets scikit-learn 1.9.1. Snippets with caller-supplied data/columns are illustrative; fit all learned preprocessing inside the training folds when estimating predictive performance.

Two worked end-to-end workflows: building a classification model and performing a
clustering analysis.

## Common Workflows

### Building a Classification Model

1. **Load and explore data**
   ```python
   import pandas as pd
   df = pd.read_csv('data.csv')
   X = df.drop('target', axis=1)
   y = df['target']
   ```

2. **Split data with stratification**
   ```python
   from sklearn.model_selection import train_test_split
   X_train, X_test, y_train, y_test = train_test_split(
       X, y, test_size=0.2, stratify=y, random_state=42
   )
   ```

3. **Create preprocessing pipeline**
   ```python
   from sklearn.pipeline import Pipeline
   from sklearn.preprocessing import StandardScaler, OneHotEncoder
   from sklearn.ensemble import RandomForestClassifier
   from sklearn.compose import ColumnTransformer

   # Choose these using the training schema; exclude target/identifiers.
   numeric_features = X_train.select_dtypes(include='number').columns.tolist()
   categorical_features = X_train.columns.difference(numeric_features).tolist()
   # This minimal example assumes no missing values.
   # Handle numeric and categorical features separately
   preprocessor = ColumnTransformer([
       ('num', StandardScaler(), numeric_features),
       ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
   ])
   ```

4. **Build complete pipeline**
   ```python
   model = Pipeline([
       ('preprocessor', preprocessor),
       ('classifier', RandomForestClassifier(random_state=42))
   ])
   ```

5. **Tune hyperparameters**
   ```python
   from sklearn.model_selection import GridSearchCV

   param_grid = {
       'classifier__n_estimators': [100, 200],
       'classifier__max_depth': [10, 20, None]
   }

   grid_search = GridSearchCV(model, param_grid, cv=5)
   grid_search.fit(X_train, y_train)
   ```

6. **Evaluate on test set**
   ```python
   from sklearn.metrics import classification_report

   best_model = grid_search.best_estimator_
   y_pred = best_model.predict(X_test)
   print(classification_report(y_test, y_pred))
   ```

### Performing Clustering Analysis

1. **Preprocess data**
   ```python
   from sklearn.preprocessing import StandardScaler

   scaler = StandardScaler()
   X_scaled = scaler.fit_transform(X)
   ```

2. **Explore candidate cluster counts**
   ```python
   from sklearn.cluster import KMeans
   from sklearn.metrics import silhouette_score

   import numpy as np
   scores = []
   candidates = range(2, min(11, len(X_scaled)))
   for k in candidates:
       kmeans = KMeans(n_clusters=k, n_init=10, random_state=42)
       labels = kmeans.fit_predict(X_scaled)
       scores.append(silhouette_score(X_scaled, labels)
                     if 2 <= len(np.unique(labels)) < len(labels) else np.nan)

   if not scores or not np.isfinite(scores).any():
       raise ValueError("No valid silhouette candidate")
   optimal_k = candidates[int(np.nanargmax(scores))]  # Exploratory candidate only
   ```

3. **Apply clustering**
   ```python
   model = KMeans(n_clusters=optimal_k, random_state=42)
   labels = model.fit_predict(X_scaled)
   ```

4. **Visualize with dimensionality reduction**
   ```python
   from sklearn.decomposition import PCA
   import matplotlib.pyplot as plt

   pca = PCA(n_components=2)
   X_2d = pca.fit_transform(X_scaled)

   plt.scatter(X_2d[:, 0], X_2d[:, 1], c=labels, cmap='viridis')
   ```

## Upstream references

- https://scikit-learn.org/stable/common_pitfalls.html
- https://scikit-learn.org/stable/modules/clustering.html
