# Contributing to paper-to-skill

Thanks for your interest! paper-to-skill converts academic paper PDFs into reusable agent skills that work with Claude Code and OpenCode.

## Quick Start

```bash
git clone https://github.com/igeng/paper-to-skill.git
cd paper-to-skill
pip install -e ".[pdf]"
```

Run the test suite:

```bash
pip install pytest
pytest tests/ -v
```

## Project Layout

```
paper-to-skill/
├── SKILL.md                     # Agent skill definition (slim — trigger + modes only)
├── references/
│   └── workflow.md              # Full extraction workflow (loaded on-demand by the agent)
├── scripts/
│   └── extract.py               # Standalone PDF extraction entrypoint
├── paper_to_skill/              # Python package
│   ├── cli.py                   # CLI orchestration
│   ├── config.py                # Constants and paths
│   ├── dependencies.py          # Optional dependency resolution
│   ├── exceptions.py            # Custom exceptions
│   ├── extractor.py             # PDF extraction pipeline
│   ├── resolver.py              # Argument parsing, file resolution, structure detection
│   ├── utils.py                 # Backward-compatible re-exports
│   └── parsers/pdf.py           # PDF extraction backends (pdftotext, pypdf, pdfminer, docling)
├── tools/
│   ├── validate_skill.py        # SKILL.md audit against host agent rules
│   └── discovery_tax.py         # Token cost comparison tool
└── tests/
```

## Development Workflow

1. **Fork and branch** — create a branch from `main`
2. **Make changes** — follow existing code style; no formatter gate yet
3. **Add tests** — cover new behaviour; `pytest tests/ -v` must pass
4. **Run lint** — `ruff check --select E9,F paper_to_skill/ scripts/ tests/ tools/`
5. **Validate SKILL.md** — `python tools/validate_skill.py SKILL.md`
6. **Submit a PR** — describe what you changed and why

## Code Style

- Follow the patterns in the existing code
- Use type hints where practical (`from __future__ import annotations` for forward references)
- Prefer explicit over clever — this project is read by both humans and AI agents

## Adding a PDF Extractor Backend

The parser module at `paper_to_skill/parsers/pdf.py` contains individual extractor functions (`extract_with_pdftotext`, `extract_with_pypdf`, `extract_with_pdfminer`, `extract_with_docling`). Each:

- Takes a `pdf_path: str` argument
- Returns `str | None` (the extracted text, or `None` if the backend is unavailable)
- Prints a `[warn]` message to stderr on unexpected failure (never crashes)
- Is tried in priority order: docling → pdftotext → pypdf → pdfminer

To add a new backend:
1. Add the function to `pdf.py`
2. Register it in the extraction chain in `extractor.py`
3. Add any optional dependency to `config.py` and `dependencies.py`

## Testing

Tests are in `tests/`. The suite is designed to run without optional dependencies:
- No PDF extractor libraries required — tests mock them
- Temp files are cleaned up automatically
- `--check` tests mock import availability

Run: `pytest tests/ -v`

## Questions?

Open a [GitHub Discussion](https://github.com/igeng/paper-to-skill/discussions).
