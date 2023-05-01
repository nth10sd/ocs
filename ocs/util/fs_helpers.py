"""Helper functions dealing with the files on the file system."""

from __future__ import annotations

import errno
import os
from pathlib import Path
import platform
import stat
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType


def ensure_cache_dir(base_dir: Path) -> Path:
    """Retrieve a cache directory for compiled shells to be in, creating one if needed.

    :param base_dir: Base directory to create the cache directory in
    :return: Full shell-cache path
    """
    cache_dir = (base_dir if base_dir else Path.home()) / "shell-cache"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir


def env_with_path(
    path: str,
    curr_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """Append the path to the appropriate library path on various platforms.

    :param path: Path to be added to $PATH
    :param curr_env: Current environment, in case os.environ is not the one required
    :raise OSError: When the current operating system is not supported
    :return: Environment with the path added
    """
    if not curr_env:
        curr_env = os.environ.copy()
    if platform.system() == "Linux":
        lib_path = "LD_LIBRARY_PATH"
        path_sep = ":"
    elif platform.system() == "Darwin":
        lib_path = "DYLD_LIBRARY_PATH"
        path_sep = ":"
    else:  # Windows (or other unknown platforms)
        lib_path = "PATH"
        path_sep = ";"

    env = curr_env.copy()
    if lib_path in env:
        if path not in env[lib_path]:
            env[lib_path] += path_sep + path
    else:
        env[lib_path] = path

    return env


def get_lock_dir_path(cache_dir_base: Path, repo_dir: Path, tbox_id: str = "") -> Path:
    """Return the name of the lock directory.

    :param cache_dir_base: Base directory where the cache directory is located
    :param repo_dir: Full path to the repository
    :param tbox_id: Tinderbox entry id

    :return: Full path to the shell cache lock directory
    """
    return ensure_cache_dir(cache_dir_base) / (
        f'shell-{repo_dir.name}-lock{f"-{tbox_id}" if tbox_id else ""}'
    )


def handle_rm_readonly_files(
    _func: Callable[[], None],
    path_: str,
    exc: tuple[PermissionError, PermissionError, TracebackType],
) -> None:
    """Handle read-only files, especially on Windows.

    :param path_: Path name passed to function
    :param exc: Exception information returned by sys.exc_info()
    """
    if isinstance(exc[1], PermissionError) and exc[1].errno == errno.EACCES:
        Path(path_).chmod(stat.S_IWRITE)  # On Windows, this unsets the read-only flag
        Path(path_).unlink()  # Delete file immediately after adjusting file permissions


def bash_piping(first_cmd: list[str], second_cmd: list[str]) -> str:
    """Simulate a bash piping command (one pipe only).

    :param first_cmd: First command to be run
    :param second_cmd: Second command to be piped through
    :return: stdout of subprocess command
    """
    with subprocess.Popen(
        first_cmd,
        stdout=subprocess.PIPE,
    ) as first_sbpr:
        return subprocess.run(
            second_cmd,
            check=True,
            stdin=first_sbpr.stdout,
            stdout=subprocess.PIPE,
        ).stdout.decode("utf-8")
