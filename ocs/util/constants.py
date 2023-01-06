"""Constants used throughout."""

from __future__ import annotations

from pathlib import Path
import platform
import subprocess
from typing import Final

from psutil import cpu_count

COMPILATION_JOBS = (
    3  # Set to 3 only for single/dual core computers
    if cpu_count() <= 2
    else (
        round(cpu_count(logical=False) * 1.25)  # Some sort of hyperthreading is present
        if cpu_count() > cpu_count(logical=False)
        else cpu_count(logical=False)
    )
)

ASAN_ERROR_EXIT_CODE: Final = 77
DEFAULT_TREES_LOCATION: Final = Path.home() / "trees"

RUN_MOZGLUE_LIB = ""
RUN_NSPR_LIB = ""
RUN_PLDS_LIB = ""
RUN_PLC_LIB = ""

if platform.system() == "Windows":
    WIN_MOZBUILD_CLANG_PATH: Final = Path.home() / ".mozbuild" / "clang"
    WIN_CLANG_CL: Final = WIN_MOZBUILD_CLANG_PATH / "bin" / "clang-cl.exe"
    if WIN_CLANG_CL.is_file():
        clang_cl_version = (
            subprocess.run([WIN_CLANG_CL, "--version"], capture_output=True, check=True)
            .stdout.decode("utf-8", errors="surrogateescape")
            .split(" (", maxsplit=1)[0]
            .removeprefix("clang version ")
        )
        CLANG_VER: Final = clang_cl_version

    # Library-related
    RUN_MOZGLUE_LIB = "mozglue.dll"
    RUN_NSPR_LIB = "nspr4.dll"
    RUN_PLDS_LIB = "plds4.dll"
    RUN_PLC_LIB = "plc4.dll"

    # These include running the js shell (mozglue) and should be in dist/bin.
    # At least Windows required the ICU libraries.
    ALL_RUN_LIBS = [
        RUN_MOZGLUE_LIB,
        RUN_NSPR_LIB,
        RUN_PLDS_LIB,
        RUN_PLC_LIB,
    ]

    # Needs to be updated when the earliest known working revision changes
    WIN_ICU_VERS: list[int] = []  # Current earliest known working rev: m-c 633690 Fx106
    WIN_ICU_VERS.extend(
        (
            71,  # prior version
            # 72,  # m-c ?????? Fx???
        )
    )

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
        ALL_RUN_LIBS.extend(
            (
                f"{RUN_ICUUC_LIB_EXCL_EXT}{icu_ver}.dll",
                f"{RUN_ICUUC_LIB_EXCL_EXT}d{icu_ver}.dll",
                f"{RUN_ICUUC_LIB_EXCL_EXT}{icu_ver}d.dll",
                f"{RUN_ICUIN_LIB_EXCL_EXT}{icu_ver}.dll",
                f"{RUN_ICUIN_LIB_EXCL_EXT}d{icu_ver}.dll",
                f"{RUN_ICUIN_LIB_EXCL_EXT}{icu_ver}d.dll",
                f"{RUN_ICUIO_LIB_EXCL_EXT}{icu_ver}.dll",
                f"{RUN_ICUIO_LIB_EXCL_EXT}d{icu_ver}.dll",
                f"{RUN_ICUIO_LIB_EXCL_EXT}{icu_ver}d.dll",
                f"{RUN_ICUDT_LIB_EXCL_EXT}{icu_ver}.dll",
                f"{RUN_ICUDT_LIB_EXCL_EXT}d{icu_ver}.dll",
                f"{RUN_ICUDT_LIB_EXCL_EXT}{icu_ver}d.dll",
                f"{RUN_ICUTEST_LIB_EXCL_EXT}{icu_ver}.dll",
                f"{RUN_ICUTEST_LIB_EXCL_EXT}d{icu_ver}.dll",
                f"{RUN_ICUTEST_LIB_EXCL_EXT}{icu_ver}d.dll",
                f"{RUN_ICUTU_LIB_EXCL_EXT}{icu_ver}.dll",
                f"{RUN_ICUTU_LIB_EXCL_EXT}d{icu_ver}.dll",
                f"{RUN_ICUTU_LIB_EXCL_EXT}{icu_ver}d.dll",
            )
        )
else:
    SSE2_FLAGS: Final = "-msse2 -mfpmath=sse"  # See bug 948321

    if platform.system() == "Darwin":
        RUN_MOZGLUE_LIB = "libmozglue.dylib"
        RUN_NSPR_LIB = "libnspr4.dylib"
        RUN_PLDS_LIB = "libplds4.dylib"
        RUN_PLC_LIB = "libplc4.dylib"
    elif platform.system() == "Linux":
        RUN_MOZGLUE_LIB = "libmozglue.so"
    else:
        raise RuntimeError("Unsupported platform")  # pragma: no cover

    ALL_RUN_LIBS = [RUN_MOZGLUE_LIB, RUN_NSPR_LIB, RUN_PLDS_LIB, RUN_PLC_LIB]
