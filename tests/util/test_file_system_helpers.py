# coding=utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Test the file_system_helpers.py file."""

import io
from pathlib import Path
import platform
import stat

import pytest

from funfuzz import util


@pytest.mark.skipif(platform.system() != "Windows", reason="Test only applies to read-only files on Windows")
def test_rm_tree_incl_readonly_files(tmpdir):
    """Test that directory trees with readonly files can be removed.

    Args:
        tmpdir (class): Fixture from pytest for creating a temporary directory
    """
    test_dir = Path(tmpdir) / "test_dir"
    read_only_dir = test_dir / "nested_read_only_dir"
    read_only_dir.mkdir(parents=True)

    test_file = read_only_dir / "test.txt"
    with io.open(test_file, "w", encoding="utf-8", errors="replace") as f:
        f.write("testing\n")

    Path.chmod(test_file, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    util.file_system_helpers.rm_tree_incl_readonly_files(test_dir)
