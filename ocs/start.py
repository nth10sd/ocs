"""Start of ocs."""

from __future__ import annotations

import sys

from ocs.spidermonkey.hatch import sm_hatch_main


def main(cli_args: list[str] | None = None) -> None:
    """Start of ocs.

    :param cli_args: Arguments to be passed in
    """
    if not cli_args:
        # Ignored (code coverage), as function is tested by passing in a known cli_args
        cli_args = sys.argv[1:]  # pragma: no cover

    sm_hatch_main()
