#!/usr/bin/env python3
"""Extract text from research paper PDF files for paper-to-skill processing.

Thin entrypoint: configures UTF-8 encoding, then delegates to paper_to_skill.cli.
Works both when pip-installed (package on PYTHONPATH) and when the skill is checked
out as a standalone git clone (sys.path fallback).
"""

import os
import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

try:
    from paper_to_skill.cli import main
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from paper_to_skill.cli import main

if __name__ == "__main__":
    main()
