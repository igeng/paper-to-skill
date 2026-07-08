"""PDF text extraction orchestration."""

from __future__ import annotations

import os
from pathlib import Path

from paper_to_skill.dependencies import prepare_dependencies
from paper_to_skill.exceptions import ExtractionError
from paper_to_skill.parsers.pdf import (
    count_pages,
    extract_with_docling,
    extract_with_pdfminer,
    extract_with_pdftotext,
    extract_with_pypdf,
)
from paper_to_skill.resolver import detect_paper_structure, estimate_tokens


def extract_single_file(
    input_path: Path, extraction_mode: str, install_mode: str
) -> dict:
    """Extract text and metadata from a single PDF file."""
    input_str = str(input_path)

    if not input_path.exists():
        raise ExtractionError(f"File not found: {input_str}")

    ext = input_path.suffix.lower()

    # Sniff magic bytes: treat unknown extensions as PDF when the header matches.
    if ext != ".pdf":
        with open(input_str, "rb") as f:
            header = f.read(8)
        if header[:4] == b"%PDF":
            print(f"  [info] extension '{ext}' does not match content — treating as PDF")
            ext = ".pdf"
        else:
            raise ExtractionError(
                f"Unsupported format '{ext}'. paper-to-skill only supports PDF files."
            )

    prepare_dependencies(extraction_mode, install_mode)

    text = ""
    method = ""

    print(f"Extracting PDF: {input_str}")
    if extraction_mode == "technical":
        print(
            "Mode: technical — using Docling (layout-aware)...", end=" ", flush=True
        )
        text = extract_with_docling(input_str)
        if text:
            method = "docling"
            print("OK")
        else:
            print("not available, falling back to pdftotext")
            extraction_mode = "text"

    if extraction_mode == "text" or not text:
        print("Mode: text — using pdftotext...")
        print("Trying pdftotext...", end=" ", flush=True)
        text = extract_with_pdftotext(input_str)

        if text:
            method = "pdftotext"
            print("OK")
        else:
            print("not available")
            print("Trying pypdf...", end=" ", flush=True)
            text = extract_with_pypdf(input_str)
            if text:
                method = "pypdf"
                print("OK")
            else:
                print("not available")
                print("Trying pdfminer.six...", end=" ", flush=True)
                text = extract_with_pdfminer(input_str)
                if text:
                    method = "pdfminer"
                    print("OK")
                else:
                    print("FAILED")
                    raise ExtractionError(
                        "Could not extract text from PDF.\n"
                        "Install one of: poppler-utils (pdftotext), pypdf, or pdfminer.six\n"
                        "  sudo apt install poppler-utils\n"
                        "  pip3 install pypdf\n"
                        "  pip3 install pdfminer.six"
                    )

    pages = count_pages(input_str)
    tokens = estimate_tokens(text)
    structure = detect_paper_structure(text)
    file_size_mb = os.path.getsize(input_str) / (1024 * 1024)

    return {
        "source_file": str(input_path.resolve()),
        "filename": input_path.name,
        "format": "pdf",
        "extraction_method": method,
        "file_size_mb": round(file_size_mb, 2),
        "pages": pages,
        "chars": len(text),
        "words": len(text.split()),
        "estimated_tokens": tokens,
        "text": text,
        **structure,
    }
