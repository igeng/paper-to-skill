"""Tests for paper_to_skill.resolver module."""
import tempfile
from pathlib import Path

from paper_to_skill.resolver import (
    detect_paper_structure,
    estimate_tokens,
    parse_arguments,
    resolve_input_files,
)


class TestEstimateTokens:
    def test_empty(self):
        assert estimate_tokens("") == 0

    def test_simple(self):
        # 750 words / 0.75 = 1000 tokens
        assert estimate_tokens("word " * 750) == 1000


class TestDetectPaperStructure:
    def test_full_paper(self):
        text = """
Abstract
This is the abstract.

Introduction
This is the introduction.

Methods
This is the method section.

Results
This is the results section.

Discussion
This is the discussion.

References
This is the reference section.
"""
        result = detect_paper_structure(text)
        assert result["has_abstract"]
        assert result["has_references"]
        assert result["sections_detected"] >= 5

    def test_no_sections(self):
        result = detect_paper_structure("Just some random text with no paper structure.")
        assert result["sections_detected"] == 0
        assert not result["has_abstract"]

    def test_has_toc_detection(self):
        text = "Table of Contents\n1. Introduction\n2. Methods\n3. Results\n"
        result = detect_paper_structure(text)
        assert result["has_toc"]

    def test_no_toc(self):
        text = "Abstract\nIntroduction\nMethods\nResults"
        result = detect_paper_structure(text)
        assert not result["has_toc"]

    # ── Multi-language section detection ──────────────────────────────────

    def test_chinese_sections(self):
        text = "摘要\n引言\n方法\n实验结果\n讨论\n结论\n参考文献"
        result = detect_paper_structure(text)
        assert result["has_abstract"]
        assert result["has_references"]
        assert result["sections_detected"] >= 4

    def test_japanese_sections(self):
        text = "要旨\nはじめに\n手法\n結果\n考察\n結論\n謝辞\n参考文献"
        result = detect_paper_structure(text)
        assert result["has_abstract"]
        assert result["has_references"]
        assert result["sections_detected"] >= 4

    def test_german_sections(self):
        text = "Zusammenfassung\nEinleitung\nMethoden\nErgebnisse\nDiskussion\nSchlussfolgerung\nLiteratur"
        result = detect_paper_structure(text)
        assert result["has_abstract"]
        assert result["has_references"]

    def test_french_sections(self):
        text = "Résumé\nIntroduction\nMéthodes\nRésultats\nDiscussion\nConclusion\nRéférences"
        result = detect_paper_structure(text)
        assert result["has_abstract"]
        assert result["has_references"]

    def test_spanish_sections(self):
        text = "Resumen\nIntroducción\nMétodos\nResultados\nDiscusión\nConclusión\nReferencias"
        result = detect_paper_structure(text)
        assert result["has_abstract"]
        assert result["has_references"]

    def test_portuguese_sections(self):
        text = "Resumo\nIntrodução\nMétodos\nResultados\nDiscussão\nConclusão\nReferências"
        result = detect_paper_structure(text)
        assert result["has_abstract"]
        assert result["has_references"]

    # ── False positive guards ─────────────────────────────────────────────

    def test_numbered_list_not_sections(self):
        text = (
            "1. This is item one of a list.\n"
            "2. This is item two of a list.\n"
            "3. This is item three.\n"
        )
        result = detect_paper_structure(text)
        assert result["sections_detected"] == 0

    def test_prose_cross_reference_not_section(self):
        text = (
            "Introduction explores the background of the problem.\n"
            "Methods are described in detail below.\n"
            "Results show significant improvements.\n"
        )
        result = detect_paper_structure(text)
        assert result["sections_detected"] == 0

    def test_numbered_section_still_detected(self):
        text = "1. Introduction\nbody\n2. Methods\nbody\n3. Results\nbody"
        result = detect_paper_structure(text)
        assert result["sections_detected"] >= 3

    def test_section_type_classification(self):
        text = "Abstract\nIntroduction\nMethods\nResults\nDiscussion\nConclusion\nReferences"
        result = detect_paper_structure(text)
        types = result["section_types"]
        assert types.get("abstract") == 1
        assert types.get("intro") == 1
        assert types.get("methods") == 1
        assert types.get("results") == 1
        assert types.get("discussion") == 1
        assert types.get("conclusion") == 1
        assert types.get("references") == 1

    # ── Chapter fallback for theses ───────────────────────────────────────

    def test_chapter_fallback_for_thesis(self):
        text = "Chapter 1: Introduction\nbody\nChapter 2: Background\nbody\nChapter 3: Method\nbody"
        result = detect_paper_structure(text)
        assert result["sections_detected"] == 3

    def test_markdown_section_fallback(self):
        text = "# Title\n\n## Section One\nbody\n\n## Section Two\nbody\n\n## Section Three\nbody"
        result = detect_paper_structure(text)
        # Falls back to structural heading count when no explicit sections found
        assert result["sections_detected"] >= 2


class TestParseArguments:
    def test_basic(self):
        paths, mode, install = parse_arguments(
            ["extract.py", "paper.pdf"]
        )
        assert paths == ["paper.pdf"]
        assert mode == "text"
        assert install in ("ask", "no")  # default depends on env

    def test_with_mode(self):
        paths, mode, _ = parse_arguments(
            ["extract.py", "--mode", "technical", "paper.pdf"]
        )
        assert paths == ["paper.pdf"]
        assert mode == "technical"

    def test_multiple_files(self):
        paths, mode, _ = parse_arguments(
            ["extract.py", "a.pdf", "b.pdf", "c.pdf"]
        )
        assert paths == ["a.pdf", "b.pdf", "c.pdf"]
        assert mode == "text"

    def test_unknown_mode_defaults_to_text(self):
        _, mode, _ = parse_arguments(
            ["extract.py", "--mode", "invalid", "paper.pdf"]
        )
        assert mode == "text"

    def test_glob_pattern(self):
        paths, _, _ = parse_arguments(
            ["extract.py", "papers/*.pdf"]
        )
        assert paths == ["papers/*.pdf"]

    def test_no_files(self):
        paths, _, _ = parse_arguments(["extract.py"])
        assert paths == []


class TestResolveInputFiles:
    def test_empty(self):
        assert resolve_input_files([]) == []

    def test_existing_pdf_file(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4 placeholder")
            tmp_path = f.name
        try:
            result = resolve_input_files([tmp_path])
            assert len(result) == 1
            assert result[0].suffix == ".pdf"
        finally:
            Path(tmp_path).unlink()

    def test_nonexistent_without_glob(self):
        result = resolve_input_files(["/nonexistent/path/paper.pdf"])
        assert result == []

    def test_directory_with_pdfs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p1 = Path(tmpdir) / "a.pdf"
            p2 = Path(tmpdir) / "b.pdf"
            p1.write_text("fake pdf")
            p2.write_text("fake pdf")
            Path(tmpdir) / "notes.txt"  # not created, not needed

            result = resolve_input_files([tmpdir])
            assert len(result) == 2
            assert any(p.name == "a.pdf" for p in result)
            assert any(p.name == "b.pdf" for p in result)

    def test_non_pdf_file_skipped(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"not a pdf")
            tmp_path = f.name
        try:
            result = resolve_input_files([tmp_path])
            assert result == []
        finally:
            Path(tmp_path).unlink()

    def test_deduplication(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4")
            tmp_path = f.name
        try:
            result = resolve_input_files([tmp_path, tmp_path])
            assert len(result) == 1
        finally:
            Path(tmp_path).unlink()
