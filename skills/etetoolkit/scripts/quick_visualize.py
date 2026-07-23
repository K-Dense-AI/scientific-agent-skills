#!/usr/bin/env python3
"""Interactive or static ETE 4 tree visualization."""

from __future__ import annotations

import argparse
import ipaddress
import sys
from pathlib import Path

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
    """An actionable problem with command-line input."""


def parser_spec(value: str) -> ParserSpec:
    """Parse numeric Newick parser IDs while retaining named aliases."""
    text = value.strip()
    try:
        return int(text)
    except ValueError:
        if not text:
            raise argparse.ArgumentTypeError("parser cannot be empty")
        return text


def mode_spec(value: str) -> str:
    """Normalize short and long layout mode names."""
    aliases = {
        "r": "rectangular",
        "rectangular": "rectangular",
        "c": "circular",
        "circular": "circular",
    }
    try:
        return aliases[value.lower()]
    except KeyError as exc:
        raise argparse.ArgumentTypeError(
            "mode must be rectangular/r or circular/c"
        ) from exc


def load_tree(path: Path, parser: ParserSpec) -> Tree:
    """Load a Newick tree from a UTF-8 file."""
    if not path.is_file():
        raise UserInputError(f"input tree does not exist or is not a file: {path}")
    try:
        with path.open(encoding="utf-8") as handle:
            return Tree(handle, parser=parser)
    except (OSError, ValueError, TypeError, NewickError) as exc:
        raise UserInputError(
            f"could not parse {path} with Newick parser {parser!r}: {exc}"
        ) from exc


def support_fraction(value: float | None) -> float | None:
    """Normalize common 0–1 and 0–100 support conventions."""
    if value is None:
        return None
    numeric = float(value)
    return numeric / 100 if numeric > 1 else numeric


def support_color(node: Tree, args: argparse.Namespace) -> str:
    """Map support to a color after normalization."""
    support = support_fraction(node.support)
    if support is None:
        return args.missing_support_color
    if support >= args.high_support:
        return args.high_support_color
    if support >= args.moderate_support:
        return args.moderate_support_color
    return args.low_support_color


def create_smartview_layout(args: argparse.Namespace):
    """Create a current SmartView layout."""
    try:
        from ete4.smartview import Layout, PropFace, TextFace
    except ImportError as exc:
        raise UserInputError(
            'SmartView is unavailable; reinstall with: uv pip install "ete4==4.4.0"'
        ) from exc

    def draw_tree(_tree):
        tree_style = {
            "shape": args.mode,
            "node-height-min": args.collapse_pixels,
            "content-height-min": args.content_pixels,
            "show-popup-props": ["name", "dist", "support"],
        }
        if args.mode == "circular":
            tree_style.update(
                {
                    "angle-start": args.arc_start,
                    "angle-span": args.arc_span,
                }
            )
        yield tree_style
        if args.title:
            yield TextFace(
                args.title,
                fs_min=8,
                fs_max=22,
                position="header",
            )

    def draw_node(node):
        fill = (
            support_color(node, args)
            if args.color_by_support and not node.is_leaf
            else args.leaf_color
            if node.is_leaf
            else args.internal_color
        )
        radius = args.leaf_size if node.is_leaf else args.internal_size
        yield {
            "dot": {
                "shape": "circle",
                "radius": radius,
                "fill": fill,
            }
        }

        if node.is_leaf and args.show_names:
            yield PropFace(
                "name",
                fs_min=4,
                fs_max=args.label_size,
                position="right",
            )

        if args.show_support and not node.is_leaf and node.support is not None:
            yield TextFace(
                f"{node.support:g}",
                fs_min=3,
                fs_max=args.label_size,
                style={"fill": "#555555"},
                position="top",
            )

        if args.show_lengths and not node.is_root and node.dist is not None:
            yield TextFace(
                f"{node.dist:g}",
                fs_min=3,
                fs_max=args.label_size,
                style={"fill": "#777777"},
                position="bottom",
            )

    return Layout(
        "quick visualization",
        draw_tree=draw_tree,
        draw_node=draw_node,
    )


def validate_bind_address(host: str, allow_remote: bool) -> None:
    """Require explicit consent before binding beyond loopback."""
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if host.lower() == "localhost":
            return
        if not allow_remote:
            raise UserInputError("non-loopback host names require --allow-remote-bind")
        return

    if not address.is_loopback and not allow_remote:
        raise UserInputError(
            "refusing a non-loopback SmartView bind without --allow-remote-bind"
        )


def run_interactive_smartview(
    tree: Tree,
    layout,
    args: argparse.Namespace,
) -> None:
    """Run the SmartView server until the user exits."""
    validate_bind_address(args.host, args.allow_remote_bind)
    try:
        from ete4.smartview import explorer
    except ImportError as exc:
        raise UserInputError("could not import the SmartView explorer") from exc

    tree.explore(
        layouts=[layout],
        host=args.host,
        port=args.port,
        open_browser=not args.no_browser,
    )
    print("SmartView is running. Press Enter or Ctrl-C to stop it.")
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        explorer.stop_server()


def render_smartview(
    tree: Tree,
    layout,
    output: Path,
    args: argparse.Namespace,
) -> None:
    """Render a SmartView PNG screenshot."""
    if output.suffix.lower() != ".png":
        raise UserInputError(
            "SmartView static output is PNG screenshot data; use a .png path "
            "or select --engine treeview for PDF/SVG"
        )
    if not output.parent.is_dir():
        raise UserInputError(f"output directory does not exist: {output.parent}")

    try:
        tree.render_sm(
            str(output),
            layouts=[layout],
            w=args.width,
            h=args.height,
        )
    except (ImportError, ModuleNotFoundError) as exc:
        raise UserInputError(
            "SmartView static rendering needs the render-sm extra: "
            'uv pip install "ete4[render-sm]==4.4.0"'
        ) from exc
    print(f"Wrote SmartView PNG: {output}")


def create_treeview_style(tree: Tree, args: argparse.Namespace):
    """Create a Qt treeview style and apply node styles."""
    try:
        from ete4.treeview import NodeStyle, TextFace, TreeStyle
    except ImportError as exc:
        raise UserInputError(
            "Qt treeview output needs the treeview extra: "
            'uv pip install "ete4[treeview]==4.4.0"'
        ) from exc

    for node in tree.traverse():
        style = NodeStyle()
        style["size"] = args.leaf_size if node.is_leaf else args.internal_size
        style["fgcolor"] = (
            support_color(node, args)
            if args.color_by_support and not node.is_leaf
            else args.leaf_color
            if node.is_leaf
            else args.internal_color
        )
        node.set_style(style)

    tree_style = TreeStyle()
    tree_style.mode = "c" if args.mode == "circular" else "r"
    tree_style.show_leaf_name = args.show_names
    tree_style.show_branch_support = args.show_support
    tree_style.show_branch_length = args.show_lengths
    tree_style.show_scale = args.show_scale

    if args.mode == "circular":
        tree_style.arc_start = args.arc_start
        tree_style.arc_span = args.arc_span

    if args.title:
        tree_style.title.add_face(
            TextFace(args.title, fsize=max(args.label_size, 12), bold=True),
            column=0,
        )
    return tree_style


def render_treeview(
    tree: Tree,
    output: Path,
    args: argparse.Namespace,
) -> None:
    """Render PNG, PDF, or SVG through Qt treeview."""
    if output.suffix.lower() not in {".png", ".pdf", ".svg"}:
        raise UserInputError("Qt treeview output must end in .png, .pdf, or .svg")
    if not output.parent.is_dir():
        raise UserInputError(f"output directory does not exist: {output.parent}")

    tree_style = create_treeview_style(tree, args)
    render_args = {
        "tree_style": tree_style,
        "units": args.units,
        "dpi": args.dpi,
    }
    if args.width is not None:
        render_args["w"] = args.width
    if args.height is not None:
        render_args["h"] = args.height

    tree.render(str(output), **render_args)
    print(f"Wrote Qt treeview output: {output}")


def choose_engine(args: argparse.Namespace) -> str:
    """Choose a renderer from the requested engine and output suffix."""
    if args.engine != "auto":
        return args.engine
    if args.output is None or args.output.suffix.lower() == ".png":
        return "smartview"
    if args.output.suffix.lower() in {".pdf", ".svg"}:
        return "treeview"
    raise UserInputError(
        "cannot infer renderer from output suffix; use .png, .pdf, or .svg"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Explore a tree with ETE 4 SmartView or render it with "
            "SmartView/Qt treeview"
        )
    )
    parser.add_argument("input", type=Path, help="Newick tree file")
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        help="optional .png, .pdf, or .svg output; omit for SmartView",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s (ETE {ete4.__version__})",
    )
    parser.add_argument("--parser", type=parser_spec, default=0)
    parser.add_argument(
        "--engine",
        choices=["auto", "smartview", "treeview"],
        default="auto",
    )
    parser.add_argument("--mode", type=mode_spec, default="rectangular")
    parser.add_argument("--title")

    display = parser.add_argument_group("display")
    display.add_argument(
        "--show-names",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    display.add_argument("--show-support", action="store_true")
    display.add_argument("--show-lengths", action="store_true")
    display.add_argument("--show-scale", action="store_true")
    display.add_argument("--color-by-support", action="store_true")
    display.add_argument("--label-size", type=int, default=12)
    display.add_argument("--leaf-size", type=int, default=5)
    display.add_argument("--internal-size", type=int, default=4)
    display.add_argument("--leaf-color", default="#2166ac")
    display.add_argument("--internal-color", default="#777777")

    support = parser.add_argument_group("support colors")
    support.add_argument("--high-support", type=float, default=0.9)
    support.add_argument("--moderate-support", type=float, default=0.7)
    support.add_argument("--high-support-color", default="#1b7837")
    support.add_argument("--moderate-support-color", default="#e08214")
    support.add_argument("--low-support-color", default="#b2182b")
    support.add_argument("--missing-support-color", default="#999999")

    smartview = parser.add_argument_group("SmartView")
    smartview.add_argument("--collapse-pixels", type=float, default=8)
    smartview.add_argument("--content-pixels", type=float, default=4)
    smartview.add_argument("--host", default="127.0.0.1")
    smartview.add_argument("--port", type=int)
    smartview.add_argument("--no-browser", action="store_true")
    smartview.add_argument(
        "--allow-remote-bind",
        action="store_true",
        help="allow SmartView to bind beyond loopback",
    )

    output = parser.add_argument_group("static output")
    output.add_argument("--width", type=int)
    output.add_argument("--height", type=int)
    output.add_argument("--units", choices=["px", "mm", "in"], default="px")
    output.add_argument("--dpi", type=int, default=300)
    output.add_argument("--arc-start", type=int, default=0)
    output.add_argument("--arc-span", type=int, default=360)
    return parser


def validate_args(args: argparse.Namespace) -> None:
    """Validate numerical and renderer-specific options."""
    if not 0 <= args.moderate_support <= args.high_support <= 1:
        raise UserInputError(
            "support thresholds must satisfy 0 <= moderate-support <= high-support <= 1"
        )
    for name in (
        "label_size",
        "leaf_size",
        "internal_size",
        "collapse_pixels",
        "content_pixels",
    ):
        if getattr(args, name) < 0:
            raise UserInputError(f"{name.replace('_', '-')} cannot be negative")
    for name in ("width", "height", "dpi"):
        value = getattr(args, name)
        if value is not None and value <= 0:
            raise UserInputError(f"{name} must be positive")
    if args.port is not None and not 1 <= args.port <= 65535:
        raise UserInputError("port must be between 1 and 65535")
    if not -360 <= args.arc_start <= 360:
        raise UserInputError("arc-start must be between -360 and 360 degrees")
    if not 0 < args.arc_span <= 360:
        raise UserInputError("arc-span must be greater than 0 and at most 360 degrees")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        validate_args(args)
        tree = load_tree(args.input, args.parser)
        engine = choose_engine(args)

        if engine == "smartview":
            layout = create_smartview_layout(args)
            if args.output is None:
                run_interactive_smartview(tree, layout, args)
            else:
                render_smartview(tree, layout, args.output, args)
        else:
            if args.output is None:
                raise UserInputError("Qt treeview mode requires an output path")
            render_treeview(tree, args.output, args)
    except UserInputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # Preserve unexpected ETE/renderer details.
        print(
            f"unexpected visualization error: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
