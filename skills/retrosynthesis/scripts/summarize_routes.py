#!/usr/bin/env python3
"""Flatten AiZynthFinder routes into a table and run RDKit sanity checks.

Accepts either output of `aizynthcli`:
  * trees.json        -- single-target run, a JSON list of route dictionaries
  * output.json(.gz)  -- batch run, a pandas "table" JSON with one row per target

Writes one CSV row per route with the route's step count, longest linear
sequence, leaves, leaves missing from stock, AiZynthFinder scores, and
per-step checks: every SMILES parses, no product element is missing from
its reactants, and stereocenters defined in a product but in none of its
reactants are flagged for review. Needs RDKit only; AiZynthFinder itself is
not imported.

Example:
    python summarize_routes.py output.json.gz routes.csv
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import sys
from collections import Counter
from pathlib import Path

from rdkit import Chem, RDLogger

ROUTE_FIELDS = [
    "target", "route", "solved", "steps", "longest_linear_steps", "n_leaves", "leaves_in_stock",
    "leaves_not_in_stock", "state_score", "scores", "unparsable_smiles", "element_mismatch_steps",
    "stereo_set_steps", "policies", "classifications",
]


def load_routes(path: Path):
    """Return a list of (target_smiles, [route_dict, ...]) from an aizynthcli output file."""
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        routes = data
        target = routes[0]["smiles"] if routes else ""
        return [(target, routes)]
    if isinstance(data, dict) and "data" in data:
        targets = []
        for row in data["data"]:
            targets.append((row.get("target", ""), row.get("trees") or []))
        return targets
    raise ValueError(f"{path}: not a trees.json list or an aizynthcli table output")


def _mol(smiles):
    return Chem.MolFromSmiles(smiles) if smiles else None


def _heavy_elements(mol):
    return Counter(atom.GetSymbol() for atom in mol.GetAtoms() if atom.GetAtomicNum() > 1)


def _defined_centers(mol):
    return sum(1 for info in Chem.FindPotentialStereo(mol)
               if info.type == Chem.StereoType.Atom_Tetrahedral
               and info.specified == Chem.StereoSpecified.Specified)


def walk(node, depth=0):
    """Yield (product_node, reaction_node, depth) for every reaction in a route dict."""
    for reaction in node.get("children", []):
        yield node, reaction, depth
        for child in reaction.get("children", []):
            yield from walk(child, depth + 1)


def leaves(node):
    children = [c for reaction in node.get("children", []) for c in reaction.get("children", [])]
    if not children:
        yield node
    for child in children:
        yield from leaves(child)


def check_route(route):
    """Summarize one route dictionary; returns a dict of ROUTE_FIELDS minus target/route."""
    unparsable, mismatch, stereo_set = set(), [], []
    policies, classes = Counter(), Counter()
    steps, longest = 0, 0
    for product, reaction, depth in walk(route):
        steps += 1
        longest = max(longest, depth + 1)
        meta = reaction.get("metadata", {})
        if meta.get("policy_name"):
            policies[meta["policy_name"]] += 1
        if meta.get("classification"):
            classes[meta["classification"]] += 1
        product_mol = _mol(product["smiles"])
        reactant_mols = []
        for child in reaction.get("children", []):
            mol = _mol(child["smiles"])
            if mol is None:
                unparsable.add(child["smiles"])
            reactant_mols.append(mol)
        if product_mol is None:
            unparsable.add(product["smiles"])
            continue
        if any(mol is None for mol in reactant_mols):
            continue
        supplied = Counter()
        for mol in reactant_mols:
            supplied.update(_heavy_elements(mol))
        missing = {el: n for el, n in _heavy_elements(product_mol).items() if supplied[el] < n}
        if missing:
            mismatch.append(f"{steps}:{product['smiles']}")
        if _defined_centers(product_mol) > sum(_defined_centers(mol) for mol in reactant_mols):
            stereo_set.append(f"{steps}:{product['smiles']}")
    leaf_nodes = list(leaves(route))
    not_in_stock = [leaf["smiles"] for leaf in leaf_nodes if not leaf.get("in_stock")]
    scores = route.get("scores", {})
    return {
        "solved": not not_in_stock,
        "steps": steps,
        "longest_linear_steps": longest,
        "n_leaves": len(leaf_nodes),
        "leaves_in_stock": ".".join(leaf["smiles"] for leaf in leaf_nodes if leaf.get("in_stock")),
        "leaves_not_in_stock": ".".join(not_in_stock),
        "state_score": scores.get("state score", ""),
        "scores": json.dumps(scores, sort_keys=True) if scores else "",
        "unparsable_smiles": ".".join(sorted(unparsable)),
        "element_mismatch_steps": "|".join(mismatch),
        "stereo_set_steps": "|".join(stereo_set),
        "policies": json.dumps(dict(policies), sort_keys=True) if policies else "",
        "classifications": json.dumps(dict(classes), sort_keys=True) if classes else "",
    }


def summarize(path: Path):
    rows = []
    for target, routes in load_routes(path):
        for index, route in enumerate(routes):
            rows.append({"target": target, "route": index, **check_route(route)})
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("input", type=Path, help="trees.json, output.json, or output.json.gz from aizynthcli")
    parser.add_argument("output", type=Path, help="CSV file with one row per route")
    args = parser.parse_args(argv)
    if not args.input.is_file():
        parser.error(f"input file not found: {args.input}")

    RDLogger.DisableLog("rdApp.*")
    rows = summarize(args.input)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=ROUTE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    targets = {row["target"] for row in rows}
    solved = {row["target"] for row in rows if row["solved"]}
    flagged = sum(1 for row in rows if row["element_mismatch_steps"] or row["unparsable_smiles"])
    print(f"[OK] {len(rows)} routes for {len(targets)} targets written to {args.output}")
    print(f"-> targets with at least one solved route: {len(solved)}/{len(targets)}")
    print(f"-> routes with stereocenters set in a step: {sum(1 for row in rows if row['stereo_set_steps'])}")
    if flagged:
        print(f"[FAIL] {flagged} routes have unparsable SMILES or element mismatches; inspect before use")
    return 0


if __name__ == "__main__":
    sys.exit(main())
