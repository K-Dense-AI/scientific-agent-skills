"""Remove unreferenced files from an unpacked PPTX directory.

Usage: python clean.py <unpacked_dir>

Example:
    python clean.py unpacked/

This script removes:
- Orphaned slides (not in sldIdLst) and their relationships
- [trash] directory (unreferenced files)
- Orphaned .rels files for deleted resources
- Unreferenced media, embeddings, charts, diagrams, drawings, ink files
- Unreferenced theme files
- Unreferenced notes slides
- Content-Type overrides for deleted files
"""

import posixpath
import sys
from pathlib import Path
from xml.parsers.expat import ExpatError

import defusedxml.minidom

from office.helpers import SLIDE_REL_TYPE, opc_target, rels_source_part

PRESENTATION_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT_TYPES_NS = "http://schemas.openxmlformats.org/package/2006/content-types"


class RefusedToClean(Exception):
    """The package does not look the way a readable package should."""


def _slide_rids(pres_rels_path: Path, unpacked_dir: Path) -> dict[str, str]:
    source_part = rels_source_part(pres_rels_path, unpacked_dir)
    rels_dom = defusedxml.minidom.parse(str(pres_rels_path))

    rids: dict[str, str] = {}
    for rel in rels_dom.getElementsByTagNameNS(PACKAGE_REL_NS, "Relationship"):
        if rel.getAttribute("Type") != SLIDE_REL_TYPE:
            continue
        part = opc_target(
            rel.getAttribute("Target"), source_part, rel.getAttribute("TargetMode")
        )
        if part is not None:
            rid = rel.getAttribute("Id")
            if not rid or rid in rids:
                raise RefusedToClean("missing or duplicate slide relationship Id")
            rids[rid] = part
    return rids


def get_slides_in_sldidlst(unpacked_dir: Path) -> set[str]:
    pres_path = unpacked_dir / "ppt" / "presentation.xml"
    pres_rels_path = unpacked_dir / "ppt" / "_rels" / "presentation.xml.rels"

    if not pres_path.is_file() or not pres_rels_path.is_file():
        raise RefusedToClean("presentation.xml and its relationships must both exist")

    rid_to_slide = _slide_rids(pres_rels_path, unpacked_dir)

    dom = defusedxml.minidom.parse(str(pres_path))
    root = dom.documentElement
    if root.namespaceURI != PRESENTATION_NS or root.localName != "presentation":
        raise RefusedToClean("unsupported or unrecognized presentation namespace")
    referenced = set()
    for node in dom.getElementsByTagNameNS(PRESENTATION_NS, "sldId"):
        rid = node.getAttributeNS(OFFICE_REL_NS, "id")
        part = rid_to_slide.get(rid)
        if part is None or not (unpacked_dir / part).is_file():
            raise RefusedToClean(f"listed slide {rid!r} has no existing internal slide target")
        if posixpath.dirname(part) != "ppt/slides":
            raise RefusedToClean(f"unsupported slide location: {part}")
        referenced.add(posixpath.basename(part))
    return referenced


def remove_orphaned_slides(unpacked_dir: Path) -> list[str]:
    slides_dir = unpacked_dir / "ppt" / "slides"
    slides_rels_dir = slides_dir / "_rels"
    pres_rels_path = unpacked_dir / "ppt" / "_rels" / "presentation.xml.rels"

    if not slides_dir.exists():
        return []

    referenced_slides = get_slides_in_sldidlst(unpacked_dir)
    on_disk = sorted(slides_dir.glob("slide*.xml"))

    removed = []

    for slide_file in on_disk:
        if slide_file.name not in referenced_slides:
            rel_path = slide_file.relative_to(unpacked_dir)
            slide_file.unlink()
            removed.append(str(rel_path))

            rels_file = slides_rels_dir / f"{slide_file.name}.rels"
            if rels_file.exists():
                rels_file.unlink()
                removed.append(str(rels_file.relative_to(unpacked_dir)))

    if removed and pres_rels_path.exists():
        rels_dom = defusedxml.minidom.parse(str(pres_rels_path))
        source_part = rels_source_part(pres_rels_path, unpacked_dir)
        changed = False

        for rel in list(rels_dom.getElementsByTagNameNS(PACKAGE_REL_NS, "Relationship")):
            if rel.getAttribute("Type") != SLIDE_REL_TYPE:
                continue
            part = opc_target(
                rel.getAttribute("Target"), source_part, rel.getAttribute("TargetMode")
            )
            if part is None:
                continue
            if posixpath.basename(part) not in referenced_slides:
                if rel.parentNode:
                    rel.parentNode.removeChild(rel)
                    changed = True

        if changed:
            with open(pres_rels_path, "wb") as f:
                f.write(rels_dom.toxml(encoding="utf-8"))

    return removed


def remove_trash_directory(unpacked_dir: Path) -> list[str]:
    trash_dir = unpacked_dir / "[trash]"
    removed = []

    if trash_dir.exists() and trash_dir.is_dir():
        for file_path in trash_dir.iterdir():
            if file_path.is_file():
                rel_path = file_path.relative_to(unpacked_dir)
                removed.append(str(rel_path))
                file_path.unlink()
        trash_dir.rmdir()

    return removed


def _referenced_by(rels_files, unpacked_dir: Path) -> set:
    referenced = set()

    for rels_file in rels_files:
        source_part = rels_source_part(rels_file, unpacked_dir)
        dom = defusedxml.minidom.parse(str(rels_file))
        if dom.documentElement.namespaceURI != PACKAGE_REL_NS:
            raise RefusedToClean(f"unsupported relationships namespace in {rels_file.name}")
        for rel in dom.getElementsByTagNameNS(PACKAGE_REL_NS, "Relationship"):
            part = opc_target(
                rel.getAttribute("Target"), source_part, rel.getAttribute("TargetMode")
            )
            if part is not None:
                referenced.add(Path(part))

    return referenced


def remove_orphaned_rels_files(unpacked_dir: Path) -> list[str]:
    resource_dirs = ["charts", "diagrams", "drawings"]
    removed = []

    for dir_name in resource_dirs:
        rels_dir = unpacked_dir / "ppt" / dir_name / "_rels"
        if not rels_dir.exists():
            continue

        for rels_file in rels_dir.glob("*.rels"):
            resource_file = rels_dir.parent / rels_file.name.replace(".rels", "")
            if not resource_file.exists():
                rels_file.unlink()
                removed.append(str(rels_file.relative_to(unpacked_dir)))

    return removed


def get_referenced_files(unpacked_dir: Path) -> set:
    return _referenced_by(sorted(unpacked_dir.rglob("*.rels")), unpacked_dir)


def remove_orphaned_files(unpacked_dir: Path, referenced: set) -> list[str]:
    resource_dirs = ["media", "embeddings", "charts", "diagrams", "tags", "drawings", "ink"]
    removed = []

    for dir_name in resource_dirs:
        dir_path = unpacked_dir / "ppt" / dir_name
        if not dir_path.exists():
            continue

        for file_path in dir_path.glob("*"):
            if not file_path.is_file():
                continue
            rel_path = file_path.relative_to(unpacked_dir)
            if rel_path not in referenced:
                file_path.unlink()
                removed.append(str(rel_path))

    theme_dir = unpacked_dir / "ppt" / "theme"
    if theme_dir.exists():
        for file_path in theme_dir.glob("theme*.xml"):
            rel_path = file_path.relative_to(unpacked_dir)
            if rel_path not in referenced:
                file_path.unlink()
                removed.append(str(rel_path))
                theme_rels = theme_dir / "_rels" / f"{file_path.name}.rels"
                if theme_rels.exists():
                    theme_rels.unlink()
                    removed.append(str(theme_rels.relative_to(unpacked_dir)))

    notes_dir = unpacked_dir / "ppt" / "notesSlides"
    if notes_dir.exists():
        for file_path in notes_dir.glob("*.xml"):
            if not file_path.is_file():
                continue
            rel_path = file_path.relative_to(unpacked_dir)
            if rel_path not in referenced:
                file_path.unlink()
                removed.append(str(rel_path))

        notes_rels_dir = notes_dir / "_rels"
        if notes_rels_dir.exists():
            for file_path in notes_rels_dir.glob("*.rels"):
                notes_file = notes_dir / file_path.name.replace(".rels", "")
                if not notes_file.exists():
                    file_path.unlink()
                    removed.append(str(file_path.relative_to(unpacked_dir)))

    return removed


def update_content_types(unpacked_dir: Path, removed_files: list[str]) -> None:
    ct_path = unpacked_dir / "[Content_Types].xml"
    if not ct_path.exists():
        return

    dom = defusedxml.minidom.parse(str(ct_path))
    changed = False

    for override in list(dom.getElementsByTagNameNS(CONTENT_TYPES_NS, "Override")):
        part_name = opc_target(override.getAttribute("PartName"), "")
        if part_name in removed_files:
            if override.parentNode:
                override.parentNode.removeChild(override)
                changed = True

    if changed:
        with open(ct_path, "wb") as f:
            f.write(dom.toxml(encoding="utf-8"))


def clean_unused_files(unpacked_dir: Path) -> list[str]:
    all_removed = []

    # Check all metadata before the first deletion, including content types,
    # which would otherwise be parsed only after slides had been removed.
    if any(path.is_symlink() for path in unpacked_dir.rglob("*")):
        raise RefusedToClean("clean an extracted package without symbolic links")
    ct_path = unpacked_dir / "[Content_Types].xml"
    if not ct_path.is_file():
        raise RefusedToClean("[Content_Types].xml is missing")
    ct = defusedxml.minidom.parse(str(ct_path))
    if ct.documentElement.namespaceURI != CONTENT_TYPES_NS:
        raise RefusedToClean("unsupported content-types namespace")
    for node in ct.getElementsByTagNameNS(CONTENT_TYPES_NS, "Override"):
        opc_target(node.getAttribute("PartName"), "")

    if list(unpacked_dir.rglob("*.rels")) and not get_referenced_files(unpacked_dir):
        raise RefusedToClean(
            "no relationship in this package names a part we can resolve. "
            "Refusing to treat every file as unreferenced."
        )

    slides_removed = remove_orphaned_slides(unpacked_dir)
    all_removed.extend(slides_removed)

    trash_removed = remove_trash_directory(unpacked_dir)
    all_removed.extend(trash_removed)

    while True:
        removed_rels = remove_orphaned_rels_files(unpacked_dir)
        referenced = get_referenced_files(unpacked_dir)
        removed_files = remove_orphaned_files(unpacked_dir, referenced)

        total_removed = removed_rels + removed_files
        if not total_removed:
            break

        all_removed.extend(total_removed)

    if all_removed:
        update_content_types(unpacked_dir, all_removed)

    return all_removed


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python clean.py <unpacked_dir>", file=sys.stderr)
        print("Example: python clean.py unpacked/", file=sys.stderr)
        sys.exit(1)

    unpacked_dir = Path(sys.argv[1])

    if not unpacked_dir.exists():
        print(f"Error: {unpacked_dir} not found", file=sys.stderr)
        sys.exit(1)

    try:
        removed = clean_unused_files(unpacked_dir)
    except (RefusedToClean, ValueError, OSError, ExpatError) as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Cleanup stopped; check the working copy before retrying.", file=sys.stderr)
        sys.exit(1)

    if removed:
        print(f"Removed {len(removed)} unreferenced files:")
        for f in removed:
            print(f"  {f}")
    else:
        print("No unreferenced files found")
