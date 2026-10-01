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


def check_diagnostics(idata, var_names=None, ess_threshold=400, rhat_threshold=1.01,
                      max_treedepth=None, bfmi_threshold=0.3):
    """Screen MCMC draws; a clean screen is not proof of convergence or identification.

    Targets PyMC 6 / ArviZ 1 DataTree objects. ESS is pooled across chains.
    Supply the sampler's configured max_treedepth when it does not record
    reached_max_treedepth. Missing HMC statistics are reported as unavailable,
    not silently counted as zero. VI draws are not independent MCMC chains.
    """
    import numpy as np

    if ess_threshold <= 0 or not np.isfinite(ess_threshold):
        raise ValueError("ess_threshold must be finite and positive")
    if not np.isfinite(rhat_threshold) or rhat_threshold < 1:
        raise ValueError("rhat_threshold must be finite and at least 1")
    if max_treedepth is not None and (max_treedepth <= 0 or int(max_treedepth) != max_treedepth):
        raise ValueError("max_treedepth must be a positive integer or None")
    if not np.isfinite(bfmi_threshold) or bfmi_threshold <= 0:
        raise ValueError("bfmi_threshold must be finite and positive")
    if not hasattr(idata, 'posterior') or not idata.posterior.data_vars:
        raise ValueError("A nonempty posterior group is required")
    summary = az.summary(idata, var_names=var_names, round_to="none")
    if summary.empty:
        raise ValueError("No posterior variables selected")
    issues, unavailable = [], []
    results = {'summary': summary, 'issues': issues, 'unavailable': unavailable}
    if idata.posterior.sizes.get('chain', 0) < 2:
        issues.append('insufficient_chains')
    diagnostic_columns = ['r_hat', 'ess_bulk', 'ess_tail']
    if not np.isfinite(summary[diagnostic_columns].to_numpy()).all():
        issues.append('nonfinite_diagnostics')
    if (summary['r_hat'] > rhat_threshold).any():
        issues.append('convergence')
    if (summary[['ess_bulk', 'ess_tail']] < ess_threshold).any().any():
        issues.append('low_ess')

    stats = getattr(idata, 'sample_stats', None)
    if stats is not None and 'diverging' in stats:
        divergences = stats['diverging'].values
        if not np.isfinite(divergences).all():
            issues.append('nonfinite_sampler_stats')
        else:
            count = int(divergences.sum())
            if count:
                results['n_divergences'] = count
                issues.append('divergences')
    else:
        unavailable.append('divergences')

    if stats is not None and 'reached_max_treedepth' in stats:
        hit_values = stats['reached_max_treedepth'].values
        if not np.isfinite(hit_values).all():
            issues.append('nonfinite_sampler_stats')
        elif hit_values.any():
            issues.append('max_treedepth')
    elif stats is not None and 'tree_depth' in stats and max_treedepth is not None:
        depth = stats['tree_depth'].values
        if not np.isfinite(depth).all():
            issues.append('nonfinite_sampler_stats')
        elif (depth >= max_treedepth).any():
            issues.append('max_treedepth')
    else:
        unavailable.append('max_treedepth')

    if stats is not None and 'energy' in stats:
        # ArviZ 1.x returns a DataTree with one energy BFMI value per chain.
        bfmi = np.asarray(az.bfmi(idata)['energy'].values)
        results['bfmi'] = bfmi
        if not np.isfinite(bfmi).all():
            issues.append('nonfinite_bfmi')
        elif (bfmi < bfmi_threshold).any():
            issues.append('low_bfmi')
    else:
        unavailable.append('bfmi')
    results['has_issues'] = bool(issues)
    print('[WARN] Diagnostic flags: ' + ', '.join(issues) if issues else
          '[OK] No flags in the available numerical diagnostics')
    if unavailable:
        print('[INFO] Unavailable checks: ' + ', '.join(unavailable))
    print('Inspect traces, MCSE for the estimand, prior sensitivity and predictive checks.')
    print('This screen does not establish convergence, identifiability or model validity.')
    return results


def create_diagnostic_report(idata, var_names=None, output_dir='diagnostics/', show=False):
    """
    Create comprehensive diagnostic report with plots.

    Parameters
    ----------
    idata : xarray.DataTree
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
    if hasattr(idata, 'sample_stats') and 'energy' in idata.sample_stats:
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
    idata : xarray.DataTree
        Posterior object with posterior samples
    prior_idata : xarray.DataTree
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
