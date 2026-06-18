"""Monte Carlo power for designs with no closed-form formula.

Closed-form power covers a handful of standard tests. For anything else --
logistic/Poisson regression, mixed-effects models, cluster-randomized trials,
survival analysis, mediation, interactions -- you estimate power by simulation:

    1. simulate a dataset under the assumed truth
    2. analyze it with the EXACT test/model you will use on real data
    3. repeat many times; power = fraction of replicates that reach significance

This module provides the harness (`simulate_power`, `find_sample_size`) plus four
worked, runnable examples. Copy an example and swap in your own data-generating
process and analysis -- that is the intended workflow.

Requires: numpy, scipy, statsmodels. The survival example also needs lifelines.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass
class PowerEstimate:
    power: float
    n_sims: int
    n: int
    ci_low: float
    ci_high: float

    def __str__(self):
        return (f"n={self.n}: power={self.power:.3f} "
                f"(95% MC CI {self.ci_low:.3f}-{self.ci_high:.3f}, {self.n_sims} sims)")


def _wilson_ci(k, n, z=1.96):
    """Wilson score interval for a proportion -- the right CI for a simulated rate."""
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
        replicate is independent. (Take alpha into account inside the function,
        or compare a returned p-value yourself; see examples.)

    Returns a PowerEstimate including a Wilson confidence interval, so you can
    tell whether 0.81 vs 0.79 is real or just simulation noise.
    """
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(n_sims):
        if gen_and_test(n, rng):
            hits += 1
    lo, hi = _wilson_ci(hits, n_sims)
    return PowerEstimate(power=hits / n_sims, n_sims=n_sims, n=n,
                         ci_low=lo, ci_high=hi)


def find_sample_size(gen_and_test, target_power=0.80, n_sims=2000, alpha=0.05,
                     lo=10, hi=2000, seed=0, verbose=True):
    """Smallest n reaching target_power, via bisection over n.

    Assumes power is (roughly) monotincreasing in n -- true for essentially all
    real designs. Uses a fixed seed per n so the search is stable; widen n_sims
    near the boundary if the curve is noisy. Returns (n, PowerEstimate).
    """
    # expand hi until it clears target (guards against too-small upper bound)
    while True:
        est_hi = simulate_power(gen_and_test, hi, n_sims, alpha, seed)
        if est_hi.power >= target_power or hi >= 1_000_000:
            break
        lo, hi = hi, hi * 2

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

    def gen_and_test(n, rng):  # n per group
        a = rng.normal(0.0, sd, n)
        b = rng.normal(effect, sd, n)
        _, p = stats.ttest_ind(a, b)
        return p < alpha

    return gen_and_test


def example_logistic_regression(beta=0.8, base_rate=0.2, x_sd=1.0, alpha=0.05):
    """Power for a single coefficient in logistic regression.

    beta is the log-odds change per 1-SD increase in a continuous predictor x.
    No closed form -- this is the canonical reason to simulate.
    """
    import statsmodels.api as sm

    intercept = math.log(base_rate / (1 - base_rate))

    def gen_and_test(n, rng):
        x = rng.normal(0, x_sd, n)
        logit = intercept + beta * x
        p = 1 / (1 + np.exp(-logit))
        y = rng.binomial(1, p)
        X = sm.add_constant(x)
        try:
            res = sm.Logit(y, X).fit(disp=0)
            return res.pvalues[1] < alpha
        except Exception:
            return False  # non-convergence / perfect separation -> not significant

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

    # split total variance into between-cluster (tau^2) and residual by the ICC
    tau = math.sqrt(icc * resid_sd**2 / (1 - icc)) if icc > 0 else 0.0

    def gen_and_test(n, rng):  # n clusters per arm
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
        try:
            res = smf.mixedlm("y ~ arm", df, groups=df["cluster"]).fit()
            return res.pvalues["arm"] < alpha
        except Exception:
            return False

    return gen_and_test


def example_linear_mixed_repeated(effect=0.4, n_timepoints=3, subj_sd=0.7,
                                  resid_sd=1.0, alpha=0.05):
    """Repeated-measures: a linear time trend within subjects, random intercepts.

    `n` is the number of subjects; each is measured at n_timepoints occasions.
    `effect` is the slope per time unit. Tests whether the time slope != 0.
    """
    import statsmodels.formula.api as smf
    import pandas as pd

    def gen_and_test(n, rng):  # n subjects
        rows = []
        for s in range(n):
            b0 = rng.normal(0, subj_sd)
            for t in range(n_timepoints):
                y = b0 + effect * t + rng.normal(0, resid_sd)
                rows.append((y, t, s))
        df = pd.DataFrame(rows, columns=["y", "time", "subj"])
        try:
            res = smf.mixedlm("y ~ time", df, groups=df["subj"]).fit()
            return res.pvalues["time"] < alpha
        except Exception:
            return False

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
    print(f"-> need ~{n} subjects ({est})")
