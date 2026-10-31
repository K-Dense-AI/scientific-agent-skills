"""Design-of-experiments (DOE) matrices as labeled, decoded pandas DataFrames.

pydoe returns designs in *coded* units (-1/+1, or 0..k-1). Researchers want the
design in *real* factor units (temperature in C, concentration in mM) with named
columns, randomized run order, and a clear sense of what each design is for. This
module wraps pydoe 1.5.0 to do exactly that.

A `factors` spec maps factor names to their real-world levels:
  - two-level / continuous:  {"temp": (20, 60), "conc": (1, 10)}   # (low, high)
  - multi-level categorical:  {"catalyst": ["A", "B", "C"]}

Functions:
  full_factorial          every combination of given levels (cost grows fast)
  two_level_factorial     2^k full factorial (screening + interactions)
  fractional_factorial    2^(k-p) fraction (screening many factors cheaply)
  plackett_burman         very economical main-effects-only screening
  central_composite       response-surface design (curvature / optimization)
  box_behnken             response-surface design, no extreme corners
  latin_hypercube         space-filling sample for simulation / computer experiments

Each returns a DataFrame in real units; pass randomize=True to also get a
randomized 'run_order' (default except for Latin hypercube).
Requires: pydoe, numpy, pandas.
"""

from __future__ import annotations

import operator

import numpy as np
import pandas as pd


def _factor_names(factors):
    if not factors or "run_order" in factors:
        raise ValueError("provide at least one factor; 'run_order' is reserved")
    return list(factors)


def _ranges(factors):
    """Reject malformed ranges rather than silently discarding a third level."""
    _factor_names(factors)
    out = {}
    for name, levels in factors.items():
        try:
            values = np.asarray(levels, dtype=float)
            valid = (values.shape == (2,) and np.isfinite(values).all()
                     and values[0] < values[1])
        except (TypeError, ValueError, OverflowError):
            valid = False
        if not valid:
            raise ValueError(f"{name!r} needs exactly two finite numeric levels, low < high")
        out[name] = tuple(values)
    return out


def _decode_two_level(coded, factors):
    """Map a -1/+1 coded matrix to real (low/high) units per factor."""
    names = list(factors)
    out = {}
    for j, name in enumerate(names):
        lvl = factors[name]
        low, high = lvl[0], lvl[1]
        mid, half = (high + low) / 2.0, (high - low) / 2.0
        out[name] = mid + coded[:, j] * half
    return pd.DataFrame(out)


def _randomize(df, randomize, seed):
    if not randomize:
        return df.reset_index(drop=True)
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(df)) + 1
    df = df.copy()
    df.insert(0, "run_order", order)
    return df.sort_values("run_order").reset_index(drop=True)


def full_factorial(factors, randomize=True, seed=0):
    """Every combination of the listed levels.

    factors values are explicit level lists, e.g.
      {"temp": [20, 40, 60], "catalyst": ["A", "B"]}  -> 3*2 = 6 runs.
    Runs = product of level counts, so this explodes quickly with many factors.
    """
    from pydoe import fullfact
    names = _factor_names(factors)
    levels = [list(factors[n]) for n in names]
    if any(not level or pd.Series(level, dtype=object).isna().any()
           or not pd.Series(level, dtype=object).is_unique for level in levels):
        raise ValueError("each factor needs nonempty, non-missing, distinct levels")
    counts = [len(l) for l in levels]
    coded = fullfact(counts).astype(int)
    data = {n: [levels[j][coded[i, j]] for i in range(len(coded))]
            for j, n in enumerate(names)}
    return _randomize(pd.DataFrame(data), randomize, seed)


def two_level_factorial(factors, randomize=True, seed=0):
    """Full 2^k factorial: all main effects and all interactions, estimable.

    Each factor needs a (low, high) pair. Use for k up to ~5; beyond that the
    run count (2^k) gets expensive — switch to fractional_factorial or
    plackett_burman for screening.
    """
    from pydoe import ff2n
    factors = _ranges(factors)
    coded = ff2n(len(factors))
    return _randomize(_decode_two_level(coded, factors), randomize, seed)


def fractional_factorial(factors, generator, randomize=True, seed=0):
    """2^(k-p) fractional factorial from a generator string.

    `generator` is pydoe's Yates notation, e.g. for 4 factors in 8 runs:
    "a b c abc" (I=ABCD, resolution IV). Each token defines a column; multi-letter tokens
    alias a factor with an interaction (this is the tradeoff — fewer runs, some
    effects confounded). Choose a higher-resolution generator if you need to
    separate main effects from two-factor interactions.
    """
    from pydoe import fracfact
    factors = _ranges(factors)
    coded = fracfact(generator)
    if coded.shape[1] != len(factors):
        raise ValueError(f"generator defines {coded.shape[1]} factors but "
                         f"{len(factors)} were named")
    return _randomize(_decode_two_level(coded, factors), randomize, seed)


def plackett_burman(factors, randomize=True, seed=0):
    """Plackett-Burman screening design: main effects only, very few runs.

    The target run count is the next multiple of 4 above k. pydoe 1.5.0 supports
    counts of form 2^a, 12*2^a, or 20*2^a; other targets (e.g. 28 runs for k=25)
    raise ValueError. Interactions can confound main effects; inspect aliasing.
    """
    from pydoe import pbdesign
    factors = _ranges(factors)
    coded = pbdesign(len(factors))
    return _randomize(_decode_two_level(coded, factors), randomize, seed)


def central_composite(factors, center=(0, 1), alpha="orthogonal",
                      face="circumscribed", randomize=True, seed=0):
    """Central composite design (CCD) for response-surface / optimization work.

    Adds axial ("star") points and center points to a 2^k factorial so you can fit
    a quadratic model and locate an optimum. With face='circumscribed' the axial
    points sit OUTSIDE the (low, high) box (so real levels exceed your stated
    range); use face='inscribed' or 'faced' to keep everything within range.
    `center` = (n center pts in factorial block, n in axial block). The default
    supplies just one center run, so it does not estimate pure error. Add true
    replicate runs when required. Output is globally shuffled: it does not
    retain block membership for an experiment run in separate batches.
    """
    from pydoe import ccdesign
    factors = _ranges(factors)
    coded = ccdesign(len(factors), center=center, alpha=alpha, face=face)
    return _randomize(_decode_two_level(coded, factors), randomize, seed)


def box_behnken(factors, center=1, randomize=True, seed=0):
    """Box-Behnken response-surface design (needs >= 3 factors).

    Like a CCD it fits a quadratic, but it never uses the extreme corner
    combinations (all-low or all-high), which is useful when those corners are
    unsafe or infeasible. Compare actual run counts; it is not always smaller.
    The default one center run does not supply pure-error replication.
    """
    from pydoe import bbdesign
    factors = _ranges(factors)
    if len(factors) < 3:
        raise ValueError("box_behnken requires at least 3 factors")
    coded = bbdesign(len(factors), center=center)
    return _randomize(_decode_two_level(coded, factors), randomize, seed)


def latin_hypercube(factors, n_samples, criterion="maximin", seed=0,
                    randomize=False):
    """Space-filling Latin hypercube sample over continuous factor ranges.

    For computer experiments / simulations where you want even coverage of a
    high-dimensional space with relatively few points. Each factor needs a
    (low, high) range. `criterion`: 'maximin' spreads points apart;
    'center'/'centermaximin'/'correlation' are alternatives.
    """
    from pydoe import lhs
    factors = _ranges(factors)
    try:
        n_samples = operator.index(n_samples)
    except TypeError:
        raise ValueError("n_samples must be a positive integer") from None
    if n_samples < 1:
        raise ValueError("n_samples must be a positive integer")
    # pydoe draws from its own default_rng, so seeding numpy's global RNG has
    # no effect -- the seed has to be handed to lhs itself.
    names = list(factors)
    unit = lhs(  # in [0,1]
        len(names), samples=n_samples, criterion=criterion, seed=seed
    )
    out = {}
    for j, n in enumerate(names):
        low, high = factors[n][0], factors[n][1]
        out[n] = low + unit[:, j] * (high - low)
    df = pd.DataFrame(out)
    return _randomize(df, randomize, seed)


if __name__ == "__main__":
    f2 = {"temp": (20, 60), "conc": (1, 10), "ph": (6, 8)}

    print("== 2^3 full factorial ==")
    print(two_level_factorial(f2, seed=1).to_string(index=False))

    print("\n== fractional 2^(4-1), generator 'a b c abc' ==")
    f4 = {"A": (-1, 1), "B": (-1, 1), "C": (-1, 1), "D": (-1, 1)}
    print(fractional_factorial(f4, "a b c abc", seed=1).to_string(index=False))

    print("\n== Plackett-Burman screening, 5 factors ==")
    f5 = {f"x{i}": (0, 1) for i in range(1, 6)}
    print(f"runs = {len(plackett_burman(f5, randomize=False))}")

    print("\n== central composite (2 factors) ==")
    print(central_composite({"temp": (20, 60), "conc": (1, 10)}, seed=1).round(2).to_string(index=False))

    print("\n== Latin hypercube, 8 samples over 3 factors ==")
    print(latin_hypercube(f2, 8, seed=1).round(2).to_string(index=False))
