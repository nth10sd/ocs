# coding=utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Miscellaneous helper functions.
"""

import copy
import os
import platform

verbose = False  # pylint: disable=invalid-name


def env_with_path(path, curr_env=None):  # pylint: disable=missing-param-doc,missing-return-doc
    # pylint: disable=missing-return-type-doc,missing-type-doc
    """Append the path to the appropriate library path on various platforms."""
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

    Args:
        directory (str): Lock directory name
    """

    def __init__(self, directory):
        self.directory = directory

    def __enter__(self):
        try:
            self.directory.mkdir()
        except OSError:
            print(f"Lock directory exists: {self.directory}")
            raise

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        self.directory.rmdir()


def vdump(inp):  # pylint: disable=missing-param-doc,missing-type-doc
    """Append the word "DEBUG" to any verbose output."""
    if verbose:
        print(f"DEBUG - {inp}")
