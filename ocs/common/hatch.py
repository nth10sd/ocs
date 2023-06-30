"""Common shell object code"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from zzbase.util.constants import ALL_LIBS
from zzbase.util.constants import HostPlatform as Hp

from ocs import build_options
from ocs.util import fs_helpers

if TYPE_CHECKING:
    import argparse


class CommonShellError(BaseException):
    """Error class unique to CommonShell objects."""


class CommonShell:
    """A CommonShell object represents an actual compiled shell binary.

    :param build_opts: Object containing the build options defined in build_options.py
    :param cset_hash: Changeset hash
    """

    def __init__(self, build_opts: argparse.Namespace, cset_hash: str):
        self._name_no_ext = build_options.compute_shell_name(build_opts, cset_hash)
        self.build_opts = build_opts

        self._js_objdir = Path()

        self._cfg_cmd_excl_env: list[str] = []
        self._added_env: list[str] = []
        self._full_env: dict[str, str] = {}

        self._js_version = ""

    @property
    def cfg_cmd_excl_env(self) -> list[str]:
        """Retrieve the configure command excluding the enviroment variables.

        :return: Configure command
        """
        return self._cfg_cmd_excl_env

    @cfg_cmd_excl_env.setter
    def cfg_cmd_excl_env(self, cfg: list[str]) -> None:
        """Sets the configure command excluding the enviroment variables.

        :param cfg: Configure command
        """
        self._cfg_cmd_excl_env = cfg

    @property
    def env_added(self) -> list[str]:
        """Retrieve environment variables that were added.

        :return: Added environment variables
        """
        return self._added_env

    @env_added.setter
    def env_added(self, added_env: list[str]) -> None:
        """Set environment variables that were added.

        :param added_env: Added environment variables
        """
        self._added_env = added_env

    @property
    def env_full(self) -> dict[str, str]:
        """Retrieve the full environment including the newly added variables.

        :return: Full environment
        """
        return self._full_env

    @env_full.setter
    def env_full(self, full_env: dict[str, str]) -> None:
        """Set the full environment including the newly added variables.

        :param full_env: Full environment
        """
        self._full_env = full_env

    @property
    def js_cfg_path(self) -> Path:
        """Retrieve the configure file in a js/src directory.

        :return: Full path to the configure file
        """
        return Path(self.build_opts.repo_dir) / "js" / "src" / "configure"

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
        return (
            fs_helpers.ensure_cache_dir(Path.home())
            / self._name_no_ext
            / self.shell_name_with_ext
        )

    @property
    def shell_compiled_path(self) -> Path:
        """Retrieve full path to the original location of js binary compiled in the
        shell cache.

        :return: Original binary location that was compiled in the shell cache
        """
        full_path = self._js_objdir / "dist" / "bin" / "js"
        return full_path.with_suffix(".exe") if Hp.IS_WIN_MB else full_path

    @property
    def shell_compiled_runlibs_path(self) -> list[Path]:
        """Retrieve the full path to the original location of the libraries of js binary
        compiled in the shell cache.

        :return: Original libraries' location of the binary compiled in the shell cache
        """
        return [self._js_objdir / "dist" / "bin" / runlib for runlib in ALL_LIBS]

    @property
    def shell_name_with_ext(self) -> str:
        """Retrieve the name of the compiled js shell with the file extension.

        :return: Name of the compiled js shell with the file extension
        """
        return f"{self._name_no_ext}.exe" if Hp.IS_WIN_MB else f"{self._name_no_ext}"

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
