"""Fill validated AcroForm values using pypdf's current appearance generator."""
import json
import sys

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, NameObject, TextStringObject
from extract_form_field_info import get_field_info


def validation_error_for_field_value(info, value):
    field_type, name = info["type"], info["field_id"]
    prefix = f'ERROR: Invalid value for {field_type} field "{name}"'
    if info.get("read_only"):
        return f'ERROR: Field "{name}" is read-only'
    if field_type == "checkbox":
        if "checked_value" not in info:
            return f"{prefix}: unsupported appearance states"
        options = [info["checked_value"], info["unchecked_value"]]
    elif field_type == "radio_group":
        options = [option["value"] for option in info["radio_options"]]
    elif field_type == "choice":
        options = [option["value"] for option in info["choice_options"]]
        if isinstance(value, list):
            if not info.get("multi_select") or any(v not in options for v in value):
                return f"{prefix}: expected declared options for a multi-select list"
            return None
        if info.get("editable") and isinstance(value, str):
            return None
    elif field_type == "text":
        return None if isinstance(value, str) else f"{prefix}: expected a string"
    else:
        return f"{prefix}: this field type is not supported"
    if not isinstance(value, str) or value not in options:
        return f"{prefix}: valid values are {options}"
    return None


def fill_pdf_fields(input_pdf_path: str, fields_json_path: str, output_pdf_path: str):
    with open(fields_json_path, encoding="utf-8") as stream:
        fields = json.load(stream)
    reader = PdfReader(input_pdf_path)
    acroform = reader.trailer["/Root"].get("/AcroForm")
    if acroform and "/XFA" in acroform.get_object():
        raise ValueError("XFA forms require an XFA-capable workflow; do not treat them as AcroForms")
    available = {f["field_id"]: f for f in get_field_info(reader)}
    values = {}
    for field in fields:
        name = field["field_id"]
        if name not in available:
            raise ValueError(f"Unknown or hidden field: {name}")
        info = available[name]
        pages = {widget["page"] for widget in info["widgets"]}
        if field["page"] not in pages:
            raise ValueError(f"Incorrect page for {name}: expected one of {sorted(pages)}")
        if "value" not in field:
            continue
        value = field["value"]
        error = validation_error_for_field_value(info, value)
        if error:
            raise ValueError(error)
        if name in values and values[name] != value:
            raise ValueError(f"Conflicting values for repeated field: {name}")
        values[name] = value
    writer = PdfWriter(clone_from=reader)
    if values:
        # pypdf 6.19's appearance builder assumes /Opt contains plain strings.
        # Generate appearances from display labels, then restore export values/options.
        # This is scoped to this writer: do not monkeypatch DictionaryObject globally.
        display_values = dict(values)
        restore = []
        for name, field in writer.get_fields().items():
            if name not in values or available[name]["type"] != "choice":
                continue
            raw = field.indirect_reference.get_object()
            options = raw.get("/Opt")
            if not options:
                continue
            labels = {o["value"]: o["text"] for o in available[name]["choice_options"]}
            restore.append((raw, options, values[name]))
            raw[NameObject("/Opt")] = ArrayObject(TextStringObject(o["text"])
                                                  for o in available[name]["choice_options"])
            value = values[name]
            display_values[name] = ([labels.get(v, v) for v in value] if isinstance(value, list)
                                    else labels.get(value, value))
        try:
            # A shared field can have widgets on several pages; regenerate every widget.
            writer.update_page_form_field_values(None, display_values, auto_regenerate=False)
        finally:
            for raw, options, value in restore:
                raw[NameObject("/Opt")] = options
                raw[NameObject("/V")] = (ArrayObject(TextStringObject(v) for v in value)
                                          if isinstance(value, list) else TextStringObject(value))
    writer.write(output_pdf_path)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: fill_fillable_fields.py [input pdf] [field_values.json] [output pdf]")
        sys.exit(1)
    try:
        fill_pdf_fields(*sys.argv[1:])
    except (ValueError, KeyError, TypeError) as error:
        print(f"[FAIL] {error}", file=sys.stderr)
        sys.exit(1)
