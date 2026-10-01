"""Real PDFs verify AcroForm values, appearance streams, rendering, and coordinates."""
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pdf"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
pypdf = pytest.importorskip("pypdf")
pytest.importorskip("reportlab")
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, NameObject, TextStringObject
from extract_form_field_info import get_field_info, make_field_dict
from fill_fillable_fields import fill_pdf_fields, validation_error_for_field_value
from fill_pdf_form_with_annotations import fill_pdf_form


@pytest.fixture
def form(tmp_path):
    path = tmp_path / "form.pdf"
    c = canvas.Canvas(str(path), pagesize=(400, 400))
    f = c.acroForm
    c.drawString(20, 380, "Synthetic form")
    f.textfield(name="name", x=100, y=300, width=200, height=30)
    f.checkbox(name="check", x=100, y=260)
    f.radio(name="radio", value="A", x=100, y=220, selected=True)
    f.radio(name="radio", value="B", x=150, y=220)
    f.choice(name="choice", options=[("Alpha", "a"), ("Beta", "b")], value="a",
             x=100, y=160, width=200, height=30)
    f.choice(name="single", options=["First", "Second"], value="First",
             x=100, y=100, width=200, height=30)
    f.listbox(name="list", options=[("One", "one"), ("Two", "two")], value="one",
              fieldFlags="multiSelect", x=100, y=20, width=200, height=60)
    c.showPage()
    c.save()
    return path


def test_acroform_export_values_and_display_appearances(form, tmp_path):
    fields = {f["field_id"]: f for f in get_field_info(PdfReader(form))}
    assert fields["single"]["choice_options"][0] == {"value": "First", "text": "First"}
    assert fields["choice"]["choice_options"][1] == {"value": "b", "text": "Beta"}
    assert fields["radio"]["type"] == "radio_group"
    values = {"name": "Ada", "check": "/Yes", "radio": "/B", "choice": "b",
              "single": "Second", "list": ["one", "two"]}
    src = tmp_path / "values.json"
    src.write_text(json.dumps([{"field_id": k, "page": 1, "value": v} for k, v in values.items()]))
    out = tmp_path / "filled.pdf"
    fill_pdf_fields(form, src, out)
    reader = PdfReader(out)
    assert {k: v.get("/V") for k, v in reader.get_fields().items()} == values
    assert reader.trailer["/Root"]["/AcroForm"]["/NeedAppearances"].value is False
    widget = next(a.get_object() for a in reader.pages[0]["/Annots"] if a.get_object().get("/T") == "choice")
    assert b"Beta" in widget["/AP"]["/N"].get_data()
    assert widget["/Opt"][1] == ["b", "Beta"]
    if shutil.which("pdftoppm"):
        from pdf2image import convert_from_path
        image = convert_from_path(out, size=400)[0].convert("RGB")
        # The text field must contain dark pixels away from its border.
        crop = image.crop((102, 75, 150, 95))
        assert crop.convert("L").getextrema()[0] < 150


def test_repeated_widget_inventory_and_updates(form, tmp_path):
    writer = PdfWriter(clone_from=form)
    widget = writer.pages[0]["/Annots"][0].get_object()
    parent = DictionaryObject({NameObject(k): widget[k] for k in ("/T", "/FT", "/V", "/DA", "/Ff")})
    parent_ref = writer._add_object(parent)
    for key in ("/T", "/FT", "/V", "/DA", "/Ff"):
        del widget[key]
    widget[NameObject("/Parent")] = parent_ref
    other = DictionaryObject(widget)
    other_ref = writer._add_object(other)
    page = writer.add_blank_page(width=400, height=400)
    page[NameObject("/Annots")] = ArrayObject([other_ref])
    other[NameObject("/P")] = page.indirect_reference
    parent[NameObject("/Kids")] = ArrayObject([widget.indirect_reference, other_ref])
    writer.root_object["/AcroForm"]["/Fields"][0] = parent_ref
    repeated = tmp_path / "repeated.pdf"
    writer.write(repeated)
    info = next(f for f in get_field_info(PdfReader(repeated)) if f["field_id"] == "name")
    assert [w["page"] for w in info["widgets"]] == [1, 2]
    values = tmp_path / "repeat.json"
    values.write_text(json.dumps([{"field_id": "name", "page": 2, "value": "Both pages"}]))
    result = tmp_path / "result.pdf"
    fill_pdf_fields(repeated, values, result)
    reader = PdfReader(result)
    assert reader.get_fields()["name"]["/V"] == "Both pages"
    for page in reader.pages:
        ann = page["/Annots"][0].get_object()
        assert b"Both pages" in ann["/AP"]["/N"].get_data()


def test_no_fields_and_unsupported_types(tmp_path):
    writer = PdfWriter()
    writer.add_blank_page(width=400, height=400)
    path = tmp_path / "blank.pdf"
    writer.write(path)
    assert get_field_info(PdfReader(path)) == []
    info = make_field_dict({"/FT": "/Btn", "/Ff": 1 << 16}, "submit")
    assert info["type"] == "pushbutton"
    assert validation_error_for_field_value(info, "anything")
    assert validation_error_for_field_value({"field_id": "name", "type": "text"}, 1)
    assert validation_error_for_field_value({"field_id": "name", "type": "text", "read_only": True}, "Ada")


def test_xfa_is_rejected(form, tmp_path):
    writer = PdfWriter(clone_from=form)
    writer.root_object["/AcroForm"][NameObject("/XFA")] = TextStringObject("fixture")
    path = tmp_path / "xfa.pdf"
    writer.write(path)
    values = tmp_path / "values.json"
    values.write_text("[]")
    with pytest.raises(ValueError, match="XFA"):
        fill_pdf_fields(path, values, tmp_path / "output.pdf")


def test_structure_and_annotation_coordinates(tmp_path):
    pytest.importorskip("pdfplumber")
    from extract_form_structure import extract_form_structure
    path = tmp_path / "static.pdf"
    c = canvas.Canvas(str(path), pagesize=(400, 400))
    c.drawString(20, 380, "Name:")
    c.line(10, 320, 390, 320)
    c.line(10, 100, 390, 300)  # A diagonal must not become a horizontal row.
    c.rect(20, 280, 10, 10)
    c.showPage()
    c.save()
    structure = extract_form_structure(path)
    assert len(structure["lines"]) == 1
    assert structure["checkboxes"][0]["top"] == 110
    data = {"pages": [{"page_number": 1, "image_width": 800, "image_height": 800,
                        "pdf_width": 400, "pdf_height": 400}],
            "form_fields": [{"page_number": 1, "description": "Name", "label_bounding_box": [40, 20, 150, 80],
                             "entry_bounding_box": [200, 20, 600, 80],
                             "entry_text": {"text": "Ada", "font_size": 12}}]}
    boxes = tmp_path / "boxes.json"
    boxes.write_text(json.dumps(data))
    output = tmp_path / "annotated.pdf"
    fill_pdf_form(path, boxes, output)
    annotation = PdfReader(output).pages[0]["/Annots"][0].get_object()
    assert annotation["/Rect"] == [100, 360, 300, 390]
    assert annotation["/Contents"] == "Ada"
    writer = PdfWriter(clone_from=path)
    writer.pages[0].rotate(90)
    rotated = tmp_path / "rotated.pdf"
    writer.write(rotated)
    with pytest.raises(ValueError, match="unrotated"):
        fill_pdf_form(rotated, boxes, output)
    data["form_fields"][0]["entry_bounding_box"][3] = 30
    boxes.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="too short"):
        fill_pdf_form(path, boxes, output)


def test_pixel_font_check_and_failure_exit(tmp_path):
    from check_bounding_boxes import get_bounding_box_messages
    data = {"pages": [{"page_number": 1, "image_height": 1000, "pdf_height": 100}],
            "form_fields": [{"page_number": 1, "description": "small", "label_bounding_box": [0, 0, 10, 10],
                             "entry_bounding_box": [20, 0, 100, 20], "entry_text": {"text": "A", "font_size": 12}}]}
    messages = get_bounding_box_messages(io.StringIO(json.dumps(data)))
    assert any(m.startswith("FAILURE") for m in messages)
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data))
    process = subprocess.run([sys.executable, str(SKILL_ROOT / "scripts/check_bounding_boxes.py"), str(path)], capture_output=True)
    assert process.returncode == 1


def test_converter_and_validation_image(form, tmp_path):
    if not shutil.which("pdftoppm"):
        pytest.skip("Poppler executable is required")
    pytest.importorskip("pdf2image")
    from convert_pdf_to_images import convert
    from create_validation_image import create_validation_image
    from PIL import Image
    output = tmp_path / "new" / "images"
    convert(form, output, max_dim=800)
    assert Image.open(output / "page_1.png").size == (800, 800)
    fields = {"pages": [{"page_number": 1, "pdf_width": 400, "pdf_height": 400}],
              "form_fields": [{"page_number": 1, "entry_bounding_box": [100, 10, 300, 40],
                               "label_bounding_box": [10, 10, 70, 40]}]}
    path = tmp_path / "fields.json"
    path.write_text(json.dumps(fields))
    validation = tmp_path / "validation.png"
    create_validation_image(1, path, output / "page_1.png", validation)
    assert Image.open(validation).getpixel((200, 20)) == (255, 0, 0)
