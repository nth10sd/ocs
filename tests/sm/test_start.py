"""Test start.py from <package name>.sm."""

from __future__ import annotations

import contextlib
from functools import cache
import os
from pathlib import Path

import pytest
from zzbase.js_shells.spidermonkey import build_options
from zzbase.patching.common import patch_files
from zzbase.util.constants import MC_PATH
from zzbase.util.constants import TREES_PATH
from zzbase.util.constants import VENV_SITE_PKGS
from zzbase.util.constants import HostPlatform as Hp
from zzbase.vcs.git_helpers import get_repo_hash
from zzbase.vcs.git_helpers import get_repo_num_val

from ocs.sm import start
from ocs.spidermonkey.hatch import OldSMShell
from ocs.util import hg_helpers

SHELL_CACHE = Path.home() / "shell-cache"


@pytest.mark.slow
@cache
def test_main() -> None:
    """Test compilation of shells depending on the specified environment variable.

    :raise ValueError: If default_parameters_debug is not in build_opts
    """
    assert MC_PATH.is_dir() or (TREES_PATH / "firefox").is_dir()
    # Change the repository location by uncommenting this line and specifying the
    # correct one: "-R ~/trees/firefox/")

    # Look for custom coverage.py patch
    if (
        "Monkeypatching coverage rev"
        not in (VENV_SITE_PKGS / "coverage" / "inorout.py").read_text()
    ):
        _ = patch_files(  # Do not assert, as we do not care if patch is already applied
            VENV_SITE_PKGS,
            (
                VENV_SITE_PKGS
                / "zzbase"
                / "data"
                / "pypi_library_patches"
                / "coverage"
                / "patch-for-m-c-to-work.diff"
            ),
            1,
        )
    assert (  # If this assert fails, try removing monkeypatching section above
        "Monkeypatching coverage rev"
        in (VENV_SITE_PKGS / "coverage" / "inorout.py").read_text()  # Re-read again
    )

    default_parameters_debug = (
        "--enable-debug --disable-optimize --enable-oom-breakpoint"
    )
    if Hp.IS_LINUX:
        default_parameters_debug += " --enable-valgrind"
    # Remember to update the corresponding BUILDSM build parameters in CI as well
    # .rstrip() is required, as we pass in " " (empty space) on Win CI. The "" null
    # string cannot seem to propagate properly from PowerShell -> batch script -> bash
    build_opts = os.getenv("BUILDSM", default_parameters_debug).rstrip()

    opts_parsed = build_options.parse_shell_opts(
        build_opts.split() if build_opts else [], is_hg=MC_PATH.is_dir()
    )
    repo_hash = (
        hg_helpers.get_repo_hash_and_id(opts_parsed.repo_dir)[0]
        if (opts_parsed.repo_dir / ".hg" / "hgrc").is_file()
        else get_repo_hash(opts_parsed.repo_dir)
    )
    if MC_PATH.is_dir():
        old_smshell = OldSMShell(opts_parsed, hg_hash=repo_hash)
        # Ensure exit code is 0
        assert not old_smshell.run([f"-b={build_opts}"])

        file_name = f"{build_options.compute_shell_type(opts_parsed)}-{repo_hash}"
    else:
        start.main([f"-b={build_opts}"])

        numerical_head_value = (
            str(get_repo_num_val(opts_parsed.repo_dir))
            if (opts_parsed.repo_dir / ".git" / "config").is_file()
            else ""
        )
        file_name = (
            f"{build_options.compute_shell_type(opts_parsed)}"
            f"-{repo_hash[:12]}"
            f"{f'-{numerical_head_value}'}"
        )

    js_bin_path = SHELL_CACHE / file_name / file_name
    js_bin_path = js_bin_path.with_suffix(".exe") if Hp.IS_WIN_MB else js_bin_path
    assert js_bin_path.is_file()

    with contextlib.suppress(OSError):
        SHELL_CACHE.rmdir()  # Cleanup shell-cache test directory only if empty
