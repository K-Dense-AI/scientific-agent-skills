"""Add a slide to a PPTX: duplicate an existing slide or instantiate a layout.

Does all of the package bookkeeping, so the deck stays valid:
  - writes the new ppt/slides/slideN.xml (and its .rels, minus any
    notesSlide reference, so the source's speaker notes aren't shared)
  - registers it in [Content_Types].xml
  - adds a slide relationship with a fresh rId to presentation.xml.rels
  - inserts <p:sldId id="..." r:id="..."/> with a fresh id into
    <p:sldIdLst> — at the end, or after --after SLIDE

Works on an unpacked directory (during an editing session) or directly on a
.pptx/.potx file (extracted to a temp dir, then rezipped atomically; the
temp dir is discarded, so unpack the output if you still need to edit the
new slide's content).

Usage:
    python add_slide.py unpacked/ slide2.xml                 # duplicate slide2
    python add_slide.py unpacked/ slideLayout3.xml           # new slide from a layout
    python add_slide.py unpacked/ slide2.xml --after slide2.xml
    python add_slide.py deck.pptx slide2.xml                 # rewrite deck.pptx in place
    python add_slide.py deck.pptx slide2.xml -o out.pptx

A duplicated slide still holds the source's content: edit ppt/slides/slideN.xml
(printed on success) to change it. To list layouts: ls <dir>/ppt/slideLayouts/
"""

import argparse
import re
import shutil
import sys
from typing import NoReturn
import tempfile
import zipfile
from pathlib import Path

import defusedxml.minidom
from xml.parsers.expat import ExpatError

from office.helpers import SLIDE_REL_TYPE, opc_target, rezip, safe_extract

PRESENTATION_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT_TYPES_NS = "http://schemas.openxmlformats.org/package/2006/content-types"

MINIMAL_SLIDE_XML = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id="1" name=""/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm>
          <a:off x="0" y="0"/>
          <a:ext cx="0" cy="0"/>
          <a:chOff x="0" y="0"/>
          <a:chExt cx="0" cy="0"/>
        </a:xfrm>
      </p:grpSpPr>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr>
    <a:masterClrMapping/>
  </p:clrMapOvr>
</p:sld>'''

SHARED_PART_TYPES = ("chart", "diagramData", "oleObject", "package")

SLIDE_ID_MIN = 256
SLIDE_ID_MAX = 2147483647


def _die(msg: str) -> NoReturn:
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def get_next_slide_number(slides_dir: Path) -> int:
    existing = [int(m.group(1)) for f in slides_dir.glob("slide*.xml")
                if (m := re.match(r"slide(\d+)\.xml", f.name))]
    return max(existing) + 1 if existing else 1


def parse_source(source: str) -> tuple[str, str | None]:
    if source.startswith("slideLayout") and source.endswith(".xml"):
        return ("layout", source)

    return ("slide", None)


def create_slide_from_layout(unpacked_dir: Path, layout_file: str, after: str | None = None) -> str:
    slides_dir = unpacked_dir / "ppt" / "slides"
    rels_dir = slides_dir / "_rels"
    layout_path = unpacked_dir / "ppt" / "slideLayouts" / layout_file

    if not layout_path.exists():
        _die(f"{layout_path} not found")

    next_num = get_next_slide_number(slides_dir)
    dest = f"slide{next_num}.xml"
    after_rid = _precheck_registration(unpacked_dir, after, dest)
    slides_dir.mkdir(parents=True, exist_ok=True)

    (slides_dir / dest).write_text(MINIMAL_SLIDE_XML, encoding="utf-8")

    rels_dir.mkdir(exist_ok=True)
    rels_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/{layout_file}"/>
</Relationships>'''
    (rels_dir / f"{dest}.rels").write_text(rels_xml, encoding="utf-8")

    _register_slide(unpacked_dir, dest, layout_file, after_rid)
    return dest


def duplicate_slide(unpacked_dir: Path, source: str, after: str | None = None) -> str:
    slides_dir = unpacked_dir / "ppt" / "slides"
    rels_dir = slides_dir / "_rels"
    source_slide = slides_dir / source

    if not source_slide.exists():
        _die(f"{source_slide} not found")

    next_num = get_next_slide_number(slides_dir)
    dest = f"slide{next_num}.xml"
    after_rid = _precheck_registration(unpacked_dir, after, dest)

    source_rels = rels_dir / f"{source}.rels"
    if source_rels.exists():
        _read_xml(source_rels, PACKAGE_REL_NS, "Relationships")
    shutil.copy2(source_slide, slides_dir / dest)

    source_rels = rels_dir / f"{source}.rels"
    shared_parts: list[str] = []
    if source_rels.exists():
        dest_rels = rels_dir / f"{dest}.rels"
        shutil.copy2(source_rels, dest_rels)
        dom = defusedxml.minidom.parse(str(dest_rels))
        for rel in list(dom.getElementsByTagNameNS(PACKAGE_REL_NS, "Relationship")):
            kind = rel.getAttribute("Type").rsplit("/", 1)[-1]
            if kind == "notesSlide":
                rel.parentNode.removeChild(rel)
            elif kind in SHARED_PART_TYPES:
                shared_parts.append(kind)
        _write_xml(dest_rels, dom)
        shared_parts = sorted(set(shared_parts))

    _register_slide(unpacked_dir, dest, source, after_rid)
    if shared_parts:
        print(
            f"Note: {dest} shares its {', '.join(shared_parts)} part(s) with {source} "
            f"(they are referenced, not copied) — editing those parts changes both slides"
        )
    return dest


def _read_xml(path: Path, namespace: str, root_name: str):
    dom = defusedxml.minidom.parse(str(path))
    root = dom.documentElement
    if (root.namespaceURI, root.localName) != (namespace, root_name):
        raise ValueError(f"unsupported XML root in {path.name}")
    return dom


def _write_xml(path: Path, dom) -> None:
    path.write_bytes(dom.toxml(encoding="utf-8"))


def _element(dom, namespace: str, name: str):
    prefix = dom.documentElement.prefix
    return dom.createElementNS(namespace, f"{prefix}:{name}" if prefix else name)


def _slide_ids(dom):
    return list(dom.getElementsByTagNameNS(PRESENTATION_NS, "sldId"))


def _precheck_registration(unpacked_dir: Path, after: str | None, dest: str) -> str | None:
    pres = _read_xml(unpacked_dir / "ppt/presentation.xml", PRESENTATION_NS, "presentation")
    ct = _read_xml(unpacked_dir / "[Content_Types].xml", CONTENT_TYPES_NS, "Types")
    rels_path = unpacked_dir / "ppt/_rels/presentation.xml.rels"
    rels = _read_xml(rels_path, PACKAGE_REL_NS, "Relationships")
    stale = any(opc_target(n.getAttribute("PartName"), "") == f"ppt/slides/{dest}"
                for n in ct.getElementsByTagNameNS(CONTENT_TYPES_NS, "Override"))
    if stale or _find_slide_relationship(rels.toxml(), dest):
        _die(f"{dest} is still registered but absent from ppt/slides/; run clean.py first")
    ids = [n.getAttribute("Id") for n in rels.getElementsByTagNameNS(PACKAGE_REL_NS, "Relationship")]
    if len(ids) != len(set(ids)) or "" in ids:
        _die("presentation relationships have duplicate or missing Id values")
    _get_next_slide_id(unpacked_dir)  # Check ID syntax before any file is written.
    if not after:
        return None
    after_rid = _rid_for_slide(unpacked_dir, after)
    if not any(n.getAttributeNS(OFFICE_REL_NS, "id") == after_rid for n in _slide_ids(pres)):
        _die(f"{after} ({after_rid}) is not listed in the slide list")
    return after_rid


def _register_slide(unpacked_dir: Path, dest: str, source_desc: str, after_rid: str | None) -> None:
    slide_id = _get_next_slide_id(unpacked_dir)
    _add_to_content_types(unpacked_dir, dest)
    rid = _add_to_presentation_rels(unpacked_dir, dest)
    pos, total = _insert_into_sld_id_lst(unpacked_dir, slide_id, rid, after_rid)
    print(f"Created ppt/slides/{dest} from {source_desc}")
    print(f'Inserted slide id="{slide_id}" r:id="{rid}" at position {pos} of {total}')


def _add_to_content_types(unpacked_dir: Path, dest: str) -> None:
    path = unpacked_dir / "[Content_Types].xml"
    dom = _read_xml(path, CONTENT_TYPES_NS, "Types")
    node = _element(dom, CONTENT_TYPES_NS, "Override")
    node.setAttribute("PartName", f"/ppt/slides/{dest}")
    node.setAttribute("ContentType", "application/vnd.openxmlformats-officedocument.presentationml.slide+xml")
    dom.documentElement.appendChild(node)
    _write_xml(path, dom)


def _add_to_presentation_rels(unpacked_dir: Path, dest: str) -> str:
    path = unpacked_dir / "ppt/_rels/presentation.xml.rels"
    dom = _read_xml(path, PACKAGE_REL_NS, "Relationships")
    existing = _find_slide_relationship(dom.toxml(), dest)
    if existing:
        return existing
    used = {n.getAttribute("Id") for n in dom.getElementsByTagNameNS(PACKAGE_REL_NS, "Relationship")}
    pres = _read_xml(unpacked_dir / "ppt/presentation.xml", PRESENTATION_NS, "presentation")
    used.update(n.getAttributeNS(OFFICE_REL_NS, "id") for n in _slide_ids(pres))
    num = max((int(m.group(1)) for rid in used if (m := re.fullmatch(r"rId(\d+)", rid))), default=0) + 1
    rid = f"rId{num}"
    node = _element(dom, PACKAGE_REL_NS, "Relationship")
    for key, value in {"Id": rid, "Type": SLIDE_REL_TYPE, "Target": f"slides/{dest}"}.items():
        node.setAttribute(key, value)
    dom.documentElement.appendChild(node)
    _write_xml(path, dom)
    return rid


def _find_slide_relationship(pres_rels: str, slide_name: str) -> str | None:
    dom = defusedxml.minidom.parseString(pres_rels)
    for node in dom.getElementsByTagNameNS(PACKAGE_REL_NS, "Relationship"):
        if node.getAttribute("Type") != SLIDE_REL_TYPE:
            continue
        part = opc_target(node.getAttribute("Target"), "ppt/presentation.xml", node.getAttribute("TargetMode"))
        if part == f"ppt/slides/{slide_name}":
            return node.getAttribute("Id")
    return None


def _get_next_slide_id(unpacked_dir: Path) -> int:
    dom = _read_xml(unpacked_dir / "ppt/presentation.xml", PRESENTATION_NS, "presentation")
    used = {int(n.getAttribute("id")) for n in _slide_ids(dom)}
    candidate = max((i for i in used if i >= SLIDE_ID_MIN), default=SLIDE_ID_MIN - 1) + 1
    if candidate <= SLIDE_ID_MAX:
        return candidate
    for i in range(SLIDE_ID_MIN, SLIDE_ID_MAX + 1):
        if i not in used:
            return i
    _die("no slide id available in [256, 2147483647]")


def _insert_into_sld_id_lst(
    unpacked_dir: Path, slide_id: int, rid: str, after_rid: str | None = None
) -> tuple[int, int]:
    path = unpacked_dir / "ppt/presentation.xml"
    dom = _read_xml(path, PRESENTATION_NS, "presentation")
    entries = _slide_ids(dom)
    if any(n.getAttributeNS(OFFICE_REL_NS, "id") == rid for n in entries):
        _die(f"presentation.xml already references {rid}")
    lists = dom.getElementsByTagNameNS(PRESENTATION_NS, "sldIdLst")
    if lists:
        slide_list = lists[0]
    else:
        slide_list = _element(dom, PRESENTATION_NS, "sldIdLst")
        # Keep existing children in place, inserting after any master ID lists.
        successors = [n for n in dom.documentElement.childNodes
                      if n.nodeType == n.ELEMENT_NODE and n.localName not in
                      ("sldMasterIdLst", "notesMasterIdLst", "handoutMasterIdLst")]
        dom.documentElement.insertBefore(slide_list, successors[0] if successors else None)
    node = _element(dom, PRESENTATION_NS, "sldId")
    node.setAttribute("id", str(slide_id))
    node.setAttribute("xmlns:r", OFFICE_REL_NS)
    node.setAttributeNS(OFFICE_REL_NS, "r:id", rid)
    if after_rid:
        anchor = next((n for n in entries if n.getAttributeNS(OFFICE_REL_NS, "id") == after_rid), None)
        if anchor is None:
            _die(f"{after_rid} is not listed in the slide list")
        slide_list.insertBefore(node, anchor.nextSibling)
    else:
        slide_list.appendChild(node)
    _write_xml(path, dom)
    entries = _slide_ids(dom)
    return entries.index(node) + 1, len(entries)


def _rid_for_slide(unpacked_dir: Path, slide_name: str) -> str:
    path = unpacked_dir / "ppt/_rels/presentation.xml.rels"
    rid = _find_slide_relationship(path.read_text(encoding="utf-8"), slide_name)
    if not rid:
        _die(f"{slide_name} has no slide relationship in presentation.xml.rels")
    return rid


def add_slide(unpacked_dir: Path, source: str, after: str | None = None) -> str:
    if not re.fullmatch(r"slide(?:Layout)?[0-9]+\.xml", source):
        _die("source must be a slideN.xml or slideLayoutN.xml filename")
    if after and not re.fullmatch(r"slide[0-9]+\.xml", after):
        _die("--after must be a slideN.xml filename")
    source_type, layout_file = parse_source(source)
    if source_type == "layout" and layout_file is not None:
        return create_slide_from_layout(unpacked_dir, layout_file, after)
    return duplicate_slide(unpacked_dir, source, after)


def add_slide_to_package(
    package: Path, source: str, after: str | None = None, output: Path | None = None
) -> str:
    out = output or package
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(package) as zf:
            safe_extract(zf, tmp_path)
        dest = add_slide(tmp_path, source, after)
        rezip(tmp_path, out)
    print(f"Wrote {out} — the new slide is ppt/slides/{dest} inside it (unpack to edit its content)")
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add a slide to a PPTX: duplicate a slide or instantiate a layout. "
        "Registers content types, relationships, and <p:sldIdLst>."
    )
    parser.add_argument("target", help="Unpacked PPTX directory OR a .pptx/.potx file")
    parser.add_argument(
        "source",
        help="slideN.xml to duplicate, or slideLayoutN.xml to create from a layout "
        "(list layouts with: ls <dir>/ppt/slideLayouts/)",
    )
    parser.add_argument(
        "--after",
        metavar="SLIDE",
        help="insert after this slide, e.g. slide2.xml (default: append at the end)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="output file (only with a .pptx/.potx target; default: rewrite the input in place)",
    )
    args = parser.parse_args()

    target = Path(args.target)
    if target.is_dir():
        if args.output:
            parser.error("--output is only valid for .pptx/.potx input; a directory is modified in place")
        add_slide(target, args.source, args.after)
    elif target.is_file() and target.suffix.lower() in (".pptx", ".potx"):
        try:
            add_slide_to_package(target, args.source, args.after, Path(args.output) if args.output else None)
        except (OSError, ValueError, ExpatError, zipfile.BadZipFile) as e:
            _die(str(e))
    else:
        _die(f"{target} is neither a directory nor a .pptx/.potx file")


if __name__ == "__main__":
    main()
