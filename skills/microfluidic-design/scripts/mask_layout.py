#!/usr/bin/env python3
"""Parametric photomask layout export: DXF R12 (and optional SVG preview).

Generates mask-ready 2D geometry for common microfluidic motifs:

  straight       one channel with an inlet and outlet port
  serpentine     folded channel (mixing/incubation/PCR length in a small footprint)
  t-junction     droplet T-junction (main + side channel, three ports)
  flow-focusing  cross junction with a narrowed orifice, four ports
  dld            deterministic-lateral-displacement post array

Shapes are axis-aligned rectangles and circles on named layers (CHANNEL,
POSTS, PORTS). Overlapping filled shapes on one layer merge during exposure,
so junctions are drawn as overlapping rectangles. POSTS is the subtractive
layer of a DLD array: posts sit INSIDE the channel outline and print as
unexposed islands. Coordinates are millimetres.

The DXF is written where --output points; layout metadata (entity counts,
bounding box, minimum feature) goes to stdout. Run fabrication_check.py on the
same dimensions before sending any mask out.

Exit 0; 2 on bad input. This tool draws what it is told -- it does not verify
process compatibility.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import _common as C

MM = 1e-3


class Layout:
    def __init__(self) -> None:
        self.rects: list[tuple[float, float, float, float, str]] = []
        self.circles: list[tuple[float, float, float, str]] = []

    def rect(self, x0: float, y0: float, x1: float, y1: float,
             layer: str = "CHANNEL") -> None:
        self.rects.append((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1), layer))

    def circle(self, cx: float, cy: float, r: float, layer: str = "PORTS") -> None:
        self.circles.append((cx, cy, r, layer))

    def bounds(self) -> tuple[float, float, float, float]:
        xs, ys = [], []
        for x0, y0, x1, y1, _ in self.rects:
            xs += [x0, x1]
            ys += [y0, y1]
        for cx, cy, r, _ in self.circles:
            xs += [cx - r, cx + r]
            ys += [cy - r, cy + r]
        if not xs:
            raise C.InputError("empty layout")
        return min(xs), min(ys), max(xs), max(ys)

    def min_feature(self) -> float:
        features = [min(x1 - x0, y1 - y0) for x0, y0, x1, y1, _ in self.rects]
        features += [2.0 * r for _, _, r, _ in self.circles]
        return min(features)


# ------------------------------ Writers ------------------------------------


def _dxf_pairs(*pairs) -> str:
    return "".join(f"{code}\n{value}\n" for code, value in pairs)


def write_dxf(layout: Layout, path: Path) -> None:
    """Minimal DXF R12: HEADER with AC1009, then ENTITIES."""
    parts = [_dxf_pairs((0, "SECTION"), (2, "HEADER"),
                        (9, "$ACADVER"), (1, "AC1009"),
                        (0, "ENDSEC"), (0, "SECTION"), (2, "ENTITIES"))]
    for x0, y0, x1, y1, layer in layout.rects:
        parts.append(_dxf_pairs((0, "POLYLINE"), (8, layer), (66, 1), (70, 1)))
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            parts.append(_dxf_pairs((0, "VERTEX"), (8, layer),
                                    (10, f"{x / MM:.6f}"), (20, f"{y / MM:.6f}")))
        parts.append(_dxf_pairs((0, "SEQEND")))
    for cx, cy, r, layer in layout.circles:
        parts.append(_dxf_pairs((0, "CIRCLE"), (8, layer),
                                (10, f"{cx / MM:.6f}"), (20, f"{cy / MM:.6f}"),
                                (40, f"{r / MM:.6f}")))
    parts.append(_dxf_pairs((0, "ENDSEC"), (0, "EOF")))
    path.write_text("".join(parts), encoding="ascii")


LAYER_COLORS = {"CHANNEL": "#4472c4", "POSTS": "#c00000", "PORTS": "#70ad47"}


def write_svg(layout: Layout, path: Path) -> None:
    x0, y0, x1, y1 = layout.bounds()
    pad = 0.05 * max(x1 - x0, y1 - y0)
    x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="{x0 / MM:.4f} {-y1 / MM:.4f} {(x1 - x0) / MM:.4f} '
        f'{(y1 - y0) / MM:.4f}" width="800">'
    ]
    for rx0, ry0, rx1, ry1, layer in layout.rects:
        lines.append(
            f'<rect x="{rx0 / MM:.4f}" y="{-ry1 / MM:.4f}" '
            f'width="{(rx1 - rx0) / MM:.4f}" height="{(ry1 - ry0) / MM:.4f}" '
            f'fill="{LAYER_COLORS.get(layer, "#888")}" fill-opacity="0.85"/>')
    for cx, cy, r, layer in layout.circles:
        lines.append(
            f'<circle cx="{cx / MM:.4f}" cy="{-cy / MM:.4f}" r="{r / MM:.4f}" '
            f'fill="{LAYER_COLORS.get(layer, "#888")}" fill-opacity="0.85"/>')
    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="ascii")


# ----------------------------- Generators ----------------------------------


def gen_straight(args) -> Layout:
    lay = Layout()
    w = C.parse_quantity(args.width, "length")
    length = C.parse_quantity(args.length, "length")
    port = 0.5 * C.parse_quantity(args.port_diameter, "length")
    lay.rect(0.0, -w / 2, length, w / 2)
    lay.circle(0.0, 0.0, port)
    lay.circle(length, 0.0, port)
    return lay


def gen_serpentine(args) -> Layout:
    lay = Layout()
    w = C.parse_quantity(args.width, "length")
    seg = C.parse_quantity(args.segment_length, "length")
    pitch = C.parse_quantity(args.pitch, "length")
    if pitch < 2.0 * w:
        raise C.InputError("pitch must be at least 2x the channel width")
    port = 0.5 * C.parse_quantity(args.port_diameter, "length")
    for i in range(args.turns + 1):
        y = i * pitch
        lay.rect(0.0, y - w / 2, seg, y + w / 2)
        if i < args.turns:
            x_conn = seg if i % 2 == 0 else 0.0
            lay.rect(x_conn - w / 2, y - w / 2, x_conn + w / 2, y + pitch + w / 2)
    lay.circle(0.0, 0.0, port)
    end_x = seg if args.turns % 2 == 0 else 0.0
    lay.circle(end_x, args.turns * pitch, port)
    return lay


def gen_t_junction(args) -> Layout:
    lay = Layout()
    w_main = C.parse_quantity(args.width, "length")
    w_side = C.parse_quantity(args.side_width, "length")
    l_main = C.parse_quantity(args.length, "length")
    l_side = C.parse_quantity(args.side_length, "length")
    port = 0.5 * C.parse_quantity(args.port_diameter, "length")
    junction_x = 0.3 * l_main
    lay.rect(0.0, -w_main / 2, l_main, w_main / 2)
    lay.rect(junction_x - w_side / 2, w_main / 2 - w_main,
             junction_x + w_side / 2, l_side)
    lay.circle(0.0, 0.0, port)
    lay.circle(l_main, 0.0, port)
    lay.circle(junction_x, l_side, port)
    return lay


def gen_flow_focusing(args) -> Layout:
    lay = Layout()
    w = C.parse_quantity(args.width, "length")
    orifice = C.parse_quantity(args.orifice, "length")
    l_in = C.parse_quantity(args.inlet_length, "length")
    l_out = C.parse_quantity(args.outlet_length, "length")
    l_orifice = C.parse_quantity(args.orifice_length, "length")
    port = 0.5 * C.parse_quantity(args.port_diameter, "length")
    lay.rect(-l_in, -w / 2, 0.0, w / 2)                       # dispersed inlet
    lay.rect(-w / 2, -l_in, w / 2, l_in)                      # two sheath inlets
    lay.rect(0.0, -orifice / 2, l_orifice, orifice / 2)       # orifice
    lay.rect(l_orifice, -w / 2, l_orifice + l_out, w / 2)     # outlet
    lay.circle(-l_in, 0.0, port)
    lay.circle(0.0, l_in, port)
    lay.circle(0.0, -l_in, port)
    lay.circle(l_orifice + l_out, 0.0, port)
    return lay


def gen_dld(args) -> Layout:
    lay = Layout()
    gap = C.parse_quantity(args.gap, "length")
    post = C.parse_quantity(args.post_diameter, "length")
    eps = args.row_shift_fraction
    rows, cols = args.rows, args.columns
    pitch = gap + post
    margin = pitch
    width = (cols - 1) * pitch + post + 2.0 * margin
    height = (rows - 1) * pitch + post + 2.0 * margin
    lay.rect(0.0, 0.0, width, height)
    for row in range(rows):
        shift = (row * eps * pitch) % pitch
        for col in range(cols):
            lay.circle(margin + post / 2 + col * pitch + shift,
                       margin + post / 2 + row * pitch,
                       post / 2, layer="POSTS")
    return lay


# ------------------------------- CLI ---------------------------------------


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", required=True, help="DXF path to write")
    parser.add_argument("--svg", help="also write an SVG preview here")
    sub = parser.add_subparsers(dest="motif", required=True)

    st = sub.add_parser("straight", help="one channel, two ports")
    st.add_argument("--width", required=True)
    st.add_argument("--length", required=True)
    st.set_defaults(gen=gen_straight)

    serp = sub.add_parser("serpentine", help="folded channel")
    serp.add_argument("--width", required=True)
    serp.add_argument("--segment-length", required=True)
    serp.add_argument("--pitch", required=True, help="row spacing, >= 2x width")
    serp.add_argument("--turns", type=int, required=True)
    serp.set_defaults(gen=gen_serpentine)

    tj = sub.add_parser("t-junction", help="droplet T-junction")
    tj.add_argument("--width", required=True, help="main channel width")
    tj.add_argument("--side-width", required=True)
    tj.add_argument("--length", required=True, help="main channel length")
    tj.add_argument("--side-length", required=True)
    tj.set_defaults(gen=gen_t_junction)

    ff = sub.add_parser("flow-focusing", help="cross junction with orifice")
    ff.add_argument("--width", required=True, help="inlet/outlet width")
    ff.add_argument("--orifice", required=True)
    ff.add_argument("--orifice-length", default="100 um")
    ff.add_argument("--inlet-length", default="3 mm")
    ff.add_argument("--outlet-length", default="5 mm")
    ff.set_defaults(gen=gen_flow_focusing)

    dld = sub.add_parser("dld", help="DLD post array")
    dld.add_argument("--gap", required=True)
    dld.add_argument("--post-diameter", required=True)
    dld.add_argument("--row-shift-fraction", type=float, required=True)
    dld.add_argument("--rows", type=int, required=True)
    dld.add_argument("--columns", type=int, required=True)
    dld.set_defaults(gen=gen_dld)

    for sp in (st, serp, tj, ff, dld):
        sp.add_argument("--port-diameter", default="1.5 mm")
        C.add_common_args(sp)

    args = parser.parse_args(argv)
    out_path = Path(args.output)
    if out_path.suffix.lower() != ".dxf":
        raise C.InputError("--output must end in .dxf")

    layout = args.gen(args)
    write_dxf(layout, out_path)
    if args.svg:
        write_svg(layout, Path(args.svg))

    x0, y0, x1, y1 = layout.bounds()
    C.emit({
        "motif": args.motif,
        "dxf": str(out_path),
        "svg": str(args.svg) if args.svg else None,
        "rectangles": len(layout.rects),
        "circles": len(layout.circles),
        "bounding_box_mm": [round(v / MM, 4) for v in (x0, y0, x1, y1)],
        "min_feature_um": layout.min_feature() * 1e6,
        "units": "DXF coordinates are millimetres",
    }, args.format)
    print("caveat: run fabrication_check.py on these dimensions before "
          "ordering a mask; POSTS is a subtractive layer.", file=sys.stderr)
    return C.EXIT_OK


if __name__ == "__main__":
    C.run_cli(main)
