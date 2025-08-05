"""Test start.py from <package name>.sm."""

# ruff: noqa: S101

from __future__ import annotations

import os

import pytest

from ocs.sm import start


def test_main() -> None:
    """Test the main function."""
    if os.getenv("GITHUB_ACTIONS") != "true":  # Until Mercurial support is removed
        with pytest.raises(SystemExit) as exc:
            start.main()

        # pylint: disable-next=line-too-long
        assert not exc.value.code  # ty: ignore[unresolved-attribute,unused-ignore-comment]
