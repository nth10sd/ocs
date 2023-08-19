"""Module details."""

from pathlib import Path

__title__ = "ocs"
__version__ = (Path(__file__).parent / "_version.txt").read_text(encoding="utf-8")
