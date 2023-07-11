"""Test the build_options.py file."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ocs import build_options

if TYPE_CHECKING:
    import pytest


def test_chance(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that the chance function works as intended.

    :param monkeypatch: Fixture from pytest for monkeypatching some variables/functions
    """
    monkeypatch.setattr(build_options.SAFE_RANDOM_FOR_CHANCE, "random", lambda: 0)
    assert build_options.chance(0.6)
    assert build_options.chance(0.1)
    assert not build_options.chance(0)
    assert not build_options.chance(-0.2)
