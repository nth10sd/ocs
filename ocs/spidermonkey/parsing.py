"""ocs spidermonkey parsing"""

from __future__ import annotations

import argparse

from zzbase.util.utils import PACKAGE_NAME


def parse_args(args: list[str]) -> argparse.Namespace:
    """Add parser options for compiling SpiderMonkey.

    :param args: Arguments to be parsed
    :return: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        prog=PACKAGE_NAME, description="Usage: %(prog)s [options]"
    )
    parser.add_argument(
        "-b",
        "--build-opts",  # Specify how the shell will be built.
        type=lambda x: str(x).removeprefix('"').removesuffix('"'),
        help='Specify build options, e.g. -b="--disable-debug --enable-optimize", '
        'note that the "equals" symbol is needed for a single build flag',
    )
    parser.add_argument(
        "-r",
        "--revision",
        help="Specify revision to build",
    )
    for arg in args:  # Must happen before parser.parse_args runs on args
        if any(arg.startswith(x) for x in ("-b", "--build-opts")) and "=" not in arg:
            parser.error('"=" is needed for -b or --build-opts due to argparse')

    return parser.parse_args(args)
