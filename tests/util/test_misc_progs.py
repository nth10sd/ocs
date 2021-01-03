# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Test the misc_progs.py file."""

from __future__ import annotations

from pathlib import Path
import platform

import pytest

from ocs.util import misc_progs


@pytest.mark.skipif(platform.system() == "Windows", reason="Windows on Travis is still new and experimental")
def test_autoconf_run(tmpdir: Path) -> None:
    """Test the autoconf runs properly.

    :param tmpdir: Fixture from pytest for creating a temporary directory
    """
    # configure.in is required by autoconf2.13
    (Path(tmpdir) / "configure.in").touch()
    misc_progs.autoconf_run(tmpdir)
