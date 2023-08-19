"""Test the fs_helpers.py file."""

# ruff: noqa: S101

from __future__ import annotations

from pathlib import Path
import shutil
import stat

from ocs.util import fs_helpers


def test_ensure_cache_dir() -> None:
    """Test shell-cache dir is created properly if it exists/does not exist."""
    assert fs_helpers.ensure_cache_dir(Path()).is_dir()
    fs_helpers.ensure_cache_dir(Path()).rmdir()
    assert fs_helpers.ensure_cache_dir(Path.home()).is_dir()


def test_handle_rm_readonly_files(tmp_path: Path) -> None:
    """Test that directory trees with read-only files can be handled and removed.

    :param tmp_path: Fixture from pytest for creating a temporary directory
    """
    test_dir = tmp_path / "test_dir"
    read_only_dir = test_dir / "nested_read_only_dir"
    read_only_dir.mkdir(parents=True)

    test_file = read_only_dir / "test.txt"
    with test_file.open("w", encoding="utf-8", errors="replace") as f:
        f.write("testing\n")

    Path.chmod(test_file, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    shutil.rmtree(test_dir, onerror=fs_helpers.handle_rm_readonly_files)

    assert not test_file.is_file()
    assert not read_only_dir.is_dir()
    assert not test_dir.is_dir()
