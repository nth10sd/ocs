# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Helper functions dealing with the files on the file system."""

import errno
from pathlib import Path
import platform
import shutil
import stat
from typing import Any


def handle_rm_readonly_files(_func: Any, path_: Path, exc: Any) -> None:
    """Handle read-only files on Windows. Adapted from https://stackoverflow.com/a/21263493.

    :param _func: Function which raised the exception
    :param path_: Path name passed to function
    :param exc: Exception information returned by sys.exc_info()

    :raise OSError: Raised if the read-only files are unable to be handled
    """
    assert platform.system() == "Windows"
    if exc[1].errno == errno.EACCES:
        Path.chmod(path_, stat.S_IWRITE)
        assert path_.is_file()
        path_.unlink()
    else:
        raise OSError("Unable to handle read-only files.")


def rm_tree_incl_readonly_files(dir_tree: Path) -> None:
    """Remove a directory tree including all read-only files. Directories should not be read-only.

    :param dir_tree: Directory tree of files to be removed
    """
    shutil.rmtree(str(dir_tree), onerror=handle_rm_readonly_files if platform.system() == "Windows" else None)
