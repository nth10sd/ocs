"""Test start.py from <package name>.sm."""

# ruff: noqa: S101

from __future__ import annotations

import pytest

from ocs.sm import start


def test_main() -> None:
    """Test the main function."""
    with pytest.raises(SystemExit) as exc:
        start.main()

    assert exc.value.code == 1  # ty: ignore[unresolved-attribute]
