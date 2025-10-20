"""jsc, for JavaScriptCore builds."""

from __future__ import annotations

import sys

from zzbase.js_shells.javascriptcore.hatch import JSCShell


def main(cli_args: list[str] | None = None) -> None:
    """Start of ocs.jsc for JavaScriptCore builds.

    :param cli_args: Arguments to be passed in
    :raise SystemExit: When the main function of JSCShell finishes execution
    """
    if not cli_args:
        cli_args = sys.argv[1:]

    if exit_code := JSCShell.main(cli_args):  # Raise unexpected exit codes (if not 0)
        raise SystemExit(exit_code)
