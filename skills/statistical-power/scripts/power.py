"""Unified closed-form power / sample-size interface over statsmodels and scipy.

One function each for the three things people actually want:
  - sample_size(...)  : solve for n given effect size, alpha, power
  - power(...)        : solve for achieved power given n and effect size
  - mde(...)          : solve for the minimum detectable effect given n and power
  - power_curve(...)  : plot power vs. n for planning figures

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

Tested with statsmodels 0.15.0, scipy 1.18.1, numpy 2.5.3, matplotlib 3.11.2.
"""

from __future__ import annotations

import math
from numbers import Integral, Real
import warnings

import numpy as np
from statsmodels.stats.power import (
    FTestAnovaPower,
    GofChisquarePower,
    NormalIndPower,
    TTestIndPower,
    TTestPower,
)
from statsmodels.stats.proportion import proportion_effectsize
from statsmodels.tools.sm_exceptions import ConvergenceWarning


def _finite(value, name):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def _positive_integer(value, name, minimum=1):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return int(value)


def _target(alpha, target):
    if not alpha < _finite(target, "power") < 1:
        raise ValueError("target power must be strictly between alpha and 1")


def _sample_n(test, nobs1, nobs, base):
    if nobs1 is not None and nobs is not None:
        raise ValueError("provide only one of nobs1= or nobs=")
    n = nobs1 if nobs1 is not None else nobs
    if n is None:
        raise ValueError("provide nobs1= (sample 1) or nobs= (total observations/pairs)")
    n = _finite(n, "sample size")
    minimum = 0
    if test in ("t_one", "t_paired"):
        minimum = 1
    elif test == "t_ind":
        minimum = max(1, 1 / base["ratio"])
    elif test == "correlation":
        minimum = 3
    elif test == "anova":
        minimum = base["k_groups"]
    elif test == "linear_regression":
        minimum = base["k_total"] + 1
    if n <= minimum:
        raise ValueError(f"sample size for {test} must be > {minimum:g}")
    return n


# --------------------------------------------------------------------------- #
# internal: build the statsmodels solver and the kwargs for the given test
# --------------------------------------------------------------------------- #
def _resolve(test, effect_size, alpha, alternative, *, solving_effect=False, **kw):
    """Return (solver, base_kwargs, n_key) for a test.

    n_key is the keyword the solver uses for "number of observations" so the
    sample_size/power/mde wrappers can fill in the right argument generically.
    """
    test = test.lower()
    allowed = {
        "t_ind": {"ratio"}, "t_one": set(), "t_paired": set(),
        "anova": {"k_groups"}, "two_proportions": {"prop1", "prop2", "ratio"},
        "one_proportion": {"prop1", "prop0"}, "correlation": set(),
        "chi2": {"dof"}, "linear_regression": {"df_num", "k_total"},
    }
    if test not in allowed:
        raise ValueError(f"unknown test '{test}'")
    if set(kw) - allowed[test]:
        raise ValueError(f"unexpected arguments for {test}: {sorted(set(kw) - allowed[test])}")
    if not 0 < _finite(alpha, "alpha") < 1:
        raise ValueError("alpha must lie strictly between 0 and 1")
    if alternative not in ("two-sided", "larger", "smaller"):
        raise ValueError("alternative must be 'two-sided', 'larger', or 'smaller'")
    if test in ("anova", "chi2", "linear_regression") and alternative != "two-sided":
        raise ValueError(f"{test} is an omnibus upper-tail test; omit alternative")
    if "ratio" in kw and _finite(kw["ratio"], "ratio") <= 0:
        raise ValueError("ratio must be positive for a two-sample test")
    if effect_size is not None:
        effect_size = _finite(effect_size, "effect_size")
        if test in ("anova", "chi2", "linear_regression") and effect_size < 0:
            raise ValueError("f, w, and f-squared effect sizes cannot be negative")
        if test == "correlation" and not -1 < effect_size < 1:
            raise ValueError("correlation must lie strictly between -1 and 1")
        if test in ("one_proportion", "two_proportions") and abs(effect_size) > math.pi:
            raise ValueError("Cohen's h must lie between -pi and pi")
    elif not solving_effect and test not in ("one_proportion", "two_proportions"):
        raise ValueError("provide effect_size=")

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
        k = _positive_integer(k, "k_groups", 2)
        base = dict(effect_size=effect_size, alpha=alpha, k_groups=k)
        return solver, base, "nobs"  # nobs = TOTAL n across all groups

    if test in ("two_proportions", "one_proportion"):
        # convert proportions to Cohen's h, then use the normal approximation
        reference = "prop2" if test == "two_proportions" else "prop0"
        p1, p2 = kw.get("prop1"), kw.get(reference)
        if solving_effect:
            if p1 is not None or p2 is not None:
                raise ValueError("MDE returns Cohen's h; omit proportions, then check baseline feasibility")
            h = None
        elif effect_size is not None:
            if p1 is not None or p2 is not None:
                raise ValueError("provide Cohen's h or proportions, not both")
            h = effect_size
        else:
            if p1 is None or p2 is None:
                raise ValueError(f"{test} requires prop1= and {reference}= (or effect_size=h)")
            if not all(0 <= _finite(p, "proportion") <= 1 for p in (p1, p2)):
                raise ValueError("proportions must lie in [0, 1]")
            h = float(proportion_effectsize(p1, p2))
        solver = NormalIndPower()
        base = dict(effect_size=h, alpha=alpha, alternative=alternative,
                    ratio=kw.get("ratio", 1.0) if test == "two_proportions" else 0.0)
        # ratio=0 is statsmodels' explicit single-sample branch.
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
        dof = _positive_integer(dof, "dof")
        base = dict(effect_size=effect_size, alpha=alpha, n_bins=dof + 1)
        return solver, base, "nobs"

    if test == "linear_regression":
        # Explicit total n keeps nuisance predictors in the residual df and
        # in the assumed noncentrality f^2 * n. See _reg_* helpers below.
        df_num = kw.get("df_num")
        if df_num is None:
            raise ValueError("linear_regression requires df_num= (number of tested predictors)")
        df_num = _positive_integer(df_num, "df_num")
        k_total = _positive_integer(kw.get("k_total", df_num), "k_total")
        if df_num > k_total:
            raise ValueError("df_num must not exceed k_total (excluding intercept)")
        return "regression", dict(effect_size=effect_size, alpha=alpha,
                                  df_num=df_num, k_total=k_total), "nobs"

    raise ValueError(f"unknown test '{test}'")


# --------------------------------------------------------------------------- #
# correlation power (Fisher z transform) -- normal approximation
# --------------------------------------------------------------------------- #
def _corr_power(r, n, alpha, alternative):
    from scipy import stats
    z = math.atanh(r)
    se = 1.0 / math.sqrt(n - 3)
    if alternative == "two-sided":
        zc = stats.norm.ppf(1 - alpha / 2)
        return float(stats.norm.cdf(z / se - zc) + stats.norm.cdf(-z / se - zc))
    else:
        zc = stats.norm.ppf(1 - alpha)
        direction = 1 if alternative == "larger" else -1
        return float(stats.norm.cdf(direction * z / se - zc))


def _corr_sample_size(r, alpha, power, alternative):
    # Invert the same Fisher-z approximation as power(), including both tails.
    # Solve for n-3, then shift; NormalIndPower(ddof=3)'s default n search
    # starts outside its domain and can return a spurious n near 3.
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        n = float(3 + NormalIndPower().solve_power(
            effect_size=math.atanh(r), alpha=alpha, power=power,
            ratio=0, alternative=alternative))
    if (not math.isfinite(n) or n <= 3 or
            not math.isclose(_corr_power(r, n, alpha, alternative), power, abs_tol=1e-5)):
        raise RuntimeError("correlation sample-size solution failed the power round-trip check")
    return n


# --------------------------------------------------------------------------- #
# multiple-regression power via the noncentral F (Cohen's f^2)
# --------------------------------------------------------------------------- #
def _reg_power(f2, n, df_num, k_total, alpha):
    """Power of the F-test for df_num tested predictors in a model with k_total
    total predictors, total sample size n. Noncentrality lambda = f^2 * n."""
    from scipy import stats
    df_denom = n - k_total - 1
    if df_denom <= 0:
        raise ValueError("regression requires positive residual degrees of freedom")
    ncp = f2 * n
    crit = stats.f.ppf(1 - alpha, df_num, df_denom)
    # SciPy 1.18.1 ncf.sf(..., nc=0) returns a negative result; use central F.
    if ncp == 0:
        return float(stats.f.sf(crit, df_num, df_denom))
    result = float(1 - stats.ncf.cdf(crit, df_num, df_denom, ncp))
    if not math.isfinite(result) or not 0 <= result <= 1:
        raise RuntimeError("regression power calculation returned a nonfinite or out-of-range value")
    return result


def _reg_sample_size(f2, df_num, k_total, alpha, power):
    lo, hi = k_total + 2, 1_000_000
    if lo > hi or _reg_power(f2, hi, df_num, k_total, alpha) < power:
        raise RuntimeError("sample size did not converge below 1e6")
    while lo < hi:
        mid = (lo + hi) // 2
        if _reg_power(f2, mid, df_num, k_total, alpha) >= power:
            hi = mid
        else:
            lo = mid + 1
    return lo


def _reg_mde(n, df_num, k_total, alpha, power):
    """Smallest detectable f^2 at fixed n, with a checked upper bracket."""
    from scipy.optimize import brentq
    hi = 1.0
    while _reg_power(hi, n, df_num, k_total, alpha) < power:
        hi *= 2
        if hi > 1e6:
            raise RuntimeError("MDE did not converge below f-squared=1e6")
    return brentq(lambda f2: _reg_power(f2, n, df_num, k_total, alpha) - power, 0, hi)


# --------------------------------------------------------------------------- #
# public API
# --------------------------------------------------------------------------- #
def sample_size(test, effect_size=None, alpha=0.05, power=0.80,
                alternative="two-sided", round_up=True, **kw):
    """Solve for required sample size.

    For two-sample tests returns n1; n2 = ratio * n1 before integer allocation.
    ANOVA returns balanced TOTAL n (rounded to a multiple of k_groups).
    For paired tests n counts pairs; for other tests n counts observations.
    Regression always searches integer n, even when round_up=False.
    """
    solver, base, n_key = _resolve(test, effect_size, alpha, alternative, **kw)
    _target(alpha, power)
    es = base["effect_size"]
    if es == 0 or (alternative == "larger" and es < 0) or (alternative == "smaller" and es > 0):
        raise ValueError("a nonzero effect in the tested direction is required for target power > alpha")

    if solver == "correlation":
        n = _corr_sample_size(effect_size, alpha, power, alternative)
        return math.ceil(n) if round_up else n

    if solver == "regression":
        return _reg_sample_size(base["effect_size"], base["df_num"],
                                base["k_total"], alpha, power)

    base["power"] = power
    base[n_key] = None
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        n = float(solver.solve_power(**base))
    if not math.isfinite(n) or n <= 0:
        raise RuntimeError("sample-size solver did not return a finite positive value")
    _sample_n(test.lower(), n, None, base)
    check = dict(base, **{n_key: n})
    check.pop("power")
    if not math.isclose(float(solver.power(**check)), power, abs_tol=1e-5):
        raise RuntimeError("sample-size solution failed the power round-trip check")
    if round_up:
        multiple = base["k_groups"] if test.lower() == "anova" else 1
        n = multiple * math.ceil(n / multiple)
    return n


def power(test, effect_size=None, nobs1=None, nobs=None, alpha=0.05,
          alternative="two-sided", **kw):
    """Solve for achieved power given the sample size.

    Pass nobs1 for per-group tests (t_ind, two_proportions), nobs for total-n tests.
    """
    solver, base, n_key = _resolve(test, effect_size, alpha, alternative, **kw)

    n = _sample_n(test.lower(), nobs1, nobs, base)

    if solver == "correlation":
        return _corr_power(effect_size, n, alpha, alternative)

    if solver == "regression":
        return _reg_power(base["effect_size"], n, base["df_num"],
                          base["k_total"], alpha)

    base[n_key] = n
    result = float(solver.power(**base))
    if not math.isfinite(result) or not 0 <= result <= 1:
        raise RuntimeError("power calculation returned a nonfinite or out-of-range value")
    return result


def mde(test, nobs1=None, nobs=None, alpha=0.05, power=0.80,
        alternative="two-sided", **kw):
    """Solve for the minimum detectable effect (standardized) at a fixed n.

    Returns the effect size in the test's native units (d, f, h, w, r, ...).
    A 'smaller' directional MDE is negative; two-sided returns magnitude.
    Proportions return Cohen's h without needing prop1/prop2/prop0.
    """
    solver, base, n_key = _resolve(test, None, alpha, alternative, solving_effect=True, **kw)
    _target(alpha, power)

    n = _sample_n(test.lower(), nobs1, nobs, base)
    sign = -1 if alternative == "smaller" else 1

    if solver == "correlation":
        with warnings.catch_warnings():
            warnings.simplefilter("error", ConvergenceWarning)
            z = NormalIndPower().solve_power(nobs1=n - 3, power=power, alpha=alpha,
                        ratio=0, alternative="larger" if sign < 0 else alternative)
        r = float(math.tanh(z))
        if not math.isfinite(r) or not 0 <= r < 1:
            raise RuntimeError("MDE is nonfinite or too close to |r|=1 to represent numerically")
        if not math.isclose(_corr_power(sign * r, n, alpha, alternative), power, abs_tol=1e-5):
            raise RuntimeError("correlation MDE solution failed the power round-trip check")
        return sign * r

    if solver == "regression":
        return _reg_mde(n, base["df_num"], base["k_total"], alpha, power)

    base["power"] = power
    base["effect_size"] = None
    base[n_key] = n
    if sign < 0:
        base["alternative"] = "larger"
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        effect = float(solver.solve_power(**base))
    if not math.isfinite(effect) or effect < 0:
        raise RuntimeError("MDE solver did not return a finite nonnegative magnitude")
    if test.lower() in ("one_proportion", "two_proportions") and effect > math.pi:
        raise ValueError("requested power requires an impossible Cohen's h > pi")
    check = dict(base, effect_size=effect)
    check.pop("power")
    if not math.isclose(float(solver.power(**check)), power, abs_tol=1e-5):
        raise RuntimeError("MDE solution failed the power round-trip check")
    return sign * effect


def power_curve(test, effect_size=None, n_range=None, alpha=0.05, power_target=0.80,
                alternative="two-sided", save=None, show=False, **kw):
    """Plot power vs. sample size. Returns (n_array, power_array).

    n_range iterates sample-1 n for two-sample tests, pairs for paired tests,
    observations otherwise (ANOVA: balanced total n).
    """
    import matplotlib.pyplot as plt

    test = test.lower()
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
    unit = " (sample 1)" if test in ("t_ind", "two_proportions") else " (total)"
    if test == "t_paired":
        unit = " (pairs)"
    ax.set_xlabel("Sample size" + unit)
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
