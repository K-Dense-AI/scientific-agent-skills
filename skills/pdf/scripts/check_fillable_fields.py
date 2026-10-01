"""Distinguish AcroForm fields from static pages and unsupported XFA forms."""
import sys
from pypdf import PdfReader


def main():
    if len(sys.argv) != 2:
        print("Usage: check_fillable_fields.py [input pdf]")
        return 1
    reader = PdfReader(sys.argv[1])
    acroform = reader.trailer["/Root"].get("/AcroForm")
    if acroform and "/XFA" in acroform.get_object():
        print("[FAIL] XFA form detected; use an XFA-capable viewer/workflow")
        return 2
    if reader.get_fields():
        print("This PDF has fillable AcroForm fields; inspect field types before filling")
    else:
        print("This PDF does not have fillable form fields; determine entry locations from structure or images")
    return 0


if __name__ == "__main__":
    sys.exit(main())
