# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Miscellaneous helper functions."""

from __future__ import annotations

from pathlib import Path
from types import TracebackType
from typing import Final

PACKAGE_NAME: Final = __name__.split(".", maxsplit=1)[0]
VERBOSE = False


class LockDir:
    """A class to create a filesystem-based lock while in scope.
    The lock dir will be deleted after the lock is released.

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
            print(f"Lock directory exists: {self.directory}")  # noqa: T001
            raise

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_val: type[BaseException] | None,
        _exc_tb: TracebackType | None,
    ) -> None:
        self.directory.rmdir()


def vdump(inp: str) -> None:
    """Append the word "DEBUG" to any verbose output.

    :param inp: Input string
    """
    if VERBOSE:
        print(f"DEBUG - {inp}")  # noqa: T001
