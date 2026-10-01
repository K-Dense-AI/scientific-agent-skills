"""Render one page at a time with Poppler, keeping preview dimensions bounded."""
import argparse
from pathlib import Path
from pdf2image import convert_from_path, pdfinfo_from_path


def convert(pdf_path, output_dir, max_dim=1000):
    if max_dim <= 0:
        raise ValueError("max_dim must be positive")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    page_count = int(pdfinfo_from_path(pdf_path, timeout=60)["Pages"])
    for number in range(1, page_count + 1):
        images = convert_from_path(pdf_path, dpi=200, first_page=number,
                                   last_page=number, size=max_dim, timeout=120)
        image = images[0]
        try:
            path = output_dir / f"page_{number}.png"
            image.save(path)
            print(f"Saved page {number} as {path} (size: {image.size})")
        finally:
            image.close()
    print(f"Converted {page_count} pages to PNG images")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_pdf")
    parser.add_argument("output_directory")
    parser.add_argument("--max-dim", type=int, default=1000)
    args = parser.parse_args()
    convert(args.input_pdf, args.output_directory, args.max_dim)
