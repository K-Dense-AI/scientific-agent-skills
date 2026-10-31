"""Local, eager pandas queries for a pinned PrimeKG CSV (no network requests).

PrimeKG serializes reverse rows; adjacency is undirected and is not causality.
IDs are opaque strings qualified by type and source. Each logical adjacency
retains all original CSV rows in ``edge_rows`` for orientation/provenance review.
"""

import os
from typing import Dict, List, Optional, Union

import pandas as pd

DATA_PATH = os.environ.get("PRIMEKG_DATA", "data/PrimeKG/kg.csv")
NODE_FIELDS = ("id", "type", "name", "source")
REQUIRED_COLUMNS = {"relation", "display_relation"} | {
    f"{side}_{field}" for side in ("x", "y") for field in NODE_FIELDS
}


def _load_kg():
    """Read the entire CSV; allow several GB of RAM for a full PrimeKG release."""
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(
            f"PrimeKG data not found at {DATA_PATH}. Download kg.csv from "
            "https://doi.org/10.7910/DVN/IXA7BM and set PRIMEKG_DATA to its path."
        )
    # Prevent numeric coercion, leading-zero loss, and literal 'NA' -> missing.
    kg = pd.read_csv(DATA_PATH, dtype=str, keep_default_na=False)
    missing = REQUIRED_COLUMNS - set(kg.columns)
    if missing:
        raise ValueError(f"Not a PrimeKG edge CSV; missing columns: {sorted(missing)}")
    for column in REQUIRED_COLUMNS:
        if kg[column].str.strip().eq("").any():
            raise ValueError(f"PrimeKG column {column!r} contains an empty value")
    indexes = {"x_index", "y_index"} & set(kg.columns)
    if indexes and len(indexes) != 2:
        raise ValueError("PrimeKG indexes must include both x_index and y_index")
    if indexes:
        nodes = _nodes(kg)
        if nodes["index"].str.strip().eq("").any():
            raise ValueError("PrimeKG contains an empty release index")
        identity = nodes[["id", "type", "source", "index"]].drop_duplicates()
        if identity.duplicated(["id", "type", "source"]).any():
            raise ValueError("Node ID maps to multiple release indexes; inspect the CSV")
        if identity.duplicated("index").any():
            raise ValueError("Release index maps to multiple node identities; inspect the CSV")
    return kg


def _nodes(kg):
    tables = []
    for side in ("x", "y"):
        fields = list(NODE_FIELDS)
        if f"{side}_index" in kg.columns:
            fields.append("index")
        tables.append(kg[[f"{side}_{field}" for field in fields]].rename(
            columns={f"{side}_{field}": field for field in fields}
        ))
    return pd.concat(tables, ignore_index=True).drop_duplicates()


def _search(kg, query, node_type=None):
    nodes = _nodes(kg)
    mask = nodes["name"].str.contains(query, case=False, regex=False, na=False)
    if node_type is not None:
        mask &= nodes["type"].eq(node_type)
    return nodes[mask].sort_values(["name", "type", "source", "id"])


def search_nodes(name_query: str, node_type: Optional[str] = None,
                 *, limit: Optional[int] = 20) -> List[Dict]:
    """Literal case-insensitive name search; use limit=None for all matches."""
    if limit is not None and (type(limit) is not int or limit < 1):
        raise ValueError("limit must be a positive integer or None")
    matches = _search(_load_kg(), name_query, node_type)
    return (matches if limit is None else matches.head(limit)).to_dict("records")


def _key(node):
    return (str(node["id"]), node["type"], node["source"])


def _resolve(kg, node_id, node_type=None, node_source=None):
    nodes = _nodes(kg)
    mask = nodes["id"].eq(str(node_id))
    if node_type is not None:
        mask &= nodes["type"].eq(node_type)
    if node_source is not None:
        mask &= nodes["source"].eq(node_source)
    matches = nodes[mask]
    keys = {_key(row) for row in matches.to_dict("records")}
    if len(keys) > 1:
        raise ValueError("Ambiguous node ID; specify node_type and node_source")
    # A release index must not map a typed/source ID to multiple distinct nodes.
    if "index" in matches and matches["index"].nunique() > 1:
        raise ValueError("Node ID maps to multiple release indexes; inspect the CSV")
    return next(iter(keys), None)


def _side_mask(kg, side, key):
    return (kg[f"{side}_id"].eq(key[0]) & kg[f"{side}_type"].eq(key[1])
            & kg[f"{side}_source"].eq(key[2]))


def _neighbors(kg, key, relation_type=None):
    grouped = {}
    for side, other in (("x", "y"), ("y", "x")):
        mask = _side_mask(kg, side, key)
        if relation_type is not None:
            mask &= kg["relation"].eq(relation_type)
        for row in kg[mask].drop_duplicates().to_dict("records"):
            neighbor = {field: row[f"{other}_{field}"] for field in NODE_FIELDS}
            # Names remain in the key so inconsistent labels are visible.
            group_key = (*_key(neighbor), neighbor["name"], row["relation"], row["display_relation"])
            if group_key not in grouped:
                grouped[group_key] = {
                    "relation": row["relation"], "display_relation": row["display_relation"],
                    **{f"neighbor_{field}": value for field, value in neighbor.items()},
                    "edge_rows": [],
                }
                if f"{other}_index" in row:
                    grouped[group_key]["neighbor_index"] = row[f"{other}_index"]
            # Preserve stored x/y orientation, indexes and any extra evidence columns.
            if row not in grouped[group_key]["edge_rows"]:
                grouped[group_key]["edge_rows"].append(row)
    return list(grouped.values())


def get_neighbors(node_id: Union[str, int], relation_type: Optional[str] = None,
                  *, node_type: Optional[str] = None,
                  node_source: Optional[str] = None) -> List[Dict]:
    """Undirected adjacency, deduplicating reverse rows but preserving edge_rows.

    Bare IDs work only when unambiguous in this file. ``x_source``/``y_source``
    describe node namespaces, not clinical evidence or the source of an edge.
    """
    kg = _load_kg()
    key = _resolve(kg, node_id, node_type, node_source)
    return [] if key is None else _neighbors(kg, key, relation_type)


def _neighbor_key(neighbor):
    return tuple(neighbor[f"neighbor_{field}"] for field in ("id", "type", "source"))


def _path_edge(neighbor, start, end):
    return {**neighbor["edge_rows"][0], "edge_rows": neighbor["edge_rows"],
            "traversal_from": dict(zip(("id", "type", "source"), start)),
            "traversal_to": dict(zip(("id", "type", "source"), end))}


def find_paths(start_node_id: str, end_node_id: str, max_depth: int = 2, *,
               start_node_type: Optional[str] = None, start_node_source: Optional[str] = None,
               end_node_type: Optional[str] = None, end_node_source: Optional[str] = None,
               max_paths: int = 1000) -> List[List[Dict]]:
    """Enumerate simple undirected one/two-hop relation paths, preserving rows.

    Depths other than 1 or 2 are rejected. Exceeding max_paths raises instead of
    silently returning an incomplete result. Paths are associations, not evidence
    of a drug mechanism, efficacy, or a directed causal chain.
    """
    if type(max_depth) is not int or max_depth not in (1, 2):
        raise ValueError("max_depth must be 1 or 2")
    if type(max_paths) is not int or max_paths < 1:
        raise ValueError("max_paths must be a positive integer")
    kg = _load_kg()
    start = _resolve(kg, start_node_id, start_node_type, start_node_source)
    end = _resolve(kg, end_node_id, end_node_type, end_node_source)
    if start is None or end is None or start == end:
        return []
    start_neighbors = _neighbors(kg, start)
    end_neighbors = _neighbors(kg, end) if max_depth == 2 else []
    by_intermediate = {}
    for neighbor in end_neighbors:
        by_intermediate.setdefault(_neighbor_key(neighbor), []).append(neighbor)
    paths = []
    for first in start_neighbors:
        middle = _neighbor_key(first)
        if middle == end:
            paths.append([_path_edge(first, start, end)])
        elif max_depth == 2 and middle != start:
            for second in by_intermediate.get(middle, []):
                paths.append([_path_edge(first, start, middle), _path_edge(second, middle, end)])
                if len(paths) > max_paths:
                    raise ValueError("Path count exceeds max_paths; narrow the input subgraph")
        if len(paths) > max_paths:
            raise ValueError("Path count exceeds max_paths; narrow the input subgraph")
    return paths


def get_disease_context(disease_name: str) -> Dict:
    """Resolve an exact name or unique substring; report ambiguity explicitly."""
    kg = _load_kg()
    matches = _search(kg, disease_name, "disease")
    exact = matches[matches["name"].str.casefold().eq(disease_name.casefold())]
    if not exact.empty:
        matches = exact
    if matches.empty:
        return {"error": "Disease not found"}
    if len(matches) != 1:
        return {"error": "Ambiguous disease name", "candidates": matches.to_dict("records")}
    disease = matches.iloc[0].to_dict()
    key = _resolve(kg, disease["id"], disease["type"], disease["source"])
    neighbors = _neighbors(kg, key)
    drugs = [n for n in neighbors if n["neighbor_type"] == "drug"]
    return {
        "disease_info": disease,
        "associated_genes": [n for n in neighbors if n["neighbor_type"] == "gene/protein"],
        "associated_drugs": drugs,
        "drug_relations": {r: [n for n in drugs if n["relation"] == r]
                           for r in ("indication", "contraindication", "off-label use")},
        "phenotypes": [n for n in neighbors if n["neighbor_type"] == "effect/phenotype"],
        "related_diseases": [n for n in neighbors if n["neighbor_type"] == "disease"],
    }
