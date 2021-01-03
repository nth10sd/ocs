# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Compiles SpiderMonkey shells on different platforms using various specified configuration parameters."""

from __future__ import annotations

import copy
import multiprocessing
from optparse import OptionParser  # pylint: disable=deprecated-module
import os
from pathlib import Path
import platform
from shlex import quote
import shutil
import subprocess
import sys
import traceback
from typing import Any
from typing import List
from typing import Optional

import distro
from pkg_resources import parse_version

from ocs import build_options
from ocs import inspect_shell
from ocs.util import fs_helpers
from ocs.util import hg_helpers
from ocs.util import misc_progs
from ocs.util import utils

if platform.system() == "Windows":
    MAKE_BINARY = "mozmake"
    CLANG_VER = "11.0.0"
    WIN_MOZBUILD_CLANG_PATH = Path.home() / ".mozbuild" / "clang"
else:
    MAKE_BINARY = "make"
    SSE2_FLAGS = "-msse2 -mfpmath=sse"  # See bug 948321

if multiprocessing.cpu_count() > 2:
    COMPILATION_JOBS = multiprocessing.cpu_count() + 1
else:
    COMPILATION_JOBS = 3  # Other single/dual core computers


class CompiledShellError(Exception):
    """Error class unique to CompiledShell objects."""


class CompiledShell:  # pylint: disable=too-many-instance-attributes,too-many-public-methods
    """A CompiledShell object represents an actual compiled shell binary.

    :param build_opts: Object containing the build options defined in build_options.py
    :param hg_hash: Changeset hash
    """

    def __init__(self, build_opts: Any, hg_hash: str):
        self._name_no_ext = build_options.compute_shell_name(build_opts, hg_hash)
        self._hg_hash = hg_hash
        self.build_opts = build_opts

        self._js_objdir = Path()

        self._cfg_cmd_excl_env: List[str] = []
        self._added_env = ""
        self._full_env = ""

        self._js_version = ""

    @classmethod
    def main(cls: Any, args: Any = None) -> Any:
        """Main function of CompiledShell class.

        :param args: Additional parameters
        :return: 0, to denote a successful compile and 1, to denote a failed compile
        """
        # logging.basicConfig(format="%(message)s", level=logging.INFO)
        try:
            return cls.run(args)
        except CompiledShellError as ex:
            print(repr(ex))
            # log.error(ex)
            return 1

    @staticmethod
    def run(argv: Any = None) -> Any:
        """Build a shell and place it in the autobisectjs cache.

        :param argv: Additional parameters
        :return: 0, to denote a successful compile
        """
        usage = "Usage: %prog [options]"
        parser = OptionParser(usage)
        parser.disable_interspersed_args()

        parser.set_defaults(
            build_opts="",
        )

        # Specify how the shell will be built.
        parser.add_option("-b", "--build",
                          dest="build_opts",
                          help='Specify build options, e.g. -b "--disable-debug --enable-optimize" '
                               "(python3 -m ocs.build_options --help)")

        parser.add_option("-r", "--rev",
                          dest="revision",
                          help="Specify revision to build")

        options = parser.parse_args(argv)[0]
        options.build_opts = build_options.parse_shell_opts(options.build_opts)

        with utils.LockDir(fs_helpers.get_lock_dir_path(Path.home(), options.build_opts.repo_dir)):
            if options.revision:
                shell = CompiledShell(options.build_opts, options.revision)
            else:
                local_orig_hg_hash = hg_helpers.get_repo_hash_and_id(options.build_opts.repo_dir)[0]
                shell = CompiledShell(options.build_opts, local_orig_hg_hash)

            obtain_shell(shell, update_to_rev=options.revision)
            print(shell.shell_cache_js_bin_path)

        return 0

    @property
    def cfg_cmd_excl_env(self) -> List[str]:
        """Retrieve the configure command excluding the enviroment variables.

        :return: Configure command
        """
        return self._cfg_cmd_excl_env

    @cfg_cmd_excl_env.setter
    def cfg_cmd_excl_env(self, cfg: List[str]) -> None:
        """Sets the configure command excluding the enviroment variables.

        :param cfg: Configure command
        """
        self._cfg_cmd_excl_env = cfg

    @property
    def env_added(self) -> Any:
        """Retrieve environment variables that were added.

        :return: Added environment variables
        """
        return self._added_env

    @env_added.setter
    def env_added(self, added_env: Any) -> None:
        """Set environment variables that were added.

        :param added_env: Added environment variables
        """
        self._added_env = added_env

    @property
    def env_full(self) -> Any:
        """Retrieve the full environment including the newly added variables.

        :return: Full environment
        """
        return self._full_env

    @env_full.setter
    def env_full(self, full_env: Any) -> None:
        """Set the full environment including the newly added variables.

        :param full_env: Full environment
        """
        self._full_env = full_env

    @property
    def hg_hash(self) -> str:
        """Retrieve the hash of the current changeset of the repository.

        :return: Changeset hash
        """
        return self._hg_hash

    @property
    def js_cfg_path(self) -> Any:
        """Retrieve the configure file in a js/src directory.

        :return: Full path to the configure file
        """
        return self.build_opts.repo_dir / "js" / "src" / "configure"

    @property
    def js_objdir(self) -> Path:
        """Retrieve the objdir of the js shell to be compiled.

        :return: Full path to the js shell objdir
        """
        return self._js_objdir

    @js_objdir.setter
    def js_objdir(self, objdir: Path) -> None:
        """Set the objdir of the js shell to be compiled.

        :param objdir: Full path to the objdir of the js shell to be compiled
        """
        self._js_objdir = objdir

    @property
    def repo_name(self) -> str:
        """Retrieve the name of a Mercurial repository.

        :return: Name of the repository
        """
        return hg_helpers.hgrc_repo_name(self.build_opts.repo_dir)

    @property
    def shell_cache_dir(self) -> Path:
        """Retrieve the shell cache directory of the intended js binary.

        :return: Full path to the shell cache directory of the intended js binary
        """
        return fs_helpers.ensure_cache_dir(Path.home()) / self._name_no_ext

    @property
    def shell_cache_js_bin_path(self) -> Path:
        """Retrieve the full path to the js binary located in the shell cache.

        :return: Full path to the js binary in the shell cache
        """
        return (fs_helpers.ensure_cache_dir(Path.home()) /
                self._name_no_ext / self.shell_name_with_ext)

    @property
    def shell_compiled_path(self) -> Path:
        """Retrieve the full path to the original location of js binary compiled in the shell cache.

        :return: Full path to the original location of js binary compiled in the shell cache
        """
        full_path = self._js_objdir / "dist" / "bin" / "js"
        return full_path.with_suffix(".exe") if platform.system() == "Windows" else full_path

    @property
    def shell_compiled_runlibs_path(self) -> List[Path]:
        """Retrieve the full path to the original location of the libraries of js binary compiled in the shell cache.

        :return: Full path to the original location of the libraries of js binary compiled in the shell cache
        """
        return [
            self._js_objdir / "dist" / "bin" / runlib for runlib in inspect_shell.ALL_RUN_LIBS
        ]

    @property
    def shell_name_with_ext(self) -> str:
        """Retrieve the name of the compiled js shell with the file extension.

        :return: Name of the compiled js shell with the file extension
        """
        return (f"{self._name_no_ext}.exe" if platform.system() == "Windows"
                else f"{self._name_no_ext}")

    @property
    def shell_name_without_ext(self) -> str:
        """Retrieve the name of the compiled js shell without the file extension.

        :return: Name of the compiled js shell without the file extension
        """
        return self._name_no_ext

    @property
    def version(self) -> str:
        """Retrieve the version number of the js shell as extracted from js.pc

        :return: Version number of the js shell
        """
        return self._js_version

    @version.setter
    def version(self, js_version: str) -> None:
        """Set the version number of the js shell as extracted from js.pc

        :param js_version: Version number of the js shell
        """
        self._js_version = js_version


def configure_js_shell_compile(shell: Any) -> None:
    """Configures, compiles and copies a js shell according to required parameters.

    :param shell: Potential compiled shell object
    """
    print("Compiling...")  # Print *with* a trailing newline to avoid breaking other stuff
    js_objdir_path = shell.shell_cache_dir / "objdir-js"
    js_objdir_path.mkdir()
    shell.js_objdir = js_objdir_path

    misc_progs.autoconf_run(shell.build_opts.repo_dir / "js" / "src")
    configure_binary(shell)
    sm_compile(shell)
    inspect_shell.verify_binary(shell)

    compile_log = shell.shell_cache_dir / f"{shell.shell_name_without_ext}.fuzzmanagerconf"
    if not compile_log.is_file():
        env_dump(shell, compile_log)


def configure_binary(shell: Any) -> None:  # pylint: disable=too-complex,too-many-branches,too-many-statements
    """Configure a binary according to required parameters.

    :param shell: Potential compiled shell object
    :raise CalledProcessError: Raise if the shell failed to compile
    """
    cfg_cmds = []
    cfg_env = copy.deepcopy(os.environ)
    orig_cfg_env = copy.deepcopy(os.environ)
    if platform.system() != "Windows":
        cfg_env["AR"] = "ar"
    if shell.build_opts.enable32 and platform.system() == "Linux":
        # 32-bit shell on 32/64-bit x86 Linux
        cfg_env["PKG_CONFIG_PATH"] = "/usr/lib/x86_64-linux-gnu/pkgconfig"
        # apt-get `g++-multilib lib32z1-dev libc6-dev-i386` first, if on 64-bit Linux. (no matter Clang or GCC)
        # Also run this: `rustup target add i686-unknown-linux-gnu`
        cfg_env["CC"] = f"clang {constants.SSE2_FLAGS}"
        cfg_env["CXX"] = f"clang++ {constants.SSE2_FLAGS}"
        cfg_cmds.append("sh")
        cfg_cmds.append(str(shell.js_cfg_path))
        cfg_cmds.append("--host=x86_64-pc-linux-gnu")
        cfg_cmds.append("--target=i686-pc-linux")
        if shell.build_opts.enableSimulatorArm32:
            cfg_cmds.append("--enable-simulator=arm")
    # 64-bit shell on Mac OS X 10.13 El Capitan and greater
    elif parse_version(platform.mac_ver()[0]) >= parse_version("10.13") and not shell.build_opts.enable32:
        if shutil.which("brew"):
            cfg_env["AUTOCONF"] = "/usr/local/Cellar/autoconf213/2.13/bin/autoconf213"
        cfg_cmds.append("sh")
        cfg_cmds.append(str(shell.js_cfg_path))
        cfg_cmds.append("--target=x86_64-apple-darwin17.7.0")  # macOS 10.13.6
        if shell.build_opts.enableSimulatorArm64:
            cfg_cmds.append("--enable-simulator=arm64")

    elif platform.system() == "Windows":
        win_mozbuild_clang_bin_path = WIN_MOZBUILD_CLANG_PATH / "bin"
        assert win_mozbuild_clang_bin_path.is_dir(), 'Please first run "./mach bootstrap".'
        assert (win_mozbuild_clang_bin_path / "clang.exe").is_file()
        assert (win_mozbuild_clang_bin_path / "llvm-config.exe").is_file()
        cfg_env["LIBCLANG_PATH"] = str(win_mozbuild_clang_bin_path)
        cfg_env["MAKE"] = "mozmake"  # Workaround for bug 948534
        if shell.build_opts.enableAddressSanitizer:
            cfg_env["LDFLAGS"] = ("clang_rt.asan_dynamic-x86_64.lib "
                                  "clang_rt.asan_dynamic_runtime_thunk-x86_64.lib")
            cfg_env["CLANG_LIB_DIR"] = str(WIN_MOZBUILD_CLANG_PATH / "lib" / "clang" / CLANG_VER / "lib" / "windows")
            # Not sure if the following line works. One seems to need to first copy a .dll to ~/.mozbuild/clang/bin
            #   cp ~/.mozbuild/clang/lib/clang/*/lib/windows/clang_rt.asan_dynamic-x86_64.dll ~/.mozbuild/clang/bin/
            cfg_env["MOZ_CLANG_RT_ASAN_LIB_PATH"] = f'{cfg_env["CLANG_LIB_DIR"]}/clang_rt.asan_dynamic-x86_64.dll'
            assert Path(cfg_env["MOZ_CLANG_RT_ASAN_LIB_PATH"]).is_file()
            cfg_env["LIB"] = cfg_env.get("LIB", "") + cfg_env["CLANG_LIB_DIR"]
        cfg_cmds.append("sh")
        cfg_cmds.append(str(shell.js_cfg_path))
        if shell.build_opts.enable32:
            cfg_cmds.append("--host=x86_64-pc-mingw32")
            cfg_cmds.append("--target=i686-pc-mingw32")
            if shell.build_opts.enableSimulatorArm32:
                cfg_cmds.append("--enable-simulator=arm")
        else:
            cfg_cmds.append("--host=x86_64-pc-mingw32")
            cfg_cmds.append("--target=x86_64-pc-mingw32")
            if shell.build_opts.enableSimulatorArm64:
                cfg_cmds.append("--enable-simulator=arm64")
    else:
        cfg_cmds.append("sh")
        cfg_cmds.append(str(shell.js_cfg_path))
        if shell.build_opts.enableSimulatorArm64:
            cfg_cmds.append("--enable-simulator=arm64")

    if shell.build_opts.enableDbg:
        cfg_cmds.append("--enable-debug")
    elif shell.build_opts.disableDbg:
        cfg_cmds.append("--disable-debug")

    if shell.build_opts.enableOpt:
        cfg_cmds.append("--enable-optimize" + ("=-O1" if shell.build_opts.enableValgrind else ""))
    elif shell.build_opts.disableOpt:
        cfg_cmds.append("--disable-optimize")
    if shell.build_opts.disableProfiling:
        cfg_cmds.append("--disable-profiling")

    if shell.build_opts.enableOomBreakpoint:  # Extra debugging help for OOM assertions
        cfg_cmds.append("--enable-oom-breakpoint")
    if shell.build_opts.enableWithoutIntlApi:  # Speeds up compilation but is non-default
        cfg_cmds.append("--without-intl-api")

    if shell.build_opts.enableAddressSanitizer:
        cfg_cmds.append("--enable-address-sanitizer")
        cfg_cmds.append("--disable-jemalloc")
    if shell.build_opts.enableValgrind:
        cfg_cmds.append("--enable-valgrind")
        cfg_cmds.append("--disable-jemalloc")

    # We add the following flags by default.
    if os.name == "posix":
        cfg_cmds.append("--with-ccache")
    cfg_cmds.append("--enable-gczeal")
    cfg_cmds.append("--enable-debug-symbols")  # gets debug symbols on opt shells
    cfg_cmds.append("--disable-tests")

    if platform.system() == "Linux" and distro.linux_distribution(full_distribution_name=False)[0] == "gentoo":
        path_to_libclang = "/usr/lib/llvm/11/lib64"
        assert Path(path_to_libclang).is_dir()
        cfg_cmds.append(f"--with-libclang-path={path_to_libclang}")

    if platform.system() == "Windows":
        # FIXME: Replace this with shlex's quote  # pylint: disable=fixme
        counter = 0
        for entry in cfg_cmds:
            if os.sep in entry:
                cfg_cmds[counter] = cfg_cmds[counter].replace(os.sep, "//")
            counter = counter + 1

    # Print whatever we added to the environment
    env_vars = []
    for env_var in set(cfg_env.keys()) - set(orig_cfg_env.keys()):
        str_to_be_appended = (
            f"{env_var}"
            f'="{cfg_env[str(env_var)]}'
            + '"' if " " in cfg_env[str(env_var)] else env_var +
            f"={cfg_env[str(env_var)]}"
        )
        env_vars.append(str_to_be_appended)
    utils.vdump(f'Command to be run is: {" ".join(quote(str(x)) for x in env_vars)} '
                f'{" ".join(quote(str(x)) for x in cfg_cmds)}')

    assert shell.js_objdir.is_dir()

    try:
        if platform.system() == "Windows":
            changed_cfg_cmds = []
            for entry in cfg_cmds:
                # For JS, quoted from :glandium: "the way icu subconfigure is called is what changed.
                #   but really, the whole thing likes forward slashes way better"
                # See bug 1038590 comment 9.
                if "\\" in entry:
                    entry = entry.replace("\\", "/")
                changed_cfg_cmds.append(entry)
            subprocess.run(changed_cfg_cmds,
                           check=True,
                           cwd=shell.js_objdir,
                           env=cfg_env,
                           stderr=subprocess.STDOUT,
                           stdout=subprocess.PIPE).stdout.decode("utf-8", errors="replace")
        else:
            subprocess.run(cfg_cmds,
                           check=True,
                           cwd=shell.js_objdir,
                           env=cfg_env,
                           stderr=subprocess.STDOUT,
                           stdout=subprocess.PIPE).stdout.decode("utf-8", errors="replace")
    except subprocess.CalledProcessError as ex:
        with open(str(shell.shell_cache_dir / f"{shell.shell_name_without_ext}.busted"), "a",
                  encoding="utf-8", errors="replace") as f:
            f.write(f"Configuration of {shell.repo_name} rev {shell.hg_hash} "
                    f"failed with the following output:\n")
            f.write(ex.stdout.decode("utf-8", errors="replace"))
        raise

    shell.env_added = env_vars
    shell.env_full = cfg_env
    shell.cfg_cmd_excl_env = cfg_cmds


def env_dump(shell: CompiledShell, log_: Path) -> None:
    """Dump environment to a .fuzzmanagerconf file.

    :param shell: A compiled shell
    :param log_: Log file location
    """
    # Platform and OS detection for the spec, part of which is in:
    #   https://wiki.mozilla.org/Security/CrashSignatures
    if shell.build_opts.enable32:
        fmconf_platform = "x86"  # Fixate to 32-bit Intel because we do not support 32-bit ARM hosts for compilation
    elif platform.system() == "Windows":
        if platform.machine() == "ARM64":
            fmconf_platform = "aarch64"  # platform.machine() returns "ARM64" on Windows
        else:
            fmconf_platform = "x86_64"  # platform.machine() returns "AMD64" on Windows
    else:
        fmconf_platform = platform.machine()

    fmconf_os = None
    if platform.system() == "Linux":
        fmconf_os = "linux"
    elif platform.system() == "Darwin":
        fmconf_os = "macosx"
    elif platform.system() == "Windows":
        fmconf_os = "windows"

    with open(str(log_), "a", encoding="utf-8", errors="replace") as f:
        f.write("# Information about shell:\n# \n")

        f.write("# Create another shell in shell-cache like this one:\n")
        f.write(f"# python3 -u -m ocs.compile_shell "
                f'-b "{shell.build_opts.build_options_str}" -r {shell.hg_hash}\n# \n')

        f.write("# Full environment is:\n")
        f.write(f"# {shell.env_full}\n# \n")

        f.write("# Full configuration command with needed environment variables is:\n")
        f.write(f'# {" ".join(quote(str(x)) for x in shell.env_added)} '
                f'{" ".join(quote(str(x)) for x in shell.cfg_cmd_excl_env)}\n# \n')

        # .fuzzmanagerconf details
        f.write("\n")
        f.write("[Main]\n")
        f.write(f"platform = {fmconf_platform}\n")
        f.write(f"product = {shell.repo_name}\n")
        f.write(f"product_version = {shell.hg_hash}\n")
        f.write(f"os = {fmconf_os}\n")

        f.write("\n")
        f.write("[Metadata]\n")
        f.write(f"buildFlags = {shell.build_opts.build_options_str}\n")
        f.write(f'majorVersion = {shell.version.split(".")[0]}\n')
        f.write(f"pathPrefix = {shell.build_opts.repo_dir}/\n")
        f.write(f"version = {shell.version}\n")


def sm_compile(shell: Any) -> Any:  # pylint:disable=too-complex
    """Compile a binary and copy essential compiled files into a desired structure.

    :param shell: SpiderMonkey shell parameters
    :raise OSError: Raises when a compiled shell is absent
    :return: Path to the compiled shell
    """
    cmd_list = [MAKE_BINARY, "-C", str(shell.js_objdir), f"-j{COMPILATION_JOBS}", "-s"]
    # Note that having a non-zero exit code does not mean that the operation did not succeed,
    # for example when compiling a shell. A non-zero exit code can appear even though a shell compiled successfully.
    # Thus, we should *not* use check=True here.
    out = subprocess.run(cmd_list,
                         check=False,
                         cwd=shell.js_objdir,
                         env=shell.env_full,
                         stderr=subprocess.STDOUT,
                         stdout=subprocess.PIPE).stdout.decode("utf-8", errors="replace")

    if not shell.shell_compiled_path.is_file():
        if ((platform.system() == "Linux" or platform.system() == "Darwin") and
                ("internal compiler error: Killed (program cc1plus)" in out or  # GCC running out of memory
                 "error: unable to execute command: Killed" in out)):  # Clang running out of memory
            print("Trying once more due to the compiler running out of memory...")
            out = subprocess.run(cmd_list,
                                 check=False,
                                 cwd=shell.js_objdir,
                                 env=shell.env_full,
                                 stderr=subprocess.STDOUT,
                                 stdout=subprocess.PIPE).stdout.decode("utf-8", errors="replace")
        # A non-zero error can be returned during make, but eventually a shell still gets compiled.
        if shell.shell_compiled_path.is_file():
            print("A shell was compiled even though there was a non-zero exit code. Continuing...")

    if shell.shell_compiled_path.is_file():
        shutil.copy2(str(shell.shell_compiled_path), str(shell.shell_cache_js_bin_path))
        for run_lib in shell.shell_compiled_runlibs_path:
            if run_lib.is_file():
                shutil.copy2(str(run_lib), str(shell.shell_cache_dir))
        if platform.system() == "Windows" and shell.build_opts.enableAddressSanitizer:
            shutil.copy2(str(WIN_MOZBUILD_CLANG_PATH / "lib" / "clang" / CLANG_VER / "lib" / "windows" /
                             "clang_rt.asan_dynamic-x86_64.dll"),
                         str(shell.shell_cache_dir))

        jspc_new_file_path = shell.js_objdir / "js" / "src" / "build" / "js.pc"
        with open(str(jspc_new_file_path), mode="r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("Version: "):  # Sample line: "Version: 47.0a2"
                    shell.version = line.split(": ")[1].rstrip()
    else:
        print(f"{MAKE_BINARY} did not result in a js shell:")
        with open(str(shell.shell_cache_dir / f"{shell.shell_name_without_ext}.busted"), "a",
                  encoding="utf-8", errors="replace") as f:
            f.write(f"Compilation of {shell.repo_name} rev {shell.hg_hash} "
                    f"failed with the following output:\n")
            f.write(out)
        raise OSError(f"{MAKE_BINARY} did not result in a js shell.")

    return shell.shell_compiled_path


def obtain_shell(shell: Any, update_to_rev: Optional[str] = None, _update_latest_txt: bool = False) -> None:
    """Obtain a js shell. Keep the objdir for now, especially .a files, for symbols.

    :param shell: Potential compiled shell object
    :param update_to_rev: Specified revision to be updated to
    :param _update_latest_txt: Whether the latest .txt file should be updated (likely obsolete)

    :raise OSError: When a cached shell that failed compilation was found, or when compilation failed
    :raise KeyboardInterrupt: When ctrl-c was pressed during shell compilation
    :raise CalledProcessError: When shell compilation failed
    """
    # pylint: disable=too-many-branches,too-complex,too-many-statements
    assert fs_helpers.get_lock_dir_path(Path.home(), shell.build_opts.repo_dir).is_dir()
    cached_no_shell = shell.shell_cache_js_bin_path.with_suffix(".busted")

    if shell.shell_cache_js_bin_path.is_file():
        # Don't remove the comma at the end of this line, and thus remove the newline printed.
        # We would break JSBugMon.
        print("Found cached shell...")
        # Assuming that since the binary is present, everything else (e.g. symbols) is also present
        if platform.system() == "Windows":
            misc_progs.verify_full_win_pageheap(shell.shell_cache_js_bin_path)
        return

    if cached_no_shell.is_file():
        raise OSError("Found a cached shell that failed compilation...")
    if shell.shell_cache_dir.is_dir():
        print("Found a cache dir without a successful/failed shell...")
        fs_helpers.rm_tree_incl_readonly_files(shell.shell_cache_dir)

    shell.shell_cache_dir.mkdir()

    try:
        if update_to_rev:
            # Print *with* a trailing newline to avoid breaking other stuff
            print(f"Updating to rev {update_to_rev} in the {shell.build_opts.repo_dir} repository...")
            subprocess.run(["hg", "-R", str(shell.build_opts.repo_dir),
                            "update", "-C", "-r", update_to_rev],
                           check=True,
                           cwd=os.getcwd(),
                           stderr=subprocess.DEVNULL,
                           timeout=9999)

        configure_js_shell_compile(shell)
        if platform.system() == "Windows":
            misc_progs.verify_full_win_pageheap(shell.shell_cache_js_bin_path)
    except KeyboardInterrupt:
        fs_helpers.rm_tree_incl_readonly_files(shell.shell_cache_dir)
        raise
    except (subprocess.CalledProcessError, OSError) as ex:
        fs_helpers.rm_tree_incl_readonly_files(shell.shell_cache_dir / "objdir-js")
        if shell.shell_cache_js_bin_path.is_file():  # Switch to contextlib.suppress when we are fully on Python 3
            shell.shell_cache_js_bin_path.unlink()
        with open(str(cached_no_shell), "a", encoding="utf-8", errors="replace") as f:
            f.write(f"\nCaught exception {ex!r} ({ex})\n")
            f.write("Backtrace:\n")
            f.write(f"{traceback.format_exc()}\n")
        print(f"Compilation failed ({ex}) (details in {cached_no_shell})")
        raise


def main() -> None:
    """Execute main() function in CompiledShell class."""
    sys.exit(CompiledShell.main())


if __name__ == "__main__":
    main()
