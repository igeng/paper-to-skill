"""Tests for paper_to_skill.extractor module."""
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from paper_to_skill.exceptions import ExtractionError
from paper_to_skill.extractor import extract_single_file


class TestExtractSingleFileErrors:
    def test_file_not_found(self):
        with pytest.raises(ExtractionError, match="File not found"):
            extract_single_file(
                Path("/nonexistent/path/paper.pdf"), "text", "no"
            )

    def test_unsupported_format(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"hello")
            tmp_path = f.name
        try:
            with pytest.raises(ExtractionError, match="Unsupported format"):
                extract_single_file(Path(tmp_path), "text", "no")
        finally:
            Path(tmp_path).unlink()

    def test_corrupt_pdf_no_extractor(self):
        """Corrupt PDF with install_mode=no should raise ExtractionError
        when no extractor can read it."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"this is not a valid pdf")
            tmp_path = f.name
        try:
            with pytest.raises(ExtractionError):
                extract_single_file(Path(tmp_path), "text", "no")
        finally:
            Path(tmp_path).unlink()


class TestMagicByteSniffing:
    """Verify that files with wrong extensions are sniffed for PDF magic bytes."""

    def test_wrong_extension_with_pdf_header(self):
        """A file named .dat but containing %PDF should be accepted as PDF."""
        with tempfile.NamedTemporaryFile(suffix=".dat", delete=False) as f:
            # Minimal valid PDF header
            f.write(b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
                    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
                    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\n"
                    b"xref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n"
                    b"0000000058 00000 n\n0000000115 00000 n\n"
                    b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n206\n%%EOF")
            tmp_path = f.name
        try:
            with mock.patch("paper_to_skill.extractor.prepare_dependencies"):
                try:
                    extract_single_file(Path(tmp_path), "text", "no")
                except ExtractionError as e:
                    # Only acceptable if it's an extraction failure, not a format error
                    assert "Unsupported format" not in str(e)
        finally:
            Path(tmp_path).unlink()

    def test_wrong_extension_without_pdf_header(self):
        """A file named .xyz without PDF header should still be rejected."""
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            f.write(b"this is not a pdf file at all")
            tmp_path = f.name
        try:
            with mock.patch("paper_to_skill.extractor.prepare_dependencies"):
                with pytest.raises(ExtractionError, match="Unsupported format"):
                    extract_single_file(Path(tmp_path), "text", "no")
        finally:
            Path(tmp_path).unlink()
