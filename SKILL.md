---
name: paper-to-skill
description: "Converts research paper PDFs into structured agent skills, extracting research questions, hypotheses, methodology, key findings, contributions, and limitations. Use when the user wants to study a paper through Claude Code or OpenCode, apply a paper's methods or frameworks while working, or build a reusable knowledge base from academic literature."
allowed-tools: [Bash, Read, Write, Edit, Glob, Grep]
---

<!--
Cross-agent notes (informational; ignored by host agents):
  - Compatible skill roots:
    Claude Code: ~/.claude/skills, .claude/skills
    OpenCode: ~/.opencode/skills, .opencode/skills
  - Argument hint: <path-to-pdf-folder-or-glob>... [skill-name-slug]
-->

# Paper-to-Skill Converter

Transform academic research papers into on-demand agent skills. The skill extracts a paper's research questions, hypotheses, methods, findings, and contributions into structured files that an agent can load on-demand — no re-reading the paper every session.

## Philosophy

- **Extract structure, not summaries.** A skill is a toolkit of methods, findings, and frameworks — not a paper abstract.
- **Preserve the authors' precision.** "Transformer self-attention" ≠ "a way to focus on relevant parts."
- **Layer depth appropriately.** Short papers → compact skills. Multi-paper collections → section files with cross-references.

## Trigger Conditions

Invoke `paper-to-skill` when the user:
- Provides a PDF path, folder, or glob pattern accompanied by a skill-related request
- Says "convert this paper into a skill", "paper-to-skill", or similar
- Asks to analyze/study/extract from a paper for reuse

**Not applicable** when the user just wants to read, summarize, or translate a paper once (use paper-fetch or direct reading instead).

## Modes

| Mode | Trigger | Output |
|------|---------|--------|
| **Full Conversion** (default) | PDF paths given, no special flags | Complete skill with SKILL.md, sections/, glossary, methods, cheatsheet |
| **Analyze Only** | User says "analyze" or "just extract" | Structured extraction report, no files generated |
| **Generate from Analysis** | User has prior analysis notes | Skill files built from provided analysis |
| **Update / Fold-in** | New PDFs + existing skill directory | Updated existing skill with new papers merged |

## Quick Usage

```
User: paper-to-skill ~/papers/attention-is-all-you-need.pdf
Agent: [detects PDF, asks paper type, extracts, generates skill]

User: paper-to-skill ~/papers/gpt3.pdf
       > analyze only
Agent: [extracts and reports analysis only, no files written]

User: paper-to-skill ~/papers/new-paper.pdf existing-skill-name
Agent: [detects existing skill, enters Update/Fold-in mode]
```

## Skill Destination

| Host agent | Personal root | Project-local root |
|---|---|---|
| **Claude Code** | `~/.claude/skills` | `.claude/skills` |
| **OpenCode** | `~/.opencode/skills` | `.opencode/skills` |

If exactly one host root exists, use it. If none exist, ask the user. If the skill name already exists, offer Update/Overwrite/Rename.

## Generated Skill Structure

```
<skill_name>/
├── SKILL.md              # Core contributions + navigable index (~4K tokens)
├── sections/
│   ├── 01-introduction.md
│   ├── 02-methodology.md
│   └── ...
├── glossary.md           # Technical terms with definitions (~1.5K tokens)
├── methods.md            # Methods, algorithms, procedures (~2K tokens)
└── cheatsheet.md         # Decision rules, comparison tables (~1.2K tokens)
```

## Dependencies

The converter needs at least one PDF extractor:
- `pdftotext` (poppler-utils) — fastest, recommended
- `pypdf` — pure Python fallback
- `pdfminer.six` — pure Python fallback
- `docling` — layout-aware extraction for technical papers (formulas, tables)

Run `paper-to-skill --check` to see what's available. Missing extractors are auto-detected with a prompt to install.

## References

- **[references/workflow.md](references/workflow.md)** — Full step-by-step workflow (Steps 0–10, Update/Fold-in, Quality Rules)
- **[README_zh.md](README_zh.md)** — 中文使用说明
