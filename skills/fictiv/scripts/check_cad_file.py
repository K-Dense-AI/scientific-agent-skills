#!/usr/bin/env python3
"""Pre-flight check for CAD files before uploading them to Fictiv.

Catches the problems that most often make a Fictiv upload fail, go to manual
review, or come back mis-scaled — before you spend a browser round-trip on it.

Usage:
    python3 check_cad_file.py PART.step [MORE FILES...] [--process cnc|3dp|sheet|urethane|im|compression|diecast] [--json]

Checks performed (standard library only, no CAD kernel needed):
  * extension accepted by Fictiv for the chosen process (mesh = 3D printing only;
    IGES / F3D / DXF / drawings-alone / assemblies are rejected)
  * STEP: schema, declared length unit, number of solid bodies (Fictiv needs
    exactly one), surface-only models, assemblies, approximate bounding box
  * STL: ascii/binary, triangle count, watertightness (every edge shared by
    exactly two triangles), bounding box, and a units sanity guess
  * PDF: reminds you a drawing must accompany a CAD file
  * rough size vs. Fictiv's published max build envelopes

Exit code: 0 = no blocking problems, 1 = at least one blocking problem.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import struct
import sys
from collections import Counter

# Extensions the upload widget accepts for non-3DP processes (read from the
# <input type=file accept=...> attribute on app.fictiv.com, Sep 2026).
PARAMETRIC = {
    ".3dm", ".3dxml", ".3mf", ".acs", ".arc", ".cgr", ".catpart", ".catshape", ".dlv",
    ".exp", ".gts", ".ifc", ".ifczip", ".ipt", ".jt", ".mf1", ".model", ".neu", ".par",
    ".pkg", ".prc", ".prt", ".psm", ".pwd", ".sab", ".sat", ".session", ".sldprt", ".step",
    ".stp", ".u3d", ".unv", ".vda", ".wrl", ".x3dv", ".x_b", ".x_t", ".xas", ".xmt",
    ".xmt_txt", ".xpr",
}
# Mesh formats: 3D printing only.
MESH = {".stl", ".3ds", ".collada", ".dae", ".obj", ".off", ".ply", ".v3d", ".pts",
        ".tri", ".acs", ".x3d", ".wrl"}
ASSEMBLY = {".sldasm", ".asm", ".iam", ".catproduct"}
UNSUPPORTED = {".igs": "IGES", ".iges": "IGES", ".f3d": "Fusion 360 archive",
               ".slddrw": "SolidWorks drawing", ".dxf": "DXF", ".dwg": "DWG",
               ".catdrawing": "CATIA drawing"}

# Published max envelopes in mm (largest first); used only for a soft warning.
MAX_ENVELOPE_MM = {
    "cnc": (1828, 500, 152),        # mill, per Help Center; larger parts via sales
    "3dp": (914, 610, 914),         # largest FDM; other technologies are smaller
    "urethane": (2200, 1200, 1000),
    "compression": (1000, 600, 600),
}
PROCESSES = ["cnc", "3dp", "sheet", "urethane", "im", "compression", "diecast"]


def human(n: float) -> str:
    return f"{n / 1e6:.1f} MB" if n >= 1e6 else f"{n / 1e3:.0f} KB"


# ---------------------------------------------------------------- STEP ----
def inspect_step(path: str) -> dict:
    info: dict = {}
    with open(path, "r", errors="ignore") as fh:
        data = fh.read()
    head = data[:5000]
    m = re.search(r"FILE_SCHEMA\s*\(\s*\(\s*'([^']+)'", head)
    info["schema"] = m.group(1) if m else None
    ents = Counter(re.findall(r"#\d+\s*=\s*([A-Z_0-9]+)\s*\(", data))
    solids = ents["MANIFOLD_SOLID_BREP"] + ents["BREP_WITH_VOIDS"]
    info["solid_bodies"] = solids
    info["surface_models"] = ents["SHELL_BASED_SURFACE_MODEL"] + ents["OPEN_SHELL"]
    info["products"] = ents["PRODUCT"]
    info["assembly_links"] = ents["NEXT_ASSEMBLY_USAGE_OCCURRENCE"]

    # Units: look for CONVERSION_BASED_UNIT('INCH'...) or SI_UNIT(.MILLI.,.METRE.)
    if re.search(r"CONVERSION_BASED_UNIT\s*\(\s*'(INCH|IN)'", data, re.I):
        info["length_unit"] = "inch"
    elif re.search(r"SI_UNIT\s*\(\s*\.MILLI\.\s*,\s*\.METRE\.", data):
        info["length_unit"] = "mm"
    elif re.search(r"SI_UNIT\s*\(\s*\.CENTI\.\s*,\s*\.METRE\.", data):
        info["length_unit"] = "cm"
    elif re.search(r"SI_UNIT\s*\(\s*\$\s*,\s*\.METRE\.", data):
        info["length_unit"] = "m"
    else:
        info["length_unit"] = "unknown"

    # Approximate bounding box from the B-rep's vertex points. Axis placements
    # and surface origins are also CARTESIAN_POINTs and can sit outside the
    # solid, so only fall back to "all points" when there are no vertices.
    # Parts bounded purely by curved faces (e.g. a sphere) can read small.
    allpts = dict(re.findall(r"#(\d+)\s*=\s*CARTESIAN_POINT\s*\(\s*'[^']*'\s*,\s*\(\s*([-\d.E+]+\s*,\s*[-\d.E+]+\s*,\s*[-\d.E+]+)\s*\)", data))
    vids = re.findall(r"VERTEX_POINT\s*\(\s*'[^']*'\s*,\s*#(\d+)\s*\)", data)
    chosen = [allpts[i] for i in vids if i in allpts] or list(allpts.values())
    pts = [tuple(s.strip() for s in p.split(",")) for p in chosen]
    if pts:
        xs, ys, zs = zip(*((float(a), float(b), float(c)) for a, b, c in pts))
        scale = {"inch": 25.4, "mm": 1.0, "cm": 10.0, "m": 1000.0}.get(info["length_unit"], 1.0)
        dims = sorted(((max(v) - min(v)) * scale for v in (xs, ys, zs)), reverse=True)
        info["approx_bbox_mm"] = [round(d, 2) for d in dims]
    if re.search(r"\bITAR\b|ITAR[- ]CONTROLLED|22 CFR 120", data, re.I):
        info["itar_marking"] = True
    return info


# ----------------------------------------------------------------- STL ----
def inspect_stl(path: str, max_tris: int = 3_000_000) -> dict:
    info: dict = {}
    size = os.path.getsize(path)
    with open(path, "rb") as fh:
        header = fh.read(84)
        is_binary = False
        if len(header) == 84:
            n = struct.unpack("<I", header[80:84])[0]
            is_binary = 84 + n * 50 == size
        tris = []
        if is_binary:
            info["encoding"] = "binary"
            info["triangles"] = n
            if n <= max_tris:
                for _ in range(n):
                    rec = fh.read(50)
                    v = struct.unpack("<12f", rec[:48])
                    tris.append((v[3:6], v[6:9], v[9:12]))
        else:
            info["encoding"] = "ascii"
            fh.seek(0)
            verts = re.findall(rb"vertex\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)", fh.read())
            vv = [tuple(float(c) for c in v) for v in verts]
            tris = [tuple(vv[i:i + 3]) for i in range(0, len(vv) - 2, 3)]
            info["triangles"] = len(tris)
    if tris:
        xs = [p[0] for t in tris for p in t]
        ys = [p[1] for t in tris for p in t]
        zs = [p[2] for t in tris for p in t]
        info["bbox_units"] = sorted([round(max(a) - min(a), 3) for a in (xs, ys, zs)], reverse=True)
        edges: Counter = Counter()
        for t in tris:
            k = [tuple(round(c, 5) for c in p) for p in t]
            for a, b in ((k[0], k[1]), (k[1], k[2]), (k[2], k[0])):
                edges[(a, b) if a < b else (b, a)] += 1
        bad = sum(1 for c in edges.values() if c != 2)
        info["non_manifold_or_open_edges"] = bad
        info["watertight"] = bad == 0
    elif info.get("triangles", 0) > max_tris:
        info["note"] = "too many triangles to check watertightness quickly"
    return info


# -------------------------------------------------------------- driver ----
def check(path: str, process: str) -> dict:
    ext = os.path.splitext(path)[1].lower()
    r = {"file": path, "extension": ext, "process": process, "blocking": [], "warnings": [], "info": {}}
    if not os.path.isfile(path):
        r["blocking"].append("file not found")
        return r
    size = os.path.getsize(path)
    r["info"]["size"] = human(size)
    if size == 0:
        r["blocking"].append("file is empty")
    if size > 100e6:
        r["warnings"].append("very large file (>100 MB); Fictiv documents no limit but uploads may time out — "
                             "try STEP or a lighter mesh")

    if ext in UNSUPPORTED:
        r["blocking"].append(f"{UNSUPPORTED[ext]} ({ext}) is not accepted by Fictiv — export STEP (.step) "
                             "or a native part file instead")
    elif ext in ASSEMBLY:
        r["blocking"].append("assembly files are only accepted as BOM reference and cannot be quoted — "
                             "export each part as its own single-body STEP")
    elif ext == ".pdf":
        r["warnings"].append("PDF drawings cannot be quoted alone; attach it to its CAD part "
                             "(Configure > Technical drawing > Upload drawing) or upload it together with the CAD file")
    elif ext in MESH and ext not in PARAMETRIC:
        if process != "3dp":
            r["blocking"].append(f"mesh files ({ext}) are accepted for 3D printing only; "
                                 f"{process} needs STEP or native CAD")
    elif ext not in PARAMETRIC:
        r["blocking"].append(f"unrecognized extension {ext}; Fictiv will not accept it")

    if ext == ".prt":
        r["warnings"].append(".prt is ambiguous (Siemens NX vs PTC Creo); if upload fails, export STEP")
    if ext == ".sldprt":
        r["warnings"].append("SolidWorks files with multiple configurations are rejected — save a single configuration")

    if ext in (".step", ".stp"):
        s = inspect_step(path)
        r["info"].update(s)
        if s["solid_bodies"] == 0 and s["surface_models"]:
            r["blocking"].append("STEP contains only surface geometry (no closed solid) — Fictiv needs a solid body")
        elif s["solid_bodies"] == 0:
            r["blocking"].append("no solid body found in STEP")
        elif s["solid_bodies"] > 1:
            msg = (f"{s['solid_bodies']} solid bodies in one file — Fictiv expects exactly one; multi-body files "
                   "lose instant pricing ('Please request a quote') and hold up the whole quote. Split into one file per part")
            (r["warnings"] if process == "3dp" else r["blocking"]).append(msg)
        if s["assembly_links"]:
            r["warnings"].append("STEP is structured as an assembly; export the single part instead")
        if s["length_unit"] == "unknown":
            r["warnings"].append("could not determine STEP length unit; check the size Fictiv shows after upload")
        if s.get("itar_marking"):
            r["blocking"].append("file text contains ITAR markings — Fictiv does not accept ITAR data; do not upload")
    elif ext == ".stl":
        s = inspect_stl(path)
        r["info"].update(s)
        if s.get("watertight") is False:
            r["warnings"].append(f"mesh is not watertight ({s['non_manifold_or_open_edges']} open/non-manifold edges) — "
                                 "repair it (e.g. Netfabb, Meshmixer) or re-export from the solid modeler")
        bb = s.get("bbox_units")
        if bb:
            if bb[0] < 5:
                r["warnings"].append(f"largest dimension is {bb[0]} units — if the part is really in inches, choose "
                                     "inches at upload or it will be 25.4x too small")
            if bb[0] > 1500:
                r["warnings"].append(f"largest dimension is {bb[0]} units — check units (metres/mm mix-up?)")
            r["info"]["bbox_if_mm"] = bb
            r["info"]["bbox_if_inch_in_mm"] = [round(v * 25.4, 2) for v in bb]

    bbox = r["info"].get("approx_bbox_mm")
    env = MAX_ENVELOPE_MM.get(process)
    # bbox is sorted largest-first, so compare against the envelope sorted the
    # same way: the part may be oriented to fit, whatever the machine axes are.
    if bbox and env and any(b > e for b, e in zip(bbox, sorted(env, reverse=True))):
        r["warnings"].append(f"approx size {bbox} mm exceeds Fictiv's published {process} envelope {list(env)} mm — "
                             "expect manual review/sales involvement, or split the part")
    return r


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--process", choices=PROCESSES, default="cnc")
    ap.add_argument("--json", action="store_true", help="print machine-readable JSON")
    a = ap.parse_args()
    results = [check(f, a.process) for f in a.files]
    if a.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            status = "BLOCKED" if r["blocking"] else ("WARN" if r["warnings"] else "OK")
            print(f"[{status}] {r['file']}  ({a.process})")
            for k, v in r["info"].items():
                print(f"    {k}: {v}")
            for b in r["blocking"]:
                print(f"    [FAIL] {b}")
            for w in r["warnings"]:
                print(f"    ! {w}")
    return 1 if any(r["blocking"] for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
