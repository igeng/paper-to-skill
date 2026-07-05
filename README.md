# paper-to-skill

**Turn research paper PDFs into structured agent skills — ready to study, reference, and use while you work in Claude Code or OpenCode.**

## What It Does

paper-to-skill takes one or more research paper PDFs and converts them into a structured, on-demand skill that your AI coding agent can load and reason with. Instead of re-reading a paper every session, teach your agent the paper's methods, findings, and frameworks once.

The generated skill includes:
- **SKILL.md** — core contributions, research motivation, methods, and a navigable index
- **sections/** — per-section summaries with key concepts, methodology, findings
- **glossary.md** — all technical terms with definitions
- **methods.md** — all methods, algorithms, and experimental procedures
- **cheatsheet.md** — decision rules, comparison tables, key results

## Supported Agents

| Agent | Personal Skill Root | Project-local Root |
|-------|--------------------|--------------------|
| **Claude Code** | `~/.claude/skills/` | `.claude/skills/` |
| **OpenCode** | `~/.opencode/skills/` | `.opencode/skills/` |

## Installation

### Option 1: Install via pip (recommended)

```bash
pip install paper-to-skill
```

With optional PDF extraction backends:

```bash
# Basic PDF extraction
pip install paper-to-skill[pdf]

# Technical papers (tables, formulas, algorithms)
pip install paper-to-skill[technical]

# Everything
pip install paper-to-skill[all]
```

### Option 2: Install as an agent skill

**Claude Code:**
```bash
mkdir -p ~/.claude/skills/
git clone https://github.com/FireJason-404/paper-to-skill.git ~/.claude/skills/paper-to-skill/
```

**OpenCode:**
```bash
mkdir -p ~/.opencode/skills/
git clone https://github.com/FireJason-404/paper-to-skill.git ~/.opencode/skills/paper-to-skill/
```

### Option 3: Install from source

```bash
git clone https://github.com/FireJason-404/paper-to-skill.git
cd paper-to-skill
pip install -e .
```

### PDF Extraction Dependencies

You need at least one PDF extractor installed:

```bash
# System tool (recommended, fastest)
sudo apt install poppler-utils

# Or Python packages (any one is enough)
pip install pypdf
# or
pip install pdfminer.six

# For technical papers with tables/formulas (optional)
pip install docling
```

## Usage

### Command Line

```bash
# Convert a single paper
paper-to-skill ~/papers/attention-is-all-you-need.pdf

# Convert multiple papers into one skill
paper-to-skill ~/papers/*.pdf my-literature-review

# Specify extraction mode for technical papers
paper-to-skill ~/papers/paper.pdf --mode technical

# Check installed extractors
paper-to-skill --check
```

### Inside Claude Code / OpenCode

Once installed as a skill, simply say in your agent:

```
paper-to-skill ~/papers/attention-is-all-you-need.pdf
```

Or analyze before generating:

```
paper-to-skill ~/papers/paper.pdf
> analyze only
```

### Python API

```python
from paper_to_skill.utils import extract_single_file, resolve_input_files
from pathlib import Path

# Resolve input files
files = resolve_input_files(["~/papers/my-paper.pdf"])

# Extract text and metadata
result = extract_single_file(files[0], extraction_mode="text", install_mode="no")
print(f"Extracted {result['words']} words using {result['extraction_method']}")
```

## Modes of Operation

| Mode | Trigger | Output |
|------|---------|--------|
| **Full Conversion** | Provide PDF path(s) | Complete skill with all files |
| **Analyze Only** | Say "analyze" or "analyze only" | Extraction report for review |
| **Generate from Analysis** | Provide prior analysis notes | Skill files from analysis |
| **Update / Fold-in** | Point to existing skill + new PDFs | Updated skill with new papers |

## Paper Types

The converter optimizes extraction based on paper type:

- **Technical/Quantitative** — ML papers, CS, engineering (uses Docling for tables, formulas, algorithms)
- **Text-heavy/Qualitative** — social science, humanities, reviews (uses fast text extraction)

## Applicable Scenarios

paper-to-skill is ideal for:

- 📚 **Literature review** — Build a searchable knowledge base from multiple papers in your research area
- 🔬 **Method implementation** — Extract algorithms and methods from papers to guide your coding agent when implementing them
- 📝 **Paper study** — Create structured notes from papers for quick reference during research
- 🤖 **Agent augmentation** — Give your AI agent domain-specific knowledge from academic papers
- 👥 **Team knowledge sharing** — Generate reusable skill files that team members can share and reference
- 🎓 **Academic writing** — Quickly reference key findings, methods, and contributions while writing

## Output Structure

After conversion, the generated skill looks like:

```
~/.claude/skills/vaswani-attention/
├── SKILL.md                    # Master index with core contributions (~4K tokens)
├── sections/
│   ├── 01-introduction.md      # Per-section summaries
│   ├── 02-background.md
│   ├── 03-methodology.md
│   ├── 04-results.md
│   └── 05-discussion.md
├── glossary.md                 # All technical terms (~1.5K tokens)
├── methods.md                  # Methods and algorithms (~2K tokens)
└── cheatsheet.md               # Decision rules and quick reference (~1.2K tokens)
```

Each section file includes:
- Core idea and research motivation
- Key concepts with precise definitions
- Methodology details (for methods sections)
- Formulas and algorithms (for technical papers)
- Key findings with metrics
- Cross-references to related sections

## Usage Effects

- **Before**: Re-read papers every session, lose context between conversations, manually search for methods
- **After**: Your agent loads paper knowledge on-demand, navigates to relevant sections, and applies methods directly

Typical conversion: a 15-page paper → ~8K tokens total skill (loaded on-demand, not all at once)

## Project Structure

```
paper-to-skill/
├── SKILL.md                    # Main skill file (slim — trigger conditions + mode summary)
├── references/
│   └── workflow.md             # Full step-by-step workflow (loaded on-demand)
├── scripts/
│   └── extract.py              # PDF text extraction entrypoint
├── paper_to_skill/             # Python package
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py                  # CLI orchestration entrypoint
│   ├── config.py               # Configuration constants
│   ├── dependencies.py         # Dependency management
│   ├── exceptions.py           # Custom exceptions
│   ├── resolver.py             # Argument parsing, file resolution, structure detection
│   ├── extractor.py            # PDF extraction orchestration
│   ├── utils.py                # Backward-compatible re-exports
│   └── parsers/
│       ├── __init__.py
│       └── pdf.py              # PDF extraction backends (pdftotext, pypdf, pdfminer, docling)
├── tests/
├── pyproject.toml
├── README.md
└── README_zh.md                # Chinese documentation
```

## Requirements

- Python >= 3.9
- At least one PDF extractor:
  - `pdftotext` (from poppler-utils) — recommended, fastest
  - `pypdf` — pure Python fallback
  - `pdfminer.six` — pure Python fallback
  - `docling` — for technical papers with tables/formulas (optional)

## Dependency Check

Run the preflight check to see what's installed:

```bash
paper-to-skill --check
# or
python3 scripts/extract.py --check
```

## Acknowledgments

This project is inspired by and adapted from [book-to-skill](https://github.com/virgiliojr94/book-to-skill) by [@virgiliojr94](https://github.com/virgiliojr94). The original project converts books into structured agent skills. paper-to-skill adapts this concept for research paper PDFs, adding academic-specific features such as research motivation extraction, methodology analysis, hypothesis identification, and support for both Claude Code and OpenCode agents.

## License

MIT
