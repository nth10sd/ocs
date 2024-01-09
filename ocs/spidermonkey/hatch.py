"""Common shell object code."""

from __future__ import annotations

import json
from logging import INFO as INFO_LOG_LEVEL
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import traceback
from typing import IO

from zzbase.js_shells.spidermonkey import build_options
from zzbase.js_shells.spidermonkey.hatch import SMShell
from zzbase.js_shells.spidermonkey.hatch import SMShellError
from zzbase.util import constants as zzconsts
from zzbase.util.constants import HostPlatform as Hp
from zzbase.util.fs_helpers import env_with_path
from zzbase.util.fs_helpers import get_lock_dir_path
from zzbase.util.fs_helpers import handle_rm_readonly_files
from zzbase.util.logging import get_logger
from zzbase.util.utils import LockDir
from zzbase.util.utils import autoconf_run
from zzbase.vcs import git_helpers
from zzbase.vcs import hg_helpers

from ocs.spidermonkey.parsing import parse_args
from ocs.util import hg_helpers as ocs_hg_helpers
from ocs.util import misc_progs

OCS_SM_HATCH_LOG = get_logger(
    __name__, fmt="%(asctime)s %(levelname)-8s [%(funcName)s] %(message)s"
)
OCS_SM_HATCH_LOG.setLevel(INFO_LOG_LEVEL)


class OldSMShellError(SMShellError):
    """Error class unique to OldSMShell objects."""


class OldSMShell(SMShell):
    """A OldSMShell object represents an actual compiled shell binary.

    :param build_opts: Object containing the build options defined in build_options.py
    :param git_hash: Git repo changeset hash
    :param hg_hash: Mercurial (hg) changeset hash
    """

    @classmethod
    def main(cls: type[SMShell], args: list[str] | None = None) -> int:
        """OldSMShell class main method.

        :param args: Additional parameters
        :raise OldSMShellError: When the run function encounters an error
        :return: 0, to denote a successful compile and 1, to denote a failed compile
        """
        if not args:
            # Ignored (code coverage), as function is tested by passing in a known args
            args = sys.argv[1:]  # pragma: no cover
        try:
            return cls.run(args)
        except OldSMShellError:
            OCS_SM_HATCH_LOG.exception("The run function encountered an error")
            raise

    @staticmethod
    def run(argv: list[str]) -> int:
        """Build a shell and place it in the autobisectjs cache.

        :param argv: Additional parameters
        :raise OldSMShellError: If repository is not clean
        :return: 0, to denote a successful compile
        """
        options = parse_args(argv)
        parse_shell_opts_list: list[str] = (
            options.build_opts.split() if options.build_opts else []
        )
        options.build_opts = build_options.parse_shell_opts(parse_shell_opts_list)

        with LockDir(
            get_lock_dir_path(Path.home(), options.build_opts.repo_dir),
        ):
            if options.revision:
                shell = OldSMShell(options.build_opts, hg_hash=options.revision)
            elif (options.build_opts.repo_dir / ".hg" / "hgrc").is_file():
                local_orig_hg_hash = ocs_hg_helpers.get_repo_hash_and_id(
                    options.build_opts.repo_dir,
                )[0]
                shell = OldSMShell(options.build_opts, hg_hash=local_orig_hg_hash)
            else:
                local_orig_git_hash = git_helpers.get_repo_hash(
                    options.build_opts.repo_dir,
                )
                if not (
                    git_helpers.is_repo_clean(options.build_opts.repo_dir)
                    or options.build_opts.overwrite_unclean_repo
                ):
                    raise OldSMShellError("Repository is not clean")
                shell = OldSMShell(options.build_opts, git_hash=local_orig_git_hash)

            obtain_shell(shell, update_to_rev=options.revision)

            shell_cache_abs_dir = shell.shell_cache_js_bin_path.parents[-3]
            OCS_SM_HATCH_LOG.info(  # Output with "~" instead of the full absolute dir
                "Desired shell is at:\n\n~/%s",
                shell.shell_cache_js_bin_path.relative_to(shell_cache_abs_dir),
            )

        return 0


def configure_js_shell_compile(shell: SMShell) -> None:
    """Configure, compile and copy a js shell according to required parameters.

    :param shell: Potential compiled shell object
    :raise CalledProcessError: If the shell failed to compile
    """
    OCS_SM_HATCH_LOG.info("Compiling build: %s", shell.build_opts.build_options_str)
    js_objdir_path = shell.shell_cache_dir / "objdir-js"
    js_objdir_path.mkdir()
    shell.js_objdir = js_objdir_path

    # Run autoconf 2.13 only on non-Windows platforms if repository revision is before:
    #   m-c rev 633690:c5dc125ea32ba3e9a7c3fe3cf5be05abd17013a3, Fx106
    #   gecko-dev 511135:b4a2cfe25078c17e2063a6866a3d2caf9d61651f, Fx106
    # See bug 1787977. m-c rev has been bumped to account for known broken ranges
    if not Hp.IS_WIN_MB and (
        (
            (shell.build_opts.repo_dir / ".hg" / "hgrc").is_file()
            and hg_helpers.exists_and_is_ancestor(
                shell.build_opts.repo_dir,
                shell.hg_hash,
                "parents(c5dc125ea32ba3e9a7c3fe3cf5be05abd17013a3)",
            )
        )
        or (
            not (shell.build_opts.repo_dir / ".hg" / "hgrc").is_file()
            and git_helpers.exists_and_is_ancestor(
                shell.build_opts.repo_dir,
                shell.git_hash,
                "b4a2cfe25078c17e2063a6866a3d2caf9d61651f",
            )
        )
    ):
        autoconf_run(shell.build_opts.repo_dir / "js" / "src")

    shell.configure()
    try:
        subprocess.run(
            shell.cfg_cmd_excl_env,
            check=True,
            cwd=shell.js_objdir,
            env=shell.env_full,
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as ex:
        with (shell.shell_cache_dir / f"{shell.shell_name_without_ext}.busted").open(
            "a", encoding="utf-8", errors="replace"
        ) as f:
            repo_name = (
                shell.hg_repo_name
                if (shell.build_opts.repo_dir / ".hg" / "hgrc").is_file()
                else shell.git_repo_name
            )
            hash_ = (
                shell.hg_hash
                if (shell.build_opts.repo_dir / ".hg" / "hgrc").is_file()
                else shell.git_hash
            )
            f.write(
                f"Configuration of {repo_name} rev {hash_} "
                "failed with the following output:\n",
            )
            f.write(ex.stdout.decode("utf-8", errors="replace"))
        raise

    sm_compile(shell)
    verify_binary(shell)
    shell.env_dump_and_cleanup()


def sm_compile(shell: SMShell) -> Path:
    """Compile a binary and copy essential compiled files into a desired structure.

    :param shell: SpiderMonkey shell parameters
    :raise OSError: Raises when a compiled shell is absent
    :return: Path to the compiled shell
    """
    cmd_list = [
        str(zzconsts.MAKE_BINARY_PATH),
        "-C",
        str(shell.js_objdir),
        f"-j{zzconsts.COMPILATION_JOBS}",
        "-s",
    ]
    # Note that having a non-zero exit code does not mean that the operation did not
    # succeed, for example when compiling a shell. A non-zero exit code can appear even
    # though a shell compiled successfully. Thus, we should *not* use check=True here.
    out = subprocess.run(
        cmd_list,
        check=False,
        cwd=shell.js_objdir,
        env=shell.env_full,
        stderr=subprocess.STDOUT,
        stdout=subprocess.PIPE,
    ).stdout.decode("utf-8", errors="replace")

    if not shell.shell_compiled_path.is_file():
        if (Hp.IS_LINUX | Hp.IS_MAC) and (
            "internal compiler error: Killed (program cc1plus)" in out
            or "error: unable to execute command: Killed"  # GCC running out of memory
            in out
        ):  # Clang running out of memory
            OCS_SM_HATCH_LOG.info(
                "Trying once more due to the compiler running out of memory..."
            )
            out = subprocess.run(
                cmd_list,
                check=False,
                cwd=shell.js_objdir,
                env=shell.env_full,
                stderr=subprocess.STDOUT,
                stdout=subprocess.PIPE,
            ).stdout.decode("utf-8", errors="replace")
        # `make` can return a non-zero error, but later a shell still gets compiled.
        if shell.shell_compiled_path.is_file():
            OCS_SM_HATCH_LOG.info(
                "A shell was compiled even though there was a non-zero exit code. "
                "Continuing...",
            )

    if shell.shell_compiled_path.is_file():
        shutil.copy2(str(shell.shell_compiled_path), str(shell.shell_cache_js_bin_path))
        for run_lib in shell.shell_compiled_runlibs_path:
            if run_lib.is_file():
                shutil.copy2(str(run_lib), str(shell.shell_cache_dir))
        if Hp.IS_WIN_MB and shell.build_opts.enable_address_sanitizer:
            shutil.copy2(
                str(
                    zzconsts.CLANG_BINARY.parents[1]
                    / "lib"
                    / "clang"
                    / zzconsts.CLANG_VER
                    / "lib"
                    / "windows"
                    / "clang_rt.asan_dynamic-x86_64.dll",
                ),
                str(shell.shell_cache_dir),
            )

        jspc_new_file_path = shell.js_objdir / "js" / "src" / "build" / "js.pc"
        with jspc_new_file_path.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("Version: "):  # Sample line: "Version: 47.0a2"
                    shell.version = line.split(": ")[1].rstrip()
    else:
        OCS_SM_HATCH_LOG.warning(
            "%s did not result in a js shell:", zzconsts.MAKE_BINARY_PATH
        )
        with (shell.shell_cache_dir / f"{shell.shell_name_without_ext}.busted").open(
            "a",
            encoding="utf-8",
            errors="replace",
        ) as f:
            repo_name = (
                shell.hg_repo_name
                if (shell.build_opts.repo_dir / ".hg" / "hgrc").is_file()
                else shell.git_repo_name
            )
            hash_ = (
                shell.hg_hash
                if (shell.build_opts.repo_dir / ".hg" / "hgrc").is_file()
                else shell.git_hash
            )
            f.write(
                f"Compilation of {repo_name} rev {hash_} "
                "failed with the following output:\n",
            )
            f.write(out)
        raise OSError(f"{zzconsts.MAKE_BINARY_PATH} did not result in a js shell.")

    return shell.shell_compiled_path


def obtain_shell(  # noqa: C901  # pylint: disable=too-complex
    shell: SMShell,
    update_to_rev: str | None = None,
    *,
    _update_latest_txt: bool = False,
) -> None:
    """Obtain a js shell. Keep the objdir for now, especially .a files, for symbols.

    :param shell: Potential compiled shell object
    :param update_to_rev: Specified revision to be updated to
    :raise RuntimeError: If MozillaBuild versions prior to 4.0 are used
    :raise FileNotFoundError: If lock dir is not a directory
    :raise OSError: When a cached failed-compile shell was found, or when compile failed
    :raise KeyboardInterrupt: When ctrl-c was pressed during shell compilation
    :raise CalledProcessError: When shell compilation failed
    """
    if zzconsts.IS_MOZILLABUILD_3_OR_OLDER:
        raise RuntimeError("MozillaBuild versions prior to 4.0 are not supported")

    lock_dir = get_lock_dir_path(Path.home(), shell.build_opts.repo_dir)
    if not lock_dir.is_dir():
        raise FileNotFoundError(f"{lock_dir} is not a directory")
    cached_no_shell = shell.shell_cache_js_bin_path.with_suffix(".busted")

    if shell.shell_cache_js_bin_path.is_file():
        OCS_SM_HATCH_LOG.info("Found cached shell...")
        # Assuming that since binary is present, others (e.g. symbols) are also present
        if Hp.IS_WIN_MB:
            misc_progs.verify_full_win_pageheap(shell.shell_cache_js_bin_path)
        return

    if cached_no_shell.is_file():
        raise OSError("Found a cached shell that failed compilation...")
    if shell.shell_cache_dir.is_dir():
        OCS_SM_HATCH_LOG.info("Found a cache dir without a successful/failed shell...")
        shutil.rmtree(shell.shell_cache_dir, onerror=handle_rm_readonly_files)

    shell.shell_cache_dir.mkdir()

    if update_to_rev:
        OCS_SM_HATCH_LOG.info(
            "Updating to rev %s in the %s repository...",
            update_to_rev,
            shell.build_opts.repo_dir,
        )
        subprocess.run(
            [
                zzconsts.HG_BINARY,
                "-R",
                str(shell.build_opts.repo_dir),
                "update",
                "-C",
                "-r",
                update_to_rev,
            ],
            check=True,
            cwd=Path.cwd(),
            stderr=subprocess.DEVNULL,
            timeout=9999,
        )

    try:
        configure_js_shell_compile(shell)
    except KeyboardInterrupt:
        shutil.rmtree(shell.shell_cache_dir, onerror=handle_rm_readonly_files)
        raise
    except (subprocess.CalledProcessError, OSError) as ex:
        shutil.rmtree(
            shell.shell_cache_dir / "objdir-js", onerror=handle_rm_readonly_files
        )
        if (
            shell.shell_cache_js_bin_path.is_file()
        ):  # Switch to contextlib.suppress when we are fully on Python 3
            shell.shell_cache_js_bin_path.unlink()
        with cached_no_shell.open("a", encoding="utf-8", errors="replace") as f:
            f.write(f"\nCaught exception {ex!r} ({ex})\n")
            f.write("Backtrace:\n")
            f.write(f"{traceback.format_exc()}\n")
        OCS_SM_HATCH_LOG.exception(
            "Compilation failure details in: %s", cached_no_shell
        )
        raise

    if Hp.IS_WIN_MB:
        misc_progs.verify_full_win_pageheap(shell.shell_cache_js_bin_path)


def arch_of_binary(binary: Path) -> str:
    """Test if a binary is 32-bit or 64-bit.

    :param binary: Path to compiled binary
    :raise ValueError: If a Windows binary was not compiled in Windows
    :raise ValueError: If a 64-bit binary was compiled though 32-bit was desired
    :raise ValueError: If a 32-bit binary was compiled though 64-bit was desired
    :return: Platform architecture of compiled binary
    """
    # We can possibly use the python-magic-bin PyPI library in the future
    unsplit_file_type = subprocess.run(
        [zzconsts.FILE_BINARY, str(binary)],
        check=True,
        cwd=Path.cwd(),
        stdout=subprocess.PIPE,
        timeout=99,
    ).stdout.decode("utf-8", errors="replace")
    filetype = unsplit_file_type.split(":", 1)[1]
    if Hp.IS_WIN_MB:
        if "MS Windows" not in filetype:
            raise ValueError(
                "A Windows binary was not compiled in Windows, "
                f"but rather the following type: {filetype}",
            )
        return (
            "32"
            if ("Intel 80386 32-bit" in filetype or "PE32 executable" in filetype)
            else "64"
        )
    if "32-bit" in filetype or "i386" in filetype:
        if "64-bit" in filetype:
            raise ValueError(f"We should not have a 64-bit binary filetype: {filetype}")
        return "32"
    if "64-bit" in filetype:
        if "32-bit" in filetype:
            raise ValueError(f"We should not have a 32-bit binary filetype: {filetype}")
        return "64"
    return "INVALID"


def test_binary(
    shell_path: Path,
    args: list[str],
    *,
    use_vg: bool = False,
    stderr: int | IO[bytes] | None = subprocess.STDOUT,
) -> tuple[str, int]:
    """Test the given shell with the given args.

    :param shell_path: Path to the compiled shell binary
    :param args: Arguments used to compile the shell
    :param use_vg: Whether Valgrind should be used
    :param stderr: stderr and where it should be redirected if needed
    :return: Tuple comprising the stdout of the run command and its return code
    """
    if use_vg:
        OCS_SM_HATCH_LOG.info("Using Valgrind to test...")
    test_cmd = [str(shell_path), *args]
    OCS_SM_HATCH_LOG.debug("The testing command is: %s", shlex.join(test_cmd))

    test_env = env_with_path(str(shell_path.parent))
    asan_options = f"exitcode={zzconsts.ASAN_ERROR_EXIT_CODE}"
    # Turn on LSan, Linux-only.
    # macOS non-support:
    # https://github.com/google/sanitizers/issues/1026
    # Windows non-support:
    # https://firefox-source-docs.mozilla.org/tools/sanitizer/asan.html
    #   (search for LSan)
    # Termux Android aarch64 is not yet supported due to possible ptrace issues
    if (
        Hp.IS_LINUX
        and not ("-asan-" in str(shell_path) and "-armsim64-" in str(shell_path))
        and "-aarch64-" not in str(shell_path)
    ):
        asan_options = f"detect_leaks=1,{asan_options}"
        test_env.update({"LSAN_OPTIONS": "max_leaks=1,"})
    test_env.update({"ASAN_OPTIONS": asan_options})

    test_cmd_result = subprocess.run(
        test_cmd,
        check=False,
        cwd=Path.cwd(),
        env=test_env,
        stderr=stderr,
        stdout=subprocess.PIPE,
        timeout=999,
    )
    out, return_code = (
        test_cmd_result.stdout.decode("utf-8", errors="replace"),
        test_cmd_result.returncode,
    )
    OCS_SM_HATCH_LOG.debug("The exit code is: %s", return_code)
    return out, return_code


def query_build_cfg(shell_path: Path, parameter: str) -> bool:
    """Test if a binary is compiled w/specified parameters, in getBuildConfiguration().

    :param shell_path: Path of the shell
    :param parameter: Parameter that will be tested
    :return: Whether the parameter is supported by the shell
    """
    return bool(
        json.loads(
            test_binary(
                shell_path,
                ["-e", f'print(getBuildConfiguration()["{parameter}"])'],
                use_vg=False,
                stderr=subprocess.DEVNULL,
            )[0]
            .split()[-1]
            .lower(),
        )
    )


def verify_binary(shell: SMShell) -> None:
    """Verify that the binary is compiled as intended.

    :param shell: Compiled binary object
    :raise ValueError: When compiled binary architecture differs from intended input
    :raise ValueError: When debug status of binary differs from intended input
    :raise ValueError: When asan status of binary differs from intended input
    :raise ValueError: When profiling status of binary differs from intended input
    :raise ValueError: When ARM32 simulator status of binary differs from intended input
    :raise ValueError: When ARM64 simulator status of binary differs from intended input
    """
    binary = shell.shell_cache_js_bin_path

    if arch_of_binary(binary) != ("32" if shell.build_opts.enable_32bit else "64"):
        raise ValueError(
            f"{arch_of_binary(binary)} architecture of binary is different "
            f"from the intended input: {shell.build_opts.enable_32bit}",
        )

    # Testing for debug / opt builds are different, as there are hybrid debug-opt builds
    if query_build_cfg(binary, "debug") != shell.build_opts.enable_debug:
        raise ValueError(
            f'Debug status of shell is: {query_build_cfg(binary, "debug")}, '
            f"compared to intended input: {shell.build_opts.enable_debug}",
        )

    if query_build_cfg(binary, "asan") != shell.build_opts.enable_address_sanitizer:
        raise ValueError(
            f'Asan status of shell is: {query_build_cfg(binary, "asan")}, '
            f"compared to intended input: {shell.build_opts.enable_address_sanitizer}",
        )
    # Checking for profiling status does not work with mozilla-beta and mozilla-release
    if query_build_cfg(binary, "profiling") == shell.build_opts.disable_profiling:
        raise ValueError(
            f'Profiling status of shell is: {query_build_cfg(binary, "profiling")}, '
            f"compared to intended input: {not shell.build_opts.disable_profiling}",
        )
    if not Hp.IS_WIN_MB_AARCH64:
        if (
            query_build_cfg(binary, "arm-simulator") and shell.build_opts.enable_32bit
        ) != shell.build_opts.enable_simulator_arm32:
            raise ValueError(
                "ARM32 simulator status of shell is: "
                f'{query_build_cfg(binary, "arm-simulator")}, '
                f"compared to intended: {shell.build_opts.enable_simulator_arm32}",
            )
        if (
            query_build_cfg(binary, "arm64-simulator")
            and not shell.build_opts.enable_32bit
        ) != shell.build_opts.enable_simulator_arm64:
            raise ValueError(
                "ARM64 simulator status of shell is: "
                f'{query_build_cfg(binary, "arm64-simulator")}, '
                f"compared to intended 32-bit status: {shell.build_opts.enable_32bit}",
                f"and intended ARM64 status: {shell.build_opts.enable_simulator_arm64}",
            )
