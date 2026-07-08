"""Input processing utilities: argument parsing, file resolution, token estimation,
and multi-language paper structure detection.

Adapts detection guards (numbered-list rejection, prose cross-reference rejection,
multi-language ToC / abstract / references) from book-to-skill's detect_structure,
specialised for academic paper sections rather than book chapters."""

from __future__ import annotations

import glob
import os
import re
from pathlib import Path

from paper_to_skill.config import WORDS_PER_TOKEN, SUPPORTED_EXTENSIONS
from paper_to_skill.dependencies import normalize_install_mode


def estimate_tokens(text: str) -> int:
    return int(len(text.split()) / WORDS_PER_TOKEN)


# ── Multi-language academic section headings ────────────────────────────────
# English + Western European + CJK section labels commonly found in academic papers.
# The tail guard (_SECTION_TAIL) rejects prose continuations ("Section 3 explores…")
# and bare numbered-list items, so false positives stay low.

_EN_SECTIONS = (
    r"Abstract|(?:Graphical\s+)?Abstract|"
    r"Introduction|Background|"
    r"Related\s+Work|Literature\s+Review|Prior\s+Work|"
    r"Methodology|Methods?|Materials?\s+and\s+Methods?|"
    r"Experimental?\s+Setup|Experimental?\s+Design|Experimental?\s+Procedure|"
    r"Results?(?:\s+and\s+(?:Discussion|Analysis|Findings))?|Findings|"
    r"Discussion|Analysis|Evaluation|Ablation\s+Stud(?:y|ies)|Case\s+Stud(?:y|ies)|"
    r"Conclusion|Conclusions|Concluding\s+Remarks|Summary|"
    r"Future\s+Work|Future\s+Directions|Outlook|Limitations|"
    r"Acknowledgment|Acknowledgement|Acknowledgments|Acknowledgements|"
    r"Conflict\s+of\s+Interest|Declaration|Author\s+Contributions|"
    r"Data\s+Availability|Code\s+Availability|Supplementary\s+Material|"
    r"References|Bibliography|Works\s+Cited|Literature\s+Cited|"
    r"Appendix|Appendices"
)

_CN_SECTIONS = (
    "摘要|"
    "引言|绪论|前言|导论|背景|"
    "相关工作|文献综述|文献回顾|相关研究|"
    "方法|方法论|实验设计|实验方法|研究方法|"
    "结果|实验结果|分析与讨论|结果与讨论|结果与分析|"
    "讨论|分析|消融实验|案例研究|"
    "结论|总结|结论与展望|未来工作|局限性|"
    "致谢|鸣谢|"
    "参考文献|引用文献|"
    "附录|附件|补充材料"
)

_JP_SECTIONS = (
    "要旨|概要|はじめに|"
    "序論|緒言|背景|関連研究|"
    "手法|方法|実験|"
    "結果|考察|結果と考察|"
    "結論|まとめ|今後の課題|"
    "謝辞|"
    "参考文献|"
    "付録|補足資料"
)

_DE_SECTIONS = (
    r"Zusammenfassung|Abstract|"
    r"Einleitung|Einführung|Hintergrund|Verwandte\s+Arbeiten|"
    r"Methode|Methoden|Methodik|Experimentelles\s+Design|"
    r"Ergebnisse|Resultate|Diskussion|Analyse|"
    r"Schlussfolgerung|Fazit|Zusammenfassung\s+und\s+Ausblick|"
    r"Danksagung|"
    r"Literatur|Literaturverzeichnis|Referenzen|"
    r"Anhang|Anhänge"
)

_FR_SECTIONS = (
    r"Résumé|Abstract|"
    r"Introduction|Contexte|Travaux\s+connexes|"
    r"Méthode|Méthodes|Méthodologie|Protocole\s+expérimental|"
    r"Résultats|Discussion|Analyse|"
    r"Conclusion|Conclusions|Perspectives|"
    r"Remerciements|"
    r"Références|Bibliographie|"
    r"Annexe|Annexes"
)

_ES_SECTIONS = (
    r"Resumen|Abstract|"
    r"Introducción|Antecedentes|Trabajos\s+relacionados|Estado\s+del\s+arte|"
    r"Método|Métodos|Metodología|Diseño\s+experimental|"
    r"Resultados|Discusión|Análisis|"
    r"Conclusión|Conclusiones|Trabajo\s+futuro|"
    r"Agradecimientos|"
    r"Referencias|Bibliografía|"
    r"Apéndice|Anexo|Anexos"
)

_PT_SECTIONS = (
    r"Resumo|Abstract|"
    r"Introdução|Introducão|Fundamentação|Trabalhos\s+relacionados|"
    r"Método|Métodos|Metodologia|"
    r"Resultados|Discussão|Análise|"
    r"Conclusão|Conclusões|Trabalhos\s+futuros|"
    r"Agradecimentos|"
    r"Referências|Bibliografia|"
    r"Apêndice|Anexo|Anexos"
)

_PAPER_SECTION_PATTERN = re.compile(
    r"^\s*(?:\d+\.?\s+)?"
    rf"({_EN_SECTIONS}|{_CN_SECTIONS}|{_JP_SECTIONS}|"
    rf"{_DE_SECTIONS}|{_FR_SECTIONS}|{_ES_SECTIONS}|{_PT_SECTIONS})"
    r"\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# A section heading is followed by end-of-line, punctuation, or a Capitalised
# title word. A lowercase continuation ("Section 3 explores…", "Results are
# shown…") is prose / a cross-reference, not a heading.
_SECTION_TAIL = re.compile(r"^\s*$|^\s*[.:\-—–]|^\s+[A-ZÀ-Þ0-9\"“(]")


def _is_heading(line: str) -> bool:
    m = _PAPER_SECTION_PATTERN.match(line.strip())
    if not m:
        return False
    # Reject prose cross-references: "Section 3 explores…" etc.
    rest = line[m.end():]
    return bool(_SECTION_TAIL.match(rest))


# ── Table-of-contents detection (multi-language) ────────────────────────────
_TOC_WORDS = (
    "table of contents", "contents", "índice", "sumário",   # EN / ES / PT
    "目录", "目錄", "目次",                                   # CN / JP
    "table des matières",                                   # FR
    "inhaltsverzeichnis",                                   # DE
    "indice", "sommario",                                   # IT
    "inhoudsopgave",                                        # NL
)
_TOC_PATTERN = re.compile(
    r"^\s*(?:" + "|".join(re.escape(h) for h in _TOC_WORDS) + r")\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# ── Abstract / References multi-language sets ───────────────────────────────
_ABSTRACT_WORDS = frozenset({
    "abstract", "résumé", "resumen", "resumo", "zusammenfassung",
    "摘要", "要旨", "概要",
})

_REFERENCES_WORDS = frozenset({
    "references", "bibliography", "works cited", "literature cited",
    "références", "bibliographie", "referencias", "bibliografía",
    "referências", "bibliografia", "literatur", "literaturverzeichnis",
    "referenzen", "引用文献", "参考文献", "참고문헌",
})


# ── Structural heading fallback (Markdown ATX / AsciiDoc / Setext RST) ──────
_ATX_HEADING = re.compile(r"^(#{1,6}|={1,6})\s+(.+?)\s*#*$")
_SETEXT_UNDERLINE = re.compile(r"^(={2,}|-{2,})$")


def _structural_section_count(text: str) -> int:
    """Count Markdown/AsciiDoc/RST section headings as a fallback when no
    explicit academic section headings are found."""
    levels: dict[int, set[str]] = {}
    in_fence = False
    prev = ""
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("```") or s.startswith("~~~"):
            in_fence = not in_fence
            prev = ""
            continue
        if in_fence:
            prev = ""
            continue
        # Setext/RST underline
        if (
            _SETEXT_UNDERLINE.match(s)
            and prev
            and not _SETEXT_UNDERLINE.match(prev)
            and len(s) >= len(prev)
        ):
            depth = 1 if s[0] == "=" else 2
            levels.setdefault(depth, set()).add(prev.lower())
            prev = ""
            continue
        # ATX heading
        m = _ATX_HEADING.match(s)
        if m:
            title = m.group(2).strip().lower()
            if title and not title[0].isdigit() and re.search(r"\w", title):
                levels.setdefault(len(m.group(1)), set()).add(title)
            prev = ""
            continue
        prev = s
    if not levels:
        return 0
    for depth in sorted(levels):
        if len(levels[depth]) >= 2:
            return len(levels[depth])
    return sum(len(titles) for titles in levels.values())


# ── Chapter number detection fallback (theses / book-derived papers) ────────
_EXPLICIT_CHAPTER = re.compile(
    r"^\s*(?:chapter|chapitre|kapitel|cap[ií]tulo|capitolo|hoofdstuk|ch\.?)\s*(\d{1,2})\b(?P<rest>.*)$",
    re.IGNORECASE,
)
_HEADING_TAIL = re.compile(r"^\s*$|^\s*[.:\-—–]|^\s+[A-ZÀ-Þ0-9\"“(]")
_ROMAN_HEAD = re.compile(r"^\s*([IVXLCDM]+)\s*[:.]\s+[A-ZÀ-Þ\"“(]")
_ROMAN_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}

_CN_NUM_VALUES = {
    "〇": 0, "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9,
}
_CN_NUM_UNITS = {"十": 10, "百": 100, "千": 1000}
_CN_NUM_CLASS = "〇零一二两三四五六七八九十百千"
_FW_DIGITS = "０-９"
_CN_CHAPTER = re.compile(rf"^\s*第\s*([0-9{_FW_DIGITS}{_CN_NUM_CLASS}]+)\s*[章回卷节篇讲]")
_MD_CN_HEADING = re.compile(rf"^#{{1,6}}\s+第?\s*([{_FW_DIGITS}{_CN_NUM_CLASS}]+)\s*[·、.:：章回卷节篇讲]")


def _cn_numeral_to_int(s: str) -> int | None:
    if s.isdigit():
        n = int(s)
        return n if 1 <= n <= 999 else None
    section = current = 0
    for ch in s:
        if ch in _CN_NUM_VALUES:
            current = _CN_NUM_VALUES[ch]
        elif ch in _CN_NUM_UNITS:
            section += (current or 1) * _CN_NUM_UNITS[ch]
            current = 0
        else:
            return None
    total = section + current
    return total if 1 <= total <= 999 else None


def _int_to_roman(n: int) -> str:
    table = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"),
             (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"),
             (5, "V"), (4, "IV"), (1, "I")]
    out = []
    for val, sym in table:
        while n >= val:
            out.append(sym)
            n -= val
    return "".join(out)


def _roman_to_int(s: str) -> int | None:
    s = s.upper()
    total = prev = 0
    for ch in reversed(s):
        v = _ROMAN_VALUES.get(ch)
        if v is None:
            return None
        total += -v if v < prev else v
        prev = max(prev, v)
    if total == 0 or total > 200:
        return None
    return total if _int_to_roman(total) == s else None


def _chapter_number(line: str) -> int | None:
    s = line.strip()
    if len(s) > 80:
        return None
    m = _EXPLICIT_CHAPTER.match(s)
    if m and _HEADING_TAIL.match(m.group("rest")):
        return int(m.group(1))
    rm = _ROMAN_HEAD.match(s)
    if rm:
        return _roman_to_int(rm.group(1))
    cm = _CN_CHAPTER.match(s) or _MD_CN_HEADING.match(s)
    if cm:
        return _cn_numeral_to_int(cm.group(1))
    return None


def _chapter_fallback_count(text: str) -> int:
    """Count distinct chapter numbers for theses / book-derived papers that
    use "Chapter N" rather than academic section headings."""
    numbers = set()
    for line in text.splitlines():
        num = _chapter_number(line)
        if num is not None:
            numbers.add(num)
    return len(numbers)


# ── Public API ──────────────────────────────────────────────────────────────

def detect_paper_structure(text: str) -> dict:
    """Detect academic paper structure with multi-language support.

    Returns a dict with:
      sections_detected      — count of matched section heading occurrences
      section_headings_sample — first 15 matched headings
      has_abstract           — bool
      has_references         — bool
      has_toc                — bool
      section_types          — dict mapping category (abstract/intro/methods/
                               results/discussion/conclusion/references/ack/
                               supplementary/other) → count of occurrences
    """
    lines = text.splitlines()

    # First pass: collect validated headings and their categories
    sections_found: list[str] = []
    section_types: dict[str, int] = {}
    has_toc = bool(_TOC_PATTERN.search(text[:30000]))

    for line in lines:
        s = line.strip()
        if _is_heading(s):
            sections_found.append(s)
            cat = _classify_section(s)
            section_types[cat] = section_types.get(cat, 0) + 1

    # Abstract / References detection (covers explicit heading text matches
    # and contents of the matched labels)
    has_abstract = any(
        any(w in s.lower() for w in _ABSTRACT_WORDS)
        for s in sections_found
    )
    has_references = any(
        any(w in s.lower() for w in _REFERENCES_WORDS)
        for s in sections_found
    )

    sections_detected = len(sections_found)

    # Fallback: if no academic sections were found, try chapter-based detection
    # (theses, dissertations, book-derived papers)
    if sections_detected == 0:
        ch_count = _chapter_fallback_count(text)
        if ch_count > 0:
            sections_detected = ch_count
        else:
            # Deep fallback: count structural Markdown/AsciiDoc headings
            sections_detected = _structural_section_count(text)

    return {
        "sections_detected": sections_detected,
        "section_headings_sample": sections_found[:15],
        "has_abstract": has_abstract,
        "has_references": has_references,
        "has_toc": has_toc,
        "section_types": section_types,
    }


def _classify_section(heading: str) -> str:
    """Classify a section heading into a broad academic category."""
    h = heading.lower()
    if any(w in h for w in _ABSTRACT_WORDS):
        return "abstract"
    if any(w in h for w in ("introduction", "background", "引言", "绪论", "前言",
                             "导论", "はじめに", "序論", "einleitung", "einführung",
                             "introducción", "introdução", "背景", "contexte")):
        return "intro"
    if any(w in h for w in ("related work", "literature review", "相关工作",
                             "文献综述", "関連研究", "verwandte arbeiten",
                             "travaux connexes", "trabajos relacionados",
                             "trabalhos relacionados", "état de l'art")):
        return "related_work"
    if any(w in h for w in ("method", "方法", "手法", "methode", "methoden",
                             "méthode", "método", "experimental", "实验")):
        return "methods"
    if any(w in h for w in ("result", "finding", "结果", "結果", "ergebnis",
                             "résultat", "resultado", "実験結果")):
        return "results"
    if any(w in h for w in ("discussion", "analysis", "讨论", "討論", "考察",
                             "diskussion", "analyse", "análisis",
                             "análise", "evaluation")):
        return "discussion"
    if any(w in h for w in ("conclusion", "concluding", "summary", "结论", "總結",
                             "結論", "schlussfolgerung", "fazit",
                             "conclusión", "conclusão", "まとめ", "今後の課題",
                             "future work", "future directions", "outlook",
                             "limitations", "未来工作", "局限性")):
        return "conclusion"
    if any(w in h for w in _REFERENCES_WORDS):
        return "references"
    if any(w in h for w in ("acknowledgment", "acknowledgement", "acknowledgments",
                             "acknowledgements", "致谢", "謝辞", "鸣谢",
                             "danksagung", "remerciements", "agradecimientos",
                             "agradecimentos")):
        return "ack"
    if any(w in h for w in ("appendix", "appendices", "supplementary",
                             "附录", "付録", "anhang", "annexe", "annexes",
                             "apéndice", "anexo", "apêndice", "附錄",
                             "補足資料", "supplémentaire")):
        return "supplementary"
    return "other"


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

    seen = set()
    unique_paths = []
    for path in resolved:
        if path not in seen:
            seen.add(path)
            unique_paths.append(path)

    return unique_paths
