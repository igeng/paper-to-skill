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
