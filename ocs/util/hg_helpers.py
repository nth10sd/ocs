"""Helper functions involving Mercurial (hg)."""

from __future__ import annotations

import configparser
from logging import INFO as INFO_LOG_LEVEL
from pathlib import Path
import subprocess

from zzbase.util.logging import get_logger

HG_HELPERS_LOG = get_logger(
    __name__, fmt="%(asctime)s %(levelname)-8s [%(funcName)s] %(message)s"
)
HG_HELPERS_LOG.setLevel(INFO_LOG_LEVEL)


def exists_and_is_ancestor(
    repo_dir: Path,
    rev_a: str,
    rev_b: str,
) -> bool:
    """Return true iff `rev_a` exists and is an ancestor of `rev_b`.

    :param repo_dir: Path to the repository
    :param rev_a: Repository ID hash that should be an ancestor of `rev_b`
    :param rev_b: Repository ID hash that should be a descendent of `rev_a`
    :return: True if the `rev_a` exists and is an ancestor of `rev_b`
    """
    # Note that if `rev_a` is the same as `rev_b`, it will return True
    # Takes advantage of "id(badhash)" being the empty set,
    # in contrast to just "badhash", which is an error
    out = subprocess.run(
        [
            "hg",
            "-R",
            str(repo_dir),
            "log",
            "-r",
            f"{rev_a} and ancestor({rev_a},{rev_b})",
            "--template={node|short}",
        ],
        check=False,
        cwd=Path.cwd(),
        stderr=subprocess.STDOUT,
        stdout=subprocess.PIPE,
        timeout=999,
    ).stdout.decode("utf-8", errors="replace")
    return (
        out != ""  # pylint: disable=compare-to-empty-string
        and out.find("abort: unknown revision") < 0
    )


def get_repo_hash_and_id(
    repo_dir: Path,
    repo_rev: str = "parents() and default",
) -> tuple[str, str, bool]:
    """Return the repository hash and id, and whether it is on default.

    It will also ask what the user wants to do, should the repository not be on default.

    :param repo_dir: Full path to the repository
    :param repo_rev: Intended Mercurial changeset details to retrieve
    :raise ValueError: Raises if the input is invalid
    :raise SystemExit: When abort is selected
    :return: Changeset hash, local numerical ID, whether repository is on default tip
    """
    # This will return null if the repository is not on default.
    hg_log_template_cmds = [
        "hg",
        "-R",
        str(repo_dir),
        "log",
        "-r",
        repo_rev,
        "--template",
        "{node|short} {rev}",
    ]
    hg_id_full = subprocess.run(
        hg_log_template_cmds,
        cwd=Path.cwd(),
        check=True,
        stdout=subprocess.PIPE,
        timeout=99,
    ).stdout.decode("utf-8", errors="replace")
    if not (is_on_default := bool(hg_id_full)):
        update_default = input(
            "Not on default tip! "
            "Would you like to (a)bort, update to (d)efault, or (u)se this rev: ",
        )
        update_default = update_default.strip()
        if update_default == "a":
            raise SystemExit("\nAborting...\n")

        if update_default == "d":
            subprocess.run(["hg", "-R", str(repo_dir), "update", "default"], check=True)
            is_on_default = True
        elif update_default == "u":
            hg_log_template_cmds = [
                "hg",
                "-R",
                str(repo_dir),
                "log",
                "-r",
                "parents()",
                "--template",
                "{node|short} {rev}",
            ]
        else:
            raise ValueError("Invalid choice.")
        hg_id_full = subprocess.run(
            hg_log_template_cmds,
            cwd=Path.cwd(),
            check=True,
            stdout=subprocess.PIPE,
            timeout=99,
        ).stdout.decode("utf-8", errors="replace")
    if hg_id_full == "":  # pylint: disable=compare-to-empty-string
        raise ValueError("hg_id_full should not be an empty string")
    (hg_id_hash, hg_id_local_num) = hg_id_full.split(" ")
    HG_HELPERS_LOG.debug("Finished getting the repository's hash and local id number")
    return hg_id_hash, hg_id_local_num, is_on_default


def hgrc_repo_name(repo_dir: Path) -> str:
    """Extract the Mercurial repo name from the hgrc file.

    :param repo_dir: Repo directory
    :return: Name of the repo in the .hgrc file
    """
    hgrc_cfg = configparser.ConfigParser()
    hgrc_cfg.read(repo_dir / ".hg" / "hgrc")
    # Not all default entries in [paths] end with "/".
    return [i for i in hgrc_cfg.get("paths", "default").split("/") if i][-1]
