# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Helper functions dealing with the files on the file system."""

from __future__ import annotations

import errno
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
from types import TracebackType
from typing import Callable


def ensure_cache_dir(base_dir: Path) -> Path:
    """Retrieve a cache directory for compiled shells to be in, creating one if needed.

    :param base_dir: Base directory to create the cache directory in
    :return: Full shell-cache path
    """
    if not base_dir:
        base_dir = Path.home()
    cache_dir = base_dir / "shell-cache"
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
    elif platform.system() == "Windows":
        lib_path = "PATH"
        path_sep = ";"
    else:
        raise OSError(f"Unsupported operating system: {platform.system()}")

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
    lockdir_name = f"shell-{repo_dir.name}-lock"
    if tbox_id:
        lockdir_name += f"-{tbox_id}"
    return ensure_cache_dir(cache_dir_base) / lockdir_name


def handle_rm_readonly_files(  # pylint: disable=useless-param-doc,useless-type-doc
    _func: Callable[..., None],
    path_: Path,
    exc: tuple[
        type[BaseException] | None,
        type[BaseException] | None,
        TracebackType | None,
    ],
) -> None:
    """Handle read-only files on Windows.
    Adapted from https://stackoverflow.com/a/21263493.

    :param _func: Function which raised the exception
    :param path_: Path name passed to function
    :param exc: Exception information returned by sys.exc_info()

    :raise OSError: Raised if the read-only files are unable to be handled
    """
    assert platform.system() == "Windows"
    if isinstance(exc[1], int) and exc[1].errno == errno.EACCES:
        Path.chmod(path_, stat.S_IWRITE)
        assert path_.is_file()
        path_.unlink()
    else:
        raise OSError("Unable to handle read-only files.")


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


def rm_tree_incl_readonly_files(dir_tree: Path) -> None:
    """Remove a directory tree including all read-only files. Directories should not be
    read-only.

    :param dir_tree: Directory tree of files to be removed
    """
    shutil.rmtree(
        str(dir_tree),
        onerror=handle_rm_readonly_files if platform.system() == "Windows" else None,
    )
