# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Test the file_system_helpers.py file."""

from __future__ import annotations

from pathlib import Path
import platform
import stat

import pytest

from ocs.util import file_system_helpers


def test_ensure_cache_dir() -> None:
    """Test the shell-cache dir is created properly if it does not exist, and things work even though it does."""
    assert file_system_helpers.ensure_cache_dir(Path()).is_dir()
    assert file_system_helpers.ensure_cache_dir(Path.home()).is_dir()


@pytest.mark.skipif(platform.system() != "Windows", reason="Test only applies to read-only files on Windows")
def test_rm_tree_incl_readonly_files(tmpdir: Path) -> None:
    """Test that directory trees with readonly files can be removed.

    :param tmpdir: Fixture from pytest for creating a temporary directory
    """
    test_dir = Path(tmpdir) / "test_dir"
    read_only_dir = test_dir / "nested_read_only_dir"
    read_only_dir.mkdir(parents=True)

    test_file = read_only_dir / "test.txt"
    with open(test_file, "w", encoding="utf-8", errors="replace") as f:
        f.write("testing\n")

    Path.chmod(test_file, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    file_system_helpers.rm_tree_incl_readonly_files(test_dir)
