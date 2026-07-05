"""Re-export module for backward compatibility.

New code should import from the specialized modules directly:
  from paper_to_skill.resolver import parse_arguments, resolve_input_files
  from paper_to_skill.extractor import extract_single_file
"""

from paper_to_skill.extractor import extract_single_file
from paper_to_skill.resolver import (
    detect_paper_structure,
    estimate_tokens,
    parse_arguments,
    resolve_input_files,
)

__all__ = [
    "detect_paper_structure",
    "estimate_tokens",
    "extract_single_file",
    "parse_arguments",
    "resolve_input_files",
]
