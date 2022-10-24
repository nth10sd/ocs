"""Test compiling a shell."""

from __future__ import annotations

import contextlib
from functools import cache
import os
from pathlib import Path
import platform

import pytest
from zzbase.patching.common import patch_files
from zzbase.util.constants import VENV_SITE_PKGS

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
    if (
        "Monkeypatching coverage rev"
        not in (VENV_SITE_PKGS / "coverage" / "inorout.py").read_text()
    ):
        patch_files(  # Do not assert, as we do not care if patch is already applied
            VENV_SITE_PKGS,
            (
                VENV_SITE_PKGS
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
        in (VENV_SITE_PKGS / "coverage" / "inorout.py").read_text()  # Re-read again
    )

    default_parameters_debug = (
        "--enable-debug --disable-optimize --enable-oom-breakpoint --without-intl-api"
    )
    if platform.system() == "Linux":
        default_parameters_debug += " --enable-valgrind"
    # Remember to update the corresponding BUILDSM build parameters in CI as well
    build_opts = os.getenv("BUILDSM", default_parameters_debug)

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
            f"js-dbg-optDisabled-64{valgrind_name_param}-oombp-intlDisabled-"
            f"{platform.system().lower()}-{platform.machine().lower()}-"
            f"{hg_hash_of_default}"
        )
    elif (
        "--disable-debug --disable-profiling --enable-address-sanitizer"
    ) in build_opts:
        # Test compilation of an opt ASan shell with profiling disabled
        file_name = (
            f"js-64-profDisabled-asan-{platform.system().lower()}-"
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
