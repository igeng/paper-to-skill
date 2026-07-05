"""Input processing utilities: argument parsing, file resolution, token estimation,
and paper structure detection."""

from __future__ import annotations

import glob
import os
import re
from pathlib import Path

from paper_to_skill.config import WORDS_PER_TOKEN, SUPPORTED_EXTENSIONS
from paper_to_skill.dependencies import normalize_install_mode


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
        # Check existence first to avoid Windows path false positives (e.g. C:\Users\[name])
        p = Path(path_str)
        if p.exists():
            if p.is_dir():
                dir_files = []
                for root, _, files in os.walk(p):
                    for file in files:
                        file_path = Path(root) / file
                        if file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                            dir_files.append(file_path.resolve())
                dir_files.sort(key=lambda x: str(x).lower())
                resolved.extend(dir_files)
            elif p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
                resolved.append(p.resolve())
        elif glob.has_magic(path_str):
            glob_matches = glob.glob(path_str, recursive=True)
            expanded = []
            for match in glob_matches:
                mp = Path(match)
                if mp.is_file() and mp.suffix.lower() in SUPPORTED_EXTENSIONS:
                    expanded.append(mp.resolve())
            expanded.sort(key=lambda x: str(x).lower())
            resolved.extend(expanded)
        # else: path doesn't exist and isn't a glob — skip silently

    seen = set()
    unique_paths = []
    for path in resolved:
        if path not in seen:
            seen.add(path)
            unique_paths.append(path)

    return unique_paths
