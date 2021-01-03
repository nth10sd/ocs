# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Allows SpiderMonkey shell inspection to ensure that it is compiled as intended."""

from __future__ import annotations

import json
import os
from pathlib import Path
import platform
from shlex import quote
import subprocess
from typing import Any
from typing import Tuple

from ocs.util import fs_helpers
from ocs.util import utils

ASAN_ERROR_EXIT_CODE = 77
RUN_MOZGLUE_LIB = ""
RUN_NSPR_LIB = ""
RUN_PLDS_LIB = ""
RUN_PLC_LIB = ""
RUN_TESTPLUG_LIB = ""

if platform.system() == "Windows":
    RUN_MOZGLUE_LIB = "mozglue.dll"
    RUN_NSPR_LIB = "nspr4.dll"
    RUN_PLDS_LIB = "plds4.dll"
    RUN_PLC_LIB = "plc4.dll"
    RUN_TESTPLUG_LIB = "testplug.dll"
elif platform.system() == "Darwin":
    RUN_MOZGLUE_LIB = "libmozglue.dylib"
elif platform.system() == "Linux":
    RUN_MOZGLUE_LIB = "libmozglue.so"

# These include running the js shell (mozglue) and should be in dist/bin.
# At least Windows required the ICU libraries.
ALL_RUN_LIBS = [RUN_MOZGLUE_LIB, RUN_NSPR_LIB, RUN_PLDS_LIB, RUN_PLC_LIB]
if platform.system() == "Windows":
    ALL_RUN_LIBS.append(RUN_TESTPLUG_LIB)
    WIN_ICU_VERS = []
    # Needs to be updated when the earliest known working revision changes. Currently:
    # m-c 528308 Fx78, 1st w/ python3 only, that does not check python2
    WIN_ICU_VERS.append(67)  # prior version
    # WIN_ICU_VERS.append(68)  # m-c XXXXXX Fx78, 1st w/ ICU 67.1, see bug 1632434 (to be updated)

    # Update if the following changes:
    # https://searchfox.org/mozilla-central/search?q=path%3Aintl%2Ficu%2Fsource%2F+.dll%3C%2FOutputFile%3E
    RUN_ICUUC_LIB_EXCL_EXT = "icuuc"
    RUN_ICUIN_LIB_EXCL_EXT = "icuin"
    RUN_ICUIO_LIB_EXCL_EXT = "icuio"
    RUN_ICUDT_LIB_EXCL_EXT = "icudt"
    RUN_ICUTEST_LIB_EXCL_EXT = "icutest"
    RUN_ICUTU_LIB_EXCL_EXT = "icutu"

    # Debug builds seem to have their debug "d" notation *before* the ICU version.
    # https://searchfox.org/mozilla-central/search?q=%24%28IcuBinOutputDir%29%5Cicudt
    for icu_ver in WIN_ICU_VERS:
        ALL_RUN_LIBS.append(f"{RUN_ICUUC_LIB_EXCL_EXT}{icu_ver}.dll")
        ALL_RUN_LIBS.append(f"{RUN_ICUUC_LIB_EXCL_EXT}d{icu_ver}.dll")
        ALL_RUN_LIBS.append(f"{RUN_ICUUC_LIB_EXCL_EXT}{icu_ver}d.dll")

        ALL_RUN_LIBS.append(f"{RUN_ICUIN_LIB_EXCL_EXT}{icu_ver}.dll")
        ALL_RUN_LIBS.append(f"{RUN_ICUIN_LIB_EXCL_EXT}d{icu_ver}.dll")
        ALL_RUN_LIBS.append(f"{RUN_ICUIN_LIB_EXCL_EXT}{icu_ver}d.dll")

        ALL_RUN_LIBS.append(f"{RUN_ICUIO_LIB_EXCL_EXT}{icu_ver}.dll")
        ALL_RUN_LIBS.append(f"{RUN_ICUIO_LIB_EXCL_EXT}d{icu_ver}.dll")
        ALL_RUN_LIBS.append(f"{RUN_ICUIO_LIB_EXCL_EXT}{icu_ver}d.dll")

        ALL_RUN_LIBS.append(f"{RUN_ICUDT_LIB_EXCL_EXT}{icu_ver}.dll")
        ALL_RUN_LIBS.append(f"{RUN_ICUDT_LIB_EXCL_EXT}d{icu_ver}.dll")
        ALL_RUN_LIBS.append(f"{RUN_ICUDT_LIB_EXCL_EXT}{icu_ver}d.dll")

        ALL_RUN_LIBS.append(f"{RUN_ICUTEST_LIB_EXCL_EXT}{icu_ver}.dll")
        ALL_RUN_LIBS.append(f"{RUN_ICUTEST_LIB_EXCL_EXT}d{icu_ver}.dll")
        ALL_RUN_LIBS.append(f"{RUN_ICUTEST_LIB_EXCL_EXT}{icu_ver}d.dll")

        ALL_RUN_LIBS.append(f"{RUN_ICUTU_LIB_EXCL_EXT}{icu_ver}.dll")
        ALL_RUN_LIBS.append(f"{RUN_ICUTU_LIB_EXCL_EXT}d{icu_ver}.dll")
        ALL_RUN_LIBS.append(f"{RUN_ICUTU_LIB_EXCL_EXT}{icu_ver}d.dll")


def arch_of_binary(binary: Path) -> str:
    """Test if a binary is 32-bit or 64-bit.

    :param binary: Path to compiled binary
    :return: Platform architecture of compiled binary
    """
    # We can possibly use the python-magic-bin PyPI library in the future
    unsplit_file_type = subprocess.run(
        ["file", str(binary)],
        check=True,
        cwd=os.getcwd(),
        stdout=subprocess.PIPE,
        timeout=99).stdout.decode("utf-8", errors="replace")
    filetype = unsplit_file_type.split(":", 1)[1]
    if platform.system() == "Windows":
        assert "MS Windows" in filetype
        return "32" if ("Intel 80386 32-bit" in filetype or "PE32 executable" in filetype) else "64"
    if "32-bit" in filetype or "i386" in filetype:
        assert "64-bit" not in filetype
        return "32"
    if "64-bit" in filetype:
        assert "32-bit" not in filetype
        return "64"
    return "INVALID"


def test_binary(shell_path: Path, args: Any, _use_vg: Any, stderr: Any = subprocess.STDOUT) -> Tuple[str, int]:
    """Test the given shell with the given args.

    :param shell_path: Path to the compiled shell binary
    :param args: Arguments used to compile the shell
    :param _use_vg: Whether Valgrind should be used
    :param stderr: stderr and where it should be redirected if needed
    :return: Tuple comprising the stdout of the run command and its return code
    """
    test_cmd = [str(shell_path)] + args
    utils.vdump(f'The testing command is: {" ".join(quote(str(x)) for x in test_cmd)}')

    test_env = fs_helpers.env_with_path(str(shell_path.parent))
    asan_options = f"exitcode={ASAN_ERROR_EXIT_CODE}"
    # Turn on LSan, Linux-only
    # macOS non-support: https://github.com/google/sanitizers/issues/1026
    # Windows non-support: https://developer.mozilla.org/en-US/docs/Mozilla/Testing/Firefox_and_Address_Sanitizer
    #   (search for LSan)
    # Termux Android aarch64 is not yet supported due to possible ptrace issues
    if platform.system() == "Linux" and not ("-asan-" in str(shell_path) and "-armsim64-" in str(shell_path)) and \
            "-aarch64-" not in str(shell_path):
        asan_options = "detect_leaks=1," + asan_options
        test_env.update({"LSAN_OPTIONS": "max_leaks=1,"})
    test_env.update({"ASAN_OPTIONS": asan_options})

    test_cmd_result = subprocess.run(
        test_cmd,
        check=False,
        cwd=os.getcwd(),
        env=test_env,
        stderr=stderr,
        stdout=subprocess.PIPE,
        timeout=999)
    out, return_code = test_cmd_result.stdout.decode("utf-8", errors="replace"), test_cmd_result.returncode
    utils.vdump(f"The exit code is: {return_code}")
    return out, return_code


def query_build_cfg(shell_path: Path, parameter: str) -> Any:
    """Test if a binary is compiled with specified parameters, in getBuildConfiguration().

    :param shell_path: Path of the shell
    :param parameter: Parameter that will be tested
    :return: Whether the parameter is supported by the shell
    """
    return json.loads(test_binary(shell_path,
                                  ["-e", f'print(getBuildConfiguration()["{parameter}"])'],
                                  False, stderr=subprocess.DEVNULL)[0].rstrip().lower())


def verify_binary(shell: Any) -> None:
    """Verify that the binary is compiled as intended.

    :param shell: Compiled binary object
    """
    binary = shell.shell_cache_js_bin_path

    assert arch_of_binary(binary) == ("32" if shell.build_opts.enable32 else "64")

    # Testing for debug or opt builds are different because there can be hybrid debug-opt builds.
    assert query_build_cfg(binary, "debug") == shell.build_opts.enableDbg

    assert query_build_cfg(binary, "asan") == shell.build_opts.enableAddressSanitizer
    # Checking for profiling status does not work with mozilla-beta and mozilla-release
    assert query_build_cfg(binary, "profiling") != shell.build_opts.disableProfiling
    if platform.machine() == "x86_64":
        assert (query_build_cfg(binary, "arm-simulator") and
                shell.build_opts.enable32) == shell.build_opts.enableSimulatorArm32
        assert (query_build_cfg(binary, "arm64-simulator") and not
                shell.build_opts.enable32) == shell.build_opts.enableSimulatorArm64
