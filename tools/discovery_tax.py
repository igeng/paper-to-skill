#!/usr/bin/env python3
r"""discovery_tax.py — measure the "Discovery Loop Tax" for paper-to-skill.

Quantifies how many tokens three strategies put into an agent's context to
answer one targeted question about a paper:

  1. context-dump   — the whole paper stays resident, re-billed every turn
  2. discovery-loop — a live PDF-reading agent navigates: reads the ToC, then
                      pulls raw sections until it locates the answer (and
                      backtracks for missing definitions)
  3. paper-to-skill — a small resident SKILL.md core + one pre-compiled section
                      loaded on demand

Honesty notes:
  * Token counts use tiktoken (cl100k_base) when installed, else a
    words/0.75 heuristic.
  * The discovery-loop figure is a *model* with stated assumptions, not a
    measurement of a specific agent. It uses the REAL token sizes of the
    paper's ToC and sections, so it is a defensible estimate, not a guess.

Usage:
  python3 tools/discovery_tax.py --full-text <full_text.txt> \
      [--skill-dir <skill_folder>] [--target-section N] [--core-tokens 4000]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paper_to_skill.resolver import _TOC_PATTERN, _is_heading  # noqa: E402

TOC_RE = _TOC_PATTERN


def count_tokens(text: str) -> int:
    """Real BPE count via tiktoken if available; else words/0.75 heuristic."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return int(len(text.split()) / 0.75)


def token_method() -> str:
    try:
        import tiktoken  # noqa: F401
        return "tiktoken cl100k_base (real BPE)"
    except Exception:
        return "words/0.75 heuristic (tiktoken not installed)"


def split_sections(text: str) -> list[tuple[int | None, str, str]]:
    """Return [(index, heading, body)], one segment per heading occurrence.

    The text before the first heading is the 'front matter / ToC' segment
    (index=None). Uses the same _is_heading guard as the extractor."""
    lines = text.splitlines()
    segments: list[tuple[int | None, str, list[str]]] = [(None, "__front__", [])]
    for i, line in enumerate(lines):
        if _is_heading(line):
            segments.append((i, line.strip(), []))
        segments[-1][2].append(line)
    return [(n, h, "\n".join(b)) for n, h, b in segments]


def best_section(sections: list[tuple[int | None, str, str]], n: int,
                 tok) -> tuple[str, int] | None:
    """Return (heading, body_tokens) for section number `n` (1-based)."""
    labelled = [(h, tok(b)) for _, h, b in sections if h and h != "__front__"]
    if 1 <= n <= len(labelled):
        return labelled[n - 1]
    return None


def extract_toc(front_matter: str) -> str:
    """Best-effort slice of the ToC block from the front matter."""
    m = TOC_RE.search(front_matter)
    if not m:
        return front_matter[:3000]  # first 3k chars as proxy
    return front_matter[m.start():]


def main() -> int:
    ap = argparse.ArgumentParser(description="Measure the Discovery Loop Tax on a real paper.")
    ap.add_argument("--full-text", required=True, help="extractor full_text.txt")
    ap.add_argument("--skill-dir", help="generated skill folder (for SKILL.md + section sizes)")
    ap.add_argument("--target-section", type=int, default=3,
                    help="1-based section index the question is about")
    ap.add_argument("--core-tokens", type=int, default=4000,
                    help="resident SKILL.md core size if --skill-dir not given (design cap)")
    args = ap.parse_args()

    full_text = Path(args.full_text).read_text(encoding="utf-8", errors="ignore")
    total = count_tokens(full_text)

    segs = split_sections(full_text)
    front = segs[0][2]
    sections = segs[1:]
    if not sections:
        print("No sections detected — cannot model discovery. The source may be a\n"
              "PDF whose headings were flattened; try technical mode (Docling).",
              file=sys.stderr)
        return 1

    toc = extract_toc(front)
    toc_tok = count_tokens(toc)

    n = args.target_section
    best = best_section(sections, n, count_tokens)
    if best is None:
        best = ("(unknown)", 500)
    target_heading, target_raw = best
    prior = best_section(sections, n - 1, count_tokens)
    prior_raw = prior[1] if prior else 0

    # paper-to-skill resident cost
    if args.skill_dir:
        sd = Path(args.skill_dir)
        skill_md = sd / "SKILL.md"
        core = (
            count_tokens(skill_md.read_text(encoding="utf-8"))
            if skill_md.exists() else args.core_tokens
        )
        secs = sorted((sd / "sections").glob("*.md")) if (sd / "sections").is_dir() else []
        comp_section = None
        for s in secs:
            if re.search(rf"0*{n}\b", s.name):
                comp_section = count_tokens(s.read_text(encoding="utf-8"))
                break
        if comp_section is None and secs:
            comp_section = sum(count_tokens(s.read_text(encoding="utf-8")) for s in secs) // len(secs)
        comp_section = comp_section or 1000
        core_label = "measured SKILL.md" if skill_md.exists() else "design cap"
    else:
        core = args.core_tokens
        comp_section = 1000
        core_label = "design cap (no --skill-dir)"

    dump = total
    skill = core + comp_section
    disc_best = toc_tok + target_raw
    disc_loop = toc_tok + target_raw + prior_raw

    def ratio(a: int, b: int) -> str:
        return f"{a / b:.1f}x" if b else "n/a"

    print("Discovery Loop Tax — measured on a real paper\n")
    print(f"  token method : {token_method()}")
    print(f"  source       : {Path(args.full_text).name}")
    print(f"  sections     : {len(sections)} detected")
    print(f"  target       : section {n}  ({target_heading[:60]})")
    print(f"  paper total  : {total:,} tokens\n")

    print("  Cost to answer ONE targeted question (tokens entering context):\n")
    print(f"    context-dump      : {dump:>9,}   (resident, re-billed EVERY turn)")
    print(f"    discovery (best)  : {disc_best:>9,}   ToC ({toc_tok:,}) + raw target section ({target_raw:,})")
    print(f"    discovery (loop)  : {disc_loop:>9,}   + 1 prior section for context ({prior_raw:,})")
    print(f"    paper-to-skill    : {skill:>9,}   core [{core_label}] ({core:,}) + compiled section ({comp_section:,})\n")

    print("  paper-to-skill advantage:")
    print(f"    vs context-dump   : {ratio(dump, skill)} fewer tokens")
    print(f"    vs discovery best : {ratio(disc_best, skill)} fewer tokens")
    print(f"    vs discovery loop : {ratio(disc_loop, skill)} fewer tokens")
    print("\n  Note: the discovery figures are a model using the paper's real ToC/section")
    print("  sizes; a single read, not a recurring cost. context-dump recurs every turn.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
