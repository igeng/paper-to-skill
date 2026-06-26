"""Tests for paper_to_skill.dependencies module."""
from paper_to_skill.dependencies import normalize_install_mode, python_module_available


def test_normalize_install_mode_default():
    mode = normalize_install_mode(["extract.py", "paper.pdf"])
    assert mode == "ask"


def test_normalize_install_mode_yes():
    mode = normalize_install_mode(["extract.py", "--install-missing", "yes"])
    assert mode == "yes"


def test_normalize_install_mode_no():
    mode = normalize_install_mode(["extract.py", "--no-install-missing"])
    assert mode == "no"


def test_python_module_available():
    assert python_module_available("os") is True
    assert python_module_available("nonexistent_module_xyz") is False
