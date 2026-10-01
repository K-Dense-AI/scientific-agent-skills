"""Inspect AcroForm fields and every visible widget (one-based pages)."""
import json
import sys

from pypdf import PdfReader


def get_full_annotation_field_id(annotation):
    components, seen = [], set()
    while annotation:
        annotation = annotation.get_object() if hasattr(annotation, "get_object") else annotation
        identity = id(annotation)
        if identity in seen:
            raise ValueError("Cyclic AcroForm parent chain")
        seen.add(identity)
        if annotation.get("/T"):
            components.append(str(annotation["/T"]))
        annotation = annotation.get("/Parent")
    return ".".join(reversed(components)) if components else None


def make_field_dict(field, field_id):
    result = {"field_id": field_id}
    ft, flags = field.get("/FT"), int(field.get("/Ff", 0))
    result["read_only"] = bool(flags & 1)
    if ft == "/Tx":
        result["type"] = "text"
    elif ft == "/Btn":
        if flags & (1 << 16):
            result["type"] = "pushbutton"
        elif flags & (1 << 15):
            result.update(type="radio_group", radio_options=[])
        else:
            result["type"] = "checkbox"
            states = field.get("/_States_", [])
            on = [str(s) for s in states if s != "/Off"]
            if len(on) == 1:
                result.update(checked_value=on[0], unchecked_value="/Off")
    elif ft == "/Ch":
        result.update(type="choice", multi_select=bool(flags & (1 << 21)),
                      editable=bool(flags & (1 << 18)))
        options = field.get("/Opt", field.get("/_States_", []))
        result["choice_options"] = [
            {"value": str(s[0]), "text": str(s[1])}
            if isinstance(s, (list, tuple)) and len(s) == 2
            else {"value": str(s), "text": str(s)} for s in options
        ]
    else:
        result["type"] = f"unknown ({ft})"
    return result


def get_field_info(reader: PdfReader):
    descriptors = {name: make_field_dict(field, name)
                   for name, field in (reader.get_fields() or {}).items()}
    for page_index, page in enumerate(reader.pages, 1):
        for ref in page.get("/Annots", []):
            annotation = ref.get_object()
            if annotation.get("/Subtype") != "/Widget":
                continue
            name = get_full_annotation_field_id(annotation)
            if name not in descriptors:
                continue
            descriptor = descriptors[name]
            rect = [float(v) for v in annotation.get("/Rect", [])]
            descriptor.setdefault("widgets", []).append({"page": page_index, "rect": rect})
            descriptor.setdefault("page", page_index)
            descriptor.setdefault("rect", rect)
            if descriptor["type"] in ("checkbox", "radio_group"):
                normal = annotation.get("/AP", {}).get("/N", {})
                normal = normal.get_object() if hasattr(normal, "get_object") else normal
                states = [str(v) for v in normal if v != "/Off"]
                if descriptor["type"] == "radio_group":
                    descriptor["radio_options"].extend(
                        {"value": v, "page": page_index, "rect": rect} for v in states)
                elif len(states) == 1:
                    descriptor.update(checked_value=states[0], unchecked_value="/Off")
    # Hidden values/nonterminal hierarchy nodes have no page to fill visually.
    result = [d for d in descriptors.values() if "widgets" in d]
    result.sort(key=lambda d: (d["page"], -d["rect"][1], d["rect"][0]))
    return result


def write_field_info(pdf_path: str, json_output_path: str):
    fields = get_field_info(PdfReader(pdf_path))
    with open(json_output_path, "w", encoding="utf-8") as stream:
        json.dump(fields, stream, indent=2)
    print(f"Wrote {len(fields)} visible fields to {json_output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: extract_form_field_info.py [input pdf] [output json]")
        sys.exit(1)
    write_field_info(sys.argv[1], sys.argv[2])
