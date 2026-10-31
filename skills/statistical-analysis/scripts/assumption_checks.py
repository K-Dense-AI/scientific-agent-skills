"""Descriptive diagnostics, not an automatic test selector or proof of assumptions.

NaNs are omitted with counts; infinities, malformed arrays, insufficient samples
and undefined diagnostics raise ValueError. Independence requires study-design
review. Legacy ``is_normal``/``is_homogeneous`` fields mean only non-rejection.
"""

from typing import Dict, List, Optional, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats


def _alpha(alpha):
    if not np.isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError("alpha must be finite and between 0 and 1")


def _array(data):
    if np.iscomplexobj(data) or np.ma.isMaskedArray(data):
        raise ValueError("data must be real and unmasked; encode missing values as NaN")
    if isinstance(data, pd.Series):
        values = data.to_numpy(dtype=float, na_value=np.nan)
    else:
        values = np.asarray(data, dtype=float)
    if values.ndim != 1:
        raise ValueError("data must be one-dimensional")
    if np.isinf(values).any():
        raise ValueError("data must not contain infinite values")
    return values


def _clean(data, minimum=1, variable=False):
    values = _array(data)
    positions = np.flatnonzero(~np.isnan(values))
    clean = values[positions]
    if clean.size < minimum:
        raise ValueError(f"at least {minimum} non-missing observations are required")
    if variable and np.ptp(clean) == 0:
        raise ValueError("constant data do not support this diagnostic")
    return clean, positions, len(values) - len(clean)


def _groups(data, value_col, group_col, minimum=1):
    if data.empty or data[group_col].isna().any():
        raise ValueError("group labels must be non-missing and data nonempty")
    groups = []
    for label, frame in data.groupby(group_col, sort=False, observed=True):
        clean, positions, omitted = _clean(frame[value_col], minimum=minimum)
        groups.append((label, clean, omitted, frame, positions))
    return groups


def _finish_plot():
    plt.tight_layout()
    plt.show()
    plt.close()


def check_normality(
    data: Union[np.ndarray, pd.Series, List], name: str = "data",
    alpha: float = 0.05, plot: bool = True
) -> Dict:
    """Shapiro-Wilk screen with Q-Q/histogram; n>5000 has no binary verdict.

    ``is_normal`` is a legacy alias for ``normality_not_rejected`` and never
    establishes normality. NaN omissions are returned as ``n_missing``.
    """
    _alpha(alpha)
    clean, _, missing = _clean(data, minimum=3, variable=True)
    statistic, p_value = stats.shapiro(clean)
    if not np.isfinite([statistic, p_value]).all():
        raise ValueError("Shapiro-Wilk returned a non-finite result")
    reliable = len(clean) <= 5000
    decision = bool(p_value > alpha) if reliable else None
    finding = ("not rejected" if decision else "rejected") if reliable else "not assessed by p-value (n > 5000)"
    interpretation = f"Normality {finding} (W = {statistic:.3f}, p = {p_value:.3g}); this does not verify assumptions."
    if plot:
        _, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
        stats.probplot(clean, dist="norm", plot=ax1)
        ax1.set_title(f"Q-Q Plot: {name}")
        ax1.grid(alpha=0.3)
        ax2.hist(clean, bins='auto', density=True, alpha=0.7, color='steelblue', edgecolor='black')
        grid = np.linspace(clean.min(), clean.max(), 100)
        ax2.plot(grid, stats.norm.pdf(grid, clean.mean(), clean.std()), 'r-', label='Normal curve')
        ax2.set(xlabel='Value', ylabel='Density', title=f'Histogram: {name}')
        ax2.legend()
        _finish_plot()
    return {
        'test': 'Shapiro-Wilk', 'statistic': statistic, 'p_value': p_value,
        'is_normal': decision, 'normality_not_rejected': decision,
        'p_value_reliable': reliable, 'interpretation': interpretation,
        'n': len(clean), 'n_missing': missing,
        'recommendation': "Review the Q-Q plot, tails, design and estimand. Neither parametric nor non-parametric inference is selected by this p-value.",
    }


def check_normality_per_group(data: pd.DataFrame, value_col: str, group_col: str,
                              alpha: float = 0.05, plot: bool = True) -> pd.DataFrame:
    """One Shapiro-Wilk screen per observed group; 'Normal' is a legacy label.

    Yes means not rejected, No means rejected, and Unassessed means n>5000.
    Missing group labels are rejected; unused categorical levels are ignored.
    """
    _alpha(alpha)
    groups = _groups(data, value_col, group_col, minimum=3)
    results = []
    if plot:
        _, axes = plt.subplots(1, len(groups), figsize=(5 * len(groups), 4), squeeze=False)
    for i, (label, clean, missing, _, _) in enumerate(groups):
        result = check_normality(clean, alpha=alpha, plot=False)
        decision = result['normality_not_rejected']
        results.append({'Group': label, 'N': len(clean), 'N_missing': missing,
                        'W': result['statistic'], 'p-value': result['p_value'],
                        'Normal': 'Unassessed' if decision is None else ('Yes' if decision else 'No')})
        if plot:
            stats.probplot(clean, dist="norm", plot=axes[0, i])
            axes[0, i].set_title(f"Q-Q Plot: {label}")
    if plot:
        _finish_plot()
    return pd.DataFrame(results)


def check_homogeneity_of_variance(data: pd.DataFrame, value_col: str, group_col: str,
                                  alpha: float = 0.05, plot: bool = True) -> Dict:
    """Median-centered Levene (Brown-Forsythe) screen; does not select a test."""
    _alpha(alpha)
    groups = _groups(data, value_col, group_col, minimum=2)
    if len(groups) < 2:
        raise ValueError("at least two observed groups are required")
    arrays = [g[1] for g in groups]
    # All within-group absolute deviations constant makes Levene undefined.
    deviations = [np.abs(g - np.median(g)) for g in arrays]
    if all(np.ptp(z) == 0 for z in deviations):
        raise ValueError("Levene diagnostic is undefined for these within-group deviations")
    statistic, p_value = stats.levene(*arrays, center='median')
    if not np.isfinite([statistic, p_value]).all():
        raise ValueError("Levene returned a non-finite result")
    variances = np.array([np.var(g, ddof=1) for g in arrays])
    if not np.isfinite(variances).all():
        raise ValueError("variances overflowed; rescale values before diagnostics")
    ratio = float(variances.max() / variances.min()) if variances.min() else np.inf
    decision = bool(p_value > alpha)
    if plot:
        _, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
        labels = [str(g[0]) for g in groups]
        ax1.boxplot(arrays, tick_labels=labels)
        ax1.set(xlabel=group_col, ylabel=value_col, title='Box Plots by Group')
        ax2.bar(np.arange(len(groups)), variances, color='steelblue')
        ax2.set_xticks(np.arange(len(groups)), labels, rotation=45)
        ax2.set(ylabel='Variance', title='Variance by Group')
        _finish_plot()
    return {
        'test': 'Levene', 'center': 'median', 'statistic': statistic,
        'p_value': p_value, 'is_homogeneous': decision,
        'variance_equality_not_rejected': decision, 'variance_ratio': ratio,
        'groups': [g[0] for g in groups], 'variances': variances,
        'n_missing': sum(g[2] for g in groups),
        'interpretation': f"Equal variances {'not rejected' if decision else 'rejected'} (F = {statistic:.3f}, p = {p_value:.3g}); non-rejection is not evidence of equality.",
        'recommendation': "For independent mean comparisons, prespecify Welch inference rather than choosing pooled versus Welch by a variance pretest.",
    }


def check_linearity(x: Union[np.ndarray, pd.Series], y: Union[np.ndarray, pd.Series],
                    x_name: str = "X", y_name: str = "Y", plot: bool = True) -> Dict:
    """Simple-regression scatter/residual plots; Pearson r does not test linearity.

    Rows missing either variable are omitted together, preserving pairing.
    """
    x, y = _array(x), _array(y)
    if len(x) != len(y):
        raise ValueError("x and y must have the same length and aligned rows")
    keep = ~np.isnan(x) & ~np.isnan(y)
    missing = int((~keep).sum())
    x, y = x[keep], y[keep]
    _clean(x, minimum=3, variable=True)
    _clean(y, minimum=3, variable=True)
    slope, intercept, r_value, _, _ = stats.linregress(x, y)
    y_pred = intercept + slope * x
    residuals = y - y_pred
    if not np.isfinite([slope, intercept, r_value]).all():
        raise ValueError("linear fit returned non-finite results; review/rescale the data")
    if plot:
        _, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
        ax1.scatter(x, y, alpha=0.6)
        order = np.argsort(x)
        ax1.plot(x[order], y_pred[order], 'r-', label=f'y = {intercept:.2f} + {slope:.2f}x')
        ax1.set(xlabel=x_name, ylabel=y_name, title='Scatter Plot with Regression Line')
        ax1.legend()
        ax2.scatter(y_pred, residuals, alpha=0.6)
        ax2.axhline(0, color='r', linestyle='--')
        ax2.set(xlabel='Fitted values', ylabel='Residuals', title='Residuals vs Fitted Values')
        _finish_plot()
    return {
        'r': r_value, 'r_squared': r_value ** 2, 'n': len(x), 'n_missing': missing,
        'interpretation': "Examine residual plots for curvature and changing spread; correlation magnitude does not establish linearity.",
        'recommendation': "Review the conditional mean model and design; consider justified nonlinear terms or variance/dependence models.",
    }


def detect_outliers(data: Union[np.ndarray, pd.Series, List], name: str = "data",
                    method: str = "iqr", threshold: Optional[float] = None,
                    plot: bool = True) -> Dict:
    """Flag values for review; return original zero-based positions and labels.

    Defaults: IQR multiplier 1.5; population-SD z-score threshold 3. A flag is
    not permission to exclude/winsorize a legitimate observation.
    """
    if method not in ('iqr', 'zscore'):
        raise ValueError("method must be 'iqr' or 'zscore'")
    threshold = (1.5 if method == 'iqr' else 3.0) if threshold is None else threshold
    if not np.isfinite(threshold) or threshold <= 0:
        raise ValueError("threshold must be finite and positive")
    clean, positions, missing = _clean(data)
    if method == 'iqr':
        q1, q3 = np.percentile(clean, [25, 75])
        lower, upper = q1 - threshold * (q3 - q1), q3 + threshold * (q3 - q1)
    else:
        mean, sd = clean.mean(), clean.std()
        lower, upper = mean - threshold * sd, mean + threshold * sd
    if not np.isfinite([lower, upper]).all():
        raise ValueError("outlier bounds overflowed; rescale values")
    mask = (clean < lower) | (clean > upper)
    indices = positions[mask]
    labels = np.asarray(data.index)[indices] if isinstance(data, pd.Series) else indices.copy()
    if plot:
        _, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
        ax1.boxplot(clean, orientation='vertical', patch_artist=True)
        ax1.set(ylabel='Value', title=f'Box Plot: {name}')
        ax2.scatter(positions[~mask], clean[~mask], label='Unflagged', alpha=0.6)
        ax2.scatter(indices, clean[mask], label='Flagged', marker='D', color='red')
        ax2.axhline(lower, linestyle='--', color='orange', label='Bounds')
        ax2.axhline(upper, linestyle='--', color='orange')
        ax2.set(xlabel='Original row position', ylabel='Value', title=f'Outlier Screen: {name}')
        ax2.legend()
        _finish_plot()
    count = int(mask.sum())
    pct = 100 * count / len(clean)
    return {
        'method': method, 'threshold': threshold, 'n': len(clean), 'n_missing': missing,
        'n_outliers': count, 'pct_outliers': pct, 'outlier_indices': indices,
        'outlier_labels': labels, 'outlier_values': clean[mask],
        'lower_bound': lower, 'upper_bound': upper,
        'interpretation': f"Flagged {count} observations ({pct:.1f}% of non-missing data)",
        'recommendation': "Investigate provenance and data-entry errors. Retain valid observations; justify exclusions and report prespecified sensitivity/robust analyses.",
    }


def check_regression_diagnostics(model, alpha: float = 0.05, plot: bool = True,
                                 ordered: bool = False) -> Dict:
    """Diagnostics for full-rank OLS with intercept, positive residual df/spread.

    Durbin-Watson is reported only for meaningfully ordered rows (ordered=True)
    and has no universal pass threshold. Dependence/causal design is not tested.
    """
    from statsmodels.regression.linear_model import OLS
    from statsmodels.stats.diagnostic import het_breuschpagan
    from statsmodels.stats.stattools import durbin_watson
    from statsmodels.stats.outliers_influence import variance_inflation_factor

    _alpha(alpha)
    if not isinstance(model.model, OLS):
        raise ValueError("this helper requires fitted OLS results")
    residuals = _array(model.resid)
    fitted = _array(model.fittedvalues)
    exog = np.asarray(model.model.exog, dtype=float)
    if not all(np.isfinite(x).all() for x in (residuals, fitted, exog)):
        raise ValueError("fitted data must be finite")
    constants = np.flatnonzero((np.ptp(exog, axis=0) == 0) & (exog[0] != 0))
    if len(constants) != 1 or exog.shape[1] < 2:
        raise ValueError("OLS must have an explicit nonzero intercept and at least one predictor")
    if np.linalg.matrix_rank(exog) != exog.shape[1] or model.df_resid <= 0:
        raise ValueError("OLS design must be full rank with positive residual degrees of freedom")
    if np.linalg.norm(residuals) <= np.finfo(float).eps * max(1, np.linalg.norm(model.model.endog)) * len(residuals):
        raise ValueError("near-perfect fit does not support residual diagnostics")
    normality = check_normality(residuals, alpha=alpha, plot=False)
    normality['ok'] = normality['normality_not_rejected']  # legacy non-rejection alias
    lm, lm_p, f_value, f_p = het_breuschpagan(residuals, exog, robust=True)
    if not np.isfinite([lm, lm_p, f_value, f_p]).all():
        raise ValueError("heteroscedasticity diagnostic is undefined")
    dw = float(durbin_watson(residuals)) if ordered else None
    vif_table = pd.DataFrame([
        {'Variable': name, 'VIF': variance_inflation_factor(exog, i)}
        for i, name in enumerate(model.model.exog_names) if i not in constants
    ])
    max_vif = float(vif_table['VIF'].max())
    if plot:
        _, axes = plt.subplots(2, 2, figsize=(12, 10))
        axes[0, 0].scatter(fitted, residuals, alpha=0.6)
        axes[0, 0].axhline(0, color='r', linestyle='--')
        axes[0, 0].set(xlabel='Fitted values', ylabel='Residuals', title='Residuals vs Fitted')
        stats.probplot(residuals, dist='norm', plot=axes[0, 1])
        axes[0, 1].set_title('Normal Q-Q')
        standardized = model.get_influence().resid_studentized_internal
        axes[1, 0].scatter(fitted, np.sqrt(np.abs(standardized)), alpha=0.6)
        axes[1, 0].set(xlabel='Fitted values', ylabel='sqrt(|Studentized residual|)', title='Scale-Location')
        axes[1, 1].hist(residuals, bins='auto', edgecolor='black')
        axes[1, 1].set(xlabel='Residuals', ylabel='Frequency', title='Residual Histogram')
        _finish_plot()
    issues = []
    if normality['normality_not_rejected'] is False:
        issues.append('residual normality rejected; review tails and inference robustness')
    if normality['normality_not_rejected'] is None:
        issues.append('Shapiro p-value unreliable above 5000 observations; inspect residual plots')
    if lm_p <= alpha:
        issues.append('heteroscedasticity screen rejected; consider justified HC3 or variance modeling')
    if not np.isfinite(max_vif) or max_vif > 5:
        issues.append('large VIF; examine identifiability and precision without automatically removing adjustment covariates')
    return {
        'residual_normality': normality,
        'heteroscedasticity': {'test': 'Koenker Breusch-Pagan', 'statistic': lm,
                              'p_value': lm_p, 'f_statistic': f_value, 'f_p_value': f_p,
                              'ok': bool(lm_p > alpha)},
        'autocorrelation': {'test': 'Durbin-Watson', 'statistic': dw, 'ok': None,
                            'interpretation': 'Requires meaningful row order and design-specific inference; cannot establish independence.'},
        'vif': vif_table, 'max_vif': max_vif, 'issues': issues,
        'interpretation': ('Screen flags: ' + '; '.join(issues) if issues else 'No flags in these numerical screens.') + ' Review plots, sampling units, dependence, exogeneity and model specification separately.',
    }


def comprehensive_assumption_check(data: pd.DataFrame, value_col: str,
                                    group_col: Optional[str] = None,
                                    alpha: float = 0.05, plot: bool = True) -> Dict:
    """Grouped descriptive screens; does not handle pairing/clustering itself.

    For paired tests pass aligned difference scores without group_col. Review
    regression residuals using check_regression_diagnostics instead.
    """
    _alpha(alpha)
    if group_col is not None:
        groups = _groups(data, value_col, group_col, minimum=3)
        results = {
            'outliers_per_group': {label: detect_outliers(frame[value_col], name=str(label), plot=plot)
                                  for label, _, _, frame, _ in groups},
            'normality_per_group': check_normality_per_group(data, value_col, group_col, alpha, plot),
            'homogeneity': check_homogeneity_of_variance(data, value_col, group_col, alpha, plot),
        }
    else:
        results = {'outliers': detect_outliers(data[value_col], name=value_col, plot=plot),
                   'normality': check_normality(data[value_col], name=value_col, alpha=alpha, plot=plot)}
    print('[OK] Diagnostic calculations completed. Missing-value counts are in each result.')
    print('-> These screens do not establish assumptions or select a test. Review design, estimand and plots.')
    return results


if __name__ == '__main__':
    rng = np.random.default_rng(42)
    df = pd.DataFrame({'score': np.r_[rng.normal(75, 8, 50), rng.normal(68, 10, 50)],
                       'group': ['A'] * 50 + ['B'] * 50})
    results = comprehensive_assumption_check(df, 'score', 'group')
