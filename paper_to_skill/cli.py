import sys
from paper_to_skill.utils import main as utils_main


def main():
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    utils_main()


if __name__ == "__main__":
    main()
