"""v8, for V8 builds."""

from __future__ import annotations

import sys

from zzbase.js_shells.v8.hatch import V8Shell


def main(cli_args: list[str] | None = None) -> None:
    """Start of ocs.v8 for V8 builds.

    :param cli_args: Arguments to be passed in
    :raise SystemExit: When the main function of V8Shell finishes execution
    """
    if not cli_args:
        cli_args = sys.argv[1:]

    if exit_code := V8Shell.main(cli_args):  # Raise unexpected exit codes (if not 0)
        raise SystemExit(exit_code)
