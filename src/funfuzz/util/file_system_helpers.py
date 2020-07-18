# coding=utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Helper functions dealing with the files on the file system.
"""

import errno
from pathlib import Path
import platform
import shutil
import stat


def handle_rm_readonly_files(_func, path, exc):
    """Handle read-only files on Windows. Adapted from https://stackoverflow.com/a/21263493.

    Args:
        _func (function): Function which raised the exception
        path (str): Path name passed to function
        exc (exception): Exception information returned by sys.exc_info()

    Raises:
        OSError: Raised if the read-only files are unable to be handled
    """
    assert platform.system() == "Windows"
    path = Path(path)
    if exc[1].errno == errno.EACCES:
        Path.chmod(path, stat.S_IWRITE)
        assert path.is_file()
        path.unlink()
    else:
        raise OSError("Unable to handle read-only files.")


def rm_tree_incl_readonly_files(dir_tree):
    """Remove a directory tree including all read-only files. Directories should not be read-only.

    Args:
        dir_tree (Path): Directory tree of files to be removed
    """
    shutil.rmtree(str(dir_tree), onerror=handle_rm_readonly_files if platform.system() == "Windows" else None)
