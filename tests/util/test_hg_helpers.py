"""Test the hg_helpers.py file."""

from __future__ import annotations

import pytest

from ocs.util import hg_helpers

from .constants_for_tests import TREES_PATH


@pytest.mark.skipif(
    not (TREES_PATH / "mozilla-central" / ".hg" / "hgrc").is_file(),
    reason="requires a Mozilla Mercurial repository",
)
def test_hgrc_repo_name() -> None:
    """Test that we are able to extract the repository name from the hgrc file."""
    assert (
        hg_helpers.hgrc_repo_name(TREES_PATH / "mozilla-central") == "mozilla-central"
    )
