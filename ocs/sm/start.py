"""sm, for SpiderMonkey builds."""

from __future__ import annotations

import sys

from zzbase.js_shells.spidermonkey.hatch import SMShell


def main(cli_args: list[str] | None = None) -> None:
    """Start of ocs.sm for SpiderMonkey builds.

    :param cli_args: Arguments to be passed in
    :raise SystemExit: When the main function of SMShell finishes execution
    """
    if not cli_args:
        # Ignored (code coverage), as function is tested by passing in a known cli_args
        cli_args = sys.argv[1:]  # pragma: no cover

    raise SystemExit(SMShell.main(cli_args))
