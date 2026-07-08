---
name: paper-to-skill
description: "Converts research paper PDFs into structured agent skills, extracting research questions, hypotheses, methodology, key findings, contributions, and limitations. Use when the user wants to study a paper through Claude Code or OpenCode, apply a paper's methods or frameworks while working, or build a reusable knowledge base from academic literature."
allowed-tools:
- Bash
- Read
- Write
- Edit
- Glob
- Grep
---

<!--
Cross-agent notes (informational; ignored by host agents):
  - Compatible skill roots:
    Claude Code: ~/.claude/skills, .claude/skills
    OpenCode: ~/.opencode/skills, .opencode/skills
  - Argument hint: <path-to-pdf-folder-or-glob>... [skill-name-slug] [--output <output-dir>]
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

## Quick Usage — Single Paper

```
User: paper-to-skill ~/papers/attention-is-all-you-need.pdf
Agent: [detects PDF, asks paper type, extracts, generates skill]

User: paper-to-skill ~/papers/gpt3.pdf
       > analyze only
Agent: [extracts and reports analysis only, no files written]

User: paper-to-skill ~/papers/new-paper.pdf existing-skill-name
Agent: [detects existing skill, enters Update/Fold-in mode]
```

## Batch Processing — Folder of Papers

When the user points at a **folder** (not a single file), we need to decide: one combined skill or one skill per paper?

### Detection

A folder input triggers the batch decision. The agent MUST pause and ask:

> "This folder contains <N> PDFs. How should I process them?
>
> 1. **One skill per paper** — each paper gets its own skill directory. Best for independent papers with different topics.
> 2. **One combined skill** — all papers merged into a single skill with cross-references. Best for papers on the same topic (e.g. a literature review collection).
> 3. **Let me pick** — show me the list, I'll choose which to convert."

### One Skill Per Paper

Each paper becomes `$SKILLS_HOME/<paper-slug>/`:
```
~/.claude/skills/
├── vaswani-attention/          # Paper 1 → skill
│   ├── SKILL.md
│   ├── sections/...
│   ├── glossary.md
│   ├── methods.md
│   └── cheatsheet.md
├── he-resnet/                  # Paper 2 → skill
│   └── ...
└── devlin-bert/                # Paper 3 → skill
    └── ...
```
Call each by name: "Ask `vaswani-attention` about the self-attention formula."

### One Combined Skill

All papers become one skill at `$SKILLS_HOME/<folder-slug>/`:
```
~/.claude/skills/llm-literature-review/
├── SKILL.md                    # Cross-paper synthesis
├── sections/
│   ├── 01-vaswani-attention.md   # Paper 1 as a section
│   ├── 02-devlin-bert.md         # Paper 2 as a section
│   └── ...
├── glossary.md                 # Merged terms
├── methods.md                  # All methods across papers
└── cheatsheet.md               # Cross-paper comparison tables
```
Call with a topic: "Ask `llm-literature-review` how different papers handle positional encoding."

## Skill Destination

Generated skills go to one of these locations:

| Host agent | Personal root | Project-local root |
|---|---|---|
| **Claude Code** | `~/.claude/skills/` | `./.claude/skills/` |
| **OpenCode** | `~/.opencode/skills/` | `./.opencode/skills/` |

### Output path resolution (BLOCKING — always confirm before generating)

The agent MUST confirm the destination before writing any files. The resolution order is:

1. **User specifies `--output <dir>`** → use `<dir>` directly. Prompt: "Skills will be saved to `<dir>`. OK?"
2. **User says "save here" or "current directory"** → use `./.claude/skills/`
3. **Auto-detect** → pick the first existing root from the table above. If none exist, ask the user. Prompt: "Skills will be saved to `<detected-root>/`. Is that OK? (Reply with a custom path to change it.)"

The user can reply with a custom path at any point to override the destination. A relative path (e.g. `./my-skills/`) is resolved against the current working directory.

### ⛔ BLOCKING rule

**Never write skill files until the user has confirmed the output path.** Before Step 6, present:
> "📁 Skills will be saved to: `<full-path>/`"
> and wait for confirmation. The user can reply "yes" or specify a different path.

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
