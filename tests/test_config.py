"""Tests for paper_to_skill.config module."""
from paper_to_skill.config import SUPPORTED_EXTENSIONS, supported_formats_message


def test_supported_extensions():
    assert ".pdf" in SUPPORTED_EXTENSIONS
    assert len(SUPPORTED_EXTENSIONS) == 1


def test_supported_formats_message():
    msg = supported_formats_message()
    assert ".pdf" in msg
