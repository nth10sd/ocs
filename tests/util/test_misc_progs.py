"""Test the misc_progs.py file."""

from __future__ import annotations

from pathlib import Path
import platform

import pytest

from ocs.util import misc_progs


@pytest.mark.skipif(
    platform.system() == "Windows",
    reason="Windows on Travis is still new and experimental",
)
def test_autoconf_run(tmp_path: Path) -> None:
    """Test the autoconf runs properly.

    :param tmp_path: Fixture from pytest for creating a temporary directory
    """
    # configure.in is required by autoconf2.13
    (tmp_path / "configure.in").touch()
    misc_progs.autoconf_run(tmp_path)
