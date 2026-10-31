"""Monte Carlo power when analytical assumptions do not match the design.

Simulation can represent features omitted by simple analytical approximations
for logistic/Poisson regression, mixed models, clustering, survival, mediation,
or interactions:

    1. simulate a dataset under the assumed truth
    2. analyze it with the EXACT test/model you will use on real data
    3. repeat many times; power = fraction of replicates that reach significance

This module provides the harness (`simulate_power`, `find_sample_size`) plus four
worked, runnable examples. Copy an example and swap in your own data-generating
process and analysis -- that is the intended workflow.

Requires: numpy, scipy, pandas, statsmodels. Survival extensions can use lifelines.
"""

from __future__ import annotations

import math
from numbers import Integral
from dataclasses import dataclass, field
import warnings

import numpy as np


@dataclass
class PowerEstimate:
    power: float
    n_sims: int
    n: int
    ci_low: float
    ci_high: float
    n_failures: int = 0
    failure_reasons: dict[str, int] = field(default_factory=dict)
    n_warned: int = 0
    warning_counts: dict[str, int] = field(default_factory=dict)

    def __str__(self):
        return (f"n={self.n}: power={self.power:.3f} "
                f"(95% MC CI {self.ci_low:.3f}-{self.ci_high:.3f}, {self.n_sims} sims; "
                f"{self.n_failures} failed, {self.n_warned} warned)")


class SimulationFitError(RuntimeError):
    """An anticipated fitting failure, counted separately and as non-rejection."""


def _fit_decision(fit, coefficient, alpha):
    """Require convergence and a finite p-value from a statsmodels fit."""
    from statsmodels.tools.sm_exceptions import (
        HessianInversionWarning, PerfectSeparationError, PerfectSeparationWarning,
    )
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", PerfectSeparationWarning)
            warnings.simplefilter("error", HessianInversionWarning)
            result = fit()
    except (np.linalg.LinAlgError, PerfectSeparationError, PerfectSeparationWarning,
            HessianInversionWarning, FloatingPointError) as exc:
        raise SimulationFitError(type(exc).__name__) from exc
    converged = (result.converged if hasattr(result, "converged")
                 else result.mle_retvals.get("converged", False))
    if not converged:
        raise SimulationFitError("nonconvergence")
    pvalue = result.pvalues[coefficient]
    if not np.isfinite(pvalue) or not 0 <= pvalue <= 1:
        raise SimulationFitError("invalid p-value")
    return bool(pvalue < alpha)


def _check_example(alpha, **positive):
    if not np.isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError("alpha must lie strictly between 0 and 1")
    for name, value in positive.items():
        if not np.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive")


def _wilson_ci(k, n, z=1.96):
    """Wilson interval for a simulated rate conditional on fixed assumptions."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def simulate_power(gen_and_test, n, n_sims=2000, alpha=0.05, seed=0):
    """Estimate power at sample size `n`.

    gen_and_test(n, rng) -> bool : build a dataset of size n under the assumed
        effect, run the planned analysis, and return True iff it is significant.
        It receives a numpy Generator `rng` so results are reproducible and each
        replicate consumes fresh pseudorandom draws. Alpha must be used inside
        the callback; the harness alpha argument is validated but not forwarded.
        Raise SimulationFitError for an expected fit failure: it counts as a
        non-rejection in the full denominator and is reported separately.
        Other exceptions propagate so programming errors are not hidden.

    Returns a PowerEstimate including a Wilson confidence interval, so you can
    tell whether 0.81 vs 0.79 is real or just simulation noise.
    """
    if any(isinstance(value, bool) or not isinstance(value, Integral) or value < 1
           for value in (n, n_sims)):
        raise ValueError("n and n_sims must be positive integers")
    if not 0 < alpha < 1:
        raise ValueError("alpha must lie strictly between 0 and 1")
    rng = np.random.default_rng(seed)
    hits = 0
    failures = {}
    warning_counts = {}
    n_warned = 0
    for _ in range(n_sims):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                rejected = gen_and_test(n, rng)
            except SimulationFitError as exc:
                reason = str(exc) or "unspecified fit failure"
                failures[reason] = failures.get(reason, 0) + 1
                rejected = False
        if caught:
            n_warned += 1
        for warning in caught:
            name = warning.category.__name__
            warning_counts[name] = warning_counts.get(name, 0) + 1
        if not isinstance(rejected, (bool, np.bool_)):
            raise TypeError("gen_and_test must return a boolean rejection decision, not a p-value")
        if rejected:
            hits += 1
    lo, hi = _wilson_ci(hits, n_sims)
    return PowerEstimate(power=hits / n_sims, n_sims=n_sims, n=n,
                         ci_low=lo, ci_high=hi, n_failures=sum(failures.values()),
                         failure_reasons=failures, n_warned=n_warned,
                         warning_counts=warning_counts)


def find_sample_size(gen_and_test, target_power=0.80, n_sims=2000, alpha=0.05,
                     lo=10, hi=2000, seed=0, verbose=True):
    """Candidate n reaching estimated target power, via noisy bisection over n.

    Requires a design whose power increases with n; discrete designs, rounding,
    and fit failures can violate this. A fixed seed makes the search reproducible
    but not monotone or noise-free. Validate the candidate and neighboring n with
    more replicates and a fresh seed. Returns (n, PowerEstimate); the reported CI
    at an adaptively selected n is not a selection-adjusted assurance interval.
    """
    if any(isinstance(value, bool) or not isinstance(value, Integral)
           for value in (lo, hi)) or not 1 <= lo <= hi <= 1_000_000:
        raise ValueError("bounds must be integers with 1 <= lo <= hi <= 1000000")
    if not 0 < target_power <= 1:
        raise ValueError("target_power must lie in (0, 1]")
    # expand hi until it clears target (guards against too-small upper bound)
    while True:
        est_hi = simulate_power(gen_and_test, hi, n_sims, alpha, seed)
        if est_hi.power >= target_power:
            break
        if hi >= 1_000_000:
            raise ValueError("target power not reached by the sample-size cap of 1000000")
        lo, hi = hi, min(hi * 2, 1_000_000)

    best = est_hi
    while lo < hi:
        mid = (lo + hi) // 2
        est = simulate_power(gen_and_test, mid, n_sims, alpha, seed)
        if verbose:
            print(est)
        if est.power >= target_power:
            hi, best = mid, est
        else:
            lo = mid + 1
    return hi, best


# ========================================================================== #
# Worked examples -- run this file directly to see them.
# Each is a `gen_and_test(n, rng)` you can adapt.
# ========================================================================== #

def example_two_group_difference(effect=0.5, sd=1.0, alpha=0.05):
    """Two-group difference in means (sanity check vs. the closed-form t-test)."""
    from scipy import stats
    _check_example(alpha, sd=sd)
    if not np.isfinite(effect):
        raise ValueError("effect must be finite")

    def gen_and_test(n, rng):  # n per group
        if n < 2:
            raise ValueError("two-group t-test needs at least two observations per group")
        a = rng.normal(0.0, sd, n)
        b = rng.normal(effect, sd, n)
        _, p = stats.ttest_ind(a, b, equal_var=True, alternative="two-sided")
        return p < alpha

    return gen_and_test


def example_logistic_regression(beta=0.8, base_rate=0.2, x_sd=1.0, alpha=0.05):
    """Power for a single coefficient in logistic regression.

    beta is the log-odds change per one raw unit of x (SD is x_sd).
    base_rate is P(y=1 | x=0), not the marginal event rate.
    """
    import statsmodels.api as sm
    from scipy.special import expit

    _check_example(alpha, x_sd=x_sd)
    if not np.isfinite(beta) or not np.isfinite(base_rate) or not 0 < base_rate < 1:
        raise ValueError("beta must be finite and base_rate must lie in (0, 1)")

    intercept = math.log(base_rate / (1 - base_rate))

    def gen_and_test(n, rng):
        if n < 3:
            raise ValueError("logistic example requires at least three observations")
        x = rng.normal(0, x_sd, n)
        logit = intercept + beta * x
        p = expit(logit)
        y = rng.binomial(1, p)
        X = sm.add_constant(x)
        return _fit_decision(lambda: sm.Logit(y, X).fit(disp=0), 1, alpha)

    return gen_and_test


def example_cluster_randomized(effect=0.3, icc=0.05, cluster_size=20,
                               resid_sd=1.0, alpha=0.05):
    """Cluster-randomized trial: clusters (not individuals) are randomized.

    Ignoring the clustering (analyzing individuals as independent) would badly
    overstate power -- that is pseudoreplication. Here `n` is the number of
    clusters PER ARM; the analysis is a mixed model with a random cluster intercept.
    """
    import statsmodels.formula.api as smf
    import pandas as pd
    _check_example(alpha, resid_sd=resid_sd)
    if not np.isfinite(effect) or not np.isfinite(icc) or not 0 <= icc < 1:
        raise ValueError("effect must be finite and icc must lie in [0, 1)")
    if isinstance(cluster_size, bool) or not isinstance(cluster_size, Integral) or cluster_size < 2:
        raise ValueError("cluster_size must be an integer >= 2")

    # split total variance into between-cluster (tau^2) and residual by the ICC
    tau = math.sqrt(icc * resid_sd**2 / (1 - icc)) if icc > 0 else 0.0

    def gen_and_test(n, rng):  # n clusters per arm
        if n < 2:
            raise ValueError("cluster example requires at least two clusters per arm")
        rows = []
        cid = 0
        for arm in (0, 1):
            for _ in range(n):
                u = rng.normal(0, tau)  # cluster random effect
                for _ in range(cluster_size):
                    y = effect * arm + u + rng.normal(0, resid_sd)
                    rows.append((y, arm, cid))
                cid += 1
        df = pd.DataFrame(rows, columns=["y", "arm", "cluster"])
        return _fit_decision(
            lambda: smf.mixedlm("y ~ arm", df, groups=df["cluster"]).fit(reml=True),
            "arm", alpha)

    return gen_and_test


def example_linear_mixed_repeated(effect=0.4, n_timepoints=3, subj_sd=0.7,
                                  resid_sd=1.0, alpha=0.05):
    """Repeated-measures: a linear time trend within subjects, random intercepts.

    `n` is the number of subjects; each is measured at n_timepoints occasions.
    `effect` is the slope per time unit. Tests whether the time slope != 0.
    """
    import statsmodels.formula.api as smf
    import pandas as pd
    _check_example(alpha, resid_sd=resid_sd)
    if not np.isfinite(effect) or not np.isfinite(subj_sd) or subj_sd < 0:
        raise ValueError("effect must be finite and subj_sd finite and nonnegative")
    if isinstance(n_timepoints, bool) or not isinstance(n_timepoints, Integral) or n_timepoints < 2:
        raise ValueError("n_timepoints must be an integer >= 2")

    def gen_and_test(n, rng):  # n subjects
        if n < 2:
            raise ValueError("repeated-measures example requires at least two subjects")
        rows = []
        for s in range(n):
            b0 = rng.normal(0, subj_sd)
            for t in range(n_timepoints):
                y = b0 + effect * t + rng.normal(0, resid_sd)
                rows.append((y, t, s))
        df = pd.DataFrame(rows, columns=["y", "time", "subj"])
        return _fit_decision(
            lambda: smf.mixedlm("y ~ time", df, groups=df["subj"]).fit(reml=True),
            "time", alpha)

    return gen_and_test


if __name__ == "__main__":
    print("== two-group difference (compare to closed-form t-test n/group=64) ==")
    g = example_two_group_difference(effect=0.5)
    print(simulate_power(g, n=64, n_sims=2000))

    print("\n== logistic regression, beta=0.8 ==")
    g = example_logistic_regression(beta=0.8, base_rate=0.2)
    print(simulate_power(g, n=150, n_sims=1000))

    print("\n== search: subjects needed for repeated-measures slope=0.4 ==")
    g = example_linear_mixed_repeated(effect=0.4, n_timepoints=3)
    n, est = find_sample_size(g, target_power=0.80, n_sims=500, lo=10, hi=60,
                              verbose=False)
    print(f"-> candidate n={n} subjects; confirm with fresh simulations ({est})")
