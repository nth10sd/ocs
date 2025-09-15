"""Test start.py from <package name>.sm."""

from __future__ import annotations

import pytest

from ocs.sm import start


@pytest.mark.skip
def test_main() -> None:
    """Test the main function."""
    with pytest.raises(SystemExit) as exc:
        start.main()

    assert not exc.value.code  # ty: ignore[unresolved-attribute,unused-ignore-comment]
