# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Test the sm_compile_helpers.py file."""

from __future__ import annotations

from pathlib import Path
import platform

import pytest

from ocs.util import sm_compile_helpers


@pytest.mark.skipif(platform.system() == "Windows", reason="Windows on Travis is still new and experimental")
def test_autoconf_run(tmpdir: Path) -> None:
    """Test the autoconf runs properly.

    :param tmpdir: Fixture from pytest for creating a temporary directory
    """
    # configure.in is required by autoconf2.13
    (Path(tmpdir) / "configure.in").touch()
    sm_compile_helpers.autoconf_run(tmpdir)


def test_ensure_cache_dir() -> None:
    """Test the shell-cache dir is created properly if it does not exist, and things work even though it does."""
    assert sm_compile_helpers.ensure_cache_dir(Path()).is_dir()
    assert sm_compile_helpers.ensure_cache_dir(Path.home()).is_dir()
