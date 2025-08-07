"""Test start.py from <package name>.sm."""

from __future__ import annotations

import pytest

from ocs.sm import start


@pytest.mark.skip
def test_main() -> None:
    """Test the main function."""
    with pytest.raises(SystemExit) as exc:
        start.main()

    # Due to immature ty now, we may be able to remove hasattr check in the future
    # As of 20250806, ty version 0.0.1a16 is immature
    assert not exc.value.code if hasattr(exc.value, "code") else 1
