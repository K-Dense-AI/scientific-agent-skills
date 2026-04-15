"""Statistical analysis: descriptive stats, hypothesis testing, ANOVA,
regression, error propagation, and confidence intervals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence, Union

import numpy as np
from scipy import stats as sp_stats

from scripts.core.utils import validate_array


# ---------------------------------------------------------------------------
# Descriptive statistics
# ---------------------------------------------------------------------------

@dataclass
class DescriptiveStats:
    """Descriptive statistics for a dataset."""
    n: int
    mean: float
    std: float
    sem: float  # standard error of the mean
    median: float
    q1: float   # 25th percentile
    q3: float   # 75th percentile
    iqr: float
    min: float
    max: float
    range: float
    skewness: float
    kurtosis: float
    cv: float   # coefficient of variation (%)
    ci_95: tuple[float, float]  # 95% confidence interval for the mean

    def report(self) -> str:
        lines = [
            "[Praxis] Descriptive Statistics",
            f"  N          = {self.n}",
            f"  Mean       = {self.mean:.6g}",
            f"  Std Dev    = {self.std:.6g}",
            f"  SEM        = {self.sem:.6g}",
            f"  Median     = {self.median:.6g}",
            f"  Q1, Q3     = {self.q1:.6g}, {self.q3:.6g}",
            f"  IQR        = {self.iqr:.6g}",
            f"  Min, Max   = {self.min:.6g}, {self.max:.6g}",
            f"  Range      = {self.range:.6g}",
            f"  Skewness   = {self.skewness:.4f}",
            f"  Kurtosis   = {self.kurtosis:.4f}",
            f"  CV         = {self.cv:.2f}%",
            f"  95% CI     = ({self.ci_95[0]:.6g}, {self.ci_95[1]:.6g})",
        ]
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.report()


def descriptive(data: Any) -> DescriptiveStats:
    """Compute descriptive statistics for a dataset.

    Parameters
    ----------
    data : array-like
        1-D numeric data.

    Returns
    -------
    DescriptiveStats
    """
    arr = validate_array(data, "data")
    arr = arr[~np.isnan(arr)]
    n = len(arr)

    mean = np.mean(arr)
    std = np.std(arr, ddof=1)
    sem = std / np.sqrt(n)
    q1, median, q3 = np.percentile(arr, [25, 50, 75])

    # 95% CI using t-distribution
    if n > 1:
        t_crit = sp_stats.t.ppf(0.975, df=n - 1)
        ci = (mean - t_crit * sem, mean + t_crit * sem)
    else:
        ci = (mean, mean)

    cv = (std / abs(mean) * 100) if mean != 0 else 0.0

    result = DescriptiveStats(
        n=n, mean=mean, std=std, sem=sem,
        median=median, q1=q1, q3=q3, iqr=q3 - q1,
        min=np.min(arr), max=np.max(arr), range=np.ptp(arr),
        skewness=float(sp_stats.skew(arr)),
        kurtosis=float(sp_stats.kurtosis(arr)),
        cv=cv, ci_95=ci,
    )
    print(result.report())
    return result


# ---------------------------------------------------------------------------
# Hypothesis testing
# ---------------------------------------------------------------------------

@dataclass
class TestResult:
    """Result of a statistical test."""
    test_name: str
    statistic: float
    p_value: float
    df: Optional[float] = None
    effect_size: Optional[float] = None
    conclusion: str = ""

    def report(self) -> str:
        lines = [
            f"[Praxis] {self.test_name}",
            f"  Statistic  = {self.statistic:.6f}",
            f"  p-value    = {self.p_value:.6e}",
        ]
        if self.df is not None:
            lines.append(f"  df         = {self.df}")
        if self.effect_size is not None:
            lines.append(f"  Effect size = {self.effect_size:.4f}")
        if self.conclusion:
            lines.append(f"  Conclusion: {self.conclusion}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.report()


def t_test(
    a: Any,
    b: Optional[Any] = None,
    *,
    paired: bool = False,
    mu: float = 0.0,
    alpha: float = 0.05,
    alternative: str = "two-sided",
) -> TestResult:
    """Perform a t-test.

    Parameters
    ----------
    a : array-like
        First sample.
    b : array-like, optional
        Second sample. If None, performs one-sample test against *mu*.
    paired : bool
        Paired t-test (requires equal-length a and b).
    mu : float
        Population mean for one-sample test.
    alpha : float
        Significance level.
    alternative : str
        'two-sided', 'less', or 'greater'.

    Returns
    -------
    TestResult
    """
    a = validate_array(a, "a")
    a = a[~np.isnan(a)]

    if b is None:
        # One-sample t-test
        stat, p = sp_stats.ttest_1samp(a, mu, alternative=alternative)
        name = f"One-sample t-test (mu={mu})"
        df = len(a) - 1
        d = (np.mean(a) - mu) / np.std(a, ddof=1) if np.std(a, ddof=1) > 0 else 0
    elif paired:
        b = validate_array(b, "b")
        b = b[~np.isnan(b)]
        stat, p = sp_stats.ttest_rel(a, b, alternative=alternative)
        name = "Paired t-test"
        df = len(a) - 1
        diff = a - b
        d = np.mean(diff) / np.std(diff, ddof=1) if np.std(diff, ddof=1) > 0 else 0
    else:
        b = validate_array(b, "b")
        b = b[~np.isnan(b)]
        stat, p = sp_stats.ttest_ind(a, b, alternative=alternative)
        name = "Independent two-sample t-test"
        df = len(a) + len(b) - 2
        pooled_std = np.sqrt(
            ((len(a) - 1) * np.var(a, ddof=1) + (len(b) - 1) * np.var(b, ddof=1)) / df
        )
        d = (np.mean(a) - np.mean(b)) / pooled_std if pooled_std > 0 else 0

    sig = "significant" if p < alpha else "not significant"
    conclusion = f"p={p:.4e}, {sig} at alpha={alpha}"

    result = TestResult(
        test_name=name, statistic=stat, p_value=p,
        df=df, effect_size=d, conclusion=conclusion,
    )
    print(result.report())
    return result


def anova(*groups: Any, alpha: float = 0.05) -> TestResult:
    """One-way ANOVA.

    Parameters
    ----------
    *groups : array-like
        Two or more groups to compare.
    alpha : float
        Significance level.

    Returns
    -------
    TestResult
    """
    if len(groups) < 2:
        raise ValueError("ANOVA requires at least 2 groups.")

    clean = [validate_array(g, f"group_{i}") for i, g in enumerate(groups)]
    clean = [g[~np.isnan(g)] for g in clean]

    stat, p = sp_stats.f_oneway(*clean)

    # Effect size: eta-squared
    grand_mean = np.mean(np.concatenate(clean))
    ss_between = sum(len(g) * (np.mean(g) - grand_mean) ** 2 for g in clean)
    ss_total = sum(np.sum((g - grand_mean) ** 2) for g in clean)
    eta_sq = ss_between / ss_total if ss_total > 0 else 0

    k = len(clean)
    n_total = sum(len(g) for g in clean)
    df_between = k - 1
    df_within = n_total - k

    sig = "significant" if p < alpha else "not significant"
    conclusion = f"F({df_between},{df_within})={stat:.4f}, p={p:.4e}, {sig} at alpha={alpha}"

    result = TestResult(
        test_name=f"One-way ANOVA ({k} groups)",
        statistic=stat, p_value=p,
        df=df_between, effect_size=eta_sq,
        conclusion=conclusion,
    )
    print(result.report())
    return result


def normality_test(data: Any, method: str = "shapiro") -> TestResult:
    """Test for normality.

    Parameters
    ----------
    data : array-like
    method : str
        'shapiro' (Shapiro-Wilk), 'ks' (Kolmogorov-Smirnov),
        'dagostino' (D'Agostino-Pearson).

    Returns
    -------
    TestResult
    """
    arr = validate_array(data, "data")
    arr = arr[~np.isnan(arr)]

    if method == "shapiro":
        stat, p = sp_stats.shapiro(arr)
        name = "Shapiro-Wilk normality test"
    elif method == "ks":
        stat, p = sp_stats.kstest(arr, "norm", args=(np.mean(arr), np.std(arr, ddof=1)))
        name = "Kolmogorov-Smirnov normality test"
    elif method == "dagostino":
        stat, p = sp_stats.normaltest(arr)
        name = "D'Agostino-Pearson normality test"
    else:
        raise ValueError(f"Unknown method: {method}. Use 'shapiro', 'ks', or 'dagostino'.")

    conclusion = "normally distributed" if p > 0.05 else "not normally distributed"
    result = TestResult(test_name=name, statistic=stat, p_value=p, conclusion=f"Data is {conclusion} (p={p:.4e})")
    print(result.report())
    return result


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------

@dataclass
class RegressionResult:
    """Result of linear regression."""
    slope: float
    intercept: float
    r_value: float
    r_squared: float
    p_value: float
    std_err: float
    intercept_stderr: float
    equation: str

    def report(self) -> str:
        lines = [
            "[Praxis] Linear Regression",
            f"  y = {self.slope:.6g} * x + {self.intercept:.6g}",
            f"  R2       = {self.r_squared:.6f}",
            f"  R        = {self.r_value:.6f}",
            f"  p-value  = {self.p_value:.4e}",
            f"  Slope SE = {self.std_err:.6g}",
        ]
        return "\n".join(lines)

    def __repr__(self) -> str:
        return self.report()


def linear_regression(x: Any, y: Any) -> RegressionResult:
    """Simple linear regression: y = mx + b.

    Parameters
    ----------
    x, y : array-like

    Returns
    -------
    RegressionResult
    """
    x = validate_array(x, "x")
    y = validate_array(y, "y")

    # Remove NaNs
    mask = ~(np.isnan(x) | np.isnan(y))
    x, y = x[mask], y[mask]

    res = sp_stats.linregress(x, y)

    result = RegressionResult(
        slope=res.slope,
        intercept=res.intercept,
        r_value=res.rvalue,
        r_squared=res.rvalue ** 2,
        p_value=res.pvalue,
        std_err=res.stderr,
        intercept_stderr=res.intercept_stderr,
        equation=f"y = {res.slope:.6g}x + {res.intercept:.6g}",
    )
    print(result.report())
    return result


# ---------------------------------------------------------------------------
# Error propagation
# ---------------------------------------------------------------------------

def propagate_error(
    func: str,
    values: dict[str, float],
    uncertainties: dict[str, float],
) -> tuple[float, float]:
    """Propagate uncertainties through a function using partial derivatives.

    Uses the uncertainties package for automatic error propagation.

    Parameters
    ----------
    func : str
        Mathematical expression, e.g. 'a * b / c'.
    values : dict
        Variable values, e.g. {'a': 10, 'b': 5, 'c': 2}.
    uncertainties : dict
        Variable uncertainties (1-sigma), e.g. {'a': 0.1, 'b': 0.05, 'c': 0.02}.

    Returns
    -------
    (result_value, result_uncertainty)
    """
    from uncertainties import ufloat
    import uncertainties.umath as umath

    # Build uncertain values
    uvars = {}
    for name in values:
        unc = uncertainties.get(name, 0.0)
        uvars[name] = ufloat(values[name], unc)

    # Evaluate
    namespace = {
        **uvars,
        "exp": umath.exp, "log": umath.log, "log10": umath.log10,
        "sin": umath.sin, "cos": umath.cos, "tan": umath.tan,
        "sqrt": umath.sqrt, "pi": np.pi, "abs": abs,
    }

    result = eval(func, {"__builtins__": {}}, namespace)
    val = result.nominal_value
    unc = result.std_dev

    print(f"[Praxis] Error propagation: {func}")
    print(f"  Result = {val:.6g} +/- {unc:.6g}")
    return val, unc


# ---------------------------------------------------------------------------
# Confidence intervals
# ---------------------------------------------------------------------------

def confidence_interval(
    data: Any,
    confidence: float = 0.95,
) -> tuple[float, float, float]:
    """Compute confidence interval for the mean.

    Parameters
    ----------
    data : array-like
    confidence : float
        Confidence level (0 to 1).

    Returns
    -------
    (mean, lower, upper)
    """
    arr = validate_array(data, "data")
    arr = arr[~np.isnan(arr)]
    n = len(arr)
    mean = np.mean(arr)
    sem = sp_stats.sem(arr)
    alpha = 1 - confidence
    t_crit = sp_stats.t.ppf(1 - alpha / 2, df=n - 1)
    margin = t_crit * sem

    print(f"[Praxis] {confidence*100:.0f}% CI: {mean:.6g} ({mean - margin:.6g}, {mean + margin:.6g})")
    return mean, mean - margin, mean + margin
