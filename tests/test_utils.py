"""Tests for paper_to_skill.utils module."""
import pytest
from paper_to_skill.utils import (
    detect_paper_structure,
    estimate_tokens,
    parse_arguments,
)


def test_estimate_tokens():
    text = " ".join(["word"] * 100)
    tokens = estimate_tokens(text)
    assert tokens == int(100 / 0.75)


def test_detect_paper_structure_basic():
    text = """Abstract

This paper presents a novel approach.

1. Introduction

We introduce a new method.

2. Methods

Our methodology involves...

3. Results

The results show...

4. Discussion

We discuss the implications.

5. Conclusion

In conclusion...

References

[1] Some reference.
"""
    structure = detect_paper_structure(text)
    assert structure["has_abstract"] is True
    assert structure["has_references"] is True
    assert structure["sections_detected"] >= 5


def test_detect_paper_structure_no_abstract():
    text = """Introduction

Some text here.

Methods

Some methods.
"""
    structure = detect_paper_structure(text)
    assert structure["has_abstract"] is False


def test_parse_arguments_basic():
    argv = ["extract.py", "paper.pdf"]
    paths, mode, install = parse_arguments(argv)
    assert paths == ["paper.pdf"]
    assert mode == "text"


def test_parse_arguments_with_mode():
    argv = ["extract.py", "paper.pdf", "--mode", "technical"]
    paths, mode, install = parse_arguments(argv)
    assert paths == ["paper.pdf"]
    assert mode == "technical"


def test_parse_arguments_multiple_files():
    argv = ["extract.py", "paper1.pdf", "paper2.pdf"]
    paths, mode, install = parse_arguments(argv)
    assert paths == ["paper1.pdf", "paper2.pdf"]


def test_parse_arguments_invalid_mode():
    argv = ["extract.py", "paper.pdf", "--mode", "invalid"]
    paths, mode, install = parse_arguments(argv)
    assert mode == "text"
