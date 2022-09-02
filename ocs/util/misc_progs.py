"""Helper functions to compile SpiderMonkey shells."""

from __future__ import annotations

import os
from pathlib import Path
import platform
import shutil
import subprocess


def autoconf_run(working_dir: Path) -> None:
    """Run autoconf binaries corresponding to the platform.

    :param working_dir: Directory to be set as the current working directory
    :raise RuntimeError: If autoconf 2.13 is not found on Linux
    :raise RuntimeError: If an unknown OS is input (i.e. not any of Windows/Linux/macOS)
    """
    if platform.system() == "Darwin":
        # Hack to support new / old Homebrew configs, can probably just call autoconf213
        if shutil.which("brew"):
            autoconf213_mac_bin = "/usr/local/Cellar/autoconf213/2.13/bin/autoconf213"
        else:
            autoconf213_mac_bin = str(shutil.which("autoconf213"))
        if not Path(autoconf213_mac_bin).is_file():
            autoconf213_mac_bin = "autoconf213"
        subprocess.run([autoconf213_mac_bin], check=True, cwd=working_dir)
    elif platform.system() == "Linux":
        if shutil.which("autoconf2.13"):
            subprocess.run(["autoconf2.13"], check=True, cwd=working_dir)
        elif shutil.which("autoconf-2.13"):
            subprocess.run(["autoconf-2.13"], check=True, cwd=working_dir)
        elif shutil.which("autoconf213"):
            subprocess.run(["autoconf213"], check=True, cwd=working_dir)
        else:
            raise RuntimeError("autoconf 2.13 not found.")
    elif platform.system() == "Windows":
        # Windows needs to call sh to be able to find autoconf.
        subprocess.run(["sh", "autoconf-2.13"], check=True, cwd=working_dir)
    else:
        raise RuntimeError("Unsupported platform")


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
        print(  # noqa: T001
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
