"""Tests for paper_to_skill.extractor module."""
import tempfile
from pathlib import Path

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
