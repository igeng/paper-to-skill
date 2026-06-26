from __future__ import annotations

import glob
import json
import os
import re
import sys
import shutil
from pathlib import Path

from paper_to_skill.exceptions import ExtractionError

from paper_to_skill.config import (
    OUTPUT_DIR,
    OUTPUT_TEXT,
    OUTPUT_META,
    WORDS_PER_TOKEN,
    SUPPORTED_EXTENSIONS,
    supported_formats_message,
)
from paper_to_skill.dependencies import (
    normalize_install_mode,
    prepare_dependencies,
    run_dependency_check,
)
from paper_to_skill.parsers.pdf import (
    extract_with_docling,
    extract_with_pdftotext,
    extract_with_pypdf,
    extract_with_pdfminer,
    count_pages,
)


def estimate_tokens(text: str) -> int:
    return int(len(text.split()) / WORDS_PER_TOKEN)


# Common section headings in academic papers
_PAPER_SECTIONS = re.compile(
    r"^\s*(?:\d+\.?\s+)?"
    r"(Abstract|Introduction|Background|Related\s+Work|Literature\s+Review|"
    r"Methodology|Methods?|Materials?\s+and\s+Methods?|Experimental?\s+Setup|"
    r"Results?|Findings|Discussion|Analysis|Evaluation|"
    r"Conclusion|Conclusions|Summary|Future\s+Work|"
    r"Acknowledgment|Acknowledgement|Acknowledgments|Acknowledgements|"
    r"References|Bibliography|Appendix|Supplementary)"
    r"\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def detect_paper_structure(text: str) -> dict:
    """Detect academic paper structure: sections, abstract, references, etc."""
    lines = text.splitlines()

    sections_found = []
    for line in lines:
        m = _PAPER_SECTIONS.match(line.strip())
        if m:
            sections_found.append(line.strip())

    has_abstract = any("abstract" in s.lower() for s in sections_found)
    has_references = any(
        s.lower().strip() in ("references", "bibliography") for s in sections_found
    )

    return {
        "sections_detected": len(sections_found),
        "section_headings_sample": sections_found[:15],
        "has_abstract": has_abstract,
        "has_references": has_references,
    }


def parse_arguments(argv: list[str]) -> tuple[list[str], str, str]:
    """Parse argv into (input_paths, extraction_mode, install_mode)."""
    input_paths = []
    extraction_mode = "text"

    args = argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--mode":
            if i + 1 < len(args):
                extraction_mode = args[i + 1].lower()
                i += 2
            else:
                i += 1
        elif arg == "--install-missing":
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                i += 2
            else:
                i += 1
        elif arg == "--no-install-missing":
            i += 1
        elif arg.startswith("-"):
            i += 1
        else:
            input_paths.append(arg)
            i += 1

    install_mode = normalize_install_mode(argv)
    if extraction_mode not in ("technical", "text"):
        extraction_mode = "text"

    return input_paths, extraction_mode, install_mode


def resolve_input_files(paths: list[str]) -> list[Path]:
    """Resolve paths including files, directories, and glob patterns to Path objects."""
    resolved = []
    for path_str in paths:
        if any(char in path_str for char in ("*", "?", "[")):
            glob_matches = glob.glob(path_str, recursive=True)
            expanded = []
            for match in glob_matches:
                p = Path(match)
                if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
                    expanded.append(p.resolve())
            expanded.sort(key=lambda x: str(x).lower())
            resolved.extend(expanded)
        else:
            p = Path(path_str)
            if p.is_dir():
                dir_files = []
                for root, _, files in os.walk(p):
                    for file in files:
                        file_path = Path(root) / file
                        if file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                            dir_files.append(file_path.resolve())
                dir_files.sort(key=lambda x: str(x).lower())
                resolved.extend(dir_files)
            else:
                resolved.append(p.resolve())

    seen = set()
    unique_paths = []
    for path in resolved:
        resolved_path = path.resolve() if path.exists() else path
        if resolved_path not in seen:
            seen.add(resolved_path)
            unique_paths.append(resolved_path)

    return unique_paths


def extract_single_file(
    input_path: Path, extraction_mode: str, install_mode: str
) -> dict:
    """Extract text and metadata from a single PDF file."""
    input_str = str(input_path)

    if not input_path.exists():
        raise ExtractionError(f"File not found: {input_str}")

    ext = input_path.suffix.lower()
    if ext != ".pdf":
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


def main():
    if "--check" in sys.argv[1:]:
        sys.exit(run_dependency_check())

    if len(sys.argv) < 2:
        print(
            "Usage: extract.py <path-to-pdf-or-folder-or-glob>... "
            "[--mode technical|text] [--install-missing ask|yes|no]",
            file=sys.stderr,
        )
        print(
            "       extract.py --check    # report which extractors are installed",
            file=sys.stderr,
        )
        print(f"Supported formats: {supported_formats_message()}", file=sys.stderr)
        sys.exit(1)

    raw_input_paths, extraction_mode, install_mode = parse_arguments(sys.argv)

    if not raw_input_paths:
        print(
            "ERROR: No input PDF, folder, or glob pattern specified.", file=sys.stderr
        )
        sys.exit(1)

    input_files = resolve_input_files(raw_input_paths)

    if not input_files:
        print(
            f"ERROR: No supported PDF files found matching: {', '.join(raw_input_paths)}",
            file=sys.stderr,
        )
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    extracted_sources = []
    combined_texts = []
    errors = []

    for file_path in input_files:
        try:
            res = extract_single_file(file_path, extraction_mode, install_mode)
        except ExtractionError as exc:
            print(f"WARNING: Skipping {file_path.name}: {exc}", file=sys.stderr)
            errors.append((file_path, str(exc)))
            continue
        extracted_sources.append(res)

        separator = (
            f"\n\n{'=' * 80}\n"
            f"SOURCE: {res['filename']} (Path: {res['source_file']})\n"
            f"{'=' * 80}\n\n"
        )
        combined_texts.append(separator + res["text"])

    if not extracted_sources:
        print(
            f"\nERROR: All {len(errors)} source(s) failed extraction:", file=sys.stderr
        )
        for path, err in errors:
            print(f"  - {path.name}: {err}", file=sys.stderr)
        sys.exit(1)

    consolidated_text = "".join(combined_texts).strip()
    OUTPUT_TEXT.write_text(consolidated_text, encoding="utf-8")

    total_file_size_mb = sum(src["file_size_mb"] for src in extracted_sources)
    total_pages = sum(src["pages"] for src in extracted_sources)
    total_chars = len(consolidated_text)
    total_words = len(consolidated_text.split())
    total_tokens = estimate_tokens(consolidated_text)

    consolidated_structure = detect_paper_structure(consolidated_text)

    metadata = {
        "source_file": (
            "Consolidated from multiple sources"
            if len(extracted_sources) > 1
            else extracted_sources[0]["source_file"]
        ),
        "filename": (
            "multi-source"
            if len(extracted_sources) > 1
            else extracted_sources[0]["filename"]
        ),
        "format": "pdf",
        "extraction_method": (
            "multi-method"
            if len(extracted_sources) > 1
            else extracted_sources[0]["extraction_method"]
        ),
        "extraction_mode": extraction_mode,
        "file_size_mb": round(total_file_size_mb, 2),
        "pages": total_pages,
        "chars": total_chars,
        "words": total_words,
        "estimated_tokens": total_tokens,
        "estimated_tokens_human": f"~{total_tokens // 1000}K",
        "output_text": str(OUTPUT_TEXT),
        "total_sources": len(extracted_sources),
        "sources": [
            {
                "source_file": src["source_file"],
                "filename": src["filename"],
                "format": src["format"],
                "extraction_method": src["extraction_method"],
                "file_size_mb": src["file_size_mb"],
                "pages": src["pages"],
                "chars": src["chars"],
                "words": src["words"],
                "estimated_tokens": src["estimated_tokens"],
                "sections_detected": src["sections_detected"],
                "has_abstract": src["has_abstract"],
                "has_references": src["has_references"],
            }
            for src in extracted_sources
        ],
        **consolidated_structure,
    }

    OUTPUT_META.write_text(json.dumps(metadata, indent=2, ensure_ascii=False))

    print("\nExtraction complete:")
    print(f"   Sources  : {len(extracted_sources)} processed")
    print(f"   Size     : {total_file_size_mb:.2f} MB")
    print(f"   Pages    : {total_pages}")
    print(f"   Words    : {total_words:,}")
    print(f"   Tokens   : ~{total_tokens // 1000}K")
    print(
        f"   Sections : {consolidated_structure['sections_detected']} detected overall"
    )
    print(
        f"   Abstract : {'yes' if consolidated_structure['has_abstract'] else 'not detected'}"
    )
    print(
        f"   References: {'yes' if consolidated_structure['has_references'] else 'not detected'}"
    )
    print(f"\n   Text -> {OUTPUT_TEXT}")
    print(f"   Meta -> {OUTPUT_META}")
    if errors:
        print(f"\n   WARNING: {len(errors)} source(s) skipped due to errors:")
        for path, err in errors:
            print(f"     - {path.name}: {err}")
