"""Test compiling a shell."""

from __future__ import annotations

import contextlib
from functools import cache
import os
from pathlib import Path
import platform
import sys

import pytest
from zzbase.patching.common import patch_files

from ocs import build_options
from ocs.spidermonkey.hatch import SMShell
from ocs.util import hg_helpers

from .util.constants_for_tests import MC_PATH
from .util.constants_for_tests import SHELL_CACHE


@pytest.mark.slow()
@cache
def test_shell_compile() -> Path:
    """Test compilation of shells depending on the specified environment variable.

    :raise ValueError: If default_parameters_debug is not in build_opts
    :return: Path to the compiled shell.
    """
    assert MC_PATH.is_dir()
    # Change the repository location by uncommenting this line and specifying the
    # correct one: "-R ~/trees/mozilla-central/")

    # Look for custom coverage.py patch
    venv_site_packages = (
        next((Path(sys.executable).parents[1] / "lib").glob("*")) / "site-packages"
    )
    patch_files(
        venv_site_packages,
        (
            venv_site_packages
            / "zzbase"
            / "data"
            / "pypi_library_patches"
            / "coverage"
            / "64130ee5-patch-for-m-c-to-work.diff"
        ),
        1,
    )
    assert (
        "Monkeypatching coverage rev"
        in (venv_site_packages / "coverage" / "inorout.py").read_text()
    )

    default_parameters_debug = (
        "--enable-debug --disable-optimize --enable-oom-breakpoint"
    )
    if platform.system() == "Linux":
        default_parameters_debug += " --enable-valgrind"
    # Remember to update the corresponding BUILD build parameters in .travis.yml as well
    build_opts = os.getenv("BUILD", default_parameters_debug)

    opts_parsed = build_options.parse_shell_opts(build_opts)
    hg_hash_of_default = hg_helpers.get_repo_hash_and_id(opts_parsed.repo_dir)[0]
    # Ensure exit code is 0
    assert not SMShell(opts_parsed, hg_hash_of_default).run([f"-b={build_opts}"])

    file_name = ""
    valgrind_name_param = ""
    if platform.system() == "Linux":
        valgrind_name_param += "-vg"
    if default_parameters_debug in build_opts:
        # Test compiling a debug shell w/OOM breakpoint support - Valgrind only on Linux
        file_name = (
            f"js-dbg-optDisabled-64{valgrind_name_param}-oombp-"
            f"{platform.system().lower()}-{platform.machine().lower()}-"
            f"{hg_hash_of_default}"
        )
    elif "--disable-debug --disable-profiling --without-intl-api" in build_opts:
        # Test compilation of an opt shell with both profiling and Intl support disabled
        # This set of builds should also have the following:
        # 32-bit with ARM, with asan, and with clang
        file_name = (
            f"js-64-profDisabled-intlDisabled-{platform.system().lower()}-"
            f"{platform.machine().lower()}-"
            f"{hg_hash_of_default}"
        )
    else:
        raise ValueError(
            f'default_parameters_debug "{default_parameters_debug}"'
            f' is not in build_opts "{build_opts}"',
        )

    js_bin_path = SHELL_CACHE / file_name / file_name
    if platform.system() == "Windows":
        js_bin_path = js_bin_path.with_suffix(".exe")
    assert js_bin_path.is_file()

    with contextlib.suppress(OSError):
        SHELL_CACHE.rmdir()  # Cleanup shell-cache test directory only if empty

    return js_bin_path
