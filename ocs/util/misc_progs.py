"""Helper functions to compile SpiderMonkey shells."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess


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
        print(  # noqa: T201
            subprocess.run(
                [
                    str(gflags_bin_path),
                    "-p",
                    "/enable",
                    str(shell_path),
                    "/full",
                ],
                check=True,
                stderr=subprocess.STDOUT,
                stdout=subprocess.PIPE,
            ).stdout,
        )
