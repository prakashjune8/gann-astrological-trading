"""Automated Unit & Verification Test for 16-Chapter Master Textbook PDF Generator."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pypdf import PdfReader
from reporting.pdf_academic_textbook import AcademicTextbookPdfGenerator

def test_academic_textbook_pdf_compilation():
    out_dir = Path(__file__).resolve().parent.parent / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = str(out_dir / "test_gann_master_textbook.pdf")

    # 1. Compile
    res_path = AcademicTextbookPdfGenerator.generate_pdf(pdf_path)
    assert os.path.exists(res_path), f"PDF file not generated at {res_path}"
    file_size = os.path.getsize(res_path)
    assert file_size > 50000, f"Expected PDF > 50KB, got {file_size} bytes"

    # 2. Inspect pages and layout
    reader = PdfReader(res_path)
    total_pages = len(reader.pages)
    assert total_pages >= 30, f"Expected >= 30 pages, got {total_pages}"

    # 3. Audit for tofu glyphs
    tofu_pages = []
    for idx, page in enumerate(reader.pages):
        text = page.extract_text()
        if "□" in text or "\ufffd" in text:
            tofu_pages.append(idx + 1)

    assert len(tofu_pages) == 0, f"Found tofu glyphs on pages: {tofu_pages}"
    print(f"PASSED: 16-Chapter Academic Textbook compiled cleanly ({total_pages} pages, {file_size:,} bytes, 0 tofu).")

if __name__ == "__main__":
    test_academic_textbook_pdf_compilation()
