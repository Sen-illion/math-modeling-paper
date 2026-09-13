"""Crop the supplied slide-one vector PDF for manuscript use.

Requires PyMuPDF. All inputs are resolved relative to this repository.
Only the first PowerPoint slide was exported to the source PDF.
"""

import hashlib
import json
from pathlib import Path

import pymupdf


def main():
    root = Path(__file__).resolve().parents[1]
    asset_dir = root / "assets" / "figures"
    source = asset_dir / "sources" / "overall_framework_slide1.pdf"
    source_doc = pymupdf.open(source)
    if len(source_doc) != 1:
        raise ValueError("The source must contain only slide one.")
    # Exclude the presentation title, subtitle, footer rule, and outer whitespace.
    # Keep the data inputs, Q1-Q4 panels, links, and storage constraints intact.
    crop = pymupdf.Rect(34, 98, 1406, 742)
    figure = pymupdf.open()
    page = figure.new_page(width=crop.width, height=crop.height)
    page.show_pdf_page(page.rect, source_doc, 0, clip=crop)
    pdf_bytes = figure.tobytes(garbage=4, deflate=True)
    png_bytes = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False).tobytes("png")
    for folder in (asset_dir, root / "figures"):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "fig_overall_framework.pdf").write_bytes(pdf_bytes)
        (folder / "fig_overall_framework.png").write_bytes(png_bytes)
    metadata = {
        "source": "sources/overall_framework_slide1.pdf",
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_slide": 1,
        "source_slide_count": 1,
        "crop_points": list(crop),
        "changes": "Crop presentation title, subtitle, footer rule, and outer whitespace only; retain all framework content.",
        "paper_placement": "Section 3.5, normal portrait page, scaled uniformly to the text width before Q1.",
        "content_policy": "Preserve all original framework text, icons, colors, arrows and arrangement; do not simplify or redraw.",
        "purpose": "Explain the Q1-Q3 progression and the two Q4 extensions.",
        "format": "Vector PDF with embedded fonts and original raster decorative icons; PNG is a preview.",
    }
    (asset_dir / "fig_overall_framework_provenance.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
