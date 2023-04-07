"""Helper functions to compile SpiderMonkey shells."""

from __future__ import annotations

from logging import INFO as INFO_LOG_LEVEL
import os
from pathlib import Path

from zzbase.util.logging import get_logger
from zzbase.util.logging import println

MISC_LOG = get_logger(
    __name__, fmt="%(asctime)s %(levelname)-8s [%(funcName)s] %(message)s"
)
MISC_LOG.setLevel(INFO_LOG_LEVEL)


def verify_full_win_pageheap(shell_path: Path) -> None:
    """Turn on full page heap verification on Windows.

    :param shell_path: Path to the compiled js shell
    """
    # See the following references:
    # https://bit.ly/36Bp09W (Microsoft Docs) or https://bit.ly/36EQAmy (Archived)
    gflags_bin_path = (
        Path(str(os.getenv("PROGRAMW6432")))
        / "Debugging Tools for Windows (x64)"
        / "gflags.exe"
    )
    if gflags_bin_path.is_file() and shell_path.is_file():
        println(
            [str(gflags_bin_path), "-p", "/enable", str(shell_path), "/full"],
            shell_path,
            MISC_LOG,
        )
