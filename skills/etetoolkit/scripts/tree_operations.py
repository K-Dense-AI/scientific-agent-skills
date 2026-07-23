#!/usr/bin/env python3
"""Validated command-line tree operations for ETE 4."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

try:
    import ete4
    from ete4 import Tree
    from ete4.parser.newick import NewickError
except ImportError as exc:
    raise SystemExit(
        'ETE 4 is required. Install it with: uv pip install "ete4==4.4.0"'
    ) from exc


ParserSpec = int | str


class UserInputError(ValueError):
    """An actionable problem with command-line input or tree content."""


def parser_spec(value: str) -> ParserSpec:
    """Parse numeric Newick parser IDs while retaining named aliases."""
    text = value.strip()
    try:
        return int(text)
    except ValueError:
        if not text:
            raise argparse.ArgumentTypeError("parser cannot be empty")
        return text


def comma_separated(value: str) -> list[str]:
    """Parse a comma-separated property list."""
    return [item.strip() for item in value.split(",") if item.strip()]


def load_tree(path: Path, parser: ParserSpec) -> Tree:
    """Load one Newick tree from a UTF-8 text file."""
    if not path.is_file():
        raise UserInputError(f"input tree does not exist or is not a file: {path}")

    try:
        with path.open(encoding="utf-8") as handle:
            return Tree(handle, parser=parser)
    except (OSError, ValueError, TypeError, NewickError) as exc:
        raise UserInputError(
            f"could not parse {path} with Newick parser {parser!r}: {exc}"
        ) from exc


def save_tree(
    tree: Tree,
    path: Path,
    parser: ParserSpec,
    props: list[str],
) -> None:
    """Serialize a tree after validating its destination directory."""
    if not path.parent.is_dir():
        raise UserInputError(f"output directory does not exist: {path.parent}")

    try:
        newick = tree.write(
            parser=parser,
            props=props,
            format_root_node=True,
        )
        path.write_text(newick.rstrip("\n") + "\n", encoding="utf-8")
    except (OSError, ValueError, TypeError, NewickError) as exc:
        raise UserInputError(
            f"could not write {path} with Newick parser {parser!r}: {exc}"
        ) from exc


def numeric_summary(values: list[float]) -> dict[str, float] | None:
    """Return basic descriptive statistics for a numeric list."""
    if not values:
        return None
    return {
        "minimum": min(values),
        "maximum": max(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
    }


def tree_stats(tree: Tree, source: Path) -> dict[str, Any]:
    """Calculate structural, branch-length, and support diagnostics."""
    nodes = list(tree.traverse())
    leaves = list(tree.leaves())
    internal = [node for node in nodes if not node.is_leaf]
    names = [leaf.name for leaf in leaves]
    duplicate_names = sorted(
        name for name, count in Counter(names).items() if name is not None and count > 1
    )
    unnamed_leaf_ids = [list(leaf.id) for leaf in leaves if not leaf.name]

    branch_lengths = [
        float(node.dist) for node in nodes if not node.is_root and node.dist is not None
    ]
    support_values = [
        float(node.support)
        for node in internal
        if not node.is_root and node.support is not None
    ]

    farthest_leaf, farthest_distance = tree.get_farthest_leaf()

    return {
        "source": str(source),
        "ete_version": ete4.__version__,
        "leaf_count": len(leaves),
        "internal_node_count": len(internal),
        "total_node_count": len(nodes),
        "root_child_count": len(tree.children),
        "polytomy_count": sum(len(node.children) > 2 for node in internal),
        "unary_node_count": sum(len(node.children) == 1 for node in internal),
        "duplicate_leaf_names": duplicate_names,
        "unnamed_leaf_ids": unnamed_leaf_ids,
        "branch_lengths": numeric_summary(branch_lengths),
        "internal_support": numeric_summary(support_values),
        "farthest_leaf": farthest_leaf.name,
        "farthest_leaf_distance": float(farthest_distance),
    }


def print_stats(stats: dict[str, Any], as_json: bool) -> None:
    """Print statistics as JSON or readable text."""
    if as_json:
        print(json.dumps(stats, indent=2, sort_keys=True))
        return

    print(f"File: {stats['source']}")
    print(f"ETE version: {stats['ete_version']}")
    print(f"Leaves: {stats['leaf_count']}")
    print(f"Internal nodes: {stats['internal_node_count']}")
    print(f"Total nodes: {stats['total_node_count']}")
    print(f"Root children: {stats['root_child_count']}")
    print(f"Polytomies: {stats['polytomy_count']}")
    print(f"Unary nodes: {stats['unary_node_count']}")
    print(f"Farthest leaf: {stats['farthest_leaf']!r}")
    print(f"Farthest distance: {stats['farthest_leaf_distance']:.6g}")

    for label, key in (
        ("Branch lengths", "branch_lengths"),
        ("Internal support", "internal_support"),
    ):
        summary = stats[key]
        if summary is None:
            print(f"{label}: none")
        else:
            print(
                f"{label}: min={summary['minimum']:.6g}, "
                f"median={summary['median']:.6g}, "
                f"mean={summary['mean']:.6g}, "
                f"max={summary['maximum']:.6g}"
            )

    print(f"Duplicate leaf names: {stats['duplicate_leaf_names'] or 'none'}")
    print(f"Unnamed leaf IDs: {stats['unnamed_leaf_ids'] or 'none'}")


def resolve_unique_node(tree: Tree, name: str) -> Tree:
    """Resolve exactly one named node."""
    matches = list(tree.search_nodes(name=name))
    if not matches:
        raise UserInputError(f"node not found: {name!r}")
    if len(matches) > 1:
        raise UserInputError(
            f"node name is ambiguous ({len(matches)} matches): {name!r}"
        )
    return matches[0]


def read_keep_names(values: list[str] | None, file_path: Path | None) -> list[str]:
    """Read requested names from arguments or a one-name-per-line file."""
    if file_path is not None:
        if not file_path.is_file():
            raise UserInputError(f"taxon file does not exist: {file_path}")
        try:
            names = [
                line.strip()
                for line in file_path.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            ]
        except OSError as exc:
            raise UserInputError(
                f"could not read taxon file {file_path}: {exc}"
            ) from exc
    else:
        names = values or []

    duplicates = sorted(name for name, count in Counter(names).items() if count > 1)
    if not names:
        raise UserInputError("at least one taxon must be requested")
    if duplicates:
        raise UserInputError(f"duplicate requested taxa: {duplicates}")
    return names


def validate_requested_names(tree: Tree, requested: list[str]) -> None:
    """Require every requested name to resolve to exactly one tree node."""
    counts = Counter(tree.leaf_names())
    missing = sorted(name for name in requested if counts[name] == 0)
    ambiguous = sorted(name for name in requested if counts[name] > 1)
    if missing:
        raise UserInputError(f"requested leaves are absent: {missing}")
    if ambiguous:
        raise UserInputError(f"requested leaf names are duplicated: {ambiguous}")


def command_stats(args: argparse.Namespace) -> None:
    tree = load_tree(args.input, args.parser)
    print_stats(tree_stats(tree, args.input), args.json)


def command_ascii(args: argparse.Namespace) -> None:
    tree = load_tree(args.input, args.parser)
    print(
        tree.to_str(
            show_internal=not args.no_internal,
            compact=args.compact,
            props=args.props,
        )
    )


def command_leaves(args: argparse.Namespace) -> None:
    tree = load_tree(args.input, args.parser)
    for name in tree.leaf_names():
        print("" if name is None else name)


def command_convert(args: argparse.Namespace) -> None:
    tree = load_tree(args.input, args.input_parser)
    save_tree(tree, args.output, args.output_parser, args.props)
    print(f"Wrote {args.output}")


def command_reroot(args: argparse.Namespace) -> None:
    tree = load_tree(args.input, args.parser)
    if args.midpoint:
        tree.set_midpoint_outgroup(topological=args.topological)
        method = (
            "topological midpoint" if args.topological else "branch-length midpoint"
        )
    else:
        if args.topological:
            raise UserInputError("--topological applies only to --midpoint")
        outgroup = resolve_unique_node(tree, args.outgroup)
        tree.set_outgroup(outgroup)
        method = f"outgroup {args.outgroup!r}"

    save_tree(tree, args.output, args.output_parser or args.parser, args.props)
    print(f"Rerooted with {method}; wrote {args.output}")


def command_prune(args: argparse.Namespace) -> None:
    tree = load_tree(args.input, args.parser)
    names = read_keep_names(args.keep, args.keep_file)
    validate_requested_names(tree, names)
    tree.prune(names, preserve_branch_length=args.preserve_branch_length)
    save_tree(tree, args.output, args.output_parser or args.parser, args.props)
    print(f"Retained {len(names)} leaves; wrote {args.output}")


def command_compare(args: argparse.Namespace) -> None:
    tree_a = load_tree(args.tree_a, args.parser_a)
    tree_b = load_tree(args.tree_b, args.parser_b)

    for label, tree in (("tree_a", tree_a), ("tree_b", tree_b)):
        names = list(tree.leaf_names())
        unnamed_count = sum(not name for name in names)
        if unnamed_count:
            raise UserInputError(f"{label} has {unnamed_count} unnamed leaves")
        counts = Counter(names)
        duplicates = sorted(
            name for name, count in counts.items() if name is not None and count > 1
        )
        if duplicates:
            raise UserInputError(f"{label} has duplicate leaf names: {duplicates}")

    (
        rf,
        max_rf,
        common,
        _edges_a,
        _edges_b,
        discarded_a,
        discarded_b,
    ) = tree_a.robinson_foulds(
        tree_b,
        unrooted_trees=args.unrooted,
        min_support_t1=args.min_support_a,
        min_support_t2=args.min_support_b,
    )

    result = {
        "tree_a": str(args.tree_a),
        "tree_b": str(args.tree_b),
        "unrooted": args.unrooted,
        "rf": rf,
        "max_rf": max_rf,
        "normalized_rf": rf / max_rf if max_rf else 0.0,
        "common_leaf_count": len(common),
        "common_leaves": sorted(common),
        "discarded_edge_count_a": len(discarded_a),
        "discarded_edge_count_b": len(discarded_b),
    }
    print(json.dumps(result, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validated ETE 4 tree operations",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s (ETE {ete4.__version__})",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    stats = subparsers.add_parser("stats", help="report tree diagnostics")
    stats.add_argument("input", type=Path)
    stats.add_argument("--parser", type=parser_spec, default=0)
    stats.add_argument("--json", action="store_true")
    stats.set_defaults(handler=command_stats)

    ascii_parser = subparsers.add_parser("ascii", help="print a terminal tree")
    ascii_parser.add_argument("input", type=Path)
    ascii_parser.add_argument("--parser", type=parser_spec, default=0)
    ascii_parser.add_argument(
        "--props",
        type=comma_separated,
        default=["name"],
        help="comma-separated node properties to display (default: name)",
    )
    ascii_parser.add_argument("--compact", action="store_true")
    ascii_parser.add_argument("--no-internal", action="store_true")
    ascii_parser.set_defaults(handler=command_ascii)

    leaves = subparsers.add_parser("leaves", help="print leaf names")
    leaves.add_argument("input", type=Path)
    leaves.add_argument("--parser", type=parser_spec, default=0)
    leaves.set_defaults(handler=command_leaves)

    convert = subparsers.add_parser("convert", help="convert Newick parsers")
    convert.add_argument("input", type=Path)
    convert.add_argument("output", type=Path)
    convert.add_argument("--input-parser", type=parser_spec, default=0)
    convert.add_argument("--output-parser", type=parser_spec, default=1)
    convert.add_argument(
        "--props",
        type=comma_separated,
        default=[],
        help="comma-separated NHX properties to retain (default: none)",
    )
    convert.set_defaults(handler=command_convert)

    reroot = subparsers.add_parser("reroot", help="reroot by outgroup or midpoint")
    reroot.add_argument("input", type=Path)
    reroot.add_argument("output", type=Path)
    reroot.add_argument("--parser", type=parser_spec, default=0)
    reroot.add_argument("--output-parser", type=parser_spec)
    rooting = reroot.add_mutually_exclusive_group(required=True)
    rooting.add_argument("--outgroup", help="unique node name to use as outgroup")
    rooting.add_argument("--midpoint", action="store_true")
    reroot.add_argument(
        "--topological",
        action="store_true",
        help="use edge counts instead of branch lengths for midpoint rooting",
    )
    reroot.add_argument(
        "--props",
        type=comma_separated,
        default=[],
        help="comma-separated NHX properties to write (default: none)",
    )
    reroot.set_defaults(handler=command_reroot)

    prune = subparsers.add_parser("prune", help="retain selected leaves")
    prune.add_argument("input", type=Path)
    prune.add_argument("output", type=Path)
    prune.add_argument("--parser", type=parser_spec, default=0)
    prune.add_argument("--output-parser", type=parser_spec)
    selection = prune.add_mutually_exclusive_group(required=True)
    selection.add_argument("--keep", nargs="+", help="leaf names to retain")
    selection.add_argument(
        "--keep-file",
        type=Path,
        help="UTF-8 file with one leaf name per line",
    )
    prune.add_argument(
        "--preserve-branch-length",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    prune.add_argument(
        "--props",
        type=comma_separated,
        default=[],
        help="comma-separated NHX properties to write (default: none)",
    )
    prune.set_defaults(handler=command_prune)

    compare = subparsers.add_parser(
        "compare",
        help="calculate Robinson-Foulds distance",
    )
    compare.add_argument("tree_a", type=Path)
    compare.add_argument("tree_b", type=Path)
    compare.add_argument("--parser-a", type=parser_spec, default=0)
    compare.add_argument("--parser-b", type=parser_spec, default=0)
    compare.add_argument("--unrooted", action="store_true")
    compare.add_argument("--min-support-a", type=float, default=0.0)
    compare.add_argument("--min-support-b", type=float, default=0.0)
    compare.set_defaults(handler=command_compare)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.handler(args)
    except UserInputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # Preserve unexpected ETE failures for CLI users.
        print(f"unexpected ETE error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
