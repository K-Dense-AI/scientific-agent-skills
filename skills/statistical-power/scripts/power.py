"""Unified closed-form power / sample-size interface over statsmodels and scipy.

One function each for the three things people actually want:
  - sample_size(...)  : solve for n given effect size, alpha, power
  - power(...)        : solve for achieved power given n and effect size
  - mde(...)          : solve for the minimum detectable effect given n and power
  - power_curve(...)  : plot power vs. n (or vs. effect size) for planning figures

Every call routes to the right statsmodels solver based on `test=`, so callers
don't need to remember which Power class belongs to which test. All four solver
quantities (effect_size, nobs, alpha, power) obey the identity "fix three, solve
the fourth"; these helpers just expose that cleanly.

Supported tests:
  t_ind          two independent means (Cohen's d)
  t_paired/t_one paired or one-sample mean (Cohen's d)
  anova          one-way ANOVA, k groups (Cohen's f)
  two_proportions  two independent proportions (give prop1, prop2; uses Cohen's h)
  one_proportion   one proportion vs. a reference (give prop1, prop0)
  correlation    Pearson r (give effect_size=r)
  chi2           goodness-of-fit / contingency (Cohen's w; give dof)
  linear_regression  added predictors via Cohen's f^2 (give f2 as effect_size, df_num)

Requires: statsmodels>=0.14.6, scipy>=1.11, numpy, matplotlib.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from statsmodels.stats.power import (
    FTestAnovaPower,
    GofChisquarePower,
    NormalIndPower,
    TTestIndPower,
    TTestPower,
)
from statsmodels.stats.proportion import proportion_effectsize


# --------------------------------------------------------------------------- #
# internal: build the statsmodels solver and the kwargs for the given test
# --------------------------------------------------------------------------- #
def _resolve(test, effect_size, alpha, alternative, **kw):
    """Return (solver, base_kwargs, n_key) for a test.

    n_key is the keyword the solver uses for "number of observations" so the
    sample_size/power/mde wrappers can fill in the right argument generically.
    """
    test = test.lower()

    if test == "t_ind":
        solver = TTestIndPower()
        es = effect_size
        base = dict(effect_size=es, alpha=alpha, alternative=alternative,
                    ratio=kw.get("ratio", 1.0))
        return solver, base, "nobs1"

    if test in ("t_paired", "t_one"):
        solver = TTestPower()
        base = dict(effect_size=effect_size, alpha=alpha, alternative=alternative)
        return solver, base, "nobs"

    if test == "anova":
        solver = FTestAnovaPower()
        k = kw.get("k_groups")
        if k is None:
            raise ValueError("anova requires k_groups=")
        base = dict(effect_size=effect_size, alpha=alpha, k_groups=k)
        return solver, base, "nobs"  # nobs = TOTAL n across all groups

    if test == "two_proportions":
        # convert proportions to Cohen's h, then use the normal approximation
        p1, p2 = kw.get("prop1"), kw.get("prop2")
        if p1 is None or p2 is None:
            raise ValueError("two_proportions requires prop1= and prop2=")
        h = proportion_effectsize(p1, p2)
        solver = NormalIndPower()
        base = dict(effect_size=h, alpha=alpha, alternative=alternative,
                    ratio=kw.get("ratio", 1.0))
        return solver, base, "nobs1"

    if test == "one_proportion":
        p1, p0 = kw.get("prop1"), kw.get("prop0")
        if p1 is None or p0 is None:
            raise ValueError("one_proportion requires prop1= and prop0=")
        h = proportion_effectsize(p1, p0)
        # one-sample: NormalIndPower with an effectively infinite second group
        solver = NormalIndPower()
        base = dict(effect_size=h, alpha=alpha, alternative=alternative, ratio=0.0)
        return solver, base, "nobs1"

    if test == "correlation":
        # Power for Pearson r via Fisher z; handled analytically below, but we
        # still route through a solver-shaped object for a uniform interface.
        return "correlation", dict(effect_size=effect_size, alpha=alpha,
                                   alternative=alternative), "nobs"

    if test == "chi2":
        solver = GofChisquarePower()
        dof = kw.get("dof")
        if dof is None:
            raise ValueError("chi2 requires dof= (n_bins-1, or (r-1)(c-1))")
        base = dict(effect_size=effect_size, alpha=alpha, n_bins=dof + 1)
        return solver, base, "nobs"

    if test == "linear_regression":
        # Handled by a dedicated noncentral-F solver (statsmodels' FTestPower is
        # unreliable when solving for sample size). See _reg_* helpers below.
        df_num = kw.get("df_num")
        if df_num is None:
            raise ValueError("linear_regression requires df_num= (number of tested predictors)")
        return "regression", dict(effect_size=effect_size, alpha=alpha,
                                  df_num=df_num,
                                  k_total=kw.get("k_total", df_num)), "nobs"

    raise ValueError(f"unknown test '{test}'")


# --------------------------------------------------------------------------- #
# correlation power (Fisher z transform) -- closed form, no statsmodels solver
# --------------------------------------------------------------------------- #
def _corr_power(r, n, alpha, alternative):
    from scipy import stats
    z = math.atanh(r)
    se = 1.0 / math.sqrt(n - 3)
    if alternative == "two-sided":
        zc = stats.norm.ppf(1 - alpha / 2)
    else:
        zc = stats.norm.ppf(1 - alpha)
    return float(stats.norm.cdf(z / se - zc) + stats.norm.cdf(-z / se - zc))


def _corr_sample_size(r, alpha, power, alternative):
    from scipy import stats
    z = abs(math.atanh(r))
    if alternative == "two-sided":
        zc = stats.norm.ppf(1 - alpha / 2)
    else:
        zc = stats.norm.ppf(1 - alpha)
    zp = stats.norm.ppf(power)
    return ((zc + zp) / z) ** 2 + 3


# --------------------------------------------------------------------------- #
# multiple-regression power via the noncentral F (Cohen's f^2)
# --------------------------------------------------------------------------- #
def _reg_power(f2, n, df_num, k_total, alpha):
    """Power of the F-test for df_num tested predictors in a model with k_total
    total predictors, total sample size n. Noncentrality lambda = f^2 * n."""
    from scipy import stats
    df_denom = n - k_total - 1
    if df_denom < 1:
        return 0.0
    ncp = f2 * n
    crit = stats.f.ppf(1 - alpha, df_num, df_denom)
    return float(1 - stats.ncf.cdf(crit, df_num, df_denom, ncp))


def _reg_sample_size(f2, df_num, k_total, alpha, power):
    n = k_total + 2  # smallest n with df_denom >= 1
    while _reg_power(f2, n, df_num, k_total, alpha) < power:
        n += 1
        if n > 1_000_000:
            raise RuntimeError("sample size did not converge below 1e6")
    return n


def _reg_mde(n, df_num, k_total, alpha, power):
    """Smallest detectable f^2 at fixed n (bisection)."""
    lo, hi = 1e-6, 100.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if _reg_power(mid, n, df_num, k_total, alpha) < power:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# --------------------------------------------------------------------------- #
# public API
# --------------------------------------------------------------------------- #
def sample_size(test, effect_size=None, alpha=0.05, power=0.80,
                alternative="two-sided", round_up=True, **kw):
    """Solve for required sample size.

    For per-group tests (t_ind, two_proportions) returns n PER GROUP.
    For anova returns TOTAL n across all groups. For chi2/regression returns total n.
    """
    solver, base, n_key = _resolve(test, effect_size, alpha, alternative, **kw)

    if solver == "correlation":
        n = _corr_sample_size(effect_size, alpha, power, alternative)
        return math.ceil(n) if round_up else n

    if solver == "regression":
        return _reg_sample_size(base["effect_size"], base["df_num"],
                                base["k_total"], alpha, power)

    base["power"] = power
    base[n_key] = None
    n = solver.solve_power(**base)
    if round_up:
        n = math.ceil(n)
    return n


def power(test, effect_size=None, nobs1=None, nobs=None, alpha=0.05,
          alternative="two-sided", **kw):
    """Solve for achieved power given the sample size.

    Pass nobs1 for per-group tests (t_ind, two_proportions), nobs for total-n tests.
    """
    solver, base, n_key = _resolve(test, effect_size, alpha, alternative, **kw)

    n = nobs1 if nobs1 is not None else nobs
    if n is None:
        raise ValueError("provide nobs1= (per-group tests) or nobs= (total-n tests)")

    if solver == "correlation":
        return _corr_power(effect_size, n, alpha, alternative)

    if solver == "regression":
        return _reg_power(base["effect_size"], n, base["df_num"],
                          base["k_total"], alpha)

    base[n_key] = n
    return float(solver.solve_power(**base))


def mde(test, nobs1=None, nobs=None, alpha=0.05, power=0.80,
        alternative="two-sided", **kw):
    """Solve for the minimum detectable effect (standardized) at a fixed n.

    Returns the effect size in the test's native units (d, f, h, w, r, ...).
    """
    solver, base, n_key = _resolve(test, None, alpha, alternative, **kw)

    n = nobs1 if nobs1 is not None else nobs
    if n is None:
        raise ValueError("provide nobs1= or nobs=")

    if solver == "correlation":
        # invert the Fisher-z sample-size formula
        from scipy import stats
        zc = stats.norm.ppf(1 - alpha / 2) if alternative == "two-sided" \
            else stats.norm.ppf(1 - alpha)
        zp = stats.norm.ppf(power)
        z = (zc + zp) / math.sqrt(n - 3)
        return float(math.tanh(z))

    if solver == "regression":
        return _reg_mde(n, base["df_num"], base["k_total"], alpha, power)

    base["power"] = power
    base["effect_size"] = None
    base[n_key] = n
    return float(solver.solve_power(**base))


def power_curve(test, effect_size=None, n_range=None, alpha=0.05, power_target=0.80,
                alternative="two-sided", save=None, show=False, **kw):
    """Plot power vs. sample size. Returns (n_array, power_array).

    n_range iterates the per-group n for per-group tests, total n otherwise.
    """
    import matplotlib.pyplot as plt

    if n_range is None:
        n_range = range(5, 205, 5)
    ns = np.array(list(n_range), dtype=float)

    pwr = []
    for n in ns:
        if test in ("t_ind", "two_proportions"):
            pwr.append(power(test, effect_size=effect_size, nobs1=n, alpha=alpha,
                             alternative=alternative, **kw))
        else:
            pwr.append(power(test, effect_size=effect_size, nobs=n, alpha=alpha,
                             alternative=alternative, **kw))
    pwr = np.array(pwr)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(ns, pwr, lw=2)
    ax.axhline(power_target, ls="--", color="crimson", lw=1,
               label=f"target power = {power_target:g}")
    ax.set_xlabel("Sample size" + (" per group" if test in ("t_ind", "two_proportions") else " (total)"))
    ax.set_ylabel("Power (1 - β)")
    ax.set_ylim(0, 1.02)
    es_label = effect_size if effect_size is not None else ""
    ax.set_title(f"Power curve: {test} (effect = {es_label}, α = {alpha:g})")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()

    if save:
        fig.savefig(save, dpi=150)
    if show:
        plt.show()
    plt.close(fig)
    return ns, pwr


if __name__ == "__main__":
    # quick smoke test of the main paths
    print("t_ind  d=0.5, 80% power -> n/group =",
          sample_size("t_ind", effect_size=0.5, power=0.80))
    print("anova  f=0.25, k=4, 80% -> total n =",
          sample_size("anova", effect_size=0.25, k_groups=4, power=0.80))
    print("2 props 0.40 vs 0.55, 80% -> n/group =",
          sample_size("two_proportions", prop1=0.40, prop2=0.55, power=0.80))
    print("correlation r=0.30, 80% -> n =",
          sample_size("correlation", effect_size=0.30, power=0.80))
    print("MDE for t_ind at n=30/group, 80% power -> d =",
          round(mde("t_ind", nobs1=30, power=0.80), 3))
    print("power for t_ind d=0.5 at n=64/group ->",
          round(power("t_ind", effect_size=0.5, nobs1=64), 3))
