"""Constants used throughout."""

from __future__ import annotations

from pathlib import Path
import platform
from typing import Final

from psutil import cpu_count

COMPILATION_JOBS: int
if cpu_count() <= 2:
    COMPILATION_JOBS = 3  # 3 only for single/dual core computers
elif cpu_count() > cpu_count(logical=False):  # Some sort of hyperthreading is present
    COMPILATION_JOBS = round(cpu_count(logical=False) * 1.25)
else:
    COMPILATION_JOBS = cpu_count(logical=False)

ASAN_ERROR_EXIT_CODE: Final = 77
DEFAULT_TREES_LOCATION: Final = Path.home() / "trees"

RUN_MOZGLUE_LIB = ""
RUN_NSPR_LIB = ""
RUN_PLDS_LIB = ""
RUN_PLC_LIB = ""
RUN_TESTPLUG_LIB = ""

if platform.system() == "Windows":
    MAKE_BINARY = "mozmake"
    CLANG_VER: Final = "12.0.0"
    WIN_MOZBUILD_CLANG_PATH: Final = Path.home() / ".mozbuild" / "clang"

    # Library-related
    RUN_MOZGLUE_LIB = "mozglue.dll"
    RUN_NSPR_LIB = "nspr4.dll"
    RUN_PLDS_LIB = "plds4.dll"
    RUN_PLC_LIB = "plc4.dll"
    RUN_TESTPLUG_LIB = "testplug.dll"

    # These include running the js shell (mozglue) and should be in dist/bin.
    # At least Windows required the ICU libraries.
    ALL_RUN_LIBS = [
        RUN_MOZGLUE_LIB,
        RUN_NSPR_LIB,
        RUN_PLDS_LIB,
        RUN_PLC_LIB,
        RUN_TESTPLUG_LIB,
    ]

    # Needs to be updated when the earliest known working revision changes. Currently:
    # m-c 599232 Fx96, 1st w/ working Windows builds using SDK 10.0.19041.0
    WIN_ICU_VERS = [69]  # prior version
    WIN_ICU_VERS.append(70)  # m-c 599344 Fx96, 1st w/ ICU 70.1, see bug 1738422
    WIN_ICU_VERS.append(71)  # m-c 613773 Fx101, 1st w/ ICU 71.1, see bug 1763783

    # Search for changes to the versioning of the ICU files:
    # https://bit.ly/3jgrTSK
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
else:
    MAKE_BINARY = "make"
    SSE2_FLAGS: Final = "-msse2 -mfpmath=sse"  # See bug 948321

    if platform.system() == "Darwin":
        RUN_MOZGLUE_LIB = "libmozglue.dylib"
    elif platform.system() == "Linux":
        RUN_MOZGLUE_LIB = "libmozglue.so"
    else:
        raise RuntimeError("Unsupported platform")

    ALL_RUN_LIBS = [RUN_MOZGLUE_LIB, RUN_NSPR_LIB, RUN_PLDS_LIB, RUN_PLC_LIB]
