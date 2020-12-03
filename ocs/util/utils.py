# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Miscellaneous helper functions."""

import copy
import os
from pathlib import Path
import platform
from typing import Any
from typing import Final

VERBOSE: Final = False


def env_with_path(path: str, curr_env: Any = None) -> Any:
    """Append the path to the appropriate library path on various platforms.

    :param path: Path to be added to $PATH
    :param curr_env: Current environment, in case os.environ is not the one required
    :return: Environment with the path added
    """
    curr_env = curr_env or os.environ
    if platform.system() == "Linux":
        lib_path = "LD_LIBRARY_PATH"
        path_sep = ":"
    elif platform.system() == "Darwin":
        lib_path = "DYLD_LIBRARY_PATH"
        path_sep = ":"
    elif platform.system() == "Windows":
        lib_path = "PATH"
        path_sep = ";"

    env = copy.deepcopy(curr_env)
    if lib_path in env:
        if path not in env[lib_path]:
            env[lib_path] += path_sep + path
    else:
        env[lib_path] = path

    return env


class LockDir:
    """A class to create a filesystem-based lock while in scope. The lock dir will be deleted after the lock is released.

    Use:
        with LockDir(path):
            # No other code is concurrently using LockDir(path)

    :param directory: Lock directory name
    """

    def __init__(self, directory: Path):
        self.directory = directory

    def __enter__(self) -> None:
        try:
            self.directory.mkdir()
        except OSError:
            print(f"Lock directory exists: {self.directory}")
            raise

    def __exit__(self, _exc_type: Any, _exc_val: Any, _exc_tb: Any) -> None:
        self.directory.rmdir()


def vdump(inp: str) -> None:
    """Append the word "DEBUG" to any verbose output.

    :param inp: Input string
    """
    if VERBOSE:
        print(f"DEBUG - {inp}")
