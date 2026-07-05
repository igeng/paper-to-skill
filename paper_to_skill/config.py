import os
import tempfile
from pathlib import Path

OUTPUT_DIR = Path(
    os.environ.get(
        "PAPER_SKILL_WORKDIR",
        str(Path(tempfile.gettempdir()) / "paper_skill_work"),
    )
)
OUTPUT_TEXT = OUTPUT_DIR / "full_text.txt"
OUTPUT_META = OUTPUT_DIR / "metadata.json"

WORDS_PER_TOKEN = 0.75  # approximate

SUPPORTED_EXTENSIONS = {".pdf"}

# Maps Python import name → pip package name (may differ, e.g. pdfminer → pdfminer.six)
PYTHON_DEPENDENCIES = {
    "docling": "docling",
    "pypdf": "pypdf",
    "pdfminer": "pdfminer.six",
}


def supported_formats_message() -> str:
    return ", ".join(sorted(SUPPORTED_EXTENSIONS))
