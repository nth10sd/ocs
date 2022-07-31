# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Constants used by tests."""

from __future__ import annotations

from pathlib import Path

SHELL_CACHE = Path.home() / "shell-cache"

TREES_PATH = Path.home() / "trees"
MC_PATH = TREES_PATH / "mozilla-central"
