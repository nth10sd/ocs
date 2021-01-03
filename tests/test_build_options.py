# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Test the build_options.py file."""

from __future__ import annotations

import random
from typing import Any

from ocs import build_options


def test_chance(monkeypatch: Any) -> None:  # Ignore till mypy knows the monkeypatch type w/o importing _pytest
    """Test that the chance function works as intended.

    :param monkeypatch: Fixture from pytest for monkeypatching some variables/functions
    """
    monkeypatch.setattr(random, "random", lambda: 0)
    assert build_options.chance(0.6)
    assert build_options.chance(0.1)
    assert not build_options.chance(0)
    assert not build_options.chance(-0.2)
