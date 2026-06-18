#!/usr/bin/env python3
"""
tree.py — persistent hypothesis-tree state manager for Arbor-style
Hypothesis Tree Refinement (HTR).

The hypothesis tree is the durable research state for an Autonomous
Optimization (AO) run. This script owns the *mechanical* parts of that state
— creating nodes, writing back evidence, propagating insights up the tree,
pruning falsified branches, recording the held-out merge gate, and rendering
an "Observe" projection — so the coordinator (you, the model) can spend its
judgment on what the evidence *means* rather than on bookkeeping.

Division of labor:
  - This script keeps the state consistent and auditable. It never decides
    which hypothesis to try or whether one is good.
  - The coordinator reads the projection (`observe`), forms hypotheses,
    interprets executor reports, and calls the mutating commands to record
    those decisions.

State lives in `.arbor/` under the run directory (default: current dir):
  .arbor/tree.json   — the hypothesis tree (nodes, edges, evidence, insights)
  .arbor/run.json    — run-level config: objective, evaluators, budget, M_best

Node fields mirror the paper's research unit  n = <h, iota, mu>:
  hypothesis  (h)    — the falsifiable claim this node tests
  insight     (iota) — distilled, reusable lesson (filled after execution)
  metadata    (mu)   — status, dev_score, test_score, result, branch_ref, depth

Run `python tree.py --help` or `python tree.py <command> --help`.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# ----------------------------------------------------------------------------
# Storage helpers
# ----------------------------------------------------------------------------

VALID_STATUS = {"pending", "running", "executed", "merged", "pruned", "root"}


def _dir(run_dir):
    return Path(run_dir) / ".arbor"


def _tree_path(run_dir):
    return _dir(run_dir) / "tree.json"


def _run_path(run_dir):
    return _dir(run_dir) / "run.json"


def _load(path, what):
    if not path.exists():
        sys.exit(
            f"error: no {what} found at {path}. Run `tree.py init` first "
            f"(from the run directory, or pass --run-dir)."
        )
    with open(path) as f:
        return json.load(f)


def _save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(path)


def _load_tree(run_dir):
    return _load(_tree_path(run_dir), "hypothesis tree")


def _load_run(run_dir):
    return _load(_run_path(run_dir), "run config")


def _next_id(tree):
    n = tree.get("_counter", 0) + 1
    tree["_counter"] = n
    return f"n{n}"


def _node(tree, node_id):
    node = tree["nodes"].get(node_id)
    if node is None:
        sys.exit(f"error: no node with id '{node_id}'. Run `tree.py status` to list nodes.")
    return node


def _children(tree, node_id):
    return [nid for nid, n in tree["nodes"].items() if n.get("parent") == node_id]


def _ancestors(tree, node_id):
    """Path from node up to (and including) root, nearest first."""
    path = []
    cur = tree["nodes"][node_id].get("parent")
    while cur is not None:
        path.append(cur)
        cur = tree["nodes"][cur].get("parent")
    return path


def _depth(tree, node_id):
    return len(_ancestors(tree, node_id))


def _stamp(node):
    node["updated_at"] = int(time.time())


# ----------------------------------------------------------------------------
# Commands
# ----------------------------------------------------------------------------


def cmd_init(args):
    d = _dir(args.run_dir)
    if _tree_path(args.run_dir).exists() and not args.force:
        sys.exit(
            f"error: a tree already exists at {_tree_path(args.run_dir)}. "
            f"Use --force to overwrite (this erases the current run)."
        )
    root = {
        "id": "n0",
        "parent": None,
        "depth": 0,
        "status": "root",
        "hypothesis": args.objective,
        "insight": "",  # global insights accumulate here via backpropagation
        "metadata": {"dev_score": None, "test_score": None, "result": "", "branch_ref": None},
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
    }
    tree = {"_counter": 0, "root": "n0", "nodes": {"n0": root}}
    run = {
        "objective": args.objective,
        "metric_direction": args.metric_direction,
        "dev_eval": args.dev_eval,
        "test_eval": args.test_eval,
        "material": args.material,
        "branching": args.branching,
        "max_depth": args.max_depth,
        "budget_cycles": args.budget,
        "cycles_used": 0,
        "best_node": None,           # node id of current M_best
        "best_test_score": None,     # held-out score of M_best
        "best_branch_ref": None,     # git ref / path of M_best artifact
        "created_at": int(time.time()),
    }
    _save(_tree_path(args.run_dir), tree)
    _save(_run_path(args.run_dir), run)
    print(f"Initialized Arbor run in {d}")
    print(f"  objective       : {args.objective}")
    print(f"  metric direction: {args.metric_direction} (higher-is-better after orienting)")
    print(f"  dev evaluator   : {args.dev_eval}")
    print(f"  test evaluator  : {args.test_eval}")
    print(f"  budget          : {args.budget} cycles, branching {args.branching}, max depth {args.max_depth}")
    print("\nNext: `tree.py observe` to read the state, then add direction nodes under n0.")


def cmd_add_node(args):
    tree = _load_tree(args.run_dir)
    parent = _node(tree, args.parent)
    run = _load_run(args.run_dir)
    nid = _next_id(tree)
    depth = _depth(tree, args.parent) + 1
    if depth > run["max_depth"]:
        print(
            f"warning: node depth {depth} exceeds max_depth {run['max_depth']}. "
            f"Deep nodes should be concrete, executable interventions.",
            file=sys.stderr,
        )
    node = {
        "id": nid,
        "parent": args.parent,
        "depth": depth,
        "status": "pending",
        "hypothesis": args.hypothesis,
        "insight": "",
        "metadata": {"dev_score": None, "test_score": None, "result": "", "branch_ref": None},
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
    }
    tree["nodes"][nid] = node
    _save(_tree_path(args.run_dir), tree)
    kind = "direction" if depth == 1 else "intervention"
    print(f"Added {kind} node {nid} (depth {depth}) under {args.parent}: {args.hypothesis}")


def cmd_set_status(args):
    tree = _load_tree(args.run_dir)
    node = _node(tree, args.node)
    if args.status not in VALID_STATUS:
        sys.exit(f"error: status must be one of {sorted(VALID_STATUS)}")
    node["status"] = args.status
    _stamp(node)
    _save(_tree_path(args.run_dir), tree)
    print(f"{args.node} -> status={args.status}")


def cmd_set_evidence(args):
    """Write an executor's report back into its node (the Backpropagate step,
    leaf part). Insight propagation upward is a separate, deliberate call."""
    tree = _load_tree(args.run_dir)
    node = _node(tree, args.node)
    meta = node["metadata"]
    if args.dev_score is not None:
        meta["dev_score"] = args.dev_score
    if args.result is not None:
        meta["result"] = args.result
    if args.branch_ref is not None:
        meta["branch_ref"] = args.branch_ref
    if args.insight is not None:
        node["insight"] = args.insight
    node["status"] = args.status or "executed"
    _stamp(node)
    _save(_tree_path(args.run_dir), tree)
    print(f"Wrote evidence to {args.node}: dev_score={meta['dev_score']} status={node['status']}")
    if node["insight"]:
        print(f"  insight: {node['insight']}")
    anc = _ancestors(tree, args.node)
    if anc:
        print(
            "\nReminder: abstract this leaf insight upward. Decide what direction-level "
            f"lesson it implies for ancestors {anc} and record it with "
            f"`tree.py propagate --node {args.node} --insight \"...\"` (and update n0 "
            "global insights if it generalizes)."
        )


def cmd_propagate(args):
    """Backpropagate a distilled, direction-level lesson up the ancestor path.

    The coordinator decides the abstracted wording; this appends it to the
    chosen ancestor(s) so later ideation is conditioned on it. By default it
    updates the immediate parent; --to-root also updates global insights."""
    tree = _load_tree(args.run_dir)
    _node(tree, args.node)  # validate
    targets = _ancestors(tree, args.node)
    if not targets:
        sys.exit("error: node has no ancestors (is it the root?).")
    if not args.to_root:
        targets = targets[:1]  # immediate parent only
    for tid in targets:
        anc = tree["nodes"][tid]
        existing = anc.get("insight", "")
        line = f"[from {args.node}] {args.insight}"
        anc["insight"] = (existing + "\n" + line).strip() if existing else line
        _stamp(anc)
    _save(_tree_path(args.run_dir), tree)
    print(f"Propagated insight from {args.node} to ancestors {targets}")


def cmd_prune(args):
    """Mark a node (and its subtree) pruned. Pruned hypotheses become negative
    constraints — record *why* so future ideation avoids the dead end."""
    tree = _load_tree(args.run_dir)
    _node(tree, args.node)
    stack = [args.node]
    pruned = []
    while stack:
        cur = stack.pop()
        node = tree["nodes"][cur]
        if node["status"] in ("merged", "root"):
            continue
        node["status"] = "pruned"
        if cur == args.node and args.reason:
            node["metadata"]["prune_reason"] = args.reason
        _stamp(node)
        pruned.append(cur)
        stack.extend(_children(tree, cur))
    _save(_tree_path(args.run_dir), tree)
    print(f"Pruned {pruned}" + (f" — reason: {args.reason}" if args.reason else ""))


def cmd_merge(args):
    """Record a held-out merge gate decision. Only call this AFTER evaluating
    the candidate on the TEST evaluator in a fresh worktree. Admitting a
    candidate that only improved dev defeats the purpose of the split."""
    tree = _load_tree(args.run_dir)
    run = _load_run(args.run_dir)
    node = _node(tree, args.node)

    direction = run["metric_direction"]
    prev = run["best_test_score"]

    def better(new, old):
        if old is None:
            return True
        return new > old if direction == "max" else new < old

    improves = better(args.test_score, prev)
    node["metadata"]["test_score"] = args.test_score
    if improves:
        node["status"] = "merged"
        run["best_node"] = args.node
        run["best_test_score"] = args.test_score
        run["best_branch_ref"] = args.branch_ref or node["metadata"].get("branch_ref")
        _stamp(node)
        _save(_tree_path(args.run_dir), tree)
        _save(_run_path(args.run_dir), run)
        print(
            f"MERGE GATE PASSED: {args.node} test={args.test_score} "
            f"beats previous best={prev}. M_best is now {args.node} "
            f"(ref: {run['best_branch_ref']})."
        )
    else:
        _stamp(node)
        _save(_tree_path(args.run_dir), tree)
        print(
            f"MERGE GATE REJECTED: {args.node} test={args.test_score} does not beat "
            f"best={prev} (direction={direction}). This is informative, not a failure: "
            "a high-dev / low-test gap means the candidate may be exploiting the dev "
            "signal. Record that lesson and keep M_best unchanged."
        )


def cmd_cycle(args):
    """Increment the cycle counter (call once per Observe->Decide pass)."""
    run = _load_run(args.run_dir)
    run["cycles_used"] += 1
    _save(_run_path(args.run_dir), run)
    left = run["budget_cycles"] - run["cycles_used"]
    print(f"Cycle {run['cycles_used']}/{run['budget_cycles']} ({left} remaining).")
    if left <= 0:
        print("Budget exhausted — finish the run: do a final merge-gate check and report.")


# ----------------------------------------------------------------------------
# Read-only projections
# ----------------------------------------------------------------------------


def _fmt_score(node, run):
    s = node["metadata"].get("dev_score")
    t = node["metadata"].get("test_score")
    bits = []
    if s is not None:
        bits.append(f"dev={s}")
    if t is not None:
        bits.append(f"test={t}")
    return (" [" + " ".join(bits) + "]") if bits else ""


def cmd_observe(args):
    """The Observe step: a compact projection the coordinator re-grounds on at
    the start of each cycle, so decisions come from the tree rather than from a
    lossy conversation history."""
    tree = _load_tree(args.run_dir)
    run = _load_run(args.run_dir)
    nodes = tree["nodes"]
    root = nodes[tree["root"]]

    print("=" * 72)
    print("OBSERVE — current research state")
    print("=" * 72)
    print(f"Objective       : {run['objective']}")
    print(f"Metric direction: {run['metric_direction']}")
    print(f"Dev evaluator   : {run['dev_eval']}")
    print(f"Test evaluator  : {run['test_eval']}")
    print(
        f"Budget          : cycle {run['cycles_used']}/{run['budget_cycles']}, "
        f"branching {run['branching']}, max depth {run['max_depth']}"
    )
    print(
        f"Current best    : "
        + (
            f"{run['best_node']} (test={run['best_test_score']}, ref={run['best_branch_ref']})"
            if run["best_node"]
            else "none yet — M_best is the initial material"
        )
    )

    print("\n-- Global insights (root) --")
    print(root["insight"].strip() if root["insight"].strip() else "  (none yet)")

    # Active frontier = pending/running leaves
    frontier = [
        n
        for n in nodes.values()
        if n["status"] in ("pending", "running") and not _children(tree, n["id"])
    ]
    print("\n-- Active frontier (selectable hypotheses) --")
    if not frontier:
        print("  (empty — ideate new children under a promising node)")
    for n in sorted(frontier, key=lambda x: x["id"]):
        anc = _ancestors(tree, n["id"])
        anc_ins = " | ".join(
            nodes[a]["insight"].replace("\n", " ")[:80] for a in anc if nodes[a]["insight"].strip()
        )
        print(f"  {n['id']} (depth {n['depth']}, {n['status']}): {n['hypothesis']}")
        if anc_ins:
            print(f"      ancestor insights: {anc_ins}")

    # Validated / executed leaves with evidence
    executed = [n for n in nodes.values() if n["status"] in ("executed", "merged")]
    print("\n-- Executed / merged nodes (evidence) --")
    if not executed:
        print("  (none yet)")
    for n in sorted(executed, key=lambda x: x["id"]):
        print(f"  {n['id']} [{n['status']}]{_fmt_score(n, run)}: {n['hypothesis']}")
        if n["insight"].strip():
            print(f"      insight: {n['insight'].splitlines()[0][:120]}")

    # Pruned lessons (negative constraints)
    pruned = [n for n in nodes.values() if n["status"] == "pruned"]
    print("\n-- Pruned lessons (negative constraints — avoid these) --")
    if not pruned:
        print("  (none yet)")
    for n in sorted(pruned, key=lambda x: x["id"]):
        reason = n["metadata"].get("prune_reason", "")
        print(f"  {n['id']}: {n['hypothesis']}" + (f" — {reason}" if reason else ""))

    print("\n" + "=" * 72)
    print(
        "Next: Ideate children under a promising node, Select one or more frontier\n"
        "leaves, Dispatch each to an executor subagent in an isolated worktree."
    )


def cmd_status(args):
    """ASCII tree render — useful for reports and quick scans."""
    tree = _load_tree(args.run_dir)
    run = _load_run(args.run_dir)
    nodes = tree["nodes"]

    symbol = {
        "root": "*",
        "pending": "o",
        "running": "~",
        "executed": "=",
        "merged": "V",
        "pruned": "x",
    }

    def render(nid, prefix=""):
        n = nodes[nid]
        sym = symbol.get(n["status"], "?")
        best = " <== M_best" if nid == run["best_node"] else ""
        print(f"{prefix}[{sym}] {nid} {n['hypothesis'][:70]}{_fmt_score(n, run)}{best}")
        kids = sorted(_children(tree, nid))
        for i, c in enumerate(kids):
            render(c, prefix + "    ")

    print(f"Run: {run['objective']}")
    print(f"Cycle {run['cycles_used']}/{run['budget_cycles']}  |  legend: * root  o pending  ~ running  = executed  V merged  x pruned\n")
    render(tree["root"])


def cmd_validate(args):
    """Check invariants — catch a corrupted or inconsistent tree early."""
    tree = _load_tree(args.run_dir)
    run = _load_run(args.run_dir)
    nodes = tree["nodes"]
    problems = []
    if tree["root"] not in nodes:
        problems.append("root id not present in nodes")
    for nid, n in nodes.items():
        p = n.get("parent")
        if p is not None and p not in nodes:
            problems.append(f"{nid}: parent {p} missing")
        if n["status"] not in VALID_STATUS:
            problems.append(f"{nid}: invalid status {n['status']}")
    if run["best_node"] and run["best_node"] not in nodes:
        problems.append(f"best_node {run['best_node']} missing")
    merged = [nid for nid, n in nodes.items() if n["status"] == "merged"]
    if run["best_node"] and run["best_node"] not in merged and run["best_node"] != tree["root"]:
        problems.append(f"best_node {run['best_node']} is not marked merged")
    if problems:
        print("INVALID:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print(f"OK — {len(nodes)} nodes, root={tree['root']}, best={run['best_node']}")


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------


def build_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--run-dir", default=".", help="Run directory holding .arbor/ (default: current dir)")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("init", help="Initialize a new AO run / hypothesis tree")
    s.add_argument("--objective", required=True, help="Natural-language research objective (root hypothesis)")
    s.add_argument("--dev-eval", required=True, help="Command/description of the development evaluator")
    s.add_argument("--test-eval", required=True, help="Command/description of the held-out test evaluator")
    s.add_argument("--material", default="", help="Path/ref to the initial artifact M_0")
    s.add_argument("--metric-direction", choices=["max", "min"], default="max", help="Is higher or lower the better score?")
    s.add_argument("--branching", type=int, default=3, help="Max children proposed per parent (k)")
    s.add_argument("--max-depth", type=int, default=2, help="Max tree depth (directions at 1, interventions at 2+)")
    s.add_argument("--budget", type=int, default=20, help="Coordinator cycle budget B")
    s.add_argument("--force", action="store_true", help="Overwrite an existing run")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("observe", help="Print the research-state projection (start of each cycle)")
    s.set_defaults(func=cmd_observe)

    s = sub.add_parser("add-node", help="Add a pending child hypothesis under a parent (Ideate)")
    s.add_argument("--parent", required=True, help="Parent node id (n0 for a new research direction)")
    s.add_argument("--hypothesis", required=True, help="Falsifiable claim this node tests")
    s.set_defaults(func=cmd_add_node)

    s = sub.add_parser("set-status", help="Set a node's status manually")
    s.add_argument("--node", required=True)
    s.add_argument("--status", required=True, help=f"One of {sorted(VALID_STATUS)}")
    s.set_defaults(func=cmd_set_status)

    s = sub.add_parser("set-evidence", help="Write an executor report into its node (Backpropagate, leaf)")
    s.add_argument("--node", required=True)
    s.add_argument("--dev-score", type=float, default=None, help="Dev evaluator score returned by the executor")
    s.add_argument("--result", default=None, help="Factual result summary")
    s.add_argument("--insight", default=None, help="Distilled, reusable lesson from this experiment")
    s.add_argument("--branch-ref", default=None, help="Git branch/commit/worktree path of the artifact")
    s.add_argument("--status", default=None, help="Override status (default: executed)")
    s.set_defaults(func=cmd_set_evidence)

    s = sub.add_parser("propagate", help="Abstract a leaf insight up to ancestors (Backpropagate, upward)")
    s.add_argument("--node", required=True, help="The leaf the lesson came from")
    s.add_argument("--insight", required=True, help="Direction-level abstraction of the lesson")
    s.add_argument("--to-root", action="store_true", help="Also record as a global insight on the root")
    s.set_defaults(func=cmd_propagate)

    s = sub.add_parser("prune", help="Prune a falsified node and its subtree (Decide)")
    s.add_argument("--node", required=True)
    s.add_argument("--reason", default="", help="Why this direction is a dead end (becomes a negative constraint)")
    s.set_defaults(func=cmd_prune)

    s = sub.add_parser("merge", help="Record a held-out merge gate decision (Decide)")
    s.add_argument("--node", required=True)
    s.add_argument("--test-score", type=float, required=True, help="Score on the TEST evaluator in a fresh worktree")
    s.add_argument("--branch-ref", default=None, help="Artifact ref to promote if it passes")
    s.set_defaults(func=cmd_merge)

    s = sub.add_parser("cycle", help="Increment the coordinator cycle counter")
    s.set_defaults(func=cmd_cycle)

    s = sub.add_parser("status", help="Render the tree as ASCII (for reports)")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("validate", help="Check tree invariants")
    s.set_defaults(func=cmd_validate)

    return p


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
