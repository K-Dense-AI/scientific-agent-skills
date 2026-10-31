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
                   verbose=True, var_name=None):
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

    _validate_comparable_observations(models_dict, var_name)

    # round_to='none' keeps the columns numeric; the default formats them for
    # display, which turns every comparison below into a string comparison.
    comparison = az.compare(models_dict, var_name=var_name, round_to='none')

    if verbose:
        print("\nModel Rankings:")
        print("-"*70)
        print(comparison.to_string())

        print("\n" + "="*70)
        print("INTERPRETATION GUIDE")
        print("="*70)
        print("- rank:       Model ranking (0 = best)")
        print("- elpd:       PSIS-LOO ELPD estimate (higher is better)")
        print("- p:          Effective number of parameters")
        print("- elpd_diff:  ELPD minus the best model's ELPD (0 for the best)")
        print("- weight:     Predictive stacking weight (not model probability)")
        print("- se:         Standard error of the ELPD estimate")
        print("- dse:        Standard error of the difference")
        print("- p_worse:    Probability the model is worse than the best one")
        print("- diag_elpd:  Reliability diagnostic for the ELPD estimate")

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
                    f"  -> Larger estimated predictive score for {best_model} "
                    f"(ELPD difference {delta:.1f} > 2 SE)"
                )
            else:
                print(
                    f"  -> Uncertain estimated advantage for {best_model} "
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


def _validate_comparable_observations(models_dict, var_name=None):
    """Reject mismatched observed values/order; predictive-unit choice remains scientific."""
    if not models_dict:
        raise ValueError("At least one model is required")
    reference = None
    reference_layout = None
    selected_name = var_name
    for name, idata in models_dict.items():
        if not hasattr(idata, 'log_likelihood') or not hasattr(idata, 'observed_data'):
            raise ValueError(f"{name}: log_likelihood and observed_data groups are required")
        names = list(idata.log_likelihood.data_vars)
        if selected_name is None:
            if len(names) != 1:
                raise ValueError("Specify var_name when there are multiple likelihoods")
            selected_name = names[0]
        if selected_name not in idata.log_likelihood or selected_name not in idata.observed_data:
            raise ValueError(f"{name}: missing likelihood/observations for {selected_name}")
        observed = idata.observed_data[selected_name]
        loglik = idata.log_likelihood[selected_name]
        if not np.isfinite(loglik.values).all():
            raise ValueError(f"{name}: log likelihood contains nonfinite values")
        if not {'chain', 'draw'}.issubset(loglik.dims):
            raise ValueError(f"{name}: log likelihood needs chain and draw dimensions")
        layout = loglik.isel(chain=0, draw=0, drop=True)
        if reference is None:
            reference = observed
            reference_layout = layout
        elif not observed.identical(reference):
            raise ValueError("Models must use identical observed outcomes, dimensions and coordinates")
        elif layout.dims != reference_layout.dims or layout.sizes != reference_layout.sizes or not layout.coords.equals(reference_layout.coords):
            raise ValueError("Pointwise likelihood dimensions and coordinates must match")
    return selected_name


def check_loo_reliability(models_dict: Dict[str, Any], threshold=None,
                          verbose=True, var_name=None):
    """Report PSIS diagnostics; default to each result's sample-size-aware good_k.

    A custom threshold may be stricter. Nonfinite k values are always flagged.
    This checks importance sampling, not convergence or the chosen predictive unit.
    """
    if threshold is not None and not np.isfinite(threshold):
        raise ValueError("threshold must be finite or None")
    _validate_comparable_observations(models_dict, var_name)
    results = {}
    for name, idata in models_dict.items():
        loo_result = az.loo(idata, pointwise=True, var_name=var_name)
        pareto_k = np.asarray(loo_result.pareto_k.values)
        cutoff = float(loo_result.good_k if threshold is None else threshold)
        invalid = ~np.isfinite(pareto_k)
        n_high = int(((pareto_k > cutoff) | invalid).sum())
        results[name] = {
            'pareto_k': pareto_k, 'n_high': n_high,
            'n_very_high': int((pareto_k > 1).sum()),
            'n_nonfinite': int(invalid.sum()), 'threshold': cutoff,
            'max_k': float(pareto_k.max()), 'loo': loo_result,
        }
        if verbose:
            print(f"{name}: {n_high} observations fail Pareto-k <= {cutoff:.3f}")
            if n_high:
                print('[WARN] Investigate influential units; refit LOO cases or use structured K-fold CV.')
                print('Switching to WAIC does not repair unreliable PSIS-LOO.')
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


def model_averaging(models_dict: Dict[str, Any], weights=None, var_name='y_obs',
                    ic='loo', *, group='posterior_predictive', n_samples=None,
                    random_seed=None):
    """Sample a predictive mixture, preserving within-draw dependence and variance.

    Returns (draws, weights_in_input_model_order). Draws have shape
    (n_samples, *prediction_dimensions), not (chain, draw, ...). Each draw selects
    one model then one complete joint predictive draw. It never averages paired
    draws. Stacking weights are predictive weights, not posterior model probabilities.
    All models must provide the same explicit group, variable, dimensions and
    coordinates; missing predictions and invalid weights raise ValueError.
    """
    names = list(models_dict)
    if not names:
        raise ValueError("At least one model is required")
    if weights is None:
        comparison = compare_models(models_dict, ic=ic, verbose=False)
        weights = comparison.loc[names, 'weight'].to_numpy()
    weights = np.asarray(weights, dtype=float)
    if weights.shape != (len(names),) or not np.isfinite(weights).all() or (weights < 0).any():
        raise ValueError("Supply one finite nonnegative weight per model")
    if weights.sum() <= 0 or not np.isfinite(weights.sum()):
        raise ValueError("Weights must have a finite positive sum")
    weights = weights / weights.sum()
    predictions, reference = [], None
    for name in names:
        idata = models_dict[name]
        if not hasattr(idata, group) or var_name not in idata[group]:
            raise ValueError(f"{name}: missing {group}/{var_name}")
        pred = idata[group][var_name]
        if not {'chain', 'draw'}.issubset(pred.dims):
            raise ValueError(f"{name}: predictions need chain and draw dimensions")
        dims = [d for d in pred.dims if d not in ('chain', 'draw')]
        ordered = pred.transpose('chain', 'draw', *dims)
        layout = ordered.isel(chain=0, draw=0, drop=True)
        if reference is None:
            reference = layout
        elif layout.dims != reference.dims or layout.sizes != reference.sizes or not layout.coords.equals(reference.coords):
            raise ValueError("Prediction dimensions and coordinates must match exactly")
        values = ordered.values.reshape((-1, *layout.shape))
        if not np.isfinite(values).all():
            raise ValueError(f"{name}: nonfinite predictive draws")
        predictions.append(values)
    if n_samples is None:
        n_samples = min(len(p) for p in predictions)
    if not isinstance(n_samples, (int, np.integer)) or n_samples <= 0:
        raise ValueError("n_samples must be a positive integer")
    rng = np.random.default_rng(random_seed)
    choices = rng.choice(len(names), size=n_samples, p=weights)
    mixture = np.empty((n_samples, *reference.shape), dtype=np.result_type(*predictions))
    for index, pred in enumerate(predictions):
        mask = choices == index
        mixture[mask] = pred[rng.integers(len(pred), size=int(mask.sum()))]
    return mixture, weights


def cross_validation_comparison(models_dict: Dict[str, Any], k=10, verbose=True):
    """Print a conceptual K-fold guide; this function does not fit or score models."""
    if not isinstance(k, int) or k < 2:
        raise ValueError("k must be an integer >= 2")
    if verbose:
        print(f"K-fold guide: {k} folds; no fits have been performed.")
        print("Choose independent units (rows, groups, or future time blocks) before splitting.")
        print("For each fold: fit preprocessing and model only on training data; diagnose it.")
        print("Update predictor AND observed pm.Data containers and coordinates for held-out data.")
        print("Compute held-out log likelihood with extend_inferencedata=False to preserve training groups.")
        print("For each held-out unit, compute logsumexp(log_lik over posterior draws) - log(n_draws).")
        print("Sum these log predictive densities over units; do NOT sum log likelihood over draws.")
        print("For a joint held-out group, sum log likelihood within that group BEFORE logsumexp.")
        print("Compare paired fold/unit scores and uncertainty on the same outcome scale.")


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
        idata1 = pm.sample()
        pm.compute_log_likelihood(idata1)

    with pm.Model() as model2:
        # ... define model 2 ...
        idata2 = pm.sample()
        pm.compute_log_likelihood(idata2)

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
