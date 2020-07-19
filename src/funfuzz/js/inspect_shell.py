# coding=utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Allows inspection of the SpiderMonkey shell to ensure that it is compiled as intended with specified configurations.
"""

import json
import os
import platform
from shlex import quote
import subprocess

from ..util import utils

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
    # m-c 436503 Fx64, 1st w/ working Windows builds with a recent Win10 SDK, see bug 1485224
    WIN_ICU_VERS.append(62)  # prior version
    WIN_ICU_VERS.append(63)  # m-c 443997 Fx65, 1st w/ ICU 63.1, see bug 1499026
    WIN_ICU_VERS.append(64)  # m-c 467933 Fx68, 1st w/ ICU 64.1, see bug 1533481
    WIN_ICU_VERS.append(65)  # m-c 498522 Fx72, 1st w/ ICU 65.1, see bug 1583269
    WIN_ICU_VERS.append(66)  # m-c 519547 Fx76, 1st w/ ICU 66.1, see bug 1610512
    WIN_ICU_VERS.append(67)  # m-c 528100 Fx78, 1st w/ ICU 67.1, see bug 1632434

    # Update if the following changes:
    # https://dxr.mozilla.org/mozilla-central/search?q=%3C%2FOutputFile%3E+.dll+path%3Aintl%2Ficu%2Fsource%2F&case=true
    RUN_ICUUC_LIB_EXCL_EXT = "icuuc"
    RUN_ICUIN_LIB_EXCL_EXT = "icuin"
    RUN_ICUIO_LIB_EXCL_EXT = "icuio"
    RUN_ICUDT_LIB_EXCL_EXT = "icudt"
    RUN_ICUTEST_LIB_EXCL_EXT = "icutest"
    RUN_ICUTU_LIB_EXCL_EXT = "icutu"

    # Debug builds seem to have their debug "d" notation *before* the ICU version.
    # Check https://dxr.mozilla.org/mozilla-central/search?q=%40BINPATH%40%2Ficudt&case=true&redirect=true
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


def archOfBinary(binary):  # pylint: disable=inconsistent-return-statements,invalid-name,missing-param-doc
    # pylint: disable=missing-return-doc,missing-return-type-doc,missing-type-doc
    """Test if a binary is 32-bit or 64-bit."""
    # We can possibly use the python-magic-bin PyPI library in the future
    unsplit_file_type = subprocess.run(
        ["file", str(binary)],
        check=True,
        cwd=os.getcwd(),
        stdout=subprocess.PIPE,
        timeout=99).stdout.decode("utf-8", errors="replace")
    filetype = unsplit_file_type.split(":", 1)[1]
    if platform.system() == "Windows":  # pylint: disable=no-else-return
        assert "MS Windows" in filetype
        return "32" if ("Intel 80386 32-bit" in filetype or "PE32 executable" in filetype) else "64"
    else:
        if "32-bit" in filetype or "i386" in filetype:
            assert "64-bit" not in filetype
            return "32"
        if "64-bit" in filetype:
            assert "32-bit" not in filetype
            return "64"


def testBinary(shellPath, args, _useValgrind, stderr=subprocess.STDOUT):  # pylint: disable=invalid-name
    # pylint: disable=missing-param-doc,missing-return-doc,missing-return-type-doc,missing-type-doc
    """Test the given shell with the given args."""
    test_cmd = [] + [str(shellPath)] + args
    utils.vdump(f'The testing command is: {" ".join(quote(str(x)) for x in test_cmd)}')

    test_env = utils.env_with_path(str(shellPath.parent))
    asan_options = f"exitcode={ASAN_ERROR_EXIT_CODE}"
    # Turn on LSan, Linux-only
    # macOS non-support: https://github.com/google/sanitizers/issues/1026
    # Windows non-support: https://developer.mozilla.org/en-US/docs/Mozilla/Testing/Firefox_and_Address_Sanitizer
    #   (search for LSan)
    if platform.system() == "Linux" and not ("-asan-" in str(shellPath) and "-armsim64-" in str(shellPath)):
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


def queryBuildConfiguration(s, parameter):  # pylint: disable=invalid-name,missing-param-doc,missing-return-doc
    # pylint: disable=missing-return-type-doc,missing-type-doc
    """Test if a binary is compiled with specified parameters, in getBuildConfiguration()."""
    return json.loads(testBinary(s,
                                 ["-e", f'print(getBuildConfiguration()["{parameter}"])'],
                                 False, stderr=subprocess.DEVNULL)[0].rstrip().lower())


def verifyBinary(sh):  # pylint: disable=invalid-name,missing-param-doc,missing-type-doc
    """Verify that the binary is compiled as intended."""
    binary = sh.get_shell_cache_js_bin_path()

    assert archOfBinary(binary) == ("32" if sh.build_opts.enable32 else "64")

    # Testing for debug or opt builds are different because there can be hybrid debug-opt builds.
    assert queryBuildConfiguration(binary, "debug") == sh.build_opts.enableDbg

    assert queryBuildConfiguration(binary, "more-deterministic") == sh.build_opts.enableMoreDeterministic
    assert queryBuildConfiguration(binary, "asan") == sh.build_opts.enableAddressSanitizer
    # Checking for profiling status does not work with mozilla-beta and mozilla-release
    assert queryBuildConfiguration(binary, "profiling") != sh.build_opts.disableProfiling
    if platform.machine() == "x86_64":
        assert (queryBuildConfiguration(binary, "arm-simulator") and
                sh.build_opts.enable32) == sh.build_opts.enableSimulatorArm32
        assert (queryBuildConfiguration(binary, "arm64-simulator") and not
                sh.build_opts.enable32) == sh.build_opts.enableSimulatorArm64
