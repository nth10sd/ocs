# coding=utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Test the sm_compile_helpers.py file."""

from pathlib import Path
import platform

import pytest

from funfuzz.util import sm_compile_helpers


@pytest.mark.skipif(platform.system() == "Windows", reason="Windows on Travis is still new and experimental")
def test_autoconf_run(tmpdir):
    """Test the autoconf runs properly.

    Args:
        tmpdir (class): Fixture from pytest for creating a temporary directory
    """
    tmpdir = Path(tmpdir)
    # configure.in is required by autoconf2.13
    (tmpdir / "configure.in").touch()  # pylint: disable=no-member
    sm_compile_helpers.autoconf_run(tmpdir)


def test_ensure_cache_dir():
    """Test the shell-cache dir is created properly if it does not exist, and things work even though it does."""
    assert sm_compile_helpers.ensure_cache_dir(None).is_dir()
    assert sm_compile_helpers.ensure_cache_dir(Path.home()).is_dir()  # pylint: disable=no-member
