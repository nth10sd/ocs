# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Allows specification of build configuration parameters."""

import argparse
from pathlib import Path
import platform
import random
import sys
from typing import Any
from typing import Dict
from typing import List
from typing import Tuple

DEFAULT_TREES_LOCATION = Path.home() / "trees"


def chance(i: float) -> bool:
    """Chooses a random boolean result based on an input probability.

    :param i: Intended probability.
    :return: Result based on the input probability
    """
    return random.random() < i


class Randomizer:
    """Class to randomize parser options."""
    def __init__(self) -> None:
        self.options: List[Dict[str, object]] = []

    def add(self, name: str, weight: float) -> None:
        """Add the option name and its testing weight."""
        self.options.append({
            "name": name,
            "weight": weight,
        })

    def get_rnd_subset(self) -> List[object]:
        """Get a random subset of build options."""
        def get_weight(opt: Any) -> Any:
            return opt["weight"]
        return [opt["name"] for opt in self.options if chance(get_weight(opt))]


def add_parser_opts() -> Tuple[Any, Any]:
    """Add parser options.

    :return: Tuple containing the parser object and the Randomizer object
    """
    # Where to find the source dir and compiler, patching if necessary.
    parser = argparse.ArgumentParser(description="Usage: Don't use this directly")
    randomizer = Randomizer()

    def randomize_bool(name: List[str], weight: float, **kwargs: Any) -> None:
        """Add a randomized boolean option that defaults to False.

        Option also has a [weight] chance of being changed to True when using --random.

        :param name: Name of the build option
        :param weight: Weight of the build option
        :param kwargs: Remaining keyword arguments to be passed into parser.add_argument
        """
        randomizer.add(name[-1], weight)
        parser.add_argument(*name, action="store_true", default=False, **kwargs)

    parser.add_argument("--random",
                        dest="enableRandom",
                        action="store_true",
                        default=False,
                        help='Chooses sensible random build options. Defaults to "%(default)s".')
    parser.add_argument("-R", "--repodir",
                        dest="repo_dir",
                        type=Path,
                        help="Sets the source repository.")

    # Basic spidermonkey options
    randomize_bool(["--32"], 0.5,
                   dest="enable32",
                   help="Build 32-bit shells, but if not enabled, 64-bit shells are built.")
    randomize_bool(["--enable-debug"], 0.5,
                   dest="enableDbg",
                   help='Build shells with --enable-debug. Defaults to "%(default)s". '
                        "Currently defaults to True in configure.in on mozilla-central.")
    randomize_bool(["--disable-debug"], 0,
                   dest="disableDbg",
                   help='Build shells with --disable-debug. Defaults to "%(default)s". '
                        "Currently defaults to True in configure.in on mozilla-central.")
    randomize_bool(["--enable-optimize"], 0,
                   dest="enableOpt",
                   help='Build shells with --enable-optimize. Defaults to "%(default)s".')
    randomize_bool(["--disable-optimize"], 0.1,
                   dest="disableOpt",
                   help='Build shells with --disable-optimize. Defaults to "%(default)s".')
    randomize_bool(["--disable-profiling"], 0.5,
                   dest="disableProfiling",
                   help='Build with profiling off. Defaults to "True" on Linux, else "%(default)s".')

    # Memory debuggers
    randomize_bool(["--enable-address-sanitizer"], 0.3,
                   dest="enableAddressSanitizer",
                   help='Build with clang AddressSanitizer support. Defaults to "%(default)s".')
    randomize_bool(["--enable-valgrind"], 0.2,
                   dest="enableValgrind",
                   help='Build with valgrind.h bits. Defaults to "%(default)s". '
                        "Requires --enable-hardfp for ARM platforms.")
    # We do not use randomize_bool because we add this flag automatically if --enable-valgrind
    # is selected.
    parser.add_argument("--run-with-valgrind",
                        dest="runWithVg",
                        action="store_true",
                        default=False,
                        help="Run the shell under Valgrind. Requires --enable-valgrind.")

    # Misc spidermonkey options
    parser.add_argument("--enable-oom-breakpoint",  # Extra debugging help for OOM assertions
                        dest="enableOomBreakpoint",
                        action="store_true",
                        default=False,
                        help='Build shells with --enable-oom-breakpoint. Defaults to "%(default)s".')
    parser.add_argument("--without-intl-api",  # Speeds up compilation but is non-default
                        dest="enableWithoutIntlApi",
                        action="store_true",
                        default=False,
                        help='Build shells using --without-intl-api. Defaults to "%(default)s".')
    randomize_bool(["--enable-simulator=arm"], 0.3,
                   dest="enableSimulatorArm32",
                   help="Build shells with --enable-simulator=arm, only applicable to 32-bit shells. "
                        'Defaults to "%(default)s".')
    randomize_bool(["--enable-simulator=arm64"], 0.3,
                   dest="enableSimulatorArm64",
                   help="Build shells with --enable-simulator=arm64, only applicable to 64-bit shells. "
                        'Defaults to "%(default)s".')

    # If adding a new compile option, be mindful of repository randomization.
    # e.g. it may be in mozilla-central but not in mozilla-beta

    return parser, randomizer


def parse_shell_opts(args: Any) -> Any:
    """Parses shell options into a build_options object.

    :param args: Arguments to be parsed
    :return: An immutable build_options object
    """
    parser, randomizer = add_parser_opts()
    build_options = parser.parse_args(args.split())

    if build_options.enableRandom:
        build_options = gen_rnd_cfgs(parser, randomizer)
    else:
        build_options.build_options_str = args
        valid = are_args_valid(build_options)
        if not valid[0]:
            print(f"WARNING: This set of build options is not tested well because: {valid[1]}")

    # Ensures releng machines do not enter the if block and assumes mozilla-central always exists
    if DEFAULT_TREES_LOCATION.is_dir():
        # Repositories do not get randomized if a repository is specified.
        if build_options.repo_dir:
            build_options.repo_dir = build_options.repo_dir.expanduser()
        else:
            build_options.repo_dir = DEFAULT_TREES_LOCATION / "mozilla-central"

            if not build_options.repo_dir.is_dir():
                sys.exit("repo_dir is not specified, and a default repository location cannot be confirmed. Exiting...")

        assert (build_options.repo_dir / ".hg" / "hgrc").is_file()
    elif build_options.repo_dir:
        build_options.repo_dir = build_options.repo_dir.expanduser()
        assert (build_options.repo_dir / ".hg" / "hgrc").is_file()
    else:
        sys.exit(f"DEFAULT_TREES_LOCATION not found at: {DEFAULT_TREES_LOCATION}. Exiting...")

    return build_options


def compute_shell_type(build_options: Any) -> str:  # pylint: disable=too-complex
    """Return configuration information of the shell.

    :param build_options: Object containing build options
    :return: Filename with build option information added
    """
    file_name = ["js"]
    if build_options.enableDbg:
        file_name.append("dbg")
    if build_options.disableOpt:
        file_name.append("optDisabled")
    file_name.append("32" if build_options.enable32 else "64")
    if build_options.disableProfiling:
        file_name.append("profDisabled")
    if build_options.enableAddressSanitizer:
        file_name.append("asan")
    if build_options.enableValgrind:
        file_name.append("vg")
    if build_options.enableOomBreakpoint:
        file_name.append("oombp")
    if build_options.enableWithoutIntlApi:
        file_name.append("intlDisabled")
    if build_options.enableSimulatorArm32:
        file_name.append("armsim32")
    if build_options.enableSimulatorArm64:
        file_name.append("armsim64")
    file_name.append(platform.system().lower())
    file_name.append(platform.machine().lower())

    assert "" not in file_name, f'Filename "{file_name!r}" should not have empty elements.'
    return "-".join(file_name)


def compute_shell_name(build_options: object, build_rev: str) -> str:
    """Return the shell type together with the build revision."""
    return f"{compute_shell_type(build_options)}-{build_rev}"


def are_args_valid(args: Any) -> Tuple[bool, str]:  # pylint: disable=too-many-branches,too-complex,too-many-return-statements
    """Check to see if chosen arguments are valid.

    :param args: Input arguments
    :return: Whether arguments are valid, with a string as the explanation
    """
    # Consider refactoring this to raise exceptions instead.
    if args.enableDbg and args.disableDbg:
        return False, "Making a debug, non-debug build would be contradictory."
    if args.enableOpt and args.disableOpt:
        return False, "Making an optimized, non-optimized build would be contradictory."
    if not args.enableDbg and args.disableOpt:
        return False, "Making a non-debug, non-optimized build would be kind of silly."

    if platform.system() == "Darwin" and args.enable32:
        return False, "We are no longer going to ship 32-bit Mac binaries."
    if platform.machine() == "aarch64" and args.enable32:
        return False, "ARM64 systems cannot seem to compile 32-bit binaries properly."
    if "Microsoft" in platform.release() and args.enable32:
        return False, "WSL does not seem to support 32-bit Linux binaries yet."

    if args.enableValgrind:
        return False, "FIXME: We need to set LD_LIBRARY_PATH first, else Valgrind segfaults."
        # Test with leak-checking disabled, test that reporting works, test only on x64 16.04
        # Test with bug 1278887
        # Also ensure we are running autobisectjs w/Valgrind having the --error-exitcode=?? flag
        # Uncomment the following when we unbreak Valgrind fuzzing.
        # if not which("valgrind"):
        #     return False, "Valgrind is not installed."
        # if not args.enableOpt:
        #     # FIXME: Isn't this enabled by default??  # pylint: disable=fixme
        #     return False, "Valgrind needs opt builds."
        # if args.enableAddressSanitizer:
        #     return False, "One should not compile with both Valgrind flags and ASan flags."

        # if platform.system() == "Windows":
        #     return False, "Valgrind does not work on Windows."
        # if platform.system() == "Darwin":
        #     return False, "Valgrind does not work well with Mac OS X 10.10 Yosemite."

    if args.runWithVg and not args.enableValgrind:
        return False, "--run-with-valgrind needs --enable-valgrind."

    if args.enableAddressSanitizer:
        if args.enable32:
            return False, "32-bit ASan builds fail on 18.04 due to https://github.com/google/sanitizers/issues/954."
        if platform.system() == "Linux" and "Microsoft" in platform.release():
            return False, "Linux ASan builds cannot yet work in WSL though there may be workarounds."
        if platform.system() == "Windows" and args.enable32:
            return False, "ASan is explicitly not supported in 32-bit Windows builds."

    if args.enableSimulatorArm32 or args.enableSimulatorArm64:
        if platform.system() == "Windows" and args.enableSimulatorArm32:
            return False, "Nobody runs the ARM32 simulators on Windows."
        if platform.system() == "Windows" and args.enableSimulatorArm64:
            return False, "Nobody runs the ARM64 simulators on Windows."
        if platform.system() == "Linux" and platform.machine() == "aarch64" and args.enableSimulatorArm32:
            return False, "Nobody runs the ARM32 simulators on ARM64 Linux."
        if platform.system() == "Linux" and platform.machine() == "aarch64" and args.enableSimulatorArm64:
            return False, "Nobody runs the ARM64 simulators on ARM64 Linux."
        if args.enableSimulatorArm32 and not args.enable32:
            return False, "The 32-bit ARM simulator builds are only for 32-bit binaries."
        if args.enableSimulatorArm64 and args.enable32:
            return False, "The 64-bit ARM simulator builds are only for 64-bit binaries."

    return True, ""


def gen_rnd_cfgs(parser: Any, randomizer: Any) -> Any:
    """Generates random configurations.

    :param parser: Parser object for specified configurations
    :param randomizer: Randomizer object for getting a random subset of build options
    :return: build_options object
    """
    while True:
        rnd_args = randomizer.get_rnd_subset()
        if "--enable-valgrind" in rnd_args and chance(0.95):
            rnd_args.append("--run-with-valgrind")
        build_options = parser.parse_args(rnd_args)
        if are_args_valid(build_options)[0]:
            build_options.build_options_str = " ".join(rnd_args)  # Used for autobisectjs
            build_options.enableRandom = True  # This has to be true since we are randomizing...
            return build_options


def main() -> None:
    """Main build_options function, generates sample random build configurations."""
    print("Here are some sample random build configurations that can be generated:")
    parser, randomizer = add_parser_opts()

    for _ in range(30):
        build_options = gen_rnd_cfgs(parser, randomizer)
        print(build_options.build_options_str)

    print()
    print("Running this file directly doesn't do anything, but here's our subparser help:")
    print()
    parser.parse_args()


if __name__ == "__main__":
    main()
