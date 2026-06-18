"""Reproducible randomization / allocation schedules for experiments and trials.

Randomization is what licenses causal inference: it breaks the link between
treatment assignment and any confounder, measured or not. But "I shuffled it"
is not enough — the *method* matters (simple vs. blocked vs. stratified) and the
schedule must be reproducible (seeded) and auditable. This module produces
allocation tables as pandas DataFrames, with a fixed seed so the exact schedule
can be regenerated and archived.

Functions:
  simple_randomization        independent coin-flip per unit (can yield imbalance)
  block_randomization         permuted blocks -> balance throughout enrollment
  stratified_block_randomization   blocks within strata -> balance per subgroup
  cluster_randomization       randomize whole clusters (sites/classes), not units
  assign_factorial_runs       randomize the RUN ORDER of a list of design rows

Requires: numpy, pandas.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _normalize_ratio(arms, ratio):
    """Turn arms + integer ratio into a block template list, e.g.
    arms=['A','B'], ratio=(2,1) -> ['A','A','B']."""
    if ratio is None:
        ratio = [1] * len(arms)
    if len(ratio) != len(arms):
        raise ValueError("ratio must have one entry per arm")
    if any(r <= 0 for r in ratio):
        raise ValueError("ratio entries must be positive integers")
    template = []
    for arm, r in zip(arms, ratio):
        template += [arm] * int(r)
    return template


def simple_randomization(n, arms=("treatment", "control"), ratio=None, seed=0):
    """Independent random assignment per unit.

    Simplest method; with small n it can produce noticeable arm-size imbalance
    (like flipping few coins). Fine for large n. Use block_randomization when you
    need balance, especially for n < ~100 or sequential enrollment.
    """
    rng = np.random.default_rng(seed)
    arms = list(arms)
    template = _normalize_ratio(arms, ratio)
    probs = np.array([template.count(a) for a in arms], dtype=float)
    probs /= probs.sum()
    assign = rng.choice(arms, size=n, p=probs)
    return pd.DataFrame({"unit_id": np.arange(1, n + 1), "arm": assign})


def block_randomization(n, arms=("treatment", "control"), block_size=None,
                        ratio=None, seed=0):
    """Permuted-block randomization: balance is maintained throughout enrollment.

    Within each block every arm appears in the specified ratio; the order inside
    a block is shuffled. block_size must be a multiple of sum(ratio). Leaving it
    None picks a small valid size. Mild caveat: fixed small blocks are slightly
    predictable in unblinded trials — vary block size if that matters.
    """
    rng = np.random.default_rng(seed)
    arms = list(arms)
    template = _normalize_ratio(arms, ratio)
    unit = len(template)
    if block_size is None:
        block_size = unit * 2  # two of each ratio-unit per block
    if block_size % unit != 0:
        raise ValueError(f"block_size ({block_size}) must be a multiple of "
                         f"sum(ratio)={unit}")
    reps = block_size // unit

    out = []
    block_id = 0
    while len(out) < n:
        block = template * reps
        rng.shuffle(block)
        for a in block:
            out.append((len(out) + 1, block_id, a))
        block_id += 1
    df = pd.DataFrame(out[:n], columns=["unit_id", "block", "arm"])
    return df


def stratified_block_randomization(strata, arms=("treatment", "control"),
                                   block_size=None, ratio=None, seed=0):
    """Block-randomize independently within each stratum.

    Use when a prognostic variable (site, sex, disease stage) must be balanced
    across arms. `strata` is a dict {stratum_label: n_in_that_stratum} or a
    sequence of stratum labels (one per unit). Each stratum gets its own permuted
    blocks, guaranteeing balance within every subgroup.
    """
    if isinstance(strata, dict):
        items = list(strata.items())
    else:  # sequence of labels
        s = pd.Series(list(strata))
        items = list(s.value_counts().sort_index().items())

    frames = []
    for i, (label, count) in enumerate(items):
        df = block_randomization(count, arms=arms, block_size=block_size,
                                 ratio=ratio, seed=seed + 1 + i)
        df.insert(1, "stratum", label)
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    out["unit_id"] = np.arange(1, len(out) + 1)
    return out


def cluster_randomization(clusters, arms=("treatment", "control"), ratio=None,
                          block_size=None, seed=0):
    """Randomize whole clusters (clinics, schools, litters) to arms.

    The cluster — not the individual — is the unit of randomization AND the unit
    of analysis-level independence. `clusters` is a list of cluster IDs (or an int
    count). Returns one row per cluster. Analyze with a method that accounts for
    clustering (mixed model / GEE); treating members as independent is
    pseudoreplication. Uses blocking across clusters for arm balance.
    """
    if isinstance(clusters, int):
        clusters = [f"cluster_{i+1}" for i in range(clusters)]
    clusters = list(clusters)
    df = block_randomization(len(clusters), arms=arms, ratio=ratio,
                             block_size=block_size, seed=seed)
    df = df.drop(columns=["unit_id"])
    df.insert(0, "cluster_id", clusters)
    return df


def assign_factorial_runs(design_df, seed=0):
    """Randomize the execution order of a set of design runs (e.g. a DOE matrix).

    Run order matters: executing a factorial design in a systematic order
    confounds the factors with time/drift (the machine warms up, the reagent
    degrades). Randomizing run order protects against that. Returns the design
    with a 'run_order' column and rows sorted by it.
    """
    rng = np.random.default_rng(seed)
    df = design_df.copy().reset_index(drop=True)
    order = rng.permutation(len(df)) + 1
    df["run_order"] = order
    return df.sort_values("run_order").reset_index(drop=True)


def arm_balance(df, arm_col="arm", by=None):
    """Quick check: counts per arm (optionally within each stratum/block)."""
    if by:
        return df.groupby([by, arm_col]).size().unstack(fill_value=0)
    return df[arm_col].value_counts()


if __name__ == "__main__":
    print("== simple (n=10) ==")
    print(arm_balance(simple_randomization(10, seed=1)).to_dict())

    print("\n== permuted blocks, 2:1 treatment:control, n=12 ==")
    d = block_randomization(12, arms=["treatment", "control"], ratio=(2, 1), seed=1)
    print(d.to_string(index=False))
    print("balance:", arm_balance(d).to_dict())

    print("\n== stratified by site (A=8, B=6) ==")
    d = stratified_block_randomization({"siteA": 8, "siteB": 6}, seed=1)
    print(arm_balance(d, by="stratum").to_string())

    print("\n== cluster randomization (6 clinics) ==")
    print(cluster_randomization(6, seed=1).to_string(index=False))
