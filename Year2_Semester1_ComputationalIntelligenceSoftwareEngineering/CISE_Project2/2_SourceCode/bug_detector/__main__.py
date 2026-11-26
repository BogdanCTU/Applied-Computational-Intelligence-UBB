"""Entry point for `python -m bug_detector`."""

import sys

from bug_detector.cli import main

if __name__ == "__main__":
    sys.exit(main())
