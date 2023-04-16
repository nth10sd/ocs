"""Constants used throughout."""

from __future__ import annotations

from pathlib import Path
import platform
import subprocess
from typing import Final

from zzbase.shell_compile_prereqs.spidermonkey import find_latest_icu_version
from zzbase.util import constants as zzconsts

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
        clang_cl_major_version = clang_cl_version.split(".", maxsplit=1)[0]
        CLANG_VER: Final = (
            clang_cl_major_version  # It was 15.0.5 but changed to only 16
            if int(clang_cl_major_version) >= 16
            else clang_cl_version
        )

    # At least Windows required the ICU libraries in dist/bin.
    # Debug builds seem to have their debug "d" notation *before* the ICU version.
    # https://searchfox.org/mozilla-central/search?q=%24%28IcuBinOutputDir%29%5Cicudt
    for icu_ver in find_latest_icu_version(71):  # m-c 633690 Fx106 earliest working rev
        zzconsts.ALL_LIBS.extend(
            (
                f"{zzconsts.RUN_ICUUC_LIB_EXCL_EXT}{icu_ver}.dll",
                f"{zzconsts.RUN_ICUUC_LIB_EXCL_EXT}d{icu_ver}.dll",
                f"{zzconsts.RUN_ICUUC_LIB_EXCL_EXT}{icu_ver}d.dll",
                f"{zzconsts.RUN_ICUIN_LIB_EXCL_EXT}{icu_ver}.dll",
                f"{zzconsts.RUN_ICUIN_LIB_EXCL_EXT}d{icu_ver}.dll",
                f"{zzconsts.RUN_ICUIN_LIB_EXCL_EXT}{icu_ver}d.dll",
                f"{zzconsts.RUN_ICUIO_LIB_EXCL_EXT}{icu_ver}.dll",
                f"{zzconsts.RUN_ICUIO_LIB_EXCL_EXT}d{icu_ver}.dll",
                f"{zzconsts.RUN_ICUIO_LIB_EXCL_EXT}{icu_ver}d.dll",
                f"{zzconsts.RUN_ICUDT_LIB_EXCL_EXT}{icu_ver}.dll",
                f"{zzconsts.RUN_ICUDT_LIB_EXCL_EXT}d{icu_ver}.dll",
                f"{zzconsts.RUN_ICUDT_LIB_EXCL_EXT}{icu_ver}d.dll",
                f"{zzconsts.RUN_ICUTEST_LIB_EXCL_EXT}{icu_ver}.dll",
                f"{zzconsts.RUN_ICUTEST_LIB_EXCL_EXT}d{icu_ver}.dll",
                f"{zzconsts.RUN_ICUTEST_LIB_EXCL_EXT}{icu_ver}d.dll",
                f"{zzconsts.RUN_ICUTU_LIB_EXCL_EXT}{icu_ver}.dll",
                f"{zzconsts.RUN_ICUTU_LIB_EXCL_EXT}d{icu_ver}.dll",
                f"{zzconsts.RUN_ICUTU_LIB_EXCL_EXT}{icu_ver}d.dll",
            )
        )
else:
    SSE2_FLAGS: Final = "-msse2 -mfpmath=sse"  # See bug 948321
