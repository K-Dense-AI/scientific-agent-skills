"""
Complete classification pipeline example with preprocessing, model training,
hyperparameter tuning, and evaluation.
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score, StratifiedKFold
from sklearn.base import clone
from sklearn.preprocessing import StandardScaler, OneHotEncoder, FunctionTransformer
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_auc_score,
    accuracy_score, precision_score, recall_score, f1_score, balanced_accuracy_score
)


def normalize_categorical_missing(X):
    """Map pandas/None missing sentinels to the imputer's np.nan sentinel."""
    frame = pd.DataFrame(X).astype(object)
    return frame.where(frame.notna(), np.nan).to_numpy()


def create_preprocessing_pipeline(numeric_features, categorical_features):
    """
    Create a preprocessing pipeline for mixed data types.

    Parameters:
    -----------
    numeric_features : list
        List of numeric feature column names
    categorical_features : list
        List of categorical feature column names

    Returns:
    --------
    ColumnTransformer
        Preprocessing pipeline
    """
    # Numeric preprocessing
    numeric_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='median', keep_empty_features=True)),
        ('scaler', StandardScaler())
    ])

    # Categorical preprocessing
    categorical_transformer = Pipeline(steps=[
        ('missing', FunctionTransformer(normalize_categorical_missing,
                                        feature_names_out='one-to-one')),
        ('imputer', SimpleImputer(strategy='constant', fill_value='missing',
                                  keep_empty_features=True)),
        ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
    ])

    # Combine transformers
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, numeric_features),
            ('cat', categorical_transformer, categorical_features)
        ]
    )

    return preprocessor


def train_and_evaluate_model(X, y, numeric_features, categorical_features,
                             test_size=0.2, random_state=42, cv=5,
                             scoring="balanced_accuracy", n_jobs=1):
    """
    Preprocess, select, tune, and evaluate independent-row classification data.

    This random-split demonstration is not appropriate for grouped or temporal
    observations. Selection CV scores are optimistic; only the untouched test
    partition evaluates the selected procedure. Dense one-hot encoding is for
    small/moderate categorical cardinalities.

    Parameters:
    -----------
    X : DataFrame
        Feature matrix (feature selectors below are column names)
    y : Series or array
        Target variable
    numeric_features : list
        List of numeric feature names
    categorical_features : list
        List of categorical feature names
    test_size : float
        Proportion of data for testing
    random_state : int
        Random seed

    cv : int
        Number of stratified training folds; every class must have this many rows
    scoring : str or callable
        Selection metric passed unchanged to cross_val_score and GridSearchCV
    n_jobs : int
        Search workers; default 1 avoids nested parallelism

    Returns:
    --------
    dict
        Trained model, predictions, selection scores, class order and test metrics
    """
    # Split data with stratification
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, stratify=y, random_state=random_state
    )

    print(f"Training set size: {len(X_train)}")
    print(f"Test set size: {len(X_test)}")
    print(f"Class distribution in training: {pd.Series(y_train).value_counts().to_dict()}")

    if pd.Series(y_train).value_counts().min() < cv:
        raise ValueError("Each training class needs at least cv samples; lower cv or add data")
    splitter = StratifiedKFold(n_splits=cv, shuffle=True, random_state=random_state)

    # Create preprocessor
    preprocessor = create_preprocessing_pipeline(numeric_features, categorical_features)

    # Define models to compare
    models = {
        'Logistic Regression': Pipeline([
            ('preprocessor', clone(preprocessor)),
            ('classifier', LogisticRegression(max_iter=1000, random_state=random_state))
        ]),
        'Random Forest': Pipeline([
            ('preprocessor', clone(preprocessor)),
            ('classifier', RandomForestClassifier(n_estimators=100, random_state=random_state))
        ]),
        'Gradient Boosting': Pipeline([
            ('preprocessor', clone(preprocessor)),
            ('classifier', GradientBoostingClassifier(n_estimators=100, random_state=random_state))
        ])
    }

    # Compare models using cross-validation
    print("\n" + "="*60)
    print(f"Model Comparison ({cv}-Fold Cross-Validation; {scoring})")
    print("="*60)

    cv_results = {}
    for name, model in models.items():
        scores = cross_val_score(model, X_train, y_train, cv=splitter, scoring=scoring, error_score='raise')
        cv_results[name] = scores.mean()
        print(f"{name:20s}: {scores.mean():.4f} (fold SD {scores.std():.4f})")

    # Select best model based on CV
    best_model_name = max(cv_results, key=cv_results.get)
    best_model = models[best_model_name]

    print(f"\nBest model: {best_model_name}")

    # Hyperparameter tuning for best model
    if best_model_name == 'Random Forest':
        param_grid = {
            'classifier__n_estimators': [100, 200],
            'classifier__max_depth': [10, 20, None],
            'classifier__min_samples_split': [2, 5]
        }
    elif best_model_name == 'Gradient Boosting':
        param_grid = {
            'classifier__n_estimators': [100, 200],
            'classifier__learning_rate': [0.01, 0.1],
            'classifier__max_depth': [3, 5]
        }
    else:  # Logistic Regression
        param_grid = {
            'classifier__C': [0.1, 1.0, 10.0],
            'classifier__l1_ratio': [0.0]
        }

    print("\n" + "="*60)
    print("Hyperparameter Tuning")
    print("="*60)

    grid_search = GridSearchCV(
        best_model, param_grid, cv=splitter, scoring=scoring,
        n_jobs=n_jobs, verbose=0, error_score="raise"
    )

    grid_search.fit(X_train, y_train)

    print(f"Best parameters: {grid_search.best_params_}")
    print(f"Best CV score: {grid_search.best_score_:.4f}")

    # Evaluate on test set
    tuned_model = grid_search.best_estimator_
    y_pred = tuned_model.predict(X_test)
    y_pred_proba = tuned_model.predict_proba(X_test)

    print("\n" + "="*60)
    print("Test Set Evaluation")
    print("="*60)

    # Calculate metrics
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, average='weighted', zero_division=0)
    recall = recall_score(y_test, y_pred, average='weighted', zero_division=0)
    f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)

    balanced_accuracy = balanced_accuracy_score(y_test, y_pred)
    macro_f1 = f1_score(y_test, y_pred, average='macro', zero_division=0)
    metrics = dict(accuracy=accuracy, balanced_accuracy=balanced_accuracy,
                   precision=precision, recall=recall, f1=f1, macro_f1=macro_f1)

    print(f"Balanced accuracy: {balanced_accuracy:.4f}")
    print(f"Macro F1:          {macro_f1:.4f}")
    print(f"Accuracy:  {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1-Score:  {f1:.4f}")

    # ROC AUC (if binary classification)
    if len(tuned_model.classes_) == 2:
        # Column 1 corresponds to classes_[1], which need not mean disease/case.
        roc_auc = roc_auc_score(y_test == tuned_model.classes_[1], y_pred_proba[:, 1])
        metrics['roc_auc'] = roc_auc
        print(f"ROC AUC:   {roc_auc:.4f}")

    print("\n" + "="*60)
    print("Classification Report")
    print("="*60)
    print(classification_report(y_test, y_pred, zero_division=0))

    print("\n" + "="*60)
    print("Confusion Matrix")
    print("="*60)
    print(confusion_matrix(y_test, y_pred))

    # Feature importance (if available)
    if hasattr(tuned_model.named_steps['classifier'], 'feature_importances_'):
        print("\n" + "="*60)
        print("Top 10 Impurity Importances (biased toward high-cardinality features)")
        print("="*60)

        feature_names = tuned_model.named_steps['preprocessor'].get_feature_names_out()
        importances = tuned_model.named_steps['classifier'].feature_importances_

        feature_importance_df = pd.DataFrame({
            'feature': feature_names,
            'importance': importances
        }).sort_values('importance', ascending=False).head(10)

        print(feature_importance_df.to_string(index=False))

    return {
        'model': tuned_model,
        'y_test': y_test,
        'y_pred': y_pred,
        'y_pred_proba': y_pred_proba,
        'classes': tuned_model.classes_,
        'positive_class': tuned_model.classes_[1] if len(tuned_model.classes_) == 2 else None,
        'selection_scoring': scoring,
        'cv_scores': cv_results,
        'metrics': metrics
    }


# Example usage
if __name__ == "__main__":
    # Load example dataset
    from sklearn.datasets import load_breast_cancer

    # Load data
    data = load_breast_cancer()
    X = pd.DataFrame(data.data, columns=data.feature_names)
    y = data.target

    # For demonstration, treat all features as numeric
    numeric_features = X.columns.tolist()
    categorical_features = []

    print("="*60)
    print("Classification Pipeline Example")
    print("Dataset: Breast Cancer Wisconsin")
    print("="*60)

    # Run complete pipeline
    results = train_and_evaluate_model(
        X, y, numeric_features, categorical_features,
        test_size=0.2, random_state=42
    )

    print("\n" + "="*60)
    print("Pipeline Complete!")
    print("="*60)
