#!/usr/bin/env python3
"""Flatten AiZynthFinder routes into a table and run RDKit sanity checks.

Accepts either output of `aizynthcli`:
  * trees.json        -- single-target run, a JSON list of route dictionaries
  * output.json(.gz)  -- batch run, a pandas "table" JSON with one row per target

Writes one CSV row per route with the route's step count, longest linear
sequence, leaves, leaves missing from stock, AiZynthFinder scores, and
per-step checks: every molecule SMILES parses, no product element is missing
from its reactants, and steps whose product has more defined tetrahedral
centres than its reactants are flagged for review. That last check is a net
count, so a step that destroys one centre while creating another is a false
negative; it finds the common case, not every case. Needs RDKit only;
AiZynthFinder itself is not imported.

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

#: Placeholder for a molecule node whose `smiles` is missing or empty.
EMPTY_SMILES = "<empty>"

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
        target = routes[0].get("smiles", "") if routes else ""
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


def molecules(node):
    """Yield every molecule node in a route, including a childless root."""
    yield node
    for reaction in node.get("children", []):
        for child in reaction.get("children", []):
            yield from molecules(child)


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
    # Every molecule node, so a childless root or an in-stock leaf cannot carry
    # an unparsable SMILES past the reaction loop below.
    for node in molecules(route):
        smiles = node.get("smiles", "")
        if _mol(smiles) is None:
            # A missing or empty SMILES is a failure too, and it has to reach the
            # report as visible text: an empty string would join to "" and make
            # the column look clean.
            unparsable.add(smiles if smiles else EMPTY_SMILES)
    for product, reaction, depth in walk(route):
        steps += 1
        longest = max(longest, depth + 1)
        meta = reaction.get("metadata", {})
        if meta.get("policy_name"):
            policies[meta["policy_name"]] += 1
        if meta.get("classification"):
            classes[meta["classification"]] += 1
        product_mol = _mol(product.get("smiles", ""))
        reactant_mols = [_mol(child.get("smiles", "")) for child in reaction.get("children", [])]
        if product_mol is None or any(mol is None for mol in reactant_mols):
            continue
        supplied = Counter()
        for mol in reactant_mols:
            supplied.update(_heavy_elements(mol))
        missing = {el: n for el, n in _heavy_elements(product_mol).items() if supplied[el] < n}
        if missing:
            mismatch.append(f"{steps}:{product.get('smiles', '')}")
        if _defined_centers(product_mol) > sum(_defined_centers(mol) for mol in reactant_mols):
            stereo_set.append(f"{steps}:{product.get('smiles', '')}")
    leaf_nodes = list(leaves(route))
    not_in_stock = [leaf.get("smiles", "") for leaf in leaf_nodes if not leaf.get("in_stock")]
    scores = route.get("scores", {})
    return {
        "solved": not not_in_stock,
        "steps": steps,
        "longest_linear_steps": longest,
        "n_leaves": len(leaf_nodes),
        "leaves_in_stock": ".".join(leaf.get("smiles", "") for leaf in leaf_nodes if leaf.get("in_stock")),
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
    """Return (rows, targets): one row per route, and every target in the file."""
    rows, targets = [], []
    for target, routes in load_routes(path):
        targets.append(target)
        for index, route in enumerate(routes):
            rows.append({"target": target, "route": index, **check_route(route)})
    return rows, targets


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("input", type=Path, help="trees.json, output.json, or output.json.gz from aizynthcli")
    parser.add_argument("output", type=Path, help="CSV file with one row per route")
    parser.add_argument("--strict", action="store_true",
                        help="exit nonzero when any route has an unparsable SMILES or a lost element")
    args = parser.parse_args(argv)
    if not args.input.is_file():
        parser.error(f"input file not found: {args.input}")

    RDLogger.DisableLog("rdApp.*")
    rows, targets = summarize(args.input)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=ROUTE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    # Targets come from the file, not from the rows: a target the search left
    # without any route has no row and must still count in the denominator.
    unique_targets = dict.fromkeys(targets)
    solved = {row["target"] for row in rows if row["solved"]}
    routeless = [target for target in unique_targets if target not in {row["target"] for row in rows}]
    flagged = sum(1 for row in rows if row["element_mismatch_steps"] or row["unparsable_smiles"])
    print(f"[OK] {len(rows)} routes for {len(unique_targets)} targets written to {args.output}")
    print(f"-> targets with at least one solved route: {len(solved)}/{len(unique_targets)}")
    if routeless:
        print(f"-> targets with no route at all: {len(routeless)}")
    print(f"-> routes with a step that sets a stereocenter: {sum(1 for row in rows if row['stereo_set_steps'])}")
    if flagged:
        print(f"[FAIL] {flagged} routes have unparsable SMILES or a lost element; inspect before use")
        if args.strict:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
