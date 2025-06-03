"""Parsing for SpiderMonkey code."""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from ocs.util.constants import PACKAGE_NAME


@dataclass(kw_only=True)
class CLIArgs(argparse.Namespace):
    """A CLI argument dataclass with types, needed to make basedpyright happy."""

    def __init__(
        self,
        # pylint: disable-next=unused-argument
        build_opts_via_cli: str | None,  # noqa: ARG002
        # pylint: disable-next=unused-argument
        revision: str,  # noqa: ARG002
    ) -> None:
        """Initialize and inherit behaviour of argparse.Namespace, e.g. exceptions."""
        super().__init__()

    build_opts_via_cli: str | None
    revision: str


def parse_args(args: list[str]) -> CLIArgs:
    """Add parser options for compiling SpiderMonkey.

    :param args: Arguments to be parsed
    :return: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        prog=PACKAGE_NAME, description="Usage: %(prog)s [options]"
    )
    _ = parser.add_argument(
        "-b",
        "--build-opts-via-cli",  # Specify how the shell will be built.
        type=lambda x: x.removeprefix('"').removesuffix('"'),
        help='Specify build options, e.g. -b="--disable-debug --enable-optimize", '
        'note that the "equals" symbol is needed for a single build flag, run -h with '
        "other package to get a generated list",
    )
    _ = parser.add_argument(
        "-r", "--revision", default="", help="Specify revision to build"
    )
    for arg in args:  # Must happen before parser.parse_args runs on args
        if (
            any(arg.startswith(x) for x in ("-b", "--build-opts-via-cli"))
            and "=" not in arg
        ):
            parser.error('"=" is needed for -b or --build-opts-via-cli due to argparse')

    return parser.parse_args(
        args, namespace=CLIArgs(build_opts_via_cli="", revision="")
    )
