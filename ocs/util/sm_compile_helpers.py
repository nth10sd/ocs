# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Helper functions to compile SpiderMonkey shells."""

from __future__ import annotations

import os
from pathlib import Path
import platform
import shutil
import subprocess


def ensure_cache_dir(base_dir: Path) -> Path:
    """Retrieve a cache directory for compiled shells to live in, and create one if needed.

    :param base_dir: Base directory to create the cache directory in
    :return: Full shell-cache path
    """
    if not base_dir:
        base_dir = Path.home()
    cache_dir = base_dir / "shell-cache"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir


def autoconf_run(working_dir: Path) -> None:
    """Run autoconf binaries corresponding to the platform.

    :param working_dir: Directory to be set as the current working directory
    """
    if platform.system() == "Darwin":
        # Total hack to support new and old Homebrew configs, we can probably just call autoconf213
        if shutil.which("brew"):
            autoconf213_mac_bin = "/usr/local/Cellar/autoconf213/2.13/bin/autoconf213"
        else:
            autoconf213_mac_bin = str(shutil.which("autoconf213"))
        if not Path(autoconf213_mac_bin).is_file():
            autoconf213_mac_bin = "autoconf213"
        subprocess.run([autoconf213_mac_bin], check=True, cwd=str(working_dir))
    elif platform.system() == "Linux":
        if shutil.which("autoconf2.13"):
            subprocess.run(["autoconf2.13"], check=True, cwd=str(working_dir))
        elif shutil.which("autoconf-2.13"):
            subprocess.run(["autoconf-2.13"], check=True, cwd=str(working_dir))
        elif shutil.which("autoconf213"):
            subprocess.run(["autoconf213"], check=True, cwd=str(working_dir))
    elif platform.system() == "Windows":
        # Windows needs to call sh to be able to find autoconf.
        subprocess.run(["sh", "autoconf-2.13"], check=True, cwd=str(working_dir))


def get_lock_dir_path(cache_dir_base: Path, repo_dir: Path, tbox_id: str = "") -> Path:
    """Return the name of the lock directory.

    :param cache_dir_base: Base directory where the cache directory is located
    :param repo_dir: Full path to the repository
    :param tbox_id: Tinderbox entry id

    :return: Full path to the shell cache lock directory
    """
    lockdir_name = f"shell-{repo_dir.name}-lock"
    if tbox_id:
        lockdir_name += f"-{tbox_id}"
    return ensure_cache_dir(cache_dir_base) / lockdir_name


def verify_full_win_pageheap(shell_path: Path) -> None:
    """Turn on full page heap verification on Windows.

    :param shell_path: Path to the compiled js shell
    """
    # More info: https://msdn.microsoft.com/en-us/library/windows/hardware/ff543097(v=vs.85).aspx
    # or https://blogs.msdn.microsoft.com/webdav_101/2010/06/22/detecting-heap-corruption-using-gflags-and-dumps/
    gflags_bin_path = Path(str(os.getenv("PROGRAMW6432"))) / "Debugging Tools for Windows (x64)" / "gflags.exe"
    if gflags_bin_path.is_file() and shell_path.is_file():
        print(subprocess.run([str(gflags_bin_path), "-p", "/enable", str(shell_path), "/full"],
                             check=True,
                             stderr=subprocess.STDOUT,
                             stdout=subprocess.PIPE).stdout)
