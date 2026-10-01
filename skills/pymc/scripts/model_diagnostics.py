"""
PyMC Model Diagnostics Script

Comprehensive diagnostic checks for PyMC models.
Run this after sampling to validate results before interpretation.

Usage:
    from scripts.model_diagnostics import check_diagnostics, create_diagnostic_report

    # Quick check
    check_diagnostics(idata)

    # Full report with plots
    create_diagnostic_report(idata, var_names=['alpha', 'beta', 'sigma'], output_dir='diagnostics/')
"""

import arviz as az
import matplotlib.pyplot as plt
from pathlib import Path


def check_diagnostics(idata, var_names=None, ess_threshold=400, rhat_threshold=1.01):
    """
    Perform comprehensive diagnostic checks on MCMC samples.

    Parameters
    ----------
    idata : xarray.DataTree or arviz.InferenceData
        Posterior object from pm.sample()
    var_names : list, optional
        Variables to check. If None, checks all model parameters
    ess_threshold : int
        Minimum acceptable effective sample size (default: 400)
    rhat_threshold : float
        Maximum acceptable R-hat value (default: 1.01)

    Returns
    -------
    dict
        Dictionary with diagnostic results and flags
    """
    print("="*70)
    print(" " * 20 + "MCMC DIAGNOSTICS REPORT")
    print("="*70)

    # Get summary statistics. round_to="none" is required: ArviZ 1.x formats the
    # default summary for display, returning strings, which makes every numeric
    # comparison below raise TypeError.
    summary = az.summary(idata, var_names=var_names, round_to="none")

    results = {
        'summary': summary,
        'has_issues': False,
        'issues': []
    }

    # 1. Check R-hat (convergence)
    print("\n1. CONVERGENCE CHECK (R-hat)")
    print("-" * 70)
    bad_rhat = summary[summary['r_hat'] > rhat_threshold]

    if len(bad_rhat) > 0:
        print(f"[WARN]  WARNING: {len(bad_rhat)} parameters have R-hat > {rhat_threshold}")
        print("\nTop 10 worst R-hat values:")
        print(bad_rhat[['r_hat']].sort_values('r_hat', ascending=False).head(10))
        print("\n[WARN]  Chains may not have converged!")
        print("   -> Run longer chains or check for multimodality")
        results['has_issues'] = True
        results['issues'].append('convergence')
    else:
        print(f"[OK] All R-hat values <= {rhat_threshold}")
        print("  Chains have converged successfully")

    # 2. Check Effective Sample Size
    print("\n2. EFFECTIVE SAMPLE SIZE (ESS)")
    print("-" * 70)
    low_ess_bulk = summary[summary['ess_bulk'] < ess_threshold]
    low_ess_tail = summary[summary['ess_tail'] < ess_threshold]

    if len(low_ess_bulk) > 0 or len(low_ess_tail) > 0:
        print(f"[WARN]  WARNING: Some parameters have ESS < {ess_threshold}")

        if len(low_ess_bulk) > 0:
            print(f"\n   Bulk ESS issues ({len(low_ess_bulk)} parameters):")
            print(low_ess_bulk[['ess_bulk']].sort_values('ess_bulk').head(10))

        if len(low_ess_tail) > 0:
            print(f"\n   Tail ESS issues ({len(low_ess_tail)} parameters):")
            print(low_ess_tail[['ess_tail']].sort_values('ess_tail').head(10))

        print("\n[WARN]  High autocorrelation detected!")
        print("   -> Sample more draws or reparameterize to reduce correlation")
        results['has_issues'] = True
        results['issues'].append('low_ess')
    else:
        print(f"[OK] All ESS values >= {ess_threshold}")
        print("  Sufficient effective samples")

    # 3. Check Divergences
    print("\n3. DIVERGENT TRANSITIONS")
    print("-" * 70)
    divergences = idata.sample_stats.diverging.sum().item()

    if divergences > 0:
        total_samples = len(idata.posterior.draw) * len(idata.posterior.chain)
        divergence_rate = divergences / total_samples * 100

        print(f"[WARN]  WARNING: {divergences} divergent transitions ({divergence_rate:.2f}% of samples)")
        print("\n   Divergences indicate biased sampling in difficult posterior regions")
        print("   Solutions:")
        print("   -> Increase target_accept (e.g., target_accept=0.95 or 0.99)")
        print("   -> Use non-centered parameterization for hierarchical models")
        print("   -> Add stronger/more informative priors")
        print("   -> Check for model misspecification")
        results['has_issues'] = True
        results['issues'].append('divergences')
        results['n_divergences'] = divergences
    else:
        print("[OK] No divergences detected")
        print("  NUTS explored the posterior successfully")

    # 4. Check Tree Depth
    print("\n4. TREE DEPTH")
    print("-" * 70)
    tree_depth = idata.sample_stats.tree_depth
    max_tree_depth = tree_depth.max().item()

    # Typical max_treedepth is 10 (default in PyMC)
    hits_max = (tree_depth >= 10).sum().item()

    if hits_max > 0:
        total_samples = len(idata.posterior.draw) * len(idata.posterior.chain)
        hit_rate = hits_max / total_samples * 100

        print(f"[WARN]  WARNING: Hit maximum tree depth {hits_max} times ({hit_rate:.2f}% of samples)")
        print("\n   Model may be difficult to explore efficiently")
        print("   Solutions:")
        print("   -> Reparameterize model to improve geometry")
        print("   -> Increase max_treedepth (if necessary)")
        results['issues'].append('max_treedepth')
    else:
        print(f"[OK] No maximum tree depth issues")
        print(f"  Maximum tree depth reached: {max_tree_depth}")

    # 5. Check Energy (if available)
    if hasattr(idata.sample_stats, 'energy'):
        print("\n5. ENERGY DIAGNOSTICS")
        print("-" * 70)
        print("[OK] Energy statistics available")
        print("  Use az.plot_energy(idata) to visualize energy transitions")
        print("  Good separation indicates healthy HMC sampling")

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    if not results['has_issues']:
        print("[OK] All diagnostics passed!")
        print("  Your model has sampled successfully.")
        print("  Proceed with inference and interpretation.")
    else:
        print("[WARN]  Some diagnostics failed!")
        print(f"  Issues found: {', '.join(results['issues'])}")
        print("  Review warnings above and consider re-running with adjustments.")

    print("="*70)

    return results


def create_diagnostic_report(idata, var_names=None, output_dir='diagnostics/', show=False):
    """
    Create comprehensive diagnostic report with plots.

    Parameters
    ----------
    idata : xarray.DataTree or arviz.InferenceData
        Posterior object from pm.sample()
    var_names : list, optional
        Variables to plot. If None, uses all model parameters
    output_dir : str
        Directory to save diagnostic plots
    show : bool
        Whether to display plots (default: False, just save)

    Returns
    -------
    dict
        Diagnostic results from check_diagnostics
    """
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Run diagnostic checks
    results = check_diagnostics(idata, var_names=var_names)

    print(f"\nGenerating diagnostic plots in '{output_dir}'...")

    # ArviZ 1.x plots return a PlotCollection and do not draw into pyplot's
    # current figure, so the figure must be saved through the collection --
    # plt.savefig() would write a blank image.
    def _save(plot_collection, filename, label):
        plot_collection.savefig(
            output_path / filename, dpi=300, bbox_inches='tight'
        )
        print(f"  [OK] Saved {label}")
        if show:
            plt.show()
        else:
            plt.close(plot_collection.viz['figure'].item())

    # 1. Trace plots
    _save(
        az.plot_trace_dist(idata, var_names=var_names),
        'trace_plots.png',
        'trace plots',
    )

    # 2. Rank plots (check mixing)
    _save(
        az.plot_rank(idata, var_names=var_names),
        'rank_plots.png',
        'rank plots',
    )

    # 3. Autocorrelation plots
    _save(
        az.plot_autocorr(idata, var_names=var_names),
        'autocorr_plots.png',
        'autocorrelation plots',
    )

    # 4. Energy plot (if available)
    if hasattr(idata.sample_stats, 'energy'):
        _save(az.plot_energy(idata), 'energy_plot.png', 'energy plot')

    # 5. ESS plot. ArviZ 1.x offers 'local' and 'quantile'; the old
    # 'evolution' kind no longer exists.
    _save(
        az.plot_ess(idata, var_names=var_names, kind='local'),
        'ess_local.png',
        'local ESS plot',
    )

    # Save summary to CSV
    results['summary'].to_csv(output_path / 'summary_statistics.csv')
    print(f"  [OK] Saved summary statistics")

    print(f"\nDiagnostic report complete! Files saved in '{output_dir}'")

    return results


def compare_prior_posterior(idata, prior_idata, var_names=None, output_path=None):
    """
    Compare prior and posterior distributions.

    Parameters
    ----------
    idata : xarray.DataTree or arviz.InferenceData
        Posterior object with posterior samples
    prior_idata : xarray.DataTree or arviz.InferenceData
        Prior object with prior samples
    var_names : list, optional
        Variables to compare. Defaults to the first three posterior variables.
    output_path : str, optional
        If provided, save plot to this path

    Returns
    -------
    arviz_plots.PlotCollection
        The overlaid prior/posterior figure.
    """
    if var_names is None:
        var_names = list(idata.posterior.data_vars)[:3]

    # ArviZ 1.x plot functions take a DataTree and a group name, not a flat
    # array plus an axis. Passing the first call's PlotCollection back into the
    # second is what overlays the two distributions on the same axes.
    collection = az.plot_dist(
        prior_idata,
        group='prior',
        var_names=var_names,
        visuals={'dist': {'color': 'blue'}},
    )
    az.plot_dist(
        idata,
        group='posterior',
        var_names=var_names,
        plot_collection=collection,
        visuals={'dist': {'color': 'green'}},
    )

    if output_path:
        collection.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Prior-posterior comparison saved to {output_path}")
        print("Prior is blue, posterior is green")
    else:
        plt.show()

    return collection


# Example usage
if __name__ == '__main__':
    print("This script provides diagnostic functions for PyMC models.")
    print("\nExample usage:")
    print("""
    import pymc as pm
    from scripts.model_diagnostics import check_diagnostics, create_diagnostic_report

    # After sampling
    with pm.Model() as model:
        # ... define model ...
        idata = pm.sample()

    # Quick diagnostic check
    results = check_diagnostics(idata)

    # Full diagnostic report with plots
    create_diagnostic_report(
        idata,
        var_names=['alpha', 'beta', 'sigma'],
        output_dir='my_diagnostics/'
    )
    """)
