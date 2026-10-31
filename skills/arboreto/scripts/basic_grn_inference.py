#!/usr/bin/env python3
"""Infer candidate TF-target associations from a observations-by-genes TSV.

Use the exact compatibility environment in SKILL.md. The output is headerless
TF, target, importance TSV; scores do not establish causal regulation.
"""

import argparse
import csv
from importlib.metadata import version

import numpy as np
import pandas as pd


def load_expression(expression_file, index_col=None):
    """Read numeric data without silently renaming duplicate gene identifiers."""
    with open(expression_file, encoding="utf-8-sig", newline="") as handle:
        header = next(csv.reader(handle, delimiter="\t"), [])
    if index_col is not None:
        if not 0 <= index_col < len(header):
            raise ValueError("index_col must identify a column in the input file")
        header = header[:index_col] + header[index_col + 1:]
    if not header or any(not name.strip() for name in header):
        raise ValueError("Gene names must be nonempty; use --index-col 0 for row IDs")
    if len(header) != len(set(header)):
        raise ValueError("Duplicate gene names: resolve identifiers before inference")
    frame = pd.read_csv(expression_file, sep="\t", index_col=index_col)
    if frame.shape[0] < 2 or frame.shape[1] < 2:
        raise ValueError("At least two observations and two genes are required")
    try:
        frame = frame.apply(pd.to_numeric, errors="raise")
    except (TypeError, ValueError) as exc:
        raise ValueError("Expression must be numeric; use --index-col 0 for row IDs") from exc
    if not np.isfinite(frame.to_numpy()).all():
        raise ValueError("Expression contains missing or nonfinite values")
    return frame


def infer_network(expression_data, tf_names, seed, limit, workers):
    """Use a fresh bounded client; keep legacy Dask configuration explicit."""
    import dask

    # PyPI Arboreto 0.1.6 creates an empty metadata graph. This tested Dask
    # release still offers the legacy backend that accepts that graph.
    if version("dask") == "2024.7.1":
        dask.config.set({"dataframe.query-planning": False})
    from arboreto.algo import grnboost2
    from distributed import Client, LocalCluster

    with LocalCluster(
        n_workers=workers, threads_per_worker=1, dashboard_address=None
    ) as cluster, Client(cluster) as client:
        return grnboost2(
            expression_data=expression_data, tf_names=tf_names, seed=seed,
            limit=limit, client_or_address=client, verbose=True,
        )


def run_grn_inference(expression_file, output_file, tf_file=None, seed=777,
                      limit=None, index_col=None, workers=1):
    """Validate inputs, infer candidates, and write a headerless adjacency TSV."""
    if limit is not None and limit <= 0:
        raise ValueError("limit must be a positive integer")
    if workers <= 0:
        raise ValueError("workers must be a positive integer")
    expression_data = load_expression(expression_file, index_col=index_col)
    print(f"[OK] Loaded {expression_data.shape[0]} observations x {expression_data.shape[1]} genes")
    tf_names = "all"
    if tf_file:
        with open(tf_file, encoding="utf-8") as handle:
            requested = list(dict.fromkeys(line.strip() for line in handle if line.strip()))
        tf_names = [name for name in requested if name in expression_data.columns]
        if not tf_names:
            raise ValueError("TF file has no names matching the expression genes")
        print(f"[OK] Matched {len(tf_names)} of {len(requested)} TF names")
    else:
        print("[OK] All genes are candidate regulators; the TF column is not restricted to known TFs")
    network = infer_network(expression_data, tf_names, seed, limit, workers)
    if network.empty:
        raise RuntimeError("Inference returned no links; inspect worker warnings and input variation")
    if not np.isfinite(network["importance"]).all():
        raise RuntimeError("Inference returned nonfinite importance scores")
    network.to_csv(output_file, sep="\t", index=False, header=False)
    print(f"[OK] Saved {len(network)} candidate links to {output_file}")
    print(network.head(10).to_string(index=False))
    return network


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("expression_file", help="Numeric TSV: observations in rows, genes in columns")
    parser.add_argument("output_file", help="Headerless TF, target, importance TSV")
    parser.add_argument("--tf-file", help="TF names, one per line")
    parser.add_argument("--seed", type=int, default=777, help="Regressor seed (default: 777)")
    parser.add_argument("--limit", type=int, help="Return the top N links globally; positive integer")
    parser.add_argument("--index-col", type=int, help="Zero-based row identifier column, typically 0")
    parser.add_argument("--workers", type=int, default=1, help="Local worker processes (default: 1)")
    args = parser.parse_args()
    run_grn_inference(**vars(args))


if __name__ == "__main__":
    main()
