#!/usr/bin/env python3
"""
Batch molecular filtering using the medchem library.

Usage:
    uv run python filter_molecules.py input.csv --rules rule_of_five,rule_of_cns --pains --output filtered.csv
    uv run python filter_molecules.py input.sdf --rules rule_of_veber --nibr --complexity 99 --output results.csv
    uv run python filter_molecules.py smiles.txt --query 'MATCHRULE("rule_of_five") AND NOT HASALERT("pains")' --output clean.csv
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import pandas as pd
    import datamol as dm
    import medchem as mc
    from rdkit import Chem
    from tqdm import tqdm
except ImportError as e:
    print(f"Error: Missing required package: {e}")
    print("Install dependencies: uv pip install medchem datamol pandas tqdm")
    sys.exit(1)


def load_molecules(
    input_file: Path, smiles_column: str = "smiles"
) -> Tuple[pd.DataFrame, List[Chem.Mol]]:
    """Load molecules from CSV/TSV, SDF, or plain SMILES text files."""
    suffix = input_file.suffix.lower()

    if suffix == ".sdf":
        print(f"Loading SDF file: {input_file}")
        supplier = Chem.SDMolSupplier(str(input_file))
        mols = [mol for mol in supplier if mol is not None]
        data = []
        for mol in mols:
            props = mol.GetPropsAsDict()
            props["smiles"] = Chem.MolToSmiles(mol)
            data.append(props)
        df = pd.DataFrame(data)

    elif suffix in [".csv", ".tsv"]:
        print(f"Loading CSV/TSV file: {input_file}")
        sep = "\t" if suffix == ".tsv" else ","
        df = pd.read_csv(input_file, sep=sep)
        if smiles_column not in df.columns:
            print(f"Error: Column '{smiles_column}' not found")
            print(f"Available columns: {', '.join(df.columns)}")
            sys.exit(1)
        print("Converting SMILES to molecules...")
        mols = [dm.to_mol(smi) for smi in tqdm(df[smiles_column], desc="Parsing")]

    elif suffix == ".txt":
        print(f"Loading text file: {input_file}")
        with open(input_file) as f:
            smiles_list = [line.strip() for line in f if line.strip()]
        df = pd.DataFrame({"smiles": smiles_list})
        print("Converting SMILES to molecules...")
        mols = [dm.to_mol(smi) for smi in tqdm(smiles_list, desc="Parsing")]

    else:
        print(f"Error: Unsupported file format: {suffix}")
        print("Supported formats: .csv, .tsv, .sdf, .txt")
        sys.exit(1)

    valid_indices = [i for i, mol in enumerate(mols) if mol is not None]
    if len(valid_indices) < len(mols):
        n_invalid = len(mols) - len(valid_indices)
        print(f"Warning: {n_invalid} invalid molecules removed")
        df = df.iloc[valid_indices].reset_index(drop=True)
        mols = [mols[i] for i in valid_indices]

    print(f"Loaded {len(mols)} valid molecules")
    return df, mols


def apply_rule_filters(
    mols: List[Chem.Mol], rules: List[str], n_jobs: int
) -> pd.DataFrame:
    """Apply medicinal chemistry rule filters. Returns rule result columns."""
    print(f"\nApplying rule filters: {', '.join(rules)}")
    rfilter = mc.rules.RuleFilters(rule_list=rules)
    results = rfilter(mols=mols, n_jobs=n_jobs, progress=True)
    return results.drop(columns=["mol"], errors="ignore")


def apply_common_alerts(mols: List[Chem.Mol], n_jobs: int) -> pd.DataFrame:
    """Apply ChEMBL-derived common structural alerts."""
    print("\nApplying common structural alerts...")
    alert_filter = mc.structural.CommonAlertsFilters()
    results = alert_filter(mols=mols, n_jobs=n_jobs, progress=True)
    return results.drop(columns=["mol"], errors="ignore").rename(
        columns={"pass_filter": "passes_common_alerts", "status": "common_alert_status"}
    )


def apply_nibr(mols: List[Chem.Mol], n_jobs: int) -> pd.DataFrame:
    """Apply NIBR screening-deck filters."""
    print("\nApplying NIBR filters...")
    nibr_filter = mc.structural.NIBRFilters()
    results = nibr_filter(mols=mols, n_jobs=n_jobs, progress=True)
    return results.drop(columns=["mol"], errors="ignore").rename(
        columns={"pass_filter": "passes_nibr", "status": "nibr_status"}
    )


def apply_alert_catalog(
    mols: List[Chem.Mol], alerts: List[str], n_jobs: int
) -> pd.DataFrame:
    """Apply named alert catalogs (pains, brenk, etc.)."""
    print(f"\nApplying alert catalogs: {', '.join(alerts)}")
    for alert in alerts:
        passes = mc.functional.alert_filter(
            mols=mols, alerts=[alert], n_jobs=n_jobs, progress=True
        )
        yield alert, passes


def apply_lilly(mols: List[Chem.Mol], max_demerits: int, n_jobs: int) -> pd.DataFrame:
    """Apply Lilly demerit filter (requires lilly-medchem-rules)."""
    print(f"\nApplying Lilly demerits filter (max={max_demerits})...")
    try:
        passes = mc.functional.lilly_demerit_filter(
            mols=mols, max_demerits=max_demerits, n_jobs=n_jobs, progress=True
        )
    except ImportError as e:
        print(f"Warning: Lilly filter unavailable: {e}")
        print("Install with: mamba install -c conda-forge lilly-medchem-rules")
        return pd.DataFrame({"passes_lilly": [None] * len(mols)})
    return pd.DataFrame({"passes_lilly": passes})


def apply_complexity(
    mols: List[Chem.Mol], limit: str, method: str, n_jobs: int
) -> pd.DataFrame:
    """Filter by complexity percentile threshold."""
    print(f"\nApplying complexity filter (metric={method}, limit={limit} percentile)...")
    passes = mc.functional.complexity_filter(
        mols=mols,
        complexity_metric=method,
        limit=limit,
        n_jobs=n_jobs,
        progress=True,
    )
    return pd.DataFrame({f"passes_complexity_{method}": passes})


def apply_query(mols: List[Chem.Mol], query: str, n_jobs: int) -> pd.DataFrame:
    """Apply medchem query language filter."""
    print(f"\nApplying query: {query}")
    qf = mc.query.QueryFilter(query)
    passes = qf(mols=mols, n_jobs=n_jobs, progress=True)
    return pd.DataFrame({"passes_query": passes})


def apply_groups(mols: List[Chem.Mol], groups: List[str]) -> pd.DataFrame:
    """Detect chemical group matches."""
    print(f"\nDetecting chemical groups: {', '.join(groups)}")
    detector = mc.groups.ChemicalGroup(groups=groups)
    return pd.DataFrame(
        {f"has_{g}": [detector.has_match(mol) for mol in mols] for g in groups}
    )


def generate_summary(df: pd.DataFrame, output_file: Path) -> None:
    """Write a text summary of filtering results."""
    summary_file = output_file.parent / f"{output_file.stem}_summary.txt"
    pass_cols = [c for c in df.columns if c.startswith("passes_") or c == "pass_all"]

    with open(summary_file, "w") as f:
        f.write("=" * 80 + "\nMEDCHEM FILTERING SUMMARY\n" + "=" * 80 + "\n\n")
        f.write(f"Total molecules processed: {len(df)}\n\n")

        for col in pass_cols:
            if col in df.columns and df[col].dtype == bool:
                n_pass = df[col].sum()
                pct = 100 * n_pass / len(df) if len(df) else 0
                f.write(f"  {col}: {n_pass} passed ({pct:.1f}%)\n")

        if pass_cols:
            bool_cols = [c for c in pass_cols if c in df.columns and df[c].dtype == bool]
            if bool_cols:
                df["_passes_all"] = df[bool_cols].all(axis=1)
                n_all = df["_passes_all"].sum()
                pct = 100 * n_all / len(df) if len(df) else 0
                f.write(f"\n  All filters passed: {n_all} ({pct:.1f}%)\n")

        f.write("\n" + "=" * 80 + "\n")

    print(f"\nSummary report saved to: {summary_file}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch molecular filtering using medchem",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("input", type=Path, help="Input file (CSV, TSV, SDF, or TXT)")
    parser.add_argument("--output", "-o", type=Path, required=True, help="Output CSV file")
    parser.add_argument("--smiles-column", default="smiles", help="SMILES column name (default: smiles)")

    parser.add_argument("--rules", help="Comma-separated rules (e.g. rule_of_five,rule_of_cns)")
    parser.add_argument("--query", help='Medchem query string (e.g. MATCHRULE("rule_of_five") AND NOT HASALERT("pains"))')
    parser.add_argument("--common-alerts", action="store_true", help="Apply common structural alerts")
    parser.add_argument("--nibr", action="store_true", help="Apply NIBR filters")
    parser.add_argument("--lilly", action="store_true", help="Apply Lilly demerits (requires lilly-medchem-rules)")
    parser.add_argument("--lilly-max", type=int, default=160, help="Max Lilly demerits (default: 160)")
    parser.add_argument(
        "--alerts",
        help="Comma-separated alert catalogs (e.g. pains,brenk). Shorthand for --pains when set to pains",
    )
    parser.add_argument("--pains", action="store_true", help="Apply PAINS filter (alias for --alerts pains)")

    parser.add_argument(
        "--complexity",
        help="Complexity percentile limit (e.g. 99 keeps below 99th percentile on ZINC-15)",
    )
    parser.add_argument(
        "--complexity-method",
        default="bertz",
        choices=["bertz", "sas", "qed", "clogp", "whitlock", "barone", "smcm", "twc"],
        help="Complexity metric (default: bertz)",
    )
    parser.add_argument("--groups", help="Comma-separated chemical groups to detect")
    parser.add_argument("--n-jobs", type=int, default=-1, help="Parallel jobs (-1 = all cores)")
    parser.add_argument("--no-summary", action="store_true", help="Skip summary report")
    parser.add_argument("--filter-output", action="store_true", help="Only output molecules passing all filters")

    args = parser.parse_args()

    if not any([args.rules, args.query, args.common_alerts, args.nibr, args.lilly,
                args.pains, args.alerts, args.complexity, args.groups]):
        print("Error: Specify at least one filter (--rules, --query, --pains, --nibr, etc.)")
        sys.exit(1)

    df, mols = load_molecules(args.input, args.smiles_column)
    result_parts = [df.reset_index(drop=True)]

    if args.rules:
        rule_list = [r.strip() for r in args.rules.split(",")]
        unknown = set(rule_list) - set(mc.rules.RuleFilters.list_available_rules_names())
        if unknown:
            print(f"Warning: Unknown rules (will error at runtime): {', '.join(sorted(unknown))}")
        result_parts.append(apply_rule_filters(mols, rule_list, args.n_jobs))

    if args.query:
        result_parts.append(apply_query(mols, args.query, args.n_jobs))

    if args.common_alerts:
        result_parts.append(apply_common_alerts(mols, args.n_jobs))

    if args.nibr:
        result_parts.append(apply_nibr(mols, args.n_jobs))

    if args.lilly:
        result_parts.append(apply_lilly(mols, args.lilly_max, args.n_jobs))

    alert_list = []
    if args.pains:
        alert_list.append("pains")
    if args.alerts:
        alert_list.extend(a.strip() for a in args.alerts.split(","))
    for alert in dict.fromkeys(alert_list):
        col_name = f"passes_{alert}"
        _, passes = next(apply_alert_catalog(mols, [alert], args.n_jobs))
        result_parts.append(pd.DataFrame({col_name: passes}))

    if args.complexity:
        result_parts.append(
            apply_complexity(mols, args.complexity, args.complexity_method, args.n_jobs)
        )

    if args.groups:
        group_list = [g.strip() for g in args.groups.split(",")]
        result_parts.append(apply_groups(mols, group_list))

    df_final = pd.concat(result_parts, axis=1)

    if args.filter_output:
        pass_cols = [c for c in df_final.columns if c.startswith("passes_") or c == "pass_all"]
        bool_cols = [c for c in pass_cols if c in df_final.columns and df_final[c].dtype == bool]
        if bool_cols:
            mask = df_final[bool_cols].all(axis=1)
            df_final = df_final[mask]
            print(f"\nFiltered to {len(df_final)} molecules passing all filters")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    df_final.to_csv(args.output, index=False)
    print(f"\nResults saved to: {args.output}")

    if not args.no_summary:
        generate_summary(df_final, args.output)

    print("\nDone!")


if __name__ == "__main__":
    main()
