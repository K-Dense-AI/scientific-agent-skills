#!/usr/bin/env python3
"""ProteinGym DMS fitness, active-site stratification, CV split, and pairwise epistasis evaluator."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any

MUTATION_TOKEN_RE = re.compile(r"^([A-Z\*])(\d+)([A-Z\*])$")
VALID_AA = frozenset("ACDEFGHIKLMNPQRSTVWY*")


def parse_mutant(mutant_str: str) -> list[tuple[str, int, str]]:
    """Parse colon-delimited substitutions into sorted (wt_aa, pos_1based, mut_aa) tuples."""
    cleaned = mutant_str.strip()
    if not cleaned or cleaned.upper() == "WT":
        return []
    parsed: list[tuple[str, int, str]] = []
    seen: set[int] = set()
    for token in cleaned.split(":"):
        match = MUTATION_TOKEN_RE.match(token.strip().upper())
        if not match:
            raise ValueError(f"Invalid ProteinGym mutation token: {token!r} in {mutant_str!r}")
        wt_aa, pos_str, mut_aa = match.groups()
        pos = int(pos_str)
        if wt_aa not in VALID_AA or mut_aa not in VALID_AA or pos < 1:
            raise ValueError(f"Invalid residue or position in {token!r}")
        if pos in seen:
            raise ValueError(f"Duplicate mutated position {pos} in {mutant_str!r}")
        if wt_aa == mut_aa:
            raise ValueError(f"Synonymous substitution {token!r} is invalid")
        seen.add(pos)
        parsed.append((wt_aa, pos, mut_aa))
    return sorted(parsed, key=lambda item: item[1])


def validate_mutant_against_wt(mutations: list[tuple[str, int, str]], wt_seq: str) -> None:
    """Verify 1-indexed wild-type residues against reference protein sequence."""
    seq = wt_seq.strip().upper()
    for wt_aa, pos, _ in mutations:
        if pos > len(seq):
            raise ValueError(f"Position {pos} exceeds wild-type length {len(seq)}")
        if seq[pos - 1] != wt_aa:
            raise ValueError(f"WT mismatch at position {pos}: expected {wt_aa}, got {seq[pos - 1]}")


def midranks(values: list[float]) -> list[float]:
    """Compute 1-based tie-averaged midranks."""
    n = len(values)
    indexed = sorted(enumerate(values), key=lambda pair: pair[1])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i + 1
        while j < n and indexed[j][1] == indexed[i][1]:
            j += 1
        avg = 0.5 * ((i + 1) + j)
        for k in range(i, j):
            ranks[indexed[k][0]] = avg
        i = j
    return ranks


def spearman_rho(y_true: list[float], y_pred: list[float]) -> float:
    """Compute tie-aware Spearman rank correlation."""
    if len(y_true) != len(y_pred):
        raise ValueError("Length mismatch")
    n = len(y_true)
    if n < 2:
        return float("nan")
    rx, ry = midranks(y_true), midranks(y_pred)
    mx, my = sum(rx) / n, sum(ry) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    denom = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return 0.0 if denom <= 1e-15 else max(-1.0, min(1.0, cov / denom))


def roc_auc_binary(y_bin: list[int], y_pred: list[float]) -> float:
    """Compute tie-aware ROC-AUC via Mann-Whitney U statistic."""
    n_pos = sum(1 for b in y_bin if b == 1)
    n_neg = sum(1 for b in y_bin if b == 0)
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    ranks = midranks(y_pred)
    u_stat = sum(r for r, b in zip(ranks, y_bin) if b == 1) - 0.5 * n_pos * (n_pos + 1)
    return u_stat / (n_pos * n_neg)


def mcc_at_prevalence(y_bin: list[int], y_pred: list[float]) -> float:
    """Compute MCC thresholding top N_pos predictions as positive."""
    n = len(y_bin)
    n_pos = sum(1 for b in y_bin if b == 1)
    n_neg = n - n_pos
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    pred_pos = set(sorted(range(n), key=lambda idx: y_pred[idx], reverse=True)[:n_pos])
    tp = sum(1 for idx in range(n) if y_bin[idx] == 1 and idx in pred_pos)
    fp = n_pos - tp
    fn = n_pos - tp
    tn = n_neg - fp
    denom = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return 0.0 if denom <= 0.0 else (tp * tn - fp * fn) / denom


def ndcg_at_quantile(y_true: list[float], y_pred: list[float], quantile: float = 0.10) -> float:
    """Compute NDCG@q with [0, 1] min-max shifted relevance gains."""
    n = len(y_true)
    if n == 0:
        return float("nan")
    y_min, y_max = min(y_true), max(y_true)
    if y_max <= y_min:
        return 1.0
    gains = [(v - y_min) / (y_max - y_min) for v in y_true]
    k = max(1, int(math.floor(quantile * n)))
    order = sorted(range(n), key=lambda idx: y_pred[idx], reverse=True)
    aligned = [0.0] * n
    i = 0
    while i < n:
        j = i + 1
        while j < n and y_pred[order[j]] == y_pred[order[i]]:
            j += 1
        mg = sum(gains[order[m]] for m in range(i, j)) / (j - i)
        for m in range(i, j):
            aligned[m] = mg
        i = j
    dcg = sum(aligned[r] / math.log2(r + 2) for r in range(k))
    idcg = sum(sorted(gains, reverse=True)[r] / math.log2(r + 2) for r in range(k))
    return (dcg / idcg) if idcg > 0.0 else 0.0


def top_k_recall(y_true: list[float], y_pred: list[float], quantile: float = 0.10) -> float:
    """Compute recall of true top-quantile variants in predicted top-quantile."""
    n = len(y_true)
    if n == 0:
        return float("nan")
    k = max(1, int(math.floor(quantile * n)))
    t_set = set(sorted(range(n), key=lambda i: y_true[i], reverse=True)[:k])
    p_set = set(sorted(range(n), key=lambda i: y_pred[i], reverse=True)[:k])
    return len(t_set & p_set) / k


def compute_pairwise_epistasis(
    records: list[dict[str, Any]], wt_score: float = 0.0, wt_pred: float | None = None, noise_tol: float = 0.05
) -> dict[str, Any]:
    """Quantify pairwise mutational epistasis across complete double-mutant cycles."""
    s_exp = {f"{r['mutations'][0][0]}{r['mutations'][0][1]}{r['mutations'][0][2]}": r["dms_score"] for r in records if len(r["mutations"]) == 1}
    s_pred = {f"{r['mutations'][0][0]}{r['mutations'][0][1]}{r['mutations'][0][2]}": r["pred_score"] for r in records if len(r["mutations"]) == 1}
    counts = {"positive_magnitude": 0, "negative_magnitude": 0, "sign": 0, "reciprocal_sign": 0, "additive": 0}
    eps_e: list[float] = []
    eps_p: list[float] = []
    cycles: list[dict[str, Any]] = []
    for row in records:
        if len(row["mutations"]) != 2:
            continue
        k1 = f"{row['mutations'][0][0]}{row['mutations'][0][1]}{row['mutations'][0][2]}"
        k2 = f"{row['mutations'][1][0]}{row['mutations'][1][1]}{row['mutations'][1][2]}"
        if k1 not in s_exp or k2 not in s_exp:
            continue
        da, db, dab = s_exp[k1] - wt_score, s_exp[k2] - wt_score, row["dms_score"] - wt_score
        eps = dab - (da + db)
        eps_e.append(eps)
        ca, cb = dab - db, dab - da
        fa = (da > noise_tol and ca < -noise_tol) or (da < -noise_tol and ca > noise_tol)
        fb = (db > noise_tol and cb < -noise_tol) or (db < -noise_tol and cb > noise_tol)
        regime = "reciprocal_sign" if (fa and fb) else ("sign" if (fa or fb) else ("positive_magnitude" if eps > noise_tol else ("negative_magnitude" if eps < -noise_tol else "additive")))
        counts[regime] += 1
        pe = None
        if wt_pred is not None:
            pe = (row["pred_score"] - wt_pred) - ((s_pred[k1] - wt_pred) + (s_pred[k2] - wt_pred))
            eps_p.append(pe)
        cycles.append({"mutant": f"{k1}:{k2}", "exp_epistasis": round(eps, 6), "pred_epistasis": round(pe, 6) if pe is not None else None, "regime": regime})
    rho = spearman_rho(eps_e, eps_p) if wt_pred is not None and len(eps_e) >= 2 else None
    return {
        "n_complete_cycles": len(cycles),
        "regime_counts": counts,
        "mean_abs_epistasis": (sum(abs(x) for x in eps_e) / len(eps_e)) if eps_e else None,
        "epistasis_spearman_rho": round(rho, 6) if rho is not None and not math.isnan(rho) else None,
        "top_epistatic_pairs": sorted(cycles, key=lambda c: abs(c["exp_epistasis"]), reverse=True)[:10],
    }


def assign_cv_folds(records: list[dict[str, Any]], scheme: str = "modulo", n_folds: int = 5, seed: int = 42) -> list[int]:
    """Assign deterministic CV fold IDs (0..n_folds-1, or -1 for cross-fold multi-mutants)."""
    if n_folds < 2 or scheme not in ("random", "modulo", "contiguous"):
        raise ValueError("Invalid CV split configuration")
    if scheme == "random":
        return [int.from_bytes(hashlib.sha256(f"{seed}:{i}:{r['mutant']}".encode()).digest()[:8], "big") % n_folds for i, r in enumerate(records)]
    positions = sorted({pos for r in records for (_, pos, _) in r["mutations"]})
    if not positions:
        return [0] * len(records)
    p2f = {p: (p % n_folds if scheme == "modulo" else min(n_folds - 1, (idx * n_folds) // len(positions))) for idx, p in enumerate(positions)}
    out: list[int] = []
    for r in records:
        fs = {p2f[pos] for (_, pos, _) in r["mutations"]}
        out.append(0 if not fs else (next(iter(fs)) if len(fs) == 1 else -1))
    return out


def evaluate_records(records: list[dict[str, Any]], quantile: float = 0.10) -> dict[str, Any]:
    """Compute the 5 standard ProteinGym metrics."""
    yt, yp = [r["dms_score"] for r in records], [r["pred_score"] for r in records]
    out: dict[str, Any] = {
        "n_variants": len(records),
        "spearman_rho": round(spearman_rho(yt, yp), 6) if len(records) >= 2 else None,
        "ndcg": round(ndcg_at_quantile(yt, yp, quantile), 6) if records else None,
        "top_recall": round(top_k_recall(yt, yp, quantile), 6) if records else None,
        "roc_auc": None,
        "mcc": None,
    }
    if len(records) >= 2 and all(r.get("dms_bin") in (0, 1) for r in records):
        yb = [int(r["dms_bin"]) for r in records]
        auc, mcc = roc_auc_binary(yb, yp), mcc_at_prevalence(yb, yp)
        out["roc_auc"] = None if math.isnan(auc) else round(auc, 6)
        out["mcc"] = None if math.isnan(mcc) else round(mcc, 6)
    return out


def run_demo() -> int:
    wt_seq = "MKTAYIAKQRQISFVKSHFSRQ"
    rows = [
        {"mutant": "A4G", "dms_score": 0.45, "pred_score": 0.40, "dms_bin": 1},
        {"mutant": "Y5F", "dms_score": 0.80, "pred_score": 0.75, "dms_bin": 1},
        {"mutant": "I6V", "dms_score": 0.10, "pred_score": 0.15, "dms_bin": 1},
        {"mutant": "K8R", "dms_score": -0.30, "pred_score": -0.25, "dms_bin": 0},
        {"mutant": "Q9A", "dms_score": -0.85, "pred_score": -0.70, "dms_bin": 0},
        {"mutant": "R10K", "dms_score": -1.20, "pred_score": -1.10, "dms_bin": 0},
        {"mutant": "A4G:Y5F", "dms_score": 1.65, "pred_score": 1.50, "dms_bin": 1},
        {"mutant": "K8R:Q9A", "dms_score": 0.25, "pred_score": 0.10, "dms_bin": 1},
    ]
    parsed = [{**r, "mutations": parse_mutant(r["mutant"])} for r in rows]
    for p in parsed:
        validate_mutant_against_wt(p["mutations"], wt_seq)
    m = evaluate_records(parsed, quantile=0.25)
    epi = compute_pairwise_epistasis(parsed, wt_score=0.0, wt_pred=0.0)
    print(f"[OK] Demo evaluated {m['n_variants']} variants | rho={m['spearman_rho']:.4f} | cycles={epi['n_complete_cycles']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Evaluate ProteinGym DMS metrics, active-site shells, CV splits, and epistasis.")
    ap.add_argument("--input", type=Path, help="Input DMS CSV path (omit to run built-in demo).")
    ap.add_argument("--pred-col", type=str, default="model_score")
    ap.add_argument("--dms-col", type=str, default="DMS_score")
    ap.add_argument("--bin-col", type=str, default="DMS_score_bin")
    ap.add_argument("--mutant-col", type=str, default="mutant")
    ap.add_argument("--negate-pred", action="store_true")
    ap.add_argument("--wt-seq", type=str, default=None)
    ap.add_argument("--quantile", type=float, default=0.10)
    ap.add_argument("--epistasis", action="store_true")
    ap.add_argument("--wt-score", type=float, default=None)
    ap.add_argument("--wt-pred", type=float, default=None)
    ap.add_argument("--residue-distances", type=Path, default=None)
    ap.add_argument("--split-scheme", choices=("random", "modulo", "contiguous"), default="modulo")
    ap.add_argument("--n-folds", type=int, default=5)
    ap.add_argument("--split-out", type=Path, default=None)
    ap.add_argument("--json-out", type=Path, default=None)
    args = ap.parse_args(argv)
    if args.input is None:
        return run_demo()
    if not args.input.exists():
        print(f"[FAIL] Input CSV not found: {args.input}")
        return 1

    raw_rows, records = [], []
    wt_s, wt_p = args.wt_score, args.wt_pred
    sign = -1.0 if args.negate_pred else 1.0
    with args.input.open("r", encoding="utf-8", newline="") as f:
        for idx, row in enumerate(csv.DictReader(f), start=2):
            ms = (row.get(args.mutant_col) or "").strip()
            dr, pr = row.get(args.dms_col), row.get(args.pred_col)
            if dr in (None, "") or pr in (None, ""):
                continue
            dv, pv = float(dr), sign * float(pr)
            if ms.upper() == "WT":
                wt_s = dv if wt_s is None else wt_s
                wt_p = pv if wt_p is None else wt_p
                continue
            try:
                muts = parse_mutant(ms)
                if args.wt_seq:
                    validate_mutant_against_wt(muts, args.wt_seq)
            except ValueError as exc:
                print(f"[FAIL] Row {idx}: {exc}")
                return 1
            bv = int(float(row[args.bin_col])) if row.get(args.bin_col) not in (None, "") else None
            raw_rows.append(row)
            records.append({"mutant": ms, "mutations": muts, "dms_score": dv, "pred_score": pv, "dms_bin": bv})
    if not records:
        print("[FAIL] No valid variant records found")
        return 1

    overall = evaluate_records(records, quantile=args.quantile)
    by_depth = {k: evaluate_records(sub, args.quantile) for k, fn in (("single", lambda m: len(m) == 1), ("double", lambda m: len(m) == 2), ("higher_order", lambda m: len(m) >= 3)) if (sub := [r for r in records if fn(r["mutations"])])}
    by_shell: dict[str, Any] = {}
    if args.residue_distances:
        with args.residue_distances.open("r", encoding="utf-8", newline="") as df:
            dmap = {int(r["position"]): float(r["distance_angstrom"]) for r in csv.DictReader(df) if r.get("position") and r.get("distance_angstrom")}
        shells: dict[str, list[dict[str, Any]]] = {"first_shell_lt_5A": [], "second_shell_5_to_10A": [], "distal_gt_10A": []}
        for rec in records:
            ds = [dmap[pos] for (_, pos, _) in rec["mutations"] if pos in dmap]
            if ds:
                md = min(ds)
                shells["first_shell_lt_5A" if md < 5.0 else ("second_shell_5_to_10A" if md <= 10.0 else "distal_gt_10A")].append(rec)
        by_shell = {k: evaluate_records(v, args.quantile) for k, v in shells.items() if v}

    epi = compute_pairwise_epistasis(records, 0.0 if wt_s is None else wt_s, wt_p) if args.epistasis else None
    if args.split_out:
        folds = assign_cv_folds(records, args.split_scheme, args.n_folds)
        with args.split_out.open("w", encoding="utf-8", newline="") as sf:
            w = csv.DictWriter(sf, fieldnames=list(raw_rows[0].keys()) + ["cv_fold"])
            w.writeheader()
            for r_d, fl in zip(raw_rows, folds):
                w.writerow({**r_d, "cv_fold": fl})
    if args.json_out:
        args.json_out.write_text(json.dumps({"overall": overall, "by_mutation_depth": by_depth, "by_active_site_shell": by_shell, "epistasis": epi}, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] Loaded {overall['n_variants']} variants -> Spearman rho: {overall['spearman_rho']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
