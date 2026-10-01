"""
PyMC Model Comparison Script

Utilities for comparing multiple Bayesian models using information criteria
and cross-validation metrics.

Usage:
    from scripts.model_comparison import compare_models, plot_model_comparison

    # Compare multiple models
    comparison = compare_models(
        {'model1': idata1, 'model2': idata2, 'model3': idata3},
        ic='loo'
    )

    # Visualize comparison
    plot_model_comparison(comparison, output_path='model_comparison.png')
"""

import arviz as az
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Any, Dict


#: ArviZ 1.x compares models on PSIS-LOO ELPD only; there is no `ic=` switch and
#: no deviance scale. WAIC is still available on its own via `az.waic()`.
SUPPORTED_IC = ('loo', 'elpd')


def compare_models(models_dict: Dict[str, Any],
                   ic='loo',
                   verbose=True):
    """
    Compare multiple models by expected log pointwise predictive density.

    Parameters
    ----------
    models_dict : dict
        Dictionary mapping model names to PyMC posterior objects.
        All models must have log_likelihood computed.
    ic : str
        Information criterion. Only 'loo' (equivalently 'elpd') is supported:
        ArviZ 1.x ranks models on PSIS-LOO ELPD.
    verbose : bool
        Print detailed comparison results (default: True)

    Returns
    -------
    pd.DataFrame
        Comparison DataFrame with model rankings and statistics, on the ELPD
        scale (higher is better, so `elpd_diff` is 0 for the best model and
        negative for the others).

    Notes
    -----
    Models must have a log_likelihood group, computed during sampling or
    afterwards with pm.compute_log_likelihood(idata).
    """
    if ic.lower() not in SUPPORTED_IC:
        raise ValueError(
            f"unknown information criterion {ic!r}: ArviZ 1.x ranks models on "
            "PSIS-LOO ELPD, so pass ic='loo'. For WAIC, call az.waic() per "
            "model directly."
        )

    if verbose:
        print("="*70)
        print(" " * 25 + "MODEL COMPARISON (LOO)")
        print("="*70)

    # round_to='none' keeps the columns numeric; the default formats them for
    # display, which turns every comparison below into a string comparison.
    comparison = az.compare(models_dict, round_to='none')

    if verbose:
        print("\nModel Rankings:")
        print("-"*70)
        print(comparison.to_string())

        print("\n" + "="*70)
        print("INTERPRETATION GUIDE")
        print("="*70)
        print("• rank:       Model ranking (0 = best)")
        print("• elpd:       PSIS-LOO ELPD estimate (higher is better)")
        print("• p:          Effective number of parameters")
        print("• elpd_diff:  ELPD minus the best model's ELPD (0 for the best)")
        print("• weight:     Model probability (stacking weights)")
        print("• se:         Standard error of the ELPD estimate")
        print("• dse:        Standard error of the difference")
        print("• p_worse:    Probability the model is worse than the best one")
        print("• diag_elpd:  Reliability diagnostic for the ELPD estimate")

        print("\n" + "="*70)
        print("MODEL SELECTION GUIDELINES")
        print("="*70)

        best_model = comparison.index[0]
        print(f"\n[OK] Best model: {best_model}")

        # Check for a clear winner. Vehtari et al. recommend treating an ELPD
        # difference below 4 as small, and otherwise judging it against the
        # standard error of the difference.
        if len(comparison) > 1:
            delta = abs(comparison.iloc[1]['elpd_diff'])
            delta_se = comparison.iloc[1]['dse']

            if delta < 4:
                print(f"  -> Models are SIMILAR (ELPD difference {delta:.1f} < 4)")
                print("    Consider model averaging or choose based on simplicity")
            elif delta > 2 * delta_se:
                print(
                    f"  -> STRONG evidence for {best_model} "
                    f"(ELPD difference {delta:.1f} > 2 SE)"
                )
            else:
                print(
                    f"  -> MODERATE evidence for {best_model} "
                    f"(ELPD difference {delta:.1f}, within 2 SE)"
                )

        # Reliability. ArviZ 1.x reports this per row as a diagnostic string
        # instead of the old boolean `warning` column.
        flagged = [
            name
            for name, diagnostic in comparison['diag_elpd'].items()
            if isinstance(diagnostic, str) and diagnostic.strip() not in ('', 'ok')
        ]
        if flagged:
            print("\n[WARN]  WARNING: Some models have reliability issues")
            print(f"   Models with warnings: {', '.join(flagged)}")
            print("   -> Check Pareto-k diagnostics with check_loo_reliability()")

    return comparison


def check_loo_reliability(models_dict: Dict[str, Any],
                          threshold=0.7,
                          verbose=True):
    """
    Check LOO-CV reliability using Pareto-k diagnostics.

    Parameters
    ----------
    models_dict : dict
        Dictionary mapping model names to PyMC posterior objects
    threshold : float
        Pareto-k threshold for flagging observations (default: 0.7)
    verbose : bool
        Print detailed diagnostics (default: True)

    Returns
    -------
    dict
        Dictionary with Pareto-k diagnostics for each model
    """
    if verbose:
        print("="*70)
        print(" " * 20 + "LOO RELIABILITY CHECK")
        print("="*70)

    results = {}

    for name, idata in models_dict.items():
        if verbose:
            print(f"\n{name}:")
            print("-"*70)

        # Compute LOO with pointwise results
        loo_result = az.loo(idata, pointwise=True)
        pareto_k = loo_result.pareto_k.values

        # Count problematic observations
        n_high = (pareto_k > threshold).sum()
        n_very_high = (pareto_k > 1.0).sum()

        results[name] = {
            'pareto_k': pareto_k,
            'n_high': n_high,
            'n_very_high': n_very_high,
            'max_k': pareto_k.max(),
            'loo': loo_result
        }

        if verbose:
            print(f"Pareto-k diagnostics:")
            print(f"  • Good (k < 0.5):       {(pareto_k < 0.5).sum()} observations")
            print(f"  • OK (0.5 <= k < 0.7):    {((pareto_k >= 0.5) & (pareto_k < 0.7)).sum()} observations")
            print(f"  • Bad (0.7 <= k < 1.0):   {((pareto_k >= 0.7) & (pareto_k < 1.0)).sum()} observations")
            print(f"  • Very bad (k >= 1.0):    {(pareto_k >= 1.0).sum()} observations")
            print(f"  • Maximum k: {pareto_k.max():.3f}")

            if n_high > 0:
                print(f"\n[WARN]  {n_high} observations with k > {threshold}")
                print("  LOO approximation may be unreliable for these points")
                print("  Solutions:")
                print("  -> Use WAIC instead (less sensitive to outliers)")
                print("  -> Investigate influential observations")
                print("  -> Consider more flexible model")

                if n_very_high > 0:
                    print(f"\n[WARN]  {n_very_high} observations with k > 1.0")
                    print("  These points have very high influence")
                    print("  -> Strongly consider K-fold CV or other validation")
            else:
                print(f"[OK] All Pareto-k values < {threshold}")
                print("  LOO estimates are reliable")

    return results


def plot_model_comparison(comparison, output_path=None, show=True):
    """
    Visualize model comparison results.

    Parameters
    ----------
    comparison : pd.DataFrame
        Comparison DataFrame from az.compare()
    output_path : str, optional
        If provided, save plot to this path
    show : bool
        Whether to display plot (default: True)

    Returns
    -------
    matplotlib.figure.Figure
        The comparison figure
    """
    # ArviZ 1.x returns a PlotCollection and does not draw into pyplot's
    # current figure, so the figure has to come back out of the collection --
    # plt.savefig() would write a blank image.
    collection = az.plot_compare(comparison)
    fig = collection.viz['figure'].item()
    fig.suptitle('Model Comparison', fontsize=14, fontweight='bold')

    if output_path:
        fig.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Comparison plot saved to {output_path}")

    if show:
        plt.show()
    else:
        plt.close(fig)

    return fig


def model_averaging(models_dict: Dict[str, Any],
                    weights=None,
                    var_name='y_obs',
                    ic='loo'):
    """
    Perform Bayesian model averaging using model weights.

    Parameters
    ----------
    models_dict : dict
        Dictionary mapping model names to PyMC posterior objects
    weights : array-like, optional
        Model weights. If None, taken from `compare_models` (stacking weights)
    var_name : str
        Name of the predicted variable (default: 'y_obs')
    ic : str
        Information criterion for computing weights if not provided

    Returns
    -------
    np.ndarray
        Averaged predictions across models
    np.ndarray
        Model weights used
    """
    if weights is None:
        comparison = compare_models(models_dict, ic=ic, verbose=False)
        weights = comparison['weight'].values
        model_names = comparison.index.tolist()
    else:
        model_names = list(models_dict.keys())
        weights = np.array(weights)
        weights = weights / weights.sum()  # Normalize

    print("="*70)
    print(" " * 22 + "BAYESIAN MODEL AVERAGING")
    print("="*70)
    print("\nModel weights:")
    for name, weight in zip(model_names, weights):
        print(f"  {name}: {weight:.4f} ({weight*100:.2f}%)")

    # Extract predictions and average
    predictions = []
    for name in model_names:
        idata = models_dict[name]
        if hasattr(idata, 'posterior_predictive') and var_name in idata.posterior_predictive:
            pred = idata.posterior_predictive[var_name].values
        elif hasattr(idata, 'predictions') and var_name in idata.predictions:
            pred = idata.predictions[var_name].values
        else:
            print(f"Warning: {name} missing posterior_predictive/predictions for {var_name}, skipping")
            continue
        predictions.append(pred)

    # Weighted average
    averaged = sum(w * p for w, p in zip(weights, predictions))

    print(f"\n[OK] Model averaging complete")
    print(f"  Combined predictions using {len(predictions)} models")

    return averaged, weights


def cross_validation_comparison(models_dict: Dict[str, Any],
                                k=10,
                                verbose=True):
    """
    Perform k-fold cross-validation comparison (conceptual guide).

    Note: This function provides guidance. Full k-fold CV requires
    re-fitting models k times, which should be done in the main script.

    Parameters
    ----------
    models_dict : dict
        Dictionary of model names to PyMC posterior objects
    k : int
        Number of folds (default: 10)
    verbose : bool
        Print guidance

    Returns
    -------
    None
    """
    if verbose:
        print("="*70)
        print(" " * 20 + "K-FOLD CROSS-VALIDATION GUIDE")
        print("="*70)
        print(f"\nTo perform {k}-fold CV:")
        print("""
1. Split data into k folds
2. For each fold:
   - Train all models on k-1 folds
   - Compute log-likelihood on held-out fold
3. Sum log-likelihoods across folds for each model
4. Compare models using total CV score

Example code:
-------------
from sklearn.model_selection import KFold

kf = KFold(n_splits=k, shuffle=True, random_seed=42)
cv_scores = {name: [] for name in models_dict.keys()}

for train_idx, test_idx in kf.split(X):
    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    for name in models_dict.keys():
        # Fit model on train set
        with create_model(name, X_train, y_train) as model:
            idata = pm.sample()

        # Compute log-likelihood on test set
        with model:
            pm.set_data({'X': X_test, 'y': y_test})
            log_lik = pm.compute_log_likelihood(idata).sum()

        cv_scores[name].append(log_lik)

# Compare total CV scores
for name, scores in cv_scores.items():
    print(f"{name}: {np.sum(scores):.2f}")
        """)

    print("\nNote: K-fold CV is expensive but most reliable for model comparison")
    print("      Use when LOO has reliability issues (high Pareto-k values)")


# Example usage
if __name__ == '__main__':
    print("This script provides model comparison utilities for PyMC.")
    print("\nExample usage:")
    print("""
    import pymc as pm
    from scripts.model_comparison import compare_models, check_loo_reliability

    # Fit multiple models (must include log_likelihood)
    with pm.Model() as model1:
        # ... define model 1 ...
        idata1 = pm.sample(idata_kwargs={'log_likelihood': True})

    with pm.Model() as model2:
        # ... define model 2 ...
        idata2 = pm.sample(idata_kwargs={'log_likelihood': True})

    # Compare models
    models = {'Simple': idata1, 'Complex': idata2}
    comparison = compare_models(models, ic='loo')

    # Check reliability
    reliability = check_loo_reliability(models)

    # Visualize
    plot_model_comparison(comparison, output_path='comparison.png')

    # Model averaging
    averaged_pred, weights = model_averaging(models, var_name='y_obs')
    """)
