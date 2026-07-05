"""CLI entry point for paper-to-skill. Handles argument parsing, extraction
orchestration, metadata generation, and reporting."""

from __future__ import annotations

import json
import sys

from paper_to_skill.config import OUTPUT_DIR, OUTPUT_TEXT, OUTPUT_META
from paper_to_skill.dependencies import normalize_install_mode, run_dependency_check
from paper_to_skill.exceptions import ExtractionError
from paper_to_skill.extractor import extract_single_file
from paper_to_skill.resolver import (
    detect_paper_structure,
    estimate_tokens,
    parse_arguments,
    resolve_input_files,
)


def _main() -> None:
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
        print(
            f"Supported formats: {', '.join(sorted({'.pdf'}))}",
            file=sys.stderr,
        )
        sys.exit(1)

    raw_input_paths, extraction_mode, install_mode = parse_arguments(sys.argv)

    if not raw_input_paths:
        print(
            "ERROR: No input PDF, folder, or glob pattern specified.",
            file=sys.stderr,
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
            f"\nERROR: All {len(errors)} source(s) failed extraction:",
            file=sys.stderr,
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


def main() -> None:
    """Entry point for paper-to-skill CLI and scripts/extract.py."""
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    _main()


if __name__ == "__main__":
    main()
