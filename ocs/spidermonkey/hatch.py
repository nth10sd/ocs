"""Common shell object code."""

from __future__ import annotations

import json
from logging import INFO as INFO_LOG_LEVEL
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
import traceback
from typing import IO

import distro
from packaging.version import parse
from zzbase.js_shells.spidermonkey import build_options
from zzbase.js_shells.spidermonkey.hatch import SMShell
from zzbase.js_shells.spidermonkey.hatch import SMShellError
from zzbase.util import constants as zzconsts
from zzbase.util.constants import FILE_BINARY
from zzbase.util.constants import HG_BINARY
from zzbase.util.constants import HostPlatform as Hp
from zzbase.util.fs_helpers import bash_piping as piping
from zzbase.util.fs_helpers import env_with_path
from zzbase.util.fs_helpers import get_lock_dir_path
from zzbase.util.fs_helpers import handle_rm_readonly_files
from zzbase.util.logging import get_logger
from zzbase.util.utils import LockDir
from zzbase.util.utils import autoconf_run

from ocs.spidermonkey.parsing import parse_args
from ocs.util import constants
from ocs.util import hg_helpers
from ocs.util import misc_progs

SM_HATCH_LOG = get_logger(
    __name__, fmt="%(asctime)s %(levelname)-8s [%(funcName)s] %(message)s"
)
SM_HATCH_LOG.setLevel(INFO_LOG_LEVEL)


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
            SM_HATCH_LOG.exception("The run function encountered an error")
            raise

    @staticmethod
    def run(argv: list[str]) -> int:
        """Build a shell and place it in the autobisectjs cache.

        :param argv: Additional parameters
        :return: 0, to denote a successful compile
        """
        options = parse_args(argv)
        options.build_opts = build_options.parse_shell_opts(
            options.build_opts.split() if options.build_opts else []
        )

        with LockDir(
            get_lock_dir_path(Path.home(), options.build_opts.repo_dir),
        ):
            if options.revision:
                shell = OldSMShell(options.build_opts, hg_hash=options.revision)
            else:
                local_orig_hg_hash = hg_helpers.get_repo_hash_and_id(
                    options.build_opts.repo_dir,
                )[0]
                shell = OldSMShell(options.build_opts, hg_hash=local_orig_hg_hash)

            obtain_shell(shell, update_to_rev=options.revision)

            shell_cache_abs_dir = shell.shell_cache_js_bin_path.parents[-3]
            SM_HATCH_LOG.info(  # Output with "~" instead of the full absolute dir
                "Desired shell is at:\n\n~/%s",
                shell.shell_cache_js_bin_path.relative_to(shell_cache_abs_dir),
            )

        return 0


def configure_js_shell_compile(shell: OldSMShell) -> None:
    """Configure, compile and copy a js shell according to required parameters.

    :param shell: Potential compiled shell object
    """
    SM_HATCH_LOG.info("Compiling...")
    js_objdir_path = shell.shell_cache_dir / "objdir-js"
    js_objdir_path.mkdir()
    shell.js_objdir = js_objdir_path

    # Run autoconf 2.13 only on non-Windows platforms if repository revision is before:
    #   m-c rev 633690:c5dc125ea32ba3e9a7c3fe3cf5be05abd17013a3, Fx106
    # See bug 1787977. m-c rev has been bumped to account for known broken ranges
    if not Hp.IS_WIN_MB and hg_helpers.exists_and_is_ancestor(
        shell.build_opts.repo_dir,
        shell.hg_hash,
        "parents(c5dc125ea32ba3e9a7c3fe3cf5be05abd17013a3)",
    ):
        autoconf_run(shell.build_opts.repo_dir / "js" / "src")

    configure_binary(shell)
    sm_compile(shell)
    verify_binary(shell)

    compile_log = (
        shell.shell_cache_dir / f"{shell.shell_name_without_ext}.fuzzmanagerconf"
    )
    if not compile_log.is_file():
        env_dump(shell, compile_log)


def configure_binary(  # noqa: C901, PLR0912, PLR0915  # pylint: disable=too-complex
    shell: OldSMShell,
) -> None:
    """Configure a binary according to required parameters.

    :param shell: Potential compiled shell object
    :raise FileNotFoundError: If the default .mozbuild folder not found, especially
                              if `./mach bootstrap` was not run
    :raise FileNotFoundError: If clang.exe not found in default .mozbuild folder
    :raise FileNotFoundError: If llvm-config.exe not found in default .mozbuild folder
    :raise FileNotFoundError: If MOZ_CLANG_RT_ASAN_LIB_PATH env var file not found
    :raise FileNotFoundError: If libclang path is not a directory
    :raise FileNotFoundError: If js_objdir is not a directory
    :raise CalledProcessError: If the shell failed to compile
    """
    # pylint: disable=too-many-branches,too-many-statements
    cfg_cmds: list[str] = []
    cfg_env = dict(os.environ.copy())
    orig_cfg_env = dict(os.environ.copy())
    if Hp.IS_LINUX | Hp.IS_MAC:
        cfg_env["AR"] = "ar"
    if Hp.IS_LINUX and shell.build_opts.enable_32bit:
        # 32-bit shell on 32/64-bit x86 Linux
        cfg_env["PKG_CONFIG_PATH"] = "/usr/lib/x86_64-linux-gnu/pkgconfig"
        # apt-get `g++-multilib lib32z1-dev libc6-dev-i386` first,
        # ^^ if on 64-bit Linux. (no matter Clang or GCC)
        # Also run this: `rustup target add i686-unknown-linux-gnu`
        cfg_env["CC"] = f"clang {constants.SSE2_FLAGS}"
        cfg_env["CXX"] = f"clang++ {constants.SSE2_FLAGS}"
        cfg_cmds.extend(
            (
                "sh",
                str(shell.js_cfg_path.as_posix()),
                "--host=x86_64-pc-linux-gnu",
                "--target=i686-pc-linux",
            )
        )
        if shell.build_opts.enable_simulator_arm32:
            cfg_cmds.append("--enable-simulator=arm")
    # 64-bit shell on macOS 10.13 El Capitan and greater
    elif (  # pylint: disable=confusing-consecutive-elif
        Hp.IS_MAC
        and parse(platform.mac_ver()[0]) >= parse("10.13")
        and not shell.build_opts.enable_32bit
    ):
        # Remove entry pointing to the venv python on macOS to play nice w/SM configure
        orig_mac_path_env_var_full = os.getenv("PATH", "").split(":", maxsplit=1)
        if (Path(orig_mac_path_env_var_full[0]) / "python").is_file():
            # Only remove first entry of PATH if it is a venv, i.e. it contains a python
            cfg_env["PATH"] = orig_mac_path_env_var_full[1]
        # Add the AUTOCONF env variable if repository revision is before:
        #   m-c rev 633690:c5dc125ea32ba3e9a7c3fe3cf5be05abd17013a3, Fx106
        # See bug 1787977. m-c rev has been bumped to account for known broken ranges
        if shutil.which("brew") and hg_helpers.exists_and_is_ancestor(
            shell.build_opts.repo_dir,
            shell.hg_hash,
            "parents(c5dc125ea32ba3e9a7c3fe3cf5be05abd17013a3)",
        ):
            cfg_env["AUTOCONF"] = "/usr/local/Cellar/autoconf213/2.13/bin/autoconf213"
        cfg_cmds.extend(
            (
                "sh",
                str(shell.js_cfg_path.as_posix()),
            )
        )
        if shell.build_opts.enable_simulator_arm64:
            cfg_cmds.append("--enable-simulator=arm64")

    elif Hp.IS_WIN_MB:  # pylint: disable=confusing-consecutive-elif
        win_mozbuild_clang_bin_path = constants.WIN_MOZBUILD_CLANG_PATH / "bin"
        if not win_mozbuild_clang_bin_path.is_dir():
            raise FileNotFoundError('Please first run "./mach bootstrap".')
        if not (win_mozbuild_clang_bin_path / "clang.exe").is_file():
            raise FileNotFoundError(
                f"clang.exe not found at: {win_mozbuild_clang_bin_path}",
            )
        if not (win_mozbuild_clang_bin_path / "llvm-config.exe").is_file():
            raise FileNotFoundError(
                f"llvm-config.exe not found at: {win_mozbuild_clang_bin_path}",
            )
        if shell.build_opts.enable_address_sanitizer:
            cfg_env["LIBS"] = (
                "clang_rt.asan_dynamic-x86_64.lib "
                "clang_rt.asan_dynamic_runtime_thunk-x86_64.lib"
            )
            clang_lib_path = (
                constants.WIN_MOZBUILD_CLANG_PATH
                / "lib"
                / "clang"
                / constants.CLANG_VER
                / "lib"
                / "windows"
            )
            cfg_env["CLANG_LIB_DIR"] = clang_lib_path.as_posix()
            cfg_env["MOZ_CLANG_RT_ASAN_LIB_PATH"] = (
                clang_lib_path / "clang_rt.asan_dynamic-x86_64.dll"
            ).as_posix()
            if not Path(cfg_env["MOZ_CLANG_RT_ASAN_LIB_PATH"]).is_file():
                raise FileNotFoundError(
                    f'{cfg_env["MOZ_CLANG_RT_ASAN_LIB_PATH"]} is not a file',
                )
            cfg_env["LIB"] = cfg_env.get("LIB", "") + cfg_env["CLANG_LIB_DIR"]
        cfg_cmds.extend(
            (
                "sh",
                str(shell.js_cfg_path.as_posix()),
            )
        )
        # Cross-compile ARM64 binary using x86_64 Python and toolchain on ARM64 host
        if Hp.IS_WIN_MB_AARCH64:
            cfg_cmds.append("--target=aarch64")
        elif shell.build_opts.enable_32bit:
            cfg_cmds.extend(
                (
                    "--host=x86_64-pc-mingw32",
                    "--target=i686-pc-mingw32",
                )
            )
            if shell.build_opts.enable_simulator_arm32:
                cfg_cmds.append("--enable-simulator=arm")
        else:
            cfg_cmds.extend(
                (
                    "--host=x86_64-pc-mingw32",
                    "--target=x86_64-pc-mingw32",
                )
            )
            if shell.build_opts.enable_simulator_arm64:
                cfg_cmds.append("--enable-simulator=arm64")
    else:
        cfg_cmds.extend(
            (
                "sh",
                str(shell.js_cfg_path.as_posix()),
            )
        )
        if shell.build_opts.enable_simulator_arm64:
            cfg_cmds.append("--enable-simulator=arm64")

    if shell.build_opts.enable_debug:
        cfg_cmds.append("--enable-debug")
    elif shell.build_opts.disable_debug:
        cfg_cmds.append("--disable-debug")

    if shell.build_opts.enable_optimize:
        cfg_cmds.append(
            f"--enable-optimize{'=-O1' if shell.build_opts.enable_valgrind else ''}",
        )
    elif shell.build_opts.disable_optimize:
        cfg_cmds.append("--disable-optimize")
    if shell.build_opts.disable_profiling:
        cfg_cmds.append("--disable-profiling")

    if shell.build_opts.enable_oom_breakpoint:  # Extra OOM assertion debugging help
        cfg_cmds.append("--enable-oom-breakpoint")
    if shell.build_opts.without_intl_api:  # Speeds up compilation but is non-default
        cfg_cmds.append("--without-intl-api")

    if shell.build_opts.enable_address_sanitizer:
        cfg_cmds.extend(
            ("--enable-address-sanitizer", "--enable-fuzzing", "--disable-jemalloc")
        )
        if Hp.IS_LINUX:
            cfg_cmds.extend(
                (
                    "--disable-stdcxx-compat",
                    # macOS & Win ASan builds fail to compile using --without-sysroot
                    "--without-sysroot",  # Else ASan builds have corrupt stack
                )
            )
    if shell.build_opts.enable_valgrind:
        cfg_cmds.extend(
            (
                "--enable-valgrind",
                "--disable-jemalloc",
            )
        )

    # We add the following flags by default.
    if Hp.IS_LINUX | Hp.IS_MAC:
        cfg_cmds.append("--with-ccache")
    # Building with NSPR is standard on upstream. However, local 32-bit builds need NSPR
    # binaries which are available, but then the LD_LIBRARY_PATH variable needs to be
    # set, so this is probably not worth the effort. Also, ctypes has 32-bit issues.
    # NSPR (and ctypes, which seems to need NSPR) does not seem to support aarch64 Linux
    if not (Hp.IS_LINUX_AARCH64 or shell.build_opts.enable_32bit):
        cfg_cmds.extend(
            (
                "--enable-nspr-build",
                "--enable-ctypes",
            )
        )
    cfg_cmds.extend(
        (
            # gets debug symbols on opt shells
            "--enable-debug-symbols",
            "--enable-gczeal",
            # Look at js/src/devtools/automation/variants/fuzzing as of 2022-10-09:
            # m-c rev c4bdea458a08b975ffd70faed4a2f6fbe1e563bc
            "--enable-rust-simd",
            "--disable-tests",
        )
    )

    if Hp.IS_LINUX and distro.id() == "gentoo":
        path_to_libclang = Path(
            "/usr/lib/llvm/"
            f'{piping(["clang", "--version"], ["cut", "-d", "/", "-f5"]).split()[-1]}'
            "/lib64"
        )
        if not path_to_libclang.is_dir():
            raise FileNotFoundError(f"{path_to_libclang} is not a directory")
        cfg_cmds.append(f"--with-libclang-path={path_to_libclang.as_posix()}")

    # Dump whatever we added to the environment
    env_vars: list[str] = []
    for env_var in set(cfg_env.keys()) - set(orig_cfg_env.keys()):
        str_to_be_appended = (
            f'{env_var}="{cfg_env[env_var]}"'
            if " " in cfg_env[env_var]
            else f"{env_var}={cfg_env[env_var]}"
        )
        env_vars.append(str_to_be_appended)

    SM_HATCH_LOG.debug(
        "Command to be run is: %s %s",
        shlex.join(env_vars),
        shlex.join(cfg_cmds),
    )

    if not shell.js_objdir.is_dir():
        raise FileNotFoundError(f"{shell.js_objdir} is not a directory")

    try:
        subprocess.run(
            cfg_cmds,
            check=True,
            cwd=shell.js_objdir,
            env=cfg_env,
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as ex:
        with (shell.shell_cache_dir / f"{shell.shell_name_without_ext}.busted").open(
            "a",
            encoding="utf-8",
            errors="replace",
        ) as f:
            f.write(
                f"Configuration of {shell.hg_repo_name} rev {shell.hg_hash} "
                "failed with the following output:\n",
            )
            f.write(ex.stdout.decode("utf-8", errors="replace"))
        raise

    shell.env_added = env_vars
    shell.env_full = cfg_env
    shell.cfg_cmd_excl_env = cfg_cmds


def env_dump(shell: OldSMShell, log_: Path) -> None:
    """Dump environment to a .fuzzmanagerconf file.

    :param shell: A compiled shell
    :param log_: Log file location
    """
    # Platform and OS detection for the spec, part of which is in:
    #   https://wiki.mozilla.org/Security/CrashSignatures
    if shell.build_opts.enable_32bit:
        fmconf_platform = "x86"  # 32-bit Intel-only, we do not support 32-bit ARM hosts
    elif Hp.IS_WIN_MB_AARCH64:
        fmconf_platform = "aarch64"
    elif Hp.IS_WIN_MB_X86_64:
        fmconf_platform = "x86_64"
    else:
        fmconf_platform = platform.machine()

    fmconf_os = ""
    if Hp.IS_LINUX:
        fmconf_os = "linux"
    elif Hp.IS_MAC:
        fmconf_os = "macosx"
    elif Hp.IS_WIN_MB:
        fmconf_os = "windows"

    with log_.open("a", encoding="utf-8", errors="replace") as f:
        f.write("# Information about shell:\n# \n")

        f.write("# Create another shell in shell-cache like this one:\n")
        f.write(
            "# python3 -u -m ocs "
            f'-b="{shell.build_opts.build_options_str}" -r {shell.hg_hash}\n# \n',
        )

        f.write("# Full environment is:\n")
        f.write(f"# {shell.env_full}\n# \n")

        f.write("# Full configuration command with needed environment variables is:\n")
        f.write(
            f"# {shlex.join(shell.env_added)} "
            f"{shlex.join(shell.cfg_cmd_excl_env)}\n# \n",
        )

        # .fuzzmanagerconf details
        f.write("\n")
        f.write("[Main]\n")
        f.write(f"platform = {fmconf_platform}\n")
        f.write(f"product = {shell.hg_repo_name}\n")
        f.write(f"product_version = {shell.hg_hash}\n")
        f.write(f"os = {fmconf_os}\n")

        f.write("\n")
        f.write("[Metadata]\n")
        f.write(f"buildFlags = {shell.build_opts.build_options_str}\n")
        f.write(f'majorVersion = {shell.version.split(".")[0]}\n')
        f.write(f"pathPrefix = {shell.build_opts.repo_dir}/\n")
        f.write(f"version = {shell.version}\n")


def sm_compile(shell: OldSMShell) -> Path:
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
            SM_HATCH_LOG.info(
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
            SM_HATCH_LOG.info(
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
                    constants.WIN_MOZBUILD_CLANG_PATH
                    / "lib"
                    / "clang"
                    / constants.CLANG_VER
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
        SM_HATCH_LOG.warning(
            "%s did not result in a js shell:", zzconsts.MAKE_BINARY_PATH
        )
        with (shell.shell_cache_dir / f"{shell.shell_name_without_ext}.busted").open(
            "a",
            encoding="utf-8",
            errors="replace",
        ) as f:
            f.write(
                f"Compilation of {shell.hg_repo_name} rev {shell.hg_hash} "
                "failed with the following output:\n",
            )
            f.write(out)
        raise OSError(f"{zzconsts.MAKE_BINARY_PATH} did not result in a js shell.")

    return shell.shell_compiled_path


def obtain_shell(  # noqa: C901  # pylint: disable=too-complex
    shell: OldSMShell,
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
        SM_HATCH_LOG.info("Found cached shell...")
        # Assuming that since binary is present, others (e.g. symbols) are also present
        if Hp.IS_WIN_MB:
            misc_progs.verify_full_win_pageheap(shell.shell_cache_js_bin_path)
        return

    if cached_no_shell.is_file():
        raise OSError("Found a cached shell that failed compilation...")
    if shell.shell_cache_dir.is_dir():
        SM_HATCH_LOG.info("Found a cache dir without a successful/failed shell...")
        shutil.rmtree(shell.shell_cache_dir, onerror=handle_rm_readonly_files)

    shell.shell_cache_dir.mkdir()

    if update_to_rev:
        SM_HATCH_LOG.info(
            "Updating to rev %s in the %s repository...",
            update_to_rev,
            shell.build_opts.repo_dir,
        )
        subprocess.run(
            [
                HG_BINARY,
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
        SM_HATCH_LOG.exception("Compilation failure details in: %s", cached_no_shell)
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
        [FILE_BINARY, str(binary)],
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
        SM_HATCH_LOG.info("Using Valgrind to test...")
    test_cmd = [str(shell_path), *args]
    SM_HATCH_LOG.debug("The testing command is: %s", shlex.join(test_cmd))

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
    SM_HATCH_LOG.debug("The exit code is: %s", return_code)
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
            .rstrip()
            .lower(),
        )
    )


def verify_binary(shell: OldSMShell) -> None:
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
