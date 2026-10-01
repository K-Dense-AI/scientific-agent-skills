#!/usr/bin/env python3
"""Shared statistics and I/O for analytical method validation checks.

Standard library only. Every distribution function here is implemented from the
regularised incomplete beta and gamma functions so the scripts run in any
Python 3.11+ interpreter without numpy or scipy.

These helpers compute and report. They never decide that a procedure is
validated, fit for purpose, or acceptable to a regulator -- that judgement
belongs to the analyst and the quality unit.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

# --------------------------------------------------------------------------
# Limits and exit codes
# --------------------------------------------------------------------------

MAX_INPUT_BYTES = 5_000_000
MAX_ROWS = 20_000

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_INPUT_ERROR = 2

TINY = 1e-300


class InputError(Exception):
    """Raised for malformed or out-of-bounds user input."""


# --------------------------------------------------------------------------
# Special functions
# --------------------------------------------------------------------------


def _betacf(a: float, b: float, x: float, itmax: int = 400, eps: float = 3e-16) -> float:
    """Continued fraction for the incomplete beta function (Lentz's method)."""
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < TINY:
        d = TINY
    d = 1.0 / d
    h = d
    for m in range(1, itmax + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < TINY:
            d = TINY
        c = 1.0 + aa / c
        if abs(c) < TINY:
            c = TINY
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < TINY:
            d = TINY
        c = 1.0 + aa / c
        if abs(c) < TINY:
            c = TINY
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def betainc(a: float, b: float, x: float) -> float:
    """Regularised incomplete beta function I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_front = (
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log1p(-x)
    )
    front = math.exp(log_front)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def gammainc_lower(a: float, x: float) -> float:
    """Regularised lower incomplete gamma P(a, x)."""
    if x <= 0.0:
        return 0.0
    if x < a + 1.0:
        # Series representation.
        term = 1.0 / a
        total = term
        n = a
        for _ in range(1000):
            n += 1.0
            term *= x / n
            total += term
            if abs(term) < abs(total) * 1e-16:
                break
        return total * math.exp(-x + a * math.log(x) - math.lgamma(a))
    # Continued fraction for Q(a, x), then complement.
    b = x + 1.0 - a
    c = 1.0 / TINY
    d = 1.0 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < TINY:
            d = TINY
        c = b + an / c
        if abs(c) < TINY:
            c = TINY
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-16:
            break
    q = math.exp(-x + a * math.log(x) - math.lgamma(a)) * h
    return 1.0 - q


def _bisect_ppf(cdf, target: float, lo: float, hi: float, tol: float = 1e-12) -> float:
    """Invert a monotone CDF by bisection."""
    for _ in range(300):
        mid = 0.5 * (lo + hi)
        if cdf(mid) < target:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol * max(1.0, abs(mid)):
            break
    return 0.5 * (lo + hi)


def t_cdf(t: float, df: float) -> float:
    """CDF of Student's t with df degrees of freedom."""
    if df <= 0:
        raise InputError("t distribution needs df > 0")
    x = df / (df + t * t)
    half = 0.5 * betainc(0.5 * df, 0.5, x)
    return half if t <= 0 else 1.0 - half


def t_ppf(p: float, df: float) -> float:
    """Quantile of Student's t."""
    if not 0.0 < p < 1.0:
        raise InputError("t_ppf needs 0 < p < 1")
    return _bisect_ppf(lambda t: t_cdf(t, df), p, -1e4, 1e4)


def chi2_cdf(x: float, df: float) -> float:
    """CDF of the chi-square distribution."""
    if x <= 0:
        return 0.0
    return gammainc_lower(0.5 * df, 0.5 * x)


def chi2_ppf(p: float, df: float) -> float:
    """Quantile of the chi-square distribution."""
    if not 0.0 < p < 1.0:
        raise InputError("chi2_ppf needs 0 < p < 1")
    return _bisect_ppf(lambda x: chi2_cdf(x, df), p, 1e-12, 1e6)


def f_cdf(x: float, df1: float, df2: float) -> float:
    """CDF of the F distribution."""
    if x <= 0:
        return 0.0
    return betainc(0.5 * df1, 0.5 * df2, df1 * x / (df1 * x + df2))


def f_sf(x: float, df1: float, df2: float) -> float:
    """Upper tail of the F distribution (the p-value for an F test).

    Computed from the complementary incomplete beta rather than as 1 - cdf,
    which underflows to exactly 0 for large F and would print a lack-of-fit
    p-value of 0 in a validation report.
    """
    if x <= 0:
        return 1.0
    return betainc(0.5 * df2, 0.5 * df1, df2 / (df1 * x + df2))


def z_ppf(p: float) -> float:
    """Standard normal quantile."""
    from statistics import NormalDist

    return NormalDist().inv_cdf(p)


# --------------------------------------------------------------------------
# Descriptive helpers
# --------------------------------------------------------------------------


def mean(values: Sequence[float]) -> float:
    if not values:
        raise InputError("mean of an empty sequence")
    return math.fsum(values) / len(values)


def sample_sd(values: Sequence[float]) -> float:
    n = len(values)
    if n < 2:
        return float("nan")
    m = mean(values)
    return math.sqrt(math.fsum((v - m) ** 2 for v in values) / (n - 1))


def rsd_percent(values: Sequence[float]) -> float:
    """Relative standard deviation (%CV). NaN when the mean is ~0."""
    m = mean(values)
    if abs(m) < 1e-15:
        return float("nan")
    return 100.0 * sample_sd(values) / abs(m)


def median(values: Sequence[float]) -> float:
    if not values:
        raise InputError("median of an empty sequence")
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else 0.5 * (s[mid - 1] + s[mid])


def sd_confidence_interval(sd: float, df: float, level: float = 0.90) -> tuple[float, float]:
    """Chi-square confidence interval for a standard deviation."""
    if df <= 0 or not math.isfinite(sd):
        return (float("nan"), float("nan"))
    alpha = 1.0 - level
    lo_chi = chi2_ppf(1.0 - alpha / 2.0, df)
    hi_chi = chi2_ppf(alpha / 2.0, df)
    return (sd * math.sqrt(df / lo_chi), sd * math.sqrt(df / hi_chi))


# --------------------------------------------------------------------------
# Regression
# --------------------------------------------------------------------------


@dataclass
class LinearFit:
    """Weighted least-squares straight-line fit and its diagnostics."""

    n: int
    slope: float
    intercept: float
    se_slope: float
    se_intercept: float
    residual_sd: float
    r_squared: float
    r: float
    df: int
    residuals: list[float] = field(default_factory=list)
    fitted: list[float] = field(default_factory=list)
    weights: list[float] = field(default_factory=list)

    def predict(self, x: float) -> float:
        return self.intercept + self.slope * x

    def slope_ci(self, level: float = 0.95) -> tuple[float, float]:
        t = t_ppf(0.5 + level / 2.0, self.df)
        return (self.slope - t * self.se_slope, self.slope + t * self.se_slope)

    def intercept_ci(self, level: float = 0.95) -> tuple[float, float]:
        t = t_ppf(0.5 + level / 2.0, self.df)
        return (self.intercept - t * self.se_intercept, self.intercept + t * self.se_intercept)


def fit_linear(
    xs: Sequence[float], ys: Sequence[float], weights: Sequence[float] | None = None
) -> LinearFit:
    """Fit y = a + b*x by (optionally weighted) least squares."""
    n = len(xs)
    if n != len(ys):
        raise InputError("x and y must be the same length")
    if n < 3:
        raise InputError("a regression needs at least 3 points")
    w = [1.0] * n if weights is None else [float(v) for v in weights]
    if len(w) != n:
        raise InputError("weights must match the number of points")
    if any(v < 0 for v in w):
        raise InputError("weights must be non-negative")

    sw = math.fsum(w)
    swx = math.fsum(wi * xi for wi, xi in zip(w, xs))
    swy = math.fsum(wi * yi for wi, yi in zip(w, ys))
    swxx = math.fsum(wi * xi * xi for wi, xi in zip(w, xs))
    swxy = math.fsum(wi * xi * yi for wi, xi, yi in zip(w, xs, ys))
    denom = sw * swxx - swx * swx
    if abs(denom) < 1e-300:
        raise InputError("x values are collinear or identical; slope is undefined")

    slope = (sw * swxy - swx * swy) / denom
    intercept = (swy - slope * swx) / sw
    fitted = [intercept + slope * xi for xi in xs]
    residuals = [yi - fi for yi, fi in zip(ys, fitted)]
    df = n - 2
    ss_res = math.fsum(wi * ri * ri for wi, ri in zip(w, residuals))
    residual_sd = math.sqrt(ss_res / df)
    se_slope = residual_sd * math.sqrt(sw / denom)
    se_intercept = residual_sd * math.sqrt(swxx / denom)

    ybar_w = swy / sw
    ss_tot = math.fsum(wi * (yi - ybar_w) ** 2 for wi, yi in zip(w, ys))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    r = math.copysign(math.sqrt(max(0.0, r_squared)), slope)

    return LinearFit(
        n=n,
        slope=slope,
        intercept=intercept,
        se_slope=se_slope,
        se_intercept=se_intercept,
        residual_sd=residual_sd,
        r_squared=r_squared,
        r=r,
        df=df,
        residuals=residuals,
        fitted=fitted,
        weights=w,
    )


def runs_test(residuals: Sequence[float]) -> dict[str, Any]:
    """Wald-Wolfowitz runs test on residual signs.

    ICH Q2(R2) 3.2.2.1 asks for the impact of any non-random pattern in the
    residual plot to be assessed. Curvature shows up as too few runs.
    """
    signs = [1 if r >= 0 else -1 for r in residuals if r != 0]
    n = len(signs)
    n_pos = sum(1 for s in signs if s > 0)
    n_neg = n - n_pos
    runs = 1 + sum(1 for i in range(1, n) if signs[i] != signs[i - 1]) if n else 0
    if n_pos < 1 or n_neg < 1 or n < 8:
        return {
            "runs": runs,
            "n_pos": n_pos,
            "n_neg": n_neg,
            "z": float("nan"),
            "p_value": float("nan"),
            "note": "too few points for a meaningful runs test (need n>=8 with both signs)",
        }
    exp = 2.0 * n_pos * n_neg / n + 1.0
    var = (2.0 * n_pos * n_neg * (2.0 * n_pos * n_neg - n)) / (n * n * (n - 1.0))
    if var <= 0:
        return {"runs": runs, "n_pos": n_pos, "n_neg": n_neg, "z": float("nan"),
                "p_value": float("nan"), "note": "degenerate variance"}
    z = (runs - exp) / math.sqrt(var)
    from statistics import NormalDist

    p = 2.0 * NormalDist().cdf(-abs(z))
    return {"runs": runs, "n_pos": n_pos, "n_neg": n_neg, "expected_runs": exp,
            "z": z, "p_value": p, "note": ""}


def lack_of_fit(xs: Sequence[float], ys: Sequence[float], fit: LinearFit) -> dict[str, Any]:
    """ANOVA lack-of-fit F test, which needs replicate y at some x levels.

    This is the statistically meaningful test of a linear calibration model.
    r-squared is not: it rises with range and is insensitive to curvature.
    """
    groups: dict[float, list[float]] = {}
    for x, y in zip(xs, ys):
        groups.setdefault(round(float(x), 12), []).append(float(y))
    k = len(groups)
    n = len(xs)
    replicated = sum(1 for vals in groups.values() if len(vals) > 1)
    df_pe = n - k
    df_lof = k - 2
    if df_pe < 1 or df_lof < 1:
        return {
            "applicable": False,
            "levels": k,
            "replicated_levels": replicated,
            "reason": "needs replicates at >=1 level and >=3 distinct levels",
        }
    ss_pe = math.fsum(
        math.fsum((v - mean(vals)) ** 2 for v in vals) for vals in groups.values()
    )
    ss_res = math.fsum(r * r for r in fit.residuals)
    ss_lof = max(0.0, ss_res - ss_pe)
    ms_pe = ss_pe / df_pe
    ms_lof = ss_lof / df_lof
    if ms_pe <= 0:
        return {"applicable": False, "levels": k, "replicated_levels": replicated,
                "reason": "zero pure-error variance; replicates are identical"}
    f_stat = ms_lof / ms_pe
    return {
        "applicable": True,
        "levels": k,
        "replicated_levels": replicated,
        "df_lack_of_fit": df_lof,
        "df_pure_error": df_pe,
        "ms_lack_of_fit": ms_lof,
        "ms_pure_error": ms_pe,
        "f_statistic": f_stat,
        "p_value": f_sf(f_stat, df_lof, df_pe),
    }


def heteroscedasticity(xs: Sequence[float], residuals: Sequence[float]) -> dict[str, Any]:
    """Compare residual spread in the lowest and highest thirds of the range.

    A large ratio means unweighted least squares over-weights the top of the
    curve, which biases back-calculated results at the bottom -- exactly where
    an impurity reporting threshold or an LLOQ lives.
    """
    pairs = sorted(zip(xs, residuals), key=lambda p: p[0])
    n = len(pairs)
    if n < 6:
        return {"applicable": False, "reason": "needs at least 6 points"}
    cut = max(2, n // 3)
    low = [r for _, r in pairs[:cut]]
    high = [r for _, r in pairs[-cut:]]
    var_low = math.fsum(r * r for r in low) / len(low)
    var_high = math.fsum(r * r for r in high) / len(high)
    if var_low <= 0:
        return {"applicable": False, "reason": "zero residual variance in the low third"}
    ratio = var_high / var_low
    return {
        "applicable": True,
        "n_low": len(low),
        "n_high": len(high),
        "variance_ratio_high_over_low": ratio,
        "sd_ratio": math.sqrt(ratio),
    }


# --------------------------------------------------------------------------
# Variance components (precision)
# --------------------------------------------------------------------------


@dataclass
class PrecisionComponents:
    """One-way random-effects decomposition of precision."""

    grand_mean: float
    n_total: int
    n_groups: int
    ms_between: float
    ms_within: float
    df_between: int
    df_within: int
    sd_repeatability: float
    sd_between: float
    sd_intermediate: float
    balanced: bool
    n_effective: float

    def rsd(self, sd: float) -> float:
        if abs(self.grand_mean) < 1e-15:
            return float("nan")
        return 100.0 * sd / abs(self.grand_mean)

    def satterthwaite_df(self) -> float:
        """Effective df for the total (intermediate) SD."""
        var_total = self.sd_intermediate ** 2
        if var_total <= 0:
            return float("nan")
        n = self.n_effective
        c1 = 1.0 / n
        c2 = (n - 1.0) / n
        num = var_total ** 2
        den = 0.0
        if self.df_between > 0:
            den += (c1 * self.ms_between) ** 2 / self.df_between
        if self.df_within > 0:
            den += (c2 * self.ms_within) ** 2 / self.df_within
        return num / den if den > 0 else float("nan")


def one_way_components(groups: dict[str, Sequence[float]]) -> PrecisionComponents:
    """Decompose precision into within-group and between-group components.

    Groups are the intermediate-precision factor -- day, analyst, instrument,
    or a combined run. Within-group scatter estimates repeatability; the total
    estimates intermediate precision.
    """
    clean = {k: [float(v) for v in vals] for k, vals in groups.items() if len(vals) >= 1}
    if len(clean) < 2:
        raise InputError("intermediate precision needs at least 2 groups")
    if all(len(v) < 2 for v in clean.values()):
        raise InputError("at least one group needs >=2 replicates to estimate repeatability")

    counts = [len(v) for v in clean.values()]
    n_total = sum(counts)
    k = len(clean)
    all_values = [v for vals in clean.values() for v in vals]
    grand = mean(all_values)

    ss_within = math.fsum(
        math.fsum((v - mean(vals)) ** 2 for v in vals) for vals in clean.values()
    )
    ss_between = math.fsum(len(vals) * (mean(vals) - grand) ** 2 for vals in clean.values())
    df_within = n_total - k
    df_between = k - 1
    ms_within = ss_within / df_within if df_within > 0 else float("nan")
    ms_between = ss_between / df_between if df_between > 0 else float("nan")

    balanced = len(set(counts)) == 1
    if balanced:
        n_eff = float(counts[0])
    else:
        # Standard unbalanced coefficient for the expected mean square.
        n_eff = (n_total - math.fsum(c * c for c in counts) / n_total) / (k - 1)

    var_within = max(0.0, ms_within) if math.isfinite(ms_within) else 0.0
    var_between = 0.0
    if math.isfinite(ms_between) and math.isfinite(ms_within) and n_eff > 0:
        var_between = max(0.0, (ms_between - ms_within) / n_eff)

    return PrecisionComponents(
        grand_mean=grand,
        n_total=n_total,
        n_groups=k,
        ms_between=ms_between,
        ms_within=ms_within,
        df_between=df_between,
        df_within=df_within,
        sd_repeatability=math.sqrt(var_within),
        sd_between=math.sqrt(var_between),
        sd_intermediate=math.sqrt(var_within + var_between),
        balanced=balanced,
        n_effective=n_eff,
    )


# --------------------------------------------------------------------------
# Method comparison
# --------------------------------------------------------------------------


def deming(
    xs: Sequence[float], ys: Sequence[float], lambda_ratio: float = 1.0
) -> dict[str, Any]:
    """Deming regression: errors in both variables.

    `lambda_ratio` is var(error in y) / var(error in x) -- the variance of the
    random error in the TEST (y) procedure over that in the COMPARATIVE (x) one.
    Check the direction against the limits, which are unambiguous: as
    lambda -> infinity the fit converges on the ordinary least-squares slope of
    y on x (x treated as error-free), and as lambda -> 0 it converges on the
    inverse regression (y treated as error-free). lambda = 1 means equal error
    variances and reduces to orthogonal regression.

    In practice lambda is estimated as (SD of x replicates / SD of y replicates)
    squared, so equal-precision procedures give 1.

    Ordinary least squares assumes x is error-free, which is false when
    comparing two measurement procedures, and biases the slope toward zero.
    """
    n = len(xs)
    if n != len(ys):
        raise InputError("x and y must be the same length")
    if n < 3:
        raise InputError("Deming regression needs at least 3 points")
    if lambda_ratio <= 0:
        raise InputError("lambda_ratio must be > 0")

    def _fit(xv: Sequence[float], yv: Sequence[float]) -> tuple[float, float]:
        xb, yb = mean(xv), mean(yv)
        sxx = math.fsum((x - xb) ** 2 for x in xv)
        syy = math.fsum((y - yb) ** 2 for y in yv)
        sxy = math.fsum((x - xb) * (y - yb) for x, y in zip(xv, yv))
        if abs(sxy) < 1e-300:
            raise InputError("zero covariance; Deming slope is undefined")
        term = syy - lambda_ratio * sxx
        slope = (term + math.sqrt(term * term + 4.0 * lambda_ratio * sxy * sxy)) / (
            2.0 * sxy
        )
        return slope, yb - slope * xb

    slope, intercept = _fit(xs, ys)

    # Jackknife standard errors.
    slopes, intercepts = [], []
    for i in range(n):
        xv = list(xs[:i]) + list(xs[i + 1 :])
        yv = list(ys[:i]) + list(ys[i + 1 :])
        try:
            s, a = _fit(xv, yv)
        except InputError:
            continue
        slopes.append(s)
        intercepts.append(a)
    if len(slopes) > 2:
        m = len(slopes)
        se_slope = math.sqrt((m - 1) / m * math.fsum((s - mean(slopes)) ** 2 for s in slopes))
        se_int = math.sqrt(
            (m - 1) / m * math.fsum((a - mean(intercepts)) ** 2 for a in intercepts)
        )
        df = m - 2
    else:
        se_slope = se_int = float("nan")
        df = 1

    t = t_ppf(0.975, df) if df > 0 else float("nan")
    return {
        "n": n,
        "lambda_ratio": lambda_ratio,
        "slope": slope,
        "intercept": intercept,
        "se_slope": se_slope,
        "se_intercept": se_int,
        "slope_ci95": (slope - t * se_slope, slope + t * se_slope),
        "intercept_ci95": (intercept - t * se_int, intercept + t * se_int),
        "df": df,
    }


def passing_bablok(xs: Sequence[float], ys: Sequence[float]) -> dict[str, Any]:
    """Passing-Bablok regression: non-parametric, no distributional assumption.

    Robust to outliers and does not assume a known error-variance ratio, which
    is why CLSI EP09-style method comparison work often prefers it.
    """
    n = len(xs)
    if n != len(ys):
        raise InputError("x and y must be the same length")
    if n < 5:
        raise InputError("Passing-Bablok needs at least 5 points")

    slopes: list[float] = []
    for i in range(n):
        for j in range(i + 1, n):
            dx = xs[j] - xs[i]
            dy = ys[j] - ys[i]
            if dx == 0 and dy == 0:
                continue
            if dx == 0:
                continue  # vertical pair carries no finite slope
            slopes.append(dy / dx)
    if not slopes:
        raise InputError("no usable pairwise slopes")

    slopes.sort()
    n_slopes = len(slopes)
    shift = sum(1 for s in slopes if s < -1.0)

    def _shifted_median(offset: int) -> float:
        idx = n_slopes // 2 + offset
        if n_slopes % 2:
            return slopes[min(max(idx, 0), n_slopes - 1)]
        lo = slopes[min(max(idx - 1, 0), n_slopes - 1)]
        hi = slopes[min(max(idx, 0), n_slopes - 1)]
        return 0.5 * (lo + hi)

    slope = _shifted_median(shift)
    intercept = median([y - slope * x for x, y in zip(xs, ys)])

    # Rank-based 95% CI on the slope. M1 and M2 are 1-based order statistics of
    # the shifted slope list, so both convert to 0-based with the same -1.
    c = z_ppf(0.975) * math.sqrt(n * (n - 1.0) * (2.0 * n + 5.0) / 18.0)
    m1 = int(round((n_slopes - c) / 2.0))
    m2 = n_slopes - m1 + 1
    lo_idx = min(max(m1 + shift - 1, 0), n_slopes - 1)
    hi_idx = min(max(m2 + shift - 1, 0), n_slopes - 1)
    slope_lo, slope_hi = slopes[lo_idx], slopes[hi_idx]
    int_lo = median([y - slope_hi * x for x, y in zip(xs, ys)])
    int_hi = median([y - slope_lo * x for x, y in zip(xs, ys)])

    return {
        "n": n,
        "n_slopes": n_slopes,
        "slope": slope,
        "intercept": intercept,
        "slope_ci95": (slope_lo, slope_hi),
        "intercept_ci95": (int_lo, int_hi),
    }


def bland_altman(
    xs: Sequence[float], ys: Sequence[float], relative: bool = False
) -> dict[str, Any]:
    """Bias and limits of agreement between paired measurements."""
    n = len(xs)
    if n != len(ys):
        raise InputError("x and y must be the same length")
    if n < 3:
        raise InputError("Bland-Altman needs at least 3 pairs")
    means = [0.5 * (x + y) for x, y in zip(xs, ys)]
    if relative:
        diffs = []
        for x, y, m in zip(xs, ys, means):
            if abs(m) < 1e-15:
                raise InputError("relative differences need non-zero pair means")
            diffs.append(100.0 * (y - x) / m)
    else:
        diffs = [y - x for x, y in zip(xs, ys)]

    bias = mean(diffs)
    sd = sample_sd(diffs)
    t = t_ppf(0.975, n - 1)
    se_bias = sd / math.sqrt(n)
    loa_lo, loa_hi = bias - 1.96 * sd, bias + 1.96 * sd
    se_loa = sd * math.sqrt(1.0 / n + (1.96 ** 2) / (2.0 * (n - 1)))

    # Proportional-bias check: does the difference trend with the mean?
    trend = None
    try:
        tf = fit_linear(means, diffs)
        t_stat = tf.slope / tf.se_slope if tf.se_slope > 0 else float("nan")
        trend = {
            "slope": tf.slope,
            "p_value": 2.0 * (1.0 - t_cdf(abs(t_stat), tf.df)) if math.isfinite(t_stat) else float("nan"),
        }
    except InputError:
        trend = None

    return {
        "n": n,
        "relative": relative,
        "bias": bias,
        "sd_differences": sd,
        "bias_ci95": (bias - t * se_bias, bias + t * se_bias),
        "loa_lower": loa_lo,
        "loa_upper": loa_hi,
        "loa_ci95_halfwidth": t * se_loa,
        "proportional_bias": trend,
    }


def tost_paired(
    diffs: Sequence[float], margin: float, alpha: float = 0.05
) -> dict[str, Any]:
    """Two one-sided tests for equivalence on paired differences.

    Absence of a significant difference is not evidence of equivalence. TOST
    tests the hypothesis that actually matters at a method transfer: that the
    true difference lies inside +/- margin.
    """
    n = len(diffs)
    if n < 2:
        raise InputError("TOST needs at least 2 differences")
    if margin <= 0:
        raise InputError("margin must be > 0")
    d = mean(diffs)
    sd = sample_sd(diffs)
    se = sd / math.sqrt(n)
    df = n - 1
    if se <= 0:
        raise InputError("zero variability; TOST is undefined")
    t_lower = (d + margin) / se
    t_upper = (d - margin) / se
    p_lower = 1.0 - t_cdf(t_lower, df)
    p_upper = t_cdf(t_upper, df)
    p = max(p_lower, p_upper)
    t_crit = t_ppf(1.0 - alpha, df)
    ci = (d - t_crit * se, d + t_crit * se)
    return {
        "n": n,
        "mean_difference": d,
        "sd_difference": sd,
        "margin": margin,
        "alpha": alpha,
        "p_lower": p_lower,
        "p_upper": p_upper,
        "p_value": p,
        "ci_1_minus_2alpha": ci,
        "equivalent": bool(ci[0] > -margin and ci[1] < margin),
    }


# --------------------------------------------------------------------------
# I/O
# --------------------------------------------------------------------------


def read_input(path: str | None) -> str:
    """Read a bounded amount of text from a path or stdin."""
    if path in (None, "-"):
        # Reading a terminal would block forever with no indication why, so an
        # omitted --input becomes an error rather than an apparent hang.
        if path is None and sys.stdin.isatty():
            raise InputError("no input given; pass --input FILE, or '-' to read stdin")
        data = sys.stdin.read(MAX_INPUT_BYTES + 1)
    else:
        p = Path(path)
        if not p.is_file():
            raise InputError(f"not a file: {path}")
        if p.stat().st_size > MAX_INPUT_BYTES:
            raise InputError(f"input larger than {MAX_INPUT_BYTES} bytes")
        data = p.read_text(encoding="utf-8", errors="replace")
    if len(data) > MAX_INPUT_BYTES:
        raise InputError(f"input larger than {MAX_INPUT_BYTES} bytes")
    return data


def parse_rows(text: str, path_hint: str | None = None) -> list[dict[str, str]]:
    """Parse CSV, TSV, or a JSON array of objects into a list of dicts."""
    stripped = text.lstrip()
    if stripped.startswith("[") or stripped.startswith("{"):
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise InputError(f"invalid JSON: {exc}") from exc
        if isinstance(payload, dict):
            payload = payload.get("rows", payload.get("data"))
        if not isinstance(payload, list):
            raise InputError("JSON input must be an array of objects, or {\"rows\": [...]}")
        # Refuse rather than truncate: silently dropping validation data would
        # produce a clean-looking result computed on part of the study.
        if len(payload) > MAX_ROWS:
            raise InputError(f"more than {MAX_ROWS} rows")
        rows = []
        for item in payload:
            if not isinstance(item, dict):
                raise InputError("JSON rows must be objects")
            # Match CSV/TSV whitespace handling while retaining null as empty.
            rows.append({
                str(k).strip(): "" if v is None else str(v).strip()
                for k, v in item.items()
            })
        if not rows:
            raise InputError("no data rows found")
        return rows

    delimiter = "\t" if (path_hint or "").endswith((".tsv", ".tab")) else None
    if delimiter is None:
        first = text.splitlines()[0] if text.splitlines() else ""
        delimiter = "\t" if first.count("\t") > first.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    rows = []
    for i, row in enumerate(reader):
        if i >= MAX_ROWS:
            raise InputError(f"more than {MAX_ROWS} rows")
        # DictReader stores surplus fields as a list under its None restkey.
        if None in row:
            raise InputError(
                f"row {i + 1}: more fields than the header ({len(row[None])} extra)"
            )
        rows.append({(k or "").strip(): (v or "").strip() for k, v in row.items()})
    if not rows:
        raise InputError("no data rows found")
    return rows


def require_columns(rows: list[dict[str, str]], columns: Iterable[str]) -> None:
    present = set(rows[0].keys())
    missing = [c for c in columns if c not in present]
    if missing:
        raise InputError(
            f"missing required column(s): {', '.join(missing)}; found: {', '.join(sorted(present))}"
        )


def to_float(value: str, column: str, row_index: int) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise InputError(
            f"row {row_index + 1}: column '{column}' is not numeric: {value!r}"
        ) from exc


def fmt(value: Any, digits: int = 4) -> str:
    """Format a number for a table cell."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        if math.isnan(value):
            return "n/a"
        if math.isinf(value):
            return "inf"
        if value != 0 and (abs(value) < 1e-4 or abs(value) >= 1e6):
            return f"{value:.{digits}e}"
        return f"{value:.{digits}f}"
    return str(value)


def emit_table(rows: list[dict[str, Any]], stream=None) -> None:
    """Print aligned columns."""
    stream = stream or sys.stdout
    if not rows:
        print("(no rows)", file=stream)
        return
    headers = list(rows[0].keys())
    cells = [[fmt(r.get(h)) for h in headers] for r in rows]
    widths = [
        max(len(h), *(len(c[i]) for c in cells)) if cells else len(h)
        for i, h in enumerate(headers)
    ]
    print("  ".join(h.ljust(w) for h, w in zip(headers, widths)).rstrip(), file=stream)
    for c in cells:
        print("  ".join(v.ljust(w) for v, w in zip(c, widths)).rstrip(), file=stream)


def emit(rows: list[dict[str, Any]], fmt_name: str, stream=None) -> None:
    """Print rows as a table, TSV, or JSON."""
    stream = stream or sys.stdout
    if fmt_name == "json":
        json.dump(rows, stream, indent=2, default=_json_default)
        print(file=stream)
    elif fmt_name == "tsv":
        if not rows:
            return
        headers = list(rows[0].keys())
        print("\t".join(headers), file=stream)
        for r in rows:
            print("\t".join(fmt(r.get(h)) for h in headers), file=stream)
    else:
        emit_table(rows, stream=stream)


def _json_default(obj: Any) -> Any:
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, tuple):
        return list(obj)
    raise TypeError(f"not JSON serialisable: {type(obj)!r}")


def note(message: str) -> None:
    """Write provenance and caveats to stderr so stdout stays parseable."""
    print(f"note: {message}", file=sys.stderr)


def finding(message: str) -> None:
    print(f"finding: {message}", file=sys.stderr)


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        choices=("table", "tsv", "json"),
        default="table",
        help="output format (default: table)",
    )


def run_cli(main_func) -> None:
    """Wrap a main() so InputError becomes a clean exit code 2."""
    try:
        sys.exit(main_func())
    except InputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(EXIT_INPUT_ERROR)
    except BrokenPipeError:
        sys.exit(EXIT_OK)
