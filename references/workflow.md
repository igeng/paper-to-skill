# Paper-to-Skill: Full Workflow Reference

> This file contains the detailed step-by-step workflow for paper-to-skill conversion.
> The agent reads this when a conversion is actually triggered, not on every session start.

## Modes of Operation

### 1. Full Conversion (Default)
**Trigger:** User provides one or more PDF paths without special instructions
**Action:** Run all steps below (Steps 0–9)
**Output:** Complete skill with SKILL.md, sections/, glossary, methods, cheatsheet

### 2. Analyze Only
**Trigger:** User says "analyze", "just extract", or "I want to review before generating"
**Action:** Run Steps 0–3, then produce a structured extraction report. Stop — do NOT generate skill files.
**Output:** Analysis report for user review

### 3. Generate from Prior Analysis
**Trigger:** User has existing analysis notes or previously ran analyze-only
**Action:** Skip Steps 0–3, use the provided analysis as input, run Steps 4–9
**Output:** Skill files from the provided analysis

### 4. Update / Fold-in (Existing Skill)
**Trigger:** User provides new PDF paths and indicates they want to update an existing skill
**Action:** Run Step 0, Step 1, Step 1.5, Step 2. Then skip to Step 5 and run the **Update / Fold-in Workflow**.
**Output:** Updated existing skill with new papers merged in.

### 5. Batch Processing (Folder of Papers)
**Trigger:** User provides a directory path (not individual files) that contains multiple PDFs
**Action:** Run Step 0 (detect batch), Step 0.5 (batch strategy prompt), then for each paper run Steps 1–10 in sequence.
**Output:** Multiple skills (one per paper) or one combined skill, depending on user choice.

**Strategy decision — BLOCKING.** The agent MUST pause and ask:
> "This folder contains `<N>` PDFs. How should I process them?
>
> 1. **One skill per paper** — each paper becomes its own skill directory. Best for independent papers.
> 2. **One combined skill** — all papers merged into a single skill. Best for papers on the same topic.
> 3. **Let me pick** — show me the list, I'll choose which to convert."

- Option 1: run the Full Conversion pipeline once per paper, giving each a unique skill slug. Skip Step 2.5 (cost estimate) after the first paper — reuse the per-paper average.
- Option 2: extract all papers together (Step 2), treat the combined text as one source, and generate a single skill with cross-paper synthesis in each section.
- Option 3: list the detected PDFs with suggested slugs, let the user pick, then process only the selected ones.

---

## Skill Locations

This converter can run from multiple skill systems. When looking for this converter's helper script or writing the generated paper skill, prefer these locations in order:

1. Claude Code personal skills: `~/.claude/skills/`
2. OpenCode personal skills: `~/.opencode/skills/`
3. Project-local Claude skills: `.claude/skills/`
4. Project-local OpenCode skills: `.opencode/skills/`

For **generated** paper skills, pick a destination that the user's host agent can actually discover (see Step 5). When more than one valid root exists, ask the user once and remember the answer for the session.

---

## Step 0 — Out-of-scope check + batch detection

If no arguments are provided, stop and respond:
> "paper-to-skill requires a PDF path, folder, or glob pattern. Usage: `paper-to-skill <path-to-pdf-folder-or-glob>... [skill-name-slug] [--output <output-dir>]`"

Throughout the workflow:
- Identify the input paths and the optional skill slug.
- If the last argument is not a file, folder, or glob that exists or matches any files, and it looks like a skill slug (e.g. lowercase hyphens, alphanumeric), treat it as `SKILL_NAME`.
- Treat all other arguments as the list of `INPUT_PATHS`.
- If any input path is an existing skill directory (contains `SKILL.md` and a `sections/` sub-folder), or if `SKILL_NAME` matches an existing skill slug in `SKILLS_HOME`, flag this run as an **Update/Fold-in** operation (Mode 4).

### Batch detection

If any `INPUT_PATH` is a directory that contains **2 or more PDFs**, flag this as a potential **Batch Processing** run (Mode 5).

- Count the PDFs in the directory (recursively, one level).
- If ≥ 2 PDFs found and the user did NOT already specify a single skill slug → proceed to Step 0.5 (batch strategy prompt).
- If the user DID specify a skill slug → they likely want one combined skill; confirm briefly ("Processing all `<N>` PDFs as one combined skill `<slug>`?") before proceeding with Mode 5 Option 2.
- If only 1 PDF found in the directory → treat as a single-paper Full Conversion.

### Step 0.5 — Batch strategy prompt (Mode 5 only)

⛔ **BLOCKING.** When Mode 5 is detected, the agent MUST pause and present:

> "This folder contains `<N>` PDFs. How should I process them?
>
> 1. **One skill per paper** — each paper gets its own skill at `$SKILLS_HOME/<paper-slug>/`. Best for independent papers with different topics.
> 2. **One combined skill** — all papers merged into a single skill at `$SKILLS_HOME/<folder-name>/` with cross-paper synthesis. Best for papers on the same topic.
> 3. **Let me pick** — I'll list the files; you choose which to convert."

Wait for user choice. Then:
- Option 1: set `BATCH_MODE=per_paper`. For each paper, run the Full Conversion pipeline (Steps 1–10) independently. Skip Step 2.5 after the first paper — show a running counter instead ("Processing 3/7: `<title>`…").
- Option 2: set `BATCH_MODE=combined`. Set `SKILL_NAME=<folder-name>`. Run Steps 1–10 once with all PDFs together.
- Option 3: list detected PDFs (filename + detected page count), ask user to confirm selection, then process selected papers with Option 1 strategy.

**After batch completion**, report all generated skills:
```
✅ Batch complete: <N> of <M> papers converted

Generated skills:
  <skill_slug_1>  →  $SKILLS_HOME/<slug_1>/    (<N> sections)
  <skill_slug_2>  →  $SKILLS_HOME/<slug_2>/    (<N> sections)
  ...

Call any skill by name: "Ask <slug> about <topic>"
```

---

## Step 1 — Validate input

Verify that there is at least one `.pdf` file among the `INPUT_PATHS`.
For directories and globs, expand them to find matching PDF files.

If no PDF files are found, stop with a clear error message.

---

## Step 1.5 — Identify paper type

Before extracting, ask the user:

> "What kind of paper(s) are these? This helps me choose the best extraction method.
>
> 1. **Technical/Quantitative** — has formulas, tables, code, algorithms, figures (e.g. ML papers, engineering, CS)
> 2. **Text-heavy/Qualitative** — mostly prose, conceptual frameworks, few formulas (e.g. social science, humanities, review papers)
> 3. **Not sure** — I'll use the fast method and warn you if quality seems limited"

Store the answer as `PAPER_TYPE`:
- Option 1 → `PAPER_TYPE=technical`
- Option 2 → `PAPER_TYPE=text`
- Option 3 → `PAPER_TYPE=text`

**If `PAPER_TYPE=technical`**, inform the user before proceeding:
> "Technical mode selected — using Docling for structure-aware extraction (tables, formulas, algorithms preserved as markdown). This takes ~1.5s per page. Starting now…"

**If `PAPER_TYPE=text`**, inform:
> "Text mode selected — using the fastest suitable extractor. Starting now…"

---

## Step 2 — Extract text from the source PDFs

Run the extraction script, passing the input paths:

```bash
SCRIPT_PATH=""
for candidate in \
  "$HOME/.claude/skills/paper-to-skill/scripts/extract.py" \
  "$HOME/.opencode/skills/paper-to-skill/scripts/extract.py" \
  ".claude/skills/paper-to-skill/scripts/extract.py" \
  ".opencode/skills/paper-to-skill/scripts/extract.py"
do
  if [ -f "$candidate" ]; then
    SCRIPT_PATH="$candidate"
    break
  fi
done

if [ -z "$SCRIPT_PATH" ]; then
  echo "Could not find scripts/extract.py for paper-to-skill" >&2
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

"$PYTHON_BIN" "$SCRIPT_PATH" $INPUT_PATHS --mode <PAPER_TYPE> --install-missing ask
```

**Tip — preflight the environment:** run `"$PYTHON_BIN" "$SCRIPT_PATH" --check` to print a report of which extractors are installed.

This creates:
- `<tempdir>/paper_skill_work/full_text.txt` — combined extracted text of all sources
- `<tempdir>/paper_skill_work/metadata.json` — size, words, pages, token counts, sources

Read `<tempdir>/paper_skill_work/metadata.json` to inspect the results.

---

## Step 2.5 — Pre-flight cost estimate

Read `<tempdir>/paper_skill_work/metadata.json` and present the user with an estimate **before doing any generation**:

```
📄 Paper(s) detected: <total_sources> paper(s)
<list each source filename from the sources metadata>
📑 Combined Pages: ~<N> | Words: ~<N> | Total tokens: ~<N>K

💰 Estimated token cost (Full Conversion / Update):
   Input  (reading + prompts): ~<N>K tokens
   Output (skill files generated/updated):  ~<N>K tokens
   Total:                           ~<N>K tokens

   Reference prices (as of 2025):
   Claude Sonnet 4.5 → ~$<X> USD
   Claude Haiku 4.5  → ~$<X> USD

   ⏱  Estimated time: ~<N> minutes

📁 Files to be generated/updated:
   SKILL.md + section files + glossary + methods + cheatsheet

➡  Proceed with Full Conversion / Update? (or type "analyze only" to preview first)
```

**How to estimate:**
- Input tokens ≈ `estimated_tokens` from metadata × 1.3 (prompts overhead per section pass)
- Output tokens ≈ sections × per-section budget + 4,000 (SKILL.md) + 4,500 (glossary + methods + cheatsheet)
  - Per-section budget midpoint by `PAPER_TYPE`: `text` ≈ 1,000, `technical` ≈ 1,800
- Price: Sonnet input=$3/MTok output=$15/MTok — Haiku input=$0.80/MTok output=$4/MTok
- Time: ~30–60s per section for generation; extraction time varies by PDF size

Wait for the user to confirm before proceeding. If they say "analyze only", switch to Mode 2.

---

## Step 2.6 — REPL-style access for large paper collections (> 50k tokens)

For paper collections over ~50k tokens, prefer programmatic probes over reading the whole file:

```bash
# Size check
wc -w "$FULL_TEXT_PATH"

# Find section offsets
grep -n -E "^\s*(Abstract|Introduction|Method|Results|Discussion|Conclusion)" "$FULL_TEXT_PATH" | head -40

# Pull only the section you need
sed -n '<start>,<end>p' "$FULL_TEXT_PATH"

# Verify a concept is actually mentioned
grep -c -i "transformer\|attention" "$FULL_TEXT_PATH"
```

On single papers under 50k tokens, a single read is fine.

---

## Step 3 — Analyze paper structure

Read the first 8,000 characters of the extracted `full_text.txt` to identify:
- Paper **title** and **author(s)**
- **Section structure** (Abstract, Introduction, Methods, Results, Discussion, Conclusion)
- **Research motivation** (the real-world problem or gap that drove this research)
- **Core research question(s)** and subject domain
- Approximate number of major sections

Then scan for section headings throughout the paper.

**If mode is "Analyze Only":** produce the extraction report now and stop. Structure:
```
## Extraction Report — <Title>

### Research Motivation
- **Problem/Gap**: <what real-world problem or knowledge gap motivated this research>
- **Why it matters**: <practical or theoretical significance>

### Research Questions & Hypotheses
- **RQ<N>**: <research question>
- **H<N>**: <hypothesis, if stated>

### Core Contributions
- <Contribution 1>: <what is novel and why it matters>

### Methodology
- **Design**: <experimental/theoretical/survey/etc.>
- **Key Methods**: <specific techniques used>

### Key Findings
- <Finding>: <result with metrics if available>

### Limitations & Future Work
- <Limitation>: <impact on generalizability>

### Suggested Skill Name
`{first-author-lastname}-{core-concept}` — e.g. `vaswani-attention`, `he-resnet`

### Sections Detected
| # | Title | Key Concepts |
```

---

## Step 4 — Ask purpose (Full Conversion only)

Before generating, ask the user:

> "What should this skill help you do? (Pick one or more)
> 1. Apply the paper's methods/algorithms in my work
> 2. Think with the paper's theoretical frameworks
> 3. Reference specific sections, formulas, and results
> 4. All of the above"

Use the answer to weight what gets highlighted in the SKILL.md Core section.

**Derive `DEPTH` from the answer:**
- Answer is **only** option 3 → `DEPTH=reference` — lean, fast-lookup sections.
- Answer includes option 1, 2, or 4 → `DEPTH=study` — deeper sections with worked examples.

---

## Step 5 — Determine skill name + output path

### 5a: Skill name

If `SKILL_NAME` was provided, use it as the skill slug.
Otherwise, propose two options and let the user choose:
- **By author-concept**: `{first-author-lastname}-{core-concept}` (e.g. `vaswani-attention`, `he-resnet`)
- **By title**: lowercase hyphens from paper title (e.g. `attention-is-all-you-need`)

Default to author-concept format.

### 5b: Output path — ⛔ BLOCKING

**Never proceed to Step 6 until the user has confirmed the output path.** Resolve in this order:

1. **User passed `--output <dir>`** → `SKILLS_HOME = <dir>` resolved to an absolute path.
2. **User says "save here" or "current directory"** → use `./.claude/skills/`.
3. **Auto-detect** → probe the filesystem for existing skill roots:

| Host agent | Personal root | Project-local root |
|---|---|---|
| **Claude Code** | `~/.claude/skills` | `.claude/skills` |
| **OpenCode** | `~/.opencode/skills` | `.opencode/skills` |

Pick the first existing root. If none exist, default to the personal root.

### 5c: Confirm with user

Before any files are written, present the user with the full destination:

> "📁 Skill will be saved to: `<SKILLS_HOME>/<skill_name>/`
>
> Is that OK? Reply "yes" to continue, or type a different path."

The user can reply with:
- `yes` or `ok` → proceed
- A custom path like `D:\my-skills\` → set `SKILLS_HOME` to that path and re-confirm the updated destination
- A relative path like `./skills/` → resolve against cwd

If the skill directory already exists, prompt:
1. **Update / Fold-in** (Mode 4)
2. **Overwrite**
3. **Rename**

---

## Step 5.5 — Pre-generation confirmation summary

⛔ **BLOCKING.** Present a final summary before generation begins:

```
📄 Paper: <title> — <author(s)>
📐 Mode: <PAPER_TYPE> | Depth: <DEPTH>
📁 Output: <SKILLS_HOME>/<skill_name>/
💰 Est. cost: ~<N>K tokens (~$<X> USD)
📑 <N> sections will be generated

Proceed?
```

Wait for the user. Once confirmed, Steps 6–10 run without further pauses.

---

## Step 6 — Create skill directory structure

```bash
mkdir -p "$SKILLS_HOME/<skill_name>/sections"
```

---

## Step 7 — Generate section summaries

**TOKEN BUDGET RULE — CRITICAL (adaptive):**

| | `DEPTH=reference` | `DEPTH=study` |
|---|---|---|
| `PAPER_TYPE=text` | 800–1,200 tokens | 1,000–1,800 tokens |
| `PAPER_TYPE=technical` | 1,200–1,800 tokens | 2,000–3,000 tokens |

For EACH major section identified in Step 3, create `$SKILLS_HOME/<skill_name>/sections/<NN>-<slug>.md` using the structure below.

**Adapt emphasis based on `PAPER_TYPE`:**
- `technical` → prioritize "Formulas & Algorithms", "Tables & Figures", "Implementation Details"
- `text` → prioritize "Theoretical Framework", "Key Arguments", "Conceptual Models"

```markdown
# Section N: <Full Title>

## Core Idea
<1–2 sentences: the single most important thing this section contributes>

## Research Context
- **Motivation**: <why this aspect of the problem needs to be addressed>
- **Problem addressed**: <what gap or question this section tackles>
- **Relation to paper's thesis**: <how it supports the overall argument>

## Key Concepts
- **<Term>**: <precise definition in 1 sentence>
(5–10 most important terms from this section)

## Methodology Details *(methods sections only)*
- **Design**: <experimental setup, data sources, sample>
- **Procedure**: <step-by-step method>
- **Metrics**: <how results are measured>

## Formulas & Algorithms *(technical papers only — omit if PAPER_TYPE=text)*
<!-- Reproduce the most important formula or algorithm from this section. -->
```<math or pseudocode>
<key formula or algorithm>
```
- **What it computes**: <one line>
- **Variables**: <brief definition of each variable>

## Tables & Figures *(technical papers only — omit if PAPER_TYPE=text)*
<!-- Reproduce key comparison tables or describe important figures. -->

## Worked Example *(DEPTH=study only — omit for DEPTH=reference)*
<!-- Reproduce or reconstruct one concrete example: a calculation walkthrough,
     an application of the method, a case study from the paper. -->

## Key Findings
1. <Finding with metric/evidence>
2. <Finding with metric/evidence>
3. <Finding with metric/evidence>

## Connects To
- **Section N**: <why this section relates>
- **<External work>**: <connection to other papers or concepts>
```

---

## Step 8 — Generate supporting files

### glossary.md
Create `$SKILLS_HOME/<skill_name>/glossary.md`:
- Every significant technical term from the paper(s), alphabetically sorted
- Format: `**Term** — definition (Section N)`
- Max 1,500 tokens

### methods.md
Create `$SKILLS_HOME/<skill_name>/methods.md`:
- All concrete methods, algorithms, experimental procedures from the paper(s)
- Format: `## Method Name\n**When to use**: ...\n**How**: ...\n**Assumptions/Limitations**: ...`
- Max 2,000 tokens

### cheatsheet.md
Create `$SKILLS_HOME/<skill_name>/cheatsheet.md`:

**This is the most differentiated layer of the skill — treat it as a reasoning aid, not a keyword list.** Anyone can grep the glossary for a term. The cheatsheet captures the authors' *judgment*: the decisions they'd make and why. It's the file that turns "I know the words" into "I'd act the way the authors would."

Prioritize, in order:
1. **Decision rules** — "When X, use method Y, because Z." The if/then logic the authors apply, stated so the reader can apply it without re-reading the paper.
2. **Decision trees / flowcharts** (as nested bullets or a small table) — for choices with more than two branches.
3. **Trade-off matrices** — competing methods/approaches scored on dimensions the authors evaluate, so the reader can pick under their own constraints.
4. **Thresholds & defaults** — the specific numbers, ratios, or rules of thumb the authors commit to (e.g. "learning rate = 3e-4", "beam size = 4", "dropout = 0.1").
5. **Tells & smells** — fast heuristics for recognizing a situation ("if you see X, you're probably in trouble Y", "when metric A drops below B, switch to method C").
6. **Key results summary** — the headline numbers and what they mean practically.
7. **Reproducibility notes** — what you need to replicate the results (data, compute, libraries).

Avoid: bare term→definition rows (that's the glossary), and prose paragraphs (that's the sections). Every line should help the reader *decide* something.

- Format mostly as compact tables and decision rules; the content you'd want on a single printed page kept beside you while working.
- Max 1,200 tokens.

---

## Step 9 — Generate the master SKILL.md

**CRITICAL TOKEN BUDGET: Keep SKILL.md body under 4,000 tokens.**

Create `$SKILLS_HOME/<skill_name>/SKILL.md`:

```markdown
---
name: <skill_name>
description: "Knowledge base from \"<Paper Title>\" by <Author(s)> (<Year>). Use when applying <authors>'s methods for <key topics>, studying the paper, or referencing its contributions."
---

<!-- argument-hint: [topic, method name, or section] -->

# <Paper Title>
**Authors**: <Author(s)> | **Year**: <YYYY> | **Pages**: ~<N> | **Venue**: <conference/journal> | **Generated**: <YYYY-MM-DD>

## How to Use This Skill

- **Without arguments** — load core contributions and methods for reference
- **With a topic** — ask about `attention`, `loss function`, or another indexed topic; I find and read the relevant section
- **With section** — ask for `sec03`; I load that specific section
- **Browse** — ask "what sections do you have?" to see the full index

When you ask about a topic not covered in Core Contributions below, I will read
the relevant section file before answering.

---

## Abstract
<paper's abstract, condensed to 2–3 sentences>

## Research Motivation
<1–2 sentences: what real-world problem or knowledge gap motivated this research, why existing solutions are insufficient>

## Core Contributions & Methods
<!-- ~2,000 tokens: the paper's most important contributions, methods, and findings.
     Preserve exact method names. Write as "Use X when Y", "X outperforms Y because Z".
     This is a toolkit, not a summary. -->

<generate 2,000 tokens of the most critical contributions and methods here>

---

## Section Index

| # | Title | Key Concepts |
|---|-------|--------------|
| [sec01](sections/01-<slug>.md) | <Title> | <concept1>, <concept2> |
| [sec02](sections/02-<slug>.md) | <Title> | <concept1>, <concept2> |
...

## Topic Index

<!-- Alphabetical. Major terms/methods → section(s) that cover them. -->
- **<Term>** → sec<N>[, sec<N>]
- **<Term>** → sec<N>

## Supporting Files

- [glossary.md](glossary.md) — all key terms with definitions
- [methods.md](methods.md) — all methods, algorithms, and procedures
- [cheatsheet.md](cheatsheet.md) — quick reference tables and decision guides

---

## Scope & Limits

This skill covers the paper content only. For hands-on implementation in your codebase,
combine with project-specific tools. For topics beyond this paper, check related skills
or ask the agent directly.
```

---

## Step 10 — Cleanup and report

```bash
PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

"$PYTHON_BIN" - <<'PY'
import os
import shutil
import tempfile
from pathlib import Path
shutil.rmtree(
    os.environ.get("PAPER_SKILL_WORKDIR", Path(tempfile.gettempdir()) / "paper_skill_work"),
    ignore_errors=True,
)
PY
```

Then report to the user:

```
Skill created: $SKILLS_HOME/<skill_name>/

Paper: <Paper Title> — <Author(s)> (<Year>)
Pages: ~<N> | Sections: <N>

Files generated:
  SKILL.md         — core contributions + index   (~X tokens)
  sections/        — <N> section summaries        (~X tokens each, ~X total)
  glossary.md      — key terms                    (~X tokens)
  methods.md       — methods & algorithms         (~X tokens)
  cheatsheet.md    — quick reference              (~X tokens)
  ─────────────────────────────────────────────────────
  Total skill size: ~X tokens (loaded on-demand, not all at once)

Usage:
  Ask for <skill_name>                  → load core contributions
  Ask <skill_name> about <topic>        → find and explain a topic
  Ask <skill_name> for sec<N>           → dive into a specific section

Reload (if your agent doesn't auto-detect new skills):
  Claude Code:  restart the session
  OpenCode:     restart the session
```

---

## Update / Fold-in Workflow

When performing an Update/Fold-in operation on an existing skill at `$SKILLS_HOME/<skill_name>/`:

### 1. Read Existing Skill Structure
- Read `$SKILLS_HOME/<skill_name>/SKILL.md` to parse the existing **Section Index**, **Topic Index**, metadata, and **Core Contributions**.
- List all files in `$SKILLS_HOME/<skill_name>/sections/` to find the highest section number.
- Read `glossary.md`, `methods.md`, and `cheatsheet.md`.

### 2. Match Content & Identify Revisions vs. Additions
Analyze the new extracted text to identify if the new content represents:
- **Updates to existing sections**: merge new details into existing section files.
- **New additions**: create **new section summary files** numbered after the highest existing section.

### 3. Generate or Update Section Summary Files
For each new or revised section, follow Step 7 formatting.

### 4. Merge Supporting Files
- **Merge glossary.md**: combine and alphabetize existing and new terms.
- **Merge methods.md**: append new methods with consistent formatting.
- **Merge cheatsheet.md**: integrate new comparison rules and decision tables.

### 5. Re-generate the Master SKILL.md
- Update metadata, section count, and dates.
- Fold in high-impact contributions from new papers.
- Append new sections to the index.
- Merge topic index alphabetically.

### 6. Cleanup and Proceed to Step 10

---

## Quality Rules

1. **Extract structure, not summaries** — capture research questions, methods, findings, contributions; not section recaps
2. **Preserve the authors' precision** — "Transformer self-attention" ≠ "a way to weigh inputs"; keep exact naming
3. **Density over completeness** — a 1,000-token extraction beats a 10,000-token excerpt
4. **Practitioner voice** — write "Use X when Y", not "The paper explains X"
5. **Front-load SKILL.md** — most important content comes first
6. **Section files are on-demand** — they don't count against skill budget until loaded
7. **Never copy raw paper text** — always synthesize, extract signal
8. **Topic index is critical** — it's how the agent navigates to the right section file
9. **Cite with precision** — include table/figure/equation numbers when referencing specific results
10. **Distinguish claims from evidence** — note whether findings are statistically validated, qualitative, or theoretical
